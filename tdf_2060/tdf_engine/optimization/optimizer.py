"""MVOOptimizer — scipy SLSQP + objective dispatch.

사용자 결정 #4: objective 는 config-driven. dispatch table 사용.
Phase B 에서 활성: max_sharpe.
나머지 objective 들은 stub (NotImplementedError) 유지.
"""

from __future__ import annotations

import logging
from typing import Callable, TYPE_CHECKING

from tdf_engine.domain.enums import Objective
from tdf_engine.domain.models import (
    CapitalMarketAssumption,
    OptimizationResult,
)
from tdf_engine.optimization.constraints import ConstraintSet

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

logger = logging.getLogger(__name__)


ObjectiveFn = Callable[..., float]


def _objective_max_sharpe(w, mu, cov, rf: float) -> float:
    """음의 Sharpe (minimize 용)."""
    import numpy as np

    port_return = float(mu @ w)
    port_var = float(w @ cov @ w)
    port_vol = float(np.sqrt(max(port_var, 1e-18)))
    return -((port_return - rf) / port_vol)


def _objective_utility(*args, **kwargs) -> float:
    raise NotImplementedError("utility — Phase B 비구현 (max_sharpe 만 활성)")


def _objective_min_volatility(*args, **kwargs) -> float:
    raise NotImplementedError("min_volatility — Phase B 비구현")


def _objective_max_return_under_risk_limit(*args, **kwargs) -> float:
    raise NotImplementedError("max_return_under_risk_limit — Phase B 비구현")


OBJECTIVE_REGISTRY: dict[Objective, ObjectiveFn] = {
    Objective.MAX_SHARPE: _objective_max_sharpe,
    Objective.UTILITY: _objective_utility,
    Objective.MIN_VOLATILITY: _objective_min_volatility,
    Objective.MAX_RETURN_UNDER_RISK_LIMIT: _objective_max_return_under_risk_limit,
}


class MVOOptimizer:
    """scipy.optimize.minimize 호출자 (SLSQP).

    bucket_to_assets:
        {"equity": ["kr_equity", ...], "fixed_income": [...]}.
        ConstraintSet.bucket_sum 을 자산 인덱스 기반 부등식으로 변환할 때 사용.
        OptimizationTool 단에서 AssetClassInfo.bucket 으로 빌드해서 주입.
    """

    def __init__(
        self,
        objective: Objective = Objective.MAX_SHARPE,
        objective_params: dict | None = None,
        solver_method: str = "SLSQP",
        solver_options: dict | None = None,
        bucket_to_assets: dict[str, list[str]] | None = None,
    ):
        if objective not in OBJECTIVE_REGISTRY:
            raise ValueError(
                f"objective '{objective}' 가 OBJECTIVE_REGISTRY 에 없음. "
                f"등록된 후보 = {[o.value for o in OBJECTIVE_REGISTRY]}"
            )
        self.objective = objective
        self.objective_fn = OBJECTIVE_REGISTRY[objective]
        self.objective_params = objective_params or {}
        self.solver_method = solver_method
        self.solver_options = solver_options or {}
        self.bucket_to_assets = bucket_to_assets or {}

    def optimize(
        self,
        cma: CapitalMarketAssumption,
        constraints: ConstraintSet,
        x0: "pd.Series | None" = None,
    ) -> OptimizationResult:
        import numpy as np
        import pandas as pd
        from scipy.optimize import minimize

        order = list(cma.expected_returns.index)
        n = len(order)
        if n == 0:
            raise ValueError("cma.expected_returns 가 비어있음")

        # bounds (asset-level). ConstraintSet.bounds 에 없으면 (0, 1).
        bounds = []
        for k in order:
            lb, ub = constraints.bounds.get(k, (0.0, 1.0))
            bounds.append((float(lb), float(ub)))

        # x0
        if x0 is None:
            init = np.full(n, 1.0 / n)
        else:
            init = np.array([float(x0.get(k, 1.0 / n)) for k in order])
            s = init.sum()
            if s > 0:
                init = init / s
            else:
                init = np.full(n, 1.0 / n)

        mu = cma.expected_returns.loc[order].to_numpy(dtype=float)
        cov = cma.covariance.loc[order, order].to_numpy(dtype=float)

        rf = float(self.objective_params.get("risk_free_rate", 0.0))

        def neg_sharpe(w):
            return self.objective_fn(w, mu, cov, rf)

        # 제약 — eq: sum=target, ineq: bucket bounds
        scipy_constraints: list[dict] = []
        scipy_constraints.append(
            {"type": "eq", "fun": lambda w: float(np.sum(w)) - constraints.weight_sum_must_equal}
        )

        # bucket sum (lb / ub) — assets: list of asset_key in bucket
        for bucket_name, (lb, ub) in constraints.bucket_sum.items():
            assets_in_bucket = self.bucket_to_assets.get(bucket_name, [])
            idx = [order.index(a) for a in assets_in_bucket if a in order]
            if not idx:
                continue
            idx_arr = np.array(idx, dtype=int)
            # ineq: w_sum - lb >= 0
            scipy_constraints.append(
                {"type": "ineq", "fun": (lambda w, ix=idx_arr, lb=lb: float(w[ix].sum()) - float(lb))}
            )
            # ineq: ub - w_sum >= 0
            scipy_constraints.append(
                {"type": "ineq", "fun": (lambda w, ix=idx_arr, ub=ub: float(ub) - float(w[ix].sum()))}
            )

        # region lower bounds (Phase A 비활성이지만 ConstraintSet 에 있으면 적용)
        for asset_key, lb in (constraints.region_lower_bounds or {}).items():
            if asset_key in order:
                ix = order.index(asset_key)
                scipy_constraints.append(
                    {"type": "ineq", "fun": (lambda w, i=ix, lb=lb: float(w[i]) - float(lb))}
                )

        options = {
            "maxiter": int(self.solver_options.get("maxiter", 200)),
            "ftol": float(self.solver_options.get("ftol", 1.0e-9)),
            "disp": False,
        }

        res = minimize(
            neg_sharpe,
            init,
            method=self.solver_method,
            bounds=bounds,
            constraints=scipy_constraints,
            options=options,
        )

        w = pd.Series(res.x, index=order, name="weight")
        port_return = float(mu @ res.x)
        port_var = float(res.x @ cov @ res.x)
        port_vol = float(np.sqrt(max(port_var, 0.0)))
        sharpe = (port_return - rf) / port_vol if port_vol > 1e-12 else float("nan")

        diagnostics = {
            "solver_status": int(res.status),
            "solver_message": str(res.message),
            "n_iter": int(getattr(res, "nit", -1)),
            "objective_name": self.objective.value,
            "n_assets": n,
            "rf": rf,
            "weight_sum": float(w.sum()),
        }

        return OptimizationResult(
            weights=w,
            expected_return=port_return,
            volatility=port_vol,
            sharpe=sharpe,
            objective_value=float(res.fun),
            objective_name=self.objective.value,
            constraints_passed=bool(res.success),
            diagnostics=diagnostics,
        )
