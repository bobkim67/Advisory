"""Phase E-10 — TAA Regime Tilt smoke test."""

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
    reason="E-6.2 portfolio JSON or taa_policy.yaml not present",
)


def _load_taa_policy() -> dict:
    import yaml

    return yaml.safe_load(TAA_POLICY.read_text(encoding="utf-8")) or {}


# ── 1. Tilt JSON 생성 ───────────────────────────────────────────────


def test_etf_tilt_json_built() -> None:
    from tdf_engine.reporting.taa_tilt import build_taa_tilt, SCHEMA_VERSION

    portfolio = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    payload = build_taa_tilt(portfolio, taa_policy=_load_taa_policy())
    assert payload["meta"]["schema_version"] == SCHEMA_VERSION
    assert payload["meta"]["product_type"] == "etf"


def test_fund_tilt_json_built() -> None:
    from tdf_engine.reporting.taa_tilt import build_taa_tilt

    portfolio = json.loads(FUND_E62_JSON.read_text(encoding="utf-8"))
    payload = build_taa_tilt(portfolio, taa_policy=_load_taa_policy())
    assert payload["meta"]["product_type"] == "fund"


# ── 2. method label = rule_based ────────────────────────────────────


def test_tilt_policy_method_is_rule_based() -> None:
    from tdf_engine.reporting.taa_tilt import build_taa_tilt, METHOD_LABEL

    portfolio = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    payload = build_taa_tilt(portfolio, taa_policy=_load_taa_policy())
    assert METHOD_LABEL == "rule_based"
    assert payload["tilt_policy"]["method"] == "rule_based"


# ── 3. limitation text — explicitly NOT regime-conditioned MVO ──────


def test_limitation_text_says_not_regime_conditioned_mvo() -> None:
    from tdf_engine.reporting.taa_tilt import build_taa_tilt, LIMITATION_TEXT

    portfolio = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    payload = build_taa_tilt(portfolio, taa_policy=_load_taa_policy())
    text = payload["tilt_policy"]["limitation_text"]
    # rule-based 명시
    assert "rule-based" in text.lower()
    # NOT regime-conditioned MVO 명시
    assert "regime-conditioned mvo" in text.lower() or "not regime-conditioned" in text.lower()
    assert "not optimized" in text.lower()
    # 모듈 상수와 일치
    assert text == LIMITATION_TEXT


# ── 4. tilt_rules_applied includes all non-zero policy tilts ────────


def test_tilt_rules_match_policy_non_zero() -> None:
    from tdf_engine.reporting.taa_tilt import build_taa_tilt

    policy = _load_taa_policy()
    portfolio = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    regime_id = int(portfolio["diagnostics"]["regime"]["regime"])
    expected_non_zero = {
        ak for ak, w in
        ((policy.get("regime_tilts") or {}).get(regime_id) or {}).get("asset_tilts", {}).items()
        if abs(float(w)) > 1e-9
    }
    payload = build_taa_tilt(portfolio, taa_policy=policy)
    rules_non_zero = {
        r["asset_key"] for r in payload["tilt_rules_applied"]
        if abs(r["applied_tilt_pp"]) > 1e-6
    }
    assert expected_non_zero == rules_non_zero, (
        f"policy non-zero {expected_non_zero} != rules applied {rules_non_zero}"
    )


# ── 5. before/after metrics numerically consistent ──────────────────


def test_before_after_metrics_consistent_with_mu_sigma() -> None:
    from tdf_engine.reporting.taa_tilt import build_taa_tilt

    portfolio = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    payload = build_taa_tilt(portfolio, taa_policy=_load_taa_policy())
    cma = portfolio["diagnostics"]["saa_diagnostics"]["cma"]
    keys = list(cma["expected_returns"].keys())
    er = [float(cma["expected_returns"][k]) for k in keys]
    cov = [
        [float((cma["covariance_matrix"].get(ki) or {}).get(kj, 0.0)) for kj in keys]
        for ki in keys
    ]
    rf = float(portfolio["diagnostics"]["saa_diagnostics"].get("rf") or 0.0)

    saa_w = [float(payload["portfolio_before_after"]["saa"]["weights"].get(k, 0.0)) for k in keys]
    taa_w = [float(payload["portfolio_before_after"]["taa_target"]["weights"].get(k, 0.0)) for k in keys]

    def metrics(w):
        ret = sum(w[i] * er[i] for i in range(len(keys)))
        var = sum(
            w[i] * sum(cov[i][j] * w[j] for j in range(len(keys)))
            for i in range(len(keys))
        )
        var = max(var, 0.0)
        vol = math.sqrt(var)
        sh = (ret - rf) / vol if vol > 1e-12 else float("nan")
        return ret, vol, sh

    saa_ret, saa_vol, saa_sh = metrics(saa_w)
    taa_ret, taa_vol, taa_sh = metrics(taa_w)

    saa_block = payload["portfolio_before_after"]["saa"]
    taa_block = payload["portfolio_before_after"]["taa_target"]
    assert abs(saa_block["expected_return"] - saa_ret) < 1e-9
    assert abs(saa_block["volatility"] - saa_vol) < 1e-9
    assert abs(saa_block["sharpe"] - saa_sh) < 1e-9
    assert abs(taa_block["expected_return"] - taa_ret) < 1e-9
    assert abs(taa_block["volatility"] - taa_vol) < 1e-9
    assert abs(taa_block["sharpe"] - taa_sh) < 1e-9


# ── 6. PNG 생성 ─────────────────────────────────────────────────────


def test_render_taa_tilt_creates_png(tmp_path: Path) -> None:
    from tdf_engine.reporting.taa_tilt import build_taa_tilt, render_taa_tilt

    portfolio = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    payload = build_taa_tilt(portfolio, taa_policy=_load_taa_policy())
    out = tmp_path / "taa_tilt.png"
    result = render_taa_tilt(payload, out, label="ETF")
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 30000


# ── 7. Mutation guard ───────────────────────────────────────────────


def test_input_files_not_mutated() -> None:
    from tdf_engine.reporting.taa_tilt import build_taa_tilt, render_taa_tilt

    src_text = ETF_E62_JSON.read_text(encoding="utf-8")
    portfolio = json.loads(src_text)
    snapshot = deepcopy(portfolio)
    payload = build_taa_tilt(portfolio, taa_policy=_load_taa_policy())
    payload_snapshot = deepcopy(payload)
    render_taa_tilt(payload, Path("/tmp/x_dummy.png"), label="ETF")
    assert ETF_E62_JSON.read_text(encoding="utf-8") == src_text
    assert portfolio == snapshot
    assert payload == payload_snapshot


# ── 8. Missing telemetry → ValueError ───────────────────────────────


def test_missing_direct_saa_fails() -> None:
    from tdf_engine.reporting.taa_tilt import build_taa_tilt

    broken = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    broken["diagnostics"]["saa_diagnostics"].pop("saa_weights", None)
    with pytest.raises(ValueError) as exc:
        build_taa_tilt(broken, taa_policy=_load_taa_policy())
    assert "saa_weights" in str(exc.value)


def test_missing_taa_feasibility_fails() -> None:
    from tdf_engine.reporting.taa_tilt import build_taa_tilt

    broken = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    broken["diagnostics"]["taa_diagnostics"]["taa_feasibility"].pop(
        "target_weights_before_projection", None
    )
    with pytest.raises(ValueError) as exc:
        build_taa_tilt(broken, taa_policy=_load_taa_policy())
    assert "target_weights_before_projection" in str(exc.value)


# ── 9. Module never claims optimization ─────────────────────────────


def test_module_does_not_claim_optimization() -> None:
    """사용자 명시 §: "optimized TAA" / "regime-conditioned MVO" 표현 사용 금지.

    runtime string literal (출력 라벨 등) 검사. docstring 은 LIMITATION 설명 위해
    "not optimized" 처럼 부정 표현으로 사용 가능. AST string constant 중 출력 가능한
    위치에 'optimized TAA' 또는 'optimized taa' literal 존재 금지.
    """
    import ast

    src = (REPO_ROOT / "tdf_engine" / "reporting" / "taa_tilt.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    # docstring 제외하고 string literal 검사
    docstrings: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            ds = ast.get_docstring(node, clean=False)
            if ds:
                docstrings.add(ds)
    runtime_strings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in docstrings:
                continue
            runtime_strings.append(node.value)

    # "optimized TAA" 또는 "TAA optimization" 이 긍정 라벨로 사용되면 안 됨.
    # 단 LIMITATION_TEXT 에 "NOT optimized TAA" 처럼 부정 표현은 허용.
    forbidden_phrases = ["optimized taa", "taa optimization"]
    for s in runtime_strings:
        low = s.lower()
        for ph in forbidden_phrases:
            if ph in low:
                # negation context (NOT optimized / not regime-conditioned 등) 인지 확인
                if any(neg in low for neg in ("not optimized", "not regime-conditioned", "not yet")):
                    continue
                pytest.fail(
                    f"runtime string '{s}' contains forbidden positive label '{ph}'"
                )

    # METHOD_LABEL must remain rule_based
    from tdf_engine.reporting.taa_tilt import METHOD_LABEL
    assert METHOD_LABEL == "rule_based"


# ── 10. CLI smoke ───────────────────────────────────────────────────


def test_cli_creates_etf_fund_outputs(tmp_path: Path) -> None:
    from tdf_engine.tools import build_taa_tilt as cli

    out_dir = tmp_path / "taa_tilt"
    summary_md = out_dir / "summary.md"
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
    for p in (
        out_dir / "taa_tilt_etf_20260511.json",
        out_dir / "taa_tilt_fund_20260511.json",
        out_dir / "taa_tilt_etf_20260511.png",
        out_dir / "taa_tilt_fund_20260511.png",
        summary_md,
    ):
        assert p.exists(), f"missing {p}"
