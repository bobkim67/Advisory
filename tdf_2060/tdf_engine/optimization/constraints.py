"""ConstraintSet — 자산별 bounds + bucket 합 + region lower bound 통합 보관.

이번 단계는 skeleton + dataclass 정의만.
실제 scipy 제약 변환은 MVOOptimizer 에서 수행.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConstraintSet:
    """MVO 제약 묶음.

    weight_sum_must_equal:    합 (보통 1.0)
    bounds:                   asset_key → (lb, ub)
    bucket_sum:               bucket_value → (lb, ub) — equity 합, fixed_income 합
    region_lower_bounds:      asset_key → lb (optimization_vba 의 EAFE/EM 하한 대응)
    err_enabled:              ERR 제약 활성 여부 (Phase A: 항상 False — 사용자 결정 #5)
    """

    weight_sum_must_equal: float = 1.0
    bounds: dict[str, tuple[float, float]] = field(default_factory=dict)
    bucket_sum: dict[str, tuple[float, float]] = field(default_factory=dict)
    region_lower_bounds: dict[str, float] = field(default_factory=dict)
    err_enabled: bool = False
    err_threshold: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def asset_keys(self) -> list[str]:
        return list(self.bounds.keys())
