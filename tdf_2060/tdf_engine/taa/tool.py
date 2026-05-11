"""TAAOverlayTool — facade.

Phase C.3: tdf_config 의 final_asset_bounds 와 taa_bounds 를 받아
TAAOverlayEngine 에 전달 → projection 적용.
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from tdf_engine.domain.enums import Regime
from tdf_engine.domain.models import AssetClassInfo, TAAResult
from tdf_engine.taa.overlay import TAAOverlayEngine
from tdf_engine.taa.policy import RegimeTAAPolicy

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

logger = logging.getLogger(__name__)


class TAAOverlayTool:
    def __init__(
        self,
        taa_config: dict[str, Any],
        assets: list[AssetClassInfo] | None = None,
        tdf_config: dict[str, Any] | None = None,
        enable_projection: bool = True,
    ):
        self.taa_config = taa_config
        self.tdf_config = tdf_config or {}
        self.policy = RegimeTAAPolicy.from_dict(taa_config.get("regime_tilts") or {})
        self.constraints = taa_config.get("constraints") or {}

        bucket_by_asset: dict[str, str] = {}
        if assets:
            bucket_by_asset = {a.asset_key: a.bucket.value for a in assets}

        # Phase C.3 — asset_bounds / bucket_bounds 추출
        # 우선순위: tdf_config.final_asset_bounds → tdf_config.weight_bounds → 무제약
        asset_bounds: dict[str, tuple[float, float]] = {}
        fab = self.tdf_config.get("final_asset_bounds") or {}
        if fab:
            asset_bounds = {ak: (float(b["min"]), float(b["max"])) for ak, b in fab.items()}
        else:
            wb = self.tdf_config.get("weight_bounds") or {}
            if wb:
                asset_bounds = {ak: (float(b["min"]), float(b["max"])) for ak, b in wb.items()}

        # bucket bounds: tdf_config.taa_bounds 우선
        bucket_bounds: dict[str, tuple[float, float]] = {}
        tb = self.tdf_config.get("taa_bounds") or {}
        if tb:
            bucket_bounds["equity"] = (float(tb.get("equity_min", 0.0)), float(tb.get("equity_max", 1.0)))
            bucket_bounds["fixed_income"] = (
                float(tb.get("fixed_income_min", 0.0)), float(tb.get("fixed_income_max", 1.0))
            )

        self.engine = TAAOverlayEngine(
            self.policy,
            self.constraints,
            bucket_by_asset=bucket_by_asset,
            asset_bounds=asset_bounds,
            bucket_bounds=bucket_bounds,
            enable_projection=enable_projection,
        )

    def run(
        self,
        saa_weights: "pd.Series",
        regime: int | Regime,
    ) -> TAAResult:
        return self.engine.apply(saa_weights, regime)
