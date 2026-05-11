"""Phase C — DBMarketDataRepository + CLI source 옵션 + file vs db 동등성.

실 DB 접속 없이 in-memory fake (dict-of-DataFrame) 로 검증.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest


# ── helpers / fakes ───────────────────────────────────────────────────


def _make_fake_levels(seed: int, n_months: int = 60, freq: str = "ME"):
    """월말 (level_t = level_{t-1}*(1+r)) 시계열. r ~ N(mu, sigma).

    blob 형식 = 단일 숫자 (str). repr 그대로 SCIP back_datapoint.data 흉내.
    """
    rng = np.random.default_rng(seed)
    mu, sigma = 0.006, 0.04  # 월간
    r = rng.normal(mu, sigma, n_months)
    levels = 100.0 * np.cumprod(1.0 + r)
    idx = pd.date_range(end=date(2026, 3, 31), periods=n_months, freq=freq)
    df = pd.DataFrame(
        {
            "timestamp_observation": idx,
            "data": [str(v) for v in levels],
        }
    )
    return df


def _build_fake_db_for_assets(asset_keys: list[str]):
    """각 asset_key 마다 (dataset_id=ix+100, dataseries=6) 시계열 1개씩 생성한 fake DB."""
    fake = {}
    mapping = {}  # asset_key → dataset_id
    for i, ak in enumerate(asset_keys, start=100):
        fake[(i, 6)] = _make_fake_levels(seed=i)
        mapping[ak] = i
    return fake, mapping


_TICKER_BY_KEY = {
    "kr_equity":          "M2KR INDEX",
    "us_growth_equity":   "M2US000G Index",
    "us_value_equity":    "M2US000V Index",
    "dm_ex_us_equity":    "TAD09XU Index",
    "em_equity":          "M2EF Index",
    "kr_aggregate_bond":  "SPBKRCOT Index",
    "kr_treasury_10y":    "KPGB10YR Index",
    "us_treasury_30y":    "BRFUT004",  # Phase C.2 매핑 갱신
    "us_high_yield":      "LF98TRUU Index",
}


def _make_db_sources_yaml_dict(mapping: dict[str, int], ust30_mode: str = "direct",
                                 ust30_proxy_id: int | None = None):
    """db_sources.yaml 의 dict 형태 생성 (fake DB 매핑 반영).

    ticker 는 asset_mapping.yaml::source_names.optimization 와 정합하게.
    DB repo 가 반환하는 DataFrame 의 Ticker 컬럼이 그 값이어야 CMA Builder 가 매칭.
    """
    assets = []
    for ak, ds_id in mapping.items():
        entry = {
            "asset_key": ak,
            "dataset_id": ds_id,
            "ticker": _TICKER_BY_KEY.get(ak, ak.upper()),
            "value_dataseries": 6,
            "currency": None,
            "frequency": "M",
            "required": True,
        }
        if ak == "us_treasury_30y":
            entry["mapping_mode"] = ust30_mode
            if ust30_mode == "proxy":
                entry["dataset_id"] = None
                entry["proxy"] = {
                    "enabled": True,
                    "proxy_dataset_id": ust30_proxy_id,
                    "reason": "test fixture: 20Y proxy",
                }
        assets.append(entry)
    return {
        "asset_rt_vol": {"computation_mode": "from_timeseries",
                          "lookback_years": 5, "annualization": 12},
        "corr_matrix": {"computation_mode": "from_timeseries", "lookback_years": 5},
        "regime_source": {"enabled": False},
        "regime_return_source": {"enabled": False},
        "assets": assets,
    }


_NINE_KEYS = [
    "kr_equity",
    "us_growth_equity",
    "us_value_equity",
    "dm_ex_us_equity",
    "em_equity",
    "kr_aggregate_bond",
    "kr_treasury_10y",
    "us_treasury_30y",
    "us_high_yield",
]


# ── 1) DB repo 가 normalized asset_rt_vol 반환 ─────────────────────────


def test_db_repository_returns_normalized_asset_rt_vol():
    from tdf_engine.repositories.db_market_data import DBMarketDataRepository

    fake, mapping = _build_fake_db_for_assets(_NINE_KEYS)
    sources = _make_db_sources_yaml_dict(mapping)
    repo = DBMarketDataRepository(fake, sources, as_of_date="2026-03-31")

    df = repo.load_asset_rt_vol()
    # file 형식: columns 동일
    assert set(df.columns) >= {"Ticker", "Name", "σ", "E[R]"}
    assert len(df) == 9
    # σ 와 E[R] 가 % 형식 문자열
    assert df["σ"].iloc[0].endswith("%")
    assert df["E[R]"].iloc[0].endswith("%")
    # diagnostics 채워짐
    assert len(repo.diag.datasets_loaded) == 9
    assert repo.diag.as_of_date == "2026-03-31"


# ── 2) DB repo 가 normalized corr_matrix 반환 ──────────────────────────


def test_db_repository_returns_normalized_corr_matrix():
    from tdf_engine.repositories.db_market_data import DBMarketDataRepository

    fake, mapping = _build_fake_db_for_assets(_NINE_KEYS)
    sources = _make_db_sources_yaml_dict(mapping)
    repo = DBMarketDataRepository(fake, sources)

    corr = repo.load_corr_matrix()
    assert corr.shape == (9, 9)
    # 대각 = 1
    assert np.allclose(np.diag(corr.to_numpy()), 1.0, atol=1e-9)
    # 대칭
    assert np.allclose(corr.to_numpy(), corr.to_numpy().T, atol=1e-9)


# ── 3) required missing → ValueError ───────────────────────────────────


def test_db_repository_missing_required_dataset_raises():
    from tdf_engine.repositories.db_market_data import DBMarketDataRepository

    fake, mapping = _build_fake_db_for_assets(_NINE_KEYS)
    sources = _make_db_sources_yaml_dict(mapping)
    # us_treasury_30y 를 requires_decision 으로 바꿔서 강제 ValueError 유도
    for a in sources["assets"]:
        if a["asset_key"] == "us_treasury_30y":
            a["mapping_mode"] = "requires_decision"
            a["dataset_id"] = None

    repo = DBMarketDataRepository(fake, sources)
    with pytest.raises(ValueError, match="requires_decision"):
        repo.load_asset_rt_vol()


# ── 4) source=file 모드 회귀 (기존 E2E 동작) ──────────────────────────


def test_build_portfolio_source_file_still_works(augmented_source_root, augmented_assets, loader):
    from tdf_engine.tools.build_portfolio import _build_with_repos
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.repositories.file_repositories import (
        FileMarketDataRepository,
        FileProductRepository,
    )

    market = FileMarketDataRepository(augmented_source_root)
    products = FileProductRepository(augmented_source_root)

    # augmented_assets (ust30 source_names 매핑된 fixture) 적용을 위해 loader.load_assets()
    # 대신 테스트용 monkeypatch 한 결과를 _build_with_repos 내부가 또 부른다 → 우회 위해
    # 직접 portfolio 빌드 (E2E 회귀와 같은 경로로).
    from tdf_engine.optimization.tool import OptimizationTool
    from tdf_engine.regime.tool import RegimeAnalysisTool
    from tdf_engine.taa.tool import TAAOverlayTool
    from tdf_engine.universe.classifier import ProductClassifier, load_rules
    from tdf_engine.universe.tool import UniverseTool
    from tdf_engine.selection.tool import ProductSelectionTool
    from tdf_engine.portfolio.tool import PortfolioConstructionTool

    pt = ProductType.FUND
    tdf = loader.load_tdf_config()
    opt_cfg = loader.load_optimization_config()
    taa_cfg = loader.load_taa_config()
    uni_cfg = loader.load_universe_config()
    raw_rules = loader.load_classification_rules_raw()
    classifier = ProductClassifier(load_rules(raw_rules))

    opt_tool = OptimizationTool(market, augmented_assets, tdf, opt_cfg)
    regime_tool = RegimeAnalysisTool(market, taa_cfg)
    taa_tool = TAAOverlayTool(taa_cfg, assets=augmented_assets)
    uni_tool = UniverseTool(products, uni_cfg, pt, classifier=classifier)

    construction = PortfolioConstructionTool(
        optimization_tool=opt_tool, regime_tool=regime_tool, taa_tool=taa_tool,
        universe_tool=uni_tool,
        selection_tool_factory=lambda u: ProductSelectionTool(u, uni_cfg, pt),
        tdf_config=tdf, universe_config=uni_cfg, assets=augmented_assets,
    )
    portfolio = construction.run(pt)

    assert abs(float(portfolio.product_weights["weight"].sum()) - 1.0) < 1e-6


# ── 5) source=db (fake) 결과 == source=file 결과 (동일 입력 가정 시) ───


def test_build_portfolio_source_db_with_fake_repo_produces_valid_result(
    augmented_source_root, augmented_assets, loader
):
    """fake DB 로 DBMarketDataRepository 를 만들고 file repo 와 합쳐서 E2E.

    데이터가 다르므로 weights 가 동일하지 않지만, *형식적 정합성* (sum=1, 9개 자산,
    bucket bound) 은 동일해야 한다.
    """
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.optimization.tool import OptimizationTool
    from tdf_engine.portfolio.tool import PortfolioConstructionTool
    from tdf_engine.regime.tool import RegimeAnalysisTool
    from tdf_engine.repositories.composite import CompositeMarketDataRepository
    from tdf_engine.repositories.db_market_data import DBMarketDataRepository
    from tdf_engine.repositories.file_repositories import (
        FileMarketDataRepository,
        FileProductRepository,
    )
    from tdf_engine.selection.tool import ProductSelectionTool
    from tdf_engine.taa.tool import TAAOverlayTool
    from tdf_engine.universe.classifier import ProductClassifier, load_rules
    from tdf_engine.universe.tool import UniverseTool

    fake, mapping = _build_fake_db_for_assets(_NINE_KEYS)
    sources = _make_db_sources_yaml_dict(mapping)

    db_repo = DBMarketDataRepository(fake, sources, as_of_date="2026-03-31")
    file_repo = FileMarketDataRepository(augmented_source_root)
    composite = CompositeMarketDataRepository(primary=db_repo, fallback=file_repo)

    products = FileProductRepository(augmented_source_root)
    pt = ProductType.FUND
    tdf = loader.load_tdf_config()
    opt_cfg = loader.load_optimization_config()
    taa_cfg = loader.load_taa_config()
    uni_cfg = loader.load_universe_config()
    classifier = ProductClassifier(load_rules(loader.load_classification_rules_raw()))

    opt_tool = OptimizationTool(composite, augmented_assets, tdf, opt_cfg)
    regime_tool = RegimeAnalysisTool(composite, taa_cfg)
    taa_tool = TAAOverlayTool(taa_cfg, assets=augmented_assets)
    uni_tool = UniverseTool(products, uni_cfg, pt, classifier=classifier)

    construction = PortfolioConstructionTool(
        optimization_tool=opt_tool, regime_tool=regime_tool, taa_tool=taa_tool,
        universe_tool=uni_tool,
        selection_tool_factory=lambda u: ProductSelectionTool(u, uni_cfg, pt),
        tdf_config=tdf, universe_config=uni_cfg, assets=augmented_assets,
    )
    portfolio = construction.run(pt)

    # 형식 정합성
    assert abs(float(portfolio.product_weights["weight"].sum()) - 1.0) < 1e-6
    assert len(portfolio.asset_weights) == 9
    # Phase D relaxed (D-01 closed): bucket hard bound 비활성. long-only + sum=1만 hard.
    assert (portfolio.asset_weights >= -1e-9).all()
    eq_keys = [a.asset_key for a in augmented_assets if a.bucket.value == "equity"]
    eq_sum = float(portfolio.asset_weights.loc[eq_keys].sum())
    assert 0.0 <= eq_sum <= 1.0  # bucket 자유 범위

    # db_repo diagnostics 가 채워짐 (자산 9 모두 fake DB 에서 load)
    assert len(db_repo.diag.datasets_loaded) == 9
    assert db_repo.diag.as_of_date == "2026-03-31"


# ── 6) ust30 proxy 사용 시 warning/diag 기록 ──────────────────────────


def test_us_treasury_30y_proxy_records_warning():
    from tdf_engine.repositories.db_market_data import DBMarketDataRepository

    fake, mapping = _build_fake_db_for_assets(_NINE_KEYS)
    # ust30 의 직접 dataset 은 제거하고, 대신 proxy id (예: 999) 를 fake 에 추가
    proxy_id = 999
    fake[(proxy_id, 6)] = _make_fake_levels(seed=999)
    sources = _make_db_sources_yaml_dict(
        mapping, ust30_mode="proxy", ust30_proxy_id=proxy_id
    )
    repo = DBMarketDataRepository(fake, sources)

    df = repo.load_asset_rt_vol()
    assert len(df) == 9
    assert repo.diag.proxy_used is True
    assert "us_treasury_30y" in repo.diag.proxy_mappings
    pm = repo.diag.proxy_mappings["us_treasury_30y"]
    assert pm["proxy_dataset_id"] == proxy_id


# ── 7) source_type 이 output payload 에 기록됨 ─────────────────────────


def test_source_type_is_written_to_output_payload(
    augmented_source_root, augmented_assets, loader, tmp_path
):
    """write_outputs 가 payload 에 source_type 을 기록한다."""
    import json
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.optimization.tool import OptimizationTool
    from tdf_engine.portfolio.tool import PortfolioConstructionTool
    from tdf_engine.regime.tool import RegimeAnalysisTool
    from tdf_engine.repositories.file_repositories import (
        FileMarketDataRepository,
        FileProductRepository,
    )
    from tdf_engine.selection.tool import ProductSelectionTool
    from tdf_engine.taa.tool import TAAOverlayTool
    from tdf_engine.tools.build_portfolio import write_outputs
    from tdf_engine.universe.classifier import ProductClassifier, load_rules
    from tdf_engine.universe.tool import UniverseTool

    market = FileMarketDataRepository(augmented_source_root)
    products = FileProductRepository(augmented_source_root)
    pt = ProductType.ETF
    tdf = loader.load_tdf_config()
    opt_cfg = loader.load_optimization_config()
    taa_cfg = loader.load_taa_config()
    uni_cfg = loader.load_universe_config()
    classifier = ProductClassifier(load_rules(loader.load_classification_rules_raw()))

    opt_tool = OptimizationTool(market, augmented_assets, tdf, opt_cfg)
    regime_tool = RegimeAnalysisTool(market, taa_cfg)
    taa_tool = TAAOverlayTool(taa_cfg, assets=augmented_assets)
    uni_tool = UniverseTool(products, uni_cfg, pt, classifier=classifier)

    construction = PortfolioConstructionTool(
        optimization_tool=opt_tool, regime_tool=regime_tool, taa_tool=taa_tool,
        universe_tool=uni_tool,
        selection_tool_factory=lambda u: ProductSelectionTool(u, uni_cfg, pt),
        tdf_config=tdf, universe_config=uni_cfg, assets=augmented_assets,
    )
    portfolio = construction.run(pt)
    portfolio.diagnostics["db_source"] = {"source_type": "file", "as_of_date": None}

    csv_path, json_path = write_outputs(portfolio, tmp_path / "out", pt.value)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["source_type"] == "file"
    assert "as_of_date" in payload
