"""RegimeTAAPolicy 가 yaml 의 4개 regime tilt 를 모두 보유하는지."""

from tdf_engine.config.loader import ConfigLoader
from tdf_engine.domain.enums import Regime
from tdf_engine.taa.policy import RegimeTAAPolicy, RegimeTilt


def test_policy_has_all_four_regimes(loader: ConfigLoader):
    raw = loader.load_taa_config()
    policy = RegimeTAAPolicy.from_dict(raw.get("regime_tilts") or {})

    for r in (1, 2, 3, 4):
        tilt = policy.get(r)
        assert isinstance(tilt, RegimeTilt)
        assert tilt.bucket_tilts, f"regime {r}: bucket_tilts 비어있음"
        assert tilt.reason, f"regime {r}: reason 비어있음"


def test_regime_1_equity_overweight(loader: ConfigLoader):
    raw = loader.load_taa_config()
    policy = RegimeTAAPolicy.from_dict(raw.get("regime_tilts") or {})
    t1 = policy.get(Regime.EXPANSION)
    assert t1.bucket_tilts.get("equity", 0.0) > 0
    assert t1.bucket_tilts.get("fixed_income", 0.0) < 0


def test_regime_3_bond_overweight(loader: ConfigLoader):
    raw = loader.load_taa_config()
    policy = RegimeTAAPolicy.from_dict(raw.get("regime_tilts") or {})
    t3 = policy.get(Regime.SLOWDOWN)
    assert t3.bucket_tilts.get("equity", 0.0) < 0
    assert t3.bucket_tilts.get("fixed_income", 0.0) > 0


def test_regime_3_hy_underweight_as_risk_asset(loader: ConfigLoader):
    """HY 는 risk_asset 이므로 Regime 3 에서 underweight."""
    raw = loader.load_taa_config()
    policy = RegimeTAAPolicy.from_dict(raw.get("regime_tilts") or {})
    t3 = policy.get(Regime.SLOWDOWN)
    assert t3.asset_tilts.get("us_high_yield", 0.0) < 0
