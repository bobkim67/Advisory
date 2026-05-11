"""DB Repository placeholder.

이번 단계에서는 connect 만 받아두고, 실제 쿼리는 NotImplementedError.
다음 단계에서 SCIP / dt / solution 매핑 결정 후 구현.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd


class DbMarketDataRepository:
    """SCIP DB 기반 MarketDataRepository (다음 단계).

    interfaces.MarketDataRepository 구현체.
    """

    def __init__(self, engine: Any):
        # SQLAlchemy Engine 등을 받음. credential 은 호출자 책임.
        self.engine = engine

    def load_asset_rt_vol(self) -> "pd.DataFrame":
        raise NotImplementedError(
            "DbMarketDataRepository.load_asset_rt_vol — DB 매핑 결정 후 구현"
        )

    def load_corr_matrix(self) -> "pd.DataFrame":
        raise NotImplementedError(
            "DbMarketDataRepository.load_corr_matrix — DB 매핑 결정 후 구현"
        )

    def load_regime_source(self) -> "pd.DataFrame":
        raise NotImplementedError(
            "DbMarketDataRepository.load_regime_source — DB 매핑 결정 후 구현"
        )

    def load_regime_return_source(self) -> "pd.DataFrame":
        raise NotImplementedError(
            "DbMarketDataRepository.load_regime_return_source — DB 매핑 결정 후 구현"
        )


class DbProductRepository:
    """dt / cream DB 기반 ProductRepository (다음 단계)."""

    def __init__(self, engine: Any):
        self.engine = engine

    def load_etf_universe(self) -> "pd.DataFrame":
        raise NotImplementedError(
            "DbProductRepository.load_etf_universe — DB 매핑 결정 후 구현"
        )

    def load_fund_universe(self) -> "pd.DataFrame":
        raise NotImplementedError(
            "DbProductRepository.load_fund_universe — DB 매핑 결정 후 구현"
        )
