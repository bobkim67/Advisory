"""OptimizationTool — facade.

CMA 빌드 → ConstraintSet 빌드 → MVOOptimizer.optimize → OptimizationResult.
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from tdf_engine.domain.enums import Objective
from tdf_engine.domain.models import (
    AssetClassInfo,
    OptimizationResult,
)
from tdf_engine.optimization.cma import CapitalMarketAssumptionBuilder
from tdf_engine.optimization.constraints import ConstraintSet
from tdf_engine.optimization.optimizer import MVOOptimizer

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd
    from tdf_engine.repositories.interfaces import MarketDataRepository

logger = logging.getLogger(__name__)


class OptimizationTool:
    def __init__(
        self,
        repo: "MarketDataRepository",
        assets: list[AssetClassInfo],
        tdf_config: dict[str, Any],
        optimization_config: dict[str, Any],
    ):
        self.repo = repo
        self.assets = assets
        self.tdf_config = tdf_config
        self.optimization_config = optimization_config

        opt_block = optimization_config.get("optimization", {}) or {}
        objective_value = opt_block.get("objective", "max_sharpe")
        try:
            self.objective = Objective(objective_value)
        except ValueError as e:
            raise ValueError(
                f"objective '{objective_value}' 가 Objective enum 에 없음. "
                f"yaml 의 optimization.objective 확인 필요."
            ) from e

        solver_block = opt_block.get("solver", {}) or {}

        # bucket → asset_keys 매핑
        bucket_to_assets: dict[str, list[str]] = {}
        for a in assets:
            bucket_to_assets.setdefault(a.bucket.value, []).append(a.asset_key)

        self.optimizer = MVOOptimizer(
            objective=self.objective,
            objective_params=opt_block.get("objective_params") or {},
            solver_method=solver_block.get("method", "SLSQP"),
            solver_options={
                "maxiter": solver_block.get("max_iter", 200),
                "ftol": solver_block.get("tol", 1.0e-9),
            },
            bucket_to_assets=bucket_to_assets,
        )
        self.cma_builder = CapitalMarketAssumptionBuilder(repo, assets)

        self.warm_start_block = optimization_config.get("warm_start", {}) or {}

    def build_constraints(self) -> ConstraintSet:
        bounds_raw = self.tdf_config.get("weight_bounds") or {}
        bounds = {
            ak: (float(b["min"]), float(b["max"]))
            for ak, b in bounds_raw.items()
        }
        cs = self.optimization_config.get("constraints", {}) or {}
        bucket_sum = {}
        if "equity_sum" in cs:
            es = cs["equity_sum"]
            bucket_sum["equity"] = (float(es["min"]), float(es["max"]))
        if "fixed_income_sum" in cs:
            fs = cs["fixed_income_sum"]
            bucket_sum["fixed_income"] = (float(fs["min"]), float(fs["max"]))

        err_block = self.optimization_config.get("err", {}) or {}
        return ConstraintSet(
            weight_sum_must_equal=float(cs.get("weight_sum_must_equal", 1.0)),
            bounds=bounds,
            bucket_sum=bucket_sum,
            region_lower_bounds={},
            err_enabled=bool(err_block.get("enabled", False)),
            err_threshold=err_block.get("threshold"),
        )

    def _resolve_warm_start(self, n_assets_in_cma: list[str]) -> "pd.Series | None":
        """warm_start.source 에 따라 x0 결정."""
        import pandas as pd

        if not self.warm_start_block.get("enabled", True):
            return None
        source = self.warm_start_block.get("source", "reference_weights")

        if source == "reference_weights":
            ref = self.tdf_config.get("reference_weights") or {}
            if not ref:
                return None
            # CMA 에 존재하는 자산만 사용
            x0 = {k: float(ref[k]) for k in n_assets_in_cma if k in ref}
            if not x0:
                return None
            return pd.Series(x0)

        # equal_weight fallback 은 optimizer 내부에서 처리
        return None

    def run(
        self,
        initial_weights: "pd.Series | None" = None,
    ) -> OptimizationResult:
        cma = self.cma_builder.build()
        constraints = self.build_constraints()
        if initial_weights is None:
            initial_weights = self._resolve_warm_start(list(cma.expected_returns.index))
        result = self.optimizer.optimize(cma, constraints, x0=initial_weights)
        # CMA diagnostics merge
        result.diagnostics.setdefault("cma", cma.diagnostics)
        # Phase E-6.2 — direct SAA weights telemetry (T-6).
        # 시각화 SAA→TAA bridge 가 inferred (taa_target − asset_tilts) 대신 본 telemetry 만 참조.
        result.diagnostics.setdefault(
            "saa_weights",
            {k: float(v) for k, v in result.weights.items()},
        )
        return result
