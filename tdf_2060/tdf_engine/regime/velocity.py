"""VelocityCalculator — Placement 의 1개월 차분.

식 (메타 row 검증 완료):
    Velocity_t = Placement_t - Placement_{t-1}
Excel `B14 = Placement!B14 - Placement!B13` 와 1:1 정합.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd


class VelocityCalculator:
    @staticmethod
    def calc(placement):
        """Series 또는 DataFrame 입력. 첫 행은 NaN."""
        return placement.diff(1)
