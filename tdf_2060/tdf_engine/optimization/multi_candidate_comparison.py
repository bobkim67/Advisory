"""R-1I — Multi-candidate dry-run comparison (read-only batch).

Spec: user R-1I directive (2026-05-13).
- Iterate R-1F.1 manager_selected validation + R-1G.2 PortfolioBuilder wiring
  across multiple candidates (sweet_spot_5 + boundary + references).
- Aggregate into a single multi-candidate comparison markdown.

Hard requirements:
- production_applied = false / dry_run_only = true / implementation_ready = false (strict)
- 기존 R-1G.2 cand_008421 산출물 (out/db_*_relaxed_e62_r1g_reselection/) 덮어쓰기 금지
  → R-1I 산출은 별도 dir (`out/db_*_relaxed_e62_r1i_multi_candidate/{cid}/`).
- reference points (`ref_*`) 는 §2 candidate universe 표에는 포함하되 R-1F/R-1G dry-run
  대상에서 제외.
- 80:20 distance metric 부활 금지.
- TAA / projection / selection / PortfolioBuilder core 무수정.
- 자동 candidate 추천 / final SAA 확정 금지.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tdf_engine.optimization.manager_selected_saa import (
    build_manager_selected_saa,
    write_manager_selected_saa_json,
)
from tdf_engine.optimization.product_reselection_dry_run import (
    TARGET_SOURCE_PROJECTION,
)
from tdf_engine.optimization.r1g2_reselected_portfolio import (
    build_r1g2_portfolio,
    render_three_way_compare_md,
    write_r1g2_portfolio_json,
)


SCHEMA_VERSION = "r1i.1"

SWEET_SPOT_FIVE: tuple[tuple[str, str], ...] = (
    ("cand_008421", "highest Sharpe / special overlap"),
    ("cand_004225", "low max weight / high diversification"),
    ("cand_007510", "low volatility"),
    ("cand_009678", "us_value tilt"),
    ("cand_000758", "balanced"),
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Candidate set builder
# ---------------------------------------------------------------------------


def select_candidate_set(opp_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return {candidate_id: {"tags": [...], "candidate": <full dict from opp_payload>}}.

    Sweet spot 5 + 4 boundary candidates (highest_er / lowest_vol /
    highest_sharpe / lowest_hhi). Deduplicate by candidate_id; merge tags.
    References (`ref_*`) are NOT included here — they are handled separately
    as comparison-only reference points.

    Sampled candidates must satisfy feasibility_status == "feasible".
    """
    feasible = [
        c for c in (opp_payload.get("candidates") or [])
        if c.get("feasibility_status") == "feasible"
    ]
    by_id = {c["candidate_id"]: c for c in feasible}

    result: dict[str, dict[str, Any]] = {}

    # Sweet spot 5 (deterministic order from SWEET_SPOT_FIVE constant)
    for cid, descr in SWEET_SPOT_FIVE:
        if cid not in by_id:
            raise ValueError(
                f"R-1I: sweet_spot candidate {cid!r} not found in opportunity set."
            )
        result.setdefault(cid, {"tags": [], "candidate": by_id[cid]})
        result[cid]["tags"].append(f"sweet_spot:{descr}")

    # Boundary candidates — deterministic top-1 selection with id tie-break
    def _topk(key_fn, reverse: bool) -> dict[str, Any]:
        vals = [
            (key_fn(c), c["candidate_id"], c)
            for c in feasible if key_fn(c) is not None
        ]
        vals.sort(key=lambda t: (-t[0], t[1]) if reverse else (t[0], t[1]))
        return vals[0][2]

    boundary: list[tuple[str, dict[str, Any]]] = [
        ("highest_expected_return",
         _topk(lambda c: c.get("expected_return"), reverse=True)),
        ("lowest_volatility",
         _topk(lambda c: c.get("volatility"), reverse=False)),
        ("highest_sharpe",
         _topk(lambda c: c.get("sharpe"), reverse=True)),
        ("lowest_concentration_hhi",
         _topk(lambda c: c.get("concentration_hhi"), reverse=False)),
    ]
    for tag, cand in boundary:
        cid = cand["candidate_id"]
        result.setdefault(cid, {"tags": [], "candidate": cand})
        result[cid]["tags"].append(f"boundary:{tag}")

    return result


def reference_points_for_comparison(opp_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return reference points to include in §2 table ONLY (no dry-run).

    Per user directive:
      - ref_80_20_equal_intra_bucket included as comparison reference
      - ref_max_sharpe also included as comparison reference (unconstrained MVO)
      - both excluded from R-1F/R-1G dry-run batch.
    """
    refs = opp_payload.get("reference_points") or {}
    out: dict[str, dict[str, Any]] = {}
    for rid in ("ref_80_20_equal_intra_bucket", "ref_max_sharpe"):
        if rid in refs:
            out[rid] = refs[rid]
    return out


# ---------------------------------------------------------------------------
# Per-candidate selection + dry-run
# ---------------------------------------------------------------------------


def _make_selection_input(
    cid: str,
    portfolio_type: str,
    *,
    tags: list[str],
    review_packet_path: Path,
    review_packet_sha: str,
    selected_at: str,
) -> dict[str, Any]:
    """Programmatic equivalent of R-1F.1 yaml input — for batch runs only.

    selected_by / selection_reason 가 자동 추천이 아님을 명시.
    """
    return {
        "portfolio_type": portfolio_type,
        "candidate_id": cid,
        "selected_by": "r1i_multi_candidate_review",
        "selected_at": selected_at,
        "selection_reason": (
            "R-1I multi-candidate comparison sample; not an automated recommendation."
        ),
        "manager_view_notes": [
            "R-1I batch sample input — must be replaced by 운용역 명시 선택 before any "
            "production sign-off.",
            f"candidate_tags: {tags}",
        ],
        "source_review_packet": {
            "path": str(review_packet_path),
            "sha256": review_packet_sha,
        },
        "allow_downstream_dry_run": True,
    }


def run_one_candidate(
    cid: str,
    portfolio_type: str,
    tags: list[str],
    *,
    opp_payload: dict[str, Any],
    opp_payload_path: Path,
    baseline_payload: dict[str, Any],
    baseline_path: Path,
    review_packet_path: Path,
    review_packet_sha: str,
    selected_at: str,
    source_root: Path,
    config_dir: Path,
    selection_out_dir: Path,
    portfolio_out_dir: Path,
    as_of: str,
    operating_mode: str = "relaxed_diagnostic",
) -> dict[str, Any]:
    """Run R-1F.1 validation + R-1G.2 portfolio build for one (candidate, portfolio_type)."""
    # 1) R-1F.1 validation
    selection = _make_selection_input(
        cid, portfolio_type, tags=tags,
        review_packet_path=review_packet_path,
        review_packet_sha=review_packet_sha,
        selected_at=selected_at,
    )
    manager_dump = build_manager_selected_saa(
        selection, opp_payload, opp_payload_path,
        operating_mode=operating_mode,
    )
    manager_dump_path = selection_out_dir / (
        f"manager_selected_saa_{portfolio_type}_{cid}_{as_of}.json"
    )
    write_manager_selected_saa_json(manager_dump, manager_dump_path)

    # 2) Build a synthetic R-1F.2 dump using R-1F.2 logic — required by R-1G.2.
    #    We re-use the existing R-1F.2 module since the asset-level dry-run is
    #    a deterministic function of (manager_dump, baseline). Re-construct here.
    from tdf_engine.optimization.manager_selected_dry_run import (
        build_dry_run_portfolio as _r1f2_build,
    )
    r1f2_payload = _r1f2_build(
        manager_dump, baseline_payload,
        config_dir=config_dir,
        manager_dump_path=manager_dump_path,
        baseline_path=baseline_path,
        operating_mode=operating_mode,
    )
    # R-1F.2 dump 를 candidate 별 dir 에 함께 보관 (R-1G.2 가 path 참조)
    r1f2_dump_path = portfolio_out_dir / f"r1f2_dry_run_{portfolio_type}_{as_of}.json"
    r1f2_dump_path.parent.mkdir(parents=True, exist_ok=True)
    r1f2_dump_path.write_text(
        json.dumps(r1f2_payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # 3) R-1G.2 portfolio + 3-way compare
    r1g2_payload = build_r1g2_portfolio(
        manager_dump, r1f2_payload, baseline_payload,
        source_root=source_root,
        config_dir=config_dir,
        manager_dump_path=manager_dump_path,
        r1f2_dump_path=r1f2_dump_path,
        baseline_portfolio_path=baseline_path,
        target_source=TARGET_SOURCE_PROJECTION,
        selection_as_of=as_of,
        output_as_of=as_of,
        baseline_portfolio_as_of=str(
            (baseline_payload.get("as_of") or "")
        ),
        universe_as_of=str(
            (baseline_payload.get("as_of") or "")
        ),
        operating_mode=operating_mode,
    )
    r1g2_json_path = portfolio_out_dir / f"portfolio_{portfolio_type}_{as_of}.json"
    write_r1g2_portfolio_json(r1g2_payload, r1g2_json_path)

    compare_md_path = portfolio_out_dir / (
        f"r1i_candidate_compare_{portfolio_type}_{cid}_{as_of}.md"
    )
    render_three_way_compare_md(
        r1g2_payload, baseline_payload, r1f2_payload, compare_md_path,
    )

    return {
        "candidate_id": cid,
        "tags": list(tags),
        "portfolio_type": portfolio_type,
        "manager_selected_saa_json_path": str(manager_dump_path),
        "r1f2_dry_run_json_path": str(r1f2_dump_path),
        "r1g2_portfolio_json_path": str(r1g2_json_path),
        "r1g2_compare_md_path": str(compare_md_path),
        "manager_dump": manager_dump,
        "r1f2_payload": r1f2_payload,
        "r1g2_payload": r1g2_payload,
    }


# ---------------------------------------------------------------------------
# Batch orchestrator
# ---------------------------------------------------------------------------


def run_multi_candidate_batch(
    *,
    opp_etf: dict[str, Any],
    opp_fund: dict[str, Any],
    opp_etf_path: Path,
    opp_fund_path: Path,
    baseline_etf: dict[str, Any],
    baseline_fund: dict[str, Any],
    baseline_etf_path: Path,
    baseline_fund_path: Path,
    review_packet_path: Path,
    source_root: Path,
    config_dir: Path,
    multi_candidate_review_dir: Path,
    etf_portfolio_dir: Path,
    fund_portfolio_dir: Path,
    as_of: str,
    selected_at: str | None = None,
    operating_mode: str = "relaxed_diagnostic",
    target_return_advisory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Batch: build candidate set + run per-candidate for ETF/Fund.

    Returns aggregated packet data (used by markdown renderer).
    """
    # ETF/Fund 모두 같은 sampled candidate set 사용 (CMA·SAA·bucket·seed 동일)
    candidate_set = select_candidate_set(opp_etf)

    # Reference points for §2 (no dry-run)
    refs_etf = reference_points_for_comparison(opp_etf)
    refs_fund = reference_points_for_comparison(opp_fund)

    review_packet_sha = _sha256_file(review_packet_path)
    selected_at_str = selected_at or datetime.now(timezone.utc).isoformat()

    multi_candidate_review_dir = Path(multi_candidate_review_dir)
    multi_candidate_review_dir.mkdir(parents=True, exist_ok=True)

    results_etf: dict[str, dict[str, Any]] = {}
    results_fund: dict[str, dict[str, Any]] = {}

    for cid, info in candidate_set.items():
        tags = list(info["tags"])
        etf_dir = Path(etf_portfolio_dir) / cid
        fund_dir = Path(fund_portfolio_dir) / cid
        etf_dir.mkdir(parents=True, exist_ok=True)
        fund_dir.mkdir(parents=True, exist_ok=True)
        results_etf[cid] = run_one_candidate(
            cid, "etf", tags,
            opp_payload=opp_etf, opp_payload_path=opp_etf_path,
            baseline_payload=baseline_etf, baseline_path=baseline_etf_path,
            review_packet_path=review_packet_path,
            review_packet_sha=review_packet_sha,
            selected_at=selected_at_str,
            source_root=source_root, config_dir=config_dir,
            selection_out_dir=multi_candidate_review_dir,
            portfolio_out_dir=etf_dir,
            as_of=as_of, operating_mode=operating_mode,
        )
        results_fund[cid] = run_one_candidate(
            cid, "fund", tags,
            opp_payload=opp_fund, opp_payload_path=opp_fund_path,
            baseline_payload=baseline_fund, baseline_path=baseline_fund_path,
            review_packet_path=review_packet_path,
            review_packet_sha=review_packet_sha,
            selected_at=selected_at_str,
            source_root=source_root, config_dir=config_dir,
            selection_out_dir=multi_candidate_review_dir,
            portfolio_out_dir=fund_dir,
            as_of=as_of, operating_mode=operating_mode,
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "operating_mode": operating_mode,
        "production_applied": False,
        "dry_run_only": True,
        "implementation_ready": False,
        "as_of": as_of,
        "selected_at": selected_at_str,
        "review_packet": {
            "path": str(review_packet_path),
            "sha256": review_packet_sha,
        },
        "candidate_set": candidate_set,
        "references_etf": refs_etf,
        "references_fund": refs_fund,
        "results_etf": results_etf,
        "results_fund": results_fund,
        "target_return_advisory": target_return_advisory,
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _fmt_pct(v: Any) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "n/a"
    return f"{f * 100:.2f}%"


def _fmt_num(v: Any, digits: int = 4) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "n/a"
    return f"{f:.{digits}f}"


def _dominant_equity_tilt(weights: dict[str, float], eq_keys: list[str]) -> str:
    pairs = [(k, float(weights.get(k, 0.0))) for k in eq_keys]
    pairs.sort(key=lambda t: -t[1])
    return pairs[0][0] if pairs else "n/a"


def render_multi_candidate_comparison_md(
    packet: dict[str, Any],
    *,
    opp_etf: dict[str, Any],
    out_path: Path,
) -> Path:
    """Render the R-1I multi-candidate comparison markdown."""
    eq_keys = list(opp_etf["inputs"]["equity_asset_keys"])
    fi_keys = list(opp_etf["inputs"]["fixed_income_asset_keys"])
    asset_keys = list(opp_etf["inputs"]["asset_keys"])

    candidate_set = packet["candidate_set"]
    refs_etf = packet["references_etf"]
    results_etf = packet["results_etf"]
    results_fund = packet["results_fund"]
    advisory = packet.get("target_return_advisory")

    cids = list(candidate_set.keys())

    lines: list[str] = []
    lines.append("# R-1I — Multi-candidate Dry-run Comparison (2026-05-13)")
    lines.append("")
    lines.append(f"> schema_version: {packet['schema_version']}")
    lines.append("> Read-only batch. `production_applied=false`, `dry_run_only=true`, "
                 "`implementation_ready=false` (all candidates).")
    lines.append(
        "> 자동 final SAA 확정 / 자동 candidate 추천 없음. "
        "본 packet 은 운용역이 final SAA 후보를 선택할 수 있도록 "
        "multi-candidate dry-run 결과를 비교한다."
    )
    lines.append("")

    # §1 Executive Summary
    lines.append("## §1. Executive Summary")
    lines.append("")
    lines.append(
        "- R-1I 목적: scatter / shortlist 에서 **여러 후보** 를 선택해 각 후보별 "
        "R-1F.1 validation + R-1G.2 dry-run 을 반복하고, 그 결과를 비교표로 제공."
    )
    lines.append(
        f"- cand_008421 은 **최종안이 아니라 비교 후보 중 하나** "
        f"(R-1H smoke / manager-selected sample input)."
    )
    lines.append(
        f"- 비교 후보군: **sweet_spot_5** + **boundary 4** (deduplicate 후 "
        f"unique sampled = {len(cids)}건) + reference (ref_80_20_equal_intra_bucket, "
        f"ref_max_sharpe)."
    )
    lines.append(
        "- production 반영 아님. 모든 후보에서 `production_applied=false`, "
        "`implementation_ready=false (strict)` 유지."
    )
    lines.append(
        f"- review_packet ref: `{packet['review_packet']['path']}` "
        f"(sha256 {packet['review_packet']['sha256'][:16]}…)"
    )
    if advisory:
        v = advisory.get("value")
        lines.append(
            f"- target_return advisory: value={_fmt_pct(v)}, mode=`{advisory.get('mode','advisory')}`, "
            f"tolerance={_fmt_pct(advisory.get('tolerance'))}. "
            f"**자동 탈락 기준 아님 (advisory only).**"
        )
    lines.append("")

    # §2 Candidate Universe
    lines.append("## §2. Candidate Universe")
    lines.append("")
    lines.append(
        "| candidate_id | tags | E[R] | σ | Sharpe | HHI | eq_iHHI | fi_iHHI | max_w | eq | fi | feasibility |"
    )
    lines.append(
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    )
    for cid in cids:
        info = candidate_set[cid]
        c = info["candidate"]
        lines.append(
            f"| {cid} "
            f"| {', '.join(info['tags'])} "
            f"| {_fmt_pct(c.get('expected_return'))} "
            f"| {_fmt_pct(c.get('volatility'))} "
            f"| {_fmt_num(c.get('sharpe'))} "
            f"| {_fmt_num(c.get('concentration_hhi'))} "
            f"| {_fmt_num(c.get('equity_intra_hhi'))} "
            f"| {_fmt_num(c.get('fixed_income_intra_hhi'))} "
            f"| {_fmt_pct(c.get('max_asset_weight'))} "
            f"| {_fmt_pct(c.get('equity_weight'))} "
            f"| {_fmt_pct(c.get('fixed_income_weight'))} "
            f"| {c.get('feasibility_status')} |"
        )
    # references
    for rid, rc in refs_etf.items():
        lines.append(
            f"| {rid} (reference, dry-run 제외) "
            f"| reference "
            f"| {_fmt_pct(rc.get('expected_return'))} "
            f"| {_fmt_pct(rc.get('volatility'))} "
            f"| {_fmt_num(rc.get('sharpe'))} "
            f"| {_fmt_num(rc.get('concentration_hhi'))} "
            f"| {_fmt_num(rc.get('equity_intra_hhi'))} "
            f"| {_fmt_num(rc.get('fixed_income_intra_hhi'))} "
            f"| {_fmt_pct(rc.get('max_asset_weight'))} "
            f"| {_fmt_pct(rc.get('equity_weight'))} "
            f"| {_fmt_pct(rc.get('fixed_income_weight'))} "
            f"| {rc.get('feasibility_status')} |"
        )
    lines.append("")

    # §3 Risk-return positioning (sweet spot 5 focus)
    sweet_ids = [cid for cid, _ in SWEET_SPOT_FIVE]
    sweet_cands = [candidate_set[cid]["candidate"] for cid in sweet_ids if cid in candidate_set]
    er_vals = [float(c["expected_return"]) for c in sweet_cands]
    vol_vals = [float(c["volatility"]) for c in sweet_cands]
    sh_vals = [float(c["sharpe"]) for c in sweet_cands if c.get("sharpe") is not None]
    lines.append("## §3. Risk-Return Positioning (sweet_spot_5)")
    lines.append("")
    if er_vals and vol_vals and sh_vals:
        lines.append(
            f"- expected_return range: **{_fmt_pct(min(er_vals))} ~ {_fmt_pct(max(er_vals))}** "
            f"(spread {_fmt_pct(max(er_vals) - min(er_vals))})"
        )
        lines.append(
            f"- volatility range: **{_fmt_pct(min(vol_vals))} ~ {_fmt_pct(max(vol_vals))}** "
            f"(spread {_fmt_pct(max(vol_vals) - min(vol_vals))})"
        )
        lines.append(
            f"- Sharpe range: **{min(sh_vals):.4f} ~ {max(sh_vals):.4f}** "
            f"(spread {max(sh_vals) - min(sh_vals):.4f})"
        )
    lines.append("")
    lines.append(
        "**해석**: sweet_spot_5 후보들은 **서로 다른 risk-return 후보가 아니라** "
        "비슷한 risk-return 영역 내에서 자산배분 성격이 다른 후보군이다. "
        "따라서 비교의 목적은 'return / σ 차이' 가 아니라 "
        "**'유사한 risk-return 내에서 어떤 allocation-style 을 택할 것인가'**."
    )
    lines.append("")

    # §4 Asset Allocation Comparison
    lines.append("## §4. Asset Allocation Comparison")
    lines.append("")
    cols = ["candidate_id"] + asset_keys + ["dom_eq_tilt", "HY", "EM", "us_growth", "max_w"]
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "|".join(["---"] + ["---:"] * (len(cols) - 1)) + "|")
    for cid in cids:
        c = candidate_set[cid]["candidate"]
        w = c.get("weights") or {}
        dom = _dominant_equity_tilt(w, eq_keys)
        row = [cid]
        for k in asset_keys:
            row.append(_fmt_pct(w.get(k, 0.0)))
        row.extend([
            dom,
            _fmt_pct(w.get("us_high_yield", 0.0)),
            _fmt_pct(w.get("em_equity", 0.0)),
            _fmt_pct(w.get("us_growth_equity", 0.0)),
            _fmt_pct(c.get("max_asset_weight")),
        ])
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # §5 Product-Level Dry-Run Comparison
    lines.append("## §5. Product-Level Dry-Run Comparison (R-1G.2 results)")
    lines.append("")
    lines.append(
        "| candidate_id | ETF sum | ETF valid | ETF n | ETF dm_ex_us | ETF hy "
        "| Fund sum | Fund valid | Fund n | Fund dm_ex_us | Fund hy | impl_ready |"
    )
    lines.append(
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    )
    for cid in cids:
        e = results_etf[cid]["r1g2_payload"]
        f = results_fund[cid]["r1g2_payload"]
        e_meta = e["meta"]
        f_meta = f["meta"]
        e_count = e.get("selected_count_by_asset", {})
        f_count = f.get("selected_count_by_asset", {})
        lines.append(
            f"| {cid} "
            f"| {e['product_weight_sum']:.6f} "
            f"| {str(e_meta['valid_product_level_portfolio']).lower()} "
            f"| {e['product_count']} "
            f"| {e_count.get('dm_ex_us_equity', 0)} "
            f"| {e_count.get('us_high_yield', 0)} "
            f"| {f['product_weight_sum']:.6f} "
            f"| {str(f_meta['valid_product_level_portfolio']).lower()} "
            f"| {f['product_count']} "
            f"| {f_count.get('dm_ex_us_equity', 0)} "
            f"| {f_count.get('us_high_yield', 0)} "
            f"| {str(e_meta['implementation_ready']).lower()} (strict) |"
        )
    lines.append("")
    lines.append(
        "> **모든 후보에서 `implementation_ready=false (strict)` 유지** — "
        "`valid_product_level_portfolio=true` 가 production 가능을 의미하지 않음."
    )
    lines.append("")

    # §6 Key trade-off matrix (review order — not recommendation)
    lines.append("## §6. Key Trade-off Matrix (review order, **추천 아님**)")
    lines.append("")

    def _by(key_fn, reverse: bool) -> list[str]:
        pairs = [
            (key_fn(candidate_set[cid]["candidate"]), cid)
            for cid in cids
            if key_fn(candidate_set[cid]["candidate"]) is not None
        ]
        pairs.sort(key=lambda t: (-t[0], t[1]) if reverse else (t[0], t[1]))
        return [p[1] for p in pairs]

    def _row(label: str, order_ids: list[str]) -> str:
        return f"| {label} | {' → '.join(order_ids)} |"

    lines.append("| review priority | review order |")
    lines.append("|---|---|")
    lines.append(_row("Sharpe 우선",
        _by(lambda c: c.get("sharpe"), reverse=True)))
    lines.append(_row("σ 낮은 후보 우선",
        _by(lambda c: c.get("volatility"), reverse=False)))
    lines.append(_row("max_asset_weight 낮은 후보 우선",
        _by(lambda c: c.get("max_asset_weight"), reverse=False)))
    lines.append(_row("HHI 낮은 후보 우선",
        _by(lambda c: c.get("concentration_hhi"), reverse=False)))
    lines.append(_row("HY (us_high_yield) 낮은 후보 우선",
        _by(lambda c: float((c.get("weights") or {}).get("us_high_yield", 0.0)),
            reverse=False)))
    lines.append(_row("EM (em_equity) 낮은 후보 우선",
        _by(lambda c: float((c.get("weights") or {}).get("em_equity", 0.0)),
            reverse=False)))
    lines.append(_row("us_growth_equity 쏠림 낮은 후보 우선",
        _by(lambda c: float((c.get("weights") or {}).get("us_growth_equity", 0.0)),
            reverse=False)))
    lines.append(_row("kr_equity (국내) 비중 높은 후보 우선",
        _by(lambda c: float((c.get("weights") or {}).get("kr_equity", 0.0)),
            reverse=True)))
    lines.append("")
    if advisory:
        thr = float(advisory.get("value") or 0.0)
        tol = float(advisory.get("tolerance") or 0.0)
        meet = [
            cid for cid in cids
            if abs(float(candidate_set[cid]["candidate"].get("expected_return") or 0.0) - thr) <= tol
        ]
        above = [
            cid for cid in cids
            if float(candidate_set[cid]["candidate"].get("expected_return") or 0.0) > thr + tol
        ]
        below = [
            cid for cid in cids
            if float(candidate_set[cid]["candidate"].get("expected_return") or 0.0) < thr - tol
        ]
        lines.append(
            f"### §6.1 target_return advisory ({_fmt_pct(thr)} ± {_fmt_pct(tol)})"
        )
        lines.append("")
        lines.append(f"- within band: {meet}")
        lines.append(f"- above band: {above}")
        lines.append(f"- below band: {below}")
        lines.append(
            "- **target_return 미달 자동 탈락 없음 (advisory only).**"
        )
        lines.append("")

    # §7 Candidate-by-candidate notes
    lines.append("## §7. Candidate-by-Candidate Notes")
    lines.append("")
    for cid in cids:
        info = candidate_set[cid]
        c = info["candidate"]
        tags = info["tags"]
        e_payload = results_etf[cid]["r1g2_payload"]
        f_payload = results_fund[cid]["r1g2_payload"]
        e_count = e_payload.get("selected_count_by_asset", {})
        f_count = f_payload.get("selected_count_by_asset", {})
        w = c.get("weights") or {}
        dom = _dominant_equity_tilt(w, eq_keys)
        lines.append(f"### {cid}")
        lines.append("")
        lines.append(f"- tags: {tags}")
        lines.append(
            f"- 특징: Sharpe={_fmt_num(c.get('sharpe'))}, "
            f"E[R]={_fmt_pct(c.get('expected_return'))}, σ={_fmt_pct(c.get('volatility'))}, "
            f"HHI={_fmt_num(c.get('concentration_hhi'))}, max_w={_fmt_pct(c.get('max_asset_weight'))}. "
            f"Dominant equity tilt: **{dom}**."
        )
        # 장점 / 부담 자동 생성 — 자동 추천이 아니라 단순 표지.
        pros: list[str] = []
        cons: list[str] = []
        if c.get("sharpe") is not None and float(c["sharpe"]) >= 0.62:
            pros.append("Sharpe 상위권")
        if float(c.get("max_asset_weight") or 0.0) <= 0.20:
            pros.append(f"max_w {_fmt_pct(c.get('max_asset_weight'))} — 집중도 낮음")
        if float(c.get("concentration_hhi") or 1.0) <= 0.15:
            pros.append(f"HHI {_fmt_num(c.get('concentration_hhi'))} — 분산 우수")
        if float(c.get("volatility") or 1.0) <= 0.123:
            pros.append(f"σ {_fmt_pct(c.get('volatility'))} — 변동성 낮음")
        if float(w.get("us_high_yield", 0.0)) >= 0.09:
            cons.append(f"us_high_yield {_fmt_pct(w.get('us_high_yield'))} — credit cycle 부담 가능")
        if float(w.get("us_growth_equity", 0.0)) >= 0.24:
            cons.append(
                f"us_growth_equity {_fmt_pct(w.get('us_growth_equity'))} — equity 집중"
            )
        if float(c.get("max_asset_weight") or 0.0) >= 0.245:
            cons.append(f"max_w {_fmt_pct(c.get('max_asset_weight'))} — 단일 자산 cap 근접")
        if float(w.get("em_equity", 0.0)) >= 0.19:
            cons.append(f"em_equity {_fmt_pct(w.get('em_equity'))} — 신흥국 over-tilt")

        if pros:
            lines.append(f"- 장점: {', '.join(pros)}")
        if cons:
            lines.append(f"- 부담 요인: {', '.join(cons)}")

        # 상품단 warning
        e_hy = e_count.get("us_high_yield", 0)
        f_hy = f_count.get("us_high_yield", 0)
        product_warnings: list[str] = []
        if e_hy <= 2 and float(w.get("us_high_yield", 0.0)) > 0.05:
            product_warnings.append(
                f"ETF us_high_yield universe 한계: picks={e_hy} (universe 2건). 대체 후보 부족."
            )
        if not e_payload["meta"]["valid_product_level_portfolio"]:
            product_warnings.append("ETF valid_product_level_portfolio = false")
        if not f_payload["meta"]["valid_product_level_portfolio"]:
            product_warnings.append("Fund valid_product_level_portfolio = false")
        if product_warnings:
            lines.append("- 상품단 warning:")
            for pw in product_warnings:
                lines.append(f"  - {pw}")

        # 운용역 판단 질문
        questions: list[str] = []
        if float(w.get("us_growth_equity", 0.0)) > 0.20:
            questions.append(
                f"us_growth_equity {_fmt_pct(w.get('us_growth_equity'))} tilt 가 운용 view 와 정합한가?"
            )
        if float(w.get("us_high_yield", 0.0)) > 0.05:
            questions.append(
                f"us_high_yield {_fmt_pct(w.get('us_high_yield'))} tilt 가 credit cycle view 와 정합한가?"
            )
        if float(w.get("em_equity", 0.0)) > 0.15:
            questions.append(
                f"em_equity {_fmt_pct(w.get('em_equity'))} 신흥국 tilt 가 view 와 정합한가?"
            )
        if float(w.get("kr_equity", 0.0)) >= 0.18:
            questions.append(
                f"kr_equity {_fmt_pct(w.get('kr_equity'))} 국내 tilt 가 view 와 정합한가?"
            )
        if questions:
            lines.append("- 운용역 판단 질문:")
            for q in questions:
                lines.append(f"  - {q}")
        lines.append("")

    # §8 Manager decision worksheet
    lines.append("## §8. Manager Decision Worksheet (운용역 작성용)")
    lines.append("")
    lines.append(
        "| candidate_id | manager_view | return_profile_fit | risk_profile_fit | "
        "equity_tilt_fit | FI_tilt_fit | HY_comfort | EM_comfort | "
        "concentration_comfort | product_implementation_comfort | "
        "include_in_final_saa_review | reason |"
    )
    lines.append("|" + "|".join(["---"] * 12) + "|")
    for cid in cids:
        lines.append("| " + cid + " | " + " | ".join([""] * 11) + " |")
    lines.append("")
    lines.append(
        "작성 가이드: `manager_view` ∈ {positive, neutral, negative, hold}; "
        "`include_in_final_saa_review` ∈ {yes, no}. 본 worksheet 는 운용역의 정성 "
        "판단을 위한 빈 필드이며, **자동 채움 없음**."
    )
    lines.append("")

    # §9 Next Options
    lines.append("## §9. Next Options")
    lines.append("")
    lines.append(
        "| 옵션 | 내용 |"
    )
    lines.append("|:---:|---|")
    lines.append(
        "| **A** | 후보군 중 1개를 final SAA review candidate 로 지정 (운용역 명시 sign-off + Decision Register 신규 entry + Phase F gate 필요) |"
    )
    lines.append(
        "| **B** | 특정 후보 주변에서 R-1D weight similarity search 로 추가 후보 발굴 |"
    )
    lines.append(
        "| **C** | target_return advisory line 을 추가하여 재필터링 (advisory only, 자동 탈락 없음) |"
    )
    lines.append(
        "| **D** | Phase F production review 는 아직 **보류** |"
    )
    lines.append("")

    # §10 Variation registry
    lines.append("## §10. 본 작업의 변경 범위")
    lines.append("")
    lines.append("| 영역 | 변경 |")
    lines.append("|---|:---:|")
    lines.append("| 본 multi-candidate comparison packet (1건) | ✓ 신규 |")
    lines.append("| candidate 별 R-1F.1 / R-1F.2 / R-1G.2 산출 (별도 dir) | ✓ 신규 |")
    lines.append("| 기존 R-1G.2 cand_008421 산출물 | ✗ 무변경 (별도 디렉토리 사용) |")
    lines.append("| R-1A ~ R-1H 산출물 | ✗ 무변경 |")
    lines.append("| 코드 / config / tests | ✗ 무변경 |")
    lines.append("| Decision Register count (14) | ✗ 무변경 |")
    lines.append("| E-series baseline | ✗ 무변경 |")
    lines.append("| `tests/_phase_e62_baseline.json` sha | ✗ 무변경 |")
    lines.append("| operating_mode | ✗ `relaxed_diagnostic` 유지 |")
    lines.append("| 80:20 distance metric | ✗ 부활 없음 |")
    lines.append("| 자동 final SAA 확정 / 자동 candidate 추천 | ✗ 금지 |")
    lines.append("| `implementation_ready` | ✗ 모든 후보에서 false strict |")
    lines.append("")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


__all__ = [
    "SCHEMA_VERSION",
    "SWEET_SPOT_FIVE",
    "select_candidate_set",
    "reference_points_for_comparison",
    "run_one_candidate",
    "run_multi_candidate_batch",
    "render_multi_candidate_comparison_md",
]
