"""Near-Frontier Scan — 단위(합성 μ/Σ) + endpoint smoke(file CMA).

핵심 검증: anchor별 near-frontier band 준수 (vol_gap 부호는 강제하지 않음 —
candidate_vol <= anchor_vol + tol_vol + eps), active_share 필터, snap, per-anchor dedupe.
"""
from __future__ import annotations

import numpy as np
import pytest

from tdf_engine.optimization.near_frontier_scan import (
    _active_share,
    _snap_to_grid,
    build_near_frontier_scan,
)

KEYS = ["a", "b", "c", "d", "e", "f", "g", "us_high_yield"]


def _synthetic():
    rng = np.random.default_rng(0)
    n = len(KEYS)
    mu = np.linspace(0.03, 0.13, n)
    A = rng.normal(size=(n, n))
    cov = (A @ A.T) / n * 0.04 + np.eye(n) * 0.01
    return KEYS, mu.tolist(), cov.tolist()


# ── snap helper ────────────────────────────────────────────────────────


def test_snap_keeps_sum_one_and_grid():
    rng = np.random.default_rng(1)
    for _ in range(20):
        w = rng.dirichlet(np.ones(8))
        s = _snap_to_grid(w, 0.005)
        assert abs(s.sum() - 1.0) < 1e-9
        # 모든 weight 가 0.5% 격자 위 (단위 정수)
        units = s / 0.005
        assert np.all(np.abs(units - np.round(units)) < 1e-6)
        assert np.all(s >= -1e-12)


def test_active_share_formula():
    a = np.array([0.5, 0.5, 0.0])
    b = np.array([0.3, 0.3, 0.4])
    assert _active_share(a, b) == pytest.approx(0.5 * (0.2 + 0.2 + 0.4))


# ── build_near_frontier_scan ───────────────────────────────────────────


def _run(**over):
    keys, mu, cov = _synthetic()
    kw = dict(
        risk_free_rate=0.02,
        target_returns=[0.06, 0.07, 0.08, 0.09],
        tol_return_bps=10, tol_vol_bps=25, n_random_directions=15,
    )
    kw.update(over)
    return build_near_frontier_scan(keys, mu, cov, **kw), keys


def test_anchors_and_candidates_present():
    res, _ = _run()
    assert res["summary"]["anchor_count"] >= 2
    assert len(res["anchors"]) == res["summary"]["anchor_count"]
    assert res["summary"]["candidate_count"] == len(res["candidates"])
    assert res["constraint_set"] == "near_frontier_scan"


def test_candidates_respect_band_no_sign_force():
    res, _ = _run()
    tol_ret = 10 / 10000.0
    tol_vol = 25 / 10000.0
    for c in res["candidates"]:
        # 핵심: vol_gap 부호 강제 X. band 준수만.
        assert c["candidate_volatility"] <= c["anchor_vol"] + tol_vol + 1e-4
        assert abs(c["return_gap_vs_anchor"]) <= tol_ret + 2e-4
        assert c["active_share_vs_anchor"] >= 0.05 - 1e-9
        # vol_gap = candidate_vol - anchor_vol (음수 허용)
        assert c["vol_gap_vs_anchor"] == pytest.approx(
            c["candidate_volatility"] - c["anchor_vol"], abs=1e-9
        )


def test_active_share_min_drop_and_emphasis():
    res, _ = _run(active_share_min=0.08, active_share_emphasis=0.15)
    for c in res["candidates"]:
        assert c["active_share_vs_anchor"] >= 0.08 - 1e-9
        assert c["emphasis"] == (c["active_share_vs_anchor"] >= 0.15)


def test_per_anchor_dedupe_distance():
    res, keys = _run(dedupe_threshold=0.05)
    n = len(keys)
    by_anchor: dict[int, list] = {}
    for c in res["candidates"]:
        by_anchor.setdefault(c["anchor_node_id"], []).append(
            np.array([c["weights"][k] for k in keys])
        )
    # 같은 anchor 내 후보쌍 distance >= threshold
    for ws in by_anchor.values():
        for i in range(len(ws)):
            for j in range(i + 1, len(ws)):
                assert _active_share(ws[i], ws[j]) >= 0.05 - 1e-9


def test_snap_produces_grid_weights():
    res, keys = _run(snap_grid=0.005)
    for c in res["candidates"]:
        for v in c["weights"].values():
            units = v / 0.005
            assert abs(units - round(units)) < 1e-6


def test_search_direction_labels():
    res, _ = _run()
    prefixes = {c["search_direction"].split(":")[0] for c in res["candidates"]}
    # 최소한 random + asset-extreme 류는 나와야
    assert prefixes & {"random", "overweight", "underweight", "force_entry", "min_hhi"}


def test_per_anchor_top_n_cap():
    res, _ = _run(per_anchor_top_n=3)
    by_anchor: dict[int, int] = {}
    for c in res["candidates"]:
        by_anchor[c["anchor_node_id"]] = by_anchor.get(c["anchor_node_id"], 0) + 1
    assert by_anchor, "no candidates"
    assert all(v <= 3 for v in by_anchor.values())


def test_structured_directions_attempted():
    # bucket_groups 주면 pairwise + group + support + hhi 가 directional 에 추가됨.
    keys, mu, cov = _synthetic()
    groups = {"g_low": [0, 1, 2], "g_high": [5, 6, 7]}
    res = build_near_frontier_scan(
        keys, mu, cov, risk_free_rate=0.02,
        target_returns=[0.07, 0.08], tol_return_bps=10, tol_vol_bps=25,
        n_random_directions=10, bucket_groups=groups,
    )
    # directions_per_anchor 가 (asset over/under ~2n + random) 보다 충분히 큼 = structured 추가됨.
    assert res["summary"]["directions_per_anchor"] > 2 * len(keys) + 10


def test_single_anchor_max_sharpe_diagnostic():
    res, _ = _run(single_anchor_max_sharpe=True)
    assert res["summary"]["anchor_count"] == 1


def test_cross_anchor_flag_marks_not_removes():
    # cross_anchor_dedupe=True 라도 후보를 제거하지 않음 (표시용 flag).
    off, _ = _run(cross_anchor_dedupe=False)
    on, _ = _run(cross_anchor_dedupe=True)
    assert off["summary"]["candidate_count"] == on["summary"]["candidate_count"]
    assert "cross_anchor_unique_count" in on["summary"]


# ── endpoint smoke (file CMA, DB 불필요) ───────────────────────────────


def test_endpoint_near_frontier_scan_smoke():
    from fastapi.testclient import TestClient
    from api.main import build_app

    client = TestClient(build_app())
    r = client.post("/api/r-track/near-frontier-scan", json={
        "portfolio_source": "out/file_mode_cma_20260528/portfolio_etf_20260528.json",
        "target_return_min": 0.06, "target_return_max": 0.10, "target_return_step": 0.01,
        "n_random_directions": 15,
    })
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["constraint_set"] == "near_frontier_scan"
    assert j["summary"]["anchor_count"] >= 2
    assert len(j["anchors"]) >= 2
    tol_vol = 25 / 10000.0
    tol_ret = 10 / 10000.0
    for c in j["candidates"]:
        # vol_gap 부호 강제 금지 — band 준수만 검증.
        assert c["candidate_volatility"] <= c["anchor_vol"] + tol_vol + 1e-4
        assert abs(c["return_gap_vs_anchor"]) <= tol_ret + 2e-4
        assert c["active_share_vs_anchor"] >= 0.05 - 1e-9
    assert j["asset_tickers"]["kr_equity"] == "M2KR"
    assert j["is_production_selection"] is False


def test_endpoint_unknown_cma_source_422():
    from fastapi.testclient import TestClient
    from api.main import build_app

    client = TestClient(build_app())
    r = client.post("/api/r-track/near-frontier-scan", json={
        "portfolio_source": "out/file_mode_cma_20260528/portfolio_etf_20260528.json",
        "cma_source": "bogus",
    })
    assert r.status_code == 422
