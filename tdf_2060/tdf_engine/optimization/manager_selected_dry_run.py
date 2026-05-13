"""R-1F.2 — Manager-Selected SAA downstream dry-run wiring (read-only).

Spec: tdf_2060/docs/r1e_manager_selected_saa_dry_run_spec.md (§5 wiring,
§8.1 default — manager_override_saa 별도 layer / 병렬 비교).

R-1F.2 scope:
- Load R-1F.1 manager_selected_saa JSON + baseline portfolio JSON
- Re-run TAA overlay + projection using manager_override_saa.weights as SAA input
- Scale product allocation proportionally to dry-run final asset weights
- Dump dry-run portfolio JSON + comparison markdown to **separate output dir**

Hard requirements (R-1E §5.4):
- 기존 core 로직 (TAAOverlayEngine / project_to_feasible / portfolio_builder) 수정 금지
- 기존 production 디렉토리 (`out/db_{etf,fund}_relaxed_e62/`) 덮어쓰기 금지
- `tests/_phase_e62_baseline.json` sha256 변경 금지
- production_applied 항상 False / dry_run_only 항상 True
- 자동 final SAA 확정 금지
- 80:20 hard constraint 보존
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tdf_engine.config.loader import ConfigLoader
from tdf_engine.taa.overlay import TAAOverlayEngine
from tdf_engine.taa.policy import RegimeTAAPolicy


SCHEMA_VERSION = "r1f2.1"

# R-1F.2.1 — product_weight_sum 이 1.0 에서 이만큼 벗어나면 portfolio 유효성
# 플래그 (valid_product_level_portfolio) 를 false 로 단언한다.
PRODUCT_WEIGHT_SUM_VALID_TOL = 1e-3

REMOVED_METRIC_KEYS = (
    "bucket_distance_from_80_20",
    "full_weight_distance_from_80_20_equal_bucket_reference",
)


# ---------------------------------------------------------------------------
# Pre-execution validation (re-check from manager_selected_saa JSON)
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _ensure_dry_run_eligible(
    manager_dump: dict[str, Any],
    *,
    operating_mode: str,
) -> None:
    """V-16 + R-1F.1 dump 의 invariant 재확인."""
    meta = manager_dump.get("meta") or {}
    if meta.get("production_applied") is not False:
        raise ValueError(
            "R-1F.2 pre-check: manager_selected_saa.meta.production_applied must be False."
        )
    if meta.get("manager_override_saa_layer") is not True:
        raise ValueError(
            "R-1F.2 pre-check: manager_override_saa_layer must be True (separate layer)."
        )
    if manager_dump.get("downstream_dry_run_allowed") is not True:
        raise ValueError(
            "R-1F.2 pre-check: downstream_dry_run_allowed must be True."
        )
    if manager_dump.get("downstream_dry_run_executed") is True:
        # 정보용 — 재실행은 허용하지만 새 dump 가 새 timestamp 로 생성됨.
        pass
    if str(meta.get("operating_mode") or "") != "relaxed_diagnostic":
        raise ValueError(
            "R-1F.2 pre-check: operating_mode in manager_selected_saa must be 'relaxed_diagnostic'."
        )
    if operating_mode != "relaxed_diagnostic":
        raise ValueError(
            f"R-1F.2 dry-run forbidden in operating_mode={operating_mode!r}; "
            "require 'relaxed_diagnostic'."
        )

    sc = manager_dump.get("selected_candidate") or {}
    cid = str(sc.get("candidate_id") or "")
    if not cid.startswith("cand_"):
        raise ValueError(
            f"R-1F.2 pre-check: selected_candidate_id must be sampled (cand_NNNNNN); got {cid!r}."
        )
    if sc.get("feasibility_status") != "feasible":
        raise ValueError(
            "R-1F.2 pre-check: selected_candidate.feasibility_status must be 'feasible'."
        )
    eq = float(sc.get("equity_weight") or 0.0)
    fi = float(sc.get("fixed_income_weight") or 0.0)
    if abs(eq - 0.80) > 1e-9:
        raise ValueError(
            f"R-1F.2 pre-check: bucket violation equity_weight={eq} (expected 0.80)."
        )
    if abs(fi - 0.20) > 1e-9:
        raise ValueError(
            f"R-1F.2 pre-check: bucket violation fixed_income_weight={fi} (expected 0.20)."
        )
    # 80:20 distance metric resurrection guard
    for k in REMOVED_METRIC_KEYS:
        if k in sc:
            raise ValueError(
                f"R-1F.2 pre-check: removed metric {k!r} resurrected in selected_candidate."
            )


# ---------------------------------------------------------------------------
# Adapter: bucket_by_asset / asset_bounds from baseline portfolio
# ---------------------------------------------------------------------------


def _bucket_by_asset_from_baseline(baseline: dict[str, Any]) -> dict[str, str]:
    return {
        row["asset_key"]: row["bucket"]
        for row in (baseline.get("asset_allocation") or [])
    }


def _regime_int_from_baseline(baseline: dict[str, Any]) -> int:
    return int((baseline.get("diagnostics") or {}).get("regime", {}).get("regime"))


# ---------------------------------------------------------------------------
# Asset-level dry-run via existing TAAOverlayEngine (core unchanged)
# ---------------------------------------------------------------------------


def run_asset_level_dry_run(
    manager_dump: dict[str, Any],
    baseline: dict[str, Any],
    *,
    config_dir: Path,
) -> dict[str, Any]:
    """Inject manager_override_saa.weights at SAA seam → TAA + projection.

    Uses production TAAOverlayEngine + RegimeTAAPolicy + config without modification.
    Returns dict containing dry-run TAA result + per-asset summary.
    """
    import pandas as pd

    loader = ConfigLoader(Path(config_dir))
    taa_cfg = loader.load_taa_config() or {}
    tilts_raw = taa_cfg.get("regime_tilts") or {}
    constraints = taa_cfg.get("constraints") or {}
    policy = RegimeTAAPolicy.from_dict(tilts_raw)

    bucket_by_asset = _bucket_by_asset_from_baseline(baseline)

    sc = manager_dump["selected_candidate"]
    asset_keys = list(sc["weights"].keys())
    override = pd.Series(
        {k: float(sc["weights"][k]) for k in asset_keys},
        name="manager_override_saa",
    )

    engine = TAAOverlayEngine(
        policy=policy,
        constraints=constraints,
        bucket_by_asset=bucket_by_asset,
        asset_bounds={},
        bucket_bounds={},
        enable_projection=True,
    )
    regime = _regime_int_from_baseline(baseline)
    taa_result = engine.apply(override, regime)

    # taa_result.taa_weights (after projection) — pd.Series
    # taa_result.tilts — per-asset tilt
    target_pre = override + taa_result.tilts
    final_after_projection = taa_result.taa_weights

    asset_rows = []
    proj_drifts = []
    for k in asset_keys:
        saa_w = float(override.get(k, 0.0))
        target_w = float(target_pre.get(k, 0.0))
        final_w = float(final_after_projection.get(k, 0.0))
        drift = final_w - target_w
        proj_drifts.append(abs(drift))
        asset_rows.append({
            "asset_key": k,
            "bucket": bucket_by_asset.get(k),
            "saa_weight_override": saa_w,
            "taa_target_weight_before_projection": target_w,
            "final_asset_weight": final_w,
            "projection_drift": drift,
        })

    eq_sum = sum(r["final_asset_weight"] for r in asset_rows if r["bucket"] == "equity")
    fi_sum = sum(
        r["final_asset_weight"] for r in asset_rows if r["bucket"] == "fixed_income"
    )

    return {
        "regime": regime,
        "regime_label": str((baseline.get("diagnostics") or {}).get("regime", {}).get("regime_label") or ""),
        "asset_keys": asset_keys,
        "asset_allocation_dry_run": asset_rows,
        "taa_target_weights": {k: float(target_pre[k]) for k in asset_keys},
        "taa_after_projection_weights": {k: float(final_after_projection[k]) for k in asset_keys},
        "bucket_sums_after_projection": {
            "equity": float(eq_sum),
            "fixed_income": float(fi_sum),
        },
        "max_abs_projection_drift": float(max(proj_drifts) if proj_drifts else 0.0),
        "taa_diagnostics": taa_result.diagnostics,
    }


# ---------------------------------------------------------------------------
# Product-level dry-run via proportional scaling (approximate)
# ---------------------------------------------------------------------------


def run_product_level_dry_run(
    baseline: dict[str, Any],
    asset_dry_run: dict[str, Any],
) -> dict[str, Any]:
    """Scale baseline product weights per asset by dry-run final asset weight.

    LIMITATION: 진짜 re-selection 은 universe + scoring engine 필요. 본 함수는
    baseline 의 product-asset 분배 비율을 유지한 채 asset-level final weight 로 scale.
    asset 의 baseline final 이 ≈0 인데 dry-run 이 > 0 인 경우 'needs_selection_rerun'
    플래그를 단다.
    """
    base_allocations = baseline.get("product_allocation") or []
    base_asset_weights = baseline.get("asset_weights") or {}
    dry_asset_weights = asset_dry_run["taa_after_projection_weights"]

    rows: list[dict[str, Any]] = []
    needs_rerun: list[str] = []
    for row in base_allocations:
        ak = row.get("asset_key")
        base_a = float(base_asset_weights.get(ak, 0.0))
        dry_a = float(dry_asset_weights.get(ak, 0.0))
        base_p = float(row.get("final_weight") or 0.0)
        if base_a < 1e-9:
            # baseline asset weight near zero — scaling 불가
            if dry_a > 1e-6:
                needs_rerun.append(ak)
            new_p = 0.0
        else:
            new_p = base_p * (dry_a / base_a)
        new_row = dict(row)
        new_row["final_weight_dry_run"] = float(new_p)
        new_row["final_weight_baseline"] = base_p
        new_row["weight_delta"] = float(new_p - base_p)
        new_row["asset_weight_baseline"] = base_a
        new_row["asset_weight_dry_run"] = dry_a
        rows.append(new_row)

    # 정합성: dry-run product weight 합 ≈ sum of dry_a where base_a > 0
    scaled_assets = {ak for ak in dry_asset_weights if float(base_asset_weights.get(ak, 0.0)) >= 1e-9}
    scaled_total = sum(v for k, v in dry_asset_weights.items() if k in scaled_assets)
    product_total = sum(r["final_weight_dry_run"] for r in rows)

    return {
        "product_allocation_dry_run": rows,
        "product_weight_sum_dry_run": float(product_total),
        "needs_selection_rerun_assets": sorted(set(needs_rerun)),
        "scaled_asset_total": float(scaled_total),
        "limitation": (
            "Product allocation dry-run is a proportional scaling of baseline product "
            "weights by the ratio (dry_run_asset_weight / baseline_asset_weight). "
            "True re-selection (re-running universe + scoring + selection) is NOT performed "
            "here. Assets where baseline weight ≈ 0 but dry-run > 0 are listed under "
            "needs_selection_rerun_assets and require R-1G or full re-selection."
        ),
    }


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------


def build_dry_run_portfolio(
    manager_dump: dict[str, Any],
    baseline: dict[str, Any],
    *,
    config_dir: Path,
    manager_dump_path: Path,
    baseline_path: Path,
    operating_mode: str = "relaxed_diagnostic",
) -> dict[str, Any]:
    """Assemble the dry-run portfolio payload."""
    _ensure_dry_run_eligible(manager_dump, operating_mode=operating_mode)

    asset_dr = run_asset_level_dry_run(
        manager_dump, baseline, config_dir=config_dir,
    )
    product_dr = run_product_level_dry_run(baseline, asset_dr)

    sc = manager_dump["selected_candidate"]
    portfolio_type = str(manager_dump["selection_input"]["portfolio_type"])

    # baseline summaries
    base_asset_weights = baseline.get("asset_weights") or {}
    base_saa = (baseline.get("diagnostics") or {}).get("saa_diagnostics", {}).get("saa_weights") or {}
    base_drift = float(baseline.get("max_abs_asset_weight_drift") or 0.0)

    # R-1F.2.1 validity labels — distinguish asset-level (valid) from
    # product-level (approximation, NOT a runnable portfolio)
    product_sum = float(product_dr["product_weight_sum_dry_run"])
    product_weight_sum_valid = abs(product_sum - 1.0) <= PRODUCT_WEIGHT_SUM_VALID_TOL
    needs_full_product_reselection = bool(
        (not product_weight_sum_valid)
        or product_dr["needs_selection_rerun_assets"]
    )
    valid_product_level_portfolio = (
        product_weight_sum_valid and not needs_full_product_reselection
    )
    implementation_ready = bool(
        valid_product_level_portfolio
        and not product_dr["needs_selection_rerun_assets"]
    )

    payload: dict[str, Any] = {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "operating_mode": operating_mode,
            "production_applied": False,
            "dry_run_only": True,
            "manager_override_saa_layer": True,
            "sign_off_required_for_production": True,
            # R-1F.2.1 — validity flags
            "valid_asset_level_dry_run": True,
            "valid_product_level_portfolio": valid_product_level_portfolio,
            "product_weight_sum_valid": product_weight_sum_valid,
            "needs_full_product_reselection": needs_full_product_reselection,
            "implementation_ready": implementation_ready,
            "product_allocation_method": "baseline_proportional_scaling",
            "scope": (
                "R-1F.2 (downstream dry-run wiring: TAA + projection asset-level + "
                "product allocation proportional scaling; baseline / production untouched)"
            ),
            "portfolio_type": portfolio_type,
        },
        "source_manager_selected_saa_json": {
            "path": str(manager_dump_path),
            "sha256": _sha256_file(Path(manager_dump_path)) if Path(manager_dump_path).exists() else None,
        },
        "baseline_portfolio_json": {
            "path": str(baseline_path),
            "sha256": _sha256_file(Path(baseline_path)) if Path(baseline_path).exists() else None,
        },
        "selected_candidate_id": sc["candidate_id"],
        "selected_candidate_weights": dict(sc["weights"]),
        "manager_override_saa": {
            "weights": dict(sc["weights"]),
            "expected_return": sc.get("expected_return"),
            "volatility": sc.get("volatility"),
            "sharpe": sc.get("sharpe"),
            "concentration_hhi": sc.get("concentration_hhi"),
            "equity_intra_hhi": sc.get("equity_intra_hhi"),
            "fixed_income_intra_hhi": sc.get("fixed_income_intra_hhi"),
            "max_asset_weight": sc.get("max_asset_weight"),
        },
        "baseline_max_sharpe_saa": {
            "weights": dict(base_saa),
        },
        "regime_used": {
            "regime": asset_dr["regime"],
            "regime_label": asset_dr["regime_label"],
        },
        "asset_allocation_dry_run": asset_dr["asset_allocation_dry_run"],
        "asset_weights_dry_run": dict(asset_dr["taa_after_projection_weights"]),
        "asset_weights_baseline": dict(base_asset_weights),
        "bucket_sums_after_projection": asset_dr["bucket_sums_after_projection"],
        "max_abs_projection_drift_dry_run": asset_dr["max_abs_projection_drift"],
        "max_abs_projection_drift_baseline": base_drift,
        "taa_diagnostics_dry_run": asset_dr["taa_diagnostics"],
        "product_allocation_dry_run": product_dr["product_allocation_dry_run"],
        "product_weight_sum_dry_run": product_dr["product_weight_sum_dry_run"],
        "needs_selection_rerun_assets": product_dr["needs_selection_rerun_assets"],
        "product_allocation_limitation": (
            "baseline zero-weight assets cannot be reallocated by proportional "
            "scaling. " + product_dr["limitation"]
        ),
        "comparison_to_baseline_available": True,
        "notes": [
            "manager_override_saa is a SEPARATE LAYER; existing SAA telemetry "
            "(`saa_diagnostics.saa_weights`) is preserved in baseline portfolio JSON.",
            "production_applied=false; this dry-run does NOT modify any production "
            "directory or baseline output.",
            "This dry-run is valid at the ASSET ALLOCATION level only. "
            "Product allocation is approximate (proportional scaling) and not "
            "portfolio-valid because product_weight_sum_dry_run "
            f"({product_sum:.4f}) deviates from 1.0 by more than the validity "
            f"tolerance ({PRODUCT_WEIGHT_SUM_VALID_TOL}).",
            "Full product re-selection (R-1G or equivalent universe + scoring "
            "+ selection re-run) is REQUIRED before manager review for "
            "implementation. implementation_ready=false until then.",
            "automated candidate recommendation is forbidden; this dry-run only consumes "
            "an explicit manager-provided selection.",
        ],
    }
    return payload


def write_dry_run_portfolio_json(payload: dict[str, Any], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return out_path


# ---------------------------------------------------------------------------
# Comparison markdown
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


def render_comparison_md(
    dry_payload: dict[str, Any],
    baseline: dict[str, Any],
    out_path: Path,
) -> Path:
    out_path = Path(out_path)
    portfolio_type = dry_payload["meta"]["portfolio_type"]
    sc_id = dry_payload["selected_candidate_id"]
    override = dry_payload["manager_override_saa"]
    base_saa = dry_payload["baseline_max_sharpe_saa"]["weights"]
    asset_dry = dry_payload["asset_weights_dry_run"]
    asset_base = dry_payload["asset_weights_baseline"]

    lines: list[str] = []
    lines.append(
        f"# Manager-Selected SAA Dry-Run Comparison ({portfolio_type.upper()}, R-1F.2)"
    )
    lines.append("")
    lines.append(f"> schema_version: {SCHEMA_VERSION}")
    lines.append("> Read-only dry-run. `production_applied=false`, `dry_run_only=true`.")
    lines.append("> Baseline portfolio JSON / production directory **변경 0**.")
    lines.append("")
    # R-1F.2.1 — explicit warning at top
    meta = dry_payload["meta"]
    product_sum = float(dry_payload["product_weight_sum_dry_run"])
    lines.append("## ⚠ Validity Warning (R-1F.2.1)")
    lines.append("")
    lines.append(
        f"- **valid_asset_level_dry_run = {str(meta['valid_asset_level_dry_run']).lower()}** "
        f"— TAA + projection at the asset allocation level is reviewable."
    )
    lines.append(
        f"- **valid_product_level_portfolio = "
        f"{str(meta['valid_product_level_portfolio']).lower()}**, "
        f"**product_weight_sum_valid = "
        f"{str(meta['product_weight_sum_valid']).lower()}** "
        f"(product_weight_sum_dry_run = {product_sum:.4f}, expected ≈ 1.0)."
    )
    lines.append(
        f"- **needs_full_product_reselection = "
        f"{str(meta['needs_full_product_reselection']).lower()}**, "
        f"**implementation_ready = "
        f"{str(meta['implementation_ready']).lower()}**."
    )
    lines.append(
        f"- product_allocation_method = `{meta['product_allocation_method']}`. "
        f"Baseline zero-weight assets cannot be reallocated by this method."
    )
    nra = dry_payload.get("needs_selection_rerun_assets") or []
    if nra:
        lines.append(f"- **needs_selection_rerun_assets**: {nra}")
    lines.append("")
    lines.append(
        "> **본 결과는 asset-level TAA/projection 검토용이다.** "
        "Product allocation 은 proportional scaling approximation 이며 "
        f"product_weight_sum_dry_run = {product_sum:.4f} ≠ 1.0 이므로 "
        "**운용 가능한 최종 포트폴리오가 아니다**. Product-level manager review 전에는 "
        "**R-1G full product re-selection 이 필요**하다."
    )
    lines.append("")

    lines.append("## §1. Selected Candidate")
    lines.append("")
    lines.append(
        f"- candidate_id: **{sc_id}** "
        f"(group / shortlist 정보는 Final Manager Review Packet 참조)"
    )
    lines.append(
        f"- Sharpe: {_fmt_num(override['sharpe'])}, "
        f"E[R]: {_fmt_pct(override['expected_return'])}, "
        f"σ: {_fmt_pct(override['volatility'])}, "
        f"HHI: {_fmt_num(override['concentration_hhi'])}, "
        f"max_w: {_fmt_pct(override['max_asset_weight'])}"
    )
    base_saa_sharpe = (baseline.get("diagnostics") or {}).get("saa_diagnostics", {}).get("solver_status")
    lines.append(
        f"- baseline (max-Sharpe SAA) reference: see baseline portfolio JSON "
        f"`diagnostics.saa_diagnostics`."
    )
    lines.append("")

    lines.append("## §2. SAA-level Asset Weight Delta")
    lines.append("")
    lines.append("| asset | baseline max-Sharpe SAA | manager_override SAA | delta |")
    lines.append("|---|---:|---:|---:|")
    for k in dry_payload["asset_weights_baseline"]:
        b = float(base_saa.get(k, 0.0))
        m = float(override["weights"].get(k, 0.0))
        lines.append(
            f"| {k} | {_fmt_pct(b)} | {_fmt_pct(m)} | {_fmt_pct(m - b)} |"
        )
    lines.append("")

    lines.append("## §3. Final Asset Weight Delta (after TAA + projection)")
    lines.append("")
    lines.append("| asset | bucket | baseline final | dry-run final | delta |")
    lines.append("|---|---|---:|---:|---:|")
    rows = dry_payload["asset_allocation_dry_run"]
    for row in rows:
        k = row["asset_key"]
        base_a = float(asset_base.get(k, 0.0))
        dry_a = float(row["final_asset_weight"])
        lines.append(
            f"| {k} | {row['bucket']} | "
            f"{_fmt_pct(base_a)} | {_fmt_pct(dry_a)} | {_fmt_pct(dry_a - base_a)} |"
        )
    lines.append("")

    bucket_sums = dry_payload["bucket_sums_after_projection"]
    lines.append("## §4. Bucket Check (after projection)")
    lines.append("")
    lines.append(f"- equity sum (dry-run): **{_fmt_pct(bucket_sums['equity'])}**")
    lines.append(f"- fixed_income sum (dry-run): **{_fmt_pct(bucket_sums['fixed_income'])}**")
    lines.append(
        f"- max_abs_projection_drift: dry-run "
        f"{_fmt_pct(dry_payload['max_abs_projection_drift_dry_run'])} vs baseline "
        f"{_fmt_pct(dry_payload['max_abs_projection_drift_baseline'])}"
    )
    lines.append("")

    # Top changed assets (by |delta|)
    asset_deltas = [
        (row["asset_key"], float(row["final_asset_weight"]) - float(asset_base.get(row["asset_key"], 0.0)))
        for row in rows
    ]
    asset_deltas.sort(key=lambda t: -abs(t[1]))
    lines.append("## §5. Top Changed Assets (by |Δ final|)")
    lines.append("")
    lines.append("| # | asset | delta |")
    lines.append("|---:|---|---:|")
    for i, (k, d) in enumerate(asset_deltas[:5], 1):
        lines.append(f"| {i} | {k} | {_fmt_pct(d)} |")
    lines.append("")

    # Top product changes
    prods = sorted(
        dry_payload["product_allocation_dry_run"],
        key=lambda r: -abs(float(r["weight_delta"])),
    )
    lines.append("## §6. Top Changed Products (by |Δ final_weight|)")
    lines.append("")
    lines.append("| # | asset_key | product_name | manager | base | dry-run | delta |")
    lines.append("|---:|---|---|---|---:|---:|---:|")
    for i, r in enumerate(prods[:10], 1):
        lines.append(
            f"| {i} | {r.get('asset_key')} | {r.get('product_name')} | "
            f"{r.get('manager')} | {_fmt_pct(r.get('final_weight_baseline'))} | "
            f"{_fmt_pct(r.get('final_weight_dry_run'))} | "
            f"{_fmt_pct(r.get('weight_delta'))} |"
        )
    lines.append("")
    if dry_payload.get("needs_selection_rerun_assets"):
        lines.append("> ⚠ **Limitation**: 아래 자산은 baseline weight ≈ 0 이지만 dry-run "
                     "에서 > 0 으로 잡혀 product allocation 비례 scaling 이 불가하다.")
        lines.append("")
        lines.append(
            f"  - needs_selection_rerun_assets: "
            f"{dry_payload['needs_selection_rerun_assets']}"
        )
        lines.append("")
    lines.append(f"> {dry_payload['product_allocation_limitation']}")
    lines.append("")

    lines.append("## §7. 운용역 검토 포인트")
    lines.append("")
    lines.append(
        "- ref_max_sharpe (baseline) → manager_override 로 변경 시 어떤 자산이 가장 "
        "크게 움직였는지 (§5 참조) 정성 view 와 정합한지 확인."
    )
    lines.append(
        "- bucket 합 (§4) 이 80/20 hard constraint 를 유지하는지 — projection 적용 후."
    )
    lines.append(
        "- product 비례 scaling 결과 (§6) 는 실제 selection 결과와 다를 수 있음. "
        "baseline weight ≈ 0 자산이 dry-run 에 등장하면 selection rerun 필수 "
        "(§6 Limitation)."
    )
    lines.append(
        "- product-level manager review / implementation 전에 **R-1G full re-selection** "
        "필수 (현재 valid_product_level_portfolio=false)."
    )
    lines.append(
        "- production 반영은 본 R-1F.2 범위 밖. 별도 Phase F sign-off 필수."
    )
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


__all__ = [
    "SCHEMA_VERSION",
    "run_asset_level_dry_run",
    "run_product_level_dry_run",
    "build_dry_run_portfolio",
    "write_dry_run_portfolio_json",
    "render_comparison_md",
]
