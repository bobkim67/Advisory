# Manager-Selected SAA Product Re-selection Summary (FUND, R-1G.1)

> schema_version: r1g1.1
> Read-only product re-selection. PortfolioBuilder 연결은 R-1G.2.
> `production_applied=false`, `dry_run_only=true`, `implementation_ready=false`.

## ⚠ Validity Summary (R-1G.1)

- **valid_asset_level_dry_run = true**
- **valid_product_level_portfolio = true**, **product_weight_sum_valid = true** (selected_weight_sum = 1.0000, target_weight_sum = 1.0000)
- **needs_full_product_reselection = false**
- **implementation_ready = false**, **implementation_review_status = `review_required`**
- product_allocation_method = `full_reselection`
- target_weight_source = `r1f2_projection_final_asset_weights`
- universe coverage warnings:
  - asset 'us_value_equity': universe count 2 < target n_core+n_satellite (3); core/satellite picks may be incomplete (fallback handled by R-1G.2 builder).

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
| kr_equity | 9.76% | 9.76% | 0.00% | 99 | 3 |
| us_growth_equity | 25.30% | 25.30% | 0.00% | 10 | 3 |
| us_value_equity | 20.95% | 20.95% | 0.00% | 2 | 2 |
| dm_ex_us_equity | 10.64% | 10.64% | 0.00% | 15 | 3 |
| em_equity | 16.08% | 16.08% | 0.00% | 72 | 3 |
| kr_aggregate_bond | 4.86% | 4.86% | 0.00% | 40 | 3 |
| kr_treasury_10y | 1.53% | 1.53% | 0.00% | 4 | 3 |
| us_treasury_30y | 0.00% | 0.00% | 0.00% | 10 | 3 |
| us_high_yield | 10.89% | 10.89% | 0.00% | 10 | 3 |
| **total** | **100.00%** | **100.00%** | **0.00%** | — | **26** |

## §5. Selected Products

| asset | product_id | product_name | manager | role | weight |
|---|---|---|---|---|---:|
| kr_equity | 43306 | 한국밸류10년투자파이오니아(주식)(C-Re) | 한국투자밸류운용 | core | 7.81% |
| kr_equity | 43040 | NH-Amundi필승코리아[주식]ClassC-P2(퇴직연금) | NH-Amundi운용 | satellite | 0.98% |
| kr_equity | 41944 | 교보악사파워인덱스자 1[주식]ClassCP | 교보악사운용 | satellite | 0.98% |
| us_growth_equity | 76305 | KB미국대표성장주자(주식)(UH)C-퇴직 | KB운용 | core | 20.24% |
| us_growth_equity | 74176 | 삼성미국그로스자UH[주식-재간접]_Cp(퇴직연금) | 삼성운용 | satellite | 2.53% |
| us_growth_equity | 73125 | AB미국그로스UH(주식-재간접)종류C-P2 | AB자산운용 | satellite | 2.53% |
| us_value_equity | 70467 | 한국투자미국배당귀족자UH(주식)(C-R) | 한국투자신탁운용 | core | 16.76% |
| us_value_equity | 70455 | 한국투자미국배당귀족자H(주식)(C-R) | 한국투자신탁운용 | satellite | 4.19% |
| dm_ex_us_equity | 42669 | 한화천연자원자(주식)P클래스 | 한화운용 | core | 8.51% |
| dm_ex_us_equity | 71463 | 피델리티재팬자(주식-재간접)CP | 피델리티운용 | satellite | 1.06% |
| dm_ex_us_equity | 70744 | 삼성일본리더스전환자 1[주식](Cp(퇴직연금)) | 삼성운용 | satellite | 1.06% |
| em_equity | 2074 | NH-Amundi성장중소형주[주식]ClassC-P2(퇴직연금) | NH-Amundi운용 | core | 12.86% |
| em_equity | 71972 | 마이다스아시아리더스성장주자(H)(주식)C-P2 | 마이다스운용 | satellite | 1.61% |
| em_equity | 71976 | 마이다스아시아리더스성장주자(UH)(주식)C-P2 | 마이다스운용 | satellite | 1.61% |
| kr_aggregate_bond | 42351 | HDC알짜배당(주식)종류C-Pe | HDC운용 | core | 3.89% |
| kr_aggregate_bond | 11688 | 코레이트셀렉트단기채[채권]C-P2 | 코레이트운용 | satellite | 0.49% |
| kr_aggregate_bond | 12483 | 삼성스마트MMF법인 1Cp(퇴직연금) | 삼성운용 | satellite | 0.49% |
| kr_treasury_10y | 4882 | 한국투자퇴직연금자 1(국공채)(C) | 한국투자신탁운용 | core | 1.23% |
| kr_treasury_10y | 10795 | KB스타중기국공채자(채권)C-퇴직 클래스 | KB운용 | satellite | 0.15% |
| kr_treasury_10y | 11317 | NH-Amundi국채10년인덱스자[채권]ClassC-P2(퇴직연금) | NH-Amundi운용 | satellite | 0.15% |
| us_treasury_30y | 60389 | 대신미국장기국채밸런스[채권-재간접]종류C-R | 대신운용 | core | 0.00% |
| us_treasury_30y | 71342 | 대신미국장기국채액티브목표전환2[채권-재간접]종류C-R | 대신운용 | satellite | 0.00% |
| us_treasury_30y | 74222 | 삼성미국투자등급장기채권자UH[채권]_Cp(퇴직연금) | 삼성운용 | satellite | 0.00% |
| us_high_yield | 71800 | 베어링글로벌하이일드자[UH](채권-재간접)ClassC-P2e | 베어링운용 | core | 8.71% |
| us_high_yield | 71791 | 베어링글로벌하이일드자[H](채권-재간접)ClassC-P2 | 베어링운용 | satellite | 1.09% |
| us_high_yield | 74369 | 교보악사미국코어하이일드자(UH)[채권-재간접]_ClassC-Re(퇴직연금) | 교보악사운용 | satellite | 1.09% |

## §6. Universe Coverage

- source type: `file`
- product_type: `fund`
- raw_count: 781, filtered_count: 262

| asset | universe count |
|---|---:|
| kr_equity | 99 |
| kr_aggregate_bond | 40 |
| em_equity | 72 |
| kr_treasury_10y | 4 |
| us_value_equity | 2 |
| us_growth_equity | 10 |
| dm_ex_us_equity | 15 |
| us_high_yield | 10 |
| us_treasury_30y | 10 |

## §7. Limitations / Next Step

- R-1G.1 은 **product re-selection only**. PortfolioBuilder fallback / drift clipping / quality validation 미적용. R-1G.2 에서 builder 연결 후 3-way (baseline / R-1F.2 / R-1G) 비교 진행.
- production 반영은 본 R-1G.1 범위 밖. 별도 Phase F sign-off 필수.
