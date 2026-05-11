"""Phase E-9 — SAA MVO / Efficient Frontier smoke test."""

from __future__ import annotations

import json
import math
from copy import deepcopy
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
ETF_E62_JSON = (
    REPO_ROOT / "out" / "db_etf_relaxed_e62" / "portfolio_etf_20260511.json"
)
FUND_E62_JSON = (
    REPO_ROOT / "out" / "db_fund_relaxed_e62" / "portfolio_fund_20260511.json"
)


pytestmark = pytest.mark.skipif(
    not (ETF_E62_JSON.exists() and FUND_E62_JSON.exists()),
    reason="E-6.2 portfolio JSON not present",
)


# ── 1. Frontier JSON 생성 ───────────────────────────────────────────


def test_etf_frontier_json_built() -> None:
    from tdf_engine.reporting.saa_frontier import build_frontier_data, SCHEMA_VERSION

    portfolio = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    payload = build_frontier_data(portfolio, grid_points=15)
    assert payload["meta"]["schema_version"] == SCHEMA_VERSION
    assert payload["meta"]["product_type"] == "etf"
    assert payload["frontier"]["points"]


def test_fund_frontier_json_built() -> None:
    from tdf_engine.reporting.saa_frontier import build_frontier_data

    portfolio = json.loads(FUND_E62_JSON.read_text(encoding="utf-8"))
    payload = build_frontier_data(portfolio, grid_points=15)
    assert payload["meta"]["product_type"] == "fund"
    assert payload["frontier"]["points"]


# ── 2. selected_saa direct telemetry ────────────────────────────────


def test_selected_saa_uses_direct_telemetry() -> None:
    from tdf_engine.reporting.saa_frontier import build_frontier_data

    portfolio = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    payload = build_frontier_data(portfolio, grid_points=15)
    sel = payload["selected_saa"]
    direct = portfolio["diagnostics"]["saa_diagnostics"]["saa_weights"]
    for k, v in direct.items():
        assert abs(sel["weights"][k] - float(v)) < 1e-12
    assert sel["point_label"] == "selected_saa_direct_telemetry"


# ── 3. Frontier 정렬 + 비어있지 않음 ────────────────────────────────


def test_frontier_points_non_empty_and_sorted_by_volatility() -> None:
    from tdf_engine.reporting.saa_frontier import build_frontier_data

    portfolio = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    payload = build_frontier_data(portfolio, grid_points=20)
    pts = payload["frontier"]["points"]
    assert pts
    vols = [p["volatility"] for p in pts]
    assert vols == sorted(vols)


# ── 4. reference points 존재 ────────────────────────────────────────


def test_reference_points_present() -> None:
    from tdf_engine.reporting.saa_frontier import build_frontier_data

    portfolio = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    payload = build_frontier_data(portfolio, grid_points=15)
    ref = payload["reference_points"]
    for key in ("min_vol", "max_sharpe", "selected_saa"):
        assert key in ref
        for f in ("expected_return", "volatility", "sharpe", "weights"):
            assert f in ref[key]


# ── 5. selected SAA metrics 일관성 (μ, Σ 로 직접 계산) ──────────────


def test_selected_saa_metrics_numerically_consistent() -> None:
    from tdf_engine.reporting.saa_frontier import build_frontier_data

    portfolio = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    payload = build_frontier_data(portfolio, grid_points=15)
    inputs = payload["inputs"]
    keys = inputs["asset_keys"]
    er = [inputs["expected_returns"][k] for k in keys]
    cov = [
        [inputs["covariance_matrix"][ki][kj] for kj in keys] for ki in keys
    ]
    rf = float(inputs["risk_free_rate"])
    sel = payload["selected_saa"]
    w = [sel["weights"][k] for k in keys]
    expected_ret = sum(w[i] * er[i] for i in range(len(keys)))
    var = sum(w[i] * sum(cov[i][j] * w[j] for j in range(len(keys))) for i in range(len(keys)))
    expected_vol = math.sqrt(max(var, 0.0))
    assert abs(sel["expected_return"] - expected_ret) < 1e-9
    assert abs(sel["volatility"] - expected_vol) < 1e-9
    if expected_vol > 1e-9:
        expected_sharpe = (expected_ret - rf) / expected_vol
        assert abs(sel["sharpe"] - expected_sharpe) < 1e-9


# ── 6. PNG 생성 ─────────────────────────────────────────────────────


def test_render_saa_mvo_creates_png(tmp_path: Path) -> None:
    from tdf_engine.reporting.saa_frontier import (
        build_frontier_data,
        render_saa_mvo,
    )

    portfolio = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    payload = build_frontier_data(portfolio, grid_points=15)
    out = tmp_path / "saa_mvo.png"
    result = render_saa_mvo(payload, out, label="ETF")
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 30000


# ── 7. Mutation guard ───────────────────────────────────────────────


def test_input_files_not_mutated() -> None:
    from tdf_engine.reporting.saa_frontier import build_frontier_data, render_saa_mvo

    src_text = ETF_E62_JSON.read_text(encoding="utf-8")
    portfolio = json.loads(src_text)
    snapshot = deepcopy(portfolio)
    payload = build_frontier_data(portfolio, grid_points=10)
    payload_snapshot = deepcopy(payload)
    render_saa_mvo(payload, Path("/tmp/x_dummy.png"), label="ETF")  # no overwrite check, just mutation guard
    assert ETF_E62_JSON.read_text(encoding="utf-8") == src_text
    assert portfolio == snapshot
    assert payload == payload_snapshot


# ── 8. Missing telemetry → ValueError ───────────────────────────────


def test_missing_direct_saa_fails(tmp_path: Path) -> None:
    from tdf_engine.reporting.saa_frontier import build_frontier_data

    broken = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    broken["diagnostics"]["saa_diagnostics"].pop("saa_weights", None)
    with pytest.raises(ValueError) as exc:
        build_frontier_data(broken, grid_points=10)
    assert "saa_weights" in str(exc.value)


def test_missing_cma_fails() -> None:
    from tdf_engine.reporting.saa_frontier import build_frontier_data

    broken = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    broken["diagnostics"]["saa_diagnostics"]["cma"].pop("expected_returns", None)
    with pytest.raises(ValueError) as exc:
        build_frontier_data(broken, grid_points=10)
    assert "expected_returns" in str(exc.value)


# ── 9. CLI smoke ────────────────────────────────────────────────────


def test_cli_creates_etf_fund_outputs(tmp_path: Path) -> None:
    from tdf_engine.tools import build_saa_frontier as cli

    out_dir = tmp_path / "saa_frontier"
    summary_md = out_dir / "summary.md"
    rc = cli.main(
        [
            "--as-of-run", "20260511",
            "--input-etf", str(ETF_E62_JSON),
            "--input-fund", str(FUND_E62_JSON),
            "--output-dir", str(out_dir),
            "--summary-md", str(summary_md),
            "--grid-points", "15",
        ]
    )
    assert rc == 0
    for p in (
        out_dir / "saa_frontier_etf_20260511.json",
        out_dir / "saa_frontier_fund_20260511.json",
        out_dir / "saa_mvo_etf_20260511.png",
        out_dir / "saa_mvo_fund_20260511.png",
        summary_md,
    ):
        assert p.exists(), f"missing {p}"
