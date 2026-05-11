"""SCIP back_datapoint.data blob 파서 (표준).

blob 형식 종류:
  {"USD": 608.66, "KRW": 868066.70}                          → currency dict
  {"totRtnIndex": "8344.74", "cleanPriceIndex": "...", ...}  → KIS bond index dict (혼합 타입)
  2451.187912                                                 → 단일 숫자
  "13.06"                                                     → 문자열 숫자
"""

from __future__ import annotations

import json
from typing import Any


def parse_data_blob(blob: Any, currency: str | None = None, key: str | None = None) -> Any:
    """blob → float (또는 dict).

    인자:
      currency : 기존 호환. dict blob 일 때 이 키의 값만 float 로 반환.
      key      : 일반화된 이름 (currency 의 alias). 둘 중 하나만 지정.

    동작:
      - blob None → None
      - dict + key/currency 지정 → 해당 키 float
      - dict + 미지정 → 숫자 변환 가능한 키만 float 로 묶은 dict
      - 단일 숫자/문자열 → float
    """
    if blob is None:
        return None

    if isinstance(blob, (bytes, bytearray)):
        s = blob.decode("utf-8", errors="strict")
    else:
        s = str(blob)
    s = s.strip()
    if not s:
        return None

    target_key = key or currency

    if s.startswith("{"):
        obj = json.loads(s)
        if isinstance(obj, dict):
            if target_key is not None:
                v = obj.get(target_key)
                if v is None:
                    return None
                return float(str(v).replace(",", ""))
            # 미지정: 숫자 변환 가능한 항목만 추려서 dict 반환
            out: dict[str, float] = {}
            for k, v in obj.items():
                try:
                    out[k] = float(str(v).replace(",", ""))
                except (TypeError, ValueError):
                    continue
            return out
        return float(obj)

    return float(s.replace(",", "").strip('"'))
