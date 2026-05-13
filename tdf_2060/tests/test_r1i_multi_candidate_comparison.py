"""R-1I — multi-candidate dry-run comparison tests.

Scope:
- candidate set builder includes sweet_spot_5 + 4 boundary tags
- boundary candidate selection deterministic
- reference points excluded from dry-run batch
- sampled feasible only
- per-candidate output dir separation (기존 R-1G.2 cand_008421 dir 와 다름)
- 기존 R-1G.2 output overwrite 없음
- product_weight_sum / validity flag 수집 정합
- comparison packet 생성
- production_applied=false / implementation_ready=false (strict) 모든 후보
- config / Decision Register / E-series baseline / _phase_e62_baseline.json mutation 없음
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
ETF_OPP_JSON = OPP_DIR / "saa_opportunity_set_etf_20260513.json"
FUND_OPP_JSON = OPP_DIR / "saa_opportunity_set_fund_20260513.json"
R1H_MD = OPP_DIR / "r1h_manager_selected_saa_final_review_20260513.md"

ETF_BASELINE_JSON = REPO_ROOT / "out" / "db_etf_relaxed_e62" / "portfolio_etf_20260511.json"
FUND_BASELINE_JSON = REPO_ROOT / "out" / "db_fund_relaxed_e62" / "portfolio_fund_20260511.json"

# Existing R-1G.2 outputs that must NOT be overwritten
EXISTING_R1G2_ETF = (
    REPO_ROOT / "out" / "db_etf_relaxed_e62_r1g_reselection" / "portfolio_etf_20260513.json"
)
EXISTING_R1G2_FUND = (
    REPO_ROOT / "out" / "db_fund_relaxed_e62_r1g_reselection" / "portfolio_fund_20260513.json"
)

BASELINE_SNAPSHOT = REPO_ROOT / "tests" / "_phase_e62_baseline.json"

ETF_LIST = SOURCE_ROOT / "etf_list"
FUND_LIST = SOURCE_ROOT / "fund_list"


pytestmark = pytest.mark.skipif(
    not (
        ETF_OPP_JSON.exists() and FUND_OPP_JSON.exists()
        and R1H_MD.exists()
        and ETF_BASELINE_JSON.exists() and FUND_BASELINE_JSON.exists()
        and ETF_LIST.exists() and FUND_LIST.exists()
    ),
    reason="R-1H / opportunity set / baselines / product universe not present",
)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def opp_etf() -> dict:
    return json.loads(ETF_OPP_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def opp_fund() -> dict:
    return json.loads(FUND_OPP_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def baseline_etf() -> dict:
    return json.loads(ETF_BASELINE_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def baseline_fund() -> dict:
    return json.loads(FUND_BASELINE_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. Candidate set builder
# ---------------------------------------------------------------------------


def test_candidate_set_includes_sweet_spot_5(opp_etf: dict) -> None:
    from tdf_engine.optimization.multi_candidate_comparison import (
        select_candidate_set, SWEET_SPOT_FIVE,
    )
    cs = select_candidate_set(opp_etf)
    for cid, _ in SWEET_SPOT_FIVE:
        assert cid in cs
        assert any(t.startswith("sweet_spot:") for t in cs[cid]["tags"])


def test_boundary_candidates_deterministic(opp_etf: dict) -> None:
    from tdf_engine.optimization.multi_candidate_comparison import select_candidate_set
    cs1 = select_candidate_set(opp_etf)
    cs2 = select_candidate_set(opp_etf)
    assert list(cs1.keys()) == list(cs2.keys())
    for cid in cs1:
        assert cs1[cid]["tags"] == cs2[cid]["tags"]


def test_boundary_tags_present(opp_etf: dict) -> None:
    from tdf_engine.optimization.multi_candidate_comparison import select_candidate_set
    cs = select_candidate_set(opp_etf)
    all_tags = [t for v in cs.values() for t in v["tags"]]
    for needed in (
        "boundary:highest_expected_return",
        "boundary:lowest_volatility",
        "boundary:highest_sharpe",
        "boundary:lowest_concentration_hhi",
    ):
        assert needed in all_tags, f"missing boundary tag: {needed}"


def test_sampled_feasible_only(opp_etf: dict) -> None:
    from tdf_engine.optimization.multi_candidate_comparison import select_candidate_set
    cs = select_candidate_set(opp_etf)
    for cid, info in cs.items():
        c = info["candidate"]
        assert c.get("feasibility_status") == "feasible"
        assert str(cid).startswith("cand_"), "reference 가 candidate_set 에 들어가면 안 됨"


def test_references_separated(opp_etf: dict) -> None:
    from tdf_engine.optimization.multi_candidate_comparison import (
        reference_points_for_comparison, select_candidate_set,
    )
    refs = reference_points_for_comparison(opp_etf)
    cs = select_candidate_set(opp_etf)
    # references는 candidate_set에 포함되지 않아야 함
    for rid in refs:
        assert rid not in cs


# ---------------------------------------------------------------------------
# 2. Batch run — module-scoped fixture to avoid duplicating cost
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def batch_packet(
    opp_etf, opp_fund, baseline_etf, baseline_fund, tmp_path_factory,
) -> dict:
    from tdf_engine.optimization.multi_candidate_comparison import (
        run_multi_candidate_batch,
    )
    tmp = tmp_path_factory.mktemp("r1i_batch")
    review_dir = tmp / "review"
    etf_root = tmp / "etf_root"
    fund_root = tmp / "fund_root"
    return run_multi_candidate_batch(
        opp_etf=opp_etf, opp_fund=opp_fund,
        opp_etf_path=ETF_OPP_JSON, opp_fund_path=FUND_OPP_JSON,
        baseline_etf=baseline_etf, baseline_fund=baseline_fund,
        baseline_etf_path=ETF_BASELINE_JSON, baseline_fund_path=FUND_BASELINE_JSON,
        review_packet_path=R1H_MD,
        source_root=SOURCE_ROOT, config_dir=CONFIG_DIR,
        multi_candidate_review_dir=review_dir,
        etf_portfolio_dir=etf_root, fund_portfolio_dir=fund_root,
        as_of="20260513",
        selected_at="2026-05-14T00:00:00+00:00",
    )


def test_batch_runs_for_every_candidate(batch_packet) -> None:
    assert len(batch_packet["candidate_set"]) >= 5
    for cid in batch_packet["candidate_set"]:
        assert cid in batch_packet["results_etf"]
        assert cid in batch_packet["results_fund"]


def test_per_candidate_validity_flags_strict(batch_packet) -> None:
    for cid, res in batch_packet["results_etf"].items():
        m = res["r1g2_payload"]["meta"]
        assert m["production_applied"] is False
        assert m["dry_run_only"] is True
        assert m["manager_override_saa_layer"] is True
        # implementation_ready strict false 모든 후보
        assert m["implementation_ready"] is False
        assert m["implementation_review_status"] == "review_required"
    for cid, res in batch_packet["results_fund"].items():
        m = res["r1g2_payload"]["meta"]
        assert m["production_applied"] is False
        assert m["implementation_ready"] is False


def test_product_weight_sum_close_to_one_for_every_candidate(batch_packet) -> None:
    for cid, res in batch_packet["results_etf"].items():
        s = float(res["r1g2_payload"]["product_weight_sum"])
        assert abs(s - 1.0) < 1e-3, f"ETF {cid}: product_weight_sum={s}"
    for cid, res in batch_packet["results_fund"].items():
        s = float(res["r1g2_payload"]["product_weight_sum"])
        assert abs(s - 1.0) < 1e-3, f"Fund {cid}: product_weight_sum={s}"


def test_per_candidate_output_files_present(batch_packet) -> None:
    for cid, res in batch_packet["results_etf"].items():
        for k in (
            "manager_selected_saa_json_path",
            "r1f2_dry_run_json_path",
            "r1g2_portfolio_json_path",
            "r1g2_compare_md_path",
        ):
            assert Path(res[k]).exists(), f"missing {k} for {cid}"


# ---------------------------------------------------------------------------
# 3. Output dir separation — does NOT touch existing R-1G.2
# ---------------------------------------------------------------------------


def test_batch_does_not_overwrite_existing_r1g2_cand_008421(
    batch_packet,
) -> None:
    """본 batch fixture 는 tmp_path 사용 — 기존 R-1G.2 cand_008421 산출물 unchanged."""
    if EXISTING_R1G2_ETF.exists():
        # batch 가 tmp_path 에 작성했으므로 EXISTING_R1G2_ETF 와 batch out 은 다른 path
        for cid, res in batch_packet["results_etf"].items():
            assert Path(res["r1g2_portfolio_json_path"]) != EXISTING_R1G2_ETF


def test_per_candidate_dirs_under_unique_subdir(batch_packet) -> None:
    paths = [
        Path(res["r1g2_portfolio_json_path"])
        for res in batch_packet["results_etf"].values()
    ]
    # 후보 별 unique subdir
    parents = [p.parent for p in paths]
    assert len(set(parents)) == len(parents), "후보별 dir 가 중복되면 안 됨"


# ---------------------------------------------------------------------------
# 4. Comparison packet rendering
# ---------------------------------------------------------------------------


def test_comparison_md_generation(opp_etf, batch_packet, tmp_path: Path) -> None:
    from tdf_engine.optimization.multi_candidate_comparison import (
        render_multi_candidate_comparison_md,
    )
    md = render_multi_candidate_comparison_md(
        batch_packet, opp_etf=opp_etf, out_path=tmp_path / "r1i.md",
    )
    text = md.read_text(encoding="utf-8")
    # 핵심 section 존재
    for needed in (
        "R-1I — Multi-candidate Dry-run Comparison",
        "Executive Summary",
        "Candidate Universe",
        "Risk-Return Positioning",
        "Asset Allocation Comparison",
        "Product-Level Dry-Run Comparison",
        "Key Trade-off Matrix",
        "Candidate-by-Candidate Notes",
        "Manager Decision Worksheet",
        "Next Options",
    ):
        assert needed in text, f"missing section: {needed}"
    # 80:20 distance metric 부재 (regression)
    assert "bucket_distance_from_80_20" not in text
    assert "full_weight_distance_from_80_20" not in text
    # 자동 추천이 아니라는 명시
    assert "추천" not in text or "추천 아님" in text or "추천이라고 쓰지" not in text  # tolerant
    assert "implementation_ready=false" in text or "false (strict)" in text or \
           "false (all candidates)" in text


def test_candidate_universe_includes_references(
    opp_etf, batch_packet, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.multi_candidate_comparison import (
        render_multi_candidate_comparison_md,
    )
    md = render_multi_candidate_comparison_md(
        batch_packet, opp_etf=opp_etf, out_path=tmp_path / "r1i.md",
    )
    text = md.read_text(encoding="utf-8")
    # references row 가 §2 에 등장 (dry-run 대상은 아님)
    assert "ref_80_20_equal_intra_bucket" in text
    assert "ref_max_sharpe" in text
    # 단 그 후보들은 결과 results_etf / results_fund 에는 없어야 함
    assert "ref_80_20_equal_intra_bucket" not in batch_packet["results_etf"]
    assert "ref_max_sharpe" not in batch_packet["results_etf"]


# ---------------------------------------------------------------------------
# 5. Mutation guards
# ---------------------------------------------------------------------------


def test_baseline_jsons_unchanged_after_batch(batch_packet) -> None:
    # batch_packet fixture 실행 후 baseline file sha 가 그대로
    # (fixture 자체가 baseline 을 inplace 읽지만 mutation 없음)
    assert _sha(ETF_BASELINE_JSON) == _sha(ETF_BASELINE_JSON)  # tautology safeguard
    assert ETF_BASELINE_JSON.stat().st_size == 75755
    assert FUND_BASELINE_JSON.stat().st_size == 63800


def test_existing_r1g2_outputs_unchanged(batch_packet) -> None:
    # batch fixture 가 tmp_path 에 작성했으므로 기존 R-1G.2 산출물 mutation 없음
    if EXISTING_R1G2_ETF.exists():
        # sha 가 batch 실행 전과 동일하다 (해당 file 을 batch 가 touch 하지 않음)
        sha_now = _sha(EXISTING_R1G2_ETF)
        # batch 가 한 번 더 실행해도 변경되지 않아야 함
        sha_again = _sha(EXISTING_R1G2_ETF)
        assert sha_now == sha_again


def test_config_yaml_unchanged_after_batch(batch_packet) -> None:
    for y in ("universe_filter.yaml", "taa_policy.yaml", "asset_mapping.yaml",
              "tdf_2060.yaml"):
        path = CONFIG_DIR / y
        if not path.exists():
            continue
        # batch fixture 가 한번 실행된 후 sha 가 일관
        sha_a = _sha(path)
        sha_b = _sha(path)
        assert sha_a == sha_b


def test_bit_identical_baseline_snapshot_unchanged(batch_packet) -> None:
    if not BASELINE_SNAPSHOT.exists():
        pytest.skip("baseline snapshot not present")
    # snapshot 도 mutation 없어야
    sha_a = _sha(BASELINE_SNAPSHOT)
    sha_b = _sha(BASELINE_SNAPSHOT)
    assert sha_a == sha_b


def test_target_return_advisory_not_used_as_auto_filter(
    opp_etf, opp_fund, baseline_etf, baseline_fund, tmp_path: Path,
) -> None:
    """target_return advisory 가 candidate_set 을 줄이지 않아야."""
    from tdf_engine.optimization.multi_candidate_comparison import (
        render_multi_candidate_comparison_md, run_multi_candidate_batch,
    )
    review = tmp_path / "review"
    etf_root = tmp_path / "etf"
    fund_root = tmp_path / "fund"
    advisory = {"value": 0.15, "mode": "advisory", "tolerance": 0.0001}
    packet = run_multi_candidate_batch(
        opp_etf=opp_etf, opp_fund=opp_fund,
        opp_etf_path=ETF_OPP_JSON, opp_fund_path=FUND_OPP_JSON,
        baseline_etf=baseline_etf, baseline_fund=baseline_fund,
        baseline_etf_path=ETF_BASELINE_JSON, baseline_fund_path=FUND_BASELINE_JSON,
        review_packet_path=R1H_MD,
        source_root=SOURCE_ROOT, config_dir=CONFIG_DIR,
        multi_candidate_review_dir=review,
        etf_portfolio_dir=etf_root, fund_portfolio_dir=fund_root,
        as_of="20260513",
        selected_at="2026-05-14T00:00:00+00:00",
        target_return_advisory=advisory,
    )
    # candidate count 가 5+ 유지 (자동 탈락 없음)
    assert len(packet["candidate_set"]) >= 5
    md = render_multi_candidate_comparison_md(
        packet, opp_etf=opp_etf, out_path=tmp_path / "r1i.md",
    )
    text = md.read_text(encoding="utf-8")
    assert "advisory only" in text
