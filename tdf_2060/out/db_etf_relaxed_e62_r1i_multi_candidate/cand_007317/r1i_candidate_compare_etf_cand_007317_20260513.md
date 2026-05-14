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

- candidate_id: **cand_007317**. target_weight_source: `r1f2_projection_final_asset_weights`.

## §3. 3-way Headline

| metric | A. baseline (max-Sharpe) | B. R-1F.2 (proportional) | C. R-1G.2 (full reselection + builder) |
|---|---:|---:|---:|
| product_weight_sum | 1.000000 | 1.128224 | **1.000000** |
| n_products | 17 | 17 | **26** |
| valid_product_level_portfolio | true (baseline) | **false** | **true** |
| dm_ex_us_equity n_picks | 3 | 3 | **3** |
| us_high_yield n_picks | 2 | 2 | **2** |

## §4. Asset Weights (3-way)

| asset | A baseline | B R-1F.2 dry-run | C R-1G.2 | Δ (C − A) |
|---|---:|---:|---:|---:|
| kr_equity | 1.00% | 10.27% | 10.27% | 9.27% |
| us_growth_equity | 70.60% | 54.52% | 54.52% | -16.08% |
| us_value_equity | 27.40% | 14.07% | 14.07% | -13.33% |
| dm_ex_us_equity | 0.00% | 0.59% | 0.59% | 0.59% |
| em_equity | 1.00% | 2.94% | 2.94% | 1.94% |
| kr_aggregate_bond | 0.00% | 0.50% | 0.50% | 0.50% |
| kr_treasury_10y | 0.00% | 0.17% | 0.17% | 0.17% |
| us_treasury_30y | 0.00% | 0.00% | 0.00% | 0.00% |
| us_high_yield | 0.00% | 16.93% | 16.93% | 16.93% |

## §5. Per-asset Product Counts & R-1G.2 Allocation

| asset | A picks | B picks | C picks | C alloc | C target |
|---|---:|---:|---:|---:|---:|
| kr_equity | 3 | 3 | **3** | 10.27% | 10.27% |
| us_growth_equity | 3 | 3 | **3** | 54.52% | 54.52% |
| us_value_equity | 3 | 3 | **3** | 14.07% | 14.07% |
| dm_ex_us_equity | 3 | 3 | **3** | 0.59% | 0.59% |
| em_equity | 3 | 3 | **3** | 2.94% | 2.94% |
| kr_aggregate_bond | 0 | 0 | **3** | 0.50% | 0.50% |
| kr_treasury_10y | 0 | 0 | **3** | 0.17% | 0.17% |
| us_treasury_30y | 0 | 0 | **3** | 0.00% | 0.00% |
| us_high_yield | 2 | 2 | **2** | 16.93% | 16.93% |

## §6. R-1G.2 Newly-introduced Asset Products
(baseline 0% 였던 자산: dm_ex_us_equity, us_high_yield)

### dm_ex_us_equity

| product_id | product_name | manager | role | weight |
|---|---|---|---|---:|
| 238720 | 한국투자ACE일본Nikkei225상장지수(주식-파생)(H) | 한국투자신탁운용 | core | 0.47% |
| 101280 | 삼성KODEX일본TOPIX100상장지수[주식] | 삼성운용 | satellite | 0.06% |
| 251350 | 삼성KODEXMSCI선진국상장지수[주식] | 삼성운용 | satellite | 0.06% |

### us_high_yield

| product_id | product_name | manager | role | weight |
|---|---|---|---|---:|
| 468380 | 삼성KODEXiShares미국하이일드액티브상장지수[채권-재간접] | 삼성운용 | core | 13.54% |
| 455660 | 한국투자ACE미국하이일드액티브상장지수[채권-재간접](H) | 한국투자신탁운용 | satellite | 3.39% |

## §7. Top Changed Assets (|R-1G.2 − baseline|)

| # | asset | Δ |
|---:|---|---:|
| 1 | us_high_yield | 16.93% |
| 2 | us_growth_equity | -16.08% |
| 3 | us_value_equity | -13.33% |
| 4 | kr_equity | 9.27% |
| 5 | em_equity | 1.94% |

## §8. Top Changed Products (|R-1G.2 − baseline|, top 10)

| # | product_id | name | manager | A base | C R-1G.2 | Δ |
|---:|---|---|---|---:|---:|---:|
| 1 | 468380 | 삼성KODEXiShares미국하이일드액티브상장지수[채권-재간접] | 삼성운용 | 0.00% | 13.54% | 13.54% |
| 2 | 402970 | 한국투자ACE미국배당다우존스상장지수(주식) | 한국투자신탁운용 | 20.00% | 11.25% | -8.75% |
| 3 | 434730 | NH-AmundiHANARO원자력iSelect상장지수(주식) | NH-Amundi운용 | 1.76% | 8.22% | 6.45% |
| 4 | 455660 | 한국투자ACE미국하이일드액티브상장지수[채권-재간접](H) | 한국투자신탁운용 | 0.00% | 3.39% | 3.39% |
| 5 | 446720 | 신한SOL미국배당다우존스상장지수[주식] | 신한자산운용 | 4.66% | 1.41% | -3.26% |
| 6 | 429000 | 미래에셋TIGER미국S&P500배당귀족상장지수(주식) | 미래에셋운용 | 4.66% | 1.41% | -3.26% |
| 7 | 411420 | 삼성KODEX미국나스닥AI테크액티브상장지수[주식] | 삼성운용 | 20.00% | 17.26% | -2.74% |
| 8 | 381180 | 미래에셋TIGER미국필라델피아반도체나스닥상장지수(주식) | 미래에셋운용 | 20.00% | 17.26% | -2.74% |
| 9 | 101280 | 삼성KODEX일본TOPIX100상장지수[주식] | 삼성운용 | 0.96% | 0.06% | -0.90% |
| 10 | 251350 | 삼성KODEXMSCI선진국상장지수[주식] | 삼성운용 | 0.96% | 0.06% | -0.90% |

## §9. Limitation 해소 여부 vs R-1F.2

| issue | R-1F.2 | R-1G.2 |
|---|---|---|
| product_weight_sum ≈ 1.0 | 1.1282 (invalid) | **1.000000** (valid) |
| needs_selection_rerun_assets | ['dm_ex_us_equity', 'us_high_yield'] | **[]** |
| dm_ex_us_equity selected | 3 | **3** |
| us_high_yield selected | 2 | **2** |

## §10. Remaining Warnings / Notes

- quality review_reasons:
  - fallback used (max_drift=0.0000; drift enforcement=telemetry_only)

## §11. Why `implementation_ready = false`

- R-1G.2 produces a product-level **portfolio-valid** dry-run (when `valid_product_level_portfolio=true`), but **does not** authorize production implementation.
- 운용역의 sign-off, Decision Register 신규 entry, 그리고 별도 Phase F gate 통과 후에만 `implementation_ready` 를 검토할 수 있다 (자동 승격 금지).
- 본 turn 까지는 manager_override_saa 가 **별도 layer** 로만 유지되며 production max-Sharpe SAA telemetry 는 그대로 보존된다.
