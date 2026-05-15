"""D-11 GET /api/r-track/opportunity-set/scatter tests."""
from __future__ import annotations

import hashlib
import json

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


# ---------- Happy path ----------


def test_scatter_returns_200_with_all_candidates(opp_file):
    r = client.get(
        "/api/r-track/opportunity-set/scatter",
        params={"source_opportunity_set_path": str(opp_file)},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["candidate_count"] == 7
    assert len(body["candidates"]) == 7
    assert {c["candidate_id"] for c in body["candidates"]} == {
        "c1", "c2", "c3", "c5", "c6", "c7", "c8"
    }


def test_scatter_schema_version_and_invariants(opp_file):
    r = client.get(
        "/api/r-track/opportunity-set/scatter",
        params={"source_opportunity_set_path": str(opp_file)},
    )
    body = r.json()
    assert body["schema_version"] == "r_track_2_scatter.1"
    assert body["is_production_selection"] is False
    assert body["dry_run_only"] is True


def test_scatter_sha256_matches_file(opp_file):
    r = client.get(
        "/api/r-track/opportunity-set/scatter",
        params={"source_opportunity_set_path": str(opp_file)},
    )
    expected = hashlib.sha256(opp_file.read_bytes()).hexdigest()
    assert r.json()["source_opportunity_set_sha256"] == expected


def test_scatter_candidate_fields_present(opp_file):
    r = client.get(
        "/api/r-track/opportunity-set/scatter",
        params={"source_opportunity_set_path": str(opp_file)},
    )
    sample = r.json()["candidates"][0]
    needed = {
        "candidate_id", "volatility", "expected_return", "sharpe",
        "concentration_hhi", "max_asset_weight", "mvo_efficiency_score",
        "feasibility_status", "overlap_score", "cloud_labels",
        "has_fallback", "has_universe_warning",
    }
    assert needed.issubset(sample.keys())


def test_scatter_has_fallback_null_when_no_batch_dir(opp_file):
    r = client.get(
        "/api/r-track/opportunity-set/scatter",
        params={"source_opportunity_set_path": str(opp_file)},
    )
    for c in r.json()["candidates"]:
        assert c["has_fallback"] is None
        assert c["has_universe_warning"] is None


def test_scatter_coordinates_match_input(opp_file):
    """Server-projected x/y must match opportunity-set source values."""
    raw = json.loads(opp_file.read_text(encoding="utf-8"))
    src_by_id = {c["candidate_id"]: c for c in raw["candidates"]}
    r = client.get(
        "/api/r-track/opportunity-set/scatter",
        params={"source_opportunity_set_path": str(opp_file)},
    )
    for c in r.json()["candidates"]:
        s = src_by_id[c["candidate_id"]]
        assert c["volatility"] == pytest.approx(s["volatility"])
        assert c["expected_return"] == pytest.approx(s["expected_return"])
        assert c["sharpe"] == pytest.approx(s["sharpe"])


# ---------- Error paths ----------


def test_scatter_missing_path_returns_404(tmp_path):
    r = client.get(
        "/api/r-track/opportunity-set/scatter",
        params={"source_opportunity_set_path": str(tmp_path / "missing.json")},
    )
    assert r.status_code == 404


def test_scatter_invalid_json_returns_400(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json {{", encoding="utf-8")
    r = client.get(
        "/api/r-track/opportunity-set/scatter",
        params={"source_opportunity_set_path": str(bad)},
    )
    assert r.status_code == 400


def test_scatter_empty_candidates_returns_400(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"meta": {}, "candidates": []}), encoding="utf-8")
    r = client.get(
        "/api/r-track/opportunity-set/scatter",
        params={"source_opportunity_set_path": str(empty)},
    )
    assert r.status_code == 400


def test_scatter_missing_path_param_returns_422():
    """source_opportunity_set_path is required — FastAPI validation."""
    r = client.get("/api/r-track/opportunity-set/scatter")
    assert r.status_code == 422


def test_scatter_path_is_directory_returns_400(tmp_path):
    r = client.get(
        "/api/r-track/opportunity-set/scatter",
        params={"source_opportunity_set_path": str(tmp_path)},
    )
    assert r.status_code == 400
