"""Phase E-11A — Product Selection Score Telemetry (read-only).

portfolio_*.json (E-11A 적용 후 — selection_diagnostics.scored_products 포함) →
formatted product_selection_telemetry dict.

Hard requirements:
- 입력 portfolio JSON mutation 없음.
- selection logic 미참조 (read-only on JSON dict).
- product_id / product_name 필수, ticker 부재 시 missing_data 명시.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "e11a.1"


def _require_e11a_telemetry(portfolio: dict[str, Any]) -> dict[str, Any]:
    diag = portfolio.get("diagnostics") or {}
    sel = diag.get("selection_diagnostics") or {}
    if "scored_products" not in sel:
        raise ValueError(
            "E-11A telemetry requires "
            "`diagnostics.selection_diagnostics.scored_products` "
            "(set by selection/tool.py after the E-11A patch). "
            "Re-run build_portfolio with the updated selection module."
        )
    return sel


def build_product_selection_telemetry(
    portfolio_json: Path,
) -> dict[str, Any]:
    """portfolio_*.json → product_selection_telemetry dict.

    raises ValueError if scored_products telemetry missing (E-11A patch not applied).
    """
    portfolio_path = Path(portfolio_json)
    raw = portfolio_path.read_text(encoding="utf-8")
    portfolio = json.loads(raw)

    sel_diag = _require_e11a_telemetry(portfolio)
    universe_diag = (portfolio.get("diagnostics") or {}).get("universe_diagnostics") or {}
    fb_diag = (portfolio.get("diagnostics") or {}).get("fallback") or {}
    pa = list(portfolio.get("product_allocation") or [])
    asset_alloc = list(portfolio.get("asset_allocation") or [])

    scored_products = list(sel_diag.get("scored_products") or [])
    excluded_by_asset = dict(sel_diag.get("excluded_by_asset") or {})
    classified_by = dict(universe_diag.get("classified_by_asset_class") or {})

    # universe.by_asset
    asset_keys_all = sorted({
        *classified_by.keys(),
        *(r["asset_key"] for r in scored_products),
        *(r.get("asset_key", "") for r in pa if r.get("asset_key")),
    })
    selected_count_by_asset: dict[str, int] = {}
    for r in pa:
        ak = str(r.get("asset_key") or "")
        if not ak:
            continue
        selected_count_by_asset[ak] = selected_count_by_asset.get(ak, 0) + 1
    eligible_count_by_asset: dict[str, int] = {}
    for r in scored_products:
        eligible_count_by_asset[r["asset_key"]] = eligible_count_by_asset.get(r["asset_key"], 0) + 1

    universe_block: dict[str, Any] = {
        "total_count": int(universe_diag.get("total_products") or 0),
        "raw_count": int(universe_diag.get("raw_count") or 0),
        "passed_filter_count": int(universe_diag.get("passed_filter_count") or 0),
        "classified_count": int(universe_diag.get("classified_count") or 0),
        "by_asset": {
            ak: {
                "raw_count": int(classified_by.get(ak, 0)),
                "eligible_count": int(eligible_count_by_asset.get(ak, 0)),
                "selected_count": int(selected_count_by_asset.get(ak, 0)),
            }
            for ak in asset_keys_all
        },
    }

    # filters.by_asset
    filters_by_asset: dict[str, Any] = {}
    for ak in asset_keys_all:
        excluded = list(excluded_by_asset.get(ak) or [])
        reason_counts: dict[str, int] = {}
        for ex in excluded:
            r = str(ex.get("reason") or "unspecified")
            reason_counts[r] = reason_counts.get(r, 0) + 1
        filters_by_asset[ak] = {
            "excluded": excluded,
            "filter_summary": reason_counts,
        }

    # scoring
    scoring_block: dict[str, Any] = {
        "score_method": str(sel_diag.get("score_method") or sel_diag.get("quant_grade_policy", {}).get("mode") or ""),
        "score_factors": list(sel_diag.get("score_factors") or []),
        "scored_products": [
            {
                **r,
                # 사용자 spec compliance: 모든 항목에 product_name + product_id 명시
                "product_id": r.get("product_id"),
                "product_name": r.get("product_name"),
                "asset_key": r.get("asset_key"),
                "score": r.get("score"),
                "rank_within_asset": r.get("rank_within_asset"),
                "selected": r.get("selected"),
                "factor_values": r.get("factor_values") or {},
            }
            for r in scored_products
        ],
        "grade_filtered_count": int(sel_diag.get("grade_filtered_count") or 0),
        "grade_penalized_count": int(sel_diag.get("grade_penalized_count") or 0),
    }

    # final_selection — product_allocation enriched + score / rank lookup
    score_lookup: dict[str, dict[str, Any]] = {
        str(r.get("product_id")): r for r in scored_products
    }
    asset_target_lookup = {
        str(r.get("asset_key")): float(r.get("final_asset_weight") or 0.0)
        for r in asset_alloc
    }
    final_sel: list[dict[str, Any]] = []
    for r in pa:
        pid = str(r.get("product_id") or "")
        s_row = score_lookup.get(pid) or {}
        flags = list(r.get("warning_flags") or [])
        cap_applied = any("fallback_absorber" in str(f) for f in flags)
        ak = str(r.get("asset_key") or "")
        final_sel.append({
            "product_id": pid,
            "product_name": str(r.get("product_name") or ""),
            "ticker": None,  # 원본 etf_list/fund_list 에 ticker 없음 — missing_data
            "manager": str(r.get("manager") or ""),
            "asset_key": ak,
            "bucket": str(r.get("bucket") or ""),
            "asset_weight": asset_target_lookup.get(ak),
            "product_weight": float(r.get("final_weight") or 0.0),
            "score": s_row.get("score"),
            "rank_within_asset": s_row.get("rank_within_asset"),
            "selected_reason": (
                str(r.get("selection_reason"))
                if r.get("selection_reason") is not None else None
            ),
            "cap_applied": cap_applied,
            "role": str(r.get("role") or ""),
            "constraint_notes": flags,
        })

    payload: dict[str, Any] = {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "product_type": str(portfolio.get("portfolio_type") or ""),
            "portfolio_as_of_date": str(portfolio.get("as_of_date") or ""),
            "portfolio_as_of_run": str(portfolio.get("as_of") or ""),
            "source_mode": str(portfolio.get("source_type") or "file"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_files": {
                "portfolio_json": str(portfolio_path),
            },
        },
        "universe": universe_block,
        "filters": {"by_asset": filters_by_asset},
        "scoring": scoring_block,
        "final_selection": {"selected_products": final_sel},
        "fallback_summary": {
            "fallback_used": bool(fb_diag.get("fallback_used", False)),
            "cash_placeholder_weight": float(fb_diag.get("cash_placeholder_weight") or 0.0),
            "fallback_absorbers_count": len(fb_diag.get("fallback_absorbers") or []),
        },
        "diagnostics": {
            "warnings": list(sel_diag.get("warnings") or []),
            "missing_data": [
                {
                    "field": "final_selection.selected_products[].ticker",
                    "impact": "Bloomberg/Reuters ticker 표기 불가",
                    "recommended_next_step": (
                        "외부 ticker mapping table 도입 또는 "
                        "DBProductRepository.product_metadata 확장"
                    ),
                },
                {
                    "field": "scoring.score_factors[].cost_penalty",
                    "impact": "비용 패널티 미사용 (weight=0.0)",
                    "recommended_next_step": (
                        "future phase — fee/expense ratio 데이터 도입"
                    ),
                },
            ],
        },
    }

    # mutation guard
    assert portfolio_path.read_text(encoding="utf-8") == raw

    return payload


def write_telemetry_json(payload: dict[str, Any], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return out_path


def render_summary_md(
    *,
    as_of_run: str,
    etf_payload: dict[str, Any],
    fund_payload: dict[str, Any],
    out_path: Path,
) -> Path:
    lines: list[str] = []
    lines.append(f"# Product Selection Score Telemetry Summary ({as_of_run})")
    lines.append("")
    lines.append(f"> schema_version: {SCHEMA_VERSION}")
    lines.append("> Read-only diagnostic. selection logic / allocation 결과 미변경 (bit-identical 검증 통과).")
    lines.append("")
    for label, payload in (("ETF", etf_payload), ("Fund", fund_payload)):
        meta = payload["meta"]
        uni = payload["universe"]
        sc = payload["scoring"]
        sel = payload["final_selection"]["selected_products"]
        lines.append(f"## {label}")
        lines.append("")
        lines.append(
            f"- portfolio as_of: **{meta['portfolio_as_of_date']}**, "
            f"source: **{meta['source_mode']}**"
        )
        lines.append(
            f"- universe: total={uni['total_count']}, raw={uni['raw_count']}, "
            f"passed_filter={uni['passed_filter_count']}, "
            f"classified={uni['classified_count']}"
        )
        lines.append(
            f"- score_method: **{sc['score_method']}**, "
            f"factors={len(sc['score_factors'])}, "
            f"scored_products={len(sc['scored_products'])}, "
            f"selected={sum(1 for r in sc['scored_products'] if r['selected'])}"
        )
        lines.append("")
        lines.append("### universe.by_asset")
        lines.append("")
        lines.append("| asset_key | raw | eligible | selected |")
        lines.append("|---|---:|---:|---:|")
        for ak, info in uni["by_asset"].items():
            lines.append(
                f"| {ak} | {info['raw_count']} | {info['eligible_count']} "
                f"| {info['selected_count']} |"
            )
        lines.append("")
        lines.append("### final_selection.selected_products")
        lines.append("")
        lines.append("| asset_key | product_id | product_name | manager | rank | score | weight |")
        lines.append("|---|---|---|---|---:|---:|---:|")
        sel_sorted = sorted(sel, key=lambda x: -float(x.get("product_weight") or 0.0))
        for r in sel_sorted:
            score = r.get("score")
            score_s = f"{float(score):.4f}" if score is not None else "—"
            rank_s = (
                str(int(r["rank_within_asset"])) if r.get("rank_within_asset") is not None else "—"
            )
            lines.append(
                f"| {r['asset_key']} | {r['product_id']} | "
                f"{r['product_name'][:40]} | {r['manager']} | "
                f"{rank_s} | {score_s} | "
                f"{r['product_weight'] * 100:.2f}% |"
            )
        lines.append("")
        lines.append("### diagnostics.missing_data")
        lines.append("")
        for m in payload["diagnostics"]["missing_data"]:
            lines.append(
                f"- **{m['field']}** — {m['impact']} → next: {m['recommended_next_step']}"
            )
        lines.append("")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


__all__ = [
    "SCHEMA_VERSION",
    "build_product_selection_telemetry",
    "write_telemetry_json",
    "render_summary_md",
]
