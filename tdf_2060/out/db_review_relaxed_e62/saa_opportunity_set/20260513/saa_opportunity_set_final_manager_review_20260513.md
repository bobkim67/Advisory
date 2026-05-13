# SAA Opportunity Set — Final Manager Review (2026-05-13)

> **Read-only review packet.** 본 문서는 R-1B.2 / R-1C / R-1C.1 / R-1D 산출물을
> 종합한 운용역 최종 검토 자료다. **자동 final SAA 선택이 아니다** — 표현은
> "manager review candidates" / "final review shortlist" 로 통일.
>
> production SAA / TAA / product selection / config / Decision Register / E-series
> baseline 모두 무변경. 80:20 은 hard constraint 로 유지.

**Source**: R-1B.2 bucket-constrained opportunity set JSON (`r1b_lite.2`).
**ETF / Fund**: CMA·SAA·bucket·seed 동일 → 모든 분석/shortlist **bit-identical**.
이하 본문은 ETF 기준이며 Fund 동일.

---

## §1. Executive Summary

| 단계 | 산출 | 결과 |
|:---:|---|---|
| **R-1B.2** | bucket-constrained Dirichlet 10,000 candidate + 2 reference | 모든 sampled candidate eq=80% / fi=20% hard |
| **R-1C** | scatter / metric cloud (6 top-decile) / overlap-score 시각화 | overlap≥3: 773, ≥4: 71, ≥5: 1, =6: 0 |
| **R-1C.1** | sweet pool 71건 → manager review shortlist 8건 | 5 dominant equity tilt 그룹 (us_value 28% / dm_ex_us 24% / us_growth 18% / em 16% / kr 14%) |
| **R-1D** | coordinate / weight similarity search (CLI + module) | shortlist 8 후보 각 nearest k 후보 풀 |
| **본 packet** | 8 후보의 정량 비교 + 후보별 review note + decision worksheet | **자동 선택 아님 — 운용역 정성 판단 입력 대기** |

본 packet 으로 운용역이 채워야 하는 것:
- 8 후보 중 어느 자산 tilt 방향이 정성 view 와 정합한가
- max_asset_weight 19.6~25.6% 범위 중 운용 정책상 수용 가능 상한
- Sharpe 0.55~0.63 trade-off 수용 여부 (vs 정책 미만족 ref_max_sharpe 0.78)

---

## §2. Hard Constraint Recap

| 항목 | 값 / 정책 |
|---|---|
| equity bucket | **= 0.80 (hard)** — 모든 sampled candidate 가 자동 만족 |
| fixed_income bucket | **= 0.20 (hard)** — 자동 만족 |
| 전체 weights sum | = 1.0 |
| 자산별 lower / upper bound | none (asset-level), Dirichlet long-only 만 |
| `ref_max_sharpe` | unconstrained MVO reference (eq=100%, fi=0%) — **운용 가능 후보 아님**, 정책 비용 정량 reference 로만 사용 |
| `ref_80_20_equal_intra_bucket` | intra-bucket 균등 anchor (eq 5×16%, fi 4×5%) — sampled pool 의 자연 anchor |
| 후보 간 차이 | **bucket 내부 분배 (intra-bucket weights) 에만 존재** |
| 제거된 평가 metric (영구) | `bucket_distance_from_80_20` / `full_weight_distance_from_80_20_equal_bucket_reference` (R-1B.2 시점 제거; 본 packet 에서도 부활 없음) |

---

## §3. Reference Point Comparison

| metric | `ref_max_sharpe` | `ref_80_20_equal_intra_bucket` | sweet pool median | shortlist Top (cand_008421) |
|---|---:|---:|---:|---:|
| expected_return | 15.40% | 10.12% | 10.19% | 10.97% |
| volatility | 15.96% | 13.20% | 13.32% | 12.69% |
| **sharpe** | **0.7769** | 0.5389 | 0.5365 | **0.6277** |
| mvo_efficiency_score | −0.0001 (frontier 위) | 0.0276 | 0.0292 | 0.0142 |
| concentration_hhi | 0.5934 | 0.1380 | 0.1578 | 0.1635 |
| equity_intra_hhi | 0.5934 | 0.2000 | 0.2299 | 0.2330 |
| fixed_income_intra_hhi | n/a (fi=0) | 0.2500 | 0.2780 | 0.3607 |
| max_asset_weight | 71.6% | 16.0% | 23.2% | 25.6% |
| equity_weight | **100%** | 80% | 80% | 80% |
| fixed_income_weight | **0%** | 20% | 20% | 20% |
| status / interpretation | **운용 불가** (정책 미만족). Sharpe 기준 reference 로만 활용. | 정책 fit 완벽, intra 균등 anchor. 정성 view 없을 때 보수 기준선. | sweet pool 의 중심. shortlist 후보의 "기본" 위치. | sweet pool max Sharpe + overlap 5. 단 max_w 25.6% 부담. |

**해석**:
- `ref_max_sharpe` 의 Sharpe 0.78 은 **2 자산 100% 집중**이라 정책상 사용 불가.
- sweet pool median Sharpe 0.54 ≈ `ref_80_20_equal_intra_bucket` Sharpe 0.54. 즉 균등
  anchor 가 sweet pool 의 중심 — equal_intra 가 합리적 baseline.
- shortlist Top 후보는 ref_80_20_equal 대비 **+0.09 Sharpe** 개선 (정책 fit 유지하면서).

---

## §4. Visualization Summary (R-1C 산출 PNG)

| 그림 | 경로 | 해석 |
|---|---|---|
| **Risk-Return Scatter** | `saa_opportunity_set_{etf,fund}_risk_return_scatter_20260513.png` | 10,000 후보가 (σ, E[R]) 평면 위에 클라우드 형성. degenerate 28~160건은 우측 boundary (frontier extrapolation) 에 위치하며 ranking 영향 0. `ref_max_sharpe` (★) 는 우상단 corner, `ref_80_20_equal_intra_bucket` (◇) 는 중앙에 위치. |
| **Metric Cloud Overlay** | `saa_opportunity_set_{etf,fund}_metric_clouds_20260513.png` | 6 top-decile cloud (Sharpe / MVO gap / HHI / eq_intra_HHI / fi_intra_HHI / max_w) overlay. Sharpe·MVO cloud (return-oriented) 는 우상단, HHI·max_w cloud (diversification-oriented) 는 중앙에 분포. 두 클러스터의 **교집합 영역이 매우 좁고, 그 안이 sweet pool**. |
| **Overlap Score Scatter** | `saa_opportunity_set_{etf,fund}_overlap_score_20260513.png` | candidate 별 overlap_score (0~6) 를 색으로 표현. overlap≥4 (강조) 71건이 좁은 띠를 형성. overlap=5 단 1건 (cand_008421), overlap=6 은 0. 분산-수익 동시 우수 영역의 희소성 시각적 확인. |

**핵심 의미**:
- Sharpe·MVO cloud 와 분산 4 metric cloud 가 거의 만나지 않음 → "효율과 분산은 서로
  trade-off" 의 시각적 증거.
- overlap=6 (전 metric 동시 top) 후보가 0건 — 모든 차원에서 최고인 후보는 존재하지 않음.
  운용역은 **어느 dimension 을 우선할지** 정성 판단 필요.

---

## §5. Sweet Pool Summary (R-1C.1, overlap_score ≥ 4)

| metric | min | p25 | median | p75 | max |
|---|---:|---:|---:|---:|---:|
| expected_return | 9.04% | 9.76% | 10.19% | 10.44% | 10.97% |
| volatility | 12.08% | 12.95% | 13.32% | 13.63% | 14.26% |
| sharpe | 0.4682 | 0.5053 | 0.5365 | 0.5629 | **0.6277** |
| mvo_efficiency_score | 0.0142 | 0.0243 | 0.0292 | 0.0333 | 0.0390 |
| concentration_hhi | 0.1441 | 0.1529 | 0.1578 | 0.1627 | 0.1662 |
| equity_intra_hhi | 0.2078 | 0.2217 | 0.2299 | 0.2371 | 0.2423 |
| fixed_income_intra_hhi | 0.2532 | 0.2689 | 0.2780 | 0.2838 | 0.3607 |
| max_asset_weight | 19.04% | 21.93% | 23.21% | 24.00% | 25.59% |

**Sweet pool 핵심**:
- 71 후보 중 1건 (cand_008421) 만 overlap=5; 6은 0건.
- equity 5 자산 평균 모두 15~17% (ref_80_20 의 16% 와 ±0.7%p), FI 4 자산 평균 모두
  4.8~5.3% (ref_80_20 의 5% 와 ±0.3%p) — sweet pool 후보들의 자산 평균은 균등 anchor
  근방.
- 후보 간 변동성은 equity 측 7~10%p IQR, FI 측 2~3%p IQR — **운용역의 자유도는 주로
  equity tilt 방향에 존재**.

| group (dominant equity tilt) | count | share |
|---|---:|---:|
| `EQ_us_value_equity` | 20 | 28% |
| `EQ_dm_ex_us_equity` | 17 | 24% |
| `EQ_us_growth_equity` | 13 | 18% |
| `EQ_em_equity` | 11 | 16% |
| `EQ_kr_equity` | 10 | 14% |

---

## §6. Final Review Shortlist (8 candidates)

> 정렬: overlap_score desc → feasible 우선 → sharpe desc → HHI asc → id asc.
> 굵은 표기 = 그 후보의 dominant equity asset (group label 의 근거).

| # | candidate_id | group | ov | E[R] | σ | Sharpe | mvo_gap | HHI | eq_iHHI | fi_iHHI | max_w | eq_max | fi_max | short interpretation |
|---:|---|---|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | **cand_008421** | EQ_us_growth | **5** | 10.97% | 12.69% | **0.6277** | 0.0142 | 0.1635 | 0.2330 | 0.3607 | 25.6% | 25.6% | 10.1% | sweet pool 유일 overlap=5. Sharpe 최고. 단 fi_intra 0.361 (HY tilt) + max_w 25.6%. |
| 2 | cand_005995 | EQ_us_growth | 4 | 10.57% | 12.54% | 0.6033 | 0.0167 | 0.1650 | 0.2403 | 0.2807 | 25.6% | 25.6% | 8.0% | 2번째 최고 Sharpe. em 21% (강한 tilt). max_w 25.6%. |
| 3 | cand_009678 | EQ_us_value | 4 | 10.82% | 13.21% | 0.5918 | 0.0206 | 0.1541 | 0.2244 | 0.2627 | 23.6% | 23.6% | 6.6% | us_value 23.6% + kr 15.6%. balanced. low HHI. |
| 4 | cand_005991 | EQ_us_value | 4 | 10.97% | 13.68% | 0.5823 | 0.0236 | 0.1650 | 0.2412 | 0.2652 | 23.1% | 23.1% | 7.0% | kr 21.0% + us_value 23.2%. dm_ex_us 매우 낮음 (4.5%). |
| 5 | cand_000758 | EQ_us_growth | 4 | 10.71% | 13.31% | 0.5794 | 0.0226 | 0.1546 | 0.2235 | 0.2882 | 23.0% | 23.0% | 8.3% | us_growth 23.0% + kr 16.4% + dm_ex_us 16.3%. kr_t10y 8.3% (가장 균형 FI). |
| 6 | cand_007510 | EQ_dm_ex_us | 4 | 9.91% | 12.08% | 0.5724 | 0.0250 | 0.1644 | 0.2392 | 0.2674 | 23.3% | 23.3% | 6.8% | dm_ex_us 23.4% (선진국 ex-US). σ 최저 (12.1%). E[R] 도 9.9% 로 낮음. |
| 7 | cand_004225 | EQ_kr | 4 | 10.70% | 13.62% | 0.5653 | 0.0265 | **0.1462** | 0.2098 | 0.2842 | **19.6%** | 19.6% | 7.2% | **가장 분산** (HHI 0.146, max_w 19.6%). kr 19.6% + dm_ex_us 16.7%. |
| 8 | cand_007699 | EQ_em | 4 | 9.77% | 12.30% | 0.5507 | 0.0277 | 0.1632 | 0.2378 | 0.2818 | 23.0% | 23.0% | 7.9% | em 23.0% + dm_ex_us 17.1%. ust30 7.9%. E[R] 최저. |

### §6.1 9-asset weights (전체)

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

---

## §7. Candidate-by-Candidate Review Notes

각 후보별: 특징 / 장점 / 부담 / R-1D 주변 후보 / 운용역 판단 질문.

### §7.1 cand_008421 — EQ_us_growth, overlap=5 (sweet pool 유일 special)

- **특징**: us_growth 25.6% + us_value 21.2% + em 14.3% 미국·신흥국 risk-on tilt. FI 측 us_high_yield 10.1% (HY 강함), us_treasury_30y 단 1.0%.
- **장점**: sweet pool max Sharpe (0.6277). overlap=5 — 6 metric 중 5 동시 top decile.
  mvo_gap 0.0142 (frontier 매우 근접).
- **부담**: max_w 25.6% (sweet pool 상한). fixed_income_intra_hhi 0.361 (HY 10% + 다른 3 FI 합산 10% 의 극단 분배).
- **R-1D 주변 후보**:
  - by-coord nearest: cand_006504 / cand_005242 / cand_007524 — 같은 Sharpe ~0.628 이나 overlap=2 (분산 약함).
  - by-weight nearest: **cand_008278** (overlap=3, Sharpe 0.609, max_w 23.7%) / cand_000718 (overlap=3, max_w 21.2%) — **자산 구조 유사 + 분산 더 강한 대안**.
- **판단 질문**: cand_008421 의 max_w 25.6% 와 HY 10% tilt 가 운용 정책상 허용 가능한가? 비슷한 구조의 cand_008278 (max_w 23.7%, Sharpe 0.609) 와의 trade-off 어떻게 평가?

### §7.2 cand_005995 — EQ_us_growth, overlap=4

- **특징**: us_growth 25.6% + em 21.1% (신흥국 강한 tilt). kr_equity 단 6.4%.
- **장점**: shortlist 내 2nd Sharpe (0.6033). em-heavy.
- **부담**: max_w 25.6% (#1 과 동률 상한). kr_equity 6.4% — 국내 비중 낮음.
- **R-1D 주변 후보**:
  - by-coord: overlap=0 후보 다수 — risk-return 만 비슷한 sweet pool 밖 후보 풍부.
  - by-weight: cand_000772 (overlap=0), cand_008278 (overlap=3) — 구조 유사 ↔ overlap 다양.
- **판단 질문**: 신흥국 (em 21.1%) 비중이 운용 view 와 정합한가? 한국 비중 6.4% 가 정책상 너무 낮은가?

### §7.3 cand_009678 — EQ_us_value, overlap=4

- **특징**: us_value 23.6% + us_growth 20.8% (미국 가치+성장 분배). kr 15.6%.
- **장점**: HHI 0.154 (shortlist 내 두 번째 분산 강함). max_w 23.6%.
- **부담**: em 9.2% (신흥국 비중 낮음).
- **R-1D 주변 후보**:
  - by-coord: cand_002694 (overlap=3) — 비슷한 좌표 + 더 분산.
  - by-weight: cand_008837 (overlap=3, Sharpe 0.611), cand_006452 (overlap=3).
- **판단 질문**: us_value vs us_growth 동시 over-tilt 가 view 와 정합한가? 신흥국 비중 9.2% 가 너무 낮은가?

### §7.4 cand_005991 — EQ_us_value, overlap=4

- **특징**: kr 21.0% + us_growth 21.0% + us_value 23.2% (한국 + 미국 강함). dm_ex_us 4.5% (선진국 ex-US 비중 미미).
- **장점**: kr_equity 21.0% — 국내 강한 tilt (한국 view 시 자연 선택지).
- **부담**: dm_ex_us 4.5% — 선진국 분산 미미. em 10.4%.
- **R-1D 주변 후보**:
  - by-coord: 같은 좌표 후보들 (cand_003209 등).
  - by-weight: cand_000970 / cand_000905 / cand_009976 — 유사 구조.
- **판단 질문**: 한국 21% tilt 가 운용 정책에서 정당화되는가? 선진국 ex-US 4.5% 가 운용 정책상 부담스럽지 않은가?

### §7.5 cand_000758 — EQ_us_growth, overlap=4

- **특징**: us_growth 23.0% + us_value 18.2% + kr 16.4% + dm_ex_us 16.3% (5 자산 균형). FI 측 kr_treasury_10y 8.3% (sweet pool 내 가장 균형 FI).
- **장점**: HHI 0.155 + 자산 5개가 16~23% 균형. em 6.2% 만 낮음.
- **부담**: em 6.2% (신흥국 비중 낮음). us_high_yield 3.6% (HY 비중 낮음).
- **R-1D 주변 후보**:
  - by-weight: cand_007692 / cand_007679 / cand_004733.
- **판단 질문**: 5 자산 균형형 (한국+미국+선진국) 이 view 와 정합한가? 신흥국 + HY 비중 낮음 수용 가능한가?

### §7.6 cand_007510 — EQ_dm_ex_us, overlap=4

- **특징**: dm_ex_us 23.4% + us_growth 20.8% + us_value 19.1% (선진국 강함). kr_equity 3.2% (국내 비중 미미).
- **장점**: σ 12.1% (shortlist 내 최저 volatility). 안정 추구형.
- **부담**: kr_equity 3.2% — 국내 비중 미미. E[R] 9.9% (낮음).
- **R-1D 주변 후보**:
  - by-weight: cand_003212 / cand_006508 / cand_004717.
- **판단 질문**: 국내 비중 3.2% 가 정책 위반은 아니지만 운용역 view 와 정합한가? σ 최저 (12.1%) 의 안정성 vs E[R] 9.9% 의 낮은 기대수익률 trade-off 수용 가능한가?

### §7.7 cand_004225 — EQ_kr, overlap=4 (최저 max_w / HHI)

- **특징**: kr 19.6% + us_growth 18.5% + dm_ex_us 16.7% + us_value 16.2% (4 자산 균형). em 9%.
- **장점**: **shortlist 내 가장 분산** (HHI 0.146, max_w 19.6%). 안정형 운용역에게 매력적.
- **부담**: Sharpe 0.5653 (8 후보 중 6위, 5건 대비 낮음). ust30 2.3% (장기 채권 비중 미미).
- **R-1D 주변 후보**:
  - by-weight: cand_004520 / cand_000524 / cand_006038.
- **판단 질문**: 가장 분산된 구조 + Sharpe 약간 양보 trade-off 수용 가능한가? 한국 19.6% 비중이 view 와 정합한가?

### §7.8 cand_007699 — EQ_em, overlap=4

- **특징**: em 23.0% + us_growth 22.6% + dm_ex_us 17.1% (신흥국+미국 성장+선진국). FI ust30 7.9% (장기채 강함).
- **장점**: em-heavy + 장기채 가능. 신흥국 view 강한 운용역에게 자연 선택지.
- **부담**: Sharpe 0.5507 (8 후보 중 8위). E[R] 9.77% (최저). us_value 13.0% (가치 비중 낮음).
- **R-1D 주변 후보**:
  - by-weight: cand_008489 / cand_000106 / cand_009404.
- **판단 질문**: 신흥국 23% over-tilt 가 view 와 정합한가? em + ust30 조합 (성장 + 안전) 의 의도가 운용 정책과 맞는가?

---

## §8. Decision Worksheet (운용역 작성용)

> 각 후보에 대해 운용역 view 를 직접 채워 final shortlist 좁히기.

| candidate_id | manager_view (positive / neutral / negative / hold) | equity_view_fit | FI_view_fit | concentration_comfort | implementation_comment | final_shortlist_include (yes / no) | reason |
|---|:---:|:---:|:---:|:---:|---|:---:|---|
| cand_008421 |   |   |   |   |   |   |   |
| cand_005995 |   |   |   |   |   |   |   |
| cand_009678 |   |   |   |   |   |   |   |
| cand_005991 |   |   |   |   |   |   |   |
| cand_000758 |   |   |   |   |   |   |   |
| cand_007510 |   |   |   |   |   |   |   |
| cand_004225 |   |   |   |   |   |   |   |
| cand_007699 |   |   |   |   |   |   |   |

작성 가이드:
- `manager_view`: 정성 종합 평가
- `equity_view_fit`: 본 후보의 equity tilt 방향이 운용역 view 와 정합한지 (정성 코멘트)
- `FI_view_fit`: FI tilt 방향 정합성 (duration / credit 측면)
- `concentration_comfort`: max_w (19.6~25.6%) 및 단일 자산 집중도 수용성
- `implementation_comment`: 실제 구현 시 product 매칭 가능성, 거래비용, 운용 한계
- `final_shortlist_include`: yes 면 다음 단계 (R-1E or downstream SAA input) 대상 후보로 보존
- `reason`: 결정 사유 한 줄

---

## §9. Selection Guidance (Selection 아님)

> **조건부 가이드만 제공. 특정 후보를 최종 선택하라고 권하지 않는다.**

| 운용역 우선순위 | 먼저 검토할 후보군 |
|---|---|
| **Sharpe 우선** (정책 비용 최소화) | cand_008421 (Sh 0.628) → cand_005995 (Sh 0.603) → cand_009678 (Sh 0.592) |
| **분산 우선** (집중도 최소화) | cand_004225 (HHI 0.146, max_w 19.6%) → cand_009678 (HHI 0.154) → cand_000758 (HHI 0.155) |
| **max_w 부담 최소화** (단일 자산 cap 정책) | cand_004225 (19.6%) → cand_007699 / cand_000758 (23.0%) → cand_005991 (23.1%) |
| **σ 최저 안정성 우선** | cand_007510 (σ 12.1%) → cand_007699 (12.3%) → cand_005995 (12.5%) |
| **E[R] 우선** (목표수익률) | cand_008421 (10.97%) ≈ cand_005991 (10.97%) → cand_009678 (10.82%) → cand_000758 (10.71%) |
| **국내 view 강함** (kr_equity tilt) | cand_005991 (kr 21.0%) → cand_004225 (kr 19.6%) → cand_000758 (kr 16.4%) |
| **신흥국 view 강함** (em tilt) | cand_007699 (em 23.0%) → cand_005995 (em 21.1%) |
| **선진국 ex-US view 강함** | cand_007510 (dm_ex_us 23.4%) → cand_000758 (dm_ex_us 16.3%) → cand_004225 (16.7%) |
| **미국 성장주 view 강함** | cand_008421 (us_growth 25.6%) → cand_005995 (25.6%) → cand_000758 (23.0%) |
| **미국 가치주 view 강함** | cand_009678 (us_value 23.6%) → cand_005991 (23.2%) |
| **HY (us_high_yield) 활용** | cand_008421 (HY 10.1%) → cand_005995 (HY 8.0%) |
| **장기채 (us_treasury_30y) 활용** | cand_007699 (ust30 7.9%) → cand_009678 (ust30 4.0%) ≈ cand_007510 (4.4%) |

---

## §10. Next Action

운용역 sign-off 후 진행 가능한 경로:

| 옵션 | 내용 | 필요 조건 |
|:---:|---|---|
| **A. Final SAA 선택** | 본 packet 8 후보 중 1건을 운용역이 최종 SAA 로 결정 | §8 Decision Worksheet 작성 → final_shortlist_include 가 `yes` 인 후보 중 1건 선택 |
| **B. R-1D similar_search 추가 탐색** | 선택 후보 1건을 기준으로 weight similarity / coordinate 검색 반복하여 대안 후보 추가 발굴 | CLI: `python -m tdf_engine.tools.search_saa_opportunity_set --mode candidate --candidate-id <cand_xxxxxx> --k 20 --out-md ...` |
| **C. R-1E dry-run 설계** | manager-selected candidate 를 downstream SAA input 으로 연결하는 wiring 설계 (production allocation 미변경, dry-run 만) | 운용역 final 선택 + R-1E spec 사용자 sign-off |

---

## §11. 본 작업의 변경 범위

| 영역 | 변경 |
|---|:---:|
| 본 final review packet (1건) | ✓ 신규 |
| scratch 분석 스크립트 + dump | ✓ scratch only (production 미반영) |
| opportunity_set JSON / R-1C PNG / cloud review / sweet_pool review / shortlist_neighbors / search demo md | ✗ 무변경 (read-only input) |
| `tdf_engine/` 코드 | ✗ 무변경 |
| `tdf_engine/config/*.yaml` | ✗ 무변경 |
| `tests/` | ✗ 무변경 |
| portfolio JSON (`portfolio_{etf,fund}_20260511.json`) | ✗ 무변경 |
| E-8 ~ E-12 산출물 | ✗ 무변경 |
| Decision Register count (14) | ✗ 무변경 |
| operating_mode | ✗ `relaxed_diagnostic` 유지 |
| 80:20 distance metric | ✗ 부활 없음 |
| 자동 final SAA 선택 | ✗ 없음 (운용역 정성 판단 입력 대기) |

---

## §12. 한 줄 요약

> **R-1B.2 → R-1C → R-1C.1 → R-1D 산출 종합. 8 manager review candidates 정량 비교
> + 후보별 review note + Decision Worksheet 제공. 자동 final SAA 선택 없음 — 운용역
> 정성 view 입력 대기. 다음 단계: A. final 선택, B. similar_search 반복 탐색, C. R-1E
> dry-run 설계 — 사용자 sign-off 후 진입.**
