"""R-1C — SAA Opportunity Set Scatter / Cloud Visualization (read-only).

R-1B.2 opportunity set JSON 을 입력 받아:
  - main risk-return scatter (feasible vs degenerate, references)
  - metric cloud overlay (top-decile 6종)
  - overlap-score scatter
  - cloud review markdown

production SAA / TAA / product selection / config / Decision Register / E-series
baseline outputs 변경 0.

R-1C scope:
- bucket constraint 는 이미 sampling 단계에서 보장됨 → 시각화에 추가 표기 없음
- 80:20 distance metric 부활 금지
- similar_search 는 R-1C 범위 외 (별도 후속)
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


R1C_SCHEMA_VERSION = "r1c.1"


# 6 cloud metrics 정의: (key in candidate dict, direction, label)
#   direction = "top"    → 큰 값 상위 10% (Sharpe)
#   direction = "bottom" → 작은 값 하위 10% (HHI, mvo_gap, max_w)
METRIC_DECILE_SPECS: list[tuple[str, str, str]] = [
    ("sharpe", "top", "Sharpe top 10%"),
    ("mvo_efficiency_score", "bottom", "MVO gap bottom 10% (closest to frontier)"),
    ("concentration_hhi", "bottom", "HHI bottom 10% (most diversified, full)"),
    ("equity_intra_hhi", "bottom", "equity_intra_HHI bottom 10%"),
    ("fixed_income_intra_hhi", "bottom", "fi_intra_HHI bottom 10%"),
    ("max_asset_weight", "bottom", "max_asset_weight bottom 10%"),
]


# ---------------------------------------------------------------------------
# Quantile threshold + overlap score
# ---------------------------------------------------------------------------


def _percentile(values: list[float], q: float) -> float:
    """Linear interpolation percentile. q ∈ [0, 1]."""
    if not values:
        return float("nan")
    s = sorted(values)
    n = len(s)
    pos = q * (n - 1)
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def _valid_metric_values(
    candidates: list[dict[str, Any]],
    metric_key: str,
) -> list[float]:
    """non-None numeric values for metric across all candidates."""
    out: list[float] = []
    for c in candidates:
        v = c.get(metric_key)
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(f):
            continue
        out.append(f)
    return out


def compute_thresholds(
    candidates: list[dict[str, Any]],
    *,
    quantile: float = 0.10,
) -> dict[str, float]:
    """Return per-metric decile threshold across all candidates with valid values.

    "top" direction → threshold = (1 - quantile) percentile (candidate must be >=)
    "bottom" direction → threshold = quantile percentile (candidate must be <=)
    """
    thresholds: dict[str, float] = {}
    for key, direction, _label in METRIC_DECILE_SPECS:
        vals = _valid_metric_values(candidates, key)
        if not vals:
            thresholds[key] = float("nan")
            continue
        if direction == "top":
            thresholds[key] = _percentile(vals, 1.0 - quantile)
        else:  # bottom
            thresholds[key] = _percentile(vals, quantile)
    return thresholds


def _candidate_in_decile(
    c: dict[str, Any],
    metric_key: str,
    direction: str,
    threshold: float,
) -> bool:
    """True if candidate passes the decile cut for the given metric."""
    if not math.isfinite(threshold):
        return False
    v = c.get(metric_key)
    if v is None:
        return False
    try:
        f = float(v)
    except (TypeError, ValueError):
        return False
    if not math.isfinite(f):
        return False
    if direction == "top":
        return f >= threshold
    return f <= threshold


def attach_overlap_scores(
    candidates: list[dict[str, Any]],
    thresholds: dict[str, float],
) -> list[dict[str, Any]]:
    """Attach `overlap_score` (0-6) + `overlap_flags` dict (per-metric bool).

    Mutates a SHALLOW copy of each candidate. Original input dicts untouched.
    """
    enriched: list[dict[str, Any]] = []
    for c in candidates:
        flags: dict[str, bool] = {}
        for key, direction, _label in METRIC_DECILE_SPECS:
            flags[key] = _candidate_in_decile(c, key, direction, thresholds.get(key, float("nan")))
        score = sum(1 for v in flags.values() if v)
        new = dict(c)
        new["overlap_flags"] = flags
        new["overlap_score"] = int(score)
        enriched.append(new)
    return enriched


def rank_sweet_spot(enriched: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Spec §3 ordering — overlap desc, feasibility, sharpe desc, HHIs asc, id asc."""

    def _key(c: dict[str, Any]) -> tuple:
        sharpe = c.get("sharpe")
        sh = -float(sharpe) if sharpe is not None else 1e18
        return (
            -int(c.get("overlap_score") or 0),                    # 1) overlap desc
            0 if c.get("feasibility_status") == "feasible" else 1,  # 2) feasible 우선
            sh,                                                    # 3) sharpe desc
            float(c.get("concentration_hhi") or 1.0),              # 4) HHI asc
            float(c.get("equity_intra_hhi") or 1.0),               # 5) eq_intra_HHI asc
            float(c.get("fixed_income_intra_hhi") or 1.0),         # 6) fi_intra_HHI asc
            str(c.get("candidate_id") or ""),                      # 7) id asc
        )

    return sorted(enriched, key=_key)


# ---------------------------------------------------------------------------
# Plotting (matplotlib Agg)
# ---------------------------------------------------------------------------


def _select_korean_font() -> str | None:
    import matplotlib.font_manager as fm

    candidates = ("Malgun Gothic", "AppleGothic", "NanumGothic", "Gulim", "MS Gothic")
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            return name
    return None


def _setup_matplotlib():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font_name = _select_korean_font()
    if font_name:
        plt.rcParams["font.family"] = [font_name, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    return plt


def _xy(candidates: list[dict[str, Any]]) -> tuple[list[float], list[float]]:
    xs = [float(c["volatility"]) * 100 for c in candidates]
    ys = [float(c["expected_return"]) * 100 for c in candidates]
    return xs, ys


def _ref_markers(ax, references: dict[str, dict[str, Any]]) -> None:
    """Plot reference points with distinct markers + annotations."""
    style_map = {
        "ref_max_sharpe": dict(
            marker="*", color="#a83232", s=320, edgecolors="white", linewidths=1.5,
        ),
        "ref_80_20_equal_intra_bucket": dict(
            marker="D", color="#3a6db0", s=140, edgecolors="white", linewidths=1.2,
        ),
    }
    for rid, rc in references.items():
        st = style_map.get(rid, dict(marker="P", color="#444", s=120))
        ax.scatter(
            [rc["volatility"] * 100], [rc["expected_return"] * 100],
            zorder=6, **st,
        )
        # annotation
        ax.annotate(
            rid, xy=(rc["volatility"] * 100, rc["expected_return"] * 100),
            xytext=(8, 6), textcoords="offset points",
            fontsize=8.5, color=st.get("color", "#333"), fontweight="bold",
        )


def render_risk_return_scatter(
    payload: dict[str, Any], out_path: Path, *, label: str | None = None
) -> Path:
    """Main risk-return scatter (feasible vs degenerate + references)."""
    plt = _setup_matplotlib()

    cands = payload["candidates"]
    refs = payload["reference_points"]
    feasible = [c for c in cands if c.get("feasibility_status") == "feasible"]
    degen = [c for c in cands if c.get("feasibility_status") != "feasible"]

    fig, ax = plt.subplots(figsize=(11.5, 7.5))
    if feasible:
        xs, ys = _xy(feasible)
        ax.scatter(xs, ys, s=6, c="#3a6db0", alpha=0.25,
                   label=f"Feasible ({len(feasible):,})")
    if degen:
        xs, ys = _xy(degen)
        ax.scatter(xs, ys, s=10, c="#888", alpha=0.55, marker="x",
                   label=f"Degenerate ({len(degen):,})")
    _ref_markers(ax, refs)

    pt = (payload.get("meta", {}).get("product_type") or "").upper()
    ax.set_title(
        f"SAA Opportunity Set — Risk-Return Scatter  ·  {pt} (R-1B.2 bucket-constrained)",
        fontsize=13, fontweight="bold", loc="left",
    )
    ax.set_xlabel("Volatility (σ, %)", fontsize=11)
    ax.set_ylabel("Expected return (E[R], %)", fontsize=11)
    ax.grid(linestyle=":", alpha=0.4)
    ax.legend(loc="lower right", fontsize=9)

    fig.text(
        0.5, 0.012,
        "80:20 is a hard constraint for sampled candidates. "
        "ref_max_sharpe is an unconstrained MVO reference (may violate 80:20).",
        ha="center", fontsize=9, color="#7a3a3a",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path


def _decile_subset(
    candidates: list[dict[str, Any]],
    metric_key: str,
    direction: str,
    threshold: float,
) -> list[dict[str, Any]]:
    return [c for c in candidates
            if _candidate_in_decile(c, metric_key, direction, threshold)]


def render_metric_clouds(
    payload: dict[str, Any],
    thresholds: dict[str, float],
    out_path: Path,
    *,
    label: str | None = None,
) -> Path:
    """Risk-return scatter + 6 top-decile clouds overlay."""
    plt = _setup_matplotlib()

    cands = payload["candidates"]
    refs = payload["reference_points"]

    fig, ax = plt.subplots(figsize=(12.5, 8.0))

    # 1. base layer — all candidates, very light
    xs, ys = _xy(cands)
    ax.scatter(xs, ys, s=4, c="#bbb", alpha=0.18, label="All candidates")

    palette = [
        "#c0392b",  # Sharpe top         — red
        "#27ae60",  # MVO gap bottom     — green
        "#2980b9",  # HHI bottom (full)  — blue
        "#e67e22",  # eq intra HHI bottom — orange
        "#8e44ad",  # fi intra HHI bottom — purple
        "#16a085",  # max_w bottom       — teal
    ]
    markers = ["o", "s", "^", "v", "D", "P"]

    for i, (key, direction, lbl) in enumerate(METRIC_DECILE_SPECS):
        sub = _decile_subset(cands, key, direction, thresholds.get(key, float("nan")))
        if not sub:
            continue
        sx, sy = _xy(sub)
        ax.scatter(
            sx, sy, s=22, c=palette[i % len(palette)],
            marker=markers[i % len(markers)], alpha=0.55,
            edgecolors="none",
            label=f"{lbl} (n={len(sub):,})",
        )

    _ref_markers(ax, refs)

    pt = (payload.get("meta", {}).get("product_type") or "").upper()
    ax.set_title(
        f"SAA Opportunity Set — 6 Top-Decile Clouds  ·  {pt}",
        fontsize=13, fontweight="bold", loc="left",
    )
    ax.set_xlabel("Volatility (σ, %)", fontsize=11)
    ax.set_ylabel("Expected return (E[R], %)", fontsize=11)
    ax.grid(linestyle=":", alpha=0.4)
    ax.legend(loc="lower right", fontsize=8.5, framealpha=0.92)

    fig.text(
        0.5, 0.012,
        "Each cloud = top decile (10%) of one metric. "
        "Overlap regions indicate candidates strong in multiple dimensions.",
        ha="center", fontsize=9, color="#7a3a3a",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path


def render_overlap_score_scatter(
    payload: dict[str, Any],
    enriched: list[dict[str, Any]],
    out_path: Path,
    *,
    label: str | None = None,
) -> Path:
    """Scatter colored by overlap_score, highlighting >=3 and >=4."""
    plt = _setup_matplotlib()

    refs = payload["reference_points"]
    # Group by overlap_score for legend
    groups: dict[int, list[dict[str, Any]]] = {}
    for c in enriched:
        groups.setdefault(int(c["overlap_score"]), []).append(c)

    fig, ax = plt.subplots(figsize=(12.5, 8.0))

    # Color scale: viridis discrete 0..6
    cmap_colors = ["#dddddd", "#9ec6df", "#6fa8c3", "#3a8a9f", "#2c7a4a", "#a87b1e", "#c0392b"]
    sizes_by_score = {0: 4, 1: 6, 2: 9, 3: 18, 4: 36, 5: 60, 6: 100}

    # Draw low scores first (bottom layer), high scores on top
    for score in sorted(groups.keys()):
        sub = groups[score]
        sx, sy = _xy(sub)
        marker_color = cmap_colors[min(score, len(cmap_colors) - 1)]
        size = sizes_by_score.get(score, 4)
        alpha = 0.20 if score < 3 else (0.7 if score < 4 else 0.92)
        edge = "none" if score < 4 else "#222"
        ax.scatter(
            sx, sy, s=size, c=marker_color, alpha=alpha,
            edgecolors=edge, linewidths=(0 if score < 4 else 0.6),
            label=f"overlap_score={score} (n={len(sub):,})",
        )

    _ref_markers(ax, refs)

    pt = (payload.get("meta", {}).get("product_type") or "").upper()
    ax.set_title(
        f"SAA Opportunity Set — Overlap Score Scatter  ·  {pt}",
        fontsize=13, fontweight="bold", loc="left",
    )
    ax.set_xlabel("Volatility (σ, %)", fontsize=11)
    ax.set_ylabel("Expected return (E[R], %)", fontsize=11)
    ax.grid(linestyle=":", alpha=0.4)
    ax.legend(loc="lower right", fontsize=8.5, framealpha=0.92)

    fig.text(
        0.5, 0.012,
        "overlap_score = number of metric top-deciles a candidate hits (0–6). "
        "Overlap_score >= 3 highlighted; >= 4 outlined.",
        ha="center", fontsize=9, color="#7a3a3a",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# Cloud review markdown
# ---------------------------------------------------------------------------


def _fmt_pct(v: float | None) -> str:
    if v is None or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        return "n/a"
    return f"{float(v) * 100:.2f}%"


def _fmt_num(v: float | None, digits: int = 4) -> str:
    if v is None or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        return "n/a"
    return f"{float(v):.{digits}f}"


def _weights_summary(c: dict[str, Any], max_items: int = 4) -> str:
    """Top-N weight string, descending."""
    w = c.get("weights") or {}
    items = sorted(w.items(), key=lambda kv: -float(kv[1]))[:max_items]
    return ", ".join(f"{k}={float(v) * 100:.1f}%" for k, v in items)


def render_cloud_review_md(
    *,
    as_of_run: str,
    etf_payload: dict[str, Any],
    fund_payload: dict[str, Any],
    etf_thresholds: dict[str, float],
    fund_thresholds: dict[str, float],
    etf_enriched_ranked: list[dict[str, Any]],
    fund_enriched_ranked: list[dict[str, Any]],
    plot_paths_etf: dict[str, Path],
    plot_paths_fund: dict[str, Path],
    out_path: Path,
) -> Path:
    """R-1C cloud review markdown."""
    out_path = Path(out_path)

    def _rel(target: Path, start: Path) -> str:
        try:
            return Path(target).resolve().relative_to(Path(start).resolve()).as_posix()
        except ValueError:
            return Path(target).as_posix()

    lines: list[str] = []
    lines.append(
        f"# SAA Opportunity Set — Cloud / Overlap Review (R-1C, {as_of_run})"
    )
    lines.append("")
    lines.append(f"> R-1C schema_version: {R1C_SCHEMA_VERSION}")
    lines.append(
        "> Source: R-1B.2 bucket-constrained opportunity set JSON "
        "(`saa_opportunity_set_{etf,fund}_<as_of>.json`). Read-only diagnostic."
    )
    lines.append(
        "> 모든 sampled candidate 는 equity 80% / fixed_income 20% 를 만족 "
        "(R-1B.2 hard constraint)."
    )
    lines.append("")

    for tag, payload, thresholds, ranked, plots in (
        ("ETF", etf_payload, etf_thresholds, etf_enriched_ranked, plot_paths_etf),
        ("Fund", fund_payload, fund_thresholds, fund_enriched_ranked, plot_paths_fund),
    ):
        meta = payload["meta"]
        diag = payload["diagnostics"]
        cands = payload["candidates"]
        refs = payload["reference_points"]

        feasible_n = sum(
            1 for c in cands if c.get("feasibility_status") == "feasible"
        )
        degen_n = sum(
            1 for c in cands if c.get("feasibility_status") != "feasible"
        )

        # overlap distribution
        score_dist: dict[int, int] = {}
        for c in ranked:
            sc = int(c.get("overlap_score") or 0)
            score_dist[sc] = score_dist.get(sc, 0) + 1
        n_ge_3 = sum(v for k, v in score_dist.items() if k >= 3)
        n_ge_4 = sum(v for k, v in score_dist.items() if k >= 4)
        n_ge_5 = sum(v for k, v in score_dist.items() if k >= 5)
        n_ge_6 = sum(v for k, v in score_dist.items() if k >= 6)

        lines.append(f"## {tag}")
        lines.append("")
        lines.append(
            f"- portfolio as_of: **{meta.get('portfolio_as_of_date')}**, "
            f"source: **{meta.get('source_mode')}**, scope: **{meta.get('scope')}**"
        )
        lines.append(
            f"- candidates: **{len(cands):,}** "
            f"(feasible {feasible_n:,} / degenerate {degen_n:,})"
        )
        lines.append(
            f"- pool_size_total: {diag['pool_size_total']:,}, "
            f"reference: {len(refs)}"
        )
        lines.append("")

        # Threshold table
        lines.append(f"### {tag} · Decile thresholds (10%)")
        lines.append("")
        lines.append("| metric | direction | threshold |")
        lines.append("|---|---|---:|")
        for key, direction, lbl in METRIC_DECILE_SPECS:
            thr = thresholds.get(key, float("nan"))
            if math.isfinite(thr):
                if key == "sharpe":
                    thr_s = f"≥ {thr:.4f}"
                elif key == "mvo_efficiency_score":
                    thr_s = f"≤ {thr:.4f}"
                elif key == "max_asset_weight":
                    thr_s = f"≤ {thr * 100:.2f}%"
                else:
                    thr_s = f"≤ {thr:.4f}"
            else:
                thr_s = "n/a"
            lines.append(f"| `{key}` | {direction} 10% | {thr_s} |")
        lines.append("")

        # Reference points
        lines.append(f"### {tag} · Reference points")
        lines.append("")
        for rid, rc in refs.items():
            sh = rc.get("sharpe")
            eq_ih = rc.get("equity_intra_hhi")
            fi_ih = rc.get("fixed_income_intra_hhi")
            mvo = rc.get("mvo_efficiency_score")
            lines.append(
                f"- **{rid}**: "
                f"E[R]={_fmt_pct(rc['expected_return'])}, "
                f"σ={_fmt_pct(rc['volatility'])}, "
                f"Sharpe={_fmt_num(sh)}, "
                f"eq={_fmt_pct(rc['equity_weight'])}, "
                f"fi={_fmt_pct(rc['fixed_income_weight'])}, "
                f"HHI={_fmt_num(rc['concentration_hhi'])}, "
                f"eq_intra_HHI={_fmt_num(eq_ih)}, "
                f"fi_intra_HHI={_fmt_num(fi_ih)}, "
                f"mvo_gap={_fmt_num(mvo)}"
            )
        lines.append("")

        # Overlap score distribution
        lines.append(f"### {tag} · Overlap score distribution (0–6)")
        lines.append("")
        lines.append("| overlap_score | count |")
        lines.append("|---:|---:|")
        for s in range(0, 7):
            lines.append(f"| {s} | {score_dist.get(s, 0):,} |")
        lines.append("")
        lines.append(
            f"- overlap_score ≥ 3: **{n_ge_3:,}**, "
            f"≥ 4: **{n_ge_4:,}**, "
            f"≥ 5: **{n_ge_5:,}**, "
            f"= 6: **{n_ge_6:,}**"
        )
        lines.append("")

        # PNG embed
        lines.append(f"### {tag} · PNG outputs")
        lines.append("")
        for key, p in plots.items():
            rel = _rel(Path(p), out_path.parent)
            lines.append(f"- **{key}**: `{rel}`")
            lines.append(f"")
            lines.append(f"  ![{tag} {key}]({rel})")
        lines.append("")

        # Top 20 sweet spot table
        lines.append(f"### {tag} · Sweet spot — Top 20 by overlap_score")
        lines.append("")
        lines.append(
            "| # | candidate_id | overlap | E[R] | σ | Sharpe | mvo_gap | HHI | "
            "eq_intra_HHI | fi_intra_HHI | max_w | eq_max | fi_max | feas | weights (top 4) |"
        )
        lines.append(
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"
        )
        for i, c in enumerate(ranked[:20], 1):
            lines.append(
                f"| {i} "
                f"| {c['candidate_id']} "
                f"| **{c['overlap_score']}** "
                f"| {_fmt_pct(c['expected_return'])} "
                f"| {_fmt_pct(c['volatility'])} "
                f"| {_fmt_num(c['sharpe'])} "
                f"| {_fmt_num(c['mvo_efficiency_score'])} "
                f"| {_fmt_num(c['concentration_hhi'])} "
                f"| {_fmt_num(c['equity_intra_hhi'])} "
                f"| {_fmt_num(c['fixed_income_intra_hhi'])} "
                f"| {_fmt_pct(c['max_asset_weight'])} "
                f"| {_fmt_pct(c['equity_max_asset_weight'])} "
                f"| {_fmt_pct(c['fixed_income_max_asset_weight'])} "
                f"| {c['feasibility_status']} "
                f"| {_weights_summary(c)} |"
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "> **Note**: cloud overlap 은 후보를 추천하지 않는다 — 운용역이 정책 가중치를 "
        "반영해 최종 SAA 를 선택한다. 추가 정밀 query (특정 σ/E[R] 점 근처 검색) 는 "
        "R-1D similar_search 진입 시 구현."
    )
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------


def build_cloud_artifacts(
    payload: dict[str, Any],
    out_dir: Path,
    *,
    as_of_run: str,
    portfolio_tag: str,
    quantile: float = 0.10,
) -> dict[str, Any]:
    """Compute thresholds + enriched candidates + 3 PNGs for a single payload.

    Returns dict: {"thresholds": ..., "enriched_ranked": ..., "plots": {key: Path}}.
    The input payload is NOT mutated (works on a deep copy where applicable).
    """
    cands = payload["candidates"]
    thresholds = compute_thresholds(cands, quantile=quantile)
    enriched = attach_overlap_scores(cands, thresholds)
    ranked = rank_sweet_spot(enriched)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    plots: dict[str, Path] = {}
    plots["risk_return_scatter"] = render_risk_return_scatter(
        payload,
        out_dir / f"saa_opportunity_set_{portfolio_tag}_risk_return_scatter_{as_of_run}.png",
        label=portfolio_tag,
    )
    plots["metric_clouds"] = render_metric_clouds(
        payload, thresholds,
        out_dir / f"saa_opportunity_set_{portfolio_tag}_metric_clouds_{as_of_run}.png",
        label=portfolio_tag,
    )
    plots["overlap_score"] = render_overlap_score_scatter(
        payload, enriched,
        out_dir / f"saa_opportunity_set_{portfolio_tag}_overlap_score_{as_of_run}.png",
        label=portfolio_tag,
    )

    return {
        "thresholds": thresholds,
        "enriched_ranked": ranked,
        "plots": plots,
    }


__all__ = [
    "R1C_SCHEMA_VERSION",
    "METRIC_DECILE_SPECS",
    "compute_thresholds",
    "attach_overlap_scores",
    "rank_sweet_spot",
    "render_risk_return_scatter",
    "render_metric_clouds",
    "render_overlap_score_scatter",
    "render_cloud_review_md",
    "build_cloud_artifacts",
]
