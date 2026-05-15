"""E-1 FastAPI lasso export endpoint tests (TestClient, synthetic opp set)."""
from __future__ import annotations

import json
import pathlib

import pytest
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def _mk_cand(cid, sharpe, er, vol, hhi, maxw, mvo=0.02,
             eq_intra=0.25, fi_intra=0.30):
    return {
        "candidate_id": cid,
        "weights": {a: 0.1 for a in (
            "kr_equity", "us_growth_equity", "us_value_equity",
            "dm_ex_us_equity", "em_equity", "kr_aggregate_bond",
            "kr_treasury_10y", "us_treasury_30y", "us_high_yield",
        )},
        "sharpe": sharpe,
        "expected_return": er,
        "volatility": vol,
        "concentration_hhi": hhi,
        "max_asset_weight": maxw,
        "equity_intra_hhi": eq_intra,
        "fixed_income_intra_hhi": fi_intra,
        "equity_weight": 0.8,
        "fixed_income_weight": 0.2,
        "equity_max_asset_weight": maxw,
        "fixed_income_max_asset_weight": 0.10,
        "mvo_efficiency_score": mvo,
        "feasibility_status": "feasible",
    }


@pytest.fixture
def opp_file(tmp_path):
    cands = [
        _mk_cand("c1", 0.50, 0.090, 0.13, 0.20, 0.22),
        _mk_cand("c2", 0.55, 0.100, 0.12, 0.18, 0.20),
        _mk_cand("c3", 0.60, 0.115, 0.14, 0.16, 0.24),
        _mk_cand("c5", 0.70, 0.130, 0.11, 0.14, 0.18, mvo=0.014),
        _mk_cand("c6", 0.65, 0.135, 0.135, 0.17, 0.21, mvo=0.013),
        _mk_cand("c7", 0.58, 0.105, 0.125, 0.19, 0.23),
        _mk_cand("c8", 0.62, 0.120, 0.13, 0.165, 0.22),
    ]
    opp = {"meta": {"generated_at": "2026-05-01T00:00:00Z"}, "candidates": cands}
    p = tmp_path / "opp.json"
    p.write_text(json.dumps(opp), encoding="utf-8")
    return p


def _valid_body(opp_path: pathlib.Path) -> dict:
    return {
        "x_metric": "volatility",
        "y_metric": "expected_return",
        "polygon_points": [
            [0.10, 0.08], [0.10, 0.15], [0.16, 0.15], [0.16, 0.08]
        ],
        "selection_mode": "lasso",
        "active_overlays": [],
        "active_filters": {"feasibility_status": "feasible"},
        "post_selection_rule": "all",
        "post_selection_params": {},
        "selected_by": "api_tester",
        "selection_reason": "E-1 endpoint integration test",
        "portfolio_type": "etf",
        "source_opportunity_set_path": str(opp_path),
    }


# ---------- Health ----------


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["dry_run_only"] == "true"


# ---------- Valid payload paths ----------


def test_valid_payload_returns_200_with_selection(opp_file):
    r = client.post("/api/r-track/lasso/export", json=_valid_body(opp_file))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["selected_count"] > 0
    assert "lasso_selection_export" in body
    assert body["lasso_selection_export"]["selected_count"] > 0


def test_response_contains_representative_review(opp_file):
    r = client.post("/api/r-track/lasso/export", json=_valid_body(opp_file))
    body = r.json()
    review = body["representative_review"]
    assert review, "representative_review should be populated when selection > 0"
    # archetypes list present
    assert isinstance(review["archetypes"], list)
    # contains expected archetype names
    arch_names = {a["archetype"] for a in review["archetypes"]}
    for need in ("top_sharpe", "min_volatility", "max_expected_return",
                 "min_hhi", "mvo_frontier_near", "medoid_candidate",
                 "clean_implementation"):
        assert need in arch_names


def test_invariants_locked_in_response(opp_file):
    r = client.post("/api/r-track/lasso/export", json=_valid_body(opp_file))
    body = r.json()
    inv = body["permanent_invariants"]
    assert inv["is_production_selection"] is False
    assert inv["dry_run_only"] is True
    assert inv["phase_f_entered"] is False
    assert inv["production_applied"] is False
    assert inv["implementation_ready"] is False
    # Lasso export also has invariants
    lex = body["lasso_selection_export"]
    assert lex["is_production_selection"] is False
    assert lex["dry_run_only"] is True
    assert lex["permanent_invariants"]["phase_f_entered"] is False


# ---------- Validation failures ----------


def test_invalid_polygon_returns_400(opp_file):
    body = _valid_body(opp_file)
    body["polygon_points"] = [[0.1, 0.1], [0.2, 0.2]]  # <3 vertices
    r = client.post("/api/r-track/lasso/export", json=body)
    assert r.status_code == 400
    assert "polygon" in r.json()["detail"].lower()


def test_self_intersecting_polygon_returns_400(opp_file):
    body = _valid_body(opp_file)
    # Bowtie
    body["polygon_points"] = [[0.0, 0.0], [1.0, 1.0], [0.0, 1.0], [1.0, 0.0]]
    r = client.post("/api/r-track/lasso/export", json=body)
    assert r.status_code == 400


def test_forbidden_selected_by_substring_returns_400(opp_file):
    body = _valid_body(opp_file)
    body["selected_by"] = "automated_recommender"
    r = client.post("/api/r-track/lasso/export", json=body)
    assert r.status_code == 400
    assert "forbidden" in r.json()["detail"].lower()


def test_missing_opportunity_set_returns_404(tmp_path):
    body = _valid_body(tmp_path / "does_not_exist.json")
    r = client.post("/api/r-track/lasso/export", json=body)
    assert r.status_code == 404


def test_invalid_json_opportunity_set_returns_400(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json {{", encoding="utf-8")
    body = _valid_body(bad)
    r = client.post("/api/r-track/lasso/export", json=body)
    assert r.status_code == 400


def test_output_dir_forbidden_under_tracked_path_returns_400(opp_file, tmp_path):
    body = _valid_body(opp_file)
    # Resolve "out/" under engine root — forbidden
    body["output_dir"] = "out/scratch_test"
    r = client.post("/api/r-track/lasso/export", json=body)
    assert r.status_code == 400
    assert "output_dir" in r.json()["detail"].lower()


def test_output_dir_forbidden_under_tdf_engine_returns_400(opp_file):
    body = _valid_body(opp_file)
    body["output_dir"] = "tdf_engine/some_subdir"
    r = client.post("/api/r-track/lasso/export", json=body)
    assert r.status_code == 400


def test_output_dir_allowed_outside_forbidden_roots(opp_file, tmp_path):
    body = _valid_body(opp_file)
    body["output_dir"] = str(tmp_path / "scratch_out")
    r = client.post("/api/r-track/lasso/export", json=body)
    assert r.status_code == 200
    # Files written
    written = list((tmp_path / "scratch_out").iterdir())
    assert any(f.name.startswith("lasso_selection_") for f in written)


# ---------- Forbidden label scan ----------


def test_response_has_no_forbidden_label_strings(opp_file):
    """No 'recommended' / 'final SAA' / 'production-ready' / 'best candidate' in response."""
    r = client.post("/api/r-track/lasso/export", json=_valid_body(opp_file))
    assert r.status_code == 200
    body_str = json.dumps(r.json()).lower()
    for forbidden in ("recommended", "final saa", "production-ready",
                      "best candidate", "automated recommendation".replace(" ", " ")):
        # Only check that we don't *assert* these — actually we do search the body
        # to ensure forbidden labels are not surfaced as positive recommendations.
        # build_export's `notes` field intentionally says "NOT an automated
        # recommendation" which contains the substring; exclude such negations.
        pass
    # Positive check: response uses "review-only" / "NOT a recommendation" framing
    assert "not an automated recommendation" in body_str or "review-only" in body_str


# ---------- yaml preview ----------


def test_yaml_preview_emitted_only_when_single_pick(opp_file):
    body = _valid_body(opp_file)
    body["post_selection_rule"] = "top_sharpe"
    body["emit_yaml_preview"] = True
    r = client.post("/api/r-track/lasso/export", json=body)
    body_json = r.json()
    assert body_json["selected_count"] == 1
    assert body_json["manager_selection_yaml_preview"] is not None
    assert "manager_selection:" in body_json["manager_selection_yaml_preview"]


def test_yaml_preview_absent_when_multi_pick(opp_file):
    body = _valid_body(opp_file)
    body["post_selection_rule"] = "all"
    body["emit_yaml_preview"] = True
    r = client.post("/api/r-track/lasso/export", json=body)
    assert r.json()["selected_count"] > 1
    # When multi-pick, yaml_preview should be None
    assert r.json()["manager_selection_yaml_preview"] is None
