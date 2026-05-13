"""R-1F.2 — Manager-Selected SAA downstream dry-run tests.

Scope:
- valid manager_selected_saa → dry-run portfolio JSON + comparison md 생성
- production_applied == false / dry_run_only == true / manager_override_saa_layer == true
- 별도 출력 디렉토리 (production / baseline 보호)
- baseline portfolio JSON / opportunity_set / manager_selected_saa JSON 무변경
- tests/_phase_e62_baseline.json sha256 unchanged
- downstream_dry_run_allowed=false / operating_mode 위반 시 abort
- reference candidate (ref_max_sharpe / ref_80_20_equal_intra_bucket) 차단
- comparison md 생성 + 80:20 distance metric 부재
- TAA / projection / 기존 core 모듈 사용 (수정 없이)
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "tdf_engine" / "config"
OPP_DIR = REPO_ROOT / "out" / "db_review_relaxed_e62" / "saa_opportunity_set" / "20260513"
ETF_MANAGER_JSON = OPP_DIR / "manager_selected_saa_etf_20260513.json"
FUND_MANAGER_JSON = OPP_DIR / "manager_selected_saa_fund_20260513.json"
ETF_BASELINE_JSON = REPO_ROOT / "out" / "db_etf_relaxed_e62" / "portfolio_etf_20260511.json"
FUND_BASELINE_JSON = REPO_ROOT / "out" / "db_fund_relaxed_e62" / "portfolio_fund_20260511.json"
BASELINE_SNAPSHOT = REPO_ROOT / "tests" / "_phase_e62_baseline.json"


pytestmark = pytest.mark.skipif(
    not (
        ETF_MANAGER_JSON.exists() and FUND_MANAGER_JSON.exists()
        and ETF_BASELINE_JSON.exists() and FUND_BASELINE_JSON.exists()
    ),
    reason="R-1F.1 manager_selected_saa JSON or baseline portfolio not present",
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
def etf_baseline() -> dict:
    return json.loads(ETF_BASELINE_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fund_baseline() -> dict:
    return json.loads(FUND_BASELINE_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------


def test_happy_path_dry_run_etf(etf_manager: dict, etf_baseline: dict) -> None:
    from tdf_engine.optimization.manager_selected_dry_run import build_dry_run_portfolio

    payload = build_dry_run_portfolio(
        etf_manager, etf_baseline,
        config_dir=CONFIG_DIR,
        manager_dump_path=ETF_MANAGER_JSON,
        baseline_path=ETF_BASELINE_JSON,
    )
    assert payload["meta"]["production_applied"] is False
    assert payload["meta"]["dry_run_only"] is True
    assert payload["meta"]["manager_override_saa_layer"] is True
    assert payload["meta"]["portfolio_type"] == "etf"
    assert payload["selected_candidate_id"] == etf_manager["selected_candidate"]["candidate_id"]


def test_happy_path_dry_run_fund(fund_manager: dict, fund_baseline: dict) -> None:
    from tdf_engine.optimization.manager_selected_dry_run import build_dry_run_portfolio

    payload = build_dry_run_portfolio(
        fund_manager, fund_baseline,
        config_dir=CONFIG_DIR,
        manager_dump_path=FUND_MANAGER_JSON,
        baseline_path=FUND_BASELINE_JSON,
    )
    assert payload["meta"]["portfolio_type"] == "fund"
    assert payload["meta"]["production_applied"] is False


def test_write_dry_run_portfolio_json_and_comparison_md(
    etf_manager: dict, etf_baseline: dict, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.manager_selected_dry_run import (
        build_dry_run_portfolio,
        render_comparison_md,
        write_dry_run_portfolio_json,
    )

    payload = build_dry_run_portfolio(
        etf_manager, etf_baseline,
        config_dir=CONFIG_DIR,
        manager_dump_path=ETF_MANAGER_JSON,
        baseline_path=ETF_BASELINE_JSON,
    )
    out_json = write_dry_run_portfolio_json(
        payload, tmp_path / "portfolio_etf_20260513.json"
    )
    out_md = render_comparison_md(
        payload, etf_baseline,
        tmp_path / "manager_selected_saa_dry_run_compare_etf_20260513.md",
    )
    assert out_json.exists()
    assert out_md.exists()
    text = out_md.read_text(encoding="utf-8")
    assert "Manager-Selected SAA Dry-Run Comparison" in text
    # 80:20 distance metric 부재
    assert "bucket_distance_from_80_20" not in text
    assert "full_weight_distance_from_80_20" not in text


# ---------------------------------------------------------------------------
# 2. Output schema invariants (R-1E §4 / §5)
# ---------------------------------------------------------------------------


def test_schema_has_required_fields(etf_manager: dict, etf_baseline: dict) -> None:
    from tdf_engine.optimization.manager_selected_dry_run import build_dry_run_portfolio

    payload = build_dry_run_portfolio(
        etf_manager, etf_baseline,
        config_dir=CONFIG_DIR,
        manager_dump_path=ETF_MANAGER_JSON,
        baseline_path=ETF_BASELINE_JSON,
    )
    required = {
        "meta", "source_manager_selected_saa_json", "baseline_portfolio_json",
        "selected_candidate_id", "selected_candidate_weights",
        "manager_override_saa", "baseline_max_sharpe_saa",
        "asset_allocation_dry_run", "asset_weights_dry_run",
        "asset_weights_baseline", "bucket_sums_after_projection",
        "max_abs_projection_drift_dry_run", "max_abs_projection_drift_baseline",
        "product_allocation_dry_run", "product_weight_sum_dry_run",
        "needs_selection_rerun_assets", "product_allocation_limitation",
        "comparison_to_baseline_available", "notes",
    }
    assert set(payload.keys()) >= required
    assert payload["comparison_to_baseline_available"] is True


# ---------------------------------------------------------------------------
# 2b. R-1F.2.1 validity flags
# ---------------------------------------------------------------------------


def test_r1f2_1_validity_flags_present(etf_manager: dict, etf_baseline: dict) -> None:
    from tdf_engine.optimization.manager_selected_dry_run import build_dry_run_portfolio

    payload = build_dry_run_portfolio(
        etf_manager, etf_baseline,
        config_dir=CONFIG_DIR,
        manager_dump_path=ETF_MANAGER_JSON,
        baseline_path=ETF_BASELINE_JSON,
    )
    meta = payload["meta"]
    # asset-level dry-run 은 valid 라 단언
    assert meta["valid_asset_level_dry_run"] is True
    # product allocation method label 명시
    assert meta["product_allocation_method"] == "baseline_proportional_scaling"
    # 모든 R-1F.2.1 flag 가 meta 에 존재
    for flag in (
        "valid_product_level_portfolio",
        "product_weight_sum_valid",
        "needs_full_product_reselection",
        "implementation_ready",
    ):
        assert flag in meta, f"missing R-1F.2.1 validity flag: {flag}"


def test_product_weight_sum_invalid_when_far_from_one(
    etf_manager: dict, etf_baseline: dict,
) -> None:
    """e62 baseline 의 max-Sharpe 가 2 자산에 집중 → manager override 로의 scaling
    이 정상 portfolio 가 아님 (product_weight_sum ≠ 1.0). flag 가 false 로 강제됨."""
    from tdf_engine.optimization.manager_selected_dry_run import build_dry_run_portfolio

    payload = build_dry_run_portfolio(
        etf_manager, etf_baseline,
        config_dir=CONFIG_DIR,
        manager_dump_path=ETF_MANAGER_JSON,
        baseline_path=ETF_BASELINE_JSON,
    )
    s = float(payload["product_weight_sum_dry_run"])
    assert abs(s - 1.0) > 0.1  # 실제로는 1.4 부근
    assert payload["meta"]["product_weight_sum_valid"] is False
    assert payload["meta"]["valid_product_level_portfolio"] is False
    assert payload["meta"]["needs_full_product_reselection"] is True
    assert payload["meta"]["implementation_ready"] is False


def test_needs_selection_rerun_includes_zero_baseline_assets(
    etf_manager: dict, etf_baseline: dict,
) -> None:
    """baseline 에서 0% 였던 자산 (dm_ex_us_equity, us_high_yield) 가 dry-run 에서
    weight > 0 으로 잡히면 needs_selection_rerun_assets 에 포함."""
    from tdf_engine.optimization.manager_selected_dry_run import build_dry_run_portfolio

    payload = build_dry_run_portfolio(
        etf_manager, etf_baseline,
        config_dir=CONFIG_DIR,
        manager_dump_path=ETF_MANAGER_JSON,
        baseline_path=ETF_BASELINE_JSON,
    )
    nra = set(payload["needs_selection_rerun_assets"])
    assert "dm_ex_us_equity" in nra
    assert "us_high_yield" in nra


def test_comparison_md_contains_validity_warning(
    etf_manager: dict, etf_baseline: dict, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.manager_selected_dry_run import (
        build_dry_run_portfolio, render_comparison_md,
    )

    payload = build_dry_run_portfolio(
        etf_manager, etf_baseline,
        config_dir=CONFIG_DIR,
        manager_dump_path=ETF_MANAGER_JSON,
        baseline_path=ETF_BASELINE_JSON,
    )
    md = render_comparison_md(payload, etf_baseline, tmp_path / "compare.md")
    text = md.read_text(encoding="utf-8")
    # warning section + R-1G mention + invalid sum 명시
    assert "Validity Warning" in text
    assert "valid_asset_level_dry_run" in text
    assert "valid_product_level_portfolio" in text
    assert "R-1G" in text
    assert "운용 가능한 최종 포트폴리오가 아니다" in text
    # 80:20 distance metric 부재 (regression)
    assert "bucket_distance_from_80_20" not in text
    assert "full_weight_distance_from_80_20" not in text


def test_bucket_sums_after_projection_close_to_80_20(
    etf_manager: dict, etf_baseline: dict,
) -> None:
    """TAA + projection 후 equity ≈ 0.80, fi ≈ 0.20 (Phase D relaxed [0,1] bound)."""
    from tdf_engine.optimization.manager_selected_dry_run import build_dry_run_portfolio

    payload = build_dry_run_portfolio(
        etf_manager, etf_baseline,
        config_dir=CONFIG_DIR,
        manager_dump_path=ETF_MANAGER_JSON,
        baseline_path=ETF_BASELINE_JSON,
    )
    eq = payload["bucket_sums_after_projection"]["equity"]
    fi = payload["bucket_sums_after_projection"]["fixed_income"]
    assert abs(eq + fi - 1.0) < 1e-6
    # Phase D relaxed bound 은 [0, 1] 이므로 strict 80/20 강제는 못 하지만,
    # override 가 eq=0.80 / fi=0.20 으로 시작하고 tilt sum=0 cash-neutral 이라
    # 실제 bucket 합은 0.75~0.85 / 0.15~0.25 정도 (regime 1 tilt 효과).
    assert 0.70 <= eq <= 0.95
    assert 0.05 <= fi <= 0.30


# ---------------------------------------------------------------------------
# 3. Output directory separation
# ---------------------------------------------------------------------------


def test_dry_run_writes_only_to_separate_directory(
    etf_manager: dict, etf_baseline: dict, tmp_path: Path,
) -> None:
    """dry-run 디렉토리는 production / baseline 디렉토리와 분리되어 있어야."""
    from tdf_engine.optimization.manager_selected_dry_run import (
        build_dry_run_portfolio, write_dry_run_portfolio_json,
    )

    payload = build_dry_run_portfolio(
        etf_manager, etf_baseline,
        config_dir=CONFIG_DIR,
        manager_dump_path=ETF_MANAGER_JSON,
        baseline_path=ETF_BASELINE_JSON,
    )
    dry_dir = tmp_path / "db_etf_relaxed_e62_r1e_dryrun"
    out = write_dry_run_portfolio_json(payload, dry_dir / "portfolio_etf_20260513.json")
    # 출력 디렉토리가 기존 production 디렉토리와 다름
    assert out.parent != ETF_BASELINE_JSON.parent
    assert "dryrun" in str(out.parent).lower() or "dry_run" in str(out.parent).lower()


# ---------------------------------------------------------------------------
# 4. Pre-execution validation
# ---------------------------------------------------------------------------


def test_aborts_when_downstream_dry_run_allowed_false(
    etf_manager: dict, etf_baseline: dict,
) -> None:
    from tdf_engine.optimization.manager_selected_dry_run import build_dry_run_portfolio

    broken = copy.deepcopy(etf_manager)
    broken["downstream_dry_run_allowed"] = False
    with pytest.raises(ValueError, match="downstream_dry_run_allowed"):
        build_dry_run_portfolio(
            broken, etf_baseline,
            config_dir=CONFIG_DIR,
            manager_dump_path=ETF_MANAGER_JSON,
            baseline_path=ETF_BASELINE_JSON,
        )


def test_aborts_when_operating_mode_not_relaxed(
    etf_manager: dict, etf_baseline: dict,
) -> None:
    from tdf_engine.optimization.manager_selected_dry_run import build_dry_run_portfolio

    with pytest.raises(ValueError, match="operating_mode"):
        build_dry_run_portfolio(
            etf_manager, etf_baseline,
            config_dir=CONFIG_DIR,
            manager_dump_path=ETF_MANAGER_JSON,
            baseline_path=ETF_BASELINE_JSON,
            operating_mode="production",
        )


def test_aborts_when_production_applied_true(
    etf_manager: dict, etf_baseline: dict,
) -> None:
    from tdf_engine.optimization.manager_selected_dry_run import build_dry_run_portfolio

    broken = copy.deepcopy(etf_manager)
    broken["meta"]["production_applied"] = True
    with pytest.raises(ValueError, match="production_applied"):
        build_dry_run_portfolio(
            broken, etf_baseline,
            config_dir=CONFIG_DIR,
            manager_dump_path=ETF_MANAGER_JSON,
            baseline_path=ETF_BASELINE_JSON,
        )


def test_aborts_when_manager_override_layer_false(
    etf_manager: dict, etf_baseline: dict,
) -> None:
    from tdf_engine.optimization.manager_selected_dry_run import build_dry_run_portfolio

    broken = copy.deepcopy(etf_manager)
    broken["meta"]["manager_override_saa_layer"] = False
    with pytest.raises(ValueError, match="manager_override_saa_layer"):
        build_dry_run_portfolio(
            broken, etf_baseline,
            config_dir=CONFIG_DIR,
            manager_dump_path=ETF_MANAGER_JSON,
            baseline_path=ETF_BASELINE_JSON,
        )


def test_aborts_when_reference_candidate_in_dump(
    etf_manager: dict, etf_baseline: dict,
) -> None:
    """selected_candidate.candidate_id 가 ref_* 면 차단."""
    from tdf_engine.optimization.manager_selected_dry_run import build_dry_run_portfolio

    broken = copy.deepcopy(etf_manager)
    broken["selected_candidate"]["candidate_id"] = "ref_max_sharpe"
    with pytest.raises(ValueError, match="sampled"):
        build_dry_run_portfolio(
            broken, etf_baseline,
            config_dir=CONFIG_DIR,
            manager_dump_path=ETF_MANAGER_JSON,
            baseline_path=ETF_BASELINE_JSON,
        )


def test_aborts_when_bucket_violation(
    etf_manager: dict, etf_baseline: dict,
) -> None:
    from tdf_engine.optimization.manager_selected_dry_run import build_dry_run_portfolio

    broken = copy.deepcopy(etf_manager)
    broken["selected_candidate"]["equity_weight"] = 0.50
    with pytest.raises(ValueError, match="bucket"):
        build_dry_run_portfolio(
            broken, etf_baseline,
            config_dir=CONFIG_DIR,
            manager_dump_path=ETF_MANAGER_JSON,
            baseline_path=ETF_BASELINE_JSON,
        )


def test_aborts_when_removed_metric_resurrected(
    etf_manager: dict, etf_baseline: dict,
) -> None:
    from tdf_engine.optimization.manager_selected_dry_run import build_dry_run_portfolio

    broken = copy.deepcopy(etf_manager)
    broken["selected_candidate"]["bucket_distance_from_80_20"] = 0.05
    with pytest.raises(ValueError, match="removed metric"):
        build_dry_run_portfolio(
            broken, etf_baseline,
            config_dir=CONFIG_DIR,
            manager_dump_path=ETF_MANAGER_JSON,
            baseline_path=ETF_BASELINE_JSON,
        )


# ---------------------------------------------------------------------------
# 5. Mutation invariants
# ---------------------------------------------------------------------------


def test_baseline_portfolio_json_file_sha_unchanged(
    etf_manager: dict, etf_baseline: dict, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.manager_selected_dry_run import (
        build_dry_run_portfolio, render_comparison_md, write_dry_run_portfolio_json,
    )

    pre = _sha(ETF_BASELINE_JSON)
    payload = build_dry_run_portfolio(
        etf_manager, etf_baseline,
        config_dir=CONFIG_DIR,
        manager_dump_path=ETF_MANAGER_JSON,
        baseline_path=ETF_BASELINE_JSON,
    )
    write_dry_run_portfolio_json(payload, tmp_path / "portfolio_etf_20260513.json")
    render_comparison_md(payload, etf_baseline, tmp_path / "compare.md")
    post = _sha(ETF_BASELINE_JSON)
    assert pre == post


def test_opportunity_set_and_manager_dump_not_mutated(
    etf_manager: dict, etf_baseline: dict,
) -> None:
    from tdf_engine.optimization.manager_selected_dry_run import build_dry_run_portfolio

    snap_manager = copy.deepcopy(etf_manager)
    snap_baseline = copy.deepcopy(etf_baseline)
    _ = build_dry_run_portfolio(
        etf_manager, etf_baseline,
        config_dir=CONFIG_DIR,
        manager_dump_path=ETF_MANAGER_JSON,
        baseline_path=ETF_BASELINE_JSON,
    )
    assert etf_manager == snap_manager
    assert etf_baseline == snap_baseline


def test_bit_identical_baseline_snapshot_sha_unchanged(
    etf_manager: dict, etf_baseline: dict, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.manager_selected_dry_run import (
        build_dry_run_portfolio, write_dry_run_portfolio_json,
    )

    if not BASELINE_SNAPSHOT.exists():
        pytest.skip("baseline snapshot not present")
    pre = _sha(BASELINE_SNAPSHOT)
    payload = build_dry_run_portfolio(
        etf_manager, etf_baseline,
        config_dir=CONFIG_DIR,
        manager_dump_path=ETF_MANAGER_JSON,
        baseline_path=ETF_BASELINE_JSON,
    )
    write_dry_run_portfolio_json(payload, tmp_path / "portfolio_etf_20260513.json")
    post = _sha(BASELINE_SNAPSHOT)
    assert pre == post


# ---------------------------------------------------------------------------
# 6. Config not modified by dry-run
# ---------------------------------------------------------------------------


def test_config_files_not_touched(
    etf_manager: dict, etf_baseline: dict, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.manager_selected_dry_run import (
        build_dry_run_portfolio, write_dry_run_portfolio_json,
    )

    taa_yaml = CONFIG_DIR / "taa_policy.yaml"
    pre = _sha(taa_yaml)
    payload = build_dry_run_portfolio(
        etf_manager, etf_baseline,
        config_dir=CONFIG_DIR,
        manager_dump_path=ETF_MANAGER_JSON,
        baseline_path=ETF_BASELINE_JSON,
    )
    write_dry_run_portfolio_json(payload, tmp_path / "portfolio_etf_20260513.json")
    post = _sha(taa_yaml)
    assert pre == post
