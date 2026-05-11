"""CapitalMarketAssumptionBuilder — Asset_rt_vol + Corr_mat → CMA.

매칭 키:
    AssetClassInfo.source_names.optimization
        → Asset_rt_vol 의 'Ticker' 컬럼 또는 'Name' 컬럼 (둘 중 매칭되는 것)
    Corr_mat 의 인덱스/컬럼은 한글 'Name' → Asset_rt_vol Ticker→Name 매핑으로 reindex.

ust30 데이터 부재 처리 (사용자 결정 #10 = b 강한 error):
    required=True 인 자산이 source 데이터에 없으면 ValueError.
    silent fallback / 자동 proxy 사용 금지.
    proxy_enabled=True + proxy_ticker 명시된 경우만 proxy 매칭 허용.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from tdf_engine.domain.models import AssetClassInfo, CapitalMarketAssumption
from tdf_engine.optimization.covariance import CovarianceEstimator

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd
    from tdf_engine.repositories.interfaces import MarketDataRepository

logger = logging.getLogger(__name__)


def _strip_pct(value) -> float:
    """'12.4%' → 0.124. 빈/NaN → ValueError."""
    import math

    if value is None:
        raise ValueError("None percentage")
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            raise ValueError("NaN percentage")
        return float(value) / 100.0
    s = str(value).strip().replace(",", "")
    if s.endswith("%"):
        s = s[:-1]
    return float(s) / 100.0


class CapitalMarketAssumptionBuilder:
    """Asset_rt_vol + Corr_mat → CapitalMarketAssumption."""

    def __init__(
        self,
        repo: "MarketDataRepository",
        assets: list[AssetClassInfo],
    ) -> None:
        self.repo = repo
        self.assets = assets

    def _resolve_lookup_label(self, asset: AssetClassInfo) -> str | None:
        """매칭에 사용할 라벨. proxy_enabled 면 proxy_ticker, 아니면 source_names.optimization."""
        if asset.proxy_enabled and asset.proxy_ticker:
            return asset.proxy_ticker
        return asset.source_names.optimization

    def build(self) -> CapitalMarketAssumption:
        import pandas as pd

        raw = self.repo.load_asset_rt_vol()
        # Asset Class 컬럼 ffill (sparse merge cell)
        if "Asset Class" in raw.columns:
            raw = raw.copy()
            raw["Asset Class"] = raw["Asset Class"].ffill()

        # Name NaN row drop
        raw = raw.dropna(subset=["Name"]).copy()
        # 공백 정리
        for col in ("Ticker", "Name"):
            if col in raw.columns:
                raw[col] = raw[col].astype(str).str.strip()

        # Ticker / Name → row index dict
        by_ticker = {t: i for i, t in enumerate(raw["Ticker"].tolist()) if t and t != "nan"}
        by_name = {n: i for i, n in enumerate(raw["Name"].tolist()) if n and n != "nan"}

        sigma_dict: dict[str, float] = {}
        er_dict: dict[str, float] = {}
        ticker_by_key: dict[str, str] = {}
        name_by_key: dict[str, str] = {}
        missing: list[str] = []
        unmapped_required: list[str] = []

        for asset in self.assets:
            label = self._resolve_lookup_label(asset)
            row_idx = None
            if label is not None:
                if label in by_ticker:
                    row_idx = by_ticker[label]
                elif label in by_name:
                    row_idx = by_name[label]

            if row_idx is None:
                if asset.required:
                    if label is None:
                        # required 인데 source_names.optimization 자체가 None
                        unmapped_required.append(asset.asset_key)
                    else:
                        missing.append(asset.asset_key)
                continue

            row = raw.iloc[row_idx]
            sigma_dict[asset.asset_key] = _strip_pct(row["σ"])
            er_dict[asset.asset_key] = _strip_pct(row["E[R]"])
            ticker_by_key[asset.asset_key] = str(row["Ticker"])
            name_by_key[asset.asset_key] = str(row["Name"])

        # 사용자 결정 #10 = b (강한 error):
        # required + 데이터 부재 → ValueError. 진행 불가.
        if unmapped_required:
            raise ValueError(
                f"required 자산의 source_names.optimization 이 None 입니다 "
                f"(asset_mapping.yaml 의 fallback_policy=explicit_proxy_only 정책 위반): "
                f"{unmapped_required}. proxy.enabled + proxy_ticker 명시 또는 "
                f"Asset_rt_vol 에 데이터 추가 필요."
            )
        if missing:
            raise ValueError(
                f"required 자산이 Asset_rt_vol 에 없음: {missing}. "
                f"silent fallback 금지 — Asset_rt_vol 에 row 추가 또는 "
                f"asset_mapping.yaml 의 source_names.optimization / proxy_ticker 수정 필요."
            )

        # Series
        order = list(sigma_dict.keys())
        sigma = pd.Series(sigma_dict, name="sigma").loc[order]
        er = pd.Series(er_dict, name="expected_return").loc[order]

        # Corr_mat — 한글 Name 인덱스 → asset_key 로 reindex
        corr_raw = self.repo.load_corr_matrix()
        # Name → asset_key 역매핑
        name_to_key = {v: k for k, v in name_by_key.items()}

        corr_idx_keys = []
        corr_missing_in_corr: list[str] = []
        for nm in corr_raw.index:
            key = name_to_key.get(str(nm).strip())
            corr_idx_keys.append(key)
        corr_col_keys = []
        for nm in corr_raw.columns:
            key = name_to_key.get(str(nm).strip())
            corr_col_keys.append(key)

        corr = corr_raw.copy()
        corr.index = pd.Index(corr_idx_keys)
        corr.columns = pd.Index(corr_col_keys)

        # 우리가 가진 asset_key 중 corr 에 없는 것 검출
        for key in order:
            if key not in corr.index or key not in corr.columns:
                corr_missing_in_corr.append(key)
        if corr_missing_in_corr:
            raise ValueError(
                f"Corr_mat 에서 매칭되지 않는 자산: {corr_missing_in_corr}. "
                f"Corr_mat 의 한글 인덱스가 Asset_rt_vol Name 과 일치해야 함."
            )

        corr = corr.loc[order, order].astype(float)

        cov = CovarianceEstimator.estimate(sigma, corr)

        diagnostics = {
            "n_assets": len(order),
            "asset_keys": order,
            "ticker_by_key": ticker_by_key,
            "name_by_key": name_by_key,
            "missing_assets": [],
            "ust30_policy": "strict_error_b",
            # Phase E-6.2 telemetry — read-only diagnostics dump.
            # 포트폴리오 산출 영향 없음 (allocation/optimizer/projection 미참조).
            # 시각화 main 블록 B (MVO Input → SAA Construction) 의존 데이터.
            "expected_returns": {k: float(er[k]) for k in order},
            "volatilities": {k: float(sigma[k]) for k in order},
            "correlation_matrix": {
                k: {kk: float(corr.loc[k, kk]) for kk in order} for k in order
            },
            "covariance_matrix": {
                k: {kk: float(cov.loc[k, kk]) for kk in order} for k in order
            },
        }

        return CapitalMarketAssumption(
            expected_returns=er,
            volatilities=sigma,
            correlation=corr,
            covariance=cov,
            diagnostics=diagnostics,
        )
