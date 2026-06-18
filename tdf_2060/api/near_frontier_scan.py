"""POST /api/r-track/near-frontier-scan — Near-Frontier Scan (batch frontier line scan).

EF 라인의 각 anchor node 근처 near-frontier band 안에서 active_share 큰 대안 포트를
directional 탐색한다. review-only. CMA 추출(file/db_window)·asset_bounds·equity 그룹
plumbing 은 frontier_neighborhood endpoint 와 동일 헬퍼를 재사용한다.
"""
from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, HTTPException

from tdf_engine.optimization.near_frontier_scan import build_near_frontier_scan
from tdf_engine.optimization.lasso_selection import sha256_file
from tdf_engine.optimization.opportunity_set import (
    _extract_bucket_map,
    _mat,
    _require_direct_saa_and_cma,
    _vec,
)

from .frontier_neighborhood import _build_db_window_cma, _build_grid, _clean_ticker
from .lasso import ENGINE_ROOT, _resolve_under_engine
from .opportunity_set import _asset_metadata_for
from .schemas import (
    NearFrontierScanAnchor,
    NearFrontierScanCandidate,
    NearFrontierScanRequest,
    NearFrontierScanResponse,
)

router = APIRouter(prefix="/api/r-track", tags=["r-track"])

_NFS_CACHE: dict[str, NearFrontierScanResponse] = {}
_NFS_CACHE_MAX = 16


def _cache_key(req: NearFrontierScanRequest, portfolio_sha: str) -> str:
    payload = {
        "portfolio_sha": portfolio_sha,
        "hy_key": req.hy_key,
        "hy_cap": round(req.hy_cap, 9),
        "rf": None if req.risk_free_rate is None else round(req.risk_free_rate, 9),
        "grid": [round(req.target_return_min, 9), round(req.target_return_max, 9), round(req.target_return_step, 9)],
        "tol": [round(req.tol_return_bps, 6), round(req.tol_vol_bps, 6)],
        "n_random": req.n_random_directions,
        "seed": req.random_seed,
        "active_share": [round(req.active_share_min, 6), round(req.active_share_emphasis, 6)],
        "snap": round(req.snap_grid, 9),
        "dedupe": round(req.dedupe_threshold, 9),
        "top_n": req.per_anchor_top_n,
        "cross": req.cross_anchor_dedupe,
        "single": req.single_anchor_max_sharpe,
        "incl_w": req.include_weights,
        "eq_keys": sorted(req.equity_weight_keys) if req.equity_weight_keys else None,
        "eq_band": [round(req.equity_weight_min, 6), round(req.equity_weight_max, 6)],
        "asset_constraints": (
            {k: [round(float(v[0]), 6), round(float(v[1]), 6)] for k, v in sorted(req.asset_constraints.items())}
            if req.asset_constraints else None
        ),
        "cma_source": req.cma_source,
        "db_window": [req.db_window_start, req.db_window_end],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


@router.post("/near-frontier-scan", response_model=NearFrontierScanResponse)
def near_frontier_scan(req: NearFrontierScanRequest) -> NearFrontierScanResponse:
    src = _resolve_under_engine(req.portfolio_source)
    if not src.exists() or not src.is_file():
        raise HTTPException(status_code=404, detail=f"portfolio_source not found: {src}")
    portfolio_sha = sha256_file(src)

    cache_key = _cache_key(req, portfolio_sha)
    cached = _NFS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    try:
        portfolio = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"invalid portfolio JSON: {e}")

    try:
        saa = _require_direct_saa_and_cma(portfolio)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    cma = saa["cma"]
    asset_keys = [str(k) for k in cma["asset_keys"]]
    ticker_by_key = {
        str(k): _clean_ticker(str(v)) for k, v in (cma.get("ticker_by_key") or {}).items()
    }
    rf = float(req.risk_free_rate if req.risk_free_rate is not None else (saa.get("rf") or 0.0))

    # ── CMA 소스 (portfolio | db_window) ──
    db_window_meta: dict | None = None
    if req.cma_source == "db_window":
        live = _build_db_window_cma(req, asset_keys)
        missing = [k for k in asset_keys if k not in live["expected_returns"]]
        if missing:
            raise HTTPException(status_code=422, detail=f"db_window CMA: 자산 누락 {missing}. window 를 넓히세요.")
        expected_returns = {k: float(live["expected_returns"][k]) for k in asset_keys}
        cov_src = live["covariance_matrix"]
        db_window_meta = {"window": live["window"], "per_asset": live["per_asset"], "warnings": live["warnings"]}
    elif req.cma_source != "portfolio":
        raise HTTPException(status_code=422, detail=f"unknown cma_source: {req.cma_source}")
    else:
        expected_returns = {k: float(cma["expected_returns"].get(k, 0.0)) for k in asset_keys}
        cov_src = cma["covariance_matrix"]

    mu = _vec(expected_returns, asset_keys)
    cov = _mat(cov_src, asset_keys)

    try:
        bucket_map = _extract_bucket_map(portfolio, asset_keys)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if req.equity_weight_keys:
        unknown = [k for k in req.equity_weight_keys if k not in asset_keys]
        if unknown:
            raise HTTPException(status_code=422, detail=f"unknown equity_weight_keys: {unknown}")
        equity_keys = [k for k in asset_keys if k in set(req.equity_weight_keys)]
    else:
        equity_keys = [k for k in asset_keys if bucket_map.get(k) == "equity"]

    asset_bounds = None
    if req.asset_constraints:
        unknown = [k for k in req.asset_constraints if k not in asset_keys]
        if unknown:
            raise HTTPException(status_code=422, detail=f"unknown asset_constraints keys: {unknown}")
        ab: list[tuple[float, float]] = []
        for k in asset_keys:
            pair = req.asset_constraints.get(k)
            if pair and len(pair) == 2:
                lo, hi = float(pair[0]), float(pair[1])
                if hi < lo:
                    raise HTTPException(status_code=422, detail=f"asset_constraints[{k}]: cap < floor")
                ab.append((max(0.0, lo), min(1.0, hi)))
            else:
                ab.append((0.0, 1.0))
        asset_bounds = ab

    grid = _build_grid(req.target_return_min, req.target_return_max, req.target_return_step)
    if not grid:
        raise HTTPException(status_code=422, detail="empty target-return grid (anchor).")

    # bucket-level direction 용 그룹 (주식/채권 버킷 + 개별 notable 자산).
    bucket_groups: dict[str, list[int]] = {}
    eq_g = [i for i, k in enumerate(asset_keys) if bucket_map.get(k) == "equity"]
    fi_g = [i for i, k in enumerate(asset_keys) if bucket_map.get(k) == "fixed_income"]
    if eq_g:
        bucket_groups["equity"] = eq_g
    if fi_g:
        bucket_groups["fixed_income"] = fi_g
    for special in ("gold", "us_growth_equity"):
        if special in asset_keys:
            bucket_groups[special] = [asset_keys.index(special)]

    result = build_near_frontier_scan(
        asset_keys, mu, cov,
        hy_key=req.hy_key,
        hy_cap=float(req.hy_cap),
        risk_free_rate=rf,
        target_returns=grid,
        tol_return_bps=float(req.tol_return_bps),
        tol_vol_bps=float(req.tol_vol_bps),
        n_random_directions=int(req.n_random_directions),
        random_seed=int(req.random_seed),
        active_share_min=float(req.active_share_min),
        active_share_emphasis=float(req.active_share_emphasis),
        snap_grid=float(req.snap_grid),
        dedupe_threshold=float(req.dedupe_threshold),
        per_anchor_top_n=int(req.per_anchor_top_n),
        cross_anchor_dedupe=bool(req.cross_anchor_dedupe),
        equity_keys=equity_keys,
        equity_weight_min=float(req.equity_weight_min),
        equity_weight_max=float(req.equity_weight_max),
        asset_bounds=asset_bounds,
        bucket_groups=bucket_groups,
        single_anchor_max_sharpe=bool(req.single_anchor_max_sharpe),
    )

    drop_w = not req.include_weights
    anchors = [
        NearFrontierScanAnchor(**({**a, "anchor_weights": None} if drop_w else a))
        for a in result["anchors"]
    ]
    cands = [
        NearFrontierScanCandidate(**({**c, "weights": None} if drop_w else c))
        for c in result["candidates"]
    ]

    out_keys = [str(k) for k in result["asset_keys"]]
    asset_labels, asset_buckets = _asset_metadata_for(out_keys)
    asset_tickers = {k: ticker_by_key[k] for k in out_keys if k in ticker_by_key} or None

    response = NearFrontierScanResponse(
        source_opportunity_set_path=(
            f"near_frontier_scan:"
            f"{src.relative_to(ENGINE_ROOT) if src.is_relative_to(ENGINE_ROOT) else src}"
        ),
        source_opportunity_set_sha256=portfolio_sha,
        constraint_set=result["constraint_set"],
        asset_keys=out_keys,
        asset_labels=asset_labels,
        asset_buckets=asset_buckets,
        asset_tickers=asset_tickers,
        cma_source=req.cma_source,
        db_window=db_window_meta,
        anchors=anchors,
        candidates=cands,
        candidate_count=len(cands),
        summary=result["summary"],
        inputs=result["inputs"],
    )

    if len(_NFS_CACHE) >= _NFS_CACHE_MAX:
        _NFS_CACHE.pop(next(iter(_NFS_CACHE)))
    _NFS_CACHE[cache_key] = response
    return response
