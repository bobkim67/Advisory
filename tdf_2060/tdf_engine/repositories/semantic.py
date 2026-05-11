"""Phase C.1 — db_sources.yaml 의 semantic_type / return_transform 정책 검증.

Allowed 조합:
  semantic_type ∈ {total_return_index, price_index, nav}   →  pct_change (default)
  semantic_type == return_series                            →  already_return (default)
  semantic_type ∈ {yield, spread}                           →  diff | duration_proxy | not_allowed
                                                                (return_transform 명시 필수)
  semantic_type == macro_indicator                          →  not_allowed (MVO 입력 불가)

duration_proxy 는 Phase C.1 미구현. 만나면 NotImplementedError.
not_allowed 는 즉시 ValueError.
명시 누락 (semantic_type 만 있고 return_transform 미설정) 인 yield/spread 는 ValueError.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# 그대로 가격/지수 시계열로 다룰 수 있는 의미
LEVEL_TYPES = {"total_return_index", "price_index", "nav"}
# 이미 수익률
RETURN_TYPES = {"return_series"}
# raw 변환 필요 (yield/spread/macro)
RAW_TYPES = {"yield", "spread", "macro_indicator"}

# return_transform 가능한 값
TRANSFORMS = {
    "pct_change",
    "diff",
    "already_return",
    "duration_proxy",
    "not_allowed",
}


def resolve_transform(
    asset_key: str,
    semantic_type: str | None,
    return_transform: str | None,
) -> str:
    """semantic_type + return_transform 조합 검증 후 effective transform 반환.

    Returns: "pct_change" | "diff" | "already_return"
    Raises: ValueError | NotImplementedError
    """
    if semantic_type is None:
        # backward compat: 정의 안 했으면 level 가정 + pct_change
        return "pct_change"

    if semantic_type not in LEVEL_TYPES | RETURN_TYPES | RAW_TYPES:
        raise ValueError(
            f"{asset_key}: 알 수 없는 semantic_type='{semantic_type}'. "
            f"허용: {sorted(LEVEL_TYPES | RETURN_TYPES | RAW_TYPES)}"
        )

    if return_transform is not None and return_transform not in TRANSFORMS:
        raise ValueError(
            f"{asset_key}: 알 수 없는 return_transform='{return_transform}'. "
            f"허용: {sorted(TRANSFORMS)}"
        )

    if return_transform == "not_allowed":
        raise ValueError(
            f"{asset_key}: return_transform=not_allowed — 이 dataset 은 MVO 입력에 사용 불가. "
            f"운영자가 다른 dataset 매핑으로 교체 필요 "
            f"(예: yield → TR index 또는 ETF NAV)."
        )

    if return_transform == "duration_proxy":
        raise NotImplementedError(
            f"{asset_key}: return_transform=duration_proxy 는 Phase C.1 미구현. "
            f"운영자가 TR index 매핑으로 교체하거나 Phase C+ 까지 대기."
        )

    if semantic_type in LEVEL_TYPES:
        # default = pct_change
        if return_transform is None:
            return "pct_change"
        if return_transform != "pct_change":
            raise ValueError(
                f"{asset_key}: semantic_type='{semantic_type}' 인데 "
                f"return_transform='{return_transform}'. "
                f"level 시계열은 pct_change 만 허용."
            )
        return "pct_change"

    if semantic_type in RETURN_TYPES:
        if return_transform is None:
            return "already_return"
        if return_transform != "already_return":
            raise ValueError(
                f"{asset_key}: semantic_type=return_series 는 already_return 만 허용. "
                f"got '{return_transform}'."
            )
        return "already_return"

    # RAW_TYPES — return_transform 명시 필수
    if return_transform is None:
        raise ValueError(
            f"{asset_key}: semantic_type='{semantic_type}' 는 return_transform 명시 필수. "
            f"허용: diff | duration_proxy | not_allowed (조용한 pct_change 금지)."
        )
    if semantic_type == "macro_indicator":
        # macro indicator 는 사실상 수익률 산출 불가 → not_allowed 권장
        raise ValueError(
            f"{asset_key}: semantic_type=macro_indicator 는 MVO 입력 불가 — "
            f"return_transform=not_allowed 로 명시하고 운영자가 매핑 교체."
        )
    return return_transform
