"""PortfolioBuilder — TAA 자산 weights + product selection → PortfolioResult.

Phase B.5 : fallback (pro-rata → bucket → cash placeholder).
Phase B.5+: quality 평가 (drift, drift_by_bucket, quality_status).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from tdf_engine.domain.enums import ProductType
from tdf_engine.domain.models import (
    AssetClassInfo,
    PortfolioResult,
    ProductSelectionResult,
    TAAResult,
)
from tdf_engine.portfolio.fallback import apply_fallback
from tdf_engine.portfolio.quality import (
    DEFAULT_ASSET_DRIFT_THRESHOLD,
    DEFAULT_BUCKET_DRIFT_THRESHOLD,
    ENFORCEMENT_PRODUCTION,
    evaluate_quality,
)

if TYPE_CHECKING:  # pragma: no cover
    pass

logger = logging.getLogger(__name__)


class PortfolioBuilder:
    @staticmethod
    def build(
        taa: TAAResult,
        selection: ProductSelectionResult,
        product_type: ProductType,
        assets: list[AssetClassInfo] | None = None,
        single_product_max_weight: float = 1.0,
        asset_drift_threshold: float = DEFAULT_ASSET_DRIFT_THRESHOLD,
        bucket_drift_threshold: float = DEFAULT_BUCKET_DRIFT_THRESHOLD,
        enforcement: str = ENFORCEMENT_PRODUCTION,
    ) -> PortfolioResult:
        bucket_by_asset: dict[str, str] = {}
        if assets:
            bucket_by_asset = {a.asset_key: a.bucket.value for a in assets}

        product_df, fb_diag = apply_fallback(
            product_weights=selection.selected,
            asset_weights=taa.taa_weights,
            selection_diagnostics=selection.diagnostics,
            bucket_by_asset=bucket_by_asset,
            single_product_max_weight=single_product_max_weight,
        )

        quality = evaluate_quality(
            target_asset_weights=taa.taa_weights,
            product_weights=product_df,
            fallback_diagnostics=fb_diag,
            selection_diagnostics=selection.diagnostics,
            bucket_by_asset=bucket_by_asset,
            asset_drift_threshold=asset_drift_threshold,
            bucket_drift_threshold=bucket_drift_threshold,
            enforcement=enforcement,
        )

        diagnostics = {
            "product_type": product_type.value,
            "asset_weight_sum": float(taa.taa_weights.sum()),
            "product_weight_sum": (
                float(product_df["weight"].sum()) if not product_df.empty else 0.0
            ),
            "n_products": int(len(product_df)),
            "taa_diagnostics": taa.diagnostics,
            "selection_diagnostics": selection.diagnostics,
            "fallback": fb_diag,
            "quality": {
                "quality_status": quality.quality_status,
                "enforcement_mode": quality.enforcement_mode,
                "target_asset_weights": quality.target_asset_weights,
                "final_asset_weights": quality.final_asset_weights,
                "asset_weight_drift": quality.asset_weight_drift,
                "max_abs_asset_weight_drift": quality.max_abs_asset_weight_drift,
                "drift_by_bucket": quality.drift_by_bucket,
                "max_abs_bucket_drift": quality.max_abs_bucket_drift,
                "cash_placeholder_weight": quality.cash_placeholder_weight,
                "review_reasons": quality.review_reasons,
                "drift_telemetry_notes": quality.drift_telemetry_notes,
                "fallback_absorbers": quality.fallback_absorbers,
                "thresholds": {
                    "asset_drift": asset_drift_threshold,
                    "bucket_drift": bucket_drift_threshold,
                    "enforcement": quality.enforcement_mode,
                },
                # Phase D — quality drift source 분류
                "drift_source_by_asset": quality.drift_source_by_asset,
                "drift_clipping_summary": quality.drift_clipping_summary,
            },
        }

        return PortfolioResult(
            asset_weights=taa.taa_weights.copy(),
            product_weights=product_df,
            portfolio_type=product_type,
            constraints_passed=True,  # validator 가 덮어씀
            diagnostics=diagnostics,
        )
