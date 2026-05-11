"""PortfolioValidator — 최종 portfolio 의 정합성 검증.

Phase B.5 강화:
  - asset_weight_sum, product_weight_sum 모두 ≈ 1.0 검증.
  - 음수 weight 검출.
  - fallback 사용 시 warnings 에 노출 (constraints_passed 자체는 유지 가능).
  - tdf_config.final_asset_bounds (옵션) 위반 시 warning (hard fail 아님).

bounds 개념 분리:
  - optimization_bounds (= tdf_config.weight_bounds): MVO 입력 제약.
  - taa_tilt_bounds (= taa_config.constraints): TAA 조정폭 제약.
  - final_asset_bounds (= tdf_config.final_asset_bounds, 옵션):
        TAA 이후 최종 자산군 비중 허용 범위. Phase B.5 는 warning 만.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd
    from tdf_engine.domain.models import PortfolioResult

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    weight_sum_ok: bool = True
    bucket_bounds_ok: bool = True
    asset_bounds_ok: bool = True
    non_negative_ok: bool = True
    product_sum_ok: bool = True
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            self.weight_sum_ok
            and self.bucket_bounds_ok
            and self.asset_bounds_ok
            and self.non_negative_ok
            and self.product_sum_ok
        )


class PortfolioValidator:
    def __init__(self, atol: float = 1e-6):
        self.atol = atol

    def validate_weights(self, weights, expected_sum: float = 1.0) -> ValidationReport:
        rep = ValidationReport()
        s = float(weights.sum())
        if abs(s - expected_sum) > self.atol:
            rep.weight_sum_ok = False
            rep.issues.append(f"weight sum {s} != {expected_sum} (atol={self.atol})")
        return rep

    def validate(
        self,
        portfolio: "PortfolioResult",
        tdf_config: dict,
        universe_config: dict | None = None,
    ) -> ValidationReport:
        rep = ValidationReport()
        w = portfolio.asset_weights

        # 1) asset_weight sum ≈ 1.0
        s_asset = float(w.sum())
        if abs(s_asset - 1.0) > 1e-4:  # TAA cash-neutral 후 약간의 numerical 잔차 허용
            rep.weight_sum_ok = False
            rep.issues.append(f"asset_weight sum {s_asset:.6f} != 1.0")

        # 2) product_weight sum ≈ 1.0 (Phase B.5)
        if not portfolio.product_weights.empty:
            s_prod = float(portfolio.product_weights["weight"].sum())
            if abs(s_prod - 1.0) > 1e-4:
                rep.product_sum_ok = False
                rep.issues.append(f"product_weight sum {s_prod:.6f} != 1.0")

            # 3) non-negative
            neg = portfolio.product_weights[portfolio.product_weights["weight"] < -1e-12]
            if not neg.empty:
                rep.non_negative_ok = False
                rep.issues.append(f"{len(neg)} product weights are negative")
        else:
            # product 가 비어있는 경우 closure 실패
            rep.product_sum_ok = False
            rep.issues.append("product_weights is empty")

        # asset 도 non-negative 검사
        neg_asset = w[w < -1e-12]
        if not neg_asset.empty:
            rep.non_negative_ok = False
            rep.issues.append(f"{len(neg_asset)} asset weights are negative")

        # 4) bucket bounds (taa_bounds) — taa_diagnostics.bucket_sums 활용
        taa_bounds = tdf_config.get("taa_bounds") or {}
        taa_diag = portfolio.diagnostics.get("taa_diagnostics") or {}
        bucket_sums = taa_diag.get("bucket_sums")
        if taa_bounds and bucket_sums:
            eq_min = float(taa_bounds.get("equity_min", 0.0))
            eq_max = float(taa_bounds.get("equity_max", 1.0))
            fi_min = float(taa_bounds.get("fixed_income_min", 0.0))
            fi_max = float(taa_bounds.get("fixed_income_max", 1.0))
            eq = float(bucket_sums.get("equity", 0.0))
            fi = float(bucket_sums.get("fixed_income", 0.0))
            if not (eq_min - 1e-6 <= eq <= eq_max + 1e-6):
                rep.bucket_bounds_ok = False
                rep.issues.append(
                    f"equity bucket {eq:.4f} outside [{eq_min:.4f}, {eq_max:.4f}]"
                )
            if not (fi_min - 1e-6 <= fi <= fi_max + 1e-6):
                rep.bucket_bounds_ok = False
                rep.issues.append(
                    f"fixed_income bucket {fi:.4f} outside [{fi_min:.4f}, {fi_max:.4f}]"
                )

        # 5) final_asset_bounds (옵션, warning 만)
        final_bounds = tdf_config.get("final_asset_bounds") or {}
        for k, v in w.items():
            b = final_bounds.get(k)
            if not b:
                continue
            lb, ub = float(b.get("min", 0.0)), float(b.get("max", 1.0))
            if v < lb - 1e-6 or v > ub + 1e-6:
                rep.warnings.append(
                    f"final_asset_bound: {k}={v:.4f} outside [{lb:.4f}, {ub:.4f}]"
                )

        # 6) Phase C.3: TAA projection 결과 점검
        taa_diag = portfolio.diagnostics.get("taa_diagnostics") or {}
        feas = taa_diag.get("taa_feasibility") or {}
        if feas:
            if feas.get("projection_used"):
                drift = float(feas.get("max_abs_projection_drift", 0.0))
                rep.warnings.append(
                    f"taa_projection_used: max_abs_projection_drift={drift:.4%}"
                )
                neg = feas.get("negative_weight_assets_before_projection") or {}
                if neg:
                    parts = [f"{k}={v:+.4%}" for k, v in neg.items()]
                    rep.warnings.append(
                        f"negative weights before projection: {', '.join(parts)}"
                    )
                buckets_after = feas.get("bucket_weights_after_projection") or {}
                if buckets_after:
                    parts = [f"{b}={s:.4%}" for b, s in buckets_after.items()]
                    rep.warnings.append(f"bucket after projection: {', '.join(parts)}")
            if feas.get("projection_used") and not feas.get("projection_success", True):
                rep.bucket_bounds_ok = False
                rep.issues.append(
                    f"taa_projection_failed: {feas.get('projection_message')}"
                )

        # 7) fallback / quality (B.5+ 구체화)
        fb = portfolio.diagnostics.get("fallback") or {}
        quality = portfolio.diagnostics.get("quality") or {}

        if fb.get("fallback_used"):
            # source asset 별 흡수 비중 합산하여 메시지 구체화
            absorbers = fb.get("fallback_absorbers") or []
            absorbed_by_source: dict[str, float] = {}
            target_bucket_by_source: dict[str, set[str]] = {}
            for a in absorbers:
                src = a.get("source_asset_key")
                if src is None:
                    continue
                absorbed_by_source[src] = absorbed_by_source.get(src, 0.0) + float(
                    a.get("absorbed_weight", 0.0)
                )
                target_bucket_by_source.setdefault(src, set()).add(
                    a.get("absorber_asset_key", "?")
                )
            for ak, cause in (fb.get("fallback_reasons") or {}).items():
                amt = absorbed_by_source.get(ak, 0.0)
                tgt = sorted(target_bucket_by_source.get(ak, set()))
                rep.warnings.append(
                    f"fallback_used: {ak} {amt:.4%} redistributed → {tgt} (cause={cause})"
                )

            no_cand = [
                k for k, e in (
                    portfolio.diagnostics.get("selection_diagnostics", {})
                    .get("unfilled_by_asset_class", {})
                ).items()
                if e.get("cause") == "no_candidates_in_universe"
            ]
            if no_cand:
                rep.warnings.append(f"no_candidates: {no_cand}")

            cash_w = float(fb.get("cash_placeholder_weight", 0.0))
            if cash_w > 1e-9:
                rep.warnings.append(
                    f"cash_placeholder_weight: {cash_w:.4%} — Phase C DB/universe 보강 후 해소 필요"
                )

        if quality:
            rep.warnings.append(
                f"max_abs_asset_weight_drift: {float(quality.get('max_abs_asset_weight_drift', 0.0)):.4%}"
            )
            rep.warnings.append(
                f"max_abs_bucket_drift: {float(quality.get('max_abs_bucket_drift', 0.0)):.4%}"
            )
            rep.warnings.append(f"quality_status: {quality.get('quality_status')}")

        return rep
