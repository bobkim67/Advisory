"""GET /api/r-track/opportunity-set/scatter — frontend scatter dataset.

Projects the R-1B.2 opportunity set + cloud tags to a small per-candidate
dict so the React scatter and the representative-marker overlay share a
single coordinate source. Review-only endpoint; permanent invariants forced.

Phase 6.2 (2026-05-26): `include_weights` query flag toggles per-candidate
weights + per-bucket fields + dataset-level asset_keys/labels/buckets. The
default (flag=false) keeps the legacy minimal payload; new fields are emitted
as `null` so existing consumers are unaffected. The bucket taxonomy is read
from `tdf_engine/config/assets.yaml` via ConfigLoader (cached per process).
"""
from __future__ import annotations

import json
import pathlib

import hashlib
from typing import Any

from fastapi import APIRouter, HTTPException

from tdf_engine.config.loader import ConfigLoader
from tdf_engine.optimization.lasso_selection import compute_cloud_tags, sha256_file
from tdf_engine.optimization.opportunity_set import build_opportunity_set

from .lasso import ENGINE_ROOT, _load_batch_signals, _resolve_under_engine
import math

from .schemas import (
    CustomOpportunitySetRequest,
    ScatterCandidate,
    ScatterDatasetResponse,
)

router = APIRouter(prefix="/api/r-track", tags=["r-track"])


_ASSET_META_CACHE: dict[str, dict[str, str]] | None = None


def _load_asset_meta() -> dict[str, dict[str, str]]:
    """Return {asset_key: {'label': display_name, 'bucket': bucket_value}}.

    Cached for the lifetime of the process; assets.yaml is config, not data,
    so reloading per request is wasteful.
    """
    global _ASSET_META_CACHE
    if _ASSET_META_CACHE is not None:
        return _ASSET_META_CACHE
    cfg_dir = ENGINE_ROOT / "tdf_engine" / "config"
    loader = ConfigLoader(config_dir=cfg_dir)
    assets = loader.load_assets()
    meta: dict[str, dict[str, str]] = {}
    for a in assets:
        bucket_val = getattr(a.bucket, "value", str(a.bucket))
        meta[a.asset_key] = {
            "label": getattr(a, "display_name", a.asset_key),
            "bucket": str(bucket_val),
        }
    _ASSET_META_CACHE = meta
    return meta


def _project_candidates_to_scatter(
    cands: list[dict],
    tagged: list[dict],
    include_weights: bool,
) -> list[ScatterCandidate]:
    """Common projection used by GET scatter + POST custom endpoints."""

    def _opt_float(c: dict, key: str) -> float | None:
        v = c.get(key)
        return None if v is None else float(v)

    def _opt_int(c: dict, key: str) -> int | None:
        v = c.get(key)
        return None if v is None else int(v)

    def _opt_weights(c: dict) -> dict[str, float] | None:
        w = c.get("weights")
        if not isinstance(w, dict):
            return None
        return {str(k): float(v) for k, v in w.items()}

    by_id = {c["candidate_id"]: c for c in cands if isinstance(c, dict)}
    tagged_full = [{**by_id.get(t["candidate_id"], {}), **t} for t in tagged]

    return [
        ScatterCandidate(
            candidate_id=c["candidate_id"],
            volatility=float(c["volatility"]),
            expected_return=float(c["expected_return"]),
            sharpe=float(c["sharpe"]),
            concentration_hhi=float(c["concentration_hhi"]),
            max_asset_weight=float(c["max_asset_weight"]),
            mvo_efficiency_score=float(c["mvo_efficiency_score"]),
            feasibility_status=str(c.get("feasibility_status", "unknown")),
            overlap_score=int(c["overlap_score"]),
            cloud_labels=str(c.get("cloud_labels", "")),
            has_fallback=(None if c.get("has_fallback") is None else bool(c["has_fallback"])),
            has_universe_warning=(
                None if c.get("has_universe_warning") is None else bool(c["has_universe_warning"])
            ),
            weights=_opt_weights(c) if include_weights else None,
            equity_weight=_opt_float(c, "equity_weight") if include_weights else None,
            fixed_income_weight=_opt_float(c, "fixed_income_weight") if include_weights else None,
            equity_intra_hhi=_opt_float(c, "equity_intra_hhi") if include_weights else None,
            fixed_income_intra_hhi=_opt_float(c, "fixed_income_intra_hhi") if include_weights else None,
            equity_max_asset_weight=_opt_float(c, "equity_max_asset_weight") if include_weights else None,
            fixed_income_max_asset_weight=_opt_float(c, "fixed_income_max_asset_weight") if include_weights else None,
            nonzero_asset_count=_opt_int(c, "nonzero_asset_count") if include_weights else None,
        )
        for c in tagged_full
    ]


def _asset_metadata_for(asset_keys: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """Return (labels, buckets) for the given asset keys."""
    meta = _load_asset_meta()
    labels = {k: meta.get(k, {}).get("label", k) for k in asset_keys}
    buckets = {k: meta.get(k, {}).get("bucket", "unknown") for k in asset_keys}
    return labels, buckets


@router.get("/opportunity-set/scatter", response_model=ScatterDatasetResponse)
def opportunity_set_scatter(
    source_opportunity_set_path: str,
    batch_results_dir: str | None = None,
    include_weights: bool = False,
) -> ScatterDatasetResponse:
    src = _resolve_under_engine(source_opportunity_set_path)
    if not src.exists():
        raise HTTPException(status_code=404, detail=f"opportunity set not found: {src}")
    if not src.is_file():
        raise HTTPException(status_code=400, detail=f"source_opportunity_set_path is not a file: {src}")

    try:
        opp = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"invalid JSON in opportunity set: {e}")

    cands = opp.get("candidates", [])
    if not isinstance(cands, list) or not cands:
        raise HTTPException(status_code=400, detail="opportunity set has no candidates")

    batch_signals = _load_batch_signals(batch_results_dir) if batch_results_dir else {}
    tagged = compute_cloud_tags(cands, batch_signals=batch_signals or None)
    projected = _project_candidates_to_scatter(cands, tagged, include_weights)

    asset_keys: list[str] | None = None
    asset_labels: dict[str, str] | None = None
    asset_buckets: dict[str, str] | None = None
    if include_weights:
        meta = _load_asset_meta()
        ordered = opp.get("inputs", {}).get("asset_keys")
        if isinstance(ordered, list) and ordered:
            asset_keys = [str(k) for k in ordered]
        else:
            asset_keys = sorted(meta.keys())
        asset_labels, asset_buckets = _asset_metadata_for(asset_keys)

    # 2026-05-27 — opportunity_set inputs.risk_free_rate (Sharpe 계산용)
    # 을 frontend 의 Sharpe 카드 주석에 사용하기 위해 함께 전달.
    rf_raw = (opp.get("inputs") or {}).get("risk_free_rate")
    risk_free_rate = float(rf_raw) if isinstance(rf_raw, (int, float)) else None

    return ScatterDatasetResponse(
        source_opportunity_set_path=str(src.relative_to(ENGINE_ROOT))
        if src.is_relative_to(ENGINE_ROOT)
        else str(src),
        source_opportunity_set_sha256=sha256_file(src),
        candidate_count=len(projected),
        candidates=projected,
        include_weights=include_weights,
        asset_keys=asset_keys,
        asset_labels=asset_labels,
        asset_buckets=asset_buckets,
        risk_free_rate=risk_free_rate,
    )


# ---------------------------------------------------------------------------
# Phase 6.5 — POST /custom: 자산 panel 입력으로 on-demand opportunity set 계산
# ---------------------------------------------------------------------------


_CUSTOM_CACHE: dict[str, ScatterDatasetResponse] = {}
_CUSTOM_CACHE_MAX = 16


def _reference_metrics(
    label: str,
    weights: dict[str, float],
    opp: dict,
) -> ScatterCandidate | None:
    """외부 reference 포트폴리오를 현재 CMA(opp.inputs)로 평가 → ScatterCandidate.

    mvo_efficiency_score 는 frontier 가 응답에 없어 None. vol/ret/sharpe/hhi 만 계산.
    누락 자산 weight=0. 합이 1 과 크게 다르면 그대로 (운용역 입력 책임).
    """
    inputs = opp.get("inputs") or {}
    keys = list(inputs.get("asset_keys") or [])
    er = inputs.get("expected_returns") or {}
    cov = inputs.get("covariance_matrix") or {}
    if not keys or not er or not cov:
        return None
    w = {k: float(weights.get(k, 0.0)) for k in keys}
    rf = float(inputs.get("risk_free_rate") or 0.0)
    ret = sum(w[k] * float(er.get(k, 0.0)) for k in keys)
    var = 0.0
    for ki in keys:
        row = cov.get(ki) or {}
        wi = w[ki]
        if wi == 0.0:
            continue
        for kj in keys:
            var += wi * w[kj] * float(row.get(kj, 0.0))
    vol = math.sqrt(max(var, 0.0))
    sharpe = (ret - rf) / vol if vol > 1e-12 else 0.0
    hhi = sum(w[k] * w[k] for k in keys)
    eq_keys = [k for k in keys if (opp.get("inputs", {}).get("asset_bucket_map", {}) or {}).get(k) == "equity"]
    fi_keys = [k for k in keys if (opp.get("inputs", {}).get("asset_bucket_map", {}) or {}).get(k) == "fixed_income"]
    eq_w = sum(w[k] for k in eq_keys)
    fi_w = sum(w[k] for k in fi_keys)
    return ScatterCandidate(
        candidate_id=label,
        volatility=float(vol),
        expected_return=float(ret),
        sharpe=float(sharpe),
        concentration_hhi=float(hhi),
        max_asset_weight=float(max(w.values()) if w else 0.0),
        mvo_efficiency_score=0.0,  # frontier 미가용 → placeholder
        feasibility_status="reference",
        overlap_score=0,
        cloud_labels="",
        has_fallback=None,
        has_universe_warning=None,
        weights={k: w[k] for k in keys},
        equity_weight=float(eq_w),
        fixed_income_weight=float(fi_w),
    )


def _solve_mvo(
    opp: dict,
    target_return: float,
    risk_asset_cap: float,
    hy_cap: float,
    label: str = "MVO (live)",
) -> tuple[ScatterCandidate | None, str | None]:
    """현재 CMA(opp.inputs) + 제약으로 min-variance 최적해 (scipy SLSQP).

    제약: w·er >= target_return, sum(risk assets) <= risk_asset_cap,
          us_high_yield <= hy_cap, long-only, sum=1.
    risk assets = equity bucket 자산 + us_high_yield (gold 는 equity bucket).
    Returns (ScatterCandidate('MVO (live)') | None, error_msg | None).
    """
    import numpy as np
    from scipy.optimize import minimize

    inputs = opp.get("inputs") or {}
    keys = list(inputs.get("asset_keys") or [])
    er_d = inputs.get("expected_returns") or {}
    cov_d = inputs.get("covariance_matrix") or {}
    bmap = inputs.get("asset_bucket_map") or {}
    if len(keys) < 2 or not er_d or not cov_d:
        return None, "MVO: CMA inputs unavailable"

    er = np.array([float(er_d.get(k, 0.0)) for k in keys])
    cov = np.array([[float((cov_d.get(a) or {}).get(b, 0.0)) for b in keys] for a in keys])
    risk_idx = [
        i for i, k in enumerate(keys)
        if bmap.get(k) == "equity" or k == "us_high_yield"
    ]
    hy_idx = keys.index("us_high_yield") if "us_high_yield" in keys else None
    n = len(keys)
    rf = float(inputs.get("risk_free_rate") or 0.0)

    def pvar(w):
        return float(w @ cov @ w)

    cons = [
        {"type": "eq", "fun": lambda w: float(w.sum() - 1.0)},
        {"type": "ineq", "fun": lambda w: float(w @ er - target_return)},
        {"type": "ineq", "fun": lambda w, ri=risk_idx: float(risk_asset_cap - sum(w[i] for i in ri))},
    ]
    bnds = [(0.0, 1.0)] * n
    if hy_idx is not None:
        bnds[hy_idx] = (0.0, float(hy_cap))

    res = minimize(
        pvar, np.full(n, 1.0 / n), method="SLSQP",
        bounds=bnds, constraints=cons,
        options={"maxiter": 800, "ftol": 1e-12},
    )
    w = res.x
    ret = float(w @ er)
    # 제약 만족 검증 (SLSQP 가 success 라도 미세 위반 가능)
    if (not res.success) or ret < target_return - 1e-4 or (
        sum(w[i] for i in risk_idx) > risk_asset_cap + 1e-4
    ):
        return None, (
            f"MVO infeasible: target_return>={target_return:.1%} / risk<={risk_asset_cap:.0%} / "
            f"HY<={hy_cap:.0%} 만족 해 없음 (target 낮추거나 cap 완화)."
        )
    vol = math.sqrt(max(pvar(w), 0.0))
    sharpe = (ret - rf) / vol if vol > 1e-12 else 0.0
    hhi = float(sum(x * x for x in w))
    eq_w = float(sum(w[i] for i, k in enumerate(keys) if bmap.get(k) == "equity"))
    fi_w = float(sum(w[i] for i, k in enumerate(keys) if bmap.get(k) == "fixed_income"))
    return (
        ScatterCandidate(
            candidate_id=label,
            volatility=float(vol),
            expected_return=ret,
            sharpe=float(sharpe),
            concentration_hhi=hhi,
            max_asset_weight=float(max(w)),
            mvo_efficiency_score=0.0,
            feasibility_status="mvo_optimal",
            overlap_score=0,
            cloud_labels="",
            has_fallback=None,
            has_universe_warning=None,
            weights={keys[i]: float(w[i]) for i in range(n)},
            equity_weight=eq_w,
            fixed_income_weight=fi_w,
        ),
        None,
    )


def _custom_cache_key(req: CustomOpportunitySetRequest, portfolio_sha: str) -> str:
    """Deterministic cache key for identical custom panel requests."""
    payload = {
        "portfolio_sha": portfolio_sha,
        "equity_total": round(req.equity_total, 9),
        "fixed_income_total": round(req.fixed_income_total, 9),
        "asset_constraints": (
            sorted(
                (k, round(v[0], 9), round(v[1], 9))
                for k, v in (req.asset_constraints or {}).items()
            )
        ),
        "selected_assets": (
            sorted(req.selected_assets) if req.selected_assets else None
        ),
        "n_candidates": req.n_candidates,
        "random_seed": req.random_seed,
        "max_attempts_multiplier": req.max_attempts_multiplier,
        "include_weights": req.include_weights,
        "risk_free_rate": round(req.risk_free_rate, 9),
        "reference_portfolios": [
            (rp.label, sorted((k, round(v, 9)) for k, v in rp.weights.items()))
            for rp in (req.reference_portfolios or [])
        ],
        "mvo": (
            [req.mvo_target_return, req.mvo_risk_asset_cap, req.mvo_hy_cap]
            if req.mvo_enabled else None
        ),
        "dirichlet_alpha": round(req.dirichlet_alpha, 6),
        "frontier": (
            [req.mvo_frontier_min, req.mvo_frontier_max, req.mvo_frontier_step]
            if req.mvo_frontier_enabled else None
        ),
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@router.post("/opportunity-set/custom", response_model=ScatterDatasetResponse)
def opportunity_set_custom(req: CustomOpportunitySetRequest) -> ScatterDatasetResponse:
    """좌측 자산 panel 의 입력 (자산 토글 + cap/floor + bucket) 으로 opportunity set 재산출.

    Review-only. R-1B.2 정합 (80:20 hard) 은 default 시 유지. 비-default bucket 시
    cap/floor + bucket sampling 만 변경하며 production allocation / TAA / product
    selection 코어는 미참조.
    """
    src = _resolve_under_engine(req.portfolio_source)
    if not src.exists() or not src.is_file():
        raise HTTPException(
            status_code=404, detail=f"portfolio_source not found: {src}",
        )
    portfolio_sha = sha256_file(src)
    cache_key = _custom_cache_key(req, portfolio_sha)
    cached = _CUSTOM_CACHE.get(cache_key)
    if cached is not None:
        return cached

    try:
        portfolio = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"invalid portfolio JSON: {e}")

    # asset_constraints: list[float, float] (Pydantic 호환) → tuple
    raw_ac = req.asset_constraints or {}
    constraints: dict[str, tuple[float, float]] | None = None
    if raw_ac:
        constraints = {}
        for k, fl_cp in raw_ac.items():
            if not isinstance(fl_cp, (list, tuple)) or len(fl_cp) != 2:
                raise HTTPException(
                    status_code=422,
                    detail=f"asset_constraints[{k!r}] must be [floor, cap]",
                )
            constraints[k] = (float(fl_cp[0]), float(fl_cp[1]))

    try:
        opp = build_opportunity_set(
            portfolio,
            n_candidates=int(req.n_candidates),
            random_seed=int(req.random_seed),
            equity_total=float(req.equity_total),
            fixed_income_total=float(req.fixed_income_total),
            asset_constraints=constraints,
            selected_assets=req.selected_assets,
            max_attempts_multiplier=int(req.max_attempts_multiplier),
            risk_free_rate=float(req.risk_free_rate),
            dirichlet_alpha=float(req.dirichlet_alpha),
        )
    except ValueError as e:
        # 입력 오류는 400 으로 frontend 에 명시 메시지 반환
        raise HTTPException(status_code=400, detail=str(e))

    cands = opp.get("candidates", [])
    if not isinstance(cands, list):
        raise HTTPException(status_code=500, detail="opportunity_set returned non-list candidates")

    tagged = compute_cloud_tags(cands, batch_signals=None)
    projected = _project_candidates_to_scatter(cands, tagged, req.include_weights)

    asset_keys = list(opp.get("inputs", {}).get("asset_keys") or [])
    asset_labels: dict[str, str] | None = None
    asset_buckets: dict[str, str] | None = None
    if req.include_weights and asset_keys:
        asset_labels, asset_buckets = _asset_metadata_for(asset_keys)

    rf_raw = (opp.get("inputs") or {}).get("risk_free_rate")
    risk_free_rate = float(rf_raw) if isinstance(rf_raw, (int, float)) else None

    sampling_warning = opp.get("diagnostics", {}).get("sampling_warning")

    # 외부 reference 포트폴리오 (Excel 등) 를 현재 CMA 로 평가해 오버레이.
    reference_points: list[ScatterCandidate] = []
    for rp in (req.reference_portfolios or []):
        rc = _reference_metrics(rp.label, rp.weights, opp)
        if rc is not None:
            reference_points.append(rc)

    # 라이브 MVO 최적해 (현재 CMA + 제약). reference_points 에 추가.
    mvo_warning: str | None = None
    if req.mvo_enabled:
        mvo_cand, mvo_err = _solve_mvo(
            opp,
            target_return=float(req.mvo_target_return),
            risk_asset_cap=float(req.mvo_risk_asset_cap),
            hy_cap=float(req.mvo_hy_cap),
        )
        if mvo_cand is not None:
            reference_points.append(mvo_cand)
        else:
            mvo_warning = mvo_err

    # MVO 효율적 프론티어 스윕 — target return 격자마다 min-var 코너해.
    if req.mvo_frontier_enabled:
        lo = float(req.mvo_frontier_min)
        hi = float(req.mvo_frontier_max)
        step = max(float(req.mvo_frontier_step), 1e-4)
        n_pts = int(round((hi - lo) / step)) + 1 if hi >= lo else 0
        for i in range(max(min(n_pts, 60), 0)):
            t = lo + i * step
            if t > hi + 1e-9:
                break
            fc, _ = _solve_mvo(
                opp,
                target_return=t,
                risk_asset_cap=float(req.mvo_risk_asset_cap),
                hy_cap=float(req.mvo_hy_cap),
                label=f"frontier {t * 100:.1f}%",
            )
            if fc is not None:
                reference_points.append(fc)

    if mvo_warning:
        sampling_warning = (
            f"{sampling_warning} | {mvo_warning}" if sampling_warning else mvo_warning
        )

    response = ScatterDatasetResponse(
        source_opportunity_set_path=f"custom:{src.relative_to(ENGINE_ROOT) if src.is_relative_to(ENGINE_ROOT) else src}",
        source_opportunity_set_sha256=portfolio_sha,
        candidate_count=len(projected),
        candidates=projected,
        include_weights=req.include_weights,
        asset_keys=asset_keys if req.include_weights else None,
        asset_labels=asset_labels,
        asset_buckets=asset_buckets,
        risk_free_rate=risk_free_rate,
        sampling_warning=sampling_warning,
        equity_bucket_total=float(req.equity_total),
        fixed_income_bucket_total=float(req.fixed_income_total),
        reference_points=reference_points or None,
    )

    # FIFO eviction (cache 작아 LRU 까지 불필요)
    if len(_CUSTOM_CACHE) >= _CUSTOM_CACHE_MAX:
        _CUSTOM_CACHE.pop(next(iter(_CUSTOM_CACHE)))
    _CUSTOM_CACHE[cache_key] = response
    return response
