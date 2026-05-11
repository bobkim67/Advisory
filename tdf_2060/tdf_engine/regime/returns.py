"""AssetReturnCalculator + RegimeReturnAnalyzer.

regimeAnalysis_src (월말 지수 레벨) → 월간 수익률 → regime 별 평균.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

logger = logging.getLogger(__name__)


class AssetReturnCalculator:
    """월말 지수 레벨 → 월간 수익률.

    r_t = level_t / level_{t-1} - 1
    """

    @staticmethod
    def monthly_returns(levels: "pd.DataFrame") -> "pd.DataFrame":
        if levels.empty:
            raise ValueError("levels DataFrame is empty")
        rt = levels.pct_change()
        # 첫 row 는 NaN — drop
        rt = rt.iloc[1:]
        return rt


class RegimeReturnAnalyzer:
    """월수익률 + regime series → regime × asset 평균수익률."""

    @staticmethod
    def analyze(
        monthly_returns: "pd.DataFrame",
        regime_series: "pd.Series",
    ) -> "pd.DataFrame":
        import pandas as pd

        # 두 시계열을 월말 타임스탬프로 통일하여 정렬
        rs = regime_series.copy()
        if not isinstance(rs.index, pd.DatetimeIndex):
            rs.index = pd.to_datetime(rs.index)
        rs.index = rs.index.to_period("M").to_timestamp("M")
        rs = rs.sort_index()

        mr = monthly_returns.copy()
        if not isinstance(mr.index, pd.DatetimeIndex):
            mr.index = pd.to_datetime(mr.index)
        mr.index = mr.index.to_period("M").to_timestamp("M")

        joined = mr.join(rs.rename("__regime__"), how="left")
        joined["__regime__"] = joined["__regime__"].ffill()

        valid = joined.dropna(subset=["__regime__"])
        if valid.empty:
            raise ValueError("regime 과 monthly_returns 의 교집합이 비어있음")

        grouped = valid.groupby("__regime__").mean(numeric_only=True)
        grouped.index = grouped.index.astype(int)
        grouped.index.name = "regime"
        return grouped
