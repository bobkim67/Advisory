"""Phase E-6 — Static chart generator smoke test.

검증:
- portfolio_*.json 을 로드하여 figures.py 함수가 PNG 를 생성한다.
- summary markdown 이 생성된다.
- 모든 PNG title 또는 markdown 본문에 RELAXED_TAG 문구가 포함된다.
- 기존 review_*.md / comparison_*.md 는 변경되지 않는다.
- 입력 portfolio dict 도 변경되지 않는다 (deep equality).
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tdf_engine.reporting import figures

REPO_ROOT = Path(__file__).resolve().parents[1]
ETF_JSON = REPO_ROOT / "out" / "db_etf_relaxed" / "portfolio_etf_20260508.json"
FUND_JSON = REPO_ROOT / "out" / "db_fund_relaxed" / "portfolio_fund_20260508.json"
ETF_REVIEW_MD = REPO_ROOT / "out" / "db_etf_relaxed" / "review_etf_20260508.md"
FUND_REVIEW_MD = REPO_ROOT / "out" / "db_fund_relaxed" / "review_fund_20260508.md"
COMPARISON_MD = (
    REPO_ROOT
    / "out"
    / "db_review_relaxed"
    / "comparison_etf_vs_fund_20260508.md"
)


pytestmark = pytest.mark.skipif(
    not (ETF_JSON.exists() and FUND_JSON.exists()),
    reason="relaxed portfolio json fixtures not present",
)


def _file_signature(path: Path) -> tuple[float, int, str] | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    return (path.stat().st_mtime, len(text), text)


@pytest.fixture
def etf_dict() -> dict:
    return json.loads(ETF_JSON.read_text(encoding="utf-8"))


@pytest.fixture
def fund_dict() -> dict:
    return json.loads(FUND_JSON.read_text(encoding="utf-8"))


def test_relaxed_tag_constant() -> None:
    assert "Relaxed Diagnostic" in figures.RELAXED_TAG
    assert "Not Production" in figures.RELAXED_TAG


def test_plot_asset_allocation_creates_png(tmp_path: Path, etf_dict: dict) -> None:
    snapshot = deepcopy(etf_dict)
    out = tmp_path / "01_asset_allocation.png"
    result = figures.plot_asset_allocation(etf_dict, out, label="ETF")
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 1000
    # 입력 dict 는 변경되지 않아야 함
    assert etf_dict == snapshot


def test_plot_comparison_creates_png(
    tmp_path: Path, etf_dict: dict, fund_dict: dict
) -> None:
    out = tmp_path / "01_asset_allocation_etf_vs_fund.png"
    result = figures.plot_asset_allocation_comparison(etf_dict, fund_dict, out)
    assert result.exists()
    assert result.stat().st_size > 1000


def test_plot_drift_summary_creates_png(tmp_path: Path, etf_dict: dict) -> None:
    out = tmp_path / "02_drift_summary.png"
    figures.plot_drift_summary(etf_dict, out, label="ETF")
    assert out.exists()


def test_plot_top_products_creates_png(tmp_path: Path, etf_dict: dict) -> None:
    out = tmp_path / "03_top_products.png"
    figures.plot_top_products(etf_dict, out, label="ETF")
    assert out.exists()


def test_plot_manager_concentration_creates_png(tmp_path: Path, etf_dict: dict) -> None:
    out = tmp_path / "04_manager_concentration.png"
    figures.plot_manager_concentration(etf_dict, out, label="ETF")
    assert out.exists()


def test_render_mvp_full_flow_and_does_not_modify_existing_md(tmp_path: Path) -> None:
    review_etf_sig = _file_signature(ETF_REVIEW_MD)
    review_fund_sig = _file_signature(FUND_REVIEW_MD)
    comparison_sig = _file_signature(COMPARISON_MD)

    etf_src_text = ETF_JSON.read_text(encoding="utf-8")
    fund_src_text = FUND_JSON.read_text(encoding="utf-8")

    output_dir = tmp_path / "figures" / "20260508"
    summary_md = tmp_path / "figures_summary_20260508.md"

    result = figures.render_mvp(
        as_of_date="20260508",
        etf_json=ETF_JSON,
        fund_json=FUND_JSON,
        output_dir=output_dir,
        summary_md=summary_md,
    )

    expected_pngs = {
        output_dir / "etf" / "01_asset_allocation.png",
        output_dir / "fund" / "01_asset_allocation.png",
        output_dir
        / "comparison"
        / "01_asset_allocation_etf_vs_fund.png",
        output_dir / "etf" / "02_drift_summary.png",
        output_dir / "fund" / "02_drift_summary.png",
        output_dir / "etf" / "03_top_products.png",
        output_dir / "fund" / "03_top_products.png",
        output_dir / "etf" / "04_manager_concentration.png",
        output_dir / "fund" / "04_manager_concentration.png",
    }
    actual_pngs = {Path(p) for p in result["png_paths"]}
    assert actual_pngs == expected_pngs
    for p in expected_pngs:
        assert p.exists(), f"missing PNG: {p}"
        assert p.stat().st_size > 1000

    # summary markdown
    assert summary_md.exists()
    md_text = summary_md.read_text(encoding="utf-8")
    assert "Relaxed Diagnostic" in md_text
    assert "production portfolio" in md_text.lower()
    assert "재계산하지 않고" in md_text
    # 9 png 모두 링크
    for token in (
        "etf/01_asset_allocation.png",
        "fund/01_asset_allocation.png",
        "comparison/01_asset_allocation_etf_vs_fund.png",
        "etf/02_drift_summary.png",
        "fund/02_drift_summary.png",
        "etf/03_top_products.png",
        "fund/03_top_products.png",
        "etf/04_manager_concentration.png",
        "fund/04_manager_concentration.png",
    ):
        assert token in md_text, f"summary md missing link: {token}"

    # 기존 review/comparison md 는 변경되지 않아야 함
    assert _file_signature(ETF_REVIEW_MD) == review_etf_sig
    assert _file_signature(FUND_REVIEW_MD) == review_fund_sig
    assert _file_signature(COMPARISON_MD) == comparison_sig

    # 입력 portfolio json 파일 자체도 변경되지 않아야 함
    assert ETF_JSON.read_text(encoding="utf-8") == etf_src_text
    assert FUND_JSON.read_text(encoding="utf-8") == fund_src_text


def test_cli_smoke(tmp_path: Path) -> None:
    """CLI 를 main() 으로 직접 호출하여 동작 확인."""
    from tdf_engine.tools import render_figures as cli

    output_dir = tmp_path / "fig"
    summary_md = tmp_path / "summary.md"
    rc = cli.main(
        [
            "--as-of-date",
            "20260508",
            "--input-etf",
            str(ETF_JSON),
            "--input-fund",
            str(FUND_JSON),
            "--output-dir",
            str(output_dir),
            "--summary-md",
            str(summary_md),
            "--mvp-only",
        ]
    )
    assert rc == 0
    assert summary_md.exists()
    assert (output_dir / "etf" / "01_asset_allocation.png").exists()


def test_cli_missing_input_raises(tmp_path: Path) -> None:
    from tdf_engine.tools import render_figures as cli

    with pytest.raises(SystemExit):
        cli.main(
            [
                "--as-of-date",
                "20260508",
                "--input-etf",
                str(tmp_path / "nope.json"),
                "--input-fund",
                str(FUND_JSON),
                "--output-dir",
                str(tmp_path / "fig"),
                "--summary-md",
                str(tmp_path / "summary.md"),
                "--mvp-only",
            ]
        )
