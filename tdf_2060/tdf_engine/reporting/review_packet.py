"""Phase E-12 — Integrated Review Packet (Markdown + HTML).

E-8 Regime Clock + E-9 SAA Frontier + E-10 TAA Tilt + E-11B Product Selection
+ portfolio JSON 을 운용역 review packet 1개 (md + html) 로 묶는 packaging
모듈.

설계는 `docs/phase_e12_integrated_review_packet.md` (E-12A) 참조.

Hard requirements (E-12):
- 새 분석 차트 미생성 — assets/ 에 PNG 복사 + md/html 신규 생성만.
- 모든 source JSON / PNG mutation 없음 (deepcopy + sha256 검증).
- silent missing artifact 금지 — explicit `missing_data` 기록.
- MVP-X 는 main 섹션 진입 금지 (--include-appendix 옵션만).
"""

from __future__ import annotations

import hashlib
import html as _html
import json
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "e12.1"

LIMITATION_LINES = (
    "Relaxed diagnostic — NOT a production portfolio.",
    "TAA is rule-based regime overlay — NOT regime-conditioned MVO and NOT optimized TAA.",
    "Ticker mapping unavailable — product_id / product_name used as identifier.",
    "Regime-conditioned assumptions unavailable (deferred to future phase).",
    "Efficient frontier sampled by SLSQP grid scan (E-9), not analytical.",
)


# ---------------------------------------------------------------------------
# Source artifact resolver
# ---------------------------------------------------------------------------


def _resolve_artifact_paths(
    *,
    review_root: Path,
    as_of_run: str,
    product_type: str,
    portfolio_json: Path | None,
) -> dict[str, Path | None]:
    """Phase 별 산출물 경로를 resolve. 미존재는 None 으로 (silent skip 금지 — caller 가 missing_data 기록)."""
    rr = Path(review_root)
    a = as_of_run
    pt = product_type
    paths: dict[str, Path | None] = {
        "regime_clock_png": rr / "regime_history" / a / f"regime_clock_{pt}_{a}.png",
        "regime_history_json": rr / "regime_history" / a / f"regime_history_{pt}_{a}.json",
        "saa_mvo_png": rr / "saa_frontier" / a / f"saa_mvo_{pt}_{a}.png",
        "saa_frontier_json": rr / "saa_frontier" / a / f"saa_frontier_{pt}_{a}.json",
        "taa_tilt_png": rr / "taa_tilt" / a / f"taa_tilt_{pt}_{a}.png",
        "taa_tilt_json": rr / "taa_tilt" / a / f"taa_tilt_{pt}_{a}.json",
        "product_selection_png": (
            rr / "product_selection_visualization" / a / f"product_selection_{pt}_{a}.png"
        ),
        "product_selection_json": (
            rr / "product_selection_visualization" / a
            / f"product_selection_visualization_{pt}_{a}.json"
        ),
        "explainability_json": (
            rr / "explainability" / a / f"explainability_{pt}_{a}.json"
        ),
        "portfolio_json": portfolio_json,
    }
    return {k: (v if v is not None and v.exists() else None) for k, v in paths.items()}


def _load_json_safe(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Asset copy (preserve original — sha256 verified)
# ---------------------------------------------------------------------------


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _copy_asset(src: Path | None, assets_dir: Path) -> Path | None:
    """source PNG 를 assets/ 로 복사. None 입력은 None 반환. 원본 sha256 == 사본 sha256 보장."""
    if src is None:
        return None
    assets_dir.mkdir(parents=True, exist_ok=True)
    dst = assets_dir / src.name
    src_h = _sha256(src)
    shutil.copy2(src, dst)
    dst_h = _sha256(dst)
    assert src_h == dst_h, f"asset copy hash mismatch: {src} → {dst}"
    return dst


# ---------------------------------------------------------------------------
# Section builders (build dict, render에서 md/html 둘 다 사용)
# ---------------------------------------------------------------------------


def _build_packet_for_product(
    *,
    product_type: str,
    as_of_run: str,
    paths: dict[str, Path | None],
    assets_dir: Path,
) -> dict[str, Any]:
    """단일 product (etf / fund) 의 packet content dict."""
    section_missing: list[dict[str, str]] = []

    def _missing(field: str, expected: Path | None, source_phase: str) -> None:
        section_missing.append({
            "field": field,
            "impact": f"{source_phase} 섹션 비어 있음",
            "recommended_next_step": (
                f"build_{source_phase} CLI 재실행 — 경로: "
                f"{expected if expected else '<unspecified>'}"
            ),
            "source_phase": source_phase,
        })

    # 0. cover / metadata
    portfolio = _load_json_safe(paths.get("portfolio_json"))
    if portfolio is None:
        _missing("portfolio_artifact_missing", paths.get("portfolio_json"), "portfolio")
    cover: dict[str, Any] = {
        "product_type": product_type.upper(),
        "portfolio_as_of_date": str((portfolio or {}).get("as_of_date") or "—"),
        "portfolio_as_of_run": str((portfolio or {}).get("as_of") or as_of_run),
        "source_mode": str((portfolio or {}).get("source_type") or "—"),
        "operating_mode": "relaxed_diagnostic",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quality_status": str((portfolio or {}).get("quality_status") or "—"),
    }

    # 2. regime
    regime_history = _load_json_safe(paths.get("regime_history_json"))
    regime_png = _copy_asset(paths.get("regime_clock_png"), assets_dir)
    if regime_history is None:
        _missing("regime_history_artifact_missing", paths.get("regime_history_json"), "regime_clock")
    if regime_png is None:
        _missing("regime_clock_png_missing", paths.get("regime_clock_png"), "regime_clock")
    regime_section: dict[str, Any] = {
        "png_rel": (f"assets/{regime_png.name}" if regime_png else None),
        "history": regime_history,
    }

    # 3. SAA
    saa_frontier = _load_json_safe(paths.get("saa_frontier_json"))
    saa_png = _copy_asset(paths.get("saa_mvo_png"), assets_dir)
    if saa_frontier is None:
        _missing("saa_frontier_artifact_missing", paths.get("saa_frontier_json"), "saa_frontier")
    if saa_png is None:
        _missing("saa_mvo_png_missing", paths.get("saa_mvo_png"), "saa_frontier")
    saa_section: dict[str, Any] = {
        "png_rel": (f"assets/{saa_png.name}" if saa_png else None),
        "frontier": saa_frontier,
    }

    # 4. TAA
    taa_tilt = _load_json_safe(paths.get("taa_tilt_json"))
    taa_png = _copy_asset(paths.get("taa_tilt_png"), assets_dir)
    if taa_tilt is None:
        _missing("taa_tilt_artifact_missing", paths.get("taa_tilt_json"), "taa_tilt")
    if taa_png is None:
        _missing("taa_tilt_png_missing", paths.get("taa_tilt_png"), "taa_tilt")
    taa_section: dict[str, Any] = {
        "png_rel": (f"assets/{taa_png.name}" if taa_png else None),
        "tilt": taa_tilt,
    }

    # 5. Product selection
    ps_viz = _load_json_safe(paths.get("product_selection_json"))
    ps_png = _copy_asset(paths.get("product_selection_png"), assets_dir)
    if ps_viz is None:
        _missing("product_selection_artifact_missing", paths.get("product_selection_json"), "product_selection")
    if ps_png is None:
        _missing("product_selection_png_missing", paths.get("product_selection_png"), "product_selection")
    ps_section: dict[str, Any] = {
        "png_rel": (f"assets/{ps_png.name}" if ps_png else None),
        "viz": ps_viz,
    }

    # 6. Final portfolio snapshot
    final_section: dict[str, Any] = {
        "asset_weights": (portfolio or {}).get("asset_weights") or {},
        "asset_weight_sum": (portfolio or {}).get("asset_weight_sum"),
        "constraints_passed": (portfolio or {}).get("constraints_passed"),
        "quality_status": (portfolio or {}).get("quality_status"),
        "max_abs_projection_drift": (portfolio or {}).get("max_abs_projection_drift"),
        "max_abs_asset_weight_drift": (portfolio or {}).get("max_abs_asset_weight_drift"),
        "fallback_used": (portfolio or {}).get("fallback_used"),
        "product_top": _top_products(portfolio),
    }

    # 7. Missing data 통합 (5 phase + section_missing)
    missing_aggregated = list(section_missing)
    explainability = _load_json_safe(paths.get("explainability_json"))
    for phase_label, payload, key in (
        ("e7_explainability", explainability, "report_ready_summary"),
        ("e8_regime_history", regime_history, "diagnostics"),
        ("e9_saa_frontier", saa_frontier, "diagnostics"),
        ("e10_taa_tilt", taa_tilt, "diagnostics"),
        ("e11b_product_selection_viz", ps_viz, "diagnostics"),
    ):
        if not payload:
            continue
        block = (payload.get(key) or {})
        for m in (block.get("missing_data") or []):
            missing_aggregated.append({
                **m,
                "source_phase": phase_label,
            })

    # 1. Executive summary metrics
    saa_w = (
        ((saa_frontier or {}).get("selected_saa") or {}).get("weights") or {}
    )
    taa_target_w = (
        ((taa_tilt or {}).get("portfolio_before_after") or {}).get("taa_target") or {}
    ).get("weights") or {}
    saa_metrics = ((saa_frontier or {}).get("selected_saa") or {})
    taa_metrics_block = (taa_tilt or {}).get("portfolio_before_after") or {}
    taa_metrics = taa_metrics_block.get("taa_target") or {}
    taa_delta = taa_metrics_block.get("delta") or {}
    regime_current = ((regime_history or {}).get("observations") or [])
    current_obs = regime_current[-1] if regime_current else {}

    executive: dict[str, Any] = {
        "current_regime": current_obs.get("regime"),
        "current_regime_label": current_obs.get("regime_label"),
        "saa_top_weights": _top_weights_dict(saa_w, 3),
        "taa_target_top_weights": _top_weights_dict(taa_target_w, 3),
        "final_top_assets": _top_weights_dict(
            (portfolio or {}).get("asset_weights") or {}, 3
        ),
        "saa_sharpe": saa_metrics.get("sharpe"),
        "taa_sharpe": taa_metrics.get("sharpe"),
        "delta_sharpe": taa_delta.get("sharpe"),
        "limitations": list(LIMITATION_LINES),
    }

    return {
        "product_type": product_type,
        "cover": cover,
        "executive": executive,
        "regime": regime_section,
        "saa": saa_section,
        "taa": taa_section,
        "product_selection": ps_section,
        "final": final_section,
        "missing_data": missing_aggregated,
    }


def _top_weights_dict(weights: dict[str, Any], n: int) -> list[tuple[str, float]]:
    pairs = [
        (str(k), float(v))
        for k, v in (weights or {}).items()
        if v is not None
    ]
    pairs.sort(key=lambda x: -x[1])
    return [(k, w) for k, w in pairs[:n]]


def _top_products(portfolio: dict[str, Any] | None, n: int = 10) -> list[dict[str, Any]]:
    if not portfolio:
        return []
    pa = list(portfolio.get("product_allocation") or [])
    pa.sort(key=lambda r: -float(r.get("final_weight") or 0.0))
    return [
        {
            "product_id": r.get("product_id"),
            "product_name": r.get("product_name"),
            "manager": r.get("manager"),
            "asset_key": r.get("asset_key"),
            "final_weight": float(r.get("final_weight") or 0.0),
            "role": r.get("role"),
        }
        for r in pa[:n]
    ]


# ---------------------------------------------------------------------------
# Markdown render
# ---------------------------------------------------------------------------


def _render_md_for_product(packet: dict[str, Any], *, include_appendix: bool) -> str:
    cover = packet["cover"]
    ex = packet["executive"]
    pt = cover["product_type"]
    lines: list[str] = []

    lines.append(f"# Integrated Review Packet — TDF 2060 {pt} Portfolio")
    lines.append("")
    lines.append(f"> schema: {SCHEMA_VERSION}")
    lines.append(
        f"> generated_at: {cover['generated_at']}  ·  "
        f"operating_mode: **{cover['operating_mode']}**"
    )
    lines.append("")
    lines.append("> **RELAXED DIAGNOSTIC RUN — NOT a production portfolio.**")
    for ln in LIMITATION_LINES[1:]:
        lines.append(f"> - {ln}")
    lines.append("")

    # 0. Cover
    lines.append("## 0. Cover / Run Metadata")
    lines.append("")
    lines.append("| 항목 | 값 |")
    lines.append("|---|---|")
    lines.append(f"| product_type | **{cover['product_type']}** |")
    lines.append(f"| portfolio_as_of_date | {cover['portfolio_as_of_date']} |")
    lines.append(f"| portfolio_as_of_run | {cover['portfolio_as_of_run']} |")
    lines.append(f"| source_mode | {cover['source_mode']} |")
    lines.append(f"| quality_status | {cover['quality_status']} |")
    lines.append(f"| operating_mode | {cover['operating_mode']} |")
    lines.append("")

    # 1. Executive Summary
    lines.append("## 1. Executive Summary")
    lines.append("")
    lines.append(_executive_paragraph(packet))
    lines.append("")
    lines.append("| metric | value |")
    lines.append("|---|---|")
    lines.append(f"| current regime | R{ex.get('current_regime')} ({ex.get('current_regime_label')}) |")
    lines.append(
        f"| SAA top weights | {_fmt_weight_pairs(ex['saa_top_weights'])} |"
    )
    lines.append(
        f"| TAA target top weights | {_fmt_weight_pairs(ex['taa_target_top_weights'])} |"
    )
    lines.append(
        f"| Final asset top | {_fmt_weight_pairs(ex['final_top_assets'])} |"
    )
    lines.append(
        f"| Sharpe SAA → TAA | {_fmt_sharpe(ex.get('saa_sharpe'))} → "
        f"{_fmt_sharpe(ex.get('taa_sharpe'))} (Δ={_fmt_sharpe(ex.get('delta_sharpe'))}) |"
    )
    lines.append("")
    lines.append("**Caveats**:")
    for c in ex["limitations"]:
        lines.append(f"- {c}")
    lines.append("")

    # 2. Regime
    lines.append("## 2. Regime Assessment")
    lines.append("")
    if packet["regime"]["png_rel"]:
        lines.append(f"![Regime Clock]({packet['regime']['png_rel']})")
        lines.append("")
    rh = packet["regime"]["history"] or {}
    if rh:
        sig = rh.get("signal") or {}
        cov = rh.get("coverage") or {}
        meta = rh.get("meta") or {}
        last_obs = (rh.get("observations") or [{}])[-1]
        lines.append(
            f"- region: **{sig.get('region')}**, signal as_of: **{meta.get('regime_signal_as_of')}**, "
            f"portfolio as_of: **{meta.get('portfolio_as_of_date')}**"
        )
        lines.append(
            f"- current: R{last_obs.get('regime')} ({last_obs.get('regime_label')}), "
            f"P={float(last_obs.get('placement', 0)):+.4f}, "
            f"V={float(last_obs.get('velocity', 0)):+.4f}"
        )
        lines.append(
            f"- coverage: **{cov.get('coverage_status')}** "
            f"(window {cov.get('count')} obs, full {cov.get('months_available')} obs)"
        )
    else:
        lines.append("_regime artifact unavailable — see §7 missing_data._")
    lines.append("")

    # 3. SAA
    lines.append("## 3. SAA Construction (max-Sharpe MVO, relaxed)")
    lines.append("")
    if packet["saa"]["png_rel"]:
        lines.append(f"![SAA MVO]({packet['saa']['png_rel']})")
        lines.append("")
    sf = packet["saa"]["frontier"] or {}
    if sf:
        sel = sf.get("selected_saa") or {}
        ref = sf.get("reference_points") or {}
        diag = sf.get("diagnostics") or {}
        lines.append(
            f"- selected SAA: E[R]={float(sel.get('expected_return', 0)) * 100:.2f}%, "
            f"σ={float(sel.get('volatility', 0)) * 100:.2f}%, "
            f"Sharpe={_fmt_sharpe(sel.get('sharpe'))}"
        )
        lines.append(
            f"- max-Sharpe ref: Sharpe={_fmt_sharpe((ref.get('max_sharpe') or {}).get('sharpe'))}; "
            f"min-vol ref: σ={float((ref.get('min_vol') or {}).get('volatility', 0)) * 100:.2f}%"
        )
        lines.append(
            f"- selected_matches_max_sharpe: **{diag.get('selected_matches_max_sharpe')}**"
        )
        lines.append(
            "- active constraints: long_only, weight_sum=1.0  ·  "
            "inactive (relaxed): weight_bounds, equity_sum, fixed_income_sum"
        )
    else:
        lines.append("_SAA frontier artifact unavailable — see §7 missing_data._")
    lines.append("")

    # 4. TAA
    lines.append("## 4. TAA Overlay (rule-based regime tilt)")
    lines.append("")
    if packet["taa"]["png_rel"]:
        lines.append(f"![TAA Tilt]({packet['taa']['png_rel']})")
        lines.append("")
    tt = packet["taa"]["tilt"] or {}
    if tt:
        ba = tt.get("portfolio_before_after") or {}
        sa = ba.get("saa") or {}
        ta = ba.get("taa_target") or {}
        de = ba.get("delta") or {}
        rules = tt.get("tilt_rules_applied") or []
        ow = [r for r in rules if r.get("direction") == "overweight"]
        uw = [r for r in rules if r.get("direction") == "underweight"]
        lines.append(
            f"- SAA: E[R]={float(sa.get('expected_return', 0)) * 100:.2f}%, "
            f"σ={float(sa.get('volatility', 0)) * 100:.2f}%, "
            f"Sharpe={_fmt_sharpe(sa.get('sharpe'))}"
        )
        lines.append(
            f"- TAA: E[R]={float(ta.get('expected_return', 0)) * 100:.2f}%, "
            f"σ={float(ta.get('volatility', 0)) * 100:.2f}%, "
            f"Sharpe={_fmt_sharpe(ta.get('sharpe'))}"
        )
        lines.append(
            f"- Δ: E[R]={float(de.get('expected_return', 0)) * 100:+.2f}pp, "
            f"σ={float(de.get('volatility', 0)) * 100:+.2f}pp, "
            f"Sharpe={_fmt_sharpe(de.get('sharpe'), signed=True)}"
        )
        if ow:
            lines.append(
                f"- overweight: {', '.join(f'{r['asset_key']} {r['applied_tilt_pp']:+.2f}pp' for r in ow)}"
            )
        if uw:
            lines.append(
                f"- underweight: {', '.join(f'{r['asset_key']} {r['applied_tilt_pp']:+.2f}pp' for r in uw)}"
            )
        lines.append("")
        lines.append(
            "> **Limitation**: TAA is rule-based regime overlay — NOT regime-conditioned MVO and NOT optimized TAA."
        )
    else:
        lines.append("_TAA tilt artifact unavailable — see §7 missing_data._")
    lines.append("")

    # 5. Product Selection
    lines.append("## 5. Product Selection")
    lines.append("")
    if packet["product_selection"]["png_rel"]:
        lines.append(f"![Product Selection]({packet['product_selection']['png_rel']})")
        lines.append("")
    pv = packet["product_selection"]["viz"] or {}
    if pv:
        funnel = pv.get("funnel") or {}
        rows = (pv.get("selected_product_table") or {}).get("rows") or []
        lines.append(
            f"- universe funnel: raw={funnel.get('raw_count')} → "
            f"passed={funnel.get('passed_filter_count')} → "
            f"classified={funnel.get('classified_count')} → "
            f"eligible={funnel.get('eligible_count')} → "
            f"selected={funnel.get('selected_count')}"
        )
        cov = (pv.get("asset_coverage") or {}).get("by_asset") or {}
        zero_eligible = [k for k, v in cov.items() if v.get("coverage_status") == "none"]
        if zero_eligible:
            lines.append(f"- zero-eligible assets: {', '.join(zero_eligible)}")
        lines.append("")
        lines.append("**Selected products (top 10 by weight):**")
        lines.append("")
        lines.append("| asset | rank | score | weight | product_id | product_name | manager |")
        lines.append("|---|---:|---:|---:|---|---|---|")
        for r in rows[:10]:
            lines.append(
                f"| {r['asset_key']} | "
                f"{int(r['rank_within_asset']) if r.get('rank_within_asset') is not None else '—'} | "
                f"{float(r['score']):.2f} | "
                f"{float(r['product_weight']) * 100:.2f}% | "
                f"{r['product_id']} | {(r['product_name'] or '')[:40]} | {r['manager']} |"
            )
        lines.append("")
        lines.append(
            "> **Identifier note**: ticker mapping unavailable — "
            "product_id / product_name used as identifier."
        )
    else:
        lines.append("_product selection artifact unavailable — see §7 missing_data._")
    lines.append("")

    # 6. Final Portfolio Snapshot
    lines.append("## 6. Final Portfolio Snapshot")
    lines.append("")
    fin = packet["final"]
    if fin.get("asset_weights"):
        lines.append("**Final asset weights:**")
        lines.append("")
        lines.append("| asset | weight |")
        lines.append("|---|---:|")
        items = sorted(fin["asset_weights"].items(), key=lambda x: -float(x[1]))
        for k, v in items:
            lines.append(f"| {k} | {float(v) * 100:.2f}% |")
        lines.append("")
        lines.append(
            f"- asset_weight_sum: {fin.get('asset_weight_sum')}  ·  "
            f"constraints_passed: **{fin.get('constraints_passed')}**  ·  "
            f"quality_status: **{fin.get('quality_status')}**"
        )
        lines.append(
            f"- max_abs_projection_drift: {_fmt_pct(fin.get('max_abs_projection_drift'))}  ·  "
            f"max_abs_asset_weight_drift: {_fmt_pct(fin.get('max_abs_asset_weight_drift'))}  ·  "
            f"fallback_used: {fin.get('fallback_used')}"
        )
        lines.append("")
        if fin.get("product_top"):
            lines.append("**Final product top 10:**")
            lines.append("")
            lines.append("| asset | product_id | product_name | manager | role | weight |")
            lines.append("|---|---|---|---|---|---:|")
            for r in fin["product_top"]:
                lines.append(
                    f"| {r['asset_key']} | {r['product_id']} | "
                    f"{(r['product_name'] or '')[:40]} | {r['manager']} | "
                    f"{r['role']} | {float(r['final_weight']) * 100:.2f}% |"
                )
            lines.append("")
    else:
        lines.append("_portfolio JSON unavailable — see §7 missing_data._")
    lines.append("")

    # 7. Missing data
    lines.append("## 7. Diagnostics / Missing Data")
    lines.append("")
    md = packet.get("missing_data") or []
    if md:
        lines.append("| field | impact | next | source phase |")
        lines.append("|---|---|---|---|")
        seen: set[tuple[str, str]] = set()
        for m in md:
            key = (m.get("field"), m.get("source_phase"))
            if key in seen:
                continue
            seen.add(key)
            lines.append(
                f"| `{m.get('field')}` | {m.get('impact')} | "
                f"{m.get('recommended_next_step')} | {m.get('source_phase')} |"
            )
    else:
        lines.append("_no missing data recorded._")
    lines.append("")

    # 8. Appendix
    if include_appendix:
        lines.append("## 8. Appendix (opt-in)")
        lines.append("")
        lines.append(
            "> Appendix is included via `--include-appendix`. "
            "MVP-X is a **deprecated prototype** retained here for traceability only."
        )
        lines.append("")

    return "\n".join(lines)


def _executive_paragraph(packet: dict[str, Any]) -> str:
    pt = packet["cover"]["product_type"]
    ex = packet["executive"]
    saa_w = packet["executive"]["saa_top_weights"]
    final_w = packet["executive"]["final_top_assets"]
    regime = ex.get("current_regime")
    label = ex.get("current_regime_label") or "—"
    saa_part = (
        f"top SAA weights: {_fmt_weight_pairs(saa_w)}"
        if saa_w else "SAA weights unavailable"
    )
    final_part = (
        f"final top: {_fmt_weight_pairs(final_w)}"
        if final_w else "final unavailable"
    )
    return (
        f"**{pt}** portfolio constructed under regime **R{regime} ({label})**. "
        f"{saa_part}. After rule-based regime tilt (SAA Sharpe {_fmt_sharpe(ex.get('saa_sharpe'))} → "
        f"TAA Sharpe {_fmt_sharpe(ex.get('taa_sharpe'))}, Δ={_fmt_sharpe(ex.get('delta_sharpe'), signed=True)}), "
        f"products were selected by quant_score / sharpe_1y / return_3y / aum_log factors. "
        f"{final_part}."
    )


def _fmt_weight_pairs(pairs: list[tuple[str, float]]) -> str:
    if not pairs:
        return "—"
    return ", ".join(f"{k} {w * 100:.2f}%" for k, w in pairs)


def _fmt_sharpe(v: Any, signed: bool = False) -> str:
    try:
        f = float(v)
        if signed:
            return f"{f:+.4f}"
        return f"{f:.4f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(v: Any) -> str:
    try:
        return f"{float(v) * 100:.2f}%"
    except (TypeError, ValueError):
        return "—"


# ---------------------------------------------------------------------------
# HTML render (simple CSS, no JS)
# ---------------------------------------------------------------------------


_HTML_CSS = """
body { font-family: 'Malgun Gothic', AppleGothic, sans-serif; max-width: 1080px;
       margin: 24px auto; padding: 0 24px; color: #222; line-height: 1.55; }
h1 { border-bottom: 2px solid #333; padding-bottom: 8px; }
h2 { border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 36px; color: #2a3a5a; }
h3 { color: #444; margin-top: 24px; }
table { border-collapse: collapse; margin: 12px 0; }
th, td { border: 1px solid #bbb; padding: 6px 10px; vertical-align: top; }
th { background: #eef2f7; }
img { max-width: 100%; height: auto; border: 1px solid #ddd; padding: 4px;
      background: #fafafa; margin: 8px 0; }
blockquote { border-left: 4px solid #a83232; background: #fff7f7;
             padding: 8px 14px; margin: 14px 0; color: #5a2a2a; }
code { background: #f0f0f0; padding: 2px 4px; border-radius: 3px; font-size: 95%; }
.disclaimer { color: #7a3a3a; font-weight: bold; }
@media print {
    h1, h2 { page-break-after: avoid; }
    img { page-break-inside: avoid; }
    body { font-size: 10.5pt; }
}
"""


def _md_to_html(md_text: str, title: str) -> str:
    """매우 간단한 markdown → html 변환 (외부 라이브러리 없음).

    지원: # 제목 / ## 부제목 / ### 소제목 / **bold** / `code` / | 표 | / ![alt](src) /
    > blockquote / - bullet / 빈 줄.
    """
    out_lines: list[str] = []
    lines = md_text.split("\n")
    i = 0
    in_table = False
    in_ul = False
    while i < len(lines):
        ln = lines[i]
        # heading
        if ln.startswith("# "):
            _close_blocks(out_lines, in_ul, in_table)
            in_ul = False; in_table = False
            out_lines.append(f"<h1>{_html_inline(ln[2:])}</h1>")
        elif ln.startswith("## "):
            _close_blocks(out_lines, in_ul, in_table)
            in_ul = False; in_table = False
            out_lines.append(f"<h2>{_html_inline(ln[3:])}</h2>")
        elif ln.startswith("### "):
            _close_blocks(out_lines, in_ul, in_table)
            in_ul = False; in_table = False
            out_lines.append(f"<h3>{_html_inline(ln[4:])}</h3>")
        elif ln.startswith("> "):
            _close_blocks(out_lines, in_ul, in_table)
            in_ul = False; in_table = False
            # multi-line blockquote
            quote_lines = []
            while i < len(lines) and lines[i].startswith(">"):
                content = lines[i][1:].lstrip()
                quote_lines.append(_html_inline(content))
                i += 1
            out_lines.append("<blockquote>" + "<br/>".join(quote_lines) + "</blockquote>")
            continue
        elif ln.startswith("|") and "|" in ln[1:]:
            if not in_table:
                out_lines.append("<table>")
                in_table = True
                # header row
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                out_lines.append(
                    "<tr>" + "".join(f"<th>{_html_inline(c)}</th>" for c in cells) + "</tr>"
                )
                # skip separator |---|---|
                if i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
                    i += 1
            else:
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                out_lines.append(
                    "<tr>" + "".join(f"<td>{_html_inline(c)}</td>" for c in cells) + "</tr>"
                )
        elif ln.startswith("- "):
            if not in_ul:
                out_lines.append("<ul>")
                in_ul = True
            out_lines.append(f"<li>{_html_inline(ln[2:])}</li>")
        elif ln.startswith("![") and "](" in ln and ln.endswith(")"):
            _close_blocks(out_lines, in_ul, in_table)
            in_ul = False; in_table = False
            alt_end = ln.index("](")
            alt = ln[2:alt_end]
            src = ln[alt_end + 2:-1]
            out_lines.append(
                f'<img src="{_html.escape(src)}" alt="{_html.escape(alt)}"/>'
            )
        elif ln.strip() == "":
            _close_blocks(out_lines, in_ul, in_table)
            in_ul = False; in_table = False
            out_lines.append("")
        else:
            _close_blocks(out_lines, in_ul, in_table)
            in_ul = False; in_table = False
            out_lines.append(f"<p>{_html_inline(ln)}</p>")
        i += 1
    _close_blocks(out_lines, in_ul, in_table)

    body = "\n".join(out_lines)
    return (
        "<!DOCTYPE html>\n<html lang=\"ko\"><head>"
        "<meta charset=\"utf-8\"/>"
        f"<title>{_html.escape(title)}</title>"
        f"<style>{_HTML_CSS}</style></head><body>\n"
        f"{body}\n"
        "</body></html>\n"
    )


def _close_blocks(out_lines: list[str], in_ul: bool, in_table: bool) -> None:
    if in_ul:
        out_lines.append("</ul>")
    if in_table:
        out_lines.append("</table>")


def _html_inline(s: str) -> str:
    """**bold** + `code` 처리. 나머지는 escape."""
    # Order matters — code first to avoid escaping inside.
    parts: list[str] = []
    s_escaped = _html.escape(s)
    # `code`
    out = ""
    in_code = False
    buf = ""
    for ch in s_escaped:
        if ch == "`":
            if in_code:
                out += f"<code>{buf}</code>"
                buf = ""
                in_code = False
            else:
                out += buf
                buf = ""
                in_code = True
        else:
            buf += ch
    out += (f"<code>{buf}</code>" if in_code else buf)
    # **bold**
    while "**" in out:
        first = out.find("**")
        second = out.find("**", first + 2)
        if second == -1:
            break
        out = out[:first] + "<strong>" + out[first + 2:second] + "</strong>" + out[second + 2:]
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_review_packet(
    *,
    review_root: Path,
    as_of_run: str,
    product_type: str,
    portfolio_json: Path | None,
    output_dir: Path,
    fmt: str = "md",
    include_appendix: bool = False,
) -> dict[str, Any]:
    """단일 product (etf / fund) review packet (md / html / both) 생성.

    Returns dict with 'md_path' / 'html_path' / 'packet' / 'assets_copied'.
    """
    output_dir = Path(output_dir)
    assets_dir = output_dir / "assets"

    paths = _resolve_artifact_paths(
        review_root=review_root,
        as_of_run=as_of_run,
        product_type=product_type,
        portfolio_json=portfolio_json,
    )

    # source mtime/sha snapshot for mutation guard
    src_snap = {
        k: (_sha256(v) if v is not None else None)
        for k, v in paths.items() if v is not None
    }

    packet = _build_packet_for_product(
        product_type=product_type,
        as_of_run=as_of_run,
        paths=paths,
        assets_dir=assets_dir,
    )
    md_text = _render_md_for_product(packet, include_appendix=include_appendix)

    md_path: Path | None = None
    html_path: Path | None = None
    if fmt in ("md", "both"):
        md_path = output_dir / f"review_packet_{product_type}_{as_of_run}.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(md_text, encoding="utf-8")
    if fmt in ("html", "both"):
        html_path = output_dir / f"review_packet_{product_type}_{as_of_run}.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(
            _md_to_html(md_text, title=f"Review Packet — {product_type.upper()} {as_of_run}"),
            encoding="utf-8",
        )

    # mutation guard
    for k, expected_h in src_snap.items():
        cur = paths[k]
        if cur is None:
            continue
        assert _sha256(cur) == expected_h, f"source mutated: {cur}"

    return {
        "packet": packet,
        "md_path": md_path,
        "html_path": html_path,
        "assets_dir": assets_dir,
        "include_appendix": include_appendix,
    }


def build_review_packet_both(
    *,
    review_root: Path,
    as_of_run: str,
    portfolio_json_etf: Path | None,
    portfolio_json_fund: Path | None,
    output_dir: Path,
    fmt: str = "md",
    include_appendix: bool = False,
) -> dict[str, Any]:
    """ETF + Fund 통합 packet (단일 md/html) 생성. 두 product 섹션 + comparison."""
    output_dir = Path(output_dir)
    assets_dir = output_dir / "assets"

    etf_paths = _resolve_artifact_paths(
        review_root=review_root, as_of_run=as_of_run,
        product_type="etf", portfolio_json=portfolio_json_etf,
    )
    fund_paths = _resolve_artifact_paths(
        review_root=review_root, as_of_run=as_of_run,
        product_type="fund", portfolio_json=portfolio_json_fund,
    )

    # snapshot for mutation guard
    src_snap = {
        f"etf::{k}": (_sha256(v) if v is not None else None)
        for k, v in etf_paths.items() if v is not None
    }
    src_snap.update({
        f"fund::{k}": (_sha256(v) if v is not None else None)
        for k, v in fund_paths.items() if v is not None
    })

    etf_packet = _build_packet_for_product(
        product_type="etf", as_of_run=as_of_run,
        paths=etf_paths, assets_dir=assets_dir,
    )
    fund_packet = _build_packet_for_product(
        product_type="fund", as_of_run=as_of_run,
        paths=fund_paths, assets_dir=assets_dir,
    )

    md_lines: list[str] = []
    md_lines.append(f"# Integrated Review Packet — TDF 2060 (ETF + Fund) {as_of_run}")
    md_lines.append("")
    md_lines.append(f"> schema: {SCHEMA_VERSION}")
    md_lines.append("")
    md_lines.append("> **RELAXED DIAGNOSTIC RUN — NOT a production portfolio.**")
    for ln in LIMITATION_LINES[1:]:
        md_lines.append(f"> - {ln}")
    md_lines.append("")
    # comparison table
    md_lines.append("## 0. ETF vs Fund Snapshot")
    md_lines.append("")
    md_lines.append("| metric | ETF | Fund |")
    md_lines.append("|---|---|---|")
    for label, ekey, fkey in [
        ("portfolio_as_of_date", "portfolio_as_of_date", "portfolio_as_of_date"),
        ("source_mode", "source_mode", "source_mode"),
        ("quality_status", "quality_status", "quality_status"),
    ]:
        md_lines.append(
            f"| {label} | {etf_packet['cover'].get(ekey)} | {fund_packet['cover'].get(fkey)} |"
        )
    md_lines.append(
        f"| current regime | R{etf_packet['executive'].get('current_regime')} "
        f"({etf_packet['executive'].get('current_regime_label')}) | "
        f"R{fund_packet['executive'].get('current_regime')} "
        f"({fund_packet['executive'].get('current_regime_label')}) |"
    )
    md_lines.append(
        f"| SAA Sharpe | {_fmt_sharpe(etf_packet['executive'].get('saa_sharpe'))} | "
        f"{_fmt_sharpe(fund_packet['executive'].get('saa_sharpe'))} |"
    )
    md_lines.append(
        f"| TAA Sharpe | {_fmt_sharpe(etf_packet['executive'].get('taa_sharpe'))} | "
        f"{_fmt_sharpe(fund_packet['executive'].get('taa_sharpe'))} |"
    )
    md_lines.append("")

    # individual sections (header level 진작 한 단계 들여서 통합)
    for label, packet in (("ETF", etf_packet), ("Fund", fund_packet)):
        md_lines.append(f"# {label}")
        md_lines.append("")
        # 단일 packet 의 md 본문에서 (h1 제목 이후) body만 사용
        body = _render_md_for_product(packet, include_appendix=include_appendix)
        # body 의 h1 제거 (첫 줄)
        body_lines = body.split("\n")
        if body_lines and body_lines[0].startswith("# "):
            body = "\n".join(body_lines[1:])
        md_lines.append(body)
        md_lines.append("")

    md_text = "\n".join(md_lines)

    md_path: Path | None = None
    html_path: Path | None = None
    if fmt in ("md", "both"):
        md_path = output_dir / f"review_packet_both_{as_of_run}.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(md_text, encoding="utf-8")
    if fmt in ("html", "both"):
        html_path = output_dir / f"review_packet_both_{as_of_run}.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(
            _md_to_html(md_text, title=f"Review Packet — ETF+Fund {as_of_run}"),
            encoding="utf-8",
        )

    # mutation guard
    for k, expected_h in src_snap.items():
        prefix, real_k = k.split("::", 1)
        srcset = etf_paths if prefix == "etf" else fund_paths
        cur = srcset[real_k]
        if cur is None:
            continue
        assert _sha256(cur) == expected_h, f"source mutated: {cur}"

    return {
        "etf_packet": etf_packet,
        "fund_packet": fund_packet,
        "md_path": md_path,
        "html_path": html_path,
        "assets_dir": assets_dir,
        "include_appendix": include_appendix,
    }


__all__ = [
    "SCHEMA_VERSION",
    "LIMITATION_LINES",
    "build_review_packet",
    "build_review_packet_both",
]
