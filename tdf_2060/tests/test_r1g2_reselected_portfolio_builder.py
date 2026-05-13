"""R-1G.2 — PortfolioBuilder wiring + 3-way comparison tests.

Scope:
- ETF / Fund happy path with PortfolioBuilder applied
- product_weight_sum ≈ 1.0 (builder fallback 가 R-1G.1 shortfall 흡수)
- validity flags strict (implementation_ready=false, etc.)
- dm_ex_us_equity / us_high_yield 신규 편입 product 유지
- 3-way comparison md (baseline / R-1F.2 / R-1G.2)
- 별도 output dir
- baseline / R-1F.2 / R-1G.1 / manager_selected_saa / config / E-series baseline
  / Decision Register / _phase_e62_baseline.json 모두 mutation 없음
- 80:20 distance metric 부활 없음
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT.parent
CONFIG_DIR = REPO_ROOT / "tdf_engine" / "config"

OPP_DIR = REPO_ROOT / "out" / "db_review_relaxed_e62" / "saa_opportunity_set" / "20260513"
ETF_MANAGER_JSON = OPP_DIR / "manager_selected_saa_etf_20260513.json"
FUND_MANAGER_JSON = OPP_DIR / "manager_selected_saa_fund_20260513.json"

ETF_R1F2_JSON = REPO_ROOT / "out" / "db_etf_relaxed_e62_r1e_dryrun" / "portfolio_etf_20260513.json"
FUND_R1F2_JSON = REPO_ROOT / "out" / "db_fund_relaxed_e62_r1e_dryrun" / "portfolio_fund_20260513.json"

ETF_BASELINE_JSON = REPO_ROOT / "out" / "db_etf_relaxed_e62" / "portfolio_etf_20260511.json"
FUND_BASELINE_JSON = REPO_ROOT / "out" / "db_fund_relaxed_e62" / "portfolio_fund_20260511.json"

ETF_R1G1_JSON = (
    REPO_ROOT / "out" / "db_etf_relaxed_e62_r1g_reselection"
    / "product_reselection_etf_20260513.json"
)
FUND_R1G1_JSON = (
    REPO_ROOT / "out" / "db_fund_relaxed_e62_r1g_reselection"
    / "product_reselection_fund_20260513.json"
)

BASELINE_SNAPSHOT = REPO_ROOT / "tests" / "_phase_e62_baseline.json"

ETF_LIST = SOURCE_ROOT / "etf_list"
FUND_LIST = SOURCE_ROOT / "fund_list"


pytestmark = pytest.mark.skipif(
    not (
        ETF_MANAGER_JSON.exists() and FUND_MANAGER_JSON.exists()
        and ETF_R1F2_JSON.exists() and FUND_R1F2_JSON.exists()
        and ETF_BASELINE_JSON.exists() and FUND_BASELINE_JSON.exists()
        and ETF_LIST.exists() and FUND_LIST.exists()
    ),
    reason="R-1F.* / baseline / etf_list / fund_list not present",
)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def etf_manager() -> dict:
    return json.loads(ETF_MANAGER_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fund_manager() -> dict:
    return json.loads(FUND_MANAGER_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def etf_r1f2() -> dict:
    return json.loads(ETF_R1F2_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fund_r1f2() -> dict:
    return json.loads(FUND_R1F2_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def etf_baseline() -> dict:
    return json.loads(ETF_BASELINE_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fund_baseline() -> dict:
    return json.loads(FUND_BASELINE_JSON.read_text(encoding="utf-8"))


def _build_etf(etf_manager, etf_r1f2, etf_baseline) -> dict:
    from tdf_engine.optimization.r1g2_reselected_portfolio import build_r1g2_portfolio
    return build_r1g2_portfolio(
        etf_manager, etf_r1f2, etf_baseline,
        source_root=SOURCE_ROOT, config_dir=CONFIG_DIR,
        manager_dump_path=ETF_MANAGER_JSON,
        r1f2_dump_path=ETF_R1F2_JSON,
        baseline_portfolio_path=ETF_BASELINE_JSON,
        r1g1_reselection_path=ETF_R1G1_JSON if ETF_R1G1_JSON.exists() else None,
        selection_as_of="20260513",
        output_as_of="20260513",
        baseline_portfolio_as_of="20260511",
        universe_as_of="20260511",
    )


def _build_fund(fund_manager, fund_r1f2, fund_baseline) -> dict:
    from tdf_engine.optimization.r1g2_reselected_portfolio import build_r1g2_portfolio
    return build_r1g2_portfolio(
        fund_manager, fund_r1f2, fund_baseline,
        source_root=SOURCE_ROOT, config_dir=CONFIG_DIR,
        manager_dump_path=FUND_MANAGER_JSON,
        r1f2_dump_path=FUND_R1F2_JSON,
        baseline_portfolio_path=FUND_BASELINE_JSON,
        r1g1_reselection_path=FUND_R1G1_JSON if FUND_R1G1_JSON.exists() else None,
        selection_as_of="20260513",
        output_as_of="20260513",
        baseline_portfolio_as_of="20260511",
        universe_as_of="20260511",
    )


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------


def test_etf_happy_path(etf_manager, etf_r1f2, etf_baseline) -> None:
    payload = _build_etf(etf_manager, etf_r1f2, etf_baseline)
    assert payload["meta"]["portfolio_type"] == "etf"
    assert payload["meta"]["product_allocation_method"] == "full_reselection"
    assert payload["meta"]["portfolio_builder_applied"] is True
    assert payload["product_count"] >= 1


def test_fund_happy_path(fund_manager, fund_r1f2, fund_baseline) -> None:
    payload = _build_fund(fund_manager, fund_r1f2, fund_baseline)
    assert payload["meta"]["portfolio_type"] == "fund"
    assert payload["meta"]["portfolio_builder_applied"] is True


def test_write_json_and_compare_md(
    etf_manager, etf_r1f2, etf_baseline, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.r1g2_reselected_portfolio import (
        render_three_way_compare_md,
        write_r1g2_portfolio_json,
    )
    payload = _build_etf(etf_manager, etf_r1f2, etf_baseline)
    j = write_r1g2_portfolio_json(payload, tmp_path / "portfolio_etf_20260513.json")
    md = render_three_way_compare_md(
        payload, etf_baseline, etf_r1f2,
        tmp_path / "r1g_three_way_compare_etf_20260513.md",
    )
    assert j.exists()
    assert md.exists()
    text = md.read_text(encoding="utf-8")
    # 3-way 비교 핵심 포함
    assert "R-1G.2 Three-way Portfolio Comparison" in text
    assert "baseline (max-Sharpe)" in text
    assert "R-1F.2 (proportional)" in text
    assert "R-1G.2 (full reselection + builder)" in text
    assert "dm_ex_us_equity" in text
    assert "us_high_yield" in text
    # 80:20 distance metric 부재 (regression)
    assert "bucket_distance_from_80_20" not in text
    assert "full_weight_distance_from_80_20" not in text


# ---------------------------------------------------------------------------
# 2. Validity flag invariants (strict)
# ---------------------------------------------------------------------------


def test_safety_flags_strict(etf_manager, etf_r1f2, etf_baseline) -> None:
    payload = _build_etf(etf_manager, etf_r1f2, etf_baseline)
    m = payload["meta"]
    assert m["production_applied"] is False
    assert m["dry_run_only"] is True
    assert m["manager_override_saa_layer"] is True
    assert m["product_allocation_method"] == "full_reselection"
    assert m["portfolio_builder_applied"] is True
    assert m["target_weight_source"] == "r1f2_projection_final_asset_weights"
    assert m["valid_asset_level_dry_run"] is True
    # implementation_ready 는 무조건 false / review_required (사용자 strict 지시)
    assert m["implementation_ready"] is False
    assert m["implementation_review_status"] == "review_required"
    assert m["sign_off_required_for_production"] is True
    assert m["comparison_to_baseline_available"] is True
    assert m["comparison_to_r1f2_available"] is True


def test_as_of_separation_fields(etf_manager, etf_r1f2, etf_baseline) -> None:
    payload = _build_etf(etf_manager, etf_r1f2, etf_baseline)
    m = payload["meta"]
    assert m["selection_as_of"] == "20260513"
    assert m["output_as_of"] == "20260513"
    assert m["baseline_portfolio_as_of"] == "20260511"
    assert m["universe_as_of"] == "20260511"


# ---------------------------------------------------------------------------
# 3. Product weight sum (builder fallback absorbs R-1G.1 shortfall)
# ---------------------------------------------------------------------------


def test_etf_product_weight_sum_close_to_one(
    etf_manager, etf_r1f2, etf_baseline,
) -> None:
    payload = _build_etf(etf_manager, etf_r1f2, etf_baseline)
    s = float(payload["product_weight_sum"])
    # R-1G.1 ETF shortfall (≈ 0.0024) 는 builder fallback 으로 흡수 → sum ≈ 1.0
    assert abs(s - 1.0) <= 1e-3


def test_fund_product_weight_sum_close_to_one(
    fund_manager, fund_r1f2, fund_baseline,
) -> None:
    payload = _build_fund(fund_manager, fund_r1f2, fund_baseline)
    s = float(payload["product_weight_sum"])
    assert abs(s - 1.0) <= 1e-3


def test_etf_valid_product_level_portfolio_after_builder(
    etf_manager, etf_r1f2, etf_baseline,
) -> None:
    payload = _build_etf(etf_manager, etf_r1f2, etf_baseline)
    # builder fallback 이 정상 작동하면 valid_product_level_portfolio = True 도달
    assert payload["meta"]["valid_product_level_portfolio"] is True
    assert payload["meta"]["product_weight_sum_valid"] is True
    # 단, implementation_ready 는 여전히 false (사용자 strict)
    assert payload["meta"]["implementation_ready"] is False


# ---------------------------------------------------------------------------
# 4. dm_ex_us_equity / us_high_yield 신규 편입 유지
# ---------------------------------------------------------------------------


def test_dm_ex_us_equity_product_allocated(
    etf_manager, etf_r1f2, etf_baseline,
) -> None:
    payload = _build_etf(etf_manager, etf_r1f2, etf_baseline)
    cnt = payload["selected_count_by_asset"].get("dm_ex_us_equity", 0)
    assert cnt >= 1, "R-1G.2 must allocate ≥1 product for dm_ex_us_equity"


def test_us_high_yield_product_allocated(
    etf_manager, etf_r1f2, etf_baseline,
) -> None:
    payload = _build_etf(etf_manager, etf_r1f2, etf_baseline)
    cnt = payload["selected_count_by_asset"].get("us_high_yield", 0)
    assert cnt >= 1, "R-1G.2 must allocate ≥1 product for us_high_yield"


def test_fund_dm_ex_us_and_us_high_yield_allocated(
    fund_manager, fund_r1f2, fund_baseline,
) -> None:
    payload = _build_fund(fund_manager, fund_r1f2, fund_baseline)
    assert payload["selected_count_by_asset"].get("dm_ex_us_equity", 0) >= 1
    assert payload["selected_count_by_asset"].get("us_high_yield", 0) >= 1


# ---------------------------------------------------------------------------
# 5. Output directory separation
# ---------------------------------------------------------------------------


def test_output_dir_separate_from_baseline_and_r1f2(
    etf_manager, etf_r1f2, etf_baseline, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.r1g2_reselected_portfolio import (
        write_r1g2_portfolio_json,
    )
    payload = _build_etf(etf_manager, etf_r1f2, etf_baseline)
    dry_dir = tmp_path / "db_etf_relaxed_e62_r1g_reselection"
    out = write_r1g2_portfolio_json(payload, dry_dir / "portfolio_etf_20260513.json")
    assert out.parent != ETF_BASELINE_JSON.parent
    assert out.parent != ETF_R1F2_JSON.parent
    assert "r1g_reselection" in str(out.parent)


# ---------------------------------------------------------------------------
# 6. Mutation guards
# ---------------------------------------------------------------------------


def test_baseline_portfolio_json_sha_unchanged(
    etf_manager, etf_r1f2, etf_baseline, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.r1g2_reselected_portfolio import (
        render_three_way_compare_md, write_r1g2_portfolio_json,
    )
    pre = _sha(ETF_BASELINE_JSON)
    payload = _build_etf(etf_manager, etf_r1f2, etf_baseline)
    write_r1g2_portfolio_json(payload, tmp_path / "p.json")
    render_three_way_compare_md(payload, etf_baseline, etf_r1f2, tmp_path / "p.md")
    assert _sha(ETF_BASELINE_JSON) == pre


def test_r1f2_dry_run_json_sha_unchanged(
    etf_manager, etf_r1f2, etf_baseline, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.r1g2_reselected_portfolio import (
        write_r1g2_portfolio_json,
    )
    pre = _sha(ETF_R1F2_JSON)
    payload = _build_etf(etf_manager, etf_r1f2, etf_baseline)
    write_r1g2_portfolio_json(payload, tmp_path / "p.json")
    assert _sha(ETF_R1F2_JSON) == pre


def test_r1g1_reselection_json_sha_unchanged_if_exists(
    etf_manager, etf_r1f2, etf_baseline, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.r1g2_reselected_portfolio import (
        write_r1g2_portfolio_json,
    )
    if not ETF_R1G1_JSON.exists():
        pytest.skip("R-1G.1 JSON not present")
    pre = _sha(ETF_R1G1_JSON)
    payload = _build_etf(etf_manager, etf_r1f2, etf_baseline)
    write_r1g2_portfolio_json(payload, tmp_path / "p.json")
    assert _sha(ETF_R1G1_JSON) == pre


def test_manager_selected_saa_json_sha_unchanged(
    etf_manager, etf_r1f2, etf_baseline, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.r1g2_reselected_portfolio import (
        write_r1g2_portfolio_json,
    )
    pre = _sha(ETF_MANAGER_JSON)
    payload = _build_etf(etf_manager, etf_r1f2, etf_baseline)
    write_r1g2_portfolio_json(payload, tmp_path / "p.json")
    assert _sha(ETF_MANAGER_JSON) == pre


def test_input_dicts_not_mutated(etf_manager, etf_r1f2, etf_baseline) -> None:
    snap_manager = copy.deepcopy(etf_manager)
    snap_r1f2 = copy.deepcopy(etf_r1f2)
    snap_baseline = copy.deepcopy(etf_baseline)
    _ = _build_etf(etf_manager, etf_r1f2, etf_baseline)
    assert etf_manager == snap_manager
    assert etf_r1f2 == snap_r1f2
    assert etf_baseline == snap_baseline


def test_bit_identical_baseline_snapshot_unchanged(
    etf_manager, etf_r1f2, etf_baseline, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.r1g2_reselected_portfolio import (
        write_r1g2_portfolio_json,
    )
    if not BASELINE_SNAPSHOT.exists():
        pytest.skip("baseline snapshot not present")
    pre = _sha(BASELINE_SNAPSHOT)
    payload = _build_etf(etf_manager, etf_r1f2, etf_baseline)
    write_r1g2_portfolio_json(payload, tmp_path / "p.json")
    assert _sha(BASELINE_SNAPSHOT) == pre


def test_config_yaml_unchanged_after_run(
    etf_manager, etf_r1f2, etf_baseline, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.r1g2_reselected_portfolio import (
        write_r1g2_portfolio_json,
    )
    for y in ("universe_filter.yaml", "taa_policy.yaml", "asset_mapping.yaml",
              "tdf_2060.yaml"):
        path = CONFIG_DIR / y
        if not path.exists():
            continue
        pre = _sha(path)
        payload = _build_etf(etf_manager, etf_r1f2, etf_baseline)
        write_r1g2_portfolio_json(payload, tmp_path / "p.json")
        assert _sha(path) == pre, f"{y} sha changed after R-1G.2 run"


# ---------------------------------------------------------------------------
# 7. Comparison report 3-way essentials
# ---------------------------------------------------------------------------


def test_comparison_summary_block_has_3_entries(
    etf_manager, etf_r1f2, etf_baseline,
) -> None:
    payload = _build_etf(etf_manager, etf_r1f2, etf_baseline)
    cs = payload["comparison_summary"]
    assert "baseline_max_sharpe" in cs
    assert "r1f2_proportional" in cs
    assert "r1g2_full_reselection" in cs
    # R-1F.2 의 invalid sum 이 그대로 노출 (1.4448 / 0.7209 부근)
    assert float(cs["r1f2_proportional"]["product_weight_sum_dry_run"]) > 1.1 or \
           float(cs["r1f2_proportional"]["product_weight_sum_dry_run"]) < 0.9
    # baseline / R-1G.2 둘 다 product_weight_sum ≈ 1
    assert abs(float(cs["baseline_max_sharpe"]["product_weight_sum"]) - 1.0) <= 1e-3
    assert abs(float(cs["r1g2_full_reselection"]["product_weight_sum"]) - 1.0) <= 1e-3
