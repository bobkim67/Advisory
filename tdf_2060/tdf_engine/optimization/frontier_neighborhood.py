"""Frontier Neighborhood Explorer — near-frontier feasible portfolio search.

목적: random portfolio cloud 를 뿌리는 것이 아니다. efficient frontier 위의 각
최적(min-variance) 포트 w* 주변에, **동일한 μ/Σ 와 동일한 제약** 하에서 risk-return
이 거의 같은 다른 자산배분안이 실제로 얼마나 존재하는지 탐색한다.

제약 set (frontier_relaxed_hy_cap_only):
    - long-only      : weights >= 0
    - sum-to-one     : sum(weights) = 1
    - target return  : frontier point 는 equality (μ·w = target),
                       neighborhood candidate 는 return_tolerance_bps 허용
    - US HY <= hy_cap (default 7%)
80:20 bucket split / equity cap / asset-class band / 기타 lower·upper bound 는
이 explorer 에 적용하지 않는다 (기존 Dirichlet explorer 와 다른 feasible region).

후보 생성:
    A. local_feasible_perturbation — w* 를 null([1ᵀ; μᵀ]) 방향으로 이동. sum 과
       return 을 정확히 보존하며 long-only/HY 경계 안에서 vol 만 증가시킨다.
    B. variance_gap_shell (asset_weight_maximizer / _minimizer) — 동일 target
       return ± tolerance 와 variance gap 안에서 각 자산 weight 를 최대/최소화
       (QCQP, SLSQP). "동일 frontier 근처에서 자산별 대체 가능 범위" 를 보여준다.

이 모듈은 portfolio I/O 를 하지 않는다. 순수 μ/Σ 입력만 받아 테스트 가능하다.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.optimize import minimize

NONZERO_EPS = 1e-4
CONSTRAINT_SET = "frontier_relaxed_hy_cap_only"
INCLUDED_CONSTRAINTS = ["long_only", "sum_to_one", "target_return", "us_hy_max_7pct"]
EXCLUDED_CONSTRAINTS = [
    "equity_bucket_80_20",
    "equity_cap",
    "asset_class_band",
    "lower_bound",
    "upper_cap_except_us_hy",
]


def _vol(w: np.ndarray, cov: np.ndarray) -> float:
    return float(math.sqrt(max(float(w @ cov @ w), 0.0)))


def solve_frontier_point(
    mu: np.ndarray,
    cov: np.ndarray,
    target_return: float,
    *,
    hy_idx: int | None = None,
    hy_cap: float = 0.07,
    equity_idx: list[int] | None = None,
    equity_min: float = 0.0,
    equity_max: float = 1.0,
) -> np.ndarray | None:
    """min wᵀΣw s.t. sum(w)=1, μ·w = target (eq), w>=0, w[hy] <= hy_cap,
    그리고 (선택) equity_min <= sum(w[equity_idx]) <= equity_max (주식비중 밴드).

    밴드는 random cloud 와 **동일 feasible region** 을 위해 frontier solver 에도
    동일 제약으로 들어간다(사후 필터 아님). 밴드 비활성 = equity_idx None 또는
    min<=0 and max>=1. Returns cleaned weight (>=0, sum 1) or None if infeasible.
    """
    n = len(mu)
    band_on = bool(equity_idx) and (equity_min > 0.0 or equity_max < 1.0)

    def pvar(w: np.ndarray) -> float:
        return float(w @ cov @ w)

    cons = [
        {"type": "eq", "fun": lambda w: float(w.sum() - 1.0)},
        {"type": "eq", "fun": lambda w: float(w @ mu - target_return)},
    ]
    if band_on:
        ei = tuple(equity_idx or [])
        cons.append({"type": "ineq", "fun": lambda w, e=ei: float(sum(w[i] for i in e) - equity_min)})
        cons.append({"type": "ineq", "fun": lambda w, e=ei: float(equity_max - sum(w[i] for i in e))})
    bnds = [(0.0, 1.0)] * n
    if hy_idx is not None:
        bnds[hy_idx] = (0.0, float(hy_cap))

    res = minimize(
        pvar, np.full(n, 1.0 / n), method="SLSQP",
        bounds=bnds, constraints=cons,
        options={"maxiter": 1000, "ftol": 1e-12},
    )
    w = np.asarray(res.x, dtype=float)
    if not res.success:
        return None
    w = np.maximum(w, 0.0)
    s = w.sum()
    if s <= 0:
        return None
    w = w / s
    # 제약 검증 (SLSQP 미세 위반 / clip 후 drift 흡수)
    if abs(float(w @ mu) - target_return) > 5e-4:
        return None
    if hy_idx is not None and w[hy_idx] > hy_cap + 1e-6:
        return None
    if band_on:
        eqw = float(sum(w[i] for i in (equity_idx or [])))
        if eqw < equity_min - 5e-3 or eqw > equity_max + 5e-3:
            return None
    return w


def _null_space_directions(mu: np.ndarray, n: int) -> np.ndarray:
    """null space of A = [[1...1], [μ...]] (2×n) — sum(d)=0 과 μ·d=0 을 만족하는 d."""
    a = np.vstack([np.ones(n), np.asarray(mu, dtype=float)])
    _, s, vh = np.linalg.svd(a)
    tol = max(a.shape) * np.finfo(float).eps * (s[0] if s.size else 1.0)
    rank = int((s > tol).sum())
    return vh[rank:]  # (n-rank) × n, 행이 직교 null 방향


def _vol_gap_bucket(gap_bps: float, buckets: tuple[int, ...]) -> int | None:
    for b in sorted(buckets):
        if gap_bps <= b + 1e-6:
            return b
    return None


def _candidate_record(
    cid: int, fi: int, target_return: float, w_star: np.ndarray, w: np.ndarray,
    mu: np.ndarray, cov: np.ndarray, min_vol: float, asset_keys: list[str],
    hy_idx: int | None, vol_gaps_bps: tuple[int, ...], method: str,
) -> dict[str, Any] | None:
    ret = float(w @ mu)
    vol = _vol(w, cov)
    vol_gap = (vol - min_vol) * 10000.0
    bucket = _vol_gap_bucket(vol_gap, vol_gaps_bps)
    if bucket is None:
        return None  # shell 밖 (max gap 초과) — 제외
    diff = w - w_star
    order = np.argsort(-np.abs(diff))[:5]
    lwd = [
        {"asset": asset_keys[i], "delta": float(diff[i])}
        for i in order if abs(float(diff[i])) > 1e-6
    ]
    return {
        "candidate_id": f"fn_{cid}",
        "source_type": "frontier_neighborhood",
        "frontier_id": fi,
        "target_return": float(target_return),
        "frontier_min_volatility": float(min_vol),
        "candidate_return": ret,
        "candidate_volatility": vol,
        "return_gap_bps": (ret - target_return) * 10000.0,
        "vol_gap_bps": vol_gap,
        "vol_gap_bucket": bucket,
        "weights": {asset_keys[i]: float(w[i]) for i in range(len(w))},
        "allocation_distance_l1_from_frontier": float(np.abs(diff).sum()),
        "allocation_distance_l2_from_frontier": float(np.sqrt(float((diff ** 2).sum()))),
        "active_asset_count": int((w > NONZERO_EPS).sum()),
        "zero_asset_count": int((w <= NONZERO_EPS).sum()),
        "hhi": float((w * w).sum()),
        "max_asset_weight": float(w.max()),
        "us_hy_weight": float(w[hy_idx]) if hy_idx is not None else 0.0,
        "largest_weight_differences_vs_frontier": lwd,
        "generation_method": method,
    }


def _frontier_point_record(
    fi: int, target_return: float, w: np.ndarray, mu: np.ndarray, cov: np.ndarray,
    min_vol: float, rf: float, hy_idx: int | None, asset_keys: list[str],
) -> dict[str, Any]:
    ret = float(w @ mu)
    sharpe = (ret - rf) / min_vol if min_vol > 1e-12 else 0.0
    return {
        "frontier_id": fi,
        "target_return": float(target_return),
        "min_volatility": float(min_vol),
        "weights": {asset_keys[i]: float(w[i]) for i in range(len(w))},
        "expected_return": ret,
        "volatility": float(min_vol),
        "sharpe": float(sharpe),
        "active_asset_count": int((w > NONZERO_EPS).sum()),
        "zero_asset_count": int((w <= NONZERO_EPS).sum()),
        "us_hy_weight": float(w[hy_idx]) if hy_idx is not None else 0.0,
        "optimizer_status": "optimal",
    }


def generate_perturbation_candidates(
    w_star: np.ndarray, mu: np.ndarray, cov: np.ndarray, *,
    hy_idx: int | None, hy_cap: float, min_vol: float, max_gap_bps: int,
    n_directions: int, steps_per_direction: int, rng: np.random.Generator,
) -> list[np.ndarray]:
    """Method A — null([1ᵀ; μᵀ]) 방향 perturbation. return/sum 정확 보존.

    방향은 frontier point 의 **활성 자산(support, w*>eps) 내부**에서만 생성한다
    (0% 자산은 그대로 0 유지). frontier 코너해는 0% 자산이 많아 전체 null-space
    방향은 대부분 long-only 경계에 즉시 막히기 때문 — 활성 자산 재분배가 dense
    near-frontier cloud 를 만든다. 0% 자산의 활성화 가능 여부는 method B 가 담당.

    각 방향 d 마다 (a) long-only/HY 경계 t 범위와 (b) vol <= min_vol+max_gap 인
    shell t 범위(이차식 해)를 교집합해 그 안에서만 t 를 샘플 → 항상 shell·feasible.
    """
    n = len(w_star)
    active = [i for i in range(n) if w_star[i] > NONZERO_EPS]
    if len(active) < 3:
        active = list(range(n))  # support 가 너무 작으면 전체로 fallback
    mu_act = np.asarray([float(mu[i]) for i in active], dtype=float)
    basis_act = _null_space_directions(mu_act, len(active))
    if basis_act.shape[0] == 0:
        return []
    cap = min_vol + max_gap_bps / 10000.0
    cap2, c0 = cap * cap, min_vol * min_vol
    sw = cov @ w_star
    out: list[np.ndarray] = []
    for _ in range(n_directions):
        coef = rng.standard_normal(basis_act.shape[0])
        d_act = coef @ basis_act
        d = np.zeros(n)
        for j, i in enumerate(active):
            d[i] = d_act[j]
        nrm = float(np.linalg.norm(d))
        if nrm < 1e-12:
            continue
        d = d / nrm
        # (a) bound-feasible t 범위: w*+t·d >= 0, (w*+t·d)[hy] <= hy_cap
        t_lo, t_hi = -np.inf, np.inf
        for i in range(n):
            di = float(d[i])
            if di > 1e-12:
                t_lo = max(t_lo, -float(w_star[i]) / di)
            elif di < -1e-12:
                t_hi = min(t_hi, -float(w_star[i]) / di)
        if hy_idx is not None:
            dh = float(d[hy_idx])
            slack = hy_cap - float(w_star[hy_idx])
            if dh > 1e-12:
                t_hi = min(t_hi, slack / dh)
            elif dh < -1e-12:
                t_lo = max(t_lo, slack / dh)
        if not (t_lo < t_hi):
            continue
        # (b) shell t 범위: a·t² + b·t + (c0 - cap²) <= 0  (vol² ≤ cap²)
        a = float(d @ cov @ d)
        b = 2.0 * float(d @ sw)
        if a <= 1e-18:
            continue
        disc = b * b - 4.0 * a * (c0 - cap2)
        if disc <= 0:
            continue
        sq = math.sqrt(disc)
        lo = max(t_lo, (-b - sq) / (2.0 * a))
        hi = min(t_hi, (-b + sq) / (2.0 * a))
        if not (lo < hi) or not math.isfinite(lo) or not math.isfinite(hi):
            continue
        for _s in range(steps_per_direction):
            t = float(rng.uniform(lo, hi))
            if abs(t) < 1e-9:
                continue
            out.append(np.maximum(w_star + t * d, 0.0))
    return out


def solve_asset_extreme(
    mu: np.ndarray, cov: np.ndarray, target_return: float, asset_idx: int, *,
    maximize: bool, hy_idx: int | None, hy_cap: float, vol_cap: float,
    return_tol: float, w_init: np.ndarray,
) -> np.ndarray | None:
    """Method B — variance gap shell 안에서 asset_idx weight 최대/최소화 (QCQP)."""
    n = len(mu)
    sign = -1.0 if maximize else 1.0

    def obj(w: np.ndarray) -> float:
        return sign * float(w[asset_idx])

    cons = [
        {"type": "eq", "fun": lambda w: float(w.sum() - 1.0)},
        {"type": "ineq", "fun": lambda w: float(return_tol - (w @ mu - target_return))},
        {"type": "ineq", "fun": lambda w: float(return_tol + (w @ mu - target_return))},
        {"type": "ineq", "fun": lambda w: float(vol_cap ** 2 - w @ cov @ w)},
    ]
    bnds = [(0.0, 1.0)] * n
    if hy_idx is not None:
        bnds[hy_idx] = (0.0, float(hy_cap))

    res = minimize(
        obj, np.asarray(w_init, dtype=float), method="SLSQP",
        bounds=bnds, constraints=cons,
        options={"maxiter": 1000, "ftol": 1e-10},
    )
    if not res.success:
        return None
    w = np.maximum(np.asarray(res.x, dtype=float), 0.0)
    s = w.sum()
    if s <= 0:
        return None
    w = w / s
    if abs(float(w @ mu) - target_return) > return_tol + 1e-4:
        return None
    if _vol(w, cov) > vol_cap + 1e-4:
        return None
    if hy_idx is not None and w[hy_idx] > hy_cap + 1e-6:
        return None
    return w


def generate_random_cloud(
    asset_keys: list[str], mu: np.ndarray, cov: np.ndarray, *,
    hy_idx: int | None, hy_cap: float, n_samples: int, rf: float,
    alpha: float = 1.0, random_seed: int = 42,
    equity_idx: list[int] | None = None,
    equity_min: float = 0.0, equity_max: float = 1.0,
) -> list[dict[str, Any]]:
    """Random portfolio cloud — relaxed feasible region (long-only, sum=1, HY<=cap,
    + 선택 equity 밴드 equity_min<=sum(w[equity_idx])<=equity_max).

    Dirichlet(α) over **모든 자산** (80:20 bucket / equity cap 미적용). US HY > cap
    또는 equity 밴드 밖 샘플은 reject/resample. target return equality 는 적용하지
    않는다(cloud 는 feasible 전체를 채운다). frontier solver 와 **동일 제약** 공유.
    좁은 밴드는 reject 비효율 → max_attempts 도달 시 채운 만큼 partial 반환.
    """
    n = len(asset_keys)
    band_on = bool(equity_idx) and (equity_min > 0.0 or equity_max < 1.0)
    ei = list(equity_idx or [])
    rng = np.random.default_rng(random_seed)
    out: list[dict[str, Any]] = []
    cid = 0
    attempts = 0
    max_attempts = max(n_samples * (200 if band_on else 40), 2000)
    batch_size = min(max(n_samples * 2, 1000), 20000)
    while len(out) < n_samples and attempts < max_attempts:
        batch = rng.dirichlet(np.full(n, alpha), size=batch_size)
        attempts += batch_size
        for w in batch:
            if len(out) >= n_samples:
                break
            if hy_idx is not None and w[hy_idx] > hy_cap:
                continue  # HY<=cap reject
            eqw = float(sum(w[i] for i in ei)) if band_on else 0.0
            if band_on and (eqw < equity_min - 1e-9 or eqw > equity_max + 1e-9):
                continue  # equity 밴드 밖 reject
            ret = float(w @ mu)
            vol = _vol(w, cov)
            out.append({
                "candidate_id": f"rc_{cid}",
                "source_type": "random_cloud",
                "volatility": vol,
                "expected_return": ret,
                "sharpe": (ret - rf) / vol if vol > 1e-12 else 0.0,
                "hhi": float((w * w).sum()),
                "max_asset_weight": float(w.max()),
                "weights": {asset_keys[i]: float(w[i]) for i in range(n)},
                "active_asset_count": int((w > NONZERO_EPS).sum()),
                "zero_asset_count": int((w <= NONZERO_EPS).sum()),
                "us_hy_weight": float(w[hy_idx]) if hy_idx is not None else 0.0,
                "equity_weight": float(sum(w[i] for i in ei)) if ei else None,
            })
            cid += 1
    return out


def _summary(
    fi: int, target_return: float, w_star: np.ndarray, min_vol: float,
    cands: list[dict[str, Any]], asset_keys: list[str],
    vol_gaps_bps: tuple[int, ...], hy_idx: int | None, hy_cap: float,
) -> dict[str, Any]:
    n_by: dict[str, int] = {}
    max_dist: dict[str, float] = {}
    med_dist: dict[str, float] = {}
    max_act: dict[str, int] = {}
    min_act: dict[str, int] = {}
    ranges: dict[str, dict[str, dict[str, float]]] = {}
    for b in sorted(vol_gaps_bps):
        key = str(b)
        sub = [c for c in cands if c["vol_gap_bps"] <= b + 1e-6]
        n_by[key] = len(sub)
        dists = [c["allocation_distance_l1_from_frontier"] for c in sub]
        max_dist[key] = max(dists) if dists else 0.0
        med_dist[key] = float(np.median(dists)) if dists else 0.0
        acts = [c["active_asset_count"] for c in sub]
        max_act[key] = max(acts) if acts else int((w_star > NONZERO_EPS).sum())
        min_act[key] = min(acts) if acts else int((w_star > NONZERO_EPS).sum())
        rng_d: dict[str, dict[str, float]] = {}
        for i, k in enumerate(asset_keys):
            ws = [c["weights"][k] for c in sub]
            fw = float(w_star[i])
            rng_d[k] = {
                "min": min(ws) if ws else fw,
                "max": max(ws) if ws else fw,
                "frontier": fw,
            }
        ranges[key] = rng_d
    hy_binding = hy_idx is not None and float(w_star[hy_idx]) >= hy_cap - 1e-4
    return {
        "frontier_id": fi,
        "target_return": float(target_return),
        "frontier_min_volatility": float(min_vol),
        "n_candidates_by_vol_gap": n_by,
        "max_allocation_distance_by_vol_gap": max_dist,
        "median_allocation_distance_by_vol_gap": med_dist,
        "max_active_asset_count_by_vol_gap": max_act,
        "min_active_asset_count_by_vol_gap": min_act,
        "asset_weight_ranges_by_vol_gap": ranges,
        "constraint_binding_status": {"us_hy_at_cap": bool(hy_binding)},
    }


def build_frontier_neighborhood(
    asset_keys: list[str],
    mu: list[float] | np.ndarray,
    cov: list[list[float]] | np.ndarray,
    *,
    hy_key: str = "us_high_yield",
    hy_cap: float = 0.07,
    risk_free_rate: float = 0.0,
    target_returns: list[float] | None = None,
    vol_gaps_bps: tuple[int, ...] = (10, 25, 50, 100),
    return_tolerance_bps: float = 5.0,
    n_directions: int = 80,
    steps_per_direction: int = 2,
    random_seed: int = 42,
    method_b: bool = True,
    include_neighborhood: bool = True,
    include_random_cloud: bool = False,
    n_random_samples: int = 4000,
    random_cloud_alpha: float = 1.0,
    equity_keys: list[str] | None = None,
    equity_weight_min: float = 0.0,
    equity_weight_max: float = 1.0,
) -> dict[str, Any]:
    """frontier point + near-frontier neighborhood candidates 를 생성.

    frontier point 와 모든 candidate 는 동일한 (asset_keys, mu, cov) 를 공유한다.
    """
    mu_a = np.asarray(mu, dtype=float)
    cov_a = np.asarray(cov, dtype=float)
    n = len(asset_keys)
    if mu_a.shape != (n,) or cov_a.shape != (n, n):
        raise ValueError(
            f"mu/cov shape mismatch: asset_keys={n}, mu={mu_a.shape}, cov={cov_a.shape}"
        )
    hy_idx = asset_keys.index(hy_key) if hy_key in asset_keys else None
    if target_returns is None:
        target_returns = [round(0.05 + 0.005 * i, 4) for i in range(15)]  # 5%~12% (0.5%)
    return_tol = return_tolerance_bps / 10000.0
    max_gap_bps = max(vol_gaps_bps)
    rng = np.random.default_rng(random_seed)

    frontier_points: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    cid = 0

    # 주식비중 밴드 — random cloud + EF solver 양쪽에 동일 적용 (사후 필터 아님).
    equity_idx = (
        [i for i, k in enumerate(asset_keys) if k in set(equity_keys or [])]
        if equity_keys else []
    )
    band_on = bool(equity_idx) and (equity_weight_min > 0.0 or equity_weight_max < 1.0)

    for fi, tr_target in enumerate(target_returns):
        w_star = solve_frontier_point(
            mu_a, cov_a, float(tr_target), hy_idx=hy_idx, hy_cap=hy_cap,
            equity_idx=equity_idx if band_on else None,
            equity_min=equity_weight_min, equity_max=equity_weight_max,
        )
        if w_star is None:
            frontier_points.append({
                "frontier_id": fi,
                "target_return": float(tr_target),
                "equity_weight": None,
                "min_volatility": None,
                "weights": None, "expected_return": None, "volatility": None,
                "sharpe": None, "active_asset_count": None, "zero_asset_count": None,
                "us_hy_weight": None, "optimizer_status": "infeasible",
            })
            continue
        min_vol = _vol(w_star, cov_a)
        tr = float(w_star @ mu_a)  # 실현 수익률 (neighborhood + record 용 target)
        eq_w = float(sum(w_star[i] for i in equity_idx)) if equity_idx else None
        rec = _frontier_point_record(fi, tr, w_star, mu_a, cov_a, min_vol, risk_free_rate, hy_idx, asset_keys)
        rec["equity_weight"] = eq_w
        frontier_points.append(rec)

        if not include_neighborhood:
            continue  # frontier point/line 만 (Random Cloud + EF Overlay 모드)

        # Method A — local feasible perturbation
        for w in generate_perturbation_candidates(
            w_star, mu_a, cov_a, hy_idx=hy_idx, hy_cap=hy_cap, min_vol=min_vol,
            max_gap_bps=max_gap_bps, n_directions=n_directions,
            steps_per_direction=steps_per_direction, rng=rng,
        ):
            rec = _candidate_record(
                cid, fi, tr, w_star, w, mu_a, cov_a, min_vol, asset_keys,
                hy_idx, vol_gaps_bps, "local_feasible_perturbation",
            )
            if rec is not None:
                candidates.append(rec)
                cid += 1

        # Method B — variance gap shell asset weight max/min (QCQP)
        if method_b:
            for gap in vol_gaps_bps:
                vol_cap = min_vol + gap / 10000.0
                for ai in range(n):
                    for maximize in (True, False):
                        w = solve_asset_extreme(
                            mu_a, cov_a, tr, ai, maximize=maximize, hy_idx=hy_idx,
                            hy_cap=hy_cap, vol_cap=vol_cap, return_tol=return_tol,
                            w_init=w_star,
                        )
                        if w is None:
                            continue
                        method = "asset_weight_maximizer" if maximize else "asset_weight_minimizer"
                        rec = _candidate_record(
                            cid, fi, tr, w_star, w, mu_a, cov_a, min_vol, asset_keys,
                            hy_idx, vol_gaps_bps, method,
                        )
                        if rec is not None:
                            candidates.append(rec)
                            cid += 1

        summaries.append(
            _summary(
                fi, tr, w_star, min_vol,
                [c for c in candidates if c["frontier_id"] == fi],
                asset_keys, vol_gaps_bps, hy_idx, hy_cap,
            )
        )

    # Random Cloud — relaxed feasible region (long-only, sum=1, HY<=cap, + equity 밴드).
    # frontier solver 와 동일 제약(밴드) 공유 — target return equality 만 없음.
    random_cloud = (
        generate_random_cloud(
            asset_keys, mu_a, cov_a, hy_idx=hy_idx, hy_cap=hy_cap,
            n_samples=n_random_samples, rf=risk_free_rate,
            alpha=random_cloud_alpha, random_seed=random_seed,
            equity_idx=equity_idx,
            equity_min=equity_weight_min, equity_max=equity_weight_max,
        )
        if include_random_cloud
        else None
    )

    constraint_set = (
        "random_cloud_relaxed_hy_cap_equity_band" if band_on else CONSTRAINT_SET
    )
    included = list(INCLUDED_CONSTRAINTS) + (["equity_weight_band"] if band_on else [])

    return {
        "schema_version": "frontier_neighborhood.1",
        "constraint_set": constraint_set,
        "included_constraints": included,
        "excluded_constraints": list(EXCLUDED_CONSTRAINTS),
        "asset_keys": list(asset_keys),
        "frontier_points": frontier_points,
        "candidates": candidates,
        "random_cloud": random_cloud,
        "summary": summaries,
        "inputs": {
            "expected_returns": {asset_keys[i]: float(mu_a[i]) for i in range(n)},
            "risk_free_rate": float(risk_free_rate),
            "hy_cap": float(hy_cap),
            "hy_key": hy_key if hy_idx is not None else None,
            "return_tolerance_bps": float(return_tolerance_bps),
            "vol_gaps_bps": list(vol_gaps_bps),
            "target_returns": [float(t) for t in target_returns],
            "include_neighborhood": bool(include_neighborhood),
            "include_random_cloud": bool(include_random_cloud),
            "n_random_samples": int(n_random_samples) if include_random_cloud else 0,
            "random_cloud_alpha": float(random_cloud_alpha),
            "equity_weight_band": [float(equity_weight_min), float(equity_weight_max)] if band_on else None,
        },
    }
