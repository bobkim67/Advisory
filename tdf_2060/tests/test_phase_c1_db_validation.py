"""Phase C.1 — semantic_type / return_transform 검증 + sanity + dry-run."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest


# ── helpers ───────────────────────────────────────────────────────────


def _level_series(seed: int, n_months: int = 60, end: date | None = None) -> pd.DataFrame:
    """레벨 시계열 (level_t = level_{t-1} × (1+r))."""
    end = end or date(2026, 3, 31)
    rng = np.random.default_rng(seed)
    r = rng.normal(0.006, 0.04, n_months)
    levels = 100.0 * np.cumprod(1.0 + r)
    idx = pd.date_range(end=end, periods=n_months, freq="ME")
    return pd.DataFrame({"timestamp_observation": idx,
                         "data": [str(v) for v in levels]})


def _yield_series(seed: int, n_months: int = 60, end: date | None = None) -> pd.DataFrame:
    """yield 시계열 (3.5% 근방을 진동). pct_change 하면 안 됨."""
    end = end or date(2026, 3, 31)
    rng = np.random.default_rng(seed)
    y = 3.5 + np.cumsum(rng.normal(0, 0.05, n_months))  # 단위: %
    idx = pd.date_range(end=end, periods=n_months, freq="ME")
    return pd.DataFrame({"timestamp_observation": idx,
                         "data": [str(v) for v in y]})


def _stale_series(seed: int = 0) -> pd.DataFrame:
    """latest 가 2년 전인 시계열."""
    return _level_series(seed=seed, n_months=60, end=date(2024, 3, 31))


def _extreme_series(seed: int = 7) -> pd.DataFrame:
    """월 50% return 한 번 포함."""
    df = _level_series(seed=seed, n_months=60)
    # 마지막 행을 50% 점프
    last_v = float(df["data"].iloc[-2])
    df.loc[df.index[-1], "data"] = str(last_v * 1.50)
    return df


def _make_sources(assets: list[dict]):
    return {
        "asset_rt_vol": {"computation_mode": "from_timeseries",
                          "lookback_years": 5, "annualization": 12},
        "corr_matrix": {"computation_mode": "from_timeseries", "lookback_years": 5},
        "regime_source": {"enabled": False},
        "regime_return_source": {"enabled": False},
        "assets": assets,
    }


# ── 1) yield + transform 미명시 → ValueError ──────────────────────────


def test_db_semantic_type_yield_without_transform_raises():
    from tdf_engine.repositories.db_market_data import DBMarketDataRepository

    fake = {(100, 6): _yield_series(seed=1)}
    sources = _make_sources([
        {
            "asset_key": "kr_treasury_10y",
            "dataset_id": 100,
            "ticker": "KPGB10YR",
            "value_dataseries": 6,
            "currency": None,
            "frequency": "M",
            "required": True,
            "semantic_type": "yield",
            # return_transform 누락 — 명시 필수
        }
    ])
    repo = DBMarketDataRepository(fake, sources)
    with pytest.raises(ValueError, match=r"return_transform 명시 필수"):
        repo.load_asset_rt_vol()


# ── 2) total_return_index + pct_change → 정상 동작 ────────────────────


def test_db_semantic_type_total_return_index_allows_pct_change():
    from tdf_engine.repositories.db_market_data import DBMarketDataRepository

    fake = {(101, 6): _level_series(seed=2)}
    sources = _make_sources([
        {
            "asset_key": "us_growth_equity",
            "dataset_id": 101,
            "ticker": "M2US000G Index",
            "value_dataseries": 6,
            "currency": None,
            "frequency": "M",
            "required": True,
            "semantic_type": "total_return_index",
            "return_transform": "pct_change",
        }
    ])
    repo = DBMarketDataRepository(fake, sources, as_of_date="2026-03-31")
    df = repo.load_asset_rt_vol()
    assert len(df) == 1
    assert df["σ"].iloc[0].endswith("%")
    s = repo.diag.sanity["us_growth_equity"]
    assert s["semantic_type"] == "total_return_index"
    assert "semantic_type_not_returnable" not in s["suspicious_flags"]


# ── 3) stale data 시 sanity 에 stale_data flag ────────────────────────


def test_db_sanity_flags_stale_data():
    from tdf_engine.repositories.db_market_data import DBMarketDataRepository

    fake = {(102, 6): _stale_series()}
    sources = _make_sources([
        {
            "asset_key": "us_value_equity",
            "dataset_id": 102,
            "ticker": "M2US000V Index",
            "value_dataseries": 6,
            "currency": None,
            "frequency": "M",
            "required": True,
            "semantic_type": "total_return_index",
            "return_transform": "pct_change",
        }
    ])
    repo = DBMarketDataRepository(fake, sources, as_of_date="2026-03-31")
    repo.load_asset_rt_vol()
    flags = repo.diag.sanity["us_value_equity"]["suspicious_flags"]
    assert "stale_data" in flags or "latest_date_before_as_of" in flags


# ── 4) extreme return 시 sanity 에 extreme_return flag ───────────────


def test_db_sanity_flags_extreme_return():
    from tdf_engine.repositories.db_market_data import DBMarketDataRepository

    fake = {(103, 6): _extreme_series()}
    sources = _make_sources([
        {
            "asset_key": "kr_equity",
            "dataset_id": 103,
            "ticker": "M2KR INDEX",
            "value_dataseries": 6,
            "currency": None,
            "frequency": "M",
            "required": True,
            "semantic_type": "total_return_index",
            "return_transform": "pct_change",
        }
    ])
    repo = DBMarketDataRepository(fake, sources, as_of_date="2026-03-31")
    repo.load_asset_rt_vol()
    assert "extreme_return" in repo.diag.sanity["kr_equity"]["suspicious_flags"]


# ── 5) dry-run 이 missing dataset 보고 ─────────────────────────────────


def test_db_dry_run_reports_missing_dataset(loader):
    """빈 fake engine 으로 DB 호출 → 모든 자산 missing 으로 진단된다 (permissive)."""
    from tdf_engine.repositories.db_market_data import DBMarketDataRepository

    raw = loader.load_db_sources_raw()
    assert raw is not None

    fake_engine: dict = {}
    repo = DBMarketDataRepository(fake_engine, raw, as_of_date="2026-03-31",
                                   permissive=True)
    with pytest.raises(ValueError, match=r"유효한 자산 데이터 없음"):
        repo.load_asset_rt_vol()
    # 9 자산 모두 missing 으로 잡혀야 함
    missing = set(repo.diag.datasets_missing)
    assert {"kr_equity", "us_growth_equity", "us_high_yield",
            "kr_aggregate_bond", "kr_treasury_10y"}.issubset(missing)


# ── 6) inspect_db_sources 출력 포맷 ────────────────────────────────────


def test_inspect_db_sources_formats_candidates():
    from tdf_engine.tools.inspect_db_sources import format_dataset_table, guess_semantic

    rows = [
        {"id": 11, "name": "Vanguard Growth ETF", "ISIN": "US9229087369", "symbol": "VUG-US"},
        {"id": 1, "name": "Treasury 20Y Yield", "ISIN": None, "symbol": None},
    ]
    out = format_dataset_table(rows, with_guess=True)
    assert "Vanguard Growth ETF" in out
    assert "Treasury 20Y Yield" in out
    # 추정 컬럼이 포함됨
    assert "nav" in out or "yield" in out

    # guess_semantic 내부 로직
    st, rt = guess_semantic("Bloomberg US Corporate High Yield Total Return")
    assert st in ("total_return_index", "nav")
    st2, _ = guess_semantic("USGG30YR Yield")
    assert st2 == "yield"


# ── 7) covariance NaN warning ─────────────────────────────────────────


def test_covariance_nan_warning_is_reported():
    """자산 시계열의 시점이 거의 겹치지 않으면 corr 입력 NaN 비율이 높아 warning 기록."""
    from tdf_engine.repositories.db_market_data import DBMarketDataRepository

    # 자산 1: 2020-01 ~ 2022-12, 자산 2: 2024-01 ~ 2026-03 → 겹침 없음
    df1 = pd.DataFrame({
        "timestamp_observation": pd.date_range(end=date(2022, 12, 31), periods=36, freq="ME"),
        "data": [str(100 + i) for i in range(36)],
    })
    df2 = pd.DataFrame({
        "timestamp_observation": pd.date_range(end=date(2026, 3, 31), periods=27, freq="ME"),
        "data": [str(100 + i) for i in range(27)],
    })
    fake = {(200, 6): df1, (201, 6): df2}
    sources = _make_sources([
        {
            "asset_key": "a", "dataset_id": 200, "ticker": "A", "value_dataseries": 6,
            "currency": None, "frequency": "M", "required": True,
            "semantic_type": "total_return_index", "return_transform": "pct_change",
        },
        {
            "asset_key": "b", "dataset_id": 201, "ticker": "B", "value_dataseries": 6,
            "currency": None, "frequency": "M", "required": True,
            "semantic_type": "total_return_index", "return_transform": "pct_change",
        },
    ])
    repo = DBMarketDataRepository(fake, sources, as_of_date="2026-03-31")
    # corr 시도 — 겹치는 행이 거의 없을 것
    try:
        repo.load_corr_matrix()
    except ValueError:
        # 정합 후 행 0 인 경우 ValueError. 어느 쪽이든 corr_nan_warning 또는
        # warnings 에 NaN 관련 메시지가 남아야 한다.
        pass
    has_nan_warning = (
        repo.diag.corr_nan_warning is not None
        or any("NaN" in w or "정합" in w for w in repo.diag.warnings)
    )
    assert has_nan_warning, f"warnings={repo.diag.warnings}"
