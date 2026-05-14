# R-1I — Multi-candidate Dry-run Comparison (2026-05-13)

> schema_version: r1i.1
> Read-only batch. `production_applied=false`, `dry_run_only=true`, `implementation_ready=false` (all candidates).
> 자동 final SAA 확정 / 자동 candidate 추천 없음. 본 packet 은 운용역이 final SAA 후보를 선택할 수 있도록 multi-candidate dry-run 결과를 비교한다.

## §1. Executive Summary

- R-1I 목적: scatter / shortlist 에서 **여러 후보** 를 선택해 각 후보별 R-1F.1 validation + R-1G.2 dry-run 을 반복하고, 그 결과를 비교표로 제공.
- cand_008421 은 **최종안이 아니라 비교 후보 중 하나** (R-1H smoke / manager-selected sample input).
- 비교 후보군: **sweet_spot_5** + **boundary 4** (deduplicate 후 unique sampled = 8건) + reference (ref_80_20_equal_intra_bucket, ref_max_sharpe).
- production 반영 아님. 모든 후보에서 `production_applied=false`, `implementation_ready=false (strict)` 유지.
- review_packet ref: `out\db_review_relaxed_e62\saa_opportunity_set\20260513\r1h_manager_selected_saa_final_review_20260513.md` (sha256 83fd8397828cae40…)

## §2. Candidate Universe

| candidate_id | tags | E[R] | σ | Sharpe | HHI | eq_iHHI | fi_iHHI | max_w | eq | fi | feasibility |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| cand_008421 | sweet_spot:highest Sharpe / special overlap | 10.97% | 12.69% | 0.6277 | 0.1635 | 0.2330 | 0.3607 | 25.56% | 80.00% | 20.00% | feasible |
| cand_004225 | sweet_spot:low max weight / high diversification | 10.70% | 13.62% | 0.5653 | 0.1462 | 0.2107 | 0.2852 | 19.57% | 80.00% | 20.00% | feasible |
| cand_007510 | sweet_spot:low volatility | 9.91% | 12.08% | 0.5724 | 0.1644 | 0.2400 | 0.2702 | 23.35% | 80.00% | 20.00% | feasible |
| cand_009678 | sweet_spot:us_value tilt | 10.82% | 13.21% | 0.5918 | 0.1541 | 0.2244 | 0.2627 | 23.64% | 80.00% | 20.00% | feasible |
| cand_000758 | sweet_spot:balanced | 10.71% | 13.31% | 0.5794 | 0.1546 | 0.2235 | 0.2882 | 22.98% | 80.00% | 20.00% | feasible |
| cand_007317 | boundary:highest_expected_return, boundary:highest_sharpe | 13.32% | 14.16% | 0.7287 | 0.3562 | 0.5142 | 0.6779 | 54.84% | 80.00% | 20.00% | feasible |
| cand_006926 | boundary:lowest_volatility | 8.97% | 11.35% | 0.5263 | 0.2545 | 0.3508 | 0.7499 | 33.07% | 80.00% | 20.00% | feasible |
| cand_006604 | boundary:lowest_concentration_hhi | 10.48% | 13.33% | 0.5611 | 0.1418 | 0.2003 | 0.3387 | 16.93% | 80.00% | 20.00% | feasible |
| ref_80_20_equal_intra_bucket (reference, dry-run 제외) | reference | 10.12% | 13.20% | 0.5389 | 0.1380 | 0.2000 | 0.2500 | 16.00% | 80.00% | 20.00% | feasible |
| ref_max_sharpe (reference, dry-run 제외) | reference | 15.40% | 15.96% | 0.7769 | 0.5934 | 0.5934 | n/a | 71.60% | 100.00% | 0.00% | feasible |

## §3. Risk-Return Positioning (sweet_spot_5)

- expected_return range: **9.91% ~ 10.97%** (spread 1.06%)
- volatility range: **12.08% ~ 13.62%** (spread 1.54%)
- Sharpe range: **0.5653 ~ 0.6277** (spread 0.0625)

**해석**: sweet_spot_5 후보들은 **서로 다른 risk-return 후보가 아니라** 비슷한 risk-return 영역 내에서 자산배분 성격이 다른 후보군이다. 따라서 비교의 목적은 'return / σ 차이' 가 아니라 **'유사한 risk-return 내에서 어떤 allocation-style 을 택할 것인가'**.

## §4. Asset Allocation Comparison

| candidate_id | kr_equity | us_growth_equity | us_value_equity | dm_ex_us_equity | em_equity | kr_aggregate_bond | kr_treasury_10y | us_treasury_30y | us_high_yield | dom_eq_tilt | HY | EM | us_growth | max_w |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cand_008421 | 8.01% | 25.56% | 21.20% | 10.89% | 14.33% | 5.11% | 3.79% | 0.96% | 10.14% | us_growth_equity | 10.14% | 14.33% | 25.56% | 25.56% |
| cand_004225 | 19.57% | 18.47% | 16.22% | 16.73% | 9.01% | 6.20% | 4.25% | 2.33% | 7.22% | kr_equity | 7.22% | 9.01% | 18.47% | 19.57% |
| cand_007510 | 3.20% | 20.79% | 19.06% | 23.35% | 13.60% | 6.75% | 5.83% | 4.42% | 3.00% | dm_ex_us_equity | 3.00% | 13.60% | 20.79% | 23.35% |
| cand_009678 | 15.63% | 20.82% | 23.64% | 10.72% | 9.19% | 3.86% | 5.57% | 4.01% | 6.57% | us_value_equity | 6.57% | 9.19% | 20.82% | 23.64% |
| cand_000758 | 16.35% | 22.98% | 18.21% | 16.28% | 6.18% | 3.71% | 8.34% | 4.40% | 3.55% | us_growth_equity | 3.55% | 6.18% | 22.98% | 22.98% |
| cand_007317 | 8.59% | 54.84% | 14.39% | 0.91% | 1.26% | 0.83% | 2.49% | 0.43% | 16.25% | us_growth_equity | 16.25% | 1.26% | 54.84% | 54.84% |
| cand_006926 | 1.00% | 5.99% | 33.07% | 7.37% | 32.57% | 17.22% | 1.18% | 1.35% | 0.25% | us_value_equity | 0.25% | 32.57% | 5.99% | 33.07% |
| cand_006604 | 15.66% | 16.93% | 16.59% | 15.50% | 15.32% | 2.52% | 4.35% | 3.10% | 10.03% | us_growth_equity | 10.03% | 15.32% | 16.93% | 16.93% |

## §5. Product-Level Dry-Run Comparison (R-1G.2 results)

| candidate_id | ETF sum | ETF valid | ETF n | ETF dm_ex_us | ETF hy | Fund sum | Fund valid | Fund n | Fund dm_ex_us | Fund hy | impl_ready |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cand_008421 | 1.000000 | true | 26 | 3 | 2 | 1.000000 | true | 26 | 3 | 3 | false (strict) |
| cand_004225 | 1.000000 | true | 23 | 3 | 2 | 1.000000 | true | 23 | 3 | 3 | false (strict) |
| cand_007510 | 1.000000 | true | 26 | 3 | 2 | 1.000000 | true | 26 | 3 | 3 | false (strict) |
| cand_009678 | 1.000000 | true | 26 | 3 | 2 | 1.000000 | true | 26 | 3 | 3 | false (strict) |
| cand_000758 | 1.000000 | true | 26 | 3 | 2 | 1.000000 | true | 26 | 3 | 3 | false (strict) |
| cand_007317 | 1.000000 | true | 26 | 3 | 2 | 1.000000 | true | 26 | 3 | 3 | false (strict) |
| cand_006926 | 1.000000 | true | 23 | 3 | 2 | 1.000000 | true | 23 | 3 | 3 | false (strict) |
| cand_006604 | 1.000000 | true | 26 | 3 | 2 | 1.000000 | true | 26 | 3 | 3 | false (strict) |

> **모든 후보에서 `implementation_ready=false (strict)` 유지** — `valid_product_level_portfolio=true` 가 production 가능을 의미하지 않음.

## §6. Key Trade-off Matrix (review order, **추천 아님**)

| review priority | review order |
|---|---|
| Sharpe 우선 | cand_007317 → cand_008421 → cand_009678 → cand_000758 → cand_007510 → cand_004225 → cand_006604 → cand_006926 |
| σ 낮은 후보 우선 | cand_006926 → cand_007510 → cand_008421 → cand_009678 → cand_000758 → cand_006604 → cand_004225 → cand_007317 |
| max_asset_weight 낮은 후보 우선 | cand_006604 → cand_004225 → cand_000758 → cand_007510 → cand_009678 → cand_008421 → cand_006926 → cand_007317 |
| HHI 낮은 후보 우선 | cand_006604 → cand_004225 → cand_009678 → cand_000758 → cand_008421 → cand_007510 → cand_006926 → cand_007317 |
| HY (us_high_yield) 낮은 후보 우선 | cand_006926 → cand_007510 → cand_000758 → cand_009678 → cand_004225 → cand_006604 → cand_008421 → cand_007317 |
| EM (em_equity) 낮은 후보 우선 | cand_007317 → cand_000758 → cand_004225 → cand_009678 → cand_007510 → cand_008421 → cand_006604 → cand_006926 |
| us_growth_equity 쏠림 낮은 후보 우선 | cand_006926 → cand_006604 → cand_004225 → cand_007510 → cand_009678 → cand_000758 → cand_008421 → cand_007317 |
| kr_equity (국내) 비중 높은 후보 우선 | cand_004225 → cand_000758 → cand_006604 → cand_009678 → cand_007317 → cand_008421 → cand_007510 → cand_006926 |

## §7. Candidate-by-Candidate Notes

### cand_008421

- tags: ['sweet_spot:highest Sharpe / special overlap']
- 특징: Sharpe=0.6277, E[R]=10.97%, σ=12.69%, HHI=0.1635, max_w=25.56%. Dominant equity tilt: **us_growth_equity**.
- 장점: Sharpe 상위권
- 부담 요인: us_high_yield 10.14% — credit cycle 부담 가능, us_growth_equity 25.56% — equity 집중, max_w 25.56% — 단일 자산 cap 근접
- 상품단 warning:
  - ETF us_high_yield universe 한계: picks=2 (universe 2건). 대체 후보 부족.
- 운용역 판단 질문:
  - us_growth_equity 25.56% tilt 가 운용 view 와 정합한가?
  - us_high_yield 10.14% tilt 가 credit cycle view 와 정합한가?

### cand_004225

- tags: ['sweet_spot:low max weight / high diversification']
- 특징: Sharpe=0.5653, E[R]=10.70%, σ=13.62%, HHI=0.1462, max_w=19.57%. Dominant equity tilt: **kr_equity**.
- 장점: max_w 19.57% — 집중도 낮음, HHI 0.1462 — 분산 우수
- 상품단 warning:
  - ETF us_high_yield universe 한계: picks=2 (universe 2건). 대체 후보 부족.
- 운용역 판단 질문:
  - us_high_yield 7.22% tilt 가 credit cycle view 와 정합한가?
  - kr_equity 19.57% 국내 tilt 가 view 와 정합한가?

### cand_007510

- tags: ['sweet_spot:low volatility']
- 특징: Sharpe=0.5724, E[R]=9.91%, σ=12.08%, HHI=0.1644, max_w=23.35%. Dominant equity tilt: **dm_ex_us_equity**.
- 장점: σ 12.08% — 변동성 낮음
- 운용역 판단 질문:
  - us_growth_equity 20.79% tilt 가 운용 view 와 정합한가?

### cand_009678

- tags: ['sweet_spot:us_value tilt']
- 특징: Sharpe=0.5918, E[R]=10.82%, σ=13.21%, HHI=0.1541, max_w=23.64%. Dominant equity tilt: **us_value_equity**.
- 상품단 warning:
  - ETF us_high_yield universe 한계: picks=2 (universe 2건). 대체 후보 부족.
- 운용역 판단 질문:
  - us_growth_equity 20.82% tilt 가 운용 view 와 정합한가?
  - us_high_yield 6.57% tilt 가 credit cycle view 와 정합한가?

### cand_000758

- tags: ['sweet_spot:balanced']
- 특징: Sharpe=0.5794, E[R]=10.71%, σ=13.31%, HHI=0.1546, max_w=22.98%. Dominant equity tilt: **us_growth_equity**.
- 운용역 판단 질문:
  - us_growth_equity 22.98% tilt 가 운용 view 와 정합한가?

### cand_007317

- tags: ['boundary:highest_expected_return', 'boundary:highest_sharpe']
- 특징: Sharpe=0.7287, E[R]=13.32%, σ=14.16%, HHI=0.3562, max_w=54.84%. Dominant equity tilt: **us_growth_equity**.
- 장점: Sharpe 상위권
- 부담 요인: us_high_yield 16.25% — credit cycle 부담 가능, us_growth_equity 54.84% — equity 집중, max_w 54.84% — 단일 자산 cap 근접
- 상품단 warning:
  - ETF us_high_yield universe 한계: picks=2 (universe 2건). 대체 후보 부족.
- 운용역 판단 질문:
  - us_growth_equity 54.84% tilt 가 운용 view 와 정합한가?
  - us_high_yield 16.25% tilt 가 credit cycle view 와 정합한가?

### cand_006926

- tags: ['boundary:lowest_volatility']
- 특징: Sharpe=0.5263, E[R]=8.97%, σ=11.35%, HHI=0.2545, max_w=33.07%. Dominant equity tilt: **us_value_equity**.
- 장점: σ 11.35% — 변동성 낮음
- 부담 요인: max_w 33.07% — 단일 자산 cap 근접, em_equity 32.57% — 신흥국 over-tilt
- 운용역 판단 질문:
  - em_equity 32.57% 신흥국 tilt 가 view 와 정합한가?

### cand_006604

- tags: ['boundary:lowest_concentration_hhi']
- 특징: Sharpe=0.5611, E[R]=10.48%, σ=13.33%, HHI=0.1418, max_w=16.93%. Dominant equity tilt: **us_growth_equity**.
- 장점: max_w 16.93% — 집중도 낮음, HHI 0.1418 — 분산 우수
- 부담 요인: us_high_yield 10.03% — credit cycle 부담 가능
- 상품단 warning:
  - ETF us_high_yield universe 한계: picks=2 (universe 2건). 대체 후보 부족.
- 운용역 판단 질문:
  - us_high_yield 10.03% tilt 가 credit cycle view 와 정합한가?
  - em_equity 15.32% 신흥국 tilt 가 view 와 정합한가?

## §8. Manager Decision Worksheet (운용역 작성용)

| candidate_id | manager_view | return_profile_fit | risk_profile_fit | equity_tilt_fit | FI_tilt_fit | HY_comfort | EM_comfort | concentration_comfort | product_implementation_comfort | include_in_final_saa_review | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cand_008421 |  |  |  |  |  |  |  |  |  |  |  |
| cand_004225 |  |  |  |  |  |  |  |  |  |  |  |
| cand_007510 |  |  |  |  |  |  |  |  |  |  |  |
| cand_009678 |  |  |  |  |  |  |  |  |  |  |  |
| cand_000758 |  |  |  |  |  |  |  |  |  |  |  |
| cand_007317 |  |  |  |  |  |  |  |  |  |  |  |
| cand_006926 |  |  |  |  |  |  |  |  |  |  |  |
| cand_006604 |  |  |  |  |  |  |  |  |  |  |  |

작성 가이드: `manager_view` ∈ {positive, neutral, negative, hold}; `include_in_final_saa_review` ∈ {yes, no}. 본 worksheet 는 운용역의 정성 판단을 위한 빈 필드이며, **자동 채움 없음**.

## §9. Next Options

| 옵션 | 내용 |
|:---:|---|
| **A** | 후보군 중 1개를 final SAA review candidate 로 지정 (운용역 명시 sign-off + Decision Register 신규 entry + Phase F gate 필요) |
| **B** | 특정 후보 주변에서 R-1D weight similarity search 로 추가 후보 발굴 |
| **C** | target_return advisory line 을 추가하여 재필터링 (advisory only, 자동 탈락 없음) |
| **D** | Phase F production review 는 아직 **보류** |

## §10. 본 작업의 변경 범위

| 영역 | 변경 |
|---|:---:|
| 본 multi-candidate comparison packet (1건) | ✓ 신규 |
| candidate 별 R-1F.1 / R-1F.2 / R-1G.2 산출 (별도 dir) | ✓ 신규 |
| 기존 R-1G.2 cand_008421 산출물 | ✗ 무변경 (별도 디렉토리 사용) |
| R-1A ~ R-1H 산출물 | ✗ 무변경 |
| 코드 / config / tests | ✗ 무변경 |
| Decision Register count (14) | ✗ 무변경 |
| E-series baseline | ✗ 무변경 |
| `tests/_phase_e62_baseline.json` sha | ✗ 무변경 |
| operating_mode | ✗ `relaxed_diagnostic` 유지 |
| 80:20 distance metric | ✗ 부활 없음 |
| 자동 final SAA 확정 / 자동 candidate 추천 | ✗ 금지 |
| `implementation_ready` | ✗ 모든 후보에서 false strict |
