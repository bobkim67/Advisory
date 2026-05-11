"""Phase E-6.2 — MVP-X 1-page integrated bridge smoke test.

검증:
- ETF + Fund 각각 PNG 1장이 생성된다 (>10KB).
- direct SAA telemetry (saa_diagnostics.saa_weights) 가 없으면 ValueError.
- 입력 portfolio dict / json 파일이 mutate 되지 않는다.
- inferred SAA 경로가 코드에 존재하지 않는다 (정적 검사).
- summary md 의 main 섹션은 항상, appendix 섹션은 with_appendix 시에만 포함.
- CLI: 기본 = MVP-X main, --with-appendix = appendix 추가, --mvp-only = legacy.
"""

from __future__ import annotations

import json
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
    reason=(
        "E-6.2 telemetry-enriched portfolio json fixtures not present "
        "(run: python -m tdf_engine.tools.build_portfolio --source db ...)"
    ),
)


@pytest.fixture
def etf_e62() -> dict:
    return json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))


@pytest.fixture
def fund_e62() -> dict:
    return json.loads(FUND_E62_JSON.read_text(encoding="utf-8"))


# ── 1. PNG 생성 ─────────────────────────────────────────────────────────


def test_mvpx_etf_png_created(tmp_path: Path, etf_e62: dict) -> None:
    from tdf_engine.reporting.figures_mvpx import render_mvpx_bridge

    snapshot = deepcopy(etf_e62)
    out = tmp_path / "00_mvpx_bridge_etf.png"
    result = render_mvpx_bridge(etf_e62, out, label="ETF")
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 10000
    # input dict mutate 금지
    assert etf_e62 == snapshot


def test_mvpx_fund_png_created(tmp_path: Path, fund_e62: dict) -> None:
    from tdf_engine.reporting.figures_mvpx import render_mvpx_bridge

    snapshot = deepcopy(fund_e62)
    out = tmp_path / "00_mvpx_bridge_fund.png"
    render_mvpx_bridge(fund_e62, out, label="Fund")
    assert out.exists()
    assert out.stat().st_size > 10000
    assert fund_e62 == snapshot


def test_mvpx_does_not_mutate_input_json_file(tmp_path: Path) -> None:
    """입력 json 파일 자체가 변경되지 않아야 함."""
    from tdf_engine.reporting.figures_mvpx import build_mvpx_for_portfolio_json

    src_text = ETF_E62_JSON.read_text(encoding="utf-8")
    out = tmp_path / "etf.png"
    build_mvpx_for_portfolio_json(ETF_E62_JSON, out, label="ETF")
    assert ETF_E62_JSON.read_text(encoding="utf-8") == src_text
    assert out.exists()


# ── 2. direct SAA telemetry 필수 ────────────────────────────────────────


def test_mvpx_requires_direct_saa_telemetry(tmp_path: Path, etf_e62: dict) -> None:
    """saa_diagnostics.saa_weights 가 없으면 ValueError 명시 raise."""
    from tdf_engine.reporting.figures_mvpx import render_mvpx_bridge

    broken = deepcopy(etf_e62)
    saa_diag = broken.get("diagnostics", {}).get("saa_diagnostics", {})
    saa_diag.pop("saa_weights", None)

    with pytest.raises(ValueError) as excinfo:
        render_mvpx_bridge(broken, tmp_path / "x.png", label="ETF")
    msg = str(excinfo.value)
    assert "saa_weights" in msg
    assert "Inferred" in msg or "inferred" in msg


def test_mvpx_uses_only_direct_saa_no_inferred_path() -> None:
    """figures_mvpx.py 의 정적 검사 (AST 기반):

    inferred SAA 경로 식별자가 *실제 코드*에 등장하면 안 됨.
    docstring/comment 안의 설명 문구는 허용.
    """
    import ast

    src_path = REPO_ROOT / "tdf_engine" / "reporting" / "figures_mvpx.py"
    src = src_path.read_text(encoding="utf-8")
    tree = ast.parse(src)

    identifiers: set[str] = set()
    string_consts: set[str] = set()

    class _Collector(ast.NodeVisitor):
        def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
            identifiers.add(node.id)
            self.generic_visit(node)

        def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: N802
            identifiers.add(node.attr)
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
            identifiers.add(node.name)
            self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
            identifiers.add(node.name)
            self.generic_visit(node)

        def visit_Constant(self, node: ast.Constant) -> None:  # noqa: N802
            # 실제 런타임 string literal — dict key 로 사용될 수 있으므로 검사
            if isinstance(node.value, str):
                string_consts.add(node.value)

    _Collector().visit(tree)

    # docstring 은 string literal 이지만 정적 검사에서 제외
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            ds = ast.get_docstring(node, clean=False)
            if ds:
                docstrings.add(ds)
    runtime_strings = string_consts - docstrings

    forbidden = {"asset_tilts", "regime_tilts"}
    forbidden_substrings = {"_inferred", "infer_saa"}

    # 1) 실제 식별자에 forbidden 이름 사용 금지
    hit_ident = forbidden & identifiers
    assert not hit_ident, (
        f"figures_mvpx.py must not use identifiers {hit_ident} "
        "— MVP-X uses direct SAA telemetry only."
    )

    # 2) 런타임 string literal (dict key 등) 에 forbidden 이름 등장 금지
    hit_str = {s for s in runtime_strings if s in forbidden}
    assert not hit_str, (
        f"figures_mvpx.py runtime strings reference {hit_str} "
        "— MVP-X must not look up inferred SAA fields."
    )

    # 3) 함수/변수 이름에 inferred 패턴 금지
    for ident in identifiers:
        for pat in forbidden_substrings:
            assert pat not in ident, (
                f"identifier '{ident}' contains forbidden pattern '{pat}'"
            )

    # 반드시 direct telemetry 경로 사용
    assert "saa_weights" in identifiers or "saa_weights" in runtime_strings
    assert "_require_direct_saa_telemetry" in identifiers


# ── 3. orchestrator + summary md 구조 ───────────────────────────────────


def test_render_mvpx_main_only(tmp_path: Path) -> None:
    from tdf_engine.reporting import figures

    output_dir = tmp_path / "fig"
    summary_md = tmp_path / "summary.md"
    result = figures.render_mvpx(
        as_of_date="20260511",
        etf_json=ETF_E62_JSON,
        fund_json=FUND_E62_JSON,
        output_dir=output_dir,
        summary_md=summary_md,
        with_appendix=False,
    )
    # 2 PNG (main only)
    assert len(result["png_paths"]) == 2
    assert (output_dir / "main" / "00_mvpx_bridge_etf.png").exists()
    assert (output_dir / "main" / "00_mvpx_bridge_fund.png").exists()
    # appendix PNG 없음
    assert not (output_dir / "etf" / "01_asset_allocation.png").exists()

    md = summary_md.read_text(encoding="utf-8")
    assert "Main: Portfolio Construction Bridge" in md
    assert "main/00_mvpx_bridge_etf.png" in md
    assert "main/00_mvpx_bridge_fund.png" in md
    # appendix 섹션 없음
    assert "Appendix" not in md


def test_render_mvpx_with_appendix(tmp_path: Path) -> None:
    from tdf_engine.reporting import figures

    output_dir = tmp_path / "fig"
    summary_md = tmp_path / "summary.md"
    result = figures.render_mvpx(
        as_of_date="20260511",
        etf_json=ETF_E62_JSON,
        fund_json=FUND_E62_JSON,
        output_dir=output_dir,
        summary_md=summary_md,
        with_appendix=True,
    )
    # 2 (main) + 9 (appendix) = 11 PNG
    assert len(result["png_paths"]) == 11
    assert (output_dir / "main" / "00_mvpx_bridge_etf.png").exists()
    assert (output_dir / "etf" / "01_asset_allocation.png").exists()
    assert (output_dir / "fund" / "04_manager_concentration.png").exists()
    assert (
        output_dir / "comparison" / "01_asset_allocation_etf_vs_fund.png"
    ).exists()

    md = summary_md.read_text(encoding="utf-8")
    assert "Main: Portfolio Construction Bridge" in md
    assert "Appendix" in md
    assert "Appendix-E.1" in md
    assert "etf/01_asset_allocation.png" in md


# ── 4. CLI ──────────────────────────────────────────────────────────────


def test_cli_default_runs_mvpx(tmp_path: Path) -> None:
    from tdf_engine.tools import render_figures as cli

    output_dir = tmp_path / "fig"
    summary_md = tmp_path / "summary.md"
    rc = cli.main(
        [
            "--as-of-date", "20260511",
            "--input-etf", str(ETF_E62_JSON),
            "--input-fund", str(FUND_E62_JSON),
            "--output-dir", str(output_dir),
            "--summary-md", str(summary_md),
        ]
    )
    assert rc == 0
    assert (output_dir / "main" / "00_mvpx_bridge_etf.png").exists()
    md = summary_md.read_text(encoding="utf-8")
    assert "Main: Portfolio Construction Bridge" in md
    assert "Appendix" not in md


def test_cli_with_appendix_flag(tmp_path: Path) -> None:
    from tdf_engine.tools import render_figures as cli

    output_dir = tmp_path / "fig"
    summary_md = tmp_path / "summary.md"
    rc = cli.main(
        [
            "--as-of-date", "20260511",
            "--input-etf", str(ETF_E62_JSON),
            "--input-fund", str(FUND_E62_JSON),
            "--output-dir", str(output_dir),
            "--summary-md", str(summary_md),
            "--with-appendix",
        ]
    )
    assert rc == 0
    assert (output_dir / "main" / "00_mvpx_bridge_etf.png").exists()
    assert (output_dir / "etf" / "01_asset_allocation.png").exists()
    md = summary_md.read_text(encoding="utf-8")
    assert "Appendix-E.1" in md
