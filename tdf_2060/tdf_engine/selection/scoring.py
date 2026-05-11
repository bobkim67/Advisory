"""ProductScorer — 단일 product 에 점수 부여.

Phase C-pre:
  quant_grade_policy.mode ∈ {hard_filter, score_penalty, disabled}
    - hard_filter   : passes_filter 가 min_grade 미만 제외
    - score_penalty : 제외하지 않고 score 에서 (등급차이 × penalty_per_grade) 감점
    - disabled      : 등급 미반영
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from tdf_engine.domain.models import ProductInfo

if TYPE_CHECKING:  # pragma: no cover
    pass


GRADE_HARD_FILTER = "hard_filter"
GRADE_SCORE_PENALTY = "score_penalty"
GRADE_DISABLED = "disabled"


@dataclass(frozen=True)
class ScoringWeights:
    quant_score: float = 0.4
    sharpe_1y: float = 0.3
    return_3y: float = 0.2
    aum_log: float = 0.1
    cost_penalty: float = 0.0


@dataclass
class ScoringConfig:
    weights: ScoringWeights = field(default_factory=ScoringWeights)
    min_quant_grade: str | None = None
    min_aum: float | None = None
    min_history_years: float | None = None
    grade_policy_mode: str = GRADE_HARD_FILTER  # hard_filter / score_penalty / disabled
    grade_penalty_per_grade: float = 0.10


_GRADE_RANK = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1, "E": 0}


def _grade_rank(grade: str | None) -> int:
    if not grade:
        return -1
    g = grade.strip().upper()[:1]
    return _GRADE_RANK.get(g, -1)


class ProductScorer:
    def __init__(self, config: ScoringConfig):
        self.config = config

    def passes_filter(self, product: ProductInfo) -> bool:
        # quant_grade
        if self.config.min_quant_grade is not None and self.config.grade_policy_mode == GRADE_HARD_FILTER:
            if _grade_rank(product.quant_grade) < _grade_rank(self.config.min_quant_grade):
                return False
        # min_aum
        if self.config.min_aum is not None:
            if product.aum is None or product.aum < self.config.min_aum:
                return False
        return True

    def is_grade_below_min(self, product: ProductInfo) -> bool:
        """min_grade 미만 여부 (penalty 적용 판단용)."""
        if self.config.min_quant_grade is None:
            return False
        return _grade_rank(product.quant_grade) < _grade_rank(self.config.min_quant_grade)

    def score(self, product: ProductInfo) -> float:
        w = self.config.weights
        qs = float(product.quant_score) if product.quant_score is not None else 0.0
        sh = float(product.sharpe_1y) if product.sharpe_1y is not None else 0.0
        r3 = float(product.return_3y) if product.return_3y is not None else 0.0
        aum = float(product.aum) if (product.aum is not None and product.aum > 0) else 0.0
        aum_log = math.log1p(aum)

        base = (
            w.quant_score * qs
            + w.sharpe_1y * sh
            + w.return_3y * r3
            + w.aum_log * aum_log
        )

        # score_penalty: 등급 차이만큼 base 에 비례 감점
        if (
            self.config.grade_policy_mode == GRADE_SCORE_PENALTY
            and self.config.min_quant_grade is not None
        ):
            min_rank = _grade_rank(self.config.min_quant_grade)
            cur_rank = _grade_rank(product.quant_grade)
            if cur_rank >= 0 and cur_rank < min_rank:
                shortfall = min_rank - cur_rank
                penalty_factor = 1.0 - shortfall * float(self.config.grade_penalty_per_grade)
                # score 가 음수가 되지 않도록 floor
                base = base * max(penalty_factor, 0.0)

        return base
