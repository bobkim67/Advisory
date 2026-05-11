"""Phase E-8 — Regime Clock visualization smoke test.

검증:
- regime history sidecar JSON 생성.
- observations 가 as_of 오름차순 정렬.
- sidecar 마지막 obs == portfolio.diagnostics.regime current.
- coverage metadata (count/start_date/end_date/months_available/coverage_status) 존재.
- regime clock PNG 생성 (>10KB).
- renderer 가 입력 portfolio JSON / source 파일 mutate 안 함.
- insufficient case 는 ValueError + 명시 메시지.
- mini timeline 사용 안 함 (renderer 에 history_n / mini timeline 패턴 부재 — 정적 검사).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
ETF_E62_JSON = (
    REPO_ROOT / "out" / "db_etf_relaxed_e62" / "portfolio_etf_20260511.json"
)
FUND_E62_JSON = (
    REPO_ROOT / "out" / "db_fund_relaxed_e62" / "portfolio_fund_20260511.json"
)
ADVISORY_ROOT = REPO_ROOT.parent
REGIME_SRC = ADVISORY_ROOT / "regime_src"


pytestmark = pytest.mark.skipif(
    not (ETF_E62_JSON.exists() and FUND_E62_JSON.exists() and REGIME_SRC.exists()),
    reason="E-6.2 portfolio JSON or regime_src not present",
)


# ── 1. history sidecar build ─────────────────────────────────────────


def test_build_regime_history_creates_payload() -> None:
    from tdf_engine.reporting.regime_clock import build_regime_history, SCHEMA_VERSION

    payload = build_regime_history(ETF_E62_JSON, source_root=ADVISORY_ROOT)
    assert payload["meta"]["schema_version"] == SCHEMA_VERSION
    assert payload["meta"]["product_type"] == "etf"
    assert payload["signal"]["region"]
    obs = payload["observations"]
    assert obs, "observations must not be empty"
    # 오름차순 정렬
    asofs = [o["as_of"] for o in obs]
    assert asofs == sorted(asofs)
    cov = payload["coverage"]
    for k in ("count", "start_date", "end_date", "months_available", "target_months", "coverage_status"):
        assert k in cov
    assert cov["coverage_status"] in ("full", "partial", "insufficient")


def test_history_current_matches_portfolio_regime() -> None:
    from tdf_engine.reporting.regime_clock import build_regime_history

    payload = build_regime_history(ETF_E62_JSON, source_root=ADVISORY_ROOT)
    obs = payload["observations_full"]
    assert obs
    last = obs[-1]
    portfolio = json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))
    pr = portfolio["diagnostics"]["regime"]
    assert abs(last["placement"] - float(pr["placement"])) < 1e-6
    assert abs(last["velocity"] - float(pr["velocity"])) < 1e-6
    assert last["regime"] == int(pr["regime"])
    assert payload["diagnostics"]["current_point_match"] is True


def test_input_files_not_mutated() -> None:
    from tdf_engine.reporting.regime_clock import build_regime_history

    src_text = ETF_E62_JSON.read_text(encoding="utf-8")
    src_regime_text = REGIME_SRC.read_text(encoding="utf-8")
    _ = build_regime_history(ETF_E62_JSON, source_root=ADVISORY_ROOT)
    assert ETF_E62_JSON.read_text(encoding="utf-8") == src_text
    assert REGIME_SRC.read_text(encoding="utf-8") == src_regime_text


# ── 2. clock PNG ─────────────────────────────────────────────────────


def test_render_regime_clock_creates_png(tmp_path: Path) -> None:
    from tdf_engine.reporting.regime_clock import build_regime_history, render_regime_clock

    payload = build_regime_history(ETF_E62_JSON, source_root=ADVISORY_ROOT)
    out = tmp_path / "regime_clock.png"
    result = render_regime_clock(payload, out, label="ETF")
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 10000


def test_renderer_raises_on_insufficient_history() -> None:
    """insufficient 케이스: observations 비우거나 coverage_status=insufficient."""
    from tdf_engine.reporting.regime_clock import render_regime_clock

    insufficient_payload = {
        "meta": {"product_type": "etf", "portfolio_as_of_date": "2026-03-31"},
        "signal": {"region": "G7"},
        "observations": [
            {"as_of": "2026-01-01", "placement": 0.5, "velocity": 0.05, "regime": 1, "regime_label": "Expansion / Acceleration"},
        ],
        "observations_full": [],
        "coverage": {
            "count": 1, "start_date": "2026-01-01", "end_date": "2026-01-01",
            "months_available": 1, "target_months": 24, "coverage_status": "insufficient",
        },
        "diagnostics": {"warnings": [], "missing_data": []},
    }
    with pytest.raises(ValueError) as exc:
        render_regime_clock(insufficient_payload, Path("/tmp/x.png"), label="ETF")
    assert "insufficient" in str(exc.value)


# ── 3. CLI smoke ─────────────────────────────────────────────────────


def test_cli_creates_history_png_summary(tmp_path: Path) -> None:
    from tdf_engine.tools import build_regime_clock as cli

    out_dir = tmp_path / "regime_history"
    summary_md = out_dir / "summary.md"
    rc = cli.main(
        [
            "--as-of-run", "20260511",
            "--input-etf", str(ETF_E62_JSON),
            "--input-fund", str(FUND_E62_JSON),
            "--source-root", str(ADVISORY_ROOT),
            "--output-history-dir", str(out_dir),
            "--output-figures-dir", str(out_dir),
            "--summary-md", str(summary_md),
        ]
    )
    assert rc == 0
    etf_json = out_dir / "regime_history_etf_20260511.json"
    fund_json = out_dir / "regime_history_fund_20260511.json"
    etf_png = out_dir / "regime_clock_etf_20260511.png"
    fund_png = out_dir / "regime_clock_fund_20260511.png"
    for p in (etf_json, fund_json, etf_png, fund_png, summary_md):
        assert p.exists(), f"missing: {p}"
    assert etf_png.stat().st_size > 10000
    assert fund_png.stat().st_size > 10000
    md = summary_md.read_text(encoding="utf-8")
    assert "ETF" in md and "Fund" in md
    assert "coverage" in md.lower()


# ── 4. design constraint — no mini timeline pattern ──────────────────


def test_module_does_not_contain_mini_timeline_helper() -> None:
    """사용자 §E-8B-5 명시: mini timeline 금지 — 본 module 은 P/V 2D 만.

    AST 기반: 'mini_timeline' / 'plot_timeline' / 'add_timeline' 식별자 부재.
    """
    import ast

    src_path = REPO_ROOT / "tdf_engine" / "reporting" / "regime_clock.py"
    src = src_path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    identifiers: set[str] = set()

    class _C(ast.NodeVisitor):
        def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
            identifiers.add(node.id)
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
            identifiers.add(node.name)
            self.generic_visit(node)

        def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: N802
            identifiers.add(node.attr)
            self.generic_visit(node)

    _C().visit(tree)
    forbidden = ("mini_timeline", "plot_timeline", "add_timeline", "section_timeline")
    for ident in identifiers:
        for pat in forbidden:
            assert pat not in ident, f"identifier '{ident}' contains forbidden '{pat}'"
