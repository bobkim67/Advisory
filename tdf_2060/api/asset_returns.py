"""Phase 6.3e (2026-05-27) — GET /api/r-track/asset-returns.

Returns daily price-level time series for the 9 MVO assets (mapped via
`tdf_engine/config/db_sources.yaml` → SCIP `back_datapoint`) so the
frontend can backtest a candidate portfolio: cumulative return + MDD,
historical line chart.

Review-only. permanent invariants (is_production_selection / dry_run_only)
unchanged. No production allocation / TAA / selection is touched.

Connection: `SCIP_URL` env var, or default
`mysql+pymysql://solution:Solution123!@192.168.195.55/SCIP?charset=utf8mb4`
(per repo CLAUDE.md DB접속 정보 — SCIP is read-only telemetry, not a
secrets-sensitive dataset).
"""
from __future__ import annotations

import os
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from tdf_engine.repositories._blob import parse_data_blob

router = APIRouter(prefix="/api/r-track", tags=["r-track"])

ENGINE_ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def _get_engine():
    from sqlalchemy import create_engine

    url = (
        os.environ.get("SCIP_URL")
        or "mysql+pymysql://solution:Solution123!@192.168.195.55/SCIP?charset=utf8mb4"
    )
    return create_engine(url, pool_pre_ping=True, future=True)


@lru_cache(maxsize=1)
def _load_assets_cfg() -> tuple[dict, ...]:
    yml = ENGINE_ROOT / "tdf_engine" / "config" / "db_sources.yaml"
    data = yaml.safe_load(yml.read_text(encoding="utf-8"))
    return tuple(data.get("assets") or [])


class AssetSeries(BaseModel):
    asset_key: str
    dataset_id: int
    dataseries_id: int
    ticker: str | None = None
    dates: list[str]
    prices: list[float]


class AssetReturnsResponse(BaseModel):
    schema_version: str = "r_track_2_asset_returns.1"
    start_date: str | None = None
    end_date: str | None = None
    asset_keys: list[str]
    series: list[AssetSeries]
    is_production_selection: bool = False
    dry_run_only: bool = True
    notes: list[str] = Field(
        default_factory=lambda: [
            "Daily price-level series from SCIP back_datapoint.",
            "Frontend uses these to backtest candidate weights (cum return + MDD).",
            "review-only / dry_run_only=true.",
        ]
    )


@router.get("/asset-returns", response_model=AssetReturnsResponse)
def asset_returns(
    start_date: str | None = Query(
        None, description="Inclusive lower bound (YYYY-MM-DD). Default = 10y before latest obs."
    ),
    end_date: str | None = Query(
        None, description="Inclusive upper bound (YYYY-MM-DD). Default = latest obs."
    ),
) -> AssetReturnsResponse:
    from sqlalchemy import text

    start_ts: date | None = None
    end_ts: date | None = None
    if start_date:
        try:
            start_ts = datetime.fromisoformat(start_date).date()
        except ValueError as e:
            raise HTTPException(400, f"invalid start_date: {start_date}") from e
    if end_date:
        try:
            end_ts = datetime.fromisoformat(end_date).date()
        except ValueError as e:
            raise HTTPException(400, f"invalid end_date: {end_date}") from e
    if start_ts and end_ts and start_ts > end_ts:
        raise HTTPException(400, "start_date must be <= end_date")

    engine = _get_engine()
    assets = _load_assets_cfg()

    sql = text(
        "SELECT timestamp_observation, data FROM back_datapoint "
        "WHERE dataset_id = :ds AND dataseries_id = :sr "
        "ORDER BY timestamp_observation"
    )

    series_out: list[AssetSeries] = []
    asset_keys_out: list[str] = []

    with engine.connect() as conn:
        for entry in assets:
            ak = str(entry.get("asset_key") or "")
            if not ak:
                continue
            ds_id = entry.get("dataset_id")
            if ds_id is None:
                continue
            value_sr = entry.get("value_dataseries", 6)
            fb_sr = entry.get("fallback_dataseries")
            blob_key = entry.get("blob_key") or entry.get("currency")

            rows = conn.execute(
                sql, {"ds": int(ds_id), "sr": int(value_sr)}
            ).fetchall()
            used_sr = int(value_sr)
            if not rows and fb_sr is not None:
                rows = conn.execute(
                    sql, {"ds": int(ds_id), "sr": int(fb_sr)}
                ).fetchall()
                used_sr = int(fb_sr)
            if not rows:
                continue

            dates_: list[str] = []
            prices: list[float] = []
            for ts, blob in rows:
                d: date
                if isinstance(ts, datetime):
                    d = ts.date()
                elif isinstance(ts, date):
                    d = ts
                else:
                    # bytes / str fallback
                    try:
                        d = datetime.fromisoformat(str(ts)).date()
                    except ValueError:
                        continue
                if start_ts and d < start_ts:
                    continue
                if end_ts and d > end_ts:
                    continue
                v = parse_data_blob(blob, key=blob_key)
                if v is None or isinstance(v, dict):
                    continue
                try:
                    vf = float(v)
                except (TypeError, ValueError):
                    continue
                if not (vf > 0):
                    # price index must be positive — skip zero/neg blobs
                    continue
                dates_.append(d.isoformat())
                prices.append(vf)

            if not dates_:
                continue

            # Sort + dedup by date (keep last value per date).
            paired = sorted(zip(dates_, prices), key=lambda p: p[0])
            dedup_d: list[str] = []
            dedup_p: list[float] = []
            for d_str, pv in paired:
                if dedup_d and dedup_d[-1] == d_str:
                    dedup_p[-1] = pv
                else:
                    dedup_d.append(d_str)
                    dedup_p.append(pv)

            asset_keys_out.append(ak)
            series_out.append(
                AssetSeries(
                    asset_key=ak,
                    dataset_id=int(ds_id),
                    dataseries_id=used_sr,
                    ticker=str(entry.get("ticker") or "") or None,
                    dates=dedup_d,
                    prices=dedup_p,
                )
            )

    return AssetReturnsResponse(
        start_date=start_date,
        end_date=end_date,
        asset_keys=asset_keys_out,
        series=series_out,
    )
