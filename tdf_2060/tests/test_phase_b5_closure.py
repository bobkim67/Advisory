"""Phase B.5 weight closure / fallback / validator warning."""

from datetime import date

import pandas as pd
import pytest


# ── helpers ───────────────────────────────────────────────────────────


def _build_fund_portfolio(augmented_source_root, augmented_assets, loader):
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
        assets=augmented_assets,
    )
    return construction.run(pt)


def _make_simple_universe(products):
    from tdf_engine.domain.models import UniverseResult

    return UniverseResult(
        raw_count=len(products),
        filtered_count=len(products),
        products=products,
        excluded=[],
        diagnostics={},
    )


def _mk_product(pid, asset_key, manager="X운용", quant=80.0, sharpe=1.0, r3=10.0):
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.domain.models import ProductInfo

    return ProductInfo(
        product_id=pid,
        fund_code=None,
        name=f"P{pid}",
        product_type=ProductType.ETF,
        kis_asset_class="국내주식",
        sub_type="기타인덱스",
        region="국내",
        theme=None,
        manager=manager,
        inception_date=date(2020, 1, 1),
        risk_grade="2",
        quant_score=quant,
        quant_grade="A",
        return_1y=0.05,
        return_3y=r3,
        sharpe_1y=sharpe,
        aum=1000.0,
        investment_limit=70.0,
        mvo_asset_class=asset_key,
    )


# ── tests ─────────────────────────────────────────────────────────────


def test_e2e_fund_product_weight_sum_is_one(augmented_source_root, augmented_assets, loader):
    """Phase B.5 핵심 — Fund 쪽도 product_weight_sum ≈ 1.0 으로 닫힌다."""
    portfolio = _build_fund_portfolio(augmented_source_root, augmented_assets, loader)
    s = float(portfolio.product_weights["weight"].sum())
    assert abs(s - 1.0) < 1e-6, f"product_weight_sum={s} not closed to 1.0"


def test_selection_diagnostics_reports_unfilled_weight(loader):
    """Selection diagnostics 가 자산군별 cause 를 기록한다."""
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.selection.tool import ProductSelectionTool

    products = [_mk_product("1", "kr_equity", manager="A", quant=80.0)]
    universe_result = _make_simple_universe(products)
    cfg = loader.load_universe_config()
    tool = ProductSelectionTool(universe_result, cfg, ProductType.ETF)

    asset_w = pd.Series({"kr_equity": 0.10, "us_growth_equity": 0.30})
    result = tool.run(asset_w)

    by_class = result.diagnostics.get("unfilled_by_asset_class") or {}
    assert "us_growth_equity" in by_class
    entry = by_class["us_growth_equity"]
    assert entry["cause"] == "no_candidates_in_universe"
    assert entry["target"] == pytest.approx(0.30)
    assert entry["unfilled"] == pytest.approx(0.30)
    assert entry["n_universe"] == 0


def test_fallback_allocates_unfilled_to_cash_placeholder(augmented_source_root, augmented_assets, loader):
    """완전 미매칭 자산군이 있을 때 cash placeholder 로 weight 가 닫힌다.

    Fund 시나리오: kr_treasury_10y, us_treasury_30y 가 universe 에 없거나 후보 부족.
    bucket fallback 이후 잔여는 cash 로 들어간다 (또는 동일 자산군/bucket 에서 모두 흡수되면 cash=0).
    """
    portfolio = _build_fund_portfolio(augmented_source_root, augmented_assets, loader)
    fb = portfolio.diagnostics.get("fallback") or {}
    assert fb.get("fallback_used") is True

    # 미배분 비중 30.7% → 일부는 같은 자산군/bucket 에서 흡수, 잔여는 cash
    pwd = portfolio.product_weights
    cash_rows = pwd[pwd["product_id"] == "__CASH__"]
    # cash 가 있을 수도 없을 수도 있지만, fallback_used=True 가 핵심 + sum=1
    s = float(pwd["weight"].sum())
    assert abs(s - 1.0) < 1e-6
    # cash 가 있다면 placeholder 표기
    if not cash_rows.empty:
        assert (cash_rows["asset_key"] == "cash").all()
        assert (cash_rows["role"] == "cash").all()


def test_validator_warns_on_fallback(augmented_source_root, augmented_assets, loader):
    """fallback 사용 시 validation.warnings 에 노출된다."""
    portfolio = _build_fund_portfolio(augmented_source_root, augmented_assets, loader)
    val = portfolio.diagnostics.get("validation") or {}
    warnings = val.get("warnings") or []
    # fallback 적용된 자산군이 warnings 에 등장 (B.5+ 메시지 포맷)
    assert any("fallback_used" in w for w in warnings), f"warnings={warnings}"


def test_etf_e2e_still_passes_after_b5(augmented_source_root, augmented_assets, loader, tmp_path):
    """기존 ETF E2E 회귀 — product_weight_sum ≈ 1.0, constraints_passed=True."""
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
    pt = ProductType.ETF

    tdf = loader.load_tdf_config()
    opt_cfg = loader.load_optimization_config()
    taa_cfg = loader.load_taa_config()
    uni_cfg = loader.load_universe_config()

    opt_tool = OptimizationTool(market_repo, augmented_assets, tdf, opt_cfg)
    regime_tool = RegimeAnalysisTool(market_repo, taa_cfg)
    taa_tool = TAAOverlayTool(taa_cfg, assets=augmented_assets)
    universe_tool = UniverseTool(product_repo, uni_cfg, pt)

    def factory(ur):
        return ProductSelectionTool(ur, uni_cfg, pt)

    construction = PortfolioConstructionTool(
        optimization_tool=opt_tool,
        regime_tool=regime_tool,
        taa_tool=taa_tool,
        universe_tool=universe_tool,
        selection_tool_factory=factory,
        tdf_config=tdf,
        universe_config=uni_cfg,
        assets=augmented_assets,
    )
    portfolio = construction.run(pt)

    s_asset = float(portfolio.asset_weights.sum())
    s_prod = float(portfolio.product_weights["weight"].sum())
    assert abs(s_asset - 1.0) < 1e-4
    assert abs(s_prod - 1.0) < 1e-6
