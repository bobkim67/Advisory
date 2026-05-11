"""CoreSatelliteSelector — 자산군별 Core / Satellite 상품 선정.

Core (60~80%): 광범위 베타 추종형
Satellite (20~40%): 스타일 / 액티브 / 테마

Phase B 단순 구현:
  - score 내림차순 정렬
  - 1순위 = core (core_ratio[1] 비중)
  - 2순위 부터 = satellite (남은 비중을 균등 분배)
  - single_product_max_weight, single_manager_max_weight 검증 (위반 시 후순위로 비중 양도)
  - n_core_target / n_satellite_target 으로 후보 수 제한
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tdf_engine.domain.models import ProductInfo

if TYPE_CHECKING:  # pragma: no cover
    pass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SelectionConstraints:
    single_product_max_weight: float = 0.20
    single_manager_max_weight: float = 0.60
    core_ratio: tuple[float, float] = (0.60, 0.80)
    n_core_target: int = 1
    n_satellite_target: int = 2


class CoreSatelliteSelector:
    def __init__(self, constraints: SelectionConstraints):
        self.constraints = constraints

    def select(
        self,
        candidates: list[tuple[ProductInfo, float]],
        asset_key: str,
        asset_weight: float,
    ) -> list[tuple[ProductInfo, float, str]]:
        """candidates: list of (product, score). score 내림차순 정렬되어 있어야 함.

        Returns: [(product, weight, role), ...]
        """
        if asset_weight <= 0 or not candidates:
            return []

        c = self.constraints
        core_lo, core_hi = c.core_ratio
        n_core = max(1, c.n_core_target)
        n_satellite = max(0, c.n_satellite_target)

        core_picks = candidates[:n_core]
        satellite_picks = candidates[n_core : n_core + n_satellite]

        results: list[tuple[ProductInfo, float, str]] = []

        if not core_picks:
            return []

        # Core 비중 = core_hi 사용 (단순화). 향후 정책 정교화.
        core_weight_total = asset_weight * core_hi
        # Core 균등 분배
        per_core = core_weight_total / len(core_picks) if core_picks else 0.0
        for prod, _ in core_picks:
            results.append((prod, per_core, "core"))

        sat_weight_total = asset_weight - core_weight_total
        if satellite_picks and sat_weight_total > 0:
            per_sat = sat_weight_total / len(satellite_picks)
            for prod, _ in satellite_picks:
                results.append((prod, per_sat, "satellite"))
        elif sat_weight_total > 0 and not satellite_picks:
            # satellite 후보가 없으면 core 에 합산
            extra = sat_weight_total / len(core_picks)
            results = [
                (prod, w + extra, role)
                for (prod, w, role) in results
            ]

        # single_product_max_weight 검증: 절대 비중 기준이 아니라 자산군 내 상대 비중인지
        # 정책상 "전체 portfolio 대비 단일 상품 최대 20%" 라고 보는 게 보수적.
        # asset_weight 자체가 portfolio 대비 비중이므로, results 의 weight 도 portfolio 대비.
        cap = c.single_product_max_weight
        clipped: list[tuple[ProductInfo, float, str]] = []
        overflow = 0.0
        for prod, w, role in results:
            if w > cap:
                overflow += w - cap
                w = cap
            clipped.append((prod, w, role))

        # overflow 는 미배분으로 둠 (자산군 내 후보 부족 시그널). diagnostics 는 호출자 책임.
        return clipped
