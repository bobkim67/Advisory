# Source File Inventory

본 문서는 `C:/Users/user/Downloads/python/Advisory/` 루트에 업로드된 12개 텍스트형 추출본 + 2개 Excel 원본의 포맷, 구조, 역할을 정리한다. 이번 단계에서는 **읽기만** 수행했으며, 원본 파일 수정은 없다.

---

## 0. 공통 사항

- 모든 텍스트 추출본은 **탭(`\t`) 구분 텍스트 (TSV)** 이며, Windows 환경에서 Excel 시트 영역을 값복사한 결과로 보인다.
- 인코딩은 UTF-8 (BOM 없음)로 읽힌다 (한글 헤더 정상 표시).
- 일부 파일 첫 줄에 Excel 셀 수식이 그대로 들어있다 (예: `B14=Placement!B14-Placement!B13`). 이는 추출 의도를 보존한 것이며 데이터 row 가 아니다.
- 행/열 수는 헤더 + 빈 행 포함 raw count 이다.

---

## 1. Asset_rt_vol

| 항목 | 값 |
|---|---|
| 경로 | `Advisory/Asset_rt_vol` |
| 포맷 | TSV (탭 구분) |
| 인코딩 | UTF-8 |
| Row 수 | 32 (헤더 1 + 자산 30 + 빈줄 1) |
| Column 수 | 5 |
| 역할 | 자산군별 기대수익률(E[R])과 변동성(σ) 마스터 |

### 컬럼

| # | 컬럼명 | 설명 |
|---|---|---|
| 1 | Asset Class | 대분류 (Equity / Fixed Income / Alternative / Currency). merge cell 형태로 첫 행에만 값이 있고 이후 자산은 빈 셀로 이어짐 |
| 2 | Ticker | Bloomberg Ticker (예: M2WD Index, SPXT Index) |
| 3 | Name | 한글 자산명 (예: 글로벌 주식, 미국 성장주) |
| 4 | σ | 연환산 변동성 (예: `12.4%`) |
| 5 | E[R] | 연환산 기대수익률 (예: `8.68%`) |

### 특이사항

- σ, E[R]은 **`%` 부착된 문자열**이므로 파싱 시 strip + `/100` 변환 필요.
- Asset Class 컬럼이 sparse (빈 셀로 그룹 표시) — forward fill 필요.
- 마지막 row 32는 빈 row.

### 자산 30종 전수

```
Equity (10):
  글로벌 주식, 미국 주식, 미국 성장주, 미국 가치주, 미국 중형주,
  미국소형주, 미국외 선진국 주식, 신흥국 주식, 한국 주식, 호주 주식
Fixed Income (14):
  글로벌 채권, 미국 채권, 미국 채권 3개월, 미국 채권 2년, 미국 채권 5년,
  미국 채권 10년, 미국 물가채, 미국 투자등급 회사채, 미국 하이일드 회사채,
  미국외 글로벌채권, 신흥국 달러채권, 한국종합채권, 한국국고채3개월,
  한국국고채3년, 한국국고채10년
Alternative (5):
  원자재, 금, 미국 리츠, 미국외 리츠, 글로벌 인프라
Currency (1):
  미국 달러
```

---

## 2. Corr_mat

| 항목 | 값 |
|---|---|
| 경로 | `Advisory/Corr_mat` |
| 포맷 | TSV |
| 인코딩 | UTF-8 |
| Row 수 | 32 (헤더 1 + 30 자산 + 빈줄 1) |
| Column 수 | 30 (라벨 1 + 자산 29) |
| 역할 | 자산군 간 correlation matrix |

### 구조

- 좌상 셀은 빈칸. 1행은 column 라벨(자산명), 1열은 row 라벨(자산명).
- 대각선 = 1.0000 (확인됨), 대칭 (재확인 필요하나 sample 검증상 대칭).
- 자산 라벨은 한글명 (Asset_rt_vol과 동일 한글 표기).
- **Currency 자산(미국 달러, USDKRW)은 Corr_mat에 포함되지 않음** — Asset_rt_vol에는 30종, Corr_mat 자산은 29종.

### 특이사항

- 한국주식–미국채권 long bond 음의 상관 (-0.69), 한국주식–한국국고채10년 (+0.17 정도) 등 직관적.
- 데이터 누락(`NaN`/`null`)은 sample 범위 내 없음.

---

## 3. optimization_vba

| 항목 | 값 |
|---|---|
| 경로 | `Advisory/optimization_vba` |
| 포맷 | VBA 매크로 소스 (.bas 형태의 텍스트) |
| 인코딩 | UTF-8 |
| Line 수 | 약 96 |
| 역할 | Excel Solver를 호출하는 최적화 매크로 (`RunOptimizer` Sub) |

### 핵심 발견

- **Solver Engine**: `Engine:=1`, `EngineDesc:="GRG Nonlinear"`
- **Target Cell**: `$L$26`
- **MaxMinVal**: `1` → Maximize
- **변경 변수 (ByChange)**: named range `rCurrWeight`
- **반복 구조 (4중 loop)**:
  1. `opt = 1 To 1` — `rCurrRepOption` (Equity Replication Ratio 계산법: 1=Sum of minimum, 2=Regional Minimum)
  2. `eqlb = 1 To 1` — `rEAFELb`, `rEMLb` (EAFE/EM 하한 비중을 `rEAFEWeight × eqlb × 0.1` 로 설정)
  3. `err = 85 To 85 Step 5` — `rLimitEqRepRatio` 를 `err/100` 로 (현재 0.85 고정)
  4. `i = 1 To nYrs` — `rCurrSN` (연도/시나리오 인덱스, `rSNs.Count` 만큼)
- **Warm Start**: 매 iteration 후 `rInitWeights = rCurrWeight.Value` 갱신
- **결과 저장**: `rCurrOutput` 을 `rOutputOrigin` offset 에 paste-special values
- **추가 함수**: `ColMin(rInput)` — 각 열의 최솟값을 1×nCols 배열로 반환 (Equity Replication 계산용 보조)

### named range 목록 (코드에서 호출되는 것)

```
rStartTime, rEndTime
rCurrRepOption, rTargetDuration (주석으로 비활성)
rEAFEWeight, rEMWeight, rEAFELb, rEMLb
rLimitEqRepRatio
rSNs, rCurrSN
rInitWeights, rCurrWeight
rCurrOutput, rOutputOrigin
```

### Python 이식 시 주의 (선행 보고)

1. **목적함수 정의**가 VBA 안에 없음 → `$L$26` 셀의 워크시트 수식이 실제 objective. 이번 단계에서는 Excel 원본 셀을 직접 열어보지 않았으므로 **objective 정의는 미확인**. 보통 GRG + Maximize + 위험자산 비중 반복이라는 패턴은 Sharpe Ratio (E[R]^T w − rf) / sqrt(w^T Σ w) 또는 Utility (E[R]^T w − λ/2 · w^T Σ w) 계열이 일반적이지만, 본 매크로의 "Equity Replication Ratio" 키워드는 **벤치마크 추종형 또는 자산복제형 목적함수**일 가능성을 시사한다.
2. **제약조건도 VBA 외부**(Excel cell formula / named range constraint)에 있을 가능성이 높음. Solver 다이얼로그의 SolverAdd 호출이 코드에 없는 것으로 보아 **이전 세션에 저장된 Solver 모델**을 재사용한다고 가정해야 함.
3. **Equity Replication Ratio (ERR)** 의 두 옵션:
   - 옵션 1 "Sum of minimum": 자산별 매수가능 비중과 BM 비중의 min 합 (∑ min(w_i, b_i))
   - 옵션 2 "Regional Minimum": 지역(미국/EAFE/EM 등) 단위로 min 적용 후 합산
4. scipy.optimize 이식 시 권장:
   - solver: `SLSQP` (선형/비선형 제약 + 1차 미분만 필요) 또는 `trust-constr` (대규모/inequality 강건)
   - warm start: 직전 해를 `x0`로 그대로 전달
   - inequality 제약: `equity_replication_ratio(w) - 0.85 ≥ 0` 형태로 callback
   - 다중 시나리오 grid: opt × eqlb × err × i 의 outer for loop 그대로 유지하되 병렬화 가능

---

## 4. regime_src

| 항목 | 값 |
|---|---|
| 경로 | `Advisory/regime_src` |
| 포맷 | TSV |
| 인코딩 | UTF-8 |
| Row 수 | 64 (헤더 1 + 월별 61 + 빈 줄) |
| Column 수 | 23 (Date + 22 국가/지역) |
| 역할 | OECD CLI 기반 국가/지역별 경기지표 원천 데이터 (월말 또는 월초 시점) |

### 컬럼

```
Date, A5M, AUS, BRA, CAN, CHN, DEU, ESP, FRA, G20, G4E, G7,
GBR, IDN, IND, ITA, JPN, KOR, MEX, NAFTA, TUR, USA, ZAF
```

- A5M, G4E, G20, G7, NAFTA 같은 composite 지역 포함.
- 값은 100 근방의 OECD CLI 표준 (long-term trend = 100).
- 기간: 2021-02-01 ~ 2026-02-01 (월별, 13~14개월 forecast 포함된 형태).

---

## 5. regime_Placement

| 항목 | 값 |
|---|---|
| 경로 | `Advisory/regime_Placement` |
| 포맷 | TSV (헤더 row 위에 수식 메모 1줄) |
| Row 수 | 65 |
| Column 수 | 23 |
| 역할 | 12개월 trailing average 대비 위치 (= Src − rolling12m mean) |

### 핵심 발견

- 1번 row: `"B13=Src!B13- AVERAGE(Src!B2:B13)"` — **수식 정의 메타데이터**.
- 즉 Placement 산식은 t − 11 ~ t 의 12개월 평균 대비 차이.
- 첫 11개월(2021-02 ~ 2021-12)은 lookback 부족으로 빈 셀.
- 2022-01부터 값 발생.

---

## 6. regime_Velocity

| 항목 | 값 |
|---|---|
| 경로 | `Advisory/regime_Velocity` |
| 포맷 | TSV (헤더 위 수식 메모 포함) |
| Row 수 | 65 |
| Column 수 | 23 |
| 역할 | Placement의 1개월 차분 |

### 핵심 발견

- 1번 row: `"B14=Placement!B14-Placement!B13"` — Velocity = ΔPlacement.
- Placement보다 한 달 더 lookback 필요 → 첫 값은 2022-02부터.

---

## 7. regime_ECI

| 항목 | 값 |
|---|---|
| 경로 | `Advisory/regime_ECI` |
| 포맷 | TSV (헤더 위 수식 메모) |
| Row 수 | 65 |
| Column 수 | 23 |
| 역할 | 1~4 국면 분류 결과 |

### 핵심 발견

- 1번 row: `"B14=IF(Placement!B14>0, IF(Velocity!B14>0, 1, 4), IF(Velocity!B14>0, 2, 3))"`
- 즉 정확히:
  - Placement > 0, Velocity > 0 → 1 (확장/가속)
  - Placement > 0, Velocity < 0 → 4 (감속)
  - Placement < 0, Velocity > 0 → 2 (회복)
  - Placement < 0, Velocity < 0 → 3 (둔화/침체)
- 2022-02부터 값 발생.

---

## 8. regime_Dashboard

| 항목 | 값 |
|---|---|
| 경로 | `Advisory/regime_Dashboard` |
| 포맷 | TSV |
| Row 수 | 51 (헤더 1 + 50개월) |
| Column 수 | 11 |
| 역할 | 단일 합성 phase 시각화용 (개별 국가가 아닌 composite cycle position) |

### 컬럼

```
Index, Date, Displacement, Velocity, Adj. Radius, Angle, Angle(x Pi), Phase(R),
Displacement(N), Velocity(N), Phase(N)
```

- Index = regime_src의 행 번호 (13부터 시작).
- Date 는 한글 형식 (`2022년 2월`).
- `Phase(R)`, `Phase(N)` 는 각각 phase angle 기반(R)과 sign 기반(N) 분류로 보이며 둘 다 1~4 값.
- ECI 시트(국가별)와 다르게 **단일 시계열의 위상**만 추적 — 합성 지표(예: G7 또는 KOR composite) 기반일 가능성.

### 미확정

- `Adj. Radius` 가 어떤 정규화에서 산출되는지, `Angle` 이 어떻게 정의되는지는 source 시트 수식 미확인.
- 이번 설계에서는 **국가별 ECI** 만 핵심 입력으로 사용하고, Dashboard 는 시각화 보조로 분리.

---

## 9. regimeAnalysis_src

| 항목 | 값 |
|---|---|
| 경로 | `Advisory/regimeAnalysis_src` |
| 포맷 | TSV |
| Row 수 | 258 (헤더 1 + 월별 257) |
| Column 수 | 26 |
| 기간 | 2004-10-29 ~ 최신 (월말) |
| 역할 | 자산군별 월말 지수 레벨, regime 기간 평균 수익률 산출 input |

### 컬럼 (Bloomberg ticker 기준)

```
M2WD, M2US, NDX, M2US000G, M2US000V, M2WOU, M2EF, M2KR, GDDUAS,
LEGATRUU, LBUSTRUU, LBUTTRUU, LUACTRUU, LF98TRUU, LG38TRUU, EMUSTRUU,
KISKALBI, SPGSCITR, XAU, FNRETR, DWXRSN, SPGTINTR, USDKRW, KOCRD,
한국채권, 미국성장주레버리지
```

### 특이사항

- 마지막 두 컬럼 `한국채권`, `미국성장주레버리지`는 ticker 가 아닌 한글 라벨. 별도 계산값으로 추정.
- KISKALBI = KIS KALBI Index (한국 채권 종합).
- 미국 채권 long bond (30Y) 또는 EDV 같은 30년 zero-coupon ETF는 **미포함**.

---

## 10. regimeAnalysis_rt

| 항목 | 값 |
|---|---|
| 경로 | `Advisory/regimeAnalysis_rt` |
| 포맷 | TSV |
| Row 수 | 7 (헤더 + Regime 1/2/3/4 + Total + 빈줄) |
| Column 수 | 24 |
| 역할 | 국면(1/2/3/4)별 자산군 평균수익률 (annualized 또는 평균월수익률 기반의 누적치) |

### 발견

- 한글 자산명 사용. `미국나스닥` 컬럼이 두 번, `한국채권` 컬럼이 두 번 등장 — **컬럼명 중복 존재**.
- 국면별 risk asset 성과 차이 명확:
  - Regime 1: 한국주식 +42.0%, 미국성장주 +24.8%, HY +10.9% — 주식 강세
  - Regime 2: 한국주식 +21.0%, 신흥국 +20.1%, HY +16.5% — 위험자산 회복
  - Regime 3: 미국채권 +13.4%, 한국채권 +15.2%, 금 +17.0%, 주식 全 음수 — 안전자산 강세
  - Regime 4: 미국주식 +11.1%, 미국성장주 +13.7% — 후기 사이클 미국 우세
- 이 표는 TAA Overlay 정책의 출발점.

---

## 11. etf_list

| 항목 | 값 |
|---|---|
| 경로 | `Advisory/etf_list` |
| 포맷 | TSV |
| Row 수 | 933 (헤더 1 + ETF 932) |
| Column 수 | 38 |
| 역할 | ETF 유니버스 + 정량평가/위험등급/수익률/운용규모 등 |

### 주요 컬럼 (38개)

```
INDEX, 제로인협회펀드코드, 상품번호, 펀드명(Short),
대유형, 소유형, 대유형(KIS MP), 지역, 테마, 운용사, 설정일,
(지표)기간수익률, (지표)BM대비초과성과, (지표)자금유출입, (지표)수정샤프지수,
(지표)IR, (지표)표준편차, (지표)수수료,
(평가)기간수익률, (평가)BM대비초과성과, (평가)운용규모, (평가)자금유출입,
(평가)수정샤프지수, (평가)IR, (평가)표준편차, (평가)수수료,
정량평가, 정량평가등급, 위험등급,
수익률(1M), 수익률(3M), 수익률(6M), 수익률(9M), 수익률(1Y), 수익률(3Y), 수익률(설정후),
수정샤프(1Y), 운용규모, 운용규모등급, 자금유출입, 투자한도
```

### 카테고리 분포

| 대유형(KIS MP) | 개수 |
|---|---:|
| 국내주식 | 362 |
| 글로벌주식 | 252 |
| 국내채권 | 117 |
| 신흥국주식 | 65 |
| 해외혼합 | 48 |
| 해외채권 | 38 |
| 대체투자 | 37 |
| 국내혼합 | 13 |

### 키워드 매칭 (펀드명 기준 — 필터 후보)

| 키워드 | etf_list 매칭 |
|---|---:|
| TDF | 13 |
| TIF | 1 |
| TRF | 3 |
| 멀티에셋 | 2 |
| 혼합 | 54 |
| 자산배분 | 2 |
| 레버리지 | 0 |
| 인버스 | 0 |
| 커버드콜 | 50 |
| 타겟커버드콜 | 12 |
| 합성 | 75 |

### 특이사항

- 숫자 필드에 `,` 구분자 + 천단위 + 개당 trailing space 가 들어있음 (예: `718 `, `45 `). 파싱 시 `replace(",", "").strip()` 후 float 캐스팅 필요.
- `수익률(*)` 필드는 `%` 없이 숫자 (예: `9.2`).
- `대유형(KIS MP)` 가 가장 깨끗한 1차 필터 컬럼 → "국내주식/글로벌주식/신흥국주식/국내채권/해외채권" 만 1차 통과시키면 845개 → 추가 키워드 필터 필요.

---

## 12. fund_list

| 항목 | 값 |
|---|---|
| 경로 | `Advisory/fund_list` |
| 포맷 | TSV |
| Row 수 | 782 (헤더 1 + 펀드 781) |
| Column 수 | 38 (etf_list 와 동일 스키마) |
| 역할 | 펀드 유니버스 |

### 카테고리 분포

| 대유형(KIS MP) | 개수 |
|---|---:|
| 해외혼합 | 236 |
| 글로벌주식 | 148 |
| 국내주식 | 100 |
| 국내혼합 | 97 |
| 해외채권 | 71 |
| 신흥국주식 | 64 |
| 국내채권 | 45 |
| 대체투자 | 20 |

### 키워드 매칭

| 키워드 | fund_list 매칭 |
|---|---:|
| TDF | 131 |
| TIF | 5 |
| TRF | 1 |
| 멀티에셋 | 6 |
| 혼합 | 95 |
| 자산배분 | 22 |
| 레버리지 | 0 |
| 인버스 | 0 |
| 커버드콜 | 4 |
| 타겟커버드콜 | 0 |
| 합성 | 0 |

### 특이사항

- 펀드형은 **글로벌라이프싸이클 (소유형) = 131건** 으로 사실상 TDF.
- "대유형(KIS MP) 해외혼합 236, 국내혼합 97" 이 매우 큰 비중 차지 → **혼합형 카테고리만 제외해도 333건 감소**.
- TDF 131 + TIF 5 + 자산배분 22 + 멀티에셋 6 = 약 164건이 직접 제외 대상 (이름 기준).

---

## 필터 적용 시 1차 추정 후보군 잔존 수

엄밀한 row-by-row 적용은 다음 단계의 책임이지만, 키워드 단순 합산만 보면:

### ETF (출발 932)

- 1차 카테고리 필터: 대유형(KIS MP) ∈ {국내주식, 글로벌주식, 신흥국주식, 국내채권, 해외채권} → 약 834건
- 2차 키워드 제외: TDF 13 + TIF 1 + TRF 3 + 멀티에셋 2 + 혼합 54 (대유형 혼합과 일부 중복) + 자산배분 2 + 커버드콜 50 + 타겟커버드콜 12(커버드콜과 중복) + 합성 75 → 중복 제거 후 약 130건 제외
- **잔존 추정: ~700건**

### Fund (출발 781)

- 1차 카테고리 필터: 같은 5개 카테고리 → 428건
- 2차 키워드 제외: TDF 131 + 자산배분 22 + 멀티에셋 6 + 혼합 95 등 → 카테고리 필터 단계에서 이미 다수 제외됨
- **잔존 추정: ~400건**

> 정확한 잔존 수는 다음 단계 `UniverseTool` skeleton 구현 시 row-by-row 검증으로 산출.

---

## 13. ECI_Neo_202603.xlsx (Excel 원본)

| 항목 | 값 |
|---|---|
| 경로 | `Advisory/ECI_Neo_202603.xlsx` |
| 크기 | 1.65 MB |
| 역할 | Regime 분석의 원본 Excel 파일 (regime_src/Placement/Velocity/ECI/Dashboard 의 시트가 들어있는 워크북으로 추정) |

이번 단계에서는 **직접 열지 않음**. 텍스트형 추출본을 우선 사용한다.

---

## 14. RegimeAnalysis_2602.xlsx (Excel 원본)

| 항목 | 값 |
|---|---|
| 경로 | `Advisory/RegimeAnalysis_2602.xlsx` |
| 크기 | 1.69 MB |
| 역할 | Regime별 자산수익률 분석 원본 Excel (regimeAnalysis_src / regimeAnalysis_rt 의 출처) |

이번 단계에서는 **직접 열지 않음**. 텍스트형 추출본을 우선 사용한다.

---

## 부록 A — 파일별 row/col 요약 표

| 파일 | rows | cols | 핵심 컬럼 키 |
|---|---:|---:|---|
| Asset_rt_vol | 32 | 5 | Name, σ, E[R] |
| Corr_mat | 32 | 30 | (자산명) × (자산명) |
| optimization_vba | 96 | — (코드) | RunOptimizer Sub |
| regime_src | 64 | 23 | Date, 22개 국가/지역 |
| regime_Placement | 65 | 23 | Date, 22개 국가/지역 |
| regime_Velocity | 65 | 23 | Date, 22개 국가/지역 |
| regime_ECI | 65 | 23 | Date, 22개 국가/지역 |
| regime_Dashboard | 51 | 11 | Date, Phase(R), Phase(N) |
| regimeAnalysis_src | 258 | 26 | date, 26개 자산 ticker |
| regimeAnalysis_rt | 7 | 24 | Regime, 24개 자산 |
| etf_list | 933 | 38 | 대유형(KIS MP), 펀드명, 정량평가 |
| fund_list | 782 | 38 | 같음 |
