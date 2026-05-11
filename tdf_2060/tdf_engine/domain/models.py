"""Domain dataclass 정의.

규칙:
  - 입출력 결과는 pandas.DataFrame 그 자체로 넘기지 않고 dataclass 로 wrap.
  - frozen=True 는 입력 마스터(AssetClassInfo, ProductInfo) 에만 적용, 결과 객체는 mutable.
  - 사용자 결정 #2/#3: AssetClassInfo 는 source_names 를 dict 로 보관 (optimization / regime_return).
  - silent fallback 금지: fallback_policy 를 명시 필드로.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, TYPE_CHECKING

from tdf_engine.domain.enums import Bucket, FallbackPolicy, ProductType, Regime

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd


@dataclass(frozen=True)
class AssetSourceNames:
    """용도별 source 라벨 (사용자 결정 #2, #3)."""

    optimization: str | None         # Asset_rt_vol / Corr_mat 의 라벨 또는 ticker
    regime_return: str | None        # regimeAnalysis_src 의 컬럼명 또는 ticker


@dataclass(frozen=True)
class AssetClassInfo:
    """MVO 자산군 마스터.

    asset_key:        코드 내부 식별자 (snake_case 영문, 유일)
    display_name:     보고서/대시보드 표시명 (한글 허용)
    source_names:     용도별 원천 라벨
    bucket:           Equity / FixedIncome / Alternative / Currency
    flags:            {"risk_asset", "credit", "duration", "safe", ...}
    required:         자산군 자체가 SAA 에서 반드시 존재해야 하는지
    fallback_policy:  데이터 없을 때 처리 방식
    db_dataset_id:    SCIP back_dataset.id 매핑 (placeholder)
    proxy_enabled:    사용자가 명시 지정한 proxy 사용 허용
    proxy_ticker:     명시 지정 proxy ticker (proxy_enabled=True 일 때만)
    """

    asset_key: str
    display_name: str
    source_names: AssetSourceNames
    bucket: Bucket
    flags: frozenset[str] = field(default_factory=frozenset)
    required: bool = True
    fallback_policy: FallbackPolicy = FallbackPolicy.ERROR_IF_MISSING
    db_dataset_id: int | None = None
    proxy_enabled: bool = False
    proxy_ticker: str | None = None
    notes: str | None = None

    def has_flag(self, flag: str) -> bool:
        return flag in self.flags


@dataclass(frozen=True)
class ProductInfo:
    """ETF / Fund 단일 상품."""

    product_id: str                  # 상품번호 (etf/fund_list 의 '상품번호')
    fund_code: str | None            # 제로인협회펀드코드
    name: str                        # 펀드명(Short)
    product_type: ProductType
    kis_asset_class: str             # 대유형(KIS MP)
    sub_type: str                    # 소유형
    region: str | None
    theme: str | None
    manager: str
    inception_date: date | None
    risk_grade: str | None
    quant_score: float | None
    quant_grade: str | None
    return_1y: float | None
    return_3y: float | None
    sharpe_1y: float | None
    aum: float | None
    investment_limit: float | None
    mvo_asset_class: str | None = None  # 매핑 후 부여 (asset_key)


@dataclass(frozen=True)
class RegimeState:
    """단일 시점 단일 region 의 ECI 상태."""

    as_of: date
    region: str
    placement: float
    velocity: float
    regime: Regime

    @property
    def label(self) -> str:
        return self.regime.label


# ── Result Objects (mutable) ──────────────────────────────────────────


@dataclass
class CapitalMarketAssumption:
    """E[R], σ, Σ 묶음."""

    expected_returns: "pd.Series"     # asset_key → E[R]
    volatilities: "pd.Series"         # asset_key → σ
    correlation: "pd.DataFrame"       # asset_key × asset_key
    covariance: "pd.DataFrame"        # σ · C · σ
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationResult:
    weights: "pd.Series"
    expected_return: float
    volatility: float
    sharpe: float
    objective_value: float
    objective_name: str
    constraints_passed: bool
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class RegimeAnalysisResult:
    placement: "pd.DataFrame"         # date × region
    velocity: "pd.DataFrame"
    regime: "pd.DataFrame"            # int 1..4
    latest_state: RegimeState
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class RegimeReturnResult:
    monthly_returns: "pd.DataFrame"   # date × asset
    regime_avg: "pd.DataFrame"        # regime × asset
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class TAAResult:
    saa_weights: "pd.Series"
    taa_weights: "pd.Series"
    tilts: "pd.Series"                # taa - saa, sum=0
    reasons: dict[str, str] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class UniverseResult:
    raw_count: int
    filtered_count: int
    products: list[ProductInfo] = field(default_factory=list)
    excluded: list[tuple[ProductInfo, str]] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProductSelectionResult:
    selected: "pd.DataFrame"          # asset_key, product_id, weight, role
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioResult:
    asset_weights: "pd.Series"        # asset_key → weight
    product_weights: "pd.DataFrame"   # product 단위
    portfolio_type: ProductType
    constraints_passed: bool
    diagnostics: dict[str, Any] = field(default_factory=dict)
