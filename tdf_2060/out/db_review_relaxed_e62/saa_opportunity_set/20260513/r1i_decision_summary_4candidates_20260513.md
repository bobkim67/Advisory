# R-1I — Manager Decision Summary (4 candidates, 1-page)

> Read-only synthesis. **자동 추천 없음.** R-1I multi-candidate comparison 결과 중
> 운용역 의사결정에 가장 도움이 될 4 후보의 1-page 요약.
> 모든 후보 `production_applied=false`, `dry_run_only=true`, `implementation_ready=false (strict)`.

**비교 reference**: `ref_max_sharpe` (Sh 0.7769, eq=100%, **운용 불가**) /
`ref_80_20_equal_intra_bucket` (Sh 0.5389, eq=80%/fi=20% 균등 anchor).

---

## §1. 4 후보 정량 비교

| | **cand_007317** | **cand_008421** | **cand_004225** | **cand_006926** |
|---|---:|---:|---:|---:|
| **tag** | highest ER + highest Sharpe (boundary) | sweet pool special (overlap=5) | low max_w / high diversification (sweet) | lowest volatility (boundary) |
| expected_return | **13.32%** | 10.97% | 10.70% | 8.97% |
| volatility | 14.16% | 12.69% | 13.62% | **11.35%** |
| **Sharpe** | **0.7287** | 0.6277 | 0.5653 | 0.5263 |
| concentration_hhi | 0.3562 | 0.1635 | **0.1462** | 0.2545 |
| equity_intra_hhi | 0.5142 | 0.2330 | 0.2107 | 0.3508 |
| fixed_income_intra_hhi | 0.6779 | 0.3607 | 0.2852 | 0.7499 |
| **max_asset_weight** | **54.84%** ⚠ | 25.56% | **19.57%** | 33.07% |
| mvo_efficiency_score (gap) | 0.0046 | 0.0142 | 0.0257 | 0.0211 |

---

## §2. 9-asset weights (모두 eq=80% / fi=20% hard)

| asset | bucket | cand_007317 | cand_008421 | cand_004225 | cand_006926 |
|---|---|---:|---:|---:|---:|
| kr_equity | eq | 8.59% | 8.01% | **19.57%** | 1.00% |
| us_growth_equity | eq | **54.84%** ⚠ | 25.56% | 18.47% | 5.99% |
| us_value_equity | eq | 14.39% | 21.20% | 16.22% | **33.07%** |
| dm_ex_us_equity | eq | 0.91% | 10.89% | 16.73% | 7.37% |
| em_equity | eq | 1.26% | 14.33% | 9.01% | **32.57%** |
| kr_aggregate_bond | fi | 0.83% | 5.11% | 6.20% | **17.22%** |
| kr_treasury_10y | fi | 2.49% | 3.79% | 4.25% | 1.18% |
| us_treasury_30y | fi | 0.43% | 0.96% | 2.33% | 1.35% |
| **us_high_yield** | fi | **16.25%** ⚠ | 10.14% | 7.22% | 0.25% |

### §2.1 핵심 tilt 요약

| tilt | cand_007317 | cand_008421 | cand_004225 | cand_006926 |
|---|---:|---:|---:|---:|
| **HY** (us_high_yield) | **16.25%** ⚠ | 10.14% | 7.22% | 0.25% |
| **EM** (em_equity) | 1.26% | 14.33% | 9.01% | **32.57%** ⚠ |
| **US growth** | **54.84%** ⚠ | 25.56% | 18.47% | 5.99% |
| kr_equity | 8.59% | 8.01% | 19.57% | 1.00% |
| dm_ex_us_equity | 0.91% | 10.89% | 16.73% | 7.37% |
| us_value_equity | 14.39% | 21.20% | 16.22% | **33.07%** ⚠ |

---

## §3. Product-level validity (R-1G.2 결과)

| | cand_007317 | cand_008421 | cand_004225 | cand_006926 |
|---|:---:|:---:|:---:|:---:|
| ETF product_weight_sum | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| Fund product_weight_sum | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| valid_product_level_portfolio (ETF/Fund) | true / true | true / true | true / true | true / true |
| n_products (ETF / Fund) | 26 / 26 | 26 / 26 | 23 / 23 | 23 / 23 |
| dm_ex_us picks (ETF / Fund) | 3 / 3 | 3 / 3 | 3 / 3 | 3 / 3 |
| us_high_yield picks (ETF / Fund) | 2 / 3 | 2 / 3 | 2 / 3 | 2 / 3 |
| **implementation_ready** | **false (strict)** | **false (strict)** | **false (strict)** | **false (strict)** |

> 모든 후보 product-level 정상. ETF `us_high_yield` 는 universe 2건 한계로 일관되게 2 picks.

---

## §4. Remaining Warnings (후보별 핵심 부담)

| 후보 | warning |
|---|---|
| **cand_007317** | **max_w 54.84% (us_growth) — 단일 자산 극단 집중**; HY 16.25% — credit cycle 후반부 부담; eq_intra_HHI 0.51 / fi_intra_HHI 0.68 — bucket 내부 분산 매우 약함; dm_ex_us 0.91% / em 1.26% — 선진국·신흥국 부재 |
| **cand_008421** | max_w 25.56% (us_growth) — 단일 자산 cap 근접; HY 10.14% — credit cycle view 검토 필요; fi_intra_HHI 0.36 — FI 측 HY 쏠림 |
| **cand_004225** | E[R] 10.70% / Sharpe 0.5653 — 4 후보 중 두 번째로 낮음; mvo_gap 0.0257 — frontier 와 거리 가장 큼; us_value 16.22% 만 — 미국 가치 비중 낮음 |
| **cand_006926** | **em 32.57% — 신흥국 over-tilt**; us_value 33.07% — 가치 집중; kr_equity 1.00% — 국내 부재; us_growth 5.99% — 성장 거의 부재; HY 0.25% — credit 미편입; **E[R] 8.97% — 4 후보 중 최저**, Sharpe 0.5263 도 최저 |

ETF us_high_yield universe 2건 한계 (모든 후보 공통).

---

## §5. 어떤 운용 view 에 적합한 후보인가

> "추천" 이 아니라 **view-fit mapping** — 운용역이 정성 view 결정 후 본 표에서 매칭.

| 운용 view | 가장 정합 후보 | 근거 |
|---|---|---|
| **성과 효율 최우선** (Sharpe / E[R]) | **cand_007317** | Sh 0.7287 (4 후보 중 최고), E[R] 13.32% (최고). ref_max_sharpe (Sh 0.7769) 대비 −0.05 Sharpe 만 양보하면서 80:20 정책 만족. |
| 균형 (성과 + 분산) | **cand_008421** | Sh 0.6277 + HHI 0.1635 + 9 자산 모두 5%+. sweet pool 유일 overlap=5. |
| **분산성 최우선** (concentration ↓) | **cand_004225** | max_w 19.57% (4 후보 중 최저), HHI 0.1462 (최저). 한국 + 선진국 ex-US balanced. Sharpe 일부 양보. |
| **변동성 안정성 최우선** | **cand_006926** | σ 11.35% (4 후보 중 최저). 단 신흥국 + us_value 집중으로 분산은 약함. |
| **us_growth 강세 view + HY 적극** | **cand_007317** | us_growth 54.84% + HY 16.25% 가 view 와 일치 시 자연 선택지. |
| **신흥국 + 채권 안정 view** | **cand_006926** | em 32.57% + kr_aggregate_bond 17.22% — 신흥국 risk-on + 채권 buffer 조합. |
| **국내 + 선진국 ex-US view** | **cand_004225** | kr 19.57% + dm_ex_us 16.73% — 미국 의존도 낮춤. |
| **credit / HY 부담 회피** | **cand_006926** | HY 0.25% (사실상 없음). 단 신흥국 32.57% 부담 동시. |
| **신흥국 부담 회피** | **cand_007317** | em 1.26% — 신흥국 사실상 없음. 단 us_growth 54.84% 부담 동시. |
| **목표 E[R] 12%+ 추구** | **cand_007317** (유일) | 나머지 3 후보 E[R] ≤ 10.97%. 단 단일 자산 54.84% 위험 인지 필요. |

---

## §6. 운용역 선택 질문 (체크리스트)

본 packet 은 어느 후보도 추천하지 않는다. 운용역이 다음 질문을 통해 직접 결정:

1. **성과 효율 우선** — Sharpe / E[R] 을 가장 중요시할 것인가?
   - **Yes** → cand_007317 검토 (단 max_w 54.84% / HY 16.25% 수용 가능 여부 확인 필수)
   - **No** → 다음 질문으로

2. **분산성 우선** — 단일 자산 집중도 / HHI 최소화를 가장 중요시할 것인가?
   - **Yes** → cand_004225 검토 (Sharpe 0.5653 으로 cand_007317 대비 −0.16 양보 수용 여부)
   - **No** → 다음 질문으로

3. **변동성 안정성 우선** — σ 최소화를 가장 중요시할 것인가?
   - **Yes** → cand_006926 검토 (E[R] 8.97% 로 cand_007317 대비 −4.35%p 양보 수용 여부)
   - **No** → 다음 질문으로

4. **HY (us_high_yield) 편입 부담** — 어느 수준까지 허용?
   - **15%+ 허용** → cand_007317 가능
   - **10% 내외 허용** → cand_008421 가능
   - **5~7% 까지만** → cand_004225 가능
   - **거의 0% 만 허용** → cand_006926 가능 (단 신흥국 부담 동시)

5. **EM (신흥국) 편입 부담** — 어느 수준까지 허용?
   - **30%+ 허용** → cand_006926 가능
   - **15% 내외 허용** → cand_008421 가능
   - **10% 미만** → cand_004225 가능
   - **거의 0%** → cand_007317 가능 (단 us_growth 집중 동시)

6. **Phase F production review 후보 수** — 1개로 좁힐 것인가, 2~3개를 병렬로 올릴 것인가?
   - **1개로 좁힘** → 위 1~5 답변 종합하여 단일 후보 선택 + Decision Register 신규 entry 1건
   - **2~3개 병렬** → 운용본부장 + 위험관리 양방향 review 진행. 각 후보별 Phase F gate 개별 통과 필요. governance 부담 증가.

---

## §7. Implementation Boundary (재확인)

| 단언 | 값 |
|---|:---:|
| 자동 final SAA 확정 / 자동 candidate 추천 | **금지** |
| `production_applied` (4 후보 모두) | **false** |
| `dry_run_only` | **true** |
| `implementation_ready` | **false (strict)** |
| `implementation_review_status` | `"review_required"` |
| Decision Register count | **14 (유지)** |
| `operating_mode` | `relaxed_diagnostic` |
| 80:20 distance metric | 부활 없음 |

Phase F 진입 = (운용역 명시 sign-off) + (Decision Register 신규 entry) + (별도 Phase F gate) 3단계 통과 후. 본 1-page summary 는 그 결정을 위한 **정성 input 자료**일 뿐 production 신호가 아니다.

---

## §8. 한 줄 요약

> **4 후보 모두 product-level valid R-1G.2 dry-run 도달, 모두 `implementation_ready=false (strict)`.**
> 선택은 운용역의 정성 우선순위 (Sharpe / 분산 / σ / HY 부담 / EM 부담) 에 달려있음.
> cand_007317 = Sharpe 1위 + max_w 54.84% 부담 / cand_008421 = 균형 + HY 10% / cand_004225 = 분산 1위 + Sharpe 양보 / cand_006926 = σ 1위 + EM 32.57% 부담.
> **자동 추천 없음. 운용역이 §6 6 질문 답변 후 1개 또는 2~3개 후보를 Phase F gate 로 상정 결정.**
