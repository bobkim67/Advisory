"""R-1D — SAA Opportunity Set similar_search tests.

Scope:
- coordinate distance correctness (manual recompute)
- coordinate ordering deterministic
- weight L2 correctness
- candidate search excludes self
- feasible_only excludes degenerate
- sampled_only excludes ref_max_sharpe (always) + ref_80_20 (by default)
- shortlist-neighborhood md generation
- input opportunity payload mutation 없음
- 80:20 distance metric 부활 없음
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
OPP_DIR = (
    REPO_ROOT / "out" / "db_review_relaxed_e62" / "saa_opportunity_set" / "20260513"
)
ETF_OPP_JSON = OPP_DIR / "saa_opportunity_set_etf_20260513.json"


pytestmark = pytest.mark.skipif(
    not ETF_OPP_JSON.exists(),
    reason="R-1B.2 opportunity_set JSON not present",
)


@pytest.fixture(scope="module")
def etf_payload() -> dict:
    return json.loads(ETF_OPP_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. Coordinate search
# ---------------------------------------------------------------------------


def test_coordinate_search_returns_k_results(etf_payload: dict) -> None:
    from tdf_engine.optimization.opportunity_set_search import find_similar_by_risk_return

    result = find_similar_by_risk_return(
        etf_payload,
        target_return=0.105, target_volatility=0.13,
        k=20,
    )
    assert result["mode"] == "coordinate"
    assert len(result["results"]) == 20


def test_coordinate_distance_correctness(etf_payload: dict) -> None:
    from tdf_engine.optimization.opportunity_set_search import find_similar_by_risk_return

    target_r, target_v = 0.105, 0.13
    result = find_similar_by_risk_return(
        etf_payload,
        target_return=target_r, target_volatility=target_v,
        k=5,
    )
    er_std = result["normalization"]["expected_return_std"]
    vol_std = result["normalization"]["volatility_std"]
    for c in result["results"]:
        dr = (c["expected_return"] - target_r) / er_std
        dv = (c["volatility"] - target_v) / vol_std
        expected = math.sqrt(dr * dr + dv * dv)
        assert abs(c["search_distance"] - expected) < 1e-12


def test_coordinate_search_deterministic_ordering(etf_payload: dict) -> None:
    from tdf_engine.optimization.opportunity_set_search import find_similar_by_risk_return

    r1 = find_similar_by_risk_return(
        etf_payload, target_return=0.10, target_volatility=0.13, k=30,
    )
    r2 = find_similar_by_risk_return(
        etf_payload, target_return=0.10, target_volatility=0.13, k=30,
    )
    ids1 = [c["candidate_id"] for c in r1["results"]]
    ids2 = [c["candidate_id"] for c in r2["results"]]
    assert ids1 == ids2


def test_coordinate_results_sorted_by_distance(etf_payload: dict) -> None:
    from tdf_engine.optimization.opportunity_set_search import find_similar_by_risk_return

    result = find_similar_by_risk_return(
        etf_payload, target_return=0.10, target_volatility=0.13, k=30,
    )
    dists = [c["search_distance"] for c in result["results"]]
    assert dists == sorted(dists)


# ---------------------------------------------------------------------------
# 2. Weight search
# ---------------------------------------------------------------------------


def test_weight_l2_correctness(etf_payload: dict) -> None:
    from tdf_engine.optimization.opportunity_set_search import find_similar_by_weights

    result = find_similar_by_weights(
        etf_payload, target_candidate_id="cand_008421", k=5,
    )
    # Manually recompute full_L2 for first result
    asset_keys = etf_payload["inputs"]["asset_keys"]
    target = None
    for c in etf_payload["candidates"]:
        if c["candidate_id"] == "cand_008421":
            target = c
            break
    assert target is not None
    first = result["results"][0]
    cand = None
    for c in etf_payload["candidates"]:
        if c["candidate_id"] == first["candidate_id"]:
            cand = c
            break
    assert cand is not None
    s = 0.0
    for k in asset_keys:
        d = float(target["weights"][k]) - float(cand["weights"][k])
        s += d * d
    expected = math.sqrt(s)
    assert abs(first["full_weight_l2_distance"] - expected) < 1e-12


def test_weight_search_excludes_self(etf_payload: dict) -> None:
    from tdf_engine.optimization.opportunity_set_search import find_similar_by_weights

    target_id = "cand_008421"
    result = find_similar_by_weights(etf_payload, target_candidate_id=target_id, k=20)
    for c in result["results"]:
        assert c["candidate_id"] != target_id


def test_weight_search_sorted_by_full_l2(etf_payload: dict) -> None:
    from tdf_engine.optimization.opportunity_set_search import find_similar_by_weights

    result = find_similar_by_weights(
        etf_payload, target_candidate_id="cand_008421", k=20,
    )
    distances = [c["full_weight_l2_distance"] for c in result["results"]]
    assert distances == sorted(distances)


def test_weight_search_includes_three_distance_metrics(etf_payload: dict) -> None:
    from tdf_engine.optimization.opportunity_set_search import find_similar_by_weights

    result = find_similar_by_weights(
        etf_payload, target_candidate_id="cand_008421", k=3,
    )
    for c in result["results"]:
        assert "full_weight_l2_distance" in c
        assert "equity_intra_weight_l2_distance" in c
        assert "fixed_income_intra_weight_l2_distance" in c
        assert c["full_weight_l2_distance"] >= 0.0
        # sampled candidates → intra L2 well-defined (eq_total=0.80, fi_total=0.20)
        assert c["equity_intra_weight_l2_distance"] is not None
        assert c["fixed_income_intra_weight_l2_distance"] is not None


# ---------------------------------------------------------------------------
# 3. Filters: feasible_only, sampled_only, include_ref_80_20
# ---------------------------------------------------------------------------


def test_feasible_only_excludes_degenerate(etf_payload: dict) -> None:
    """feasible_only=True (default) 시 degenerate 후보가 결과에 등장하지 않아야."""
    from tdf_engine.optimization.opportunity_set_search import find_similar_by_risk_return

    result = find_similar_by_risk_return(
        etf_payload,
        # 우측 extrapolation 영역 — degenerate 후보가 모이는 곳
        target_return=0.12, target_volatility=0.20,
        k=50, feasible_only=True,
    )
    for c in result["results"]:
        assert c["feasibility_status"] == "feasible"


def test_sampled_only_default_excludes_references(etf_payload: dict) -> None:
    """sampled_only=True (default) 시 ref_max_sharpe / ref_80_20 모두 결과 제외."""
    from tdf_engine.optimization.opportunity_set_search import find_similar_by_risk_return

    result = find_similar_by_risk_return(
        etf_payload,
        target_return=0.10, target_volatility=0.13,
        k=100, sampled_only=True,
    )
    ids = {c["candidate_id"] for c in result["results"]}
    assert "ref_max_sharpe" not in ids
    assert "ref_80_20_equal_intra_bucket" not in ids


def test_ref_max_sharpe_never_in_results_even_when_sampled_only_false(
    etf_payload: dict,
) -> None:
    """ref_max_sharpe 는 어떤 조합에서도 결과에 등장하지 않아야 (spec)."""
    from tdf_engine.optimization.opportunity_set_search import find_similar_by_risk_return

    result = find_similar_by_risk_return(
        etf_payload,
        target_return=0.105, target_volatility=0.13,
        k=200, sampled_only=False, include_ref_80_20=True,
    )
    ids = {c["candidate_id"] for c in result["results"]}
    assert "ref_max_sharpe" not in ids


def test_include_ref_80_20_when_enabled(etf_payload: dict) -> None:
    """include_ref_80_20=True 일 때 ref_80_20 이 풀에 포함되어 검색 가능."""
    from tdf_engine.optimization.opportunity_set_search import find_similar_by_risk_return

    refs = etf_payload["reference_points"]
    ref80 = refs["ref_80_20_equal_intra_bucket"]
    result = find_similar_by_risk_return(
        etf_payload,
        target_return=float(ref80["expected_return"]),
        target_volatility=float(ref80["volatility"]),
        k=200, include_ref_80_20=True,
    )
    ids = [c["candidate_id"] for c in result["results"]]
    # ref_80_20 좌표 정확히 일치 → distance=0 → 첫번째
    assert "ref_80_20_equal_intra_bucket" in ids


# ---------------------------------------------------------------------------
# 4. Target lookup edge cases
# ---------------------------------------------------------------------------


def test_unknown_candidate_id_raises(etf_payload: dict) -> None:
    from tdf_engine.optimization.opportunity_set_search import find_similar_by_weights

    with pytest.raises(ValueError, match="not found"):
        find_similar_by_weights(etf_payload, target_candidate_id="cand_999999")


# ---------------------------------------------------------------------------
# 5. Shortlist neighborhood
# ---------------------------------------------------------------------------


def test_shortlist_neighborhood_covers_all_eight_ids(etf_payload: dict) -> None:
    from tdf_engine.optimization.opportunity_set_search import (
        SHORTLIST_CANDIDATE_IDS,
        build_shortlist_neighborhood,
    )
    result = build_shortlist_neighborhood(etf_payload, k=5)
    assert set(result["results"].keys()) == set(SHORTLIST_CANDIDATE_IDS)
    for sid, entry in result["results"].items():
        assert not entry.get("missing"), f"{sid} missing"
        assert len(entry["by_risk_return"]) == 5
        assert len(entry["by_weights"]) == 5
        # 자기 자신 제외
        for c in entry["by_risk_return"]:
            assert c["candidate_id"] != sid
        for c in entry["by_weights"]:
            assert c["candidate_id"] != sid


def test_shortlist_neighborhood_md_generation(etf_payload: dict, tmp_path: Path) -> None:
    from tdf_engine.optimization.opportunity_set_search import (
        build_shortlist_neighborhood,
        render_shortlist_neighborhood_md,
    )
    result = build_shortlist_neighborhood(etf_payload, k=5)
    md = render_shortlist_neighborhood_md(
        result, etf_payload, tmp_path / "shortlist_neighbors.md",
    )
    assert md.exists()
    text = md.read_text(encoding="utf-8")
    assert "Shortlist Neighborhood" in text
    assert "cand_008421" in text
    assert "cand_007699" in text
    assert "risk-return" in text
    assert "weight similarity" in text
    # 80:20 metric 부활 금지
    assert "bucket_distance_from_80_20" not in text
    assert "full_weight_distance_from_80_20" not in text


# ---------------------------------------------------------------------------
# 6. Input mutation 없음
# ---------------------------------------------------------------------------


def test_input_payload_not_mutated_after_searches(etf_payload: dict) -> None:
    from tdf_engine.optimization.opportunity_set_search import (
        build_shortlist_neighborhood,
        find_similar_by_risk_return,
        find_similar_by_weights,
    )
    snapshot = copy.deepcopy(etf_payload)
    _ = find_similar_by_risk_return(
        etf_payload, target_return=0.10, target_volatility=0.13, k=10,
    )
    _ = find_similar_by_weights(
        etf_payload, target_candidate_id="cand_008421", k=10,
    )
    _ = build_shortlist_neighborhood(etf_payload, k=5)
    # 후보 dict 에 overlap_flags / overlap_score 가 새겨지지 않아야 함
    for c in etf_payload["candidates"][:5]:
        assert "overlap_flags" not in c
        assert "overlap_score" not in c
    assert etf_payload == snapshot
