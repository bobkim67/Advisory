"""TAA feasibility projection — Phase C.3.

목적:
  TAA overlay 가 만든 target = SAA + tilt 가 long-only / bucket bound 를
  보장하지 않을 수 있음 (예: SAA=0 자산에 음수 tilt 가 더해져 음수 weight).
  Phase C.3 는 이를 SLSQP projection 으로 보정.

문제 정의:
  minimize    Σ (w_i - target_i)^2
  subject to  Σ w_i = sum_target              (보통 1.0)
              asset_lb_i ≤ w_i ≤ asset_ub_i   (필수 — long-only)
              bucket_lb ≤ Σ_{i ∈ bucket} w_i ≤ bucket_ub
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

logger = logging.getLogger(__name__)


# Phase D — drift_source taxonomy (projection 단계).
PROJECTION_DRIFT_LONG_ONLY_CLIPPING = "long_only_clipping"
PROJECTION_DRIFT_REDISTRIBUTION = "redistribution_from_long_only_clipping"
PROJECTION_DRIFT_BUCKET_CONSTRAINT = "bucket_constraint"
PROJECTION_DRIFT_ASSET_UPPER_BOUND = "asset_upper_bound"
PROJECTION_DRIFT_ASSET_LOWER_BOUND = "asset_lower_bound"
PROJECTION_DRIFT_NORMALIZATION = "normalization"
PROJECTION_DRIFT_NONE = "none"


@dataclass
class ProjectionDiagnostics:
    projection_used: bool = False
    projection_success: bool = True
    projection_message: str = ""
    target_weights_before_projection: dict[str, float] = field(default_factory=dict)
    final_weights_after_projection: dict[str, float] = field(default_factory=dict)
    negative_weight_assets_before_projection: dict[str, float] = field(default_factory=dict)
    clipped_weight_total: float = 0.0
    bucket_weights_before_projection: dict[str, float] = field(default_factory=dict)
    bucket_weights_after_projection: dict[str, float] = field(default_factory=dict)
    asset_weight_drift_from_target: dict[str, float] = field(default_factory=dict)
    max_abs_projection_drift: float = 0.0
    constraints_after_projection: dict[str, Any] = field(default_factory=dict)
    # Phase D — drift_source 분류 + clipping summary
    drift_source_by_asset: dict[str, str] = field(default_factory=dict)
    clipping_summary: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "projection_used": self.projection_used,
            "projection_success": self.projection_success,
            "projection_message": self.projection_message,
            "target_weights_before_projection": dict(self.target_weights_before_projection),
            "final_weights_after_projection": dict(self.final_weights_after_projection),
            "negative_weight_assets_before_projection": dict(self.negative_weight_assets_before_projection),
            "clipped_weight_total": self.clipped_weight_total,
            "bucket_weights_before_projection": dict(self.bucket_weights_before_projection),
            "bucket_weights_after_projection": dict(self.bucket_weights_after_projection),
            "asset_weight_drift_from_target": dict(self.asset_weight_drift_from_target),
            "max_abs_projection_drift": self.max_abs_projection_drift,
            "constraints_after_projection": dict(self.constraints_after_projection),
            "drift_source_by_asset": dict(self.drift_source_by_asset),
            "clipping_summary": dict(self.clipping_summary),
        }


def _classify_projection_drift_source(
    target_weights: "pd.Series",
    final_weights: "pd.Series",
    asset_bounds: dict[str, tuple[float, float]],
    bucket_bounds: dict[str, tuple[float, float]],
    bucket_by_asset: dict[str, str],
    atol: float = 1e-6,
) -> tuple[dict[str, str], dict[str, Any]]:
    """projection drift 를 자산별로 source 분류 + clipping summary 생성.

    Source 우선순위 (자산별):
      1. long_only_clipping        : target<0 이고 final≈0
      2. asset_upper_bound         : final 이 upper bound 에 binding 하고 target>ub
      3. asset_lower_bound         : final 이 lower bound 에 binding 하고 target<lb
      4. bucket_constraint         : 자산이 속한 bucket 의 sum 이 bound 에 binding
      5. redistribution_from_long_only_clipping : target>=0 인데 다른 자산이 clip 되어 spillover 받음
      6. normalization             : 그 외 (rare — sum 정규화 잔차)
      7. none                      : drift ≈ 0
    """
    sources: dict[str, str] = {}
    has_negative_target = any(float(v) < -atol for v in target_weights)

    # bucket sums for bucket_constraint detection
    target_bucket: dict[str, float] = {}
    final_bucket: dict[str, float] = {}
    for k in target_weights.index:
        b = bucket_by_asset.get(k)
        if b is not None:
            target_bucket[b] = target_bucket.get(b, 0.0) + float(target_weights[k])
            final_bucket[b] = final_bucket.get(b, 0.0) + float(final_weights.get(k, 0.0))

    for k in target_weights.index:
        t = float(target_weights[k])
        f = float(final_weights.get(k, 0.0))
        drift = f - t
        if abs(drift) < atol:
            sources[k] = PROJECTION_DRIFT_NONE
            continue
        # 1. Long-only clipping: target<0 → final≈0
        if t < -atol and abs(f) < 1e-4:
            sources[k] = PROJECTION_DRIFT_LONG_ONLY_CLIPPING
            continue
        # 2. Asset upper bound binding
        lb, ub = asset_bounds.get(k, (0.0, 1.0))
        if abs(f - ub) < 1e-4 and t > ub + atol:
            sources[k] = PROJECTION_DRIFT_ASSET_UPPER_BOUND
            continue
        # 3. Asset lower bound binding (relaxed mode 에서는 발생 X)
        if abs(f - lb) < 1e-4 and t < lb - atol and t >= -atol:
            sources[k] = PROJECTION_DRIFT_ASSET_LOWER_BOUND
            continue
        # 4. Bucket constraint binding
        # bucket bound 가 사실상 [0, 1] (no-op) 이면 bucket constraint 가 binding
        # 했다고 보지 않음. 이 경우 final 이 ub=1.0 에 가깝게 보일 수 있으나
        # 그건 sum=1 정규화 결과이지 bucket bound 강제 때문이 아님.
        b = bucket_by_asset.get(k)
        if b and b in bucket_bounds:
            blb, bub = bucket_bounds[b]
            is_noop_bucket = abs(float(blb)) < 1e-9 and abs(float(bub) - 1.0) < 1e-9
            if not is_noop_bucket:
                bsum_t = target_bucket.get(b, 0.0)
                bsum_f = final_bucket.get(b, 0.0)
                if (abs(bsum_f - blb) < 1e-4 and bsum_t < blb - atol) or \
                   (abs(bsum_f - bub) < 1e-4 and bsum_t > bub + atol):
                    sources[k] = PROJECTION_DRIFT_BUCKET_CONSTRAINT
                    continue
        # 5. Redistribution from clipped assets
        if has_negative_target:
            sources[k] = PROJECTION_DRIFT_REDISTRIBUTION
        else:
            sources[k] = PROJECTION_DRIFT_NORMALIZATION

    # Clipping summary
    clipped = [k for k, s in sources.items() if s == PROJECTION_DRIFT_LONG_ONLY_CLIPPING]
    long_only_amt = {k: float(-target_weights[k]) for k in clipped}  # |negative target|
    total_clip = sum(long_only_amt.values())
    max_clip = max(long_only_amt.values()) if long_only_amt else 0.0

    redistributors = {
        k: float(final_weights.get(k, 0.0) - target_weights[k])
        for k, s in sources.items()
        if s == PROJECTION_DRIFT_REDISTRIBUTION
    }
    redistribution_total = sum(abs(v) for v in redistributors.values())

    sources_count: dict[str, int] = {}
    for s in sources.values():
        if s == PROJECTION_DRIFT_NONE:
            continue
        sources_count[s] = sources_count.get(s, 0) + 1
    primary = (
        max(sources_count.items(), key=lambda kv: kv[1])[0]
        if sources_count else PROJECTION_DRIFT_NONE
    )

    summary = {
        "n_assets_clipped_long_only": len(clipped),
        "clipped_assets": clipped,
        "long_only_clipping_by_asset": long_only_amt,
        "total_long_only_clipping_magnitude": total_clip,
        "max_long_only_clipping": max_clip,
        "redistribution_total": redistribution_total,
        "redistribution_by_recipient": redistributors,
        "drift_source_primary": primary,
        "drift_source_counts": sources_count,
        "relaxed_mode_unexpected_sources": [
            s for s in sources_count
            if s in (
                PROJECTION_DRIFT_BUCKET_CONSTRAINT,
                PROJECTION_DRIFT_ASSET_UPPER_BOUND,
                PROJECTION_DRIFT_ASSET_LOWER_BOUND,
            )
        ],
    }
    return sources, summary


def _bucket_sums(weights: "pd.Series", bucket_by_asset: dict[str, str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in weights.items():
        b = bucket_by_asset.get(k)
        if b is None:
            continue
        out[b] = out.get(b, 0.0) + float(v)
    return out


def _is_feasible(
    w: "pd.Series",
    asset_bounds: dict[str, tuple[float, float]],
    bucket_bounds: dict[str, tuple[float, float]],
    bucket_by_asset: dict[str, str],
    sum_target: float,
    atol: float = 1e-7,
) -> bool:
    if abs(float(w.sum()) - sum_target) > atol:
        return False
    for k, v in w.items():
        lb, ub = asset_bounds.get(k, (0.0, 1.0))
        if float(v) < lb - atol or float(v) > ub + atol:
            return False
    sums = _bucket_sums(w, bucket_by_asset)
    for b, (lb, ub) in bucket_bounds.items():
        s = sums.get(b, 0.0)
        if s < lb - atol or s > ub + atol:
            return False
    return True


def project_to_feasible(
    target_weights: "pd.Series",
    asset_bounds: dict[str, tuple[float, float]] | None = None,
    bucket_bounds: dict[str, tuple[float, float]] | None = None,
    bucket_by_asset: dict[str, str] | None = None,
    sum_target: float = 1.0,
    atol: float = 1e-9,
) -> tuple["pd.Series", ProjectionDiagnostics]:
    """target 에 가장 가까운 feasible weight vector 를 SLSQP 로 projection.

    feasible 조건:
      sum(w) = sum_target
      asset_lb_i ≤ w_i ≤ asset_ub_i   (long-only 면 lb≥0)
      bucket_lb ≤ Σ bucket weights ≤ bucket_ub

    feasible target 이면 그대로 반환 (objective=0).
    """
    import numpy as np
    import pandas as pd
    from scipy.optimize import minimize

    asset_bounds = asset_bounds or {}
    bucket_bounds = bucket_bounds or {}
    bucket_by_asset = bucket_by_asset or {}

    diag = ProjectionDiagnostics(
        target_weights_before_projection={k: float(v) for k, v in target_weights.items()},
        bucket_weights_before_projection=_bucket_sums(target_weights, bucket_by_asset),
    )
    neg = {k: float(v) for k, v in target_weights.items() if float(v) < -atol}
    diag.negative_weight_assets_before_projection = neg

    # 이미 feasible 이면 즉시 반환
    if _is_feasible(target_weights, asset_bounds, bucket_bounds, bucket_by_asset, sum_target):
        diag.projection_used = False
        diag.projection_success = True
        diag.projection_message = "already feasible — no projection"
        diag.final_weights_after_projection = {k: float(v) for k, v in target_weights.items()}
        diag.bucket_weights_after_projection = diag.bucket_weights_before_projection.copy()
        diag.asset_weight_drift_from_target = {k: 0.0 for k in target_weights.index}
        diag.max_abs_projection_drift = 0.0
        # Phase D — drift_source 분류 (모두 none)
        diag.drift_source_by_asset = {
            k: PROJECTION_DRIFT_NONE for k in target_weights.index
        }
        diag.clipping_summary = {
            "n_assets_clipped_long_only": 0,
            "clipped_assets": [],
            "long_only_clipping_by_asset": {},
            "total_long_only_clipping_magnitude": 0.0,
            "max_long_only_clipping": 0.0,
            "redistribution_total": 0.0,
            "redistribution_by_recipient": {},
            "drift_source_primary": PROJECTION_DRIFT_NONE,
            "drift_source_counts": {},
            "relaxed_mode_unexpected_sources": [],
        }
        return target_weights.copy(), diag

    diag.projection_used = True

    order = list(target_weights.index)
    n = len(order)
    target_arr = target_weights.loc[order].astype(float).to_numpy()

    bounds = []
    for k in order:
        lb, ub = asset_bounds.get(k, (0.0, 1.0))
        bounds.append((float(lb), float(ub)))

    constraints = []
    constraints.append({"type": "eq", "fun": lambda w: float(np.sum(w)) - sum_target})

    for bucket_name, (lb, ub) in bucket_bounds.items():
        idx = [i for i, k in enumerate(order) if bucket_by_asset.get(k) == bucket_name]
        if not idx:
            continue
        idx_arr = np.array(idx, dtype=int)
        constraints.append(
            {"type": "ineq", "fun": (lambda w, ix=idx_arr, lb=lb: float(w[ix].sum()) - float(lb))}
        )
        constraints.append(
            {"type": "ineq", "fun": (lambda w, ix=idx_arr, ub=ub: float(ub) - float(w[ix].sum()))}
        )

    def objective(w):
        diff = w - target_arr
        return float(np.dot(diff, diff))

    # init: target 을 [lb, ub] 로 clip 후 sum_target 이 되도록 보정.
    init = np.array(target_arr, dtype=float)
    for i, (lb, ub) in enumerate(bounds):
        if init[i] < lb:
            init[i] = lb
        elif init[i] > ub:
            init[i] = ub
    cur = init.sum()
    if abs(cur - sum_target) > 1e-9 and cur > 0:
        init = init * (sum_target / cur)

    res = minimize(
        objective,
        init,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 300, "ftol": 1e-12, "disp": False},
    )

    w_arr = np.array(res.x, dtype=float)
    # numerical residual: 음수가 미세하게 나면 0으로 clamp + 재정규화
    w_arr = np.clip(w_arr, 0.0, None)
    s = w_arr.sum()
    if s > 0:
        w_arr = w_arr * (sum_target / s)

    final = pd.Series(w_arr, index=order, name=target_weights.name)

    diag.projection_success = bool(res.success)
    diag.projection_message = str(res.message)
    diag.final_weights_after_projection = {k: float(v) for k, v in final.items()}
    diag.bucket_weights_after_projection = _bucket_sums(final, bucket_by_asset)
    drift = {k: float(final[k] - target_weights.get(k, 0.0)) for k in order}
    diag.asset_weight_drift_from_target = drift
    diag.max_abs_projection_drift = float(max(abs(v) for v in drift.values())) if drift else 0.0
    diag.clipped_weight_total = float(sum(max(0.0, -v) for v in target_arr))

    # 결과 feasibility 재확인
    feas = _is_feasible(final, asset_bounds, bucket_bounds, bucket_by_asset, sum_target, atol=1e-6)
    diag.constraints_after_projection = {
        "feasible": feas,
        "sum": float(final.sum()),
        "min_weight": float(final.min()),
        "buckets": diag.bucket_weights_after_projection,
    }

    # Phase D — drift_source 분류 + clipping summary
    sources, summary = _classify_projection_drift_source(
        target_weights, final, asset_bounds, bucket_bounds, bucket_by_asset
    )
    diag.drift_source_by_asset = sources
    diag.clipping_summary = summary

    return final, diag
