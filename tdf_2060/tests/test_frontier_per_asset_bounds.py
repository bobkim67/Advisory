"""Frontier Neighborhood — per-asset floor/cap + equity_weight_keys 그룹 cap.

endpoint 레벨(file CMA, DB 불필요). EF 점·random cloud 가 제약을 지키는지 검증.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import build_app

PORT = "out/file_mode_cma_20260528/portfolio_etf_20260528.json"
EQUITY5 = ["kr_equity", "us_growth_equity", "us_value_equity", "dm_ex_us_equity", "em_equity"]


@pytest.fixture(scope="module")
def client():
    return TestClient(build_app())


def _post(client, **over):
    body = {
        "portfolio_source": PORT,
        "include_neighborhood": False,
        "include_random_cloud": True,
        "n_random_samples": 300,
        "include_weights": True,
    }
    body.update(over)
    r = client.post("/api/r-track/frontier-neighborhood", json=body)
    return r


def test_per_asset_cap_respected_on_frontier_and_cloud(client):
    r = _post(client, asset_constraints={"us_growth_equity": [0.0, 0.10]})
    assert r.status_code == 200, r.text
    j = r.json()
    assert "per_asset_floor_cap" in j["included_constraints"]
    # EF 점 (optimal) 모두 us_growth <= 10%
    for fp in j["frontier_points"]:
        if fp["optimizer_status"] == "optimal" and fp["weights"]:
            assert fp["weights"]["us_growth_equity"] <= 0.10 + 2e-3
    # random cloud 도 us_growth <= 10%
    for rc in j["random_cloud"]:
        assert rc["weights"]["us_growth_equity"] <= 0.10 + 1e-6


def test_per_asset_floor_respected_on_cloud(client):
    r = _post(client, asset_constraints={"gold": [0.05, 1.0]}, n_random_samples=200)
    assert r.status_code == 200, r.text
    for rc in r.json()["random_cloud"]:
        assert rc["weights"]["gold"] >= 0.05 - 1e-6


def test_equity_group_cap_risk_assets_80pct(client):
    # 주식+금+HY 80% 상한 (상한만; min=0)
    keys = EQUITY5 + ["gold", "us_high_yield"]
    r = _post(client, equity_weight_keys=keys, equity_weight_min=0.0, equity_weight_max=0.80)
    assert r.status_code == 200, r.text
    j = r.json()
    assert "equity_weight_band" in j["included_constraints"]
    # frontier 점의 그룹 합 <= 80%
    for fp in j["frontier_points"]:
        if fp["optimizer_status"] == "optimal" and fp["weights"]:
            grp = sum(fp["weights"][k] for k in keys)
            assert grp <= 0.80 + 5e-3
    # random cloud 의 equity_weight(그룹 합) <= 80%
    for rc in j["random_cloud"]:
        assert rc["equity_weight"] is None or rc["equity_weight"] <= 0.80 + 1e-6


def test_default_no_bounds_unchanged_label(client):
    r = _post(client)
    assert r.status_code == 200
    assert r.json()["constraint_set"] == "frontier_relaxed_hy_cap_only"
    assert "per_asset_floor_cap" not in r.json()["included_constraints"]


def test_unknown_asset_constraints_key_422(client):
    r = _post(client, asset_constraints={"bogus_asset": [0.0, 0.1]})
    assert r.status_code == 422


def test_unknown_equity_weight_keys_422(client):
    r = _post(client, equity_weight_keys=["bogus"])
    assert r.status_code == 422


def test_cap_below_floor_422(client):
    r = _post(client, asset_constraints={"gold": [0.5, 0.1]})
    assert r.status_code == 422
