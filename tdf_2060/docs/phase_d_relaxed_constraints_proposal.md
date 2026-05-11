# Phase D — Relaxed Constraints Proposal

작성일: 2026-05-08. **분석 / 변경안만**. config·코드·테스트 변경 없음.

> 운용역 정책 확정 (2026-05-08): TAA 이후 bucket range (75~85% / 15~25%) hard constraint 해제,
> 개별 자산군 cap/floor/band 미적용. 본 단계 hard constraint = **long-only + sum-to-100%** 만 유지.
> 80/20 SAA glidepath 는 reference / initial SAA 로만 보존.

본 문서는 (1) 현재 제약 위치 전수 매핑, (2) 비활성화 / 유지 분류, (3) Decision Register 재정렬,
(4) Warning 정책 재정의, (5) config diff 초안, (6) rerun 계획을 단일 시트로 정리한다.

---

## 1. 운용역 확정 정책 (재기록, 2026-05-08 revise)

| # | 정책 |
|---|---|
| 1 | 2060 glidepath 80/20 = reference / starting SAA |
| 2 | **TAA 적용 허용범위 일괄 해제** — bucket range (75~85/15~25) + per-asset tilt 폭 제한 (±3%p) 모두 hard constraint **미적용** |
| 3 | 개별 자산군 비중 0% **모두 허용** |
| 4 | 개별 자산군 음수 비중 **금지** |
| 5 | 개별 자산군별 cap/floor/band **미적용** (현 단계) |
| 6 | 전체 weight 합계 = 100% **유지** |
| 7 | **현 단계 hard constraint = long-only + sum-to-100%** |
| 8 | 자산군별 band, bucket range, TAA 허용범위(per-asset tilt 폭 포함)는 **추후 도입** |

> 본 revise (2026-05-08) 의 핵심 변경: 이전 proposal 에서 `taa_policy.constraints.per_asset_max_tilt = 0.03` 를
> "유지 hard constraint" 로 분류했던 것을 정책 #2 / #8 정합성 위해 **비활성 대상으로 이동**.
> `tilt_sum_must_be_zero` 는 정책 제약이 아닌 **sum-to-100% 회계 정합성 장치** 임을 명확화 후 유지.

---

## 2. 현재 config 제약 위치 — 전수 인벤토리

### 2.1 yaml 위치

| 제약 | yaml 경로 | 현재 값 |
|---|---|---|
| **strategic_allocation** (80/20) | `tdf_2060.yaml:11` strategic_allocation | equity=0.80, fixed_income=0.20 |
| **taa_bounds (bucket)** | `tdf_2060.yaml:17` taa_bounds | equity_min/max=0.75/0.85, fixed_income_min/max=0.15/0.25 |
| **reference_weights** (MVO warm-start) | `tdf_2060.yaml:24` reference_weights | 9개 자산 (합 1.0) |
| **weight_bounds (per-asset MVO 제약)** | `tdf_2060.yaml:47` weight_bounds | 9개 자산 min/max — kr_equity [0.03, 0.20], us_growth [0.05, 0.40] 등 |
| **final_asset_bounds (per-asset 최종)** | `tdf_2060.yaml:61` final_asset_bounds | 9개 자산 min/max — kr_equity [0.02, 0.22], dm_ex_us [0.04, 0.27] 등 |
| **MVO weight_sum_must_equal** | `optimization_constraints.yaml:34` | 1.0 |
| **MVO non_negative** | `optimization_constraints.yaml:36` | true |
| **MVO equity_sum** | `optimization_constraints.yaml:38` | min=0.75, max=0.85 |
| **MVO fixed_income_sum** | `optimization_constraints.yaml:41` | min=0.15, max=0.25 |
| **region_lower_bounds (MVO)** | `optimization_constraints.yaml:46` | enabled=false (이미 비활성) |
| **TAA bucket_tilts** | `taa_policy.yaml:30` regime_tilts.{1~4}.bucket_tilts | regime별 ±5%p |
| **TAA asset_tilts** | `taa_policy.yaml:33` regime_tilts.{1~4}.asset_tilts | regime별 자산별 |
| **TAA equity_total_min/max** | `taa_policy.yaml:81` constraints.equity_total_min/max | 0.75/0.85 |
| **TAA fixed_income_total_min/max** | `taa_policy.yaml:84` | 0.15/0.25 |
| **TAA per_asset_max_tilt** | `taa_policy.yaml:88` | 0.03 (±3%p) |
| **TAA tilt_sum_must_be_zero** | `taa_policy.yaml:91` | true (cash neutral) |
| **ust30 fallback_policy** | `asset_mapping.yaml:108` | explicit_proxy_only (= no_silent_fallback / hard_error_if_missing) |
| **ust30 db_dataset_id** | `asset_mapping.yaml:112` | 201 (BRFUT004 direct mapping) |

### 2.2 코드 위치

| 제약 / 임계 | 코드 경로 | 동작 |
|---|---|---|
| sum_to_1 (MVO) | `optimization/optimizer.py:131` | SLSQP equality constraint |
| non_negative (MVO) | `optimization/optimizer.py:103-107` | bounds = (lb, ub), lb≥0 |
| per-asset bounds (MVO) | `optimization/optimizer.py:106` | `constraints.bounds.get(k, (0, 1))` |
| bucket sum (MVO) | `optimization/optimizer.py` | `equity_sum`, `fixed_income_sum` constraints (ineq) |
| bucket bounds (TAA) | `taa/overlay.py:88-91` | `equity_total_min/max` 등 |
| bucket bounds (projection) | `taa/projection.py:72-84, 148` | SLSQP ineq |
| asset bounds (projection input) | `taa/tool.py:42-49`, `taa/projection.py:71-80` | `final_asset_bounds → weight_bounds → (0, 1)` 우선순위 |
| **long-only (projection)** | `taa/projection.py:80, 142` | `lb, ub = asset_bounds.get(k, (0, 1))` |
| **sum_to_1 (projection)** | `taa/projection.py:124, 203` | `_is_feasible` weight sum check |
| sum_to_1 (validator) | `portfolio/validator.py:73` | `abs(s_asset - 1.0) > 1e-4` → issue |
| **non_negative (validator)** | `portfolio/validator.py:84-98` | asset/product weight < -1e-12 → issue |
| bucket bounds (validator) | `portfolio/validator.py:101-120` | `taa_bounds` 위반 시 issue |
| final_asset_bounds (validator) | `portfolio/validator.py:122-132` | warning만 |
| projection drift (validator) | `portfolio/validator.py:138-148` | warning |
| asset_drift_threshold | `portfolio/quality.py:32` | DEFAULT=0.03 (3%p) |
| bucket_drift_threshold | `portfolio/quality.py:33` | DEFAULT=0.05 (5%p) |
| ust30 strict_error_b | `optimization/cma.py` + `repositories/db_market_data.py` | BRFUT004 미존재 시 ValueError |
| policy_review_items 휴리스틱 | `reporting/review.py:198-257` | zero weight, near_bound, projection drift, lookback, cash_placeholder, no_candidates |
| 자산배분 요약 (review) | `reporting/review.py:335` | bucket target = `taa_bounds.fixed_income_total` (default {min:0.15, max:0.25}) |

### 2.3 테스트 의존

| 테스트 | 위치 | 의존 제약 |
|---|---|---|
| `test_equity_sum_in_bucket_bounds` | `test_mvo_max_sharpe.py:33` | equity ∈ [0.75, 0.85] |
| `test_taa_projection_enforces_bucket_bounds` | `test_phase_c3_projection.py:125` | bucket_bounds 강제 (fixture 직접 전달) |
| `test_e2e_etf` bucket 검증 | `test_e2e_etf.py:52-54` | equity/fixed_income bucket 합계 |
| `test_phase_b5plus_quality.py` | quality_status 분기 | drift threshold 의존 |
| `test_review_summary_contains_required_keys` 등 (review packet) | `test_phase_c4_review.py` | review packet schema (bucket bound 표기 영향) |

⚠️ config 실제 변경 시 위 테스트들이 깨질 가능성 높음. **사용자가 "tests 기대값 변경 금지" 라고 명시했으므로 본 분석 단계에서는 변경 제안만 하고 실제 적용은 별도 승인 후 진행.**

---

## 3. 비활성화 대상 제약

| 제약 | 처리 방안 | 영향 위치 |
|---|---|---|
| `taa_bounds.equity_min/max` | yaml에서 제거 OR 0/1로 완화 | tdf_2060.yaml + validator + taa/overlay + taa/tool |
| `taa_bounds.fixed_income_min/max` | 동일 | 동일 |
| `optimization_constraints.constraints.equity_sum` | 비활성 (block 통째 주석/삭제) | optimization_constraints.yaml + optimizer.py |
| `optimization_constraints.constraints.fixed_income_sum` | 동일 | 동일 |
| `weight_bounds` (per-asset min/max) | min=0, max=1 로 완화 OR yaml에서 제거 | tdf_2060.yaml + optimizer.py + taa/tool.py |
| `final_asset_bounds` | yaml에서 제거 OR telemetry only | tdf_2060.yaml + validator + taa/tool + reporting/review |
| `taa_policy.constraints.equity_total_min/max` | 0/1 로 완화 (long-only + sum-to-1만 남기기) | taa_policy.yaml + taa/overlay + taa/projection |
| `taa_policy.constraints.fixed_income_total_min/max` | 동일 | 동일 |
| `quality.py asset_drift_threshold (3%)` | 비활성 OR 매우 큰 값으로 사실상 무효화 | quality.py |
| `quality.py bucket_drift_threshold (5%)` | 동일 | quality.py |
| `policy_review_items` 중 `zero weight`, `near_bound`, `violation_below/above` | 발생 안 함 (bound 없음) 또는 info-only | reporting/review.py |
| **`taa_policy.constraints.per_asset_max_tilt = 0.03`** | **비활성 (1.0 으로 완화 권장; 아래 §3.1 참조)** | taa_policy.yaml + taa/overlay.py + reporting/review.py |
| **per-asset tilt 초과 warning** | **비활성** (warn_if_per_asset_tilt_violated=false) | taa_policy.yaml validation 블록 + taa/overlay.py |

### 3.1 per_asset_max_tilt 처리 — option 비교 / 추천

| option | 동작 | 코드 영향 | 평가 |
|---|---|---|---|
| **A. null / disabled** | yaml에서 키 제거 또는 null. 코드는 None 시 ineq 추가 안 함. | taa/overlay.py 가 `self.constraints.get("per_asset_max_tilt")` 가 None 이면 skip 하도록 분기 추가. 1줄 수정. | 의미가 명확하지만 기존 code path 분기 추가 필요. |
| **B. 1.0 (사실상 비제약)** ✅ **추천** | `per_asset_max_tilt: 1.0`. 100%p tilt 까지 허용 = math 상 무제약. | 코드 변경 0줄. yaml 1줄 변경. | 가장 단순. constraint 자체 구조 보존, 추후 band 재도입 시 값만 0.03 등으로 되돌리면 끝. |
| C. 코드에서 항상 skip | 항상 ineq 미적용. yaml 무관. | taa/overlay.py 에 skip 로직 hard-code (yaml 무시) — 정책-config 분리 깨짐. | 비추천 (config-first 원칙 위반). |

**추천 = Option B**. 이유:
1. yaml 1줄 변경만으로 정책 적용 / 회귀 가능 (추후 band 재도입 시 값만 0.03 으로 복원).
2. taa/overlay.py 의 ineq 구조 그대로 유지 — 코드 변경 없음.
3. SLSQP solver 에 해롭지 않음 (1.0 절대값 ineq 는 항상 만족 → 사실상 무효).
4. 단, sum-to-100% 정합성은 별도 — `tilt_sum_must_be_zero` (§4 참조) 가 담당. per_asset_max_tilt 와 무관.

**sum-to-100% 정합성 처리**: `tilt_sum_must_be_zero=true` 가 SAA 합 1.0 + tilt 합 0 = TAA 합 1.0 을 보장.
per_asset_max_tilt 완화는 개별 tilt 크기에만 영향을 주고 합계에는 영향 없음. normalization 추가 필요 없음.

---

## 4. 유지 대상 hard constraint

| 제약 | 위치 | 유지 이유 |
|---|---|---|
| **sum-to-100%** | optimizer.py:131, projection.py:124, validator.py:73 | 운용역 정책 #6 |
| **long-only (non-negative)** | optimizer.py:103, projection.py:80, validator.py:84-98 | 운용역 정책 #4 |
| **ust30 strict_error_b (BRFUT004)** | cma.py + db_market_data.py | D-04 closed |
| **DB source missing → hard error** | repositories/db_market_data.py | 데이터 무결성 |
| **NaN/invalid return data** | repositories/db_market_data.py + cma.py | 수치 안정성 |
| **optimizer convergence failure** | optimizer.py | MVO solver 실패는 항상 issue |
| **projection convergence failure** | taa/projection.py | TAA projection 실패는 항상 issue |
| **product_weight_sum mismatch** | validator.py:78-82 | 상품 단계 closure 보장 |
| **TAA `tilt_sum_must_be_zero`** | taa/overlay.py | **§4.1 참조 — 회계 정합성 장치 (정책 제약 아님)** |
| **80/20 SAA glidepath** | tdf_2060.yaml strategic_allocation, reference_weights | reference / initial SAA / MVO warm-start |

> ⚠️ **이전 proposal 의 `TAA per_asset_max_tilt = 0.03` 항목은 본 표에서 제거됨.** 운용역 정책 #2/#8 (TAA 허용범위 일괄 해제) 에 따라 §3 비활성화 대상으로 이동.

### 4.1 `tilt_sum_must_be_zero` 해석 — 정책 제약 vs 회계 장치

다음 두 해석을 명확히 구분.

| 해석 | 내용 | 본 정책 적용 |
|---|---|---|
| (a) **TAA 폭 제한 (정책 제약)** | "TAA 가 SAA 를 net 으로 변경하지 못하게 함" | ❌ 적용 안 함 (정책 #2: TAA 허용범위 해제) |
| (b) **회계 정합성 장치 (math)** | "SAA 합 1.0 + tilt 합 0 = TAA 합 1.0 보장. tilt 합이 0 이 아니면 TAA 합 ≠ 1.0 → 별도 normalization 필요" | ✅ **유지** (정책 #6: 합 1.0 유지) |

**최종 해석 = (b) 회계 정합성 장치**. 근거:
1. SAA(합=1.0) + tilt → TAA. 각 자산은 SAA + 자산별 tilt 로 계산.
2. TAA 합 = SAA 합 + tilt 합 = 1.0 + tilt 합. **TAA 합이 1.0 이려면 tilt 합 = 0 필요**.
3. tilt 자체의 부호·크기는 무관 (자산별로 +5%p, -3%p, +1%p 등 자유). 합만 0 이면 됨.
4. 만약 `tilt_sum_must_be_zero = false` 로 풀면 TAA 합이 1.0 ≠ 가능 → 이후 sum=1 normalization (rescaling) 필요.
   normalization 로직은 현재 코드에 없음. 추가하면 모든 자산이 비율 변동 → 운용역 의도와 어긋날 수 있음.
5. **결론**: tilt_sum=0 은 "TAA 적용 후에도 자산비중 합 100% 유지" 라는 정책 #6 을 그대로 만족시키는 기존 메커니즘. 변경 불필요.

→ 유지. **단** 본 항목이 "TAA 폭 제한" 으로 오해되지 않도록 yaml 주석 갱신 권장 (§7.3).

---

## 5. Decision Register 재정렬 — 변경안

### 5.1 항목별 status / decision 변경

| # | 항목 | **현재** | **변경 후** | decision |
|---|---|---|---|---|
| D-01 | (구) `final_asset_bounds` 운영값 확정 | open | **closed (재정의)** | 새 제목: **Hard constraint set definition**. decision: hard constraint = `long-only + sum-to-100%`. final_asset_bounds·bucket range·per-asset band 는 reference/telemetry 만. |
| D-02 | `max_abs_projection_drift` 3% 임계 | open | **pending_rerun** | bucket·asset bound 제거 후 projection 자체가 거의 trigger 안 될 가능성. relaxed rerun 결과 본 후 임계 재평가. |
| D-10 | ust30/kr_t10 final 0% 허용 | open | **closed** | 모든 개별 자산군 0% 허용. negative weight 만 금지. |
| D-11 | dm_ex_us 4% lower bound | open | **deferred** | 현 단계 미적용. 자산군별 band 도입 단계에서 재논의. |
| D-12 | us_value 30% cap | open | **deferred** | 동일. |

### 5.2 신규 status 도입

| status | 의미 |
|---|---|
| `deferred` | 결정 완료 (현 단계 미적용) + 추후 band 재도입 시 재논의 대상 |
| `pending_rerun` | 결정 보류 (다른 변경의 영향을 본 후 재평가) |

### 5.3 새 분포

| status | count | D-ID |
|---|---:|---|
| open | **3** | D-03, D-13, D-14 |
| pending_external | **3** | D-06, D-08, D-09 |
| pending_rerun | **1** | D-02 |
| deferred | **2** | D-11, D-12 |
| closed | **5** | D-01, D-04, D-05, D-07, D-10 |
| **total** | **14** | (변경 없음) |

이전: open 8 / pending_external 3 / closed 3 = 14
변경: open 3 / pending_external 3 / pending_rerun 1 / deferred 2 / closed 5 = 14 ✓

### 5.4 Phase D 종료 조건 갱신

이전 blocker: D-01/02/03/08/09/10/11/12 (8건).
변경 후 blocker: **D-02 (pending_rerun → closed), D-03, D-08, D-09 (4건)**.

D-01/D-10 closed, D-11/D-12 deferred 로 blocker에서 빠짐.

---

## 6. Warning 정책 재정의 변경안

### 6.1 demote — 더 이상 decision-required 아님

| 기존 warning | 처리 |
|---|---|
| `kr_treasury_10y final weight is 0.00%; confirm whether zero allocation is acceptable` | **삭제** (정책 #3: 0% 허용) |
| `us_treasury_30y final weight is 0.00%` | **삭제** |
| `<asset> final weight X% is near a final bound` | **삭제** (정책 #5: final_asset_bound 미적용) |
| `final_asset_bound: <asset>=X outside [...]` | **삭제** |
| `equity bucket X outside [0.75, 0.85]` | **삭제** (정책 #2: bucket range 해제) |
| `fixed_income bucket X outside [0.15, 0.25]` | **삭제** |
| `equity total X outside TAA range` / `fixed_income total X outside TAA range` | **삭제** (정책 #2) |
| **`<asset> tilt X% exceeds per_asset_max_tilt 3%`** | **삭제** (정책 #2: TAA per-asset tilt 폭 제한 해제) |
| `<asset> cap clipping` (`product_cap_clipping` cause) | **info-only** (telemetry only) |

### 6.2 keep — critical / hard error 유지

| Warning / Error | severity | 이유 |
|---|---|---|
| `<n> asset/product weights are negative` | issue | 운용역 정책 #4 |
| `asset_weight sum X != 1.0` | issue | 운용역 정책 #6 |
| `product_weight sum X != 1.0` | issue | closure 무결성 |
| DB source 미존재 | issue (raise) | 데이터 무결성 |
| `BRFUT004 missing` | issue (raise) | D-04 |
| NaN/invalid return | issue (raise) | 수치 안정성 |
| optimizer convergence failure | issue (raise) | solver 실패 |
| projection failure (`projection_success=False`) | issue | math 정합성 |

### 6.3 keep — informational telemetry (decision_required=False 로)

| 항목 | severity |
|---|---|
| `taa_projection_used: max_abs_projection_drift=X%` | warning (info) |
| `negative weights before projection: ...` | warning (info, projection 으로 이미 0% 처리됨) |
| `bucket after projection: equity=X%, fixed_income=Y%` | warning (info) |
| `fallback_used: <asset> X redistributed → ...` | warning (info) |
| `max_abs_asset_weight_drift: X%` | warning (info) |
| `quality_status: ...` | warning (info) |
| ust30 lookback obs short (D-03) | warning (info, decision_required=True 유지) |
| `cash_placeholder_weight > 0` | warning (info, decision_required=True 유지 — 의미 있음) |
| `no_candidates_in_universe` | warning (info, decision_required=True 유지) |

### 6.4 quality_status 임계 재정의

D-02 pending_rerun 결정 전까지 임시:
- `clean`: fallback 미사용 + projection 미사용
- `warning`: fallback 사용 OR projection 사용 (drift 무관)
- `review_required`: projection_success=False, cash_placeholder>0, no_candidates 발생, NaN

기존 임계 (`asset_drift_threshold=3%`, `bucket_drift_threshold=5%`)는 D-02 결정 시 재계산.

---

## 7. Config diff 초안 (NOT applied)

### 7.1 `tdf_engine/config/tdf_2060.yaml`

```diff
 strategic_allocation:
   equity: 0.80           # ← reference / starting SAA 로만 유지
   fixed_income: 0.20

-# ── TAA 허용 범위 ───────────────────────────────────────────────────────
-taa_bounds:
-  equity_min: 0.75
-  equity_max: 0.85
-  fixed_income_min: 0.15
-  fixed_income_max: 0.25
+# ── TAA 허용 범위 ───────────────────────────────────────────────────────
+# Phase D relaxed: bucket range hard constraint 비활성. reference 만 보존.
+taa_bounds_reference:           # ← 이름 변경, 실제 enforce 안 함
+  equity_min: 0.75
+  equity_max: 0.85
+  fixed_income_min: 0.15
+  fixed_income_max: 0.25
+  enforced: false               # ← 신규 플래그

 reference_weights:
   ...                           # 변경 없음 (warm-start로 유지)

-weight_bounds:
-  kr_equity:          { min: 0.03, max: 0.20 }
-  us_growth_equity:   { min: 0.05, max: 0.40 }
-  ...
+# Phase D relaxed: per-asset bounds 비활성. long-only 만 hard.
+weight_bounds:
+  # 모든 자산 [0, 1]. 명시적 bound 제거.
+  _disabled: true
+  _reference_only:              # ← 추후 band 재도입 시 사용할 reference
+    kr_equity:          { min: 0.03, max: 0.20 }
+    us_growth_equity:   { min: 0.05, max: 0.40 }
+    ...

-final_asset_bounds:
-  kr_equity:          { min: 0.02, max: 0.22 }
-  ...
+# Phase D relaxed: final_asset_bounds 비활성.
+final_asset_bounds:
+  _disabled: true
+  _reference_only:
+    kr_equity:          { min: 0.02, max: 0.22 }
+    ...
```

대안: yaml에서 키 자체 제거 + 코드에서 `tdf_config.get("weight_bounds")` → 없으면 `(0,1)` default. 단순하지만 reference 기록 보존 안 됨. 사용자 선호에 따라 선택.

### 7.2 `tdf_engine/config/optimization_constraints.yaml`

```diff
 constraints:
   weight_sum_must_equal: 1.0
   non_negative: true

-  # bucket 합계 (tdf_2060.taa_bounds 와 정합)
-  equity_sum:
-    min: 0.75
-    max: 0.85
-  fixed_income_sum:
-    min: 0.15
-    max: 0.25
+  # Phase D relaxed: bucket 합계 hard constraint 비활성.
+  # equity_sum / fixed_income_sum 키 자체 제거 또는 무력화.
+  # equity_sum: null
+  # fixed_income_sum: null

   region_lower_bounds:
     enabled: false             # 변경 없음
```

### 7.3 `tdf_engine/config/taa_policy.yaml`

```diff
 constraints:
-  equity_total_min: 0.75
-  equity_total_max: 0.85
-  fixed_income_total_min: 0.15
-  fixed_income_total_max: 0.25
+  # Phase D relaxed: bucket bound 비활성. projection 은 long-only + sum-to-1 만.
+  equity_total_min: 0.0
+  equity_total_max: 1.0
+  fixed_income_total_min: 0.0
+  fixed_income_total_max: 1.0

-  # 자산군 단일 tilt 폭 (절대값)
-  per_asset_max_tilt: 0.03        # ±3%p
+  # Phase D relaxed: per-asset tilt 폭 제한 비활성 (정책 #2/#8).
+  # Option B 채택: 1.0 으로 완화 (= 사실상 비제약). 코드 path/구조 보존.
+  # 추후 자산군별 band 재도입 시 0.03 등으로 복원하면 재활성.
+  per_asset_max_tilt: 1.0

-  # tilt 합 = 0 (cash neutral) — 자동 검증
-  tilt_sum_must_be_zero: true
+  # tilt 합 = 0 — sum-to-100% 회계 정합성 장치 (정책 #6).
+  # TAA 폭 제한이 아닌 "SAA 합 1.0 + tilt 합 0 = TAA 합 1.0 보장" 메커니즘.
+  # 본 항목 변경 시 별도 normalization 로직 필요 → 유지.
+  tilt_sum_must_be_zero: true

 validation:
-  warn_if_bucket_bound_violated: true
-  warn_if_per_asset_tilt_violated: true
+  # Phase D relaxed: bucket bound / per-asset tilt 위반 자체가 정의 안 됨.
+  warn_if_bucket_bound_violated: false
+  warn_if_per_asset_tilt_violated: false
   warn_if_unknown_regime: true
```

### 7.4 코드 변경안 (제안만, 미적용)

| 파일 | 변경 |
|---|---|
| `portfolio/validator.py:101-120` | bucket_bounds 검증 블록 비활성 (taa_bounds 가 없거나 enforced=false 면 skip) |
| `portfolio/validator.py:122-132` | final_asset_bounds 검증 블록 비활성 (`_disabled: true` 면 skip) |
| `portfolio/quality.py:32-33` | DEFAULT_ASSET_DRIFT_THRESHOLD = 1.0 (사실상 무효화) — D-02 결정 후 재설정 |
| `optimization/tool.py:72` | `weight_bounds` 가 `_disabled: true` 면 모든 자산 (0, 1) |
| `taa/tool.py:42-49` | `final_asset_bounds._disabled: true` 면 (0, 1) |
| `taa/overlay.py:88-91`, `taa/projection.py` | bucket_bounds 가 (0, 1) 이면 ineq 추가 안 함 (또는 그대로 두면 항상 만족이라 무해) |
| **`taa/overlay.py` per_asset_max_tilt 적용 부분** | **per_asset_max_tilt = 1.0 일 때 기존 ineq 자동 만족 → 코드 변경 불필요 (Option B 의 장점). 단 `violations` 검출 로직이 `per_asset_max_tilt < 1.0` 일 때만 활성화되도록 가드 1줄 추가 권장** |
| `reporting/review.py:198-257` | policy_review_items 항목 1, 2, 3, 4 (zero weight, violation_below, violation_above, near_bound) 비활성화 |
| `reporting/review.py:335` | 자산배분 요약의 bucket target_range 표기를 `enforced=false` 시 "(reference, **not enforced — sanity monitoring only**)" 로 |
| **`reporting/review.py` warning register linker** | **per_asset_tilt 초과 / bucket bound outside / final_asset_bound outside 패턴 → linked_decision=null + decision_required=False 로 demote (현재 D-IDs 매핑 룰 보존하되 출력 severity 만 info 로)** |

---

## 8. Rerun 계획

### 8.1 사전 작업 (별도 PR, 본 분석 단계 외)

1. config 3종 변경 적용 (위 7.1~7.3)
2. 코드 변경 적용 (위 7.4)
3. 테스트 영향 점검 — **삭제/skip 이 아니라 새 정책 기준으로 갱신**:

   **(a) 유지해야 할 테스트** (정책 변경 무관, 본 변경 후에도 동일 통과 기대):

   | 테스트 / 검증 항목 | 위치 | 검증 |
   |---|---|---|
   | long-only (음수 weight 검출) | `test_portfolio_validator.py`, `validator.validate` 의 non_negative 브랜치 | 정책 #4 |
   | sum-to-100% (asset / product) | 동일 | 정책 #6 |
   | NaN / invalid return data 차단 | `test_phase_c1_db_validation.py`, `test_phase_c_db.py` | 데이터 무결성 |
   | DB source missing → ValueError | `test_phase_c_db.py`, `test_cma_builder.py` | 무결성 |
   | BRFUT004 direct mapping (`db_dataset_id=201`) | `test_config_loader.py::test_us_treasury_30y_explicit_proxy_only`, `test_phase_c_db.py` | D-04 |
   | optimizer / projection convergence | `test_mvo_max_sharpe.py` (수렴 확인 부분), `test_phase_c3_projection.py` | math |
   | review packet schema 키 셋 | `test_phase_c4_review.py::test_review_summary_contains_required_keys` | 표현 호환 |

   **(b) 새 정책 기준으로 갱신해야 할 테스트** (assertion 자체를 새 정책에 맞게 변경):

   | 테스트 | 현재 가정 | 새 기준 |
   |---|---|---|
   | `test_mvo_max_sharpe.py::test_equity_sum_in_bucket_bounds` | equity ∈ [0.75, 0.85] | 사용자 #2 정책 → **assertion 의미 없음**. (i) bucket sum 을 `monitoring telemetry` 로 표기만, 또는 (ii) 새 hard constraint (long-only + sum=1.0) 검증으로 재작성. |
   | `test_phase_c3_projection.py::test_taa_projection_enforces_bucket_bounds` 등 | bucket_bounds 강제 (fixture 주입) | fixture 가 직접 bound 주입 → 테스트 자체는 동작 가능. 단 "relaxed 시 무제약 path" 검증 추가 권장 (ineq 0건 케이스). |
   | `test_e2e_etf.py:52-54` bucket 검증 | bucket 합계 범위 가정 | sum 자체와 long-only 만 검증. bucket 합은 telemetry 로만 출력. |
   | `test_phase_b5plus_quality.py` | drift threshold 3% / 5% 의존 | D-02 결정 후 임계 재설정 시 함께 갱신. 임시 quality_status 분기 변경 (drift 무관) 반영. |
   | `test_phase_c4_review.py` 일부 (policy_review_items) | zero weight / near_bound 항목이 packet 에 포함된다고 가정하는 경우 | 본 항목들 비활성화 → packet 의 해당 entry 가 줄어듦. 테스트의 항목 카운트 / 메시지 substring assertion 업데이트. |
   | `test_phase_c5_golden_parity.py` | golden answer 와 parity (Placement/Velocity/Regime) | 본 단계 영향 없음 — regime 산출은 변경 없음. 통과 유지 예상. |

   **(c) 신규 추가 권장 테스트** (relaxed mode 검증 명시):

   | 테스트명 후보 | 검증 |
   |---|---|
   | `test_phase_d_relaxed_long_only` | 모든 산출에서 weight ≥ 0 |
   | `test_phase_d_relaxed_sum_to_one` | 모든 산출에서 sum = 1.0 ± 1e-4 |
   | `test_phase_d_relaxed_bucket_unconstrained` | bucket sum 이 [0, 1] 범위면 통과 (75-85 강제 안 함) |
   | `test_phase_d_relaxed_per_asset_tilt_unbounded` | per_asset_max_tilt 1.0 시 ineq 자동 만족 |

4. **테스트 기대값 변경은 사용자 명시 승인 후 진행** (사용자 정책 #6 / 본 turn 지시 #6).

### 8.2 산출물 생성 (config 변경 적용 후)

```bash
# ETF 재산출
python -m tdf_engine.tools.build_portfolio \
    --source-root C:/Users/user/Downloads/python/Advisory \
    --source db --as-of-date 2026-03-31 \
    --product-type etf \
    --output-dir out/db_etf_relaxed

# Fund 재산출
python -m tdf_engine.tools.build_portfolio \
    --source-root C:/Users/user/Downloads/python/Advisory \
    --source db --as-of-date 2026-03-31 \
    --product-type fund \
    --output-dir out/db_fund_relaxed

# Review markdown 재렌더 (enhanced)
python -m tdf_engine.tools.render_review \
    --json out/db_etf_relaxed/portfolio_etf_*.json
python -m tdf_engine.tools.render_review \
    --json out/db_fund_relaxed/portfolio_fund_*.json

# 비교 리포트
python -m tdf_engine.tools.render_review \
    --etf-json out/db_etf_relaxed/portfolio_etf_*.json \
    --fund-json out/db_fund_relaxed/portfolio_fund_*.json \
    --comparison-out out/db_review_relaxed/comparison_etf_vs_fund_*.md
```

### 8.3 비교 항목 (constrained vs relaxed)

본 분석 단계에서 비교 리포트를 별도 작성할 계획. 항목:

| 항목 | constrained (현재) | relaxed (예상) |
|---|---|---|
| equity bucket | 82.32% (in [75, 85]) | ? (자유) |
| fixed_income bucket | 17.68% (in [15, 25]) | ? (자유) |
| us_growth final | 39.29% (cap 40% 도달) | ↑ 가능 (50%+?) |
| us_value final | 29.29% (cap 30% 도달) | ↑ 가능 |
| dm_ex_us final | 4.29% (lower 4% 도달) | 더 낮을 수 있음 (sharpe 낮으면 0%) |
| ust30/kr_t10 final | 0% / 0% | 0% 유지 가능성 (regime 1 tilt 음수) |
| 0% 자산군 수 | 2개 | ≥2 (관측 후) |
| negative count | 0 | **0 (필수)** |
| projection_used | True | False 가능성 (bound 없으면 음수도 자체 발생 안 함, MVO 단계에서 long-only) |
| projection drift | 3.00% | 0% 가능성 |
| validation warnings | 8 | ↓ 예상 |
| validation issues | 0 | 0 유지 (필수) |
| quality_status | warning | clean 가능성 |
| product_weight_sum | 1.0 | 1.0 (필수) |
| asset_weight_sum | 1.0 | 1.0 (필수) |
| product allocation 분포 | 26 상품 | 변동 가능 (cap 제거로 single product 비중 ↑) |
| ETF/Fund 자산비중 차이 | 0% (동일) | 0% (동일 — universe 차이만) |
| 운용사 concentration | ETF top=26.87% / Fund top=30% | ↑ 가능성 |

### 8.4 수용 기준 (acceptance) — pass/fail vs sanity monitoring 분리

**Pass/Fail 판정 (hard)** — 위반 시 산출 reject:

| 기준 | 통과 조건 | 근거 |
|---|---|---|
| **기본 무결성** | `asset_weight_sum = 1.0 ± 1e-4`, `product_weight_sum = 1.0 ± 1e-4`, **no negative weight** | 정책 #4 / #6 |
| **DB / 데이터** | BRFUT004 direct mapping 정상, NaN/invalid return 0건, DB source 정상 로드 | D-04, 데이터 무결성 |
| **수렴** | optimizer `solver_status=0`, projection `projection_success=True` | math |

위 3개를 **모두 통과** 해야 산출 채택. 그 외 어느 항목도 hard fail 트리거 아님.

**Sanity Monitoring Range (soft)** — 위반 시 fail 이 아닌 **운용역 검토 flag**:

| 항목 | monitoring 범위 | 이탈 시 |
|---|---|---|
| equity bucket | [60%, 95%] (sanity sense) | 운용역 검토 flag (자동 감지). 정책 변경 또는 자산 쏠림 신호. |
| fixed_income bucket | [5%, 40%] (= 100 - equity sanity) | 동일 |
| 자산 다변화 | 9개 중 ≥6개에 weight > 1% | 2~3개 자산 쏠림 시 운용역 재검토 트리거 |
| 80/20 reference 와의 괴리 | drift < 20%p (참고치) | telemetry 로 노출. fail 아님. |
| ETF/Fund 동일 자산비중 | 차이 = 0.00%p | engine 정합성 검증 (값 다르면 코드 버그) |

⚠️ **위 monitoring range 는 hard constraint 아님.** report 의 monitoring section 으로만 표시. equity 60% 미만 / 95% 초과 자체로 산출 reject 하지 않음.

만약 **자산 쏠림이 심각** 하면 (예: us_growth 70%+) 운용역이 D-13/14 (quant_grade_policy, 운용사 concentration cap) 정책으로 별도 처리 결정 가능. 본 단계 자체가 fail 트리거 하지는 않음.

---

## 9. 위험 / 잠재 이슈

| # | 위험 | 영향 | 완화 |
|---|---|---|---|
| 1 | MVO 가 sharpe 최고 자산 (us_value/growth) 에 70%+ 쏠릴 가능성 | TDF 다변화 정신과 어긋남 | rerun 결과 모니터링. 필요시 D-13/14 활성화 |
| 2 | regime 3 (slowdown) 진입 시 equity 100%+ 시도 (TAA tilt 실패) | bucket 미제약 + per-asset 미제약 → tilt 적용 후 sum=1만 유지 | TAA tilt_sum=0 유지로 직접 100% 도달은 안 됨. 단 SAA 가 이미 80/20 가까우면 적용 가능 |
| 3 | tests 124건 중 일부 fail 예상 | freeze 위반 | 본 단계는 분석만. config 변경 시 사용자 승인 후 test 갱신 |
| 4 | quality_status 임계 미정 (D-02) 상태로 rerun → status 의미 불분명 | 운용역 검토 시 신호 약화 | 임시 임계 (drift_threshold = 1.0 = 사실상 비활성) 후 D-02 결정 |
| 5 | 자산쏠림 현상이 backtest 미진행 상태로 노출 | 미래 drawdown risk | rerun 후 운용역 즉시 검토 + backtest 트리거 가능 |
| 6 | reference (80/20) 와 final 의 괴리가 커도 경고 못함 | 자동 감지 손실 | telemetry 에 reference vs final 차이 노출 (기존 quality.drift 활용) |

---

## 10. 요약 / Sign-off

### 10.1 본 분석 단계 산출

- 본 문서 (`docs/phase_d_relaxed_constraints_proposal.md`) 신설 + 1회 revise (2026-05-08)
  - revise 1: per_asset_max_tilt 를 비활성 대상으로 이동, tilt_sum_must_be_zero 해석 명확화 (회계 장치),
    수용 기준 분리 (hard pass/fail vs sanity monitoring), test 영향 분류 재구조 (유지 vs 갱신),
    config diff 보강 (taa_policy.constraints + validation 블록)
- **코드/config/테스트 무변경**
- pytest 미실행 (변경 없음 — 다음 단계에서 실행)

### 10.2 다음 단계 (운용역 추가 승인 필요)

| 단계 | 내용 | 승인 필요 |
|---|---|---|
| (a) | Decision Register 갱신 (D-01 재정의, D-02 pending_rerun, D-10 closed, D-11/12 deferred) | 운용역 |
| (b) | config 3종 변경 (위 §7.1~7.3) | 운용역 |
| (c) | 코드 변경 (validator·quality·optimizer·taa·reporting; 위 §7.4) | 운용역 |
| (d) | 영향 받는 tests 갱신 또는 skip 처리 | 운용역 (test 기대값 변경 명시 승인) |
| (e) | DB rerun → constrained vs relaxed 비교 → 운용역 검토 | 운용역 |
| (f) | rerun 결과 기반 D-02 임계 결정 (`pending_rerun` → closed) | 운용역 |
| (g) | 운용역 최종 sign-off → Phase D 종료 후보 |

### 10.3 한 줄 요약 (revise 후)

> **본 단계 hard constraint = `long-only` + `sum-to-100%` + ust30 BRFUT004 mapping + DB 무결성 + 수치/수렴 안정성. 그 외 모두 비활성 (bucket range, per-asset bounds, per_asset_max_tilt).**
> `tilt_sum_must_be_zero` 는 정책 제약이 아닌 **sum-to-100% 회계 정합성 장치** 로 유지.
> equity 60~95% 등 범위는 hard constraint 가 아닌 **sanity monitoring** 으로만 표시.
> Decision Register 14건 재분포: open 3 / pending_external 3 / pending_rerun 1 / deferred 2 / closed 5.
> Phase D 종료 blocker 8건 → 4건으로 축소 (D-02·D-03·D-08·D-09).
