"""TAAOverlayEngine — SAA + Regime → TAA-tilted weights.

Phase B  : asset_tilts 적용 + cash-neutral + warning 만.
Phase C.3: 결과를 long-only + bucket bound 로 SLSQP projection 하여 항상 feasible.
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from tdf_engine.domain.enums import Regime
from tdf_engine.domain.models import TAAResult
from tdf_engine.taa.policy import RegimeTAAPolicy
from tdf_engine.taa.projection import project_to_feasible

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

logger = logging.getLogger(__name__)


class TAAOverlayEngine:
    """RegimeTAAPolicy + bound 검증 + cash-neutral 보정 + Phase C.3 feasibility projection."""

    def __init__(
        self,
        policy: RegimeTAAPolicy,
        constraints: dict[str, Any],
        bucket_by_asset: dict[str, str] | None = None,
        asset_bounds: dict[str, tuple[float, float]] | None = None,
        bucket_bounds: dict[str, tuple[float, float]] | None = None,
        enable_projection: bool = True,
    ):
        """asset_bounds / bucket_bounds 가 None 이면 projection 단계에서 (0, 1) / 무제약."""
        self.policy = policy
        self.constraints = constraints
        self.bucket_by_asset = bucket_by_asset or {}
        self.asset_bounds = asset_bounds or {}
        self.bucket_bounds = bucket_bounds or {}
        self.enable_projection = bool(enable_projection)

    def apply(
        self,
        saa_weights: "pd.Series",
        regime: int | Regime,
    ) -> TAAResult:
        import pandas as pd

        regime_int = int(regime)
        tilt_def = self.policy.get(regime_int)

        tilts = pd.Series(0.0, index=saa_weights.index, name="tilt")
        for k, v in tilt_def.asset_tilts.items():
            if k in tilts.index:
                tilts.loc[k] = float(v)
            else:
                logger.warning("TAA tilt 자산 '%s' 가 SAA 인덱스에 없음 — 무시", k)

        residual = float(tilts.sum())
        if abs(residual) > 1e-12:
            adj = -residual / float(len(tilts))
            tilts = tilts + adj

        target = saa_weights + tilts

        diagnostics: dict[str, Any] = {
            "regime": regime_int,
            "regime_label": Regime(regime_int).label,
            "residual_before_adjust": residual,
            "tilt_sum_after_adjust": float(tilts.sum()),
            "violations": [],
        }

        per_asset_max = float(self.constraints.get("per_asset_max_tilt", 0.03))
        violations: list[str] = []
        for k, t in tilts.items():
            if abs(float(t)) > per_asset_max + 1e-12:
                violations.append(
                    f"per_asset_max_tilt violated: {k} tilt={t:+.4f} > {per_asset_max:+.4f}"
                )

        # ── Phase C.3: feasibility projection ───────────────────────────
        if self.enable_projection:
            # bucket_bounds 가 비었으면 constraints 에서 추출 (taa_policy.constraints)
            bucket_bounds = dict(self.bucket_bounds)
            if not bucket_bounds:
                eq_min = float(self.constraints.get("equity_total_min", 0.75))
                eq_max = float(self.constraints.get("equity_total_max", 0.85))
                fi_min = float(self.constraints.get("fixed_income_total_min", 0.15))
                fi_max = float(self.constraints.get("fixed_income_total_max", 0.25))
                bucket_bounds = {
                    "equity": (eq_min, eq_max),
                    "fixed_income": (fi_min, fi_max),
                }
            taa, proj_diag = project_to_feasible(
                target_weights=target,
                asset_bounds=self.asset_bounds,
                bucket_bounds=bucket_bounds,
                bucket_by_asset=self.bucket_by_asset,
                sum_target=1.0,
            )
            diagnostics["taa_feasibility"] = proj_diag.as_dict()
        else:
            taa = target
            diagnostics["taa_feasibility"] = {"projection_used": False,
                                                "projection_success": True}

        # bucket sum 진단 (projection 후)
        if self.bucket_by_asset:
            buckets: dict[str, float] = {}
            for k, w in taa.items():
                b = self.bucket_by_asset.get(k)
                if b is None:
                    continue
                buckets[b] = buckets.get(b, 0.0) + float(w)
            diagnostics["bucket_sums"] = buckets

        if violations:
            diagnostics["violations"] = violations
            for msg in violations:
                logger.warning("TAA constraint warning: %s", msg)

        reasons = {k: tilt_def.reason for k in tilt_def.asset_tilts}

        return TAAResult(
            saa_weights=saa_weights.copy(),
            taa_weights=taa,
            tilts=tilts,
            reasons=reasons,
            diagnostics=diagnostics,
        )
