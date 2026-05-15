"""Unit tests for tdf_engine.optimization.lasso_review (C-4)."""
from __future__ import annotations

import pytest

from tdf_engine.optimization.lasso_review import (
    LassoReviewError,
    build_review_csv,
    build_review_export,
    build_review_md,
    dedup_archetypes,
    extract_archetypes,
    find_medoid,
    resolve_selected_candidates,
)


# ---------- Fixtures ----------


def _mk_cand(cid, sharpe, er, vol, hhi, maxw, mvo=0.02,
             eq_intra=0.25, fi_intra=0.30, eq_w=0.8, fi_w=0.2,
             feasibility="feasible"):
    return {
        "candidate_id": cid,
        "sharpe": sharpe,
        "expected_return": er,
        "volatility": vol,
        "concentration_hhi": hhi,
        "max_asset_weight": maxw,
        "mvo_efficiency_score": mvo,
        "equity_intra_hhi": eq_intra,
        "fixed_income_intra_hhi": fi_intra,
        "equity_weight": eq_w,
        "fixed_income_weight": fi_w,
        "feasibility_status": feasibility,
        "weights": {},
    }


@pytest.fixture
def opportunity_set():
    cands = [
        _mk_cand("c1", 0.50, 0.09, 0.13, 0.20, 0.22, mvo=0.03),
        _mk_cand("c2", 0.55, 0.10, 0.12, 0.18, 0.20, mvo=0.025),  # min vol
        _mk_cand("c3", 0.60, 0.115, 0.14, 0.16, 0.24, mvo=0.022),  # min hhi
        _mk_cand("c4", 0.45, 0.085, 0.15, 0.30, 0.40, mvo=0.05),
        _mk_cand("c5", 0.70, 0.13, 0.11, 0.14, 0.18, mvo=0.015),  # top_sharpe ALSO min_vol candidate
        _mk_cand("c6", 0.65, 0.135, 0.135, 0.17, 0.21, mvo=0.014),  # max_er and frontier_near
    ]
    return {
        "meta": {"generated_at": "2026-05-01T00:00:00Z"},
        "candidates": cands,
    }


def _lasso_export(ids: list[str], selection_id: str = "lasso_test_1") -> dict:
    return {
        "schema_version": "r_track_2_lasso.1",
        "selection_id": selection_id,
        "source_opportunity_set_path": "/tmp/opp.json",
        "source_opportunity_set_sha256": "0" * 64,
        "selected_candidate_ids": ids,
        "selected_count": len(ids),
        "warning_labels": [],
    }


# ---------- Empty / single ----------


def test_extract_archetypes_empty_fails():
    with pytest.raises(LassoReviewError, match="empty"):
        extract_archetypes([])


def test_resolve_selected_candidates_single(opportunity_set):
    exp = _lasso_export(["c5"])
    out = resolve_selected_candidates(exp, opportunity_set)
    assert len(out) == 1
    assert out[0]["candidate_id"] == "c5"


def test_extract_archetypes_single_review(opportunity_set):
    out = resolve_selected_candidates(_lasso_export(["c5"]), opportunity_set)
    archetypes = extract_archetypes(out)
    # All 7 archetypes should point to c5 (single review degenerate)
    ids = [a.get("candidate_id") for a in archetypes if a["archetype"] != "clean_implementation"]
    assert all(i == "c5" for i in ids)
    # medoid distance should be 0.0 for single candidate
    medoid = next(a for a in archetypes if a["archetype"] == "medoid_candidate")
    assert medoid["metric_value"] == 0.0


# ---------- Individual archetypes ----------


def test_top_sharpe(opportunity_set):
    out = resolve_selected_candidates(_lasso_export(["c1", "c2", "c3", "c5", "c6"]), opportunity_set)
    archetypes = extract_archetypes(out)
    top = next(a for a in archetypes if a["archetype"] == "top_sharpe")
    assert top["candidate_id"] == "c5"  # sharpe=0.70


def test_min_volatility(opportunity_set):
    out = resolve_selected_candidates(_lasso_export(["c1", "c2", "c3", "c5", "c6"]), opportunity_set)
    archetypes = extract_archetypes(out)
    mv = next(a for a in archetypes if a["archetype"] == "min_volatility")
    assert mv["candidate_id"] == "c5"  # vol=0.11


def test_max_expected_return(opportunity_set):
    out = resolve_selected_candidates(_lasso_export(["c1", "c2", "c3", "c5", "c6"]), opportunity_set)
    archetypes = extract_archetypes(out)
    me = next(a for a in archetypes if a["archetype"] == "max_expected_return")
    assert me["candidate_id"] == "c6"  # er=0.135


def test_min_hhi(opportunity_set):
    out = resolve_selected_candidates(_lasso_export(["c1", "c2", "c3", "c5", "c6"]), opportunity_set)
    archetypes = extract_archetypes(out)
    mh = next(a for a in archetypes if a["archetype"] == "min_hhi")
    assert mh["candidate_id"] == "c5"  # hhi=0.14


def test_mvo_frontier_near(opportunity_set):
    out = resolve_selected_candidates(_lasso_export(["c1", "c2", "c3", "c5", "c6"]), opportunity_set)
    archetypes = extract_archetypes(out)
    fn = next(a for a in archetypes if a["archetype"] == "mvo_frontier_near")
    assert fn["candidate_id"] == "c6"  # mvo=0.014 (smallest)


# ---------- Clean implementation ----------


def test_clean_implementation_null_when_no_batch(opportunity_set):
    out = resolve_selected_candidates(_lasso_export(["c1", "c5", "c6"]), opportunity_set)
    archetypes = extract_archetypes(out)
    clean = next(a for a in archetypes if a["archetype"] == "clean_implementation")
    assert clean["candidate_id"] is None
    assert "no R-1G.2 batch" in clean["reason_if_null"]


def test_clean_implementation_picks_max_sharpe_when_clean_exists(opportunity_set):
    batch = {
        "c5": {"has_fallback": False, "has_universe_warning": False, "universe_warn_assets": ""},
        "c6": {"has_fallback": False, "has_universe_warning": False, "universe_warn_assets": ""},
        "c1": {"has_fallback": True, "has_universe_warning": True, "universe_warn_assets": "us_high_yield"},
    }
    out = resolve_selected_candidates(_lasso_export(["c1", "c5", "c6"]), opportunity_set, batch_signals=batch)
    archetypes = extract_archetypes(out)
    clean = next(a for a in archetypes if a["archetype"] == "clean_implementation")
    # Among c5 (clean, sharpe=0.70) and c6 (clean, sharpe=0.65) → c5 wins
    assert clean["candidate_id"] == "c5"


def test_clean_universe_warning_no_longer_blocks_clean(opportunity_set):
    """Policy (2026-05-15): universe_warning is product-selection concern, not
    SAA-clean criterion. c6 has has_fallback=False (eligible) + has_universe_warning=True;
    it must now count as clean_implementation."""
    batch = {
        "c5": {"has_fallback": True, "has_universe_warning": False, "universe_warn_assets": ""},
        "c6": {"has_fallback": False, "has_universe_warning": True, "universe_warn_assets": "us_high_yield"},
    }
    out = resolve_selected_candidates(_lasso_export(["c5", "c6"]), opportunity_set, batch_signals=batch)
    archetypes = extract_archetypes(out)
    clean = next(a for a in archetypes if a["archetype"] == "clean_implementation")
    # c5 is fallback=True → excluded from eligible set.
    # c6 is fallback=False → eligible AND clean (universe warning ignored).
    assert clean["candidate_id"] == "c6"


def test_all_fallback_raises_lasso_review_error(opportunity_set):
    """Policy: fallback_used candidates are excluded; if every selected
    candidate is fallback=True, extract_archetypes raises."""
    batch = {
        "c5": {"has_fallback": True, "has_universe_warning": False, "universe_warn_assets": ""},
        "c6": {"has_fallback": True, "has_universe_warning": False, "universe_warn_assets": ""},
    }
    out = resolve_selected_candidates(_lasso_export(["c5", "c6"]), opportunity_set, batch_signals=batch)
    with pytest.raises(LassoReviewError, match="fallback_used"):
        extract_archetypes(out)


def test_fallback_candidates_dropped_from_archetypes(opportunity_set):
    """Policy: fallback=True candidate must not become any archetype."""
    batch = {
        # c5 has the highest sharpe but is fallback=True → must NOT win top_sharpe.
        "c5": {"has_fallback": True, "has_universe_warning": False, "universe_warn_assets": ""},
        "c6": {"has_fallback": False, "has_universe_warning": False, "universe_warn_assets": ""},
        "c7": {"has_fallback": False, "has_universe_warning": False, "universe_warn_assets": ""},
    }
    out = resolve_selected_candidates(
        _lasso_export(["c5", "c6", "c7"]), opportunity_set, batch_signals=batch,
    )
    archetypes = extract_archetypes(out)
    for a in archetypes:
        # Every populated archetype must point to an eligible candidate.
        if a.get("candidate_id") is not None:
            assert a["candidate_id"] != "c5"


# ---------- Medoid ----------


def test_medoid_centroid_nearest(opportunity_set):
    out = resolve_selected_candidates(_lasso_export(["c1", "c2", "c3", "c5", "c6"]), opportunity_set)
    medoid_id, dist = find_medoid(out)
    assert medoid_id in {"c1", "c2", "c3", "c5", "c6"}
    assert dist is not None and dist >= 0.0


def test_medoid_distance_nonneg(opportunity_set):
    out = resolve_selected_candidates(_lasso_export(["c1", "c2", "c3", "c5", "c6"]), opportunity_set)
    archetypes = extract_archetypes(out)
    medoid = next(a for a in archetypes if a["archetype"] == "medoid_candidate")
    assert medoid["candidate_id"] is not None
    assert medoid["metric_value"] >= 0.0


# ---------- Dedup ----------


def test_dedup_archetypes_groups_roles(opportunity_set):
    # c5 is top_sharpe AND min_volatility AND min_hhi → dedup to single entry with 3 roles
    out = resolve_selected_candidates(_lasso_export(["c1", "c2", "c3", "c5", "c6"]), opportunity_set)
    archetypes = extract_archetypes(out)
    dedup = dedup_archetypes(archetypes)
    by_id = {r["candidate_id"]: r for r in dedup}
    assert "c5" in by_id
    assert "top_sharpe" in by_id["c5"]["roles"]
    assert "min_volatility" in by_id["c5"]["roles"]
    assert "min_hhi" in by_id["c5"]["roles"]
    # Null archetype (clean_implementation) excluded
    for r in dedup:
        assert r["candidate_id"] is not None


# ---------- Warning propagation ----------


def test_warning_propagation_selection_and_per_archetype(opportunity_set):
    # Make c4 corner-like (high HHI) so it surfaces WARN labels
    batch = {"c4": {"has_fallback": True, "has_universe_warning": True, "universe_warn_assets": "us_high_yield"}}
    out = resolve_selected_candidates(_lasso_export(["c1", "c2", "c4", "c5", "c6"]), opportunity_set, batch_signals=batch)
    archetypes = extract_archetypes(out)
    dedup = dedup_archetypes(archetypes)
    review = build_review_export(
        lasso_export=_lasso_export(["c1", "c2", "c4", "c5", "c6"]),
        candidates=out,
        archetypes=archetypes,
        dedup=dedup,
    )
    sl = review["selection_level_warning_labels"]
    # c4 has corner-like + fallback + universe warning → some WARN in selection level
    assert any("WARN" in lab for lab in sl)
    # Per-archetype warnings exist
    assert "per_archetype_warning_labels" in review


# ---------- Invariants ----------


def test_invariants_locked(opportunity_set):
    out = resolve_selected_candidates(_lasso_export(["c1", "c2", "c3"]), opportunity_set)
    archetypes = extract_archetypes(out)
    dedup = dedup_archetypes(archetypes)
    review = build_review_export(
        lasso_export=_lasso_export(["c1", "c2", "c3"]),
        candidates=out,
        archetypes=archetypes,
        dedup=dedup,
    )
    assert review["is_production_selection"] is False
    assert review["dry_run_only"] is True
    inv = review["permanent_invariants"]
    assert inv["implementation_ready"] is False
    assert inv["production_applied"] is False
    assert inv["phase_f_entered"] is False
    assert inv["operating_mode"] == "relaxed_diagnostic"


# ---------- CSV / MD smoke ----------


def test_csv_md_render(opportunity_set):
    out = resolve_selected_candidates(_lasso_export(["c1", "c2", "c3", "c5", "c6"]), opportunity_set)
    archetypes = extract_archetypes(out)
    dedup = dedup_archetypes(archetypes)
    csv_str = build_review_csv(out, archetypes)
    assert "archetype,candidate_id" in csv_str
    assert "top_sharpe" in csv_str
    review = build_review_export(
        lasso_export=_lasso_export(["c1", "c2", "c3", "c5", "c6"]),
        candidates=out, archetypes=archetypes, dedup=dedup,
    )
    md = build_review_md(review, out)
    assert "Archetypes" in md
    assert "top_sharpe" in md
    assert "is_production_selection" not in md or "False" in md  # invariants section uses backticks
