"""POST /api/r-track/frontier-neighborhood — Frontier Neighborhood Explorer.

efficient frontier 최적 포트(min-variance) 주변에, **동일한 μ/Σ 와 동일한 제약**
(long-only, sum=1, target return, US HY<=cap) 하에서 risk-return 이 거의 같은
near-frontier feasible portfolio 들을 탐색해 반환한다. review-only.

μ/Σ 는 기존 explorer 와 동일하게 portfolio JSON 의 saa_diagnostics.cma 에서 추출
(build_opportunity_set 과 동일 경로) → frontier point 와 neighborhood candidate 가
동일한 CMA 를 공유함이 보장된다 (Dirichlet cloud 와는 다른 feasible region).
"""
from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, HTTPException

from tdf_engine.optimization.frontier_neighborhood import build_frontier_neighborhood
from tdf_engine.optimization.lasso_selection import sha256_file
from tdf_engine.optimization.opportunity_set import (
    _extract_bucket_map,
    _mat,
    _require_direct_saa_and_cma,
    _vec,
)

from .lasso import ENGINE_ROOT, _resolve_under_engine
from .opportunity_set import _asset_metadata_for
from .schemas import (
    FrontierNeighborhoodCandidate,
    FrontierNeighborhoodRequest,
    FrontierNeighborhoodResponse,
    FrontierPoint,
    RandomCloudCandidate,
)

router = APIRouter(prefix="/api/r-track", tags=["r-track"])

_FN_CACHE: dict[str, FrontierNeighborhoodResponse] = {}
_FN_CACHE_MAX = 16
_MAX_GRID_POINTS = 40


def _cache_key(req: FrontierNeighborhoodRequest, portfolio_sha: str) -> str:
    payload = {
        "portfolio_sha": portfolio_sha,
        "hy_key": req.hy_key,
        "hy_cap": round(req.hy_cap, 9),
        "risk_free_rate": None if req.risk_free_rate is None else round(req.risk_free_rate, 9),
        "grid": [round(req.target_return_min, 9), round(req.target_return_max, 9), round(req.target_return_step, 9)],
        "vol_gaps_bps": sorted(int(g) for g in req.vol_gaps_bps),
        "return_tolerance_bps": round(req.return_tolerance_bps, 6),
        "n_directions": req.n_directions,
        "steps_per_direction": req.steps_per_direction,
        "method_b": req.method_b,
        "random_seed": req.random_seed,
        "include_weights": req.include_weights,
        "include_neighborhood": req.include_neighborhood,
        "include_random_cloud": req.include_random_cloud,
        "n_random_samples": req.n_random_samples,
        "random_cloud_alpha": round(req.random_cloud_alpha, 6),
        "equity_band": [round(req.equity_weight_min, 6), round(req.equity_weight_max, 6)],
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _build_grid(lo: float, hi: float, step: float) -> list[float]:
    if hi < lo or step <= 0:
        return []
    n_pts = int(round((hi - lo) / step)) + 1
    n_pts = max(0, min(n_pts, _MAX_GRID_POINTS))
    grid: list[float] = []
    for i in range(n_pts):
        t = round(lo + i * step, 6)
        if t > hi + 1e-9:
            break
        grid.append(t)
    return grid


@router.post("/frontier-neighborhood", response_model=FrontierNeighborhoodResponse)
def frontier_neighborhood(req: FrontierNeighborhoodRequest) -> FrontierNeighborhoodResponse:
    src = _resolve_under_engine(req.portfolio_source)
    if not src.exists() or not src.is_file():
        raise HTTPException(status_code=404, detail=f"portfolio_source not found: {src}")
    portfolio_sha = sha256_file(src)

    cache_key = _cache_key(req, portfolio_sha)
    cached = _FN_CACHE.get(cache_key)
    if cached is not None:
        return cached

    try:
        portfolio = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"invalid portfolio JSON: {e}")

    # μ/Σ — 기존 explorer 와 동일 CMA 추출 (cloud 생성 없이 inputs 만).
    try:
        saa = _require_direct_saa_and_cma(portfolio)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    cma = saa["cma"]
    asset_keys = [str(k) for k in cma["asset_keys"]]
    mu = _vec(cma["expected_returns"], asset_keys)
    cov = _mat(cma["covariance_matrix"], asset_keys)
    rf = float(
        req.risk_free_rate if req.risk_free_rate is not None else (saa.get("rf") or 0.0)
    )
    # bucket map — equity_weight frontier mode 의 주식비중(equity bucket=주식+금) 정의용.
    try:
        bucket_map = _extract_bucket_map(portfolio, asset_keys)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    equity_keys = [k for k in asset_keys if bucket_map.get(k) == "equity"]

    grid = _build_grid(req.target_return_min, req.target_return_max, req.target_return_step)
    if not grid:
        raise HTTPException(
            status_code=422,
            detail="empty target-return grid (check min/max/step).",
        )
    vol_gaps = tuple(sorted({int(g) for g in req.vol_gaps_bps if int(g) > 0}))
    if not vol_gaps:
        raise HTTPException(status_code=422, detail="vol_gaps_bps must contain positive ints.")

    result = build_frontier_neighborhood(
        asset_keys, mu, cov,
        hy_key=req.hy_key,
        hy_cap=float(req.hy_cap),
        risk_free_rate=rf,
        target_returns=grid,
        vol_gaps_bps=vol_gaps,
        return_tolerance_bps=float(req.return_tolerance_bps),
        n_directions=int(req.n_directions),
        steps_per_direction=int(req.steps_per_direction),
        random_seed=int(req.random_seed),
        method_b=bool(req.method_b),
        include_neighborhood=bool(req.include_neighborhood),
        include_random_cloud=bool(req.include_random_cloud),
        n_random_samples=int(req.n_random_samples),
        random_cloud_alpha=float(req.random_cloud_alpha),
        equity_keys=equity_keys,
        equity_weight_min=float(req.equity_weight_min),
        equity_weight_max=float(req.equity_weight_max),
    )

    fps = [FrontierPoint(**fp) for fp in result["frontier_points"]]
    cands = []
    for c in result["candidates"]:
        if not req.include_weights:
            c = {**c, "weights": None}
        cands.append(FrontierNeighborhoodCandidate(**c))
    if not req.include_weights:
        for fp in fps:
            fp.weights = None
    random_cloud = None
    if result.get("random_cloud") is not None:
        random_cloud = [
            RandomCloudCandidate(**({**rc, "weights": None} if not req.include_weights else rc))
            for rc in result["random_cloud"]
        ]

    asset_labels, asset_buckets = _asset_metadata_for(result["asset_keys"])

    response = FrontierNeighborhoodResponse(
        source_opportunity_set_path=(
            f"frontier_neighborhood:"
            f"{src.relative_to(ENGINE_ROOT) if src.is_relative_to(ENGINE_ROOT) else src}"
        ),
        source_opportunity_set_sha256=portfolio_sha,
        constraint_set=result["constraint_set"],
        included_constraints=result["included_constraints"],
        excluded_constraints=result["excluded_constraints"],
        asset_keys=result["asset_keys"],
        asset_labels=asset_labels,
        asset_buckets=asset_buckets,
        frontier_points=fps,
        candidates=cands,
        random_cloud=random_cloud,
        candidate_count=len(cands),
        summary=result["summary"],
        inputs=result["inputs"],
    )

    if len(_FN_CACHE) >= _FN_CACHE_MAX:
        _FN_CACHE.pop(next(iter(_FN_CACHE)))
    _FN_CACHE[cache_key] = response
    return response
