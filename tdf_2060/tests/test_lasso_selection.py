"""Unit tests for tdf_engine.optimization.lasso_selection (C-2)."""
from __future__ import annotations

import datetime as dt

import pytest

from tdf_engine.optimization.lasso_selection import (
    SCHEMA_VERSION,
    PolygonError,
    SelectionConfigError,
    apply_post_selection_rule,
    build_export,
    compute_cloud_tags,
    compute_decile_thresholds,
    point_in_polygon,
    select_in_polygon,
    to_r1f1_yaml,
    validate_polygon,
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
def synthetic_pool():
    # 10 candidates spanning metric ranges for decile testing
    return [
        _mk_cand("c1", 0.50, 0.09, 0.13, 0.20, 0.22),
        _mk_cand("c2", 0.55, 0.10, 0.12, 0.18, 0.20),
        _mk_cand("c3", 0.60, 0.11, 0.14, 0.16, 0.24),
        _mk_cand("c4", 0.45, 0.08, 0.15, 0.30, 0.40),
        _mk_cand("c5", 0.70, 0.13, 0.11, 0.14, 0.18),  # high sharpe / low vol
        _mk_cand("c6", 0.40, 0.07, 0.16, 0.35, 0.45),  # warn-side
        _mk_cand("c7", 0.65, 0.12, 0.13, 0.17, 0.21),
        _mk_cand("c8", 0.58, 0.105, 0.14, 0.19, 0.23),
        _mk_cand("c9", 0.52, 0.095, 0.135, 0.21, 0.26),
        _mk_cand("c10", 0.48, 0.085, 0.145, 0.28, 0.55),  # corner_like (maxw>0.5)
    ]


# ---------- Polygon validation ----------


def test_validate_polygon_too_few_vertices():
    with pytest.raises(PolygonError, match="3 vertices"):
        validate_polygon([[0.0, 0.0], [1.0, 1.0]])


def test_validate_polygon_self_intersecting_bowtie():
    # Bowtie: edges (0,0)-(1,1) and (0,1)-(1,0) cross
    bowtie = [[0.0, 0.0], [1.0, 1.0], [0.0, 1.0], [1.0, 0.0]]
    with pytest.raises(PolygonError, match="intersect"):
        validate_polygon(bowtie)


def test_validate_polygon_simple_quad_ok():
    quad = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    validate_polygon(quad)  # no raise


# ---------- point_in_polygon ----------


def test_point_in_polygon_inside():
    square = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    assert point_in_polygon(0.5, 0.5, square) is True


def test_point_in_polygon_outside():
    square = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    assert point_in_polygon(1.5, 0.5, square) is False
    assert point_in_polygon(-0.5, 0.5, square) is False


def test_point_in_polygon_boundary_edge():
    square = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    # Point on bottom edge
    assert point_in_polygon(0.5, 0.0, square) is True
    # Point on right edge
    assert point_in_polygon(1.0, 0.5, square) is True


def test_point_in_polygon_vertex():
    square = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    assert point_in_polygon(0.0, 0.0, square) is True
    assert point_in_polygon(1.0, 1.0, square) is True


# ---------- Decile thresholds + cloud tags ----------


def test_compute_decile_thresholds_sharpe_top(synthetic_pool):
    th = compute_decile_thresholds(synthetic_pool)
    # 90th percentile via linear interpolation; for n=10 it falls between
    # the 8th and 9th sorted values. The single max candidate must clear it.
    sharpes_sorted = sorted(c["sharpe"] for c in synthetic_pool)
    assert sharpes_sorted[-2] <= th.sharpe_top <= sharpes_sorted[-1]
    # And the top candidate (c5=0.70) is_sharpe_top=True
    tagged = compute_cloud_tags(synthetic_pool)
    by_id = {c["candidate_id"]: c for c in tagged}
    assert by_id["c5"]["is_sharpe_top"] is True


def test_compute_cloud_tags_corner_like(synthetic_pool):
    tagged = compute_cloud_tags(synthetic_pool)
    by_id = {c["candidate_id"]: c for c in tagged}
    # c10 has maxw=0.55 > 0.50 → is_corner_like
    assert by_id["c10"]["is_corner_like"] is True
    # c5 has maxw=0.18, hhi=0.14 → not corner
    assert by_id["c5"]["is_corner_like"] is False


def test_compute_cloud_tags_batch_unknown_vs_false(synthetic_pool):
    tagged = compute_cloud_tags(synthetic_pool, batch_signals=None)
    assert all(c["has_fallback"] is None for c in tagged)
    assert all(c["has_universe_warning"] is None for c in tagged)


def test_compute_cloud_tags_batch_signals_applied(synthetic_pool):
    batch = {"c5": {"has_fallback": True, "has_universe_warning": False, "universe_warn_assets": ""}}
    tagged = compute_cloud_tags(synthetic_pool, batch_signals=batch)
    by_id = {c["candidate_id"]: c for c in tagged}
    assert by_id["c5"]["has_fallback"] is True
    assert by_id["c1"]["has_fallback"] is None  # not in batch → unknown
    assert "fallback_EXCLUDE" in by_id["c5"]["cloud_labels"].split(",")


def test_compute_cloud_tags_warn_label_present(synthetic_pool):
    tagged = compute_cloud_tags(synthetic_pool)
    # c10 is corner_like → corner_like (informational, no WARN suffix per
    # 2026-05-15 policy) should be in labels
    by_id = {c["candidate_id"]: c for c in tagged}
    assert "corner_like" in by_id["c10"]["cloud_labels"].split(",")


# ---------- select_in_polygon ----------


def test_select_in_polygon_with_filter(synthetic_pool):
    tagged = compute_cloud_tags(synthetic_pool)
    # Polygon covering volatility 0.10-0.16, expected_return 0.07-0.13
    poly = [[0.10, 0.06], [0.16, 0.06], [0.16, 0.14], [0.10, 0.14]]
    out = select_in_polygon(
        tagged, poly,
        x_metric="volatility",
        y_metric="expected_return",
        active_filters={"feasibility_status": "feasible"},
    )
    assert len(out) == len(tagged)  # all are in range and feasible


def test_select_in_polygon_excludes_infeasible(synthetic_pool):
    # Mark one candidate infeasible
    pool = list(synthetic_pool)
    pool.append(_mk_cand("c_inf", 0.55, 0.10, 0.13, 0.20, 0.22, feasibility="degenerate"))
    tagged = compute_cloud_tags(pool)
    poly = [[0.10, 0.06], [0.16, 0.06], [0.16, 0.14], [0.10, 0.14]]
    out = select_in_polygon(
        tagged, poly,
        x_metric="volatility", y_metric="expected_return",
        active_filters={"feasibility_status": "feasible"},
    )
    ids = {c["candidate_id"] for c in out}
    assert "c_inf" not in ids


def test_select_in_polygon_invalid_metric(synthetic_pool):
    tagged = compute_cloud_tags(synthetic_pool)
    poly = [[0.10, 0.06], [0.16, 0.06], [0.16, 0.14], [0.10, 0.14]]
    with pytest.raises(SelectionConfigError):
        select_in_polygon(
            tagged, poly, x_metric="bogus_metric", y_metric="expected_return",
        )


# ---------- post-selection rules ----------


def test_apply_top_sharpe(synthetic_pool):
    tagged = compute_cloud_tags(synthetic_pool)
    out = apply_post_selection_rule(tagged, "top_sharpe")
    assert len(out) == 1
    assert out[0]["candidate_id"] == "c5"  # sharpe=0.70 is max


def test_apply_min_hhi(synthetic_pool):
    tagged = compute_cloud_tags(synthetic_pool)
    out = apply_post_selection_rule(tagged, "min_hhi")
    assert len(out) == 1
    assert out[0]["candidate_id"] == "c5"  # hhi=0.14 is min


def test_apply_top_n_by_metric(synthetic_pool):
    tagged = compute_cloud_tags(synthetic_pool)
    out = apply_post_selection_rule(tagged, "top_n_by_metric", {"metric": "sharpe", "n": 3})
    ids = [c["candidate_id"] for c in out]
    assert ids == ["c5", "c7", "c3"]  # 0.70, 0.65, 0.60


def test_apply_all(synthetic_pool):
    tagged = compute_cloud_tags(synthetic_pool)
    out = apply_post_selection_rule(tagged, "all")
    assert len(out) == len(tagged)


def test_apply_representative_3_distinct(synthetic_pool):
    tagged = compute_cloud_tags(synthetic_pool)
    out = apply_post_selection_rule(tagged, "representative_3")
    ids = [c["candidate_id"] for c in out]
    assert len(set(ids)) == 3  # all distinct
    # First axis = max sharpe → c5
    assert ids[0] == "c5"


def test_apply_unknown_rule(synthetic_pool):
    with pytest.raises(SelectionConfigError):
        apply_post_selection_rule(synthetic_pool, "bogus_rule")


# ---------- build_export ----------


def _kwargs_base(pool):
    tagged = compute_cloud_tags(pool)
    return {
        "candidates_with_tags": tagged,
        "opportunity_set_path": "/tmp/opp.json",
        "opportunity_set_sha256": "0" * 64,
        "polygon_points": [[0.10, 0.06], [0.16, 0.06], [0.16, 0.14], [0.10, 0.14]],
        "x_metric": "volatility",
        "y_metric": "expected_return",
        "active_overlays": ["is_sharpe_top"],
        "active_filters": {"feasibility_status": "feasible"},
        "selection_mode": "lasso",
        "post_selection_rule": "top_sharpe",
        "post_selection_params": None,
        "selected_by": "tester_alice",
        "selection_reason": "unit test",
        "now": dt.datetime(2026, 5, 14, 10, 0, 0, tzinfo=dt.timezone.utc),
        "selection_id": "lasso_fixed_id",
    }


def test_build_export_invariants_locked(synthetic_pool):
    kw = _kwargs_base(synthetic_pool)
    export = build_export(**kw)
    assert export["is_production_selection"] is False
    assert export["dry_run_only"] is True
    assert export["permanent_invariants"]["implementation_ready"] is False
    assert export["permanent_invariants"]["production_applied"] is False
    assert export["permanent_invariants"]["phase_f_entered"] is False
    assert export["schema_version"] == SCHEMA_VERSION


def test_build_export_warning_propagation(synthetic_pool):
    # Polygon catches c10 (corner_like). Per 2026-05-15 policy corner_like
    # is informational (no WARN suffix), so it must NOT appear in
    # warning_labels. We assert c10 selection and the absence of the old WARN.
    kw = _kwargs_base(synthetic_pool)
    kw["polygon_points"] = [[0.10, 0.06], [0.17, 0.06], [0.17, 0.14], [0.10, 0.14]]
    kw["post_selection_rule"] = "all"
    export = build_export(**kw)
    # c10 should be in selected_before_rule (volatility=0.145 inside, er=0.085 inside)
    assert "c10" in export["selected_candidate_ids_before_rule"]
    assert "corner_like_WARN" not in export["warning_labels"]
    assert "corner_like" not in export["warning_labels"]  # neutral, never a WARN


def test_build_export_selected_by_forbidden_substring(synthetic_pool):
    kw = _kwargs_base(synthetic_pool)
    for bad in ["automated_recommender", "r1f1_smoke_test", "smoke_run"]:
        kw["selected_by"] = bad
        with pytest.raises(SelectionConfigError, match="forbidden"):
            build_export(**kw)


def test_build_export_selected_by_empty_rejected(synthetic_pool):
    kw = _kwargs_base(synthetic_pool)
    kw["selected_by"] = ""
    with pytest.raises(SelectionConfigError):
        build_export(**kw)


def test_build_export_manual_candidate_pick(synthetic_pool):
    kw = _kwargs_base(synthetic_pool)
    kw["selection_mode"] = "manual_candidate_pick"
    kw["active_filters"] = {"manual_ids": ["c1", "c5"]}
    kw["post_selection_rule"] = "all"
    export = build_export(**kw)
    assert set(export["selected_candidate_ids_before_rule"]) == {"c1", "c5"}


def test_build_export_cloud_click(synthetic_pool):
    kw = _kwargs_base(synthetic_pool)
    kw["selection_mode"] = "cloud_click"
    kw["active_overlays"] = ["is_sharpe_top"]
    kw["active_filters"] = {"feasibility_status": "feasible"}
    kw["post_selection_rule"] = "all"
    export = build_export(**kw)
    # Top 10% Sharpe in 10-cand pool = 1 → c5
    assert export["selected_candidate_ids_before_rule"] == ["c5"]


# ---------- yaml conversion ----------


def test_to_r1f1_yaml_single_pick_structure(synthetic_pool):
    kw = _kwargs_base(synthetic_pool)
    export = build_export(**kw)
    yaml_text = to_r1f1_yaml(
        export,
        portfolio_type="etf",
        source_review_packet_path="scratch/review_packet.md",
        source_review_packet_sha256="a" * 64,
    )
    assert "schema_version: r1f1.1" in yaml_text
    # Top-level key must be `manager_selection:` (R-1F.1 CLI expects this).
    assert "manager_selection:" in yaml_text
    assert "selection_input:" not in yaml_text
    assert "candidate_id: \"c5\"" in yaml_text  # top_sharpe = c5
    assert "production_applied: false" in yaml_text
    assert "phase_f_entry_status:" in yaml_text
    assert "manager_signoff_recorded: false" in yaml_text
    assert "source_lasso_selection_id: \"lasso_fixed_id\"" in yaml_text
    # Path convention note present in header
    assert "Path convention:" in yaml_text


def test_to_r1f1_yaml_empty_review_packet_path_rejected(synthetic_pool):
    kw = _kwargs_base(synthetic_pool)
    export = build_export(**kw)
    with pytest.raises(SelectionConfigError, match="V-11.*path is required"):
        to_r1f1_yaml(
            export,
            portfolio_type="etf",
            source_review_packet_path="",
            source_review_packet_sha256="a" * 64,
        )


def test_to_r1f1_yaml_empty_review_packet_sha256_rejected(synthetic_pool):
    kw = _kwargs_base(synthetic_pool)
    export = build_export(**kw)
    with pytest.raises(SelectionConfigError, match="V-11.*sha256 is required"):
        to_r1f1_yaml(
            export,
            portfolio_type="etf",
            source_review_packet_path="scratch/review_packet.md",
            source_review_packet_sha256="",
        )


def test_to_r1f1_yaml_multi_pick_rejected(synthetic_pool):
    kw = _kwargs_base(synthetic_pool)
    kw["post_selection_rule"] = "top_n_by_metric"
    kw["post_selection_params"] = {"metric": "sharpe", "n": 3}
    export = build_export(**kw)
    with pytest.raises(SelectionConfigError, match="exactly 1"):
        to_r1f1_yaml(
            export,
            portfolio_type="etf",
            source_review_packet_path="scratch/review_packet.md",
            source_review_packet_sha256="a" * 64,
        )


def test_to_r1f1_yaml_invalid_portfolio_type(synthetic_pool):
    kw = _kwargs_base(synthetic_pool)
    export = build_export(**kw)
    with pytest.raises(SelectionConfigError):
        to_r1f1_yaml(
            export,
            portfolio_type="bogus",
            source_review_packet_path="scratch/review_packet.md",
            source_review_packet_sha256="a" * 64,
        )
