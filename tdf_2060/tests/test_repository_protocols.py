"""Repository Protocol 정합성 + DB 구현체가 NotImplementedError 임을 검증."""

import pytest

from tdf_engine.repositories.db_repositories import (
    DbMarketDataRepository,
    DbProductRepository,
)
from tdf_engine.repositories.file_repositories import (
    FileMarketDataRepository,
    FileProductRepository,
)
from tdf_engine.repositories.interfaces import (
    MarketDataRepository,
    ProductRepository,
)


def test_file_repos_are_protocol_compliant(advisory_root):
    """runtime_checkable Protocol 인스턴스 검증."""
    if not advisory_root.exists():
        pytest.skip(f"advisory_root not found: {advisory_root}")
    fm = FileMarketDataRepository(advisory_root)
    fp = FileProductRepository(advisory_root)
    assert isinstance(fm, MarketDataRepository)
    assert isinstance(fp, ProductRepository)


def test_db_repos_raise_not_implemented():
    db_m = DbMarketDataRepository(engine=None)
    db_p = DbProductRepository(engine=None)
    with pytest.raises(NotImplementedError):
        db_m.load_asset_rt_vol()
    with pytest.raises(NotImplementedError):
        db_m.load_corr_matrix()
    with pytest.raises(NotImplementedError):
        db_m.load_regime_source()
    with pytest.raises(NotImplementedError):
        db_m.load_regime_return_source()
    with pytest.raises(NotImplementedError):
        db_p.load_etf_universe()
    with pytest.raises(NotImplementedError):
        db_p.load_fund_universe()
