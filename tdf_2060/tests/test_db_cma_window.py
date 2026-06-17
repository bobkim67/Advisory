"""db_cma_window.build_window_cma — 라이브 DB CMA window 산출 단위 테스트.

실 DB 접속 없이 in-memory fake (dict-of-DataFrame) 로 검증.
endpoint(db_window) wiring 은 _build_db_window_cma monkeypatch 로 DB 없이 검증.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from tdf_engine.optimization.db_cma_window import build_window_cma

KEYS = [
    "kr_equity", "us_growth_equity", "us_value_equity", "dm_ex_us_equity",
    "em_equity", "kr_aggregate_bond", "kr_treasury_10y", "us_aggregate_bond",
    "gold", "us_high_yield",
]


def _levels(seed: int, start: str, end: str, mu: float = 0.006, sigma: float = 0.04):
    """월말 level 시계열 (blob = 단일 숫자 str), [start, end] 월말."""
    idx = pd.date_range(start=start, end=end, freq="ME")
    rng = np.random.default_rng(seed)
    r = rng.normal(mu, sigma, len(idx))
    lv = 100.0 * np.cumprod(1.0 + r)
    return pd.DataFrame({"timestamp_observation": idx, "data": [str(v) for v in lv]})


def _fake_db(start="2014-01-31", end="2026-05-31", late_key=None, late_start="2020-01-31"):
    """각 asset_key → (dataset_id=100+i, ds=9) level. late_key 만 늦게 시작."""
    fake, mapping = {}, {}
    for i, ak in enumerate(KEYS, start=100):
        s = late_start if ak == late_key else start
        fake[(i, 9)] = _levels(seed=i, start=s, end=end)
        mapping[ak] = i
    return fake, mapping


def _cfg(mapping: dict[str, int]):
    assets = [
        {
            "asset_key": ak, "dataset_id": ds, "ticker": ak.upper(),
            "value_dataseries": 9, "fallback_dataseries": None, "currency": None,
            "frequency": "D", "required": True,
            "semantic_type": "total_return_index", "return_transform": "pct_change",
        }
        for ak, ds in mapping.items()
    ]
    return {
        "asset_rt_vol": {"lookback_years": 10, "annualization": 12},
        "corr_matrix": {"lookback_years": 10},
        "assets": assets,
    }


def _build(start, end, **kw):
    fake, mapping = _fake_db(**kw)
    return build_window_cma(KEYS, _cfg(mapping), fake, start=start, end=end)


# ── 구조 / 키 ──────────────────────────────────────────────────────────


def test_returns_all_assets_and_required_keys():
    res = _build("2016-05-31", "2026-05-31")
    assert set(res["asset_keys"]) == set(KEYS)
    for k in ("expected_returns", "volatilities", "correlation_matrix",
              "covariance_matrix", "window", "per_asset", "warnings"):
        assert k in res
    assert set(res["expected_returns"]) == set(KEYS)
    assert set(res["volatilities"]) == set(KEYS)


def test_covariance_equals_corr_times_sigma():
    res = _build("2016-05-31", "2026-05-31")
    vol = res["volatilities"]
    for ai in KEYS:
        # 대각 = sigma^2
        assert res["covariance_matrix"][ai][ai] == pytest.approx(vol[ai] ** 2, rel=1e-9)
        # 상관 대각 = 1
        assert res["correlation_matrix"][ai][ai] == pytest.approx(1.0, abs=1e-9)
        for aj in KEYS:
            c = res["correlation_matrix"][ai][aj]
            assert res["covariance_matrix"][ai][aj] == pytest.approx(
                c * vol[ai] * vol[aj], rel=1e-9
            )
            assert -1.0001 <= c <= 1.0001


def test_volatility_positive_and_annualized():
    res = _build("2016-05-31", "2026-05-31")
    for k in KEYS:
        assert res["volatilities"][k] > 0
        # 월 sigma 0.04 → 연 ≈ 0.04*sqrt(12) ≈ 13.9% 부근 (난수라 범위 체크)
        assert 0.05 < res["volatilities"][k] < 0.40


# ── window 필터 ────────────────────────────────────────────────────────


def test_narrower_window_has_fewer_obs():
    wide = _build("2016-05-31", "2026-05-31")
    narrow = _build("2022-05-31", "2026-05-31")
    assert narrow["window"]["n_common_obs"] < wide["window"]["n_common_obs"]
    assert wide["window"]["requested_start"] == "2016-05-31"
    assert wide["window"]["requested_end"] == "2026-05-31"


def test_obs_count_matches_month_span():
    res = _build("2020-01-31", "2025-01-31")
    # 2020-01 .. 2025-01 월말 ≈ 61개월
    assert 58 <= res["window"]["n_common_obs"] <= 62
    for k in KEYS:
        assert res["per_asset"][k]["obs"] == res["window"]["n_common_obs"]


# ── short history ──────────────────────────────────────────────────────


def test_short_history_flag_and_warning():
    # kr_treasury_10y 만 2020-01 시작 → 2016 요청 시 short history.
    res = _build("2016-05-31", "2026-05-31", late_key="kr_treasury_10y",
                 late_start="2020-01-31")
    pa = res["per_asset"]["kr_treasury_10y"]
    assert pa["short_history"] is True
    assert pa["effective_start"] >= "2020-01-01"
    assert any("kr_treasury_10y" in w for w in res["warnings"])
    # 나머지는 short history 아님
    assert res["per_asset"]["kr_equity"]["short_history"] is False


# ── 에러 ──────────────────────────────────────────────────────────────


def test_end_before_start_raises():
    fake, mapping = _fake_db()
    with pytest.raises(ValueError):
        build_window_cma(KEYS, _cfg(mapping), fake, start="2026-05-31", end="2016-05-31")


def test_too_short_window_raises():
    # 단일 월 → 공통 관측 < 2 → ValueError
    fake, mapping = _fake_db()
    with pytest.raises(ValueError):
        build_window_cma(KEYS, _cfg(mapping), fake, start="2026-05-31", end="2026-05-31")


# ── endpoint wiring (DB 없이 monkeypatch) ──────────────────────────────


def _synthetic_live_cma():
    er = {k: 0.06 + 0.01 * i for i, k in enumerate(KEYS)}
    vol = {k: 0.10 + 0.01 * i for i, k in enumerate(KEYS)}
    corr = {ai: {aj: (1.0 if ai == aj else 0.2) for aj in KEYS} for ai in KEYS}
    cov = {ai: {aj: corr[ai][aj] * vol[ai] * vol[aj] for aj in KEYS} for ai in KEYS}
    return {
        "asset_keys": list(KEYS), "expected_returns": er, "volatilities": vol,
        "correlation_matrix": corr, "covariance_matrix": cov,
        "window": {"requested_start": "2016-05-31", "requested_end": "2026-05-31",
                   "annualization": 12, "n_common_obs": 120},
        "per_asset": {k: {"obs": 120, "missing": False, "short_history": False} for k in KEYS},
        "warnings": [],
    }


def test_endpoint_db_window_wiring(monkeypatch):
    from fastapi.testclient import TestClient
    import api.frontier_neighborhood as fn
    from api.main import build_app

    monkeypatch.setattr(fn, "_build_db_window_cma", lambda req, keys: _synthetic_live_cma())
    client = TestClient(build_app())
    r = client.post("/api/r-track/frontier-neighborhood", json={
        "portfolio_source": "out/baseline_regen_20260527/portfolio_etf_20260527.json",
        "cma_source": "db_window",
        "db_window_start": "2016-05-31", "db_window_end": "2026-05-31",
        "include_neighborhood": False, "include_random_cloud": True,
        "n_random_samples": 50,
    })
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["cma_source"] == "db_window"
    assert j["db_window"]["window"]["n_common_obs"] == 120
    assert set(j["asset_expected_returns"]) == set(KEYS)
    assert set(j["asset_volatilities"]) == set(KEYS)
    # ticker 는 portfolio JSON 에서 유지
    assert j["asset_tickers"] and "kr_equity" in j["asset_tickers"]


def test_endpoint_portfolio_mode_exposes_per_asset_cma():
    from fastapi.testclient import TestClient
    from api.main import build_app

    client = TestClient(build_app())
    r = client.post("/api/r-track/frontier-neighborhood", json={
        "portfolio_source": "out/file_mode_cma_20260528/portfolio_etf_20260528.json",
        "include_neighborhood": False, "include_random_cloud": True,
        "n_random_samples": 50,
    })
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["cma_source"] == "portfolio"
    assert j["db_window"] is None
    assert j["asset_expected_returns"] and j["asset_volatilities"]
    assert j["asset_tickers"]["kr_equity"]
    # " Index" / " Curncy" 접미사 제거 확인 (M2KR INDEX → M2KR, XAU Curncy → XAU).
    for tk in j["asset_tickers"].values():
        assert not tk.lower().endswith(" index")
        assert not tk.lower().endswith(" curncy")
    assert j["asset_tickers"]["kr_equity"] == "M2KR"


def test_endpoint_unknown_cma_source_422():
    from fastapi.testclient import TestClient
    from api.main import build_app

    client = TestClient(build_app())
    r = client.post("/api/r-track/frontier-neighborhood", json={
        "portfolio_source": "out/file_mode_cma_20260528/portfolio_etf_20260528.json",
        "cma_source": "bogus",
    })
    assert r.status_code == 422
