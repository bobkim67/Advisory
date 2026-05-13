# R-1G.2 Three-way Portfolio Comparison (FUND)

> schema_version: r1g2.1
> Read-only dry-run. `production_applied=false`, `dry_run_only=true`, `portfolio_builder_applied=true`.
> manager_override_saa layer is SEPARATE; baseline SAA telemetry preserved.

## ⚠ Validity Summary (R-1G.2)

- **valid_asset_level_dry_run** = true
- **valid_product_level_portfolio** = true, **product_weight_sum_valid** = true (R-1G.2 product_weight_sum = 1.000000)
- **implementation_ready** = false, **implementation_review_status** = `review_required`, **sign_off_required_for_production** = true
- `product_allocation_method` = `full_reselection`, `portfolio_builder_applied` = true

> **R-1G.2 reaches a portfolio-valid dry-run, but implementation_ready stays `false`** until 운용역 sign-off + Decision Register entry + Phase F gate.

## §1. As-of separation

- selection_as_of: **20260513**
- output_as_of: **20260513**
- baseline_portfolio_as_of: **20260511**
- universe_as_of: **20260511**

## §2. Selected Candidate

- candidate_id: **cand_009678**. target_weight_source: `r1f2_projection_final_asset_weights`.

## §3. 3-way Headline

| metric | A. baseline (max-Sharpe) | B. R-1F.2 (proportional) | C. R-1G.2 (full reselection + builder) |
|---|---:|---:|---:|
| product_weight_sum | 1.000000 | 0.732775 | **1.000000** |
| n_products | 17 | 17 | **26** |
| valid_product_level_portfolio | true (baseline) | **false** | **true** |
| dm_ex_us_equity n_picks | 3 | 3 | **3** |
| us_high_yield n_picks | 3 | 3 | **3** |

## §4. Asset Weights (3-way)

| asset | A baseline | B R-1F.2 dry-run | C R-1G.2 | Δ (C − A) |
|---|---:|---:|---:|---:|
| kr_equity | 1.00% | 17.63% | 17.63% | 16.63% |
| us_growth_equity | 70.60% | 20.82% | 20.82% | -49.78% |
| us_value_equity | 27.40% | 23.64% | 23.64% | -3.75% |
| dm_ex_us_equity | 0.00% | 10.72% | 10.72% | 10.72% |
| em_equity | 1.00% | 11.19% | 11.19% | 10.19% |
| kr_aggregate_bond | 0.00% | 3.86% | 3.86% | 3.86% |
| kr_treasury_10y | 0.00% | 3.57% | 3.57% | 3.57% |
| us_treasury_30y | 0.00% | 1.01% | 1.01% | 1.01% |
| us_high_yield | 0.00% | 7.57% | 7.57% | 7.57% |

## §5. Per-asset Product Counts & R-1G.2 Allocation

| asset | A picks | B picks | C picks | C alloc | C target |
|---|---:|---:|---:|---:|---:|
| kr_equity | 3 | 3 | **3** | 17.63% | 17.63% |
| us_growth_equity | 3 | 3 | **3** | 20.82% | 20.82% |
| us_value_equity | 2 | 2 | **2** | 23.64% | 23.64% |
| dm_ex_us_equity | 3 | 3 | **3** | 10.72% | 10.72% |
| em_equity | 3 | 3 | **3** | 11.19% | 11.19% |
| kr_aggregate_bond | 0 | 0 | **3** | 3.86% | 3.86% |
| kr_treasury_10y | 0 | 0 | **3** | 3.57% | 3.57% |
| us_treasury_30y | 0 | 0 | **3** | 1.01% | 1.01% |
| us_high_yield | 3 | 3 | **3** | 7.57% | 7.57% |

## §6. R-1G.2 Newly-introduced Asset Products
(baseline 0% 였던 자산: dm_ex_us_equity, us_high_yield)

### dm_ex_us_equity

| product_id | product_name | manager | role | weight |
|---|---|---|---|---:|
| 42669 | 한화천연자원자(주식)P클래스 | 한화운용 | core | 8.58% |
| 71463 | 피델리티재팬자(주식-재간접)CP | 피델리티운용 | satellite | 1.07% |
| 70744 | 삼성일본리더스전환자 1[주식](Cp(퇴직연금)) | 삼성운용 | satellite | 1.07% |

### us_high_yield

| product_id | product_name | manager | role | weight |
|---|---|---|---|---:|
| 71800 | 베어링글로벌하이일드자[UH](채권-재간접)ClassC-P2e | 베어링운용 | core | 6.05% |
| 71791 | 베어링글로벌하이일드자[H](채권-재간접)ClassC-P2 | 베어링운용 | satellite | 0.76% |
| 74369 | 교보악사미국코어하이일드자(UH)[채권-재간접]_ClassC-Re(퇴직연금) | 교보악사운용 | satellite | 0.76% |

## §7. Top Changed Assets (|R-1G.2 − baseline|)

| # | asset | Δ |
|---:|---|---:|
| 1 | us_growth_equity | -49.78% |
| 2 | kr_equity | 16.63% |
| 3 | dm_ex_us_equity | 10.72% |
| 4 | em_equity | 10.19% |
| 5 | us_high_yield | 7.57% |

## §8. Top Changed Products (|R-1G.2 − baseline|, top 10)

| # | product_id | name | manager | A base | C R-1G.2 | Δ |
|---:|---|---|---|---:|---:|---:|
| 1 | 74176 | 삼성미국그로스자UH[주식-재간접]_Cp(퇴직연금) | 삼성운용 | 20.30% | 2.08% | -18.22% |
| 2 | 73125 | AB미국그로스UH(주식-재간접)종류C-P2 | AB자산운용 | 20.30% | 2.08% | -18.22% |
| 3 | 76305 | KB미국대표성장주자(주식)(UH)C-퇴직 | KB운용 | 30.00% | 16.66% | -13.34% |
| 4 | 43306 | 한국밸류10년투자파이오니아(주식)(C-Re) | 한국투자밸류운용 | 0.80% | 14.10% | 13.30% |
| 5 | 42669 | 한화천연자원자(주식)P클래스 | 한화운용 | 0.00% | 8.58% | 8.58% |
| 6 | 2074 | NH-Amundi성장중소형주[주식]ClassC-P2(퇴직연금) | NH-Amundi운용 | 0.80% | 8.95% | 8.15% |
| 7 | 71800 | 베어링글로벌하이일드자[UH](채권-재간접)ClassC-P2e | 베어링운용 | 0.00% | 6.05% | 6.05% |
| 8 | 42351 | HDC알짜배당(주식)종류C-Pe | HDC운용 | 0.00% | 3.09% | 3.09% |
| 9 | 70467 | 한국투자미국배당귀족자UH(주식)(C-R) | 한국투자신탁운용 | 21.92% | 18.91% | -3.00% |
| 10 | 4882 | 한국투자퇴직연금자 1(국공채)(C) | 한국투자신탁운용 | 0.00% | 2.85% | 2.85% |

## §9. Limitation 해소 여부 vs R-1F.2

| issue | R-1F.2 | R-1G.2 |
|---|---|---|
| product_weight_sum ≈ 1.0 | 0.7328 (invalid) | **1.000000** (valid) |
| needs_selection_rerun_assets | ['dm_ex_us_equity', 'us_high_yield'] | **[]** |
| dm_ex_us_equity selected | 3 | **3** |
| us_high_yield selected | 3 | **3** |

## §10. Remaining Warnings / Notes

- quality review_reasons: (none)

## §11. Why `implementation_ready = false`

- R-1G.2 produces a product-level **portfolio-valid** dry-run (when `valid_product_level_portfolio=true`), but **does not** authorize production implementation.
- 운용역의 sign-off, Decision Register 신규 entry, 그리고 별도 Phase F gate 통과 후에만 `implementation_ready` 를 검토할 수 있다 (자동 승격 금지).
- 본 turn 까지는 manager_override_saa 가 **별도 layer** 로만 유지되며 production max-Sharpe SAA telemetry 는 그대로 보존된다.
