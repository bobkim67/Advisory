"""Placement = rolling 12m mean diff, Velocity = ΔPlacement 검증."""

import numpy as np
import pandas as pd

from tdf_engine.regime.placement import PlacementCalculator
from tdf_engine.regime.velocity import VelocityCalculator


def test_placement_rolling_window():
    # 13개월 시계열 — 13번째에 첫 placement 값
    s = pd.Series(np.arange(1.0, 14.0))
    p = PlacementCalculator(window=12).calc(s)
    # 첫 11개월은 NaN (rolling 부족)
    assert p.iloc[:11].isna().all()
    # 12번째 = 12 - mean(1..12) = 12 - 6.5 = 5.5
    assert p.iloc[11] == 5.5
    # 13번째 = 13 - mean(2..13) = 13 - 7.5 = 5.5
    assert p.iloc[12] == 5.5


def test_velocity_diff():
    p = pd.Series([np.nan, 1.0, 2.5, 2.0, 1.5])
    v = VelocityCalculator().calc(p)
    assert v.iloc[0] != v.iloc[0]  # NaN
    assert v.iloc[2] == 1.5
    assert v.iloc[3] == -0.5
    assert v.iloc[4] == -0.5
