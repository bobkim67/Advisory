"""R-1G.1 — Full Product Re-selection (selection only, no PortfolioBuilder).

Spec: tdf_2060/docs/r1g_full_product_reselection_spec.md
Scope:
- Load R-1F.1 manager_selected_saa JSON + R-1F.2 dry-run JSON
- Use R-1F.2 `asset_weights_dry_run` as target asset weights (default)
- Re-run ProductSelectionTool.run(target_asset_weights) — core 무수정
- Dump product re-selection JSON + summary md to **separate output dir**
- PortfolioBuilder 연결은 R-1G.2 로 분리

Hard requirements:
- production_applied = false / dry_run_only = true / manager_override_saa_layer = true
- implementation_ready = false (강제) + implementation_review_status = "review_required"
- 80:20 distance metric 부활 금지 (R-1B.2 정합)
- 기존 production / baseline / R-1F.* / E-series 산출물 무변경
- selection core 무수정
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tdf_engine.config.loader import ConfigLoader
from tdf_engine.domain.enums import ProductType
from tdf_engine.repositories.file_repositories import FileProductRepository
from tdf_engine.selection.tool import ProductSelectionTool
from tdf_engine.universe.classifier import ProductClassifier, load_rules
from tdf_engine.universe.tool import UniverseTool


SCHEMA_VERSION = "r1g1.1"
PRODUCT_WEIGHT_SUM_VALID_TOL = 1e-3

REMOVED_METRIC_KEYS = (
    "bucket_distance_from_80_20",
    "full_weight_distance_from_80_20_equal_bucket_reference",
)

# Allowed target sources
TARGET_SOURCE_PROJECTION = "projection_final_asset_weights"
TARGET_SOURCE_MANAGER_OVERRIDE = "manager_override_saa"
TARGET_SOURCE_TAA_PRE_PROJECTION = "taa_overlay_pre_projection"

# Internal label used in JSON (more explicit)
TARGET_SOURCE_LABEL_PROJECTION = "r1f2_projection_final_asset_weights"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Pre-execution validation (re-check from R-1F.1 / R-1F.2 dumps)
# ---------------------------------------------------------------------------


def _ensure_manager_dump_eligible(
    manager_dump: dict[str, Any],
    *,
    operating_mode: str,
) -> None:
    meta = manager_dump.get("meta") or {}
    if meta.get("production_applied") is not False:
        raise ValueError(
            "R-1G.1 pre-check: manager_selected_saa.meta.production_applied must be False."
        )
    if meta.get("manager_override_saa_layer") is not True:
        raise ValueError(
            "R-1G.1 pre-check: manager_override_saa_layer must be True."
        )
    if manager_dump.get("downstream_dry_run_allowed") is not True:
        raise ValueError(
            "R-1G.1 pre-check: downstream_dry_run_allowed must be True."
        )
    if str(meta.get("operating_mode") or "") != "relaxed_diagnostic":
        raise ValueError(
            "R-1G.1 pre-check: manager_selected_saa operating_mode must be "
            "'relaxed_diagnostic'."
        )
    if operating_mode != "relaxed_diagnostic":
        raise ValueError(
            f"R-1G.1 dry-run forbidden in operating_mode={operating_mode!r}."
        )
    sc = manager_dump.get("selected_candidate") or {}
    cid = str(sc.get("candidate_id") or "")
    if not cid.startswith("cand_"):
        raise ValueError(
            f"R-1G.1 pre-check: selected_candidate_id must be sampled; got {cid!r}."
        )
    if sc.get("feasibility_status") != "feasible":
        raise ValueError(
            "R-1G.1 pre-check: selected_candidate.feasibility_status must be 'feasible'."
        )
    for k in REMOVED_METRIC_KEYS:
        if k in sc:
            raise ValueError(
                f"R-1G.1 pre-check: removed metric {k!r} resurrected — schema regression."
            )


def _ensure_r1f2_dump_eligible(r1f2_dump: dict[str, Any]) -> None:
    meta = r1f2_dump.get("meta") or {}
    if meta.get("production_applied") is not False:
        raise ValueError("R-1G.1 pre-check: r1f2_dump.meta.production_applied must be False.")
    if meta.get("dry_run_only") is not True:
        raise ValueError("R-1G.1 pre-check: r1f2_dump.meta.dry_run_only must be True.")
    if meta.get("valid_asset_level_dry_run") is not True:
        raise ValueError(
            "R-1G.1 pre-check: r1f2_dump.meta.valid_asset_level_dry_run must be True."
        )
    if "asset_weights_dry_run" not in r1f2_dump:
        raise ValueError(
            "R-1G.1 pre-check: r1f2_dump.asset_weights_dry_run is required."
        )


# ---------------------------------------------------------------------------
# Target weights resolution
# ---------------------------------------------------------------------------


def _resolve_target_weights(
    manager_dump: dict[str, Any],
    r1f2_dump: dict[str, Any],
    *,
    target_source: str,
) -> tuple[dict[str, float], str]:
    """Returns (weights_dict, source_label)."""
    if target_source == TARGET_SOURCE_PROJECTION:
        w = r1f2_dump.get("asset_weights_dry_run") or {}
        return ({str(k): float(v) for k, v in w.items()},
                TARGET_SOURCE_LABEL_PROJECTION)
    if target_source == TARGET_SOURCE_TAA_PRE_PROJECTION:
        w = (r1f2_dump.get("taa_target_weights") or {})
        return ({str(k): float(v) for k, v in w.items()},
                "r1f2_taa_overlay_pre_projection")
    if target_source == TARGET_SOURCE_MANAGER_OVERRIDE:
        w = ((manager_dump.get("selected_candidate") or {}).get("weights") or {})
        return ({str(k): float(v) for k, v in w.items()},
                "manager_selected_saa.selected_candidate.weights")
    raise ValueError(
        f"R-1G.1: unknown target_source={target_source!r}. "
        f"Allowed: {TARGET_SOURCE_PROJECTION}, {TARGET_SOURCE_MANAGER_OVERRIDE}, "
        f"{TARGET_SOURCE_TAA_PRE_PROJECTION}."
    )


# ---------------------------------------------------------------------------
# Universe re-construction (file-based by default; baseline used FileProductRepository)
# ---------------------------------------------------------------------------


def build_universe(
    source_root: Path,
    config_dir: Path,
    product_type: ProductType,
):
    """Re-run UniverseTool using file-based ProductRepository.

    baseline production wiring 과 동일 (build_portfolio.py 의 product_repo =
    FileProductRepository(source_root)). DB 의존 없음.
    """
    loader = ConfigLoader(Path(config_dir))
    universe_config = loader.load_universe_config()
    raw_rules = loader.load_classification_rules_raw()
    classifier = ProductClassifier(load_rules(raw_rules))
    product_repo = FileProductRepository(Path(source_root))
    universe_tool = UniverseTool(
        product_repo, universe_config, product_type, classifier=classifier,
    )
    return universe_tool.run(), universe_config


# ---------------------------------------------------------------------------
# R-1G.1 main builder
# ---------------------------------------------------------------------------


def build_product_reselection(
    manager_dump: dict[str, Any],
    r1f2_dump: dict[str, Any],
    *,
    source_root: Path,
    config_dir: Path,
    manager_dump_path: Path,
    r1f2_dump_path: Path,
    baseline_portfolio_path: Path | None = None,
    target_source: str = TARGET_SOURCE_PROJECTION,
    selection_as_of: str = "",
    output_as_of: str = "",
    universe_as_of: str = "",
    baseline_portfolio_as_of: str = "",
    operating_mode: str = "relaxed_diagnostic",
) -> dict[str, Any]:
    """Re-run product selection only. PortfolioBuilder 연결은 R-1G.2."""
    import pandas as pd

    _ensure_manager_dump_eligible(manager_dump, operating_mode=operating_mode)
    _ensure_r1f2_dump_eligible(r1f2_dump)

    portfolio_type = str((manager_dump.get("selection_input") or {}).get("portfolio_type") or "")
    if portfolio_type not in ("etf", "fund"):
        raise ValueError(
            f"R-1G.1: invalid portfolio_type={portfolio_type!r}."
        )
    ptype = ProductType(portfolio_type)

    target_weights, target_source_label = _resolve_target_weights(
        manager_dump, r1f2_dump, target_source=target_source,
    )

    # Build universe (file-based)
    universe_result, universe_config = build_universe(
        Path(source_root), Path(config_dir), ptype,
    )

    # Run selection — core unchanged
    asset_keys = list(target_weights.keys())
    series = pd.Series({k: float(target_weights[k]) for k in asset_keys}, name="target_asset_weights")
    selection_tool = ProductSelectionTool(universe_result, universe_config, ptype)
    selection = selection_tool.run(series)

    # Aggregate by asset
    sel_df = selection.selected  # columns: asset_key, product_id, ..., weight, role
    if not sel_df.empty:
        allocated_by_asset = sel_df.groupby("asset_key")["weight"].sum().to_dict()
        count_by_asset = sel_df.groupby("asset_key").size().to_dict()
    else:
        allocated_by_asset = {}
        count_by_asset = {}

    classified_by_asset = (
        universe_result.diagnostics.get("classified_by_asset_class") or {}
    )

    selection_rows: list[dict[str, Any]] = []
    for _, row in sel_df.iterrows():
        selection_rows.append({
            "asset_key": str(row["asset_key"]),
            "product_id": str(row["product_id"]),
            "fund_code": (None if row.get("fund_code") in (None, "") else str(row["fund_code"])),
            "product_name": str(row.get("name") or ""),
            "manager": str(row.get("manager") or ""),
            "kis_asset_class": str(row.get("kis_asset_class") or ""),
            "sub_type": str(row.get("sub_type") or ""),
            "weight": float(row["weight"]),
            "role": str(row["role"]),
        })

    selected_weight_sum = sum(r["weight"] for r in selection_rows)
    target_weight_sum = sum(float(v) for v in target_weights.values())

    # Per-asset summary
    asset_summary: list[dict[str, Any]] = []
    unresolved_assets: list[str] = []
    universe_short_warnings: list[str] = []
    for ak in asset_keys:
        tgt = float(target_weights[ak])
        alloc = float(allocated_by_asset.get(ak, 0.0))
        n_uni = int(classified_by_asset.get(ak, 0))
        n_sel = int(count_by_asset.get(ak, 0))
        unfilled = tgt - alloc if tgt > 0 else 0.0
        asset_summary.append({
            "asset_key": ak,
            "target_weight": tgt,
            "allocated_weight": alloc,
            "unfilled_weight": unfilled,
            "n_universe": n_uni,
            "n_selected": n_sel,
        })
        if tgt > 1e-6 and n_uni == 0:
            unresolved_assets.append(ak)
        if tgt > 1e-6 and 0 < n_uni < 3:
            universe_short_warnings.append(
                f"asset {ak!r}: universe count {n_uni} < target n_core+n_satellite (3); "
                "core/satellite picks may be incomplete (fallback handled by R-1G.2 builder)."
            )

    # Validity flags
    product_weight_sum_valid = (
        abs(selected_weight_sum - target_weight_sum) <= PRODUCT_WEIGHT_SUM_VALID_TOL
    )
    # 모든 target>0 asset 이 universe 보유 + n_selected ≥ 1
    coverage_ok = all(
        (s["target_weight"] <= 1e-6) or (s["n_universe"] > 0 and s["n_selected"] >= 1)
        for s in asset_summary
    )
    all_weights_nonneg = all(r["weight"] >= -1e-12 for r in selection_rows)

    valid_product_level_portfolio = bool(
        product_weight_sum_valid and coverage_ok and all_weights_nonneg
        and not unresolved_assets
    )
    needs_full_product_reselection = not valid_product_level_portfolio

    payload: dict[str, Any] = {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "operating_mode": operating_mode,
            "production_applied": False,
            "dry_run_only": True,
            "manager_override_saa_layer": True,
            "product_allocation_method": "full_reselection",
            "target_weight_source": target_source_label,
            # as_of_date separation (R-1G.0 §3.5 / B-8)
            "selection_as_of": str(selection_as_of or ""),
            "baseline_portfolio_as_of": str(baseline_portfolio_as_of or ""),
            "universe_as_of": str(universe_as_of or ""),
            "output_as_of": str(output_as_of or ""),
            # validity flags
            "valid_asset_level_dry_run": True,
            "valid_product_level_portfolio": valid_product_level_portfolio,
            "product_weight_sum_valid": product_weight_sum_valid,
            "needs_full_product_reselection": needs_full_product_reselection,
            "implementation_ready": False,                # strict — never True at R-1G.1
            "implementation_review_status": "review_required",
            "sign_off_required_for_production": True,
            "scope": (
                "R-1G.1 (product re-selection only; PortfolioBuilder wiring deferred "
                "to R-1G.2)"
            ),
            "portfolio_type": portfolio_type,
        },
        "source_manager_selected_saa_json": {
            "path": str(manager_dump_path),
            "sha256": (
                _sha256_file(Path(manager_dump_path))
                if Path(manager_dump_path).exists() else None
            ),
        },
        "source_r1f2_dry_run_json": {
            "path": str(r1f2_dump_path),
            "sha256": (
                _sha256_file(Path(r1f2_dump_path))
                if Path(r1f2_dump_path).exists() else None
            ),
        },
        "baseline_portfolio_json": (
            {
                "path": str(baseline_portfolio_path),
                "sha256": (
                    _sha256_file(Path(baseline_portfolio_path))
                    if Path(baseline_portfolio_path).exists() else None
                ),
            }
            if baseline_portfolio_path is not None else None
        ),
        "selected_candidate_id": (manager_dump.get("selected_candidate") or {}).get("candidate_id"),
        "target_asset_weights": {k: float(v) for k, v in target_weights.items()},
        "target_weight_sum": float(target_weight_sum),
        "universe_source": {
            "type": "file",
            "source_root": str(source_root),
            "product_type": portfolio_type,
            "raw_count": universe_result.raw_count,
            "filtered_count": universe_result.filtered_count,
            "classified_by_asset_class": dict(classified_by_asset),
        },
        "selected_products": selection_rows,
        "selected_weight_sum": float(selected_weight_sum),
        "product_count": len(selection_rows),
        "asset_summary": asset_summary,
        "selection_diagnostics": selection.diagnostics,
        "warnings": list(universe_short_warnings),
        "unresolved_assets": unresolved_assets,
        "needs_selection_rerun_assets": list(unresolved_assets),
        "notes": [
            "R-1G.1 performs product re-selection ONLY. PortfolioBuilder wiring "
            "(fallback / drift clipping / quality validation) is deferred to R-1G.2.",
            "implementation_ready=false and implementation_review_status="
            "'review_required' are STRICT — never auto-promote to true.",
            "manager_override_saa is a SEPARATE LAYER from existing SAA telemetry "
            "(`saa_diagnostics.saa_weights`).",
            "automated candidate recommendation is forbidden.",
        ],
    }
    return payload


def write_product_reselection_json(payload: dict[str, Any], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return out_path


# ---------------------------------------------------------------------------
# Summary markdown
# ---------------------------------------------------------------------------


def _fmt_pct(v: Any) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "n/a"
    return f"{f * 100:.2f}%"


def render_product_reselection_summary_md(
    payload: dict[str, Any],
    out_path: Path,
) -> Path:
    out_path = Path(out_path)
    portfolio_type = payload["meta"]["portfolio_type"]
    sc_id = payload.get("selected_candidate_id")
    meta = payload["meta"]
    target = payload["target_asset_weights"]
    asset_summary = payload["asset_summary"]
    selection_rows = payload["selected_products"]

    lines: list[str] = []
    lines.append(
        f"# Manager-Selected SAA Product Re-selection Summary ({portfolio_type.upper()}, R-1G.1)"
    )
    lines.append("")
    lines.append(f"> schema_version: {SCHEMA_VERSION}")
    lines.append("> Read-only product re-selection. PortfolioBuilder 연결은 R-1G.2.")
    lines.append("> `production_applied=false`, `dry_run_only=true`, "
                 "`implementation_ready=false`.")
    lines.append("")

    # Validity warning
    lines.append("## ⚠ Validity Summary (R-1G.1)")
    lines.append("")
    lines.append(
        f"- **valid_asset_level_dry_run = {str(meta['valid_asset_level_dry_run']).lower()}**"
    )
    lines.append(
        f"- **valid_product_level_portfolio = "
        f"{str(meta['valid_product_level_portfolio']).lower()}**, "
        f"**product_weight_sum_valid = "
        f"{str(meta['product_weight_sum_valid']).lower()}** "
        f"(selected_weight_sum = {payload['selected_weight_sum']:.4f}, "
        f"target_weight_sum = {payload['target_weight_sum']:.4f})"
    )
    lines.append(
        f"- **needs_full_product_reselection = "
        f"{str(meta['needs_full_product_reselection']).lower()}**"
    )
    lines.append(
        f"- **implementation_ready = {str(meta['implementation_ready']).lower()}**, "
        f"**implementation_review_status = `{meta['implementation_review_status']}`**"
    )
    lines.append(
        f"- product_allocation_method = `{meta['product_allocation_method']}`"
    )
    lines.append(
        f"- target_weight_source = `{meta['target_weight_source']}`"
    )
    if payload["unresolved_assets"]:
        lines.append(
            f"- **unresolved_assets** (universe missing or zero picks): "
            f"{payload['unresolved_assets']}"
        )
    if payload["warnings"]:
        lines.append("- universe coverage warnings:")
        for w in payload["warnings"]:
            lines.append(f"  - {w}")
    lines.append("")

    # As-of separation
    lines.append("## §1. As-of date separation")
    lines.append("")
    lines.append(f"- selection_as_of: **{meta['selection_as_of'] or 'n/a'}**")
    lines.append(f"- output_as_of: **{meta['output_as_of'] or 'n/a'}**")
    lines.append(f"- baseline_portfolio_as_of: **{meta['baseline_portfolio_as_of'] or 'n/a'}**")
    lines.append(f"- universe_as_of: **{meta['universe_as_of'] or 'n/a'}**")
    lines.append("")

    # Selected candidate
    lines.append("## §2. Selected Candidate")
    lines.append("")
    lines.append(
        f"- candidate_id: **{sc_id}** (see Final Manager Review Packet for context)"
    )
    lines.append("")

    # Target asset weights
    lines.append("## §3. Target Asset Weights (= R-1F.2 projection final)")
    lines.append("")
    lines.append("| asset | target weight |")
    lines.append("|---|---:|")
    for k, v in target.items():
        lines.append(f"| {k} | {_fmt_pct(v)} |")
    lines.append(f"| **sum** | **{_fmt_pct(payload['target_weight_sum'])}** |")
    lines.append("")

    # Per-asset summary
    lines.append("## §4. Per-asset Selection Summary")
    lines.append("")
    lines.append("| asset | target | allocated | unfilled | n_universe | n_selected |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for s in asset_summary:
        lines.append(
            f"| {s['asset_key']} "
            f"| {_fmt_pct(s['target_weight'])} "
            f"| {_fmt_pct(s['allocated_weight'])} "
            f"| {_fmt_pct(s['unfilled_weight'])} "
            f"| {s['n_universe']} "
            f"| {s['n_selected']} |"
        )
    lines.append(
        f"| **total** | **{_fmt_pct(payload['target_weight_sum'])}** "
        f"| **{_fmt_pct(payload['selected_weight_sum'])}** "
        f"| **{_fmt_pct(payload['target_weight_sum'] - payload['selected_weight_sum'])}** "
        f"| — | **{payload['product_count']}** |"
    )
    lines.append("")

    # Selected products table
    lines.append("## §5. Selected Products")
    lines.append("")
    lines.append("| asset | product_id | product_name | manager | role | weight |")
    lines.append("|---|---|---|---|---|---:|")
    for r in selection_rows:
        lines.append(
            f"| {r['asset_key']} "
            f"| {r['product_id']} "
            f"| {r['product_name']} "
            f"| {r['manager']} "
            f"| {r['role']} "
            f"| {_fmt_pct(r['weight'])} |"
        )
    lines.append("")

    # Universe context
    uni = payload["universe_source"]
    lines.append("## §6. Universe Coverage")
    lines.append("")
    lines.append(f"- source type: `{uni['type']}`")
    lines.append(f"- product_type: `{uni['product_type']}`")
    lines.append(
        f"- raw_count: {uni['raw_count']}, filtered_count: {uni['filtered_count']}"
    )
    lines.append("")
    lines.append("| asset | universe count |")
    lines.append("|---|---:|")
    for ak, cnt in uni["classified_by_asset_class"].items():
        lines.append(f"| {ak} | {cnt} |")
    lines.append("")

    # Limitations
    lines.append("## §7. Limitations / Next Step")
    lines.append("")
    lines.append(
        "- R-1G.1 은 **product re-selection only**. "
        "PortfolioBuilder fallback / drift clipping / quality validation 미적용. "
        "R-1G.2 에서 builder 연결 후 3-way (baseline / R-1F.2 / R-1G) 비교 진행."
    )
    if not meta["valid_product_level_portfolio"]:
        lines.append(
            "- `valid_product_level_portfolio = false` — "
            "selection 단계만으로 sum=1.0 또는 모든 자산 cover 달성 못 함. "
            "R-1G.2 builder 의 fallback / drift clipping 이 잔여 weight 흡수해야 함."
        )
    lines.append(
        "- production 반영은 본 R-1G.1 범위 밖. 별도 Phase F sign-off 필수."
    )
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


__all__ = [
    "SCHEMA_VERSION",
    "TARGET_SOURCE_PROJECTION",
    "TARGET_SOURCE_MANAGER_OVERRIDE",
    "TARGET_SOURCE_TAA_PRE_PROJECTION",
    "build_universe",
    "build_product_reselection",
    "write_product_reselection_json",
    "render_product_reselection_summary_md",
]
