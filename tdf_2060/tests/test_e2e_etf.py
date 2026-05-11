"""End-to-end ETF — Phase B happy-path."""

import json
from pathlib import Path


def test_e2e_etf_pipeline(augmented_source_root, augmented_assets, loader, tmp_path):
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
    from tdf_engine.tools.build_portfolio import write_outputs
    from tdf_engine.universe.tool import UniverseTool

    market_repo = FileMarketDataRepository(augmented_source_root)
    product_repo = FileProductRepository(augmented_source_root)

    tdf = loader.load_tdf_config()
    opt_cfg = loader.load_optimization_config()
    taa_cfg = loader.load_taa_config()
    universe_cfg = loader.load_universe_config()

    pt = ProductType.ETF
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

    # asset weights sum=1 (정책 #6, hard)
    assert abs(float(portfolio.asset_weights.sum()) - 1.0) < 1e-4

    # long-only (정책 #4, hard)
    assert (portfolio.asset_weights >= -1e-9).all()

    # Phase D relaxed: bucket 합계는 telemetry 로만 노출. hard bound 검증 안 함.
    # (이전 [0.74, 0.86] / [0.14, 0.26] 가정은 D-01 closed 로 제거)
    eq_keys = [a.asset_key for a in augmented_assets if a.bucket.value == "equity"]
    fi_keys = [a.asset_key for a in augmented_assets if a.bucket.value == "fixed_income"]
    eq_sum = float(portfolio.asset_weights.loc[eq_keys].sum())
    fi_sum = float(portfolio.asset_weights.loc[fi_keys].sum())
    # hard: 양쪽 모두 [0, 1], 합 = 1.0
    assert 0.0 <= eq_sum <= 1.0
    assert 0.0 <= fi_sum <= 1.0
    assert abs((eq_sum + fi_sum) - 1.0) < 1e-6

    # product 단위 결과
    assert not portfolio.product_weights.empty

    # csv/json 출력
    csv_path, json_path = write_outputs(portfolio, tmp_path / "out", pt.value)
    assert csv_path.exists()
    assert json_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["portfolio_type"] == "etf"
    assert "asset_weights" in payload
    assert "product_weights" in payload
    assert payload["asset_weight_sum"] > 0.99
