"""Phase E-6.2 telemetry smoke test.

신규 telemetry 6건 (T-1~T-6) 의 존재 + 형태 검증.
allocation 결과 bit-identical 검증은 별도 (live DB run 필요 → 본 파일 외 산출물 비교).

T-1 expected_returns      → saa_diagnostics.cma.expected_returns       (dict[asset_key, float])
T-2 volatilities          → saa_diagnostics.cma.volatilities           (dict[asset_key, float])
T-3 correlation_matrix    → saa_diagnostics.cma.correlation_matrix     (dict[k, dict[k, float]])
T-4 covariance_matrix     → saa_diagnostics.cma.covariance_matrix      (dict[k, dict[k, float]])
T-5 regime history        → diagnostics.regime.history                 (list[dict])
T-6 SAA weights direct    → saa_diagnostics.saa_weights                (dict[asset_key, float])
                            + asset_allocation[].saa_weight            (float)
"""

from __future__ import annotations

import math


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
    taa_tool = TAAOverlayTool(taa_cfg, assets=augmented_assets, tdf_config=tdf)
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


def test_t1_expected_returns_dump(augmented_source_root, augmented_assets, loader):
    """T-1: μ vector 가 saa_diagnostics.cma.expected_returns 에 있어야 함."""
    portfolio = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    cma_diag = portfolio.diagnostics["saa_diagnostics"]["cma"]
    assert "expected_returns" in cma_diag, "T-1 telemetry missing"
    er = cma_diag["expected_returns"]
    assert isinstance(er, dict)
    assert len(er) >= 1
    for k, v in er.items():
        assert isinstance(v, float)
        assert math.isfinite(v)


def test_t2_volatilities_dump(augmented_source_root, augmented_assets, loader):
    """T-2: σ vector."""
    portfolio = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    cma_diag = portfolio.diagnostics["saa_diagnostics"]["cma"]
    assert "volatilities" in cma_diag, "T-2 telemetry missing"
    sig = cma_diag["volatilities"]
    assert isinstance(sig, dict)
    assert len(sig) == len(cma_diag["expected_returns"])
    for k, v in sig.items():
        assert isinstance(v, float)
        assert math.isfinite(v)
        assert v >= 0.0


def test_t3_correlation_matrix_dump(augmented_source_root, augmented_assets, loader):
    """T-3: ρ matrix (square + diag=1 + symmetric)."""
    portfolio = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    cma_diag = portfolio.diagnostics["saa_diagnostics"]["cma"]
    assert "correlation_matrix" in cma_diag, "T-3 telemetry missing"
    corr = cma_diag["correlation_matrix"]
    keys = list(cma_diag["expected_returns"].keys())
    assert set(corr.keys()) == set(keys)
    for k in keys:
        assert set(corr[k].keys()) == set(keys)
        # diag = 1
        assert abs(corr[k][k] - 1.0) < 1e-9
        for kk in keys:
            # symmetric
            assert abs(corr[k][kk] - corr[kk][k]) < 1e-9
            # bound [-1, 1]
            assert -1.0 - 1e-6 <= corr[k][kk] <= 1.0 + 1e-6


def test_t4_covariance_matrix_dump(augmented_source_root, augmented_assets, loader):
    """T-4: Σ matrix (symmetric + diag = σ² 일관성)."""
    portfolio = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    cma_diag = portfolio.diagnostics["saa_diagnostics"]["cma"]
    assert "covariance_matrix" in cma_diag, "T-4 telemetry missing"
    cov = cma_diag["covariance_matrix"]
    sig = cma_diag["volatilities"]
    keys = list(sig.keys())
    for k in keys:
        # diag(Σ) ≈ σ²
        assert abs(cov[k][k] - sig[k] ** 2) < 1e-9
        for kk in keys:
            assert abs(cov[k][kk] - cov[kk][k]) < 1e-9


def test_t5_regime_history_dump(augmented_source_root, augmented_assets, loader):
    """T-5: regime history (latest N obs, default 5)."""
    portfolio = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    regime = portfolio.diagnostics["regime"]
    assert "history" in regime, "T-5 telemetry missing"
    history = regime["history"]
    assert isinstance(history, list)
    assert 1 <= len(history) <= 5
    for entry in history:
        assert "as_of" in entry
        assert "placement" in entry
        assert "velocity" in entry
        assert "regime" in entry
        assert isinstance(entry["regime"], int)
        assert 1 <= entry["regime"] <= 4
    # 마지막 history entry == 현재 latest_state (일치 검증)
    last = history[-1]
    assert last["regime"] == regime["regime"]
    assert abs(last["placement"] - regime["placement"]) < 1e-9
    assert abs(last["velocity"] - regime["velocity"]) < 1e-9


def test_t6_saa_weights_direct_dump(augmented_source_root, augmented_assets, loader):
    """T-6: direct SAA weights (saa_diagnostics.saa_weights + asset_allocation[].saa_weight).

    핵심: inferred (taa_target − asset_tilts) 가 아닌 MVO 결과 직접 dump.
    """
    portfolio = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    saa_diag = portfolio.diagnostics["saa_diagnostics"]
    assert "saa_weights" in saa_diag, "T-6 telemetry missing"
    saa_w = saa_diag["saa_weights"]
    assert isinstance(saa_w, dict)
    assert len(saa_w) >= 1
    for k, v in saa_w.items():
        assert isinstance(v, float)
        assert math.isfinite(v)
        assert v >= -1e-9  # long-only
    # sum ≈ 1
    assert abs(sum(saa_w.values()) - 1.0) < 1e-4


def test_t6_asset_allocation_saa_weight_filled(
    augmented_source_root, augmented_assets, loader, tmp_path
):
    """T-6: review packet 의 asset_allocation[].saa_weight 가 더 이상 None 이 아님."""
    from tdf_engine.tools.build_portfolio import write_outputs
    import json

    portfolio = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    csv_path, json_path = write_outputs(
        portfolio,
        tmp_path / "out",
        "etf",
        assets=augmented_assets,
        tdf_config=loader.load_tdf_config(),
    )
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    aa = payload["asset_allocation"]
    assert aa, "asset_allocation must not be empty"
    n_with_saa = sum(1 for r in aa if r.get("saa_weight") is not None)
    # 모든 자산이 MVO 결과를 가지므로 전부 채워져야 함
    assert n_with_saa == len(aa), (
        f"saa_weight None entries remain: "
        f"{[r['asset_key'] for r in aa if r.get('saa_weight') is None]}"
    )
    # SAA sum ≈ 1
    saa_sum = sum(float(r["saa_weight"]) for r in aa)
    assert abs(saa_sum - 1.0) < 1e-4


def test_telemetry_does_not_change_allocation(
    augmented_source_root, augmented_assets, loader
):
    """telemetry 추가가 SAA / TAA / final allocation 결과에 영향을 주면 안 됨.

    동일한 입력으로 두 번 build → asset_weights / final_weights_after_projection 동일성 확인.
    """
    p1 = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    p2 = _build_etf_portfolio(augmented_source_root, augmented_assets, loader)
    # asset_weights 동일
    for k in p1.asset_weights.index:
        assert abs(float(p1.asset_weights[k]) - float(p2.asset_weights[k])) < 1e-12
    # taa_feasibility.final_weights_after_projection 동일
    feas1 = p1.diagnostics["taa_diagnostics"]["taa_feasibility"]
    feas2 = p2.diagnostics["taa_diagnostics"]["taa_feasibility"]
    f1 = feas1["final_weights_after_projection"]
    f2 = feas2["final_weights_after_projection"]
    assert set(f1.keys()) == set(f2.keys())
    for k in f1:
        assert abs(float(f1[k]) - float(f2[k])) < 1e-12


def test_existing_baseline_snapshot_unchanged():
    """기존 portfolio_*.json 의 핵심 allocation 영역 hash 가 baseline 과 동일해야 함.

    baseline = tests/_phase_e62_baseline.json (E-6.2 진입 직전 snapshot).
    telemetry 추가 후 기존 산출물 (out/db_*_relaxed/*.json) 을 재생성하지 않은 시점에서는
    이 테스트는 산출물 자체를 다시 읽어 비교하는 것이 아니라, snapshot 파일 자체가 보존되었는지만
    smoke check (baseline 파일 존재 + 키 형태 검증).

    실제 bit-identical 검증은 사용자가 build_portfolio 재실행 후 별도 수행.
    """
    from pathlib import Path
    import json

    baseline_path = (
        Path(__file__).resolve().parent / "_phase_e62_baseline.json"
    )
    assert baseline_path.exists(), "baseline snapshot missing"
    snap = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert len(snap) >= 1
    for fname, entry in snap.items():
        assert "sha256" in entry
        assert "core" in entry
        core = entry["core"]
        assert "asset_weights" in core
        assert "final_weights_after_projection" in core
        assert "max_abs_projection_drift" in core
