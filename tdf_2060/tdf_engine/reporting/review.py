"""Phase C.4 — 운용자 검토용 review packet.

구조 (dict):
  review_summary       : 한눈 요약 (constraints / quality / drift / fallback / projection / counts)
  projection_summary   : projection 영향 (음수→0, bucket before/after, top5 drift)
  asset_allocation     : SAA / TAA target / final / drift / bound status (자산 단위)
  product_allocation   : 상품 단위 enriched (bucket / source_asset_weight / fallback_absorbed / flags)
  policy_review_items  : 운용역 확인 필요 항목 (휴리스틱)

  -- Phase D.2 추가 (rendering 보강용 derive 키, 기존 키는 무변경) --
  executive_summary    : 한눈 go/no-go (portfolio_type, sums, warnings, decision placeholder)
  regime_context       : ECI regime 정보 (region, placement, velocity, regime, label)
  bucket_summary       : 주식/채권/HY 합계와 목표 범위 충족 여부
  excluded_summary     : 유니버스 분류/제외 카운트 (개별 ID 미노출 — telemetry 한계)
  warning_register     : validation/db warning을 D-ID(Decision Register) 와 best-effort 연결
  review_checklist     : 운용역이 한 번 보고 체크할 표준 목록 (정적)
  future_telemetry_notes: 현재 노출 안 된 telemetry 후보 (SAA, tilt, excluded list)

코어 로직 변경 없이 portfolio.diagnostics 만 사용해서 derive.
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd
    from tdf_engine.domain.models import AssetClassInfo, PortfolioResult

logger = logging.getLogger(__name__)


# ── helper ─────────────────────────────────────────────────────────────


def _bucket_by_asset(assets: list["AssetClassInfo"] | None) -> dict[str, str]:
    if not assets:
        return {}
    return {a.asset_key: a.bucket.value for a in assets}


def _final_asset_bounds(tdf_config: dict | None) -> dict[str, dict[str, float]]:
    if not tdf_config:
        return {}
    return tdf_config.get("final_asset_bounds") or {}


def _bound_status(weight: float, bounds: dict[str, float] | None) -> str:
    if not bounds:
        return "no_bound"
    lb = float(bounds.get("min", 0.0))
    ub = float(bounds.get("max", 1.0))
    if weight < lb - 1e-6:
        return "violation_below"
    if weight > ub + 1e-6:
        return "violation_above"
    if weight < lb + 0.005 or weight > ub - 0.005:
        return "near_bound"
    return "ok"


# ── packet builder ────────────────────────────────────────────────────


def build_review_packet(
    portfolio: "PortfolioResult",
    assets: list["AssetClassInfo"] | None = None,
    tdf_config: dict | None = None,
) -> dict[str, Any]:
    """portfolio + 도메인 정보 → 운용자 검토용 packet."""

    bucket_by_asset = _bucket_by_asset(assets)
    fab = _final_asset_bounds(tdf_config)
    diag = portfolio.diagnostics or {}
    taa_diag = diag.get("taa_diagnostics") or {}
    feas = taa_diag.get("taa_feasibility") or {}
    fb = diag.get("fallback") or {}
    quality = diag.get("quality") or {}
    val = diag.get("validation") or {}
    db = diag.get("db_source") or {}
    sel_diag = diag.get("selection_diagnostics") or {}
    saa_diag = diag.get("saa_diagnostics") or {}

    # bucket sums (after projection)
    bucket_sums_after = (taa_diag.get("bucket_sums") or {})
    eq_after = float(bucket_sums_after.get("equity", 0.0))
    fi_after = float(bucket_sums_after.get("fixed_income", 0.0))

    # ── review_summary ─────────────────────────────────────────────
    review_summary = {
        "source_type": db.get("source_type", "file"),
        "as_of_date": db.get("as_of_date"),
        "portfolio_type": portfolio.portfolio_type.value,
        "constraints_passed": bool(portfolio.constraints_passed),
        "quality_status": quality.get("quality_status"),
        "asset_weight_sum": float(portfolio.asset_weights.sum()),
        "product_weight_sum": (
            float(portfolio.product_weights["weight"].sum())
            if not portfolio.product_weights.empty else 0.0
        ),
        "equity_bucket_weight": eq_after,
        "fixed_income_bucket_weight": fi_after,
        "fallback_used": bool(fb.get("fallback_used", False)),
        "projection_used": bool(feas.get("projection_used", False)),
        "max_abs_projection_drift": float(feas.get("max_abs_projection_drift", 0.0)),
        "max_abs_asset_weight_drift": float(quality.get("max_abs_asset_weight_drift", 0.0)),
        "proxy_used": bool(db.get("proxy_used", False)),
        "db_warnings_count": len(db.get("warnings") or []),
        "validation_issues_count": len(val.get("issues") or []),
        "validation_warnings_count": len(val.get("warnings") or []),
    }

    # ── projection_summary ─────────────────────────────────────────
    target_before = feas.get("target_weights_before_projection") or {}
    final_after = feas.get("final_weights_after_projection") or {
        k: float(v) for k, v in portfolio.asset_weights.items()
    }
    drifts = feas.get("asset_weight_drift_from_target") or {}
    sorted_drifts = sorted(drifts.items(), key=lambda kv: -abs(float(kv[1])))[:5]
    projection_summary = {
        "projection_used": bool(feas.get("projection_used", False)),
        "projection_success": bool(feas.get("projection_success", True)),
        "reason": feas.get("projection_message", ""),
        "negative_assets_before_projection": dict(
            feas.get("negative_weight_assets_before_projection") or {}
        ),
        "bucket_before": dict(feas.get("bucket_weights_before_projection") or {}),
        "bucket_after": dict(feas.get("bucket_weights_after_projection") or bucket_sums_after),
        "max_abs_projection_drift": float(feas.get("max_abs_projection_drift", 0.0)),
        "largest_projection_drifts_top5": [
            {"asset_key": k, "drift": float(v),
             "before": float(target_before.get(k, 0.0)),
             "after":  float(final_after.get(k, 0.0))}
            for k, v in sorted_drifts
        ],
    }

    # ── asset_allocation comparison ────────────────────────────────
    # Phase E-6.2 (T-6): direct SAA weights telemetry 가 saa_diagnostics["saa_weights"]
    # 에 dump 되므로 본 컬럼에서도 직접 노출. 역산(taa_target − asset_tilts) 사용 금지.
    # telemetry 부재 시 (이전 산출물 호환) None 유지.
    saa_weights_direct = saa_diag.get("saa_weights") or {}
    asset_allocation: list[dict] = []
    for ak, fw in portfolio.asset_weights.items():
        b = bucket_by_asset.get(ak)
        bnd = fab.get(ak)
        target_w = float(target_before.get(ak, fw))
        final_w = float(fw)
        proj_drift = float(drifts.get(ak, 0.0))
        saa_val = saa_weights_direct.get(ak)
        asset_allocation.append({
            "asset_key": ak,
            "asset_name": ak,
            "bucket": b,
            "saa_weight": (float(saa_val) if saa_val is not None else None),
            "taa_target_weight_before_projection": target_w,
            "final_asset_weight": final_w,
            "projection_drift": proj_drift,
            "final_bound_lower": float(bnd["min"]) if bnd else None,
            "final_bound_upper": float(bnd["max"]) if bnd else None,
            "bound_status": _bound_status(final_w, bnd),
        })

    # ── product_allocation enriched ────────────────────────────────
    pw_df = portfolio.product_weights
    asset_w_map = {k: float(v) for k, v in portfolio.asset_weights.items()}
    unfilled = sel_diag.get("unfilled_by_asset_class") or {}
    fb_absorbers = fb.get("fallback_absorbers") or []
    absorbed_by_pid: dict[str, float] = {}
    for ab in fb_absorbers:
        pid = str(ab.get("product_id") or "")
        absorbed_by_pid[pid] = absorbed_by_pid.get(pid, 0.0) + float(ab.get("absorbed_weight", 0.0))

    product_allocation: list[dict] = []
    if not pw_df.empty:
        for _, r in pw_df.iterrows():
            ak = str(r.get("asset_key") or "")
            pid = str(r.get("product_id") or "")
            cause = (unfilled.get(ak) or {}).get("cause")
            flags: list[str] = []
            if cause:
                flags.append(f"unfilled_cause={cause}")
            if pid in absorbed_by_pid:
                flags.append("fallback_absorber")
            if pid == "__CASH__":
                flags.append("cash_placeholder")
            product_allocation.append({
                "product_type": portfolio.portfolio_type.value,
                "asset_key": ak,
                "bucket": bucket_by_asset.get(ak),
                "product_id": pid,
                "product_name": r.get("name"),
                "manager": r.get("manager"),
                "role": r.get("role"),
                "score": None,  # selection diagnostics 에 score 미보존 (코어 미변경 정책)
                "final_weight": float(r.get("weight", 0.0)),
                "source_asset_weight": asset_w_map.get(ak),
                "selection_reason": cause,
                "fallback_absorbed_weight": float(absorbed_by_pid.get(pid, 0.0)),
                "warning_flags": flags,
            })

    # ── policy_review_items ────────────────────────────────────────
    # Phase D relaxed (2026-05-08, D-10 closed): 자산 0% 자체는 허용 (정책 #3).
    # zero/near_bound 항목은 final_asset_bounds 가 의미 있는 운영 정책일 때만 emit.
    # bounds 가 [0, 1] (Phase D 기본) 이면 silent 처리.
    items: list[str] = []

    def _has_meaningful_bound(b: dict | None) -> bool:
        """bound 가 [0, 1] (no-op) 가 아니라 운영상 의미 있는 제약인지."""
        if not b:
            return False
        return float(b.get("min", 0.0)) > 0.0 or float(b.get("max", 1.0)) < 1.0

    # 1) zero weight — bounds 가 의미 있고 lower>0 일 때만 violation 으로 보고
    for ak, fw in portfolio.asset_weights.items():
        bnd = fab.get(ak)
        if float(fw) <= 1e-9 and bnd and float(bnd.get("min", 0.0)) > 0.0:
            items.append(
                f"{ak} final weight is 0.00%; "
                f"violates final_asset_bounds.min={float(bnd['min']):.4%}."
            )
    # 2) violation_below / violation_above — 항상 critical (long-only + sum=1 위반은 별도)
    # 3) near_bound — bounds 가 의미 있을 때만 emit
    for row in asset_allocation:
        if row["bound_status"] == "violation_below":
            items.append(
                f"{row['asset_key']} final weight {row['final_asset_weight']:.4%} "
                f"< final_bound_lower {row['final_bound_lower']:.4%}; "
                f"confirm whether this violates intended lower bound."
            )
        elif row["bound_status"] == "violation_above":
            items.append(
                f"{row['asset_key']} final weight {row['final_asset_weight']:.4%} "
                f"> final_bound_upper {row['final_bound_upper']:.4%}; "
                f"confirm acceptability."
            )
        elif row["bound_status"] == "near_bound":
            bnd = fab.get(row["asset_key"])
            if _has_meaningful_bound(bnd):
                items.append(
                    f"{row['asset_key']} final weight {row['final_asset_weight']:.4%} "
                    f"is near a final bound; confirm cap appropriateness."
                )
    # 3) projection drift 큼
    if projection_summary["projection_used"]:
        d = projection_summary["max_abs_projection_drift"]
        if d > 0:
            items.append(
                f"projection was used; confirm max_abs_projection_drift "
                f"{d:.4%} is acceptable."
            )
    # 4) DB sanity flags / lookback 짧음
    db_sanity = db.get("sanity") or {}
    obs_counts = {k: int(s.get("obs_count", 0)) for k, s in db_sanity.items()}
    if obs_counts:
        max_obs = max(obs_counts.values())
        for k, n in obs_counts.items():
            if max_obs and n < max_obs * 0.8:
                items.append(
                    f"{k} has shorter history, obs={n} vs others {max_obs}; "
                    f"confirm lookback policy."
                )
    # 5) cash placeholder
    if (fb.get("cash_placeholder_weight") or 0.0) > 1e-9:
        items.append(
            f"cash placeholder used: weight={float(fb['cash_placeholder_weight']):.4%}; "
            f"confirm post-process to MMF/short-bond."
        )
    # 6) no_candidates_in_universe
    no_cand = [k for k, e in unfilled.items() if e.get("cause") == "no_candidates_in_universe"]
    if no_cand:
        items.append(
            f"no_candidates_in_universe asset classes: {no_cand}; "
            f"confirm classifier rules / product universe coverage."
        )

    # ── Phase D.2 derived sections (rendering 보강용) ──────────────────
    regime_blob = diag.get("regime") or {}
    universe_diag = diag.get("universe_diagnostics") or {}

    return {
        "review_summary": review_summary,
        "projection_summary": projection_summary,
        "asset_allocation": asset_allocation,
        "product_allocation": product_allocation,
        "policy_review_items": items,
        # ── Phase D.2 신규 (기존 키와 독립) ─────────────────────────
        "operating_mode_banner": _build_operating_mode_banner(tdf_config),
        "_quality_diag": dict(quality),  # enforcement / drift_telemetry_notes / thresholds 노출용
        # Phase D — drift_source breakdown (projection + quality 두 단계)
        "_diagnostics_drift": {
            "projection_clipping_summary": dict(feas.get("clipping_summary") or {}),
            "projection_drift_source_by_asset": dict(feas.get("drift_source_by_asset") or {}),
            "projection_asset_drift_from_target": dict(feas.get("asset_weight_drift_from_target") or {}),
            "quality_drift_clipping_summary": dict(quality.get("drift_clipping_summary") or {}),
            "quality_drift_source_by_asset": dict(quality.get("drift_source_by_asset") or {}),
            "quality_asset_weight_drift": dict(quality.get("asset_weight_drift") or {}),
        },
        "executive_summary": _build_executive_summary(review_summary),
        "regime_context": _build_regime_context(regime_blob, taa_diag),
        "bucket_summary": _build_bucket_summary(review_summary, tdf_config, portfolio),
        "excluded_summary": _build_excluded_summary(universe_diag, sel_diag),
        "warning_register": _build_warning_register(val, db, items),
        "review_checklist": _build_review_checklist(),
        "future_telemetry_notes": _build_future_telemetry_notes(),
    }


# ── Phase D.2 — derive helpers ────────────────────────────────────────


def _build_executive_summary(rs: dict) -> dict:
    """한눈 go/no-go (Section A)."""
    warn_cnt = int(rs.get("validation_warnings_count", 0)) + int(rs.get("db_warnings_count", 0))
    return {
        "portfolio_type": rs.get("portfolio_type"),
        "as_of_date": rs.get("as_of_date"),
        "constraints_passed": bool(rs.get("constraints_passed")),
        "quality_status": rs.get("quality_status"),
        "asset_weight_sum": float(rs.get("asset_weight_sum", 0.0)),
        "product_weight_sum": float(rs.get("product_weight_sum", 0.0)),
        "equity_weight": float(rs.get("equity_bucket_weight", 0.0)),
        "fixed_income_weight": float(rs.get("fixed_income_bucket_weight", 0.0)),
        "warning_count_total": warn_cnt,
        "reviewer_decision_options": ["Approve", "Revise", "Hold"],
        "reviewer_decision_selected": None,  # 운용역이 직접 체크
    }


def _build_regime_context(regime_blob: dict, taa_diag: dict) -> dict:
    """ECI regime 정보 (Section B 컨텍스트)."""
    return {
        "as_of": regime_blob.get("as_of"),
        "region": regime_blob.get("region"),
        "placement": (
            float(regime_blob["placement"]) if regime_blob.get("placement") is not None else None
        ),
        "velocity": (
            float(regime_blob["velocity"]) if regime_blob.get("velocity") is not None else None
        ),
        "regime_id": regime_blob.get("regime") or taa_diag.get("regime"),
        "regime_label": regime_blob.get("regime_label") or taa_diag.get("regime_label"),
    }


def _build_bucket_summary(rs: dict, tdf_config: dict | None, portfolio) -> dict:
    """주식/채권/HY 합계 + sanity monitoring 범위 (Section C).

    Phase D relaxed (D-01 closed): bucket range hard bound 비활성.
    아래 range 는 **sanity monitoring only — NOT enforced**.
    이탈 시 fail 이 아닌 운용역 검토 flag.
    """
    eq_w = float(rs.get("equity_bucket_weight", 0.0))
    fi_w = float(rs.get("fixed_income_bucket_weight", 0.0))

    # Phase D relaxed sanity range. yaml taa_sanity_range 우선,
    # 없으면 user 정책 default [60%, 95%] / [5%, 40%].
    cfg = tdf_config or {}
    sr = cfg.get("taa_sanity_range") or {}
    eq_min = float(sr.get("equity_min", 0.60))
    eq_max = float(sr.get("equity_max", 0.95))
    fi_min = float(sr.get("fixed_income_min", 0.05))
    fi_max = float(sr.get("fixed_income_max", 0.40))

    eq_in_range = eq_min - 1e-9 <= eq_w <= eq_max + 1e-9
    fi_in_range = fi_min - 1e-9 <= fi_w <= fi_max + 1e-9

    # HY weight (us_high_yield 자산군)
    hy_w = 0.0
    try:
        hy_w = float(portfolio.asset_weights.get("us_high_yield", 0.0))
    except Exception:  # pragma: no cover
        hy_w = 0.0

    return {
        "equity_total": eq_w,
        "equity_sanity_range": {"min": eq_min, "max": eq_max},
        "equity_in_sanity_range": bool(eq_in_range),
        "fixed_income_total": fi_w,
        "fixed_income_sanity_range": {"min": fi_min, "max": fi_max},
        "fixed_income_in_sanity_range": bool(fi_in_range),
        "us_high_yield_weight": hy_w,
        "us_high_yield_classification": "fixed_income bucket + risk_asset + credit (D-07 closed)",
        "monitoring_only_note": "위 sanity range 는 hard bound 가 아니며, 이탈 시 fail 이 아닌 운용역 검토 flag (D-01 closed).",
        # 호환 키 (기존 packet schema 보존)
        "equity_target_range": {"min": eq_min, "max": eq_max},
        "equity_in_range": bool(eq_in_range),
        "fixed_income_target_range": {"min": fi_min, "max": fi_max},
        "fixed_income_in_range": bool(fi_in_range),
    }


def _build_excluded_summary(universe_diag: dict, sel_diag: dict) -> dict:
    """제외/필터링 카운트 (Section E — 개별 ID 미노출 한계 명시)."""
    total = int(universe_diag.get("total_products", 0))
    raw = int(universe_diag.get("raw_count", 0))
    passed = int(universe_diag.get("passed_filter_count", 0))
    classified = int(universe_diag.get("classified_count", 0))
    excluded = int(universe_diag.get("excluded_count", 0))
    by_class = dict(universe_diag.get("classified_by_asset_class") or {})
    zero_classes = list(universe_diag.get("asset_classes_with_zero_count") or [])
    grade_filtered = int(sel_diag.get("grade_filtered_count", 0))
    grade_penalized = int(sel_diag.get("grade_penalized_count", 0))
    return {
        "total_products": total,
        "raw_count": raw,
        "passed_filter_count": passed,
        "classified_count": classified,
        "excluded_count": excluded,
        "classified_by_asset_class": by_class,
        "asset_classes_with_zero_count": zero_classes,
        "grade_filtered_count": grade_filtered,
        "grade_penalized_count": grade_penalized,
        "individual_excluded_list_available": False,
        "note": (
            "개별 제외 상품 ID/사유 목록은 현재 universe_diagnostics 에 미노출 "
            "(future telemetry §10 참고)."
        ),
    }


# ── Decision Register linker (Section F — best-effort) ────────────────
#
# 우선순위 기반 매핑. 더 구체적인 패턴(BRFUT004/projection/cap 등) 부터 검사하고,
# 마지막에 자산명 fallback. ust30 의 경우 BRFUT004/file mode/proxy 키워드만 D-04
# 로 가고, zero/0%/near bound/negative/lookback 등은 정책 결정 필요 항목(D-10/02/03)
# 으로 분리한다.
#
# 정확 매핑은 운용역 검토 후 본 함수의 키워드를 갱신하면 된다.


def _has_any(msg: str, *keywords: str) -> bool:
    return any(k in msg for k in keywords)


def _link_decision(message: str) -> str | None:
    if not message:
        return None
    msg = message.lower()

    # 1) BRFUT004 mapping / fallback / file mode / hard error / proxy → D-04 (closed)
    if _has_any(
        msg,
        "brfut004", "file mode", "explicit_proxy_only",
        "no_silent_fallback", "hard_error_if_missing", "proxy_used",
        "tlt", "edv", "usgg10yr", "usgg30yr",
    ):
        return "D-04"

    # 2) Projection drift → D-02
    if _has_any(
        msg,
        "max_abs_projection_drift", "projection was used",
        "taa_projection_used", "projection_drift",
    ):
        return "D-02"

    # 3) Lookback / obs / shorter history → D-03
    if _has_any(msg, "lookback", "obs=", "shorter history"):
        return "D-03"

    # 4) us_value / us_growth / cap clipping → D-12 (us_value 30% cap 적정성)
    if _has_any(
        msg,
        "us_value_equity", "us_growth_equity",
        "cap clipping", "product_cap_clipping",
    ):
        return "D-12"

    # 5) dm_ex_us_equity → D-11
    if "dm_ex_us_equity" in msg:
        return "D-11"

    # 6) negative weights / zero allocation / final 0% / near bound → D-10
    #    (ust30/kr_t10 의 zero allocation·near bound 는 정책 결정)
    if _has_any(
        msg,
        "negative weights", "negative weight",
        "zero allocation", "zero weight",
        "final weight is 0.00", "final weight 0.00",
        "near a final bound", "near_bound",
    ):
        return "D-10"

    # 7) ust30 / kr_t10 자산명 fallback → D-10 (default)
    if _has_any(msg, "us_treasury_30y", "kr_treasury_10y"):
        return "D-10"

    # 8) quant_grade / score / candidates / cash placeholder → D-13
    if _has_any(
        msg,
        "quant_grade", "no_candidates_in_universe",
        "cash placeholder", "grade_filtered",
    ):
        return "D-13"

    # 9) 운용사 / manager / concentration → D-14
    if _has_any(msg, "manager", "concentration"):
        return "D-14"

    # 10) generic final_bound (자산 미특정) → D-01
    if "final_bound" in msg:
        return "D-01"

    return None


# Phase D relaxed (2026-05-08): closed/deferred D-IDs 는 informational only.
# decision_required 는 active D-IDs 로 매핑된 경우에만 True.
ACTIVE_DECISION_IDS = {"D-02", "D-03", "D-06", "D-08", "D-09", "D-13", "D-14"}
INFO_ONLY_DECISION_IDS = {"D-01", "D-04", "D-05", "D-07", "D-10", "D-11", "D-12"}


def _is_active_decision(linked: str | None) -> bool:
    if not linked:
        return False
    head = linked.split(" ")[0].strip()
    return head in ACTIVE_DECISION_IDS


def _build_warning_register(val: dict, db: dict, policy_items: list[str]) -> list[dict]:
    """validation / db / policy_review 항목을 통합 + D-ID 연결 (Section F).

    Phase D relaxed: linked_decision 이 closed/deferred 면 decision_required=False.
    """
    out: list[dict] = []
    for i, m in enumerate(val.get("warnings") or []):
        link = _link_decision(str(m))
        out.append({
            "warning_id": f"VAL-{i+1:02d}",
            "severity": "warning",
            "source": "validation",
            "message": str(m),
            "linked_decision_id": link,
            "decision_required": _is_active_decision(link),
        })
    for i, m in enumerate(val.get("issues") or []):
        link = _link_decision(str(m))
        out.append({
            "warning_id": f"VAL-ISSUE-{i+1:02d}",
            "severity": "issue",
            "source": "validation",
            "message": str(m),
            "linked_decision_id": link,
            "decision_required": True,  # issues 는 항상 required (sum/negative/optimizer 등)
        })
    for i, m in enumerate(db.get("warnings") or []):
        link = _link_decision(str(m))
        out.append({
            "warning_id": f"DB-{i+1:02d}",
            "severity": "warning",
            "source": "db_source",
            "message": str(m),
            "linked_decision_id": link,
            "decision_required": _is_active_decision(link),
        })
    for i, m in enumerate(policy_items or []):
        link = _link_decision(str(m))
        out.append({
            "warning_id": f"POL-{i+1:02d}",
            "severity": "review_required",
            "source": "policy_review_items",
            "message": str(m),
            "linked_decision_id": link,
            "decision_required": _is_active_decision(link),
        })
    return out


def _build_review_checklist() -> list[dict]:
    """운용역 표준 체크리스트 (Section G)."""
    return [
        {"key": "asset_allocation_range", "label": "자산배분 범위 적정 (주식 75~85%, 채권 15~25%)", "checked": False},
        {"key": "ust30_brfut004", "label": "미국 국고채30년 BRFUT004 처리 확인 (D-04 closed)", "checked": False},
        {"key": "hy_in_fi_bucket", "label": "HY 채권 버킷 편입 적정 (risk_asset + credit, D-07 closed)", "checked": False},
        {"key": "asset_concentration", "label": "특정 자산군 쏠림 적정 (us_value cap 30% — D-12)", "checked": False},
        {"key": "manager_concentration", "label": "특정 상품/운용사 쏠림 적정 (D-14)", "checked": False},
        {"key": "exclusion_rules", "label": "제외 상품 규칙 적정 (혼합형/TDF/TIF/TRF/멀티에셋/재간접)", "checked": False},
        {"key": "warnings_acceptable", "label": "warning 수용 가능 (Section 5.1 Warning Register 검토)", "checked": False},
        {"key": "final_decision", "label": "최종 결정", "checked": False,
         "options": ["Approve", "Revise", "Hold"]},
    ]


def _build_operating_mode_banner(tdf_config: dict | None) -> dict:
    """Phase D relaxed: operating_mode 에 따른 disclaimer banner 생성.

    relaxed_diagnostic 모드에서 산출은 운용 최종안이 아닌 diagnostic baseline.
    """
    cfg = tdf_config or {}
    mode = str(cfg.get("operating_mode") or "production").strip().lower()
    if mode == "relaxed_diagnostic":
        return {
            "mode": "relaxed_diagnostic",
            "banner": "RELAXED DIAGNOSTIC RUN — NOT a production portfolio",
            "disclaimer": [
                "본 산출은 **운용 최종안이 아니라** 제약 해제 시 optimizer / TAA 쏠림을 확인하기 위한 **diagnostic run** 입니다.",
                "glide path 80/20 은 **reference / starting SAA** 로만 보존되며 hard constraint 가 아닙니다.",
                "equity 100% / fixed_income 0% 등 극단 비중은 **fail 이 아닌 monitoring flag** 로만 노출됩니다.",
                "향후 운용안 확정 시 **자산군별 band 또는 bucket range 를 재도입** 할 수 있습니다 (Decision Register D-11/D-12 deferred).",
                "현 단계 hard constraint = `long-only` + `sum-to-100%` + 데이터 무결성 (BRFUT004 mapping / DB / NaN / convergence).",
            ],
        }
    return {"mode": mode, "banner": None, "disclaimer": []}


def _build_future_telemetry_notes() -> list[str]:
    """현재 미노출 telemetry — telemetry enhancement candidate (정식 Decision 항목 아님).

    Phase E-6.2 (2026-05-11) 적용: SAA / μ / σ / ρ / Σ / regime history 6건은
    saa_diagnostics.* 및 regime.history 로 직접 노출. 본 목록은 잔여 항목만 유지.
    """
    return [
        "TAA tilt by asset 미노출 — taa_diagnostics.tilt_by_asset = None. "
        "regime → final 완전 분해 불가. "
        "candidate id: **D-16 (telemetry enhancement, 정식 아님)**.",
        "제외 상품 개별 ID/사유 목록 미노출 — universe_diagnostics.excluded_sample 비어있음. "
        "운용역이 제외 룰 검증하려면 sample 확장 필요. "
        "candidate id: **D-17 (telemetry enhancement, 정식 아님)**.",
        "selection score 미노출 — product_allocation.score = None. "
        "selection/tool.py 에서 보존 필요. "
        "candidate id: **D-18 (telemetry enhancement, 정식 아님)**.",
    ]


# ── Markdown render ────────────────────────────────────────────────────


def render_markdown(packet: dict[str, Any]) -> str:
    rs = packet["review_summary"]
    ps = packet["projection_summary"]
    aa = packet["asset_allocation"]
    pa = packet["product_allocation"]
    items = packet["policy_review_items"]
    # Phase D.2 — 신규 키 (없으면 graceful)
    omb = packet.get("operating_mode_banner") or {}
    es = packet.get("executive_summary") or _build_executive_summary(rs)
    rc = packet.get("regime_context") or {}
    bs = packet.get("bucket_summary") or {}
    xs = packet.get("excluded_summary") or {}
    wr = packet.get("warning_register") or []
    chk = packet.get("review_checklist") or _build_review_checklist()
    ftn = packet.get("future_telemetry_notes") or _build_future_telemetry_notes()

    lines: list[str] = []
    ap = lines.append

    ap(f"# TDF 2060 Portfolio Review — {rs['portfolio_type'].upper()}")
    ap("")
    ap(f"as_of: **{rs.get('as_of_date') or '-'}** · source: **{rs['source_type']}**")
    ap("")

    # Phase D — Operating mode banner (relaxed_diagnostic / production)
    if omb.get("banner"):
        ap(f"> ⚠️ **{omb['banner']}**")
        for line in omb.get("disclaimer", []):
            ap(f"> - {line}")
        ap("")

    # 0. Executive Summary (Phase D.2 — Section A)
    ap("## 0. Executive Summary")
    ap("")
    ap("| 항목 | 값 |")
    ap("|---|---|")
    ap(f"| portfolio_type | **{(es.get('portfolio_type') or '-').upper()}** |")
    ap(f"| as_of_date | {es.get('as_of_date') or '-'} |")
    ap(f"| constraints_passed | **{es.get('constraints_passed')}** |")
    ap(f"| quality_status | **{es.get('quality_status')}** |")
    ap(f"| asset_weight_sum | {float(es.get('asset_weight_sum', 0.0)):.6f} |")
    ap(f"| product_weight_sum | {float(es.get('product_weight_sum', 0.0)):.6f} |")
    ap(f"| equity_weight | {float(es.get('equity_weight', 0.0)):.4%} |")
    ap(f"| fixed_income_weight | {float(es.get('fixed_income_weight', 0.0)):.4%} |")
    ap(f"| warning_count_total | {int(es.get('warning_count_total', 0))} |")
    ap("")
    ap("**운용역 판단란**: ")
    ap("- [ ] Approve  ·  - [ ] Revise  ·  - [ ] Hold")
    ap("")

    # 1. 요약
    ap("## 1. 요약")
    ap("")
    ap("| 항목 | 값 |")
    ap("|---|---|")
    ap(f"| constraints_passed | **{rs['constraints_passed']}** |")
    ap(f"| quality_status | **{rs['quality_status']}** |")
    ap(f"| asset_weight_sum | {rs['asset_weight_sum']:.6f} |")
    ap(f"| product_weight_sum | {rs['product_weight_sum']:.6f} |")
    ap(f"| equity bucket | {rs['equity_bucket_weight']:.4%} |")
    ap(f"| fixed_income bucket | {rs['fixed_income_bucket_weight']:.4%} |")
    ap(f"| fallback_used | {rs['fallback_used']} |")
    ap(f"| projection_used | {rs['projection_used']} |")
    ap(f"| max_abs_projection_drift | {rs['max_abs_projection_drift']:.4%} |")
    ap(f"| max_abs_asset_weight_drift | {rs['max_abs_asset_weight_drift']:.4%} |")
    ap(f"| proxy_used | {rs['proxy_used']} |")
    ap(f"| db_warnings_count | {rs['db_warnings_count']} |")
    ap(f"| validation_issues_count | {rs['validation_issues_count']} |")
    ap(f"| validation_warnings_count | {rs['validation_warnings_count']} |")
    ap("")

    # 2. 최종 자산배분 (+ Phase D.2 regime 컨텍스트, SAA→TAA→Final 변화표)
    ap("## 2. 최종 자산배분")
    ap("")
    # Regime 컨텍스트 한 줄 (Section B 일부)
    if rc:
        regime_id = rc.get("regime_id")
        regime_label = rc.get("regime_label") or "-"
        region = rc.get("region") or "-"
        plc = rc.get("placement")
        vel = rc.get("velocity")
        plc_s = f"{float(plc):.4f}" if plc is not None else "-"
        vel_s = f"{float(vel):.4f}" if vel is not None else "-"
        ap(
            f"**Regime 컨텍스트**: region=**{region}** · "
            f"Placement={plc_s} · Velocity={vel_s} · "
            f"regime=**{regime_id}** ({regime_label})"
        )
        ap("")
    ap("| asset_key | bucket | SAA | TAA target (before proj) | **final** | drift | bound [lb, ub] | status |")
    ap("|---|---|---:|---:|---:|---:|---|---|")
    for r in aa:
        bnd = ""
        if r["final_bound_lower"] is not None:
            bnd = f"[{r['final_bound_lower']:.4%}, {r['final_bound_upper']:.4%}]"
        saa_w = r.get("saa_weight")
        saa_s = f"{float(saa_w):>+8.4%}" if saa_w is not None else "—"
        ap(
            f"| {r['asset_key']} | {r['bucket'] or '-'} | "
            f"{saa_s} | "
            f"{r['taa_target_weight_before_projection']:>+8.4%} | "
            f"**{r['final_asset_weight']:>+8.4%}** | "
            f"{r['projection_drift']:>+8.4%} | {bnd or '-'} | {r['bound_status']} |"
        )
    ap("")
    ap(
        "> **부분 attribution 안내**: SAA 컬럼과 TAA tilt(자산별 정량 분해)는 일부가 "
        "telemetry 미노출로 `—` 표시됨. 본 packet 의 SAA → TAA → Final attribution 은 "
        "**partial view** 이며, 완전한 attribution 은 향후 telemetry 개선 후에 가능. "
        "이 개선은 정식 Decision Register 항목이 아니라 enhancement candidate (§10 참고). "
        "TAA target 컬럼은 SAA + regime tilt 적용 후 값(=projection 직전)을 의미."
    )
    ap("")

    # 2.1 자산배분 요약 (Section C — Phase D relaxed: sanity monitoring only)
    if bs:
        ap("### 2.1 자산배분 요약 — sanity monitoring only (NOT enforced)")
        ap("")
        eq_rng = bs.get("equity_sanity_range") or bs.get("equity_target_range") or {}
        fi_rng = bs.get("fixed_income_sanity_range") or bs.get("fixed_income_target_range") or {}
        eq_in = "✓" if bs.get("equity_in_sanity_range", bs.get("equity_in_range")) else "⚠"
        fi_in = "✓" if bs.get("fixed_income_in_sanity_range", bs.get("fixed_income_in_range")) else "⚠"
        ap("| 항목 | 값 | sanity range | 범위 내 |")
        ap("|---|---:|---|:---:|")
        ap(
            f"| 주식 합계 | {float(bs.get('equity_total', 0.0)):.4%} | "
            f"[{float(eq_rng.get('min', 0.60)):.2%}, {float(eq_rng.get('max', 0.95)):.2%}] | {eq_in} |"
        )
        ap(
            f"| 채권 합계 | {float(bs.get('fixed_income_total', 0.0)):.4%} | "
            f"[{float(fi_rng.get('min', 0.05)):.2%}, {float(fi_rng.get('max', 0.40)):.2%}] | {fi_in} |"
        )
        ap(
            f"| HY 비중 (us_high_yield) | {float(bs.get('us_high_yield_weight', 0.0)):.4%} | "
            f"— | — |"
        )
        ap("")
        if bs.get("monitoring_only_note"):
            ap(f"> {bs['monitoring_only_note']}")
        ap(f"> HY 분류: {bs.get('us_high_yield_classification', '-')}")
        ap("")

    # 3. Projection 전후
    ap("## 3. Projection 전후")
    ap("")
    if ps["projection_used"]:
        ap(f"projection_used = **True** · max_abs_drift = {ps['max_abs_projection_drift']:.4%}")
        ap("")
        bb = ps["bucket_before"]
        ba = ps["bucket_after"]
        ap("| bucket | before | after |")
        ap("|---|---:|---:|")
        for b in sorted(set(list(bb.keys()) + list(ba.keys()))):
            ap(f"| {b} | {bb.get(b, 0):.4%} | {ba.get(b, 0):.4%} |")
        ap("")
        neg = ps["negative_assets_before_projection"]
        if neg:
            ap("**음수 자산 (projection 전)**: " + ", ".join(
                f"{k}={v:+.4%}" for k, v in neg.items()
            ))
            ap("")
        if ps["largest_projection_drifts_top5"]:
            ap("Top-5 projection drift:")
            ap("")
            ap("| asset_key | before | after | drift |")
            ap("|---|---:|---:|---:|")
            for d in ps["largest_projection_drifts_top5"]:
                ap(
                    f"| {d['asset_key']} | {d['before']:>+8.4%} | "
                    f"{d['after']:>+8.4%} | {d['drift']:>+8.4%} |"
                )
            ap("")
    else:
        ap("projection_used = False (target 이 이미 feasible)")
        ap("")

    # 3.1 Drift source breakdown (Phase D — D-02 telemetry 보강)
    diag_for_drift = packet.get("_diagnostics_drift") or {}
    proj_clip = diag_for_drift.get("projection_clipping_summary") or {}
    proj_src = diag_for_drift.get("projection_drift_source_by_asset") or {}
    qual_clip = diag_for_drift.get("quality_drift_clipping_summary") or {}
    qual_src = diag_for_drift.get("quality_drift_source_by_asset") or {}

    if proj_clip or qual_clip:
        ap("### 3.1 Drift source breakdown")
        ap("")
        if omb.get("mode") == "relaxed_diagnostic":
            ap("> ⚠️ relaxed_diagnostic mode 에서 drift 는 fail 이 아니라 telemetry. 본 섹션은 분석용.")
            ap("")

        # ── (a) Projection drift (taa/projection.py 단계) ─────────────
        ap("**(a) Projection 단계 drift** (long-only 강제 등 — `max_abs_projection_drift`)")
        ap("")
        ap(f"- projection_used: **{ps.get('projection_used')}**")
        ap(f"- max_abs_projection_drift: {ps.get('max_abs_projection_drift', 0.0):.4%}")
        if proj_clip:
            primary = proj_clip.get("drift_source_primary", "none")
            ap(f"- primary drift source: **{primary}**")
            cas = proj_clip.get("clipped_assets") or []
            if cas:
                long_only = proj_clip.get("long_only_clipping_by_asset") or {}
                clip_strs = ", ".join(
                    f"{a}={float(long_only.get(a, 0.0)):+.4%}" for a in cas
                )
                ap(f"- clipped assets (long-only): **{len(cas)}** — {clip_strs}")
                ap(f"- total long-only clipping magnitude: {float(proj_clip.get('total_long_only_clipping_magnitude', 0.0)):.4%}")
                ap(f"- max long-only clipping: {float(proj_clip.get('max_long_only_clipping', 0.0)):.4%}")
            redist = proj_clip.get("redistribution_by_recipient") or {}
            if redist:
                top_redist = sorted(redist.items(), key=lambda kv: -abs(float(kv[1])))[:5]
                redist_strs = ", ".join(
                    f"{a}={float(v):+.4%}" for a, v in top_redist
                )
                ap(f"- redistribution recipients (top-5): {redist_strs}")
                ap(f"- redistribution total: {float(proj_clip.get('redistribution_total', 0.0)):.4%}")
            unexp = proj_clip.get("relaxed_mode_unexpected_sources") or []
            if unexp:
                ap(f"- ⚠️ unexpected source(s) in relaxed mode: {unexp}")
            counts = proj_clip.get("drift_source_counts") or {}
            if counts:
                cnt_strs = ", ".join(f"{k}={v}" for k, v in counts.items())
                ap(f"- drift_source counts: {cnt_strs}")
        ap("")

        # ── (b) Quality drift (selection + fallback 단계) ─────────────
        ap("**(b) Selection + fallback 단계 drift** (product cap clipping 등 — `max_abs_asset_weight_drift`)")
        ap("")
        ap(f"- max_abs_asset_weight_drift: {rs.get('max_abs_asset_weight_drift', 0.0):.4%}")
        if qual_clip:
            primary = qual_clip.get("drift_source_primary", "none")
            ap(f"- primary drift source: **{primary}**")
            outflow = qual_clip.get("outflow_assets") or []
            if outflow:
                of_amt = qual_clip.get("outflow_by_asset") or {}
                of_strs = ", ".join(
                    f"{a}={float(of_amt.get(a, 0.0)):+.4%}" for a in outflow[:5]
                )
                ap(f"- outflow assets (target → final 감소): {of_strs}")
                ap(f"- total outflow: {float(qual_clip.get('total_outflow_magnitude', 0.0)):.4%}")
            inflow = qual_clip.get("inflow_assets") or []
            if inflow:
                if_amt = qual_clip.get("inflow_by_asset") or {}
                if_strs = ", ".join(
                    f"{a}={float(if_amt.get(a, 0.0)):+.4%}" for a in inflow[:5]
                )
                ap(f"- inflow assets (target → final 증가): {if_strs}")
                ap(f"- total inflow: {float(qual_clip.get('total_inflow_magnitude', 0.0)):.4%}")
            counts = qual_clip.get("drift_source_counts") or {}
            if counts:
                cnt_strs = ", ".join(f"{k}={v}" for k, v in counts.items())
                ap(f"- drift_source counts: {cnt_strs}")
        ap("")

        # 자산별 drift_source 표 (top by magnitude)
        if proj_src or qual_src:
            ap("**자산별 drift_source (top 10 by |drift|)**")
            ap("")
            ap("| asset_key | proj drift | proj source | qual drift | qual source |")
            ap("|---|---:|---|---:|---|")
            # collect drifts
            all_assets = set(proj_src.keys()) | set(qual_src.keys())
            proj_drifts = (diag_for_drift.get("projection_asset_drift_from_target") or {})
            qual_drifts = (diag_for_drift.get("quality_asset_weight_drift") or {})
            ranked = sorted(
                all_assets,
                key=lambda a: -max(
                    abs(float(proj_drifts.get(a, 0.0))),
                    abs(float(qual_drifts.get(a, 0.0))),
                ),
            )[:10]
            for a in ranked:
                pd_v = float(proj_drifts.get(a, 0.0))
                qd_v = float(qual_drifts.get(a, 0.0))
                ps_v = proj_src.get(a, "—")
                qs_v = qual_src.get(a, "—")
                ap(f"| {a} | {pd_v:>+8.4%} | {ps_v} | {qd_v:>+8.4%} | {qs_v} |")
            ap("")

    # 4. 최종 상품 (+ Phase D.2 score 컬럼, 4.1 제외 상품 요약)
    ap(f"## 4. 최종 상품 ({len(pa)}개)")
    ap("")
    if pa:
        ap("| asset_key | bucket | product | manager | role | score | weight | flags |")
        ap("|---|---|---|---|---|---:|---:|---|")
        for p in pa:
            flags = ", ".join(p["warning_flags"]) if p["warning_flags"] else "-"
            score_s = "—" if p.get("score") is None else f"{float(p['score']):.3f}"
            ap(
                f"| {p['asset_key']} | {p['bucket'] or '-'} | "
                f"{p['product_name']} | {p['manager']} | {p['role']} | "
                f"{score_s} | "
                f"{p['final_weight']:>+8.4%} | {flags} |"
            )
        ap("")
        ap("> score 컬럼 `—` = selection score 미보존 (selection/tool.py 정책 — §10 future_telemetry_notes 참고).")
        ap("")
    else:
        ap("(상품 없음)")
        ap("")

    # 4.1 제외 상품 요약 (Phase D.2 — Section E, 한계 명시)
    if xs:
        ap("### 4.1 제외 / 분류 요약")
        ap("")
        ap("| 항목 | 값 |")
        ap("|---|---:|")
        ap(f"| total_products (raw) | {int(xs.get('raw_count', 0))} |")
        ap(f"| passed_filter_count | {int(xs.get('passed_filter_count', 0))} |")
        ap(f"| classified_count | {int(xs.get('classified_count', 0))} |")
        ap(f"| excluded_count | **{int(xs.get('excluded_count', 0))}** |")
        ap(f"| grade_filtered_count | {int(xs.get('grade_filtered_count', 0))} |")
        ap(f"| grade_penalized_count | {int(xs.get('grade_penalized_count', 0))} |")
        ap("")
        by_class = xs.get("classified_by_asset_class") or {}
        if by_class:
            ap("**자산군별 후보 수**:")
            ap("")
            ap("| asset_key | n |")
            ap("|---|---:|")
            for k in sorted(by_class.keys()):
                ap(f"| {k} | {int(by_class[k])} |")
            ap("")
        zc = xs.get("asset_classes_with_zero_count") or []
        if zc:
            ap(f"**후보 0건 자산군**: {', '.join(zc)}")
            ap("")
        if not xs.get("individual_excluded_list_available"):
            ap(f"> {xs.get('note', '')}")
            ap("")

    # 5. Validation
    ap("## 5. Validation")
    ap("")
    val_issues_n = rs["validation_issues_count"]
    val_warn_n = rs["validation_warnings_count"]
    ap(f"- issues: **{val_issues_n}**")
    ap(f"- warnings: **{val_warn_n}**")
    ap("")

    # 5.1 Constraint & Warning Register (Phase D.2 — Section F, D-ID 연결)
    if wr:
        ap("### 5.1 Constraint & Warning Register")
        ap("")
        ap("| warning_id | severity | source | message | linked_decision | required |")
        ap("|---|---|---|---|---|:---:|")
        for w in wr:
            mt = str(w.get("message", "")).replace("|", "/").replace("\n", " ")
            if len(mt) > 110:
                mt = mt[:107] + "..."
            ld = w.get("linked_decision_id") or "-"
            req = "✓" if w.get("decision_required") else "—"
            ap(
                f"| {w.get('warning_id')} | {w.get('severity')} | "
                f"{w.get('source')} | {mt} | {ld} | {req} |"
            )
        ap("")
        ap("> linked_decision 은 substring heuristic. 운용역 실제 매핑은 검토 후 확정.")
        ap("")

    # 6. Quality
    ap("## 6. Quality")
    ap("")
    ap(f"- quality_status: **{rs['quality_status']}**")
    ap(f"- max_abs_asset_weight_drift: {rs['max_abs_asset_weight_drift']:.4%}")
    # Phase D — enforcement mode + drift telemetry
    diag_q = (packet.get("_quality_diag") or {})
    enforcement = diag_q.get("enforcement_mode")
    if enforcement:
        if enforcement == "telemetry_only":
            ap(f"- enforcement: **telemetry_only** — drift 초과는 quality_status 에 영향 없음 (telemetry 만 보존)")
        else:
            thr = diag_q.get("thresholds") or {}
            ap(
                f"- enforcement: **{enforcement}** "
                f"(threshold asset={float(thr.get('asset_drift', 0.0)):.4%}, "
                f"bucket={float(thr.get('bucket_drift', 0.0)):.4%})"
            )
        notes = diag_q.get("drift_telemetry_notes") or []
        if notes:
            ap("- drift telemetry notes:")
            for n in notes:
                ap(f"  - {n}")
        ap("- drift_source breakdown: 다음 PR 예정 (`docs/phase_d_drift_telemetry_proposal.md` §2 참조).")
    ap("")

    # 7. DB source
    ap("## 7. DB source")
    ap("")
    ap(f"- source_type: {rs['source_type']}")
    ap(f"- proxy_used: {rs['proxy_used']}")
    ap(f"- db_warnings_count: {rs['db_warnings_count']}")
    ap("")

    # 8. 운용역 확인 필요 사항
    ap("## 8. 운용역 확인 필요 사항")
    ap("")
    if items:
        for it in items:
            ap(f"- {it}")
    else:
        ap("(자동 감지된 검토 항목 없음)")
    ap("")

    # 9. 운용역 Review Checklist (Phase D.2 — Section G)
    ap("## 9. 운용역 Review Checklist")
    ap("")
    for c in chk:
        if c.get("options"):
            opts = "  ·  ".join(f"[ ] {o}" for o in c["options"])
            ap(f"- **{c['label']}**: {opts}")
        else:
            box = "[x]" if c.get("checked") else "[ ]"
            ap(f"- {box} {c['label']}")
    ap("")

    # 10. 향후 telemetry 개선 후보 (Phase D.2)
    ap("## 10. 향후 telemetry 개선 후보")
    ap("")
    ap(
        "**중요**: 아래 D-15~D-18 은 **정식 Decision Register 항목이 아니라 "
        "telemetry enhancement candidate** 입니다. 정식 등록 시 "
        "`investment_decision_register.md` 의 total count 와 status distribution 을 "
        "별도 갱신해야 합니다."
    )
    ap("")
    for n in ftn:
        ap(f"- {n}")
    ap("")

    return "\n".join(lines)
