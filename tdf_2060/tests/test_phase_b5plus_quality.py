"""Phase B.5+ — drift diagnostics + quality_status."""

from datetime import date

import pandas as pd
import pytest

from tdf_engine.portfolio.quality import (
    DEFAULT_ASSET_DRIFT_THRESHOLD,
    DEFAULT_BUCKET_DRIFT_THRESHOLD,
    QUALITY_CLEAN,
    QUALITY_REVIEW_REQUIRED,
    QUALITY_WARNING,
    evaluate_quality,
)


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
    pt = ProductType.FUND

    tdf = loader.load_tdf_config()
    opt_cfg = loader.load_optimization_config()
    taa_cfg = loader.load_taa_config()
    uni_cfg = loader.load_universe_config()

    opt_tool = OptimizationTool(market_repo, augmented_assets, tdf, opt_cfg)
    regime_tool = RegimeAnalysisTool(market_repo, taa_cfg)
    taa_tool = TAAOverlayTool(taa_cfg, assets=augmented_assets)
    universe_tool = UniverseTool(product_repo, uni_cfg, pt)

    def factory(uni_res):
        return ProductSelectionTool(uni_res, uni_cfg, pt)

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
    return construction.run(pt)


# ── unit tests on evaluate_quality ────────────────────────────────────


def test_quality_status_clean_when_no_fallback():
    target = pd.Series({"a": 0.6, "b": 0.4})
    df = pd.DataFrame(
        [
            {"asset_key": "a", "product_id": "1", "name": "P1", "weight": 0.6},
            {"asset_key": "b", "product_id": "2", "name": "P2", "weight": 0.4},
        ]
    )
    rep = evaluate_quality(
        target_asset_weights=target,
        product_weights=df,
        fallback_diagnostics={"fallback_used": False, "cash_placeholder_weight": 0.0,
                              "fallback_absorbers": []},
        selection_diagnostics={"unfilled_by_asset_class": {}},
        bucket_by_asset={"a": "equity", "b": "fixed_income"},
    )
    assert rep.quality_status == QUALITY_CLEAN
    assert rep.max_abs_asset_weight_drift == pytest.approx(0.0)


def test_quality_status_review_required_when_drift_exceeds_threshold():
    """asset drift 5%p (3%p threshold 초과) → review_required.

    Phase D relaxed (D-02 pending_rerun): 모듈 default threshold 가 1.0 으로 완화됨.
    drift 임계의 동작 자체는 보존 — 명시적으로 threshold=0.03 을 전달해 검증.
    D-02 closed 시 default 가 다시 0.03 등으로 복원되면 본 인자 제거 가능.
    """
    target = pd.Series({"a": 0.6, "b": 0.4})
    df = pd.DataFrame(
        [
            {"asset_key": "a", "product_id": "1", "name": "P1", "weight": 0.65},
            {"asset_key": "b", "product_id": "2", "name": "P2", "weight": 0.35},
        ]
    )
    rep = evaluate_quality(
        target_asset_weights=target,
        product_weights=df,
        fallback_diagnostics={"fallback_used": True, "cash_placeholder_weight": 0.0,
                              "fallback_absorbers": []},
        selection_diagnostics={"unfilled_by_asset_class": {
            "b": {"cause": "selector_short", "unfilled": 0.05}
        }},
        bucket_by_asset={"a": "equity", "b": "fixed_income"},
        asset_drift_threshold=0.03,   # explicit (Phase D relaxed)
        bucket_drift_threshold=0.05,
    )
    assert rep.quality_status == QUALITY_REVIEW_REQUIRED
    assert rep.max_abs_asset_weight_drift >= 0.03 - 1e-12
    assert any("asset drift" in r for r in rep.review_reasons)


def test_quality_status_review_required_when_cash_placeholder_used():
    target = pd.Series({"a": 0.5, "b": 0.5})
    df = pd.DataFrame(
        [
            {"asset_key": "a", "product_id": "1", "name": "P1", "weight": 0.5},
            {"asset_key": "b", "product_id": "2", "name": "P2", "weight": 0.49},
            {"asset_key": "cash", "product_id": "__CASH__", "name": "Cash", "weight": 0.01},
        ]
    )
    rep = evaluate_quality(
        target_asset_weights=target,
        product_weights=df,
        fallback_diagnostics={"fallback_used": True, "cash_placeholder_weight": 0.01,
                              "fallback_absorbers": []},
        selection_diagnostics={"unfilled_by_asset_class": {
            "b": {"cause": "selector_short", "unfilled": 0.01}
        }},
        bucket_by_asset={"a": "equity", "b": "fixed_income"},
    )
    assert rep.quality_status == QUALITY_REVIEW_REQUIRED
    assert any("cash_placeholder_weight" in r for r in rep.review_reasons)


def test_quality_status_warning_when_fallback_used_with_small_drift():
    """fallback 있지만 drift 가 threshold 미만 → warning."""
    target = pd.Series({"a": 0.6, "b": 0.4})
    df = pd.DataFrame(
        [
            {"asset_key": "a", "product_id": "1", "name": "P1", "weight": 0.61},
            {"asset_key": "b", "product_id": "2", "name": "P2", "weight": 0.39},
        ]
    )
    rep = evaluate_quality(
        target_asset_weights=target,
        product_weights=df,
        fallback_diagnostics={"fallback_used": True, "cash_placeholder_weight": 0.0,
                              "fallback_absorbers": [
                                  {"source_asset_key": "b", "absorber_asset_key": "a",
                                   "absorbed_weight": 0.01, "product_id": "1",
                                   "product_name": "P1", "mode": "same_bucket_sibling_pro_rata"}
                              ]},
        selection_diagnostics={"unfilled_by_asset_class": {
            "b": {"cause": "selector_short", "unfilled": 0.01}
        }},
        bucket_by_asset={"a": "equity", "b": "fixed_income"},
    )
    assert rep.quality_status == QUALITY_WARNING
    assert rep.max_abs_asset_weight_drift < DEFAULT_ASSET_DRIFT_THRESHOLD


# ── E2E tests ─────────────────────────────────────────────────────────


def test_fallback_records_asset_weight_drift(augmented_source_root, augmented_assets, loader):
    """Fund E2E — diagnostics.quality 가 target/final/drift 와 absorbers 를 기록."""
    portfolio = _build_fund_portfolio(augmented_source_root, augmented_assets, loader)
    q = portfolio.diagnostics.get("quality") or {}

    assert "target_asset_weights" in q
    assert "final_asset_weights" in q
    assert "asset_weight_drift" in q
    assert "max_abs_asset_weight_drift" in q
    assert "drift_by_bucket" in q
    assert "fallback_absorbers" in q

    # absorbers 에 source/absorber/product 가 모두 기록됨 (특정 source 강제는 안 함 —
    # classifier 룰이 발전하면 일부 source 가 더 이상 미배분 으로 안 잡힐 수 있음)
    absorbers = q["fallback_absorbers"]
    assert absorbers, "expected at least one absorber"
    for a in absorbers:
        assert "source_asset_key" in a
        assert "absorber_asset_key" in a
        assert "product_id" in a
        assert "absorbed_weight" in a
        assert "mode" in a

    # absorbers entry 의 mode 가 알려진 값 중 하나
    valid_modes = {
        "same_asset_class_pro_rata",
        "same_bucket_sibling_pro_rata",
        "cash_placeholder",
    }
    for a in absorbers:
        assert a["mode"] in valid_modes


def test_fund_e2e_quality_diagnostics_populated(augmented_source_root, augmented_assets, loader):
    """Fund E2E — quality 진단 값이 정상적으로 채워진다.

    Phase C-pre 룰 보강 + score_penalty 정책으로 대부분 자산군이 매칭되면서
    quality_status 가 warning 또는 clean 으로 내려갈 수 있다. 따라서 특정 status 를
    강제하지 않고, quality 구조와 status 가 알려진 값 중 하나임을 검증.
    """
    from tdf_engine.portfolio.quality import (
        QUALITY_CLEAN,
        QUALITY_REVIEW_REQUIRED,
        QUALITY_WARNING,
    )
    portfolio = _build_fund_portfolio(augmented_source_root, augmented_assets, loader)
    q = portfolio.diagnostics.get("quality") or {}
    assert q.get("quality_status") in {QUALITY_CLEAN, QUALITY_WARNING, QUALITY_REVIEW_REQUIRED}
    assert "max_abs_asset_weight_drift" in q
    assert "drift_by_bucket" in q
    assert "review_reasons" in q


def test_validator_warning_includes_drift_and_quality_status(augmented_source_root, augmented_assets, loader):
    """validation.warnings 에 max_abs_drift / quality_status 가 노출된다."""
    portfolio = _build_fund_portfolio(augmented_source_root, augmented_assets, loader)
    val = portfolio.diagnostics.get("validation") or {}
    warnings = val.get("warnings") or []
    assert any("max_abs_asset_weight_drift" in w for w in warnings)
    assert any("quality_status" in w for w in warnings)
