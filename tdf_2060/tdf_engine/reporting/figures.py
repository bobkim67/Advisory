"""Phase E-6 — Relaxed diagnostic 산출물 정적 시각화 (matplotlib only).

입력은 build_portfolio.py 가 생성한 portfolio_*.json 만 사용한다. optimizer /
projection / selection / DB 를 다시 호출하지 않으므로 allocation 결과는 절대
변동하지 않는다.

차트 5종 (MVP):
  01_asset_allocation              : 9 자산 final weight bar
  01_asset_allocation_etf_vs_fund  : ETF/Fund 자산배분 grouped bar
  02_drift_summary                 : projection drift + quality/selection drift
  03_top_products                  : product_allocation top 10
  04_manager_concentration         : manager 별 합산 weight top 10

차트 규칙:
  - matplotlib only (seaborn 미사용)
  - 색상은 의미 체계 4종 (equity / fixed_income / risk_asset / cash)
  - 모든 chart title 에 RELAXED_TAG 강제
  - product / manager cap·threshold 선 그리지 않음 (caption 만)
  - 기존 review_*.md / comparison_*.md 변경 없음
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # noqa: E402  GUI backend 강제 차단

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as _font_manager  # noqa: E402


def _select_korean_font() -> str | None:
    candidates = ("Malgun Gothic", "AppleGothic", "NanumGothic", "Gulim", "MS Gothic")
    available = {f.name for f in _font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            return name
    return None


_KOREAN_FONT = _select_korean_font()
if _KOREAN_FONT:
    plt.rcParams["font.family"] = [_KOREAN_FONT, "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


RELAXED_TAG = "Relaxed Diagnostic — Not Production"

# 의미 체계 색상 (보정 §1)
BUCKET_COLORS: dict[str, str] = {
    "equity": "#3a6db0",
    "fixed_income": "#7fa8c2",
    "risk_asset": "#c97a2a",
    "cash": "#9aa3ad",
    "_other": "#cfcfcf",
}

# drift source 색상 (5-source taxonomy + unknown)
DRIFT_SOURCE_COLORS: dict[str, str] = {
    "product_cap_clipping_outflow": "#c0504d",
    "fallback_redistribution_inflow": "#4f81bd",
    "long_only_clipping": "#9bbb59",
    "redistribution_from_long_only_clipping": "#8064a2",
    "none": "#bfbfbf",
    "unknown": "#404040",
}

# HY 등 risk_asset 플래그가 있는 자산은 fixed_income bucket 이라도 risk_asset 색상
RISK_ASSET_KEYS: frozenset[str] = frozenset({"us_high_yield"})

DEFAULT_FIG_SIZE: tuple[float, float] = (12.8, 7.2)
DEFAULT_DPI: int = 150


# ---------------------------------------------------------------------------
# Loaders / extractors (read-only)
# ---------------------------------------------------------------------------


def load_portfolio_json(path: Path) -> dict[str, Any]:
    """portfolio_*.json 을 dict 로 로드. 입력 파일은 변경하지 않는다."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _asset_color(asset_key: str, bucket: str) -> str:
    if asset_key in RISK_ASSET_KEYS:
        return BUCKET_COLORS["risk_asset"]
    return BUCKET_COLORS.get(bucket, BUCKET_COLORS["_other"])


def _portfolio_label(portfolio: dict[str, Any]) -> str:
    return str(portfolio.get("portfolio_type", "")).upper()


def _as_of_label(portfolio: dict[str, Any]) -> str:
    return str(portfolio.get("as_of_date") or portfolio.get("as_of") or "")


def _short(name: str, max_len: int = 30) -> str:
    if name is None:
        return ""
    s = str(name)
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _sorted_asset_rows(portfolio: dict[str, Any]) -> list[dict[str, Any]]:
    """자산 정렬: bucket 그룹 (equity → fixed_income → 기타) + weight 내림차순."""
    rows = list(portfolio.get("asset_allocation") or [])
    bucket_order = {"equity": 0, "fixed_income": 1}

    def key(row: dict[str, Any]) -> tuple[int, float]:
        b = row.get("bucket", "")
        return (
            bucket_order.get(b, 9),
            -float(row.get("final_asset_weight") or 0.0),
        )

    return sorted(rows, key=key)


def _bucket_weights(portfolio: dict[str, Any]) -> dict[str, float]:
    rs = portfolio.get("review_summary", {}) or {}
    return {
        "equity": float(rs.get("equity_bucket_weight") or 0.0),
        "fixed_income": float(rs.get("fixed_income_bucket_weight") or 0.0),
    }


def _relaxed_caption(portfolio: dict[str, Any], extra: str = "") -> str:
    rs = portfolio.get("review_summary") or {}
    eq = float(rs.get("equity_bucket_weight") or 0.0) * 100
    fi = float(rs.get("fixed_income_bucket_weight") or 0.0) * 100
    base = (
        f"Equity {eq:.2f}% / Fixed Income {fi:.2f}% — monitoring result. "
        f"as_of_date={_as_of_label(portfolio)}, "
        f"operating_mode=relaxed_diagnostic."
    )
    if extra:
        base = f"{base} {extra}"
    return base


def _apply_title_and_caption(
    fig: plt.Figure,
    title: str,
    caption: str,
) -> None:
    fig.suptitle(f"{title} — {RELAXED_TAG}", fontsize=13, fontweight="bold")
    if caption:
        fig.text(
            0.5,
            0.01,
            caption,
            ha="center",
            va="bottom",
            fontsize=9,
            color="#444444",
        )


def _save(fig: plt.Figure, out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(out_path, dpi=DEFAULT_DPI)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# Chart 01 — Asset allocation (single)
# ---------------------------------------------------------------------------


def plot_asset_allocation(
    portfolio: dict[str, Any],
    out_path: Path,
    *,
    label: str | None = None,
) -> Path:
    rows = _sorted_asset_rows(portfolio)
    if not rows:
        raise ValueError("portfolio['asset_allocation'] is empty")

    keys = [r["asset_key"] for r in rows]
    weights = [float(r.get("final_asset_weight") or 0.0) * 100 for r in rows]
    colors = [_asset_color(r["asset_key"], r.get("bucket", "")) for r in rows]

    label = label or _portfolio_label(portfolio)
    fig, ax = plt.subplots(figsize=DEFAULT_FIG_SIZE)
    bars = ax.barh(keys, weights, color=colors)
    ax.invert_yaxis()
    ax.set_xlabel("Final asset weight (%)")
    ax.set_xlim(0, max(100, max(weights) * 1.1 if weights else 100))
    ax.grid(axis="x", linestyle=":", alpha=0.4)

    for bar, w in zip(bars, weights):
        ax.text(
            bar.get_width() + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{w:.2f}%",
            va="center",
            fontsize=9,
        )

    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, color=BUCKET_COLORS["equity"], label="equity"),
        plt.Rectangle(
            (0, 0), 1, 1, color=BUCKET_COLORS["fixed_income"], label="fixed_income"
        ),
        plt.Rectangle(
            (0, 0), 1, 1, color=BUCKET_COLORS["risk_asset"], label="risk_asset (HY)"
        ),
    ]
    ax.legend(handles=legend_handles, loc="lower right", fontsize=9)

    _apply_title_and_caption(
        fig,
        title=f"{label} Asset Allocation",
        caption=_relaxed_caption(portfolio),
    )
    return _save(fig, out_path)


# ---------------------------------------------------------------------------
# Chart 01 — ETF vs Fund comparison
# ---------------------------------------------------------------------------


def plot_asset_allocation_comparison(
    etf: dict[str, Any],
    fund: dict[str, Any],
    out_path: Path,
) -> Path:
    etf_rows = _sorted_asset_rows(etf)
    fund_map = {
        r["asset_key"]: r for r in (fund.get("asset_allocation") or [])
    }
    keys = [r["asset_key"] for r in etf_rows]
    etf_w = [float(r.get("final_asset_weight") or 0.0) * 100 for r in etf_rows]
    fund_w = [
        float((fund_map.get(k) or {}).get("final_asset_weight") or 0.0) * 100
        for k in keys
    ]

    import numpy as np

    y = np.arange(len(keys))
    height = 0.4

    fig, ax = plt.subplots(figsize=DEFAULT_FIG_SIZE)
    ax.barh(
        y - height / 2,
        etf_w,
        height=height,
        color="#3a6db0",
        label="ETF",
    )
    ax.barh(
        y + height / 2,
        fund_w,
        height=height,
        color="#c97a2a",
        label="Fund",
    )
    ax.set_yticks(y)
    ax.set_yticklabels(keys)
    ax.invert_yaxis()
    ax.set_xlabel("Final asset weight (%)")
    ax.set_xlim(0, max(100, max(etf_w + fund_w) * 1.1 if (etf_w or fund_w) else 100))
    ax.grid(axis="x", linestyle=":", alpha=0.4)
    ax.legend(loc="lower right", fontsize=9)

    etf_eq = float((etf.get("review_summary") or {}).get("equity_bucket_weight") or 0.0) * 100
    fund_eq = float((fund.get("review_summary") or {}).get("equity_bucket_weight") or 0.0) * 100
    caption = (
        f"ETF equity={etf_eq:.2f}% / Fund equity={fund_eq:.2f}%. "
        f"as_of_date={_as_of_label(etf)}, operating_mode=relaxed_diagnostic. "
        "Compare diagnostic baseline only."
    )
    _apply_title_and_caption(
        fig,
        title="ETF vs Fund Asset Allocation",
        caption=caption,
    )
    return _save(fig, out_path)


# ---------------------------------------------------------------------------
# Chart 02 — Drift summary
# ---------------------------------------------------------------------------


def _drift_source_color(src: str | None) -> str:
    if not src:
        return DRIFT_SOURCE_COLORS["unknown"]
    return DRIFT_SOURCE_COLORS.get(src, DRIFT_SOURCE_COLORS["unknown"])


def plot_drift_summary(
    portfolio: dict[str, Any],
    out_path: Path,
    *,
    label: str | None = None,
) -> Path:
    label = label or _portfolio_label(portfolio)
    proj = portfolio.get("projection_summary") or {}
    quality = (portfolio.get("diagnostics") or {}).get("quality") or {}
    drift_by_asset: dict[str, float] = quality.get("asset_weight_drift") or {}
    drift_source: dict[str, str] = quality.get("drift_source_by_asset") or {}
    clip_summary = quality.get("drift_clipping_summary") or {}
    enforcement = quality.get("enforcement_mode") or "telemetry_only"

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(DEFAULT_FIG_SIZE[0], DEFAULT_FIG_SIZE[1] * 1.15)
    )

    # Top: projection drift (top 5 by abs drift)
    proj_records = list(proj.get("largest_projection_drifts_top5") or [])
    if proj_records:
        keys = [r["asset_key"] for r in proj_records]
        vals = [float(r.get("drift") or 0.0) * 100 for r in proj_records]
        colors_top = [
            "#9bbb59" if v >= 0 else "#8064a2" for v in vals
        ]  # long_only_clipping (+) / redistribution (-)
        ax_top.barh(keys, vals, color=colors_top)
        ax_top.invert_yaxis()
        ax_top.axvline(0, color="#888", linewidth=0.7)
        ax_top.set_xlabel("Projection drift (%p, signed)")
        ax_top.grid(axis="x", linestyle=":", alpha=0.4)
        for i, v in enumerate(vals):
            ax_top.text(
                v + (0.1 if v >= 0 else -0.1),
                i,
                f"{v:+.2f}",
                va="center",
                ha="left" if v >= 0 else "right",
                fontsize=8,
            )
    else:
        ax_top.text(0.5, 0.5, "no projection drift", ha="center", va="center")
        ax_top.set_axis_off()
    ax_top.set_title(
        f"Projection drift (top 5) · max_abs={float(proj.get('max_abs_projection_drift') or 0.0) * 100:.2f}%",
        fontsize=11,
    )

    # Bottom: quality / selection drift (signed)
    items = [(k, v) for k, v in drift_by_asset.items() if abs(float(v)) > 1e-9]
    items.sort(key=lambda kv: float(kv[1]))  # outflow (negative) → inflow (positive)
    if items:
        keys2 = [k for k, _ in items]
        vals2 = [float(v) * 100 for _, v in items]
        colors2 = [_drift_source_color(drift_source.get(k)) for k, _ in items]
        ax_bot.barh(keys2, vals2, color=colors2)
        ax_bot.invert_yaxis()
        ax_bot.axvline(0, color="#888", linewidth=0.7)
        ax_bot.set_xlabel("Quality / selection drift (%p, signed)")
        ax_bot.grid(axis="x", linestyle=":", alpha=0.4)
        for i, v in enumerate(vals2):
            ax_bot.text(
                v + (0.1 if v >= 0 else -0.1),
                i,
                f"{v:+.2f}",
                va="center",
                ha="left" if v >= 0 else "right",
                fontsize=8,
            )
    else:
        ax_bot.text(0.5, 0.5, "no quality drift", ha="center", va="center")
        ax_bot.set_axis_off()
    primary = clip_summary.get("drift_source_primary") or "n/a"
    ax_bot.set_title(
        f"Quality / selection drift · primary={primary} · enforcement={enforcement}",
        fontsize=11,
    )

    # drift source legend (bottom panel)
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, color=color, label=src)
        for src, color in DRIFT_SOURCE_COLORS.items()
        if src != "unknown"
    ]
    ax_bot.legend(handles=legend_handles, loc="lower right", fontsize=8)

    caption = (
        "Top panel = D-02 projection drift (long_only_clipping / "
        "redistribution_from_long_only_clipping). "
        "Bottom panel = quality drift (product_cap_clipping_outflow / "
        "fallback_redistribution_inflow). "
        "These two are distinct telemetry layers."
    )
    _apply_title_and_caption(fig, title=f"{label} Drift Summary", caption=caption)
    return _save(fig, out_path)


# ---------------------------------------------------------------------------
# Chart 03 — Top product concentration
# ---------------------------------------------------------------------------


def plot_top_products(
    portfolio: dict[str, Any],
    out_path: Path,
    *,
    label: str | None = None,
    top_n: int = 10,
) -> Path:
    products = list(portfolio.get("product_allocation") or [])
    if not products:
        raise ValueError("portfolio['product_allocation'] is empty")
    products.sort(key=lambda r: float(r.get("final_weight") or 0.0), reverse=True)
    top = products[:top_n]

    label = label or _portfolio_label(portfolio)
    names = [
        f"{_short(r.get('product_name') or r.get('product_id') or '')} ({r.get('manager') or '?'})"
        for r in top
    ]
    weights = [float(r.get("final_weight") or 0.0) * 100 for r in top]
    colors = [_asset_color(r.get("asset_key", ""), r.get("bucket", "")) for r in top]

    fig, ax = plt.subplots(figsize=DEFAULT_FIG_SIZE)
    bars = ax.barh(names, weights, color=colors)
    ax.invert_yaxis()
    ax.set_xlabel("Product weight (%)")
    ax.set_xlim(0, max(weights) * 1.15 if weights else 1)
    ax.grid(axis="x", linestyle=":", alpha=0.4)

    for bar, w in zip(bars, weights):
        ax.text(
            bar.get_width() + 0.2,
            bar.get_y() + bar.get_height() / 2,
            f"{w:.2f}%",
            va="center",
            fontsize=9,
        )

    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, color=BUCKET_COLORS["equity"], label="equity"),
        plt.Rectangle(
            (0, 0), 1, 1, color=BUCKET_COLORS["fixed_income"], label="fixed_income"
        ),
        plt.Rectangle(
            (0, 0), 1, 1, color=BUCKET_COLORS["risk_asset"], label="risk_asset (HY)"
        ),
    ]
    ax.legend(handles=legend_handles, loc="lower right", fontsize=9)

    caption = (
        f"Top {len(top)} products by final_weight. "
        "Existing product allocation cap inside selection may affect fallback distribution; "
        "no new cap line is drawn here."
    )
    _apply_title_and_caption(
        fig,
        title=f"{label} Top {len(top)} Products",
        caption=caption,
    )
    return _save(fig, out_path)


# ---------------------------------------------------------------------------
# Chart 04 — Manager concentration
# ---------------------------------------------------------------------------


def plot_manager_concentration(
    portfolio: dict[str, Any],
    out_path: Path,
    *,
    label: str | None = None,
    top_n: int = 10,
) -> Path:
    products = list(portfolio.get("product_allocation") or [])
    if not products:
        raise ValueError("portfolio['product_allocation'] is empty")

    by_manager: dict[str, dict[str, float]] = {}
    for r in products:
        m = r.get("manager") or "unknown"
        agg = by_manager.setdefault(m, {"weight": 0.0, "n": 0.0})
        agg["weight"] += float(r.get("final_weight") or 0.0)
        agg["n"] += 1

    items = sorted(
        by_manager.items(), key=lambda kv: kv[1]["weight"], reverse=True
    )[:top_n]
    names = [f"{m} (n={int(v['n'])})" for m, v in items]
    weights = [v["weight"] * 100 for _, v in items]

    label = label or _portfolio_label(portfolio)
    fig, ax = plt.subplots(figsize=DEFAULT_FIG_SIZE)
    bars = ax.barh(names, weights, color="#5a6c7d")
    ax.invert_yaxis()
    ax.set_xlabel("Manager weight sum (%)")
    ax.set_xlim(0, max(weights) * 1.15 if weights else 1)
    ax.grid(axis="x", linestyle=":", alpha=0.4)

    for bar, w in zip(bars, weights):
        ax.text(
            bar.get_width() + 0.2,
            bar.get_y() + bar.get_height() / 2,
            f"{w:.2f}%",
            va="center",
            fontsize=9,
        )

    caption = (
        "Monitoring only — no manager threshold applied. "
        "Manager concentration cap is not enforced (D-14 deferred). "
        "Bar shows aggregated final_weight per manager."
    )
    _apply_title_and_caption(
        fig,
        title=f"{label} Manager Concentration (Top {len(items)})",
        caption=caption,
    )
    return _save(fig, out_path)


# ---------------------------------------------------------------------------
# Summary markdown
# ---------------------------------------------------------------------------


SUMMARY_BANNER = (
    "본 시각화는 relaxed_diagnostic 산출물 해석용이며 production portfolio가 "
    "아닙니다. Allocation, TAA, selection 결과를 재계산하지 않고 기존 portfolio "
    "JSON을 시각화합니다."
)


def render_summary_markdown(
    *,
    as_of_date: str,
    etf: dict[str, Any],
    fund: dict[str, Any],
    figures_root: Path,
    summary_path: Path,
) -> Path:
    summary_path = Path(summary_path)
    figures_root = Path(figures_root)
    rel_root = _relpath(figures_root, summary_path.parent)

    etf_rs = etf.get("review_summary") or {}
    fund_rs = fund.get("review_summary") or {}
    etf_regime = (etf.get("diagnostics") or {}).get("regime") or {}

    def _fmt_pct(v: Any) -> str:
        try:
            return f"{float(v) * 100:.2f}%"
        except (TypeError, ValueError):
            return "n/a"

    lines: list[str] = []
    lines.append(f"# Relaxed Diagnostic Run — Visualization Summary ({as_of_date})")
    lines.append("")
    lines.append(f"> {RELAXED_TAG}")
    lines.append(">")
    lines.append(f"> {SUMMARY_BANNER}")
    lines.append("")
    lines.append("## Run snapshot")
    lines.append("")
    lines.append("| 항목 | ETF | Fund |")
    lines.append("|---|---|---|")
    lines.append(
        f"| equity bucket | {_fmt_pct(etf_rs.get('equity_bucket_weight'))} | "
        f"{_fmt_pct(fund_rs.get('equity_bucket_weight'))} |"
    )
    lines.append(
        f"| fixed_income bucket | {_fmt_pct(etf_rs.get('fixed_income_bucket_weight'))} | "
        f"{_fmt_pct(fund_rs.get('fixed_income_bucket_weight'))} |"
    )
    lines.append(
        f"| asset_weight_sum | {etf_rs.get('asset_weight_sum'):.4f} | "
        f"{fund_rs.get('asset_weight_sum'):.4f} |"
    )
    lines.append(
        f"| product_weight_sum | {etf_rs.get('product_weight_sum'):.4f} | "
        f"{fund_rs.get('product_weight_sum'):.4f} |"
    )
    lines.append(
        f"| max_abs_projection_drift | {_fmt_pct(etf_rs.get('max_abs_projection_drift'))} | "
        f"{_fmt_pct(fund_rs.get('max_abs_projection_drift'))} |"
    )
    lines.append(
        f"| max_abs_asset_weight_drift | {_fmt_pct(etf_rs.get('max_abs_asset_weight_drift'))} | "
        f"{_fmt_pct(fund_rs.get('max_abs_asset_weight_drift'))} |"
    )
    lines.append(
        f"| quality_status | {etf_rs.get('quality_status')} | "
        f"{fund_rs.get('quality_status')} |"
    )
    lines.append(
        f"| fallback_used | {etf_rs.get('fallback_used')} | "
        f"{fund_rs.get('fallback_used')} |"
    )
    lines.append(
        f"| regime | {etf_regime.get('regime_label', 'n/a')} "
        f"(region={etf_regime.get('region', 'n/a')}) | (same) |"
    )
    lines.append("")
    lines.append("## ETF figures")
    lines.append("")
    for fname, alt in [
        ("etf/01_asset_allocation.png", "ETF Asset Allocation"),
        ("etf/02_drift_summary.png", "ETF Drift Summary"),
        ("etf/03_top_products.png", "ETF Top Products"),
        ("etf/04_manager_concentration.png", "ETF Manager Concentration"),
    ]:
        lines.append(f"![{alt}]({rel_root}/{fname})")
        lines.append("")

    lines.append("## Fund figures")
    lines.append("")
    for fname, alt in [
        ("fund/01_asset_allocation.png", "Fund Asset Allocation"),
        ("fund/02_drift_summary.png", "Fund Drift Summary"),
        ("fund/03_top_products.png", "Fund Top Products"),
        ("fund/04_manager_concentration.png", "Fund Manager Concentration"),
    ]:
        lines.append(f"![{alt}]({rel_root}/{fname})")
        lines.append("")

    lines.append("## Comparison figures")
    lines.append("")
    lines.append(
        f"![ETF vs Fund Asset Allocation]({rel_root}/comparison/01_asset_allocation_etf_vs_fund.png)"
    )
    lines.append("")

    lines.append("## Source")
    lines.append("")
    lines.append(
        "- portfolio_etf_*.json, portfolio_fund_*.json (asset_allocation / "
        "product_allocation / diagnostics.quality / projection_summary / "
        "diagnostics.regime)"
    )
    lines.append("- 본 summary 는 review_*.md / comparison_*.md 를 변경하지 않습니다.")
    lines.append("")

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def _relpath(target: Path, start: Path) -> str:
    """summary md 기준 figures 디렉터리 상대경로 (POSIX 슬래시)."""
    try:
        rel = Path(target).resolve().relative_to(Path(start).resolve())
    except ValueError:
        # not on same root → fall back to as_posix
        return Path(target).as_posix()
    return rel.as_posix()


# ---------------------------------------------------------------------------
# MVP orchestrator
# ---------------------------------------------------------------------------


def _render_appendix_pngs(
    etf_view: dict[str, Any],
    fund_view: dict[str, Any],
    output_dir: Path,
) -> list[Path]:
    """기존 9 PNG (MVP set) 생성. 본 함수는 옵션 (appendix) 으로만 호출됨."""
    etf_dir = output_dir / "etf"
    fund_dir = output_dir / "fund"
    cmp_dir = output_dir / "comparison"
    for d in (etf_dir, fund_dir, cmp_dir):
        d.mkdir(parents=True, exist_ok=True)

    pngs: list[Path] = []
    pngs.append(
        plot_asset_allocation(etf_view, etf_dir / "01_asset_allocation.png", label="ETF")
    )
    pngs.append(
        plot_asset_allocation(
            fund_view, fund_dir / "01_asset_allocation.png", label="Fund"
        )
    )
    pngs.append(
        plot_asset_allocation_comparison(
            etf_view, fund_view, cmp_dir / "01_asset_allocation_etf_vs_fund.png"
        )
    )
    pngs.append(
        plot_drift_summary(etf_view, etf_dir / "02_drift_summary.png", label="ETF")
    )
    pngs.append(
        plot_drift_summary(fund_view, fund_dir / "02_drift_summary.png", label="Fund")
    )
    pngs.append(
        plot_top_products(etf_view, etf_dir / "03_top_products.png", label="ETF")
    )
    pngs.append(
        plot_top_products(fund_view, fund_dir / "03_top_products.png", label="Fund")
    )
    pngs.append(
        plot_manager_concentration(
            etf_view, etf_dir / "04_manager_concentration.png", label="ETF"
        )
    )
    pngs.append(
        plot_manager_concentration(
            fund_view, fund_dir / "04_manager_concentration.png", label="Fund"
        )
    )
    return pngs


def render_mvp(
    *,
    as_of_date: str,
    etf_json: Path,
    fund_json: Path,
    output_dir: Path,
    summary_md: Path,
) -> dict[str, Any]:
    """기존 9 PNG 세트 + 기존 summary md.

    Phase E-6.1 재분류 이후에도 backward-compat 용으로 유지 (test_phase_e_figures
    외부 호출 보존). 본 함수는 main MVP-X 와 별개로 9 PNG appendix-set 을 한 번에
    만들고 싶을 때 사용한다.
    """
    etf = load_portfolio_json(Path(etf_json))
    fund = load_portfolio_json(Path(fund_json))
    etf_view = deepcopy(etf)
    fund_view = deepcopy(fund)

    output_dir = Path(output_dir)
    pngs = _render_appendix_pngs(etf_view, fund_view, output_dir)
    summary = render_summary_markdown(
        as_of_date=as_of_date,
        etf=etf,
        fund=fund,
        figures_root=output_dir,
        summary_path=Path(summary_md),
    )

    return {
        "as_of_date": as_of_date,
        "png_paths": [str(p) for p in pngs],
        "summary_md": str(summary),
    }


# ---------------------------------------------------------------------------
# MVP-X (main) orchestrator — Phase E-6.2
# ---------------------------------------------------------------------------


def _render_mvpx_summary_markdown(
    *,
    as_of_date: str,
    etf: dict[str, Any],
    fund: dict[str, Any],
    figures_root: Path,
    summary_path: Path,
    mvpx_etf_rel: str,
    mvpx_fund_rel: str,
    appendix_included: bool,
) -> Path:
    """MVP-X main 섹션 + (옵션) Appendix 섹션 markdown 생성."""
    summary_path = Path(summary_path)
    figures_root = Path(figures_root)
    rel_root = _relpath(figures_root, summary_path.parent)

    etf_rs = etf.get("review_summary") or {}
    fund_rs = fund.get("review_summary") or {}
    etf_regime = (etf.get("diagnostics") or {}).get("regime") or {}

    def _fmt_pct(v: Any) -> str:
        try:
            return f"{float(v) * 100:.2f}%"
        except (TypeError, ValueError):
            return "n/a"

    lines: list[str] = []
    lines.append(
        f"# Portfolio Construction Bridge — Visualization Summary ({as_of_date})"
    )
    lines.append("")
    lines.append(f"> {RELAXED_TAG}")
    lines.append(">")
    lines.append(f"> {SUMMARY_BANNER}")
    lines.append("")
    lines.append("## Run snapshot")
    lines.append("")
    lines.append("| 항목 | ETF | Fund |")
    lines.append("|---|---|---|")
    lines.append(
        f"| equity bucket | {_fmt_pct(etf_rs.get('equity_bucket_weight'))} | "
        f"{_fmt_pct(fund_rs.get('equity_bucket_weight'))} |"
    )
    lines.append(
        f"| fixed_income bucket | {_fmt_pct(etf_rs.get('fixed_income_bucket_weight'))} | "
        f"{_fmt_pct(fund_rs.get('fixed_income_bucket_weight'))} |"
    )
    lines.append(
        f"| asset_weight_sum | {etf_rs.get('asset_weight_sum'):.4f} | "
        f"{fund_rs.get('asset_weight_sum'):.4f} |"
    )
    lines.append(
        f"| product_weight_sum | {etf_rs.get('product_weight_sum'):.4f} | "
        f"{fund_rs.get('product_weight_sum'):.4f} |"
    )
    lines.append(
        f"| max_abs_projection_drift | {_fmt_pct(etf_rs.get('max_abs_projection_drift'))} | "
        f"{_fmt_pct(fund_rs.get('max_abs_projection_drift'))} |"
    )
    lines.append(
        f"| max_abs_asset_weight_drift | {_fmt_pct(etf_rs.get('max_abs_asset_weight_drift'))} | "
        f"{_fmt_pct(fund_rs.get('max_abs_asset_weight_drift'))} |"
    )
    lines.append(
        f"| quality_status | {etf_rs.get('quality_status')} | "
        f"{fund_rs.get('quality_status')} |"
    )
    lines.append(
        f"| fallback_used | {etf_rs.get('fallback_used')} | "
        f"{fund_rs.get('fallback_used')} |"
    )
    lines.append(
        f"| regime | {etf_regime.get('regime_label', 'n/a')} "
        f"(region={etf_regime.get('region', 'n/a')}) | (same) |"
    )
    lines.append("")
    lines.append("## Main: Portfolio Construction Bridge (1-page integrated)")
    lines.append("")
    lines.append(
        "각 PNG 한 페이지 안에서 다음 흐름이 보입니다 — "
        "Regime → SAA(direct telemetry) → TAA tilt → Projection → Final asset → Products."
    )
    lines.append("")
    lines.append(f"### ETF — `{mvpx_etf_rel}`")
    lines.append("")
    lines.append(f"![ETF MVP-X bridge]({rel_root}/{mvpx_etf_rel})")
    lines.append("")
    lines.append(f"### Fund — `{mvpx_fund_rel}`")
    lines.append("")
    lines.append(f"![Fund MVP-X bridge]({rel_root}/{mvpx_fund_rel})")
    lines.append("")

    if appendix_included:
        lines.append("## Appendix — legacy 9 PNG set (downstream-only)")
        lines.append("")
        lines.append(
            "본 섹션은 `--with-appendix` 옵션으로만 첨부됩니다. 운용역 review 의 main "
            "산출은 위의 1-page bridge 입니다."
        )
        lines.append("")
        lines.append("### Appendix-E.1 Asset allocation")
        lines.append("")
        for fname, alt in [
            ("etf/01_asset_allocation.png", "ETF Asset Allocation"),
            ("fund/01_asset_allocation.png", "Fund Asset Allocation"),
            (
                "comparison/01_asset_allocation_etf_vs_fund.png",
                "ETF vs Fund Asset Allocation",
            ),
        ]:
            lines.append(f"![{alt}]({rel_root}/{fname})")
            lines.append("")
        lines.append("### Appendix-E.4 Drift summary (downstream layer)")
        lines.append("")
        for fname, alt in [
            ("etf/02_drift_summary.png", "ETF Drift Summary"),
            ("fund/02_drift_summary.png", "Fund Drift Summary"),
        ]:
            lines.append(f"![{alt}]({rel_root}/{fname})")
            lines.append("")
        lines.append("### Appendix-E.5 Product / Manager concentration")
        lines.append("")
        for fname, alt in [
            ("etf/03_top_products.png", "ETF Top Products"),
            ("fund/03_top_products.png", "Fund Top Products"),
            ("etf/04_manager_concentration.png", "ETF Manager Concentration"),
            ("fund/04_manager_concentration.png", "Fund Manager Concentration"),
        ]:
            lines.append(f"![{alt}]({rel_root}/{fname})")
            lines.append("")

    lines.append("## Source")
    lines.append("")
    lines.append(
        "- portfolio_etf_*.json, portfolio_fund_*.json (asset_allocation / "
        "product_allocation / diagnostics.{regime,saa_diagnostics,taa_diagnostics,quality})"
    )
    lines.append(
        "- MVP-X 는 `diagnostics.saa_diagnostics.saa_weights` (E-6.2 T-6) 를 직접 사용합니다 "
        "— inferred SAA (taa_target − asset_tilts) 경로는 사용하지 않습니다."
    )
    lines.append(
        "- 본 summary 는 review_*.md / comparison_*.md / 기존 portfolio_*.json 을 "
        "변경하지 않습니다."
    )
    lines.append("")

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def render_mvpx(
    *,
    as_of_date: str,
    etf_json: Path,
    fund_json: Path,
    output_dir: Path,
    summary_md: Path,
    with_appendix: bool = False,
) -> dict[str, Any]:
    """MVP-X (main) 1-page bridge × 2 (ETF + Fund) + summary md.

    `with_appendix=True` 이면 기존 9 PNG 세트도 같은 output_dir 아래 생성하고
    summary md 의 ## Appendix 섹션에 임베드한다.
    """
    from tdf_engine.reporting.figures_mvpx import render_mvpx_bridge

    etf = load_portfolio_json(Path(etf_json))
    fund = load_portfolio_json(Path(fund_json))
    etf_view = deepcopy(etf)
    fund_view = deepcopy(fund)

    output_dir = Path(output_dir)
    main_dir = output_dir / "main"
    main_dir.mkdir(parents=True, exist_ok=True)

    etf_png = main_dir / "00_mvpx_bridge_etf.png"
    fund_png = main_dir / "00_mvpx_bridge_fund.png"
    render_mvpx_bridge(etf_view, etf_png, label="ETF")
    render_mvpx_bridge(fund_view, fund_png, label="Fund")

    pngs: list[Path] = [etf_png, fund_png]
    if with_appendix:
        appendix_pngs = _render_appendix_pngs(etf_view, fund_view, output_dir)
        pngs.extend(appendix_pngs)

    summary = _render_mvpx_summary_markdown(
        as_of_date=as_of_date,
        etf=etf,
        fund=fund,
        figures_root=output_dir,
        summary_path=Path(summary_md),
        mvpx_etf_rel="main/00_mvpx_bridge_etf.png",
        mvpx_fund_rel="main/00_mvpx_bridge_fund.png",
        appendix_included=with_appendix,
    )

    return {
        "as_of_date": as_of_date,
        "png_paths": [str(p) for p in pngs],
        "summary_md": str(summary),
        "with_appendix": with_appendix,
    }
