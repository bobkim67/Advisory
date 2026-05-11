"""End-to-end Fund — Phase B happy-path."""


def test_e2e_fund_pipeline(augmented_source_root, augmented_assets, loader):
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.optimization.tool import OptimizationTool
    from tdf_engine.portfolio.tool import PortfolioConstructionTool
    from tdf_engine.regime.tool import RegimeAnalysisTool
    from tdf_engine.repositories.file_repositories import (
        FileMarketDataRepository,
        FileProductRepository,
    )
    from tdf_engine.selection.tool import ProductSelectionTool
    from tdf_engine.taa.tool import TAAOverlayTool
    from tdf_engine.universe.tool import UniverseTool

    market_repo = FileMarketDataRepository(augmented_source_root)
    product_repo = FileProductRepository(augmented_source_root)

    tdf = loader.load_tdf_config()
    opt_cfg = loader.load_optimization_config()
    taa_cfg = loader.load_taa_config()
    universe_cfg = loader.load_universe_config()

    pt = ProductType.FUND
    opt_tool = OptimizationTool(market_repo, augmented_assets, tdf, opt_cfg)
    regime_tool = RegimeAnalysisTool(market_repo, taa_cfg)
    taa_tool = TAAOverlayTool(taa_cfg, assets=augmented_assets)
    universe_tool = UniverseTool(product_repo, universe_cfg, pt)

    def factory(uni_res):
        return ProductSelectionTool(uni_res, universe_cfg, pt)

    construction = PortfolioConstructionTool(
        optimization_tool=opt_tool,
        regime_tool=regime_tool,
        taa_tool=taa_tool,
        universe_tool=universe_tool,
        selection_tool_factory=factory,
        tdf_config=tdf,
        universe_config=universe_cfg,
    )
    portfolio = construction.run(pt)

    assert abs(float(portfolio.asset_weights.sum()) - 1.0) < 1e-4
    assert portfolio.portfolio_type is ProductType.FUND
