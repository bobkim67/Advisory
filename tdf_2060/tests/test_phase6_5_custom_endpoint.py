"""Phase 6.5 POST /api/r-track/opportunity-set/custom 통합 테스트.

좌측 자산 panel 의 실행 버튼이 호출하는 endpoint. 검증 범위:
- default 호출 → 200 OK, candidate 수 정확
- 자유 bucket (equity_total=0.7) → 모든 candidate eq 합 일치
- asset_constraints → cap/floor 적용
- selected_assets subset → 출력 자산 set
- invalid input (bucket sum != 1) → 400
- invalid asset key → 400
- 동일 입력 두 번 호출 → 캐시 (동일 응답)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)

ENGINE_ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_REL = "out/baseline_regen_20260527/portfolio_etf_20260527.json"
PORTFOLIO_ABS = ENGINE_ROOT / PORTFOLIO_REL


pytestmark = pytest.mark.skipif(
    not PORTFOLIO_ABS.exists(),
    reason="10-asset baseline portfolio not present",
)


SMALL_N = 200  # 테스트 속도 위해 작게


def _post(body: dict):
    return client.post("/api/r-track/opportunity-set/custom", json=body)


# ---------------------------------------------------------------------------
# 1. Default 호출
# ---------------------------------------------------------------------------


def test_custom_default_returns_200_with_candidates():
    r = _post({
        "portfolio_source": PORTFOLIO_REL,
        "n_candidates": SMALL_N,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["candidate_count"] == SMALL_N
    assert len(data["candidates"]) == SMALL_N
    assert data["equity_bucket_total"] == 0.80
    assert data["fixed_income_bucket_total"] == 0.20
    assert data["sampling_warning"] is None
    assert data["is_production_selection"] is False
    assert data["dry_run_only"] is True


def test_custom_default_bucket_constraint_hard():
    r = _post({
        "portfolio_source": PORTFOLIO_REL,
        "n_candidates": SMALL_N,
        "include_weights": True,
    })
    assert r.status_code == 200
    data = r.json()
    for c in data["candidates"]:
        assert abs(c["equity_weight"] - 0.80) < 1e-9
        assert abs(c["fixed_income_weight"] - 0.20) < 1e-9


def test_custom_default_includes_weights_and_asset_meta():
    r = _post({
        "portfolio_source": PORTFOLIO_REL,
        "n_candidates": 50,
        "include_weights": True,
    })
    data = r.json()
    assert data["include_weights"] is True
    assert data["asset_keys"] is not None and len(data["asset_keys"]) == 10
    assert "kr_equity" in data["asset_keys"]
    assert data["asset_labels"] is not None
    assert data["asset_buckets"]["kr_equity"] == "equity"
    assert data["asset_buckets"]["us_high_yield"] == "fixed_income"


# ---------------------------------------------------------------------------
# 2. 자유 bucket
# ---------------------------------------------------------------------------


def test_custom_free_bucket_70_30():
    r = _post({
        "portfolio_source": PORTFOLIO_REL,
        "n_candidates": SMALL_N,
        "equity_total": 0.70,
        "fixed_income_total": 0.30,
        "include_weights": True,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["equity_bucket_total"] == 0.70
    assert data["fixed_income_bucket_total"] == 0.30
    for c in data["candidates"]:
        assert abs(c["equity_weight"] - 0.70) < 1e-9


def test_custom_invalid_bucket_sum_returns_400():
    r = _post({
        "portfolio_source": PORTFOLIO_REL,
        "n_candidates": 50,
        "equity_total": 0.70,
        "fixed_income_total": 0.25,
    })
    assert r.status_code == 400
    assert "must equal 1.0" in r.text


# ---------------------------------------------------------------------------
# 3. asset_constraints
# ---------------------------------------------------------------------------


def test_custom_asset_cap_enforced():
    r = _post({
        "portfolio_source": PORTFOLIO_REL,
        "n_candidates": SMALL_N,
        "include_weights": True,
        "asset_constraints": {"kr_equity": [0.0, 0.10]},
    })
    assert r.status_code == 200, r.text
    for c in r.json()["candidates"]:
        assert c["weights"]["kr_equity"] <= 0.10 + 1e-12


def test_custom_bucket_infeasible_returns_400():
    eq_assets = [
        "kr_equity", "us_growth_equity", "us_value_equity",
        "dm_ex_us_equity", "em_equity", "gold",
    ]
    r = _post({
        "portfolio_source": PORTFOLIO_REL,
        "n_candidates": 50,
        "asset_constraints": {k: [0.0, 0.10] for k in eq_assets},
    })
    assert r.status_code == 400
    assert "equity bucket infeasible" in r.text


# ---------------------------------------------------------------------------
# 4. selected_assets subset
# ---------------------------------------------------------------------------


def test_custom_selected_assets_subset():
    subset = [
        "kr_equity", "us_growth_equity", "us_value_equity",  # 3 eq
        "us_aggregate_bond", "us_high_yield",                # 2 fi
    ]
    r = _post({
        "portfolio_source": PORTFOLIO_REL,
        "n_candidates": SMALL_N,
        "include_weights": True,
        "selected_assets": subset,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert set(data["asset_keys"]) == set(subset)
    for c in data["candidates"]:
        assert set(c["weights"].keys()) == set(subset)


def test_custom_unknown_asset_returns_400():
    r = _post({
        "portfolio_source": PORTFOLIO_REL,
        "n_candidates": 50,
        "selected_assets": ["kr_equity", "no_such_asset"],
    })
    assert r.status_code == 400
    assert "unknown keys" in r.text


# ---------------------------------------------------------------------------
# 5. Edge cases
# ---------------------------------------------------------------------------


def test_custom_missing_portfolio_returns_404():
    r = _post({
        "portfolio_source": "out/does_not_exist.json",
        "n_candidates": 50,
    })
    assert r.status_code == 404


def test_custom_n_candidates_validation():
    # n_candidates < 10 → 422 (pydantic validation)
    r = _post({
        "portfolio_source": PORTFOLIO_REL,
        "n_candidates": 5,
    })
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 6. Cache
# ---------------------------------------------------------------------------


def test_custom_cache_returns_identical_response():
    body = {
        "portfolio_source": PORTFOLIO_REL,
        "n_candidates": 100,
        "random_seed": 42,
        "include_weights": True,
    }
    r1 = _post(body)
    r2 = _post(body)
    assert r1.status_code == 200 and r2.status_code == 200
    # 동일 입력 → 동일 응답 (cache 또는 deterministic 재계산)
    assert r1.json() == r2.json()
