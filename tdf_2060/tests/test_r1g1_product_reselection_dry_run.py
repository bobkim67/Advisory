"""R-1G.1 — Product Re-selection (selection only) tests.

Scope:
- ETF / Fund happy path
- dm_ex_us_equity / us_high_yield 신규 편입 (target > 0 → selected)
- product_weight_sum 정합성
- validity flag invariants (production_applied=false / dry_run_only=true /
  manager_override_saa_layer=true / implementation_ready=false /
  implementation_review_status="review_required")
- 별도 출력 디렉토리
- baseline / R-1F.2 / manager_selected_saa JSON / config mutation 없음
- bit-identical baseline (`_phase_e62_baseline.json`) sha256 unchanged
- 80:20 distance metric 부활 없음
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT.parent  # Advisory/
CONFIG_DIR = REPO_ROOT / "tdf_engine" / "config"

OPP_DIR = REPO_ROOT / "out" / "db_review_relaxed_e62" / "saa_opportunity_set" / "20260513"
ETF_MANAGER_JSON = OPP_DIR / "manager_selected_saa_etf_20260513.json"
FUND_MANAGER_JSON = OPP_DIR / "manager_selected_saa_fund_20260513.json"

ETF_R1F2_JSON = REPO_ROOT / "out" / "db_etf_relaxed_e62_r1e_dryrun" / "portfolio_etf_20260513.json"
FUND_R1F2_JSON = REPO_ROOT / "out" / "db_fund_relaxed_e62_r1e_dryrun" / "portfolio_fund_20260513.json"

ETF_BASELINE_JSON = REPO_ROOT / "out" / "db_etf_relaxed_e62" / "portfolio_etf_20260511.json"
FUND_BASELINE_JSON = REPO_ROOT / "out" / "db_fund_relaxed_e62" / "portfolio_fund_20260511.json"

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
    reason="R-1F.1/R-1F.2 outputs or etf_list/fund_list not present",
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


def _build_etf_payload(etf_manager, etf_r1f2) -> dict:
    from tdf_engine.optimization.product_reselection_dry_run import (
        build_product_reselection,
    )
    return build_product_reselection(
        etf_manager, etf_r1f2,
        source_root=SOURCE_ROOT,
        config_dir=CONFIG_DIR,
        manager_dump_path=ETF_MANAGER_JSON,
        r1f2_dump_path=ETF_R1F2_JSON,
        baseline_portfolio_path=ETF_BASELINE_JSON,
        selection_as_of="20260513",
        output_as_of="20260513",
        baseline_portfolio_as_of="20260511",
        universe_as_of="20260511",
    )


def _build_fund_payload(fund_manager, fund_r1f2) -> dict:
    from tdf_engine.optimization.product_reselection_dry_run import (
        build_product_reselection,
    )
    return build_product_reselection(
        fund_manager, fund_r1f2,
        source_root=SOURCE_ROOT,
        config_dir=CONFIG_DIR,
        manager_dump_path=FUND_MANAGER_JSON,
        r1f2_dump_path=FUND_R1F2_JSON,
        baseline_portfolio_path=FUND_BASELINE_JSON,
        selection_as_of="20260513",
        output_as_of="20260513",
        baseline_portfolio_as_of="20260511",
        universe_as_of="20260511",
    )


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------


def test_happy_path_etf(etf_manager, etf_r1f2) -> None:
    payload = _build_etf_payload(etf_manager, etf_r1f2)
    assert payload["meta"]["portfolio_type"] == "etf"
    assert payload["meta"]["product_allocation_method"] == "full_reselection"
    assert payload["product_count"] >= 1


def test_happy_path_fund(fund_manager, fund_r1f2) -> None:
    payload = _build_fund_payload(fund_manager, fund_r1f2)
    assert payload["meta"]["portfolio_type"] == "fund"
    assert payload["product_count"] >= 1


def test_write_json_and_md(etf_manager, etf_r1f2, tmp_path: Path) -> None:
    from tdf_engine.optimization.product_reselection_dry_run import (
        render_product_reselection_summary_md,
        write_product_reselection_json,
    )
    payload = _build_etf_payload(etf_manager, etf_r1f2)
    j = write_product_reselection_json(payload, tmp_path / "p.json")
    m = render_product_reselection_summary_md(payload, tmp_path / "p.md")
    assert j.exists()
    assert m.exists()
    text = m.read_text(encoding="utf-8")
    assert "R-1G.1" in text
    # 80:20 distance metric 부재 (regression)
    assert "bucket_distance_from_80_20" not in text
    assert "full_weight_distance_from_80_20" not in text


# ---------------------------------------------------------------------------
# 2. Validity flag invariants (strict)
# ---------------------------------------------------------------------------


def test_safety_flags_strict_etf(etf_manager, etf_r1f2) -> None:
    payload = _build_etf_payload(etf_manager, etf_r1f2)
    m = payload["meta"]
    assert m["production_applied"] is False
    assert m["dry_run_only"] is True
    assert m["manager_override_saa_layer"] is True
    assert m["product_allocation_method"] == "full_reselection"
    # implementation_ready 는 무조건 false / review_required (사용자 지시)
    assert m["implementation_ready"] is False
    assert m["implementation_review_status"] == "review_required"
    assert m["sign_off_required_for_production"] is True
    assert m["valid_asset_level_dry_run"] is True


def test_as_of_separation_meta_fields(etf_manager, etf_r1f2) -> None:
    payload = _build_etf_payload(etf_manager, etf_r1f2)
    m = payload["meta"]
    assert m["selection_as_of"] == "20260513"
    assert m["baseline_portfolio_as_of"] == "20260511"
    assert m["universe_as_of"] == "20260511"
    assert m["output_as_of"] == "20260513"


def test_target_weight_source_default_label(etf_manager, etf_r1f2) -> None:
    payload = _build_etf_payload(etf_manager, etf_r1f2)
    assert payload["meta"]["target_weight_source"] == "r1f2_projection_final_asset_weights"


def test_target_weights_match_r1f2_asset_weights_dry_run(
    etf_manager, etf_r1f2,
) -> None:
    payload = _build_etf_payload(etf_manager, etf_r1f2)
    tgt = payload["target_asset_weights"]
    src = etf_r1f2["asset_weights_dry_run"]
    for k in src:
        assert abs(float(tgt[k]) - float(src[k])) < 1e-15


# ---------------------------------------------------------------------------
# 3. Newly-introduced assets get selected (key R-1G goal)
# ---------------------------------------------------------------------------


def test_dm_ex_us_equity_gets_selected_when_target_positive(
    etf_manager, etf_r1f2,
) -> None:
    payload = _build_etf_payload(etf_manager, etf_r1f2)
    tgt = payload["target_asset_weights"]["dm_ex_us_equity"]
    assert tgt > 0, "test prerequisite: target dm_ex_us_equity must be > 0"
    summary_row = next(
        s for s in payload["asset_summary"] if s["asset_key"] == "dm_ex_us_equity"
    )
    assert summary_row["n_universe"] > 0
    assert summary_row["n_selected"] >= 1, (
        "R-1G.1 must select ≥1 product for dm_ex_us_equity (target > 0)"
    )


def test_us_high_yield_universe_short_warning_or_selected(
    etf_manager, etf_r1f2,
) -> None:
    """us_high_yield universe = 2 건 (ETF). selected ≥ 1 또는 warning 표기."""
    payload = _build_etf_payload(etf_manager, etf_r1f2)
    tgt = payload["target_asset_weights"]["us_high_yield"]
    assert tgt > 0, "test prerequisite: target us_high_yield must be > 0"
    summary_row = next(
        s for s in payload["asset_summary"] if s["asset_key"] == "us_high_yield"
    )
    # 두 경우 모두 OK: (a) selected ≥1 + universe short warning 가능 또는
    # (b) universe = 0 으로 unresolved 표기
    if summary_row["n_universe"] > 0:
        assert summary_row["n_selected"] >= 1
        if summary_row["n_universe"] < 3:
            # universe short warning 명시 (asset 명 포함)
            warnings_str = " ".join(payload["warnings"])
            assert "us_high_yield" in warnings_str
    else:
        assert "us_high_yield" in payload["unresolved_assets"]


# ---------------------------------------------------------------------------
# 4. Pre-execution validation (recursive from R-1F.1 / R-1F.2)
# ---------------------------------------------------------------------------


def test_aborts_when_manager_production_applied_true(
    etf_manager, etf_r1f2,
) -> None:
    from tdf_engine.optimization.product_reselection_dry_run import (
        build_product_reselection,
    )
    broken = copy.deepcopy(etf_manager)
    broken["meta"]["production_applied"] = True
    with pytest.raises(ValueError, match="production_applied"):
        build_product_reselection(
            broken, etf_r1f2,
            source_root=SOURCE_ROOT, config_dir=CONFIG_DIR,
            manager_dump_path=ETF_MANAGER_JSON,
            r1f2_dump_path=ETF_R1F2_JSON,
            baseline_portfolio_path=ETF_BASELINE_JSON,
        )


def test_aborts_when_r1f2_dry_run_only_false(
    etf_manager, etf_r1f2,
) -> None:
    from tdf_engine.optimization.product_reselection_dry_run import (
        build_product_reselection,
    )
    broken = copy.deepcopy(etf_r1f2)
    broken["meta"]["dry_run_only"] = False
    with pytest.raises(ValueError, match="dry_run_only"):
        build_product_reselection(
            etf_manager, broken,
            source_root=SOURCE_ROOT, config_dir=CONFIG_DIR,
            manager_dump_path=ETF_MANAGER_JSON,
            r1f2_dump_path=ETF_R1F2_JSON,
            baseline_portfolio_path=ETF_BASELINE_JSON,
        )


def test_aborts_in_production_operating_mode(
    etf_manager, etf_r1f2,
) -> None:
    from tdf_engine.optimization.product_reselection_dry_run import (
        build_product_reselection,
    )
    with pytest.raises(ValueError, match="operating_mode"):
        build_product_reselection(
            etf_manager, etf_r1f2,
            source_root=SOURCE_ROOT, config_dir=CONFIG_DIR,
            manager_dump_path=ETF_MANAGER_JSON,
            r1f2_dump_path=ETF_R1F2_JSON,
            baseline_portfolio_path=ETF_BASELINE_JSON,
            operating_mode="production",
        )


def test_aborts_when_reference_selected(
    etf_manager, etf_r1f2,
) -> None:
    from tdf_engine.optimization.product_reselection_dry_run import (
        build_product_reselection,
    )
    broken = copy.deepcopy(etf_manager)
    broken["selected_candidate"]["candidate_id"] = "ref_max_sharpe"
    with pytest.raises(ValueError, match="sampled"):
        build_product_reselection(
            broken, etf_r1f2,
            source_root=SOURCE_ROOT, config_dir=CONFIG_DIR,
            manager_dump_path=ETF_MANAGER_JSON,
            r1f2_dump_path=ETF_R1F2_JSON,
            baseline_portfolio_path=ETF_BASELINE_JSON,
        )


# ---------------------------------------------------------------------------
# 5. Output directory separation
# ---------------------------------------------------------------------------


def test_output_dir_separate_from_baseline(
    etf_manager, etf_r1f2, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.product_reselection_dry_run import (
        write_product_reselection_json,
    )
    payload = _build_etf_payload(etf_manager, etf_r1f2)
    dry_dir = tmp_path / "db_etf_relaxed_e62_r1g_reselection"
    out = write_product_reselection_json(
        payload, dry_dir / "product_reselection_etf_20260513.json",
    )
    assert out.parent != ETF_BASELINE_JSON.parent
    assert out.parent != ETF_R1F2_JSON.parent
    assert "r1g_reselection" in str(out.parent)


# ---------------------------------------------------------------------------
# 6. Mutation guards
# ---------------------------------------------------------------------------


def test_baseline_portfolio_json_sha_unchanged(
    etf_manager, etf_r1f2, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.product_reselection_dry_run import (
        render_product_reselection_summary_md,
        write_product_reselection_json,
    )
    pre = _sha(ETF_BASELINE_JSON)
    payload = _build_etf_payload(etf_manager, etf_r1f2)
    write_product_reselection_json(payload, tmp_path / "p.json")
    render_product_reselection_summary_md(payload, tmp_path / "p.md")
    post = _sha(ETF_BASELINE_JSON)
    assert pre == post


def test_r1f2_dry_run_json_sha_unchanged(
    etf_manager, etf_r1f2, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.product_reselection_dry_run import (
        write_product_reselection_json,
    )
    pre = _sha(ETF_R1F2_JSON)
    payload = _build_etf_payload(etf_manager, etf_r1f2)
    write_product_reselection_json(payload, tmp_path / "p.json")
    post = _sha(ETF_R1F2_JSON)
    assert pre == post


def test_input_payloads_not_mutated(etf_manager, etf_r1f2) -> None:
    snap_manager = copy.deepcopy(etf_manager)
    snap_r1f2 = copy.deepcopy(etf_r1f2)
    _ = _build_etf_payload(etf_manager, etf_r1f2)
    assert etf_manager == snap_manager
    assert etf_r1f2 == snap_r1f2


def test_bit_identical_baseline_snapshot_unchanged(
    etf_manager, etf_r1f2, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.product_reselection_dry_run import (
        write_product_reselection_json,
    )
    if not BASELINE_SNAPSHOT.exists():
        pytest.skip("baseline snapshot not present")
    pre = _sha(BASELINE_SNAPSHOT)
    payload = _build_etf_payload(etf_manager, etf_r1f2)
    write_product_reselection_json(payload, tmp_path / "p.json")
    post = _sha(BASELINE_SNAPSHOT)
    assert pre == post


def test_config_yaml_unchanged_after_run(
    etf_manager, etf_r1f2, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.product_reselection_dry_run import (
        write_product_reselection_json,
    )
    for y in ("universe_filter.yaml", "taa_policy.yaml", "asset_mapping.yaml"):
        path = CONFIG_DIR / y
        if not path.exists():
            continue
        pre = _sha(path)
        payload = _build_etf_payload(etf_manager, etf_r1f2)
        write_product_reselection_json(payload, tmp_path / "p.json")
        post = _sha(path)
        assert pre == post, f"{y} sha changed after R-1G.1 run"


# ---------------------------------------------------------------------------
# 7. Product weight sanity
# ---------------------------------------------------------------------------


def test_all_selected_weights_non_negative(etf_manager, etf_r1f2) -> None:
    payload = _build_etf_payload(etf_manager, etf_r1f2)
    for r in payload["selected_products"]:
        assert float(r["weight"]) >= -1e-12


def test_selected_weight_sum_does_not_exceed_target_plus_tol(
    etf_manager, etf_r1f2,
) -> None:
    payload = _build_etf_payload(etf_manager, etf_r1f2)
    assert payload["selected_weight_sum"] <= payload["target_weight_sum"] + 1e-6


# ---------------------------------------------------------------------------
# 8. Universe diagnostics surface
# ---------------------------------------------------------------------------


def test_universe_source_block_present(etf_manager, etf_r1f2) -> None:
    payload = _build_etf_payload(etf_manager, etf_r1f2)
    uni = payload["universe_source"]
    assert uni["type"] == "file"
    assert uni["product_type"] == "etf"
    assert uni["raw_count"] > 0
    assert isinstance(uni["classified_by_asset_class"], dict)
    # dm_ex_us_equity / us_high_yield 분류 카운트가 universe diag 에 등장
    assert "dm_ex_us_equity" in uni["classified_by_asset_class"]
