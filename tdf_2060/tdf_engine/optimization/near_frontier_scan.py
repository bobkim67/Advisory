"""Near-Frontier Scan — batch frontier line scan. **review-only**.

녹색 MVO EF 라인 전체를 따라, 각 expected-return node(anchor) 근처에 "성과 손실
거의 없이(near-frontier band) 자산배분이 실질적으로 다른(active_share 큰)" 대안
포트가 존재하는지 결정론적으로 스캔한다. 단일 optimal 1점이 아니다.

frontier_neighborhood 의 solver/bound 헬퍼(solve_frontier_point, _build_bounds,
_within_bounds, _vol, NONZERO_EPS)를 재사용한다. frozen 경로 미변경.
"""
from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np
from scipy.optimize import minimize

from .frontier_neighborhood import (
    NONZERO_EPS,
    _build_bounds,
    _vol,
    _within_bounds,
    solve_frontier_point,
)

CONSTRAINT_SET = "near_frontier_scan"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _active_share(w: np.ndarray, ref: np.ndarray) -> float:
    return 0.5 * float(np.abs(w - ref).sum())


def _snap_to_grid(w: np.ndarray, grid: float) -> np.ndarray:
    """largest-remainder(Hamilton) 로 0이상·sum=1·grid 격자 유지."""
    n = len(w)
    total = int(round(1.0 / grid))
    units = np.maximum(w, 0.0) / grid
    floor = np.floor(units).astype(int)
    rem = total - int(floor.sum())
    if rem > 0:
        frac = units - floor
        order = np.argsort(-frac)
        for i in range(rem):
            floor[order[i % n]] += 1
    elif rem < 0:  # 드묾 (over-allocation)
        frac = units - np.floor(units)
        order = np.argsort(frac)
        i = 0
        while rem < 0:
            j = order[i % n]
            if floor[j] > 0:
                floor[j] -= 1
                rem += 1
            i += 1
    return floor.astype(float) * grid


def _solve_in_band(
    mu: np.ndarray,
    cov: np.ndarray,
    anchor_return: float,
    tol_return: float,
    vol_cap: float,
    *,
    objective: Callable[[np.ndarray], float],
    hy_idx: int | None,
    hy_cap: float,
    equity_idx: list[int] | None,
    equity_min: float,
    equity_max: float,
    asset_bounds: list[tuple[float, float]] | None,
    w_init: np.ndarray,
) -> np.ndarray | None:
    """near-frontier band 안에서 objective 를 최소화. band+기존 제약 적용."""
    n = len(mu)
    band_on = bool(equity_idx) and (equity_min > 0.0 or equity_max < 1.0)
    cons: list[dict[str, Any]] = [
        {"type": "eq", "fun": lambda w: float(w.sum() - 1.0)},
        {"type": "ineq", "fun": lambda w: float(tol_return - (w @ mu - anchor_return))},
        {"type": "ineq", "fun": lambda w: float(tol_return + (w @ mu - anchor_return))},
        {"type": "ineq", "fun": lambda w: float(vol_cap ** 2 - w @ cov @ w)},
    ]
    if band_on:
        ei = tuple(equity_idx or [])
        cons.append({"type": "ineq", "fun": lambda w, e=ei: float(sum(w[i] for i in e) - equity_min)})
        cons.append({"type": "ineq", "fun": lambda w, e=ei: float(equity_max - sum(w[i] for i in e))})
    bnds = _build_bounds(n, asset_bounds, hy_idx, hy_cap)

    res = minimize(
        objective, np.asarray(w_init, dtype=float), method="SLSQP",
        bounds=bnds, constraints=cons, options={"maxiter": 200, "ftol": 1e-8},
    )
    if not res.success:
        return None
    w = np.maximum(np.asarray(res.x, dtype=float), 0.0)
    s = w.sum()
    if s <= 0:
        return None
    w = w / s
    if abs(float(w @ mu) - anchor_return) > tol_return + 2e-4:
        return None
    if _vol(w, cov) > vol_cap + 2e-4:
        return None
    if hy_idx is not None and w[hy_idx] > hy_cap + 1e-6:
        return None
    if not _within_bounds(w, bnds, tol=2e-3):
        return None
    if band_on:
        eqw = float(sum(w[i] for i in (equity_idx or [])))
        if eqw < equity_min - 5e-3 or eqw > equity_max + 5e-3:
            return None
    return w


def _validate_after_snap(
    w: np.ndarray, mu: np.ndarray, cov: np.ndarray, anchor_return: float,
    tol_return: float, vol_cap: float, hy_idx: int | None, hy_cap: float,
    bnds: list[tuple[float, float]], equity_idx: list[int] | None,
    equity_min: float, equity_max: float, band_on: bool,
) -> bool:
    if abs(float(w @ mu) - anchor_return) > tol_return + 1e-4:
        return False
    if _vol(w, cov) > vol_cap + 1e-4:
        return False
    if hy_idx is not None and w[hy_idx] > hy_cap + 1e-6:
        return False
    if not _within_bounds(w, bnds, tol=1e-6):
        return False
    if band_on:
        eqw = float(sum(w[i] for i in (equity_idx or [])))
        if eqw < equity_min - 1e-6 or eqw > equity_max + 1e-6:
            return False
    return True


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def build_near_frontier_scan(
    asset_keys: list[str],
    mu: list[float] | np.ndarray,
    cov: list[list[float]] | np.ndarray,
    *,
    hy_key: str = "us_high_yield",
    hy_cap: float = 0.07,
    risk_free_rate: float = 0.0,
    target_returns: list[float] | None = None,
    tol_return_bps: float = 10.0,
    tol_vol_bps: float = 10.0,
    n_random_directions: int = 150,
    random_seed: int = 42,
    active_share_min: float = 0.05,
    active_share_emphasis: float = 0.10,
    snap_grid: float = 0.005,
    dedupe_threshold: float = 0.03,
    per_anchor_top_n: int = 5,
    cross_anchor_dedupe: bool = False,
    equity_keys: list[str] | None = None,
    equity_weight_min: float = 0.0,
    equity_weight_max: float = 1.0,
    asset_bounds: list[tuple[float, float]] | None = None,
    bucket_groups: dict[str, list[int]] | None = None,
    single_anchor_max_sharpe: bool = False,
) -> dict[str, Any]:
    mu_a = np.asarray(mu, dtype=float)
    cov_a = np.asarray(cov, dtype=float)
    n = len(asset_keys)
    if mu_a.shape != (n,) or cov_a.shape != (n, n):
        raise ValueError(f"mu/cov shape mismatch: keys={n}, mu={mu_a.shape}, cov={cov_a.shape}")
    hy_idx = asset_keys.index(hy_key) if hy_key in asset_keys else None
    if target_returns is None:
        target_returns = [round(0.05 + 0.005 * i, 4) for i in range(15)]
    tol_return = tol_return_bps / 10000.0
    tol_vol = tol_vol_bps / 10000.0
    rng = np.random.default_rng(random_seed)

    equity_idx = (
        [i for i, k in enumerate(asset_keys) if k in set(equity_keys or [])]
        if equity_keys else []
    )
    band_on = bool(equity_idx) and (equity_weight_min > 0.0 or equity_weight_max < 1.0)
    bnds = _build_bounds(n, asset_bounds, hy_idx, hy_cap)

    def _sharpe(ret: float, vol: float) -> float:
        return (ret - risk_free_rate) / vol if vol > 1e-12 else 0.0

    # ── 1) anchors = EF nodes ──
    anchors: list[dict[str, Any]] = []
    infeasible_anchors: list[int] = []
    for node_id, tr_target in enumerate(target_returns):
        w_star = solve_frontier_point(
            mu_a, cov_a, float(tr_target), hy_idx=hy_idx, hy_cap=hy_cap,
            equity_idx=equity_idx if band_on else None,
            equity_min=equity_weight_min, equity_max=equity_weight_max,
            asset_bounds=asset_bounds,
        )
        if w_star is None:
            infeasible_anchors.append(node_id)
            continue
        a_ret = float(w_star @ mu_a)
        a_vol = _vol(w_star, cov_a)
        anchors.append({
            "anchor_node_id": node_id,
            "anchor_return": a_ret,
            "anchor_vol": a_vol,
            "anchor_sharpe": _sharpe(a_ret, a_vol),
            "anchor_weights": {asset_keys[i]: float(w_star[i]) for i in range(n)},
            "_w": w_star,
        })

    # optional: max-Sharpe single-anchor diagnostic
    if single_anchor_max_sharpe and anchors:
        best = max(anchors, key=lambda a: a["anchor_sharpe"])
        anchors = [best]

    # ── 2)+3) anchor 별 directional 탐색 ──
    # 목적 = 구조적으로 다른 대안 발견. random + structured(pairwise swap / bucket
    # group max·min / support-change). HHI 최소화는 core 가 아니라 optional 단일 방향.
    groups = bucket_groups or {}
    cid = 0
    by_anchor: dict[int, list[dict[str, Any]]] = {}
    skipped_directions = 0
    dropped_after_snap = 0
    attempts_total = 0

    for a in anchors:
        node_id = a["anchor_node_id"]
        w_anchor = a["_w"]
        a_ret = a["anchor_return"]
        a_vol = a["anchor_vol"]
        vol_cap = a_vol + tol_vol
        raw: list[tuple[str, np.ndarray]] = []

        def add(label: str, objective) -> None:
            nonlocal skipped_directions, attempts_total
            attempts_total += 1
            w = _solve_in_band(
                mu_a, cov_a, a_ret, tol_return, vol_cap,
                objective=objective, hy_idx=hy_idx, hy_cap=hy_cap,
                equity_idx=equity_idx, equity_min=equity_weight_min,
                equity_max=equity_weight_max, asset_bounds=asset_bounds, w_init=w_anchor,
            )
            if w is not None:
                raw.append((label, w))
            else:
                skipped_directions += 1

        # (a) asset over/under-weight + forced-entry (linear boundary; 빠름)
        for ai in range(n):
            lbl = "force_entry" if w_anchor[ai] <= NONZERO_EPS else "overweight"
            add(f"{lbl}:{asset_keys[ai]}", lambda w, j=ai: -float(w[j]))
            if w_anchor[ai] > NONZERO_EPS:
                add(f"underweight:{asset_keys[ai]}", lambda w, j=ai: float(w[j]))

        # (b) pairwise swap — maximize w_i - w_j (active 보유분 j 기준)
        active_ix = [x for x in range(n) if w_anchor[x] > NONZERO_EPS]
        for j in active_ix:
            for i in range(n):
                if i == j:
                    continue
                add(f"swap:{asset_keys[i]}>{asset_keys[j]}",
                    lambda w, p=i, q=j: -float(w[p] - w[q]))

        # (c) bucket-level group max/min
        for gname, gidx in groups.items():
            gi = tuple(int(x) for x in gidx)
            if not gi:
                continue
            add(f"group_max:{gname}", lambda w, g=gi: -float(sum(w[x] for x in g)))
            add(f"group_min:{gname}", lambda w, g=gi: float(sum(w[x] for x in g)))

        # (d) support-change — anchor top-2 자산 강제 축소
        for ai in sorted(range(n), key=lambda x: -float(w_anchor[x]))[:2]:
            if w_anchor[ai] > NONZERO_EPS:
                add(f"support_reduce:{asset_keys[ai]}", lambda w, j=ai: float(w[j]))

        # (e) HHI 최소화 — optional 단일 방향 (diagnostic)
        add("min_hhi", lambda w: float(w @ w))

        # (f) random direction maximize — 다양화
        for jj in range(int(n_random_directions)):
            d = rng.normal(size=n)
            add(f"random:{jj}", lambda w, dd=d: -float(dd @ w))

        # ── 4) snap + 재계산 + 재검증 + active_share filter ──
        cand_list: list[dict[str, Any]] = []
        for search_dir, w in raw:
            if snap_grid and snap_grid > 0:
                w = _snap_to_grid(w, snap_grid)
                if not _validate_after_snap(
                    w, mu_a, cov_a, a_ret, tol_return, vol_cap, hy_idx, hy_cap,
                    bnds, equity_idx, equity_weight_min, equity_weight_max, band_on,
                ):
                    dropped_after_snap += 1
                    continue
            ash = _active_share(w, w_anchor)
            if ash < active_share_min:
                continue
            ret = float(w @ mu_a)
            vol = _vol(w, cov_a)
            cand_list.append({
                "_w": w,
                "anchor_node_id": node_id,
                "anchor_return": a_ret,
                "anchor_vol": a_vol,
                "candidate_return": ret,
                "candidate_volatility": vol,
                "sharpe": _sharpe(ret, vol),
                "return_gap_vs_anchor": ret - a_ret,
                "vol_gap_vs_anchor": vol - a_vol,
                "active_share_vs_anchor": ash,
                "hhi": float((w * w).sum()),
                "max_asset_weight": float(w.max()),
                "active_asset_count": int((w > NONZERO_EPS).sum()),
                "zero_count": int((w <= NONZERO_EPS).sum()),
                "us_hy_weight": float(w[hy_idx]) if hy_idx is not None else 0.0,
                "search_direction": search_dir,
                "emphasis": bool(ash >= active_share_emphasis),
            })

        # ── 5) per-anchor 선택 — frontier 에 가까운 순(vol_gap ASC) + 다양성 ──
        # "성과 유사(near-frontier)" 우선: vol_gap 작은 후보부터, 단 active_share≥min(구조 차이)
        # 이면서 후보 간 distance >= dedupe_threshold 인 것만 최대 per_anchor_top_n 개.
        # → 각 EF 구간에서 "frontier 에 붙어있으면서 서로 구조가 다른" 대안.
        cand_list.sort(key=lambda c: c["vol_gap_vs_anchor"])
        kept: list[dict[str, Any]] = []
        for c in cand_list:
            if len(kept) >= per_anchor_top_n:
                break
            if all(_active_share(c["_w"], k["_w"]) >= dedupe_threshold for k in kept):
                kept.append(c)
        by_anchor[node_id] = kept

    # ── 6) cross-anchor dedupe = 표시용 옵션 (제거하지 않음) ──
    all_cands: list[dict[str, Any]] = []
    for node_id in sorted(by_anchor.keys()):
        all_cands.extend(by_anchor[node_id])

    cross_unique: list[dict[str, Any]] = []
    for c in all_cands:
        c["cross_anchor_duplicate_of"] = None
        dup_of = None
        for u in cross_unique:
            if _active_share(c["_w"], u["_w"]) < dedupe_threshold:
                dup_of = u["anchor_node_id"]
                break
        if dup_of is None:
            cross_unique.append(c)
        elif cross_anchor_dedupe:
            c["cross_anchor_duplicate_of"] = int(dup_of)
    cross_anchor_unique_count = len(cross_unique)

    # ── 레코드 정리 (weights 부여, _w 제거) ──
    candidates: list[dict[str, Any]] = []
    for c in all_cands:
        w = c.pop("_w")
        rec = {"candidate_id": f"nfs_{cid}", **c,
               "weights": {asset_keys[i]: float(w[i]) for i in range(n)}}
        candidates.append(rec)
        cid += 1

    anchor_records = [
        {k: v for k, v in a.items() if k != "_w"} for a in anchors
    ]

    return {
        "schema_version": "near_frontier_scan.1",
        "constraint_set": CONSTRAINT_SET,
        "asset_keys": list(asset_keys),
        "anchors": anchor_records,
        "candidates": candidates,
        "summary": {
            "anchor_count": len(anchor_records),
            "infeasible_anchors": infeasible_anchors,
            "candidate_count": len(candidates),
            "cross_anchor_unique_count": cross_anchor_unique_count,
            "skipped_directions": skipped_directions,
            "dropped_after_snap": dropped_after_snap,
            "directions_per_anchor": round(attempts_total / max(len(anchor_records), 1)),
        },
        "inputs": {
            "risk_free_rate": float(risk_free_rate),
            "hy_cap": float(hy_cap),
            "hy_key": hy_key if hy_idx is not None else None,
            "tol_return_bps": float(tol_return_bps),
            "tol_vol_bps": float(tol_vol_bps),
            "n_random_directions": int(n_random_directions),
            "active_share_min": float(active_share_min),
            "active_share_emphasis": float(active_share_emphasis),
            "snap_grid": float(snap_grid),
            "dedupe_threshold": float(dedupe_threshold),
            "per_anchor_top_n": int(per_anchor_top_n),
            "bucket_groups": {k: list(v) for k, v in groups.items()} or None,
            "cross_anchor_dedupe": bool(cross_anchor_dedupe),
            "single_anchor_max_sharpe": bool(single_anchor_max_sharpe),
            "target_returns": [float(t) for t in target_returns],
            "equity_weight_band": (
                [float(equity_weight_min), float(equity_weight_max)] if band_on else None
            ),
        },
    }
