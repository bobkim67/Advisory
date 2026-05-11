"""PlacementCalculator — Src 의 12개월 trailing 평균 차이.

식 (메타 row 검증 완료):
    Placement_t = Src_t - mean(Src_{t-window+1 .. t})
Excel `B13 = Src!B13 - AVERAGE(Src!B2:B13)` 와 1:1 정합.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd


class PlacementCalculator:
    DEFAULT_WINDOW = 12

    def __init__(self, window: int = DEFAULT_WINDOW):
        if window < 2:
            raise ValueError(f"window must be >= 2, got {window}")
        self.window = int(window)

    def calc(self, src):
        """Series 또는 DataFrame 입력 → 동일 shape 반환.

        앞 (window-1) 행은 NaN.
        """
        rolling_mean = src.rolling(window=self.window, min_periods=self.window).mean()
        return src - rolling_mean
