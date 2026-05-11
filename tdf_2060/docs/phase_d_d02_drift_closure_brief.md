# Phase D — D-02 Projection Drift Closure Brief

작성일: 2026-05-08. 운용역 판단용 brief. 코드/config/test 변경 없음.
**Sign-off: 2026-05-08 — D-02 closed by 운용역 승인 (`phase_d_d02_signoff_patch_plan.md §1` 정책).**

> **결론**: D-02 **closed**. projection 단계의 long-only clipping 정책에 관한 결정 완료.
> 정책 = `relaxed_diagnostic=telemetry_only` / `review=warning` / `production=review_required` /
> asset drift 3% / bucket drift 5% / **scope = projection drift only**.
> `max_abs_asset_weight_drift = 10.60%` 는 D-02 가 아닌 selection/product cap binding 단계의 drift 로,
> 별도 candidate (D-15/D-16/D-17) 로 분리.

소스: `out/db_etf_relaxed/review_etf_20260508.md`, `out/db_fund_relaxed/review_fund_20260508.md`,
`out/db_review_relaxed/comparison_etf_vs_fund_20260508.md`, `docs/investment_decision_register.md`,
`diagnostics.taa_diagnostics.taa_feasibility.clipping_summary`, `diagnostics.quality.drift_clipping_summary`.

---

## 1. Executive Summary

| 항목 | 값 |
|---|---:|
| **D-02 status** | **`closed` (2026-05-08, 운용역 sign-off)** |
| Projection drift (max_abs) | **3.00%** |
| Projection drift primary source | `redistribution_from_long_only_clipping` |
| Quality / selection drift (max_abs) | **10.60%** |
| Quality drift primary source | `fallback_redistribution_inflow` (개수 4) / `product_cap_clipping_outflow` (us_growth) |
| relaxed_mode_unexpected_sources | **[ ]** (bucket_constraint / asset_upper_bound 발생 0건) |
| 산출 ETF/Fund 자산비중 차이 | 0.00% (universe/selection 단계 차이만) |

**판정**:
- ✅ Projection drift 3.00% 는 long_only_clipping (ust30 −3%p / kr_t10 −2%p tilt 가 0% 로 clip) 의 직접 결과 → **현재 정책 (long-only + sum-to-100%) 정합**.
- ⚠️ Quality drift 10.60% 는 us_growth target 70.60% 가 ETF single product cap 20% × 3 상품 = 60% 로 채워진 결과 → **D-02 가 아닌 product allocation 단계 이슈**.
- 두 drift 를 같은 D-02 로 다루면 의사결정이 꼬임. **분리 처리 필수**.

---

## 2. Projection Drift 분석 (D-02 직접 대상)

### 2.1 정량 데이터

| 항목 | 값 |
|---|---:|
| `max_abs_projection_drift` | **3.00%** |
| `clipped_weight_total` | 5.00% |
| `n_assets_clipped_long_only` | 2 |
| `redistribution_total` | 5.00% |

**Clipped assets (target<0 → final≈0)**:

| asset_key | target_before_projection | final_after_projection | clipping magnitude | source |
|---|---:|---:|---:|---|
| `us_treasury_30y` | −3.00% | +0.00% | 3.00% | long_only_clipping |
| `kr_treasury_10y` | −2.00% | +0.00% | 2.00% | long_only_clipping |

**Redistribution recipients (target≥0 인데 다른 자산의 clipping 으로 spillover 손실)**:

| asset_key | target | final | drift | source |
|---|---:|---:|---:|---|
| `us_value_equity` | +28.40% | +27.40% | −1.00% | redistribution_from_long_only_clipping |
| `em_equity` | +2.00% | +1.00% | −1.00% | redistribution_from_long_only_clipping |
| `kr_equity` | +2.00% | +1.00% | −1.00% | redistribution_from_long_only_clipping |
| `us_high_yield` | +1.00% | +0.00% | −1.00% | redistribution_from_long_only_clipping |
| `us_growth_equity` | +71.60% | +70.60% | −1.00% | redistribution_from_long_only_clipping |

### 2.2 Source counts

```
redistribution_from_long_only_clipping = 5
long_only_clipping                     = 2
relaxed_mode_unexpected_sources        = []
```

**`bucket_constraint`, `asset_upper_bound`, `asset_lower_bound` source 발생 0건** — relaxed mode (bucket [0,1], per-asset [0,1]) 에서 의도된 결과. yaml 의 모든 bound 가 no-op 임을 코드 레벨로 검증.

### 2.3 정책 정합성 판단

| 정책 | 본 결과 | 정합 |
|---|---|:---:|
| #4: 개별 자산군 음수 비중 금지 | ust30 −3%p, kr_t10 −2%p 음수 target 이 0% 로 clip → final 음수 0개 | ✅ |
| #6: 전체 weight 합계 100% | sum(final) = 1.0 (재분배로 정합 유지) | ✅ |
| #7: hard constraint = long-only + sum-to-100% | clipping 자체가 long-only 강제. redistribution 은 sum-to-1 강제. | ✅ |
| #2: TAA 허용범위 해제 | bucket_constraint / per_asset_max_tilt source 발생 0건 | ✅ |

**판정**: **projection drift 3.00% 는 오류가 아니라 long-only 정책의 정상 적용**.

원인을 더 거슬러 올라가면 — regime 1 (Expansion) 의 TAA tilt 정책상 안전채권 (ust30, kr_t10) 에 음수 tilt 가 들어감 + relaxed mode 에서 SAA ust30/kr_t10 ≈ 0 → SAA + tilt 가 음수가 되는 구조적 문제. 이는 **TAA tilt policy 자체** 의 문제이지 projection drift 임계의 문제가 아님.

---

## 3. Quality / Selection Drift 분석 (D-02 가 아님)

### 3.1 정량 데이터

| 항목 | 값 |
|---|---:|
| `max_abs_asset_weight_drift` | **10.60%** |
| `total_outflow_magnitude` | 10.60% |
| `total_inflow_magnitude` | 10.60% |
| `n_assets_with_outflow` | 1 |
| `n_assets_with_inflow` | 4 |

**Outflow (target → final 감소, 1개)**:

| asset_key | target | final | drift | source |
|---|---:|---:|---:|---|
| `us_growth_equity` | +70.60% | +60.00% | **−10.60%** | **product_cap_clipping_outflow** |

**Inflow (target → final 증가, 4개)**:

| asset_key | target | final | drift | source |
|---|---:|---:|---:|---|
| `em_equity` | +1.00% | +3.89% | +2.89% | fallback_redistribution_inflow |
| `kr_equity` | +1.00% | +3.89% | +2.89% | fallback_redistribution_inflow |
| `dm_ex_us_equity` | +0.00% | +2.89% | +2.89% | fallback_redistribution_inflow |
| `us_value_equity` | +27.40% | +29.32% | +1.93% | fallback_redistribution_inflow |

### 3.2 발생 메커니즘

1. **자산군 단계** (relaxed): MVO 가 sharpe 최고인 us_growth 에 70.60% 쏠림. 자산군별 cap/floor (D-11/D-12 deferred) 미적용 → 정책상 정상.
2. **TAA 단계**: us_growth target 그대로 71.60% (regime 1 에서 us_growth 에 명시 tilt 없음). projection 후 70.60% (redistribution 손실).
3. **상품 단계**: ETF universe_filter 의 `single_product_max_weight = 0.20` 가 binding. us_growth 후보 ETF 22 개 중 score top-3 (core 1 + satellite 2) 에 각 20% 배분 → 60% 만 채워짐.
4. **Fallback 단계**: 잔여 10.60% 가 same-bucket sibling (kr_eq, dm_ex_us, em, us_value) 에 pro-rata 분배.

### 3.3 정책 영역 판정

| 측면 | D-02 영역? | 별도 영역 |
|---|:---:|---|
| us_growth target 70.60% 자체의 적정성 | ❌ | **D-12 (deferred — 자산군 cap)** + 신규 candidate |
| ETF single product cap 20% 의 적정성 | ❌ | **신규 D-16 candidate (product-level cap policy)** |
| asset target → product allocation 차이 (드리프트 메커니즘 자체) | ❌ | **신규 D-15 candidate (asset target vs product allocation drift)** |
| 자산 쏠림 monitoring | ❌ | **신규 D-17 candidate (asset concentration monitoring)** |
| Projection drift threshold 운영값 | ✅ | (D-02 closure 시점 결정) |

**판정**: **10.60% drift 는 D-02 가 아닌 product allocation 단계 이슈**. D-02 closure 조건에서 명시 분리 필요.

---

## 4. Decision Recommendation (D-02)

### 4.1 enforcement 모드별 권장

| operating_mode | enforcement | drift exceed → |
|---|---|---|
| `relaxed_diagnostic` | **`telemetry_only`** (현재) | quality_status 영향 없음. drift 값은 telemetry 보존. |
| `review` | `warning` | drift exceed → WARNING. (review_required 까지 안 감) |
| `production` | `review_required` | drift exceed → REVIEW_REQUIRED. (legacy 동작) |

본 권장은 yaml `tdf_2060.yaml::drift_thresholds.modes` 에 이미 구조화되어 있음. 운영 단계 전환 시 `operating_mode` 값만 변경하면 자동 매핑.

### 4.2 D-02 가 다루는 것 / 다루지 않는 것

```
D-02 closure 대상 (직접):
  ✅ projection drift threshold 운영값 (DEFAULT 0.03 / 0.05 유지 여부)
  ✅ long-only clipping 으로 인한 projection impact 의 운용 수용 여부
  ✅ relaxed_diagnostic → review/production 전환 시 enforcement 정책

D-02 closure 대상 아님 (분리):
  ❌ product single cap 으로 발생한 selection/quality drift (10.60%)
  ❌ us_growth target 70.6% 자체의 운용 수용 여부
  ❌ 상품 universe 부족 / cap binding 문제
  ❌ 자산군 band 재도입 여부 (D-11/D-12 deferred 영역)
```

### 4.3 신규 candidate (정식 등록 아님)

본 brief 는 candidate 만 제시. 정식 Decision Register 등록 전까지 **total count / status distribution 영향 없음**.

| candidate id | 영역 | 핵심 결정 |
|---|---|---|
| **D-15 (candidate)** | Asset target vs product allocation drift policy | product cap binding 으로 자산군 target 을 다 채우지 못할 때 (예: us_growth target 70.6% → 60.00%) fallback 허용 여부 / 임계 / 체계 |
| **D-16 (candidate)** | Product-level single cap policy | `single_product_max_weight` 20% 유지 / 완화 / 자산군별 차등화 |
| **D-17 (candidate)** | Asset concentration monitoring | us_growth 70%+ target 같은 쏠림을 monitoring 만 할지, 향후 band 로 제어할지 (D-11/D-12 reactivation 여부 포함) |

> ⚠️ D-15/D-16/D-17 은 **정식 Decision Register 항목이 아니라 telemetry enhancement / future decision candidate**. 정식 등록 시 register 의 total count (현재 14) 와 status distribution 을 별도 갱신해야 함.

---

## 5. D-02 Closure 조건 — **4 조건 모두 충족 (2026-05-08)**

1. ✅ **projection drift source 가 long_only_clipping 으로 설명 가능** (relaxed ETF: redistribution=5 + long_only_clipping=2, 모두 long-only 정책의 직접 결과)
2. ✅ **relaxed mode 에서 `bucket_constraint` / `asset_upper_bound` source 발생 0건** (`relaxed_mode_unexpected_sources = []`)
3. ✅ **production / review mode 의 enforcement 정책 확정** (운용역 승인 2026-05-08: `relaxed=telemetry_only` / `review=warning` / `production=review_required`, asset 3% / bucket 5%. yaml `drift_thresholds.modes` 에 이미 구조화)
4. ✅ **selection / product cap drift 가 별도 decision candidate 로 분리** (D-15/D-16/D-17 candidate. 정식 Decision Register 등록은 D-02 closure 와 독립적인 후속 결정)

### 5.1 closure 적용 내역 (2026-05-08)

`docs/phase_d_d02_signoff_patch_plan.md §3` 의 4개 파일 patch 적용:

- `docs/investment_decision_register.md` — D-02 status `pending_rerun → closed`, 분포 `pr 1→0 / closed 5→6`, blocker 4→3, §2 본문 + §5 변경 이력 갱신
- `HANDOFF.md` — blocker 표기 D-03/D-08/D-09 (3건)
- `memory/project_state.md` — Decision Register 분포 + closure 기록
- `docs/phase_d_d02_drift_closure_brief.md` (본 문서) — sign-off note + closure 조건 충족 표기

**코드 / config / tests / out 산출물 무변경** — yaml `drift_thresholds` 가 이미 본 정책과 정합.

### 5.2 후속 (D-02 와 독립)

- D-15/D-16/D-17 정식 Decision Register 등록 여부는 별도 결정. 등록 시 `register total count 14 → 17` 갱신 + `§5 변경 이력` 기록.
- `relaxed → review/production` mode 전환 시 `tdf_2060.yaml::operating_mode` 값 1줄 변경. 추가 코드/yaml 변경 불필요.

---

## 7. Sign-off note (2026-05-08)

```
─────────────────────────────────────────────────────────────────────────
D-02 closed by 운용역 sign-off — 2026-05-08

승인 정책 (전문):
- relaxed_diagnostic: enforcement = telemetry_only
                       drift 초과는 quality_status 영향 없음. 값은 telemetry 보존.
- review            : enforcement = warning
- production        : enforcement = review_required
- asset drift threshold  = 3%
- bucket drift threshold = 5%
- scope             = projection drift only
- product cap / selection fallback drift 는 D-15/D-16/D-17 candidate 로 분리

closure 4 조건 모두 충족:
  ✅ projection drift source = long_only_clipping (설명 가능)
  ✅ relaxed mode unexpected source = 0
  ✅ enforcement 정책 운용역 승인 완료
  ✅ product cap drift 가 별도 candidate 로 분리

코드 / config / tests / out 무변경.
yaml `tdf_2060.yaml::drift_thresholds` 가 이미 본 정책과 정합.
─────────────────────────────────────────────────────────────────────────
```

---

## 6. 한 줄 요약

> **D-02 는 "projection drift 가 정책 (long-only) 의 직접 결과로 설명 가능한지" 만 다루는 결정.**
> 현재 projection drift 3.00% 는 ✅ 설명 가능. 단 closure 전 (a) production/review enforcement 운영값 확정,
> (b) quality drift 10.60% 를 별도 candidate (D-15~17) 로 분리 등록 필요.
> **D-02 status: `pending_rerun` 유지**.
