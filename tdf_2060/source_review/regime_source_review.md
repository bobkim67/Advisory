# Regime Source Review

본 문서는 `regime_src`, `regime_Placement`, `regime_Velocity`, `regime_ECI`, `regime_Dashboard`, `regimeAnalysis_src`, `regimeAnalysis_rt` 7개 파일을 기반으로 Regime 기반 TAA 모듈의 데이터/로직 출발점을 정리한다.

> **Operator confirmation (2026-05-08, D-08 / D-09 closure)**:
> - `RegimeAnalysis_2602.xlsx` / `ECI_Neo_202603.xlsx` (DRM 보호) 내용 = 위 7개 file 의 **결합물**. 추가 정보 없음.
> - `regimeAnalysis_rt` = **파일 자체가 canonical definition**. 별도 definition 자료 없음.
> - DRM 보호 xlsx 3건은 **영구 해제 불가** → SAA / TAA / Final weights 1:1 parity 검증 영구 waived (`closed_with_permanent_limitation`).
> - 본 7개 file 이 정본. 후속 작업은 본 file 만 참조하면 됨.

---

## 1. Regime 산식 — 추출본 메타데이터에서 확인된 식

각 파일의 1번 row에는 시트 셀 수식이 보존되어 있다.

| 파일 | 헤더 위 메모 | 의미 |
|---|---|---|
| `regime_Placement` | `B13=Src!B13- AVERAGE(Src!B2:B13)` | Placement_t = Src_t − AVG(Src_{t-11..t}) |
| `regime_Velocity` | `B14=Placement!B14-Placement!B13` | Velocity_t = Placement_t − Placement_{t-1} |
| `regime_ECI` | `B14=IF(Placement!B14>0, IF(Velocity!B14>0, 1, 4), IF(Velocity!B14>0, 2, 3))` | ECI 1~4 분류 |

---

## 2. 산식이 사용자 spec과 일치하는지

**일치 — 100% 동일.**

작업지시서 / CLAUDE.md 상의 정의:

```
Placement_t = Src_t - Average(Src_{t-11} ... Src_t)
Velocity_t  = Placement_t - Placement_{t-1}

IF(Placement > 0,
   IF(Velocity > 0, 1, 4),
   IF(Velocity > 0, 2, 3))
```

추출본 메타데이터에서 확인된 정의:

```
Placement: B13 = Src!B13 - AVERAGE(Src!B2:B13)
           → Src 의 12개월 trailing window 평균 대비 (Src!B2..B13 = 12행)
Velocity:  B14 = Placement!B14 - Placement!B13
           → 1개월 차분
ECI:       정확히 동일 IF 중첩
```

⇒ **양식과 시트 산식이 완전히 일치**. Python 이식 시 다음과 같이 표현 가능:

```python
def placement(src: pd.Series, window: int = 12) -> pd.Series:
    return src - src.rolling(window).mean()

def velocity(placement: pd.Series) -> pd.Series:
    return placement.diff(1)

def classify_eci(p: float, v: float) -> int:
    if p > 0:
        return 1 if v > 0 else 4
    else:
        return 2 if v > 0 else 3
```

> **주의**: rolling window 의 "포함 시점" 차이.  
> Excel `AVERAGE(Src!B2:B13)` 는 12개의 셀 (B2~B13 inclusive). t=B13 시점에서 lookback 11개월 + 당월 = 12개월을 포함한다. pandas `Series.rolling(window=12).mean()` 도 동일하게 t를 포함한 직전 12개월 평균이므로 산식이 1:1 매칭된다.

---

## 3. regime_Dashboard 와 ECI 의 관계

### 3.1 구조 차이

| 항목 | regime_ECI | regime_Dashboard |
|---|---|---|
| 시계열 차원 | 22개 국가/지역 별 ECI(1~4) | 단일 합성 위상 |
| Date 형식 | "2022-02-01" 등 ISO | "2022년 2월" 한글 |
| 산출 방식 | Placement/Velocity 부호 조합 | Phase angle 기반 (Adj. Radius, Angle) + sign 기반 |
| 결과 컬럼 | 22개 정수 (1~4) | Phase(R) 정수 + Phase(N) 정수 |

### 3.2 Dashboard 의 추가 컬럼

```
Index, Date, Displacement, Velocity, Adj. Radius, Angle, Angle(x Pi),
Phase(R), Displacement(N), Velocity(N), Phase(N)
```

- `Displacement`, `Velocity`: 단일 합성 시계열의 placement/velocity 값. 어떤 국가/composite 인지는 추출본만으로는 미확인 (한국 또는 G7 composite 가능성).
- `Adj. Radius`, `Angle`: phase plane (Placement, Velocity) 위에서 점의 극좌표 변환.
- `Angle(x Pi)`: angle 을 π 단위로 정규화.
- `Phase(R)`: angle 기반 1~4 분류 (예: 0~π/2 → 1, π/2~π → 2 등).
- `Phase(N)`: sign 기반 분류 (정확히 ECI 식과 동일).

### 3.3 결론

- **이번 설계에서는 ECI(국가별 1~4 분류)가 1차 source of truth**. Dashboard 는 시각화/검증 보조로만 사용한다.
- TAA 정책 입력은 단일 "현재 국면(1/2/3/4)" 이며, 어느 국가/composite 의 ECI를 기준으로 할지는 별도 결정 필요 (후보: KOR, USA, G7).

---

## 4. regimeAnalysis_src → regimeAnalysis_rt 계산 흐름

### 4.1 src 의 구조

```
date | M2WD | M2US | NDX | M2US000G | M2US000V | M2WOU | M2EF | M2KR | GDDUAS |
       LEGATRUU | LBUSTRUU | LBUTTRUU | LUACTRUU | LF98TRUU | LG38TRUU | EMUSTRUU |
       KISKALBI | SPGSCITR | XAU | FNRETR | DWXRSN | SPGTINTR | USDKRW | KOCRD |
       한국채권 | 미국성장주레버리지
```

월말 지수 레벨. 2004-10 ~ 최신.

### 4.2 rt 의 구조 (재구성된 가공본)

```
Regime  | 24개 자산 평균수익률 (Regime 1/2/3/4 + Total)
```

### 4.3 추정되는 계산 흐름

```
Step 1. regimeAnalysis_src 로부터 월간 수익률 계산
        r_t = level_t / level_{t-1} - 1   (단순 수익률 또는 log)

Step 2. ECI(국가/composite 단위) 결과를 동일 월에 join
        e_t ∈ {1, 2, 3, 4}

Step 3. Regime 별 그룹핑 후 평균
        avg_return[regime, asset] = mean( r_t | e_t == regime )

Step 4. Total 행 = 전체 기간 평균
```

regimeAnalysis_rt 의 표 (rounded):

| Regime | 글로벌주식 | 미국주식 | 미국성장주 | 한국주식 | 미국채권 | 한국채권(KIS) | 금 | HY |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 23.9% | 24.7% | 24.8% | 42.0% | -0.8% | -0.3% | 16.2% | 10.9% |
| 2 | 13.9% | 13.3% | 19.3% | 21.0% | 5.2% | 1.7% | 14.4% | 16.5% |
| 3 | -5.0% | 0.4% | 0.4% | -17.4% | 13.4% | 15.2% | 17.0% | 1.5% |
| 4 | 10.7% | 11.1% | 13.7% | 10.8% | 2.2% | -0.1% | 10.8% | 4.6% |

> 단위가 % 이고 숫자 크기로 보아 **연율화된 평균** 이거나 **regime 동안 누적된 평균월수익률 × 12** 로 추정.

### 4.4 중복 컬럼 이슈

- regimeAnalysis_rt 에 `미국나스닥` 컬럼이 두 번, `한국채권` 컬럼이 두 번 등장.
- 두 컬럼의 값이 다른 것으로 보아 **다른 계산법(예: 환헤지 vs 비헤지, 또는 단리 vs 복리)** 일 가능성.
- 향후 적재 시 컬럼명을 `한국채권`, `한국채권_alt` 로 명확히 분리해야 함.

---

## 5. Regime 별 자산수익률에서 도출되는 TAA 정책 시사점

### 5.1 핵심 패턴

| Regime | 의미 | Best 자산 | Worst 자산 |
|---|---|---|---|
| 1 (확장) | Placement>0, Velocity>0 | 한국주식, 미국성장주, 신흥국, HY, 미국외선진국 (모든 위험자산 강세) | 글로벌채권 (-1.5%), 미국채권 (-0.8%) |
| 2 (회복) | Placement<0, Velocity>0 | 한국주식, 신흥국, HY, 미국성장주 | 한국채권 (1.7%), IG (9.8%) — 채권도 양수지만 위험자산 대비 약함 |
| 3 (둔화/침체) | Placement<0, Velocity<0 | 미국채권, 한국채권, 물가채, 금, IG, HY | 한국주식 (-17.4%), 신흥국 (-12.4%), 미국외선진국 (-9.6%) |
| 4 (감속) | Placement>0, Velocity<0 | 미국주식, 미국성장주, 미국리츠 | HY (4.6%), 한국채권 (-0.1%) — 미국 우세, 신흥국 약세 |

### 5.2 Regime 별 TAA tilt 정책 초안 (TDF 2060 기준 SAA = 80/20)

> 이 표는 **설계 초안**이며, regimeAnalysis_rt 의 평균 수익률 부호와 크기에서 단순 도출한 것이다. 운영 적용 전 백테스트 필요.

| Regime | Equity tilt | Bond tilt | 자산군 강조 | 자산군 약화 |
|---|---:|---:|---|---|
| 1 (확장) | +5%p (SAA 80% → 85%) | −5%p (20% → 15%) | em_equity, kr_equity, us_high_yield | kr_treasury_10y, us_treasury_30y |
| 2 (회복) | +3%p (80% → 83%) | −3%p (20% → 17%) | em_equity, us_high_yield | safe bonds |
| 3 (침체) | −5%p (80% → 75%) | +5%p (20% → 25%) | us_treasury_30y, kr_aggregate_bond, gold(외부) | kr_equity, em_equity, us_high_yield (HY가 risk asset이므로 함께 내림) |
| 4 (감속) | 0%p ~ +1%p (80% → 80~81%) | 0%p ~ −1%p | us_growth_equity, us_value_equity, dm_ex_us_equity | em_equity, kr_equity (미국 우세 후기 사이클) |

### 5.3 TAA 적용 원칙

1. **TAA 는 SAA 를 훼손하지 않는다.** Equity tilt 폭은 ±5%p 이내(spec: 75~85%) 로 제한.
2. **HY 는 채권 bucket 이지만 risk_asset flag** → Regime 1/2 에서 +, Regime 3 에서 − 처리.
3. **단일 자산 비중 변동 폭 제한** — 한 자산군의 tilt 는 ±3%p 이하로 제한 (config 로 조정).
4. **tilt 합 = 0** 가정 (자산군 rebalancing, 자금 유입/유출 없음).
5. **tilt 사유 (reason) 출력 의무화** — 어떤 regime, 어떤 자산이 어떻게 조정되었는지 reason 필드에 기록.

---

## 6. ECI 입력 — 어느 국가/composite를 기준으로 할 것인가

### 6.1 후보

| 후보 | 장점 | 단점 |
|---|---|---|
| KOR (한국) | 한국 OCIO/연금 펀드라는 도메인에 맞음 | 한국 단독 사이클은 글로벌 자산 평균수익률과 미스매치 가능 (regimeAnalysis_rt 가 글로벌 자산 기준이므로) |
| USA (미국) | regimeAnalysis_rt 평균수익률의 주된 driver | 한국 자산(한국주식, 한국채권) tilt 와 부분 미스매치 |
| G7 / G20 (composite) | 글로벌 자산과 가장 정합 | 한국 사이클 반영 약함 |
| Multi-region weighted | 자산군별로 다른 region ECI 사용 | 복잡도 증가 |

### 6.2 권장 (이번 설계 단계)

- **1차 default**: G7 또는 G20 composite ECI 를 단일 입력으로 사용.
- **확장 옵션**: TAA Overlay 가 자산군별 region 매핑을 받아, 자산군마다 다른 region 의 ECI 로 tilt 를 계산할 수 있도록 설계. config 로 ON/OFF.

```yaml
# taa_policy_draft.yaml
regime_input:
  mode: composite_g7    # composite_g7 | composite_g20 | per_asset_region
  per_asset_region:     # mode = per_asset_region 일 때만 적용
    kr_equity: KOR
    us_growth_equity: USA
    em_equity: G20
    ...
```

---

## 7. 향후 코드 골격에서의 클래스 분담

| 클래스 | 역할 | 입력 | 출력 |
|---|---|---|---|
| `PlacementCalculator` | rolling 12m 평균 차이 | `pd.DataFrame[date × country]` (Src) | `pd.DataFrame[date × country]` |
| `VelocityCalculator` | 1개월 차분 | Placement DF | Velocity DF |
| `ECIRegimeClassifier` | sign 조합 분류 | Placement DF + Velocity DF | DF[date × country, int 1~4] |
| `RegimeDashboardBuilder` | 단일 composite 의 phase angle 시각화용 | Placement+Velocity (single series) | 위상 정보 (R, Angle, Phase) |
| `RegimeAnalysisTool` | 위 4개를 묶는 facade | RegimeAnalysisInput | `RegimeAnalysisResult` |
| `AssetReturnCalculator` | level → 월간 수익률 | regimeAnalysis_src | DF[date × asset] |
| `RegimeReturnAnalyzer` | regime × asset 평균수익률 | 월수익률 + ECI | DF[regime × asset] |
| `RegimeReturnTool` | 두 클래스 묶음 facade | input | `RegimeReturnResult` |

---

## 8. Dashboard 의 Adj. Radius / Angle — 이번 단계 처리 방침

- **이번 설계 단계에서는 구현하지 않음.** Phase angle 기반 분류는 ECI sign-based 분류와 결과가 거의 동일하며 (`Phase(N)` 컬럼이 그 증거), 정책 결정에 추가 정보를 거의 주지 않는다.
- 향후 시각화 요구가 생기면 별도 모듈로 추가.

---

## 9. 요약 — Regime 모듈에 대한 핵심 결정 사항 (이번 단계 보고)

```
[1] Placement / Velocity / ECI 산식: 100% 사용자 spec과 일치 (메타 row 검증 완료).
[2] regime_Dashboard: 단일 composite 의 phase 시각화. 1차 설계에서는 사용하지 않고 ECI 만 정본.
[3] regimeAnalysis_src → regimeAnalysis_rt: 월수익률 × ECI join 후 평균. 컬럼 중복(미국나스닥 2회, 한국채권 2회) 발견 — 적재 시 명확화 필요.
[4] regimeAnalysis_rt 의 결과는 TAA tilt 정책 설계의 객관적 근거가 된다.
[5] ECI 입력 region 결정: 1차 default = G7/G20 composite. config 로 변경 가능하게 설계.
[6] HY 는 fixed_income bucket + risk_asset flag → Regime 1/2 +, Regime 3 −.
[7] TAA 변동 폭은 SAA ±5%p 이내, 자산군별 tilt 는 ±3%p 이내 (초안).
```
