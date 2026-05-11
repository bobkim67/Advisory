"""Phase C-pre — classifier YAML 외부화 + match_reason + diagnostics +
quant_grade_policy 옵션화."""

from datetime import date

import pandas as pd
import pytest


# ── helpers ───────────────────────────────────────────────────────────


def _mk_product(pid, asset_key, manager="X운용", grade="C", quant=50.0,
                sharpe=0.8, r3=20.0, aum=500.0):
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
        quant_grade=grade,
        return_1y=0.05,
        return_3y=r3,
        sharpe_1y=sharpe,
        aum=aum,
        investment_limit=70.0,
        mvo_asset_class=asset_key,
    )


def _make_universe_result(products):
    from tdf_engine.domain.models import UniverseResult

    return UniverseResult(
        raw_count=len(products),
        filtered_count=len(products),
        products=products,
        excluded=[],
        diagnostics={},
    )


# ── classifier yaml + match_reason ────────────────────────────────────


def test_classifier_loads_yaml_rules(loader):
    from tdf_engine.universe.classifier import ProductClassifier, load_rules

    raw = loader.load_classification_rules_raw()
    assert raw is not None, "universe_classification.yaml 가 로드되어야 함"

    rules = load_rules(raw)
    assert len(rules) > 0
    # priority 오름차순 정렬되어야 함
    priorities = [r.priority for r in rules]
    assert priorities == sorted(priorities)
    # 9개 자산군 모두 등장
    asset_keys = {r.asset_key for r in rules}
    expected = {
        "kr_equity", "us_growth_equity", "us_value_equity",
        "dm_ex_us_equity", "em_equity",
        "kr_aggregate_bond", "kr_treasury_10y", "us_treasury_30y", "us_high_yield",
    }
    assert expected.issubset(asset_keys)

    cls = ProductClassifier(rules)
    # 룰 적용 — 미국 장기국채 펀드 매칭
    row = {
        "펀드명(Short)": "삼성미국투자등급장기채권자H[채권-재간접]",
        "대유형(KIS MP)": "해외채권",
        "지역": "미국",
        "소유형": "북미채권",
    }
    ak, reason = cls.classify(row)
    assert ak == "us_treasury_30y"
    assert reason and "미국" in reason or "장기" in reason or "투자등급장기채" in reason


def test_classifier_records_match_reason():
    from tdf_engine.universe.classifier import ProductClassifier

    cls = ProductClassifier()
    row = {
        "펀드명(Short)": "한국투자글로벌하이일드(채권)",
        "대유형(KIS MP)": "해외채권",
        "지역": "글로벌",
        "소유형": "글로벌하이일드채권",
    }
    ak, reason = cls.classify(row)
    assert ak == "us_high_yield"
    assert reason is not None
    assert "하이일드" in reason or "keyword" in reason


def test_fund_bond_products_are_classified_when_keywords_match(advisory_root, loader):
    """Fund 채권 펀드가 룰 보강으로 매칭된다 (kr_treasury_10y / us_treasury_30y / etc)."""
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.repositories.file_repositories import FileProductRepository
    from tdf_engine.universe.classifier import ProductClassifier, load_rules
    from tdf_engine.universe.tool import UniverseTool

    raw = loader.load_classification_rules_raw()
    classifier = ProductClassifier(load_rules(raw))
    repo = FileProductRepository(advisory_root)
    cfg = loader.load_universe_config()

    tool = UniverseTool(repo, cfg, ProductType.FUND, classifier=classifier)
    result = tool.run()

    by_class = result.diagnostics["classified_by_asset_class"]
    # 보강 후엔 적어도 us_treasury_30y / kr_treasury_10y / us_high_yield / kr_aggregate_bond 중
    # 다수가 매칭되어야 함 (이전엔 0이었음)
    bond_classes_with_matches = sum(
        1 for k in ("us_treasury_30y", "kr_treasury_10y", "us_high_yield", "kr_aggregate_bond")
        if by_class.get(k, 0) > 0
    )
    assert bond_classes_with_matches >= 3, (
        f"Fund 채권 룰 보강 후 4개 자산군 중 3개 이상이 매칭되어야 함. "
        f"현재: {{k: by_class.get(k, 0) for k in (...)}}"
    )


def test_universe_diagnostics_reports_unclassified_samples(advisory_root, loader):
    """diagnostics 에 unclassified_samples / classified_by_asset_class /
    asset_classes_with_zero_count 등이 채워진다."""
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.repositories.file_repositories import FileProductRepository
    from tdf_engine.universe.classifier import ProductClassifier, load_rules
    from tdf_engine.universe.tool import UniverseTool

    raw = loader.load_classification_rules_raw()
    classifier = ProductClassifier(load_rules(raw))
    repo = FileProductRepository(advisory_root)
    cfg = loader.load_universe_config()

    tool = UniverseTool(repo, cfg, ProductType.FUND, classifier=classifier)
    result = tool.run()
    d = result.diagnostics

    assert "total_products" in d
    assert "passed_filter_count" in d
    assert "classified_count" in d
    assert "unclassified_count" in d
    assert "classified_by_asset_class" in d
    assert "unclassified_samples" in d
    assert "asset_classes_with_zero_count" in d
    assert "match_reasons_by_asset_class" in d
    # 분류된 자산군 1개 이상
    assert d["classified_count"] > 0
    # match_reasons 가 자산군별로 채워짐
    assert any(d["match_reasons_by_asset_class"].values())


# ── quant_grade_policy ─────────────────────────────────────────────────


def test_selection_quant_grade_policy_score_penalty_keeps_candidates(loader):
    """score_penalty 모드에서는 D 등급도 후보에 남는다 (단, score 감점)."""
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.selection.tool import ProductSelectionTool

    products = [
        _mk_product("1", "kr_equity", manager="A", grade="A", quant=80.0),
        _mk_product("2", "kr_equity", manager="B", grade="D", quant=80.0),
        _mk_product("3", "kr_equity", manager="C", grade="D", quant=80.0),
    ]
    universe_result = _make_universe_result(products)

    cfg = loader.load_universe_config()
    # fund 블록은 score_penalty default
    tool = ProductSelectionTool(universe_result, cfg, ProductType.FUND)
    asset_w = pd.Series({"kr_equity": 0.10})
    result = tool.run(asset_w)

    selected_ids = set(result.selected["product_id"].tolist())
    # D 등급도 포함됨
    assert "2" in selected_ids or "3" in selected_ids
    assert result.diagnostics["grade_penalized_count"] >= 1
    assert result.diagnostics["quant_grade_policy"]["mode"] == "score_penalty"


def test_selection_quant_grade_policy_hard_filter_excludes_candidates(loader):
    """hard_filter 모드에서는 D 등급이 후보에서 제외된다."""
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.selection.tool import ProductSelectionTool

    products = [
        _mk_product("1", "kr_equity", manager="A", grade="A", quant=80.0),
        _mk_product("2", "kr_equity", manager="B", grade="D", quant=80.0),
    ]
    universe_result = _make_universe_result(products)

    cfg = loader.load_universe_config()
    # ETF 블록 = hard_filter, min_grade=C
    tool = ProductSelectionTool(universe_result, cfg, ProductType.ETF)
    asset_w = pd.Series({"kr_equity": 0.10})
    result = tool.run(asset_w)

    selected_ids = set(result.selected["product_id"].tolist())
    assert "2" not in selected_ids  # D 제외
    assert result.diagnostics["grade_filtered_count"] >= 1
    assert result.diagnostics["quant_grade_policy"]["mode"] == "hard_filter"


def test_fund_e2e_quality_improves_or_reports_remaining_causes(
    augmented_source_root, augmented_assets, loader
):
    """Phase C-pre 후 Fund quality_status 가 review_required 가 아닐 수 있다.
    review_required 라면 review_reasons 가 비어있지 않다.
    """
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.optimization.tool import OptimizationTool
    from tdf_engine.portfolio.quality import (
        QUALITY_CLEAN,
        QUALITY_REVIEW_REQUIRED,
        QUALITY_WARNING,
    )
    from tdf_engine.portfolio.tool import PortfolioConstructionTool
    from tdf_engine.regime.tool import RegimeAnalysisTool
    from tdf_engine.repositories.file_repositories import (
        FileMarketDataRepository,
        FileProductRepository,
    )
    from tdf_engine.selection.tool import ProductSelectionTool
    from tdf_engine.taa.tool import TAAOverlayTool
    from tdf_engine.universe.classifier import ProductClassifier, load_rules
    from tdf_engine.universe.tool import UniverseTool

    market_repo = FileMarketDataRepository(augmented_source_root)
    product_repo = FileProductRepository(augmented_source_root)

    raw_rules = loader.load_classification_rules_raw()
    classifier = ProductClassifier(load_rules(raw_rules))

    pt = ProductType.FUND
    tdf = loader.load_tdf_config()
    opt_cfg = loader.load_optimization_config()
    taa_cfg = loader.load_taa_config()
    uni_cfg = loader.load_universe_config()

    opt_tool = OptimizationTool(market_repo, augmented_assets, tdf, opt_cfg)
    regime_tool = RegimeAnalysisTool(market_repo, taa_cfg)
    taa_tool = TAAOverlayTool(taa_cfg, assets=augmented_assets)
    universe_tool = UniverseTool(product_repo, uni_cfg, pt, classifier=classifier)

    def factory(uni):
        return ProductSelectionTool(uni, uni_cfg, pt)

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

    # weight closure 유지
    assert abs(float(portfolio.product_weights["weight"].sum()) - 1.0) < 1e-6

    q = portfolio.diagnostics.get("quality") or {}
    status = q.get("quality_status")
    assert status in {QUALITY_CLEAN, QUALITY_WARNING, QUALITY_REVIEW_REQUIRED}
    if status == QUALITY_REVIEW_REQUIRED:
        # review_required 면 사유가 명시되어야 함
        assert q.get("review_reasons")
