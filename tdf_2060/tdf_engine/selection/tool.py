"""ProductSelectionTool — facade.

Phase B.5: 미배분 비중을 자산군별로 추적하는 diagnostics 강화.
unfilled_by_asset_class 의 cause 분류:
  - no_candidates_in_universe : universe 통과 product 0
  - filtered_out_by_scoring   : passes_filter (grade/aum) 후 0
  - product_cap_clipping       : single_product_max_weight cap 으로 잘림
  - satellite_short            : n_satellite_target 미달 → 비중 미배분
  - manager_cap_scaling        : manager 비례 scale 로 weight 축소
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, TYPE_CHECKING

from tdf_engine.domain.enums import ProductType
from tdf_engine.domain.models import (
    ProductInfo,
    ProductSelectionResult,
    UniverseResult,
)
from tdf_engine.selection.scoring import (
    GRADE_HARD_FILTER,
    GRADE_SCORE_PENALTY,
    ProductScorer,
    ScoringConfig,
)
from tdf_engine.selection.selector import (
    CoreSatelliteSelector,
    SelectionConstraints,
)

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

logger = logging.getLogger(__name__)


class ProductSelectionTool:
    def __init__(
        self,
        universe_result: UniverseResult,
        universe_config: dict[str, Any],
        product_type: ProductType,
    ):
        self.universe_result = universe_result
        self.universe_config = universe_config
        self.product_type = product_type

        type_block = universe_config.get(product_type.value, {}) or {}
        pc = type_block.get("product_constraints", {}) or {}
        self.selection_constraints = SelectionConstraints(
            single_product_max_weight=float(pc.get("single_product_max_weight", 0.20)),
            single_manager_max_weight=float(pc.get("single_manager_max_weight", 0.60)),
        )
        # Phase C-pre: quant_grade_policy 우선, 없으면 target_quant_grade_min 호환.
        qgp = type_block.get("quant_grade_policy") or {}
        grade_mode = str(qgp.get("mode", GRADE_HARD_FILTER))
        min_grade = qgp.get("min_grade", pc.get("target_quant_grade_min"))
        penalty = float(qgp.get("penalty_per_grade", 0.10))

        self.scoring_config = ScoringConfig(
            min_quant_grade=min_grade,
            min_aum=pc.get("min_aum"),
            grade_policy_mode=grade_mode,
            grade_penalty_per_grade=penalty,
        )
        self.scorer = ProductScorer(self.scoring_config)
        self.selector = CoreSatelliteSelector(self.selection_constraints)

    def _group_by_asset_universe(self) -> dict[str, list[ProductInfo]]:
        """필터 전 자산군별 universe count (분모)."""
        groups: dict[str, list[ProductInfo]] = defaultdict(list)
        for p in self.universe_result.products:
            if p.mvo_asset_class is None:
                continue
            groups[p.mvo_asset_class].append(p)
        return groups

    def _enforce_manager_cap(
        self, picks: list[tuple[ProductInfo, float, str]]
    ) -> tuple[list[tuple[ProductInfo, float, str]], list[str]]:
        cap = self.selection_constraints.single_manager_max_weight
        agg: dict[str, float] = defaultdict(float)
        for p, w, _ in picks:
            agg[p.manager] += w

        warnings: list[str] = []
        scale: dict[str, float] = {}
        for mgr, total in agg.items():
            if total > cap and total > 0:
                scale[mgr] = cap / total
                warnings.append(
                    f"manager '{mgr}' total {total:.4f} > cap {cap:.4f} → scale {scale[mgr]:.4f}"
                )

        if not scale:
            return picks, warnings

        adjusted = []
        for p, w, role in picks:
            s = scale.get(p.manager, 1.0)
            adjusted.append((p, w * s, role))
        return adjusted, warnings

    def run(
        self,
        asset_weights: "pd.Series",
    ) -> ProductSelectionResult:
        import pandas as pd

        groups_universe = self._group_by_asset_universe()

        rows: list[dict] = []
        warnings: list[str] = []
        unfilled_by_asset_class: dict[str, dict[str, Any]] = {}
        grade_filtered_count = 0
        grade_penalized_count = 0
        # Phase E-11A — scored products telemetry. selection logic 미변경, dump 만 추가.
        scored_products_telemetry: list[dict[str, Any]] = []
        excluded_telemetry: dict[str, list[dict[str, Any]]] = {}

        for asset_key, target_w in asset_weights.items():
            target_w = float(target_w)
            if target_w <= 0:
                continue

            in_universe = groups_universe.get(asset_key, [])
            after_filter = [p for p in in_universe if self.scorer.passes_filter(p)]

            # E-11A — excluded products telemetry (filter 통과 못한 product 사유 기록)
            excluded_for_asset: list[dict[str, Any]] = []
            for p in in_universe:
                if p in after_filter:
                    continue
                reasons: list[str] = []
                if self.scorer.is_grade_below_min(p):
                    reasons.append(
                        f"grade_below_min(grade={p.quant_grade}, "
                        f"min={self.scoring_config.min_quant_grade})"
                    )
                if self.scoring_config.min_aum is not None:
                    if p.aum is None or float(p.aum) < float(self.scoring_config.min_aum):
                        reasons.append(
                            f"aum_below_min(aum={p.aum}, "
                            f"min={self.scoring_config.min_aum})"
                        )
                excluded_for_asset.append({
                    "product_id": p.product_id,
                    "product_name": p.name,
                    "manager": p.manager,
                    "reason": ";".join(reasons) if reasons else "filter_unspecified",
                })
            if excluded_for_asset:
                excluded_telemetry[asset_key] = excluded_for_asset

            # quant_grade 카운트
            if self.scoring_config.grade_policy_mode == GRADE_HARD_FILTER:
                grade_filtered_count += sum(
                    1 for p in in_universe if self.scorer.is_grade_below_min(p)
                )
            elif self.scoring_config.grade_policy_mode == GRADE_SCORE_PENALTY:
                grade_penalized_count += sum(
                    1 for p in after_filter if self.scorer.is_grade_below_min(p)
                )

            entry: dict[str, Any] = {
                "target": target_w,
                "n_universe": len(in_universe),
                "n_after_filter": len(after_filter),
                "n_picks": 0,
                "allocated": 0.0,
                "unfilled": target_w,
                "cause": None,
            }

            if not in_universe:
                entry["cause"] = "no_candidates_in_universe"
                unfilled_by_asset_class[asset_key] = entry
                continue
            if not after_filter:
                entry["cause"] = "filtered_out_by_scoring"
                unfilled_by_asset_class[asset_key] = entry
                continue

            scored = sorted(
                ((p, self.scorer.score(p)) for p in after_filter),
                key=lambda kv: kv[1],
                reverse=True,
            )

            picks = self.selector.select(scored, asset_key, target_w)
            picks_ids: set[str] = {prod.product_id for prod, _, _ in picks}

            # E-11A — scored products telemetry (rank + score + factor_values).
            # selection logic 미변경 — picks 결과를 기반으로 selected 플래그만 표기.
            for rank_idx, (prod, score_val) in enumerate(scored):
                scored_products_telemetry.append({
                    "product_id": prod.product_id,
                    "fund_code": prod.fund_code,
                    "product_name": prod.name,
                    "manager": prod.manager,
                    "asset_key": asset_key,
                    "product_type": prod.product_type.value,
                    "score": float(score_val),
                    "rank_within_asset": rank_idx + 1,
                    "selected": prod.product_id in picks_ids,
                    "quant_grade": prod.quant_grade,
                    "factor_values": {
                        "quant_score": (
                            float(prod.quant_score)
                            if prod.quant_score is not None else None
                        ),
                        "sharpe_1y": (
                            float(prod.sharpe_1y)
                            if prod.sharpe_1y is not None else None
                        ),
                        "return_3y": (
                            float(prod.return_3y)
                            if prod.return_3y is not None else None
                        ),
                        "aum": (
                            float(prod.aum)
                            if prod.aum is not None else None
                        ),
                        "missing_fields": [
                            f for f, v in (
                                ("quant_score", prod.quant_score),
                                ("sharpe_1y", prod.sharpe_1y),
                                ("return_3y", prod.return_3y),
                                ("aum", prod.aum),
                            ) if v is None
                        ],
                    },
                })

            if not picks:
                entry["cause"] = "selector_returned_empty"
                unfilled_by_asset_class[asset_key] = entry
                continue

            allocated_in_class = sum(w for _, w, _ in picks)
            entry["n_picks"] = len(picks)
            entry["allocated"] = allocated_in_class
            entry["unfilled"] = target_w - allocated_in_class

            if entry["unfilled"] > 1e-9:
                # cause 분류
                # 1) satellite_short: n_picks < n_core + n_satellite_target 이면 후보 부족
                expected_picks = (
                    self.selector.constraints.n_core_target
                    + self.selector.constraints.n_satellite_target
                )
                cap = self.selection_constraints.single_product_max_weight
                core_target_per = (target_w * self.selector.constraints.core_ratio[1]) / max(
                    self.selector.constraints.n_core_target, 1
                )
                if len(picks) < expected_picks:
                    entry["cause"] = "satellite_short"
                elif core_target_per > cap + 1e-12:
                    entry["cause"] = "product_cap_clipping"
                else:
                    entry["cause"] = "selector_short"
                unfilled_by_asset_class[asset_key] = entry

            for prod, w, role in picks:
                rows.append(
                    {
                        "asset_key": asset_key,
                        "product_id": prod.product_id,
                        "fund_code": prod.fund_code,
                        "name": prod.name,
                        "manager": prod.manager,
                        "kis_asset_class": prod.kis_asset_class,
                        "sub_type": prod.sub_type,
                        "weight": w,
                        "role": role,
                    }
                )

        df = pd.DataFrame(rows, columns=[
            "asset_key", "product_id", "fund_code", "name", "manager",
            "kis_asset_class", "sub_type", "weight", "role",
        ])

        # manager cap 검증
        if not df.empty:
            id_to_product = {p.product_id: p for p in self.universe_result.products}
            picks_tuples = []
            for r in rows:
                p = id_to_product.get(r["product_id"])
                if p is None:
                    continue
                picks_tuples.append((p, r["weight"], r["role"]))

            adjusted, w_msgs = self._enforce_manager_cap(picks_tuples)
            warnings.extend(w_msgs)
            if w_msgs:
                w_by_id = {p.product_id: w for p, w, _ in adjusted}
                df["weight"] = df["product_id"].map(w_by_id).fillna(df["weight"])

                # manager_cap_scaling 으로 자산군별 unfilled 재계산
                allocated = df.groupby("asset_key")["weight"].sum()
                for ak, target in asset_weights.items():
                    a = float(allocated.get(ak, 0.0))
                    diff = float(target) - a
                    if diff > 1e-9:
                        if ak in unfilled_by_asset_class:
                            unfilled_by_asset_class[ak]["unfilled"] = diff
                            unfilled_by_asset_class[ak]["allocated"] = a
                            if unfilled_by_asset_class[ak]["cause"] is None:
                                unfilled_by_asset_class[ak]["cause"] = "manager_cap_scaling"
                        else:
                            unfilled_by_asset_class[ak] = {
                                "target": float(target),
                                "n_universe": len(groups_universe.get(ak, [])),
                                "n_after_filter": -1,
                                "n_picks": int((df["asset_key"] == ak).sum()),
                                "allocated": a,
                                "unfilled": diff,
                                "cause": "manager_cap_scaling",
                            }

        diagnostics = {
            "product_type": self.product_type.value,
            "n_picks": int(len(df)),
            "warnings": warnings,
            "selected_weight_sum": float(df["weight"].sum()) if not df.empty else 0.0,
            "unfilled_by_asset_class": unfilled_by_asset_class,
            "unfilled_total": float(
                sum(e["unfilled"] for e in unfilled_by_asset_class.values())
            ),
            "quant_grade_policy": {
                "mode": self.scoring_config.grade_policy_mode,
                "min_grade": self.scoring_config.min_quant_grade,
                "penalty_per_grade": self.scoring_config.grade_penalty_per_grade,
            },
            "grade_filtered_count": grade_filtered_count,
            "grade_penalized_count": grade_penalized_count,
            # Phase E-11A — score / rank / factor telemetry (read-only, allocation 불변)
            "score_method": self.scoring_config.grade_policy_mode,
            "score_factors": [
                {"factor": "quant_score",
                 "weight": float(self.scoring_config.weights.quant_score),
                 "description": "정량평가 점수",
                 "available": True},
                {"factor": "sharpe_1y",
                 "weight": float(self.scoring_config.weights.sharpe_1y),
                 "description": "1년 수정 샤프지수",
                 "available": True},
                {"factor": "return_3y",
                 "weight": float(self.scoring_config.weights.return_3y),
                 "description": "3년 수익률",
                 "available": True},
                {"factor": "aum_log",
                 "weight": float(self.scoring_config.weights.aum_log),
                 "description": "log1p(AUM)",
                 "available": True},
                {"factor": "cost_penalty",
                 "weight": float(self.scoring_config.weights.cost_penalty),
                 "description": "(미사용)",
                 "available": False},
            ],
            "scored_products": scored_products_telemetry,
            "excluded_by_asset": excluded_telemetry,
        }

        return ProductSelectionResult(selected=df, diagnostics=diagnostics)
