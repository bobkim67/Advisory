"""UniverseTool — Phase B."""


def test_etf_universe_runs(advisory_root, loader):
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.repositories.file_repositories import FileProductRepository
    from tdf_engine.universe.tool import UniverseTool

    repo = FileProductRepository(advisory_root)
    cfg = loader.load_universe_config()
    tool = UniverseTool(repo, cfg, ProductType.ETF)
    result = tool.run()

    assert result.raw_count > 0
    assert result.filtered_count > 0
    assert result.filtered_count <= result.raw_count
    # 분류된 자산이 1개 이상
    classes = {p.mvo_asset_class for p in result.products if p.mvo_asset_class}
    assert len(classes) >= 1


def test_fund_universe_runs(advisory_root, loader):
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.repositories.file_repositories import FileProductRepository
    from tdf_engine.universe.tool import UniverseTool

    repo = FileProductRepository(advisory_root)
    cfg = loader.load_universe_config()
    tool = UniverseTool(repo, cfg, ProductType.FUND)
    result = tool.run()

    assert result.raw_count > 0
    assert result.filtered_count > 0


def test_excluded_threshold_visible(advisory_root, loader):
    """30% 이상 제외되는지 확인 — diagnostics 가 그것을 노출."""
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.repositories.file_repositories import FileProductRepository
    from tdf_engine.universe.tool import UniverseTool

    repo = FileProductRepository(advisory_root)
    cfg = loader.load_universe_config()
    tool = UniverseTool(repo, cfg, ProductType.ETF)
    result = tool.run()
    assert result.diagnostics["raw_count"] == result.raw_count
    assert "filtered_count" in result.diagnostics
