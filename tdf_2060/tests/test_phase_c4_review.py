"""Phase C.4 — 운용자 검토용 review packet."""

from __future__ import annotations

import pandas as pd
import pytest


# ── helpers ───────────────────────────────────────────────────────────


def _build_etf_portfolio(augmented_source_root, augmented_assets, loader):
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
    from tdf_engine.universe.classifier import ProductClassifier, load_rules
    from tdf_engine.universe.tool import UniverseTool

    market = FileMarketDataRepository(augmented_source_root)
    products = FileProductRepository(augmented_source_root)
    pt = ProductType.ETF
    tdf = loader.load_tdf_config()
    classifier = ProductClassifier(load_rules(loader.load_classification_rules_raw()))

    opt_tool = OptimizationTool(market, augmented_assets, tdf, loader.load_optimization_config())
    regime_tool = RegimeAnalysisTool(market, loader.load_taa_config())
    taa_tool = TAAOverlayTool(loader.load_taa_config(), assets=augmented_assets, tdf_config=tdf)
    uni_tool = UniverseTool(products, loader.load_universe_config(), pt, classifier=classifier)

    construction = PortfolioConstructionTool(
        optimization_tool=opt_tool, regime_tool=regime_tool, taa_tool=taa_tool,
        universe_tool=uni_tool,
        selection_tool_factory=lambda u: ProductSelectionTool(u, loader.load_universe_config(), pt),
        tdf_config=tdf, universe_config=loader.load_universe_config(), assets=augmented_assets,
    )
    return construction.run(pt), tdf, augmented_assets


# ── 1) review_summary 키 셋 ───────────────────────────────────────────


def test_review_summary_contains_required_keys(augmented_source_root, augmented_assets, loader):
    from tdf_engine.reporting.review import build_review_packet

    portfolio, tdf, assets = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    packet = build_review_packet(portfolio, assets=assets, tdf_config=tdf)
    rs = packet["review_summary"]

    required = {
        "source_type", "as_of_date", "portfolio_type",
        "constraints_passed", "quality_status",
        "asset_weight_sum", "product_weight_sum",
        "equity_bucket_weight", "fixed_income_bucket_weight",
        "fallback_used", "projection_used",
        "max_abs_projection_drift", "max_abs_asset_weight_drift",
        "proxy_used",
        "db_warnings_count", "validation_issues_count", "validation_warnings_count",
    }
    missing = required - set(rs.keys())
    assert not missing, f"missing keys: {missing}"


# ── 2) asset_allocation: target vs final 구분 ─────────────────────────


def test_asset_allocation_comparison_distinguishes_target_and_final(
    augmented_source_root, augmented_assets, loader
):
    from tdf_engine.reporting.review import build_review_packet

    portfolio, tdf, assets = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    packet = build_review_packet(portfolio, assets=assets, tdf_config=tdf)
    aa = packet["asset_allocation"]
    assert aa, "asset_allocation 비어있음"
    for row in aa:
        # target/final 모두 키 존재
        assert "taa_target_weight_before_projection" in row
        assert "final_asset_weight" in row
        assert "projection_drift" in row
        # bound 필드
        assert "final_bound_lower" in row
        assert "final_bound_upper" in row
        assert "bound_status" in row
        assert row["bound_status"] in {"ok", "near_bound", "violation_below",
                                         "violation_above", "no_bound"}


# ── 3) policy_review_items: zero weight required asset ────────────────


def test_policy_review_items_include_zero_weight_required_assets():
    """0% 자산이 의미 있는 lower bound (min > 0) 를 위반하면 policy_review_items 에 등장.

    Phase D relaxed (D-10 closed): 0% 자체는 정책상 허용. 단 운용역이 명시적으로
    lower bound > 0 을 설정한 경우에만 violation 으로 보고 (자산군별 band 재도입 시 사용).
    본 테스트는 bound 가 의미 있을 때 (min > 0) 의 동작을 검증.
    """
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.domain.models import PortfolioResult
    from tdf_engine.reporting.review import build_review_packet

    asset_w = pd.Series({
        "kr_equity": 0.85, "us_treasury_30y": 0.0, "kr_aggregate_bond": 0.15,
    })
    pw = pd.DataFrame([
        {"asset_key": "kr_equity", "product_id": "1", "name": "P1", "manager": "X",
         "kis_asset_class": "", "sub_type": "", "weight": 0.85, "role": "core"},
        {"asset_key": "kr_aggregate_bond", "product_id": "2", "name": "P2", "manager": "Y",
         "kis_asset_class": "", "sub_type": "", "weight": 0.15, "role": "core"},
    ])
    p = PortfolioResult(
        asset_weights=asset_w, product_weights=pw,
        portfolio_type=ProductType.ETF, constraints_passed=True,
        diagnostics={"taa_diagnostics": {"taa_feasibility": {"projection_used": False}}},
    )
    # us_treasury_30y 에 의미 있는 lower bound (0.05 > 0) 를 강제로 설정 → violation 트리거
    tdf = {
        "final_asset_bounds": {
            "kr_equity": {"min": 0.03, "max": 0.20},
            "us_treasury_30y": {"min": 0.05, "max": 0.15},  # min > 0 (test scenario)
            "kr_aggregate_bond": {"min": 0.0, "max": 0.15},
        }
    }
    packet = build_review_packet(p, assets=None, tdf_config=tdf)
    items = packet["policy_review_items"]
    joined = "\n".join(items)
    assert "us_treasury_30y" in joined and "0.00%" in joined


# ── 4) projection_summary: 음수 자산 노출 ─────────────────────────────


def test_projection_summary_lists_negative_assets_before_projection():
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.domain.models import PortfolioResult
    from tdf_engine.reporting.review import build_review_packet

    asset_w = pd.Series({"a": 0.5, "b": 0.5})
    pw = pd.DataFrame([
        {"asset_key": "a", "product_id": "1", "name": "P1", "manager": "X",
         "kis_asset_class": "", "sub_type": "", "weight": 0.5, "role": "core"},
        {"asset_key": "b", "product_id": "2", "name": "P2", "manager": "Y",
         "kis_asset_class": "", "sub_type": "", "weight": 0.5, "role": "core"},
    ])
    p = PortfolioResult(
        asset_weights=asset_w, product_weights=pw,
        portfolio_type=ProductType.ETF, constraints_passed=True,
        diagnostics={
            "taa_diagnostics": {
                "taa_feasibility": {
                    "projection_used": True,
                    "projection_success": True,
                    "negative_weight_assets_before_projection": {
                        "kr_treasury_10y": -0.02, "us_treasury_30y": -0.03,
                    },
                    "bucket_weights_before_projection": {"equity": 0.86, "fixed_income": 0.14},
                    "bucket_weights_after_projection": {"equity": 0.82, "fixed_income": 0.18},
                    "asset_weight_drift_from_target": {
                        "kr_treasury_10y": 0.02, "us_treasury_30y": 0.03,
                        "us_growth_equity": -0.005,
                    },
                    "max_abs_projection_drift": 0.03,
                    "target_weights_before_projection": {
                        "kr_treasury_10y": -0.02, "us_treasury_30y": -0.03,
                        "us_growth_equity": 0.40,
                    },
                    "final_weights_after_projection": {
                        "kr_treasury_10y": 0.0, "us_treasury_30y": 0.0,
                        "us_growth_equity": 0.395,
                    },
                }
            }
        },
    )
    packet = build_review_packet(p, assets=None, tdf_config={})
    ps = packet["projection_summary"]
    assert ps["projection_used"] is True
    neg = ps["negative_assets_before_projection"]
    assert "kr_treasury_10y" in neg and "us_treasury_30y" in neg
    top = ps["largest_projection_drifts_top5"]
    assert top, "top5 drift 비어있음"
    # 가장 큰 drift 가 us_treasury_30y (3%)
    assert top[0]["asset_key"] == "us_treasury_30y"


# ── 5) review_<pt>_<date>.md 생성 ─────────────────────────────────────


def test_review_markdown_is_written(augmented_source_root, augmented_assets, loader, tmp_path):
    from tdf_engine.tools.build_portfolio import write_outputs

    portfolio, tdf, assets = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    out = tmp_path / "out"
    csv_path, json_path = write_outputs(
        portfolio, out, "etf", assets=assets, tdf_config=tdf,
    )
    # review_etf_<date>.md 가 생성됐는지
    md_files = list(out.glob("review_etf_*.md"))
    assert len(md_files) == 1
    text = md_files[0].read_text(encoding="utf-8")
    # 8 섹션 헤더 모두 등장
    for header in ["1. 요약", "2. 최종 자산배분", "3. Projection 전후",
                    "4. 최종 상품", "5. Validation", "6. Quality",
                    "7. DB source", "8. 운용역 확인 필요 사항"]:
        assert header in text, f"section missing: {header}"
