"""Fallback allocator — minimal weight closure (Phase B.5).

미배분 비중을 다음 우선순위로 처리:
  (1) 동일 자산군 내 selected product 에 pro-rata 재배분
       (single_product_max_weight cap 재적용)
  (2) 동일 bucket 내 다른 자산군의 selected product 에 pro-rata 분배
  (3) 그래도 남은 비중은 cash placeholder row 로 추가

원칙:
  - 미배분 비중을 silent drop 하지 않는다.
  - product_weight_sum 은 1.0 으로 닫는다.
  - fallback 사용 시 fallback_used=True, fallback_reasons[asset_key]=cause 기록.
  - 추가 (B.5+): fallback_absorbers 에 source→absorber 매핑을 product 단위로 기록.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

logger = logging.getLogger(__name__)

CASH_PRODUCT_ID = "__CASH__"
CASH_FUND_CODE = None
CASH_NAME = "Cash placeholder (Phase B.5 fallback)"
CASH_MANAGER = "-"
CASH_KIS = "현금성"
CASH_SUB = "cash_placeholder"
CASH_ASSET_KEY = "cash"


def _bucket_of_asset(asset_key: str, bucket_by_asset: dict[str, str]) -> str | None:
    return bucket_by_asset.get(asset_key)


def apply_fallback(
    product_weights: "pd.DataFrame",
    asset_weights: "pd.Series",
    selection_diagnostics: dict[str, Any],
    bucket_by_asset: dict[str, str],
    single_product_max_weight: float = 1.0,
) -> tuple["pd.DataFrame", dict[str, Any]]:
    """미배분 비중을 fallback 정책으로 처리.

    반환: (조정된 product_weights, fallback_diagnostics)

    fallback_diagnostics 키:
      - fallback_used: bool
      - fallback_reasons: {source_asset_key: cause}
      - reallocations: list of {asset_key, mode, amount, target}
        (B.5 호환 유지)
      - fallback_absorbers: list of
        {source_asset_key, absorber_asset_key, absorbed_weight, product_id, product_name, mode}
        (B.5+ 신규 — product 단위 추적)
      - cash_placeholder_weight: float
      - product_weight_sum_before: float
      - product_weight_sum_after: float
    """
    import pandas as pd

    df = product_weights.copy()

    fb_diag: dict[str, Any] = {
        "fallback_used": False,
        "fallback_reasons": {},
        "reallocations": [],
        "fallback_absorbers": [],
        "cash_placeholder_weight": 0.0,
        "product_weight_sum_before": float(df["weight"].sum()) if not df.empty else 0.0,
    }

    unfilled = selection_diagnostics.get("unfilled_by_asset_class") or {}
    if not unfilled:
        fb_diag["product_weight_sum_after"] = fb_diag["product_weight_sum_before"]
        return df, fb_diag

    for source_asset_key, entry in unfilled.items():
        amount = float(entry.get("unfilled", 0.0))
        if amount <= 1e-12:
            continue
        cause = str(entry.get("cause", "unknown"))
        fb_diag["fallback_used"] = True
        fb_diag["fallback_reasons"][source_asset_key] = cause

        # (1) 동일 자산군 pro-rata 재배분
        same_class_mask = df["asset_key"] == source_asset_key
        same_class_idx = df.index[same_class_mask].tolist()
        if same_class_idx:
            placed, leftover, additions = _redistribute(
                df, same_class_idx, amount, single_product_max_weight
            )
            if placed > 1e-12:
                fb_diag["reallocations"].append(
                    {
                        "asset_key": source_asset_key,
                        "mode": "same_asset_class_pro_rata",
                        "amount": placed,
                        "target": source_asset_key,
                    }
                )
                _record_absorbers(
                    fb_diag["fallback_absorbers"],
                    df,
                    source_asset_key,
                    additions,
                    "same_asset_class_pro_rata",
                )
            amount = leftover

        if amount <= 1e-12:
            continue

        # (2) 동일 bucket sibling pro-rata
        bucket = _bucket_of_asset(source_asset_key, bucket_by_asset)
        if bucket is not None:
            sibling_keys = [
                k for k, b in bucket_by_asset.items()
                if b == bucket and k != source_asset_key
            ]
            sibling_mask = df["asset_key"].isin(sibling_keys)
            sibling_idx = df.index[sibling_mask].tolist()
            if sibling_idx:
                placed, leftover, additions = _redistribute(
                    df, sibling_idx, amount, single_product_max_weight
                )
                if placed > 1e-12:
                    fb_diag["reallocations"].append(
                        {
                            "asset_key": source_asset_key,
                            "mode": "same_bucket_sibling_pro_rata",
                            "amount": placed,
                            "target": bucket,
                        }
                    )
                    _record_absorbers(
                        fb_diag["fallback_absorbers"],
                        df,
                        source_asset_key,
                        additions,
                        "same_bucket_sibling_pro_rata",
                    )
                amount = leftover

        if amount <= 1e-12:
            continue

        # (3) cash placeholder
        df, cash_idx = _add_or_top_up_cash(df, amount)
        fb_diag["cash_placeholder_weight"] += amount
        fb_diag["reallocations"].append(
            {
                "asset_key": source_asset_key,
                "mode": "cash_placeholder",
                "amount": amount,
                "target": CASH_ASSET_KEY,
            }
        )
        fb_diag["fallback_absorbers"].append(
            {
                "source_asset_key": source_asset_key,
                "absorber_asset_key": CASH_ASSET_KEY,
                "absorbed_weight": amount,
                "product_id": CASH_PRODUCT_ID,
                "product_name": CASH_NAME,
                "mode": "cash_placeholder",
            }
        )

    fb_diag["product_weight_sum_after"] = float(df["weight"].sum())
    return df, fb_diag


def _record_absorbers(
    absorbers: list,
    df: "pd.DataFrame",
    source_asset_key: str,
    additions: list[tuple[int, float]],
    mode: str,
) -> None:
    for idx, amt in additions:
        if amt <= 1e-12:
            continue
        absorbers.append(
            {
                "source_asset_key": source_asset_key,
                "absorber_asset_key": str(df.at[idx, "asset_key"]),
                "absorbed_weight": float(amt),
                "product_id": str(df.at[idx, "product_id"]),
                "product_name": str(df.at[idx, "name"]),
                "mode": mode,
            }
        )


def _redistribute(
    df: "pd.DataFrame",
    target_idx: list,
    amount: float,
    cap: float,
) -> tuple[float, float, list[tuple[int, float]]]:
    """target_idx 행들에 amount 를 균등 분배. cap 초과분은 leftover.

    Returns: (placed_total, leftover, additions=[(idx, amount), ...])
    """
    if amount <= 0 or not target_idx:
        return 0.0, amount, []

    placed = 0.0
    remaining = amount
    additions: dict[int, float] = {i: 0.0 for i in target_idx}

    for _ in range(5):
        if remaining <= 1e-12:
            break
        room_idx = [
            i for i in target_idx
            if float(df.at[i, "weight"]) < cap - 1e-12
        ]
        if not room_idx:
            break
        share = remaining / len(room_idx)
        actually_placed = 0.0
        for i in room_idx:
            cur = float(df.at[i, "weight"])
            room = cap - cur
            add = min(share, room)
            df.at[i, "weight"] = cur + add
            additions[i] += add
            actually_placed += add
        placed += actually_placed
        remaining -= actually_placed
        if actually_placed <= 1e-12:
            break

    return placed, remaining, [(i, a) for i, a in additions.items() if a > 1e-12]


def _add_or_top_up_cash(df: "pd.DataFrame", amount: float) -> tuple["pd.DataFrame", int]:
    import pandas as pd

    cash_mask = df["product_id"] == CASH_PRODUCT_ID
    if cash_mask.any():
        idx = int(df.index[cash_mask][0])
        df.at[idx, "weight"] = float(df.at[idx, "weight"]) + amount
        return df, idx

    new_row = {
        "asset_key": CASH_ASSET_KEY,
        "product_id": CASH_PRODUCT_ID,
        "fund_code": CASH_FUND_CODE,
        "name": CASH_NAME,
        "manager": CASH_MANAGER,
        "kis_asset_class": CASH_KIS,
        "sub_type": CASH_SUB,
        "weight": amount,
        "role": "cash",
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return df, int(df.index[-1])
