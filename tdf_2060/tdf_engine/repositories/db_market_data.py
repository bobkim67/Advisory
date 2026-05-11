"""DBMarketDataRepository — SCIP back_datapoint 기반 시계열을
file repo 와 동일한 normalized DataFrame 으로 반환.

Phase C    : 구조 + fake DB 검증.
Phase C.1  : semantic_type / return_transform 정책 + sanity check + dry-run.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any, TYPE_CHECKING

from tdf_engine.repositories._blob import parse_data_blob
from tdf_engine.repositories.semantic import resolve_transform

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

logger = logging.getLogger(__name__)


# ── 결과 진단 ──────────────────────────────────────────────────────────


@dataclass
class DBSourceDiagnostics:
    source_type: str = "db"
    datasets_loaded: list[int] = field(default_factory=list)
    datasets_missing: list[str] = field(default_factory=list)
    proxy_used: bool = False
    proxy_mappings: dict[str, dict[str, Any]] = field(default_factory=dict)
    latest_data_date_by_dataset: dict[int, str] = field(default_factory=dict)
    as_of_date: str | None = None
    warnings: list[str] = field(default_factory=list)
    config_path: str | None = None
    # Phase C.1 — 자산별 sanity
    sanity: dict[str, dict[str, Any]] = field(default_factory=dict)
    cov_matrix_psd_warning: str | None = None
    corr_nan_warning: str | None = None

    def as_dict(self) -> dict:
        return {
            "source_type": self.source_type,
            "datasets_loaded": list(self.datasets_loaded),
            "datasets_missing": list(self.datasets_missing),
            "proxy_used": self.proxy_used,
            "proxy_mappings": dict(self.proxy_mappings),
            "latest_data_date_by_dataset": dict(self.latest_data_date_by_dataset),
            "as_of_date": self.as_of_date,
            "warnings": list(self.warnings),
            "config_path": self.config_path,
            "sanity": dict(self.sanity),
            "cov_matrix_psd_warning": self.cov_matrix_psd_warning,
            "corr_nan_warning": self.corr_nan_warning,
        }


# ── sanity threshold ──────────────────────────────────────────────────


@dataclass(frozen=True)
class SanityThresholds:
    min_obs: int = 12
    stale_days: int = 60
    extreme_monthly_return: float = 0.30
    zero_vol_threshold: float = 1e-4
    min_ann_vol: float = 0.005      # 0.5% — 비현실적으로 낮음
    max_ann_vol: float = 1.50       # 150% — 비현실적으로 높음


# ── 핵심 repository ────────────────────────────────────────────────────


class DBMarketDataRepository:
    def __init__(
        self,
        engine_or_conn,
        db_sources: dict,
        as_of_date: date | str | None = None,
        sanity_thresholds: SanityThresholds | None = None,
        permissive: bool = False,
    ):
        """permissive=True 면 required_but_missing / requires_decision 시
        ValueError 대신 diag.datasets_missing 에 기록하고 다음 자산으로 진행.
        dry-run 진단에 사용. 실제 portfolio build 에서는 False (기본).
        """
        self.engine = engine_or_conn
        self.cfg = db_sources or {}
        if isinstance(as_of_date, str):
            try:
                as_of_date = date.fromisoformat(as_of_date)
            except ValueError as e:
                raise ValueError(f"as_of_date must be YYYY-MM-DD: {as_of_date}") from e
        self.as_of_date: date | None = as_of_date
        self.thresholds = sanity_thresholds or SanityThresholds()
        self.permissive = bool(permissive)
        self.diag = DBSourceDiagnostics(
            as_of_date=str(as_of_date) if as_of_date else None,
        )
        # 캐시 — corr 산출 시 동일 시계열 재로딩 방지
        self._monthly_cache: dict[str, "pd.Series"] = {}

    # ── 공개 인터페이스 ────────────────────────────────────────────────

    def load_asset_rt_vol(self) -> "pd.DataFrame":
        import pandas as pd

        ar = self.cfg.get("asset_rt_vol") or {}
        lookback = int(ar.get("lookback_years", 10))
        annualization = int(ar.get("annualization", 12))

        rows: list[dict] = []
        for entry in self.cfg.get("assets") or []:
            asset_key = entry["asset_key"]
            ticker = entry.get("ticker") or asset_key
            name = entry.get("display_name") or ticker

            dataset_id, used_proxy = self._resolve_dataset_id(entry)
            if dataset_id is None:
                if entry.get("required", True):
                    self.diag.datasets_missing.append(asset_key)
                continue

            try:
                transform = resolve_transform(
                    asset_key,
                    entry.get("semantic_type"),
                    entry.get("return_transform"),
                )
            except (ValueError, NotImplementedError) as e:
                if self.permissive:
                    self.diag.datasets_missing.append(asset_key)
                    self.diag.warnings.append(f"{asset_key}: semantic 정책 위반 — {e}")
                    continue
                raise

            ret = self._monthly_returns(
                asset_key=asset_key,
                dataset_id=dataset_id,
                value_dataseries=int(entry.get("value_dataseries", 6)),
                fallback_dataseries=entry.get("fallback_dataseries"),
                blob_key=entry.get("blob_key") or entry.get("currency"),
                lookback_years=lookback,
                transform=transform,
            )
            if ret is None or ret.empty:
                if entry.get("required", True):
                    self.diag.datasets_missing.append(asset_key)
                    self.diag.warnings.append(
                        f"{asset_key}: dataset_id={dataset_id} 시계열 비어있음"
                    )
                continue

            mu = float(ret.mean()) * annualization
            sigma = float(ret.std()) * math.sqrt(annualization)

            # sanity record
            self._record_sanity(
                asset_key=asset_key,
                dataset_id=dataset_id,
                semantic_type=entry.get("semantic_type"),
                ret=ret,
                ann_ret=mu,
                ann_vol=sigma,
            )

            rows.append(
                {
                    "Asset Class": entry.get("bucket_label", ""),
                    "Ticker": ticker,
                    "Name": name,
                    "σ": f"{sigma * 100:.2f}%",
                    "E[R]": f"{mu * 100:.2f}%",
                }
            )

            self.diag.datasets_loaded.append(int(dataset_id))
            self.diag.latest_data_date_by_dataset[int(dataset_id)] = str(ret.index[-1].date())
            if used_proxy:
                self.diag.proxy_used = True
                self.diag.proxy_mappings[asset_key] = {
                    "proxy_dataset_id": dataset_id,
                    "reason": (entry.get("proxy") or {}).get("reason"),
                }

        if not rows:
            raise ValueError(
                "DBMarketDataRepository: asset_rt_vol — 유효한 자산 데이터 없음. "
                "db_sources.yaml::assets 매핑 확인 필요."
            )
        return pd.DataFrame(rows)

    def load_corr_matrix(self) -> "pd.DataFrame":
        import numpy as np
        import pandas as pd

        series_by_name: dict[str, "pd.Series"] = {}
        for entry in self.cfg.get("assets") or []:
            asset_key = entry["asset_key"]
            ticker = entry.get("ticker") or asset_key
            name = entry.get("display_name") or ticker

            dataset_id, _ = self._resolve_dataset_id(entry)
            if dataset_id is None:
                continue

            try:
                transform = resolve_transform(
                    asset_key,
                    entry.get("semantic_type"),
                    entry.get("return_transform"),
                )
            except (ValueError, NotImplementedError):
                continue

            # cache 활용
            ret = self._monthly_cache.get(asset_key)
            if ret is None:
                ret = self._monthly_returns(
                    asset_key=asset_key,
                    dataset_id=dataset_id,
                    value_dataseries=int(entry.get("value_dataseries", 6)),
                    fallback_dataseries=entry.get("fallback_dataseries"),
                    blob_key=entry.get("blob_key") or entry.get("currency"),
                    lookback_years=int((self.cfg.get("corr_matrix") or {}).get("lookback_years", 10)),
                    transform=transform,
                )
            if ret is None or len(ret) < 12:
                continue
            series_by_name[name] = ret

        if len(series_by_name) < 2:
            raise ValueError(
                "DBMarketDataRepository: corr_matrix — 유효 자산 < 2. 매핑 확인 필요."
            )

        joined = pd.concat(series_by_name, axis=1)
        nan_ratio = float(joined.isna().sum().sum() / max(joined.size, 1))
        joined = joined.dropna(how="any")
        if nan_ratio > 0.20:
            self.diag.corr_nan_warning = (
                f"corr 입력 NaN ratio {nan_ratio:.2%} > 20% — 시계열 정합성 점검 필요"
            )
            self.diag.warnings.append(self.diag.corr_nan_warning)

        if joined.empty or joined.shape[1] < 2:
            raise ValueError("corr_matrix 입력 정합 후 행이 없음")

        corr = joined.corr()
        if corr.isna().any().any():
            self.diag.warnings.append("corr_matrix 에 NaN 존재 — 운영자 점검 필요")
            corr = corr.fillna(0.0)
            np.fill_diagonal(corr.values, 1.0)

        # PSD 체크 (covariance 가 아닌 corr 로 체크 — 동등)
        try:
            eigvals = np.linalg.eigvalsh(corr.to_numpy())
            min_eig = float(eigvals.min())
            if min_eig < -1e-8:
                self.diag.cov_matrix_psd_warning = (
                    f"correlation eigvals min={min_eig:.4e} < 0 — covariance 가 PSD 아님. "
                    f"nearest PSD repair 는 Phase C+ 에서 구현 예정"
                )
                self.diag.warnings.append(self.diag.cov_matrix_psd_warning)
        except Exception as e:  # pragma: no cover
            self.diag.warnings.append(f"PSD 체크 실패: {e}")

        return corr

    def load_regime_source(self) -> "pd.DataFrame":
        rs = self.cfg.get("regime_source") or {}
        if not rs.get("enabled", False):
            raise NotImplementedError(
                "regime_source DB 모드 비활성. db_sources.yaml::regime_source.enabled "
                "= true 로 켜고 schema 매핑을 채운 뒤 다시 실행하세요. "
                "Phase C 1차는 file repo 와 혼합 사용을 권장 (CompositeMarketDataRepository)."
            )
        raise NotImplementedError("regime_source DB query — Phase C+ 구현 예정")

    def load_regime_return_source(self) -> "pd.DataFrame":
        rs = self.cfg.get("regime_return_source") or {}
        if not rs.get("enabled", False):
            raise NotImplementedError(
                "regime_return_source DB 모드 비활성."
            )
        raise NotImplementedError("regime_return_source DB query — Phase C+ 구현 예정")

    # ── helper ──────────────────────────────────────────────────────────

    def _resolve_dataset_id(self, entry: dict) -> tuple[int | None, bool]:
        asset_key = entry.get("asset_key")
        mapping_mode = entry.get("mapping_mode")

        if mapping_mode == "requires_decision":
            self.diag.datasets_missing.append(asset_key)
            self.diag.warnings.append(
                f"{asset_key}: mapping_mode=requires_decision — db_sources.yaml 결정 필요"
            )
            if entry.get("required", True) and not self.permissive:
                raise ValueError(
                    f"{asset_key}: db_sources.yaml::mapping_mode=requires_decision. "
                    f"운영자가 direct/proxy/synthetic 중 1개 선택 후 dataset 매핑 명시 필요."
                )
            return None, False

        if mapping_mode == "proxy":
            proxy = entry.get("proxy") or {}
            if proxy.get("enabled") and proxy.get("proxy_dataset_id"):
                return int(proxy["proxy_dataset_id"]), True
            self.diag.warnings.append(
                f"{asset_key}: mapping_mode=proxy 인데 proxy.enabled / proxy_dataset_id 미설정"
            )
            return None, False

        if mapping_mode == "synthetic":
            self.diag.warnings.append(
                f"{asset_key}: mapping_mode=synthetic 은 Phase C 미구현"
            )
            return None, False

        ds = entry.get("dataset_id")
        if ds is None:
            return None, False
        return int(ds), False

    def _monthly_returns(
        self,
        asset_key: str,
        dataset_id: int,
        value_dataseries: int,
        fallback_dataseries: int | None,
        blob_key: str | None,
        lookback_years: int,
        transform: str,
    ):
        """raw 시계열 → transform 적용 → 월간 수익률 Series 반환.

        transform: pct_change | diff | already_return.
        """
        import pandas as pd

        levels = self._query_levels(
            dataset_id=dataset_id,
            value_dataseries=value_dataseries,
            fallback_dataseries=fallback_dataseries,
            blob_key=blob_key,
            lookback_years=lookback_years,
        )
        if levels is None or levels.empty:
            return None

        # 월말 리샘플
        monthly = levels.resample("ME").last().dropna()

        if transform == "pct_change":
            ret = monthly.pct_change().dropna()
        elif transform == "diff":
            ret = monthly.diff().dropna()
        elif transform == "already_return":
            ret = monthly
        else:
            raise ValueError(f"unknown transform: {transform}")

        self._monthly_cache[asset_key] = ret
        return ret

    def _record_sanity(
        self,
        asset_key: str,
        dataset_id: int,
        semantic_type: str | None,
        ret,
        ann_ret: float,
        ann_vol: float,
    ):
        import pandas as pd

        flags: list[str] = []
        n = int(len(ret))
        latest = ret.index.max() if n else None
        start = ret.index.min() if n else None

        # too few obs
        if n < self.thresholds.min_obs:
            flags.append("too_few_observations")

        # stale
        if self.as_of_date is not None and latest is not None:
            stale_cutoff = pd.Timestamp(self.as_of_date) - pd.Timedelta(days=self.thresholds.stale_days)
            if latest < stale_cutoff:
                flags.append("stale_data")
            if latest > pd.Timestamp(self.as_of_date) + pd.Timedelta(days=1):
                flags.append("latest_date_after_as_of")
            if latest < pd.Timestamp(self.as_of_date) - pd.Timedelta(days=370):
                flags.append("latest_date_before_as_of")

        # extreme return
        if n:
            mn = float(ret.min())
            mx = float(ret.max())
            if abs(mn) > self.thresholds.extreme_monthly_return or abs(mx) > self.thresholds.extreme_monthly_return:
                flags.append("extreme_return")
        else:
            mn = mx = None

        # zero / extreme vol
        if ann_vol < self.thresholds.zero_vol_threshold:
            flags.append("zero_volatility")
        if ann_vol < self.thresholds.min_ann_vol:
            flags.append("annualized_vol_too_low")
        if ann_vol > self.thresholds.max_ann_vol:
            flags.append("annualized_vol_too_high")

        if semantic_type in {"yield", "spread", "macro_indicator"}:
            flags.append("semantic_type_not_returnable")

        sanity = {
            "asset_key": asset_key,
            "dataset_id": int(dataset_id),
            "semantic_type": semantic_type,
            "start_date": str(start.date()) if start is not None else None,
            "end_date": str(latest.date()) if latest is not None else None,
            "obs_count": n,
            "missing_ratio": 0.0,  # 월말 그리드 기준 — 단순화
            "latest_date": str(latest.date()) if latest is not None else None,
            "annualized_return": ann_ret,
            "annualized_vol": ann_vol,
            "min_monthly_return": mn,
            "max_monthly_return": mx,
            "suspicious_flags": flags,
        }
        self.diag.sanity[asset_key] = sanity
        if flags:
            self.diag.warnings.append(
                f"{asset_key} sanity flags: {flags}"
            )

    def _query_levels(
        self,
        dataset_id: int,
        value_dataseries: int = 6,
        fallback_dataseries: int | None = 39,
        blob_key: str | None = None,
        lookback_years: int = 10,
    ):
        import pandas as pd

        for ds_id in [value_dataseries, fallback_dataseries]:
            if ds_id is None:
                continue
            df = self._raw_query(dataset_id, int(ds_id))
            if df is None or df.empty:
                continue
            parsed = []
            for _, row in df.iterrows():
                v = parse_data_blob(row["data"], key=blob_key)
                if v is None:
                    continue
                if isinstance(v, dict):
                    continue
                parsed.append((row["timestamp_observation"], float(v)))
            if not parsed:
                continue
            s = pd.Series(
                [v for _, v in parsed],
                index=pd.to_datetime([d for d, _ in parsed]),
            ).sort_index()
            if self.as_of_date is not None:
                s = s.loc[: pd.Timestamp(self.as_of_date)]
            if lookback_years and not s.empty:
                start = s.index.max() - pd.Timedelta(days=int(lookback_years * 365.25))
                s = s.loc[s.index >= start]
            if not s.empty:
                return s
        return None

    def _raw_query(self, dataset_id: int, dataseries_id: int):
        if isinstance(self.engine, dict):
            df = self.engine.get((int(dataset_id), int(dataseries_id)))
            return df

        import pandas as pd
        try:
            from sqlalchemy.engine import Engine
            if isinstance(self.engine, Engine):
                from sqlalchemy import text
                stmt = text(
                    "SELECT timestamp_observation, data "
                    "FROM back_datapoint "
                    "WHERE dataset_id = :ds AND dataseries_id = :sr "
                    "ORDER BY timestamp_observation"
                )
                return pd.read_sql(stmt, self.engine, params={"ds": int(dataset_id), "sr": int(dataseries_id)})
        except Exception:
            pass

        sql = (
            "SELECT timestamp_observation, data FROM back_datapoint "
            "WHERE dataset_id = %s AND dataseries_id = %s ORDER BY timestamp_observation"
        )
        with self.engine.cursor() as cur:
            cur.execute(sql, (int(dataset_id), int(dataseries_id)))
            rows = cur.fetchall()
        if not rows:
            return pd.DataFrame(columns=["timestamp_observation", "data"])
        if isinstance(rows[0], dict):
            df = pd.DataFrame(rows)
        else:
            df = pd.DataFrame(rows, columns=["timestamp_observation", "data"])
        return df
