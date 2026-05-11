"""CovarianceEstimator — σ + correlation → covariance matrix.

Σ = D · C · D, where D = diag(σ).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

logger = logging.getLogger(__name__)


class CovarianceEstimator:
    """σ vector + correlation matrix → covariance matrix.

    Σ = D · C · D, where D = diag(σ).
    """

    @staticmethod
    def estimate(
        volatilities: "pd.Series",
        correlation: "pd.DataFrame",
    ) -> "pd.DataFrame":
        """Σ = D @ C @ D.

        Parameters
        ----------
        volatilities : pd.Series
            asset_key indexed σ vector (annualized, non-negative).
        correlation : pd.DataFrame
            asset_key × asset_key correlation. 대각=1, 대칭.

        Returns
        -------
        pd.DataFrame
            asset_key × asset_key covariance.

        Notes
        -----
        - correlation 의 index/columns 가 정합되지 않으면 ValueError.
        - volatilities 와 correlation 의 키가 정확히 일치하지 않으면, **둘의 교집합**으로
          축소하여 반환한다 (silent fallback 이 아니라 명시 reindex).
        - 음의 분산은 raise.
        """
        import numpy as np
        import pandas as pd

        if list(correlation.index) != list(correlation.columns):
            raise ValueError("correlation matrix index와 columns가 다릅니다")

        # σ 와 corr 의 공통 키만 사용 (silent fill 금지, 명시 교집합)
        common = [k for k in correlation.index if k in volatilities.index]
        if not common:
            raise ValueError("volatilities 와 correlation 사이에 공통 자산 없음")

        sigma = volatilities.loc[common].astype(float)
        if (sigma < 0).any():
            raise ValueError(f"음의 변동성 존재: {sigma[sigma < 0].to_dict()}")

        c = correlation.loc[common, common].astype(float).to_numpy()
        s = sigma.to_numpy()
        cov = (s[:, None] * c) * s[None, :]
        return pd.DataFrame(cov, index=common, columns=common)

    @staticmethod
    def is_symmetric(matrix: "pd.DataFrame", atol: float = 1e-10) -> bool:
        import numpy as np

        a = matrix.to_numpy()
        if a.shape[0] != a.shape[1]:
            return False
        return bool(np.allclose(a, a.T, atol=atol))
