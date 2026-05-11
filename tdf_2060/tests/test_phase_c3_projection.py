"""Phase C.3 — TAA feasibility projection."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


# ── helpers ───────────────────────────────────────────────────────────


def _make_fake_db_for_assets(asset_keys: list[str]):
    """Phase C 테스트와 같은 fake DB 생성기."""
    from datetime import date

    fake = {}
    mapping = {}
    for i, ak in enumerate(asset_keys, start=100):
        rng = np.random.default_rng(i)
        n_months = 60
        r = rng.normal(0.006, 0.04, n_months)
        levels = 100.0 * np.cumprod(1.0 + r)
        idx = pd.date_range(end=date(2026, 3, 31), periods=n_months, freq="ME")
        fake[(i, 6)] = pd.DataFrame(
            {"timestamp_observation": idx, "data": [str(v) for v in levels]}
        )
        mapping[ak] = i
    return fake, mapping


_TICKER_BY_KEY = {
    "kr_equity":          "M2KR INDEX",
    "us_growth_equity":   "M2US000G Index",
    "us_value_equity":    "M2US000V Index",
    "dm_ex_us_equity":    "TAD09XU Index",
    "em_equity":          "M2EF Index",
    "kr_aggregate_bond":  "SPBKRCOT Index",
    "kr_treasury_10y":    "KPGB10YR Index",
    "us_treasury_30y":    "BRFUT004",
    "us_high_yield":      "LF98TRUU Index",
}

_NINE_KEYS = list(_TICKER_BY_KEY.keys())


def _db_sources_for_test(mapping):
    assets = []
    for ak, ds_id in mapping.items():
        assets.append(
            {
                "asset_key": ak,
                "dataset_id": ds_id,
                "ticker": _TICKER_BY_KEY[ak],
                "value_dataseries": 6,
                "currency": None,
                "frequency": "M",
                "required": True,
                "semantic_type": "total_return_index",
                "return_transform": "pct_change",
            }
        )
    return {
        "asset_rt_vol": {"computation_mode": "from_timeseries",
                          "lookback_years": 5, "annualization": 12},
        "corr_matrix": {"computation_mode": "from_timeseries", "lookback_years": 5},
        "regime_source": {"enabled": False},
        "regime_return_source": {"enabled": False},
        "assets": assets,
    }


# ── 1) projection 이 음수 weight 제거 ─────────────────────────────────


def test_taa_projection_removes_negative_weights():
    from tdf_engine.taa.projection import project_to_feasible

    target = pd.Series({
        "kr_equity": 0.05, "us_growth_equity": 0.40, "us_value_equity": 0.20,
        "dm_ex_us_equity": 0.05, "em_equity": 0.05,
        "kr_aggregate_bond": 0.10, "kr_treasury_10y": -0.02,
        "us_treasury_30y": -0.03, "us_high_yield": 0.20,
    })
    bucket_by_asset = {
        "kr_equity": "equity", "us_growth_equity": "equity", "us_value_equity": "equity",
        "dm_ex_us_equity": "equity", "em_equity": "equity",
        "kr_aggregate_bond": "fixed_income", "kr_treasury_10y": "fixed_income",
        "us_treasury_30y": "fixed_income", "us_high_yield": "fixed_income",
    }
    final, diag = project_to_feasible(
        target_weights=target,
        asset_bounds={k: (0.0, 1.0) for k in target.index},
        bucket_bounds={"equity": (0.75, 0.85), "fixed_income": (0.15, 0.25)},
        bucket_by_asset=bucket_by_asset,
        sum_target=1.0,
    )
    assert (final >= -1e-9).all()
    assert "kr_treasury_10y" in diag.negative_weight_assets_before_projection
    assert "us_treasury_30y" in diag.negative_weight_assets_before_projection


# ── 2) sum=1 보존 ─────────────────────────────────────────────────────


def test_taa_projection_preserves_sum_to_one():
    from tdf_engine.taa.projection import project_to_feasible

    target = pd.Series({"a": -0.1, "b": 0.5, "c": 0.6})
    bucket_by_asset = {"a": "equity", "b": "equity", "c": "fixed_income"}
    final, diag = project_to_feasible(
        target_weights=target,
        asset_bounds={k: (0.0, 1.0) for k in target.index},
        bucket_bounds={"equity": (0.5, 0.8), "fixed_income": (0.2, 0.5)},
        bucket_by_asset=bucket_by_asset,
        sum_target=1.0,
    )
    assert abs(float(final.sum()) - 1.0) < 1e-6
    assert diag.projection_used is True


# ── 3) bucket bound 강제 ──────────────────────────────────────────────


def test_taa_projection_enforces_bucket_bounds():
    from tdf_engine.taa.projection import project_to_feasible

    # equity 만으로 100% 지정 → bucket bound (eq 0.5~0.8) 강제 시 줄여야 함
    target = pd.Series({"a": 0.6, "b": 0.4, "c": 0.0})
    bucket_by_asset = {"a": "equity", "b": "equity", "c": "fixed_income"}
    final, diag = project_to_feasible(
        target_weights=target,
        asset_bounds={k: (0.0, 1.0) for k in target.index},
        bucket_bounds={"equity": (0.5, 0.8), "fixed_income": (0.2, 0.5)},
        bucket_by_asset=bucket_by_asset,
        sum_target=1.0,
    )
    eq = final[["a", "b"]].sum()
    fi = final["c"]
    assert 0.5 - 1e-6 <= eq <= 0.8 + 1e-6
    assert 0.2 - 1e-6 <= fi <= 0.5 + 1e-6


# ── 4) negative_weight_assets_before_projection 기록 ──────────────────


def test_taa_projection_records_negative_assets_before_projection():
    from tdf_engine.taa.projection import project_to_feasible

    target = pd.Series({"a": -0.05, "b": 1.05})
    bucket_by_asset = {"a": "equity", "b": "fixed_income"}
    final, diag = project_to_feasible(
        target_weights=target,
        asset_bounds={"a": (0.0, 0.5), "b": (0.0, 1.0)},
        bucket_bounds={},
        bucket_by_asset=bucket_by_asset,
        sum_target=1.0,
    )
    assert diag.negative_weight_assets_before_projection.get("a") == pytest.approx(-0.05)
    assert diag.projection_used is True
    assert diag.constraints_after_projection["feasible"] is True


# ── 5) DB E2E projection 후 product_weight_sum=1 ──────────────────────


def test_db_e2e_after_projection_product_weight_sum_is_one(
    augmented_source_root, augmented_assets, loader
):
    """DB fake + projection 통합 → product_weight_sum=1.0 보장."""
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.optimization.tool import OptimizationTool
    from tdf_engine.portfolio.tool import PortfolioConstructionTool
    from tdf_engine.regime.tool import RegimeAnalysisTool
    from tdf_engine.repositories.composite import CompositeMarketDataRepository
    from tdf_engine.repositories.db_market_data import DBMarketDataRepository
    from tdf_engine.repositories.file_repositories import (
        FileMarketDataRepository,
        FileProductRepository,
    )
    from tdf_engine.selection.tool import ProductSelectionTool
    from tdf_engine.taa.tool import TAAOverlayTool
    from tdf_engine.universe.classifier import ProductClassifier, load_rules
    from tdf_engine.universe.tool import UniverseTool

    fake, mapping = _make_fake_db_for_assets(_NINE_KEYS)
    sources = _db_sources_for_test(mapping)
    db_repo = DBMarketDataRepository(fake, sources, as_of_date="2026-03-31")
    file_repo = FileMarketDataRepository(augmented_source_root)
    composite = CompositeMarketDataRepository(primary=db_repo, fallback=file_repo)

    products = FileProductRepository(augmented_source_root)
    pt = ProductType.FUND
    tdf = loader.load_tdf_config()
    opt_cfg = loader.load_optimization_config()
    taa_cfg = loader.load_taa_config()
    uni_cfg = loader.load_universe_config()
    classifier = ProductClassifier(load_rules(loader.load_classification_rules_raw()))

    opt_tool = OptimizationTool(composite, augmented_assets, tdf, opt_cfg)
    regime_tool = RegimeAnalysisTool(composite, taa_cfg)
    taa_tool = TAAOverlayTool(taa_cfg, assets=augmented_assets, tdf_config=tdf)
    uni_tool = UniverseTool(products, uni_cfg, pt, classifier=classifier)

    construction = PortfolioConstructionTool(
        optimization_tool=opt_tool, regime_tool=regime_tool, taa_tool=taa_tool,
        universe_tool=uni_tool,
        selection_tool_factory=lambda u: ProductSelectionTool(u, uni_cfg, pt),
        tdf_config=tdf, universe_config=uni_cfg, assets=augmented_assets,
    )
    portfolio = construction.run(pt)

    s = float(portfolio.product_weights["weight"].sum())
    assert abs(s - 1.0) < 1e-6
    # asset weights 도 모두 non-negative
    assert (portfolio.asset_weights >= -1e-9).all()


# ── 6) DB E2E constraints_passed=True ─────────────────────────────────


def test_db_e2e_after_projection_constraints_pass(
    augmented_source_root, augmented_assets, loader
):
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.optimization.tool import OptimizationTool
    from tdf_engine.portfolio.tool import PortfolioConstructionTool
    from tdf_engine.regime.tool import RegimeAnalysisTool
    from tdf_engine.repositories.composite import CompositeMarketDataRepository
    from tdf_engine.repositories.db_market_data import DBMarketDataRepository
    from tdf_engine.repositories.file_repositories import (
        FileMarketDataRepository,
        FileProductRepository,
    )
    from tdf_engine.selection.tool import ProductSelectionTool
    from tdf_engine.taa.tool import TAAOverlayTool
    from tdf_engine.universe.classifier import ProductClassifier, load_rules
    from tdf_engine.universe.tool import UniverseTool

    fake, mapping = _make_fake_db_for_assets(_NINE_KEYS)
    sources = _db_sources_for_test(mapping)
    db_repo = DBMarketDataRepository(fake, sources, as_of_date="2026-03-31")
    file_repo = FileMarketDataRepository(augmented_source_root)
    composite = CompositeMarketDataRepository(primary=db_repo, fallback=file_repo)

    products = FileProductRepository(augmented_source_root)
    pt = ProductType.ETF
    tdf = loader.load_tdf_config()
    classifier = ProductClassifier(load_rules(loader.load_classification_rules_raw()))

    opt_tool = OptimizationTool(composite, augmented_assets, tdf, loader.load_optimization_config())
    regime_tool = RegimeAnalysisTool(composite, loader.load_taa_config())
    taa_tool = TAAOverlayTool(loader.load_taa_config(), assets=augmented_assets, tdf_config=tdf)
    uni_tool = UniverseTool(products, loader.load_universe_config(), pt, classifier=classifier)

    construction = PortfolioConstructionTool(
        optimization_tool=opt_tool, regime_tool=regime_tool, taa_tool=taa_tool,
        universe_tool=uni_tool,
        selection_tool_factory=lambda u: ProductSelectionTool(u, loader.load_universe_config(), pt),
        tdf_config=tdf, universe_config=loader.load_universe_config(), assets=augmented_assets,
    )
    portfolio = construction.run(pt)

    # Phase C.3 핵심: constraints_passed=True
    assert portfolio.constraints_passed is True
    # Phase D relaxed (D-01 closed): bucket bound hard 비활성. bucket sums 의 [0, 1] 범위만 검증.
    # (이전 [0.7499, 0.8501] / [0.1499, 0.2501] 가정은 D-01 closed 로 제거)
    bucket = (portfolio.diagnostics.get("taa_diagnostics") or {}).get("bucket_sums") or {}
    eq = float(bucket.get("equity", 0))
    fi = float(bucket.get("fixed_income", 0))
    assert 0.0 <= eq <= 1.0
    assert 0.0 <= fi <= 1.0
    assert abs((eq + fi) - 1.0) < 1e-4


# ── 7) Validator warning 에 projection 메시지 ──────────────────────────


def test_validator_reports_projection_warning():
    """projection_used=True 면 warning 에 max_abs_projection_drift 등 노출."""
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.domain.models import PortfolioResult
    from tdf_engine.portfolio.validator import PortfolioValidator

    # 가짜 portfolio diagnostics — taa_feasibility 만 set
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
                    "max_abs_projection_drift": 0.0123,
                    "negative_weight_assets_before_projection": {"x": -0.02},
                    "bucket_weights_after_projection": {"equity": 0.80, "fixed_income": 0.20},
                }
            }
        },
    )
    rep = PortfolioValidator().validate(p, tdf_config={})
    msgs = " ".join(rep.warnings)
    assert "taa_projection_used" in msgs
    assert "1.2300%" in msgs or "0.0123" in msgs
    assert "negative weights before projection" in msgs
    assert "bucket after projection" in msgs
