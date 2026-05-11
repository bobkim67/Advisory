"""Phase E-11B — Product Selection Visualization smoke test."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
ETF_TELEMETRY = (
    REPO_ROOT / "out" / "db_review_relaxed_e62" / "product_selection_telemetry"
    / "20260511" / "product_selection_telemetry_etf_20260511.json"
)
FUND_TELEMETRY = (
    REPO_ROOT / "out" / "db_review_relaxed_e62" / "product_selection_telemetry"
    / "20260511" / "product_selection_telemetry_fund_20260511.json"
)


pytestmark = pytest.mark.skipif(
    not (ETF_TELEMETRY.exists() and FUND_TELEMETRY.exists()),
    reason="E-11A telemetry JSON not present (run build_product_selection_telemetry first)",
)


# ── 1. PNG ──────────────────────────────────────────────────────────


def test_etf_png_created(tmp_path: Path) -> None:
    from tdf_engine.reporting.product_selection_viz import (
        build_visualization_data,
        render_product_selection,
    )

    payload = build_visualization_data(ETF_TELEMETRY)
    out = tmp_path / "etf.png"
    result = render_product_selection(payload, out, label="ETF")
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 30000


def test_fund_png_created(tmp_path: Path) -> None:
    from tdf_engine.reporting.product_selection_viz import (
        build_visualization_data,
        render_product_selection,
    )

    payload = build_visualization_data(FUND_TELEMETRY)
    out = tmp_path / "fund.png"
    render_product_selection(payload, out, label="Fund")
    assert out.exists()
    assert out.stat().st_size > 30000


# ── 2. visualization JSON ───────────────────────────────────────────


def test_visualization_json_etf_fund() -> None:
    from tdf_engine.reporting.product_selection_viz import (
        build_visualization_data,
        SCHEMA_VERSION,
    )

    for path, pt in ((ETF_TELEMETRY, "etf"), (FUND_TELEMETRY, "fund")):
        payload = build_visualization_data(path)
        assert payload["meta"]["schema_version"] == SCHEMA_VERSION
        assert payload["meta"]["product_type"] == pt
        assert "funnel" in payload
        assert "asset_coverage" in payload
        assert "filter_exclusions" in payload
        assert "selected_product_table" in payload


# ── 3. funnel counts match telemetry ────────────────────────────────


def test_funnel_counts_match_telemetry() -> None:
    from tdf_engine.reporting.product_selection_viz import build_visualization_data

    telemetry = json.loads(ETF_TELEMETRY.read_text(encoding="utf-8"))
    payload = build_visualization_data(ETF_TELEMETRY)
    funnel = payload["funnel"]
    uni = telemetry["universe"]
    assert funnel["raw_count"] == uni["raw_count"]
    assert funnel["passed_filter_count"] == uni["passed_filter_count"]
    assert funnel["classified_count"] == uni["classified_count"]
    elig_sum = sum(v["eligible_count"] for v in uni["by_asset"].values())
    sel_sum = sum(v["selected_count"] for v in uni["by_asset"].values())
    assert funnel["eligible_count"] == elig_sum
    assert funnel["selected_count"] == sel_sum


# ── 4. selected_product_table rows match final_selection ────────────


def test_selected_product_table_matches_final_selection() -> None:
    from tdf_engine.reporting.product_selection_viz import build_visualization_data

    telemetry = json.loads(ETF_TELEMETRY.read_text(encoding="utf-8"))
    payload = build_visualization_data(ETF_TELEMETRY)
    fs_ids = {r["product_id"] for r in telemetry["final_selection"]["selected_products"]}
    table_ids = {r["product_id"] for r in payload["selected_product_table"]["rows"]}
    assert fs_ids == table_ids


# ── 5. product_id / product_name / manager 모두 존재 ────────────────


def test_required_product_fields_present() -> None:
    from tdf_engine.reporting.product_selection_viz import build_visualization_data

    payload = build_visualization_data(ETF_TELEMETRY)
    for r in payload["selected_product_table"]["rows"]:
        assert r["product_id"]
        assert r["product_name"]
        assert r["manager"]
        assert r["asset_key"]


# ── 6. ticker missing 명시 ──────────────────────────────────────────


def test_missing_ticker_explicitly_recorded() -> None:
    from tdf_engine.reporting.product_selection_viz import build_visualization_data

    payload = build_visualization_data(ETF_TELEMETRY)
    rows = payload["selected_product_table"]["rows"]
    assert all(r["ticker"] is None for r in rows)
    msgs = [m["field"] for m in payload["diagnostics"]["missing_data"]]
    assert any("ticker" in m for m in msgs)


# ── 7. mutation 없음 ────────────────────────────────────────────────


def test_renderer_does_not_mutate_inputs(tmp_path: Path) -> None:
    from tdf_engine.reporting.product_selection_viz import (
        build_visualization_data,
        render_product_selection,
    )

    src = ETF_TELEMETRY.read_text(encoding="utf-8")
    payload = build_visualization_data(ETF_TELEMETRY)
    payload_snapshot = json.dumps(payload, sort_keys=True, default=str)
    render_product_selection(payload, tmp_path / "x.png", label="ETF")
    assert ETF_TELEMETRY.read_text(encoding="utf-8") == src
    assert json.dumps(payload, sort_keys=True, default=str) == payload_snapshot


# ── 8. score factor weights 보존 ────────────────────────────────────


def test_score_factor_weights_preserved_exactly() -> None:
    from tdf_engine.reporting.product_selection_viz import build_visualization_data

    telemetry = json.loads(ETF_TELEMETRY.read_text(encoding="utf-8"))
    payload = build_visualization_data(ETF_TELEMETRY)
    src_factors = telemetry["scoring"]["score_factors"]
    out_factors = payload["input_telemetry"]["score_factors"]
    assert len(src_factors) == len(out_factors)
    for s, o in zip(src_factors, out_factors):
        assert s["factor"] == o["factor"]
        assert float(s["weight"]) == float(o["weight"])
        assert bool(s.get("available")) == bool(o.get("available"))


# ── 9. 0-eligible asset → coverage_status=none ──────────────────────


def test_zero_eligible_asset_marked_as_none() -> None:
    from tdf_engine.reporting.product_selection_viz import build_visualization_data

    payload = build_visualization_data(ETF_TELEMETRY)
    cov = payload["asset_coverage"]["by_asset"]
    # 데이터: kr_aggregate_bond / kr_treasury_10y / us_treasury_30y 0 eligible
    expected_none = {"kr_aggregate_bond", "kr_treasury_10y", "us_treasury_30y"}
    actual_none = {k for k, v in cov.items() if v["coverage_status"] == "none"}
    assert expected_none.issubset(actual_none)


# ── 10. CLI smoke ───────────────────────────────────────────────────


def test_cli_creates_etf_fund_outputs(tmp_path: Path) -> None:
    from tdf_engine.tools import build_product_selection_viz as cli

    out_dir = tmp_path / "viz"
    summary_md = out_dir / "summary.md"
    rc = cli.main(
        [
            "--as-of-run", "20260511",
            "--input-etf-telemetry", str(ETF_TELEMETRY),
            "--input-fund-telemetry", str(FUND_TELEMETRY),
            "--output-dir", str(out_dir),
            "--summary-md", str(summary_md),
        ]
    )
    assert rc == 0
    for p in (
        out_dir / "product_selection_etf_20260511.png",
        out_dir / "product_selection_fund_20260511.png",
        out_dir / "product_selection_visualization_etf_20260511.json",
        out_dir / "product_selection_visualization_fund_20260511.json",
        summary_md,
    ):
        assert p.exists(), f"missing {p}"
