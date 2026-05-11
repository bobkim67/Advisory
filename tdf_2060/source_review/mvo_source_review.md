# MVO Source Review

본 문서는 `Asset_rt_vol`, `Corr_mat`, `optimization_vba` 세 파일을 기반으로 TDF 2060 MVO 모듈의 데이터/로직 출발점을 정리한다.

---

## 1. Asset_rt_vol 구조 분석

### 1.1 raw 구조 요약

- 4개 대분류(Equity / Fixed Income / Alternative / Currency) 안에 **30개 자산**.
- 각 자산은 `(Asset Class, Ticker, Name, σ, E[R])` 5개 필드를 가진다.
- **Currency = USDKRW 단일 항목** (자산이 아니라 환율 그 자체로 들어가 있음 — MVO 자산군 후보 아님).

### 1.2 9개 MVO 자산군과 Asset_rt_vol 매칭

| MVO 자산군 (TDF 2060) | Asset_rt_vol Name | Ticker | E[R] | σ | bucket |
|---|---|---|---:|---:|---|
| 한국 주식 | 한국 주식 | M2KR INDEX | 5.72% | 25.6% | equity |
| 미국 성장주 | 미국 성장주 | M2US000G Index | 11.99% | 14.9% | equity |
| 미국 가치주 | 미국 가치주 | M2US000V Index | 8.25% | 13.1% | equity |
| 미국외 선진국 주식 | 미국외 선진국 주식 | TAD09XU Index | 6.85% | 13.0% | equity |
| 신흥국 주식 | 신흥국 주식 | M2EF Index | 7.46% | 15.3% | equity |
| 한국 종합채권 | 한국종합채권 | SPBKRCOT Index | 3.23% | 3.8% | fixed_income |
| 한국 국고채10년 | 한국국고채10년 | KPGB10YR Index | 3.27% | 8.0% | fixed_income |
| **미국 국고채30년** | **❌ 미존재** | — | — | — | fixed_income |
| 미국 하이일드 회사채 | 미국 하이일드 회사채 | LF98TRUU Index | 8.03% | 9.8% | fixed_income (risk asset) |

### 1.3 미국 국고채30년 존재 여부 — 명시 보고

```
미국 국고채30년 존재 여부: 없음

확인한 파일:
- Asset_rt_vol  : 미국 채권 항목은 (3M, 2Y, 5Y, 10Y, 종합 LBUSTRUU, 물가채 LBUTTRUU,
                  IG LUACTRUU, HY LF98TRUU, 미국외 글로벌 LG38TRUH, EM 달러 EMUSTRUU)
                  10종이며, 30Y 단독은 없음.
- Corr_mat       : Asset_rt_vol과 자산 라벨이 동일하므로 30Y 없음 (확인됨).
- regimeAnalysis_src: LBUSTRUU(종합), LBUTTRUU(물가채), LUACTRUU(IG), LF98TRUU(HY),
                     LG38TRUU(미국외), EMUSTRUU(EM달러), KISKALBI(한국채권 KIS) 만 존재.
                     30Y 단독 컬럼 없음.

직접 항목이 없을 경우 proxy 후보 (가까운 순):
  1. 미국 채권 10년 (USGG10YR Index) — duration ~9, σ 8.7%, E[R] 3.10%
  2. 미국 채권 종합 (LBUSTRUU Index) — duration ~6, σ 10.6%, E[R] 4.89%
  3. 별도 30Y proxy ticker 추가:
     - EDV ETF (Vanguard Extended Duration Treasury, duration ~24)
     - TLT ETF (iShares 20+ Year Treasury Bond, duration ~17)
     - USGG30YR Index (Bloomberg US 30Y yield curve)
     ⇒ 위 3종은 Bloomberg 또는 SCIP DB에서 별도 적재 필요.

권장 처리:
  - 1차 단계 (이번 설계): asset_mapping_draft.yaml 에서 us_treasury_30y 항목을
    db_dataset_id: null + fallback_policy: error_if_missing 으로 두고, 실제 실행 시
    데이터 없음을 명시 에러로 띄운다. 단순 fallback은 절대 silent 적용하지 않는다.
  - 2차 단계 (실데이터 연결): SCIP DB의 dataset 후보 확인 후 추가하거나, regimeAnalysis_src
    수준에서 별도 컬럼을 추가한다. proxy 사용이 불가피한 경우에는 반드시 warning + log + 보고서 노트.
```

### 1.4 자산명 분리 규칙 (display vs source)

향후 매핑 충돌을 막기 위해 다음 분리를 둔다.

| 키 | 사용처 | 예시 |
|---|---|---|
| `asset_key` | 코드 내부 식별자 (snake_case 영문) | `us_growth_equity` |
| `display_name` | 보고서/대시보드 표시 | "미국 성장주" |
| `source_name` | 원천 파일 컬럼명/라벨 | "미국 성장주" (Asset_rt_vol 한글) |
| `ticker` | Bloomberg ticker | "M2US000G Index" |
| `db_dataset_id` | 향후 SCIP back_dataset.id 연결 | (placeholder) |

---

## 2. Corr_mat 구조 분석

### 2.1 자산 정합성

- 행 라벨 / 열 라벨이 모두 한글 자산명. Asset_rt_vol의 한글 Name과 1:1 정합.
- 단, **Currency(미국 달러)는 미포함** → Corr_mat 자산 수 = 29.
- MVO 9개 자산군은 모두 Corr_mat 안에 존재 (단, 미국 국고채30년은 어차피 Asset_rt_vol에도 없음).

### 2.2 9개 자산군 부분 행렬 (initial sanity check)

| | 한국주식 | 미성장 | 미가치 | 선진국 | 신흥국 | 한채종 | 한국채10 | (미30) | HY |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 한국주식 | 1.00 | 0.22 | 0.15 | 0.43 | 0.64 | -0.07 | 0.17 | — | -0.20 |
| 미성장 | 0.22 | 1.00 | 0.78 | 0.75 | 0.53 | 0.09 | -0.10 | — | 0.61 |
| 미가치 | 0.15 | 0.78 | 1.00 | 0.80 | 0.48 | -0.02 | -0.16 | — | 0.60 |
| 선진국 | 0.43 | 0.75 | 0.80 | 1.00 | 0.77 | -0.03 | -0.15 | — | 0.53 |
| 신흥국 | 0.64 | 0.53 | 0.48 | 0.77 | 1.00 | -0.11 | -0.13 | — | 0.31 |
| 한채종 | -0.07 | 0.09 | -0.02 | -0.03 | -0.11 | 1.00 | 0.80 | — | 0.19 |
| 한국채10 | 0.17 | -0.10 | -0.16 | -0.15 | -0.13 | 0.80 | 1.00 | — | -0.18 |
| HY | -0.20 | 0.61 | 0.60 | 0.53 | 0.31 | 0.19 | -0.18 | — | 1.00 |

(Asset_rt_vol/Corr_mat에서 직접 발췌. 미국 국고채30년 "—" 는 자료 부재.)

### 2.3 관찰

- HY는 fixed income bucket이지만 **주식과의 상관 0.53~0.61** → `risk_asset` flag 부여 정당화됨.
- 한국 주식은 미국 주식과 상관 낮음 (0.15~0.22) → 분산 효과 큼.
- 한국 국고채10년은 한국 종합채권과 0.80 상관 → 둘을 동시에 모두 포함하면 redundancy 우려. 향후 둘 중 하나에 weight cap 또는 single-name limit 필요.

---

## 3. optimization_vba 분석

### 3.1 확정 사항

| 항목 | 값 |
|---|---|
| Solver Engine | GRG Nonlinear (Engine := 1) |
| Target Cell | $L$26 (Maximize, MaxMinVal := 1) |
| 변경 변수 | named range `rCurrWeight` |
| 외부 루프 | opt × eqlb × err × i (4중) |
| Warm Start | `rInitWeights = rCurrWeight.Value` 매 iteration |

### 3.2 외부 루프 의미

```
opt = 1 .. 1                   ← rCurrRepOption (1=Sum of minimum, 2=Regional Minimum)
eqlb = 1 .. 1                  ← rEAFELb/rEMLb 기준 비중 lower bound
                                  rEAFELb = eqlb * 0.1 * rEAFEWeight
                                  rEMLb   = eqlb * 0.1 * rEMWeight
err = 85 .. 85 step 5          ← rLimitEqRepRatio = err/100 (현재 0.85 고정)
i   = 1 .. nYrs                ← rCurrSN (시나리오/연도 인덱스, rSNs.Count 만큼)
```

> 즉 본 매크로는 `(rCurrRepOption, EAFE/EM 하한 강도, ERR 하한, 시나리오 i)` 4-축 grid를 도는 구조이며, 현재 코드 상태에서는 처음 3축이 단일 값으로 고정되어 있어 사실상 시나리오 루프 i 만 활성화됨.

### 3.3 named range 인벤토리

```
[옵션/제약 입력]
rCurrRepOption          - ERR 계산법 옵션 (1/2)
rTargetDuration         - 채권 sub-portfolio 타깃 듀레이션 (현재 비활성)
rEAFEWeight, rEMWeight  - EAFE/EM 기준 비중 (BM 비중)
rEAFELb,    rEMLb        - EAFE/EM 비중 lower bound
rLimitEqRepRatio        - Equity Replication Ratio 하한

[시나리오]
rSNs, rCurrSN           - 시나리오/연도 리스트 + 현재 인덱스

[최적화 변수/결과]
rInitWeights            - 초기값 (warm start 갱신)
rCurrWeight             - Solver의 변수 (자산별 비중)
rCurrOutput             - 한 시나리오 결과 (output row)
rOutputOrigin           - 결과 누적 영역의 좌상단

[로그]
rStartTime, rEndTime
```

### 3.4 미확정 사항 (Excel 셀 수식 안에 있음)

VBA 코드 자체에는 다음이 명시되지 않으며, **워크시트 셀 수식**으로 정의되어 있을 가능성이 높다.

1. **목적함수의 정확한 정의** (`$L$26` 의 수식)
   - Maximize 라는 점, ERR 옵션을 가진다는 점, EAFE/EM 비중을 명시 제어한다는 점 등에서
     **벤치마크 추종 + Equity Replication Ratio 제약 + 목적함수 (Sharpe / Utility / Excess Return)**
     계열로 추정됨. 정확한 식은 향후 Excel 원본 직접 확인 필요.
2. **제약조건 전체 목록**
   - 비음수 (w ≥ 0) 와 합 = 1 은 거의 확실.
   - 자산별 상하한 (특히 EAFE/EM 하한) 은 named range로 잡혀있음.
   - ERR ≥ rLimitEqRepRatio 는 명시.
   - 채권 듀레이션 타깃 (rTargetDuration) 은 현재 비활성이지만 모델에 존재.
3. **ERR 의 정의**
   - 옵션 1 "Sum of minimum": likely Σ_i min(w_i, b_i) — 자산별 BM과의 매수 가능 비중 합
   - 옵션 2 "Regional Minimum": 지역(미국/EAFE/EM 등) 단위 합산 후 min
   - 정확한 식은 시트 수식 직접 확인 필요.

### 3.5 Python (scipy.optimize) 이식 시 고려사항

| 항목 | 권장 처리 |
|---|---|
| Solver | `scipy.optimize.minimize(method="SLSQP")` 1차 후보, `trust-constr` 2차 |
| 변수 차원 | 9개 자산군이면 `w ∈ R^9`, sum=1 + bounds + ERR ≥ 0.85 |
| 등호 제약 | `{"type": "eq", "fun": lambda w: w.sum() - 1}` |
| 비음수 | bounds=[(0, max_w_i) for i] |
| 자산별 상하한 | bounds 또는 inequality로 |
| 지역 lower bound (EAFE/EM) | inequality `region_weight(w) - lb ≥ 0` |
| ERR 제약 | inequality callback |
| 채권 듀레이션 (활성화 시) | inequality `Σ d_i w_i^FI - target_dur = 0` 또는 \|·\| ≤ ε |
| Warm start | grid scan 시 직전 해를 다음 `x0` 로 사용 |
| 시나리오 grid | python `itertools.product(opt_options, eqlb_options, err_options)` 외부 루프 |
| 결과 저장 | `OptimizationResult` dataclass 리스트 → DataFrame 변환 |
| 재현성 | scipy 1.13+ 의 SLSQP는 결정적이지만, 여러 초기값 multi-start 권장 |

### 3.6 향후 코드 골격에서의 클래스 분담

| 클래스 | 역할 |
|---|---|
| `CapitalMarketAssumption` | E[R], σ 로딩 + 검증 (`Asset_rt_vol` source) |
| `CovarianceEstimator` | σ + Corr_mat → Σ 행렬 (`Σ = D · C · D`) |
| `ConstraintSet` | 자산별 bounds, region lower bounds, ERR 하한, sum=1 등을 통합 보관 |
| `MVOOptimizer` | scipy 호출, warm start 관리, 다중 시나리오 grid |
| `OptimizationTool` | 위를 묶어서 외부에서 한 번 호출하는 facade |

---

## 4. 9개 MVO 자산군 — 최종 매핑 표 (이번 단계 확정)

| asset_key | display_name | source_name (Asset_rt_vol) | ticker | bucket | risk_flag | E[R] | σ | regimeAnalysis_src 컬럼 |
|---|---|---|---|---|---|---:|---:|---|
| kr_equity | 한국 주식 | 한국 주식 | M2KR INDEX | equity | risk_asset | 5.72% | 25.6% | M2KR Index |
| us_growth_equity | 미국 성장주 | 미국 성장주 | M2US000G Index | equity | risk_asset | 11.99% | 14.9% | M2US000G Index |
| us_value_equity | 미국 가치주 | 미국 가치주 | M2US000V Index | equity | risk_asset | 8.25% | 13.1% | M2US000V Index |
| dm_ex_us_equity | 미국외 선진국 주식 | 미국외 선진국 주식 | TAD09XU Index | equity | risk_asset | 6.85% | 13.0% | M2WOU Index ⚠️ ticker 다름 |
| em_equity | 신흥국 주식 | 신흥국 주식 | M2EF Index | equity | risk_asset | 7.46% | 15.3% | M2EF Index |
| kr_aggregate_bond | 한국 종합채권 | 한국종합채권 | SPBKRCOT Index | fixed_income | safe | 3.23% | 3.8% | KISKALBI 또는 한국채권 ⚠️ |
| kr_treasury_10y | 한국 국고채10년 | 한국국고채10년 | KPGB10YR Index | fixed_income | safe | 3.27% | 8.0% | ❌ 컬럼 없음 |
| us_treasury_30y | 미국 국고채30년 | **부재** | (proxy) | fixed_income | safe | — | — | ❌ |
| us_high_yield | 미국 하이일드 회사채 | 미국 하이일드 회사채 | LF98TRUU Index | fixed_income | risk_asset, credit | 8.03% | 9.8% | LF98TRUU Index |

> ⚠️ 표시:
> - 미국외 선진국 주식: Asset_rt_vol 은 `TAD09XU Index`(MSCI EAFE 표준 IMI total return), regimeAnalysis_src 는 `M2WOU Index` (MSCI World ex US). 두 지수 모두 "미국외 선진국" 카테고리이지만 정확히 동일 인덱스는 아님 — 향후 매핑 시 어느 쪽을 정본으로 둘지 결정 필요.
> - 한국 종합채권: Asset_rt_vol 은 `SPBKRCOT Index`(S&P Korea 종합), regimeAnalysis_src 는 `KISKALBI Index` 또는 별도 한국채권 컬럼. 둘은 다른 산출 방법론.

---

## 5. 이번 분석에서 도출된 다음 단계 의사결정 포인트

1. **미국 국고채30년 데이터 소스 결정** — SCIP DB에 USGG30YR / TLT / EDV 등 어느 ticker를 추가할지 결정 필요. 사용자 측 결정 사항.
2. **EAFE 지수의 정본 결정** — TAD09XU vs M2WOU.
3. **한국 종합채권 정본 결정** — SPBKRCOT vs KISKALBI.
4. **목적함수 정본 결정** — Excel `$L$26` 수식 직접 확인 후 Python 이식.
5. **Equity Replication Ratio 정의 확정** — Sum of minimum vs Regional Minimum 의 정확한 식.
6. **시나리오 grid 의 의미** — `rSNs` 가 연도별 시나리오인지, 글라이드패스 단계인지 확인.

---

## 부록 — Asset_rt_vol 의 Risk-Return Sanity Check

| 자산군 | E[R] | σ | E[R]/σ |
|---|---:|---:|---:|
| 한국 주식 | 5.72% | 25.6% | 0.22 |
| 미국 성장주 | 11.99% | 14.9% | **0.81** |
| 미국 가치주 | 8.25% | 13.1% | 0.63 |
| 미국외 선진국 | 6.85% | 13.0% | 0.53 |
| 신흥국 주식 | 7.46% | 15.3% | 0.49 |
| 한국 종합채권 | 3.23% | 3.8% | 0.85 |
| 한국 국고채10년 | 3.27% | 8.0% | 0.41 |
| 미국 하이일드 | 8.03% | 9.8% | 0.82 |

- 미국 성장주의 risk-adjusted return 이 압도적으로 높게 잡혀 있음 (0.81). MVO 무제약 시 미국 성장주에 비중이 쏠릴 가능성이 큼 → 자산별/지역별 상한이 ConstraintSet 에서 반드시 필요.
- 한국 주식의 risk-adjusted return 이 매우 낮음 (0.22) — 단순 MVO 시 0% 해가 나올 가능성. 그래도 BM 추종/홈컨트리 바이어스 측면에서 lower bound 필요.
