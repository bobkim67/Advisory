"""ConfigLoader가 5종 yaml을 정상 로드하고 9개 자산을 빌드하는지 검증."""

import pytest

from tdf_engine.config.loader import ConfigLoader
from tdf_engine.domain.enums import Bucket, FallbackPolicy
from tdf_engine.domain.models import AssetClassInfo


def test_load_tdf_config(loader: ConfigLoader):
    cfg = loader.load_tdf_config()
    assert cfg["target_date"] == 2060
    assert cfg["strategic_allocation"]["equity"] == 0.80
    assert cfg["strategic_allocation"]["fixed_income"] == 0.20


def test_load_optimization_config_default_objective(loader: ConfigLoader):
    cfg = loader.load_optimization_config()
    # 사용자 결정 #4
    assert cfg["optimization"]["objective"] == "max_sharpe"
    # 사용자 결정 #5: ERR 비활성
    assert cfg["err"]["enabled"] is False


def test_load_universe_and_taa(loader: ConfigLoader):
    u = loader.load_universe_config()
    t = loader.load_taa_config()
    assert "common" in u and "etf" in u and "fund" in u
    assert "regime_tilts" in t and "regime_input" in t


def test_load_assets_returns_nine(loader: ConfigLoader):
    assets = loader.load_assets()
    assert len(assets) == 9
    keys = {a.asset_key for a in assets}
    expected = {
        "kr_equity",
        "us_growth_equity",
        "us_value_equity",
        "dm_ex_us_equity",
        "em_equity",
        "kr_aggregate_bond",
        "kr_treasury_10y",
        "us_treasury_30y",
        "us_high_yield",
    }
    assert keys == expected


def test_hy_has_risk_asset_and_credit_flags(loader: ConfigLoader):
    """HY 는 fixed_income bucket + risk_asset + credit flag (사용자 결정/spec)."""
    assets = {a.asset_key: a for a in loader.load_assets()}
    hy = assets["us_high_yield"]
    assert hy.bucket is Bucket.FIXED_INCOME
    assert "risk_asset" in hy.flags
    assert "credit" in hy.flags


def test_us_treasury_30y_explicit_proxy_only(loader: ConfigLoader):
    """사용자 결정 #1: us_treasury_30y 는 explicit_proxy_only.

    Phase C.2 — DB 매핑 확정 (BRFUT004) 으로 source_names.optimization 채움.
    fallback_policy 와 required 정책은 그대로 유지 (file 모드 explicit error).
    """
    assets = {a.asset_key: a for a in loader.load_assets()}
    ust30 = assets["us_treasury_30y"]
    assert ust30.fallback_policy is FallbackPolicy.EXPLICIT_PROXY_ONLY
    # Phase C.2 후: source_names.optimization 은 BRFUT004 (KIS 미국채 30Y TR 지수)
    assert ust30.source_names.optimization == "BRFUT004"
    assert ust30.source_names.regime_return is None
    assert ust30.proxy_enabled is False
    assert ust30.required is True


def test_dm_ex_us_and_kr_aggregate_have_split_sources(loader: ConfigLoader):
    """사용자 결정 #2, #3: 용도별 source 분리."""
    assets = {a.asset_key: a for a in loader.load_assets()}
    dm = assets["dm_ex_us_equity"]
    assert dm.source_names.optimization == "TAD09XU Index"
    assert dm.source_names.regime_return == "M2WOU Index"

    krb = assets["kr_aggregate_bond"]
    assert krb.source_names.optimization == "SPBKRCOT Index"
    assert krb.source_names.regime_return == "KISKALBI Index"
