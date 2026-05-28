# TDF 2060 Portfolio Review — FUND

as_of: **-** · source: **file**

> ⚠️ **RELAXED DIAGNOSTIC RUN — NOT a production portfolio**
> - 본 산출은 **운용 최종안이 아니라** 제약 해제 시 optimizer / TAA 쏠림을 확인하기 위한 **diagnostic run** 입니다.
> - glide path 80/20 은 **reference / starting SAA** 로만 보존되며 hard constraint 가 아닙니다.
> - equity 100% / fixed_income 0% 등 극단 비중은 **fail 이 아닌 monitoring flag** 로만 노출됩니다.
> - 향후 운용안 확정 시 **자산군별 band 또는 bucket range 를 재도입** 할 수 있습니다 (Decision Register D-11/D-12 deferred).
> - 현 단계 hard constraint = `long-only` + `sum-to-100%` + 데이터 무결성 (LBUSTRUU mapping / DB / NaN / convergence).

## 0. Executive Summary

| 항목 | 값 |
|---|---|
| portfolio_type | **FUND** |
| as_of_date | - |
| constraints_passed | **True** |
| quality_status | **clean** |
| asset_weight_sum | 1.000000 |
| product_weight_sum | 1.000000 |
| equity_weight | 68.7033% |
| fixed_income_weight | 31.2967% |
| warning_count_total | 6 |

**운용역 판단란**: 
- [ ] Approve  ·  - [ ] Revise  ·  - [ ] Hold

## 1. 요약

| 항목 | 값 |
|---|---|
| constraints_passed | **True** |
| quality_status | **clean** |
| asset_weight_sum | 1.000000 |
| product_weight_sum | 1.000000 |
| equity bucket | 68.7033% |
| fixed_income bucket | 31.2967% |
| fallback_used | False |
| projection_used | True |
| max_abs_projection_drift | 3.0000% |
| max_abs_asset_weight_drift | 0.0000% |
| proxy_used | False |
| db_warnings_count | 0 |
| validation_issues_count | 0 |
| validation_warnings_count | 6 |

## 2. 최종 자산배분

**Regime 컨텍스트**: region=**G7** · Placement=0.7223 · Velocity=0.0586 · regime=**1** (Expansion / Acceleration)

| asset_key | bucket | SAA | TAA target (before proj) | **final** | drift | bound [lb, ub] | status |
|---|---|---:|---:|---:|---:|---|---|
| kr_equity | equity | +5.3674% | +7.3674% | **+6.8674%** | -0.5000% | [0.0000%, 100.0000%] | ok |
| us_growth_equity | equity | +36.5184% | +36.5184% | **+36.0184%** | -0.5000% | [0.0000%, 100.0000%] | ok |
| us_value_equity | equity | +0.0000% | +0.0000% | **+0.0000%** | -0.0000% | [0.0000%, 100.0000%] | near_bound |
| dm_ex_us_equity | equity | +0.0000% | +0.0000% | **+0.0000%** | +0.0000% | [0.0000%, 100.0000%] | near_bound |
| em_equity | equity | +0.0000% | +2.0000% | **+1.5000%** | -0.5000% | [0.0000%, 100.0000%] | ok |
| kr_aggregate_bond | fixed_income | +0.0000% | +0.0000% | **+0.0000%** | -0.0000% | [0.0000%, 100.0000%] | near_bound |
| kr_treasury_10y | fixed_income | +14.7716% | +12.7716% | **+12.2716%** | -0.5000% | [0.0000%, 100.0000%] | ok |
| us_aggregate_bond | fixed_income | +0.0000% | -3.0000% | **+0.0000%** | +3.0000% | [0.0000%, 100.0000%] | near_bound |
| gold | equity | +24.8175% | +24.8175% | **+24.3175%** | -0.5000% | [0.0000%, 100.0000%] | ok |
| us_high_yield | fixed_income | +18.5251% | +19.5251% | **+19.0251%** | -0.5000% | [0.0000%, 100.0000%] | ok |

> **부분 attribution 안내**: SAA 컬럼과 TAA tilt(자산별 정량 분해)는 일부가 telemetry 미노출로 `—` 표시됨. 본 packet 의 SAA → TAA → Final attribution 은 **partial view** 이며, 완전한 attribution 은 향후 telemetry 개선 후에 가능. 이 개선은 정식 Decision Register 항목이 아니라 enhancement candidate (§10 참고). TAA target 컬럼은 SAA + regime tilt 적용 후 값(=projection 직전)을 의미.

### 2.1 자산배분 요약 — sanity monitoring only (NOT enforced)

| 항목 | 값 | sanity range | 범위 내 |
|---|---:|---|:---:|
| 주식 합계 | 68.7033% | [60.00%, 95.00%] | ✓ |
| 채권 합계 | 31.2967% | [5.00%, 40.00%] | ✓ |
| HY 비중 (us_high_yield) | 19.0251% | — | — |

> 위 sanity range 는 hard bound 가 아니며, 이탈 시 fail 이 아닌 운용역 검토 flag (D-01 closed).
> HY 분류: fixed_income bucket + risk_asset + credit (D-07 closed)

## 3. Projection 전후

projection_used = **True** · max_abs_drift = 3.0000%

| bucket | before | after |
|---|---:|---:|
| equity | 70.7033% | 68.7033% |
| fixed_income | 29.2967% | 31.2967% |

**음수 자산 (projection 전)**: us_aggregate_bond=-3.0000%

Top-5 projection drift:

| asset_key | before | after | drift |
|---|---:|---:|---:|
| us_aggregate_bond | -3.0000% | +0.0000% | +3.0000% |
| gold | +24.8175% | +24.3175% | -0.5000% |
| em_equity | +2.0000% | +1.5000% | -0.5000% |
| kr_equity | +7.3674% | +6.8674% | -0.5000% |
| us_growth_equity | +36.5184% | +36.0184% | -0.5000% |

### 3.1 Drift source breakdown

> ⚠️ relaxed_diagnostic mode 에서 drift 는 fail 이 아니라 telemetry. 본 섹션은 분석용.

**(a) Projection 단계 drift** (long-only 강제 등 — `max_abs_projection_drift`)

- projection_used: **True**
- max_abs_projection_drift: 3.0000%
- primary drift source: **redistribution_from_long_only_clipping**
- clipped assets (long-only): **1** — us_aggregate_bond=+3.0000%
- total long-only clipping magnitude: 3.0000%
- max long-only clipping: 3.0000%
- redistribution recipients (top-5): gold=-0.5000%, em_equity=-0.5000%, kr_equity=-0.5000%, us_growth_equity=-0.5000%, us_high_yield=-0.5000%
- redistribution total: 3.0000%
- drift_source counts: redistribution_from_long_only_clipping=6, long_only_clipping=1

**(b) Selection + fallback 단계 drift** (product cap clipping 등 — `max_abs_asset_weight_drift`)

- max_abs_asset_weight_drift: 0.0000%
- primary drift source: **none**

**자산별 drift_source (top 10 by |drift|)**

| asset_key | proj drift | proj source | qual drift | qual source |
|---|---:|---|---:|---|
| us_aggregate_bond | +3.0000% | long_only_clipping | +0.0000% | none |
| gold | -0.5000% | redistribution_from_long_only_clipping | +0.0000% | none |
| em_equity | -0.5000% | redistribution_from_long_only_clipping | +0.0000% | none |
| kr_equity | -0.5000% | redistribution_from_long_only_clipping | +0.0000% | none |
| us_growth_equity | -0.5000% | redistribution_from_long_only_clipping | +0.0000% | none |
| us_high_yield | -0.5000% | redistribution_from_long_only_clipping | +0.0000% | none |
| kr_treasury_10y | -0.5000% | redistribution_from_long_only_clipping | +0.0000% | none |
| us_value_equity | -0.0000% | none | +0.0000% | none |
| kr_aggregate_bond | -0.0000% | none | +0.0000% | none |
| dm_ex_us_equity | +0.0000% | none | +0.0000% | none |

## 4. 최종 상품 (25개)

| asset_key | bucket | product | manager | role | score | weight | flags |
|---|---|---|---|---|---:|---:|---|
| kr_equity | equity | 한국밸류10년투자파이오니아(주식)(C-Re) | 한국투자밸류운용 | core | — | +5.4940% | - |
| kr_equity | equity | NH-Amundi필승코리아[주식]ClassC-P2(퇴직연금) | NH-Amundi운용 | satellite | — | +0.6867% | - |
| kr_equity | equity | 교보악사파워인덱스자 1[주식]ClassCP | 교보악사운용 | satellite | — | +0.6867% | - |
| us_growth_equity | equity | KB미국대표성장주자(주식)(UH)C-퇴직 | KB운용 | core | — | +28.8147% | - |
| us_growth_equity | equity | 삼성미국그로스자UH[주식-재간접]_Cp(퇴직연금) | 삼성운용 | satellite | — | +3.6018% | - |
| us_growth_equity | equity | AB미국그로스UH(주식-재간접)종류C-P2 | AB자산운용 | satellite | — | +3.6018% | - |
| us_value_equity | equity | 한국투자미국배당귀족자UH(주식)(C-R) | 한국투자신탁운용 | core | — | +0.0000% | - |
| us_value_equity | equity | 한국투자미국배당귀족자H(주식)(C-R) | 한국투자신탁운용 | satellite | — | +0.0000% | - |
| em_equity | equity | NH-Amundi성장중소형주[주식]ClassC-P2(퇴직연금) | NH-Amundi운용 | core | — | +1.2000% | - |
| em_equity | equity | 마이다스아시아리더스성장주자(H)(주식)C-P2 | 마이다스운용 | satellite | — | +0.1500% | - |
| em_equity | equity | 마이다스아시아리더스성장주자(UH)(주식)C-P2 | 마이다스운용 | satellite | — | +0.1500% | - |
| kr_aggregate_bond | fixed_income | HDC알짜배당(주식)종류C-Pe | HDC운용 | core | — | +0.0000% | - |
| kr_aggregate_bond | fixed_income | 코레이트셀렉트단기채[채권]C-P2 | 코레이트운용 | satellite | — | +0.0000% | - |
| kr_aggregate_bond | fixed_income | 삼성스마트MMF법인 1Cp(퇴직연금) | 삼성운용 | satellite | — | +0.0000% | - |
| kr_treasury_10y | fixed_income | 한국투자퇴직연금자 1(국공채)(C) | 한국투자신탁운용 | core | — | +9.8173% | - |
| kr_treasury_10y | fixed_income | KB스타중기국공채자(채권)C-퇴직 클래스 | KB운용 | satellite | — | +1.2272% | - |
| kr_treasury_10y | fixed_income | NH-Amundi국채10년인덱스자[채권]ClassC-P2(퇴직연금) | NH-Amundi운용 | satellite | — | +1.2272% | - |
| us_aggregate_bond | fixed_income | 삼성미국투자등급장기채권자UH[채권]_Cp(퇴직연금) | 삼성운용 | core | — | +0.0000% | - |
| us_aggregate_bond | fixed_income | 삼성미국투자등급장기채권자H[채권]_Cp(퇴직연금) | 삼성운용 | satellite | — | +0.0000% | - |
| gold | equity | iM에셋월드골드자(주식-재간접)(UH)(C-Rp) | iM에셋운용 | core | — | +19.4540% | - |
| gold | equity | 신한골드 1[주식](종류C-r) | 신한자산운용 | satellite | — | +2.4317% | - |
| gold | equity | iM에셋월드골드자(주식-재간접)(H)(C-Rp) | iM에셋운용 | satellite | — | +2.4317% | - |
| us_high_yield | fixed_income | 베어링글로벌하이일드자[UH](채권-재간접)ClassC-P2e | 베어링운용 | core | — | +15.2201% | - |
| us_high_yield | fixed_income | 베어링글로벌하이일드자[H](채권-재간접)ClassC-P2 | 베어링운용 | satellite | — | +1.9025% | - |
| us_high_yield | fixed_income | 교보악사미국코어하이일드자(UH)[채권-재간접]_ClassC-Re(퇴직연금) | 교보악사운용 | satellite | — | +1.9025% | - |

> score 컬럼 `—` = selection score 미보존 (selection/tool.py 정책 — §10 future_telemetry_notes 참고).

### 4.1 제외 / 분류 요약

| 항목 | 값 |
|---|---:|
| total_products (raw) | 781 |
| passed_filter_count | 414 |
| classified_count | 259 |
| excluded_count | **522** |
| grade_filtered_count | 0 |
| grade_penalized_count | 143 |

**자산군별 후보 수**:

| asset_key | n |
|---|---:|
| dm_ex_us_equity | 15 |
| em_equity | 72 |
| gold | 5 |
| kr_aggregate_bond | 40 |
| kr_equity | 99 |
| kr_treasury_10y | 4 |
| us_aggregate_bond | 2 |
| us_growth_equity | 10 |
| us_high_yield | 10 |
| us_value_equity | 2 |

> 개별 제외 상품 ID/사유 목록은 현재 universe_diagnostics 에 미노출 (future telemetry §10 참고).

## 5. Validation

- issues: **0**
- warnings: **6**

### 5.1 Constraint & Warning Register

| warning_id | severity | source | message | linked_decision | required |
|---|---|---|---|---|:---:|
| VAL-01 | warning | validation | taa_projection_used: max_abs_projection_drift=3.0000% | D-02 | ✓ |
| VAL-02 | warning | validation | negative weights before projection: us_aggregate_bond=-3.0000% | D-10 | — |
| VAL-03 | warning | validation | bucket after projection: equity=68.7033%, fixed_income=31.2967% | - | — |
| VAL-04 | warning | validation | max_abs_asset_weight_drift: 0.0000% | - | — |
| VAL-05 | warning | validation | max_abs_bucket_drift: 0.0000% | - | — |
| VAL-06 | warning | validation | quality_status: clean | - | — |
| POL-01 | review_required | policy_review_items | projection was used; confirm max_abs_projection_drift 3.0000% is acceptable. | D-02 | ✓ |

> linked_decision 은 substring heuristic. 운용역 실제 매핑은 검토 후 확정.

## 6. Quality

- quality_status: **clean**
- max_abs_asset_weight_drift: 0.0000%
- enforcement: **telemetry_only** — drift 초과는 quality_status 에 영향 없음 (telemetry 만 보존)
- drift_source breakdown: 다음 PR 예정 (`docs/phase_d_drift_telemetry_proposal.md` §2 참조).

## 7. DB source

- source_type: file
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
