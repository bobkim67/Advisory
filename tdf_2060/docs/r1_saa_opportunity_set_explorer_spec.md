# R-1A — SAA Opportunity Set Explorer (Tech Spec)

작성일: 2026-05-13. **R-track 진입 문서.** E-series (E-8~E-12) 는 진단·보고 레이어로
완료 처리하고 freeze. 본 문서는 **구현이 아니라 R-1B 구현자가 바로 읽고 작업 가능한
최소 테크스펙**이다.

> **Phase D completed register-blocker resolution only.
> This does not mean production readiness.
> The engine remains in relaxed_diagnostic mode.**

> **현재 SAA = max-Sharpe 단일 최적화 결과. corner solution (us_growth/us_value 집중,
> fixed_income 0%) 발생. 본 R-track 은 SAA 엔진을 "단일 자동 산출" 이 아닌
> "후보 집합 + 운용역 최종 선택" 패러다임으로 재정의한다. 단, R-1A 는 spec only.**

---

## 0. TL;DR

| 항목 | 결정 |
|---|---|
| **Scope** | spec 작성만. 구현 / config 변경 / output 생성 / test 실행 **금지**. |
| **출력 (R-1A)** | 본 문서 1건. |
| **다음 단계 (R-1B)** | `tdf_engine/optimization/opportunity_set.py` + CLI + tests + JSON dump |
| **방향성** | Broad candidate generation → multi-criteria scoring → user selection. |
| **MVO 위상** | reference / score dimension. **hard filter 아님. final answer 아님.** |
| **Production 영향** | 0. 기존 SAA / TAA / product selection / portfolio builder 미변경. |

---

## 1. Purpose

SAA 엔진은 **최적 포트폴리오 1개를 자동 선택하지 않는다.**

- 운용 가능한 후보 포트폴리오 집합 (Opportunity Set) 을 생성한다.
- 각 후보를 risk / return / diversification / policy fit / implementation feasibility
  복수 dimension 에서 평가한다.
- 운용역이 risk-return scatter 와 candidate list 를 보고 **최종 SAA 를 선택**한다.

핵심 명제:
> **MVO efficient frontier 위의 포트폴리오만이 "올바른" SAA 가 아니다.**
> Frontier 밖에 있어도 drawdown / diversification / policy fit / implementation
> feasibility 측면에서 더 운용 가능한 후보가 있을 수 있다.

본 엔진은 운용역의 의사결정을 **대체하지 않고 보조**한다.

---

## 2. Problem Diagnosis

현재 (Phase E-12 시점) SAA 산출 구조:

```
CMA (μ/σ/ρ) → MVO max_sharpe → selected_matches_max_sharpe=True → SAA 확정
```

본 문서는 두 레이어를 **명시적으로 분리**한다:

| 레이어 | 정의 | 비고 |
|---|---|---|
| **MVO SAA weights** (= "Current SAA") | MVO max_sharpe 산출 직후의 자산별 weight | E-9 `selected` 와 동일. asset-level. |
| **Final implemented asset weights** | TAA overlay + projection (long-only / bucket bound) + product selection + drift clipping 적용 후 자산별 합산 weight | `portfolio.asset_allocation[*].weight`. equity / fixed_income bucket 합산은 여기서. |

관찰된 **concentrated corner solution** (relaxed_diagnostic baseline, 2026-05-11):

**(a) Current SAA (MVO max_sharpe 결과)**
- us_growth_equity / us_value_equity 로의 집중 (MVO 자체의 corner solution, 운영 cap/band 와 무관)
- kr_treasury_10y / us_treasury_30y MVO weight ≈ 0%

**(b) Final implemented asset weights (TAA + projection + selection 적용 후)**
- equity bucket 82.32% / fixed_income bucket 17.68% (bucket bound 내, fixed_income 내부는 여전히 corner)
- final 자산별 weight 의 0% / near-bound 항목은 운용역 결정 register 항목 D-01 / D-02 와 연결

> **주의:** 위 (a) 의 "집중" 은 운영 cap / band / threshold 가 실제로 적용된 결과가 아니다.
> 현 SAA 단계에서는 운영 cap / band / threshold 가 강제되지 않으며, MVO 가 수학적으로
> 도출한 corner solution 그 자체이다. final implemented weights 도 어떤 cap 적용 결과가
> 아니라 TAA overlay + projection + product selection 의 합성 결과이다.

이는 다음을 의미한다:

1. **수학적으로는 MVO 결과**. 입력 (μ/σ/ρ) 과 objective (max Sharpe) 에 충실.
2. **운용 정책 포트폴리오로 직접 사용 어려움**. 운용역 정성 판단 / 분산 요구 / 정책 band 와 괴리.
3. **목표수익률 단일 박기** (max_return_under_risk_limit, utility 등) 도 정책 결정 부담.

해결 방향:

- MVO SAA 결과는 **하나의 reference point** 로 유지하되 (= `ref_max_sharpe`, §6),
- **bucket-constrained candidate generation** 으로 80:20 정책을 만족하는 후보 풀 생성 (§4),
- **multi-criteria scoring** 으로 운용역이 intra-bucket trade-off 를 비교한 뒤 선택.

> **[R-1B.2 update — 2026-05-13]** 사용자 결정: **80:20 은 평가 지표가 아니라 반드시 만족해야 하는 hard constraint** 이다.
> 따라서 candidate generation 자체가 equity 합 = 0.80, fixed_income 합 = 0.20 을 강제하며,
> 후보 비교 시 80:20 거리 metric (`bucket_distance_from_80_20`,
> `full_weight_distance_from_80_20_equal_bucket_reference`) 은 **제거**한다.
> 후보 간 차이는 **bucket 내부 분배** (intra-bucket weights) 에만 존재한다.
> 다만 `ref_max_sharpe` (= Current SAA telemetry) 는 unconstrained MVO 결과이므로
> 80:20 을 만족하지 않을 수 있다 — reference 용도로만 보존하며 sampled candidate pool 과 별개.

---

## 3. Design Principle

| 순서 | 단계 | 원칙 |
|:---:|---|---|
| 1 | Broad candidate generation | 적은 가정으로 넓게 샘플링 |
| 2 | Multi-model / multi-criteria scoring | MVO efficiency 는 score 의 **한 차원** |
| 3 | User selection | 엔진은 추천하지 않음. 운용역이 결정. |

추가 원칙:

- **MVO efficiency 는 hard filter 가 아니라 evaluation metric.**
- **재현성 보장** — `random_seed` 고정. Phase E-6.2 의 deterministic ordering 정책과 정합.
- **기존 코어 미변경** — Phase C.4+ "코어 로직 변경 금지" 정책 유지.
- **read-only telemetry pattern** — E-6.2 / E-11A 와 동일하게 부가 산출물로 dump.

---

## 4. Candidate Generation (R-1B.2: bucket-constrained)

R-1B 초기 구현은 **최소 복잡도** 로 시작. 80:20 은 hard constraint (§2 update).

### 4.1 Bucket-constrained Sampling

| 항목 | 값 (default) |
|---|---|
| 방법 | **Bucket-constrained Dirichlet** — equity / fixed_income 두 simplex 를 각각 샘플링 후 scaling |
| equity sampling | `eq_weights = rng.dirichlet([1.0] * n_eq) * 0.80` (n_eq=5) |
| fixed_income sampling | `fi_weights = rng.dirichlet([1.0] * n_fi) * 0.20` (n_fi=4) |
| total weight | concat → 9-vector. equity 합 = 0.80, FI 합 = 0.20, total = 1.0 |
| `n_candidates` | **10,000** (default) |
| `random_seed` | **42** (default). deterministic 보장. 동일 seed 에서 equity / FI 샘플링 순서도 deterministic. |
| weight constraint | long-only, equity 합 = 0.80, FI 합 = 0.20 (모두 hard) |

의사 코드:

```python
eq_keys = [k for k in asset_keys if bucket_map[k] == "equity"]        # 5 assets
fi_keys = [k for k in asset_keys if bucket_map[k] == "fixed_income"]  # 4 assets

rng = np.random.default_rng(random_seed)
eq_samples = rng.dirichlet([1.0] * len(eq_keys), size=n_candidates)   # each row sums to 1
fi_samples = rng.dirichlet([1.0] * len(fi_keys), size=n_candidates)

# normalize within bucket (ULP safety) then scale by bucket target
for idx in range(n_candidates):
    eq_row = eq_samples[idx] / eq_samples[idx].sum() * 0.80
    fi_row = fi_samples[idx] / fi_samples[idx].sum() * 0.20
    weights = {k: eq_row[i] for i, k in enumerate(eq_keys)}
    weights.update({k: fi_row[i] for i, k in enumerate(fi_keys)})
```

각 후보는 **equity_weight ≡ 0.80, fixed_income_weight ≡ 0.20** (numerical noise 무시) 가
**구조적으로 보장**된다. 80:20 fit 검증은 별도 metric 없이 sampling 자체에서 보장.

### 4.2 Optional Filters (config, default disabled — R-1B.2 에서도 모두 미활성)

```yaml
opportunity_set:
  max_single_asset_weight: null         # e.g. 0.30 — 활성 시 후보 reject 또는 rejection-sampling
  min_nonzero_assets: null              # e.g. 5 — 활성 시 sparse 후보 reject
```

> bucket-constrained sampling 이 도입되며 기존의 `equity_range` / `fixed_income_range`
> filter 는 의미가 사라진다 (bucket 합이 항상 0.80 / 0.20). spec 에서 제거.

### 4.3 Candidate Pool Composition

```
sampled (bucket-constrained):   n_candidates 건 (default 10,000)
reference_points:               추가 (§6, R-1B-lite scope = 2 건)
────────────────────────────────────────────────────────────────
total candidates:               n_candidates + |reference_points|
```

Reference point (특히 `ref_max_sharpe`) 는 bucket constraint 를 **만족하지 않을 수 있다**
(unconstrained MVO 결과). 별도 row 로 추가하되 sampled pool 과 비교 시 이 점을 명시.

---

## 5. Candidate Metrics

각 후보 1건에 대해 계산:

| 필드 | 정의 | 비고 |
|---|---|---|
| `candidate_id` | str (e.g. `cand_000001`) | reference 는 `ref_max_sharpe` 등 |
| `weights` | dict[asset_key, float] | 9 asset, sum=1.0 |
| `expected_return` | `w · μ` | CMA 의 μ 사용 (annual) |
| `volatility` | `sqrt(w · Σ · w)` | CMA 의 Σ 사용 (annual) |
| `sharpe` | `(E[R] - rf) / σ` | rf 는 기존 CMA `risk_free_rate` 사용 |
| `equity_weight` | sum of equity bucket | sampled candidate 는 **≡ 0.80** (hard). reference 는 다를 수 있음. |
| `fixed_income_weight` | sum of FI bucket | sampled candidate 는 **≡ 0.20** (hard). reference 는 다를 수 있음. |
| `max_asset_weight` | `max(w)` | concentration 신호 (asset-level) |
| `nonzero_asset_count` | count where `w > eps` (eps=1e-4) | diversification 신호 |
| `concentration_hhi` | HHI = `sum(w^2)` | 0~1, 작을수록 분산. **전체 9-vector 기준**. |
| `equity_intra_hhi` | sum((w_i / equity_weight)^2 for equity i) | **bucket 내부** equity 분산. equity_weight=0 인 reference 의 경우 None. |
| `fixed_income_intra_hhi` | sum((w_j / fixed_income_weight)^2 for FI j) | bucket 내부 FI 분산. FI_weight=0 인 reference 의 경우 None. |
| `equity_max_asset_weight` | max(w_i) over equity i (raw, not renormalized) | equity bucket 의 최대 자산 비중 |
| `fixed_income_max_asset_weight` | max(w_j) over FI j (raw, not renormalized) | FI bucket 의 최대 자산 비중 |
| `mvo_efficiency_score` | `frontier_efficiency_gap` = `frontier_expected_return_at_candidate_volatility - candidate_expected_return` | same-volatility 기준 frontier 와 candidate 의 E[R] 차이. **양수 = frontier 아래, 음수 ≈ 0 = frontier 위/근접**. E-9 31 grid 위에서 candidate volatility 에 대한 frontier E[R] 은 **선형 interpolation** 사용 (extrapolation 시 boundary clip + `feasibility_status = degenerate` 마킹 가능). |
| `feasibility_status` | enum: `feasible` / `violates_filter` / `degenerate` | filter disabled 시 기본 `feasible`. frontier extrapolation 시 `degenerate`. |

> **제거된 metric (R-1B.2):** `bucket_distance_from_80_20`,
> `full_weight_distance_from_80_20_equal_bucket_reference` — 80:20 이 hard constraint
> 가 되며 모든 sampled candidate 가 자동 만족하므로 평가 의미가 사라짐.

**제외 (R-1A 범위 외, 명시적 backlog):**

- CVaR / max drawdown / tail risk
- Black-Litterman posterior
- robust optimization (uncertainty set)
- regime-conditioned expected return
- liquidity / implementation cost score

---

## 6. Reference Points

다음 후보는 **sampling 과 무관하게 항상 포함**:

| id | 정의 | source | 80:20 만족? |
|---|---|---|:---:|
| `ref_max_sharpe` | Current SAA = MVO max-Sharpe 직후의 asset-level weights (= E-9 selected) | **`diagnostics.saa_diagnostics.saa_weights`** (E-6.2 T-6 direct telemetry). final implemented weights (`portfolio.asset_allocation[*].weight`) 와 **다름** — final 은 TAA overlay + projection + product selection 후 합성 결과이며 ref_max_sharpe source 로 **사용 금지**. | **✗ (unconstrained MVO; e62 baseline 기준 eq=100% / fi=0%)** |
| `ref_min_vol` | min-volatility portfolio (unconstrained) | E-9 frontier 의 min_vol endpoint. **R-1B-lite 범위 외 (R-1C+).** | (R-1C+) |
| `ref_equal_weight` | `w_i = 1/9` for all | 합성. **R-1B-lite 범위 외 (R-1C+).** | ✗ (eq=5/9, fi=4/9) |
| **`ref_80_20_equal_intra_bucket`** | bucket 내부 균등 배분: equity 80% / 5 자산 = 16% each, FI 20% / 4 자산 = 5% each | 합성 (asset universe 순서) | ✓ |
| `ref_user_selected` (optional) | placeholder for user-chosen point | **R-1B-lite 범위 외 (R-1C+).** |

`ref_80_20_equal_intra_bucket` 의 intra-bucket 분배 default:
- equity 80%: 5 asset 균등 (16% each)
- fixed_income 20%: 4 asset 균등 (5% each)
- 향후 변경 시 config 노출.

본 reference 는 모든 sampled candidate 와 **동일한 bucket 합** (80/20) 을 갖되,
intra-bucket 만 균등이라는 **단일 특수 case**. 후보 간 비교의 anchor 점.

> **R-1B-lite scope (R-1B.2 update):** R-1B-lite implements only `ref_max_sharpe` and
> `ref_80_20_equal_intra_bucket`. `ref_min_vol`, `ref_equal_weight`, and
> `ref_user_selected` are deferred to R-1C or later.

---

## 7. Similar Candidate Search

사용자가 risk-return 평면에서 한 점 `(target_return, target_volatility)` 을 선택했을 때,
가장 유사한 후보 k 건을 반환.

### 7.1 인터페이스

```python
find_similar_candidates(
    candidates: list[Candidate],
    target_return: float,
    target_volatility: float,
    k: int = 20,
) -> list[Candidate]
```

### 7.2 거리 계산

```
d_i = sqrt( ((E[R]_i - target_return) / σ_return_norm)^2
          + ((σ_i - target_volatility)  / σ_vol_norm)^2 )
```

`σ_return_norm`, `σ_vol_norm` 는 candidate pool 전체의 std (normalization).

### 7.3 Tie-breakers

같은 거리 (within 1e-6) 후보 정렬 (R-1B.2 update):

1. lower `concentration_hhi` (전체 9-vector 분산)
2. lower `equity_intra_hhi` (equity bucket 내부 분산)
3. lower `fixed_income_intra_hhi` (FI bucket 내부 분산)
4. `feasibility_status == feasible` 우선
5. lexicographic on `candidate_id` (final deterministic)

> bucket_distance / full_weight_distance tie-breaker 는 모든 sampled candidate 가
> 동일한 bucket 합 (80/20) 을 가지므로 의미가 사라져 제거. similar_search 자체는
> R-1C+ 구현 항목.

---

## 8. Output Schema

JSON 구조 (제안, R-1B 에서 확정):

```yaml
saa_opportunity_set:
  meta:
    schema_version: "r1.0"
    generated_at: ISO8601
    portfolio_type: "etf" | "fund"
    as_of_run: "YYYYMMDD"
    operating_mode: "relaxed_diagnostic"
    upstream_portfolio_json: <path>
    random_seed: 42

  inputs:
    cma_source: "saa_diagnostics.cma"        # E-6.2 telemetry
    mu: dict[asset_key, float]
    sigma: dict[asset_key, float]
    rho: dict[(asset_a, asset_b), float]
    covariance: dict[(asset_a, asset_b), float]
    risk_free_rate: float

  generation:
    method: "dirichlet_bucket_constrained"              # R-1B.2
    n_candidates: 10000
    alpha_equity: [1.0, 1.0, 1.0, 1.0, 1.0]             # 5 equity assets
    alpha_fixed_income: [1.0, 1.0, 1.0, 1.0]            # 4 FI assets
    equity_bucket_total: 0.80                           # hard
    fixed_income_bucket_total: 0.20                     # hard

  constraints:
    long_only: true
    full_investment: true                                # sum=1
    equity_bucket_total_fixed: 0.80                      # R-1B.2 hard
    fixed_income_bucket_total_fixed: 0.20                # R-1B.2 hard
    optional_filters_enabled:
      max_single_asset_weight: false
      min_nonzero_assets: false

  candidates:
    - candidate_id: "cand_000001"
      weights: {...}                                                 # 9 asset, sum=1; eq sum=0.80, fi sum=0.20
      expected_return: ...
      volatility: ...
      sharpe: ...
      equity_weight: ...                                             # ≡ 0.80 for sampled
      fixed_income_weight: ...                                       # ≡ 0.20 for sampled
      max_asset_weight: ...
      nonzero_asset_count: ...
      concentration_hhi: ...                                         # full 9-vector HHI
      equity_intra_hhi: ...                                          # sum((w_i / 0.80)^2 for equity)
      fixed_income_intra_hhi: ...                                    # sum((w_j / 0.20)^2 for FI)
      equity_max_asset_weight: ...                                   # max(w_i) raw, over equity
      fixed_income_max_asset_weight: ...                             # max(w_j) raw, over FI
      mvo_efficiency_score: ...                                      # frontier gap (same-σ E[R] diff, interpolated)
      feasibility_status: "feasible"
    # ... (10000 + reference_points)

  reference_points:
    # R-1B-lite 범위: 아래 2개만 dump.
    # ref_min_vol / ref_equal_weight / ref_user_selected 는 R-1C+ 에서 추가.
    ref_max_sharpe:                {candidate_id: "ref_max_sharpe", ...}                # source = diagnostics.saa_diagnostics.saa_weights; bucket constraint 위반 가능
    ref_80_20_equal_intra_bucket:  {candidate_id: "ref_80_20_equal_intra_bucket", ...}  # bucket 내부 균등 reference

  # similar_search 는 R-1C+ 에서 구현.
  # R-1B-lite 에서는 본 키 자체를 생략하거나 빈 placeholder {last_query: null, last_result: []} 만 dump (사용자 결정).

  diagnostics:
    pool_size_total: <int>                 # = n_candidates + |reference_points| (default 10000 + 2 = 10002)
    feasible_count: <int>                  # candidates with feasibility_status == "feasible"
    rejected_by_filter: <dict[str, int]>   # filter_name → reject count (R-1B-lite: all 0; optional filter disabled)
    rejected_by_degeneracy: <int>          # frontier extrapolation / numerical degenerate count
    frontier_sample_size: 31               # E-9 grid 재사용 (mvo_efficiency_score frontier interpolation 용)
    determinism_check:
      seed: 42
      first_5_candidate_weight_strings: [...]   # 재현성 검증용
    # ── invariant (실제 산출에서 항상 성립해야 함) ──────────────────────
    # pool_size_total == feasible_count + rejected_by_degeneracy + sum(rejected_by_filter.values())
    #
    # 예) R-1B.2 시점 ETF/Fund 산출 (n=10000, seed=42, E-9 frontier 31 grid):
    #   pool_size_total       = 10002
    #   feasible_count        = 9842
    #   rejected_by_filter    = {}
    #   rejected_by_degeneracy= 160
    #   → 9842 + 160 + 0 = 10002 ✓
    # 수치는 sampling seed / n / frontier grid 변경 시 달라질 수 있음 — invariant 만 enforce.
```

---

## 9. Visualization Requirement (R-1C or later; not in R-1B-lite)

R-1A 에서는 **그리지 않는다.** R-1B 진입 시 다음 방향:

| 요소 | 값 |
|---|---|
| x-axis | volatility |
| y-axis | expected_return |
| color | sharpe 또는 equity_weight (toggle) |
| size | 작은 dot (n=10k 라 alpha 낮게) |
| marker — reference | star / cross / triangle, 색 구분 |
| highlight — similar_search 결과 | 굵은 outline + table 동행 |
| 산출 | static PNG (matplotlib) — 기존 reporting pattern 과 정합 |
| HTML 산출 | E-12 packet 과 호환 가능한 형태 (단, 본 turn 비결정) |

차트 caption 에 강제 표기:

> "These are candidate portfolios for diagnostic review.
> Final SAA selection requires manager judgment."

cap / threshold / band 선 **금지** (E-series 와 동일 정책).

---

## 10. Non-goals

본 R-1A / R-1B 범위에서 **명시적으로 하지 않는 것**:

```
✗ production SAA 교체
✗ TAA 변경
✗ product selection 변경
✗ review packet / PDF / report polish (E-13 / E-14 / E-15)
✗ RL / MPC / HMM 구현
✗ policy band 확정
✗ Black-Litterman / robust optimization / CVaR 구현
✗ regime-conditioned MVO 구현
✗ Decision Register count (14) 변경
✗ operating_mode = "production" 전환
✗ allocation 결과 (asset weights / product weights) 영향
✗ "optimized TAA" / "regime-conditioned MVO" 라벨 사용
✗ tests/_phase_e62_baseline.json sha256 변경
```

---

## 10.1 R-1B-lite Scope (first implementation)

R-1B 진입은 **lite scope** 로 출발한다. 본 lite scope 만으로 1 turn 안에 마무리 가능하도록
범위를 자른다. R-1B-full 또는 R-1C 는 lite 산출물 검토 후 별도 sign-off.

**R-1B-lite (R-1B.2 corrected) 에서 구현하는 것:**

```
✓ Bucket-constrained Dirichlet candidate generation (seed=42, n=10000)
   - equity 5-asset Dirichlet × 0.80
   - fixed_income 4-asset Dirichlet × 0.20
   - equity_weight ≡ 0.80, fixed_income_weight ≡ 0.20 hard
✓ Core metrics:
    candidate_id / weights /
    expected_return / volatility / sharpe /
    equity_weight / fixed_income_weight /
    max_asset_weight / nonzero_asset_count /
    concentration_hhi /
    equity_intra_hhi / fixed_income_intra_hhi /
    equity_max_asset_weight / fixed_income_max_asset_weight /
    mvo_efficiency_score (frontier_efficiency_gap) /
    feasibility_status
✓ Reference points 2종:
    ref_max_sharpe                  (current direct SAA / E-9 selected; bucket 위반 가능)
    ref_80_20_equal_intra_bucket    (eq 80% 균등 + FI 20% 균등 합성 anchor)
✓ JSON dump (etf / fund) — §8 schema
✓ Summary markdown (etf / fund)
✓ Tests (determinism / bucket=0.80/0.20 hard / non-negative / metric consistency /
         reference / mutation / metric absence 등)
```

**R-1B-lite 에서 defer 하는 것 (R-1C 또는 후속):**

```
✗ ref_min_vol (bucket-constrained version 도 R-1C 에서 결정)
✗ ref_equal_weight (9-자산 균등 — bucket 위반)
✗ ref_user_selected placeholder
✗ scatterplot PNG
✗ similar_search last_query / last_result dump (인터페이스 자체도 R-1C)
✗ clustering / Pareto filtering
✗ HTML / report packaging
✗ optional filter 활성화 (max_single_asset_weight / min_nonzero_assets — 모두 disabled 유지)
✗ bucket-distance / full-weight-distance metric — R-1B.2 에서 영구 제거
```

`similar_search` 키는 R-1B-lite 에서 **dump 하지 않는다** (R-1C 진입 시 추가).

---

## 11. R-1B Implementation Plan

R-1A 승인 후 R-1B 진입. 구현 후보 파일:

```
tdf_engine/optimization/
└── opportunity_set.py                 (Dirichlet sampling + metrics; similar search deferred to R-1C)

tdf_engine/tools/
└── build_saa_opportunity_set.py       (CLI: --portfolio-json --as-of --out-dir [--n 10000] [--seed 42])

tests/
└── test_r1_saa_opportunity_set.py     (R-1B-lite test scope, R-1B.2 corrected:
                                        - determinism (seed=42)
                                        - sum-to-1 (within tolerance)
                                        - non-negative weights
                                        - bucket constraint: equity == 0.80 hard
                                        - bucket constraint: fixed_income == 0.20 hard
                                        - intra-bucket HHI consistency
                                        - metric correctness (μ, Σ 정합)
                                        - ref_max_sharpe inclusion + source 검증
                                        - ref_80_20_equal_intra_bucket inclusion + sum + intra 분배
                                        - removed metric absence: bucket_distance_from_80_20
                                        - removed metric absence: full_weight_distance_from_80_20_equal_bucket_reference
                                        - schema shape (2 reference, similar_search 키 없음)
                                        - summary md creation
                                        - no mutation of source portfolio JSON)
```

예상 산출 디렉토리 (관용 경로, E-7~E-12 pattern 정합):

```
out/db_review_relaxed_e62/saa_opportunity_set/20260513/
├── saa_opportunity_set_etf_20260513.json
├── saa_opportunity_set_fund_20260513.json
├── saa_opportunity_set_summary_20260513.md
└── (R-1B 후속) saa_opportunity_set_{etf,fund}_20260513.png   ← optional, separate turn
```

R-1B 작업 분량 예상:

| 작업 | 예상 |
|---|---|
| opportunity_set.py 구현 | 1.0~1.5h |
| CLI + summary md | 0.5h |
| tests 10건 | 1.0h |
| ETF/Fund dump + sanity | 0.5h |
| **합계** | **~3h (1 turn)** |

차트 (R-1B 또는 별도 R-1C) 는 +0.5~1h.

---

## 12. Hard Requirements (R-1A turn)

| 영역 | 변경 |
|---|:---:|
| 본 문서 신규 작성 | ✓ |
| `tdf_engine/` 코드 | ✗ |
| `tdf_engine/config/*.yaml` | ✗ |
| `tests/` | ✗ (실행 불필요) |
| `out/` 산출물 | ✗ |
| `docs/investment_decision_register.md` | ✗ |
| `docs/phase_e_current_handoff.md` | ✗ (R-1B 진입 시점에서 갱신 검토) |
| Decision Register total count (14) | ✗ |
| E-8~E-12 산출물 | ✗ |
| operating_mode | ✗ (relaxed_diagnostic 유지) |

---

## 13. Backlog (R-1A 시점 분리 보관)

본 spec 에서 **명시적으로 미루는 항목** (R-2+ 후보):

| # | 항목 | 비고 |
|:---:|---|---|
| B-1 | Black-Litterman posterior μ | view + confidence 정책 결정 필요 |
| B-2 | robust optimization (uncertainty set) | ellipsoidal / box, computation cost 검토 |
| B-3 | CVaR / tail risk metric | return distribution 가정 필요 (parametric vs historical) |
| B-4 | MPC (model predictive control) overlay | rebalancing horizon / cost model |
| B-5 | RL overlay (Q / actor-critic) | reward 정의 / data sample 부족 위험 |
| B-6 | regime-conditioned MVO (true) | E-7 missing_data `taa.regime_conditioned_assumptions` 와 연결 |
| B-7 | HMM regime classifier (current = ECI rule-based) | E-8 regime clock 데이터와 호환 |
| B-8 | implementation cost / liquidity score | ETF AUM / spread / 운용사 capability 추정 필요 |
| B-9 | dynamic candidate filter | 운용역 정성 input → filter (manager judgment loop) |
| B-10 | confidence-scaled tilt | rule-based TAA → confidence weight 도입 (별도 phase) |

위 항목은 모두 **R-1A/B 범위 외**. 별도 spec 으로 분리 후 사용자 sign-off 시 진입.

---

## 14. 본 문서 수용 기준 (R-1A acceptance)

| 기준 | 검증 |
|---|---|
| 본 문서가 3~5페이지 수준인가 | 본 md ≈ 4 페이지 (markdown render 기준) |
| R-1B 구현자가 바로 작업 가능한가 | §4 / §5 / §6 / §7 / §8 / §11 만 읽으면 구현 가능 |
| 심층 리서치 / 미래 모델 논의 분리되었는가 | §13 Backlog 로 격리 |
| 코드/config/output/test 변경 0 | §12 Hard Requirements |
| E-series freeze 정책과 충돌 없는가 | §10 Non-goals 에 명시 |
| Phase E-12 기존 산출물 변경 없는가 | §10 / §12 |

---

## 15. 한 줄 요약

> **R-1B.2 completed.** Bucket-constrained Dirichlet candidate generator (10k candidates +
> 2 reference points) 구현 + tests + ETF/Fund diagnostic outputs 생성 완료.
> 80:20 은 hard constraint — 모든 sampled candidate 가 equity 80% / fixed_income 20% 를 만족.
> Core metrics = sharpe / HHI (full + intra-bucket per side) / max_w (full + intra-bucket per side) /
> mvo_efficiency_score / feasibility_status.
> 2 reference points: `ref_max_sharpe` (Current SAA, bucket 위반 가능),
> `ref_80_20_equal_intra_bucket` (intra-bucket 균등 anchor).
> similar search / scatterplot / extra reference points are deferred to R-1C+.
> **production SAA / TAA / product selection / config / Decision Register / E-series baseline
> outputs remain unchanged.** R-1C 진입은 사용자 sign-off 후.
