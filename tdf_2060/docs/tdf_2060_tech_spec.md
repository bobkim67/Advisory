# TDF 2060 Tech Spec

> **상태**: Phase A 완료 (코드 골격 + 44 smoke test 통과)
> **버전**: draft v0.2 (Phase A 결과 반영)
> **최초 작성**: 2026-04-30
> **소스 분석 근거**: `tdf_2060/source_review/source_file_inventory.md`, `mvo_source_review.md`, `regime_source_review.md`
> **이어 작업하기**: `tdf_2060/HANDOFF.md` 참조 (Phase B 진입점)

---

## 1. 목적

TDF 2060형 자산배분 포트폴리오를 Python 기반 OOP 엔진에서 산출한다. 이 문서는 **비즈니스 스펙** 을 정의하며, OOP/모듈 설계는 `tdf_engine_architecture.md` 에서 다룬다.

### 1.1 산출물 범위 (Phase A 완료 시점)

```
[설계 단계 — 완료]
docs/tdf_2060_tech_spec.md            ← 이 문서
docs/tdf_engine_architecture.md
source_review/*.md (3 파일)
config_draft/*.yaml (5 파일)

[Phase A — 완료]
tdf_engine/ 패키지 (41 .py + 5 yaml)
tests/ (10 test 파일, 44 통과)
CLAUDE.md, HANDOFF.md

[Phase B — 다음]
HANDOFF.md 참조. minimal end-to-end (CMA 빌드 → max_sharpe SAA → Regime → TAA → Universe).
```

### 1.2 엔진의 비즈니스 목표

```
[입력]  ETF/Fund 유니버스 + 자산군 CMA + Corr_mat + ECI Regime + 현재 사이클
[엔진]  MVO (SAA) + Regime Analysis + TAA Overlay + Product Selection
[출력]  TDF 2060 ETF형 포트폴리오 + TDF 2060 펀드형 포트폴리오 (자산군 + 상품 단위)
```

---

## 2. TDF 2060 의 정의

### 2.1 기본 자산배분 (SAA)

| 구분 | 비중 |
|---|---:|
| 주식 | 80% |
| 채권 | 20% |
| 합계 | 100% |

### 2.2 TAA 후 허용 범위

| 구분 | SAA | TAA 허용 범위 |
|---|---:|---:|
| 주식 | 80% | 75 ~ 85% |
| 채권 | 20% | 15 ~ 25% |

> ±5%p 단위로만 tilt 한다. SAA를 훼손하지 않으며, TAA 는 overlay 로만 적용한다.

### 2.3 적합 투자자

- 은퇴 시점 = 2060 (현재 기준 약 34년 long-horizon).
- 자산축적기 후반부 ~ 정점기. 위험자산 비중이 가장 높은 그룹.
- 본 문서는 단일 vintage(2060)에 대한 스펙이며, 다른 vintage의 글라이드패스는 별도 문서로 다룬다.

---

## 3. 투자 유니버스 원칙

### 3.1 핵심 원칙

> 본 프로젝트의 포트폴리오는 **자산배분형 상품을 편입하는 것이 아니라**, 주식형/채권형 상품을 조합하여 직접 자산배분형 포트폴리오를 만드는 것이다.

따라서 다음 두 그룹의 상품은 모두 제외한다.

#### 3.1.1 제외 대상 (포함 시 look-through 없이 익스포저 측정 불가)

```
- 혼합형 (주식+채권 혼합)
- 자산배분형 ETF / 펀드
- TDF / TIF / TRF
- 멀티에셋형
- 글로벌라이프싸이클 (= 사실상 TDF)
- 재간접 혼합형
```

#### 3.1.2 제외 대상 (구조적 / 파생 / 합성)

```
- 레버리지
- 인버스
- 커버드콜
- 타겟커버드콜
- 과도한 합성형 / 파생형 (옵션 매도 인컴, 변동성 매도 등)
```

### 3.2 포함 대상

```
- 순수 주식형 (국내/글로벌/신흥국)
- 순수 채권형 (국내/해외/하이일드)
- 단기채/현금성 (필요 시)
```

### 3.3 1차 카테고리 필터 (KIS MP 대유형 기준)

ETF/Fund 모두 다음 8개 KIS MP 대유형이 존재하며, 이 중 5개만 포함한다.

| 대유형(KIS MP) | 포함 여부 |
|---|:-:|
| 국내주식 | ✅ |
| 글로벌주식 | ✅ |
| 신흥국주식 | ✅ |
| 국내채권 | ✅ |
| 해외채권 | ✅ |
| 국내혼합 | ❌ |
| 해외혼합 | ❌ |
| 대체투자 | ❌ |

> 대체투자는 TDF 2060 SAA(80/20 주식/채권)에 직접 들어갈 자리가 없으므로 1차 단계에서는 제외. 향후 alternative bucket 추가 시 재검토.

### 3.4 2차 키워드 필터 (펀드명 기반)

1차 통과 후에도 다음 키워드를 펀드명에 포함하면 제외한다.

```
TDF, TIF, TRF, 멀티에셋, 자산배분, 혼합, 라이프싸이클,
레버리지, 인버스, 커버드콜, 타겟커버드콜, 합성
```

> 다만 `합성` 키워드는 ETF의 경우 신흥국/베트남 같은 합법적인 합성 ETF가 다수 있으므로, **합성 ETF 중 인덱스 추종형은 별도 화이트리스트로 관리**할 수 있다 (config 로 결정).

### 3.5 1차 추정 잔존 후보 (소스 분석 결과)

- ETF 출발 932 → 약 700건 잔존 추정.
- Fund 출발 781 → 약 400건 잔존 추정.
- 정확한 수는 다음 단계 `UniverseTool` skeleton 구현 시 row-by-row 검증.

---

## 4. MVO 자산군 9개

### 4.1 9개 자산군 정의 (이번 단계 확정)

#### Equity (5개, 합 80%)

| asset_key | display_name | source ticker | E[R] | σ |
|---|---|---|---:|---:|
| kr_equity | 한국 주식 | M2KR INDEX | 5.72% | 25.6% |
| us_growth_equity | 미국 성장주 | M2US000G Index | 11.99% | 14.9% |
| us_value_equity | 미국 가치주 | M2US000V Index | 8.25% | 13.1% |
| dm_ex_us_equity | 미국외 선진국 주식 | TAD09XU Index | 6.85% | 13.0% |
| em_equity | 신흥국 주식 | M2EF Index | 7.46% | 15.3% |

#### Fixed Income (4개, 합 20%)

| asset_key | display_name | source ticker | E[R] | σ | flags |
|---|---|---|---:|---:|---|
| kr_aggregate_bond | 한국 종합채권 | SPBKRCOT Index | 3.23% | 3.8% | safe |
| kr_treasury_10y | 한국 국고채10년 | KPGB10YR Index | 3.27% | 8.0% | safe, duration |
| us_treasury_30y | 미국 국고채30년 | **부재** (Asset_rt_vol에 없음) | — | — | safe, duration |
| us_high_yield | 미국 하이일드 회사채 | LF98TRUU Index | 8.03% | 9.8% | **risk_asset, credit** |

### 4.2 핵심 주의사항

1. **HY = fixed_income bucket + `risk_asset` + `credit` flag** — 단순 채권으로 취급하면 안 됨.
2. **us_treasury_30y 데이터 미존재** — Asset_rt_vol/Corr_mat/regimeAnalysis_src 어디에도 없음. 향후 SCIP DB 또는 별도 ticker 추가 필요. **silent fallback 금지**, 데이터 없으면 명시 에러 또는 명시 warning.
3. **dm_ex_us_equity 의 정본 ticker 미확정** — Asset_rt_vol = TAD09XU, regimeAnalysis_src = M2WOU. 둘은 다른 인덱스. 향후 결정 필요.
4. **kr_aggregate_bond 의 정본 ticker 미확정** — Asset_rt_vol = SPBKRCOT, regimeAnalysis_src = KISKALBI 또는 별도 한국채권 컬럼. 향후 결정 필요.

### 4.3 초기 기준비중 후보 (MVO 초기값 / 검증 baseline)

| asset_key | 비중 |
|---|---:|
| kr_equity | 10% |
| us_growth_equity | 30% |
| us_value_equity | 20% |
| dm_ex_us_equity | 12% |
| em_equity | 8% |
| **Equity 합** | **80%** |
| kr_aggregate_bond | 8% |
| kr_treasury_10y | 4% |
| us_treasury_30y | 5% |
| us_high_yield | 3% |
| **Fixed Income 합** | **20%** |

---

## 5. MVO 설계

### 5.1 입력

```
CMA (Capital Market Assumptions):
  - 9개 자산군 × E[R] 벡터
  - 9개 자산군 × σ 벡터
  - 9 × 9 correlation matrix → 9 × 9 covariance matrix

Constraints:
  - sum(w) = 1
  - 0 ≤ w_i ≤ max_w_i (자산별)
  - bucket constraints: equity 합 ∈ [0.75, 0.85], fixed income 합 ∈ [0.15, 0.25]
  - region lower bound (옵션): EAFE/EM 하한 비중
  - HY 단독 cap (옵션, risk_asset 추가 익스포저 제어용)

Initial weights:
  - 4.3 의 기준비중 후보 또는 직전 시나리오 해 (warm start)
```

### 5.2 목적함수 — 미확정

`optimization_vba` 분석 결과, 본 매크로의 목적함수 (`$L$26` 셀의 수식) 는 VBA 외부에 있으며 직접 확인되지 않았다. Maximize 라는 점, Equity Replication Ratio 옵션 / 하한이 있다는 점 등에서 다음 후보 중 하나로 추정된다.

| 후보 | 식 | 평가 |
|---|---|---|
| Sharpe Ratio | (μᵀw − r_f) / √(wᵀΣw) | TDF 일반적 목적함수 |
| Mean-Variance Utility | μᵀw − (λ/2)·wᵀΣw | risk aversion 명시 |
| Excess Return vs BM | μᵀw − μᵀb | BM 추종형 |
| Sortino / CVaR | downside risk 기반 | 본 매크로엔 잘 안 맞음 |

### 5.3 ERR (Equity Replication Ratio) 제약

- `optimization_vba` 의 `rLimitEqRepRatio` (현재 0.85 고정) 가 ERR 의 하한 제약.
- ERR 정의 옵션:
  - 옵션 1 "Sum of minimum": Σᵢ min(wᵢ, bᵢ) — 자산별 BM 비중과 매수가능 비중의 min 합
  - 옵션 2 "Regional Minimum": 지역(미국/EAFE/EM 등) 단위 합산 후 min
- **이번 설계 단계에서는 옵션 1 을 default 로 두되, 옵션 2 도 config 로 선택 가능하게 둔다.**

### 5.4 Solver 이식

| Excel | Python |
|---|---|
| GRG Nonlinear | scipy.optimize.minimize(method="SLSQP") |
| named range rCurrWeight | numpy array `w ∈ R^9` |
| Solver constraint cells | `constraints` 리스트 (eq/ineq) |
| Warm start (`rInitWeights = rCurrWeight.Value`) | 직전 해를 다음 `x0` 에 전달 |
| 외부 4중 루프 | `itertools.product` |

### 5.5 출력

```python
@dataclass
class OptimizationResult:
    weights: pd.Series              # asset_key → weight
    expected_return: float
    volatility: float
    sharpe: float
    constraints_passed: bool
    diagnostics: dict[str, Any]     # ERR, region weights, solver iter, etc.
```

---

## 6. Regime Analysis 설계

### 6.1 산식 (이미 확인 완료)

```
Placement_t = Src_t - mean(Src_{t-11..t})
Velocity_t  = Placement_t - Placement_{t-1}

Regime = 1 if (P>0 ∧ V>0)
       = 4 if (P>0 ∧ V<0)
       = 2 if (P<0 ∧ V>0)
       = 3 if (P<0 ∧ V<0)
```

### 6.2 입력 시계열

- `regime_src` 의 22개 국가/지역 OECD CLI 기반 지수.
- 월별. 2021-02 ~ 최신.

### 6.3 ECI 입력 region 결정

- 이번 설계 단계 default: **G7 또는 G20 composite**.
- config 로 변경 가능 (KOR / USA / per_asset_region 등).

### 6.4 Regime별 자산수익률 (regimeAnalysis_rt)

- 입력: `regimeAnalysis_src` (월말 지수 레벨 24+종) + 동일 월의 ECI.
- 계산: `r_t = level_t / level_{t-1} − 1` → group by regime → mean.
- 출력: `pd.DataFrame[regime × asset]` 평균수익률 표.

### 6.5 검증 — regimeAnalysis_rt 의 패턴

| Regime | 위험자산 평균 | 안전자산 평균 | 정책 시사 |
|---:|---:|---:|---|
| 1 (확장) | 매우 강세 | 약세 | risk-on (equity overweight) |
| 2 (회복) | 강세 | 약세~중립 | risk-on (equity overweight) |
| 3 (침체) | 매우 약세 | 강세 | risk-off (bond + gold overweight) |
| 4 (감속) | 미국 우세 / 신흥국 약세 | 중립 | 미국 선진국 우세 |

---

## 7. TAA Overlay 설계

### 7.1 핵심 원칙

1. **TAA 는 SAA 를 훼손하지 않는다.** 80/20 → 75/25 ~ 85/15 범위 내에서만 조정.
2. **자산군별 tilt 폭은 ±3%p 이내** (config 로 조정 가능).
3. **tilt 의 합 = 0** (자산군 rebalancing, cash neutral).
4. **HY 는 risk_asset 으로 취급** — Regime 1/2 에서 +, Regime 3 에서 −.
5. **사유 (reason) 필수 출력** — 어떤 regime, 어떤 자산이 어떻게 조정되었는지 문자열 기록.

### 7.2 Regime 별 tilt 정책 초안

> 본 표는 regimeAnalysis_rt 의 부호/크기에서 단순 도출한 초안. 운영 적용 전 백테스트 필요.

| Regime | Equity tilt | Bond tilt | 강조 자산군 | 약화 자산군 |
|---|---:|---:|---|---|
| 1 (확장) | +5%p | −5%p | em_equity, kr_equity, us_high_yield | kr_treasury_10y, us_treasury_30y |
| 2 (회복) | +3%p | −3%p | em_equity, us_high_yield | kr_aggregate_bond, kr_treasury_10y |
| 3 (침체) | −5%p | +5%p | us_treasury_30y, kr_aggregate_bond | kr_equity, em_equity, us_high_yield |
| 4 (감속) | 0~+1%p | 0~−1%p | us_growth_equity, us_value_equity, dm_ex_us_equity | em_equity, kr_equity |

### 7.3 출력

```python
@dataclass
class TAAResult:
    saa_weights: pd.Series          # 변경 전
    taa_weights: pd.Series          # 변경 후
    tilts: pd.Series                # 자산별 변동분 (sum=0)
    reasons: dict[str, str]         # asset_key → 사유 텍스트
    diagnostics: dict[str, Any]     # regime, equity_total, bond_total, bound check
```

---

## 8. Product Selection 설계

### 8.1 두 가지 포트폴리오 타입

| 타입 | 입력 유니버스 | 같은 점 | 다른 점 |
|---|---|---|---|
| ETF형 | etf_list | OptimizationTool, RegimeAnalysisTool, TAAOverlayTool 동일 | ProductRepository, UniverseFilter, ProductScorer 의 기준 |
| 펀드형 | fund_list | (위와 같음) | (위와 같음) |

### 8.2 정책 차이 표

| 항목 | ETF형 | 펀드형 |
|---|---|---|
| SAA / MVO | 동일 | 동일 |
| TAA Overlay | 동일 | 동일 |
| 상품 유니버스 | ETF만 | 펀드만 |
| 상품 선정 기준 | 비용, 추적성, 유동성 중시 | 정량평가, 운용규모, 성과 안정성 중시 |
| 단일 상품 max weight | 낮게 (예: 20%) | 상대적으로 높게 (예: 30%) |
| 운용사 concentration | 상대적으로 완화 | 제한 필요 (예: 60% 이내) → 펀드형은 50% |
| 상품 수 | 다소 많아도 가능 | 너무 많으면 관리 어려움 |

### 8.3 상품 매핑 룰 초안 (MVO 자산군 → 상품)

| MVO 자산군 | 상품 후보 필터 (펀드명 키워드) | 추가 조건 |
|---|---|---|
| kr_equity | KOSPI, KOSPI200, 국내, 코스피, 한국 | 소유형: 일반주식/K200인덱스/배당주식/중소형주식 |
| us_growth_equity | 미국, 성장, Growth, 나스닥, NASDAQ, 대형성장 | 지역: 북미/미국, 소유형: 북미주식 |
| us_value_equity | 미국 + 가치/Value/배당 | 지역: 북미/미국 |
| dm_ex_us_equity | 선진국, 미국제외, ex US, EAFE, 유럽, 일본 | 지역: 글로벌/유럽/일본 |
| em_equity | 신흥국, Emerging, EM, 중국, 인도, 베트남 | 소유형: 중국/인도/베트남/신흥국 |
| kr_aggregate_bond | 국내, 종합, 일반채권 | 대유형(KIS MP) = 국내채권 |
| kr_treasury_10y | 국고채10년, 국채10년, 장기국채 | |
| us_treasury_30y | 미국채30년, 미 국채30년, Treasury 30 | (현재 후보 매우 적음) |
| us_high_yield | 하이일드, HY, High Yield | |

향후 보완: 상품 마스터에 `mvo_asset_class` 컬럼을 부여 (DB 또는 별도 매핑 테이블).

### 8.4 Core-Satellite 구조 (초안)

각 MVO 자산군 안에서 상품을 선정할 때:

- **Core (60~80%)**: 광범위 베타 노출 인덱스 추종형. 비용/추적성 중심.
- **Satellite (20~40%)**: 스타일/액티브/테마. 정량평가 등급 중심.
- 두 비중은 자산군별로 config 로 조정.

### 8.5 출력

```python
@dataclass
class ProductSelectionResult:
    products: pd.DataFrame   # asset_key, product_id, fund_code, name, weight, role(core/satellite)
    diagnostics: dict[str, Any]   # per-asset cover ratio, per-manager concentration
```

---

## 9. 향후 DB 연결 전환 방식

### 9.1 현재 단계 — File-based

- Asset_rt_vol, Corr_mat, regime_src, regimeAnalysis_src, etf_list, fund_list 모두 파일에서 직접 로드.
- `FileMarketDataRepository`, `FileProductRepository` 가 그 역할을 담당 (다음 단계 코드 골격에서 만들 클래스).

### 9.2 다음 단계 — DB 연결

- `DbMarketDataRepository`, `DbProductRepository` 구현체 추가.
- 매핑 정보:
  - 자산 ticker ↔ SCIP `back_dataset.id` 또는 ISIN
  - 펀드/ETF 코드 ↔ dt 또는 cream DB
- `Repository` 인터페이스는 동일하므로, 계산 모듈은 무변경.

### 9.3 매핑 placeholder

`config_draft/asset_mapping_draft.yaml` 에서 각 자산군에 `db_dataset_id: null` 로 placeholder 를 둠. 실제 DB 매핑은 사용자가 결정 후 채움.

---

## 10. 다음 단계 구현 계획

### 10.1 Step 1 (코드 골격)

```
tdf_engine/
  domain/models.py         ← AssetClassInfo, ProductInfo 등 dataclass
  repositories/interfaces.py   ← Protocol 인터페이스
  repositories/file_repositories.py  ← 1차 File 구현체
  repositories/db_repositories.py    ← placeholder
  optimization/{cma,covariance,constraints,optimizer,tool}.py
  regime/{placement,velocity,classifier,returns,tool}.py
  taa/{policy,overlay,tool}.py
  universe/{filters,classifier,tool}.py
  selection/{scoring,selector,tool}.py
  portfolio/{builder,validator,rebalance}.py
  config/*.yaml            ← config_draft 의 정본화
  tools/*.py               ← Tool 단위 실행 entry point
  tests/*.py               ← smoke test
```

### 10.2 Step 2 (실데이터 검증)

- File 기반 1차 동작.
- 9개 자산군 전체 데이터 정합 (특히 us_treasury_30y, dm_ex_us_equity 정본 결정).

### 10.3 Step 3 (DB 연결)

- DbRepository 구현.
- File ↔ DB 결과 동등성 검증.

### 10.4 향후 smoke test 후보

```
- covariance matrix가 symmetric인지 확인
- regime sign 조합별 1/2/3/4 분류 확인
- UniverseFilter 가 혼합형/TDF/레버리지/커버드콜 제외하는지 확인
- 최종 포트폴리오 비중 합계가 100%인지 확인
- HY 가 fixed_income 이면서 risk_asset flag 를 갖는지 확인
- TAA 후 equity 합이 [0.75, 0.85] 안에 있는지 확인
- ProductScorer 가 운용사 concentration 한도를 위반하는 case 를 검출하는지 확인
```

---

## 11. 미확정 / 리스크

| # | 항목 | 영향 | 대응 |
|---|---|---|---|
| 1 | 미국 국고채30년 데이터 부재 | MVO 9개 자산군 중 1개 누락 | DB ticker 추가 또는 proxy 명시 사용 |
| 2 | optimization_vba 의 목적함수 정의 미확정 | MVO 결과 재현성 검증 불가 | Excel 원본 직접 열어 `$L$26` 수식 확인 |
| 3 | ERR 정의 (옵션 1 vs 옵션 2) 미확정 | 제약식 차이 | Excel 원본 셀 수식 직접 확인 |
| 4 | dm_ex_us_equity 정본 ticker 미확정 | 분석 vs 운용 데이터 불일치 가능 | 사용자 결정 |
| 5 | kr_aggregate_bond 정본 ticker 미확정 | 위와 같음 | 사용자 결정 |
| 6 | ECI 입력 region (KOR/USA/G7/G20) 미확정 | TAA 의 입력 결정 | config default 후 백테스트로 결정 |
| 7 | TAA tilt 폭 (±3~5%p) 미검증 | TAA 수익 기여도 미정 | 백테스트로 결정 |
| 8 | 펀드형의 글로벌라이프싸이클 131건 처리 | 사실상 TDF 이므로 제외해야 함 | 2차 키워드 필터에 포함 |
| 9 | 합성 ETF 75건의 포함 여부 | EM/베트남 등 합법적 합성 ETF 다수 | 화이트리스트 정책 결정 필요 |
| 10 | 단일 운용사 concentration 한도 | 펀드형은 한국투자신탁운용 비중이 클 수 있음 | 정책 초안 50% 후 백테스트 |
