# TDF Engine Architecture

> **상태**: Phase A 완료 (패키지 골격 + 44 smoke test 통과)
> **버전**: draft v0.2 (Phase A 결과 반영)
> **최초 작성**: 2026-04-30
> **사전 문서**: `tdf_2060_tech_spec.md`, `source_review/*.md`
> **이어 작업하기**: `tdf_2060/HANDOFF.md`

본 문서는 TDF 엔진의 OOP 설계, Tool 단위 인터페이스, Repository 패턴, config-first 정책을 정의한다. 비즈니스 스펙은 `tdf_2060_tech_spec.md` 를 참고.

---

## 1. 설계 원칙

### 1.1 핵심 5원칙

1. **계산 ↔ 데이터 접근 분리** — Repository 인터페이스로 데이터 출처를 추상화한다. 계산 모듈은 File / DB 출처를 모른다.
2. **Tool 단위 독립 실행** — OptimizationTool, RegimeAnalysisTool 등이 각각 독립 실행 가능해야 한다. 한 Tool 의 실패가 다른 Tool 을 막지 않는다.
3. **Config-first** — 비즈니스 룰은 yaml 에 둔다. Python 코드는 룰을 받아 실행한다.
4. **Result Object 명시화** — pandas DataFrame 을 그대로 넘기지 않는다. 주요 결과는 dataclass 로 감싼다.
5. **Silent Fallback 금지** — 데이터가 없거나 매핑이 깨졌을 때 조용히 대체하지 않는다. warning + log + 명시 필드.

### 1.2 안티패턴

```
× 계산 함수 안에서 직접 SQLAlchemy/PyMySQL 호출
× 하드코딩된 자산명 ("미국 성장주") 을 코드에 박기
× DataFrame 의 컬럼명에 의존한 implicit interface
× pd.read_csv 의 결과를 그대로 다른 모듈에 넘기기
× 자산 누락 시 zeros 또는 평균값으로 silent fill
```

---

## 2. 패키지 구조 (Phase A 에서 생성 완료)

> Phase A 에서 아래 구조 + `tests/` 가 모두 생성되어 있다. `pytest tests/` 로 44 통과 확인.

```
tdf_engine/
  __init__.py
  domain/
    __init__.py
    models.py            # AssetClassInfo, ProductInfo, RegimeState, 등 dataclass
    enums.py             # Bucket, Regime, ProductType 등
  repositories/
    __init__.py
    interfaces.py        # Protocol 인터페이스
    file_repositories.py # File 구현체
    db_repositories.py   # DB 구현체 (placeholder)
  optimization/
    __init__.py
    cma.py               # CapitalMarketAssumption
    covariance.py        # CovarianceEstimator
    constraints.py       # ConstraintSet
    optimizer.py         # MVOOptimizer
    tool.py              # OptimizationTool
  regime/
    __init__.py
    placement.py
    velocity.py
    classifier.py        # ECIRegimeClassifier
    returns.py           # AssetReturnCalculator, RegimeReturnAnalyzer
    tool.py              # RegimeAnalysisTool, RegimeReturnTool
  taa/
    __init__.py
    policy.py            # RegimeTAAPolicy
    overlay.py           # TAAOverlayEngine
    tool.py              # TAAOverlayTool
  universe/
    __init__.py
    filters.py           # UniverseFilter
    classifier.py        # ProductClassifier (펀드명 → mvo_asset_class)
    tool.py              # UniverseTool
  selection/
    __init__.py
    scoring.py           # ProductScorer
    selector.py          # CoreSatelliteSelector
    tool.py              # ProductSelectionTool
  portfolio/
    __init__.py
    builder.py           # PortfolioBuilder
    validator.py         # PortfolioValidator
    rebalance.py         # RebalanceEngine
    tool.py              # PortfolioConstructionTool
  reporting/
    __init__.py
    formats.py           # 결과 직렬화
  tools/
    run_optimization.py
    run_regime.py
    run_regime_return.py
    run_universe.py
    build_portfolio.py
  config/
    tdf_2060.yaml
    asset_mapping.yaml
    universe_filter.yaml
    taa_policy.yaml
    optimization_constraints.yaml
  tests/
    test_covariance_estimator.py
    test_regime_classifier.py
    test_universe_filter.py
    test_portfolio_weight_sum.py
```

---

## 3. Domain 모델 (dataclass 정의)

### 3.1 AssetClassInfo

```python
@dataclass(frozen=True)
class AssetClassInfo:
    asset_key: str                  # "us_growth_equity"
    display_name: str               # "미국 성장주"
    source_name: str                # Asset_rt_vol 의 한글명
    ticker: str | None              # "M2US000G Index"
    bucket: Bucket                  # Equity | FixedIncome | Alternative | Currency
    flags: frozenset[str] = frozenset()  # {"risk_asset", "credit", "duration", "safe"}
    expected_return: float | None = None
    volatility: float | None = None
    db_dataset_id: int | None = None
    fallback_policy: FallbackPolicy = FallbackPolicy.ERROR_IF_MISSING
```

### 3.2 ProductInfo

```python
@dataclass(frozen=True)
class ProductInfo:
    product_id: str                 # 상품번호
    fund_code: str | None           # 제로인협회펀드코드
    name: str                       # 펀드명(Short)
    product_type: ProductType       # ETF | FUND
    kis_asset_class: str            # 대유형(KIS MP)
    sub_type: str                   # 소유형
    region: str | None
    theme: str | None
    manager: str                    # 운용사
    inception_date: date | None
    risk_grade: str | None
    quant_score: float | None
    quant_grade: str | None
    return_1y: float | None
    return_3y: float | None
    sharpe_1y: float | None
    aum: float | None               # 운용규모 (단위 정규화 필요)
    investment_limit: float | None  # 투자한도
    mvo_asset_class: str | None = None  # 매핑 후 부여
```

### 3.3 RegimeState

```python
@dataclass(frozen=True)
class RegimeState:
    as_of: date
    region: str                     # "G7", "KOR", "USA", ...
    placement: float
    velocity: float
    regime: int                     # 1..4
    label: str                      # "Expansion / Acceleration"

class Regime(IntEnum):
    EXPANSION = 1   # P>0, V>0
    RECOVERY = 2    # P<0, V>0
    SLOWDOWN = 3    # P<0, V<0
    DECELERATION = 4  # P>0, V<0
```

### 3.4 결과 객체

```python
@dataclass
class CapitalMarketAssumption:
    expected_returns: pd.Series     # asset_key → E[R]
    volatilities: pd.Series         # asset_key → σ
    correlation: pd.DataFrame       # asset_key × asset_key
    covariance: pd.DataFrame        # σ · C · σ

@dataclass
class OptimizationResult:
    weights: pd.Series
    expected_return: float
    volatility: float
    sharpe: float
    constraints_passed: bool
    diagnostics: dict[str, Any]

@dataclass
class RegimeAnalysisResult:
    placement: pd.DataFrame         # date × region
    velocity: pd.DataFrame
    regime: pd.DataFrame            # int 1..4
    latest_state: RegimeState

@dataclass
class RegimeReturnResult:
    monthly_returns: pd.DataFrame   # date × asset
    regime_avg: pd.DataFrame        # regime × asset
    diagnostics: dict[str, Any]

@dataclass
class TAAResult:
    saa_weights: pd.Series
    taa_weights: pd.Series
    tilts: pd.Series
    reasons: dict[str, str]
    diagnostics: dict[str, Any]

@dataclass
class UniverseResult:
    raw_count: int
    filtered_count: int
    products: list[ProductInfo]
    excluded: list[tuple[ProductInfo, str]]   # (product, reason)

@dataclass
class ProductSelectionResult:
    selected: pd.DataFrame
    diagnostics: dict[str, Any]

@dataclass
class PortfolioResult:
    asset_weights: pd.Series        # MVO asset_key → weight
    product_weights: pd.DataFrame   # product_id × weight + role
    portfolio_type: ProductType
    constraints_passed: bool
    diagnostics: dict[str, Any]
```

---

## 4. Repository 패턴

### 4.1 인터페이스

```python
# repositories/interfaces.py
class MarketDataRepository(Protocol):
    def load_asset_rt_vol(self) -> pd.DataFrame: ...
    def load_corr_matrix(self) -> pd.DataFrame: ...
    def load_regime_source(self) -> pd.DataFrame: ...
    def load_regime_return_source(self) -> pd.DataFrame: ...

class ProductRepository(Protocol):
    def load_etf_universe(self) -> pd.DataFrame: ...
    def load_fund_universe(self) -> pd.DataFrame: ...
```

### 4.2 File 구현체

```python
# repositories/file_repositories.py
class FileMarketDataRepository:
    def __init__(self, root: Path):
        self.root = root  # Advisory/

    def load_asset_rt_vol(self) -> pd.DataFrame:
        df = pd.read_csv(self.root / "Asset_rt_vol", sep="\t", encoding="utf-8")
        df["Asset Class"] = df["Asset Class"].ffill()
        df["σ"] = df["σ"].str.rstrip("%").astype(float) / 100
        df["E[R]"] = df["E[R]"].str.rstrip("%").astype(float) / 100
        return df.dropna(subset=["Name"])

    def load_corr_matrix(self) -> pd.DataFrame:
        df = pd.read_csv(self.root / "Corr_mat", sep="\t", encoding="utf-8", index_col=0)
        return df

    def load_regime_source(self) -> pd.DataFrame:
        # 1행은 수식 메모 → skiprows=1
        df = pd.read_csv(self.root / "regime_src", sep="\t", encoding="utf-8")
        df["Date"] = pd.to_datetime(df["Date"])
        return df.set_index("Date")

    def load_regime_return_source(self) -> pd.DataFrame:
        df = pd.read_csv(self.root / "regimeAnalysis_src", sep="\t", encoding="utf-8")
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")


class FileProductRepository:
    def __init__(self, root: Path):
        self.root = root

    def load_etf_universe(self) -> pd.DataFrame:
        return self._load("etf_list")

    def load_fund_universe(self) -> pd.DataFrame:
        return self._load("fund_list")

    def _load(self, name: str) -> pd.DataFrame:
        df = pd.read_csv(self.root / name, sep="\t", encoding="utf-8")
        # 정량평가 등 숫자 필드 정리: 천단위 콤마, trailing space 제거
        ...
        return df
```

### 4.3 DB 구현체 (placeholder)

```python
# repositories/db_repositories.py
class DbMarketDataRepository:
    """다음 단계에서 SCIP DB와 연결.
    interfaces.MarketDataRepository 구현체.
    """
    def __init__(self, engine: sqlalchemy.Engine):
        self.engine = engine

    def load_asset_rt_vol(self) -> pd.DataFrame:
        raise NotImplementedError("DB 매핑 확정 후 구현")

    def load_corr_matrix(self) -> pd.DataFrame:
        raise NotImplementedError(...)

    def load_regime_source(self) -> pd.DataFrame:
        raise NotImplementedError(...)

    def load_regime_return_source(self) -> pd.DataFrame:
        raise NotImplementedError(...)
```

---

## 5. Tool 단위 인터페이스

각 Tool 은 다음 공통 패턴을 가진다.

```python
class XxxTool:
    def __init__(self, config: XxxConfig, repo: XxxRepository):
        self.config = config
        self.repo = repo

    def run(self, **runtime_inputs) -> XxxResult:
        ...
```

### 5.1 OptimizationTool

```python
class OptimizationTool:
    def __init__(self,
                 config: OptimizationConfig,    # 자산 키 리스트, 제약, 목적함수
                 repo: MarketDataRepository):
        self.config = config
        self.repo = repo

    def run(self,
            initial_weights: pd.Series | None = None,
            scenario: str | None = None) -> OptimizationResult:
        # 1) repo 로부터 raw 로드
        # 2) CapitalMarketAssumption 빌드 (E[R], σ, Σ)
        # 3) ConstraintSet 빌드
        # 4) MVOOptimizer.optimize(cma, constraints, x0=initial_weights)
        # 5) 결과 dataclass 반환
        ...
```

### 5.2 RegimeAnalysisTool

```python
class RegimeAnalysisTool:
    def __init__(self,
                 config: RegimeConfig,          # window=12, region="G7", ...
                 repo: MarketDataRepository):
        ...

    def run(self) -> RegimeAnalysisResult:
        # 1) src 로드
        # 2) PlacementCalculator.calc(src, window=12)
        # 3) VelocityCalculator.calc(placement)
        # 4) ECIRegimeClassifier.classify(placement, velocity)
        # 5) latest_state 추출
        ...
```

### 5.3 RegimeReturnTool

```python
class RegimeReturnTool:
    def __init__(self, config: RegimeReturnConfig, repo: MarketDataRepository):
        ...

    def run(self, regime: pd.Series) -> RegimeReturnResult:
        # regime: 단일 region 의 월별 ECI 시계열
        ...
```

### 5.4 UniverseTool

```python
class UniverseTool:
    def __init__(self,
                 config: UniverseConfig,        # exclude_keywords, include_kis_classes 등
                 repo: ProductRepository,
                 product_type: ProductType):
        ...

    def run(self) -> UniverseResult:
        # 1) repo.load_etf_universe() / fund_universe()
        # 2) UniverseFilter 적용 (KIS MP 카테고리 + 키워드)
        # 3) ProductClassifier 가 mvo_asset_class 부여
        # 4) ProductInfo 리스트로 변환
        # 5) excluded 사유와 함께 반환
        ...
```

### 5.5 ProductSelectionTool

```python
class ProductSelectionTool:
    def __init__(self,
                 config: SelectionConfig,
                 universe_result: UniverseResult):
        ...

    def run(self,
            asset_weights: pd.Series,         # MVO asset_key → weight
            product_type: ProductType) -> ProductSelectionResult:
        # 1) asset 별 후보 그룹핑
        # 2) ProductScorer 가 각 후보에 점수 부여
        # 3) CoreSatelliteSelector 가 자산군별 Core/Satellite 선정
        # 4) 운용사 concentration 한도 검증
        ...
```

### 5.6 TAAOverlayTool

```python
class TAAOverlayTool:
    def __init__(self, config: TAAConfig):     # regime별 tilt 정책 yaml
        ...

    def run(self,
            saa_weights: pd.Series,
            regime: int) -> TAAResult:
        # 1) RegimeTAAPolicy 에서 regime 별 tilt 정책 조회
        # 2) TAAConstraint 적용 (equity bound, asset tilt cap)
        # 3) tilt 합 = 0 보정
        # 4) 사유 기록
        ...
```

### 5.7 PortfolioConstructionTool

```python
class PortfolioConstructionTool:
    def __init__(self,
                 optimization_tool: OptimizationTool,
                 regime_tool: RegimeAnalysisTool,
                 taa_tool: TAAOverlayTool,
                 universe_tool: UniverseTool,
                 selection_tool: ProductSelectionTool):
        ...

    def run(self, product_type: ProductType) -> PortfolioResult:
        opt = self.optimization_tool.run()
        regime = self.regime_tool.run()
        taa = self.taa_tool.run(opt.weights, regime.latest_state.regime)
        sel = self.selection_tool.run(taa.taa_weights, product_type)
        # validator + builder 호출
        ...
```

---

## 6. ETF형 / 펀드형 분리 전략

같은 `PortfolioConstructionTool` 인스턴스를 두 번 실행하지 않는다. 대신:

```python
def build_etf_portfolio(...) -> PortfolioResult:
    universe_tool = UniverseTool(config_etf, FileProductRepository(root), ProductType.ETF)
    selection_tool = ProductSelectionTool(config_etf_selection, universe_tool.run())
    return PortfolioConstructionTool(
        optimization_tool=opt_tool,
        regime_tool=regime_tool,
        taa_tool=taa_tool,
        universe_tool=universe_tool,
        selection_tool=selection_tool,
    ).run(ProductType.ETF)


def build_fund_portfolio(...) -> PortfolioResult:
    # 같은 opt_tool, regime_tool, taa_tool 재사용
    # universe_tool, selection_tool 만 펀드용 config 로 새로 만듦
    ...
```

> **공통**: OptimizationTool, RegimeAnalysisTool, RegimeReturnTool, TAAOverlayTool 인스턴스는 두 portfolio 가 공유.  
> **다름**: UniverseTool (ProductType, exclude_keywords), ProductSelectionTool (single max weight, manager concentration).

---

## 7. Config-First 설계

### 7.1 5개 yaml 파일 (`config/`)

```
tdf_2060.yaml                  # vintage 2060 의 SAA / TAA bound / equity 합 등
asset_mapping.yaml             # asset_key → display_name, ticker, db_dataset_id, fallback_policy
universe_filter.yaml           # 1차 카테고리 필터, 2차 키워드 필터, ETF/Fund 별 분리
taa_policy.yaml                # regime별 tilt 정책 + ECI 입력 region
optimization_constraints.yaml  # 자산별 lb/ub, region lb, ERR 옵션, 목적함수, solver 옵션
```

### 7.2 yaml 로드 / 검증

```python
class ConfigLoader:
    @staticmethod
    def load_tdf_config(path: Path) -> TdfConfig:
        ...
    @staticmethod
    def load_asset_mapping(path: Path) -> dict[str, AssetClassInfo]:
        ...
```

### 7.3 검증 시점

- 패키지 init 시 validate 호출 (자산 키 정합, 비중 합 = 1, 등).
- 각 Tool 의 `__init__` 에서 자기 config 의 정합성 한 번 더 확인.

---

## 8. 에러 / 경고 정책

### 8.1 silent fallback 금지 — 구체 예시

| 시나리오 | 잘못된 처리 | 올바른 처리 |
|---|---|---|
| us_treasury_30y 데이터 없음 | 미국 채권 10년으로 자동 대체 | 명시 에러 또는 명시 warning + diagnostics 에 기록 |
| 자산 ticker 매핑 실패 | weight 0 으로 두고 진행 | `MissingAssetError` 발생 |
| Corr_mat 비대칭 | 자동 대칭화 | warning + 결과 diagnostics 에 기록 |
| ETF 펀드명에 미확인 키워드 | 그냥 포함 | `ProductClassifier.UNKNOWN` 으로 분류 + excluded 에 사유 기록 |

### 8.2 logging

- 표준 logging 사용. 로그 레벨:
  - DEBUG: 각 row 단위 처리 detail
  - INFO: Tool 실행 완료, 자산별 weight, 후보 수
  - WARNING: fallback, missing data, 약한 위반
  - ERROR: 강한 위반 (필수 자산 누락, 합 ≠ 1)

---

## 9. 데이터 흐름 다이어그램 (텍스트)

```
[File / DB]
    │
    ▼
[MarketDataRepository] ─┐
                         ├─→ [OptimizationTool]   ──→ OptimizationResult (SAA)
                         ├─→ [RegimeAnalysisTool] ──→ RegimeAnalysisResult
                         └─→ [RegimeReturnTool]   ──→ RegimeReturnResult
                                                          │
                                                          ▼
                              [TAAOverlayTool] ←────── 위 3개의 결과 (SAA + Regime)
                                  │
                                  ▼
                              TAAResult (TAA-tilted weights)

[File / DB]
    │
    ▼
[ProductRepository] ──→ [UniverseTool] ──→ UniverseResult
                                              │
                                              ▼
                              [ProductSelectionTool]  ←── TAAResult.taa_weights
                                  │
                                  ▼
                              ProductSelectionResult
                                  │
                                  ▼
                           [PortfolioConstructionTool]
                                  │
                                  ▼
                              PortfolioResult
                                  │
                                  ▼
                              ETF형 / 펀드형 최종 산출
```

---

## 10. 향후 smoke test 계획

```
tests/test_covariance_estimator.py
  - σ + Corr_mat → Σ 가 symmetric 인지
  - Σ 의 모든 대각 원소 > 0 인지

tests/test_regime_classifier.py
  - (P=+0.1, V=+0.1) → 1
  - (P=+0.1, V=-0.1) → 4
  - (P=-0.1, V=+0.1) → 2
  - (P=-0.1, V=-0.1) → 3

tests/test_universe_filter.py
  - "한국투자ACE혼합형" → 제외
  - "한국투자KINDEX미국나스닥100" → 포함
  - "한국투자ACE미국30년국채액티브타겟커버드콜" → 제외

tests/test_portfolio_weight_sum.py
  - SAA 합 = 1.0 ± 1e-9
  - TAA 후 합 = 1.0
  - equity 합 ∈ [0.75, 0.85]

tests/test_hy_flag.py
  - us_high_yield 의 bucket = fixed_income
  - us_high_yield 의 flags 에 'risk_asset', 'credit' 포함
```

---

## 11. 구현하지 않을 것 (이번 단계 + 다음 단계 초기까지)

```
× UI / 대시보드
× production DB credential 작성
× 실제 SCIP DB 연결
× 자동 리밸런싱 스케줄러
× 글라이드패스 (vintage 별 SAA 변화) — 별도 모듈로 분리
× 백테스트 엔진 — 별도 프로젝트
× 위험기여도 (Risk Contribution) 분석 — 옵션
× CVaR / Black-Litterman 등 고급 최적화 — 옵션
```

---

## 12. 다음 단계 작업 분해 (코드 골격 생성 시)

### Phase A — 골격 only (1~2일 추정)

```
□ tdf_engine/ 패키지 디렉토리 생성
□ domain/models.py — dataclass 8개 정의 + Enum 4개
□ repositories/interfaces.py — Protocol 2개
□ repositories/file_repositories.py — File 구현체 2개 (raw 로드만)
□ optimization/{cma,covariance,constraints,optimizer,tool}.py — class skeleton (run 은 NotImplementedError 또는 minimal)
□ regime/*.py — 동일
□ taa/*.py — 동일
□ universe/*.py — 동일
□ selection/*.py — 동일
□ portfolio/*.py — 동일
□ config/*.yaml — config_draft 의 정본화
□ tools/*.py — entry point, __main__ 으로 실행 가능
□ tests/ — smoke test 5~10개
```

### Phase B — minimal end-to-end (1주 추정)

```
□ FileMarketDataRepository 동작
□ OptimizationTool 가 9개 자산군 SAA 산출
□ RegimeAnalysisTool 이 G7 ECI 산출
□ RegimeReturnTool 이 regimeAnalysis_rt 와 동등한 값 산출 (검증)
□ TAAOverlayTool 이 SAA → TAA 산출
□ UniverseTool + ProductSelectionTool 이 ETF형 후보 출력
□ PortfolioConstructionTool 이 최종 ETF 포트폴리오 산출
```

### Phase C — DB 연결 + 펀드형 (이후)

```
□ DbMarketDataRepository / DbProductRepository
□ 펀드형 universe_filter / selection 정책
□ 실데이터 검증
```
