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
import os
from datetime import date

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
        "equity_weight_keys": sorted(req.equity_weight_keys) if req.equity_weight_keys else None,
        "asset_constraints": (
            {k: [round(float(v[0]), 6), round(float(v[1]), 6)] for k, v in sorted(req.asset_constraints.items())}
            if req.asset_constraints else None
        ),
        "cma_source": req.cma_source,
        "db_window": [req.db_window_start, req.db_window_end],
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _clean_ticker(t: str) -> str:
    """표시용 ticker — 후행 " Index" / " Curncy" 접미사 제거 (대소문자 무시)."""
    s = t.strip()
    for suf in (" index", " curncy"):
        if s.lower().endswith(suf):
            return s[: -len(suf)].strip()
    return s


def _prev_month_end(today: date) -> date:
    """today 기준 전월 말일."""
    first_of_this_month = today.replace(day=1)
    import datetime as _dt

    return first_of_this_month - _dt.timedelta(days=1)


def _default_db_window() -> tuple[str, str]:
    """default = 종료 전월 말 / 시작 −10년 (직전 10년)."""
    end = _prev_month_end(date.today())
    try:
        start = end.replace(year=end.year - 10)
    except ValueError:  # 2/29 등
        start = end.replace(year=end.year - 10, day=28)
    return start.isoformat(), end.isoformat()


def _build_db_window_cma(req: "FrontierNeighborhoodRequest", asset_keys: list[str]) -> dict:
    """SCIP DB 에서 [db_window_start, db_window_end] 라이브 CMA 산출 (review-only).

    credential 은 환경변수(TDF_DB_HOST/USER/PASSWORD/NAME) — 코드 미하드코딩.
    """
    import yaml

    from tdf_engine.optimization.db_cma_window import build_window_cma

    start = req.db_window_start
    end = req.db_window_end
    if not start or not end:
        d_start, d_end = _default_db_window()
        start = start or d_start
        end = end or d_end
    try:
        s_date = date.fromisoformat(start)
        e_date = date.fromisoformat(end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"db_window 날짜 형식(YYYY-MM-DD) 오류: {exc}")
    if e_date < s_date:
        raise HTTPException(status_code=422, detail=f"db_window_end({end}) < db_window_start({start})")

    cfg_path = ENGINE_ROOT / "tdf_engine" / "config" / "db_sources.yaml"
    if not cfg_path.exists():
        raise HTTPException(status_code=500, detail="db_sources.yaml 없음")
    db_sources_cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))

    db_user = os.environ.get("TDF_DB_USER", "${DB_USER}")
    db_pw = os.environ.get("TDF_DB_PASSWORD", "${DB_PASSWORD}")
    db_host = os.environ.get("TDF_DB_HOST", "${DB_HOST}")
    db_name = os.environ.get("TDF_DB_NAME", "SCIP")
    try:
        from sqlalchemy import create_engine, text

        url = f"mysql+pymysql://{db_user}:{db_pw}@{db_host}/{db_name}?charset=utf8mb4"
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"SCIP DB 연결 실패 (host={db_host}): {exc}. "
                "내부망/VPN + 환경변수(TDF_DB_HOST/USER/PASSWORD/NAME) 확인."
            ),
        )
    try:
        return build_window_cma(asset_keys, db_sources_cfg, engine, start=s_date, end=e_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"db_window CMA 산출 실패: {exc}")
    finally:
        engine.dispose()


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
    # asset 순서·ticker 는 portfolio JSON 기준 유지 (db_window 모드에서도 동일).
    # 표시용으로 " Index" / " Curncy" 접미사 제거 (M2KR INDEX → M2KR 등).
    ticker_by_key = {
        str(k): _clean_ticker(str(v)) for k, v in (cma.get("ticker_by_key") or {}).items()
    }
    rf = float(
        req.risk_free_rate if req.risk_free_rate is not None else (saa.get("rf") or 0.0)
    )

    # ── CMA 소스 분기 ──
    # "portfolio" (default) = JSON saa_diagnostics.cma 그대로.
    # "db_window"          = SCIP DB 라이브 재계산 μ/Σ 로 교체 (review-only).
    db_window_meta: dict | None = None
    if req.cma_source == "db_window":
        live = _build_db_window_cma(req, asset_keys)
        missing = [k for k in asset_keys if k not in live["expected_returns"]]
        if missing:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"db_window CMA: window 내 데이터 부족으로 자산 누락 {missing}. "
                    "window 를 넓히세요."
                ),
            )
        expected_returns = {k: float(live["expected_returns"][k]) for k in asset_keys}
        volatilities = {k: float(live["volatilities"][k]) for k in asset_keys}
        cov_src = live["covariance_matrix"]
        db_window_meta = {
            "window": live["window"],
            "per_asset": live["per_asset"],
            "warnings": live["warnings"],
        }
    elif req.cma_source != "portfolio":
        raise HTTPException(
            status_code=422,
            detail=f"unknown cma_source: {req.cma_source} (portfolio | db_window)",
        )
    else:
        expected_returns = {k: float(cma["expected_returns"].get(k, 0.0)) for k in asset_keys}
        volatilities = {k: float((cma.get("volatilities") or {}).get(k, 0.0)) for k in asset_keys}
        cov_src = cma["covariance_matrix"]

    mu = _vec(expected_returns, asset_keys)
    cov = _mat(cov_src, asset_keys)
    # bucket map — equity_weight frontier mode 의 주식비중(equity bucket=주식+금) 정의용.
    try:
        bucket_map = _extract_bucket_map(portfolio, asset_keys)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    # equity 밴드 그룹 — request 가 명시(3-mode: 주식/주식+금/주식+금+HY)하면 그걸,
    # 아니면 bucket=="equity"(주식5+금) default.
    if req.equity_weight_keys:
        unknown = [k for k in req.equity_weight_keys if k not in asset_keys]
        if unknown:
            raise HTTPException(status_code=422, detail=f"unknown equity_weight_keys: {unknown}")
        equity_keys = [k for k in asset_keys if k in set(req.equity_weight_keys)]
    else:
        equity_keys = [k for k in asset_keys if bucket_map.get(k) == "equity"]

    # per-asset (floor, cap) — request asset_constraints → asset_keys 순서 (lo,hi) 리스트.
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
        asset_bounds=asset_bounds,
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
    out_keys = [str(k) for k in result["asset_keys"]]
    asset_tickers = {k: ticker_by_key[k] for k in out_keys if k in ticker_by_key} or None

    response = FrontierNeighborhoodResponse(
        source_opportunity_set_path=(
            f"frontier_neighborhood:"
            f"{src.relative_to(ENGINE_ROOT) if src.is_relative_to(ENGINE_ROOT) else src}"
        ),
        source_opportunity_set_sha256=portfolio_sha,
        constraint_set=result["constraint_set"],
        included_constraints=result["included_constraints"],
        excluded_constraints=result["excluded_constraints"],
        asset_keys=out_keys,
        asset_labels=asset_labels,
        asset_buckets=asset_buckets,
        asset_expected_returns={k: expected_returns[k] for k in out_keys if k in expected_returns},
        asset_volatilities={k: volatilities[k] for k in out_keys if k in volatilities},
        asset_tickers=asset_tickers,
        cma_source=req.cma_source,
        db_window=db_window_meta,
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
