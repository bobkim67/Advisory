"""RegimeAnalysisTool / RegimeReturnTool — facade."""

from __future__ import annotations

import logging
from datetime import date as _date
from typing import Any, TYPE_CHECKING

from tdf_engine.domain.enums import Regime
from tdf_engine.domain.models import (
    AssetClassInfo,
    RegimeAnalysisResult,
    RegimeReturnResult,
    RegimeState,
)
from tdf_engine.regime.classifier import ECIRegimeClassifier
from tdf_engine.regime.placement import PlacementCalculator
from tdf_engine.regime.returns import AssetReturnCalculator, RegimeReturnAnalyzer
from tdf_engine.regime.velocity import VelocityCalculator

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd
    from tdf_engine.repositories.interfaces import MarketDataRepository

logger = logging.getLogger(__name__)


def _ensure_date_index(df: "pd.DataFrame") -> "pd.DataFrame":
    """첫 컬럼이 date/Date 면 datetime 인덱스로 변환."""
    import pandas as pd

    df = df.copy()
    cols_lower = [str(c).lower() for c in df.columns]
    if "date" in cols_lower:
        date_col = df.columns[cols_lower.index("date")]
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col).sort_index()
    return df


class RegimeAnalysisTool:
    """regime_src → Placement → Velocity → ECI → 최신 RegimeState."""

    def __init__(
        self,
        repo: "MarketDataRepository",
        taa_config: dict[str, Any],
    ):
        self.repo = repo
        self.taa_config = taa_config

        ri = (taa_config.get("regime_input") or {})
        self.region = ri.get("composite_region", "G7")
        self.window = int(ri.get("composite_window", 12))

    def run(self) -> RegimeAnalysisResult:
        import pandas as pd

        raw = self.repo.load_regime_source()
        df = _ensure_date_index(raw)

        if self.region not in df.columns:
            raise ValueError(
                f"region '{self.region}' 가 regime_src 컬럼에 없음. "
                f"available={list(df.columns)}"
            )

        # 단일 region 사용 (composite mode default)
        s = df[self.region].astype(float)

        placement = PlacementCalculator(window=self.window).calc(s)
        velocity = VelocityCalculator.calc(placement)
        regime = ECIRegimeClassifier.classify_frame(placement, velocity)

        # latest non-null
        regime_clean = regime.dropna()
        if regime_clean.empty:
            raise ValueError(
                f"regime 분류 결과가 모두 NaN. 입력 데이터 길이가 window={self.window} 보다 짧을 수 있음."
            )

        latest_idx = regime_clean.index[-1]
        latest_p = float(placement.loc[latest_idx])
        latest_v = float(velocity.loc[latest_idx])
        latest_regime = Regime(int(regime_clean.iloc[-1]))

        as_of = latest_idx
        if hasattr(as_of, "date"):
            as_of = as_of.date()
        elif not isinstance(as_of, _date):
            as_of = pd.to_datetime(as_of).date()

        latest_state = RegimeState(
            as_of=as_of,
            region=self.region,
            placement=latest_p,
            velocity=latest_v,
            regime=latest_regime,
        )

        # DataFrame 형태로 wrap (단일 region 이지만 일관성)
        placement_df = placement.to_frame(name=self.region)
        velocity_df = velocity.to_frame(name=self.region)
        regime_df = regime.to_frame(name=self.region)

        # Phase E-6.2 (T-5) — latest N regime observations history.
        # 시각화 main 블록 A.3 (Regime timeline) 의존. allocation/regime classification 영향 없음.
        history_n = 5
        history_tail = regime_clean.tail(history_n)
        history: list[dict] = []
        for idx in history_tail.index:
            d = idx
            if hasattr(d, "date"):
                d = d.date()
            elif not isinstance(d, _date):
                d = pd.to_datetime(d).date()
            history.append({
                "as_of": str(d),
                "placement": float(placement.loc[idx]),
                "velocity": float(velocity.loc[idx]),
                "regime": int(regime_clean.loc[idx]),
            })

        diagnostics = {
            "region": self.region,
            "window": self.window,
            "n_obs": int(len(df)),
            "n_regime_valid": int(regime_clean.shape[0]),
            "latest_date": str(as_of),
            "history": history,
        }

        return RegimeAnalysisResult(
            placement=placement_df,
            velocity=velocity_df,
            regime=regime_df,
            latest_state=latest_state,
            diagnostics=diagnostics,
        )


class RegimeReturnTool:
    """regimeAnalysis_src + ECI → regime × asset 평균수익률."""

    def __init__(
        self,
        repo: "MarketDataRepository",
        assets: list[AssetClassInfo],
    ):
        self.repo = repo
        self.assets = assets

    def run(self, regime_series: "pd.Series") -> RegimeReturnResult:
        import pandas as pd

        raw = self.repo.load_regime_return_source()
        df = _ensure_date_index(raw)

        # asset_key → 컬럼명 매핑 (regime_return source label)
        col_by_key: dict[str, str] = {}
        missing: list[str] = []
        for a in self.assets:
            label = a.source_names.regime_return
            if label is None:
                missing.append(a.asset_key)
                continue
            if label in df.columns:
                col_by_key[a.asset_key] = label
            else:
                missing.append(a.asset_key)

        if not col_by_key:
            raise ValueError(
                "regimeAnalysis_src 와 매칭되는 자산 컬럼이 하나도 없음. "
                "asset_mapping.yaml 의 source_names.regime_return 확인 필요."
            )

        levels = df[list(col_by_key.values())].astype(float)
        levels.columns = list(col_by_key.keys())

        monthly = AssetReturnCalculator.monthly_returns(levels)
        regime_avg = RegimeReturnAnalyzer.analyze(monthly, regime_series)

        diagnostics = {
            "n_assets": len(col_by_key),
            "missing_assets": missing,
            "n_obs": int(len(monthly)),
        }

        return RegimeReturnResult(
            monthly_returns=monthly,
            regime_avg=regime_avg,
            diagnostics=diagnostics,
        )
