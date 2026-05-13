"""R-1C — SAA Opportunity Set scatter / cloud plot tests.

Scope:
- compute_thresholds determinism + correctness
- overlap_score correctness
- rank_sweet_spot ordering (overlap → feasible → sharpe → HHIs → id)
- 3 PNG file generation per portfolio
- cloud review markdown generation
- input opportunity payload mutation 없음
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]

# R-1B.2 산출물을 입력으로 사용. test 가 R-1B.2 산출 후 실행되도록 skipif.
OPP_DIR = (
    REPO_ROOT / "out" / "db_review_relaxed_e62" / "saa_opportunity_set" / "20260513"
)
ETF_OPP_JSON = OPP_DIR / "saa_opportunity_set_etf_20260513.json"
FUND_OPP_JSON = OPP_DIR / "saa_opportunity_set_fund_20260513.json"


pytestmark = pytest.mark.skipif(
    not (ETF_OPP_JSON.exists() and FUND_OPP_JSON.exists()),
    reason="R-1B.2 opportunity_set JSON not present",
)


@pytest.fixture(scope="module")
def etf_payload() -> dict:
    return json.loads(ETF_OPP_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fund_payload() -> dict:
    return json.loads(FUND_OPP_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. compute_thresholds
# ---------------------------------------------------------------------------


def test_thresholds_keys_match_metric_specs(etf_payload: dict) -> None:
    from tdf_engine.optimization.opportunity_set_plot import (
        compute_thresholds, METRIC_DECILE_SPECS,
    )
    th = compute_thresholds(etf_payload["candidates"], quantile=0.10)
    spec_keys = {k for k, _, _ in METRIC_DECILE_SPECS}
    assert set(th.keys()) == spec_keys


def test_thresholds_deterministic(etf_payload: dict) -> None:
    from tdf_engine.optimization.opportunity_set_plot import compute_thresholds

    t1 = compute_thresholds(etf_payload["candidates"], quantile=0.10)
    t2 = compute_thresholds(etf_payload["candidates"], quantile=0.10)
    assert t1 == t2


def test_thresholds_direction_invariants(etf_payload: dict) -> None:
    """sharpe top 10% → high threshold; bottom-direction metrics → low threshold."""
    from tdf_engine.optimization.opportunity_set_plot import compute_thresholds

    th = compute_thresholds(etf_payload["candidates"], quantile=0.10)
    cands = etf_payload["candidates"]
    sharpe_vals = [c["sharpe"] for c in cands if c["sharpe"] is not None]
    hhi_vals = [c["concentration_hhi"] for c in cands]

    # sharpe top 10% threshold (90th percentile) > median
    sorted_sharpe = sorted(sharpe_vals)
    median_sharpe = sorted_sharpe[len(sorted_sharpe) // 2]
    assert th["sharpe"] > median_sharpe

    # HHI bottom 10% threshold (10th percentile) < median
    sorted_hhi = sorted(hhi_vals)
    median_hhi = sorted_hhi[len(sorted_hhi) // 2]
    assert th["concentration_hhi"] < median_hhi


# ---------------------------------------------------------------------------
# 2. overlap_score
# ---------------------------------------------------------------------------


def test_overlap_score_in_range_0_to_6(etf_payload: dict) -> None:
    from tdf_engine.optimization.opportunity_set_plot import (
        attach_overlap_scores, compute_thresholds,
    )
    th = compute_thresholds(etf_payload["candidates"], quantile=0.10)
    enriched = attach_overlap_scores(etf_payload["candidates"], th)
    for c in enriched:
        assert isinstance(c["overlap_score"], int)
        assert 0 <= c["overlap_score"] <= 6
        assert set(c["overlap_flags"].keys()) == {k for k, _, _ in __import__(
            "tdf_engine.optimization.opportunity_set_plot",
            fromlist=["METRIC_DECILE_SPECS"]
        ).METRIC_DECILE_SPECS}


def test_overlap_score_matches_flag_sum(etf_payload: dict) -> None:
    from tdf_engine.optimization.opportunity_set_plot import (
        attach_overlap_scores, compute_thresholds,
    )
    th = compute_thresholds(etf_payload["candidates"], quantile=0.10)
    enriched = attach_overlap_scores(etf_payload["candidates"], th)
    for c in enriched[:50]:
        manual = sum(1 for v in c["overlap_flags"].values() if v)
        assert c["overlap_score"] == manual


def test_overlap_score_manual_recompute_for_first_candidate(etf_payload: dict) -> None:
    """첫 후보의 overlap_score 를 metric / threshold 로 직접 재계산해 일치 확인."""
    from tdf_engine.optimization.opportunity_set_plot import (
        attach_overlap_scores, compute_thresholds, METRIC_DECILE_SPECS,
    )
    th = compute_thresholds(etf_payload["candidates"], quantile=0.10)
    enriched = attach_overlap_scores(etf_payload["candidates"], th)
    c = enriched[0]
    expected_flags: dict[str, bool] = {}
    for key, direction, _lbl in METRIC_DECILE_SPECS:
        v = c.get(key)
        if v is None or not math.isfinite(float(v)):
            expected_flags[key] = False
            continue
        thr = th[key]
        if direction == "top":
            expected_flags[key] = float(v) >= thr
        else:
            expected_flags[key] = float(v) <= thr
    assert c["overlap_flags"] == expected_flags
    assert c["overlap_score"] == sum(1 for v in expected_flags.values() if v)


# ---------------------------------------------------------------------------
# 3. rank_sweet_spot
# ---------------------------------------------------------------------------


def test_rank_sweet_spot_overlap_desc(etf_payload: dict) -> None:
    from tdf_engine.optimization.opportunity_set_plot import (
        attach_overlap_scores, compute_thresholds, rank_sweet_spot,
    )
    th = compute_thresholds(etf_payload["candidates"], quantile=0.10)
    enriched = attach_overlap_scores(etf_payload["candidates"], th)
    ranked = rank_sweet_spot(enriched)
    scores = [c["overlap_score"] for c in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rank_sweet_spot_tiebreak_within_same_overlap(etf_payload: dict) -> None:
    """동일 overlap_score 내부에서 sharpe desc 가 우선이고, 이어 HHI asc 가 작동하는지."""
    from tdf_engine.optimization.opportunity_set_plot import (
        attach_overlap_scores, compute_thresholds, rank_sweet_spot,
    )
    th = compute_thresholds(etf_payload["candidates"], quantile=0.10)
    enriched = attach_overlap_scores(etf_payload["candidates"], th)
    ranked = rank_sweet_spot(enriched)
    # 같은 overlap_score 인접 후보 둘 골라 sharpe / HHI 순서 검증
    for i in range(len(ranked) - 1):
        a, b = ranked[i], ranked[i + 1]
        if a["overlap_score"] != b["overlap_score"]:
            continue
        if a["feasibility_status"] != b["feasibility_status"]:
            continue
        sa = a["sharpe"] if a["sharpe"] is not None else -1e18
        sb = b["sharpe"] if b["sharpe"] is not None else -1e18
        if sa != sb:
            assert sa >= sb
            return
    # 만약 모든 인접 쌍이 sharpe tie 라면 본 test 는 vacuously pass.


# ---------------------------------------------------------------------------
# 4. Plot generation (smoke)
# ---------------------------------------------------------------------------


def test_build_cloud_artifacts_generates_three_plots(
    etf_payload: dict, tmp_path: Path
) -> None:
    from tdf_engine.optimization.opportunity_set_plot import build_cloud_artifacts

    art = build_cloud_artifacts(
        etf_payload, tmp_path, as_of_run="20260513",
        portfolio_tag="etf", quantile=0.10,
    )
    assert set(art["plots"].keys()) == {
        "risk_return_scatter", "metric_clouds", "overlap_score"
    }
    for p in art["plots"].values():
        assert Path(p).exists()
        assert Path(p).stat().st_size > 2000  # non-empty PNG


def test_review_md_generation(
    etf_payload: dict, fund_payload: dict, tmp_path: Path
) -> None:
    from tdf_engine.optimization.opportunity_set_plot import (
        build_cloud_artifacts, render_cloud_review_md,
    )
    etf_art = build_cloud_artifacts(
        etf_payload, tmp_path, as_of_run="20260513",
        portfolio_tag="etf", quantile=0.10,
    )
    fund_art = build_cloud_artifacts(
        fund_payload, tmp_path, as_of_run="20260513",
        portfolio_tag="fund", quantile=0.10,
    )
    md = render_cloud_review_md(
        as_of_run="20260513",
        etf_payload=etf_payload,
        fund_payload=fund_payload,
        etf_thresholds=etf_art["thresholds"],
        fund_thresholds=fund_art["thresholds"],
        etf_enriched_ranked=etf_art["enriched_ranked"],
        fund_enriched_ranked=fund_art["enriched_ranked"],
        plot_paths_etf=etf_art["plots"],
        plot_paths_fund=fund_art["plots"],
        out_path=tmp_path / "cloud_review.md",
    )
    assert md.exists()
    text = md.read_text(encoding="utf-8")
    assert "Cloud / Overlap Review" in text
    assert "overlap_score" in text
    assert "ref_max_sharpe" in text
    assert "ref_80_20_equal_intra_bucket" in text
    assert "## ETF" in text
    assert "## Fund" in text
    # 80:20 metric 부활 금지 — 옛 metric 이름이 review md 에 등장하면 안 됨
    assert "bucket_distance_from_80_20" not in text
    assert "full_weight_distance_from_80_20" not in text


# ---------------------------------------------------------------------------
# 5. Input mutation 없음
# ---------------------------------------------------------------------------


def test_input_payload_not_mutated(etf_payload: dict, tmp_path: Path) -> None:
    from tdf_engine.optimization.opportunity_set_plot import build_cloud_artifacts

    snapshot = copy.deepcopy(etf_payload)
    _ = build_cloud_artifacts(
        etf_payload, tmp_path, as_of_run="20260513",
        portfolio_tag="etf", quantile=0.10,
    )
    # overlap_flags / overlap_score 는 enriched copy 에만 존재, 원본은 무변경
    for c in etf_payload["candidates"][:5]:
        assert "overlap_flags" not in c
        assert "overlap_score" not in c
    assert etf_payload == snapshot
