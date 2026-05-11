"""tdf_engine 의 모든 서브패키지를 import 할 수 있는지 sanity check."""


def test_top_level_import():
    import tdf_engine
    assert tdf_engine.__version__


def test_subpackages_import():
    import tdf_engine.domain
    import tdf_engine.repositories
    import tdf_engine.optimization
    import tdf_engine.regime
    import tdf_engine.taa
    import tdf_engine.universe
    import tdf_engine.selection
    import tdf_engine.portfolio
    import tdf_engine.config
    import tdf_engine.tools
    import tdf_engine.reporting

    # 모듈 참조가 살아있는지
    for mod in [
        tdf_engine.domain,
        tdf_engine.repositories,
        tdf_engine.optimization,
        tdf_engine.regime,
        tdf_engine.taa,
        tdf_engine.universe,
        tdf_engine.selection,
        tdf_engine.portfolio,
        tdf_engine.config,
    ]:
        assert mod is not None
