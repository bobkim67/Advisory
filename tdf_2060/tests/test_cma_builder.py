"""CapitalMarketAssumptionBuilder — Phase B."""

import pytest


def test_builds_cma_for_10_assets(augmented_source_root, augmented_assets):
    from tdf_engine.optimization.cma import CapitalMarketAssumptionBuilder
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    repo = FileMarketDataRepository(augmented_source_root)
    builder = CapitalMarketAssumptionBuilder(repo, augmented_assets)
    cma = builder.build()

    assert len(cma.expected_returns) == 10
    assert len(cma.volatilities) == 10
    assert cma.correlation.shape == (10, 10)
    assert cma.covariance.shape == (10, 10)

    # σ, E[R] 합리적 범위
    assert (cma.volatilities > 0).all()
    assert (cma.volatilities < 1.0).all()
    assert "us_aggregate_bond" in cma.expected_returns.index
    assert "gold" in cma.expected_returns.index


def test_diagnostics_contains_metadata(augmented_source_root, augmented_assets):
    from tdf_engine.optimization.cma import CapitalMarketAssumptionBuilder
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    repo = FileMarketDataRepository(augmented_source_root)
    builder = CapitalMarketAssumptionBuilder(repo, augmented_assets)
    cma = builder.build()
    assert cma.diagnostics["n_assets"] == 10
    assert "ticker_by_key" in cma.diagnostics


def test_covariance_is_symmetric(augmented_source_root, augmented_assets):
    import numpy as np
    from tdf_engine.optimization.cma import CapitalMarketAssumptionBuilder
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    repo = FileMarketDataRepository(augmented_source_root)
    builder = CapitalMarketAssumptionBuilder(repo, augmented_assets)
    cma = builder.build()
    arr = cma.covariance.to_numpy()
    assert np.allclose(arr, arr.T, atol=1e-10)
