# SAA Opportunity Set — Sweet Pool Review (R-1C.1, 2026-05-13)

> R-1C cloud / overlap visualization 산출물 (`saa_opportunity_set_cloud_review_20260513.md`,
> `*_overlap_score_*.png`) 에서 식별된 **overlap_score ≥ 4 후보 71건** 을 운용역 검토용
> shortlist 후보군으로 정리하는 read-only 분석. SAA / TAA / product selection / config /
> Decision Register / E-series baseline 모두 미변경.
>
> **source**: R-1B.2 bucket-constrained opportunity set JSON (`r1b_lite.2` schema).
> 80:20 은 hard constraint — 모든 후보가 equity 80% / fixed_income 20% 만족.
>
> **ETF / Fund 동등성**: 두 산출물의 CMA (μ, Σ, ρ) / `saa_diagnostics.saa_weights` /
> bucket_map / seed (=42) / n (=10000) 가 모두 동일하므로 sweet pool, 통계, 그룹,
> shortlist 모두 **bit-identical**. 이하 본문은 ETF 기준으로 기술하며 Fund 결과는 동일.

---

## §1. Sweet Pool 정의

| 항목 | 값 |
|---|---|
| Source candidates | 10,000 (sampled, bucket-constrained) + 2 references |
| Filter (1) | `overlap_score >= 4` (= R-1C 6 metric 중 4개 이상의 top decile) |
| Filter (2) | `feasibility_status == "feasible"` |
| **Sweet pool size** | **71** |
| 그 중 special (overlap_score ≥ 5) | **1** (cand_008421) |
| overlap_score = 6 (perfect) | **0** |

R-1C decile thresholds (sweet pool 진입 cut, 재확인):

| metric | direction | threshold |
|---|---|---:|
| `sharpe` | top 10% | **≥ 0.6270** |
| `mvo_efficiency_score` | bottom 10% | **≤ 0.0147** |
| `concentration_hhi` | bottom 10% | **≤ 0.1717** |
| `equity_intra_hhi` | bottom 10% | **≤ 0.2435** |
| `fixed_income_intra_hhi` | bottom 10% | **≤ 0.2888** |
| `max_asset_weight` | bottom 10% | **≤ 25.66%** |

**관찰**: sweet pool 71건은 분산 4개 metric (full HHI, equity intra HHI, fixed_income intra
HHI, max_asset_weight) 의 **우수 후보 (각 top decile)** 가 거의 동시에 포함된 영역이며,
return 2개 metric (sharpe, mvo_efficiency_score) 의 우수 후보 (sharpe top 10% / mvo gap
bottom 10%) 와 겹치는 영역은 매우 좁다 — sweet pool 의 본질은 **"분산 우수 후보와 성과/효율
우수 후보가 겹치는 좁은 교집합"**. 유일한 special 후보 (cand_008421) 만 분산 4 metric +
return 1 metric (`sharpe`) 의 5-way 우수 겹침.

---

## §2. Sweet Pool 요약 통계 (71건)

| metric | min | p25 | median | p75 | max | mean |
|---|---:|---:|---:|---:|---:|---:|
| expected_return | 9.04% | 9.76% | 10.19% | 10.44% | **10.97%** | 10.09% |
| volatility | 12.08% | 12.95% | 13.32% | 13.63% | 14.26% | 13.27% |
| **sharpe** | 0.4682 | 0.5053 | 0.5365 | 0.5629 | **0.6277** | 0.5348 |
| mvo_efficiency_score | 0.0142 | 0.0243 | 0.0292 | 0.0333 | 0.0390 | 0.0284 |
| concentration_hhi | 0.1441 | 0.1529 | 0.1578 | 0.1627 | 0.1662 | 0.1572 |
| equity_intra_hhi | 0.2078 | 0.2217 | 0.2299 | 0.2371 | 0.2423 | 0.2283 |
| fixed_income_intra_hhi | 0.2532 | 0.2689 | 0.2780 | 0.2838 | 0.3607 | 0.2765 |
| max_asset_weight | 19.04% | 21.93% | 23.21% | 24.00% | 25.59% | 22.95% |
| equity_max_asset_weight | 19.04% | 21.93% | 23.21% | 24.00% | 25.59% | 22.95% |
| fixed_income_max_asset_weight | 5.42% | 6.65% | 7.20% | 7.69% | 10.14% | 7.17% |

**핵심 관찰**:
- max_asset_weight 와 equity_max_asset_weight 가 동일 — 모든 sweet pool 후보의
  최대 비중 자산은 equity 자산 (FI 자산은 bucket=0.20 이라 단일 자산 ≤ 0.20).
- 후보 간 σ / Sharpe 변동성 작음 (Sharpe IQR = 0.51~0.56, 5%p 폭).
- ref_80_20_equal_intra_bucket (Sharpe **0.5389**, mvo_gap 0.0276) 는 sweet pool
  median (Sharpe 0.5365, mvo 0.0292) 와 거의 일치 — equal_intra 자체가 sweet pool
  의 중심에 위치.

---

## §3. 자산별 weight 분포 (sweet pool 71건)

| asset | bucket | min | p25 | median | p75 | max | mean | ref_80_20 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| kr_equity | equity | 2.49% | 13.14% | 17.20% | 20.03% | 25.17% | 16.11% | 16.00% |
| us_growth_equity | equity | 2.18% | 10.14% | 18.05% | 20.70% | 25.59% | 15.46% | 16.00% |
| us_value_equity | equity | 2.96% | 13.25% | 18.34% | 21.20% | 25.01% | 16.67% | 16.00% |
| dm_ex_us_equity | equity | 2.77% | 12.76% | 16.73% | 21.42% | 25.55% | 16.46% | 16.00% |
| em_equity | equity | 2.59% | 9.97% | 16.35% | 20.53% | 24.27% | 15.30% | 16.00% |
| kr_aggregate_bond | FI | 1.95% | 3.49% | 4.96% | 6.40% | 7.91% | 5.04% | 5.00% |
| kr_treasury_10y | FI | 1.95% | 3.79% | 4.72% | 5.81% | 8.34% | 4.83% | 5.00% |
| us_treasury_30y | FI | 0.96% | 4.29% | 5.13% | 6.43% | 8.03% | 5.27% | 5.00% |
| us_high_yield | FI | 2.39% | 3.43% | 4.49% | 6.08% | 10.14% | 4.87% | 5.00% |

**관찰**:
- sweet pool 평균은 9개 자산 모두 ref_80_20 (각 equity 16% / FI 5%) 와 **0.7%p 이내 근사**.
  decile 기준 (diversification top 10%) 이 ref_80_20 균등 anchor 주변을 정확히 포착.
- 후보 간 변동은 equity 측 더 큼 (각 자산 IQR 약 7~10%p) vs FI 측 좁음 (IQR 2~3%p).
- 어떤 자산도 25.66% 를 넘지 않음 (max_w decile filter 효과).

---

## §4. 후보군 분류 (Dominant Equity Tilt 5 그룹)

분류 기준: candidate 의 **equity bucket 내부 최대 비중 자산**.
sweet pool 후보들이 모두 `sharpe` & `mvo` flag = False 로 구성되어 (sharpe, mvo) 축
분류가 의미를 잃었기 때문에, 운용역 정성 결정의 핵심인 **"어느 equity asset 에 가장
tilt 되었는가"** 로 분류. tie 는 asset_keys 순서 (kr → us_growth → us_value →
dm_ex_us → em).

| group | dominant asset | count | share |
|---|---|---:|---:|
| `EQ_us_value_equity` | us_value_equity 최대 | **20** | 28% |
| `EQ_dm_ex_us_equity` | dm_ex_us_equity 최대 | **17** | 24% |
| `EQ_us_growth_equity` | us_growth_equity 최대 | **13** | 18% |
| `EQ_em_equity` | em_equity 최대 | **11** | 16% |
| `EQ_kr_equity` | kr_equity 최대 | **10** | 14% |

5 그룹 모두 비어있지 않고 균형 잡힘. us_value tilt 가 가장 많고 kr_equity tilt 가
가장 적음.

### §4.1 각 그룹 대표 후보 (Top 1)

선정 기준: `overlap_score desc → feasibility 우선 → sharpe desc → concentration_hhi asc →
equity_intra_hhi asc → fixed_income_intra_hhi asc → candidate_id asc` (R-1C sweet spot
ranking 과 동일).

| group | candidate_id | overlap | Sharpe | E[R] | σ | HHI | max_w |
|---|---|:---:|---:|---:|---:|---:|---:|
| `EQ_us_growth_equity` | **cand_008421** | **5** | **0.6277** | 10.97% | 12.69% | 0.1635 | 25.6% |
| `EQ_us_value_equity` | cand_009678 | 4 | 0.5918 | 10.82% | 13.21% | 0.1541 | 23.6% |
| `EQ_dm_ex_us_equity` | cand_007510 | 4 | 0.5724 | 9.91% | 12.08% | 0.1644 | 23.3% |
| `EQ_kr_equity` | cand_004225 | 4 | 0.5653 | 10.70% | 13.62% | 0.1462 | 19.6% |
| `EQ_em_equity` | cand_007699 | 4 | 0.5507 | 9.77% | 12.30% | 0.1632 | 23.0% |

`cand_008421` (us_growth tilt) 는 sweet pool 의 유일한 overlap=5 후보이며, sweet pool
내 max Sharpe (0.6277). 단 max_w 25.6% 로 분산 측면에서는 다른 그룹 대표보다 약함.

---

## §5. Manager Review Shortlist (8 candidates)

> **자동 선택 아님.** 본 표는 운용역의 정성 view (자산별 outlook / 정책 / regime
> tilt) 를 반영해 final SAA 를 결정하기 위한 **review shortlist** 다.

선정: 5 그룹 대표 × 1건 + 잔여 자리는 ranking 상위 (us_growth tilt 가 강한 후보들이
잔여 자리를 차지). 정렬은 sweet spot ranking (overlap → sharpe → HHI → id).

| # | candidate_id | group | overlap | E[R] | σ | Sharpe | mvo_gap | HHI | eq_iHHI | fi_iHHI | max_w |
|---:|---|---|:---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **cand_008421** | EQ_us_growth | **5** | 10.97% | 12.69% | **0.6277** | 0.0142 | 0.1635 | 0.2330 | 0.3607 | 25.6% |
| 2 | cand_005995 | EQ_us_growth | 4 | 10.57% | 12.54% | 0.6033 | 0.0167 | 0.1650 | 0.2403 | 0.2807 | 25.6% |
| 3 | cand_009678 | EQ_us_value | 4 | 10.82% | 13.21% | 0.5918 | 0.0206 | 0.1541 | 0.2244 | 0.2627 | 23.6% |
| 4 | cand_005991 | EQ_us_value | 4 | 10.97% | 13.68% | 0.5823 | 0.0236 | 0.1650 | 0.2412 | 0.2652 | 23.1% |
| 5 | cand_000758 | EQ_us_growth | 4 | 10.71% | 13.31% | 0.5794 | 0.0226 | 0.1546 | 0.2235 | 0.2882 | 23.0% |
| 6 | cand_007510 | EQ_dm_ex_us | 4 | 9.91% | 12.08% | 0.5724 | 0.0250 | 0.1644 | 0.2392 | 0.2674 | 23.3% |
| 7 | cand_004225 | EQ_kr | 4 | 10.70% | 13.62% | 0.5653 | 0.0265 | 0.1462 | 0.2098 | 0.2842 | 19.6% |
| 8 | cand_007699 | EQ_em | 4 | 9.77% | 12.30% | 0.5507 | 0.0277 | 0.1632 | 0.2378 | 0.2818 | 23.0% |

### §5.1 Shortlist 9-asset weight 표

| candidate | kr_eq | us_gr | us_val | dm_ex_us | em | kr_agg | kr_t10y | ust30 | hy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cand_008421 |  8.0% | **25.6%** | 21.2% | 10.9% | 14.3% | 5.1% | 3.8% | 1.0% | **10.1%** |
| cand_005995 |  6.4% | **25.6%** | 17.6% |  9.3% | 21.1% | 4.2% | 4.3% | 3.5% | 8.0% |
| cand_009678 | 15.6% | 20.8% | **23.6%** | 10.7% |  9.2% | 3.9% | 5.6% | 4.0% | 6.6% |
| cand_005991 | 21.0% | 21.0% | **23.2%** |  4.5% | 10.4% | 3.8% | 7.0% | 4.1% | 5.1% |
| cand_000758 | 16.4% | **23.0%** | 18.2% | 16.3% |  6.2% | 3.7% | 8.3% | 4.4% | 3.6% |
| cand_007510 |  3.2% | 20.8% | 19.1% | **23.4%** | 13.6% | 6.8% | 5.8% | 4.4% | 3.0% |
| cand_004225 | **19.6%** | 18.5% | 16.2% | 16.7% |  9.0% | 6.2% | 4.3% | 2.3% | 7.2% |
| cand_007699 |  4.3% | 22.6% | 13.0% | 17.1% | **23.0%** | 4.7% | 4.0% |  7.9% | 3.4% |

> 굵게 표시 = 각 후보의 최대 비중 자산. equity bucket 합은 모두 80.00%, FI bucket
> 합은 모두 20.00% (R-1B.2 hard constraint, ULP 수준 정확).

---

## §6. Reference 대비 비교

### §6.1 ref_max_sharpe (Current SAA) 대비

| 항목 | ref_max_sharpe | shortlist Top (cand_008421) | shortlist Bottom (cand_007699) |
|---|---:|---:|---:|
| equity / FI | 100% / 0% | 80% / 20% | 80% / 20% |
| Sharpe | **0.7769** | 0.6277 | 0.5507 |
| E[R] | 15.40% | 10.97% | 9.77% |
| σ | 15.96% | 12.69% | 12.30% |
| HHI | 0.5934 | 0.1635 | 0.1632 |
| max_w | 71.6% (us_growth) | 25.6% | 23.0% |
| nonzero | 2 | 9 | 9 |

**Sharpe 희생 폭** (ref_max_sharpe → shortlist):
- Top shortlist 대비: **−0.1492 (−19.2% relative)**
- Bottom shortlist 대비: **−0.2262 (−29.1% relative)**

E[R] 절대 차이는 −4.4 ~ −5.6%p. 단, ref_max_sharpe 는 운용 정책 (80:20 hard) 을 만족
하지 못하므로 실제 사용 불가 — Sharpe 비교는 "정책 비용 정량" 이 목적.

### §6.2 ref_80_20_equal_intra_bucket (Policy anchor) 대비

| 항목 | ref_80_20_equal | shortlist Top (cand_008421) | shortlist Bottom (cand_007699) |
|---|---:|---:|---:|
| equity / FI | 80% / 20% | 80% / 20% | 80% / 20% |
| Sharpe | 0.5389 | **0.6277** | 0.5507 |
| E[R] | 10.12% | 10.97% | 9.77% |
| σ | 13.20% | 12.69% | 12.30% |
| HHI | 0.1380 | 0.1635 | 0.1632 |
| max_w | 16.00% | 25.60% | 23.00% |
| nonzero | 9 | 9 | 9 |

**Sharpe 개선 폭** (ref_80_20_equal → shortlist):
- Top shortlist: **+0.0888 (+16.5% relative)** — 분산은 약간 양보 (max_w 16→26%, HHI 0.138→0.164)
- Bottom shortlist: **+0.0118 (+2.2% relative)** — 거의 동등 수준

즉 ref_80_20_equal_intra_bucket 의 균등 anchor 는 sweet pool 의 거의 **중앙**에 있고,
shortlist Top 후보는 **분산 약간 양보 + Sharpe 16% 개선** 의 trade-off.

---

## §7. Sweet Pool 공통 자산배분 특징

1. **bucket fit 완벽** (R-1B.2 sampling hard constraint)
2. **equity 5 자산 모두 nonzero** — 가장 작은 자산도 2%+ (Dirichlet uniform 효과)
3. **max_asset_weight 19~26%** — 단일 자산 over-concentration 자동 차단
4. **각 equity 평균 ≈ 16%** — ref_80_20 균등 분배 근방
5. **각 FI 평균 ≈ 5%** — 마찬가지로 균등 anchor 근방
6. **Sharpe 0.47~0.63 / E[R] 9~11% / σ 12~14%** — 매우 좁은 risk-return 클러스터
7. **dominant equity tilt 5 종 (us_value > dm_ex_us > us_growth > em > kr_equity)** — 균형 분포

---

## §8. 운용역 검토 포인트 (manager judgment 영역)

본 R-1C.1 분석으로 **데이터 기반 정량 후보 71건 → 8건 shortlist** 가 좁혀졌다. 다음
정성 결정은 운용역 몫:

| 결정 항목 | 근거 / 선택 옵션 |
|---|---|
| **Equity tilt 방향** | 운용역 macro view (성장 vs 가치 vs 신흥국 vs 한국) → 5 dominant tilt 그룹 중 선택 |
| **FI tilt 방향** | duration view (kr_treasury_10y / us_treasury_30y) vs credit view (us_high_yield) vs base (kr_aggregate_bond) → §3 자산별 weight 분포 활용 |
| **Sharpe vs 분산 trade-off** | shortlist 내 Sharpe 0.55~0.63 / max_w 19.6~25.6%. 운용 정책상 **20% 단일 자산 cap** 을 강제할지 여부 |
| **Regime overlay 대상** | 본 SAA shortlist 가 결정되면 기존 TAA overlay (rule-based, regime-specific tilts) 가 그 위에 작동 — overlay 후 검토 필요 |
| **목표수익률 충족 여부** | E[R] 9.8~11.0% 가 TDF 2060 운용 정책 / 기대수익률과 정합한지 |

---

## §9. R-1D similar_search 가 필요한 이유

본 R-1C.1 review 로 8개 shortlist 까지 좁혔지만, 운용역의 **추가 free-form query** 는
아직 미지원:

| 시나리오 | 현재 (R-1C / R-1C.1) | R-1D similar_search 필요 |
|---|---|---|
| "특정 risk-return 좌표 (σ=12.5%, E[R]=10.5%) 근방 후보를 보고 싶다" | scatter PNG 로 시각 확인만 가능 | nearest-k 후보 list 자동 반환 |
| "shortlist Top1 (cand_008421) 와 자산 weight 가 유사한 다른 후보는?" | 수동 비교 | weight L2 / cosine 거리 기반 k-NN |
| "us_value tilt + Sharpe 0.6 이상 후보만" | metric filter 수동 | API/CLI 한 줄로 sub-pool |
| "ref_80_20_equal anchor 근처지만 Sharpe 더 높은 후보" | R-1B.1 review packet 에 1회 분석 (현재 deprecated) | 정형 인터페이스로 재현 |

R-1D 의 핵심은 "8 shortlist 가 충분하지 않을 때 운용역이 직접 후보 풀을 탐색"
할 수 있게 하는 것. 본 R-1C.1 까지는 정량 데이터 + 추천 shortlist 까지 제공, R-1D
부터는 **인터랙티브 query** 단계.

---

## §10. 본 작업의 변경 범위

| 영역 | 변경 |
|---|:---:|
| 본 review md (1건) | ✓ 신규 |
| scratch 분석 스크립트 + dump | ✓ scratch only (production 미반영) |
| opportunity_set JSON / R-1C PNG / cloud_review md | ✗ 무변경 (read-only input) |
| `tdf_engine/` 코드 | ✗ 무변경 |
| `tdf_engine/config/*.yaml` | ✗ 무변경 |
| `tests/` | ✗ 무변경 |
| portfolio JSON (`portfolio_{etf,fund}_20260511.json`) | ✗ 무변경 |
| E-8 ~ E-12 산출물 | ✗ 무변경 |
| Decision Register count (14) | ✗ 무변경 |
| operating_mode | ✗ `relaxed_diagnostic` 유지 |
| 80:20 distance metric | ✗ 부활 없음 |

---

## §11. 한 줄 요약

> **Sweet pool 71건 (overlap_score ≥ 4) = 분산 4 metric 우수 후보와 성과/효율 2 metric
> 우수 후보가 겹치는 좁은 교집합 영역. dominant equity tilt 로 5 그룹 (us_value 28% /
> dm_ex_us 24% / us_growth 18% / em 16% / kr 14%) 분포. Manager review shortlist 8건
> 제안 — Sharpe 0.55~0.63, max_w 19.6~25.6%, ref_80_20_equal 대비 Sharpe +0.01~+0.09,
> ref_max_sharpe 대비 Sharpe −0.15~−0.23 (정책 비용). 다음 단계 = 운용역 정성 view →
> final SAA 결정, 또는 R-1D similar_search 진입.**
