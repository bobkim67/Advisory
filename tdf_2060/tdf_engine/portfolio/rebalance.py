"""RebalanceEngine — 현재 포트폴리오 vs 타겟 포트폴리오 → 매매 지시.

Phase A: skeleton 만. 다음 단계 (또는 그 이후) 에서 구현.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

logger = logging.getLogger(__name__)


class RebalanceEngine:
    @staticmethod
    def diff(
        current: "pd.Series",
        target: "pd.Series",
        threshold: float = 0.005,
    ) -> "pd.Series":
        """target − current. threshold 이내 무시."""
        raise NotImplementedError("RebalanceEngine.diff — 향후 단계")
