# Phase D — D-03 Lookback Policy Review

작성일: 2026-05-08. **Sign-off 적용**: 2026-05-08 — D-03 closed by 운용역 승인 (Option C — Hybrid).
yaml 4 line 추가 (db_sources.yaml). 코드 / tests / out 무변경.

> **결론 (sign-off 후)**: D-03 **closed**. Option C — Hybrid 정책으로 운용:
> return/vol = asset-specific max history, corr = `dropna(how="any")` common intersection.
> min_obs=12, short_history_warning_ratio=0.8. ust30 obs=87 허용 (telemetry).
> yaml 4 line 추가로 정책 명문화 — 기존 코드 동작 변경 없음.

---

## 1. 현재 lookback 사용 위치 — 전수 조사

### 1.1 yaml 위치

| 위치 | 키 | 현재 값 | 용도 |
|---|---|---:|---|
| `db_sources.yaml::asset_rt_vol` | `lookback_years` | **10** | return / vol 산출 시 as_of 기준 max 10년 |
| `db_sources.yaml::asset_rt_vol` | `annualization` | 12 | 월간 → 연환산 |
| `db_sources.yaml::asset_rt_vol` | `computation_mode` | from_timeseries | DB 시계열에서 직접 산출 (file mode 는 from_static_table) |
| `db_sources.yaml::corr_matrix` | `lookback_years` | **10** | corr 산출 시 자산별 max 10년 (intersection 후 실제 obs는 더 짧을 수 있음) |
| `taa_policy.yaml::regime_input` | `composite_window` | **12** | regime placement 의 rolling 평균 window (개월) |
| `db_sources.yaml::regime_source` | `enabled` | false | regime 데이터 source (Phase C 미사용) |

### 1.2 코드 위치

| 위치 | 동작 |
|---|---|
| `db_market_data.py::SanityThresholds.min_obs` | **= 12** (월간 12개월 미만 → `too_few_observations` flag) |
| `db_market_data.py::_query_levels(lookback_years=...)` | as_of 기준 `start = latest − lookback*365.25일` 로 자름 (line 473-474) |
| `db_market_data.py::load_asset_rt_vol` | 각 자산별로 `_monthly_returns(...)` 호출 → 자산별 obs 가 다를 수 있음 (asset-specific) |
| `db_market_data.py::load_corr_matrix` | 모든 자산 monthly returns 를 `pd.concat(axis=1)` → **`dropna(how="any")`** (line 240-242) → **자동 common intersection** |
| `regime/placement.py::PlacementCalculator(window=12)` | regime composite window. `min_periods=window` → 처음 11 row NaN |
| `regime/tool.py` | regime composite_window 사용. `n_obs` 진단 보존 |
| `reporting/review.py::policy_review_items` | `obs_count` 자산이 `< max_obs * 0.8` 이면 "shorter history, confirm lookback policy" warning |
| `tools/build_portfolio.py::dry_run_db_check` | sanity 진단 print (obs count + flags) |

### 1.3 테스트 위치

| 위치 | lookback 의존 |
|---|---|
| `test_phase_c1_db_validation.py` | semantic_type / return_transform 검증 + obs 진단 키 확인 |
| `test_phase_c_db.py` | min_obs / sanity 진단 / fake DB 동등성 |
| `test_phase_c5_golden_parity.py` | regime composite_window=12 |
| `test_placement_velocity.py` | window=12 |

### 1.4 review packet 진단 위치

| 키 | 위치 |
|---|---|
| `diagnostics.db_source.sanity[asset_key]` | obs_count / start_date / end_date / annualized_return / annualized_vol / suspicious_flags |
| review §8 policy_review_items | shorter history warning (현재 ust30 87 vs others 120 → emit) |

---

## 2. 자산별 obs 현황 (relaxed run, ETF, as_of=2026-03-31)

| asset_key | source_name (yaml ticker) | dataset_id | dataseries | obs | start_date | end_date | ann_ret | ann_vol | suspicious_flags |
|---|---|---:|---:|---:|---|---|---:|---:|---|
| `kr_equity` | M2KR INDEX | 144 | 6 | **120** | 2016-04-30 | 2026-03-31 | +13.91% | 26.93% | [] |
| `us_growth_equity` | M2US000G | 11 | 6 | **120** | 2016-04-30 | 2026-03-31 | +16.62% | 17.84% | [] |
| `us_value_equity` | M2US000V | 12 | 6 | **120** | 2016-04-30 | 2026-03-31 | +12.31% | 14.60% | [] |
| `dm_ex_us_equity` | TAD09XU | 63 | 6 | **120** | 2016-04-30 | 2026-03-31 | +9.44% | 14.89% | [] |
| `em_equity` | M2EF | 37 | 6 | **120** | 2016-04-30 | 2026-03-31 | +8.60% | 15.41% | [] |
| `kr_aggregate_bond` | KST0000T | 59 | 9 | **120** | 2016-04-30 | 2026-03-31 | +1.52% | 3.52% | [] |
| `kr_treasury_10y` | KTBITR | 421 | 9 | **120** | 2016-04-30 | 2026-03-31 | +0.99% | 5.94% | [] |
| **`us_treasury_30y`** | **BRFUT004** | **201** | **33** | **🟡 87** | **2019-01-31** | 2026-03-31 | −1.24% | 15.50% | **[]** (단 다른 자산보다 33개월 짧음) |
| `us_high_yield` | LF98TRUU | 401 | 9 | **120** | 2016-04-30 | 2026-03-31 | +6.22% | 7.17% | [] |

**핵심 관찰**:
- 8 자산 = **120 obs** (10년 정확히 lookback). 1 자산 (`us_treasury_30y` = BRFUT004) = **87 obs** (2019-01 시작, 33개월 짧음).
- yaml `lookback_years=10` 으로 동일하게 설정되어 있으나, ust30 은 데이터 자체가 2019-01부터라 lookback 10년이 무의미.
- `obs_count >= min_obs(12)` 모두 통과 → suspicious_flags 빈 배열.
- 그러나 `reporting/review.py` 의 휴리스틱 (`obs < max_obs * 0.8 = 96`) 에 ust30 (87) 만 걸림 → policy_review_items 에 "shorter history" 표시.

### 2.1 corr 산출 시 실제 사용 obs (silent contraction)

`db_market_data.py::load_corr_matrix` (line 240-242):
```python
joined = pd.concat(series_by_name, axis=1)
joined = joined.dropna(how="any")  # ← 자동 common intersection
```

→ corr 입력은 **모든 9 자산이 동일하게 시작하는 월부터** = `2019-01` 부터 = **87 obs** 만 사용.

다른 8 자산 의 33개월 (2016-04 ~ 2018-12) 은 **corr 산출 단계에서 silent 하게 버려짐**. 이 동작은 yaml 에 명시 안 됨.

→ **현재 de facto Hybrid**:
- return / vol: 자산별 max history (8개 자산 120, ust30 87)
- corr: 모든 자산 공통 87 (ust30 시작점 binding)
- min_obs threshold = 12

---

## 3. D-03 핵심 질문 정의 (운용역 결정 대상)

| # | 질문 | 현재 상태 |
|---|---|---|
| **A** | 모든 자산군에 동일 lookback window 를 적용할 것인가? | yaml 동일 (10년). 단 데이터 시작 차이로 실제 obs 다름. |
| **B** | 자산별 가능한 최대 history 를 사용할 것인가? | return/vol = ✓ asset-specific. corr = ✗ common intersection (de facto). |
| **C** | 짧은 history 자산 (예: BRFUT004 obs=87) 을 허용할 것인가? | ✓ 현재 허용. min_obs(12) 만족. 운용역 명시 결정은 안 됨. |
| **D** | return / volatility / correlation lookback 을 동일하게 둘 것인가? | ✗ return/vol vs corr 의 effective lookback 이 다름 (120 vs 87). yaml 미명시. |
| **E** | regime return ticker 와 optimization ticker 의 lookback 차이를 허용할 것인가? | (asset_mapping 의 source_names.optimization vs regime_return 분리. 현재 lookback 정책은 optimization 만 다룸). |

---

## 4. 정책 옵션 비교

### Option A — Common intersection window

- **정의**: 모든 자산이 공통으로 보유한 기간만 사용 (return / vol / corr 모두). 본 케이스에서는 87 obs (2019-01~).
- **장점**: corr / vol / return 의 obs 가 동일 → 통계적 정합성 ↑. PSD 검증 안정.
- **단점**: 8 자산의 33개월 (2016-04~2018-12) 정보 **버림** → return/vol 추정 noise ↑. ust30 같은 짧은 자산이 추가될 때마다 전체 history 가 더 짧아짐 (ratchet effect).
- **구현 변경**: `db_market_data.py::load_asset_rt_vol` 도 corr 와 동일하게 `dropna(how="any")` 적용. 또는 `lookback_years` 와는 별도로 `effective_start_date = max(asset starts)` 산출 후 모든 자산 그 이후로 자름.

### Option B — Asset-specific max history

- **정의**: 각 자산별로 자기 데이터 최대 history 사용. return / vol / corr 모두.
- **장점**: 각 자산 추정치 최대 정보 활용.
- **단점**: corr 산출 시 자산쌍 별 obs 가 다름 → pairwise 정책 필요 (`pd.DataFrame.corr(min_periods=k)` 등). PSD 미보장 가능성. 동일 자산 vs 자산쌍 obs 차이로 사용자 혼동.
- **구현 변경**: `load_corr_matrix` 의 `dropna(how="any")` 제거. `corr(min_periods=12)` 등 pairwise 로 전환. PSD 보정 (nearest PSD) 추가 필요.

### Option C — Hybrid (현재 de facto + 명문화) ✅ **추천**

- **정의**:
  - **return / vol**: 자산별 max history (asset-specific). yaml `lookback_years=10` 은 절단 상한 (10년 초과 시 자름).
  - **corr**: common intersection (모든 자산 공통 기간만). 현재 `dropna(how="any")` 동작 유지 + yaml 명시.
  - **min_obs threshold**: 12 (월간) 유지 또는 운용역 결정 (예: 36, 60).
  - **짧은 history 자산**: 허용. obs 차이가 임계 (예: 80%) 미만이면 telemetry warning. fail 아님.
- **장점**:
  - 현재 코드 동작과 정합 → 변경 최소화
  - return/vol 의 자산별 정보 최대 활용 (8 자산 120 obs)
  - corr 의 통계적 정합성 보장 (PSD 자연 만족)
  - 짧은 history 자산은 명시적으로 telemetry 화 → 운용역이 인지
- **단점**:
  - return/vol 과 corr 의 effective lookback 이 다름 → 운영 시 "왜 corr 만 87 obs 인가?" 질문 발생 → 본 정책 명문화로 해소
- **구현 변경**:
  - yaml `db_sources.yaml::corr_matrix` 에 `intersection_policy: common` 명시 (현재 동작 그대로)
  - yaml `db_sources.yaml::asset_rt_vol` 에 `intersection_policy: asset_specific` 명시
  - yaml `db_sources.yaml` 에 `min_obs: 12` 명시 (현재 코드 default 동일)
  - yaml `db_sources.yaml` 에 `short_history_warning_ratio: 0.8` 명시 (현재 review.py 휴리스틱 동일)
  - 코드는 **변경 없음** (현재 동작 그대로 의미만 yaml 에 명시)

### 비교 요약표

| 측면 | A — Common | B — Asset-specific | **C — Hybrid (추천)** |
|---|---|---|---|
| return/vol effective obs | 87 (모든 자산) | 자산별 120 또는 87 | 자산별 120 또는 87 |
| corr effective obs | 87 (모든 자산) | pairwise 12~120 | 87 (common) |
| 코드 변경 범위 | load_asset_rt_vol 변경 | load_corr_matrix 변경 + PSD 보정 | **없음 (yaml 명시만)** |
| PSD 안정성 | ✓ | ⚠️ pairwise 보정 필요 | ✓ |
| 정보 활용도 | 낮음 (33개월 버림) | 최대 | 중간 (return/vol 만 max) |
| 운영 직관성 | 단순 | 복잡 (자산쌍별 다름) | 두 단계 (return/vol vs corr) 명시 |
| 현재 동작과 정합 | ✗ | ✗ | **✓** |

---

## 5. 권장안 — Option C (Hybrid) + 명문화

### 5.1 정책 명문화 (yaml 변경안 — 미적용)

```yaml
# db_sources.yaml — D-03 정책 명문화 (제안)

asset_rt_vol:
  computation_mode: from_timeseries
  lookback_years: 10
  return_field: value_pct_change
  annualization: 12
  intersection_policy: asset_specific          # ← 신규 명시. 자산별 max history
  min_obs: 12                                  # ← 신규 명시 (코드 SanityThresholds 와 정합)

corr_matrix:
  computation_mode: from_timeseries
  lookback_years: 10
  intersection_policy: common                  # ← 신규 명시. 자산 공통 기간만 (dropna how=any)
  short_history_warning_ratio: 0.8             # ← 신규 명시. obs < max_obs * 0.8 → warning

# (선택) 자산별 lookback override — 현재 미사용, 향후 자산별 차등 도입 시
# assets:
#   - asset_key: us_treasury_30y
#     lookback_years: 7   # BRFUT004 데이터 시작 2019 → 7년이면 충분
```

### 5.2 권장 근거

1. **현재 코드와 정합** → 코드 변경 없이 yaml 표기만으로 정책 적용 가능
2. **운영 투명성** → "왜 ust30 영향으로 모든 자산의 corr obs 가 87 인가" 가 yaml 에 명시되어 의문 해소
3. **D-04 (BRFUT004) closed 와 정합** → ust30 = BRFUT004 direct mapping 유지하면서 짧은 history 의 처리 방식이 명문화됨
4. **변경 범위 최소** → tests / 산출 결과 영향 없음. yaml 4 line 추가만.
5. **D-02 closed 정책과 정합** → drift 가 enforcement_mode = telemetry_only 로 분기. corr lookback 차이가 야기하는 추정 noise 가 telemetry 로 노출되며 quality_status 영향 없음.

### 5.3 권장 운영 파라미터

| 파라미터 | 권장값 | 근거 |
|---|---:|---|
| `asset_rt_vol.lookback_years` | 10 (그대로) | 8 자산 모두 충분히 커버 |
| `asset_rt_vol.intersection_policy` | `asset_specific` | 자산별 max history |
| `asset_rt_vol.min_obs` | 12 | 코드 SanityThresholds default. 운용역이 36 또는 60 으로 강화 가능 |
| `corr_matrix.lookback_years` | 10 (그대로) | 단 effective 는 ust30 시작 기준 87 obs |
| `corr_matrix.intersection_policy` | `common` | dropna(how="any") 동작 유지 |
| `corr_matrix.short_history_warning_ratio` | 0.8 | review.py 현재 휴리스틱과 정합 |

### 5.4 운용역이 결정해야 할 추가 항목 (옵션)

| # | 항목 | 권장 | 비고 |
|---|---|---|---|
| 1 | min_obs 강화 (12 → 36 또는 60) | 12 유지 | ust30 87 obs 가 통과 → 강화 시 ust30 fail. 현재 단계 12 유지 권장 |
| 2 | short_history_warning_ratio (0.8 vs 0.5) | 0.8 유지 | 현재 review.py 휴리스틱 |
| 3 | ust30 lookback 자산별 override | 미적용 | 데이터가 자연스럽게 자기 시작점 사용. override 불필요 |
| 4 | corr 산출 시 PSD nearest 보정 | 미적용 | 현재 PSD 만족 (eigvals min ≥ 0). 향후 위반 발생 시 별도 결정 |

---

## 6. D-03 closure 조건

D-03 를 `open → closed` 로 전환하려면 **아래 5 조건 모두 만족** 필요:

1. **lookback policy 옵션 선택** (A / B / C 중 하나) — 권장 = **C (Hybrid)**
2. **min_observation threshold 확정** — 권장 = **12 (현재 default 유지)**
3. **ust30 / BRFUT004 짧은 history 허용 여부 확정** — 권장 = **허용** (현재 동작 유지, telemetry 로만 노출)
4. **warning vs review_required 기준 확정** — 권장 = **D-02 closed 정책 따름** (relaxed=telemetry_only / review=warning / production=review_required). 즉 D-02 와 동일 enforcement 모드. lookback warning 자체는 항상 telemetry 로 노출하되 production mode 에서 obs < min_obs 면 review_required.
5. **관련 config / test 변경 필요 여부 정리** — 권장 = **yaml 4 line 추가만** (코드/test 무변경, Option C 채택 시)

### 6.1 closure 시 수반 작업 (예상, 별도 PR)

- `db_sources.yaml::asset_rt_vol` + `corr_matrix` 에 4 line 추가 (intersection_policy, min_obs, short_history_warning_ratio)
- `register::D-03` status `open → closed` + decision 본문 작성
- HANDOFF.md + memory/project_state.md blocker 갱신 (D-03 빠짐 → blocker 2건: D-08 / D-09)

### 6.2 closure 시 변경하지 않을 것

- ✗ `db_market_data.py` 코드 (현재 `dropna(how="any")` 동작 그대로)
- ✗ `quality.py` / `review.py` (현재 short_history warning 휴리스틱 그대로)
- ✗ `tests/` (현재 통과 그대로)
- ✗ `out/` 산출물 (재산출 불필요)
- ✗ Decision Register total count (14 무변경, D-03 status 만 이동)

---

## 7. 한 줄 요약 (sign-off 후)

> **D-03 closed = Option C (Hybrid). return/vol = asset-specific, corr = common intersection. yaml 4 line 추가로 정책 명문화. 코드 / tests / 산출 결과 무변경. min_obs=12, short_history_warning_ratio=0.8.**
> ust30 obs=87 은 정책상 허용 (telemetry 로 노출, fail 아님).

---

## 8. DB sanity flag vs Review / policy warning — 구분 명시

운용역 검토 시 두 기준이 동시에 작동하므로 **별개로 해석** 필요. 같은 자산이 sanity flag 통과하면서 review warning 대상이 될 수 있음 (모순 아님).

| 기준 | 발동 조건 | 의미 | ust30 obs=87 케이스 |
|---|---|---|---|
| **DB sanity flag** | `obs < min_obs (=12)` 시 `too_few_observations` | hard data integrity. min_obs 미충족 시 자산 자체가 의심. | ✓ obs=87 ≥ 12 → flag = []. **hard issue 아님.** |
| **Review / policy warning** | `obs < max_obs * short_history_warning_ratio (=0.8)` | telemetry. 다른 자산 대비 짧은 history → corr / 추정 noise 영향. | ⚠ obs=87 < 120*0.8=96 → review packet `policy_review_items` 에 short-history warning 표시. **운용역 검토 telemetry.** |

**구체적 동작**:
- DB sanity (`db_market_data.py::_record_sanity`): min_obs=12 미만 시 `suspicious_flags` 에 `too_few_observations` 추가. corr/vol 산출 자체가 의심스러운 수준.
- Review warning (`reporting/review.py::policy_review_items`): max_obs 대비 80% 미만 시 "shorter history, confirm lookback policy" 메시지. 운용역이 lookback 정책 정합성을 검토하라는 신호. fail 아님.

**enforcement 분기**: D-02 enforcement 모드에 따라 review warning 의 quality_status 영향 결정.
- `relaxed_diagnostic` → telemetry only (현재)
- `review` → warning
- `production` → review_required (단 hard issue 가 아니라면 enforcement_mode 별 처리는 운용역 추가 결정)

---

## 9. Sign-off note (2026-05-08)

```
─────────────────────────────────────────────────────────────────────────
D-03 closed by 운용역 sign-off — 2026-05-08

승인 정책 (Option C — Hybrid):
- return / volatility intersection_policy = asset_specific
- correlation intersection_policy         = common
- asset_rt_vol.lookback_years              = 10 (유지)
- corr_matrix.lookback_years               = 10 (유지, effective 는 가장 짧은 자산)
- min_obs                                  = 12
- short_history_warning_ratio              = 0.8
- BRFUT004 / ust30 obs=87                  = 허용 (telemetry only)

closure 5 조건 모두 충족:
  ✅ lookback policy 옵션 선택 (Option C)
  ✅ min_observation threshold 확정 (12)
  ✅ ust30 / BRFUT004 짧은 history 허용 결정 (telemetry)
  ✅ warning vs review_required 기준 (D-02 enforcement 모드 따름)
  ✅ config / test 변경 정리 (yaml 4 line 추가, 코드/test 무변경)

적용 위치:
  ✓ tdf_engine/config/db_sources.yaml — asset_rt_vol + corr_matrix 4 line 추가
  ✓ docs/investment_decision_register.md — status / 본문 / 변경 이력
  ✓ HANDOFF.md — blocker 3건 → 2건
  ✓ memory/project_state.md — closure 기록
  ✓ docs/phase_d_d03_lookback_policy_review.md (본 문서) — sign-off note + sanity vs warning 구분

코드 / tests / out 무변경. yaml 4 line 추가만.
─────────────────────────────────────────────────────────────────────────
```

---

## 10. 본 문서 변경 범위 (sign-off 후)

| 영역 | 변경 |
|---|:---:|
| `tdf_engine/` 코드 | ✗ 무변경 |
| `tdf_engine/config/db_sources.yaml` | ✓ 4 line 추가 (intersection_policy / min_obs / short_history_warning_ratio) |
| `tests/` | ✗ 무변경 |
| `out/` 산출물 | ✗ 무변경 |
| `docs/investment_decision_register.md` D-03 status | ✓ `open → closed` |
| Decision Register total count (14) | ✗ 무변경 |
| 본 문서 | ✓ sign-off note + sanity vs warning 구분 추가 |

pytest: 142 passed / 5 skipped / 1 xfailed (yaml 추가 후 무회귀).
