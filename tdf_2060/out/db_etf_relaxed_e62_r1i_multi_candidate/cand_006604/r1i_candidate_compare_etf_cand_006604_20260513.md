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

- candidate_id: **cand_006604**. target_weight_source: `r1f2_projection_final_asset_weights`.

## §3. 3-way Headline

| metric | A. baseline (max-Sharpe) | B. R-1F.2 (proportional) | C. R-1G.2 (full reselection + builder) |
|---|---:|---:|---:|
| product_weight_sum | 1.000000 | 1.683096 | **1.000000** |
| n_products | 17 | 17 | **26** |
| valid_product_level_portfolio | true (baseline) | **false** | **true** |
| dm_ex_us_equity n_picks | 3 | 3 | **3** |
| us_high_yield n_picks | 2 | 2 | **2** |

## §4. Asset Weights (3-way)

| asset | A baseline | B R-1F.2 dry-run | C R-1G.2 | Δ (C − A) |
|---|---:|---:|---:|---:|
| kr_equity | 1.00% | 17.66% | 17.66% | 16.66% |
| us_growth_equity | 70.60% | 16.93% | 16.93% | -53.67% |
| us_value_equity | 27.40% | 16.59% | 16.59% | -10.81% |
| dm_ex_us_equity | 0.00% | 15.50% | 15.50% | 15.50% |
| em_equity | 1.00% | 17.32% | 17.32% | 16.32% |
| kr_aggregate_bond | 0.00% | 2.52% | 2.52% | 2.52% |
| kr_treasury_10y | 0.00% | 2.35% | 2.35% | 2.35% |
| us_treasury_30y | 0.00% | 0.10% | 0.10% | 0.10% |
| us_high_yield | 0.00% | 11.03% | 11.03% | 11.03% |

## §5. Per-asset Product Counts & R-1G.2 Allocation

| asset | A picks | B picks | C picks | C alloc | C target |
|---|---:|---:|---:|---:|---:|
| kr_equity | 3 | 3 | **3** | 17.66% | 17.66% |
| us_growth_equity | 3 | 3 | **3** | 16.93% | 16.93% |
| us_value_equity | 3 | 3 | **3** | 16.59% | 16.59% |
| dm_ex_us_equity | 3 | 3 | **3** | 15.50% | 15.50% |
| em_equity | 3 | 3 | **3** | 17.32% | 17.32% |
| kr_aggregate_bond | 0 | 0 | **3** | 2.52% | 2.52% |
| kr_treasury_10y | 0 | 0 | **3** | 2.35% | 2.35% |
| us_treasury_30y | 0 | 0 | **3** | 0.10% | 0.10% |
| us_high_yield | 2 | 2 | **2** | 11.03% | 11.03% |

## §6. R-1G.2 Newly-introduced Asset Products
(baseline 0% 였던 자산: dm_ex_us_equity, us_high_yield)

### dm_ex_us_equity

| product_id | product_name | manager | role | weight |
|---|---|---|---|---:|
| 238720 | 한국투자ACE일본Nikkei225상장지수(주식-파생)(H) | 한국투자신탁운용 | core | 12.40% |
| 101280 | 삼성KODEX일본TOPIX100상장지수[주식] | 삼성운용 | satellite | 1.55% |
| 251350 | 삼성KODEXMSCI선진국상장지수[주식] | 삼성운용 | satellite | 1.55% |

### us_high_yield

| product_id | product_name | manager | role | weight |
|---|---|---|---|---:|
| 468380 | 삼성KODEXiShares미국하이일드액티브상장지수[채권-재간접] | 삼성운용 | core | 8.82% |
| 455660 | 한국투자ACE미국하이일드액티브상장지수[채권-재간접](H) | 한국투자신탁운용 | satellite | 2.21% |

## §7. Top Changed Assets (|R-1G.2 − baseline|)

| # | asset | Δ |
|---:|---|---:|
| 1 | us_growth_equity | -53.67% |
| 2 | kr_equity | 16.66% |
| 3 | em_equity | 16.32% |
| 4 | dm_ex_us_equity | 15.50% |
| 5 | us_high_yield | 11.03% |

## §8. Top Changed Products (|R-1G.2 − baseline|, top 10)

| # | product_id | name | manager | A base | C R-1G.2 | Δ |
|---:|---|---|---|---:|---:|---:|
| 1 | 411420 | 삼성KODEX미국나스닥AI테크액티브상장지수[주식] | 삼성운용 | 20.00% | 1.69% | -18.31% |
| 2 | 381180 | 미래에셋TIGER미국필라델피아반도체나스닥상장지수(주식) | 미래에셋운용 | 20.00% | 1.69% | -18.31% |
| 3 | 434730 | NH-AmundiHANARO원자력iSelect상장지수(주식) | NH-Amundi운용 | 1.76% | 14.13% | 12.37% |
| 4 | 446690 | 삼성KODEX아시아AI반도체exChina액티브상장지수[주식] | 삼성운용 | 1.76% | 13.86% | 12.09% |
| 5 | 238720 | 한국투자ACE일본Nikkei225상장지수(주식-파생)(H) | 한국투자신탁운용 | 0.96% | 12.40% | 11.43% |
| 6 | 468380 | 삼성KODEXiShares미국하이일드액티브상장지수[채권-재간접] | 삼성운용 | 0.00% | 8.82% | 8.82% |
| 7 | 402970 | 한국투자ACE미국배당다우존스상장지수(주식) | 한국투자신탁운용 | 20.00% | 13.27% | -6.73% |
| 8 | 426030 | 타임폴리오TIME미국나스닥100액티브상장지수(주식) | 타임폴리오자산운용 | 20.00% | 13.55% | -6.45% |
| 9 | 446720 | 신한SOL미국배당다우존스상장지수[주식] | 신한자산운용 | 4.66% | 1.66% | -3.00% |
| 10 | 429000 | 미래에셋TIGER미국S&P500배당귀족상장지수(주식) | 미래에셋운용 | 4.66% | 1.66% | -3.00% |

## §9. Limitation 해소 여부 vs R-1F.2

| issue | R-1F.2 | R-1G.2 |
|---|---|---|
| product_weight_sum ≈ 1.0 | 1.6831 (invalid) | **1.000000** (valid) |
| needs_selection_rerun_assets | ['dm_ex_us_equity', 'us_high_yield'] | **[]** |
| dm_ex_us_equity selected | 3 | **3** |
| us_high_yield selected | 2 | **2** |

## §10. Remaining Warnings / Notes

- quality review_reasons: (none)

## §11. Why `implementation_ready = false`

- R-1G.2 produces a product-level **portfolio-valid** dry-run (when `valid_product_level_portfolio=true`), but **does not** authorize production implementation.
- 운용역의 sign-off, Decision Register 신규 entry, 그리고 별도 Phase F gate 통과 후에만 `implementation_ready` 를 검토할 수 있다 (자동 승격 금지).
- 본 turn 까지는 manager_override_saa 가 **별도 layer** 로만 유지되며 production max-Sharpe SAA telemetry 는 그대로 보존된다.
