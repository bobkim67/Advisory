"""Phase E-7 — Explainability Data Layer.

read-only extractor: portfolio_*.json + taa_policy.yaml + (옵션) etf_list/fund_list 를
입력으로 받아 5 블록 explainability dict 를 빌드한다. 차트 미생성, allocation 미변경.

Schema 정의는 `docs/phase_e7_explainability_data_contract.md` 참조 (schema_version="e7.1").

Hard requirements:
- 입력 portfolio JSON / taa_policy.yaml / 원본 list 모두 mutate 없음.
- SAA inferred 절대 금지 — `saa_diagnostics.saa_weights` 직접 telemetry 만 사용.
- 추가 read-only 계산만 허용 (risk contribution, before/after summary).
- efficient_frontier 는 본 phase 미산출 (E-9 deferred), missing_data 명시.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "e7.1"
EXPECTED_REGIME_HISTORY_MONTHS = 24


# ---------------------------------------------------------------------------
# Loaders (read-only)
# ---------------------------------------------------------------------------


def load_portfolio_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_taa_policy_yaml(path: Path) -> dict[str, Any]:
    """taa_policy.yaml 의 regime_tilts 만 read-only 로 로드."""
    import yaml

    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def load_product_list_lookup(path: Path | None) -> dict[str, dict[str, Any]]:
    """etf_list / fund_list → {product_id(str): row_dict}.

    경로 None 또는 파일 미존재 시 빈 dict 반환 (ticker 등 lookup 항목은 missing_data).
    """
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    import pandas as pd

    df = pd.read_csv(p, sep="\t", encoding="utf-8")
    if "상품번호" not in df.columns:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        pid = str(row["상품번호"]).strip()
        if pid and pid != "nan":
            out[pid] = {k: row[k] for k in df.columns}
    return out


# ---------------------------------------------------------------------------
# Direct SAA telemetry guard (E-6.2 T-6 enforcement)
# ---------------------------------------------------------------------------


def _require_direct_saa_telemetry(portfolio: dict[str, Any]) -> dict[str, float]:
    saa_diag = (portfolio.get("diagnostics") or {}).get("saa_diagnostics") or {}
    saa_w = saa_diag.get("saa_weights")
    if not saa_w or not isinstance(saa_w, dict):
        raise ValueError(
            "E-7 explainability requires direct SAA telemetry "
            "`diagnostics.saa_diagnostics.saa_weights` (E-6.2 T-6). "
            "Inferred SAA (taa_target − asset_tilts) is forbidden."
        )
    return {str(k): float(v) for k, v in saa_w.items()}


# ---------------------------------------------------------------------------
# Numerical helpers (read-only, no allocation impact)
# ---------------------------------------------------------------------------


def _matvec(matrix: dict[str, dict[str, float]], vec: dict[str, float], keys: list[str]) -> list[float]:
    """Σw — keys 순서대로."""
    out = [0.0] * len(keys)
    for i, ki in enumerate(keys):
        s = 0.0
        row = matrix.get(ki) or {}
        for j, kj in enumerate(keys):
            s += float(row.get(kj, 0.0)) * float(vec.get(kj, 0.0))
        out[i] = s
    return out


def _portfolio_return_vol_sharpe(
    weights: dict[str, float],
    er: dict[str, float],
    cov: dict[str, dict[str, float]],
    rf: float,
) -> tuple[float, float, float]:
    """w · μ , sqrt(w' Σ w), sharpe."""
    keys = list(er.keys())
    w_vec = [float(weights.get(k, 0.0)) for k in keys]
    er_vec = [float(er.get(k, 0.0)) for k in keys]
    sigma_w = _matvec(cov, weights, keys)
    port_var = sum(w_vec[i] * sigma_w[i] for i in range(len(keys)))
    port_var = max(port_var, 0.0)
    port_vol = math.sqrt(port_var)
    port_ret = sum(w_vec[i] * er_vec[i] for i in range(len(keys)))
    sharpe = (port_ret - float(rf)) / port_vol if port_vol > 1e-12 else float("nan")
    return port_ret, port_vol, sharpe


def _risk_contribution(
    weights: dict[str, float],
    cov: dict[str, dict[str, float]],
) -> dict[str, Any]:
    """marginal RC = (Σw)_i, total RC = w_i · (Σw)_i, percent = trc / Σ trc."""
    keys = list(cov.keys())
    if not keys:
        return {"by_asset": {}, "portfolio_volatility": 0.0, "available": False}
    sigma_w = _matvec(cov, weights, keys)
    trc = [float(weights.get(keys[i], 0.0)) * sigma_w[i] for i in range(len(keys))]
    port_var = sum(trc)
    port_var = max(port_var, 0.0)
    port_vol = math.sqrt(port_var)
    pct = [
        (trc[i] / port_var if port_var > 1e-12 else 0.0)
        for i in range(len(keys))
    ]
    by_asset: dict[str, dict[str, float]] = {}
    for i, k in enumerate(keys):
        by_asset[k] = {
            "weight": float(weights.get(k, 0.0)),
            "marginal_risk_contribution": float(sigma_w[i]),
            "total_risk_contribution": float(trc[i]),
            "percent_risk_contribution": float(pct[i]),
        }
    return {
        "by_asset": by_asset,
        "portfolio_volatility": float(port_vol),
        "available": True,
    }


# ---------------------------------------------------------------------------
# Block builders
# ---------------------------------------------------------------------------


def _build_meta(
    portfolio: dict[str, Any],
    *,
    portfolio_json_path: Path,
    taa_policy_path: Path,
    product_list_path: Path | None,
    operating_mode: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "portfolio_type": str(portfolio.get("portfolio_type", "")),
        "portfolio_as_of_date": str(portfolio.get("as_of_date") or ""),
        "portfolio_as_of_run": str(portfolio.get("as_of") or ""),
        "source_type": str(portfolio.get("source_type") or "file"),
        "operating_mode": operating_mode,
        "source_files": {
            "portfolio_json": str(portfolio_json_path),
            "taa_policy_yaml": str(taa_policy_path),
            "product_list": (str(product_list_path) if product_list_path else None),
        },
        "upstream_run": {
            "build_portfolio_version": "phase-e62 (telemetry+determinism patch)",
            "determinism_patch_applied": True,
        },
    }


def _build_regime(
    portfolio: dict[str, Any],
    taa_policy: dict[str, Any],
) -> dict[str, Any]:
    diag = portfolio.get("diagnostics") or {}
    regime = diag.get("regime") or {}

    history = list(regime.get("history") or [])
    history_obs = [
        {
            "as_of": str(h.get("as_of") or ""),
            "placement": float(h.get("placement") or 0.0),
            "velocity": float(h.get("velocity") or 0.0),
            "regime": int(h.get("regime") or 0),
            "regime_label": _regime_label(int(h.get("regime") or 0)),
        }
        for h in history
    ]

    # transition summary
    transition = {
        "previous_regime": None,
        "current_regime": int(regime.get("regime") or 0),
        "changed": False,
        "direction": "unknown",
        "comment": "history 가 2건 미만 — transition 평가 불가",
    }
    if len(history_obs) >= 2:
        prev = history_obs[-2]["regime"]
        curr = history_obs[-1]["regime"]
        transition["previous_regime"] = prev
        transition["current_regime"] = curr
        transition["changed"] = prev != curr
        transition["direction"] = "regime_change" if prev != curr else "stable"
        transition["comment"] = (
            f"prev=R{prev} → curr=R{curr} ({'changed' if prev != curr else 'stable'})"
        )

    # asset_class_preference from taa_policy.regime_tilts.<n>.asset_tilts
    # yaml 값은 비중 단위 (예: +0.02 = +2%p). tilt_pp 필드는 %p 단위로 통일.
    regime_id = int(regime.get("regime") or 0)
    regime_tilts = (taa_policy.get("regime_tilts") or {}).get(regime_id) or {}
    asset_tilts_weight = regime_tilts.get("asset_tilts") or {}
    by_asset: dict[str, Any] = {}
    for ak, tilt_w_raw in asset_tilts_weight.items():
        tilt_weight = float(tilt_w_raw)
        tilt_pp = tilt_weight * 100.0
        if tilt_weight > 1e-9:
            pref = "overweight"
        elif tilt_weight < -1e-9:
            pref = "underweight"
        else:
            pref = "neutral"
        by_asset[str(ak)] = {
            "preference": pref,
            "tilt_pp": float(tilt_pp),
            "reason": (
                f"taa_policy.regime_tilts.{regime_id}.asset_tilts.{ak} "
                f"= {tilt_pp:+.2f}pp"
            ),
            "source": "rule_based",
        }

    return {
        "current": {
            "portfolio_as_of_date": str(portfolio.get("as_of_date") or ""),
            "regime_signal_as_of_date": str(regime.get("as_of") or ""),
            "region": str(regime.get("region") or ""),
            "placement": float(regime.get("placement") or 0.0),
            "velocity": float(regime.get("velocity") or 0.0),
            "regime": int(regime.get("regime") or 0),
            "regime_label": str(regime.get("regime_label") or ""),
            "quadrant_label": _regime_label(int(regime.get("regime") or 0)),
        },
        "history": {
            "observations": history_obs,
            "count": len(history_obs),
            "start_date": (history_obs[0]["as_of"] if history_obs else None),
            "end_date": (history_obs[-1]["as_of"] if history_obs else None),
            "expected_full_history_months": EXPECTED_REGIME_HISTORY_MONTHS,
            "actual_history_months": len(history_obs),
            "full_history_available": len(history_obs) >= EXPECTED_REGIME_HISTORY_MONTHS,
        },
        "transition_summary": transition,
        "asset_class_preference": {
            "by_asset": by_asset,
        },
    }


def _regime_label(regime_id: int) -> str:
    return {
        1: "Expansion / Acceleration",
        2: "Recovery / Improvement",
        3: "Slowdown / Contraction",
        4: "Late Cycle / Deceleration",
    }.get(int(regime_id), "Unknown")


def _build_saa(portfolio: dict[str, Any]) -> dict[str, Any]:
    diag = portfolio.get("diagnostics") or {}
    saa_diag = diag.get("saa_diagnostics") or {}
    cma = saa_diag.get("cma") or {}

    saa_weights = _require_direct_saa_telemetry(portfolio)

    er = {str(k): float(v) for k, v in (cma.get("expected_returns") or {}).items()}
    sig = {str(k): float(v) for k, v in (cma.get("volatilities") or {}).items()}
    corr_raw = cma.get("correlation_matrix") or {}
    cov_raw = cma.get("covariance_matrix") or {}
    corr = {
        str(k): {str(kk): float(vv) for kk, vv in (row or {}).items()}
        for k, row in corr_raw.items()
    }
    cov = {
        str(k): {str(kk): float(vv) for kk, vv in (row or {}).items()}
        for k, row in cov_raw.items()
    }

    rf = float(saa_diag.get("rf") or 0.0)
    port_ret, port_vol, sharpe = _portfolio_return_vol_sharpe(
        saa_weights, er, cov, rf
    )

    constraints = _enumerate_saa_constraints()

    return {
        "cma_inputs": {
            "expected_returns": er,
            "volatilities": sig,
            "correlation_matrix": corr,
            "covariance_matrix": cov,
        },
        "optimization": {
            "objective": str(saa_diag.get("objective_name") or ""),
            "objective_params": {"rf": rf},
            "constraints": constraints,
            "universe": {
                "asset_keys": list(cma.get("asset_keys") or []),
                "asset_names": list((cma.get("name_by_key") or {}).values()),
                "ticker_by_key": dict(cma.get("ticker_by_key") or {}),
            },
            "selected_saa_weights": saa_weights,
            "selected_point": {
                "expected_return": float(port_ret),
                "volatility": float(port_vol),
                "sharpe": (float(sharpe) if math.isfinite(sharpe) else None),
                "utility_score": None,
            },
            "solver": {
                "status": str(saa_diag.get("solver_status") or ""),
                "message": str(saa_diag.get("solver_message") or ""),
                "n_iter": int(saa_diag.get("n_iter") or 0),
                "weight_sum": float(saa_diag.get("weight_sum") or 0.0),
            },
        },
        "efficient_frontier": {
            "points": [],
            "selected_point_index": None,
            "min_vol_point_index": None,
            "max_sharpe_point_index": None,
            "available": False,
            "deferred_to": "E-9",
        },
        "risk_contribution": _risk_contribution(saa_weights, cov),
        "diagnostics": {
            "warnings": [],
            "missing_data": [
                {
                    "field": "efficient_frontier",
                    "impact": "Selected SAA point 의 frontier 위치 시각화 불가",
                    "recommended_next_step": "E-9 phase: scipy.optimize 로 σ-grid scan",
                },
            ],
        },
    }


def _enumerate_saa_constraints() -> list[dict[str, Any]]:
    """Phase D relaxed_diagnostic 기준 — long-only + sum=1 만 hard, 나머지 비활성.

    binding 평가는 본 phase 미수행 ('unknown' 표시).
    """
    return [
        {
            "constraint_id": "long_only",
            "description": "All asset weights >= 0",
            "lower_bound": 0.0,
            "upper_bound": None,
            "applied": True,
            "binding": "unknown",
        },
        {
            "constraint_id": "weight_sum_eq_1",
            "description": "Sum of weights = 1.0",
            "lower_bound": 1.0,
            "upper_bound": 1.0,
            "applied": True,
            "binding": "binding",
        },
        {
            "constraint_id": "weight_bounds_per_asset",
            "description": "Per-asset min/max bounds (Phase D relaxed → [0, 1])",
            "lower_bound": 0.0,
            "upper_bound": 1.0,
            "applied": False,
            "binding": "n/a (relaxed)",
        },
        {
            "constraint_id": "equity_sum",
            "description": "Equity bucket sum range (Phase D relaxed → [0, 1])",
            "lower_bound": 0.0,
            "upper_bound": 1.0,
            "applied": False,
            "binding": "n/a (relaxed)",
        },
        {
            "constraint_id": "fixed_income_sum",
            "description": "Fixed-income bucket sum range (Phase D relaxed → [0, 1])",
            "lower_bound": 0.0,
            "upper_bound": 1.0,
            "applied": False,
            "binding": "n/a (relaxed)",
        },
    ]


def _build_taa(
    portfolio: dict[str, Any],
    saa_block: dict[str, Any],
    taa_policy: dict[str, Any],
) -> dict[str, Any]:
    diag = portfolio.get("diagnostics") or {}
    regime = diag.get("regime") or {}
    taa_diag = diag.get("taa_diagnostics") or {}
    feas = taa_diag.get("taa_feasibility") or {}
    target_before = {
        str(k): float(v)
        for k, v in (feas.get("target_weights_before_projection") or {}).items()
    }

    saa_weights = saa_block["optimization"]["selected_saa_weights"]
    er = saa_block["cma_inputs"]["expected_returns"]
    cov = saa_block["cma_inputs"]["covariance_matrix"]
    rf = float(saa_block["optimization"]["objective_params"].get("rf", 0.0))

    regime_id = int(regime.get("regime") or 0)
    regime_tilts = (taa_policy.get("regime_tilts") or {}).get(regime_id) or {}
    asset_tilts_weight = regime_tilts.get("asset_tilts") or {}
    regime_reason = str(regime_tilts.get("reason") or "")

    by_asset: dict[str, Any] = {}
    all_keys = sorted(set(saa_weights.keys()) | set(target_before.keys()))
    for ak in all_keys:
        s = float(saa_weights.get(ak, 0.0))
        t = float(target_before.get(ak, 0.0))
        tilt = t - s
        if tilt > 1e-9:
            direction = "overweight"
        elif tilt < -1e-9:
            direction = "underweight"
        else:
            direction = "neutral"
        # yaml asset_tilts 값 = 비중 단위. *100 으로 %p 단위 통일.
        policy_tilt_pp = float(asset_tilts_weight.get(ak, 0.0)) * 100.0
        rationale = (
            f"Regime {regime_id} → asset_tilts.{ak} = {policy_tilt_pp:+.2f}pp "
            f"(applied tilt = {tilt * 100:+.2f}pp)"
        )
        by_asset[ak] = {
            "saa_weight": s,
            "tilt": float(tilt),
            "taa_target_weight": t,
            "direction": direction,
            "rationale": rationale,
            "source": "rule_based",
            "confidence": None,
        }

    # before / after summary
    pr_b, pv_b, sh_b = _portfolio_return_vol_sharpe(saa_weights, er, cov, rf)
    pr_a, pv_a, sh_a = _portfolio_return_vol_sharpe(target_before, er, cov, rf)

    def _sub_finite(a: float | None, b: float | None) -> float | None:
        if a is None or b is None:
            return None
        return float(a) - float(b)

    sh_b_v = sh_b if math.isfinite(sh_b) else None
    sh_a_v = sh_a if math.isfinite(sh_a) else None
    delta_sh = _sub_finite(sh_a_v, sh_b_v)

    improvement_comment = (
        f"ΔE[R]={(pr_a - pr_b) * 100:+.2f}pp, "
        f"Δσ={(pv_a - pv_b) * 100:+.2f}pp, "
        f"ΔSharpe={(delta_sh if delta_sh is not None else 0.0):+.4f}"
    )

    return {
        "current_regime": {
            "regime": regime_id,
            "regime_label": str(regime.get("regime_label") or ""),
            "placement": float(regime.get("placement") or 0.0),
            "velocity": float(regime.get("velocity") or 0.0),
        },
        "regime_conditioned_assumptions": {
            "by_asset": {},
            "available": False,
            "note": (
                "TAA = prototype heuristic rule overlay (not regime-MVO). "
                "regime-conditioned μ/σ 미구현."
            ),
        },
        "tilt_policy": {
            "policy_id": "taa_policy.yaml::regime_tilts",
            "policy_version": "phase-d frozen",
            "method": "rule_based",
            "description": (
                "regime → asset_tilts (%p) lookup. SAA 에 ±%p 가산. "
                "tilt_sum=0 정합."
            ),
            "per_asset_max_tilt": 1.0,
            "bucket_tilts_active": False,
            "regime_reason": regime_reason,
        },
        "tilt_decisions": {
            "by_asset": by_asset,
        },
        "taa_portfolio_summary": {
            "expected_return_before_tilt": float(pr_b),
            "volatility_before_tilt": float(pv_b),
            "sharpe_before_tilt": sh_b_v,
            "expected_return_after_tilt": float(pr_a),
            "volatility_after_tilt": float(pv_a),
            "sharpe_after_tilt": sh_a_v,
            "improvement_summary": {
                "delta_expected_return": float(pr_a - pr_b),
                "delta_volatility": float(pv_a - pv_b),
                "delta_sharpe": (float(delta_sh) if delta_sh is not None else None),
                "comment": improvement_comment,
            },
        },
        "diagnostics": {
            "warnings": [],
            "missing_data": [
                {
                    "field": "regime_conditioned_assumptions",
                    "impact": "regime-aware MVO / risk premia 분해 불가",
                    "recommended_next_step": (
                        "future phase — regime_mvo (현재 future_study only)"
                    ),
                },
                {
                    "field": "tilt_decisions.confidence",
                    "impact": "tilt 의 통계적 유의성 표시 불가",
                    "recommended_next_step": "future phase — confidence scaling",
                },
            ],
        },
    }


def _build_product_selection(
    portfolio: dict[str, Any],
    product_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    diag = portfolio.get("diagnostics") or {}
    universe_diag = diag.get("universe_diagnostics") or {}
    sel_diag = diag.get("selection_diagnostics") or {}
    fb_diag = diag.get("fallback") or {}

    classified_by = dict(universe_diag.get("classified_by_asset_class") or {})
    match_reasons = dict(universe_diag.get("match_reasons_by_asset_class") or {})
    by_asset: dict[str, Any] = {}
    for ak, count in classified_by.items():
        by_asset[str(ak)] = {
            "classified_count": int(count),
            "match_reasons": list(match_reasons.get(ak) or []),
            "products": [],
            "products_available": False,
            "deferred_to": "E-11",
        }

    # final selection — product_allocation enriched
    pa = list(portfolio.get("product_allocation") or [])
    # weight 내림차순 + asset 내 rank
    by_asset_groups: dict[str, list[dict[str, Any]]] = {}
    for r in pa:
        ak = str(r.get("asset_key") or "")
        by_asset_groups.setdefault(ak, []).append(r)
    rank_by_pid: dict[str, int] = {}
    for ak, rows in by_asset_groups.items():
        rows_sorted = sorted(
            rows,
            key=lambda x: float(x.get("final_weight") or 0.0),
            reverse=True,
        )
        for i, row in enumerate(rows_sorted):
            rank_by_pid[str(row.get("product_id") or "")] = i + 1

    selected_products: list[dict[str, Any]] = []
    ticker_lookup_attempted = bool(product_lookup)
    n_with_ticker = 0
    for r in pa:
        pid = str(r.get("product_id") or "")
        lookup_row = product_lookup.get(pid) if product_lookup else None
        # ticker 대체: 원본에 ticker 컬럼 없음 → product_id 자체가 식별자
        ticker_value: str | None = None
        if lookup_row is not None:
            n_with_ticker += 1
        warning_flags = list(r.get("warning_flags") or [])
        cap_applied = any("fallback_absorber" in str(f) for f in warning_flags)
        selected_products.append({
            "product_id": pid,
            "product_name": str(r.get("product_name") or ""),
            "ticker": ticker_value,
            "manager": str(r.get("manager") or ""),
            "asset_key": str(r.get("asset_key") or ""),
            "bucket": str(r.get("bucket") or ""),
            "asset_weight": float(r.get("source_asset_weight") or 0.0),
            "product_weight": float(r.get("final_weight") or 0.0),
            "rank_within_asset": rank_by_pid.get(pid, 0),
            "role": str(r.get("role") or ""),
            "selected_reason": (
                str(r.get("selection_reason"))
                if r.get("selection_reason") is not None else None
            ),
            "cap_applied": cap_applied,
            "constraint_notes": warning_flags,
            "lookup_metadata_available": lookup_row is not None,
        })

    return {
        "universe": {
            "total_count": int(universe_diag.get("total_products") or 0),
            "raw_count": int(universe_diag.get("raw_count") or 0),
            "passed_filter_count": int(universe_diag.get("passed_filter_count") or 0),
            "classified_count": int(universe_diag.get("classified_count") or 0),
            "by_asset_class": by_asset,
        },
        "filtering": {
            "excluded_products": [],
            "excluded_sample": list(universe_diag.get("unclassified_samples") or [])[:20],
            "eligible_count_by_asset": classified_by,
        },
        "scoring": {
            "score_method": str(sel_diag.get("quant_grade_policy") or ""),
            "score_factors": [],
            "scored_products": [],
            "scoring_available": False,
            "deferred_to": "E-11 + selection/tool.py 의 score 보존",
            "grade_filtered_count": int(sel_diag.get("grade_filtered_count") or 0),
            "grade_penalized_count": int(sel_diag.get("grade_penalized_count") or 0),
        },
        "final_selection": {
            "selected_products": selected_products,
            "ticker_lookup_attempted": ticker_lookup_attempted,
            "ticker_lookup_hits": n_with_ticker,
        },
        "fallback_summary": {
            "fallback_used": bool(fb_diag.get("fallback_used", False)),
            "cash_placeholder_weight": float(fb_diag.get("cash_placeholder_weight") or 0.0),
            "fallback_absorbers_count": len(fb_diag.get("fallback_absorbers") or []),
        },
        "diagnostics": {
            "warnings": list(sel_diag.get("warnings") or []),
            "missing_data": [
                {
                    "field": "by_asset_class.products / scoring.scored_products",
                    "impact": (
                        "ETF/Fund universe 전체 대비 selection 비율 시각화 불가, "
                        "factor 별 score 분해 불가"
                    ),
                    "recommended_next_step": (
                        "E-11 phase: ProductRepository read-only 호출 + "
                        "selection/tool.py 의 score 보존"
                    ),
                },
                {
                    "field": "final_selection.selected_products.ticker",
                    "impact": "ticker 표기 불가 (etf_list/fund_list 에 ticker 컬럼 없음)",
                    "recommended_next_step": (
                        "외부 Bloomberg/FactSet ticker mapping table 또는 "
                        "DBMarketDataRepository.product_metadata 확장"
                    ),
                },
            ],
        },
    }


# ---------------------------------------------------------------------------
# report_ready_summary (Korean text)
# ---------------------------------------------------------------------------


def _build_report_ready_summary(
    regime_block: dict[str, Any],
    saa_block: dict[str, Any],
    taa_block: dict[str, Any],
    product_block: dict[str, Any],
) -> dict[str, Any]:
    cur = regime_block["current"]
    hist = regime_block["history"]
    transition = regime_block["transition_summary"]
    asset_pref = regime_block["asset_class_preference"]["by_asset"]

    over = sorted(
        [(k, v["tilt_pp"]) for k, v in asset_pref.items() if v["preference"] == "overweight"],
        key=lambda x: -x[1],
    )
    under = sorted(
        [(k, v["tilt_pp"]) for k, v in asset_pref.items() if v["preference"] == "underweight"],
        key=lambda x: x[1],
    )

    cma = saa_block["cma_inputs"]
    er_vals = list(cma["expected_returns"].values())
    sig_vals = list(cma["volatilities"].values())
    sel = saa_block["optimization"]["selected_point"]
    saa_w = saa_block["optimization"]["selected_saa_weights"]
    nonzero_saa = [(k, v) for k, v in saa_w.items() if v >= 0.005]
    nonzero_saa.sort(key=lambda x: -x[1])
    saa_text_parts = [f"{k} {v * 100:.1f}%" for k, v in nonzero_saa[:5]]

    taa_sum = taa_block["taa_portfolio_summary"]
    pa_top = sorted(
        product_block["final_selection"]["selected_products"],
        key=lambda x: -float(x.get("product_weight") or 0.0),
    )[:5]

    universe = product_block["universe"]
    score_method = product_block["scoring"]["score_method"]

    regime_summary = {
        "title": "현재 경기국면 진단",
        "current_location_text": (
            f"{cur['region']} region 의 ECI 좌표는 "
            f"P={cur['placement']:+.4f} / V={cur['velocity']:+.4f} 으로 "
            f"Regime {cur['regime']} ({cur['regime_label']}) 에 위치합니다."
        ),
        "transition_text": (
            transition.get("comment", "")
            + (f" (history {hist['count']} obs, "
               f"{hist['actual_history_months']}/{hist['expected_full_history_months']} months)")
        ),
        "asset_implication_text": (
            f"현재 regime 의 자산군 선호 — "
            f"비중 확대: {', '.join(f'{k} {v:+.1f}pp' for k, v in over) or '없음'} / "
            f"비중 축소: {', '.join(f'{k} {v:+.1f}pp' for k, v in under) or '없음'}."
        ),
    }

    saa_summary = {
        "title": "SAA 도출 (max_sharpe MVO)",
        "input_summary_text": (
            f"{len(er_vals)}개 자산 — μ vector 평균={sum(er_vals)/len(er_vals)*100:.2f}%, "
            f"σ vector 평균={sum(sig_vals)/len(sig_vals)*100:.2f}%. "
            f"ρ matrix {len(cma['correlation_matrix'])}×{len(cma['correlation_matrix'])}, "
            f"Σ matrix {len(cma['covariance_matrix'])}×{len(cma['covariance_matrix'])} "
            "(E-6.2 telemetry, direct dump)."
        ),
        "selected_saa_text": (
            f"MVO 결과 (top weights): {' / '.join(saa_text_parts)}. "
            f"E[R]={sel['expected_return'] * 100:.2f}% / σ={sel['volatility'] * 100:.2f}% / "
            f"Sharpe={(sel['sharpe'] if sel['sharpe'] is not None else float('nan')):.4f}."
        ),
        "frontier_summary_text": (
            "Efficient frontier visualization 은 E-9 phase 대상 (현재 미산출)."
        ),
        "constraint_summary_text": (
            "Active constraints: long_only, weight_sum=1.0 (hard). "
            "비활성 (Phase D relaxed): weight_bounds, equity_sum, fixed_income_sum."
        ),
    }

    taa_summary = {
        "title": "TAA Tilt 적용",
        "current_regime_tilt_text": (
            f"Regime {taa_block['current_regime']['regime']} "
            f"({taa_block['current_regime']['regime_label']}) 의 "
            "prototype heuristic tilt 적용."
        ),
        "key_overweights": [
            f"{k} {v['tilt'] * 100:+.2f}pp"
            for k, v in taa_block["tilt_decisions"]["by_asset"].items()
            if v["direction"] == "overweight"
        ],
        "key_underweights": [
            f"{k} {v['tilt'] * 100:+.2f}pp"
            for k, v in taa_block["tilt_decisions"]["by_asset"].items()
            if v["direction"] == "underweight"
        ],
        "before_after_text": (
            f"Before: E[R]={taa_sum['expected_return_before_tilt'] * 100:.2f}% / "
            f"σ={taa_sum['volatility_before_tilt'] * 100:.2f}% / "
            f"Sharpe={(taa_sum['sharpe_before_tilt'] if taa_sum['sharpe_before_tilt'] is not None else float('nan')):.4f}. "
            f"After:  E[R]={taa_sum['expected_return_after_tilt'] * 100:.2f}% / "
            f"σ={taa_sum['volatility_after_tilt'] * 100:.2f}% / "
            f"Sharpe={(taa_sum['sharpe_after_tilt'] if taa_sum['sharpe_after_tilt'] is not None else float('nan')):.4f}."
        ),
        "limitation_text": (
            "Current tilt is generated from regime rule policy, not from "
            "regime-conditioned MVO. Confidence/optimizer 미적용."
        ),
    }

    product_summary = {
        "title": "Product Selection",
        "universe_summary_text": (
            f"raw={universe['raw_count']} / "
            f"passed_filter={universe['passed_filter_count']} / "
            f"classified={universe['classified_count']} (by_asset_class 카운트만 노출)."
        ),
        "selection_method_text": (
            f"score_method={score_method or 'n/a'}. "
            "single_product/manager cap 은 selection logic 내부에서 적용 (E-7 read-only 미평가)."
        ),
        "top_selected_products": [
            f"{r['product_name']} ({r['manager']}, {r['asset_key']}) {r['product_weight'] * 100:.2f}%"
            for r in pa_top
        ],
        "limitation_text": (
            "Score factor 분해 / universe 전체 표 는 E-11 phase 대상 "
            "(selection score 미보존, ticker 미수록)."
        ),
    }

    warnings = [
        {
            "warning_code": "EFRONTIER_DEFERRED",
            "message": "Efficient frontier 미산출 — E-9 phase 대상.",
        },
        {
            "warning_code": "REGIME_HISTORY_PARTIAL",
            "message": (
                f"Regime history {hist['actual_history_months']} obs 한정 — "
                f"{hist['expected_full_history_months']}m timeline 미산출."
            ),
        },
        {
            "warning_code": "TAA_RULE_BASED",
            "message": (
                "TAA 는 rule-based heuristic prototype — "
                "regime-conditioned MVO 미적용."
            ),
        },
        {
            "warning_code": "PRODUCT_SCORE_MISSING",
            "message": "selection score / factor values 미보존 — universe 전체 대비 분석 불가.",
        },
    ]

    missing_data = [
        {
            "field": "saa.efficient_frontier",
            "impact": "selected SAA point 의 frontier 위치 시각화 불가",
            "recommended_next_step": "E-9 phase",
        },
        {
            "field": f"regime.history ({EXPECTED_REGIME_HISTORY_MONTHS}m)",
            "impact": "장기 regime timeline 시각화 불가",
            "recommended_next_step": "regime backfill sidecar 또는 telemetry enhancement",
        },
        {
            "field": "product.scoring.scored_products",
            "impact": "factor 별 score 분해 불가",
            "recommended_next_step": "E-11 phase + selection/tool.py 에서 score 보존",
        },
        {
            "field": "taa.regime_conditioned_assumptions",
            "impact": "regime-aware MVO 비교 불가",
            "recommended_next_step": "future phase (regime_mvo, future study only)",
        },
        {
            "field": "product.selected_products.ticker",
            "impact": "Bloomberg/Reuters ticker 표기 불가",
            "recommended_next_step": "외부 ticker mapping table 도입 또는 DBProductRepository 확장",
        },
    ]

    return {
        "regime_summary": regime_summary,
        "saa_summary": saa_summary,
        "taa_summary": taa_summary,
        "product_selection_summary": product_summary,
        "warnings": warnings,
        "missing_data": missing_data,
    }


# ---------------------------------------------------------------------------
# Top-level builder
# ---------------------------------------------------------------------------


def build_explainability(
    portfolio_json: Path,
    *,
    taa_policy_yaml: Path,
    product_list: Path | None = None,
    operating_mode: str = "relaxed_diagnostic",
) -> dict[str, Any]:
    """portfolio_*.json + taa_policy.yaml → explainability dict (read-only).

    raises ValueError if direct SAA telemetry is missing (E-6.2 T-6).
    """
    portfolio_path = Path(portfolio_json)
    taa_policy_path = Path(taa_policy_yaml)
    product_list_path = Path(product_list) if product_list else None

    # snapshot for mutation guard
    portfolio_raw = portfolio_path.read_text(encoding="utf-8")
    portfolio = json.loads(portfolio_raw)
    portfolio_view = deepcopy(portfolio)

    taa_policy = load_taa_policy_yaml(taa_policy_path)
    product_lookup = load_product_list_lookup(product_list_path)

    meta = _build_meta(
        portfolio_view,
        portfolio_json_path=portfolio_path,
        taa_policy_path=taa_policy_path,
        product_list_path=product_list_path,
        operating_mode=operating_mode,
    )
    regime_block = _build_regime(portfolio_view, taa_policy)
    saa_block = _build_saa(portfolio_view)
    taa_block = _build_taa(portfolio_view, saa_block, taa_policy)
    product_block = _build_product_selection(portfolio_view, product_lookup)
    summary_block = _build_report_ready_summary(
        regime_block, saa_block, taa_block, product_block
    )

    # mutation guard (입력 파일 변경 안 됨 보장)
    assert portfolio_path.read_text(encoding="utf-8") == portfolio_raw

    return {
        "meta": meta,
        "regime_explainability": regime_block,
        "saa_explainability": saa_block,
        "taa_explainability": taa_block,
        "product_selection_explainability": product_block,
        "report_ready_summary": summary_block,
    }


def write_explainability_json(payload: dict[str, Any], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return out_path


def render_explainability_summary_md(
    *,
    as_of_run: str,
    etf_payload: dict[str, Any],
    fund_payload: dict[str, Any],
    out_path: Path,
) -> Path:
    """ETF + Fund 의 report_ready_summary 를 한 페이지 markdown 으로 직렬화."""
    lines: list[str] = []
    lines.append(f"# Portfolio Explainability Summary ({as_of_run})")
    lines.append("")
    lines.append(f"> schema_version: {SCHEMA_VERSION}")
    lines.append("> Read-only diagnostic. Allocation logic was not re-executed.")
    lines.append("")
    for label, payload in (("ETF", etf_payload), ("Fund", fund_payload)):
        lines.append(f"## {label}")
        lines.append("")
        rrs = payload.get("report_ready_summary") or {}
        for sec_key in (
            "regime_summary",
            "saa_summary",
            "taa_summary",
            "product_selection_summary",
        ):
            sec = rrs.get(sec_key) or {}
            lines.append(f"### {sec.get('title') or sec_key}")
            lines.append("")
            for k, v in sec.items():
                if k == "title":
                    continue
                if isinstance(v, list):
                    lines.append(f"- **{k}**:")
                    for item in v:
                        lines.append(f"  - {item}")
                else:
                    lines.append(f"- **{k}**: {v}")
            lines.append("")
        lines.append("### Warnings")
        lines.append("")
        for w in (rrs.get("warnings") or []):
            lines.append(f"- `{w.get('warning_code')}` — {w.get('message')}")
        lines.append("")
        lines.append("### Missing data (deferred)")
        lines.append("")
        for m in (rrs.get("missing_data") or []):
            lines.append(
                f"- **{m.get('field')}** — {m.get('impact')}  "
                f"→ next: {m.get('recommended_next_step')}"
            )
        lines.append("")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


__all__ = [
    "SCHEMA_VERSION",
    "build_explainability",
    "write_explainability_json",
    "render_explainability_summary_md",
    "load_portfolio_json",
    "load_taa_policy_yaml",
    "load_product_list_lookup",
]
