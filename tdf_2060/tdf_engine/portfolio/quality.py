"""Portfolio quality evaluator (Phase B.5+, Phase D relaxed structural).

constraints_passed (제약 통과) 와 별도로, fallback 이 SAA/TAA 의도를 얼마나
훼손했는지 정량 평가.

quality_status 정의:
  - "clean"           : fallback 미사용 + drift 거의 없음
  - "warning"         : fallback 사용 OR no_candidates 발생, drift 작음 (또는 enforcement=review 시 drift exceed)
  - "review_required" : 아래 중 하나라도 해당 (단 enforcement 모드에 따라 drift 분기 변경)
                        - max_abs_asset_weight_drift >= asset_drift_threshold (production / review_required 모드만)
                        - max_abs_bucket_drift >= bucket_drift_threshold (동)
                        - cash_placeholder_weight > 0 (모드 무관, 항상)
                        - any cause == "no_candidates_in_universe" (모드 무관, 항상)

Enforcement modes (Phase D — config-driven):
  - "production"        : drift exceed → review_required (legacy/default 동작)
  - "review_required"   : production 와 동일
  - "review"            : drift exceed → warning (review_required 까지 가지 않음)
  - "warning"           : `review` 의 alias
  - "telemetry_only"    : drift exceed 가 quality_status 에 영향 없음.
                          단 drift 값은 report 필드와 telemetry_notes 에 보존.
                          (relaxed_diagnostic mode 의 default)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

logger = logging.getLogger(__name__)


# 운영 default — Phase D 의 relaxed_diagnostic 시점 임시 1.0 변경 → 0.03 / 0.05 로 복원
# (config-driven 구조 도입으로 yaml 의 drift_thresholds 가 우선. 본 default 는
#  yaml 미존재/누락 시 fallback 으로만 사용.)
DEFAULT_ASSET_DRIFT_THRESHOLD = 0.03   # Phase B.5+ 운영값
DEFAULT_BUCKET_DRIFT_THRESHOLD = 0.05

QUALITY_CLEAN = "clean"
QUALITY_WARNING = "warning"
QUALITY_REVIEW_REQUIRED = "review_required"

# Enforcement modes
ENFORCEMENT_PRODUCTION = "production"
ENFORCEMENT_REVIEW_REQUIRED = "review_required"
ENFORCEMENT_REVIEW = "review"
ENFORCEMENT_WARNING = "warning"
ENFORCEMENT_TELEMETRY_ONLY = "telemetry_only"

_PRODUCTION_LIKE = {ENFORCEMENT_PRODUCTION, ENFORCEMENT_REVIEW_REQUIRED}
_REVIEW_LIKE = {ENFORCEMENT_REVIEW, ENFORCEMENT_WARNING}
_VALID_ENFORCEMENT = (
    _PRODUCTION_LIKE | _REVIEW_LIKE | {ENFORCEMENT_TELEMETRY_ONLY}
)


# Phase D — quality drift source taxonomy (selection + fallback 단계).
# projection drift (taa/projection.py) 와 별개. quality drift 는 product 단계의
# target vs final 차이를 의미.
QUALITY_DRIFT_PRODUCT_CAP_OUTFLOW = "product_cap_clipping_outflow"
QUALITY_DRIFT_FALLBACK_INFLOW = "fallback_redistribution_inflow"
QUALITY_DRIFT_SELECTION_SHORTFALL = "selection_shortfall"
QUALITY_DRIFT_SELECTION_OVERFLOW = "selection_overflow"
QUALITY_DRIFT_NONE = "none"


def _classify_quality_drift_source(
    target: dict[str, float],
    final: dict[str, float],
    fallback_diagnostics: dict[str, Any],
    atol: float = 1e-6,
) -> tuple[dict[str, str], dict[str, Any]]:
    """quality drift (target vs final asset weights) 를 source 별로 분류.

    selection + fallback 단계의 drift. projection drift 와 별개.
    Source:
      product_cap_clipping_outflow : 자산이 fallback 의 source (target 대비 final 작음)
      fallback_redistribution_inflow : 자산이 fallback 의 absorber (target 대비 final 큼)
      selection_shortfall          : 자산이 target 대비 final 작음 (fallback source 아님)
      selection_overflow           : 자산이 target 대비 final 큼 (absorber 아님)
      none                         : drift ≈ 0
    """
    sources: dict[str, str] = {}

    fb_absorbers = fallback_diagnostics.get("fallback_absorbers") or []
    absorbed_from_source: dict[str, float] = {}
    absorbed_to_recipient: dict[str, float] = {}
    for ab in fb_absorbers:
        src = str(ab.get("source_asset_key") or "")
        abr = str(ab.get("absorber_asset_key") or "")
        amt = float(ab.get("absorbed_weight", 0))
        if src:
            absorbed_from_source[src] = absorbed_from_source.get(src, 0.0) + amt
        if abr:
            absorbed_to_recipient[abr] = absorbed_to_recipient.get(abr, 0.0) + amt

    # Phase E-6.2 — deterministic ordering for diagnostics serialization.
    # set iteration 은 Python hash randomization 영향으로 매 run 다른 순서 → drift_clipping_summary
    # 의 outflow_assets / inflow_assets list 순서가 비결정적이었음. logical equivalent.
    all_keys = sorted(set(target.keys()) | set(final.keys()))

    for k in all_keys:
        t = float(target.get(k, 0.0))
        f = float(final.get(k, 0.0))
        drift = f - t
        if abs(drift) < atol:
            sources[k] = QUALITY_DRIFT_NONE
            continue
        if drift < -atol:
            if absorbed_from_source.get(k, 0.0) > atol:
                sources[k] = QUALITY_DRIFT_PRODUCT_CAP_OUTFLOW
            else:
                sources[k] = QUALITY_DRIFT_SELECTION_SHORTFALL
        else:  # drift > atol
            if absorbed_to_recipient.get(k, 0.0) > atol:
                sources[k] = QUALITY_DRIFT_FALLBACK_INFLOW
            else:
                sources[k] = QUALITY_DRIFT_SELECTION_OVERFLOW

    outflow = [k for k, s in sources.items() if s == QUALITY_DRIFT_PRODUCT_CAP_OUTFLOW]
    outflow_amt = {k: float(target.get(k, 0) - final.get(k, 0)) for k in outflow}
    total_outflow = sum(abs(v) for v in outflow_amt.values())

    inflow = [k for k, s in sources.items() if s == QUALITY_DRIFT_FALLBACK_INFLOW]
    inflow_amt = {k: float(final.get(k, 0) - target.get(k, 0)) for k in inflow}
    total_inflow = sum(abs(v) for v in inflow_amt.values())

    sources_count: dict[str, int] = {}
    for s in sources.values():
        if s == QUALITY_DRIFT_NONE:
            continue
        sources_count[s] = sources_count.get(s, 0) + 1
    primary = (
        max(sources_count.items(), key=lambda kv: kv[1])[0]
        if sources_count else QUALITY_DRIFT_NONE
    )

    summary = {
        "n_assets_with_outflow": len(outflow),
        "outflow_assets": outflow,
        "outflow_by_asset": outflow_amt,
        "total_outflow_magnitude": total_outflow,
        "n_assets_with_inflow": len(inflow),
        "inflow_assets": inflow,
        "inflow_by_asset": inflow_amt,
        "total_inflow_magnitude": total_inflow,
        "drift_source_primary": primary,
        "drift_source_counts": sources_count,
    }
    return sources, summary


def _normalize_enforcement(enforcement: str | None) -> str:
    """알 수 없는 값은 production 으로 fallback (안전 default)."""
    if not enforcement:
        return ENFORCEMENT_PRODUCTION
    e = str(enforcement).strip().lower()
    if e in _VALID_ENFORCEMENT:
        return e
    logger.warning("unknown enforcement mode '%s', falling back to 'production'", e)
    return ENFORCEMENT_PRODUCTION


@dataclass
class QualityReport:
    quality_status: str = QUALITY_CLEAN
    target_asset_weights: dict[str, float] = field(default_factory=dict)
    final_asset_weights: dict[str, float] = field(default_factory=dict)
    asset_weight_drift: dict[str, float] = field(default_factory=dict)
    max_abs_asset_weight_drift: float = 0.0
    drift_by_bucket: dict[str, float] = field(default_factory=dict)
    max_abs_bucket_drift: float = 0.0
    cash_placeholder_weight: float = 0.0
    review_reasons: list[str] = field(default_factory=list)
    fallback_absorbers: list[dict] = field(default_factory=list)
    # Phase D — enforcement / drift telemetry 분리
    enforcement_mode: str = ENFORCEMENT_PRODUCTION
    asset_drift_threshold: float = DEFAULT_ASSET_DRIFT_THRESHOLD
    bucket_drift_threshold: float = DEFAULT_BUCKET_DRIFT_THRESHOLD
    drift_telemetry_notes: list[str] = field(default_factory=list)
    # Phase D — quality drift source 분류 (selection + fallback 단계)
    drift_source_by_asset: dict[str, str] = field(default_factory=dict)
    drift_clipping_summary: dict[str, Any] = field(default_factory=dict)


def evaluate_quality(
    target_asset_weights: "pd.Series",
    product_weights: "pd.DataFrame",
    fallback_diagnostics: dict[str, Any],
    selection_diagnostics: dict[str, Any],
    bucket_by_asset: dict[str, str],
    asset_drift_threshold: float = DEFAULT_ASSET_DRIFT_THRESHOLD,
    bucket_drift_threshold: float = DEFAULT_BUCKET_DRIFT_THRESHOLD,
    enforcement: str = ENFORCEMENT_PRODUCTION,
) -> QualityReport:
    import pandas as pd

    enforcement = _normalize_enforcement(enforcement)
    report = QualityReport(
        enforcement_mode=enforcement,
        asset_drift_threshold=float(asset_drift_threshold),
        bucket_drift_threshold=float(bucket_drift_threshold),
    )

    target = {str(k): float(v) for k, v in target_asset_weights.items()}
    report.target_asset_weights = target

    # final_asset_weights = product_weights 의 asset_key 별 합
    if not product_weights.empty:
        final_series = product_weights.groupby("asset_key")["weight"].sum()
        final = {str(k): float(v) for k, v in final_series.items()}
    else:
        final = {}
    report.final_asset_weights = final

    # drift = final - target. cash 등 신규 asset_key 도 포함.
    all_keys = set(target.keys()) | set(final.keys())
    drift = {k: final.get(k, 0.0) - target.get(k, 0.0) for k in all_keys}
    report.asset_weight_drift = drift
    report.max_abs_asset_weight_drift = (
        max(abs(v) for v in drift.values()) if drift else 0.0
    )

    # bucket drift
    bucket_target: dict[str, float] = {}
    bucket_final: dict[str, float] = {}
    for k, v in target.items():
        b = bucket_by_asset.get(k, "unmapped")
        bucket_target[b] = bucket_target.get(b, 0.0) + v
    for k, v in final.items():
        b = bucket_by_asset.get(k, "cash" if k == "cash" else "unmapped")
        bucket_final[b] = bucket_final.get(b, 0.0) + v
    bucket_keys = set(bucket_target) | set(bucket_final)
    bucket_drift = {b: bucket_final.get(b, 0.0) - bucket_target.get(b, 0.0) for b in bucket_keys}
    report.drift_by_bucket = bucket_drift
    report.max_abs_bucket_drift = (
        max(abs(v) for v in bucket_drift.values()) if bucket_drift else 0.0
    )

    report.cash_placeholder_weight = float(
        fallback_diagnostics.get("cash_placeholder_weight", 0.0)
    )
    report.fallback_absorbers = list(fallback_diagnostics.get("fallback_absorbers") or [])

    fb_used = bool(fallback_diagnostics.get("fallback_used", False))
    unfilled = selection_diagnostics.get("unfilled_by_asset_class") or {}
    has_no_candidates = any(
        e.get("cause") == "no_candidates_in_universe" for e in unfilled.values()
    )

    # drift exceed reasons (telemetry — 모드 무관 하게 계산)
    drift_reasons: list[str] = []
    if report.max_abs_asset_weight_drift >= asset_drift_threshold - 1e-12:
        drift_reasons.append(
            f"asset drift {report.max_abs_asset_weight_drift:.4f} "
            f">= threshold {asset_drift_threshold:.4f}"
        )
    if report.max_abs_bucket_drift >= bucket_drift_threshold - 1e-12:
        drift_reasons.append(
            f"bucket drift {report.max_abs_bucket_drift:.4f} "
            f">= threshold {bucket_drift_threshold:.4f}"
        )

    # 모드 무관 — 항상 review_required 트리거 (data integrity / coverage 이슈)
    other_reasons: list[str] = []
    if report.cash_placeholder_weight > 1e-12:
        other_reasons.append(
            f"cash_placeholder_weight {report.cash_placeholder_weight:.4f} > 0"
        )
    if has_no_candidates:
        no_cand_keys = [
            k for k, e in unfilled.items()
            if e.get("cause") == "no_candidates_in_universe"
        ]
        other_reasons.append(f"no_candidates_in_universe: {no_cand_keys}")

    # quality_status 결정 (enforcement 모드별 분기)
    if enforcement == ENFORCEMENT_TELEMETRY_ONLY:
        # drift 는 quality_status 에 영향 없음. drift_reasons 는 telemetry 만.
        if other_reasons:
            report.quality_status = QUALITY_REVIEW_REQUIRED
            report.review_reasons = other_reasons
        elif fb_used:
            report.quality_status = QUALITY_WARNING
            report.review_reasons = [
                f"fallback used (max_drift={report.max_abs_asset_weight_drift:.4f}; "
                f"drift enforcement=telemetry_only)"
            ]
        else:
            report.quality_status = QUALITY_CLEAN
        # drift exceed 는 telemetry_notes 에 보존
        if drift_reasons:
            report.drift_telemetry_notes = list(drift_reasons)
    elif enforcement in _REVIEW_LIKE:
        # drift exceed → warning (review_required 까지 안 감)
        if other_reasons:
            report.quality_status = QUALITY_REVIEW_REQUIRED
            report.review_reasons = other_reasons
        elif drift_reasons or fb_used:
            report.quality_status = QUALITY_WARNING
            wr = list(drift_reasons)
            if fb_used:
                wr.append(
                    f"fallback used (max_drift={report.max_abs_asset_weight_drift:.4f})"
                )
            report.review_reasons = wr
        else:
            report.quality_status = QUALITY_CLEAN
    else:  # production / review_required
        all_reasons = drift_reasons + other_reasons
        if all_reasons:
            report.quality_status = QUALITY_REVIEW_REQUIRED
            report.review_reasons = all_reasons
        elif fb_used:
            report.quality_status = QUALITY_WARNING
            report.review_reasons = [
                f"fallback used (max_drift={report.max_abs_asset_weight_drift:.4f})"
            ]
        else:
            report.quality_status = QUALITY_CLEAN

    # Phase D — quality drift source 분류 (모든 모드에서 적용, telemetry)
    src_by_asset, clip_summary = _classify_quality_drift_source(
        target=target,
        final=final,
        fallback_diagnostics=fallback_diagnostics,
    )
    report.drift_source_by_asset = src_by_asset
    report.drift_clipping_summary = clip_summary

    return report
