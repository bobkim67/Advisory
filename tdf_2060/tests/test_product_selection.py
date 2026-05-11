"""ProductSelectionTool — Phase B."""

from datetime import date

import pandas as pd


def _make_universe_result(products):
    from tdf_engine.domain.models import UniverseResult

    return UniverseResult(
        raw_count=len(products),
        filtered_count=len(products),
        products=products,
        excluded=[],
        diagnostics={},
    )


def _mk_product(pid, asset_key, score_hint, manager="X운용"):
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
        quant_score=score_hint * 50.0,  # 점수 영향
        quant_grade="B",
        return_1y=score_hint * 0.05,
        return_3y=score_hint * 0.10,
        sharpe_1y=score_hint,
        aum=1000.0,
        investment_limit=70.0,
        mvo_asset_class=asset_key,
    )


def test_selection_runs_for_simple_universe(loader):
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.selection.tool import ProductSelectionTool

    products = [
        _mk_product("1", "kr_equity", 1.5, manager="A"),
        _mk_product("2", "kr_equity", 1.0, manager="B"),
        _mk_product("3", "kr_equity", 0.8, manager="C"),
    ]
    universe_result = _make_universe_result(products)
    cfg = loader.load_universe_config()
    tool = ProductSelectionTool(universe_result, cfg, ProductType.ETF)

    asset_w = pd.Series({"kr_equity": 0.10})
    result = tool.run(asset_w)

    assert not result.selected.empty
    # 선택된 비중 합 <= asset_weight (clipping 가능)
    assert result.selected["weight"].sum() <= 0.10 + 1e-9


def test_unfilled_asset_recorded(loader):
    """자산군에 후보가 0 이면 unfilled_assets 에 기록."""
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.selection.tool import ProductSelectionTool

    products = [_mk_product("1", "kr_equity", 1.0)]
    universe_result = _make_universe_result(products)
    cfg = loader.load_universe_config()
    tool = ProductSelectionTool(universe_result, cfg, ProductType.ETF)

    asset_w = pd.Series({"kr_equity": 0.10, "us_growth_equity": 0.30})
    result = tool.run(asset_w)
    assert "us_growth_equity" in result.diagnostics["unfilled_by_asset_class"]
    assert (
        result.diagnostics["unfilled_by_asset_class"]["us_growth_equity"]["cause"]
        == "no_candidates_in_universe"
    )
