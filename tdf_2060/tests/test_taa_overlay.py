"""TAAOverlayEngine — Phase B."""

import pandas as pd
import pytest


@pytest.fixture
def saa() -> pd.Series:
    return pd.Series(
        {
            "kr_equity": 0.10,
            "us_growth_equity": 0.30,
            "us_value_equity": 0.20,
            "dm_ex_us_equity": 0.12,
            "em_equity": 0.08,
            "kr_aggregate_bond": 0.08,
            "kr_treasury_10y": 0.04,
            "us_treasury_30y": 0.05,
            "us_high_yield": 0.03,
        }
    )


def test_regime1_increases_equity_bucket(saa, loader):
    from tdf_engine.taa.tool import TAAOverlayTool

    assets = loader.load_assets()
    tool = TAAOverlayTool(loader.load_taa_config(), assets=assets)
    result = tool.run(saa, regime=1)

    eq_keys = [a.asset_key for a in assets if a.bucket.value == "equity"]
    saa_eq = float(saa.loc[eq_keys].sum())
    taa_eq = float(result.taa_weights.loc[eq_keys].sum())
    assert taa_eq > saa_eq - 1e-9


def test_taa_weights_sum_to_one(saa, loader):
    from tdf_engine.taa.tool import TAAOverlayTool

    assets = loader.load_assets()
    tool = TAAOverlayTool(loader.load_taa_config(), assets=assets)
    for r in (1, 2, 3, 4):
        result = tool.run(saa, regime=r)
        assert abs(float(result.taa_weights.sum()) - 1.0) < 1e-9


def test_per_asset_tilt_within_cap(saa, loader):
    from tdf_engine.taa.tool import TAAOverlayTool

    assets = loader.load_assets()
    cfg = loader.load_taa_config()
    cap = float(cfg["constraints"]["per_asset_max_tilt"])
    tool = TAAOverlayTool(cfg, assets=assets)
    for r in (1, 2, 3, 4):
        result = tool.run(saa, regime=r)
        tilt_max = float(result.tilts.abs().max())
        # cash-neutral 보정으로 약간 초과될 수 있어 작은 여유분 허용
        assert tilt_max <= cap + 0.005


def test_reasons_attached(saa, loader):
    from tdf_engine.taa.tool import TAAOverlayTool

    assets = loader.load_assets()
    tool = TAAOverlayTool(loader.load_taa_config(), assets=assets)
    result = tool.run(saa, regime=1)
    assert any(result.reasons.values())
