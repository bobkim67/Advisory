"""Phase E-9 — SAA MVO / Efficient Frontier Visualization.

E-9A: efficient frontier diagnostic JSON (read-only)
E-9B: SAA MVO PNG (4-panel: CMA scatter + ρ heatmap + frontier + SAA bar)

read-only diagnostic — production optimizer 결과를 변경하지 않음. frontier 는 별도
scipy.optimize SLSQP 호출로 grid scan. long-only + sum=1 만 적용 (Phase D relaxed
정책 정합).

Hard requirements:
- 입력 portfolio JSON / E-7 explainability 모두 mutate 없음.
- direct SAA telemetry (saa_diagnostics.saa_weights) 가 없으면 ValueError.
- inferred SAA 경로 절대 사용 금지.
- 새로운 production allocation 생성하지 않음 — diagnostic frontier 만.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "e9.1"
DEFAULT_GRID_POINTS = 31
ZERO_WEIGHT_THRESHOLD = 0.005


# ---------------------------------------------------------------------------
# Telemetry guard + helpers
# ---------------------------------------------------------------------------


def _require_direct_saa_and_cma(portfolio: dict[str, Any]) -> dict[str, Any]:
    diag = portfolio.get("diagnostics") or {}
    saa = diag.get("saa_diagnostics") or {}
    cma = saa.get("cma") or {}
    if not saa.get("saa_weights"):
        raise ValueError(
            "E-9 SAA frontier requires direct SAA telemetry "
            "`diagnostics.saa_diagnostics.saa_weights` (E-6.2 T-6). "
            "Inferred SAA is forbidden."
        )
    for need in ("expected_returns", "volatilities", "covariance_matrix"):
        if not cma.get(need):
            raise ValueError(
                f"E-9 SAA frontier requires `saa_diagnostics.cma.{need}` "
                "(E-6.2 T-1~T-4). re-run build_portfolio with telemetry patch."
            )
    return saa


def _ordered_keys(cma: dict[str, Any]) -> list[str]:
    keys = cma.get("asset_keys") or list(
        (cma.get("expected_returns") or {}).keys()
    )
    return [str(k) for k in keys]


def _vec(d: dict[str, float], keys: list[str]) -> list[float]:
    return [float(d.get(k, 0.0)) for k in keys]


def _mat(d: dict[str, dict[str, float]], keys: list[str]) -> list[list[float]]:
    return [[float((d.get(ki) or {}).get(kj, 0.0)) for kj in keys] for ki in keys]


def _matvec(mat: list[list[float]], v: list[float]) -> list[float]:
    n = len(v)
    out = [0.0] * n
    for i in range(n):
        s = 0.0
        row = mat[i]
        for j in range(n):
            s += row[j] * v[j]
        out[i] = s
    return out


def _portfolio_metrics(
    weights: list[float], er: list[float], cov: list[list[float]], rf: float
) -> tuple[float, float, float]:
    sigma_w = _matvec(cov, weights)
    var = sum(weights[i] * sigma_w[i] for i in range(len(weights)))
    var = max(var, 0.0)
    vol = math.sqrt(var)
    ret = sum(weights[i] * er[i] for i in range(len(weights)))
    sharpe = (ret - rf) / vol if vol > 1e-12 else float("nan")
    return ret, vol, sharpe


# ---------------------------------------------------------------------------
# Frontier solvers (scipy SLSQP, read-only diagnostic)
# ---------------------------------------------------------------------------


def _solve_min_var_at_target(
    target_return: float | None,
    er: list[float],
    cov: list[list[float]],
) -> dict[str, Any]:
    """Long-only + sum=1, optionally w·μ=target_return. minimize w·Σw."""
    import numpy as np
    from scipy.optimize import minimize

    n = len(er)
    mu = np.asarray(er, dtype=float)
    sigma = np.asarray(cov, dtype=float)
    x0 = np.ones(n) / n

    def fun(w):
        return float(w @ sigma @ w)

    def grad(w):
        return 2.0 * (sigma @ w)

    cons: list[dict[str, Any]] = [
        {"type": "eq", "fun": lambda w: float(w.sum() - 1.0),
         "jac": lambda w: np.ones(n)},
    ]
    if target_return is not None:
        tr = float(target_return)
        cons.append({
            "type": "eq",
            "fun": lambda w: float(w @ mu - tr),
            "jac": lambda w: mu,
        })
    bounds = [(0.0, 1.0)] * n

    result = minimize(
        fun, x0, jac=grad, method="SLSQP",
        constraints=cons, bounds=bounds,
        options={"maxiter": 300, "ftol": 1e-10, "disp": False},
    )
    w = result.x.tolist()
    var = float(result.fun)
    return {
        "success": bool(result.success),
        "status": str(result.message),
        "weights": w,
        "variance": max(var, 0.0),
    }


def _solve_max_sharpe(er: list[float], cov: list[list[float]], rf: float) -> dict[str, Any]:
    """직접 max sharpe — minimize -sharpe, long-only + sum=1."""
    import numpy as np
    from scipy.optimize import minimize

    n = len(er)
    mu = np.asarray(er, dtype=float)
    sigma = np.asarray(cov, dtype=float)
    x0 = np.ones(n) / n

    def neg_sharpe(w):
        ret = float(w @ mu)
        var = float(w @ sigma @ w)
        if var <= 1e-16:
            return 1e6
        return -((ret - rf) / math.sqrt(var))

    cons = [
        {"type": "eq", "fun": lambda w: float(w.sum() - 1.0)},
    ]
    bounds = [(0.0, 1.0)] * n
    result = minimize(
        neg_sharpe, x0, method="SLSQP",
        constraints=cons, bounds=bounds,
        options={"maxiter": 300, "ftol": 1e-10},
    )
    return {
        "success": bool(result.success),
        "status": str(result.message),
        "weights": result.x.tolist(),
    }


def build_frontier_data(
    portfolio: dict[str, Any],
    *,
    grid_points: int = DEFAULT_GRID_POINTS,
) -> dict[str, Any]:
    """saa_diagnostics 에서 μ/Σ + direct SAA → efficient frontier dict.

    raises ValueError if direct SAA / cma telemetry missing.
    """
    saa = _require_direct_saa_and_cma(portfolio)
    cma = saa["cma"]
    keys = _ordered_keys(cma)
    er = _vec(cma["expected_returns"], keys)
    cov = _mat(cma["covariance_matrix"], keys)
    corr_raw = cma.get("correlation_matrix") or {}
    sig_vals = _vec(cma.get("volatilities") or {}, keys)
    rf = float(saa.get("rf") or 0.0)

    saa_w_dict = {str(k): float(v) for k, v in saa["saa_weights"].items()}
    saa_w = _vec(saa_w_dict, keys)

    # Selected SAA metrics (direct telemetry, computed read-only)
    sel_ret, sel_vol, sel_sharpe = _portfolio_metrics(saa_w, er, cov, rf)

    # min-vol point (no target return constraint)
    mv = _solve_min_var_at_target(None, er, cov)
    mv_ret, mv_vol, mv_sharpe = _portfolio_metrics(mv["weights"], er, cov, rf)

    # max-sharpe point
    ms = _solve_max_sharpe(er, cov, rf)
    ms_ret, ms_vol, ms_sharpe = _portfolio_metrics(ms["weights"], er, cov, rf)

    # target return grid: from min_vol_return to max(mu) (single-asset upper bound)
    upper_ret = max(er)
    lower_ret = mv_ret
    if upper_ret <= lower_ret + 1e-9:
        # degenerate (모든 자산 동일 mu)
        upper_ret = lower_ret + 1e-3
    grid = [
        lower_ret + (upper_ret - lower_ret) * i / max(grid_points - 1, 1)
        for i in range(grid_points)
    ]

    points: list[dict[str, Any]] = []
    failed = 0
    for tr in grid:
        sol = _solve_min_var_at_target(tr, er, cov)
        if not sol["success"] or sol["variance"] < 0:
            failed += 1
            continue
        w = sol["weights"]
        ret, vol, sh = _portfolio_metrics(w, er, cov, rf)
        points.append({
            "expected_return": float(ret),
            "volatility": float(vol),
            "sharpe": (float(sh) if math.isfinite(sh) else None),
            "weights": {keys[i]: float(w[i]) for i in range(len(keys))},
            "status": sol["status"],
        })

    points.sort(key=lambda p: p["volatility"])

    selected_matches_max_sharpe = (
        abs(sel_sharpe - ms_sharpe) < 5e-3
        and abs(sel_ret - ms_ret) < 1e-3
        and abs(sel_vol - ms_vol) < 1e-3
    ) if (math.isfinite(sel_sharpe) and math.isfinite(ms_sharpe)) else False

    constraints_block = [
        {
            "constraint_id": "long_only",
            "description": "All asset weights >= 0",
            "applied": True,
            "lower_bound": 0.0,
            "upper_bound": None,
            "binding_assets": [
                keys[i] for i, w in enumerate(saa_w) if w <= 1e-9
            ],
        },
        {
            "constraint_id": "weight_sum_eq_1",
            "description": "Sum of weights = 1.0 (full investment)",
            "applied": True,
            "lower_bound": 1.0,
            "upper_bound": 1.0,
            "binding_assets": [],
        },
        {
            "constraint_id": "weight_bounds_per_asset",
            "description": "Per-asset min/max (Phase D relaxed → [0, 1])",
            "applied": False,
            "lower_bound": 0.0,
            "upper_bound": 1.0,
            "binding_assets": [],
        },
        {
            "constraint_id": "equity_sum",
            "description": "Equity bucket sum (Phase D relaxed → [0, 1])",
            "applied": False,
            "lower_bound": 0.0,
            "upper_bound": 1.0,
            "binding_assets": [],
        },
        {
            "constraint_id": "fixed_income_sum",
            "description": "Fixed-income bucket sum (Phase D relaxed → [0, 1])",
            "applied": False,
            "lower_bound": 0.0,
            "upper_bound": 1.0,
            "binding_assets": [],
        },
    ]

    payload: dict[str, Any] = {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "product_type": str(portfolio.get("portfolio_type") or ""),
            "portfolio_as_of_date": str(portfolio.get("as_of_date") or ""),
            "source_mode": str(portfolio.get("source_type") or "file"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "inputs": {
            "asset_keys": keys,
            "expected_returns": {keys[i]: er[i] for i in range(len(keys))},
            "volatilities": {keys[i]: sig_vals[i] for i in range(len(keys))},
            "covariance_matrix": {
                keys[i]: {keys[j]: cov[i][j] for j in range(len(keys))}
                for i in range(len(keys))
            },
            "correlation_matrix": {
                str(ki): {str(kj): float((corr_raw.get(ki) or {}).get(kj, 0.0))
                          for kj in keys}
                for ki in keys
            },
            "risk_free_rate": rf,
        },
        "constraints": constraints_block,
        "selected_saa": {
            "weights": saa_w_dict,
            "expected_return": float(sel_ret),
            "volatility": float(sel_vol),
            "sharpe": (float(sel_sharpe) if math.isfinite(sel_sharpe) else None),
            "point_label": "selected_saa_direct_telemetry",
        },
        "frontier": {
            "method": "scipy.optimize SLSQP — minimize w'Σw s.t. w'μ=target, sum w=1, w>=0",
            "target_return_grid": grid,
            "points": points,
        },
        "reference_points": {
            "min_vol": {
                "expected_return": float(mv_ret),
                "volatility": float(mv_vol),
                "sharpe": (float(mv_sharpe) if math.isfinite(mv_sharpe) else None),
                "weights": {keys[i]: float(mv["weights"][i]) for i in range(len(keys))},
            },
            "max_sharpe": {
                "expected_return": float(ms_ret),
                "volatility": float(ms_vol),
                "sharpe": (float(ms_sharpe) if math.isfinite(ms_sharpe) else None),
                "weights": {keys[i]: float(ms["weights"][i]) for i in range(len(keys))},
            },
            "selected_saa": {
                "expected_return": float(sel_ret),
                "volatility": float(sel_vol),
                "sharpe": (float(sel_sharpe) if math.isfinite(sel_sharpe) else None),
                "weights": saa_w_dict,
            },
        },
        "diagnostics": {
            "frontier_point_count": len(points),
            "failed_grid_points": failed,
            "selected_matches_max_sharpe": selected_matches_max_sharpe,
            "warnings": [],
            "missing_data": [],
        },
    }
    return payload


def write_frontier_json(payload: dict[str, Any], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return out_path


# ---------------------------------------------------------------------------
# SAA MVO PNG (E-9B)
# ---------------------------------------------------------------------------


def _select_korean_font() -> str | None:
    import matplotlib.font_manager as fm

    candidates = ("Malgun Gothic", "AppleGothic", "NanumGothic", "Gulim", "MS Gothic")
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            return name
    return None


def render_saa_mvo(
    frontier_payload: dict[str, Any],
    out_path: Path,
    *,
    label: str | None = None,
) -> Path:
    """4-panel SAA MVO PNG: header / CMA scatter / corr heatmap / frontier / SAA bar."""
    payload = deepcopy(frontier_payload)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import gridspec as _gs
    import numpy as np

    font_name = _select_korean_font()
    if font_name:
        plt.rcParams["font.family"] = [font_name, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    meta = payload["meta"]
    inputs = payload["inputs"]
    constraints = payload["constraints"]
    sel = payload["selected_saa"]
    ref = payload["reference_points"]
    diag = payload["diagnostics"]
    points = payload["frontier"]["points"]

    keys = list(inputs["asset_keys"])
    er = [inputs["expected_returns"][k] for k in keys]
    sig = [inputs["volatilities"][k] for k in keys]
    corr = [
        [inputs["correlation_matrix"][ki][kj] for kj in keys] for ki in keys
    ]
    saa_w = sel["weights"]

    fig = plt.figure(figsize=(14.0, 16.5))
    gs = _gs.GridSpec(
        nrows=5, ncols=2,
        height_ratios=[0.55, 2.6, 2.8, 2.8, 2.4],
        width_ratios=[1.0, 1.0],
        hspace=0.55, wspace=0.20,
        left=0.07, right=0.97, top=0.97, bottom=0.05,
    )

    # --- 1. Header ---
    ax_h = fig.add_subplot(gs[0, :])
    ax_h.set_axis_off()
    pt = (meta.get("product_type") or "").upper()
    ax_h.text(
        0.0, 0.85,
        f"SAA MVO — {pt} Portfolio  ·  Efficient Frontier Diagnostic",
        transform=ax_h.transAxes,
        fontsize=15, fontweight="bold", va="top",
    )
    constraint_short = "  ·  ".join([
        f"{c['constraint_id']}={'on' if c['applied'] else 'off'}"
        for c in constraints
    ])
    ax_h.text(
        0.0, 0.45,
        f"as_of={meta.get('portfolio_as_of_date')}  ·  source={meta.get('source_mode')}  "
        f"·  objective=max_sharpe (relaxed)  ·  rf={inputs.get('risk_free_rate', 0.0):.4f}",
        transform=ax_h.transAxes, fontsize=10.5, color="#333", va="center",
    )
    ax_h.text(
        0.0, 0.10,
        f"constraints: {constraint_short}",
        transform=ax_h.transAxes, fontsize=9.5, color="#555", va="bottom",
    )

    # --- 2. CMA scatter (E[R] vs σ, per asset) ---
    ax_sc = fig.add_subplot(gs[1, 0])
    weights_pct = [float(saa_w.get(k, 0.0)) * 100 for k in keys]
    sizes = [40 + 18 * w for w in weights_pct]  # SAA weight 시각화
    sc = ax_sc.scatter(
        [s * 100 for s in sig], [r * 100 for r in er],
        s=sizes, c=weights_pct, cmap="viridis",
        edgecolors="#333", linewidths=0.6, alpha=0.9,
    )
    for i, k in enumerate(keys):
        ax_sc.annotate(
            k, (sig[i] * 100, er[i] * 100),
            xytext=(5, 5), textcoords="offset points",
            fontsize=8, color="#222",
        )
    ax_sc.set_xlabel("Volatility (σ, %)")
    ax_sc.set_ylabel("Expected return (μ, %)")
    ax_sc.set_title(
        "1. CMA Inputs (asset μ vs σ — bubble size & color = SAA weight)",
        fontsize=11, fontweight="bold", loc="left",
    )
    ax_sc.grid(linestyle=":", alpha=0.4)
    cb = plt.colorbar(sc, ax=ax_sc, fraction=0.04, pad=0.02)
    cb.set_label("SAA weight (%)", fontsize=8)
    cb.ax.tick_params(labelsize=8)

    # --- 3. Correlation heatmap ---
    ax_hm = fig.add_subplot(gs[1, 1])
    arr = np.asarray(corr)
    im = ax_hm.imshow(arr, cmap="RdBu_r", vmin=-1.0, vmax=1.0)
    ax_hm.set_xticks(range(len(keys)))
    ax_hm.set_yticks(range(len(keys)))
    ax_hm.set_xticklabels(keys, rotation=45, ha="right", fontsize=8)
    ax_hm.set_yticklabels(keys, fontsize=8)
    ax_hm.set_title(
        "2. Correlation Matrix (ρ)",
        fontsize=11, fontweight="bold", loc="left",
    )
    for i in range(len(keys)):
        for j in range(len(keys)):
            ax_hm.text(
                j, i, f"{arr[i, j]:.2f}",
                ha="center", va="center",
                fontsize=7, color=("white" if abs(arr[i, j]) > 0.55 else "#222"),
            )
    cb2 = plt.colorbar(im, ax=ax_hm, fraction=0.04, pad=0.02)
    cb2.ax.tick_params(labelsize=8)

    # --- 4. Efficient Frontier ---
    ax_ef = fig.add_subplot(gs[2:4, :])
    if points:
        fr_vol = [p["volatility"] * 100 for p in points]
        fr_ret = [p["expected_return"] * 100 for p in points]
        ax_ef.plot(fr_vol, fr_ret, color="#3a6db0", linewidth=1.5, label="Efficient frontier")
    # individual asset 점
    ax_ef.scatter(
        [s * 100 for s in sig], [r * 100 for r in er],
        s=40, c="#bbb", edgecolors="#666", linewidths=0.5,
        label="Individual assets",
    )
    for i, k in enumerate(keys):
        ax_ef.annotate(
            k, (sig[i] * 100, er[i] * 100),
            xytext=(4, 4), textcoords="offset points",
            fontsize=7, color="#666",
        )
    # min vol + max sharpe + selected SAA
    ax_ef.scatter(
        [ref["min_vol"]["volatility"] * 100], [ref["min_vol"]["expected_return"] * 100],
        s=180, marker="o", color="#3a8a3e", edgecolors="white", linewidths=1.5,
        label=f"Min Vol  (Sharpe={ref['min_vol']['sharpe']:.3f})",
        zorder=5,
    )
    ax_ef.scatter(
        [ref["max_sharpe"]["volatility"] * 100], [ref["max_sharpe"]["expected_return"] * 100],
        s=200, marker="D", color="#c97a2a", edgecolors="white", linewidths=1.5,
        label=f"Max Sharpe (Sharpe={ref['max_sharpe']['sharpe']:.3f})",
        zorder=5,
    )
    sel_x = sel["volatility"] * 100
    sel_y = sel["expected_return"] * 100
    ax_ef.scatter(
        [sel_x], [sel_y],
        s=320, marker="*", color="#a83232", edgecolors="white", linewidths=1.5,
        label=f"Selected SAA (Sharpe={sel['sharpe']:.3f})  ★",
        zorder=6,
    )
    match_text = (
        "✓ matches max-Sharpe"
        if diag.get("selected_matches_max_sharpe") else
        "≠ max-Sharpe (grid sampling vs solver may differ)"
    )
    ax_ef.annotate(
        f"Selected SAA\nE[R]={sel_y:.2f}%  σ={sel_x:.2f}%\nSharpe={sel['sharpe']:.4f}\n{match_text}",
        xy=(sel_x, sel_y),
        xytext=(35, -15), textcoords="offset points",
        fontsize=10, fontweight="bold", color="#a83232",
        bbox=dict(facecolor="white", edgecolor="#a83232", boxstyle="round,pad=0.4", alpha=0.95),
        arrowprops=dict(arrowstyle="-", color="#a83232", lw=0.8),
    )
    ax_ef.set_xlabel("Volatility (σ, %)", fontsize=10)
    ax_ef.set_ylabel("Expected return (μ, %)", fontsize=10)
    ax_ef.set_title(
        "3. Efficient Frontier (long-only + sum=1; relaxed bounds)",
        fontsize=12, fontweight="bold", loc="left",
    )
    ax_ef.legend(loc="lower right", fontsize=9)
    ax_ef.grid(linestyle=":", alpha=0.4)

    # --- 5. SAA weights bar ---
    ax_w = fig.add_subplot(gs[4, :])
    nonzero = [(k, float(saa_w.get(k, 0.0)) * 100) for k in keys
               if float(saa_w.get(k, 0.0)) >= ZERO_WEIGHT_THRESHOLD]
    nonzero.sort(key=lambda x: -x[1])
    omitted = [k for k in keys if float(saa_w.get(k, 0.0)) < ZERO_WEIGHT_THRESHOLD]
    if nonzero:
        names = [t[0] for t in nonzero]
        ws = [t[1] for t in nonzero]
        ax_w.barh(names, ws, color="#3a6db0")
        ax_w.invert_yaxis()
        ax_w.set_xlabel("SAA weight (%)")
        upper = max(ws) * 1.20
        ax_w.set_xlim(0, max(upper, 1.0))
        ax_w.grid(axis="x", linestyle=":", alpha=0.4)
        for i, w in enumerate(ws):
            ax_w.text(w + upper * 0.005, i, f"{w:.2f}%", va="center", fontsize=9)
    else:
        ax_w.set_axis_off()
    ax_w.set_title(
        "4. Selected SAA Weights (direct telemetry — saa_diagnostics.saa_weights)",
        fontsize=12, fontweight="bold", loc="left",
    )
    if omitted:
        omitted_short = ", ".join(omitted[:6]) + ("…" if len(omitted) > 6 else "")
        ax_w.text(
            1.0, -0.20,
            f"omitted (< {ZERO_WEIGHT_THRESHOLD * 100:.1f}%): "
            f"{len(omitted)} assets — {omitted_short}",
            transform=ax_w.transAxes, ha="right", va="top",
            fontsize=8.5, color="#666",
        )

    # footer — relaxed disclaimer
    fig.text(
        0.5, 0.012,
        "Relaxed diagnostic: long-only and full-investment constraints only; "
        "asset caps/bucket bands not applied in this phase.",
        ha="center", fontsize=9, color="#7a3a3a",
    )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# Summary md
# ---------------------------------------------------------------------------


def render_saa_frontier_summary_md(
    *,
    as_of_run: str,
    etf_payload: dict[str, Any],
    fund_payload: dict[str, Any],
    etf_png_rel: str,
    fund_png_rel: str,
    out_path: Path,
) -> Path:
    lines: list[str] = []
    lines.append(f"# SAA MVO / Efficient Frontier Summary ({as_of_run})")
    lines.append("")
    lines.append(f"> schema_version: {SCHEMA_VERSION}")
    lines.append(
        "> Read-only diagnostic. Frontier 는 별도 SLSQP grid scan — "
        "production allocation 결과 미변경."
    )
    lines.append("")
    for label, payload, png_rel in (("ETF", etf_payload, etf_png_rel), ("Fund", fund_payload, fund_png_rel)):
        meta = payload["meta"]
        sel = payload["selected_saa"]
        ref = payload["reference_points"]
        diag = payload["diagnostics"]
        lines.append(f"## {label}")
        lines.append("")
        lines.append(
            f"- portfolio as_of: **{meta.get('portfolio_as_of_date')}**, "
            f"source: **{meta.get('source_mode')}**"
        )
        lines.append(
            f"- selected SAA: E[R]={sel['expected_return'] * 100:.2f}%, "
            f"σ={sel['volatility'] * 100:.2f}%, Sharpe={sel['sharpe']:.4f}"
        )
        lines.append(
            f"- min-vol: E[R]={ref['min_vol']['expected_return'] * 100:.2f}%, "
            f"σ={ref['min_vol']['volatility'] * 100:.2f}%, Sharpe={ref['min_vol']['sharpe']:.4f}"
        )
        lines.append(
            f"- max-Sharpe: E[R]={ref['max_sharpe']['expected_return'] * 100:.2f}%, "
            f"σ={ref['max_sharpe']['volatility'] * 100:.2f}%, "
            f"Sharpe={ref['max_sharpe']['sharpe']:.4f}"
        )
        lines.append(
            f"- selected_matches_max_sharpe: **{diag.get('selected_matches_max_sharpe')}**"
        )
        lines.append(
            f"- frontier point count: {diag.get('frontier_point_count')}, "
            f"failed grid points: {diag.get('failed_grid_points')}"
        )
        lines.append("")
        lines.append(f"![{label} SAA MVO]({png_rel})")
        lines.append("")
    lines.append(
        "> **Constraints note**: Relaxed diagnostic — long-only + sum=1 만 적용. "
        "asset caps / bucket bands 미적용 (Phase D relaxed)."
    )
    lines.append("")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


__all__ = [
    "SCHEMA_VERSION",
    "DEFAULT_GRID_POINTS",
    "build_frontier_data",
    "write_frontier_json",
    "render_saa_mvo",
    "render_saa_frontier_summary_md",
]
