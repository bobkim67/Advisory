"""RegimeAnalysisTool — Phase B."""

import pytest


def test_returns_latest_state_with_g7_default(advisory_root, loader):
    from tdf_engine.regime.tool import RegimeAnalysisTool
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    repo = FileMarketDataRepository(advisory_root)
    taa = loader.load_taa_config()
    tool = RegimeAnalysisTool(repo, taa)
    result = tool.run()

    assert result.latest_state.region == "G7"
    assert int(result.latest_state.regime) in (1, 2, 3, 4)
    assert result.placement.shape == result.velocity.shape == result.regime.shape


def test_classify_frame_matches_scalar_for_each_row(advisory_root, loader):
    from tdf_engine.regime.classifier import ECIRegimeClassifier
    from tdf_engine.regime.tool import RegimeAnalysisTool
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    repo = FileMarketDataRepository(advisory_root)
    taa = loader.load_taa_config()
    tool = RegimeAnalysisTool(repo, taa)
    result = tool.run()

    p = result.placement.iloc[:, 0]
    v = result.velocity.iloc[:, 0]
    r = result.regime.iloc[:, 0]
    common = p.dropna().index.intersection(v.dropna().index).intersection(r.dropna().index)
    for ts in common[-10:]:
        scalar = ECIRegimeClassifier.classify_scalar(float(p.loc[ts]), float(v.loc[ts]))
        assert int(r.loc[ts]) == int(scalar)


def test_unknown_region_raises(advisory_root, loader):
    from tdf_engine.regime.tool import RegimeAnalysisTool
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    repo = FileMarketDataRepository(advisory_root)
    taa = loader.load_taa_config()
    taa["regime_input"]["composite_region"] = "ZZZ"
    tool = RegimeAnalysisTool(repo, taa)
    with pytest.raises(ValueError, match=r"region"):
        tool.run()
