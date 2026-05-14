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

- candidate_id: **cand_000758**. target_weight_source: `r1f2_projection_final_asset_weights`.

## §3. 3-way Headline

| metric | A. baseline (max-Sharpe) | B. R-1F.2 (proportional) | C. R-1G.2 (full reselection + builder) |
|---|---:|---:|---:|
| product_weight_sum | 1.000000 | 1.422759 | **1.000000** |
| n_products | 17 | 17 | **26** |
| valid_product_level_portfolio | true (baseline) | **false** | **true** |
| dm_ex_us_equity n_picks | 3 | 3 | **3** |
| us_high_yield n_picks | 2 | 2 | **2** |

## §4. Asset Weights (3-way)

| asset | A baseline | B R-1F.2 dry-run | C R-1G.2 | Δ (C − A) |
|---|---:|---:|---:|---:|
| kr_equity | 1.00% | 18.35% | 18.35% | 17.35% |
| us_growth_equity | 70.60% | 22.98% | 22.98% | -47.62% |
| us_value_equity | 27.40% | 18.21% | 18.21% | -9.18% |
| dm_ex_us_equity | 0.00% | 16.28% | 16.28% | 16.28% |
| em_equity | 1.00% | 8.18% | 8.18% | 7.18% |
| kr_aggregate_bond | 0.00% | 3.71% | 3.71% | 3.71% |
| kr_treasury_10y | 0.00% | 6.34% | 6.34% | 6.34% |
| us_treasury_30y | 0.00% | 1.40% | 1.40% | 1.40% |
| us_high_yield | 0.00% | 4.55% | 4.55% | 4.55% |

## §5. Per-asset Product Counts & R-1G.2 Allocation

| asset | A picks | B picks | C picks | C alloc | C target |
|---|---:|---:|---:|---:|---:|
| kr_equity | 3 | 3 | **3** | 18.35% | 18.35% |
| us_growth_equity | 3 | 3 | **3** | 22.98% | 22.98% |
| us_value_equity | 3 | 3 | **3** | 18.21% | 18.21% |
| dm_ex_us_equity | 3 | 3 | **3** | 16.28% | 16.28% |
| em_equity | 3 | 3 | **3** | 8.18% | 8.18% |
| kr_aggregate_bond | 0 | 0 | **3** | 3.71% | 3.71% |
| kr_treasury_10y | 0 | 0 | **3** | 6.34% | 6.34% |
| us_treasury_30y | 0 | 0 | **3** | 1.40% | 1.40% |
| us_high_yield | 2 | 2 | **2** | 4.55% | 4.55% |

## §6. R-1G.2 Newly-introduced Asset Products
(baseline 0% 였던 자산: dm_ex_us_equity, us_high_yield)

### dm_ex_us_equity

| product_id | product_name | manager | role | weight |
|---|---|---|---|---:|
| 238720 | 한국투자ACE일본Nikkei225상장지수(주식-파생)(H) | 한국투자신탁운용 | core | 13.02% |
| 101280 | 삼성KODEX일본TOPIX100상장지수[주식] | 삼성운용 | satellite | 1.63% |
| 251350 | 삼성KODEXMSCI선진국상장지수[주식] | 삼성운용 | satellite | 1.63% |

### us_high_yield

| product_id | product_name | manager | role | weight |
|---|---|---|---|---:|
| 468380 | 삼성KODEXiShares미국하이일드액티브상장지수[채권-재간접] | 삼성운용 | core | 3.64% |
| 455660 | 한국투자ACE미국하이일드액티브상장지수[채권-재간접](H) | 한국투자신탁운용 | satellite | 0.91% |

## §7. Top Changed Assets (|R-1G.2 − baseline|)

| # | asset | Δ |
|---:|---|---:|
| 1 | us_growth_equity | -47.62% |
| 2 | kr_equity | 17.35% |
| 3 | dm_ex_us_equity | 16.28% |
| 4 | us_value_equity | -9.18% |
| 5 | em_equity | 7.18% |

## §8. Top Changed Products (|R-1G.2 − baseline|, top 10)

| # | product_id | name | manager | A base | C R-1G.2 | Δ |
|---:|---|---|---|---:|---:|---:|
| 1 | 411420 | 삼성KODEX미국나스닥AI테크액티브상장지수[주식] | 삼성운용 | 20.00% | 2.30% | -17.70% |
| 2 | 381180 | 미래에셋TIGER미국필라델피아반도체나스닥상장지수(주식) | 미래에셋운용 | 20.00% | 2.30% | -17.70% |
| 3 | 434730 | NH-AmundiHANARO원자력iSelect상장지수(주식) | NH-Amundi운용 | 1.76% | 14.68% | 12.92% |
| 4 | 238720 | 한국투자ACE일본Nikkei225상장지수(주식-파생)(H) | 한국투자신탁운용 | 0.96% | 13.02% | 12.06% |
| 5 | 402970 | 한국투자ACE미국배당다우존스상장지수(주식) | 한국투자신탁운용 | 20.00% | 14.57% | -5.43% |
| 6 | 114820 | 미래에셋TIGER국채3상장지수(채권) | 미래에셋운용 | 0.00% | 5.07% | 5.07% |
| 7 | 446690 | 삼성KODEX아시아AI반도체exChina액티브상장지수[주식] | 삼성운용 | 1.76% | 6.54% | 4.78% |
| 8 | 468380 | 삼성KODEXiShares미국하이일드액티브상장지수[채권-재간접] | 삼성운용 | 0.00% | 3.64% | 3.64% |
| 9 | 497880 | 신한SOLCD금리&머니마켓액티브상장지수[채권] | 신한자산운용 | 0.00% | 2.97% | 2.97% |
| 10 | 446720 | 신한SOL미국배당다우존스상장지수[주식] | 신한자산운용 | 4.66% | 1.82% | -2.84% |

## §9. Limitation 해소 여부 vs R-1F.2

| issue | R-1F.2 | R-1G.2 |
|---|---|---|
| product_weight_sum ≈ 1.0 | 1.4228 (invalid) | **1.000000** (valid) |
| needs_selection_rerun_assets | ['dm_ex_us_equity', 'us_high_yield'] | **[]** |
| dm_ex_us_equity selected | 3 | **3** |
| us_high_yield selected | 2 | **2** |

## §10. Remaining Warnings / Notes

- quality review_reasons: (none)

## §11. Why `implementation_ready = false`

- R-1G.2 produces a product-level **portfolio-valid** dry-run (when `valid_product_level_portfolio=true`), but **does not** authorize production implementation.
- 운용역의 sign-off, Decision Register 신규 entry, 그리고 별도 Phase F gate 통과 후에만 `implementation_ready` 를 검토할 수 있다 (자동 승격 금지).
- 본 turn 까지는 manager_override_saa 가 **별도 layer** 로만 유지되며 production max-Sharpe SAA telemetry 는 그대로 보존된다.
