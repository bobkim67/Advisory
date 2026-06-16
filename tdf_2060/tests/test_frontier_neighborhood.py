"""Frontier Neighborhood Explorer — acceptance tests (spec §10).

엔진 모듈은 합성 μ/Σ 로 검증 (DB/portfolio 불필요). 추가로 endpoint smoke 는
file-mode portfolio 가 있을 때만 실행.

검증 (§10):
  1. 모든 frontier point weight sum = 1
  2. 모든 candidate weight sum = 1
  3. 모든 candidate weight >= 0
  4. 모든 candidate US HY <= 7%
  5. 모든 candidate return 이 target ± return_tolerance 안
  6. 모든 candidate vol 이 frontier_min_volatility + vol_gap 안
  7. allocation_distance 가 frontier weights 와 일치
  8. frontier point 와 candidate 가 동일 μ/Σ 사용
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import app
from tdf_engine.optimization.frontier_neighborhood import (
    CONSTRAINT_SET,
    build_frontier_neighborhood,
    generate_random_cloud,
)

# --------------------------------------------------------------------------
# 합성 CMA (10 자산) — 결정적, 외부 의존 없음
# --------------------------------------------------------------------------
KEYS = [
    "kr_equity", "us_growth_equity", "us_value_equity", "dm_ex_us_equity",
    "em_equity", "gold", "kr_aggregate_bond", "kr_treasury_10y",
    "us_aggregate_bond", "us_high_yield",
]
MU = np.array([0.057, 0.120, 0.085, 0.072, 0.094, 0.105, 0.038, 0.041, 0.045, 0.063])
_SIG = np.array([0.16, 0.19, 0.15, 0.15, 0.21, 0.17, 0.05, 0.06, 0.06, 0.10])
_CORR = np.full((10, 10), 0.25)
np.fill_diagonal(_CORR, 1.0)
COV = np.outer(_SIG, _SIG) * _CORR

HY_CAP = 0.07
RETURN_TOL = 5.0  # bps
VOL_GAPS = (10, 25, 50, 100)


@pytest.fixture(scope="module")
def result():
    return build_frontier_neighborhood(
        KEYS, MU, COV,
        hy_cap=HY_CAP, risk_free_rate=0.025,
        target_returns=[0.06, 0.07, 0.08],
        vol_gaps_bps=VOL_GAPS, return_tolerance_bps=RETURN_TOL,
        n_directions=60, steps_per_direction=2, random_seed=42, method_b=True,
    )


def _frontier_weights(result, fid):
    fp = next(f for f in result["frontier_points"] if f["frontier_id"] == fid)
    return fp["weights"]


def test_generates_points_and_candidates(result):
    optimal = [f for f in result["frontier_points"] if f["optimizer_status"] == "optimal"]
    assert len(optimal) == 3
    assert len(result["candidates"]) > 0
    methods = {c["generation_method"] for c in result["candidates"]}
    assert "local_feasible_perturbation" in methods
    assert {"asset_weight_maximizer", "asset_weight_minimizer"} & methods


def test_constraint_set_metadata(result):
    assert result["constraint_set"] == CONSTRAINT_SET == "frontier_relaxed_hy_cap_only"
    assert set(result["included_constraints"]) == {
        "long_only", "sum_to_one", "target_return", "us_hy_max_7pct"
    }
    assert "equity_bucket_80_20" in result["excluded_constraints"]
    assert "equity_cap" in result["excluded_constraints"]


# §10.1
def test_frontier_point_weight_sum_one(result):
    for fp in result["frontier_points"]:
        if fp["optimizer_status"] != "optimal":
            continue
        assert abs(sum(fp["weights"].values()) - 1.0) < 1e-6


# §10.2
def test_candidate_weight_sum_one(result):
    for c in result["candidates"]:
        assert abs(sum(c["weights"].values()) - 1.0) < 1e-5


# §10.3
def test_candidate_weights_nonneg(result):
    for c in result["candidates"]:
        assert min(c["weights"].values()) >= -1e-9


# §10.4
def test_candidate_hy_cap(result):
    for c in result["candidates"]:
        assert c["weights"]["us_high_yield"] <= HY_CAP + 1e-6


# §10.5
def test_candidate_return_within_tolerance(result):
    tol = RETURN_TOL / 10000.0
    for c in result["candidates"]:
        assert abs(c["candidate_return"] - c["target_return"]) <= tol + 1e-4


# §10.6
def test_candidate_vol_within_gap(result):
    tol = RETURN_TOL / 10000.0
    for c in result["candidates"]:
        cap = c["frontier_min_volatility"] + c["vol_gap_bucket"] / 10000.0
        assert c["candidate_volatility"] <= cap + 1e-4
        # method B 는 return tolerance(±tol) 를 허용하므로 target 보다 살짝 낮은
        # return slice 의 더 낮은 min-var 점이 frontier_min_vol 아래로 약간 내려갈 수
        # 있다. 단 그 폭은 작아야 함 (tolerance 내 frontier 곡률 수준).
        assert c["candidate_volatility"] >= c["frontier_min_volatility"] - (tol + 1e-3)


# §10.7
def test_allocation_distance_matches_frontier(result):
    for c in result["candidates"]:
        fw = _frontier_weights(result, c["frontier_id"])
        diffs = [c["weights"][k] - fw[k] for k in KEYS]
        l1 = sum(abs(d) for d in diffs)
        l2 = math.sqrt(sum(d * d for d in diffs))
        assert abs(l1 - c["allocation_distance_l1_from_frontier"]) < 1e-9
        assert abs(l2 - c["allocation_distance_l2_from_frontier"]) < 1e-9


# §10.8 — frontier point 와 candidate 가 동일 μ/Σ 사용
def test_same_mu_sigma_for_frontier_and_candidates(result):
    key_idx = {k: i for i, k in enumerate(KEYS)}
    for c in result["candidates"]:
        w = np.array([c["weights"][k] for k in KEYS])
        # 동일 μ 로 계산한 return / 동일 Σ 로 계산한 vol 이 저장값과 일치
        ret = float(w @ MU)
        vol = math.sqrt(max(float(w @ COV @ w), 0.0))
        assert abs(ret - c["candidate_return"]) < 1e-9
        assert abs(vol - c["candidate_volatility"]) < 1e-9
        # candidate 의 frontier_min_volatility 가 해당 frontier point 와 동일
        fp = next(f for f in result["frontier_points"] if f["frontier_id"] == c["frontier_id"])
        assert abs(fp["min_volatility"] - c["frontier_min_volatility"]) < 1e-12
        # frontier point vol 도 동일 Σ 로 재계산 일치
        fw = np.array([fp["weights"][k] for k in KEYS])
        assert abs(math.sqrt(max(float(fw @ COV @ fw), 0.0)) - fp["min_volatility"]) < 1e-9


def test_summary_structure(result):
    s = next(s for s in result["summary"] if abs(s["target_return"] - 0.08) < 1e-9)
    for gap in VOL_GAPS:
        assert str(gap) in s["n_candidates_by_vol_gap"]
        assert str(gap) in s["asset_weight_ranges_by_vol_gap"]
    # cumulative: 큰 gap 이 작은 gap 후보를 포함 (monotone non-decreasing)
    counts = [s["n_candidates_by_vol_gap"][str(g)] for g in VOL_GAPS]
    assert counts == sorted(counts)
    # asset weight range frontier 값이 frontier point 와 일치
    fw = _frontier_weights(result, s["frontier_id"])
    rng100 = s["asset_weight_ranges_by_vol_gap"]["100"]
    for k in KEYS:
        assert abs(rng100[k]["frontier"] - fw[k]) < 1e-9
        assert rng100[k]["min"] <= rng100[k]["frontier"] + 1e-9
        assert rng100[k]["max"] >= rng100[k]["frontier"] - 1e-9


# --------------------------------------------------------------------------
# Random Cloud + EF Overlay mode
# --------------------------------------------------------------------------
def test_random_cloud_invariants():
    hy_idx = KEYS.index("us_high_yield")
    cloud = generate_random_cloud(
        KEYS, MU, COV, hy_idx=hy_idx, hy_cap=HY_CAP, n_samples=500,
        rf=0.025, alpha=1.0, random_seed=42,
    )
    assert len(cloud) == 500
    for c in cloud:
        w = list(c["weights"].values())
        assert abs(sum(w) - 1.0) < 1e-9          # sum-to-one
        assert min(w) >= -1e-12                   # long-only
        assert c["weights"]["us_high_yield"] <= HY_CAP + 1e-9  # HY<=cap
        assert c["source_type"] == "random_cloud"
        wa = np.array([c["weights"][k] for k in KEYS])
        assert abs(float(wa @ MU) - c["expected_return"]) < 1e-9
        assert abs(math.sqrt(max(float(wa @ COV @ wa), 0.0)) - c["volatility"]) < 1e-9


def test_build_with_random_cloud_skips_neighborhood():
    res = build_frontier_neighborhood(
        KEYS, MU, COV, hy_cap=HY_CAP, risk_free_rate=0.025,
        target_returns=[0.06, 0.08], include_neighborhood=False,
        include_random_cloud=True, n_random_samples=400, random_seed=42,
    )
    assert res["random_cloud"] is not None and len(res["random_cloud"]) == 400
    assert len(res["candidates"]) == 0  # neighborhood (method A/B) skipped
    optimal = [f for f in res["frontier_points"] if f["optimizer_status"] == "optimal"]
    assert len(optimal) == 2  # frontier point/line 은 여전히 계산 (EF overlay 용)


# 주식비중 밴드 = random cloud + EF solver 동일 제약 (사후 필터 아님).
_EQUITY_KEYS = [
    "kr_equity", "us_growth_equity", "us_value_equity",
    "dm_ex_us_equity", "em_equity", "gold",
]


def test_random_cloud_equity_band():
    eq_idx = [i for i, k in enumerate(KEYS) if k in _EQUITY_KEYS]
    cloud = generate_random_cloud(
        KEYS, MU, COV, hy_idx=KEYS.index("us_high_yield"), hy_cap=HY_CAP,
        n_samples=300, rf=0.025, equity_idx=eq_idx, equity_min=0.4, equity_max=0.6,
    )
    assert len(cloud) > 0
    for c in cloud:
        eqw = sum(c["weights"][KEYS[i]] for i in eq_idx)
        assert 0.4 - 1e-9 <= eqw <= 0.6 + 1e-9       # 밴드
        assert c["weights"]["us_high_yield"] <= HY_CAP + 1e-9
        assert abs(sum(c["weights"].values()) - 1.0) < 1e-9
        assert abs(c["equity_weight"] - eqw) < 1e-9   # 응답 equity_weight 일치


def test_frontier_band_constrained():
    res = build_frontier_neighborhood(
        KEYS, MU, COV, hy_cap=HY_CAP, risk_free_rate=0.025,
        target_returns=[0.06, 0.07, 0.08], include_neighborhood=False,
        equity_keys=_EQUITY_KEYS, equity_weight_min=0.4, equity_weight_max=0.6,
    )
    optimal = [f for f in res["frontier_points"] if f["optimizer_status"] == "optimal"]
    assert len(optimal) > 0
    for f in optimal:
        assert f["equity_weight"] is not None
        # solver 가 밴드를 강제 — 사후 필터 아님
        assert 0.4 - 5e-3 <= f["equity_weight"] <= 0.6 + 5e-3
        # 동일 μ/Σ 로 equity 합 재검증
        eqw = sum(f["weights"][KEYS[i]] for i in range(len(KEYS)) if KEYS[i] in _EQUITY_KEYS)
        assert 0.4 - 5e-3 <= eqw <= 0.6 + 5e-3
    assert res["constraint_set"] == "random_cloud_relaxed_hy_cap_equity_band"
    assert "equity_weight_band" in res["included_constraints"]


# --------------------------------------------------------------------------
# Endpoint smoke (file-mode portfolio 있을 때만)
# --------------------------------------------------------------------------
ENGINE_ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_REL = "out/file_mode_cma_20260528/portfolio_etf_20260528.json"
PORTFOLIO_ABS = ENGINE_ROOT / PORTFOLIO_REL

client = TestClient(app)

endpoint = pytest.mark.skipif(
    not PORTFOLIO_ABS.exists(), reason="file-mode portfolio not present"
)


@endpoint
def test_endpoint_default_ok():
    r = client.post(
        "/api/r-track/frontier-neighborhood",
        json={"portfolio_source": PORTFOLIO_REL, "n_directions": 40},
    )
    assert r.status_code == 200
    d = r.json()
    assert d["constraint_set"] == "frontier_relaxed_hy_cap_only"
    assert d["is_production_selection"] is False
    assert d["dry_run_only"] is True
    assert d["candidate_count"] == len(d["candidates"]) > 0
    # endpoint candidate 도 핵심 불변식 충족
    for c in d["candidates"]:
        assert abs(sum(c["weights"].values()) - 1.0) < 1e-5
        assert c["weights"]["us_high_yield"] <= 0.07 + 1e-6


@endpoint
def test_endpoint_include_weights_false_strips_weights():
    r = client.post(
        "/api/r-track/frontier-neighborhood",
        json={"portfolio_source": PORTFOLIO_REL, "n_directions": 20, "include_weights": False},
    )
    assert r.status_code == 200
    d = r.json()
    assert all(c["weights"] is None for c in d["candidates"])


@endpoint
def test_endpoint_cache_identical():
    body = {"portfolio_source": PORTFOLIO_REL, "n_directions": 30, "random_seed": 7}
    a = client.post("/api/r-track/frontier-neighborhood", json=body).json()
    b = client.post("/api/r-track/frontier-neighborhood", json=body).json()
    assert a == b


@endpoint
def test_endpoint_missing_portfolio_404():
    r = client.post(
        "/api/r-track/frontier-neighborhood",
        json={"portfolio_source": "out/does_not_exist_zzz.json"},
    )
    assert r.status_code == 404


@endpoint
def test_endpoint_random_cloud_mode():
    r = client.post(
        "/api/r-track/frontier-neighborhood",
        json={
            "portfolio_source": PORTFOLIO_REL,
            "include_neighborhood": False,
            "include_random_cloud": True,
            "n_random_samples": 500,
        },
    )
    assert r.status_code == 200
    d = r.json()
    assert d["candidate_count"] == 0  # neighborhood off
    assert d["random_cloud"] is not None and len(d["random_cloud"]) == 500
    assert len(d["frontier_points"]) > 0  # EF overlay 용 frontier 유지
    for c in d["random_cloud"]:
        assert c["source_type"] == "random_cloud"
        assert c["us_hy_weight"] <= 0.07 + 1e-9


@endpoint
def test_endpoint_empty_grid_422():
    r = client.post(
        "/api/r-track/frontier-neighborhood",
        json={
            "portfolio_source": PORTFOLIO_REL,
            "target_return_min": 0.09,
            "target_return_max": 0.05,  # max < min → empty grid
        },
    )
    assert r.status_code == 422
