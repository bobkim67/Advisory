"""UniverseFilter — KIS MP 카테고리 + 키워드 필터.

순서 (중요):
  1) KIS MP 카테고리 화이트리스트
  2) 소유형 (sub_type) 제외 패턴
  3) 합성 처리 (synthetic_policy 가 keyword 검사보다 먼저)
     - whitelist 모드: 합성 + 화이트리스트 키워드 = pass
       (이 경우 keyword 검사 시 "합성" 키워드는 무시)
     - exclude_all 모드: 즉시 제외
  4) 일반 키워드 제외 패턴
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FilterConfig:
    """단일 ProductType 의 필터 정책 (yaml 의 common+etf 또는 common+fund 결합)."""

    include_kis_mp_categories: tuple[str, ...] = ()
    exclude_keywords: tuple[str, ...] = ()
    exclude_sub_types: tuple[str, ...] = ()
    synthetic_mode: str = "whitelist"   # "whitelist" | "exclude_all" | "off"
    synthetic_whitelist: tuple[str, ...] = ()


class UniverseFilter:
    SYNTHETIC_KEYWORD = "합성"

    def __init__(self, config: FilterConfig):
        self.config = config

    def is_excluded(self, row: dict) -> tuple[bool, str | None]:
        """제외 사유 반환. (excluded?, reason)."""

        # 1) KIS MP 카테고리
        kis = str(row.get("대유형(KIS MP)", "") or "")
        if (
            self.config.include_kis_mp_categories
            and kis not in self.config.include_kis_mp_categories
        ):
            return True, f"KIS MP category '{kis}' not in include list"

        # 2) 소유형
        sub_type = str(row.get("소유형", "") or "")
        for s in self.config.exclude_sub_types:
            if s and s in sub_type:
                return True, f"sub_type matches exclude pattern '{s}'"

        # 3) 합성 처리 (keyword 검사보다 먼저)
        name = str(row.get("펀드명(Short)", "") or "")
        synthetic_allowed = False
        if self.SYNTHETIC_KEYWORD in name:
            mode = self.config.synthetic_mode
            if mode == "exclude_all":
                return True, "synthetic excluded by policy=exclude_all"
            elif mode == "whitelist":
                if any(wk in name for wk in self.config.synthetic_whitelist):
                    synthetic_allowed = True
                else:
                    return True, "synthetic not in whitelist"
            elif mode == "off":
                synthetic_allowed = True

        # 4) 일반 키워드 제외 (단, synthetic_allowed 면 "합성" 키워드는 무시)
        for kw in self.config.exclude_keywords:
            if kw == self.SYNTHETIC_KEYWORD and synthetic_allowed:
                continue
            if kw and kw in name:
                return True, f"name matches exclude keyword '{kw}'"

        return False, None
