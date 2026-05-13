# R-1G.2 Three-way Portfolio Comparison (ETF)

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
| product_weight_sum | 1.000000 | 1.551433 | **1.000000** |
| n_products | 17 | 17 | **26** |
| valid_product_level_portfolio | true (baseline) | **false** | **true** |
| dm_ex_us_equity n_picks | 3 | 3 | **3** |
| us_high_yield n_picks | 2 | 2 | **2** |

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
| us_value_equity | 3 | 3 | **3** | 23.64% | 23.64% |
| dm_ex_us_equity | 3 | 3 | **3** | 10.72% | 10.72% |
| em_equity | 3 | 3 | **3** | 11.19% | 11.19% |
| kr_aggregate_bond | 0 | 0 | **3** | 3.86% | 3.86% |
| kr_treasury_10y | 0 | 0 | **3** | 3.57% | 3.57% |
| us_treasury_30y | 0 | 0 | **3** | 1.01% | 1.01% |
| us_high_yield | 2 | 2 | **2** | 7.57% | 7.57% |

## §6. R-1G.2 Newly-introduced Asset Products
(baseline 0% 였던 자산: dm_ex_us_equity, us_high_yield)

### dm_ex_us_equity

| product_id | product_name | manager | role | weight |
|---|---|---|---|---:|
| 238720 | 한국투자ACE일본Nikkei225상장지수(주식-파생)(H) | 한국투자신탁운용 | core | 8.58% |
| 101280 | 삼성KODEX일본TOPIX100상장지수[주식] | 삼성운용 | satellite | 1.07% |
| 251350 | 삼성KODEXMSCI선진국상장지수[주식] | 삼성운용 | satellite | 1.07% |

### us_high_yield

| product_id | product_name | manager | role | weight |
|---|---|---|---|---:|
| 468380 | 삼성KODEXiShares미국하이일드액티브상장지수[채권-재간접] | 삼성운용 | core | 6.05% |
| 455660 | 한국투자ACE미국하이일드액티브상장지수[채권-재간접](H) | 한국투자신탁운용 | satellite | 1.51% |

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
| 1 | 411420 | 삼성KODEX미국나스닥AI테크액티브상장지수[주식] | 삼성운용 | 20.00% | 2.08% | -17.92% |
| 2 | 381180 | 미래에셋TIGER미국필라델피아반도체나스닥상장지수(주식) | 미래에셋운용 | 20.00% | 2.08% | -17.92% |
| 3 | 434730 | NH-AmundiHANARO원자력iSelect상장지수(주식) | NH-Amundi운용 | 1.76% | 14.10% | 12.34% |
| 4 | 238720 | 한국투자ACE일본Nikkei225상장지수(주식-파생)(H) | 한국투자신탁운용 | 0.96% | 8.58% | 7.61% |
| 5 | 446690 | 삼성KODEX아시아AI반도체exChina액티브상장지수[주식] | 삼성운용 | 1.76% | 8.95% | 7.19% |
| 6 | 468380 | 삼성KODEXiShares미국하이일드액티브상장지수[채권-재간접] | 삼성운용 | 0.00% | 6.05% | 6.05% |
| 7 | 426030 | 타임폴리오TIME미국나스닥100액티브상장지수(주식) | 타임폴리오자산운용 | 20.00% | 16.66% | -3.34% |
| 8 | 497880 | 신한SOLCD금리&머니마켓액티브상장지수[채권] | 신한자산운용 | 0.00% | 3.09% | 3.09% |
| 9 | 114820 | 미래에셋TIGER국채3상장지수(채권) | 미래에셋운용 | 0.00% | 2.85% | 2.85% |
| 10 | 446720 | 신한SOL미국배당다우존스상장지수[주식] | 신한자산운용 | 4.66% | 2.36% | -2.30% |

## §9. Limitation 해소 여부 vs R-1F.2

| issue | R-1F.2 | R-1G.2 |
|---|---|---|
| product_weight_sum ≈ 1.0 | 1.5514 (invalid) | **1.000000** (valid) |
| needs_selection_rerun_assets | ['dm_ex_us_equity', 'us_high_yield'] | **[]** |
| dm_ex_us_equity selected | 3 | **3** |
| us_high_yield selected | 2 | **2** |

## §10. Remaining Warnings / Notes

- quality review_reasons: (none)

## §11. Why `implementation_ready = false`

- R-1G.2 produces a product-level **portfolio-valid** dry-run (when `valid_product_level_portfolio=true`), but **does not** authorize production implementation.
- 운용역의 sign-off, Decision Register 신규 entry, 그리고 별도 Phase F gate 통과 후에만 `implementation_ready` 를 검토할 수 있다 (자동 승격 금지).
- 본 turn 까지는 manager_override_saa 가 **별도 layer** 로만 유지되며 production max-Sharpe SAA telemetry 는 그대로 보존된다.
