"""Repository Protocol 정의.

계산 로직과 데이터 접근을 분리한다. Tool 들은 이 Protocol 만 의존.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd


@runtime_checkable
class MarketDataRepository(Protocol):
    """자산 가격 / Regime 원천 데이터 접근."""

    def load_asset_rt_vol(self) -> "pd.DataFrame":
        """Asset_rt_vol 원본 (Asset Class, Ticker, Name, σ, E[R])."""

    def load_corr_matrix(self) -> "pd.DataFrame":
        """Corr_mat 원본 (자산명 × 자산명)."""

    def load_regime_source(self) -> "pd.DataFrame":
        """regime_src — date × 22 region OECD CLI."""

    def load_regime_return_source(self) -> "pd.DataFrame":
        """regimeAnalysis_src — date × 26 자산 월말 지수."""


@runtime_checkable
class ProductRepository(Protocol):
    """ETF / Fund 유니버스 접근."""

    def load_etf_universe(self) -> "pd.DataFrame":
        """etf_list 원본."""

    def load_fund_universe(self) -> "pd.DataFrame":
        """fund_list 원본."""
