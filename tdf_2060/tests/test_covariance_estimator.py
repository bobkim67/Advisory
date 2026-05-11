"""σ + corr → Σ symmetric / 대각 = σ² 검증."""

import numpy as np
import pandas as pd

from tdf_engine.optimization.covariance import CovarianceEstimator


def test_cov_symmetric_and_diagonal():
    sigma = pd.Series({"A": 0.10, "B": 0.20, "C": 0.30})
    corr = pd.DataFrame(
        [[1.0, 0.2, -0.1],
         [0.2, 1.0, 0.4],
         [-0.1, 0.4, 1.0]],
        index=["A", "B", "C"],
        columns=["A", "B", "C"],
    )
    cov = CovarianceEstimator().estimate(sigma, corr)
    assert CovarianceEstimator.is_symmetric(cov)
    # 대각 = σ²
    assert np.isclose(cov.loc["A", "A"], 0.10**2)
    assert np.isclose(cov.loc["B", "B"], 0.20**2)
    assert np.isclose(cov.loc["C", "C"], 0.30**2)
    # off-diagonal = σ_i · σ_j · ρ_ij
    assert np.isclose(cov.loc["A", "B"], 0.10 * 0.20 * 0.2)
    assert np.isclose(cov.loc["A", "C"], 0.10 * 0.30 * -0.1)


def test_cov_handles_partial_overlap():
    sigma = pd.Series({"A": 0.1, "B": 0.2, "X": 0.5})
    corr = pd.DataFrame(
        [[1.0, 0.5], [0.5, 1.0]],
        index=["A", "B"],
        columns=["A", "B"],
    )
    cov = CovarianceEstimator().estimate(sigma, corr)
    # X 는 corr 에 없어 자동 제외
    assert list(cov.index) == ["A", "B"]
