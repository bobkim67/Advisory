"""Phase E-8 — Regime Clock Visualization (history backfill + 2D clock).

E-8A: regime history sidecar (24m+ placement/velocity/regime trajectory)
E-8B: regime clock PNG (P/V quadrant + trajectory + current highlight)

read-only: RegimeAnalysisTool 을 read-only 로 재호출하여 full history 시계열을
산출한다. allocation/optimizer/TAA/selection 무관 — regime 산출은 portfolio build
시점의 동일 입력 (regime_src) 을 사용하므로 결과가 deterministic.

Hard requirements:
- 입력 portfolio JSON / source 파일 모두 mutate 없음.
- coverage 미달 시 절대 fake 금지 — `coverage_status=partial|insufficient` 명시.
- chart 에 mini timeline 사용 금지 (사용자 §E-8B-5 명시) — 본 모듈은 P/V 2D 만.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "e8.1"
TARGET_MONTHS = 24
INSUFFICIENT_THRESHOLD_MONTHS = 12

# Quadrant labels — 본 프로젝트의 ECI Regime 정의와 일치
# (regime/classifier.py: P>0, V>0 → R1, P>0, V≤0 → R4, P<0, V≤0 → R3, P<0, V>0 → R2)
REGIME_QUADRANT: dict[int, str] = {
    1: "Expansion / Acceleration",
    2: "Recovery / Improvement",
    3: "Slowdown / Contraction",
    4: "Late Cycle / Deceleration",
}

QUADRANT_COLORS: dict[int, str] = {
    1: "#3a8a3e",  # Expansion — green
    2: "#3a6db0",  # Recovery — blue
    3: "#a83232",  # Slowdown — red
    4: "#c97a2a",  # Late Cycle — orange
}


# ---------------------------------------------------------------------------
# History backfill (E-8A)
# ---------------------------------------------------------------------------


def _portfolio_regime_block(portfolio: dict[str, Any]) -> dict[str, Any]:
    return (portfolio.get("diagnostics") or {}).get("regime") or {}


def build_regime_history(
    portfolio_json: Path,
    *,
    source_root: Path,
    target_months: int = TARGET_MONTHS,
    region_override: str | None = None,
    window_override: int | None = None,
) -> dict[str, Any]:
    """portfolio JSON 의 region/as_of 를 읽고 RegimeAnalysisTool 을 read-only 로 재호출.

    raises FileNotFoundError if regime_src not present.
    raises ValueError if portfolio.diagnostics.regime missing.
    """
    portfolio_path = Path(portfolio_json)
    portfolio_raw = portfolio_path.read_text(encoding="utf-8")
    portfolio = json.loads(portfolio_raw)

    pr = _portfolio_regime_block(portfolio)
    if not pr:
        raise ValueError(
            f"portfolio JSON 에 diagnostics.regime 이 없음: {portfolio_path}"
        )

    region = str(region_override or pr.get("region") or "G7")
    window = int(window_override or 12)
    portfolio_signal_as_of = str(pr.get("as_of") or "")

    # RegimeAnalysisTool read-only 재호출
    from tdf_engine.regime.tool import RegimeAnalysisTool
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    repo = FileMarketDataRepository(Path(source_root))
    taa_config = {
        "regime_input": {
            "composite_region": region,
            "composite_window": window,
        }
    }
    tool = RegimeAnalysisTool(repo, taa_config=taa_config)
    result = tool.run()

    # placement / velocity / regime 모두 동일 인덱스
    p_series = result.placement.iloc[:, 0]
    v_series = result.velocity.iloc[:, 0]
    r_series = result.regime.iloc[:, 0]

    # NaN 제거 (regime classification 가능한 시점부터)
    valid_mask = ~(p_series.isna() | v_series.isna() | r_series.isna())
    obs_full: list[dict[str, Any]] = []
    for idx in p_series.index[valid_mask]:
        d = idx.date() if hasattr(idx, "date") else idx
        obs_full.append({
            "as_of": str(d),
            "placement": float(p_series.loc[idx]),
            "velocity": float(v_series.loc[idx]),
            "regime": int(r_series.loc[idx]),
            "regime_label": REGIME_QUADRANT.get(int(r_series.loc[idx]), "Unknown"),
            "quadrant_label": REGIME_QUADRANT.get(int(r_series.loc[idx]), "Unknown"),
        })

    # cutoff at portfolio_signal_as_of
    if portfolio_signal_as_of:
        cutoff = portfolio_signal_as_of
        obs_full = [o for o in obs_full if o["as_of"] <= cutoff]

    obs_full.sort(key=lambda o: o["as_of"])

    months_available = len(obs_full)
    if months_available >= target_months:
        coverage_status = "full"
    elif months_available >= INSUFFICIENT_THRESHOLD_MONTHS:
        coverage_status = "partial"
    else:
        coverage_status = "insufficient"

    # 24m 윈도우 (full 또는 partial)
    obs_window = obs_full[-target_months:]

    # current point 일치 검증 — portfolio diagnostics.regime 와 sidecar 마지막 obs
    current_match = True
    current_diff_note = None
    if obs_full:
        last = obs_full[-1]
        portfolio_p = float(pr.get("placement") or 0.0)
        portfolio_v = float(pr.get("velocity") or 0.0)
        portfolio_r = int(pr.get("regime") or 0)
        if (
            abs(last["placement"] - portfolio_p) > 1e-6
            or abs(last["velocity"] - portfolio_v) > 1e-6
            or last["regime"] != portfolio_r
        ):
            current_match = False
            current_diff_note = (
                f"sidecar last (P={last['placement']:+.6f}, V={last['velocity']:+.6f}, "
                f"R={last['regime']}) ≠ portfolio.diagnostics.regime "
                f"(P={portfolio_p:+.6f}, V={portfolio_v:+.6f}, R={portfolio_r})"
            )

    diagnostics: dict[str, Any] = {
        "warnings": [],
        "missing_data": [],
        "current_point_match": current_match,
    }
    if current_diff_note:
        diagnostics["warnings"].append(current_diff_note)
    if coverage_status == "insufficient":
        diagnostics["warnings"].append(
            f"history months_available={months_available} < "
            f"insufficient_threshold={INSUFFICIENT_THRESHOLD_MONTHS}; "
            "regime clock visualization 권장 미달"
        )

    payload: dict[str, Any] = {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "product_type": str(portfolio.get("portfolio_type") or ""),
            "portfolio_as_of_date": str(portfolio.get("as_of_date") or ""),
            "regime_signal_as_of": portfolio_signal_as_of,
            "source_mode": str(portfolio.get("source_type") or "file"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "signal": {
            "region": region,
            "placement_source": "regime_src::PlacementCalculator",
            "velocity_source": "regime_src::VelocityCalculator",
            "classifier": "ECIRegimeClassifier",
            "composite_window": window,
        },
        "observations_full": obs_full,
        "observations": obs_window,
        "coverage": {
            "count": len(obs_window),
            "start_date": (obs_window[0]["as_of"] if obs_window else None),
            "end_date": (obs_window[-1]["as_of"] if obs_window else None),
            "months_available": months_available,
            "target_months": target_months,
            "coverage_status": coverage_status,
            "full_history_months": months_available,
            "full_history_start_date": (obs_full[0]["as_of"] if obs_full else None),
            "full_history_end_date": (obs_full[-1]["as_of"] if obs_full else None),
        },
        "diagnostics": diagnostics,
    }

    # mutation guard
    assert portfolio_path.read_text(encoding="utf-8") == portfolio_raw

    return payload


def write_regime_history_json(payload: dict[str, Any], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return out_path


# ---------------------------------------------------------------------------
# Regime Clock visualization (E-8B)
# ---------------------------------------------------------------------------


def _select_korean_font() -> str | None:
    import matplotlib.font_manager as fm

    candidates = ("Malgun Gothic", "AppleGothic", "NanumGothic", "Gulim", "MS Gothic")
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            return name
    return None


def render_regime_clock(
    history: dict[str, Any],
    out_path: Path,
    *,
    label: str | None = None,
) -> Path:
    """24m+ trajectory regime clock PNG.

    raises ValueError if history.observations 가 비어 있거나 coverage_status=insufficient.
    """
    history = deepcopy(history)
    obs = list(history.get("observations") or [])
    coverage = history.get("coverage") or {}
    coverage_status = coverage.get("coverage_status")

    if not obs:
        raise ValueError("regime history observations 가 비어 있음")
    if coverage_status == "insufficient":
        raise ValueError(
            f"regime history coverage_status=insufficient — "
            f"months_available={coverage.get('months_available')} 이 시각화 권장값 미달. "
            "back-fill 보강 후 재시도 권장."
        )

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font_name = _select_korean_font()
    if font_name:
        plt.rcParams["font.family"] = [font_name, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    placements = [float(o["placement"]) for o in obs]
    velocities = [float(o["velocity"]) for o in obs]
    regimes = [int(o["regime"]) for o in obs]
    dates = [str(o["as_of"]) for o in obs]

    # axis range — symmetric around 0, 약간 여유
    p_max = max(abs(min(placements)), abs(max(placements))) * 1.25
    v_max = max(abs(min(velocities)), abs(max(velocities))) * 1.25
    p_max = max(p_max, 0.05)
    v_max = max(v_max, 0.05)

    fig, ax = plt.subplots(figsize=(10.5, 9.5))
    # 4 사분면 배경 (옅은 색상)
    ax.fill_betweenx([0, v_max], 0, p_max, color=QUADRANT_COLORS[1], alpha=0.07)
    ax.fill_betweenx([0, v_max], -p_max, 0, color=QUADRANT_COLORS[2], alpha=0.07)
    ax.fill_betweenx([-v_max, 0], -p_max, 0, color=QUADRANT_COLORS[3], alpha=0.07)
    ax.fill_betweenx([-v_max, 0], 0, p_max, color=QUADRANT_COLORS[4], alpha=0.07)
    # quadrant 라벨
    ax.text(
        p_max * 0.92, v_max * 0.92, REGIME_QUADRANT[1],
        ha="right", va="top", fontsize=10, color=QUADRANT_COLORS[1], fontweight="bold",
    )
    ax.text(
        -p_max * 0.92, v_max * 0.92, REGIME_QUADRANT[2],
        ha="left", va="top", fontsize=10, color=QUADRANT_COLORS[2], fontweight="bold",
    )
    ax.text(
        -p_max * 0.92, -v_max * 0.92, REGIME_QUADRANT[3],
        ha="left", va="bottom", fontsize=10, color=QUADRANT_COLORS[3], fontweight="bold",
    )
    ax.text(
        p_max * 0.92, -v_max * 0.92, REGIME_QUADRANT[4],
        ha="right", va="bottom", fontsize=10, color=QUADRANT_COLORS[4], fontweight="bold",
    )

    # axes
    ax.axhline(0, color="#333", linewidth=0.7)
    ax.axvline(0, color="#333", linewidth=0.7)
    ax.set_xlim(-p_max, p_max)
    ax.set_ylim(-v_max, v_max)
    ax.set_xlabel("Placement (composite leading indicator gap)", fontsize=11)
    ax.set_ylabel("Velocity (Δ Placement)", fontsize=11)
    ax.grid(linestyle=":", alpha=0.35)

    # trajectory line — alpha gradient (오래된 obs 흐리게, 최근 진하게)
    n = len(obs)
    for i in range(n - 1):
        a = 0.25 + 0.55 * (i / max(n - 1, 1))
        ax.plot(
            placements[i:i + 2], velocities[i:i + 2],
            color="#555", linewidth=1.2, alpha=a, zorder=2,
        )

    # monthly dots — regime 별 색상
    for i in range(n):
        r = regimes[i]
        ax.scatter(
            placements[i], velocities[i],
            s=42, color=QUADRANT_COLORS.get(r, "#888"),
            edgecolors="white", linewidths=0.8, zorder=3, alpha=0.85,
        )

    # current point highlight
    cp_x, cp_y = placements[-1], velocities[-1]
    ax.scatter(
        cp_x, cp_y, s=260, marker="*",
        color="#222", edgecolors="#fff", linewidths=1.5, zorder=5,
    )
    ax.annotate(
        f"NOW  {dates[-1]}\nR{regimes[-1]} {REGIME_QUADRANT.get(regimes[-1], '')}\n"
        f"P={cp_x:+.4f}  V={cp_y:+.4f}",
        xy=(cp_x, cp_y),
        xytext=(20, 20), textcoords="offset points",
        fontsize=10, fontweight="bold",
        bbox=dict(facecolor="white", edgecolor="#222", boxstyle="round,pad=0.4", alpha=0.9),
        arrowprops=dict(arrowstyle="-", color="#222", lw=0.8),
    )

    # key annotations — start + regime change points
    ax.annotate(
        f"start  {dates[0]}\nR{regimes[0]}",
        xy=(placements[0], velocities[0]),
        xytext=(-50, -30), textcoords="offset points",
        fontsize=9, color="#333",
        bbox=dict(facecolor="white", edgecolor="#aaa", boxstyle="round,pad=0.3", alpha=0.85),
        arrowprops=dict(arrowstyle="-", color="#aaa", lw=0.7),
    )
    for i in range(1, n):
        if regimes[i] != regimes[i - 1]:
            ax.annotate(
                f"{dates[i]}\nR{regimes[i - 1]}→R{regimes[i]}",
                xy=(placements[i], velocities[i]),
                xytext=(15, -25), textcoords="offset points",
                fontsize=8, color=QUADRANT_COLORS.get(regimes[i], "#555"),
                bbox=dict(
                    facecolor="white", edgecolor=QUADRANT_COLORS.get(regimes[i], "#555"),
                    boxstyle="round,pad=0.25", alpha=0.85,
                ),
                arrowprops=dict(
                    arrowstyle="-",
                    color=QUADRANT_COLORS.get(regimes[i], "#555"),
                    lw=0.7,
                ),
            )

    # title
    meta = history.get("meta") or {}
    sig = history.get("signal") or {}
    pt = (meta.get("product_type") or "").upper()
    region = sig.get("region") or "?"
    sig_as_of = meta.get("regime_signal_as_of") or "?"
    title = (
        f"Regime Clock — {pt}  ·  region={region}  ·  signal as_of={sig_as_of}  "
        f"·  current R{regimes[-1]} ({REGIME_QUADRANT.get(regimes[-1], '?')})"
    )
    ax.set_title(title, fontsize=12, fontweight="bold", loc="center")

    # footer — coverage + portfolio vs signal as_of distinction
    portfolio_as_of = meta.get("portfolio_as_of_date") or "?"
    coverage_text = (
        f"coverage: {coverage.get('count')} obs ({coverage.get('start_date')} → "
        f"{coverage.get('end_date')}, status={coverage.get('coverage_status')}, "
        f"full_history={coverage.get('full_history_months')} obs)"
    )
    asof_text = (
        f"portfolio as_of_date={portfolio_as_of}  ·  "
        f"regime signal as_of={sig_as_of}"
    )
    if portfolio_as_of != sig_as_of:
        asof_text += "  ·  (signal lags portfolio rebalancing date — monthly regime data)"
    fig.text(0.5, 0.025, coverage_text, ha="center", fontsize=8.5, color="#555")
    fig.text(0.5, 0.005, asof_text, ha="center", fontsize=8.5, color="#555")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# Summary md
# ---------------------------------------------------------------------------


def render_regime_clock_summary_md(
    *,
    as_of_run: str,
    etf_history: dict[str, Any],
    fund_history: dict[str, Any],
    etf_png_rel: str,
    fund_png_rel: str,
    out_path: Path,
) -> Path:
    lines: list[str] = []
    lines.append(f"# Regime Clock Visualization Summary ({as_of_run})")
    lines.append("")
    lines.append(f"> schema_version: {SCHEMA_VERSION}")
    lines.append("> Read-only diagnostic — RegimeAnalysisTool re-invoked on the same regime_src.")
    lines.append("")
    for label, hist, png_rel in (("ETF", etf_history, etf_png_rel), ("Fund", fund_history, fund_png_rel)):
        meta = hist.get("meta") or {}
        sig = hist.get("signal") or {}
        cov = hist.get("coverage") or {}
        diag = hist.get("diagnostics") or {}
        obs = hist.get("observations") or []
        lines.append(f"## {label}")
        lines.append("")
        lines.append(f"- region: **{sig.get('region')}**, signal as_of: **{meta.get('regime_signal_as_of')}**")
        lines.append(
            f"- coverage: **{cov.get('coverage_status')}** "
            f"({cov.get('count')} obs in window, {cov.get('months_available')} obs full history, "
            f"target={cov.get('target_months')}m)"
        )
        lines.append(
            f"- window: {cov.get('start_date')} → {cov.get('end_date')}"
        )
        if obs:
            cur = obs[-1]
            lines.append(
                f"- current: R{cur['regime']} ({cur['regime_label']}), "
                f"P={cur['placement']:+.4f} / V={cur['velocity']:+.4f}"
            )
        lines.append(f"- current_point_match (sidecar last vs portfolio): "
                     f"{diag.get('current_point_match')}")
        if diag.get("warnings"):
            lines.append("- warnings:")
            for w in diag["warnings"]:
                lines.append(f"  - {w}")
        lines.append("")
        lines.append(f"![{label} Regime Clock]({png_rel})")
        lines.append("")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


__all__ = [
    "SCHEMA_VERSION",
    "TARGET_MONTHS",
    "INSUFFICIENT_THRESHOLD_MONTHS",
    "REGIME_QUADRANT",
    "build_regime_history",
    "write_regime_history_json",
    "render_regime_clock",
    "render_regime_clock_summary_md",
]
