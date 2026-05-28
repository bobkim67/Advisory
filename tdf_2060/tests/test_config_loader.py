"""ConfigLoader가 5종 yaml을 정상 로드하고 10개 자산을 빌드하는지 검증."""

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


def test_load_assets_returns_ten(loader: ConfigLoader):
    assets = loader.load_assets()
    assert len(assets) == 10
    keys = {a.asset_key for a in assets}
    expected = {
        "kr_equity",
        "us_growth_equity",
        "us_value_equity",
        "dm_ex_us_equity",
        "em_equity",
        "gold",
        "kr_aggregate_bond",
        "kr_treasury_10y",
        "us_aggregate_bond",
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


def test_us_aggregate_bond_mapping(loader: ConfigLoader):
    """2026-05-27 — us_aggregate_bond 매핑 검증.

    LT-CMA (Asset_rt_vol) ticker = LBUSTRUU Index. SCIP id=278 LHMN0001 동일 지수.
    Asset_rt_vol 본체에 LBUSTRUU row 존재 → fallback_policy = error_if_missing.
    """
    assets = {a.asset_key: a for a in loader.load_assets()}
    us_agg = assets["us_aggregate_bond"]
    assert us_agg.fallback_policy is FallbackPolicy.ERROR_IF_MISSING
    assert us_agg.source_names.optimization == "LBUSTRUU Index"
    assert us_agg.source_names.regime_return is None
    assert us_agg.proxy_enabled is False
    assert us_agg.required is True
    assert us_agg.db_dataset_id == 278


def test_gold_mapping(loader: ConfigLoader):
    """2026-05-27 — gold 신규 자산 매핑 검증.

    LT-CMA Alternative bucket 의 XAU Curncy. 사용자 결정으로 equity bucket 편입.
    SCIP id=408 동일 ticker.
    """
    assets = {a.asset_key: a for a in loader.load_assets()}
    gold = assets["gold"]
    assert gold.bucket is Bucket.EQUITY              # 사용자 결정 equity 편입
    assert "risk_asset" in gold.flags
    assert "alternative" in gold.flags
    assert gold.source_names.optimization == "XAU Curncy"
    assert gold.db_dataset_id == 408
    assert gold.required is True


def test_dm_ex_us_and_kr_aggregate_have_split_sources(loader: ConfigLoader):
    """사용자 결정 #2, #3: 용도별 source 분리."""
    assets = {a.asset_key: a for a in loader.load_assets()}
    dm = assets["dm_ex_us_equity"]
    assert dm.source_names.optimization == "TAD09XU Index"
    assert dm.source_names.regime_return == "M2WOU Index"

    krb = assets["kr_aggregate_bond"]
    assert krb.source_names.optimization == "SPBKRCOT Index"
    assert krb.source_names.regime_return == "KISKALBI Index"
