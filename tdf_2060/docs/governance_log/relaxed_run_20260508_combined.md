# Relaxed Diagnostic Run — Governance Log (20260508 combined)

작성일: 2026-05-08. **첫 governance log**. ETF + Fund 동일 as_of_date 의 relaxed_diagnostic
산출을 본 단일 문서로 결합하여 기록한다. 본 log 는 `docs/phase_e_relaxed_run_log_template.md` 를
복제·작성한 사례이며, 양식 자체는 무변경.

> **Phase D completed register-blocker resolution only.**
> **This does not mean production readiness.**
> **The engine remains in relaxed_diagnostic mode.**

> 본 log 는 future Phase E-1 (production 전환) 결정의 참고 자료로만 사용한다.
> 누적 자체가 production 자동 전환 근거가 아니다.

---

## 1. Purpose

| 측면 | 내용 |
|---|---|
| **위상** | production portfolio **아님**. diagnostic baseline only. |
| **목적** | optimizer / TAA / selection / fallback 단계의 쏠림 / 한계 / 정책 영향을 관찰하고 누적 기록. |
| **사용처** | E-2 governance review 의 첫 사례. 후속 누적 + Phase E-1 / E-3 / E-4 / E-5 정책 결정의 참고 자료. |
| **본 log 의 outcome** | `pending_review` (운용역 최종 sign-off 미수령). production approval 로 해석 금지. |

---

## 2. Run Metadata

| 필드 | 값 |
|---|---|
| `run_id` | `relaxed_20260508_combined_001` |
| `as_of_date` | `2026-03-31` (review_summary.as_of_date) |
| `created_at` | `2026-05-08` (build_portfolio.py / render_figures.py 산출 시점) |
| `reviewer` | _운용역 sign-off 대기_ |
| `operating_mode` | `relaxed_diagnostic` |
| `source_mode` | `db` |
| `portfolio_type` | `combined` (ETF + Fund 결합 기록) |
| `config_version` | `tdf_engine/config/*.yaml` (현 시점 git tracked) |
| `template` | [`docs/phase_e_relaxed_run_log_template.md`](../phase_e_relaxed_run_log_template.md) |
| **output paths** | (아래) |

```
output_paths:
  - out/db_etf_relaxed/portfolio_etf_20260508.{csv,json}
  - out/db_etf_relaxed/review_etf_20260508.md
  - out/db_fund_relaxed/portfolio_fund_20260508.{csv,json}
  - out/db_fund_relaxed/review_fund_20260508.md
  - out/db_review_relaxed/comparison_etf_vs_fund_20260508.md
  - out/db_review_relaxed/figures_summary_20260508.md
  - out/db_review_relaxed/figures/20260508/{etf,fund,comparison}/*.png  (9 PNG)
```

| 산출물 | 경로 |
|---|---|
| ETF review | [`review_etf_20260508.md`](../../out/db_etf_relaxed/review_etf_20260508.md) |
| Fund review | [`review_fund_20260508.md`](../../out/db_fund_relaxed/review_fund_20260508.md) |
| Comparison | [`comparison_etf_vs_fund_20260508.md`](../../out/db_review_relaxed/comparison_etf_vs_fund_20260508.md) |
| **figures_summary** | [`figures_summary_20260508.md`](../../out/db_review_relaxed/figures_summary_20260508.md) |

---

## 3. Hard Constraint Check

| # | 항목 | ETF | Fund | 통과 |
|:---:|---|:---:|:---:|:---:|
| H-1 | **long-only**: negative count | 0 | 0 | ✓ |
| H-2 | **sum-to-100%**: asset_weight_sum / product_weight_sum | 1.0000 / 1.0000 | 1.0000 / 1.0000 | ✓ |
| H-3 | **DB source 정상**: datasets_loaded=9, missing=[] | ✓ | ✓ | ✓ |
| H-4 | **BRFUT004 direct mapping** (D-04): dataset_id=201, blob_key=totRtnIndex | ✓ | ✓ | ✓ |
| H-5 | **NaN / invalid return 없음**: db_warnings_count | 0 | 0 | ✓ |
| H-6 | **optimizer / projection convergence**: solver_status=0, projection_success=True | ✓ | ✓ | ✓ |

**결과**: 6 hard constraints 모두 ✓. ETF / Fund 양쪽 동일.

---

## 4. Diagnostic Summary

| 항목 | ETF | Fund |
|---|---|---|
| equity bucket | **100.00%** | **100.00%** |
| fixed_income bucket | **0.00%** | **0.00%** |
| top asset (asset_key / weight) | `us_growth_equity` / 70.60% | `us_growth_equity` / 70.60% |
| 2nd asset | `us_value_equity` / 27.40% | `us_value_equity` / 27.40% |
| 3rd asset | `em_equity` / 1.00% | `em_equity` / 1.00% |
| zero-weight asset 수 | **5** | **5** |
| zero-weight asset list | `us_high_yield, dm_ex_us_equity, kr_aggregate_bond, kr_treasury_10y, us_treasury_30y` | (동일) |
| max_abs_projection_drift | **3.00%** | **3.00%** |
| projection drift primary source | `long_only_clipping` (kr_t10 -2% → 0, ust30 -3% → 0) | (동일) |
| max_abs_asset_weight_drift (quality) | **10.60%** | **0.00%** |
| quality drift primary source | `fallback_redistribution_inflow` (us_growth outflow 10.60% → us_value/em/kr/dm_ex_us 분배) | `none` |
| product cap binding (top) | `426030` 20.00%, `411420` 20.00%, `381180` 20.00% (모두 us_growth, ETF cap 20%) | `76305` 30.00% (KB운용, Fund cap 30%) |
| top manager (weight) | 미래에셋운용 25.73% / 삼성운용 23.69% / 한국투자신탁운용 23.09% | KB운용 30.00% / 한국투자신탁운용 27.40% / 삼성운용 20.30% |
| short-history telemetry | `ust30 obs=87 (< max*0.8 = 96)` | (동일) |
| validation_warnings_count | 8 | 7 |
| quality_status | `warning` | `warning` |
| fallback_used | `True` | `True` |
| regime | `Expansion / Acceleration` (region=G7, placement=0.7223, velocity=0.0586) | (동일) |
| enforcement_mode | `telemetry_only` | `telemetry_only` |

### 4.1 ETF vs Fund quality drift 차이 해석

ETF 는 product cap **20%** 으로 us_growth target 70.60% 를 3 product × 20% = 60% 까지만 흡수 →
잔여 10.60% 가 us_value / em / kr / dm_ex_us 로 fallback redistribution. 그래서 quality drift 10.60%.

Fund 는 product cap **30%** 으로 us_growth target 70.60% 가 30% + 20.30% + 20.30% = 70.60% 로
asset 단위에서 정확 매칭 → quality drift 0.00%. 단 manager 단위에서 KB 30% 가 단일 product cap
binding 상태.

본 차이는 selection 단계의 **기존 product cap** (ETF 20% / Fund 30%) 영향이며 본 단계에서 **신규
cap / threshold 도입 없음**. 모니터링만.

---

## 5. Visual Review Links

[`figures_summary_20260508.md`](../../out/db_review_relaxed/figures_summary_20260508.md) 에 9
PNG 가 묶여 있으며, 본 log 에서는 영역별 링크만 인덱싱.

| 영역 | 차트 | 경로 |
|---|---|---|
| ETF | Asset Allocation | [`figures/20260508/etf/01_asset_allocation.png`](../../out/db_review_relaxed/figures/20260508/etf/01_asset_allocation.png) |
| ETF | Drift Summary | [`figures/20260508/etf/02_drift_summary.png`](../../out/db_review_relaxed/figures/20260508/etf/02_drift_summary.png) |
| ETF | Top Products | [`figures/20260508/etf/03_top_products.png`](../../out/db_review_relaxed/figures/20260508/etf/03_top_products.png) |
| ETF | Manager Concentration | [`figures/20260508/etf/04_manager_concentration.png`](../../out/db_review_relaxed/figures/20260508/etf/04_manager_concentration.png) |
| Fund | Asset Allocation | [`figures/20260508/fund/01_asset_allocation.png`](../../out/db_review_relaxed/figures/20260508/fund/01_asset_allocation.png) |
| Fund | Drift Summary | [`figures/20260508/fund/02_drift_summary.png`](../../out/db_review_relaxed/figures/20260508/fund/02_drift_summary.png) |
| Fund | Top Products | [`figures/20260508/fund/03_top_products.png`](../../out/db_review_relaxed/figures/20260508/fund/03_top_products.png) |
| Fund | Manager Concentration | [`figures/20260508/fund/04_manager_concentration.png`](../../out/db_review_relaxed/figures/20260508/fund/04_manager_concentration.png) |
| Comparison | ETF vs Fund Asset Allocation | [`figures/20260508/comparison/01_asset_allocation_etf_vs_fund.png`](../../out/db_review_relaxed/figures/20260508/comparison/01_asset_allocation_etf_vs_fund.png) |

> 모든 차트 title / caption 에 `Relaxed Diagnostic — Not Production` 표기. cap / threshold 선
> 미사용 (monitoring only).

---

## 6. Key Observations

본 섹션은 운용역이 직접 검토한 결과를 누적하는 자유 기재 영역. 본 첫 log 는 산출 자체에서
즉시 확인 가능한 관찰을 기본 채움. 운용역 추가 의견은 sign-off 시점에 보완.

### 6.1 자산군 쏠림 (asset concentration)

- **equity 100% / fixed_income 0%** — sanity range [60-95]% 상한 이탈, [5-40]% 하한 이탈.
  단 relaxed_diagnostic 모드에서 **monitoring flag 만**, fail 아님.
- **us_growth_equity = 70.60%** (단일 자산군 70%+). D-12 deferred (us_value cap) 의 인접 트리거
  영역. 본 log 자체가 정책 변경 아님.
- **zero-weight 자산 5종** (us_high_yield, dm_ex_us_equity, kr_aggregate_bond, kr_treasury_10y,
  us_treasury_30y). D-10 closed (0% 허용) 정책상 정상.

### 6.2 상품 쏠림 (product concentration)

- **ETF top 3 product 가 모두 us_growth_equity, 각 20.00%** (`426030`, `411420`, `381180`) —
  selection 의 기존 product cap 20% binding.
- **Fund top product = KB운용 76305, 30.00%** — selection 의 기존 product cap 30% binding.
- 본 log 는 신규 product cap / threshold 미도입. 기존 selection-level cap 만 영향.

### 6.3 운용사 쏠림 (manager concentration)

- ETF: 미래에셋 25.73% / 삼성 23.69% / 한투 23.09% — 분산 (top 3 합 = 72.5%, ETF cap 60%
  reference 미도입).
- Fund: KB 30.00% / 한투 27.40% / 삼성 20.30% — 단일 manager (KB) 가 30%. Fund cap 50%
  reference 미도입.
- D-14 (manager concentration cap) 는 deferred 상태. 본 log 는 monitoring 만.

### 6.4 TAA prototype rule 관련 특이사항

- **TAA rule = prototype operator-defined heuristic overlay**. final quantitative TAA 모델 아님.
  asset_tilts 만 적용, bucket_tilts 미사용, per_asset_max_tilt=1.0 (사실상 비제약).
- regime = `Expansion / Acceleration` (region=G7) — taa_policy.yaml::regime_tilts.regime_1
  적용. 본 결과의 us_growth 70.60% 는 이 prototype tilt 의 산출.
- 본 log 는 TAA 엔진 / 정책 / 수치 어떤 변경도 동반하지 않음.

### 6.5 Fallback redistribution / projection 특이사항

- **Projection drift 3.00%**: kr_treasury_10y (-2%p → 0), us_treasury_30y (-3%p → 0). 모두
  `long_only_clipping`. D-02 closed 정책상 telemetry only.
- **Quality drift (ETF) 10.60%**: us_growth_equity outflow 10.60%p → us_value 1.93 / em 2.89 /
  kr_equity 2.89 / dm_ex_us 2.89 (`fallback_redistribution_inflow`). D-15 candidate 영역.
- **Quality drift (Fund) 0.00%**: us_growth target 70.60% 가 Fund cap 30% × 다수 product 로
  asset 단위에서 정확 흡수. 단 product / manager 수준의 cap binding 은 별개 monitoring.

### 6.6 데이터 이슈

- `ust30 obs=87` (< max*0.8=96). short_history_warning_ratio 트리거. D-03 closed 정책상 telemetry
  only.
- DB source missing = []. NaN 없음.
- regime label 직전 산출 대비 변경 여부 = (별도 추적 자료 미보유).

### 6.7 영구 인지 사항 (sign-off 시 함께 인지)

- **본 결과는 production portfolio 가 아님**. diagnostic baseline only.
- D-08 limitation: DRM 3 xlsx 영구 해제 불가 → SAA / TAA / Final Excel 1:1 parity 영구 waived.
- D-09: regimeAnalysis_rt 파일 자체가 canonical definition. 별도 답안지 부재.
- glidepath.yaml = reference metadata only (4 vintage, enforced=false).

---

## 7. Governance Outcome

### 7.1 결정

```
☑ pending_review                  ← 본 log 의 outcome
☐ approve_for_diagnostic_record
☐ request_rerun
☐ request_policy_change
☐ reject_as_invalid
```

### 7.2 사유

운용역 최종 sign-off 가 아직 수령되지 않았으므로 **`pending_review`** 로 기록.
`approve_for_diagnostic_record` / `request_rerun` / `request_policy_change` /
`reject_as_invalid` 중 어느 것으로 확정될지는 운용역 검토 결과에 따라 별도 갱신.

### 7.3 production approval 로 해석 금지 명시

본 log 의 어떤 항목도 production approval / 자동 운용 적용 / 고객 자료 직접 사용의 근거가 되지
않는다. `relaxed_diagnostic` 산출의 진단 기록 한정.

### 7.4 운용역 sign-off 시 추가 기재 영역 (예약)

```
승인일: ____________
운용역: ____________ (서명 / 시스템 ID)
최종 outcome: ____________
추가 의견: ____________
```

---

## 8. Policy Candidate Notes (informational only)

본 섹션은 **future candidate 기록용** 이며, **Decision Register total count 14 를 변경하지
않는다.** 정식 등록 / 제약 추가 / 정책 변경 일체 없음.

### 8.1 D-15 candidate — Asset target vs product allocation drift

| 항목 | 값 |
|---|---|
| 본 run 의 max drift | ETF 10.60%p / Fund 0.00%p |
| primary source | ETF: `fallback_redistribution_inflow` / Fund: `none` |
| 트리거 발생 여부 | ETF ☑ / Fund ☐ |
| 누적 정식 등록 권고? | ☐ Yes / ☑ No (정식 등록은 별도 운용역 결정 필요) |
| 메모 | ETF cap 20% × us_growth 3 product = 60% < target 70.60% → 10.60% redistribution. Fund 는 cap 30% 로 정확 흡수. ETF 1건 누적. |

### 8.2 D-16 candidate — Product single cap policy

| 항목 | 값 |
|---|---|
| 본 run 의 top product weight | ETF 20.00% (3 products tied) / Fund 30.00% |
| ETF cap 20% / Fund cap 30% 도달 product 수 | ETF 3 / Fund 1 |
| 트리거 발생 여부 (단일 product > 30%) | ETF ☐ / Fund ☐ |
| 누적 정식 등록 권고? | ☐ Yes / ☑ No |
| 메모 | 기존 selection-level cap (ETF 20% / Fund 30%) 이 binding. 신규 cap 없음. |

### 8.3 D-17 candidate — Asset concentration monitoring

| 항목 | 값 |
|---|---|
| 본 run 의 top asset weight | 70.60% (us_growth, ETF/Fund 동일) |
| 트리거 발생 여부 (단일 자산군 > 80%) | ☐ |
| 누적 정식 등록 권고? | ☐ Yes / ☑ No |
| 메모 | us_growth 70.60% 는 80% 미달이나 단일 자산군 sanity 영역. equity 100% 상태와 결합 관찰 필요. |

### 8.4 명시 문구 (인용)

> "본 섹션은 future candidate 기록용이며, Decision Register total count 14 를 변경하지 않는다."

---

## 9. 본 log 의 변경 범위

| 영역 | 결과 |
|---|:---:|
| `tdf_engine/` 코드 | ✗ 무변경 |
| `tdf_engine/config/*.yaml` | ✗ 무변경 |
| `tests/` | ✗ 무변경 |
| `out/` 산출물 (portfolio_*, review_*, comparison_*, figures_*, figures/) | ✗ 무변경 |
| `docs/investment_decision_register.md` status / count (14) | ✗ 무변경 |
| operating_mode (`relaxed_diagnostic`) | ✗ 무변경 |
| TAA engine / 정책 / 수치 | ✗ 무변경 |
| asset cap / floor / band / soft warning threshold | ✗ 무변경 |
| production dry-run 진입 | ✗ 미진입 |
| D-15 / D-16 / D-17 정식 등록 | ✗ 미등록 (informational only) |
| 본 문서 신설 | ✓ `docs/governance_log/relaxed_run_20260508_combined.md` |

pytest: `151 passed, 5 skipped, 1 xfailed` (E-6 figures 9건 추가 후 baseline. 본 문서 작성으로
미실행, 영향 없음).

---

## 10. 한 줄 요약

> **첫 governance log — 20260508 ETF + Fund relaxed_diagnostic run 결합 기록. Hard constraint
> 6/6 통과, equity 100% / us_growth 70.60% 쏠림 monitoring, ETF quality drift 10.60% (cap 20%
> binding), Fund 0% (cap 30% 흡수), TAA = prototype heuristic, regime = Expansion / Acceleration.
> Outcome = `pending_review` (운용역 sign-off 미수령). figures_summary_20260508.md + 9 PNG 연결.
> Decision Register / 코드 / config / 산출물 / cap / band / threshold 모두 무변경.**
