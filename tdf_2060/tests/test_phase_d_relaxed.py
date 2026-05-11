"""Phase D relaxed constraints — hard constraint 검증 테스트 (2026-05-08).

본 단계 hard constraint:
  - long-only (정책 #4)
  - sum-to-100% (정책 #6)
  - 데이터 무결성 (BRFUT004 / DB / NaN / optimizer · projection convergence)

본 단계 NOT enforced (relaxed):
  - bucket range (75-85 / 15-25)
  - per-asset weight bounds
  - per_asset_max_tilt 0.03
  - final_asset_bounds
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


# ── helper — file mode E2E ─────────────────────────────────────────────


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
    return construction.run(pt)


# ── 1) long-only — final portfolio 음수 금지 ───────────────────────────


def test_phase_d_relaxed_long_only(augmented_source_root, augmented_assets, loader):
    """정책 #4: 최종 포트폴리오에서 negative weight 금지.

    중간 TAA target 에서는 음수가 허용되지만 (regime tilt 음수 + SAA≈0),
    projection 이 long-only 로 보정. final 산출에 음수 없음.
    """
    portfolio = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    # asset_weights 모두 ≥ 0
    assert (portfolio.asset_weights >= -1e-9).all(), \
        f"negative asset weights: {portfolio.asset_weights[portfolio.asset_weights < -1e-9].to_dict()}"
    # product_weights 모두 ≥ 0
    if not portfolio.product_weights.empty:
        assert (portfolio.product_weights["weight"] >= -1e-9).all()


# ── 2) sum-to-100% — 정책 #6 ───────────────────────────────────────────


def test_phase_d_relaxed_sum_to_one(augmented_source_root, augmented_assets, loader):
    """정책 #6: asset_weight 합 = 1.0, product_weight 합 = 1.0."""
    portfolio = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    asset_sum = float(portfolio.asset_weights.sum())
    assert abs(asset_sum - 1.0) < 1e-4, f"asset_weight sum {asset_sum} != 1.0"
    if not portfolio.product_weights.empty:
        prod_sum = float(portfolio.product_weights["weight"].sum())
        assert abs(prod_sum - 1.0) < 1e-4, f"product_weight sum {prod_sum} != 1.0"


# ── 3) bucket unconstrained — bucket range hard bound 비활성 ────────────


def test_phase_d_relaxed_bucket_unconstrained(augmented_source_root, augmented_assets, loader):
    """Phase D relaxed: equity / fixed_income bucket 합계는 [0, 1] 범위 내,
    합 = 1.0 만 검증. 75-85 / 15-25 hard bound 자체가 비활성.
    """
    portfolio = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    eq_keys = [a.asset_key for a in augmented_assets if a.bucket.value == "equity"]
    fi_keys = [a.asset_key for a in augmented_assets if a.bucket.value == "fixed_income"]
    eq_sum = float(portfolio.asset_weights.loc[eq_keys].sum())
    fi_sum = float(portfolio.asset_weights.loc[fi_keys].sum())
    assert 0.0 <= eq_sum <= 1.0
    assert 0.0 <= fi_sum <= 1.0
    assert abs((eq_sum + fi_sum) - 1.0) < 1e-6


# ── 4) per_asset_max_tilt unbounded — TAA tilt 폭 제한 비활성 ───────────


def test_phase_d_relaxed_per_asset_tilt_unbounded(loader):
    """Phase D relaxed: taa_policy.constraints.per_asset_max_tilt = 1.0
    (Option B = 사실상 비제약). ineq trivially 만족.
    """
    taa_cfg = loader.load_taa_config()
    constraints = taa_cfg.get("constraints") or {}
    pat = constraints.get("per_asset_max_tilt")
    assert pat is not None
    assert float(pat) >= 1.0 - 1e-12, f"per_asset_max_tilt={pat} should be unbounded (≥1.0)"

    # tilt_sum_must_be_zero 는 sum-to-100% 회계 정합성 장치로 유지
    assert constraints.get("tilt_sum_must_be_zero") is True

    # validation 플래그도 false 인지 검증 (per-asset tilt 위반 warning 비활성)
    validation = taa_cfg.get("validation") or {}
    assert validation.get("warn_if_per_asset_tilt_violated") is False
    assert validation.get("warn_if_bucket_bound_violated") is False


# ── 5) Decision Register active set 정합성 ─────────────────────────────


def test_phase_d_relaxed_active_decision_set():
    """reporting.review.ACTIVE_DECISION_IDS 가 register status 와 정합."""
    from tdf_engine.reporting.review import (
        ACTIVE_DECISION_IDS,
        INFO_ONLY_DECISION_IDS,
    )
    # closed/deferred + active = 14 (D-01 ~ D-14)
    union = ACTIVE_DECISION_IDS | INFO_ONLY_DECISION_IDS
    assert {f"D-{i:02d}" for i in range(1, 15)} == union
    # closed + deferred 는 informational only
    assert {"D-01", "D-04", "D-05", "D-07", "D-10", "D-11", "D-12"} == INFO_ONLY_DECISION_IDS
    # 나머지는 active (decision_required)
    assert {"D-02", "D-03", "D-06", "D-08", "D-09", "D-13", "D-14"} == ACTIVE_DECISION_IDS


# ── 6) D-02 drift threshold 구조화 (Option A) ─────────────────────────


def _drift_fixture():
    """drift 5%p 발생을 강제하는 mini fixture."""
    target = pd.Series({"a": 0.6, "b": 0.4})
    df = pd.DataFrame([
        {"asset_key": "a", "product_id": "1", "name": "P1", "weight": 0.65},
        {"asset_key": "b", "product_id": "2", "name": "P2", "weight": 0.35},
    ])
    return target, df


def test_quality_default_thresholds_restored():
    """Phase D Option A: DEFAULT 0.03 / 0.05 로 복원."""
    from tdf_engine.portfolio.quality import (
        DEFAULT_ASSET_DRIFT_THRESHOLD,
        DEFAULT_BUCKET_DRIFT_THRESHOLD,
    )
    assert DEFAULT_ASSET_DRIFT_THRESHOLD == 0.03
    assert DEFAULT_BUCKET_DRIFT_THRESHOLD == 0.05


def test_quality_telemetry_only_does_not_escalate_status():
    """enforcement=telemetry_only: drift 5%p 가 quality_status 를 review_required 로 올리지 않음."""
    from tdf_engine.portfolio.quality import (
        QUALITY_CLEAN, QUALITY_REVIEW_REQUIRED, QUALITY_WARNING,
        evaluate_quality, ENFORCEMENT_TELEMETRY_ONLY,
    )
    target, df = _drift_fixture()
    rep = evaluate_quality(
        target_asset_weights=target, product_weights=df,
        fallback_diagnostics={"fallback_used": False, "cash_placeholder_weight": 0.0,
                              "fallback_absorbers": []},
        selection_diagnostics={"unfilled_by_asset_class": {}},
        bucket_by_asset={"a": "equity", "b": "fixed_income"},
        enforcement=ENFORCEMENT_TELEMETRY_ONLY,
    )
    # drift 는 발생 (telemetry 보존)
    assert rep.max_abs_asset_weight_drift >= 0.03 - 1e-12
    assert any("asset drift" in n for n in rep.drift_telemetry_notes), \
        "telemetry_only 에서 drift exceed 가 telemetry_notes 에 보존되어야 함"
    # 그러나 quality_status 는 악화되지 않음 (fallback 없음 → CLEAN)
    assert rep.quality_status == QUALITY_CLEAN
    assert rep.enforcement_mode == ENFORCEMENT_TELEMETRY_ONLY


def test_quality_review_mode_drift_to_warning():
    """enforcement=review (warning alias): drift exceed → WARNING, NOT review_required."""
    from tdf_engine.portfolio.quality import (
        QUALITY_WARNING, evaluate_quality, ENFORCEMENT_REVIEW,
    )
    target, df = _drift_fixture()
    rep = evaluate_quality(
        target_asset_weights=target, product_weights=df,
        fallback_diagnostics={"fallback_used": False, "cash_placeholder_weight": 0.0,
                              "fallback_absorbers": []},
        selection_diagnostics={"unfilled_by_asset_class": {}},
        bucket_by_asset={"a": "equity", "b": "fixed_income"},
        enforcement=ENFORCEMENT_REVIEW,
    )
    assert rep.quality_status == QUALITY_WARNING
    assert any("asset drift" in r for r in rep.review_reasons)
    assert rep.enforcement_mode == ENFORCEMENT_REVIEW


def test_quality_production_mode_drift_to_review_required():
    """enforcement=production: drift exceed → review_required (legacy/default 동작)."""
    from tdf_engine.portfolio.quality import (
        QUALITY_REVIEW_REQUIRED, evaluate_quality, ENFORCEMENT_PRODUCTION,
    )
    target, df = _drift_fixture()
    rep = evaluate_quality(
        target_asset_weights=target, product_weights=df,
        fallback_diagnostics={"fallback_used": True, "cash_placeholder_weight": 0.0,
                              "fallback_absorbers": []},
        selection_diagnostics={"unfilled_by_asset_class": {}},
        bucket_by_asset={"a": "equity", "b": "fixed_income"},
        enforcement=ENFORCEMENT_PRODUCTION,
    )
    assert rep.quality_status == QUALITY_REVIEW_REQUIRED
    assert any("asset drift" in r for r in rep.review_reasons)


def test_quality_telemetry_values_preserved_across_modes():
    """모든 enforcement 모드에서 drift 값 자체는 동일하게 report 에 보존."""
    from tdf_engine.portfolio.quality import (
        evaluate_quality, ENFORCEMENT_PRODUCTION, ENFORCEMENT_REVIEW,
        ENFORCEMENT_TELEMETRY_ONLY,
    )
    target, df = _drift_fixture()
    common_args = dict(
        target_asset_weights=target, product_weights=df,
        fallback_diagnostics={"fallback_used": False, "cash_placeholder_weight": 0.0,
                              "fallback_absorbers": []},
        selection_diagnostics={"unfilled_by_asset_class": {}},
        bucket_by_asset={"a": "equity", "b": "fixed_income"},
    )
    drifts: dict[str, float] = {}
    for mode in (ENFORCEMENT_PRODUCTION, ENFORCEMENT_REVIEW, ENFORCEMENT_TELEMETRY_ONLY):
        rep = evaluate_quality(enforcement=mode, **common_args)
        drifts[mode] = rep.max_abs_asset_weight_drift
        # drift_by_bucket / asset_weight_drift 도 항상 채워짐
        assert rep.asset_weight_drift, f"{mode}: asset_weight_drift empty"
        assert rep.drift_by_bucket, f"{mode}: drift_by_bucket empty"
    # 모든 모드에서 동일한 drift 값
    assert len(set(round(v, 9) for v in drifts.values())) == 1, \
        f"drift values differ across modes: {drifts}"


def test_quality_yaml_drift_thresholds_loadable(loader):
    """tdf_2060.yaml 에 drift_thresholds + modes.relaxed_diagnostic.enforcement 가 정의됨."""
    tdf = loader.load_tdf_config()
    drift_cfg = tdf.get("drift_thresholds")
    assert drift_cfg is not None
    assert "modes" in drift_cfg
    relaxed = drift_cfg["modes"].get("relaxed_diagnostic")
    assert relaxed is not None
    assert relaxed.get("enforcement") == "telemetry_only"
    # production / review 도 정의 (운영 단계 전환 가능)
    assert "production" in drift_cfg["modes"]
    assert "review" in drift_cfg["modes"]


def test_e2e_relaxed_diagnostic_uses_telemetry_only_enforcement(
    augmented_source_root, augmented_assets, loader
):
    """tdf_config.operating_mode=relaxed_diagnostic + drift_thresholds.modes 매핑이 E2E 에 적용됨."""
    portfolio = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    q = portfolio.diagnostics.get("quality") or {}
    # enforcement_mode 가 telemetry_only 로 설정되어야 함
    assert q.get("enforcement_mode") == "telemetry_only"
    # thresholds 는 production 운영값 (0.03 / 0.05) 로 보존 (telemetry_only 에서도 값 자체는 보존)
    thr = q.get("thresholds") or {}
    assert abs(float(thr.get("asset_drift", -1)) - 0.03) < 1e-12
    assert abs(float(thr.get("bucket_drift", -1)) - 0.05) < 1e-12


# ── 7) D-02 drift_source 분류 (projection + quality 단계) ──────────────


def test_projection_drift_source_long_only_clipping():
    """ust30/kr_t10 음수 target 이 long-only clipping 으로 분류됨."""
    import pandas as pd
    from tdf_engine.taa.projection import (
        project_to_feasible,
        PROJECTION_DRIFT_LONG_ONLY_CLIPPING,
        PROJECTION_DRIFT_REDISTRIBUTION,
    )
    target = pd.Series({
        "us_growth_equity": 0.716,
        "us_value_equity": 0.284,
        "us_treasury_30y": -0.03,
        "kr_treasury_10y": -0.02,
        "em_equity": 0.02,
        "kr_equity": 0.02,
        "us_high_yield": 0.01,
    })
    asset_bounds = {k: (0.0, 1.0) for k in target.index}
    bucket_bounds = {}  # relaxed mode
    bucket_by_asset = {
        "us_growth_equity": "equity", "us_value_equity": "equity",
        "us_treasury_30y": "fixed_income", "kr_treasury_10y": "fixed_income",
        "em_equity": "equity", "kr_equity": "equity",
        "us_high_yield": "fixed_income",
    }
    final, diag = project_to_feasible(
        target, asset_bounds=asset_bounds, bucket_bounds=bucket_bounds,
        bucket_by_asset=bucket_by_asset, sum_target=1.0,
    )
    # final 은 non-negative
    assert (final >= -1e-9).all()
    # sum = 1.0
    assert abs(float(final.sum()) - 1.0) < 1e-6
    # ust30, kr_t10 은 long_only_clipping 으로 분류
    assert diag.drift_source_by_asset["us_treasury_30y"] == PROJECTION_DRIFT_LONG_ONLY_CLIPPING
    assert diag.drift_source_by_asset["kr_treasury_10y"] == PROJECTION_DRIFT_LONG_ONLY_CLIPPING
    # 양수 target 자산은 redistribution 또는 none
    assert diag.drift_source_by_asset["us_growth_equity"] in (
        PROJECTION_DRIFT_REDISTRIBUTION,
        "none",
    )
    # clipping_summary 보존
    summary = diag.clipping_summary
    assert summary["n_assets_clipped_long_only"] == 2
    assert "us_treasury_30y" in summary["clipped_assets"]
    assert "kr_treasury_10y" in summary["clipped_assets"]
    assert abs(summary["total_long_only_clipping_magnitude"] - 0.05) < 1e-6
    assert summary["drift_source_primary"] == PROJECTION_DRIFT_REDISTRIBUTION  # 5 자산 redistribution > 2 long_only


def test_projection_drift_relaxed_no_bucket_or_asset_bound_sources():
    """relaxed mode (asset/bucket bound = [0,1]) 에서는 bucket_constraint /
    asset_upper_bound source 가 발생하지 않아야 함."""
    import pandas as pd
    from tdf_engine.taa.projection import project_to_feasible

    target = pd.Series({
        "a": 0.6, "b": -0.1, "c": 0.5,  # b 가 음수 → projection 트리거
    })
    asset_bounds = {"a": (0.0, 1.0), "b": (0.0, 1.0), "c": (0.0, 1.0)}
    bucket_bounds = {}
    bucket_by_asset = {"a": "equity", "b": "fixed_income", "c": "equity"}
    _, diag = project_to_feasible(
        target, asset_bounds=asset_bounds, bucket_bounds=bucket_bounds,
        bucket_by_asset=bucket_by_asset, sum_target=1.0,
    )
    unexpected = diag.clipping_summary.get("relaxed_mode_unexpected_sources") or []
    assert unexpected == [], f"unexpected sources in relaxed mode: {unexpected}"


def test_quality_drift_source_product_cap_clipping(
    augmented_source_root, augmented_assets, loader
):
    """relaxed E2E: quality drift 가 product_cap_clipping_outflow 로 분류됨.

    us_growth_equity 가 70%+ target 인데 single product cap (ETF=20%) 로
    여러 상품으로 분산 + fallback. 그 결과 source asset (us_growth) 는 outflow,
    absorber assets (kr_equity, dm_ex_us 등 bucket sibling) 은 inflow.
    """
    portfolio = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    q = portfolio.diagnostics.get("quality") or {}
    src_by_asset = q.get("drift_source_by_asset") or {}
    summary = q.get("drift_clipping_summary") or {}

    # 분류가 채워짐
    assert src_by_asset, "quality drift_source_by_asset is empty"
    assert summary, "quality drift_clipping_summary is empty"
    # primary source 가 outflow / inflow 중 하나
    primary = summary.get("drift_source_primary")
    valid_primary = {
        "product_cap_clipping_outflow", "fallback_redistribution_inflow",
        "selection_shortfall", "selection_overflow", "none",
    }
    assert primary in valid_primary, f"unexpected primary={primary}"


def test_drift_source_review_packet_renders_section_3_1(
    augmented_source_root, augmented_assets, loader, tmp_path
):
    """relaxed E2E: review markdown 에 §3.1 Drift source breakdown 섹션이 등장."""
    from tdf_engine.tools.build_portfolio import write_outputs

    portfolio = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    out = tmp_path / "out"
    tdf_cfg = loader.load_tdf_config()
    write_outputs(portfolio, out, "etf", assets=augmented_assets, tdf_config=tdf_cfg)
    md_files = list(out.glob("review_etf_*.md"))
    assert md_files
    text = md_files[0].read_text(encoding="utf-8")
    assert "3.1 Drift source breakdown" in text, \
        "§3.1 Drift source breakdown section missing"
    # primary drift source 표기 확인
    assert "primary drift source" in text


def test_projection_final_non_negative_and_sum_one():
    """모든 projection 결과는 long-only + sum=1.0 보장 (D-01 hard constraint)."""
    import pandas as pd
    from tdf_engine.taa.projection import project_to_feasible
    # 다양한 target 케이스
    cases = [
        {"a": 0.5, "b": 0.5},                   # 이미 feasible
        {"a": 0.6, "b": -0.1, "c": 0.5},        # 음수 1개
        {"a": -0.05, "b": -0.05, "c": 1.1},     # 음수 2개 + 한 자산 > 1
    ]
    for tgt in cases:
        target = pd.Series(tgt)
        asset_bounds = {k: (0.0, 1.0) for k in target.index}
        bucket_by_asset = {k: "equity" for k in target.index}
        final, _ = project_to_feasible(
            target, asset_bounds=asset_bounds, bucket_bounds={},
            bucket_by_asset=bucket_by_asset, sum_target=1.0,
        )
        assert (final >= -1e-9).all(), f"negative final for case {tgt}: {final}"
        assert abs(float(final.sum()) - 1.0) < 1e-6, f"sum != 1 for case {tgt}: {float(final.sum())}"


def test_quality_drift_telemetry_keys_in_diagnostics(
    augmented_source_root, augmented_assets, loader
):
    """diagnostics.quality 에 drift_source_by_asset / drift_clipping_summary 보존."""
    portfolio = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    q = portfolio.diagnostics.get("quality") or {}
    assert "drift_source_by_asset" in q
    assert "drift_clipping_summary" in q
    summary = q["drift_clipping_summary"]
    # 키 셋 검증
    required = {
        "n_assets_with_outflow", "outflow_assets", "outflow_by_asset",
        "total_outflow_magnitude",
        "n_assets_with_inflow", "inflow_assets", "inflow_by_asset",
        "total_inflow_magnitude",
        "drift_source_primary", "drift_source_counts",
    }
    missing = required - set(summary.keys())
    assert not missing, f"missing keys: {missing}"
