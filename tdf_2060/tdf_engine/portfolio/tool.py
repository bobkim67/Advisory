"""PortfolioConstructionTool — orchestrator (top-level).

흐름:
  optimization.run()
    → regime.run()
    → taa.run(saa, regime.latest)
    → universe.run()
    → selection.run(taa.taa_weights)
    → builder.build
    → validator.validate
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from tdf_engine.domain.enums import ProductType
from tdf_engine.domain.models import PortfolioResult
from tdf_engine.portfolio.builder import PortfolioBuilder
from tdf_engine.portfolio.validator import PortfolioValidator

if TYPE_CHECKING:  # pragma: no cover
    from tdf_engine.optimization.tool import OptimizationTool
    from tdf_engine.regime.tool import RegimeAnalysisTool
    from tdf_engine.selection.tool import ProductSelectionTool
    from tdf_engine.taa.tool import TAAOverlayTool
    from tdf_engine.universe.tool import UniverseTool

logger = logging.getLogger(__name__)


class PortfolioConstructionTool:
    def __init__(
        self,
        optimization_tool: "OptimizationTool",
        regime_tool: "RegimeAnalysisTool",
        taa_tool: "TAAOverlayTool",
        universe_tool: "UniverseTool",
        selection_tool_factory,
        tdf_config: dict | None = None,
        universe_config: dict | None = None,
        assets=None,
    ):
        """selection_tool_factory: callable(universe_result) → ProductSelectionTool."""
        self.optimization_tool = optimization_tool
        self.regime_tool = regime_tool
        self.taa_tool = taa_tool
        self.universe_tool = universe_tool
        self.selection_tool_factory = selection_tool_factory
        self.tdf_config = tdf_config or {}
        self.universe_config = universe_config or {}
        self.assets = assets

    def run(self, product_type: ProductType) -> PortfolioResult:
        # 1) SAA
        saa = self.optimization_tool.run()
        logger.info(
            "SAA: sharpe=%.4f sum=%.6f", saa.sharpe, float(saa.weights.sum())
        )

        # 2) Regime
        regime_result = self.regime_tool.run()
        regime = regime_result.latest_state.regime
        logger.info(
            "Regime: %s (P=%+.4f V=%+.4f as_of=%s)",
            regime_result.latest_state.label,
            regime_result.latest_state.placement,
            regime_result.latest_state.velocity,
            regime_result.latest_state.as_of,
        )

        # 3) TAA
        taa = self.taa_tool.run(saa.weights, regime)
        logger.info(
            "TAA: sum=%.6f violations=%d",
            float(taa.taa_weights.sum()),
            len(taa.diagnostics.get("violations") or []),
        )

        # 4) Universe
        universe_result = self.universe_tool.run()
        logger.info(
            "Universe: passed=%d / raw=%d",
            universe_result.filtered_count,
            universe_result.raw_count,
        )

        # 5) Selection
        selection_tool = self.selection_tool_factory(universe_result)
        selection = selection_tool.run(taa.taa_weights)
        logger.info(
            "Selection: %d picks (selected_weight_sum=%.4f, unfilled=%s)",
            len(selection.selected),
            selection.diagnostics.get("selected_weight_sum"),
            selection.diagnostics.get("unfilled_assets"),
        )

        # 6) Build (+ fallback)
        type_block = self.universe_config.get(product_type.value, {}) or {}
        pc = type_block.get("product_constraints", {}) or {}
        single_product_cap = float(pc.get("single_product_max_weight", 1.0))

        # Phase D — drift threshold 구조화 (config-driven, mode-aware).
        from tdf_engine.portfolio.quality import (
            DEFAULT_ASSET_DRIFT_THRESHOLD,
            DEFAULT_BUCKET_DRIFT_THRESHOLD,
            ENFORCEMENT_PRODUCTION,
        )
        drift_cfg = (self.tdf_config.get("drift_thresholds") or {})
        op_mode = str(self.tdf_config.get("operating_mode") or "production").strip().lower()
        modes_cfg = drift_cfg.get("modes") or {}
        mode_specific = modes_cfg.get(op_mode) or {}
        # 우선순위: modes.<op_mode>.enforcement → drift_thresholds.enforcement → "production"
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

        portfolio = PortfolioBuilder.build(
            taa,
            selection,
            product_type,
            assets=self.assets,
            single_product_max_weight=single_product_cap,
            asset_drift_threshold=asset_thr,
            bucket_drift_threshold=bucket_thr,
            enforcement=enforcement,
        )

        # diagnostics 보강
        portfolio.diagnostics["regime"] = {
            "as_of": str(regime_result.latest_state.as_of),
            "region": regime_result.latest_state.region,
            "placement": regime_result.latest_state.placement,
            "velocity": regime_result.latest_state.velocity,
            "regime": int(regime_result.latest_state.regime),
            "regime_label": regime_result.latest_state.label,
            # Phase E-6.2 (T-5) — latest N regime observations.
            "history": list(regime_result.diagnostics.get("history") or []),
        }
        portfolio.diagnostics["saa_diagnostics"] = saa.diagnostics
        portfolio.diagnostics["universe_diagnostics"] = universe_result.diagnostics

        # 7) Validate
        validator = PortfolioValidator(atol=1e-6)
        report = validator.validate(portfolio, self.tdf_config, self.universe_config)
        portfolio.constraints_passed = report.passed
        portfolio.diagnostics["validation"] = {
            "passed": report.passed,
            "issues": report.issues,
            "warnings": report.warnings,
        }

        return portfolio
