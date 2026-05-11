"""RegimeReturn — Phase B."""

import pandas as pd


def test_monthly_returns_drops_first_row():
    from tdf_engine.regime.returns import AssetReturnCalculator

    levels = pd.DataFrame({"a": [100.0, 110.0, 121.0]})
    rt = AssetReturnCalculator.monthly_returns(levels)
    assert len(rt) == 2
    assert abs(rt.iloc[0, 0] - 0.10) < 1e-9
    assert abs(rt.iloc[1, 0] - 0.10) < 1e-9


def test_regime_return_groupby_mean():
    from tdf_engine.regime.returns import RegimeReturnAnalyzer

    idx = pd.date_range("2020-01-31", periods=4, freq="ME")
    monthly = pd.DataFrame(
        {"a": [0.10, 0.20, -0.05, 0.0]}, index=idx
    )
    regime = pd.Series([1, 1, 3, 3], index=idx)

    out = RegimeReturnAnalyzer.analyze(monthly, regime)
    assert int(out.loc[1, "a"] * 100) == 15
    assert abs(out.loc[3, "a"] - (-0.025)) < 1e-9


def test_regime_return_tool_runs(advisory_root, loader):
    from tdf_engine.regime.tool import RegimeAnalysisTool, RegimeReturnTool
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    repo = FileMarketDataRepository(advisory_root)
    assets = loader.load_assets()
    taa = loader.load_taa_config()

    regime_result = RegimeAnalysisTool(repo, taa).run()
    rr = RegimeReturnTool(repo, assets).run(
        regime_result.regime[regime_result.diagnostics["region"]]
    )

    assert not rr.regime_avg.empty
    # 매칭된 자산이 1개 이상
    assert rr.regime_avg.shape[1] >= 1
