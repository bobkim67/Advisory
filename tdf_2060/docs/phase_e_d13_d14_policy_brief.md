# Phase E-4 — D-13 / D-14 Policy Decision Brief

작성일: 2026-05-08. **운용역 판단용 brief**. 코드 / config / test / out 변경 없음.

**Sign-off (2026-05-08, 운용역 정정 sign-off)**:
- **D-13 closed** — 현행 유지 (ETF=hard_filter / Fund=score_penalty). 추가 제약 도입 안 함.
- **D-14 deferred** — manager cap / soft warning threshold 모두 미도입. monitoring telemetry only. 후속 Phase 재검토.
- **정정**: 본 brief 의 §3.6 / §6 Option B (soft warning ETF 50% / Fund 40%) 는 **채택하지 않음**. 일관 정책 = "현 단계는 제약 추가 안 함. relaxed 결과 관찰만 한다." cap / threshold / warning rule 은 후속 Phase 에서 도입 여부 재검토.

> **Phase D completed register-blocker resolution only.**
> **This does not mean production readiness.**
> **The engine remains in relaxed_diagnostic mode.**
>
> 본 brief 는 production 전환 전 필수 결정사항인 **D-13 (`quant_grade_policy`)** 와
> **D-14 (manager concentration cap)** 를 운용역이 판단할 수 있도록 정리.
> 정책 확정은 별도 sign-off 후. 본 turn 은 brief 만.

소스: `docs/phase_d_concentration_brief.md`, `docs/phase_e_relaxed_governance.md`,
`docs/phase_e_production_transition_design.md`, `out/db_etf_relaxed/`, `out/db_fund_relaxed/`,
`out/db_review_relaxed/comparison_etf_vs_fund_20260508.md`, `docs/investment_decision_register.md`.

---

## 1. Executive Summary

| 항목 | 값 |
|---|---|
| **D-13 status** | `open` (production 전환 전 필수 결정) |
| **D-14 status** | `open` (production 전환 전 필수 결정) |
| **D-13 추천** | **A. 현행 유지** (ETF=hard_filter / Fund=score_penalty) |
| **D-14 추천** | **B. soft warning threshold** (hard cap 즉시 도입 비추천) |

### 1.1 Concentration 의 1차 원인 — 운용사 cap 부재가 아님

relaxed 산출의 concentration (ETF us_growth top-3 = 60% / Fund KB운용 30%) 의 근본 원인:

| 가설 | 진위 | 근거 |
|---|:---:|---|
| (a) 자산군 쏠림 (relaxed mode 의 자산 cap 부재) | **✓ 1차 원인** | MVO 가 sharpe 최고 자산 (us_growth) 에 70.6% 쏠림 → us_growth target 70.6% 가 그대로 product 단계에 흘러감 |
| (b) 상품 선정 정책 (quant_grade_policy) | △ 부분 영향 | ETF hard_filter 가 64 상품 제외 → 후보 풀 축소 → 일부 자산군 (ust30, hy) 후보 부족 가능. 단 us_growth 쏠림 자체와 무관. |
| (c) 운용사 cap 부재 | ✗ 1차 원인 아님 | ETF 운용사 cap 60% / Fund 50% 모두 미발동. 운용사 분산 자체는 cap 없이도 자연스럽게 발생 (ETF top-1=25.73%, Fund top-1=30%) |

**결론**: concentration 은 자산군 단계 (D-11/D-12 deferred + D-15/D-17 candidate) 의 결과. **운용사 cap 만 강화하면 진짜 risk 를 가리면서 상품 선정만 왜곡**.

---

## 2. D-13 — quant_grade_policy 분석

### 2.1 현재 정책

| product type | mode | 효과 |
|---|---|---|
| **ETF** | `hard_filter` | C 등급 미만 ETF 가 후보군에서 사전 제거. 후보 풀 축소. |
| **Fund** | `score_penalty` | 등급 미만이라도 후보군 유지 + score 에 penalty. 후보 풀 유지. |

설정: `tdf_engine/config/universe_filter.yaml::quant_grade_policy.{etf,fund}.mode`. min_grade=C, penalty_per_grade=0.1.

### 2.2 relaxed 결과 영향

| product type | grade_filtered_count | grade_penalized_count | 효과 |
|---|---:|---:|---|
| ETF | **64** | 0 | 64 ETF 후보가 hard_filter 로 제외. 9 자산군 중 일부 (특히 ust30 obs=87 / hy 등) 후보 풀 축소. |
| Fund | 0 | **117** | 117 펀드 후보에 grade penalty 적용. 후보 풀 유지하되 score 정렬에 영향. |

**최종 portfolio 영향**:
- ETF 17 상품 / Fund 17 상품으로 비슷한 산출.
- ETF 의 hard_filter 가 fallback 빈도에 직접 영향 미발견 (9 자산군 중 일부에서 candidate 부족 가능성은 있으나 현재 산출에는 fallback_used=True 의 원인이 product_cap_clipping 이지 grade filter 가 아님).
- Fund 의 score_penalty 는 score 정렬에서 자연스럽게 작동. 결과적으로 KB / 한투 / 삼성 / AB 가 top-4 (운용사 cap 없이도 다변화).

### 2.3 선택지

| 옵션 | 내용 | 평가 |
|---|---|---|
| **A. 현행 유지** ✅ **추천** | ETF=hard_filter / Fund=score_penalty | 변경 영향 없음. fallback 빈도 / 후보 풀 둘 다 안정. concentration 1차 원인 아님. |
| B. ETF 도 `score_penalty` 로 완화 | ETF 후보 풀 확대 | 후보 부족 자산 (ust30=6, hy=2) 의 fallback 위험 감소. 단 등급 미달 ETF 가 score 로만 배제 → 운영 의도와 어긋날 수 있음 (ETF 는 보수적 운용). |
| C. Fund 도 `hard_filter` 로 강화 | Fund 후보 풀 축소 | quality 우선. 단 117 펀드 후보 일부가 즉시 제외 → fallback 빈도 ↑ 가능성. |
| D. monitoring_only 모드 신설 | grade 로 filter / penalty 안 함, telemetry 만 | 운용역이 사후 검토. 단 코드 변경 필요 (현재 mode = `hard_filter` / `score_penalty` 두 종류만). |

### 2.4 D-13 권장안

**옵션 A. 현행 유지**.

근거:
1. relaxed 결과의 concentration 은 D-13 의 영향이 아닌 자산군 쏠림 (D-11/D-12 deferred 영역) 에서 발생.
2. ETF 의 보수적 (hard_filter) + Fund 의 유연 (score_penalty) 분리는 product 특성과 정합 (ETF 등급 미달 = 운용 신뢰도 의심, Fund 등급 미달 = 운용 다변화).
3. 변경 시 후보 풀 / fallback 빈도 변화 발생 → relaxed/production 산출 모두 재검증 필요. **production 전환 전 추가 변동 도입 = 위험**.
4. 운용역이 현 정책 동작 충분히 인지 + 64 ETF 제외 / 117 Fund penalty 가 운영 의도와 정합 확인 후 closed 가능.

**closure 조건** (D-13):
- 운용역이 ETF=hard_filter / Fund=score_penalty 정책을 확인 + 옵션 A 그대로 closed
- 또는 옵션 B/C/D 중 하나 선택 + config 변경 (`universe_filter.yaml::quant_grade_policy.{etf,fund}.mode`) + 회귀 검증

---

## 3. D-14 — Manager Concentration Analysis

### 3.1 현재 정책

| product type | manager cap | 동작 |
|---|---:|---|
| **ETF** | 60% | universe_filter 단계에서 단일 운용사 합 60% 초과 시 cap 적용 |
| **Fund** | 50% | 동 |

설정: `tdf_engine/config/universe_filter.yaml::{etf,fund}.product_constraints.manager_max_weight` (또는 유사 키).

### 3.2 relaxed 결과 — 운용사 concentration

#### ETF top-5 manager

| rank | manager | sum weight | cap (60%) 도달? |
|---:|---|---:|:---:|
| 1 | 미래에셋운용 | **25.73%** | ✗ |
| 2 | 삼성운용 | 23.69% | ✗ |
| 3 | 한국투자신탁운용 | 23.09% | ✗ |
| 4 | 타임폴리오자산운용 | 20.00% | ✗ |
| 5 | 신한자산운용 | 4.66% | ✗ |

top-1 = 25.73% (cap 60% 미발동). top-4 합 = 92.51%.

#### Fund top-5 manager

| rank | manager | sum weight | cap (50%) 도달? |
|---:|---|---:|:---:|
| 1 | **KB운용** | **30.00%** | ✗ (cap 50% 미발동) |
| 2 | 한국투자신탁운용 | 27.40% | ✗ |
| 3 | 삼성운용 | 20.30% | ✗ |
| 4 | AB자산운용 | 20.30% | ✗ |
| 5 | NH-Amundi운용 | 0.90% | ✗ |

top-1 = 30.00%, top-2 합 = 57.40%, top-4 합 = 98.00%.

### 3.3 Concentration 의 진짜 원인 분석

**Fund 의 KB 30% 는 manager cap 이 아닌 단일 product cap 이 binding**:
- us_growth target 70.60% (자산군 쏠림 — D-11/D-12 deferred)
- Fund single product cap = 30% (D-16 candidate 영역)
- → us_growth core 1 product (KB미국대표성장주자) = 30% (single cap binding)
- → 운용사 KB = 30% 는 **상품 cap 의 결과** (운용사 cap 의 결과 아님)

**ETF 의 top-3 가 각 20% 인 것도 동일 메커니즘**:
- us_growth target 70.60% / ETF single product cap = 20% / core 1 + satellite 2 = 60%
- → 3 상품 각 20%. 운용사 분산 자연스럽게 발생 (타임폴리오 / 삼성 / 미래에셋).

**결론**: 본 데이터의 manager concentration 은 **product cap binding 의 부산물**. manager cap 자체는 binding 안 됨.

### 3.4 단일 운용사 threshold 후보

| threshold | ETF 영향 | Fund 영향 |
|---|---|---|
| 60% / 50% (현행) | 미발동 | 미발동 |
| 50% / 40% | 미발동 | 미발동 |
| 30% / 30% | 미발동 | **KB 30% binding** → core product (us_growth) 강제 분산 → 다른 운용사 product 로 fallback → 자산군은 같은데 운용사만 분산 → 부산물 왜곡 |
| 20% / 20% | 미래에셋 25.73% binding → 분산 → ETF top-3 (각 20%) 강제 재분배 → fallback 발생 | 동 |
| monitoring only | 발동 자체가 안 됨. telemetry 표시만. | 동 |

### 3.5 선택지

| 옵션 | 내용 | 평가 |
|---|---|---|
| A. cap 없음, monitoring only | hard cap 제거. telemetry 만 표시. | D-01 정신 (hard constraint 최소화) 와 정합. 단 production 시점에서 운용사 분산 보장 약함. |
| **B. soft warning threshold** ✅ **추천** | hard cap 유지하되 cap 미달이라도 warning threshold (예: ETF 50% / Fund 40%) 초과 시 review packet 에 warning. fail 아님. | hard cap 의 안전망 유지 + warning 으로 과도한 쏠림 사전 감지. 현재 산출 영향 없음. |
| C. hard cap (현행 또는 강화) | 현행 60%/50% 유지 또는 강화. cap 도달 시 fallback. | 현행은 미발동이라 영향 없음. 강화 (30%/30%) 시 자산군은 같은데 운용사만 강제 분산 → product cap 과 결합하면 의도치 않은 산출 왜곡 가능. |
| D. 자산군 band 재도입 후 재검토 | D-11/D-12 reactivate 후 us_growth 자산군 자체가 70%+ 가 안 되면 manager concentration 도 자연 해소. 그 후 cap 재검토. | D-11/D-12 deferred 영역 의존. 시간 비용 ↑ but 가장 정합적. |

### 3.6 D-14 권장안

**옵션 B. soft warning threshold**.

근거:
1. concentration 1차 원인이 manager 가 아닌 자산군 쏠림 + product cap 부산물.
2. hard cap 즉시 도입 (옵션 C) → 진짜 risk (자산 쏠림) 가림 + 상품 선정 왜곡 (의도치 않은 fallback) → 비추천.
3. cap 완전 제거 (옵션 A) → 안전망 손실. 미래의 극단 케이스 (예: 단일 운용사 80%+) 대비 약함.
4. **soft warning** = 현행 hard cap 유지 + 추가 warning threshold (예: ETF 50% / Fund 40%) 도입. cap 도달 전 단계에서 review packet 에 telemetry warning. fail 아님.
5. 자산군 band (D-11/D-12) reactivate 시 manager concentration 도 자연 해소 → 그때 cap / warning threshold 재조정.

**구현 부담**: review packet 의 §4.1 또는 §6 에 운용사 sum weight 표시 + threshold 비교. 코드 변경 작음. yaml 에 `manager_warning_threshold` 키 추가.

**closure 조건** (D-14):
- 운용역이 옵션 B 채택 + warning threshold 운영값 결정 (예: ETF 50% / Fund 40%)
- 또는 옵션 A/C/D 중 하나 선택 + 그에 따른 config / 코드 변경

---

## 4. Production 전환 관점의 권장 정책

### 4.1 production dry-run 전에 반드시 닫을 항목

| 항목 | 우선순위 | 이유 |
|---|:---:|---|
| **D-13** | **닫아야 함** | production 전환 시 quant_grade 정책이 명시되어야 함. 옵션 A 채택 시 변경 0 — 현행 유지로 즉시 closed 가능. |
| **D-14** | **닫아야 함** (또는 monitoring_only 로 전환) | production 시점에서 운용사 cap 정책 명시 필요. 옵션 B (soft warning) 채택 시 cap 자체는 유지 + warning threshold 추가. |

### 4.2 production 정식 전환 전까지 monitoring 으로 둘 항목

| 항목 | monitoring 사유 |
|---|---|
| Fund KB 30% 같은 product 단계 concentration | D-15 / D-16 candidate 영역. monitoring 으로 두고 누적 시 정식 등록. |
| ETF top-1 운용사 25%+ | manager warning threshold 발동 / 미발동을 사례별로 누적 |
| 자산군 70%+ 쏠림 (us_growth) | D-17 candidate 영역. monitoring 으로 누적 후 D-11/D-12 reactivate 결정 근거 |

### 4.3 hard cap 즉시 도입 시 부작용

| 정책 | 부작용 |
|---|---|
| D-14 manager cap 30%/30% 강화 | (a) Fund KB 30% binding → core product 강제 분산 → 자산군 비중 동일한데 운용사만 분산 → 진짜 risk (자산 쏠림) 가림. (b) ETF 미래에셋 25.73% binding → 강제 재분배 → 운용역 의도와 어긋난 fallback. |
| D-13 ETF 도 score_penalty / Fund 도 hard_filter 변경 | 후보 풀 변화 → fallback 빈도 / quality_status 영향. relaxed/production 산출 모두 재검증 필요. production 전환 전 추가 변동 = 위험. |
| 자산군 cap 재도입 (D-11/D-12) 없이 운용사 cap / 상품 cap 만 강화 | 비대칭. 자산은 자유, 운용사·상품만 제약 → 진짜 risk 가려짐. |

---

## 5. Closure 조건

### 5.1 D-13 closure 조건

| 옵션 | closure 처리 | 후속 작업 |
|---|---|---|
| A. 현행 유지 | `closed` (status `open → closed`). decision = "ETF=hard_filter / Fund=score_penalty 현행 유지". | config 변경 없음. register status / 본문 갱신만. |
| B. ETF 도 score_penalty | closed. config `universe_filter.yaml` ETF mode 변경 + 회귀 검증. | yaml 변경 + pytest. |
| C. Fund 도 hard_filter | 동 (Fund mode 변경). | 동. |
| D. monitoring_only | closed. 단 monitoring_only 모드 코드 신설 필요. | 코드 변경 + config + tests. |

### 5.2 D-14 closure 조건

| 옵션 | closure 처리 | 후속 작업 |
|---|---|---|
| A. cap 없음, monitoring only | closed. `manager_max_weight` 제거 또는 1.0 으로 완화. | config 변경 + review packet manager telemetry 추가. |
| B. soft warning threshold | closed. yaml `manager_warning_threshold.{etf,fund}` 키 신설 + review.py 에 warning 로직 추가 (warning telemetry, fail 아님). | yaml + 코드 (review.py) + tests. |
| C. hard cap 강화 | closed (또는 deferred). yaml `manager_max_weight` 값 변경. | config 변경 + 회귀 검증 (binding 시 fallback 동작 확인). |
| D. 자산군 band 재도입 후 재검토 | **deferred** (D-11/D-12 와 함께). | D-11/D-12 reactivate 시점까지 보류. |

### 5.3 deferred 또는 monitoring_only 처리 가능 여부

- **D-13**: deferred 비추천 — production 전환 전 명시 필요. monitoring_only 는 옵션 D 로 코드 변경 후 가능.
- **D-14**: deferred 가능 (옵션 D — 자산군 band 후 재검토). 또는 monitoring_only (옵션 A) 즉시 적용 가능. soft warning (옵션 B) 가 둘 사이의 절충.

---

## 6. Sign-off Options (운용역 4 옵션)

운용역이 한 번에 결정 가능한 4 옵션 묶음. 각 옵션의 closure 사유와 후속 작업이 다름.

### Option A — 현행 유지 (보수)
```
D-13: A (ETF=hard_filter / Fund=score_penalty 현행 유지) → closed
D-14: A (cap 없음, monitoring only) → closed
의미: 변경 최소. concentration 1차 원인 (자산군 쏠림) 은 D-11/D-12 / D-15-17 영역으로 분리.
config 변경: D-14 manager_max_weight 제거 또는 1.0 (monitoring 코드 추가)
부작용: 미래 극단 케이스 (단일 운용사 80%+) 시 안전망 약함.
```

### Option B — 현행 + soft warning (추천)
```
D-13: A (현행 유지) → closed
D-14: B (soft warning threshold) → closed
의미: D-13 은 그대로. D-14 는 hard cap 유지 + warning threshold 추가 (ETF 50% / Fund 40%).
config 변경: yaml manager_warning_threshold.{etf,fund} 신설 + review.py 의 §4 또는 §6 에 운용사 telemetry warning 추가
부작용: 본 산출 영향 없음 (현재 미발동). 코드 변경 작음.
✅ 본 brief 추천.
```

### Option C — 강화 (적극)
```
D-13: A (현행 유지) → closed
D-14: C (hard cap 강화, 예: ETF 30% / Fund 30%) → closed
의미: 운용사 cap 강화. 단 자산군 cap (D-11/D-12) 는 deferred 그대로.
config 변경: yaml manager_max_weight ETF 60→30, Fund 50→30
부작용: 자산은 자유, 운용사만 제약 → 진짜 risk (us_growth 70%+) 가림. 상품 선정 왜곡 가능.
비추천 — 자산군 band 없이 운용사 cap 만 강화는 비대칭.
```

### Option D — Production dry-run 후 재판단
```
D-13: open 유지 (production dry-run 결과 본 후 결정)
D-14: open 유지 (동)
의미: production yaml 1회 변경 → dry-run 산출 → review → 그 결과로 D-13/D-14 정책 결정.
config 변경: 본 brief 단계에서는 없음. dry-run 시 operating_mode 만 변경.
부작용: production 전환 전 필수 결정사항이 미정 상태로 dry-run 진입 → governance 흐름 정합성 약화.
주의: 본 옵션은 "정책 결정 보류 + dry-run 으로 데이터 더 확보" 의미. dry-run 결과가 문제 시 다시 옵션 A/B/C 선택.
```

---

## 7. 권장 흐름 (사용자 가설 반영)

사용자 제시 가설:
> "D-13: 현행 유지 우선. ETF hard_filter, Fund score_penalty.
> D-14: hard cap 즉시 도입보다 monitoring 또는 soft warning 우선.
> 이유는 현재 concentration 의 1차 원인이 운용사 문제가 아니라 relaxed mode 에서 자산군 제약을 푼 결과이기 때문."

본 brief 의 분석과 정합. 추천 흐름:

```
1. Option B 채택 (D-13 A + D-14 B)
   → D-13 closed (현행 유지)
   → D-14 closed (soft warning threshold)

2. config 변경 (별도 turn, 운용역 승인 후)
   - tdf_engine/config/universe_filter.yaml
     · D-13 변경 없음 (현행 유지)
     · D-14: manager_warning_threshold.etf = 0.50 (또는 운용역 결정값)
             manager_warning_threshold.fund = 0.40

3. 코드 변경 (별도 turn)
   - tdf_engine/reporting/review.py 또는 동등 위치:
     운용사 sum weight 가 warning_threshold 초과 시 review packet 에 warning telemetry 출력
   - 신규 테스트 1~2건

4. D-13 / D-14 closure 후 register / HANDOFF / memory 갱신
   - register: open 2 → 0, closed 9 → 11
   - blocker: 0건 그대로 (D-13/D-14 는 production 전환 전 필수 결정이지 register blocker 아님)

5. Phase E roadmap 다음:
   - E-5 (D-15/D-16/D-17 candidate 처리)
   - 그 후 E-3 (D-11/D-12 reactivate 결정)
   - 그 후 production dry-run
```

---

## 8. 본 brief 까지의 변경 / 후속 변경 영역

| 영역 | 본 turn | 후속 (사용자 승인 후) |
|---|:---:|---|
| `tdf_engine/` 코드 | ✗ | (옵션 B 채택 시) review.py 의 manager warning telemetry 추가 |
| `tdf_engine/config/universe_filter.yaml` | ✗ | (옵션 B) `manager_warning_threshold.{etf,fund}` 신설 |
| `tests/` | ✗ | (옵션 B) manager warning telemetry 검증 1~2 테스트 |
| `out/` 산출물 | ✗ | (옵션 B 적용 후) review packet 재생성으로 manager warning 노출 |
| `docs/investment_decision_register.md` D-13/D-14 status | ✗ | (옵션 B) `open → closed` × 2 + 분포 갱신 + 변경 이력 |
| Decision Register total count | ✗ (14 그대로) | (옵션 B) 14 그대로. closed 9→11. open 2→0. |
| `HANDOFF.md` / `memory/project_state.md` | ✗ | (옵션 B) 분포 갱신 |
| 본 brief 신설 | ✓ | — |

pytest: `142 passed, 5 skipped, 1 xfailed` (sanity 차원, 본 turn 변경 없음).

---

## 9. 한 줄 요약 (sign-off 후)

> **D-13 closed = 현행 유지 (A). ETF hard_filter / Fund score_penalty 그대로. 추가 제약 도입 안 함.**
> **D-14 deferred = cap / soft warning threshold 모두 미도입. monitoring telemetry only. 후속 Phase 재검토.**
> **정정**: 본 brief §3.6 / §6 Option B (soft warning ETF 50% / Fund 40%) 채택 안 함.
> **일관 정책**: 현 단계는 **제약 추가 안 함. relaxed 결과 관찰만 한다.**

---

## 10. Sign-off note (2026-05-08, 운용역 정정 sign-off)

```
─────────────────────────────────────────────────────────────────────────
D-13 closed / D-14 deferred — 운용역 sign-off (2026-05-08)

D-13 (quant_grade_policy):
  status: open → closed
  decision: 현행 유지 (ETF=hard_filter / Fund=score_penalty)
  근거:
    - relaxed concentration 의 1차 원인 = 자산군 쏠림 (D-11/D-12 deferred 영역).
      D-13 영향 미발견.
    - 변경 시 후보 풀 / fallback 빈도 변동 위험 → production 전환 전 추가 변동 = 위험.
  config / 코드 / tests / out 변경: 없음

D-14 (manager concentration cap):
  status: open → deferred
  decision: 제약 도입 안 함. monitoring telemetry only.
  근거:
    - 현재 concentration 1차 원인 = relaxed_diagnostic mode 의 자산군 쏠림
      (us_growth 70.6%) + product cap binding 부산물.
    - manager cap 부재가 원인이 아님. cap / soft warning 만 먼저 도입 시
      진짜 risk 가림 + 상품 선정 왜곡.
    - 일관 정책 = "현 단계는 제약 추가 안 함. relaxed 결과 관찰만."
  재검토 시점: 후속 Phase (E-3 자산군 band 재도입 결정 후 또는
                production dry-run 결과 누적 후)
  config / 코드 / tests / out 변경: 없음

정정 사유:
  - 직전 turn 의 Option B 권장 (soft warning ETF 50% / Fund 40%) 은
    "현 단계 제약 추가 안 함" 정책과 부합하지 않아 채택하지 않음.
  - manager_warning_threshold yaml 추가 / review.py warning 로직 추가 모두 ✗.

분포 변화:
  open 2 → 0 / deferred 2 → 3 / closed 9 → 10. total 14 유지.

승인일: 2026-05-08 (운용역 정정 sign-off)
─────────────────────────────────────────────────────────────────────────
```
