"""라이브 DB CMA — 사용자 지정 [start, end] window 로 SCIP 에서 월말 수익률을
계산해 μ/Σ (expected returns / covariance) 를 산출한다. **review-only**.

frozen 경로(`db_market_data.py`, baseline portfolio JSON)는 건드리지 않는다.
`DBMarketDataRepository` 의 월간수익률 방법론(일별 레벨 → 월말 resample("ME") →
return_transform → ×annualization / ×√annualization)만 그대로 재사용하고,
lookback_years 대신 명시적 [start, end] 로 필터한다.

정책 정합:
- E[R], σ  : asset-specific — 자산별로 [start, end] ∩ (해당 자산 가용구간) 에서 계산.
- 상관행렬 : common intersection — 자산 간 공통 월(dropna how="any") 로 계산.
  (db_sources.yaml::asset_rt_vol.intersection_policy=asset_specific,
   corr_matrix.intersection_policy=common 과 동일.)
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any

from tdf_engine.repositories.db_market_data import DBMarketDataRepository
from tdf_engine.repositories.semantic import resolve_transform


def _as_ts(d: "date | str"):
    import pandas as pd

    return pd.Timestamp(d)


def build_window_cma(
    asset_keys: list[str],
    db_sources_cfg: dict[str, Any],
    engine: Any,
    *,
    start: "date | str",
    end: "date | str",
    annualization: int = 12,
    short_history_tolerance_days: int = 40,
) -> dict[str, Any]:
    """[start, end] window 로 라이브 CMA dict 산출.

    반환 구조는 frozen baseline 의 saa_diagnostics.cma 와 동일 키를 따른다
    (asset_key 로 keyed):
        expected_returns, volatilities, correlation_matrix, covariance_matrix.
    + window 진단(per_asset / warnings).
    """
    import numpy as np
    import pandas as pd

    start_ts = _as_ts(start)
    end_ts = _as_ts(end)
    if end_ts < start_ts:
        raise ValueError(f"end({end_ts.date()}) < start({start_ts.date()})")

    # as_of_date=end → upper bound. lookback 은 우리가 직접 [start,end] 필터하므로
    # repo 내부 lookback 컷은 끈다(_query_levels 는 lookback_years 가 falsy 면 미적용).
    repo = DBMarketDataRepository(
        engine, db_sources_cfg, as_of_date=end_ts.date(), permissive=True
    )
    entries = {e["asset_key"]: e for e in (db_sources_cfg.get("assets") or [])}

    ann = int(annualization)
    sqrt_ann = math.sqrt(ann)

    returns_by_key: dict[str, "pd.Series"] = {}
    expected_returns: dict[str, float] = {}
    volatilities: dict[str, float] = {}
    per_asset: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []

    for ak in asset_keys:
        entry = entries.get(ak)
        if entry is None:
            per_asset[ak] = {"obs": 0, "missing": True, "reason": "db_sources 매핑 없음"}
            warnings.append(f"{ak}: db_sources.yaml 매핑 없음 — window CMA 제외")
            continue

        dataset_id, _used_proxy = repo._resolve_dataset_id(entry)
        if dataset_id is None:
            per_asset[ak] = {"obs": 0, "missing": True, "reason": "dataset_id 없음"}
            warnings.append(f"{ak}: dataset_id 없음 — window CMA 제외")
            continue

        try:
            transform = resolve_transform(
                ak, entry.get("semantic_type"), entry.get("return_transform")
            )
        except (ValueError, NotImplementedError) as e:
            per_asset[ak] = {"obs": 0, "missing": True, "reason": f"semantic: {e}"}
            warnings.append(f"{ak}: semantic 정책 위반 — {e}")
            continue

        ret = repo._monthly_returns(
            asset_key=ak,
            dataset_id=dataset_id,
            value_dataseries=int(entry.get("value_dataseries", 6)),
            fallback_dataseries=entry.get("fallback_dataseries"),
            blob_key=entry.get("blob_key") or entry.get("currency"),
            lookback_years=0,  # falsy → _query_levels 하한 컷 미적용 (전체 history)
            transform=transform,
        )
        if ret is None or ret.empty:
            per_asset[ak] = {"obs": 0, "missing": True, "reason": "시계열 비어있음"}
            warnings.append(f"{ak}: dataset_id={dataset_id} 시계열 비어있음")
            continue

        # 요청 window 로 필터 (월말 인덱스).
        ret = ret.loc[(ret.index >= start_ts) & (ret.index <= end_ts)]
        obs = int(ret.shape[0])
        if obs < 2:
            per_asset[ak] = {"obs": obs, "missing": True, "reason": "window 내 관측 < 2"}
            warnings.append(f"{ak}: window 내 월수익률 {obs}건 — 제외")
            continue

        eff_start = ret.index.min()
        eff_end = ret.index.max()
        short_history = bool(
            (eff_start - start_ts).days > short_history_tolerance_days
        )

        mu = float(ret.mean()) * ann
        sigma = float(ret.std(ddof=1)) * sqrt_ann

        returns_by_key[ak] = ret
        expected_returns[ak] = mu
        volatilities[ak] = sigma
        per_asset[ak] = {
            "obs": obs,
            "missing": False,
            "effective_start": str(eff_start.date()),
            "effective_end": str(eff_end.date()),
            "short_history": short_history,
            "annualized_return": mu,
            "annualized_vol": sigma,
        }
        if short_history:
            warnings.append(
                f"{ak}: 가용 시작 {eff_start.date()} > 요청 시작 {start_ts.date()} "
                f"(short history, obs={obs})"
            )

    present = list(returns_by_key.keys())
    if len(present) < 2:
        raise ValueError(
            "window CMA: 유효 자산 < 2 — window 가 너무 짧거나 데이터 부재."
        )

    # ── 상관행렬: common intersection (dropna how=any) ──
    joined = pd.concat(returns_by_key, axis=1)
    common = joined.dropna(how="any")
    n_common = int(common.shape[0])
    if n_common < 2:
        raise ValueError("window CMA: 공통 관측월 < 2 — 상관행렬 산출 불가.")
    corr_df = common.corr()
    if corr_df.isna().any().any():
        corr_df = corr_df.fillna(0.0)
        np.fill_diagonal(corr_df.values, 1.0)
        warnings.append("상관행렬 NaN 보정 (0 으로 채움).")

    # ── covariance = D · C · D (D = diag(sigma)) ──
    correlation_matrix: dict[str, dict[str, float]] = {}
    covariance_matrix: dict[str, dict[str, float]] = {}
    for ai in present:
        correlation_matrix[ai] = {}
        covariance_matrix[ai] = {}
        for aj in present:
            c = float(corr_df.loc[ai, aj])
            correlation_matrix[ai][aj] = c
            covariance_matrix[ai][aj] = c * volatilities[ai] * volatilities[aj]

    return {
        "asset_keys": present,
        "expected_returns": expected_returns,
        "volatilities": volatilities,
        "correlation_matrix": correlation_matrix,
        "covariance_matrix": covariance_matrix,
        "window": {
            "requested_start": str(start_ts.date()),
            "requested_end": str(end_ts.date()),
            "annualization": ann,
            "n_common_obs": n_common,
        },
        "per_asset": per_asset,
        "warnings": warnings,
    }
