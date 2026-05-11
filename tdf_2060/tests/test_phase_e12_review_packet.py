"""Phase E-12 — Integrated Review Packet smoke test."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
REVIEW_ROOT = REPO_ROOT / "out" / "db_review_relaxed_e62"
ETF_PORTFOLIO = REPO_ROOT / "out" / "db_etf_relaxed_e62_e11a" / "portfolio_etf_20260511.json"
FUND_PORTFOLIO = REPO_ROOT / "out" / "db_fund_relaxed_e62_e11a" / "portfolio_fund_20260511.json"

ETF_REGIME_PNG = REVIEW_ROOT / "regime_history" / "20260511" / "regime_clock_etf_20260511.png"
FUND_REGIME_PNG = REVIEW_ROOT / "regime_history" / "20260511" / "regime_clock_fund_20260511.png"
ETF_SAA_PNG = REVIEW_ROOT / "saa_frontier" / "20260511" / "saa_mvo_etf_20260511.png"
ETF_TAA_PNG = REVIEW_ROOT / "taa_tilt" / "20260511" / "taa_tilt_etf_20260511.png"
ETF_PS_PNG = REVIEW_ROOT / "product_selection_visualization" / "20260511" / "product_selection_etf_20260511.png"


pytestmark = pytest.mark.skipif(
    not all(
        p.exists()
        for p in (
            ETF_PORTFOLIO, FUND_PORTFOLIO,
            ETF_REGIME_PNG, ETF_SAA_PNG, ETF_TAA_PNG, ETF_PS_PNG,
        )
    ),
    reason="E-7~E-11B + e62_e11a portfolio outputs not all present",
)


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ── 1-3. md / html / both packet 생성 ───────────────────────────────


def test_etf_markdown_packet_built(tmp_path: Path) -> None:
    from tdf_engine.reporting.review_packet import build_review_packet

    out = tmp_path / "packet"
    result = build_review_packet(
        review_root=REVIEW_ROOT,
        as_of_run="20260511",
        product_type="etf",
        portfolio_json=ETF_PORTFOLIO,
        output_dir=out,
        fmt="md",
    )
    assert result["md_path"] is not None
    assert result["md_path"].exists()
    text = result["md_path"].read_text(encoding="utf-8")
    assert "TDF 2060 ETF Portfolio" in text
    # 4 core image link 모두
    for token in (
        "regime_clock_etf_20260511.png",
        "saa_mvo_etf_20260511.png",
        "taa_tilt_etf_20260511.png",
        "product_selection_etf_20260511.png",
    ):
        assert f"assets/{token}" in text, f"missing image link: {token}"


def test_fund_markdown_packet_built(tmp_path: Path) -> None:
    from tdf_engine.reporting.review_packet import build_review_packet

    out = tmp_path / "packet"
    result = build_review_packet(
        review_root=REVIEW_ROOT,
        as_of_run="20260511",
        product_type="fund",
        portfolio_json=FUND_PORTFOLIO,
        output_dir=out,
        fmt="md",
    )
    text = result["md_path"].read_text(encoding="utf-8")
    assert "TDF 2060 FUND Portfolio" in text
    for token in (
        "regime_clock_fund_20260511.png",
        "saa_mvo_fund_20260511.png",
        "taa_tilt_fund_20260511.png",
        "product_selection_fund_20260511.png",
    ):
        assert f"assets/{token}" in text


def test_both_packet_built(tmp_path: Path) -> None:
    from tdf_engine.reporting.review_packet import build_review_packet_both

    out = tmp_path / "packet"
    result = build_review_packet_both(
        review_root=REVIEW_ROOT,
        as_of_run="20260511",
        portfolio_json_etf=ETF_PORTFOLIO,
        portfolio_json_fund=FUND_PORTFOLIO,
        output_dir=out,
        fmt="md",
    )
    text = result["md_path"].read_text(encoding="utf-8")
    assert "ETF + Fund" in text
    assert "ETF vs Fund Snapshot" in text
    # 8 image (4 × 2 product)
    for pt in ("etf", "fund"):
        for token in (
            f"regime_clock_{pt}_20260511.png",
            f"saa_mvo_{pt}_20260511.png",
            f"taa_tilt_{pt}_20260511.png",
            f"product_selection_{pt}_20260511.png",
        ):
            assert f"assets/{token}" in text


# ── 4. HTML packet ──────────────────────────────────────────────────


def test_html_packet_built(tmp_path: Path) -> None:
    from tdf_engine.reporting.review_packet import build_review_packet

    out = tmp_path / "packet"
    result = build_review_packet(
        review_root=REVIEW_ROOT,
        as_of_run="20260511",
        product_type="etf",
        portfolio_json=ETF_PORTFOLIO,
        output_dir=out,
        fmt="both",
    )
    assert result["html_path"] is not None
    assert result["html_path"].exists()
    html = result["html_path"].read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "<style>" in html
    assert "<table>" in html
    assert "<img " in html
    # 외부 JS 의존 없음
    assert "<script" not in html


# ── 5. 4 core 이미지 포함 (assets/ 복사) ────────────────────────────


def test_packet_includes_four_core_images(tmp_path: Path) -> None:
    from tdf_engine.reporting.review_packet import build_review_packet

    out = tmp_path / "packet"
    build_review_packet(
        review_root=REVIEW_ROOT,
        as_of_run="20260511",
        product_type="etf",
        portfolio_json=ETF_PORTFOLIO,
        output_dir=out,
        fmt="md",
    )
    expected = {
        "regime_clock_etf_20260511.png",
        "saa_mvo_etf_20260511.png",
        "taa_tilt_etf_20260511.png",
        "product_selection_etf_20260511.png",
    }
    actual = {p.name for p in (out / "assets").iterdir() if p.suffix == ".png"}
    assert expected.issubset(actual)


# ── 6. limitation text 명시 ─────────────────────────────────────────


def test_packet_includes_explicit_limitation_text(tmp_path: Path) -> None:
    from tdf_engine.reporting.review_packet import build_review_packet

    out = tmp_path / "packet"
    result = build_review_packet(
        review_root=REVIEW_ROOT,
        as_of_run="20260511",
        product_type="etf",
        portfolio_json=ETF_PORTFOLIO,
        output_dir=out,
        fmt="md",
    )
    text = result["md_path"].read_text(encoding="utf-8")
    low = text.lower()
    assert "relaxed diagnostic" in low
    assert "rule-based" in low
    assert ("not optimized taa" in low) or ("not regime-conditioned" in low)
    assert "ticker mapping unavailable" in low


# ── 7. missing_data 통합 ────────────────────────────────────────────


def test_packet_aggregates_missing_data(tmp_path: Path) -> None:
    from tdf_engine.reporting.review_packet import build_review_packet

    out = tmp_path / "packet"
    result = build_review_packet(
        review_root=REVIEW_ROOT,
        as_of_run="20260511",
        product_type="etf",
        portfolio_json=ETF_PORTFOLIO,
        output_dir=out,
        fmt="md",
    )
    md = result["packet"].get("missing_data") or []
    source_phases = {m.get("source_phase") for m in md}
    # 5 phase 전부 또는 일부 명시 (데이터 가용성에 따라). 최소 2 phase 이상 등장 기대.
    assert len(source_phases) >= 2
    # missing_data 섹션 텍스트 존재
    text = result["md_path"].read_text(encoding="utf-8")
    assert "Diagnostics / Missing Data" in text


# ── 8. assets/ 복사 sha256 일치 (원본 미변경) ──────────────────────


def test_assets_copy_sha256_matches_source(tmp_path: Path) -> None:
    from tdf_engine.reporting.review_packet import build_review_packet

    src_h_before = {
        "regime": _sha256(ETF_REGIME_PNG),
        "saa": _sha256(ETF_SAA_PNG),
        "taa": _sha256(ETF_TAA_PNG),
        "ps": _sha256(ETF_PS_PNG),
    }
    out = tmp_path / "packet"
    build_review_packet(
        review_root=REVIEW_ROOT,
        as_of_run="20260511",
        product_type="etf",
        portfolio_json=ETF_PORTFOLIO,
        output_dir=out,
        fmt="md",
    )
    # 원본 sha256 unchanged
    assert _sha256(ETF_REGIME_PNG) == src_h_before["regime"]
    assert _sha256(ETF_SAA_PNG) == src_h_before["saa"]
    assert _sha256(ETF_TAA_PNG) == src_h_before["taa"]
    assert _sha256(ETF_PS_PNG) == src_h_before["ps"]
    # 사본 sha256 == 원본 sha256
    assert _sha256(out / "assets" / ETF_REGIME_PNG.name) == src_h_before["regime"]
    assert _sha256(out / "assets" / ETF_SAA_PNG.name) == src_h_before["saa"]
    assert _sha256(out / "assets" / ETF_TAA_PNG.name) == src_h_before["taa"]
    assert _sha256(out / "assets" / ETF_PS_PNG.name) == src_h_before["ps"]


# ── 9. CLI smoke ────────────────────────────────────────────────────


def test_cli_etf_md(tmp_path: Path) -> None:
    from tdf_engine.tools import build_review_packet as cli

    out = tmp_path / "packet"
    rc = cli.main([
        "--as-of-run", "20260511",
        "--product-type", "etf",
        "--review-root", str(REVIEW_ROOT),
        "--portfolio-json", str(ETF_PORTFOLIO),
        "--output-dir", str(out),
        "--format", "md",
    ])
    assert rc == 0
    assert (out / "review_packet_etf_20260511.md").exists()


def test_cli_both_html(tmp_path: Path) -> None:
    from tdf_engine.tools import build_review_packet as cli

    out = tmp_path / "packet"
    rc = cli.main([
        "--as-of-run", "20260511",
        "--product-type", "both",
        "--review-root", str(REVIEW_ROOT),
        "--portfolio-json", str(ETF_PORTFOLIO),
        "--portfolio-json-fund", str(FUND_PORTFOLIO),
        "--output-dir", str(out),
        "--format", "both",
        "--include-appendix",
    ])
    assert rc == 0
    assert (out / "review_packet_both_20260511.md").exists()
    assert (out / "review_packet_both_20260511.html").exists()
    md = (out / "review_packet_both_20260511.md").read_text(encoding="utf-8")
    assert "Appendix (opt-in)" in md
