# SAA Opportunity Set — Candidate Pool Review Packet (R-1B.1)

> ### ⚠️ DEPRECATED — R-1B.2 (2026-05-13) 이후
>
> 본 packet 의 분석은 **R-1B-lite v1 (schema_version `r1b_lite.1`)** 기준으로 작성됨.
> 그 이후 사용자 결정으로 **80:20 이 hard constraint** 가 되며 R-1B.2 (`r1b_lite.2`)
> 가 도입되었고, 그 결과:
>
> - sampling 이 **9-asset full simplex → bucket-constrained (eq 80% + fi 20%)** 으로 변경
> - metric `bucket_distance_from_80_20`, `full_weight_distance_from_80_20_equal_bucket_reference`
>   가 **영구 제거**
> - reference `ref_80_20` 가 **`ref_80_20_equal_intra_bucket`** 으로 rename
>
> 따라서 본 packet 의 §3 (Top 10 by bucket_distance), §4 (sweet spot intersection
> with bucket_distance), §5.2 의 bucket percentile rank 등은 **현 schema 와 정합하지 않는다**.
> "184건 sweet spot" 등의 정량 결과는 R-1B.1 시점의 historical record 로만 보존하며,
> R-1B.2 산출 (재생성된 `saa_opportunity_set_{etf,fund}_20260513.json` + summary md)
> 을 새로운 review 의 출발점으로 사용한다.
>
> R-1B.2 시점에는 모든 sampled candidate 가 자동으로 80:20 을 만족하므로 운용역 검토는
> **intra-bucket trade-off** (equity_intra_hhi, fixed_income_intra_hhi, equity/fi
> max_asset_weight, mvo_efficiency_score, sharpe) 에 집중한다.

**작성일**: 2026-05-13 · **scope**: read-only analysis · **source schema**: `r1b_lite.1` (deprecated)

> R-1B-lite 산출물 (10,000 Dirichlet candidates + 2 reference points) 을
> 운용역 관점에서 검토 가능한 형태로 정리한 리포트. SAA / TAA / product selection
> / config / Decision Register 미변경. 본 문서는 R-1B-lite JSON / summary md /
> 기존 portfolio JSON 을 read-only 로 분석.

원천 산출물:

- `saa_opportunity_set_etf_20260513.json` (10000 candidates + ref_max_sharpe + ref_80_20)
- `saa_opportunity_set_fund_20260513.json`
- `saa_opportunity_set_summary_20260513.md`

---

## §1. JSON Sanity 재확인

| 항목 | ETF | Fund | 기대 |
|---|---:|---:|---|
| candidates count | **10000** | **10000** | =10000 |
| reference_points count | **2** | **2** | ref_max_sharpe, ref_80_20 |
| pool_size_total | **10002** | **10002** | =10000+2 |
| feasible_count | **9974** | **9974** | — |
| rejected_by_degeneracy | **28** | **28** | — |
| rejected_by_filter (total) | **0** | **0** | (R-1B-lite optional filter disabled) |
| `feasible + degen + filter == pool_size_total` | **✓** | **✓** | 9974+28+0=10002 |
| `similar_search` key absent | ✓ | ✓ | (R-1C 으로 defer) |
| `ref_min_vol` / `ref_equal_weight` / `ref_user_selected` absent | ✓ | ✓ | (R-1C+) |
| `ref_max_sharpe` source vs `diagnostics.saa_diagnostics.saa_weights` max-abs-diff | **0.00e+00** | **0.00e+00** | bit-identical |
| schema_version | `r1b_lite.1` | `r1b_lite.1` | — |
| scope | `R-1B-lite` | `R-1B-lite` | — |

**판정**: 모든 sanity check PASS. ETF/Fund 수치가 동일한 이유는 두 portfolio JSON 의
`saa_diagnostics.cma` (μ, Σ, ρ), `saa_diagnostics.saa_weights`, `asset_allocation[*].bucket`,
random_seed (=42), n_candidates (=10000) 가 모두 동일하기 때문 — asset-level 입력이
같은 한 candidate 생성도 동일하다 (intended behavior).

이하 본문은 ETF 기준으로 기술. Fund 는 모든 metric / candidate_id / ranking 이
**bit-identical** 이므로 별도 표기 생략.

---

## §2. Degenerate 후보 분석 (28건)

| 항목 | 값 |
|---|---|
| count | **28** |
| volatility range | **17.88% ~ 22.06%** |
| expected_return range | **9.84% ~ 12.78%** |
| sharpe range | **0.3683 ~ 0.5175** |
| feasible volatility max (참고) | **17.81%** |
| feasible volatility min (참고) | **4.91%** |
| 모두 feasible 좌측 (vol < feasible_min) 인가? | **No** |
| 모두 feasible **우측** (vol > feasible_max=17.81%) 인가? | **Yes (28/28)** |
| `mvo_efficiency_score == None` 개수 | **0** (모두 boundary clip 후 계산됨) |
| Top 10 by Sharpe 에 등장 | **0건** |
| Top 10 by bucket_distance 에 등장 | **0건** |
| Top 10 by HHI 에 등장 | **0건** |

**사유**: Dirichlet 샘플 중 weight 가 고변동 자산 (us_growth_equity 등) 에 과집중된
극단 후보 28건이 E-9 frontier grid (31 points) 의 **우측 upper bound (max_er 기반)
밖** 으로 떨어진다. spec §5 정의대로 boundary clip + `feasibility_status = degenerate`
로 마킹. `mvo_efficiency_score` 는 clip 된 frontier value 로 계산되어 값 자체는
존재하지만 (None 아님), feasibility flag 만 degenerate.

**상위 ranking 영향**: 28건 모두 Sharpe 0.37~0.52 구간이므로 Top 10 Sharpe (≥0.70)
나 Top 10 bucket / HHI 후보군에 **단 1건도 진입하지 않음**. R-1B.1 리뷰 결론에
영향 없음.

**R-1C 권고**: scatterplot 작성 시 degenerate 28건은 별도 marker / 회색 처리하여
운용역에게 boundary 표시.

---

## §3. 후보군 비교 — Top 10 × 5종

### §3.1 Top 10 by Sharpe (feasible only)

| # | candidate_id | E[R] | σ | Sharpe | eq | fi | max_w | nz | HHI | bucket_d | full_d | mvo_gap | feas |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | cand_005676 | 13.43% | 14.53% | **0.7176** | 89.8% | 10.2% | 47.7% | 9 | 0.3829 | 0.1965 | 0.6021 | 0.0069 | feasible |
| 2 | cand_009328 | 12.66% | 13.63% | 0.7087 | 78.7% | 21.3% | 43.6% | 9 | 0.3323 | 0.0261 | 0.4787 | 0.0062 | feasible |
| 3 | cand_004963 | 12.22% | 13.01% | 0.7084 | 72.2% | 27.8% | 38.6% | 9 | 0.2791 | 0.1559 | 0.4317 | 0.0047 | feasible |
| 4 | cand_007720 | 10.22% | 10.81% | 0.6674 | 60.2% | 39.8% | 32.1% | 9 | 0.2260 | 0.3959 | 0.4106 | 0.0034 | feasible |
| 5 | cand_002711 | 11.72% | 12.39% | 0.7040 | 78.8% | 21.2% | 38.5% | 9 | 0.2959 | 0.0235 | 0.4271 | 0.0037 | feasible |

> (Top 1~3 + 대표 5건 — Sharpe 0.66~0.72 구간, 거의 모두 9 자산 nonzero, HHI 0.22~0.38.
> Sharpe top 후보들은 모두 **상당히 집중**되어 있다 — HHI 가 ref_80_20 의 0.138 대비 2~3 배.)

### §3.2 Top 10 by lowest `bucket_distance_from_80_20`

| # | candidate_id | E[R] | σ | Sharpe | eq | fi | HHI | bucket_d | full_d |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | cand_004014 | 10.82% | 12.76% | 0.6133 | 80.0% | 20.0% | 0.2072 | **0.0000** | 0.2860 |
| 2 | cand_000844 |  8.04% | 12.21% | 0.4133 | 80.0% | 20.0% | 0.3229 | **0.0000** | 0.4753 |
| 3 | cand_000511 | 10.11% | 12.14% | 0.5860 | 80.0% | 20.0% | 0.2826 | 0.0001 | 0.4012 |

> bucket 합 80/20 정확히 일치하는 후보 다수. Sharpe 0.41~0.61 범위 — bucket fit 만으로는
> ref_max_sharpe 의 0.78 보다 낮다. 단 ref_80_20 의 0.54 대비 +0.05~+0.07 개선 가능.

### §3.3 Top 10 by lowest `concentration_hhi`

| # | candidate_id | HHI | nz | max_w | E[R] | σ | Sharpe | eq | fi |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | cand_008122 | **0.1155** | 9 | 16.7% |  7.37% | 10.47% | 0.4176 | 57.4% | 42.6% |
| 2 | cand_006183 | 0.1165 | 9 | 17.7% |  7.99% | 10.90% | 0.4577 | 59.4% | 40.6% |
| 3 | cand_009981 | 0.1201 | 9 | 18.3% |  7.15% | 10.13% | 0.4103 | 52.9% | 47.1% |

> HHI 최저권 후보들은 모두 fixed_income 비중이 40%+ 로 매우 높음 (Dirichlet uniform 의
> 분산 효과). Sharpe 가 0.41~0.46 으로 ref_80_20 (0.54) 보다도 낮다 — **분산은 좋지만
> 운용 정책 (eq 80%) 과 거리가 멀어 단독 채택 어려움**.

### §3.4 Top 10 by lowest `full_weight_distance_from_80_20_equal_bucket_reference`

| # | candidate_id | full_d | bucket_d | HHI | Sharpe | E[R] | σ | eq | fi |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | cand_005983 | **0.1382** | 0.0180 | 0.1382 | 0.5440 | 10.14% | 13.12% | 79.1% | 20.9% |
| 2 | cand_009581 | 0.1463 | 0.0186 | 0.1463 | 0.5563 | 10.45% | 13.39% | 80.9% | 19.1% |
| 3 | cand_004873 | 0.1530 | 0.0557 | 0.1530 | 0.5526 | 10.75% | 14.02% | 82.8% | 17.2% |

> ref_80_20 (각 equity 16% / 각 FI 5%) 에 9-자산 vector L2 로 가장 가까운 후보들.
> Sharpe 0.54~0.56 — ref_80_20 의 0.54 와 동등 (구조가 거의 동일하므로 자연스러움).

### §3.5 Top 10 by lowest `mvo_efficiency_score` (degenerate 제외)

| # | candidate_id | mvo_gap | Sharpe | E[R] | σ | eq | fi | HHI | bucket_d |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | cand_004019 | **0.0032** | 0.7043 | 11.61% | 12.23% | 75.9% | 24.1% | 0.2940 | 0.0824 |
| 2 | cand_007720 | 0.0034 | 0.6674 | 10.22% | 10.81% | 60.2% | 39.8% | 0.2260 | 0.3959 |
| 3 | cand_002711 | 0.0037 | 0.7040 | 11.72% | 12.39% | 78.8% | 21.2% | 0.2959 | 0.0235 |

> 같은 σ 의 frontier E[R] 대비 candidate E[R] 차이 (작을수록 frontier 위/근접).
> cand_004019 / cand_002711 은 mvo_gap 이 매우 작으면서 bucket_d 도 ≤0.08 — frontier
> 근접 + 80/20 정책 근접의 **이중 우수 후보**.

---

## §4. Sweet Spot — Sharpe ↑ ∩ bucket_distance ↓ ∩ HHI ↓ 교집합

각 metric 의 percentile threshold 를 1%/5%/10% 로 변화시키며 교집합 candidate
수를 측정.

| percentile band | Sharpe threshold (≥) | bucket_d threshold (≤) | HHI threshold (≤) | 후보 수 |
|---|---:|---:|---:|---:|
| **top 1% × bot 1% × bot 1%** | 0.6505 | 0.0099 | 0.1321 | **0** |
| **top 5% × bot 5% × bot 5%** | 0.5942 | 0.0522 | 0.1437 | **0** |
| **top 10% × bot 10% × bot 10%** | 0.5592 | 0.1023 | 0.1506 | **2** |

### §4.1 top 10% × bot 10% × bot 10% — 후보 2건 (대표 전수)

| # | candidate_id | Sharpe | E[R] | σ | eq | fi | HHI | bucket_d | full_d | mvo_gap |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **cand_005095** | 0.5879 | 10.44% | 12.65% | 76.0% | 24.0% | 0.1408 | 0.0804 | 0.1769 | 0.0235 |
| 2 | **cand_003531** | 0.5708 |  9.90% | 12.10% | 77.5% | 22.5% | 0.1491 | 0.0508 | 0.1932 | 0.0269 |

**관찰**:
- top 5% × bot 5% × bot 5% 까지 좁히면 교집합은 비어있다.
- top 10% (Sharpe ≥ 0.56) × bot 10% (bucket_d ≤ 0.10 / HHI ≤ 0.15) 에서 2건 발견.
- 두 후보 모두 Sharpe 0.57~0.59 로 **ref_80_20 (0.54) 대비 +0.03~+0.05 개선, ref_max_sharpe (0.78)
  대비 −0.20** — Sharpe 측면 trade-off 큼.
- 핵심: **세 metric 모두 동시에 강한 후보는 매우 희소**. 운용역은 어느 metric 을 우선할지
  policy 결정 필요.

---

## §5. Reference Point 비교

### §5.1 정량 비교

| metric | `ref_max_sharpe` (Current SAA) | `ref_80_20` (Policy reference) | 차이 |
|---|---:|---:|---|
| source | `diagnostics.saa_diagnostics.saa_weights` (E-6.2 T-6) | 합성 (eq 5×16%, fi 4×5%) | — |
| expected_return | **15.40%** | 10.12% | +5.28%p |
| volatility | **15.96%** | 13.20% | +2.76%p |
| sharpe | **0.7769** | 0.5389 | +0.2380 |
| equity_weight | **100.0%** | 80.0% | +20.0%p |
| fixed_income_weight | **0.0%** | 20.0% | −20.0%p |
| max_asset_weight | **71.6%** (us_growth) | 16.0% | +55.6%p |
| nonzero_asset_count | **2** | 9 | −7 |
| concentration_hhi | **0.5934** | 0.1380 | +0.4554 |
| bucket_distance_from_80_20 | **0.4000** | 0.0000 | +0.4000 |
| full_weight_distance_from_80_20_equal_bucket_reference | **0.6414** | 0.0000 | +0.6414 |
| mvo_efficiency_score (gap) | **−0.0001** (frontier 위) | 0.0276 | +0.0277 |
| feasibility_status | feasible | feasible | — |

### §5.2 Percentile rank in candidate pool (feasible 9974건 기준)

| reference | Sharpe rank | HHI rank | bucket_d rank |
|---|---:|---:|---:|
| `ref_max_sharpe` | **100.0% (top)** | **99.99% (top, 매우 집중)** | — |
| `ref_80_20` | 85.88% (상위 14%) | **2.68% (bottom 3%, 매우 분산)** | **0.00% (bottom)** |

### §5.3 해석

**(a) ref_max_sharpe — Sharpe 최고 / 집중 극단**
- Sharpe 0.78 로 **pool top 100%** (그 어느 candidate 보다도 우월) — frontier 위 또는 직상.
- 단 HHI 0.5934 는 **pool top 0.01%** (가장 집중된 후보 수준). 단 2 자산 (us_growth_equity 71.6%, us_value_equity 28.4%) 에 100% 배분.
- equity 100% / fixed_income 0% — TDF 2060 정책 (80/20) 과 **20%p 괴리**.
- **운용 사용 불가**. 단일 자동 산출물로 채택 불가능. (R-1A §2 corner solution 진단과 정합.)

**(b) ref_80_20 — Policy fit 최고 / Sharpe 희생**
- bucket_distance = 0 (정확히 80/20). HHI 0.138 (pool bottom 3%, 매우 분산).
- Sharpe 0.5389 — pool 상위 14% 수준. ref_max_sharpe 대비 **−0.24**, **약 31% 감소**.
- mvo_efficiency_score (gap) = 0.0276 — 같은 σ 의 frontier E[R] 대비 **2.76%p 낮음**.
- **정책 fit 은 완벽하나 risk-return 효율은 frontier 와 큰 격차**.

**(c) candidate pool 내 ref_80_20 ↔ Sharpe 향상 후보의 존재**

ref_80_20 의 bucket fit 을 0.05 이내로 유지하면서 Sharpe 를 더 높이는 후보:

| 조건 | 결과 |
|---|---:|
| `bucket_distance ≤ 0.05 + 0.05 (=0.05)` AND `sharpe > 0.5389` | **184건** 존재 |

대표 5건:

| # | candidate_id | Sharpe | E[R] | σ | eq | fi | HHI | bucket_d |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | cand_009328 | **0.7087** | 12.66% | 13.63% | 78.7% | 21.3% | 0.3323 | 0.0261 |
| 2 | cand_002711 | 0.7040 | 11.72% | 12.39% | 78.8% | 21.2% | 0.2959 | 0.0235 |
| 3 | cand_001695 | 0.6945 | 12.10% | 13.10% | 81.4% | 18.6% | 0.2804 | 0.0289 |
| 4 | cand_004570 | 0.6889 | 12.36% | 13.59% | 79.7% | 20.3% | 0.3358 | 0.0070 |
| 5 | cand_009555 | 0.6872 | 12.00% | 13.09% | 80.7% | 19.3% | 0.3206 | 0.0146 |

> bucket fit 은 거의 80/20 (bucket_d 0.007~0.029) 을 유지하면서 Sharpe **0.69~0.71**
> 달성. ref_80_20 대비 **+0.15~+0.17**. 단, HHI 는 0.28~0.34 로 ref_80_20 의 0.138
> 대비 **2~2.5배** — 운용 정책 의지에 따라 채택 여부 갈림.

---

## §6. 운용역 검토용 결론

### §6.1 현재 max-Sharpe 단일 SAA 의 문제 (= ref_max_sharpe)

- 수학적 최적해이나 **2 자산 (us_growth_equity 71.6%, us_value_equity 28.4%) 에 100%
  집중** → TDF 2060 운용 정책으로 직접 사용 불가.
- equity 100% — 80/20 정책 대비 **20%p 초과**. TAA 와 projection 으로 강제 조정해야 하는
  구조적 문제 → final implemented weights 와 SAA 의 의미 분리가 불가피.
- HHI 0.59 는 pool top 0.01% — 분산 측면에서 극단.

### §6.2 80/20 reference (= ref_80_20) 의 장단점

| 장점 | 단점 |
|---|---|
| bucket fit 완벽 (0/0/0) | Sharpe 0.54 — frontier 대비 −2.76%p E[R] |
| HHI 0.138 (pool bottom 3%) | 단일 자산 16%/5% 균등은 자산별 view 미반영 |
| 9 자산 nonzero — 분산 강함 | risk-return 효율 측면 약함 |
| 운용 설명 / 보고 쉬움 | E[R] 10.1% — TDF 2060 목표수익률 부족 가능 |

### §6.3 후보군에서 관찰되는 trade-off

1. **Sharpe ↔ HHI**: Top Sharpe 후보들은 모두 HHI 0.22~0.38 (집중). Sharpe 와 분산은 동시 달성 어렵다.
2. **Sharpe ↔ bucket fit**: bucket_d=0 (정확히 80/20) 인 후보의 Sharpe 는 0.41~0.61 — top Sharpe (0.71) 보다 −0.10 ~ −0.30.
3. **세 metric 동시 만족**: top 10% × bot 10% × bot 10% 교집합 = **단 2건**. Sharpe 0.57~0.59. 세 차원 동시 강자는 매우 희소.
4. **policy-feasible Sharpe sweet spot**: bucket_d ≤ 0.05 조건만으로는 **184건** 의 Sharpe 0.55~0.71 후보 풀이 존재. HHI 조건을 풀면 운용 가능 후보 폭이 크게 늘어남.

### §6.4 R-1C 에서 시각화가 필요한 이유

- 현재 review packet 은 텍스트 표 기반 — 184건의 sweet spot pool, 10000 candidate
  의 분포 형태, frontier 와의 위치 관계, ref_max_sharpe 와 ref_80_20 의 좌표 거리를
  운용역이 한눈에 비교하기 어렵다.
- 운용역의 자연 질문 ("내가 σ 13%, E[R] 12% 점을 원한다면 어떤 후보들이 있나?") 에
  답하려면 좌표 평면 + similar_search 가 필요.
- Top-K 표는 **5개 dimension 중 1개** 만 정렬할 뿐 — 운용역이 정책 가중치를 다르게
  주면 표를 재정렬해야 한다.

### §6.5 R-1C 진입 시 우선 구현 순서 (권고)

| 우선순위 | 항목 | 사유 |
|:---:|---|---|
| **1** | scatterplot PNG (x=σ, y=E[R], color=Sharpe 또는 equity_weight, ref 좌표 강조) | 분포 즉시 파악. 184건 sweet spot 시각화. degenerate 28건 boundary 표시. |
| **2** | `similar_search` (target σ, E[R] 점에서 가까운 k 건) | 운용역 free-form query 대응. spec §7 인터페이스대로 구현. |
| **3** | `ref_min_vol` (E-9 frontier min_vol endpoint) | 보수 운용 대안 reference. low-σ 영역 비교 가능. |
| **4** | `ref_equal_weight` (w_i = 1/9) | 무정보 baseline. ref_80_20 와의 차이 (bucket weighting 효과) 분리. |

scatterplot 이 단연 우선 — 본 packet 의 모든 표 / 교집합 / 184건 sweet spot 이
**한 장의 그림으로 운용역 review 가능**해진다.

---

## §7. 본 작업의 변경 범위

| 영역 | 변경 |
|---|:---:|
| 신규 산출 | 본 packet md (1건) + scratch 분석 스크립트 (1건, production 미반영) |
| `tdf_engine/` 코드 | ✗ 무변경 |
| `tdf_engine/config/*.yaml` | ✗ 무변경 |
| `tests/` | ✗ 무변경 |
| 기존 portfolio JSON (`portfolio_{etf,fund}_20260511.json`) | ✗ 무변경 (read-only) |
| 기존 opportunity_set JSON | ✗ 무변경 (read-only) |
| 기존 summary md | ✗ 무변경 (read-only) |
| E-8 ~ E-12 산출물 | ✗ 무변경 |
| Decision Register (count=14) | ✗ 무변경 |
| operating_mode | ✗ `relaxed_diagnostic` 유지 |

---

## §8. 한 줄 요약

> **R-1B-lite candidate pool 10,000 + 2 reference 분석 결과: max-Sharpe 단일 SAA 는
> 2 자산 집중 (HHI 0.59, eq 100%) 으로 운용 정책 부적합. 80/20 reference 는 정책 fit
> 완벽하나 Sharpe 0.54 로 frontier 대비 2.76%p E[R] 격차. bucket_d ≤ 0.05 sweet spot
> 에서 Sharpe 0.69~0.71 후보 184건 존재 — 운용역 검토 가치 큼. R-1C scatterplot +
> similar_search 우선 구현 권고.**
