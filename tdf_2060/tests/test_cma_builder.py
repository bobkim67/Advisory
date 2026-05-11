"""CapitalMarketAssumptionBuilder — Phase B."""

import pytest


def test_builds_cma_for_9_assets(augmented_source_root, augmented_assets):
    from tdf_engine.optimization.cma import CapitalMarketAssumptionBuilder
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    repo = FileMarketDataRepository(augmented_source_root)
    builder = CapitalMarketAssumptionBuilder(repo, augmented_assets)
    cma = builder.build()

    assert len(cma.expected_returns) == 9
    assert len(cma.volatilities) == 9
    assert cma.correlation.shape == (9, 9)
    assert cma.covariance.shape == (9, 9)

    # σ, E[R] 합리적 범위
    assert (cma.volatilities > 0).all()
    assert (cma.volatilities < 1.0).all()
    assert "us_treasury_30y" in cma.expected_returns.index


def test_raises_when_required_asset_missing(advisory_root, loader):
    """원본 Advisory/ 데이터에는 ust30 이 없음 → (b) 강한 error."""
    from tdf_engine.optimization.cma import CapitalMarketAssumptionBuilder
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    repo = FileMarketDataRepository(advisory_root)
    assets = loader.load_assets()
    builder = CapitalMarketAssumptionBuilder(repo, assets)
    with pytest.raises(ValueError, match=r"(?i)required|missing|ust30|us_treasury"):
        builder.build()


def test_diagnostics_contains_metadata(augmented_source_root, augmented_assets):
    from tdf_engine.optimization.cma import CapitalMarketAssumptionBuilder
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    repo = FileMarketDataRepository(augmented_source_root)
    builder = CapitalMarketAssumptionBuilder(repo, augmented_assets)
    cma = builder.build()
    assert cma.diagnostics["n_assets"] == 9
    assert "ticker_by_key" in cma.diagnostics
    assert cma.diagnostics["ust30_policy"] == "strict_error_b"


def test_covariance_is_symmetric(augmented_source_root, augmented_assets):
    import numpy as np
    from tdf_engine.optimization.cma import CapitalMarketAssumptionBuilder
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    repo = FileMarketDataRepository(augmented_source_root)
    builder = CapitalMarketAssumptionBuilder(repo, augmented_assets)
    cma = builder.build()
    arr = cma.covariance.to_numpy()
    assert np.allclose(arr, arr.T, atol=1e-10)
