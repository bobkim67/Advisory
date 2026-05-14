"""R-1G.2 — PortfolioBuilder wiring + 3-way comparison (dry-run).

Spec: tdf_2060/docs/r1g_full_product_reselection_spec.md
Scope:
- Reuse R-1G.1 universe + selection logic
- Adapt TAAResult with target asset weights (= R-1F.2 projection final weights)
- Call PortfolioBuilder.build() — core 무수정
- Generate dry-run portfolio JSON + 3-way comparison md (baseline / R-1F.2 / R-1G.2)

Hard requirements (per R-1G.0 §11 / user's R-1G.2 directive):
- production_applied = false / dry_run_only = true / manager_override_saa_layer = true
- portfolio_builder_applied = true
- implementation_ready = false (STRICT)
- implementation_review_status = "review_required"
- 80:20 distance metric 부활 금지
- production / baseline / R-1B.2 ~ R-1G.1 산출물 무변경
- TAA / projection / selection / PortfolioBuilder core 무수정
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tdf_engine.config.loader import ConfigLoader
from tdf_engine.domain.enums import ProductType
from tdf_engine.domain.models import TAAResult
from tdf_engine.optimization.product_reselection_dry_run import (
    TARGET_SOURCE_LABEL_PROJECTION,
    TARGET_SOURCE_MANAGER_OVERRIDE,
    TARGET_SOURCE_PROJECTION,
    TARGET_SOURCE_TAA_PRE_PROJECTION,
    _ensure_manager_dump_eligible,
    _ensure_r1f2_dump_eligible,
    _resolve_target_weights,
    build_universe,
)
from tdf_engine.portfolio.builder import PortfolioBuilder
from tdf_engine.portfolio.quality import (
    DEFAULT_ASSET_DRIFT_THRESHOLD,
    DEFAULT_BUCKET_DRIFT_THRESHOLD,
    ENFORCEMENT_PRODUCTION,
)
from tdf_engine.selection.tool import ProductSelectionTool


SCHEMA_VERSION = "r1g2.1"
PRODUCT_WEIGHT_SUM_VALID_TOL = 1e-6  # builder fallback 후엔 거의 정확히 1.0


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# TAAResult adapter
# ---------------------------------------------------------------------------


def _make_taa_adapter(target_weights: dict[str, float], source_label: str) -> TAAResult:
    """Build a synthetic TAAResult that injects target weights at the TAA seam.

    saa_weights = taa_weights = target (no further tilts at this stage; tilts
    have already been applied in R-1F.2). diagnostics 에는 r1g_target_substitute
    명시 — 후속 분석이 본 결과가 production max-Sharpe SAA 와 다르다는 점을
    추적 가능하도록.
    """
    import pandas as pd

    keys = list(target_weights.keys())
    saa_series = pd.Series(
        {k: float(target_weights[k]) for k in keys}, name="saa_weights",
    )
    taa_series = pd.Series(
        {k: float(target_weights[k]) for k in keys}, name="taa_weights",
    )
    tilts = pd.Series(0.0, index=keys, name="tilts")
    diagnostics = {
        "method": "r1g_target_substitute",
        "source_label": source_label,
        "notes": [
            "saa_weights / taa_weights here are the R-1G target asset weights "
            "(default = R-1F.2 projection final). NOT the production max-Sharpe "
            "SAA telemetry. Existing baseline saa_diagnostics.saa_weights is "
            "preserved separately.",
        ],
        "regime": None,  # builder 가 직접 사용하지 않음
    }
    return TAAResult(
        saa_weights=saa_series,
        taa_weights=taa_series,
        tilts=tilts,
        reasons={},
        diagnostics=diagnostics,
    )


# ---------------------------------------------------------------------------
# Drift thresholds helper (mode-aware, mirror of build_portfolio path)
# ---------------------------------------------------------------------------


def _resolve_drift_thresholds(tdf_config: dict, operating_mode: str) -> dict[str, Any]:
    drift_cfg = tdf_config.get("drift_thresholds") or {}
    modes_cfg = drift_cfg.get("modes") or {}
    mode_specific = modes_cfg.get(operating_mode) or {}
    enforcement = str(
        mode_specific.get("enforcement")
        or drift_cfg.get("enforcement")
        or ENFORCEMENT_PRODUCTION
    ).strip().lower()
    asset_thr = float(
        mode_specific.get("asset")
        or drift_cfg.get("asset")
        or DEFAULT_ASSET_DRIFT_THRESHOLD
    )
    bucket_thr = float(
        mode_specific.get("bucket")
        or drift_cfg.get("bucket")
        or DEFAULT_BUCKET_DRIFT_THRESHOLD
    )
    return {
        "enforcement": enforcement,
        "asset_drift_threshold": asset_thr,
        "bucket_drift_threshold": bucket_thr,
    }


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------


def build_r1g2_portfolio(
    manager_dump: dict[str, Any],
    r1f2_dump: dict[str, Any],
    baseline_portfolio: dict[str, Any],
    *,
    source_root: Path,
    config_dir: Path,
    manager_dump_path: Path,
    r1f2_dump_path: Path,
    baseline_portfolio_path: Path,
    r1g1_reselection_path: Path | None = None,
    target_source: str = TARGET_SOURCE_PROJECTION,
    selection_as_of: str = "",
    output_as_of: str = "",
    universe_as_of: str = "",
    baseline_portfolio_as_of: str = "",
    operating_mode: str = "relaxed_diagnostic",
) -> dict[str, Any]:
    """End-to-end R-1G.2 dry-run portfolio assembly."""
    import pandas as pd

    # --- 1. Validate ---------------------------------------------------
    _ensure_manager_dump_eligible(manager_dump, operating_mode=operating_mode)
    _ensure_r1f2_dump_eligible(r1f2_dump)

    portfolio_type = str(
        (manager_dump.get("selection_input") or {}).get("portfolio_type") or ""
    )
    if portfolio_type not in ("etf", "fund"):
        raise ValueError(f"R-1G.2: invalid portfolio_type={portfolio_type!r}.")
    ptype = ProductType(portfolio_type)

    target_weights, target_source_label = _resolve_target_weights(
        manager_dump, r1f2_dump, target_source=target_source,
    )

    # --- 2. Universe + selection (re-run; R-1G.1 logic reused) ---------
    universe_result, universe_config = build_universe(
        Path(source_root), Path(config_dir), ptype,
    )

    loader = ConfigLoader(Path(config_dir))
    tdf_config = loader.load_tdf_config()
    assets = loader.load_assets()
    drift_pkg = _resolve_drift_thresholds(tdf_config, operating_mode)

    asset_keys = list(target_weights.keys())
    target_series = pd.Series(
        {k: float(target_weights[k]) for k in asset_keys}, name="target_asset_weights",
    )

    selection_tool = ProductSelectionTool(universe_result, universe_config, ptype)
    selection = selection_tool.run(target_series)

    # --- 3. Adapter TAAResult ----------------------------------------
    taa = _make_taa_adapter(target_weights, target_source_label)

    # --- 4. PortfolioBuilder.build ----------------------------------
    type_block = universe_config.get(ptype.value, {}) or {}
    pc = type_block.get("product_constraints", {}) or {}
    single_product_cap = float(pc.get("single_product_max_weight", 1.0))

    portfolio = PortfolioBuilder.build(
        taa,
        selection,
        ptype,
        assets=assets,
        single_product_max_weight=single_product_cap,
        asset_drift_threshold=drift_pkg["asset_drift_threshold"],
        bucket_drift_threshold=drift_pkg["bucket_drift_threshold"],
        enforcement=drift_pkg["enforcement"],
    )

    # --- 5. Convert PortfolioResult to JSON shape -------------------
    product_df = portfolio.product_weights
    product_rows: list[dict[str, Any]] = []
    if not product_df.empty:
        for _, r in product_df.iterrows():
            product_rows.append({
                "asset_key": str(r["asset_key"]),
                "product_id": str(r.get("product_id") or ""),
                "fund_code": (
                    None if r.get("fund_code") in (None, "") else str(r["fund_code"])
                ),
                "product_name": str(r.get("name") or ""),
                "manager": str(r.get("manager") or ""),
                "role": str(r.get("role") or ""),
                "weight": float(r["weight"]),
                "warning_flags": (
                    list(r["warning_flags"])
                    if "warning_flags" in r and r["warning_flags"] is not None
                    else []
                ),
            })

    # Per-asset allocated weight
    allocated_by_asset: dict[str, float] = {}
    selected_count_by_asset: dict[str, int] = {}
    for r in product_rows:
        ak = r["asset_key"]
        allocated_by_asset[ak] = allocated_by_asset.get(ak, 0.0) + float(r["weight"])
        selected_count_by_asset[ak] = selected_count_by_asset.get(ak, 0) + 1

    asset_weights_final = (
        portfolio.asset_weights if isinstance(portfolio.asset_weights, pd.Series)
        else pd.Series(portfolio.asset_weights)
    )
    final_asset_weights = {
        str(k): float(v) for k, v in asset_weights_final.items()
    }

    product_weight_sum = float(
        portfolio.diagnostics.get("product_weight_sum") or 0.0
    )

    # --- 6. Validity flags ----------------------------------------------
    target_sum = sum(float(v) for v in target_weights.values())
    product_weight_sum_valid = (
        abs(product_weight_sum - 1.0) <= PRODUCT_WEIGHT_SUM_VALID_TOL
    )
    coverage_ok = all(
        (float(target_weights[k]) <= 1e-6)
        or (selected_count_by_asset.get(k, 0) >= 1)
        for k in asset_keys
    )
    unresolved_assets = [
        k for k in asset_keys
        if float(target_weights[k]) > 1e-6 and selected_count_by_asset.get(k, 0) == 0
    ]
    all_weights_nonneg = all(float(r["weight"]) >= -1e-12 for r in product_rows)
    valid_product_level_portfolio = bool(
        product_weight_sum_valid and coverage_ok and all_weights_nonneg
        and not unresolved_assets
    )

    # --- 7. Comparison snapshot vs baseline / R-1F.2 ------------------
    base_asset_w = dict(baseline_portfolio.get("asset_weights") or {})
    base_product_rows = baseline_portfolio.get("product_allocation") or []
    base_product_sum = float(baseline_portfolio.get("product_weight_sum") or 0.0)
    base_n_products = len(base_product_rows)

    r1f2_asset_w = dict(r1f2_dump.get("asset_weights_dry_run") or {})
    r1f2_product_sum = float(r1f2_dump.get("product_weight_sum_dry_run") or 0.0)
    r1f2_product_rows = r1f2_dump.get("product_allocation_dry_run") or []
    r1f2_n_products = len(r1f2_product_rows)
    r1f2_needs_rerun = r1f2_dump.get("needs_selection_rerun_assets") or []

    payload: dict[str, Any] = {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "operating_mode": operating_mode,
            "production_applied": False,
            "dry_run_only": True,
            "manager_override_saa_layer": True,
            "product_allocation_method": "full_reselection",
            "portfolio_builder_applied": True,
            "target_weight_source": target_source_label,
            "selection_as_of": str(selection_as_of or ""),
            "baseline_portfolio_as_of": str(baseline_portfolio_as_of or ""),
            "universe_as_of": str(universe_as_of or ""),
            "output_as_of": str(output_as_of or ""),
            # validity flags
            "valid_asset_level_dry_run": True,
            "valid_product_level_portfolio": valid_product_level_portfolio,
            "product_weight_sum_valid": product_weight_sum_valid,
            "implementation_ready": False,             # strict
            "implementation_review_status": "review_required",
            "sign_off_required_for_production": True,
            "comparison_to_baseline_available": True,
            "comparison_to_r1f2_available": True,
            "scope": (
                "R-1G.2 (full re-selection + PortfolioBuilder; 3-way comparison)"
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
        "source_r1g1_reselection_json": (
            {
                "path": str(r1g1_reselection_path),
                "sha256": (
                    _sha256_file(Path(r1g1_reselection_path))
                    if r1g1_reselection_path
                    and Path(r1g1_reselection_path).exists() else None
                ),
            }
            if r1g1_reselection_path is not None else None
        ),
        "baseline_portfolio_json": {
            "path": str(baseline_portfolio_path),
            "sha256": (
                _sha256_file(Path(baseline_portfolio_path))
                if Path(baseline_portfolio_path).exists() else None
            ),
        },
        "selected_candidate_id": (
            (manager_dump.get("selected_candidate") or {}).get("candidate_id")
        ),
        "target_asset_weights": {k: float(v) for k, v in target_weights.items()},
        "target_weight_sum": float(target_sum),
        "final_asset_weights": final_asset_weights,
        "product_allocation": product_rows,
        "product_weight_sum": product_weight_sum,
        "product_count": len(product_rows),
        "allocated_by_asset": {k: float(v) for k, v in allocated_by_asset.items()},
        "selected_count_by_asset": {k: int(v) for k, v in selected_count_by_asset.items()},
        "unresolved_assets": unresolved_assets,
        "comparison_summary": {
            "baseline_max_sharpe": {
                "label": "baseline (max-Sharpe SAA)",
                "asset_weights": base_asset_w,
                "product_weight_sum": base_product_sum,
                "n_products": base_n_products,
            },
            "r1f2_proportional": {
                "label": "R-1F.2 (proportional scaling, ASSET-LEVEL valid only)",
                "asset_weights_dry_run": r1f2_asset_w,
                "product_weight_sum_dry_run": r1f2_product_sum,
                "n_products": r1f2_n_products,
                "needs_selection_rerun_assets": list(r1f2_needs_rerun),
            },
            "r1g2_full_reselection": {
                "label": "R-1G.2 (full re-selection + PortfolioBuilder)",
                "asset_weights": final_asset_weights,
                "product_weight_sum": product_weight_sum,
                "n_products": len(product_rows),
                "valid_product_level_portfolio": valid_product_level_portfolio,
            },
        },
        "diagnostics": {
            # PortfolioBuilder 의 raw diagnostics — quality / fallback / taa / selection 묶음
            "portfolio_builder": portfolio.diagnostics,
            "drift_thresholds": drift_pkg,
            "single_product_max_weight": single_product_cap,
            "universe_classified_by_asset_class": (
                universe_result.diagnostics.get("classified_by_asset_class") or {}
            ),
        },
        "notes": [
            "R-1G.2 = R-1G.1 product re-selection + PortfolioBuilder fallback / "
            "drift clipping / quality evaluation.",
            "manager_override_saa is a SEPARATE LAYER; existing SAA telemetry "
            "(saa_diagnostics.saa_weights) in baseline portfolio JSON is preserved.",
            "implementation_ready=false / implementation_review_status="
            "'review_required' are STRICT — never auto-promote to true.",
            "Production reflection is OUT OF SCOPE for R-1G.2. Requires (a) explicit "
            "manager selection, (b) Decision Register new entry, (c) separate Phase F "
            "sign-off.",
            "automated candidate recommendation is forbidden.",
        ],
    }
    return payload


def write_r1g2_portfolio_json(payload: dict[str, Any], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return out_path


# ---------------------------------------------------------------------------
# 3-way comparison markdown
# ---------------------------------------------------------------------------


def _fmt_pct(v: Any) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "n/a"
    return f"{f * 100:.2f}%"


def render_three_way_compare_md(
    payload: dict[str, Any],
    baseline_portfolio: dict[str, Any],
    r1f2_dump: dict[str, Any],
    out_path: Path,
) -> Path:
    out_path = Path(out_path)
    portfolio_type = payload["meta"]["portfolio_type"]
    sc_id = payload.get("selected_candidate_id")
    meta = payload["meta"]
    target = payload["target_asset_weights"]
    asset_keys = list(target.keys())

    # Final asset weights (R-1G.2 portfolio builder 결과)
    final_a = payload["final_asset_weights"]
    base_a = dict(baseline_portfolio.get("asset_weights") or {})
    r1f2_a = dict(r1f2_dump.get("asset_weights_dry_run") or {})

    # Product counts per asset
    r1g2_count = payload["selected_count_by_asset"]
    base_count: dict[str, int] = {}
    for r in baseline_portfolio.get("product_allocation") or []:
        ak = r.get("asset_key")
        if ak:
            base_count[ak] = base_count.get(ak, 0) + 1
    r1f2_count: dict[str, int] = {}
    for r in r1f2_dump.get("product_allocation_dry_run") or []:
        ak = r.get("asset_key")
        if ak:
            r1f2_count[ak] = r1f2_count.get(ak, 0) + 1

    # Product weight sums
    base_sum = float(baseline_portfolio.get("product_weight_sum") or 0.0)
    r1f2_sum = float(r1f2_dump.get("product_weight_sum_dry_run") or 0.0)
    r1g2_sum = float(payload["product_weight_sum"])
    base_n = len(baseline_portfolio.get("product_allocation") or [])
    r1f2_n = len(r1f2_dump.get("product_allocation_dry_run") or [])
    r1g2_n = payload["product_count"]

    lines: list[str] = []
    lines.append(
        f"# R-1G.2 Three-way Portfolio Comparison ({portfolio_type.upper()})"
    )
    lines.append("")
    lines.append(f"> schema_version: {SCHEMA_VERSION}")
    lines.append(
        "> Read-only dry-run. `production_applied=false`, `dry_run_only=true`, "
        "`portfolio_builder_applied=true`."
    )
    lines.append(
        "> manager_override_saa layer is SEPARATE; baseline SAA telemetry preserved."
    )
    lines.append("")

    # Validity warning
    lines.append("## ⚠ Validity Summary (R-1G.2)")
    lines.append("")
    lines.append(
        f"- **valid_asset_level_dry_run** = {str(meta['valid_asset_level_dry_run']).lower()}"
    )
    lines.append(
        f"- **valid_product_level_portfolio** = "
        f"{str(meta['valid_product_level_portfolio']).lower()}, "
        f"**product_weight_sum_valid** = "
        f"{str(meta['product_weight_sum_valid']).lower()} "
        f"(R-1G.2 product_weight_sum = {r1g2_sum:.6f})"
    )
    lines.append(
        f"- **implementation_ready** = {str(meta['implementation_ready']).lower()}, "
        f"**implementation_review_status** = `{meta['implementation_review_status']}`, "
        f"**sign_off_required_for_production** = "
        f"{str(meta['sign_off_required_for_production']).lower()}"
    )
    lines.append(
        f"- `product_allocation_method` = `{meta['product_allocation_method']}`, "
        f"`portfolio_builder_applied` = {str(meta['portfolio_builder_applied']).lower()}"
    )
    if payload["unresolved_assets"]:
        lines.append(
            f"- **unresolved_assets**: {payload['unresolved_assets']}"
        )
    lines.append("")
    lines.append(
        "> **R-1G.2 reaches a portfolio-valid dry-run, but implementation_ready stays "
        "`false`** until 운용역 sign-off + Decision Register entry + Phase F gate."
    )
    lines.append("")

    # As-of separation
    lines.append("## §1. As-of separation")
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
        f"- candidate_id: **{sc_id}**. target_weight_source: "
        f"`{meta['target_weight_source']}`."
    )
    lines.append("")

    # 3-way headline
    lines.append("## §3. 3-way Headline")
    lines.append("")
    lines.append("| metric | A. baseline (max-Sharpe) | B. R-1F.2 (proportional) | C. R-1G.2 (full reselection + builder) |")
    lines.append("|---|---:|---:|---:|")
    lines.append(
        f"| product_weight_sum | {base_sum:.6f} | {r1f2_sum:.6f} | **{r1g2_sum:.6f}** |"
    )
    lines.append(
        f"| n_products | {base_n} | {r1f2_n} | **{r1g2_n}** |"
    )
    lines.append(
        f"| valid_product_level_portfolio | true (baseline) | **false** | "
        f"**{str(meta['valid_product_level_portfolio']).lower()}** |"
    )
    lines.append(
        f"| dm_ex_us_equity n_picks | {base_count.get('dm_ex_us_equity', 0)} | "
        f"{r1f2_count.get('dm_ex_us_equity', 0)} | "
        f"**{r1g2_count.get('dm_ex_us_equity', 0)}** |"
    )
    lines.append(
        f"| us_high_yield n_picks | {base_count.get('us_high_yield', 0)} | "
        f"{r1f2_count.get('us_high_yield', 0)} | "
        f"**{r1g2_count.get('us_high_yield', 0)}** |"
    )
    lines.append("")

    # Asset weights 3-way table
    lines.append("## §4. Asset Weights (3-way)")
    lines.append("")
    lines.append("| asset | A baseline | B R-1F.2 dry-run | C R-1G.2 | Δ (C − A) |")
    lines.append("|---|---:|---:|---:|---:|")
    for k in asset_keys:
        a = float(base_a.get(k, 0.0))
        b = float(r1f2_a.get(k, 0.0))
        c = float(final_a.get(k, 0.0))
        lines.append(
            f"| {k} | {_fmt_pct(a)} | {_fmt_pct(b)} | {_fmt_pct(c)} "
            f"| {_fmt_pct(c - a)} |"
        )
    lines.append("")

    # Per-asset selection count + allocation (3-way)
    lines.append("## §5. Per-asset Product Counts & R-1G.2 Allocation")
    lines.append("")
    lines.append("| asset | A picks | B picks | C picks | C alloc | C target |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for k in asset_keys:
        lines.append(
            f"| {k} "
            f"| {base_count.get(k, 0)} "
            f"| {r1f2_count.get(k, 0)} "
            f"| **{r1g2_count.get(k, 0)}** "
            f"| {_fmt_pct(payload['allocated_by_asset'].get(k, 0.0))} "
            f"| {_fmt_pct(target.get(k, 0.0))} |"
        )
    lines.append("")

    # Newly added assets' products
    lines.append("## §6. R-1G.2 Newly-introduced Asset Products")
    lines.append("(baseline 0% 였던 자산: dm_ex_us_equity, us_high_yield)")
    lines.append("")
    new_assets = ("dm_ex_us_equity", "us_high_yield")
    for asset in new_assets:
        lines.append(f"### {asset}")
        lines.append("")
        lines.append(
            "| product_id | product_name | manager | role | weight |"
        )
        lines.append(
            "|---|---|---|---|---:|"
        )
        rows = [r for r in payload["product_allocation"] if r["asset_key"] == asset]
        for r in rows:
            lines.append(
                f"| {r['product_id']} | {r['product_name']} | "
                f"{r['manager']} | {r['role']} | {_fmt_pct(r['weight'])} |"
            )
        if not rows:
            lines.append(f"| _no allocation_ | — | — | — | — |")
        lines.append("")

    # Top changed assets (by |C − A|)
    asset_deltas = sorted(
        [
            (k, float(final_a.get(k, 0.0)) - float(base_a.get(k, 0.0)))
            for k in asset_keys
        ],
        key=lambda t: -abs(t[1]),
    )
    lines.append("## §7. Top Changed Assets (|R-1G.2 − baseline|)")
    lines.append("")
    lines.append("| # | asset | Δ |")
    lines.append("|---:|---|---:|")
    for i, (k, d) in enumerate(asset_deltas[:5], 1):
        lines.append(f"| {i} | {k} | {_fmt_pct(d)} |")
    lines.append("")

    # Top changed products (vs baseline)
    base_pid_weight: dict[str, float] = {}
    for r in baseline_portfolio.get("product_allocation") or []:
        base_pid_weight[str(r.get("product_id"))] = float(r.get("final_weight") or 0.0)
    r1g2_pid_weight = {r["product_id"]: float(r["weight"]) for r in payload["product_allocation"]}
    all_pids = set(base_pid_weight) | set(r1g2_pid_weight)
    prod_deltas = []
    for pid in all_pids:
        b = float(base_pid_weight.get(pid, 0.0))
        c = float(r1g2_pid_weight.get(pid, 0.0))
        prod_deltas.append((pid, b, c, c - b))
    prod_deltas.sort(key=lambda t: -abs(t[3]))

    pid_to_row = {r["product_id"]: r for r in payload["product_allocation"]}
    pid_to_base = {
        str(r.get("product_id")): r
        for r in (baseline_portfolio.get("product_allocation") or [])
    }
    lines.append("## §8. Top Changed Products (|R-1G.2 − baseline|, top 10)")
    lines.append("")
    lines.append("| # | product_id | name | manager | A base | C R-1G.2 | Δ |")
    lines.append("|---:|---|---|---|---:|---:|---:|")
    for i, (pid, b, c, d) in enumerate(prod_deltas[:10], 1):
        row = pid_to_row.get(pid) or pid_to_base.get(pid) or {}
        name = row.get("product_name") or row.get("name") or ""
        manager = row.get("manager") or ""
        lines.append(
            f"| {i} | {pid} | {name} | {manager} "
            f"| {_fmt_pct(b)} | {_fmt_pct(c)} | {_fmt_pct(d)} |"
        )
    lines.append("")

    # Limitation 해소 표
    lines.append("## §9. Limitation 해소 여부 vs R-1F.2")
    lines.append("")
    r1f2_needs_rerun = r1f2_dump.get("needs_selection_rerun_assets") or []
    lines.append("| issue | R-1F.2 | R-1G.2 |")
    lines.append("|---|---|---|")
    lines.append(
        f"| product_weight_sum ≈ 1.0 | "
        f"{r1f2_sum:.4f} (invalid) | "
        f"**{r1g2_sum:.6f}** "
        f"({'valid' if meta['product_weight_sum_valid'] else 'invalid'}) |"
    )
    lines.append(
        f"| needs_selection_rerun_assets | {r1f2_needs_rerun} | "
        f"**{payload['unresolved_assets'] or '[]'}** |"
    )
    lines.append(
        f"| dm_ex_us_equity selected | {r1f2_count.get('dm_ex_us_equity', 0)} | "
        f"**{r1g2_count.get('dm_ex_us_equity', 0)}** |"
    )
    lines.append(
        f"| us_high_yield selected | {r1f2_count.get('us_high_yield', 0)} | "
        f"**{r1g2_count.get('us_high_yield', 0)}** |"
    )
    lines.append("")

    # Builder warnings + remaining limitations
    quality_block = (
        payload.get("diagnostics", {}).get("portfolio_builder", {}).get("quality") or {}
    )
    review_reasons = list(quality_block.get("review_reasons") or [])
    fb_block = (
        payload.get("diagnostics", {}).get("portfolio_builder", {}).get("fallback") or {}
    )
    lines.append("## §10. Remaining Warnings / Notes")
    lines.append("")
    if review_reasons:
        lines.append("- quality review_reasons:")
        for r in review_reasons:
            lines.append(f"  - {r}")
    else:
        lines.append("- quality review_reasons: (none)")
    fb_warnings = (fb_block.get("warnings") if isinstance(fb_block, dict) else None) or []
    if fb_warnings:
        lines.append("- fallback warnings:")
        for w in fb_warnings:
            lines.append(f"  - {w}")
    lines.append("")

    # Why implementation_ready is still false
    lines.append("## §11. Why `implementation_ready = false`")
    lines.append("")
    lines.append(
        "- R-1G.2 produces a product-level **portfolio-valid** dry-run (when "
        "`valid_product_level_portfolio=true`), but **does not** authorize production "
        "implementation."
    )
    lines.append(
        "- 운용역의 sign-off, Decision Register 신규 entry, 그리고 별도 Phase F gate "
        "통과 후에만 `implementation_ready` 를 검토할 수 있다 (자동 승격 금지)."
    )
    lines.append(
        "- 본 turn 까지는 manager_override_saa 가 **별도 layer** 로만 유지되며 "
        "production max-Sharpe SAA telemetry 는 그대로 보존된다."
    )
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


__all__ = [
    "SCHEMA_VERSION",
    "build_r1g2_portfolio",
    "write_r1g2_portfolio_json",
    "render_three_way_compare_md",
]
