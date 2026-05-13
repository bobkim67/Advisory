# R-1H — Manager-Selected SAA Final Review Packet (2026-05-13)

> **Read-only review packet.** R-1A ~ R-1G.2 전체 R-track 산출물을 운용역 검토용
> 단일 문서로 묶음. **자동 final SAA 확정 / production 반영이 아니다.**
>
> `production_applied=false`, `dry_run_only=true`, `implementation_ready=false`,
> `sign_off_required_for_production=true`, Decision Register count = **14 (유지)**.
> production / baseline / config / E-series baseline 모두 무변경.

---

## §1. Executive Summary

| 단계 | 핵심 산출 | 결과 |
|:---:|---|---|
| **R-1A** | spec (opportunity set explorer) | 80:20 hard, candidate pool 패러다임 정의 |
| **R-1B / R-1B.2** | bucket-constrained Dirichlet 10,000 후보 + 2 reference | `r1b_lite.2`, 모든 후보 eq=80% / fi=20% hard |
| **R-1C** | scatter / 6 top-decile cloud / overlap-score 시각화 | overlap≥3: 773, ≥4: 71, ≥5: 1, =6: 0 |
| **R-1C.1** | sweet pool 71건 → 8 manager review shortlist | 5 dominant equity tilt 그룹 |
| **R-1D** | coordinate + weight similarity search | 8 shortlist 주변 후보 탐색 |
| **Final Manager Review Packet** | 8 후보 정량 비교 + decision worksheet | 운용역 review 입력 대기 |
| **R-1E** | manager-selected dry-run contract spec | 16 validation rules + `production_applied=false` 강제 |
| **R-1F.1** | manager selection validation + JSON dump | smoke `cand_008421` validation 16/16 pass |
| **R-1F.2** | downstream dry-run (TAA + projection asset-level + product proportional scaling) | asset-level valid, **product-level invalid** (sum 1.4448 / 0.7209) |
| **R-1F.2.1** | invalid 라벨링 + R-1G 권고 | `valid_product_level_portfolio=false` 명시 |
| **R-1G.0** | full product re-selection mini-spec | entrypoint 조사 + R-1G plan |
| **R-1G.1** | product re-selection (selection only) | ETF 0.997578 (cap clipping), Fund 1.000000 |
| **R-1G.2** | + PortfolioBuilder fallback + 3-way compare | **ETF/Fund 모두 sum=1.000000 / valid_product_level_portfolio=true** ✅ |

R-track 1차 기술 목적 달성. **그러나 본 packet 은 운용역 검토 / 거버넌스 sign-off 의
입력일 뿐, production 반영이 아니다.**

---

## §2. Decision Context

| 항목 | 값 |
|---|---|
| **선택 candidate** | `cand_008421` |
| 선택 방식 | manager-selected (R-1F.1 yaml input), **자동 추천 아님** |
| 입력 형태 | R-1F.1 smoke sample (`selected_by="r1f1_smoke_test"`, "not an automated recommendation" 명시) |
| ETF / Fund | **동일 candidate** (OD-2 default) |
| SAA 적용 방식 | **`manager_override_saa` 별도 layer** (OD-3 default). 기존 max-Sharpe SAA telemetry 보존. |
| Production 영향 | **0**. R-1F.* / R-1G.* 모두 별도 디렉토리 dump. |
| Decision Register count | **14 (유지)**. |
| operating_mode | `relaxed_diagnostic` |

> 본 review packet 의 cand_008421 채택은 **smoke sample** 이며 운용역의 실제 final
> 선택과 별개. 실 운용 결정 시 운용역은 R-1F.1 schema 로 직접 candidate / selected_by /
> selection_reason / sha256 입력 필요.

---

## §3. Candidate Summary (cand_008421)

### §3.1 Metric 요약

| metric | 값 |
|---|---:|
| expected_return | **10.97%** |
| volatility | **12.69%** |
| sharpe | **0.6277** |
| overlap_score | **5** (sweet pool 유일 special, R-1C overlap≥5) |
| concentration_hhi | 0.1635 |
| equity_intra_hhi | 0.2330 |
| fixed_income_intra_hhi | 0.3607 |
| max_asset_weight | 25.56% |
| equity_max_asset_weight | 25.56% (us_growth) |
| fixed_income_max_asset_weight | 10.14% (us_high_yield) |
| nonzero_asset_count | **9** |
| dominant equity tilt | `EQ_us_growth_equity` (Group A in R-1C.1) |

### §3.2 9-asset weights

| asset | weight |
|---|---:|
| kr_equity | 8.01% |
| **us_growth_equity** | **25.56%** ← dominant equity tilt |
| us_value_equity | 21.20% |
| dm_ex_us_equity | 10.89% |
| em_equity | 14.33% |
| kr_aggregate_bond | 5.11% |
| kr_treasury_10y | 3.79% |
| us_treasury_30y | 0.96% |
| **us_high_yield** | **10.14%** ← FI tilt, fixed_income_max |
| **sum** | **100.00%** (eq=80%, fi=20% hard) |

### §3.3 Reference 대비

| | cand_008421 | `ref_max_sharpe` (운용 불가) | `ref_80_20_equal_intra_bucket` |
|---|---:|---:|---:|
| Sharpe | **0.6277** | 0.7769 | 0.5389 |
| equity / FI | 80% / 20% | 100% / 0% | 80% / 20% |
| HHI | 0.1635 | 0.5934 | 0.1380 |
| max_w | 25.56% | 71.6% | 16.0% |
| nonzero | 9 | 2 | 9 |
| Sharpe vs ref_max_sharpe | **−0.1492 (−19.2%)** | — | −0.2380 |
| Sharpe vs ref_80_20_equal | **+0.0888 (+16.5%)** | +0.2380 | — |

해석: cand_008421 은 80:20 정책 만족 (운용 가능) + Sharpe ref_80_20_equal 대비 +0.09 개선.
단 us_growth_equity 25.56% / us_high_yield 10.14% 의 집중도는 별도 검토 필요.

---

## §4. 3-Way Comparison (baseline / R-1F.2 / R-1G.2)

| metric | **A. baseline (max-Sharpe)** | **B. R-1F.2 (proportional scaling)** | **C. R-1G.2 (full re-selection + builder)** |
|---|---:|---:|---:|
| operating_mode | relaxed_diagnostic | relaxed_diagnostic | relaxed_diagnostic |
| `production_applied` | false | false | **false** |
| `dry_run_only` | n/a (baseline) | true | **true** |
| `product_weight_sum` | 1.000000 | **ETF 1.4448 / Fund 0.7209** ✗ | **1.000000 (both)** ✅ |
| `valid_product_level_portfolio` | true (baseline) | **false** | **true (both)** ✅ |
| `n_products` | 17 | 17 | **26 (both)** |
| **`dm_ex_us_equity` picks** | **0** | scaling 불가 | **3 (both)** ✅ |
| **`us_high_yield` picks** | **0** | scaling 불가 | **ETF 2 / Fund 3** ✅ |
| `implementation_ready` | n/a | false | **false (strict)** |
| `implementation_review_status` | n/a | n/a | `"review_required"` |
| key limitation | corner solution (us_growth 71.6%) | proportional scaling 한계 → invalid | ETF us_high_yield universe 2건 한계 (cap) |

**핵심 메시지**: R-1G.2 가 R-1F.2 의 product-level invalid 를 해소했지만, **`valid_product_level_portfolio=true` 는 production 가능을 의미하지 않는다**. `implementation_ready=false / implementation_review_status="review_required"` 유지.

---

## §5. Asset-Level Change (baseline vs R-1G.2)

| asset | baseline final | R-1G.2 final | Δ | 해석 |
|---|---:|---:|---:|---|
| kr_equity | 1.00% | **9.76%** | **+8.76%p** | 국내 비중 증가 |
| **us_growth_equity** | **70.60%** | **25.30%** | **−45.30%p** | 미국 성장주 대폭 축소 (corner 해소) |
| us_value_equity | 27.40% | 20.95% | −6.45%p | 미국 가치주 소폭 축소 |
| **dm_ex_us_equity** ★ | 0.00% | **10.64%** | **+10.64%p** | **신규 편입** (선진국 ex-US) |
| **em_equity** | 1.00% | **16.08%** | **+15.08%p** | 신흥국 확대 |
| kr_aggregate_bond | 0.00% | 4.86% | +4.86%p | 신규 편입 (한국 종합채권) |
| kr_treasury_10y | 0.00% | 1.53% | +1.53%p | 신규 편입 (한국 10년물) |
| us_treasury_30y | 0.00% | 0.00% | 0.00%p | 미편입 유지 (target 0%) |
| **us_high_yield** ★ | 0.00% | **10.89%** | **+10.89%p** | **신규 편입** (HY) |

ETF/Fund 동일 (CMA·target 동일). bucket: baseline final equity 100% → R-1G.2 ~ 82.72% / fi ~ 17.28% (regime 1 TAA tilt 적용).

---

## §6. Product-Level Change

| | ETF baseline | ETF R-1G.2 | Fund baseline | Fund R-1G.2 |
|---|---:|---:|---:|---:|
| n_products | 17 | **26** (+9) | 17 | **26** (+9) |
| product_weight_sum | 1.000000 | **1.000000** ✅ | 1.000000 | **1.000000** ✅ |
| dm_ex_us_equity picks | 0 | **3** | 0 | **3** |
| us_high_yield picks | 0 | **2** (universe 2건 한계) | 0 | **3** |

### §6.1 자산군별 selected product count (R-1G.2)

| asset | ETF | Fund |
|---|:---:|:---:|
| kr_equity | 3 | 3 |
| us_growth_equity | 3 | 3 |
| us_value_equity | 3 | **2** (Fund universe 2건) |
| dm_ex_us_equity | **3 (신규)** | **3 (신규)** |
| em_equity | 3 | 3 |
| kr_aggregate_bond | **3 (신규)** | **3 (신규)** |
| kr_treasury_10y | **3 (신규)** | **3 (신규)** |
| us_treasury_30y | 3 (target 0% — universe 보유) | 3 |
| us_high_yield | **2 (신규, universe 2건 한계)** | **3 (신규)** |

### §6.2 Top changed assets (Δ |R-1G.2 − baseline|, top 5)

1. us_growth_equity: **−45.30%p**
2. em_equity: +15.08%p
3. us_high_yield: +10.89%p
4. dm_ex_us_equity: +10.64%p
5. kr_equity: +8.76%p

### §6.3 product-level limitation 해소 여부

| issue | R-1F.2 | **R-1G.2** |
|---|---|---|
| product_weight_sum ≈ 1.0 | ETF 1.4448 / Fund 0.7209 (**invalid**) | **1.000000 (valid)** ✅ |
| `needs_selection_rerun_assets` | `['dm_ex_us_equity', 'us_high_yield']` | **`[]`** ✅ |
| dm_ex_us_equity 편입 | scaling 불가 | **3 picks** ✅ |
| us_high_yield 편입 | scaling 불가 | **ETF 2 / Fund 3 picks** ✅ |

---

## §7. Remaining Warnings (운용역 검토 필수)

### §7.1 ETF us_high_yield universe 2건 한계 ⚠

- **사실**: ETF universe 의 `us_high_yield` 분류 product 가 **2건뿐**.
- **결과**: R-1G.2 ETF 가 core 1 + satellite 1 = 2 picks 로만 충당 (default core+satellite=3 미달).
- **영향**: us_high_yield 10.89% target 은 채워졌으나 **만약 한 상품 운용이 중단되거나 cap 충돌 시 대체 후보 부족**. Fund 측은 3 picks 로 여유 있음.
- **운용역 판단**: ETF us_high_yield universe 확장 필요 여부 — 운용 정책 / 유동성 / 추적 가능 여부 검토.

### §7.2 ETF shortfall PortfolioBuilder fallback 흡수 구조 ⚠

- **R-1G.1 ETF selected_weight_sum = 0.997578** (single_product/manager cap clipping 으로 0.24%p shortfall).
- **R-1G.2** 에서 `PortfolioBuilder.apply_fallback()` 가 잔여 0.24%p 를 **pro-rata / cash placeholder / bucket sibling 알고리즘으로 흡수** → product_weight_sum = 1.000000 도달.
- **운용역 판단**: cap 충돌로 인한 fallback 흡수 분량 (0.24%p) 의 운용 정합성 검토. `diagnostics.portfolio_builder.fallback` 에 상세 기록.

### §7.3 일반 경고 (영구)

- `implementation_ready = false` — 운용역 sign-off 전 자동 승격 금지.
- `valid_product_level_portfolio = true` 는 **portfolio 구조 정합성** 만 의미; 실제 운용 가능 여부와 다름.
- 운용역 sign-off 없이는 production 적용 절대 금지.

---

## §8. Manager Review Checklist (운용역 작성용)

| # | 검토 항목 | 운용역 판단 (체크) | 코멘트 |
|:---:|---|:---:|---|
| 1 | cand_008421 SAA 구조 수용 가능 여부 | ☐ Yes / ☐ No / ☐ Hold | |
| 2 | 미국 성장주 70.60% → 25.30% **−45.30%p 축소** 수용 가능 여부 | ☐ Yes / ☐ No / ☐ Hold | |
| 3 | 미국외 선진국 신규 편입 (dm_ex_us_equity 10.64%) 수용 가능 여부 | ☐ Yes / ☐ No / ☐ Hold | |
| 4 | 신흥국 확대 (em 1% → 16.08%) 수용 가능 여부 | ☐ Yes / ☐ No / ☐ Hold | |
| 5 | 한국 비중 확대 (kr 1% → 9.76%) 수용 가능 여부 | ☐ Yes / ☐ No / ☐ Hold | |
| 6 | us_high_yield 신규 편입 (10.89%) 수용 가능 여부 | ☐ Yes / ☐ No / ☐ Hold | |
| 7 | **ETF us_high_yield universe 2건 한계** 수용 가능 여부 | ☐ Yes / ☐ No / ☐ Hold | |
| 8 | product count 증가 (17 → 26) 수용 가능 여부 | ☐ Yes / ☐ No / ☐ Hold | |
| 9 | **PortfolioBuilder fallback 흡수 (ETF 0.24%p)** 처리 수용 가능 여부 | ☐ Yes / ☐ No / ☐ Hold | |
| 10 | max_asset_weight 25.56% (us_growth) 수용 가능 여부 | ☐ Yes / ☐ No / ☐ Hold | |
| 11 | 운용 정책 80:20 hard constraint 정합 확인 (자동 만족) | ☐ Yes / ☐ No / ☐ Hold | |
| 12 | **R-1G.2 결과를 Phase F production review 후보로 상정 여부** | ☐ Yes / ☐ No / ☐ Hold | |

작성 후 보관 위치는 운영 정책에 따름. Decision Register 에 신규 entry 가 필요한지는 OD-7 사용자 결정 사항 (현 default = R-1G.2 만으로는 미작성).

---

## §9. Implementation Boundary (안전장치)

| 단언 | 값 |
|---|:---:|
| `production_applied` | **false** |
| `dry_run_only` | **true** |
| `manager_override_saa_layer` | **true** (기존 max-Sharpe SAA telemetry 보존) |
| `valid_asset_level_dry_run` | true |
| `valid_product_level_portfolio` | true (ETF, Fund 모두) |
| `product_weight_sum_valid` | true (sum = 1.000000) |
| `implementation_ready` | **false (strict)** |
| `implementation_review_status` | `"review_required"` |
| `sign_off_required_for_production` | **true** |
| Decision Register count | **14 (유지)** |
| operating_mode | `relaxed_diagnostic` |
| 80:20 distance metric | 부활 없음 (R-1B.2 정합) |

**Production 승격 게이트 (OD-10 default, R-1G.2 범위 밖)**:

1. 운용역 명시 선택 + §8 checklist 작성
2. Decision Register 신규 entry (D-15 등) 신설
3. 별도 Phase F sign-off

위 3 단계 통과 전까지 R-1G.2 결과는 **dry-run 산출물로만 유효**.

---

## §10. Next Options

| 옵션 | 내용 | 후행 작업 |
|:---:|---|---|
| **A** | 운용역이 R-1G.2 결과를 검토하고 **보류** | §8 checklist 작성 후 보류 사유 명기. R-1F~R-1G 산출물은 historical record 로 보존. |
| **B** | **다른 candidate** 로 R-1F.1 → R-1F.2 → R-1G.1 → R-1G.2 재실행 | manager review shortlist 다른 7건 (cand_005995 / cand_009678 / cand_005991 / cand_000758 / cand_007510 / cand_004225 / cand_007699) 중 선택 → 동일 흐름. |
| **C** | cand_008421 R-1G.2 결과를 **Phase F production review 후보로 상정** | Decision Register D-15 신설 + 운용본부장 + 위험관리 sign-off 절차 진입 (OD-10). |

옵션 A/B/C 모두 본 R-track 산출물 변경 없이 진행 가능.

---

## §11. 본 작업의 변경 범위

| 영역 | 변경 |
|---|:---:|
| 본 review packet (1건) | ✓ 신규 |
| 코드 / config / tests | ✗ 무변경 |
| R-1A ~ R-1G.2 모든 산출물 | ✗ 무변경 (read-only synthesis) |
| portfolio JSON (`portfolio_{etf,fund}_20260511.json`) | ✗ 무변경 |
| `tdf_engine/config/*.yaml` | ✗ 무변경 |
| `docs/investment_decision_register.md` / count (14) | ✗ 무변경 |
| E-8 ~ E-12 산출물 | ✗ 무변경 |
| `tests/_phase_e62_baseline.json` sha | ✗ 무변경 |
| operating_mode | ✗ `relaxed_diagnostic` 유지 |
| 80:20 distance metric | ✗ 부활 없음 |
| 자동 final SAA 확정 / 자동 candidate 추천 | ✗ 금지 명시 |
| `implementation_ready` | ✗ false 강제 (auto-promote 없음) |

---

## §12. 한 줄 요약

> **R-1H 는 R-1A ~ R-1G.2 전체 산출물의 운용역 검토용 단일 packet.**
> cand_008421 (smoke) 의 dry-run 흐름이 max-Sharpe corner SAA 의 한계를 해소하여
> 80:20 만족 + 9-자산 분산 + product_weight_sum=1.000000 + valid_product_level_portfolio=true 까지 도달.
> 단 `implementation_ready=false` / `implementation_review_status="review_required"` 가 strict 유지되므로
> production 반영은 별도 Phase F sign-off 후. **R-track 기술 개발 1차 완료 — 이후는 운용역/거버넌스 판단 단계.**
