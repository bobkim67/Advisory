"""R-1B-lite — SAA Opportunity Set Candidate Generator (read-only diagnostic).

본 모듈은 SAA 를 단일 max-Sharpe 자동 산출물이 아니라, 운용역이 선택할 수 있는
candidate opportunity set 으로 제시한다. production allocation / TAA / product
selection 결과를 절대 변경하지 않는다.

Spec: tdf_2060/docs/r1_saa_opportunity_set_explorer_spec.md (R-1B-lite, R-1B.2 corrected).

R-1B.2 update — 사용자 결정 (2026-05-13):
  80:20 은 평가 지표가 아니라 **hard constraint**. 따라서 candidate generation 자체가
  equity 합 = 0.80, fixed_income 합 = 0.20 을 강제하며, 80:20 거리 metric 은 모두 제거.

R-1B-lite scope (R-1B.2):
- bucket-constrained Dirichlet candidate generation (seed=42, n=10000)
   - equity 5-asset Dirichlet × 0.80
   - fixed_income 4-asset Dirichlet × 0.20
- core metrics (sharpe / full+intra-bucket HHI / full+intra-bucket max_w / frontier_efficiency_gap)
- reference points:
    ref_max_sharpe                 (= diagnostics.saa_diagnostics.saa_weights; bucket 위반 가능)
    ref_80_20_equal_intra_bucket   (eq 80% 5×0.16 + FI 20% 4×0.05)
- JSON dump + summary md

deferred to R-1C+:
- ref_min_vol / ref_equal_weight / ref_user_selected
- scatterplot PNG
- similar_search (키 자체 dump 하지 않음)
- clustering / Pareto
- optional filter 활성화
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "r1b_lite.2"  # R-1B.2: bucket-constrained sampling correction
DEFAULT_N_CANDIDATES = 10_000
DEFAULT_SEED = 42
NONZERO_EPS = 1e-4
ZERO_WEIGHT_THRESHOLD = 0.005
FRONTIER_GRID_POINTS = 31

EQUITY_BUCKET = "equity"
FIXED_INCOME_BUCKET = "fixed_income"

# R-1B.2 hard bucket totals
EQUITY_BUCKET_TOTAL = 0.80
FIXED_INCOME_BUCKET_TOTAL = 0.20


# ---------------------------------------------------------------------------
# Telemetry guard
# ---------------------------------------------------------------------------


def _require_direct_saa_and_cma(portfolio: dict[str, Any]) -> dict[str, Any]:
    """direct SAA telemetry + CMA presence check.

    portfolio.asset_allocation 의 final implemented weights 는 ref_max_sharpe
    source 로 사용하지 않는다 — 본 함수가 반환하는 saa_diagnostics.saa_weights 만
    Current SAA 로 인정된다.
    """
    diag = portfolio.get("diagnostics") or {}
    saa = diag.get("saa_diagnostics") or {}
    cma = saa.get("cma") or {}
    if not saa.get("saa_weights"):
        raise ValueError(
            "R-1B-lite opportunity set requires direct SAA telemetry "
            "`diagnostics.saa_diagnostics.saa_weights` (E-6.2 T-6). "
            "`portfolio.asset_allocation[*].weight` is final implemented "
            "(TAA + projection + selection) and must NOT be used as ref_max_sharpe source."
        )
    for need in ("asset_keys", "expected_returns", "volatilities", "covariance_matrix"):
        if not cma.get(need):
            raise ValueError(
                f"R-1B-lite opportunity set requires `saa_diagnostics.cma.{need}` "
                "(E-6.2 T-1~T-4). re-run build_portfolio with telemetry patch."
            )
    return saa


def _extract_bucket_map(portfolio: dict[str, Any], asset_keys: list[str]) -> dict[str, str]:
    """portfolio.asset_allocation 의 bucket 매핑 추출.

    bucket 매핑은 final implemented weights 와 무관하게 asset → bucket lookup
    table 로만 사용한다 (ref_max_sharpe source 와 다름).
    """
    allocations = portfolio.get("asset_allocation") or []
    raw_map: dict[str, str] = {}
    for row in allocations:
        ak = row.get("asset_key")
        bk = row.get("bucket")
        if ak is not None and bk is not None:
            raw_map[str(ak)] = str(bk)
    missing = [k for k in asset_keys if k not in raw_map]
    if missing:
        raise ValueError(
            f"R-1B-lite opportunity set: bucket map missing for {missing}. "
            "portfolio.asset_allocation[*].bucket required."
        )
    return {k: raw_map[k] for k in asset_keys}


# ---------------------------------------------------------------------------
# Linear algebra helpers (pure-python, deterministic ordering)
# ---------------------------------------------------------------------------


def _vec(d: dict[str, float], keys: list[str]) -> list[float]:
    return [float(d.get(k, 0.0)) for k in keys]


def _mat(d: dict[str, dict[str, float]], keys: list[str]) -> list[list[float]]:
    return [[float((d.get(ki) or {}).get(kj, 0.0)) for kj in keys] for ki in keys]


def _matvec(mat: list[list[float]], v: list[float]) -> list[float]:
    n = len(v)
    out = [0.0] * n
    for i in range(n):
        row = mat[i]
        s = 0.0
        for j in range(n):
            s += row[j] * v[j]
        out[i] = s
    return out


def _portfolio_return_vol(
    weights: list[float], er: list[float], cov: list[list[float]]
) -> tuple[float, float]:
    sigma_w = _matvec(cov, weights)
    var = sum(weights[i] * sigma_w[i] for i in range(len(weights)))
    var = max(var, 0.0)
    return sum(weights[i] * er[i] for i in range(len(weights))), math.sqrt(var)


def _sharpe(ret: float, vol: float, rf: float) -> float:
    if vol <= 1e-12:
        return float("nan")
    return (ret - rf) / vol


# ---------------------------------------------------------------------------
# Frontier (re-use E-9 solver for mvo_efficiency_score interpolation)
# ---------------------------------------------------------------------------


def _build_frontier_points(
    er: list[float], cov: list[list[float]], grid_points: int = FRONTIER_GRID_POINTS
) -> list[tuple[float, float]]:
    """E-9 와 동일한 SLSQP grid scan. 반환은 (volatility, expected_return) 정렬 리스트.

    long-only + sum=1 만 적용 (Phase D relaxed 정책 정합).
    """
    import numpy as np
    from scipy.optimize import minimize

    n = len(er)
    mu = np.asarray(er, dtype=float)
    sigma = np.asarray(cov, dtype=float)
    x0 = np.ones(n) / n
    bounds = [(0.0, 1.0)] * n

    def _solve_min_var_no_target() -> tuple[list[float], float]:
        cons = [{"type": "eq", "fun": lambda w: float(w.sum() - 1.0),
                 "jac": lambda w: np.ones(n)}]
        result = minimize(
            lambda w: float(w @ sigma @ w),
            x0,
            jac=lambda w: 2.0 * (sigma @ w),
            method="SLSQP",
            constraints=cons,
            bounds=bounds,
            options={"maxiter": 300, "ftol": 1e-10, "disp": False},
        )
        return result.x.tolist(), max(float(result.fun), 0.0)

    def _solve_at_target(tr: float) -> tuple[list[float], float, bool]:
        cons = [
            {"type": "eq", "fun": lambda w: float(w.sum() - 1.0),
             "jac": lambda w: np.ones(n)},
            {"type": "eq", "fun": lambda w, t=tr: float(w @ mu - t),
             "jac": lambda w: mu},
        ]
        result = minimize(
            lambda w: float(w @ sigma @ w),
            x0,
            jac=lambda w: 2.0 * (sigma @ w),
            method="SLSQP",
            constraints=cons,
            bounds=bounds,
            options={"maxiter": 300, "ftol": 1e-10, "disp": False},
        )
        return result.x.tolist(), max(float(result.fun), 0.0), bool(result.success)

    mv_w, _ = _solve_min_var_no_target()
    mv_ret, _ = _portfolio_return_vol(mv_w, er, cov)
    upper_ret = max(er)
    lower_ret = mv_ret
    if upper_ret <= lower_ret + 1e-9:
        upper_ret = lower_ret + 1e-3
    grid = [
        lower_ret + (upper_ret - lower_ret) * i / max(grid_points - 1, 1)
        for i in range(grid_points)
    ]

    points: list[tuple[float, float]] = []
    for tr in grid:
        w, _var, ok = _solve_at_target(tr)
        if not ok:
            continue
        ret, vol = _portfolio_return_vol(w, er, cov)
        points.append((vol, ret))
    points.sort(key=lambda p: p[0])
    # 중복 vol 제거 (interpolation 안전)
    dedup: list[tuple[float, float]] = []
    for v, r in points:
        if dedup and abs(v - dedup[-1][0]) < 1e-12:
            if r > dedup[-1][1]:
                dedup[-1] = (v, r)
            continue
        dedup.append((v, r))
    return dedup


def _frontier_er_at_vol(
    frontier_points: list[tuple[float, float]], vol: float
) -> tuple[float, bool]:
    """선형 interpolation. boundary 밖이면 (clipped value, True)."""
    if not frontier_points:
        return float("nan"), True
    if vol <= frontier_points[0][0]:
        return frontier_points[0][1], (vol < frontier_points[0][0] - 1e-12)
    if vol >= frontier_points[-1][0]:
        return frontier_points[-1][1], (vol > frontier_points[-1][0] + 1e-12)
    # bisect
    lo, hi = 0, len(frontier_points) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if frontier_points[mid][0] <= vol:
            lo = mid
        else:
            hi = mid
    v0, r0 = frontier_points[lo]
    v1, r1 = frontier_points[hi]
    if v1 - v0 < 1e-15:
        return (r0 + r1) / 2.0, False
    t = (vol - v0) / (v1 - v0)
    return r0 + t * (r1 - r0), False


# ---------------------------------------------------------------------------
# Reference: 80/20 equal intra-bucket reference (R-1B.2 rename)
# ---------------------------------------------------------------------------


def _build_ref_equal_intra_bucket_weights(
    asset_keys: list[str],
    bucket_map: dict[str, str],
    equity_total: float = EQUITY_BUCKET_TOTAL,
    fixed_income_total: float = FIXED_INCOME_BUCKET_TOTAL,
) -> list[float]:
    """Equity bucket 합 / FI bucket 합 을 intra-bucket 균등 분배.

    R-1B.2 정합: bucket 합은 (equity_total, fixed_income_total) 로 hard. intra-bucket
    만 균등. Phase 6.5 — bucket totals 자유 입력 지원 (기본 0.80 / 0.20).
    """
    eq_keys = [k for k in asset_keys if bucket_map[k] == EQUITY_BUCKET]
    fi_keys = [k for k in asset_keys if bucket_map[k] == FIXED_INCOME_BUCKET]
    if equity_total > 1e-9 and not eq_keys:
        raise ValueError(
            "ref_equal_intra_bucket: equity_total > 0 but no equity asset present."
        )
    if fixed_income_total > 1e-9 and not fi_keys:
        raise ValueError(
            "ref_equal_intra_bucket: fixed_income_total > 0 but no fixed_income asset present."
        )
    eq_w = (equity_total / len(eq_keys)) if eq_keys else 0.0
    fi_w = (fixed_income_total / len(fi_keys)) if fi_keys else 0.0
    out = []
    for k in asset_keys:
        bk = bucket_map[k]
        if bk == EQUITY_BUCKET:
            out.append(eq_w)
        elif bk == FIXED_INCOME_BUCKET:
            out.append(fi_w)
        else:
            raise ValueError(
                f"ref_equal_intra_bucket: unsupported bucket '{bk}' for asset '{k}'."
            )
    return out


# Backward-compat alias (do not remove — referenced by older code paths).
_build_ref_80_20_equal_intra_bucket_weights = _build_ref_equal_intra_bucket_weights


# ---------------------------------------------------------------------------
# Bucket-level constrained sampling (Phase 6.5 — cap/floor + free bucket)
# ---------------------------------------------------------------------------


def _sample_bucket_constrained(
    rng,
    n_target: int,
    n_keys: int,
    bucket_total: float,
    floors: list[float],
    caps: list[float],
    max_attempts_multiplier: int = 5,
    dirichlet_alpha: float = 1.0,
) -> tuple[list[list[float]], int]:
    """Bucket 단위 Dirichlet × bucket_total → cap/floor rejection sampling.

    Returns (accepted_rows, total_attempts).
      accepted_rows : list of length-`n_keys` lists summing to `bucket_total`.
      total_attempts: 누적 Dirichlet draws (rejection 포함).

    Backward-compat 보장:
      cap/floor 기본값 (0, bucket_total) + bucket_total = EQUITY_BUCKET_TOTAL 인 경우
      Dirichlet draws 가 항상 valid 라 단일 batch (size=n_target) 1회 호출. 따라서
      legacy code path 의 rng state 진행과 동일 (단, dirichlet → renormalize → scale
      순서 동일).
    """
    import numpy as np

    if n_keys == 0:
        if bucket_total > 1e-9:
            raise ValueError(
                f"_sample_bucket_constrained: bucket_total={bucket_total} > 0 "
                f"but no assets in bucket."
            )
        return [], 0

    if bucket_total <= 1e-12:
        # zero bucket: 모든 후보가 zero vector
        return [[0.0] * n_keys for _ in range(n_target)], 0

    if n_keys == 1:
        # single-asset bucket: weight = bucket_total (feasible 시 동일 후보 n_target개)
        if floors[0] - 1e-9 <= bucket_total <= caps[0] + 1e-9:
            return [[bucket_total] for _ in range(n_target)], 0
        return [], 0

    # dirichlet_alpha: 1.0=내부 균등(기본), <1=코너/sparse 선호. 대칭 Dirichlet.
    alpha = np.full(n_keys, float(dirichlet_alpha), dtype=float)
    floors_arr = np.asarray(floors, dtype=float)
    caps_arr = np.asarray(caps, dtype=float)

    accepted: list[list[float]] = []
    total_attempts = 0
    max_attempts = max(n_target * max(max_attempts_multiplier, 1), n_target * 2)
    # 첫 batch 는 size=n_target. constraint 가 없는 경우 (legacy default) 1회로 종료.
    first_batch = True

    while len(accepted) < n_target and total_attempts < max_attempts:
        bs = (
            n_target if first_batch
            else min(n_target, max(max_attempts - total_attempts, 1))
        )
        first_batch = False

        samples = rng.dirichlet(alpha, size=bs)
        # ULP-safe renormalize (legacy 와 동일)
        row_sums = samples.sum(axis=1, keepdims=True)
        nonzero = (row_sums > 0).flatten()
        samples = samples[nonzero] / row_sums[nonzero] * bucket_total

        valid_mask = np.all(
            (samples >= floors_arr - 1e-12) & (samples <= caps_arr + 1e-12),
            axis=1,
        )
        valid = samples[valid_mask]
        if valid.shape[0] > 0:
            need = n_target - len(accepted)
            take = valid[:need]
            accepted.extend(take.tolist())
        total_attempts += bs

    return accepted, total_attempts


# ---------------------------------------------------------------------------
# Candidate metrics
# ---------------------------------------------------------------------------


def _metrics_for_weights(
    candidate_id: str,
    weights: list[float],
    asset_keys: list[str],
    bucket_map: dict[str, str],
    er: list[float],
    cov: list[list[float]],
    rf: float,
    frontier_points: list[tuple[float, float]],
) -> dict[str, Any]:
    """Compute R-1B.2 metric set for a candidate weight vector.

    Bucket-distance / full-weight-distance metric 은 R-1B.2 에서 제거됨 (80:20 hard
    constraint 도입으로 의미 상실). 대신 intra-bucket HHI / max_w 4종 추가.
    """
    n = len(asset_keys)
    ret, vol = _portfolio_return_vol(weights, er, cov)
    sharpe = _sharpe(ret, vol, rf)

    eq_w_total = 0.0
    fi_w_total = 0.0
    eq_vals: list[float] = []
    fi_vals: list[float] = []
    for i, k in enumerate(asset_keys):
        bk = bucket_map[k]
        if bk == EQUITY_BUCKET:
            eq_w_total += weights[i]
            eq_vals.append(weights[i])
        elif bk == FIXED_INCOME_BUCKET:
            fi_w_total += weights[i]
            fi_vals.append(weights[i])

    max_w = max(weights) if weights else 0.0
    nz = sum(1 for w in weights if w > NONZERO_EPS)
    hhi = sum(w * w for w in weights)

    # intra-bucket HHI (renormalized to bucket=1). bucket total 이 0 인 reference
    # (예: ref_max_sharpe 의 fi=0) 의 경우 None.
    def _intra_hhi(vals: list[float], total: float) -> float | None:
        if total <= 1e-12:
            return None
        return sum((v / total) ** 2 for v in vals)

    eq_intra_hhi = _intra_hhi(eq_vals, eq_w_total)
    fi_intra_hhi = _intra_hhi(fi_vals, fi_w_total)
    eq_max_w = max(eq_vals) if eq_vals else 0.0
    fi_max_w = max(fi_vals) if fi_vals else 0.0

    front_er_at_vol, extrap = _frontier_er_at_vol(frontier_points, vol)
    if math.isfinite(front_er_at_vol):
        mvo_gap = front_er_at_vol - ret
    else:
        mvo_gap = float("nan")

    feasibility = "feasible"
    if extrap or not math.isfinite(mvo_gap):
        feasibility = "degenerate"

    return {
        "candidate_id": candidate_id,
        "weights": {asset_keys[i]: float(weights[i]) for i in range(n)},
        "expected_return": float(ret),
        "volatility": float(vol),
        "sharpe": (float(sharpe) if math.isfinite(sharpe) else None),
        "equity_weight": float(eq_w_total),
        "fixed_income_weight": float(fi_w_total),
        "max_asset_weight": float(max_w),
        "nonzero_asset_count": int(nz),
        "concentration_hhi": float(hhi),
        "equity_intra_hhi": (float(eq_intra_hhi) if eq_intra_hhi is not None else None),
        "fixed_income_intra_hhi": (
            float(fi_intra_hhi) if fi_intra_hhi is not None else None
        ),
        "equity_max_asset_weight": float(eq_max_w),
        "fixed_income_max_asset_weight": float(fi_max_w),
        "mvo_efficiency_score": (float(mvo_gap) if math.isfinite(mvo_gap) else None),
        "feasibility_status": feasibility,
    }


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------


def build_opportunity_set(
    portfolio: dict[str, Any],
    *,
    n_candidates: int = DEFAULT_N_CANDIDATES,
    random_seed: int = DEFAULT_SEED,
    frontier_grid_points: int = FRONTIER_GRID_POINTS,
    equity_total: float = EQUITY_BUCKET_TOTAL,
    fixed_income_total: float = FIXED_INCOME_BUCKET_TOTAL,
    asset_constraints: dict[str, tuple[float, float]] | None = None,
    selected_assets: list[str] | None = None,
    max_attempts_multiplier: int = 5,
    risk_free_rate: float | None = None,
    dirichlet_alpha: float = 1.0,
) -> dict[str, Any]:
    """R-1B.2 + Phase 6.5: bucket-constrained Dirichlet + cap/floor rejection.

    Default arguments reproduce the original R-1B.2 80:20 hard behavior bit-identically.
    New Phase 6.5 parameters:
      equity_total / fixed_income_total : free bucket totals (sum must be 1.0).
      asset_constraints                 : {asset_key: (floor, cap)} per-asset bounds.
      selected_assets                   : subset of CMA asset_keys (None = all).
      max_attempts_multiplier           : rejection sampling budget = n_candidates × mult.

    Reference points may violate the bucket constraint (notably ref_max_sharpe =
    unconstrained MVO result restricted to selected asset subset).

    Returns JSON-serializable dict per R-1B-lite schema. Phase 6.5 additions:
      generation.equity_bucket_total / .fixed_income_bucket_total now reflect inputs
      constraints.asset_constraints (when provided)
      diagnostics.sampling_warning (str | None) for partial-result cases
      diagnostics.attempts_used = {equity: N, fixed_income: N}
    """
    import numpy as np

    if equity_total < -1e-9 or fixed_income_total < -1e-9:
        raise ValueError(
            f"bucket totals must be >= 0: equity={equity_total}, fi={fixed_income_total}"
        )
    bucket_sum = equity_total + fixed_income_total
    if abs(bucket_sum - 1.0) > 1e-6:
        raise ValueError(
            f"equity_total + fixed_income_total must equal 1.0: got {bucket_sum:.6f} "
            f"(equity={equity_total}, fi={fixed_income_total})"
        )

    saa = _require_direct_saa_and_cma(portfolio)
    cma = saa["cma"]
    all_asset_keys = [str(k) for k in cma["asset_keys"]]

    # asset subset filtering (selected_assets keeps original order from CMA)
    if selected_assets is not None:
        selected_set = set(selected_assets)
        invalid = [k for k in selected_assets if k not in all_asset_keys]
        if invalid:
            raise ValueError(
                f"selected_assets contains unknown keys: {invalid}. "
                f"valid asset_keys = {all_asset_keys}"
            )
        asset_keys = [k for k in all_asset_keys if k in selected_set]
    else:
        asset_keys = list(all_asset_keys)
    n = len(asset_keys)
    if n == 0:
        raise ValueError("selected_assets resulted in empty asset list")

    er = _vec(cma["expected_returns"], asset_keys)
    sig = _vec(cma["volatilities"], asset_keys)
    cov = _mat(cma["covariance_matrix"], asset_keys)
    # rf: portfolio JSON 의 saa_diagnostics.rf 가 기본. risk_free_rate override 시
    # 그 값 사용 (lasso 리뷰 도구에서 엔진 config / frozen baseline 미변경하고
    # Sharpe 기준 rf 만 조정).
    rf = float(risk_free_rate if risk_free_rate is not None else (saa.get("rf") or 0.0))

    bucket_map = _extract_bucket_map(portfolio, asset_keys)

    # bucket key partitions (asset_keys 순서 보존) — 사용자 message 일관성 위해
    # ref_eq_w 계산 전에 검증.
    eq_keys = [k for k in asset_keys if bucket_map[k] == EQUITY_BUCKET]
    fi_keys = [k for k in asset_keys if bucket_map[k] == FIXED_INCOME_BUCKET]
    if equity_total > 1e-9 and not eq_keys:
        raise ValueError(
            f"equity_total={equity_total} > 0 but no equity asset selected."
        )
    if fixed_income_total > 1e-9 and not fi_keys:
        raise ValueError(
            f"fixed_income_total={fixed_income_total} > 0 but no fixed_income asset selected."
        )
    eq_index_in_full = {k: asset_keys.index(k) for k in eq_keys}
    fi_index_in_full = {k: asset_keys.index(k) for k in fi_keys}

    ref_eq_w = _build_ref_equal_intra_bucket_weights(
        asset_keys, bucket_map, equity_total, fixed_income_total
    )

    # Normalize asset_constraints: default (0, bucket_total) per asset.
    norm_constraints: dict[str, tuple[float, float]] = {}
    for k in asset_keys:
        bk = bucket_map[k]
        bt = equity_total if bk == EQUITY_BUCKET else fixed_income_total
        if asset_constraints and k in asset_constraints:
            fl_raw, cp_raw = asset_constraints[k]
            fl, cp = float(fl_raw), float(cp_raw)
        else:
            fl, cp = 0.0, float(bt)
        if fl < -1e-9 or cp > 1.0 + 1e-9 or fl > cp + 1e-9:
            raise ValueError(
                f"invalid constraint for {k}: floor={fl}, cap={cp} (require 0 <= floor <= cap <= 1)"
            )
        norm_constraints[k] = (max(fl, 0.0), min(cp, 1.0))

    # Per-bucket feasibility (sum of floors <= bucket_total <= sum of caps).
    def _bucket_feasibility(keys, bt, name):
        if not keys:
            return
        fls = [norm_constraints[k][0] for k in keys]
        cps = [norm_constraints[k][1] for k in keys]
        if sum(fls) > bt + 1e-9:
            raise ValueError(
                f"{name} bucket infeasible: sum(floors)={sum(fls):.4f} > bucket_total={bt:.4f}"
            )
        if sum(cps) < bt - 1e-9:
            raise ValueError(
                f"{name} bucket infeasible: sum(caps)={sum(cps):.4f} < bucket_total={bt:.4f}"
            )

    _bucket_feasibility(eq_keys, equity_total, "equity")
    _bucket_feasibility(fi_keys, fixed_income_total, "fixed_income")

    eq_floors = [norm_constraints[k][0] for k in eq_keys]
    eq_caps = [norm_constraints[k][1] for k in eq_keys]
    fi_floors = [norm_constraints[k][0] for k in fi_keys]
    fi_caps = [norm_constraints[k][1] for k in fi_keys]

    # frontier for mvo_efficiency_score (on selected subset)
    frontier_pts = _build_frontier_points(er, cov, grid_points=frontier_grid_points)

    # ── Bucket-constrained Dirichlet sampling with cap/floor rejection ────
    rng = np.random.default_rng(int(random_seed))

    eq_rows, eq_attempts = _sample_bucket_constrained(
        rng, int(n_candidates), len(eq_keys), equity_total,
        eq_floors, eq_caps, max_attempts_multiplier=max_attempts_multiplier,
        dirichlet_alpha=dirichlet_alpha,
    )
    fi_rows, fi_attempts = _sample_bucket_constrained(
        rng, int(n_candidates), len(fi_keys), fixed_income_total,
        fi_floors, fi_caps, max_attempts_multiplier=max_attempts_multiplier,
        dirichlet_alpha=dirichlet_alpha,
    )

    n_actual = min(len(eq_rows), len(fi_rows), int(n_candidates))
    sampling_warning: str | None = None
    if n_actual < int(n_candidates):
        sampling_warning = (
            f"partial result: requested {int(n_candidates)} candidates, accepted {n_actual} "
            f"(equity_accepted={len(eq_rows)}, fi_accepted={len(fi_rows)}). "
            f"cap/floor constraints may be too tight — try relaxing per-asset bounds."
        )

    # ── candidate metrics ────────────────────────────────────────────
    candidates: list[dict[str, Any]] = []
    for idx in range(n_actual):
        eq_row = eq_rows[idx]
        fi_row = fi_rows[idx]
        w = [0.0] * n
        for i, k in enumerate(eq_keys):
            w[eq_index_in_full[k]] = float(eq_row[i])
        for j, k in enumerate(fi_keys):
            w[fi_index_in_full[k]] = float(fi_row[j])
        cid = f"cand_{idx + 1:06d}"
        candidates.append(
            _metrics_for_weights(
                cid, w, asset_keys, bucket_map, er, cov, rf, frontier_pts
            )
        )

    # ── reference points (2개만) ─────────────────────────────────────
    saa_w_dict = {
        k: float(saa["saa_weights"].get(k, 0.0)) for k in asset_keys
    }
    saa_w_list = [saa_w_dict[k] for k in asset_keys]
    ref_max_sharpe = _metrics_for_weights(
        "ref_max_sharpe", saa_w_list, asset_keys, bucket_map, er, cov, rf,
        frontier_pts,
    )
    ref_80_20 = _metrics_for_weights(
        "ref_80_20_equal_intra_bucket", ref_eq_w, asset_keys, bucket_map,
        er, cov, rf, frontier_pts,
    )

    pool_total = len(candidates) + 2
    feasible_count = sum(
        1 for c in candidates if c["feasibility_status"] == "feasible"
    )
    feasible_count += sum(
        1 for c in (ref_max_sharpe, ref_80_20)
        if c["feasibility_status"] == "feasible"
    )
    rejected_by_degeneracy = pool_total - feasible_count

    determinism_check_hashes = [
        # 첫 5건의 weight tuple → 재현성 검증용
        ",".join(f"{c['weights'][k]:.10f}" for k in asset_keys)
        for c in candidates[:5]
    ]

    payload: dict[str, Any] = {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "product_type": str(portfolio.get("portfolio_type") or ""),
            "portfolio_as_of_date": str(portfolio.get("as_of_date") or ""),
            "source_mode": str(portfolio.get("source_type") or "file"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope": "R-1B-lite (R-1B.2 bucket-constrained)",
        },
        "inputs": {
            "asset_keys": asset_keys,
            "expected_returns": {asset_keys[i]: er[i] for i in range(n)},
            "volatilities": {asset_keys[i]: sig[i] for i in range(n)},
            "covariance_matrix": {
                asset_keys[i]: {asset_keys[j]: cov[i][j] for j in range(n)}
                for i in range(n)
            },
            "asset_bucket_map": {k: bucket_map[k] for k in asset_keys},
            "equity_asset_keys": list(eq_keys),
            "fixed_income_asset_keys": list(fi_keys),
            "risk_free_rate": rf,
        },
        "generation": {
            "method": "dirichlet_bucket_constrained",
            "random_seed": int(random_seed),
            "n_requested": int(n_candidates),
            "n_generated": len(candidates),
            "alpha_equity": [float(dirichlet_alpha)] * len(eq_keys),
            "alpha_fixed_income": [float(dirichlet_alpha)] * len(fi_keys),
            "dirichlet_alpha": float(dirichlet_alpha),
            "equity_bucket_total": float(equity_total),
            "fixed_income_bucket_total": float(fixed_income_total),
            "max_attempts_multiplier": int(max_attempts_multiplier),
            "attempts_used": {
                "equity": int(eq_attempts),
                "fixed_income": int(fi_attempts),
            },
        },
        "constraints": {
            "long_only": True,
            "full_investment": True,
            "equity_bucket_total_fixed": float(equity_total),
            "fixed_income_bucket_total_fixed": float(fixed_income_total),
            "asset_constraints": {
                k: [float(norm_constraints[k][0]), float(norm_constraints[k][1])]
                for k in asset_keys
            },
            "selected_assets": list(asset_keys),
            "optional_filters_enabled": {
                "max_single_asset_weight": bool(asset_constraints is not None),
                "min_nonzero_assets": False,
            },
        },
        "candidates": candidates,
        "reference_points": {
            # R-1B-lite scope: 2개만. ref_min_vol / ref_equal_weight /
            # ref_user_selected 는 R-1C+ 에서 추가.
            "ref_max_sharpe": ref_max_sharpe,
            "ref_80_20_equal_intra_bucket": ref_80_20,
        },
        "diagnostics": {
            "pool_size_total": pool_total,
            "feasible_count": feasible_count,
            "rejected_by_filter": {},
            "rejected_by_degeneracy": rejected_by_degeneracy,
            "frontier_sample_size": len(frontier_pts),
            "determinism_check": {
                "seed": int(random_seed),
                "first_5_candidate_weight_strings": determinism_check_hashes,
            },
            "warnings": [],
            "sampling_warning": sampling_warning,
            "n_actual": int(n_actual),
            "missing_data": [
                "ref_min_vol (deferred to R-1C+)",
                "ref_equal_weight (deferred to R-1C+)",
                "ref_user_selected (deferred to R-1C+)",
                "scatterplot PNG (deferred to R-1C+)",
                "similar_search (deferred to R-1C+)",
            ],
            "removed_metrics_r1b2": [
                "bucket_distance_from_80_20 (R-1B.2: 80:20 hard constraint 도입)",
                "full_weight_distance_from_80_20_equal_bucket_reference (R-1B.2)",
            ],
        },
    }
    return payload


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------


def write_opportunity_set_json(payload: dict[str, Any], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return out_path


# ---------------------------------------------------------------------------
# Summary md
# ---------------------------------------------------------------------------


def _topk(
    candidates: list[dict[str, Any]],
    *,
    key_fn,
    reverse: bool,
    k: int = 10,
) -> list[dict[str, Any]]:
    """deterministic top-k: primary key + tie-break by candidate_id."""
    enriched = [
        (key_fn(c), c["candidate_id"], c) for c in candidates
        if c.get("feasibility_status") == "feasible"
    ]
    enriched.sort(key=lambda t: (-t[0], t[1]) if reverse else (t[0], t[1]))
    return [t[2] for t in enriched[:k]]


def render_opportunity_set_summary_md(
    *,
    as_of_run: str,
    etf_payload: dict[str, Any],
    fund_payload: dict[str, Any],
    out_path: Path,
) -> Path:
    lines: list[str] = []
    lines.append(
        f"# SAA Opportunity Set Summary ({as_of_run})  ·  R-1B-lite"
    )
    lines.append("")
    lines.append(f"> schema_version: {SCHEMA_VERSION}")
    lines.append(
        "> Read-only diagnostic. SAA 는 자동 선택되지 않으며 운용역이 후보 중 최종 결정한다."
    )
    lines.append(
        "> `ref_max_sharpe` source = `diagnostics.saa_diagnostics.saa_weights` "
        "(E-6.2 T-6). final implemented weights 와 다름."
    )
    lines.append("")

    for label, payload in (("ETF", etf_payload), ("Fund", fund_payload)):
        meta = payload["meta"]
        gen = payload["generation"]
        diag = payload["diagnostics"]
        cands = payload["candidates"]
        ref = payload["reference_points"]

        feasible = [c for c in cands if c["feasibility_status"] == "feasible"]
        ret_vals = [c["expected_return"] for c in feasible]
        vol_vals = [c["volatility"] for c in feasible]
        sharpe_vals = [c["sharpe"] for c in feasible if c["sharpe"] is not None]
        eq_vals = [c["equity_weight"] for c in feasible]
        fi_vals = [c["fixed_income_weight"] for c in feasible]

        lines.append(f"## {label}")
        lines.append("")
        lines.append(
            f"- portfolio as_of: **{meta.get('portfolio_as_of_date')}**, "
            f"source: **{meta.get('source_mode')}**"
        )
        lines.append(
            f"- candidate count: **{len(cands)}** "
            f"(requested {gen['n_requested']}, generated {gen['n_generated']})"
        )
        lines.append(
            f"- reference count: **{len(ref)}** "
            f"(ref_max_sharpe, ref_80_20_equal_intra_bucket)"
        )
        lines.append(
            f"- pool_size_total: **{diag['pool_size_total']}**, "
            f"feasible_count: **{diag['feasible_count']}**, "
            f"rejected_by_degeneracy: {diag['rejected_by_degeneracy']}"
        )
        lines.append("")

        def _rng(vals: list[float]) -> str:
            if not vals:
                return "n/a"
            return f"{min(vals) * 100:.2f}% ~ {max(vals) * 100:.2f}%"

        lines.append(f"- expected_return range: **{_rng(ret_vals)}**")
        lines.append(f"- volatility range: **{_rng(vol_vals)}**")
        if sharpe_vals:
            lines.append(
                f"- Sharpe range: **{min(sharpe_vals):.4f} ~ {max(sharpe_vals):.4f}**"
            )
        lines.append(f"- equity_weight range: **{_rng(eq_vals)}**")
        lines.append(f"- fixed_income_weight range: **{_rng(fi_vals)}**")
        lines.append("")

        lines.append("### Reference points")
        lines.append("")
        for ref_id, ref_c in ref.items():
            sh = ref_c["sharpe"]
            sh_str = f"{sh:.4f}" if sh is not None else "n/a"
            eq_ih = ref_c["equity_intra_hhi"]
            fi_ih = ref_c["fixed_income_intra_hhi"]
            eq_ih_s = f"{eq_ih:.4f}" if eq_ih is not None else "n/a"
            fi_ih_s = f"{fi_ih:.4f}" if fi_ih is not None else "n/a"
            lines.append(
                f"- **{ref_id}**: E[R]={ref_c['expected_return'] * 100:.2f}%, "
                f"σ={ref_c['volatility'] * 100:.2f}%, Sharpe={sh_str}, "
                f"eq={ref_c['equity_weight'] * 100:.2f}%, "
                f"fi={ref_c['fixed_income_weight'] * 100:.2f}%, "
                f"HHI={ref_c['concentration_hhi']:.4f}, "
                f"eq_intra_HHI={eq_ih_s}, fi_intra_HHI={fi_ih_s}"
            )
        lines.append("")

        # Top 10 by Sharpe (R-1B.2 columns)
        lines.append("### Top 10 candidates by Sharpe (feasible)")
        lines.append("")
        lines.append(
            "| candidate_id | E[R] | σ | Sharpe | HHI | eq_intra_HHI | fi_intra_HHI | "
            "eq_max | fi_max | mvo_gap |"
        )
        lines.append(
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
        )
        for c in _topk(
            cands,
            key_fn=lambda x: (x["sharpe"] if x["sharpe"] is not None else -1e18),
            reverse=True,
            k=10,
        ):
            sh = c["sharpe"]
            mvo = c["mvo_efficiency_score"]
            sh_str = f"{sh:.4f}" if sh is not None else "n/a"
            mvo_str = f"{mvo:.4f}" if mvo is not None else "n/a"
            eq_ih = c["equity_intra_hhi"]
            fi_ih = c["fixed_income_intra_hhi"]
            eq_ih_s = f"{eq_ih:.4f}" if eq_ih is not None else "n/a"
            fi_ih_s = f"{fi_ih:.4f}" if fi_ih is not None else "n/a"
            lines.append(
                f"| {c['candidate_id']} "
                f"| {c['expected_return'] * 100:.2f}% "
                f"| {c['volatility'] * 100:.2f}% "
                f"| {sh_str} "
                f"| {c['concentration_hhi']:.4f} "
                f"| {eq_ih_s} "
                f"| {fi_ih_s} "
                f"| {c['equity_max_asset_weight'] * 100:.2f}% "
                f"| {c['fixed_income_max_asset_weight'] * 100:.2f}% "
                f"| {mvo_str} |"
            )
        lines.append("")

        # Top 10 lowest equity_intra_hhi (most diversified within equity)
        lines.append("### Top 10 candidates with lowest equity_intra_hhi (intra-equity diversification)")
        lines.append("")
        lines.append(
            "| candidate_id | eq_intra_HHI | eq_max | E[R] | σ | Sharpe | fi_intra_HHI | mvo_gap |"
        )
        lines.append(
            "|---|---:|---:|---:|---:|---:|---:|---:|"
        )
        for c in _topk(
            cands,
            key_fn=lambda x: (
                x["equity_intra_hhi"] if x["equity_intra_hhi"] is not None else 1e18
            ),
            reverse=False,
            k=10,
        ):
            sh = c["sharpe"]
            mvo = c["mvo_efficiency_score"]
            sh_str = f"{sh:.4f}" if sh is not None else "n/a"
            mvo_str = f"{mvo:.4f}" if mvo is not None else "n/a"
            eq_ih = c["equity_intra_hhi"]
            fi_ih = c["fixed_income_intra_hhi"]
            eq_ih_s = f"{eq_ih:.4f}" if eq_ih is not None else "n/a"
            fi_ih_s = f"{fi_ih:.4f}" if fi_ih is not None else "n/a"
            lines.append(
                f"| {c['candidate_id']} "
                f"| {eq_ih_s} "
                f"| {c['equity_max_asset_weight'] * 100:.2f}% "
                f"| {c['expected_return'] * 100:.2f}% "
                f"| {c['volatility'] * 100:.2f}% "
                f"| {sh_str} "
                f"| {fi_ih_s} "
                f"| {mvo_str} |"
            )
        lines.append("")

        # Top 10 lowest mvo_gap (frontier 근접)
        lines.append("### Top 10 candidates closest to MVO frontier (lowest mvo_efficiency_score)")
        lines.append("")
        lines.append(
            "| candidate_id | mvo_gap | Sharpe | E[R] | σ | HHI | eq_intra_HHI | fi_intra_HHI |"
        )
        lines.append(
            "|---|---:|---:|---:|---:|---:|---:|---:|"
        )
        mvo_pool = [c for c in cands if c["mvo_efficiency_score"] is not None]
        for c in _topk(
            mvo_pool,
            key_fn=lambda x: x["mvo_efficiency_score"],
            reverse=False,
            k=10,
        ):
            sh = c["sharpe"]
            mvo = c["mvo_efficiency_score"]
            sh_str = f"{sh:.4f}" if sh is not None else "n/a"
            mvo_str = f"{mvo:.4f}" if mvo is not None else "n/a"
            eq_ih = c["equity_intra_hhi"]
            fi_ih = c["fixed_income_intra_hhi"]
            eq_ih_s = f"{eq_ih:.4f}" if eq_ih is not None else "n/a"
            fi_ih_s = f"{fi_ih:.4f}" if fi_ih is not None else "n/a"
            lines.append(
                f"| {c['candidate_id']} "
                f"| {mvo_str} "
                f"| {sh_str} "
                f"| {c['expected_return'] * 100:.2f}% "
                f"| {c['volatility'] * 100:.2f}% "
                f"| {c['concentration_hhi']:.4f} "
                f"| {eq_ih_s} "
                f"| {fi_ih_s} |"
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "> **Note (R-1B.2)**: 모든 sampled candidate 는 equity 80% / fixed_income 20% "
        "**hard constraint** 를 만족한다 (bucket-constrained Dirichlet). 후보 간 차이는 "
        "bucket 내부 분배 (intra-bucket weights) 에만 존재한다. "
        "본 산출은 후보 집합이며 final SAA 는 자동 선택되지 않는다 — 운용역이 "
        "risk-return / intra-bucket concentration / frontier 근접도 등을 종합 검토하여 결정. "
        "ref_min_vol / ref_equal_weight / scatterplot / similar_search 는 R-1C+ 에서 추가."
    )
    lines.append("")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


__all__ = [
    "SCHEMA_VERSION",
    "DEFAULT_N_CANDIDATES",
    "DEFAULT_SEED",
    "FRONTIER_GRID_POINTS",
    "build_opportunity_set",
    "write_opportunity_set_json",
    "render_opportunity_set_summary_md",
]
