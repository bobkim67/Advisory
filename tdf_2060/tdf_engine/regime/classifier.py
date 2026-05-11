"""ECIRegimeClassifier — Placement / Velocity 의 부호 조합 → 1~4.

식 (메타 row 검증 완료):
    IF(P > 0, IF(V > 0, 1, 4), IF(V > 0, 2, 3))
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tdf_engine.domain.enums import Regime

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd


class ECIRegimeClassifier:
    """ECI sign-based 분류."""

    @staticmethod
    def classify_scalar(placement: float, velocity: float) -> Regime:
        if placement > 0:
            return Regime.EXPANSION if velocity > 0 else Regime.DECELERATION
        else:
            return Regime.RECOVERY if velocity > 0 else Regime.SLOWDOWN

    @staticmethod
    def classify_frame(
        placement: "pd.DataFrame",
        velocity: "pd.DataFrame",
    ) -> "pd.DataFrame":
        """date × region (또는 Series) 분류. NaN 입력은 pd.NA 로 보존."""
        import numpy as np
        import pandas as pd

        p = placement
        v = velocity
        if p.shape != v.shape:
            raise ValueError(
                f"placement shape {p.shape} != velocity shape {v.shape}"
            )

        p_arr = np.asarray(p, dtype=float)
        v_arr = np.asarray(v, dtype=float)

        out = np.where(
            p_arr > 0,
            np.where(v_arr > 0, 1, 4),
            np.where(v_arr > 0, 2, 3),
        ).astype(float)

        # NaN 보존
        nan_mask = np.isnan(p_arr) | np.isnan(v_arr)
        out[nan_mask] = np.nan

        if isinstance(p, pd.Series):
            return pd.Series(out, index=p.index, name=p.name)
        return pd.DataFrame(out, index=p.index, columns=p.columns)
