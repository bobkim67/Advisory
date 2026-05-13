# Manager-Selected SAA Product Re-selection Summary (ETF, R-1G.1)

> schema_version: r1g1.1
> Read-only product re-selection. PortfolioBuilder 연결은 R-1G.2.
> `production_applied=false`, `dry_run_only=true`, `implementation_ready=false`.

## ⚠ Validity Summary (R-1G.1)

- **valid_asset_level_dry_run = true**
- **valid_product_level_portfolio = false**, **product_weight_sum_valid = false** (selected_weight_sum = 0.9976, target_weight_sum = 1.0000)
- **needs_full_product_reselection = true**
- **implementation_ready = false**, **implementation_review_status = `review_required`**
- product_allocation_method = `full_reselection`
- target_weight_source = `r1f2_projection_final_asset_weights`
- universe coverage warnings:
  - asset 'us_high_yield': universe count 2 < target n_core+n_satellite (3); core/satellite picks may be incomplete (fallback handled by R-1G.2 builder).

## §1. As-of date separation

- selection_as_of: **20260513**
- output_as_of: **20260513**
- baseline_portfolio_as_of: **20260511**
- universe_as_of: **20260511**

## §2. Selected Candidate

- candidate_id: **cand_008421** (see Final Manager Review Packet for context)

## §3. Target Asset Weights (= R-1F.2 projection final)

| asset | target weight |
|---|---:|
| kr_equity | 9.76% |
| us_growth_equity | 25.30% |
| us_value_equity | 20.95% |
| dm_ex_us_equity | 10.64% |
| em_equity | 16.08% |
| kr_aggregate_bond | 4.86% |
| kr_treasury_10y | 1.53% |
| us_treasury_30y | 0.00% |
| us_high_yield | 10.89% |
| **sum** | **100.00%** |

## §4. Per-asset Selection Summary

| asset | target | allocated | unfilled | n_universe | n_selected |
|---|---:|---:|---:|---:|---:|
| kr_equity | 9.76% | 9.76% | 0.00% | 347 | 3 |
| us_growth_equity | 25.30% | 25.06% | 0.24% | 22 | 3 |
| us_value_equity | 20.95% | 20.95% | 0.00% | 18 | 3 |
| dm_ex_us_equity | 10.64% | 10.64% | 0.00% | 15 | 3 |
| em_equity | 16.08% | 16.08% | 0.00% | 55 | 3 |
| kr_aggregate_bond | 4.86% | 4.86% | 0.00% | 97 | 3 |
| kr_treasury_10y | 1.53% | 1.53% | 0.00% | 10 | 3 |
| us_treasury_30y | 0.00% | 0.00% | 0.00% | 6 | 3 |
| us_high_yield | 10.89% | 10.89% | 0.00% | 2 | 2 |
| **total** | **100.00%** | **99.76%** | **0.24%** | — | **26** |

## §5. Selected Products

| asset | product_id | product_name | manager | role | weight |
|---|---|---|---|---|---:|
| kr_equity | 434730 | NH-AmundiHANARO원자력iSelect상장지수(주식) | NH-Amundi운용 | core | 7.81% |
| kr_equity | 449450 | 한화PLUSK방산상장지수(주식) | 한화운용 | satellite | 0.98% |
| kr_equity | 433500 | 한국투자ACE원자력TOP10상장지수(주식) | 한국투자신탁운용 | satellite | 0.98% |
| us_growth_equity | 426030 | 타임폴리오TIME미국나스닥100액티브상장지수(주식) | 타임폴리오자산운용 | core | 20.00% |
| us_growth_equity | 411420 | 삼성KODEX미국나스닥AI테크액티브상장지수[주식] | 삼성운용 | satellite | 2.53% |
| us_growth_equity | 381180 | 미래에셋TIGER미국필라델피아반도체나스닥상장지수(주식) | 미래에셋운용 | satellite | 2.53% |
| us_value_equity | 402970 | 한국투자ACE미국배당다우존스상장지수(주식) | 한국투자신탁운용 | core | 16.76% |
| us_value_equity | 446720 | 신한SOL미국배당다우존스상장지수[주식] | 신한자산운용 | satellite | 2.09% |
| us_value_equity | 429000 | 미래에셋TIGER미국S&P500배당귀족상장지수(주식) | 미래에셋운용 | satellite | 2.09% |
| dm_ex_us_equity | 238720 | 한국투자ACE일본Nikkei225상장지수(주식-파생)(H) | 한국투자신탁운용 | core | 8.51% |
| dm_ex_us_equity | 101280 | 삼성KODEX일본TOPIX100상장지수[주식] | 삼성운용 | satellite | 1.06% |
| dm_ex_us_equity | 251350 | 삼성KODEXMSCI선진국상장지수[주식] | 삼성운용 | satellite | 1.06% |
| em_equity | 446690 | 삼성KODEX아시아AI반도체exChina액티브상장지수[주식] | 삼성운용 | core | 12.86% |
| em_equity | 105010 | 미래에셋TIGER라틴상장지수(주식) | 미래에셋운용 | satellite | 1.61% |
| em_equity | 277540 | 한국투자ACE아시아TOP50상장지수(주식) | 한국투자신탁운용 | satellite | 1.61% |
| kr_aggregate_bond | 497880 | 신한SOLCD금리&머니마켓액티브상장지수[채권] | 신한자산운용 | core | 3.89% |
| kr_aggregate_bond | 487340 | 한국투자ACE머니마켓액티브상장지수(채권) | 한국투자신탁운용 | satellite | 0.49% |
| kr_aggregate_bond | 488770 | 삼성KODEX머니마켓액티브상장지수[채권] | 삼성운용 | satellite | 0.49% |
| kr_treasury_10y | 114820 | 미래에셋TIGER국채3상장지수(채권) | 미래에셋운용 | core | 1.23% |
| kr_treasury_10y | 438570 | 신한SOL국고채10년상장지수[채권] | 신한자산운용 | satellite | 0.15% |
| kr_treasury_10y | 461460 | 한화PLUS국고채10년액티브상장지수(채권) | 한화운용 | satellite | 0.15% |
| us_treasury_30y | 476760 | 한국투자ACE미국30년국채액티브상장지수[채권] | 한국투자신탁운용 | core | 0.00% |
| us_treasury_30y | 481340 | KBRISE미국30년국채액티브상장지수(채권) | KB운용 | satellite | 0.00% |
| us_treasury_30y | 484790 | 삼성KODEX미국30년국채액티브상장지수[채권-재간접](H) | 삼성운용 | satellite | 0.00% |
| us_high_yield | 468380 | 삼성KODEXiShares미국하이일드액티브상장지수[채권-재간접] | 삼성운용 | core | 8.71% |
| us_high_yield | 455660 | 한국투자ACE미국하이일드액티브상장지수[채권-재간접](H) | 한국투자신탁운용 | satellite | 2.18% |

## §6. Universe Coverage

- source type: `file`
- product_type: `etf`
- raw_count: 932, filtered_count: 572

| asset | universe count |
|---|---:|
| kr_equity | 347 |
| dm_ex_us_equity | 15 |
| em_equity | 55 |
| kr_treasury_10y | 10 |
| kr_aggregate_bond | 97 |
| us_growth_equity | 22 |
| us_value_equity | 18 |
| us_treasury_30y | 6 |
| us_high_yield | 2 |

## §7. Limitations / Next Step

- R-1G.1 은 **product re-selection only**. PortfolioBuilder fallback / drift clipping / quality validation 미적용. R-1G.2 에서 builder 연결 후 3-way (baseline / R-1F.2 / R-1G) 비교 진행.
- `valid_product_level_portfolio = false` — selection 단계만으로 sum=1.0 또는 모든 자산 cover 달성 못 함. R-1G.2 builder 의 fallback / drift clipping 이 잔여 weight 흡수해야 함.
- production 반영은 본 R-1G.1 범위 밖. 별도 Phase F sign-off 필수.
