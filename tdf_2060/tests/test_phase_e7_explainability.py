"""Phase E-7 — Explainability data layer smoke test.

검증:
- 5 블록 (meta / regime / saa / taa / product_selection / report_ready_summary) 모두 존재.
- SAA block: μ/σ/ρ/Σ/saa_weights 직접 telemetry 사용 (inferred 금지).
- TAA block: current regime + tilt_decisions + before/after summary.
- Product block: actual product name/manager/asset_key 포함, ticker 미존재 명시.
- missing_data 가 명시되어 있다 (efficient_frontier / regime_history(24m) / scoring / ticker).
- 입력 portfolio JSON 파일 mutation 없음.
- direct SAA telemetry 부재 시 ValueError.
"""

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
TAA_POLICY = REPO_ROOT / "tdf_engine" / "config" / "taa_policy.yaml"


pytestmark = pytest.mark.skipif(
    not (ETF_E62_JSON.exists() and FUND_E62_JSON.exists() and TAA_POLICY.exists()),
    reason="E-6.2 telemetry portfolio JSON or taa_policy.yaml not present",
)


# ── 1. Schema / 5 블록 존재 ───────────────────────────────────────────


def test_explainability_top_level_blocks() -> None:
    from tdf_engine.reporting.explainability import build_explainability, SCHEMA_VERSION

    payload = build_explainability(ETF_E62_JSON, taa_policy_yaml=TAA_POLICY)
    for block in (
        "meta",
        "regime_explainability",
        "saa_explainability",
        "taa_explainability",
        "product_selection_explainability",
        "report_ready_summary",
    ):
        assert block in payload, f"missing top-level block: {block}"
    assert payload["meta"]["schema_version"] == SCHEMA_VERSION


# ── 2. Mutation guard ────────────────────────────────────────────────


def test_input_json_not_mutated(tmp_path: Path) -> None:
    from tdf_engine.reporting.explainability import build_explainability

    src_text = ETF_E62_JSON.read_text(encoding="utf-8")
    _ = build_explainability(ETF_E62_JSON, taa_policy_yaml=TAA_POLICY)
    assert ETF_E62_JSON.read_text(encoding="utf-8") == src_text


# ── 3. SAA block — direct telemetry only ──────────────────────────────


def test_saa_block_uses_direct_telemetry_and_includes_cma() -> None:
    from tdf_engine.reporting.explainability import build_explainability

    payload = build_explainability(ETF_E62_JSON, taa_policy_yaml=TAA_POLICY)
    saa = payload["saa_explainability"]
    cma = saa["cma_inputs"]
    assert cma["expected_returns"]
    assert cma["volatilities"]
    assert cma["correlation_matrix"]
    assert cma["covariance_matrix"]

    # selected SAA weights = direct telemetry
    saa_w = saa["optimization"]["selected_saa_weights"]
    assert saa_w
    assert abs(sum(saa_w.values()) - 1.0) < 1e-4

    # 추가 read-only 계산 항목
    sel = saa["optimization"]["selected_point"]
    assert math.isfinite(float(sel["expected_return"]))
    assert float(sel["volatility"]) >= 0.0

    # risk contribution sums to ~1 (또는 0 if vol=0)
    rc = saa["risk_contribution"]
    if rc["available"] and rc["portfolio_volatility"] > 1e-9:
        pct_sum = sum(v["percent_risk_contribution"] for v in rc["by_asset"].values())
        assert abs(pct_sum - 1.0) < 1e-3

    # efficient frontier deferred
    assert saa["efficient_frontier"]["available"] is False
    assert saa["efficient_frontier"]["deferred_to"] == "E-9"


def test_explainability_requires_direct_saa_telemetry(tmp_path: Path) -> None:
    """saa_diagnostics.saa_weights 가 없으면 ValueError."""
    from tdf_engine.reporting.explainability import build_explainability

    broken = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    broken["diagnostics"]["saa_diagnostics"].pop("saa_weights", None)
    broken_path = tmp_path / "portfolio_broken.json"
    broken_path.write_text(json.dumps(broken), encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        build_explainability(broken_path, taa_policy_yaml=TAA_POLICY)
    assert "saa_weights" in str(exc.value)
    assert "Inferred" in str(exc.value) or "inferred" in str(exc.value)


def test_explainability_no_inferred_saa_path_in_module() -> None:
    """explainability.py 가 inferred SAA 경로 사용하지 않음 (AST 기반)."""
    import ast

    src_path = REPO_ROOT / "tdf_engine" / "reporting" / "explainability.py"
    src = src_path.read_text(encoding="utf-8")
    tree = ast.parse(src)

    identifiers: set[str] = set()

    class _C(ast.NodeVisitor):
        def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
            identifiers.add(node.id)
            self.generic_visit(node)

        def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: N802
            identifiers.add(node.attr)
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
            identifiers.add(node.name)
            self.generic_visit(node)

    _C().visit(tree)

    forbidden = {"asset_tilts"}  # SAA 역산 식별자 (단, taa_policy lookup 은 별도 ok)
    # asset_tilts 는 taa_policy.yaml lookup 변수로 사용될 수 있음 — string literal 만 허용
    # 식별자 자체로 SAA 역산에 쓰이면 안 됨. "asset_tilts" 식별자는 explainability.py 에서
    # 'asset_tilts_pp' 같은 변수명이지만 SAA 역산 (taa_target - asset_tilts) 식은 없음.
    # 단순 substring 검사 대신 다음 패턴이 없어야 함:
    forbidden_patterns = ["_inferred", "infer_saa"]
    for ident in identifiers:
        for pat in forbidden_patterns:
            assert pat not in ident, f"identifier '{ident}' contains '{pat}'"
    # require_direct_saa_telemetry 가드 사용
    assert "_require_direct_saa_telemetry" in identifiers


# ── 4. Regime block ──────────────────────────────────────────────────


def test_regime_block_history_and_preference() -> None:
    from tdf_engine.reporting.explainability import build_explainability, EXPECTED_REGIME_HISTORY_MONTHS

    payload = build_explainability(ETF_E62_JSON, taa_policy_yaml=TAA_POLICY)
    reg = payload["regime_explainability"]
    cur = reg["current"]
    assert cur["region"]
    assert isinstance(cur["regime"], int) and 1 <= cur["regime"] <= 4
    hist = reg["history"]
    assert hist["count"] >= 1
    assert hist["expected_full_history_months"] == EXPECTED_REGIME_HISTORY_MONTHS
    # 5 obs only — full history 미충족
    assert hist["full_history_available"] is False
    # asset_class_preference from taa_policy
    by_asset = reg["asset_class_preference"]["by_asset"]
    assert by_asset
    for ak, info in by_asset.items():
        assert info["preference"] in ("overweight", "neutral", "underweight")
        assert info["source"] == "rule_based"


# ── 5. TAA block ─────────────────────────────────────────────────────


def test_taa_block_tilt_decisions_and_before_after() -> None:
    from tdf_engine.reporting.explainability import build_explainability

    payload = build_explainability(ETF_E62_JSON, taa_policy_yaml=TAA_POLICY)
    taa = payload["taa_explainability"]
    cur = taa["current_regime"]
    assert isinstance(cur["regime"], int) and 1 <= cur["regime"] <= 4
    decisions = taa["tilt_decisions"]["by_asset"]
    assert decisions
    for ak, d in decisions.items():
        assert d["direction"] in ("overweight", "underweight", "neutral")
        assert d["source"] == "rule_based"
    # tilt sum ≈ 0 (long-only + sum=1 정합)
    s = sum(d["tilt"] for d in decisions.values())
    assert abs(s) < 1e-6, f"tilt sum should be ~0, got {s}"
    # regime conditioned assumptions = unavailable (현 prototype)
    assert taa["regime_conditioned_assumptions"]["available"] is False
    # before/after summary present
    summ = taa["taa_portfolio_summary"]
    assert "expected_return_before_tilt" in summ
    assert "expected_return_after_tilt" in summ
    assert "improvement_summary" in summ


# ── 6. Product block ─────────────────────────────────────────────────


def test_product_block_includes_real_product_metadata() -> None:
    from tdf_engine.reporting.explainability import build_explainability

    payload = build_explainability(ETF_E62_JSON, taa_policy_yaml=TAA_POLICY)
    prod = payload["product_selection_explainability"]
    sel = prod["final_selection"]["selected_products"]
    assert sel
    for r in sel:
        assert r["product_id"]
        assert r["product_name"]
        assert r["asset_key"]
        assert r["bucket"]
        assert r["manager"]
        assert isinstance(r["rank_within_asset"], int) and r["rank_within_asset"] >= 1
    # ticker 는 etf_list/fund_list 에 없으므로 None
    tickers = {r["ticker"] for r in sel}
    assert tickers == {None}
    # missing_data 명시
    msgs = [m["field"] for m in prod["diagnostics"]["missing_data"]]
    assert any("ticker" in m for m in msgs)
    assert any("scoring" in m or "scored_products" in m for m in msgs)


# ── 7. report_ready_summary ──────────────────────────────────────────


def test_report_ready_summary_text_blocks() -> None:
    from tdf_engine.reporting.explainability import build_explainability

    payload = build_explainability(ETF_E62_JSON, taa_policy_yaml=TAA_POLICY)
    rrs = payload["report_ready_summary"]
    for sec in (
        "regime_summary",
        "saa_summary",
        "taa_summary",
        "product_selection_summary",
    ):
        assert rrs[sec]["title"]
    assert any(w["warning_code"] == "EFRONTIER_DEFERRED" for w in rrs["warnings"])
    assert any("regime.history" in m["field"] for m in rrs["missing_data"])


# ── 8. CLI smoke ─────────────────────────────────────────────────────


def test_cli_creates_etf_fund_json_and_summary(tmp_path: Path) -> None:
    from tdf_engine.tools import build_explainability as cli

    out_dir = tmp_path / "explainability"
    summary_md = tmp_path / "summary.md"
    rc = cli.main(
        [
            "--as-of-run", "20260511",
            "--input-etf", str(ETF_E62_JSON),
            "--input-fund", str(FUND_E62_JSON),
            "--taa-policy", str(TAA_POLICY),
            "--output-dir", str(out_dir),
            "--summary-md", str(summary_md),
        ]
    )
    assert rc == 0
    etf_json = out_dir / "explainability_etf_20260511.json"
    fund_json = out_dir / "explainability_fund_20260511.json"
    assert etf_json.exists() and etf_json.stat().st_size > 5000
    assert fund_json.exists() and fund_json.stat().st_size > 5000
    assert summary_md.exists()
    md = summary_md.read_text(encoding="utf-8")
    assert "## ETF" in md and "## Fund" in md
    assert "Missing data" in md
