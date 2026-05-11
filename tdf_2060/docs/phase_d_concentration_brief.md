# Phase D — Concentration Brief (D-13 / D-14)

작성일: 2026-05-08. 운용역 판단용 brief. 데이터 출처: `out/db_etf_relaxed/`, `out/db_fund_relaxed/` (2026-05-08 산출).

> ⚠️ **본 brief 의 수치는 RELAXED DIAGNOSTIC RUN 결과**. production 산출 아님. 자산군별 band /
> bucket range 가 비활성된 상태에서 optimizer + product cap clipping 만 작용했을 때의 집중도.
> Decision 자체는 monitoring vs hard cap 선택지 제시. 본 brief 가 "cap 즉시 도입" 을 주장하지는 않음.

---

## 1. 산출 메타

| 항목 | ETF | Fund |
|---|---:|---:|
| 상품 수 | **17** | **17** |
| equity bucket | 100.00% | 100.00% |
| fixed_income bucket | 0.00% | 0.00% |
| 0% 자산군 수 | 5 (kr_aggregate / kr_t10 / ust30 / dm_ex_us / hy) | 5 (동일) |

> constrained run (2026-05-07) 대비 ETF/Fund 모두 26 상품 → **17 상품** 으로 축소.
> 9개 자산군 중 5개가 0% → 활성 자산은 4개 (kr_equity, us_growth, us_value, em_equity).
> us_growth 70.6% + us_value 27.4% = 미국주식 98% → 사실상 single-region equity 포트폴리오.

---

## 2. 상품 집중도 (top-5 by final_weight)

### 2.1 ETF — top-5 product

| asset_key | weight | manager | product |
|---|---:|---|---|
| us_growth_equity | **20.00%** | 타임폴리오자산운용 | 타임폴리오TIME미국나스닥100액티브상장지수(주식) |
| us_growth_equity | **20.00%** | 삼성운용 | 삼성KODEX미국나스닥AI테크액티브상장지수[주식] |
| us_growth_equity | **20.00%** | 미래에셋운용 | 미래에셋TIGER미국필라델피아반도체나스닥상장지수(주식) |
| us_value_equity | **20.00%** | 한국투자신탁운용 | 한국투자ACE미국배당다우존스상장지수(주식) |
| us_value_equity | 4.66% | 신한자산운용 | 신한SOL미국배당다우존스상장지수[주식] |

ETF 단일 상품 cap = 20% (universe_filter 의 single_product_max_weight 가 binding). top-3 상품 합 = **60.00%** (모두 us_growth, AI/반도체 테마 중복).

### 2.2 Fund — top-5 product

| asset_key | weight | manager | product |
|---|---:|---|---|
| us_growth_equity | **30.00%** | KB운용 | KB미국대표성장주자(주식)(UH)C-퇴직 |
| us_value_equity | **21.92%** | 한국투자신탁운용 | 한국투자미국배당귀족자UH(주식)(C-R) |
| us_growth_equity | **20.30%** | 삼성운용 | 삼성미국그로스자UH[주식-재간접]_Cp(퇴직연금) |
| us_growth_equity | **20.30%** | AB자산운용 | AB미국그로스UH(주식-재간접)종류C-P2 |
| us_value_equity | 5.48% | 한국투자신탁운용 | 한국투자미국배당귀족자H(주식)(C-R) |

Fund 단일 상품 cap = 30% (Fund용). top-1 상품 (KB 30%) 만으로 portfolio 의 30% 점유.

---

## 3. 운용사 집중도 (top-5)

### 3.1 ETF — top-5 manager

| manager | sum weight |
|---|---:|
| 미래에셋운용 | **25.73%** |
| 삼성운용 | **23.69%** |
| 한국투자신탁운용 | **23.09%** |
| 타임폴리오자산운용 | **20.00%** |
| 신한자산운용 | 4.66% |

top-4 운용사 합 = **92.51%** (5개 중 4개에 90%+). 단일 운용사 한도 60% (현 yaml) 도달 안 함.

### 3.2 Fund — top-5 manager

| manager | sum weight |
|---|---:|
| KB운용 | **30.00%** |
| 한국투자신탁운용 | **27.40%** |
| 삼성운용 | 20.30% |
| AB자산운용 | 20.30% |
| NH-Amundi운용 | 0.90% |

top-2 운용사 합 = **57.40%**, top-4 = 98.00%. 단일 운용사 한도 50% (현 yaml) 도달 안 함 (KB 30%).
Fund 의 KB 30% 는 단일 상품 cap 30% 가 binding 한 결과 — 운용사 cap 이 binding 한 게 아님.

---

## 4. Fund 의 KB 30% / 한투 27.40% 해석

| 측면 | 해석 |
|---|---|
| 원인 | us_growth 자산이 SAA에서 70%+ 비중을 받았고, Fund의 us_growth 후보군 중 KB의 'KB미국대표성장주자' 가 최고 score → core 1 상품으로 30% 채택. |
| 현재 cap 작동 여부 | 운용사 cap 50% 미도달. 단일 상품 cap 30% 가 binding. |
| 위험 | (a) 단일 운용사 30% 노출 (KB 운용 risk 직접). (b) us_growth 라는 **단일 자산군 + 단일 thesis** 에 portfolio 의 70%+. |
| 다변화 신호 | top-2 운용사 (KB + 한투) = 57% → 과반. top-4 = 98% → 사실상 4개 운용사 portfolio. |
| relaxed 정책의 자연적 결과 | bucket range / per-asset band 비활성 → MVO 가 sharpe 최고 자산에 70%+ 쏠림 → 그 자산의 최고 score 상품에 단일 상품 cap 까지 채워짐 → 운용사 cap 은 미발동. |

> 본 집중도는 **"cap 이 너무 느슨하다" 가 아니라 "자산군 단계의 다변화 도구가 비활성"** 된 결과. 자산군 cap (D-11/D-12 deferred) 또는 bucket range (D-01 closed, 향후 재도입) 가 더 직접적인 해결 도구. 운용사 cap 은 보조 장치.

---

## 5. quant_grade_policy 영향

| 모드 | filtered | penalized | 효과 |
|---|---:|---:|---|
| ETF (`hard_filter`) | **64** 후보 제외 | 0 | C 등급 미만 ETF 가 후보군에서 사전 제거. 후보 풀 축소 → 결과적으로 후보 적은 자산 (예: ust30=6, hy=2) 의 selection 가용성에 영향. |
| Fund (`score_penalty`) | 0 | **117** 후보에 grade penalty | 등급 미만이라도 후보군 유지하되 score 에 패널티 적용 → 더 풍부한 후보풀에서 score 기반 정렬. |

**모드 차이의 의미**:
- `hard_filter` (ETF): 보수적. 등급 미만 자산을 아예 안 봄. 후보 부족 자산은 fallback 위험.
- `score_penalty` (Fund): 유연. 등급 미만도 후보 유지, score 로 자연 정렬. 후보 풀 큰 자산군에서 효과적.

본 relaxed 산출에서는 active 자산이 4개뿐이라 quant_grade_policy 차이가 결과에 큰 영향을 주지 않음. 다만 자산군별 band 재도입 시 lookup 필요.

---

## 6. D-13 / D-14 결정해야 할 사항 (옵션 제시)

### 6.1 D-13 — `quant_grade_policy` mode (현재: ETF=hard_filter, Fund=score_penalty)

| 옵션 | 내용 | 영향 |
|---|---|---|
| A | 현 상태 유지 | ETF 보수적, Fund 유연. 자산군 다변화가 충분하면 자연스러운 결과. |
| B | ETF 도 `score_penalty` 로 통일 | ETF 후보 풀 확대. 등급 미만 ETF 도 score 로 자연 배제. relaxed mode 처럼 후보가 적은 자산에서 fallback 위험 감소. |
| C | Fund 도 `hard_filter` 로 통일 | Fund 보수적 정렬. 후보 풀 축소. quality 우선. |
| D | mode 자체를 `monitoring_only` 추가 | grade 로 filter/penalty 안 함, telemetry 만 표시. 운용역이 사후 검토. |

### 6.2 D-14 — 운용사 concentration cap (현재: ETF 60%, Fund 50%)

| 옵션 | 내용 | 영향 |
|---|---|---|
| A | 현 상태 유지 (hard cap, ETF 60% / Fund 50%) | relaxed 산출에서 미발동 (ETF top1=25.73%, Fund top1=30%). 자산군 band 재도입 시 다시 유의미. |
| **B** | **monitoring only 로 전환** | cap 위반 시 fail 이 아닌 telemetry flag. relaxed 시점 D-01 정신 (hard constraint 최소화) 과 정합. **추천**. |
| C | 더 엄격하게 (ETF 30%, Fund 30%) | 단일 운용사 위험 축소. 단 Fund 의 KB 30% 가 cap 도달 → 다른 운용사 상품으로 강제 분산 → fallback 발생 가능. 자산군 band 비활성 상태에서 운용사 cap 만 강화하는 것은 비대칭 (자산은 자유, 운용사만 제약). |
| D | 현재값 유지하되 reference 로 표기 | yaml `manager_cap_reference` 키로 보존, hard cap 제거. monitoring section 에서 ETF/Fund 별 top-1 운용사 비중 노출. **B 와 유사**. |

### 6.3 주의 — 본 brief 가 추천하지 않는 행동

- "지금 운용사 cap 을 30% 로 강화" → **비추천**. 자산군 band (D-11/D-12 deferred) 가 우선 도구. 운용사 cap 만 강화하면 자산은 여전히 70%+ us_growth 인데 운용사만 분산 → 진짜 risk (자산 쏠림) 가 가려짐.
- "지금 D-13 을 hard_filter 로 통일" → **비추천**. 후보 풀 축소가 fallback 빈도를 높일 수 있음. monitoring 모드 (D 옵션) 가 우선.

---

## 7. 권장안 한 줄 요약

| Decision | 추천 | 이유 |
|---|---|---|
| **D-13** | **A 유지** (또는 D 신설 = monitoring only) | relaxed 시점에서 mode 변경의 근거 약함. D-11/D-12 재도입 단계에서 함께 검토. |
| **D-14** | **B (monitoring only)** | D-01 hard constraint 최소화 정신 정합. 현재 cap 미발동이라 즉시 영향 없음. cap 강화는 자산군 band 재도입 후 검토. |

---

## 8. 다음 단계

1. 운용역이 §6.1 / §6.2 옵션 선택
2. 선택 결과를 `investment_decision_register.md` D-13 / D-14 entry 에 반영 (현재 둘 다 `open`)
3. monitoring 으로 결정 시 reporting/review.py 의 `_build_warning_register` 와 `_build_excluded_summary` 에 운용사 / quant_grade telemetry 항목 보강 (별도 PR)
4. hard cap 으로 결정 시 universe_filter.yaml + selection/tool.py 갱신 (별도 PR)
