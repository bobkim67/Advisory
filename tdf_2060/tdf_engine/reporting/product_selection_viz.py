"""Phase E-11B — Product Selection Explainability Visualization.

E-11A telemetry JSON (product_selection_telemetry_*.json) → visualization-ready
summary + 6-panel PNG.

6 panel:
  1. Universe funnel (raw → passed → classified → eligible → selected)
  2. Asset-level coverage (raw / eligible / selected per asset)
  3. Filter exclusion reasons
  4. Scoring method / factor weights
  5. Rank vs selected product table
  6. Final selection explanation footer

Hard requirements:
- E-11A telemetry 만 사용 (read-only).
- selection / scoring / allocation 로직 미참조 (telemetry JSON dict 만).
- ticker 부재는 missing_data 로 명시.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "e11b.1"

ASSET_BUCKET_HINT: dict[str, str] = {
    # 색상 매핑 hint — 보기 편하게 grouping
    "kr_equity": "equity",
    "us_growth_equity": "equity",
    "us_value_equity": "equity",
    "dm_ex_us_equity": "equity",
    "em_equity": "equity",
    "kr_aggregate_bond": "fixed_income",
    "kr_treasury_10y": "fixed_income",
    "us_treasury_30y": "fixed_income",
    "us_high_yield": "risk_asset",
}

BUCKET_COLORS: dict[str, str] = {
    "equity": "#3a6db0",
    "fixed_income": "#7fa8c2",
    "risk_asset": "#c97a2a",
    "_other": "#bbbbbb",
}


# ---------------------------------------------------------------------------
# Telemetry guard
# ---------------------------------------------------------------------------


def _require_e11a_telemetry(telemetry: dict[str, Any]) -> None:
    for need in ("universe", "scoring", "final_selection"):
        if need not in telemetry:
            raise ValueError(
                f"E-11B requires E-11A telemetry block `{need}` "
                f"(product_selection_telemetry_*.json)."
            )
    if "scored_products" not in (telemetry.get("scoring") or {}):
        raise ValueError(
            "E-11B requires `scoring.scored_products` from E-11A telemetry."
        )


# ---------------------------------------------------------------------------
# Visualization JSON builder
# ---------------------------------------------------------------------------


def _coverage_status(eligible: int, selected: int) -> str:
    if eligible == 0:
        return "none"
    if selected == 0:
        return "limited"
    return "sufficient"


def build_visualization_data(
    telemetry_json: Path,
) -> dict[str, Any]:
    """E-11A telemetry JSON → visualization-ready dict.

    raises ValueError if telemetry blocks missing.
    """
    telemetry_path = Path(telemetry_json)
    raw = telemetry_path.read_text(encoding="utf-8")
    telemetry = json.loads(raw)
    _require_e11a_telemetry(telemetry)

    meta = telemetry.get("meta") or {}
    uni = telemetry.get("universe") or {}
    filt = telemetry.get("filters") or {}
    sc = telemetry.get("scoring") or {}
    fs = telemetry.get("final_selection") or {}

    # funnel — eligible_count: scored_products 의 unique 자산 합계 = scored_products 수
    eligible_count = sum(
        info.get("eligible_count", 0) for info in (uni.get("by_asset") or {}).values()
    )
    selected_count = sum(
        info.get("selected_count", 0) for info in (uni.get("by_asset") or {}).values()
    )
    funnel = {
        "raw_count": int(uni.get("raw_count") or 0),
        "passed_filter_count": int(uni.get("passed_filter_count") or 0),
        "classified_count": int(uni.get("classified_count") or 0),
        "eligible_count": int(eligible_count),
        "selected_count": int(selected_count),
    }

    # asset_coverage
    asset_coverage_by_asset: dict[str, dict[str, Any]] = {}
    for ak, info in (uni.get("by_asset") or {}).items():
        raw_c = int(info.get("raw_count") or 0)
        elig_c = int(info.get("eligible_count") or 0)
        sel_c = int(info.get("selected_count") or 0)
        asset_coverage_by_asset[ak] = {
            "raw_count": raw_c,
            "eligible_count": elig_c,
            "selected_count": sel_c,
            "coverage_status": _coverage_status(elig_c, sel_c),
        }

    # filter exclusions — by_reason aggregate + by_asset_reason
    by_reason: dict[str, int] = {}
    by_asset_reason: dict[str, dict[str, int]] = {}
    for ak, block in (filt.get("by_asset") or {}).items():
        summary = dict(block.get("filter_summary") or {})
        if summary:
            by_asset_reason[ak] = summary
        for reason, count in summary.items():
            by_reason[reason] = by_reason.get(reason, 0) + int(count)

    # selected product table
    selected_rows: list[dict[str, Any]] = []
    for r in (fs.get("selected_products") or []):
        selected_rows.append({
            "asset_key": str(r.get("asset_key") or ""),
            "product_id": str(r.get("product_id") or ""),
            "product_name": str(r.get("product_name") or ""),
            "manager": str(r.get("manager") or ""),
            "ticker": r.get("ticker"),  # None 보존
            "rank_within_asset": r.get("rank_within_asset"),
            "score": r.get("score"),
            "product_weight": float(r.get("product_weight") or 0.0),
            "selected_reason": r.get("selected_reason"),
            "cap_applied": bool(r.get("cap_applied", False)),
            "role": str(r.get("role") or ""),
        })
    # weight 내림차순
    selected_rows.sort(key=lambda x: -float(x["product_weight"] or 0.0))

    payload: dict[str, Any] = {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "product_type": str(meta.get("product_type") or ""),
            "portfolio_as_of_date": str(meta.get("portfolio_as_of_date") or ""),
            "source_mode": str(meta.get("source_mode") or ""),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "input_telemetry": {
            "source_json": str(telemetry_path),
            "score_method": str(sc.get("score_method") or ""),
            "score_factors": list(sc.get("score_factors") or []),
        },
        "funnel": funnel,
        "asset_coverage": {"by_asset": asset_coverage_by_asset},
        "filter_exclusions": {
            "by_reason": by_reason,
            "by_asset_reason": by_asset_reason,
        },
        "selected_product_table": {"rows": selected_rows},
        "diagnostics": {
            "warnings": list(telemetry.get("diagnostics", {}).get("warnings") or []),
            "missing_data": list(
                telemetry.get("diagnostics", {}).get("missing_data") or []
            ),
        },
    }

    # mutation guard
    assert telemetry_path.read_text(encoding="utf-8") == raw

    return payload


def write_viz_json(payload: dict[str, Any], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return out_path


# ---------------------------------------------------------------------------
# PNG renderer (6 panel)
# ---------------------------------------------------------------------------


def _select_korean_font() -> str | None:
    import matplotlib.font_manager as fm

    candidates = ("Malgun Gothic", "AppleGothic", "NanumGothic", "Gulim", "MS Gothic")
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            return name
    return None


def _short(text: str, max_len: int = 40) -> str:
    if text is None:
        return ""
    s = str(text)
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def render_product_selection(
    viz_payload: dict[str, Any],
    out_path: Path,
    *,
    label: str | None = None,
) -> Path:
    """6-panel product selection PNG (read-only, deepcopy)."""
    payload = deepcopy(viz_payload)

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
    inp = payload["input_telemetry"]
    funnel = payload["funnel"]
    cov = payload["asset_coverage"]["by_asset"]
    excl = payload["filter_exclusions"]
    rows = payload["selected_product_table"]["rows"]

    pt = (meta.get("product_type") or "").upper()

    fig = plt.figure(figsize=(15.0, 22.0))
    gs = _gs.GridSpec(
        nrows=6, ncols=2,
        height_ratios=[0.6, 1.6, 2.0, 2.0, 1.4, 4.0],
        width_ratios=[1.0, 1.0],
        hspace=0.55, wspace=0.20,
        left=0.06, right=0.97, top=0.98, bottom=0.04,
    )

    # ── Header ──────────────────────────────────────────────────────
    ax_h = fig.add_subplot(gs[0, :])
    ax_h.set_axis_off()
    ax_h.text(
        0.0, 0.85,
        f"Product Selection Explainability — {pt} Portfolio",
        fontsize=15, fontweight="bold", transform=ax_h.transAxes, va="top",
    )
    ax_h.text(
        0.0, 0.45,
        f"as_of={meta.get('portfolio_as_of_date')}  ·  source={meta.get('source_mode')}  ·  "
        f"score_method={inp.get('score_method')}  ·  schema={meta.get('schema_version')}",
        fontsize=10.5, color="#333", transform=ax_h.transAxes, va="center",
    )
    ax_h.text(
        0.0, 0.10,
        "Read-only diagnostic. Selection / scoring logic was not re-executed.",
        fontsize=9, color="#7a3a3a", transform=ax_h.transAxes, va="bottom",
    )

    # ── Panel 1: Universe funnel ────────────────────────────────────
    ax1 = fig.add_subplot(gs[1, 0])
    funnel_steps = [
        ("raw", funnel["raw_count"]),
        ("passed_filter", funnel["passed_filter_count"]),
        ("classified", funnel["classified_count"]),
        ("eligible", funnel["eligible_count"]),
        ("selected", funnel["selected_count"]),
    ]
    names = [s[0] for s in funnel_steps]
    counts = [s[1] for s in funnel_steps]
    y = np.arange(len(names))
    ax1.barh(y, counts, color=["#3a6db0", "#7fa8c2", "#9bbb59", "#c97a2a", "#a83232"])
    ax1.set_yticks(y)
    ax1.set_yticklabels(names)
    ax1.invert_yaxis()
    ax1.set_xlabel("Product count")
    upper = max(counts) * 1.20 if counts else 1
    ax1.set_xlim(0, max(upper, 1))
    ax1.grid(axis="x", linestyle=":", alpha=0.4)
    for i, c in enumerate(counts):
        ax1.text(c + upper * 0.01, i, str(c), va="center", fontsize=10, fontweight="bold")
    ax1.set_title(
        "1. Universe Funnel (raw → passed → classified → eligible → selected)",
        fontsize=11, fontweight="bold", loc="left",
    )

    # ── Panel 2: Asset-level coverage ──────────────────────────────
    ax2 = fig.add_subplot(gs[1, 1])
    asset_keys = list(cov.keys())
    raw_v = [cov[k]["raw_count"] for k in asset_keys]
    elig_v = [cov[k]["eligible_count"] for k in asset_keys]
    sel_v = [cov[k]["selected_count"] for k in asset_keys]
    ya = np.arange(len(asset_keys))
    ax2.barh(ya, raw_v, color="#cccccc", label="raw")
    ax2.barh(ya, elig_v, color="#7fa8c2", label="eligible")
    ax2.barh(ya, sel_v, color="#a83232", label="selected")
    # 0-eligible 자산 highlight
    for i, k in enumerate(asset_keys):
        if cov[k]["coverage_status"] == "none":
            ax2.text(
                max(raw_v) * 1.02 if raw_v else 1, i,
                "  ⚠ no eligible",
                va="center", fontsize=8.5, color="#a83232", fontweight="bold",
            )
    ax2.set_yticks(ya)
    ax2.set_yticklabels(asset_keys, fontsize=9)
    ax2.invert_yaxis()
    ax2.set_xlabel("Product count")
    upper2 = max(raw_v) * 1.20 if raw_v else 1
    ax2.set_xlim(0, max(upper2, 1))
    ax2.grid(axis="x", linestyle=":", alpha=0.4)
    ax2.legend(loc="lower right", fontsize=9)
    ax2.set_title(
        "2. Asset-Level Coverage (raw / eligible / selected per asset)",
        fontsize=11, fontweight="bold", loc="left",
    )

    # ── Panel 3: Filter exclusion reasons ──────────────────────────
    ax3 = fig.add_subplot(gs[2, 0])
    by_reason = excl.get("by_reason") or {}
    by_asset_reason = excl.get("by_asset_reason") or {}
    if by_reason:
        # stacked bar: x=asset_key, stack=reason
        reasons_all = sorted(by_reason.keys())
        # short reason 라벨
        def _short_reason(r: str) -> str:
            if "grade_below_min" in r:
                return "grade_below_min"
            if "aum_below_min" in r:
                return "aum_below_min"
            return r[:30]

        # asset 별 stacked
        asset_excl_keys = sorted(by_asset_reason.keys())
        x_pos = np.arange(len(asset_excl_keys))
        bottom = [0.0] * len(asset_excl_keys)
        cmap = plt.get_cmap("Set2")
        for ri, full_reason in enumerate(reasons_all):
            short = _short_reason(full_reason)
            vals = []
            for ak in asset_excl_keys:
                count = 0
                for r2, c2 in (by_asset_reason.get(ak) or {}).items():
                    if _short_reason(r2) == short and r2 == full_reason:
                        count += int(c2)
                vals.append(count)
            ax3.bar(
                x_pos, vals, bottom=bottom,
                color=cmap(ri % 8), label=short[:25],
            )
            bottom = [bottom[j] + vals[j] for j in range(len(asset_excl_keys))]
        ax3.set_ylabel("Excluded count")
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels(asset_excl_keys, rotation=30, ha="right", fontsize=8)
        ax3.grid(axis="y", linestyle=":", alpha=0.4)
        ax3.legend(loc="upper right", fontsize=8)
    else:
        ax3.set_axis_off()
        ax3.text(0.5, 0.5, "no exclusions recorded", ha="center", va="center")
    ax3.set_title(
        "3. Filter Exclusion Reasons (by asset)",
        fontsize=11, fontweight="bold", loc="left",
    )

    # ── Panel 4: Scoring method / factor weights ───────────────────
    ax4 = fig.add_subplot(gs[2, 1])
    factors = inp.get("score_factors") or []
    if factors:
        names4 = [f["factor"] for f in factors]
        weights4 = [float(f["weight"]) * 100 for f in factors]
        avail4 = [bool(f.get("available", True)) for f in factors]
        colors4 = [
            "#3a6db0" if a else "#cccccc" for a in avail4
        ]
        bars = ax4.barh(names4, weights4, color=colors4)
        ax4.invert_yaxis()
        ax4.set_xlabel("Weight (%)")
        upper4 = max(weights4) * 1.30 if weights4 else 1
        ax4.set_xlim(0, max(upper4, 1))
        ax4.grid(axis="x", linestyle=":", alpha=0.4)
        for bar, w, a in zip(bars, weights4, avail4):
            suffix = "" if a else "  (unavailable)"
            color = "#444" if a else "#a83232"
            ax4.text(
                bar.get_width() + upper4 * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{w:.1f}%{suffix}",
                va="center", fontsize=9, color=color,
            )
    else:
        ax4.set_axis_off()
        ax4.text(0.5, 0.5, "no score factors", ha="center", va="center")
    ax4.set_title(
        f"4. Scoring Method = {inp.get('score_method')}  ·  Factor Weights",
        fontsize=11, fontweight="bold", loc="left",
    )

    # ── Panel 5: Selected product table (rank vs weight) ───────────
    ax5 = fig.add_subplot(gs[3:5, :])
    ax5.set_axis_off()
    ax5.set_title(
        "5. Selected Products — rank within asset · score · weight",
        fontsize=12, fontweight="bold", loc="left",
    )
    if rows:
        # render table
        headers = [
            "asset_key", "rank", "score", "weight", "product_id",
            "product_name", "manager", "ticker",
        ]
        cell_text: list[list[str]] = []
        for r in rows:
            score = r.get("score")
            score_s = f"{float(score):.4f}" if score is not None else "—"
            rank_s = (
                str(int(r["rank_within_asset"]))
                if r.get("rank_within_asset") is not None else "—"
            )
            cell_text.append([
                r["asset_key"],
                rank_s,
                score_s,
                f"{float(r['product_weight']) * 100:.2f}%",
                r["product_id"],
                _short(r["product_name"], 38),
                _short(r["manager"], 14),
                "unavailable" if r.get("ticker") in (None, "") else str(r["ticker"]),
            ])
        table = ax5.table(
            cellText=cell_text, colLabels=headers,
            loc="upper center", cellLoc="left", colLoc="center",
            colWidths=[0.13, 0.05, 0.08, 0.08, 0.08, 0.32, 0.16, 0.10],
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8.5)
        table.scale(1.0, 1.35)
        # header style
        for j in range(len(headers)):
            cell = table[(0, j)]
            cell.set_facecolor("#dfe7f0")
            cell.set_text_props(fontweight="bold")
        # selected row tint
        for i, r in enumerate(rows, start=1):
            tint = "#fafafa" if i % 2 == 1 else "#ffffff"
            for j in range(len(headers)):
                table[(i, j)].set_facecolor(tint)
            # ticker missing red
            ticker_cell = table[(i, len(headers) - 1)]
            if r.get("ticker") in (None, ""):
                ticker_cell.set_text_props(color="#a83232")
    else:
        ax5.text(0.5, 0.5, "no selected products", ha="center", va="center")

    # ── Panel 6: Final selection explanation footer ────────────────
    ax6 = fig.add_subplot(gs[5, :])
    ax6.set_axis_off()
    explain_lines = [
        "Selected products are top-ranked eligible products within each asset bucket.",
        "Final product weights reflect target asset weights, per-product cap constraints, "
        "and fallback redistribution.",
        "",
        "Method note:",
        "  ETF: broader raw universe, hard-filter method (grade_below_min excluded outright).",
        "  Fund: narrower eligible universe, score-penalty method "
        "(grade_below_min remains but score is reduced).",
        "",
        "Identifier note:",
        "  Ticker mapping unavailable; product_id / product_name used as identifier.",
        "  See diagnostics.missing_data for the deferred ticker mapping plan.",
    ]
    ax6.text(
        0.02, 0.98, "\n".join(explain_lines),
        transform=ax6.transAxes, ha="left", va="top",
        fontsize=10, color="#333", family="monospace",
        bbox=dict(facecolor="#f7f7f7", edgecolor="#aaa", boxstyle="round,pad=0.6"),
    )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# Summary md
# ---------------------------------------------------------------------------


def render_summary_md(
    *,
    as_of_run: str,
    etf_payload: dict[str, Any],
    fund_payload: dict[str, Any],
    etf_png_rel: str,
    fund_png_rel: str,
    out_path: Path,
) -> Path:
    lines: list[str] = []
    lines.append(f"# Product Selection Visualization Summary ({as_of_run})")
    lines.append("")
    lines.append(f"> schema_version: {SCHEMA_VERSION}")
    lines.append("> Read-only diagnostic. Selection / scoring logic not re-executed.")
    lines.append("")
    for label, payload, png_rel in (
        ("ETF", etf_payload, etf_png_rel),
        ("Fund", fund_payload, fund_png_rel),
    ):
        meta = payload["meta"]
        funnel = payload["funnel"]
        inp = payload["input_telemetry"]
        cov = payload["asset_coverage"]["by_asset"]
        excl = payload["filter_exclusions"]
        rows = payload["selected_product_table"]["rows"]
        lines.append(f"## {label}")
        lines.append("")
        lines.append(
            f"- portfolio as_of: **{meta['portfolio_as_of_date']}**, "
            f"source: **{meta['source_mode']}**, "
            f"score_method: **{inp['score_method']}**"
        )
        lines.append(
            f"- funnel: raw={funnel['raw_count']} → "
            f"passed_filter={funnel['passed_filter_count']} → "
            f"classified={funnel['classified_count']} → "
            f"eligible={funnel['eligible_count']} → "
            f"selected={funnel['selected_count']}"
        )
        zero_elig = [k for k, v in cov.items() if v["coverage_status"] == "none"]
        if zero_elig:
            lines.append(
                f"- assets with zero eligible: {', '.join(zero_elig)}"
            )
        lines.append("")
        lines.append("### filter exclusion reasons")
        lines.append("")
        for r, c in sorted((excl.get("by_reason") or {}).items()):
            lines.append(f"- `{r}`: {c}")
        lines.append("")
        lines.append("### selected products (top by weight)")
        lines.append("")
        lines.append("| asset_key | rank | score | weight | product_id | product_name | manager |")
        lines.append("|---|---:|---:|---:|---|---|---|")
        for r in rows:
            score = r.get("score")
            score_s = f"{float(score):.4f}" if score is not None else "—"
            rank_s = (
                str(int(r["rank_within_asset"]))
                if r.get("rank_within_asset") is not None else "—"
            )
            lines.append(
                f"| {r['asset_key']} | {rank_s} | {score_s} | "
                f"{r['product_weight'] * 100:.2f}% | {r['product_id']} | "
                f"{_short(r['product_name'], 40)} | {r['manager']} |"
            )
        lines.append("")
        lines.append(f"![{label} Product Selection]({png_rel})")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "**Identifier note**: Ticker mapping unavailable for both ETF and Fund — "
        "product_id / product_name used as identifier. See diagnostics.missing_data."
    )
    lines.append("")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


__all__ = [
    "SCHEMA_VERSION",
    "build_visualization_data",
    "write_viz_json",
    "render_product_selection",
    "render_summary_md",
]
