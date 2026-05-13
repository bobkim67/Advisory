# Manager-Selected SAA Dry-Run Comparison (FUND, R-1F.2)

> schema_version: r1f2.1
> Read-only dry-run. `production_applied=false`, `dry_run_only=true`.
> Baseline portfolio JSON / production directory **변경 0**.

## ⚠ Validity Warning (R-1F.2.1)

- **valid_asset_level_dry_run = true** — TAA + projection at the asset allocation level is reviewable.
- **valid_product_level_portfolio = false**, **product_weight_sum_valid = false** (product_weight_sum_dry_run = 0.7209, expected ≈ 1.0).
- **needs_full_product_reselection = true**, **implementation_ready = false**.
- product_allocation_method = `baseline_proportional_scaling`. Baseline zero-weight assets cannot be reallocated by this method.
- **needs_selection_rerun_assets**: ['dm_ex_us_equity', 'us_high_yield']

> **본 결과는 asset-level TAA/projection 검토용이다.** Product allocation 은 proportional scaling approximation 이며 product_weight_sum_dry_run = 0.7209 ≠ 1.0 이므로 **운용 가능한 최종 포트폴리오가 아니다**. Product-level manager review 전에는 **R-1G full product re-selection 이 필요**하다.

## §1. Selected Candidate

- candidate_id: **cand_008421** (group / shortlist 정보는 Final Manager Review Packet 참조)
- Sharpe: 0.6277, E[R]: 10.97%, σ: 12.69%, HHI: 0.1635, max_w: 25.56%
- baseline (max-Sharpe SAA) reference: see baseline portfolio JSON `diagnostics.saa_diagnostics`.

## §2. SAA-level Asset Weight Delta

| asset | baseline max-Sharpe SAA | manager_override SAA | delta |
|---|---:|---:|---:|
| kr_equity | 0.00% | 8.01% | 8.01% |
| us_growth_equity | 71.60% | 25.56% | -46.05% |
| us_value_equity | 28.40% | 21.20% | -7.19% |
| dm_ex_us_equity | 0.00% | 10.89% | 10.89% |
| em_equity | 0.00% | 14.33% | 14.33% |
| kr_aggregate_bond | 0.00% | 5.11% | 5.11% |
| kr_treasury_10y | 0.00% | 3.79% | 3.79% |
| us_treasury_30y | 0.00% | 0.96% | 0.96% |
| us_high_yield | 0.00% | 10.14% | 10.14% |

## §3. Final Asset Weight Delta (after TAA + projection)

| asset | bucket | baseline final | dry-run final | delta |
|---|---|---:|---:|---:|
| kr_equity | equity | 1.00% | 9.76% | 8.76% |
| us_growth_equity | equity | 70.60% | 25.30% | -45.30% |
| us_value_equity | equity | 27.40% | 20.95% | -6.45% |
| dm_ex_us_equity | equity | 0.00% | 10.64% | 10.64% |
| em_equity | equity | 1.00% | 16.08% | 15.08% |
| kr_aggregate_bond | fixed_income | 0.00% | 4.86% | 4.86% |
| kr_treasury_10y | fixed_income | 0.00% | 1.53% | 1.53% |
| us_treasury_30y | fixed_income | 0.00% | 0.00% | 0.00% |
| us_high_yield | fixed_income | 0.00% | 10.89% | 10.89% |

## §4. Bucket Check (after projection)

- equity sum (dry-run): **82.72%**
- fixed_income sum (dry-run): **17.28%**
- max_abs_projection_drift: dry-run 2.04% vs baseline 0.00%

## §5. Top Changed Assets (by |Δ final|)

| # | asset | delta |
|---:|---|---:|
| 1 | us_growth_equity | -45.30% |
| 2 | em_equity | 15.08% |
| 3 | us_high_yield | 10.89% |
| 4 | dm_ex_us_equity | 10.64% |
| 5 | kr_equity | 8.76% |

## §6. Top Changed Products (by |Δ final_weight|)

| # | asset_key | product_name | manager | base | dry-run | delta |
|---:|---|---|---|---:|---:|---:|
| 1 | us_growth_equity | KB미국대표성장주자(주식)(UH)C-퇴직 | KB운용 | 30.00% | 10.75% | -19.25% |
| 2 | us_growth_equity | 삼성미국그로스자UH[주식-재간접]_Cp(퇴직연금) | 삼성운용 | 20.30% | 7.28% | -13.03% |
| 3 | us_growth_equity | AB미국그로스UH(주식-재간접)종류C-P2 | AB자산운용 | 20.30% | 7.28% | -13.03% |
| 4 | em_equity | NH-Amundi성장중소형주[주식]ClassC-P2(퇴직연금) | NH-Amundi운용 | 0.80% | 12.86% | 12.06% |
| 5 | kr_equity | 한국밸류10년투자파이오니아(주식)(C-Re) | 한국투자밸류운용 | 0.80% | 7.81% | 7.01% |
| 6 | us_value_equity | 한국투자미국배당귀족자UH(주식)(C-R) | 한국투자신탁운용 | 21.92% | 16.76% | -5.16% |
| 7 | em_equity | 마이다스아시아리더스성장주자(H)(주식)C-P2 | 마이다스운용 | 0.10% | 1.61% | 1.51% |
| 8 | em_equity | 마이다스아시아리더스성장주자(UH)(주식)C-P2 | 마이다스운용 | 0.10% | 1.61% | 1.51% |
| 9 | us_value_equity | 한국투자미국배당귀족자H(주식)(C-R) | 한국투자신탁운용 | 5.48% | 4.19% | -1.29% |
| 10 | kr_equity | NH-Amundi필승코리아[주식]ClassC-P2(퇴직연금) | NH-Amundi운용 | 0.10% | 0.98% | 0.88% |

> ⚠ **Limitation**: 아래 자산은 baseline weight ≈ 0 이지만 dry-run 에서 > 0 으로 잡혀 product allocation 비례 scaling 이 불가하다.

  - needs_selection_rerun_assets: ['dm_ex_us_equity', 'us_high_yield']

> baseline zero-weight assets cannot be reallocated by proportional scaling. Product allocation dry-run is a proportional scaling of baseline product weights by the ratio (dry_run_asset_weight / baseline_asset_weight). True re-selection (re-running universe + scoring + selection) is NOT performed here. Assets where baseline weight ≈ 0 but dry-run > 0 are listed under needs_selection_rerun_assets and require R-1G or full re-selection.

## §7. 운용역 검토 포인트

- ref_max_sharpe (baseline) → manager_override 로 변경 시 어떤 자산이 가장 크게 움직였는지 (§5 참조) 정성 view 와 정합한지 확인.
- bucket 합 (§4) 이 80/20 hard constraint 를 유지하는지 — projection 적용 후.
- product 비례 scaling 결과 (§6) 는 실제 selection 결과와 다를 수 있음. baseline weight ≈ 0 자산이 dry-run 에 등장하면 selection rerun 필수 (§6 Limitation).
- product-level manager review / implementation 전에 **R-1G full re-selection** 필수 (현재 valid_product_level_portfolio=false).
- production 반영은 본 R-1F.2 범위 밖. 별도 Phase F sign-off 필수.
