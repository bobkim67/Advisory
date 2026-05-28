# TDF 2060 Portfolio Review — ETF

as_of: **2026-03-31** · source: **db**

> ⚠️ **RELAXED DIAGNOSTIC RUN — NOT a production portfolio**
> - 본 산출은 **운용 최종안이 아니라** 제약 해제 시 optimizer / TAA 쏠림을 확인하기 위한 **diagnostic run** 입니다.
> - glide path 80/20 은 **reference / starting SAA** 로만 보존되며 hard constraint 가 아닙니다.
> - equity 100% / fixed_income 0% 등 극단 비중은 **fail 이 아닌 monitoring flag** 로만 노출됩니다.
> - 향후 운용안 확정 시 **자산군별 band 또는 bucket range 를 재도입** 할 수 있습니다 (Decision Register D-11/D-12 deferred).
> - 현 단계 hard constraint = `long-only` + `sum-to-100%` + 데이터 무결성 (LBUSTRUU mapping / DB / NaN / convergence).

## 0. Executive Summary

| 항목 | 값 |
|---|---|
| portfolio_type | **ETF** |
| as_of_date | 2026-03-31 |
| constraints_passed | **True** |
| quality_status | **warning** |
| asset_weight_sum | 1.000000 |
| product_weight_sum | 1.000000 |
| equity_weight | 100.0000% |
| fixed_income_weight | 0.0000% |
| warning_count_total | 8 |

**운용역 판단란**: 
- [ ] Approve  ·  - [ ] Revise  ·  - [ ] Hold

## 1. 요약

| 항목 | 값 |
|---|---|
| constraints_passed | **True** |
| quality_status | **warning** |
| asset_weight_sum | 1.000000 |
| product_weight_sum | 1.000000 |
| equity bucket | 100.0000% |
| fixed_income bucket | 0.0000% |
| fallback_used | True |
| projection_used | True |
| max_abs_projection_drift | 3.0000% |
| max_abs_asset_weight_drift | 29.6378% |
| proxy_used | False |
| db_warnings_count | 0 |
| validation_issues_count | 0 |
| validation_warnings_count | 8 |

## 2. 최종 자산배분

**Regime 컨텍스트**: region=**G7** · Placement=0.7223 · Velocity=0.0586 · regime=**1** (Expansion / Acceleration)

| asset_key | bucket | SAA | TAA target (before proj) | **final** | drift | bound [lb, ub] | status |
|---|---|---:|---:|---:|---:|---|---|
| kr_equity | equity | +0.0000% | +2.0000% | **+1.0000%** | -1.0000% | [0.0000%, 100.0000%] | ok |
| us_growth_equity | equity | +49.3622% | +49.3622% | **+48.3622%** | -1.0000% | [0.0000%, 100.0000%] | ok |
| us_value_equity | equity | +0.0000% | +0.0000% | **+0.0000%** | +0.0000% | [0.0000%, 100.0000%] | near_bound |
| dm_ex_us_equity | equity | +0.0000% | +0.0000% | **+0.0000%** | +0.0000% | [0.0000%, 100.0000%] | near_bound |
| em_equity | equity | +0.0000% | +2.0000% | **+1.0000%** | -1.0000% | [0.0000%, 100.0000%] | ok |
| kr_aggregate_bond | fixed_income | +0.0000% | +0.0000% | **+0.0000%** | +0.0000% | [0.0000%, 100.0000%] | near_bound |
| kr_treasury_10y | fixed_income | +0.0000% | -2.0000% | **+0.0000%** | +2.0000% | [0.0000%, 100.0000%] | near_bound |
| us_aggregate_bond | fixed_income | +0.0000% | -3.0000% | **+0.0000%** | +3.0000% | [0.0000%, 100.0000%] | near_bound |
| gold | equity | +50.6378% | +50.6378% | **+49.6378%** | -1.0000% | [0.0000%, 100.0000%] | ok |
| us_high_yield | fixed_income | +0.0000% | +1.0000% | **+0.0000%** | -1.0000% | [0.0000%, 100.0000%] | near_bound |

> **부분 attribution 안내**: SAA 컬럼과 TAA tilt(자산별 정량 분해)는 일부가 telemetry 미노출로 `—` 표시됨. 본 packet 의 SAA → TAA → Final attribution 은 **partial view** 이며, 완전한 attribution 은 향후 telemetry 개선 후에 가능. 이 개선은 정식 Decision Register 항목이 아니라 enhancement candidate (§10 참고). TAA target 컬럼은 SAA + regime tilt 적용 후 값(=projection 직전)을 의미.

### 2.1 자산배분 요약 — sanity monitoring only (NOT enforced)

| 항목 | 값 | sanity range | 범위 내 |
|---|---:|---|:---:|
| 주식 합계 | 100.0000% | [60.00%, 95.00%] | ⚠ |
| 채권 합계 | 0.0000% | [5.00%, 40.00%] | ⚠ |
| HY 비중 (us_high_yield) | 0.0000% | — | — |

> 위 sanity range 는 hard bound 가 아니며, 이탈 시 fail 이 아닌 운용역 검토 flag (D-01 closed).
> HY 분류: fixed_income bucket + risk_asset + credit (D-07 closed)

## 3. Projection 전후

projection_used = **True** · max_abs_drift = 3.0000%

| bucket | before | after |
|---|---:|---:|
| equity | 104.0000% | 100.0000% |
| fixed_income | -4.0000% | 0.0000% |

**음수 자산 (projection 전)**: kr_treasury_10y=-2.0000%, us_aggregate_bond=-3.0000%

Top-5 projection drift:

| asset_key | before | after | drift |
|---|---:|---:|---:|
| us_aggregate_bond | -3.0000% | +0.0000% | +3.0000% |
| kr_treasury_10y | -2.0000% | +0.0000% | +2.0000% |
| gold | +50.6378% | +49.6378% | -1.0000% |
| us_growth_equity | +49.3622% | +48.3622% | -1.0000% |
| us_high_yield | +1.0000% | +0.0000% | -1.0000% |

### 3.1 Drift source breakdown

> ⚠️ relaxed_diagnostic mode 에서 drift 는 fail 이 아니라 telemetry. 본 섹션은 분석용.

**(a) Projection 단계 drift** (long-only 강제 등 — `max_abs_projection_drift`)

- projection_used: **True**
- max_abs_projection_drift: 3.0000%
- primary drift source: **redistribution_from_long_only_clipping**
- clipped assets (long-only): **2** — kr_treasury_10y=+2.0000%, us_aggregate_bond=+3.0000%
- total long-only clipping magnitude: 5.0000%
- max long-only clipping: 3.0000%
- redistribution recipients (top-5): gold=-1.0000%, us_growth_equity=-1.0000%, us_high_yield=-1.0000%, em_equity=-1.0000%, kr_equity=-1.0000%
- redistribution total: 5.0000%
- drift_source counts: redistribution_from_long_only_clipping=5, long_only_clipping=2

**(b) Selection + fallback 단계 drift** (product cap clipping 등 — `max_abs_asset_weight_drift`)

- max_abs_asset_weight_drift: 29.6378%
- primary drift source: **fallback_redistribution_inflow**
- outflow assets (target → final 감소): gold=+29.6378%
- total outflow: 29.6378%
- inflow assets (target → final 증가): em_equity=+11.1142%, kr_equity=+11.1142%, us_growth_equity=+7.4095%
- total inflow: 29.6378%
- drift_source counts: fallback_redistribution_inflow=3, product_cap_clipping_outflow=1

**자산별 drift_source (top 10 by |drift|)**

| asset_key | proj drift | proj source | qual drift | qual source |
|---|---:|---|---:|---|
| gold | -1.0000% | redistribution_from_long_only_clipping | -29.6378% | product_cap_clipping_outflow |
| em_equity | -1.0000% | redistribution_from_long_only_clipping | +11.1142% | fallback_redistribution_inflow |
| kr_equity | -1.0000% | redistribution_from_long_only_clipping | +11.1142% | fallback_redistribution_inflow |
| us_growth_equity | -1.0000% | redistribution_from_long_only_clipping | +7.4095% | fallback_redistribution_inflow |
| us_aggregate_bond | +3.0000% | long_only_clipping | +0.0000% | none |
| kr_treasury_10y | +2.0000% | long_only_clipping | +0.0000% | none |
| us_high_yield | -1.0000% | redistribution_from_long_only_clipping | +0.0000% | none |
| dm_ex_us_equity | +0.0000% | none | +0.0000% | none |
| kr_aggregate_bond | +0.0000% | none | +0.0000% | none |
| us_value_equity | +0.0000% | none | +0.0000% | none |

## 4. 최종 상품 (15개)

| asset_key | bucket | product | manager | role | score | weight | flags |
|---|---|---|---|---|---:|---:|---|
| kr_equity | equity | NH-AmundiHANARO원자력iSelect상장지수(주식) | NH-Amundi운용 | core | — | +4.5047% | fallback_absorber |
| kr_equity | equity | 한화PLUSK방산상장지수(주식) | 한화운용 | satellite | — | +3.8047% | fallback_absorber |
| kr_equity | equity | 한국투자ACE원자력TOP10상장지수(주식) | 한국투자신탁운용 | satellite | — | +3.8047% | fallback_absorber |
| us_growth_equity | equity | 타임폴리오TIME미국나스닥100액티브상장지수(주식) | 타임폴리오자산운용 | core | — | +20.0000% | unfilled_cause=product_cap_clipping |
| us_growth_equity | equity | 삼성KODEX미국나스닥AI테크액티브상장지수[주식] | 삼성운용 | satellite | — | +17.8858% | unfilled_cause=product_cap_clipping, fallback_absorber |
| us_growth_equity | equity | 미래에셋TIGER미국필라델피아반도체나스닥상장지수(주식) | 미래에셋운용 | satellite | — | +17.8858% | unfilled_cause=product_cap_clipping, fallback_absorber |
| em_equity | equity | 삼성KODEX아시아AI반도체exChina액티브상장지수[주식] | 삼성운용 | core | — | +4.5047% | fallback_absorber |
| em_equity | equity | 미래에셋TIGER라틴상장지수(주식) | 미래에셋운용 | satellite | — | +3.8047% | fallback_absorber |
| em_equity | equity | 한국투자ACE아시아TOP50상장지수(주식) | 한국투자신탁운용 | satellite | — | +3.8047% | fallback_absorber |
| us_aggregate_bond | fixed_income | 삼성KODEXiShares미국투자등급회사채액티브상장지수[채권-재간접] | 삼성운용 | core | — | +0.0000% | - |
| us_aggregate_bond | fixed_income | 한화PLUS미국채30년액티브상장지수(채권) | 한화운용 | satellite | — | +0.0000% | - |
| us_aggregate_bond | fixed_income | 삼성KODEX미국종합채권ESG액티브상장지수[채권](H) | 삼성운용 | satellite | — | +0.0000% | - |
| gold | equity | 키움KIWOOM미국S&P500&GOLD상장지수[주식] | 키움투자운용 | core | — | +20.0000% | unfilled_cause=satellite_short |
| us_high_yield | fixed_income | 삼성KODEXiShares미국하이일드액티브상장지수[채권-재간접] | 삼성운용 | core | — | +0.0000% | - |
| us_high_yield | fixed_income | 한국투자ACE미국하이일드액티브상장지수[채권-재간접](H) | 한국투자신탁운용 | satellite | — | +0.0000% | - |

> score 컬럼 `—` = selection score 미보존 (selection/tool.py 정책 — §10 future_telemetry_notes 참고).

### 4.1 제외 / 분류 요약

| 항목 | 값 |
|---|---:|
| total_products (raw) | 932 |
| passed_filter_count | 736 |
| classified_count | 571 |
| excluded_count | **361** |
| grade_filtered_count | 62 |
| grade_penalized_count | 0 |

**자산군별 후보 수**:

| asset_key | n |
|---|---:|
| dm_ex_us_equity | 15 |
| em_equity | 55 |
| gold | 1 |
| kr_aggregate_bond | 97 |
| kr_equity | 347 |
| kr_treasury_10y | 10 |
| us_aggregate_bond | 4 |
| us_growth_equity | 22 |
| us_high_yield | 2 |
| us_value_equity | 18 |

> 개별 제외 상품 ID/사유 목록은 현재 universe_diagnostics 에 미노출 (future telemetry §10 참고).

## 5. Validation

- issues: **0**
- warnings: **8**

### 5.1 Constraint & Warning Register

| warning_id | severity | source | message | linked_decision | required |
|---|---|---|---|---|:---:|
| VAL-01 | warning | validation | taa_projection_used: max_abs_projection_drift=3.0000% | D-02 | ✓ |
| VAL-02 | warning | validation | negative weights before projection: kr_treasury_10y=-2.0000%, us_aggregate_bond=-3.0000% | D-10 | — |
| VAL-03 | warning | validation | bucket after projection: equity=100.0000%, fixed_income=0.0000% | - | — |
| VAL-04 | warning | validation | fallback_used: us_growth_equity 18.6897% redistributed → ['us_growth_equity'] (cause=product_cap_clipping) | D-12 | — |
| VAL-05 | warning | validation | fallback_used: gold 29.6378% redistributed → ['em_equity', 'kr_equity', 'us_growth_equity'] (cause=satellit... | D-12 | — |
| VAL-06 | warning | validation | max_abs_asset_weight_drift: 29.6378% | - | — |
| VAL-07 | warning | validation | max_abs_bucket_drift: 0.0000% | - | — |
| VAL-08 | warning | validation | quality_status: warning | - | — |
| POL-01 | review_required | policy_review_items | projection was used; confirm max_abs_projection_drift 3.0000% is acceptable. | D-02 | ✓ |

> linked_decision 은 substring heuristic. 운용역 실제 매핑은 검토 후 확정.

## 6. Quality

- quality_status: **warning**
- max_abs_asset_weight_drift: 29.6378%
- enforcement: **telemetry_only** — drift 초과는 quality_status 에 영향 없음 (telemetry 만 보존)
- drift telemetry notes:
  - asset drift 0.2964 >= threshold 0.0300
- drift_source breakdown: 다음 PR 예정 (`docs/phase_d_drift_telemetry_proposal.md` §2 참조).

## 7. DB source

- source_type: db
- proxy_used: False
- db_warnings_count: 0

## 8. 운용역 확인 필요 사항

- projection was used; confirm max_abs_projection_drift 3.0000% is acceptable.

## 9. 운용역 Review Checklist

- [ ] 자산배분 범위 적정 (주식 75~85%, 채권 15~25%)
- [ ] 미국 종합채권 LBUSTRUU/LHMN0001 처리 확인 (D-04 closed)
- [ ] HY 채권 버킷 편입 적정 (risk_asset + credit, D-07 closed)
- [ ] 특정 자산군 쏠림 적정 (us_value cap 30% — D-12)
- [ ] 특정 상품/운용사 쏠림 적정 (D-14)
- [ ] 제외 상품 규칙 적정 (혼합형/TDF/TIF/TRF/멀티에셋/재간접)
- [ ] warning 수용 가능 (Section 5.1 Warning Register 검토)
- **최종 결정**: [ ] Approve  ·  [ ] Revise  ·  [ ] Hold

## 10. 향후 telemetry 개선 후보

**중요**: 아래 D-15~D-18 은 **정식 Decision Register 항목이 아니라 telemetry enhancement candidate** 입니다. 정식 등록 시 `investment_decision_register.md` 의 total count 와 status distribution 을 별도 갱신해야 합니다.

- TAA tilt by asset 미노출 — taa_diagnostics.tilt_by_asset = None. regime → final 완전 분해 불가. candidate id: **D-16 (telemetry enhancement, 정식 아님)**.
- 제외 상품 개별 ID/사유 목록 미노출 — universe_diagnostics.excluded_sample 비어있음. 운용역이 제외 룰 검증하려면 sample 확장 필요. candidate id: **D-17 (telemetry enhancement, 정식 아님)**.
- selection score 미노출 — product_allocation.score = None. selection/tool.py 에서 보존 필요. candidate id: **D-18 (telemetry enhancement, 정식 아님)**.
