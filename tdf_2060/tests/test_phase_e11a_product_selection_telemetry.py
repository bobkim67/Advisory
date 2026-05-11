"""Phase E-11A — Product Selection Score Telemetry smoke test."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
ETF_E11A_JSON = (
    REPO_ROOT / "out" / "db_etf_relaxed_e62_e11a" / "portfolio_etf_20260511.json"
)
FUND_E11A_JSON = (
    REPO_ROOT / "out" / "db_fund_relaxed_e62_e11a" / "portfolio_fund_20260511.json"
)


pytestmark = pytest.mark.skipif(
    not (ETF_E11A_JSON.exists() and FUND_E11A_JSON.exists()),
    reason="E-11A patched portfolio JSON not present (run build_portfolio first)",
)


# ── 1. JSON 생성 ────────────────────────────────────────────────────


def test_etf_telemetry_json_built() -> None:
    from tdf_engine.reporting.product_selection_telemetry import (
        build_product_selection_telemetry,
        SCHEMA_VERSION,
    )

    payload = build_product_selection_telemetry(ETF_E11A_JSON)
    assert payload["meta"]["schema_version"] == SCHEMA_VERSION
    assert payload["meta"]["product_type"] == "etf"
    assert payload["scoring"]["scored_products"]


def test_fund_telemetry_json_built() -> None:
    from tdf_engine.reporting.product_selection_telemetry import (
        build_product_selection_telemetry,
    )

    payload = build_product_selection_telemetry(FUND_E11A_JSON)
    assert payload["meta"]["product_type"] == "fund"
    assert payload["scoring"]["scored_products"]


# ── 3. selected products in telemetry match portfolio.product_weights ──


def test_selected_products_match_portfolio_product_weights() -> None:
    from tdf_engine.reporting.product_selection_telemetry import (
        build_product_selection_telemetry,
    )

    portfolio = json.loads(ETF_E11A_JSON.read_text(encoding="utf-8"))
    pa_ids = {str(r.get("product_id")) for r in (portfolio.get("product_allocation") or [])}
    payload = build_product_selection_telemetry(ETF_E11A_JSON)
    fs_ids = {r["product_id"] for r in payload["final_selection"]["selected_products"]}
    assert pa_ids == fs_ids
    # selected=True 인 scored_product 도 동일 set
    selected_ids = {
        r["product_id"]
        for r in payload["scoring"]["scored_products"]
        if r["selected"]
    }
    assert pa_ids == selected_ids


# ── 4. scored_products 필드 ─────────────────────────────────────────


def test_scored_products_have_required_fields() -> None:
    from tdf_engine.reporting.product_selection_telemetry import (
        build_product_selection_telemetry,
    )

    payload = build_product_selection_telemetry(ETF_E11A_JSON)
    for r in payload["scoring"]["scored_products"]:
        assert "product_id" in r
        assert "product_name" in r and r["product_name"]
        assert "asset_key" in r and r["asset_key"]
        assert "score" in r and isinstance(r["score"], (int, float))
        assert "rank_within_asset" in r
        assert isinstance(r["rank_within_asset"], int)
        assert r["rank_within_asset"] >= 1
        assert "selected" in r
        assert isinstance(r["selected"], bool)
        assert "factor_values" in r and isinstance(r["factor_values"], dict)


# ── 5. rank order deterministic (sort by score desc within asset) ───


def test_rank_order_is_score_desc_within_asset() -> None:
    from tdf_engine.reporting.product_selection_telemetry import (
        build_product_selection_telemetry,
    )

    payload = build_product_selection_telemetry(ETF_E11A_JSON)
    by_asset: dict[str, list] = {}
    for r in payload["scoring"]["scored_products"]:
        by_asset.setdefault(r["asset_key"], []).append(r)
    for ak, rows in by_asset.items():
        rows_sorted = sorted(rows, key=lambda x: x["rank_within_asset"])
        scores = [r["score"] for r in rows_sorted]
        assert scores == sorted(scores, reverse=True), (
            f"asset {ak} rank order != score desc"
        )


# ── 6. ticker missing → missing_data 에 명시 ────────────────────────


def test_missing_ticker_recorded_in_missing_data() -> None:
    from tdf_engine.reporting.product_selection_telemetry import (
        build_product_selection_telemetry,
    )

    payload = build_product_selection_telemetry(ETF_E11A_JSON)
    sel = payload["final_selection"]["selected_products"]
    assert all(r["ticker"] is None for r in sel)
    msgs = [m["field"] for m in payload["diagnostics"]["missing_data"]]
    assert any("ticker" in m for m in msgs)


# ── 7. extractor 가 portfolio JSON mutate 안 함 ─────────────────────


def test_extractor_does_not_mutate_input_file() -> None:
    from tdf_engine.reporting.product_selection_telemetry import (
        build_product_selection_telemetry,
    )

    src = ETF_E11A_JSON.read_text(encoding="utf-8")
    _ = build_product_selection_telemetry(ETF_E11A_JSON)
    assert ETF_E11A_JSON.read_text(encoding="utf-8") == src


# ── 8. bit-identical (selection telemetry 추가 전후 동일) ───────────


def test_e11a_baseline_bit_identical() -> None:
    """E-11A telemetry 추가 후 e11a JSON 의 allocation core 가 _phase_e62_baseline.json 의 sha256 과 일치."""
    import hashlib

    baseline = json.loads(
        (REPO_ROOT / "tests" / "_phase_e62_baseline.json").read_text(encoding="utf-8")
    )

    def _norm_dcs(dcs):
        if not dcs:
            return dcs
        out = {**dcs}
        for k in ("inflow_assets", "outflow_assets"):
            if k in out:
                out[k] = sorted(out[k])
        for k in ("inflow_by_asset", "outflow_by_asset"):
            if k in out:
                out[k] = dict(sorted((out[k] or {}).items()))
        return out

    def _extract(p):
        d = json.loads(p.read_text(encoding="utf-8"))
        diag = d.get("diagnostics", {})
        feas = (diag.get("taa_diagnostics") or {}).get("taa_feasibility") or {}
        quality = diag.get("quality") or {}
        return {
            "asset_weights": d.get("asset_weights"),
            "asset_weight_sum": d.get("asset_weight_sum"),
            "product_weight_sum": d.get("product_weight_sum"),
            "product_weights": d.get("product_weights"),
            "final_weights_after_projection": feas.get("final_weights_after_projection"),
            "target_weights_before_projection": feas.get("target_weights_before_projection"),
            "max_abs_projection_drift": feas.get("max_abs_projection_drift"),
            "bucket_weights_after_projection": feas.get("bucket_weights_after_projection"),
            "drift_clipping_summary": _norm_dcs(quality.get("drift_clipping_summary")),
            "max_abs_asset_weight_drift": quality.get("max_abs_asset_weight_drift"),
        }

    for base_key, p in (
        ("portfolio_etf_20260508.json", ETF_E11A_JSON),
        ("portfolio_fund_20260508.json", FUND_E11A_JSON),
    ):
        new_hash = hashlib.sha256(
            json.dumps(_extract(p), sort_keys=True, default=str).encode()
        ).hexdigest()
        base_hash = baseline[base_key]["sha256"]
        assert new_hash == base_hash, (
            f"E-11A allocation core hash mismatch for {base_key}: "
            f"new={new_hash[:24]} vs base={base_hash[:24]}"
        )


# ── 9. missing scoring data → ValueError ────────────────────────────


def test_missing_scored_products_fails_clearly(tmp_path: Path) -> None:
    from tdf_engine.reporting.product_selection_telemetry import (
        build_product_selection_telemetry,
    )

    broken = json.loads(ETF_E11A_JSON.read_text(encoding="utf-8"))
    broken["diagnostics"]["selection_diagnostics"].pop("scored_products", None)
    broken_path = tmp_path / "broken.json"
    broken_path.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        build_product_selection_telemetry(broken_path)
    assert "scored_products" in str(exc.value)


# ── 10. CLI smoke ───────────────────────────────────────────────────


def test_cli_creates_etf_fund_outputs(tmp_path: Path) -> None:
    from tdf_engine.tools import build_product_selection_telemetry as cli

    out_dir = tmp_path / "telemetry"
    summary_md = out_dir / "summary.md"
    rc = cli.main(
        [
            "--as-of-run", "20260511",
            "--input-etf", str(ETF_E11A_JSON),
            "--input-fund", str(FUND_E11A_JSON),
            "--output-dir", str(out_dir),
            "--summary-md", str(summary_md),
        ]
    )
    assert rc == 0
    for p in (
        out_dir / "product_selection_telemetry_etf_20260511.json",
        out_dir / "product_selection_telemetry_fund_20260511.json",
        summary_md,
    ):
        assert p.exists(), f"missing {p}"
