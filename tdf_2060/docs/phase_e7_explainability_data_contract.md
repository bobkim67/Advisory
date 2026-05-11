# Phase E-7 — Explainability Data Contract

작성일: 2026-05-11. **포트폴리오 의사결정 과정 (Regime → SAA → TAA → Product Selection) 을
설명 가능하게 만드는 데이터 계약.** 본 문서는 schema 정의 + 각 필드의 source / availability /
missing 처리 정책을 포함한다.

> **Phase D completed register-blocker resolution only.**
> **This does not mean production readiness.**
> **The engine remains in relaxed_diagnostic mode.**

---

## 0. TL;DR

| 항목 | 결정 |
|---|---|
| **Scope** | 데이터 계약 + dump 구조. **차트 미생성**. |
| **출력** | `out/db_review_relaxed_e62/explainability/<as_of>/explainability_{etf,fund}_<as_of>.json` |
| **모듈** | `tdf_engine/reporting/explainability.py` (extractor, read-only) |
| **CLI** | `tdf_engine/tools/build_explainability.py` |
| **입력** | (1) `portfolio_*.json` (필수) + (2) `tdf_engine/config/taa_policy.yaml` (regime → tilt 매핑) + (3) `etf_list` / `fund_list` 원본 (ticker lookup) |
| **변경** | allocation/optimizer/TAA/selection/config 무변경. read-only diagnostics dump only. |
| **SAA inferred** | 절대 금지 — `saa_diagnostics.saa_weights` (E-6.2 T-6) 직접 telemetry 만 사용. |

---

## 1. Top-level structure

```
portfolio_explainability
├── meta
├── regime_explainability
├── saa_explainability
├── taa_explainability
├── product_selection_explainability
└── report_ready_summary
```

---

## 2. `meta`

```yaml
meta:
  schema_version: "e7.1"
  generated_at: ISO8601
  portfolio_type: "etf" | "fund"
  portfolio_as_of_date: "YYYY-MM-DD"   # portfolio.as_of_date
  portfolio_as_of_run: "YYYYMMDD"      # portfolio.as_of (build 일자)
  source_type: "db" | "file"
  operating_mode: "relaxed_diagnostic"
  source_files:
    portfolio_json: <path>
    taa_policy_yaml: <path>
    product_list: <path or null>
  upstream_run:
    build_portfolio_version: "phase-e62 (telemetry+determinism patch)"
    determinism_patch_applied: true
```

| 필드 | source | availability |
|---|---|:---:|
| schema_version | hard-coded | available |
| portfolio_as_of_date / portfolio_as_of_run | portfolio.{as_of_date, as_of} | available |
| source_type / operating_mode | portfolio.{source_type, …} + tdf_2060.yaml | available |
| source_files | CLI args | available |
| upstream_run.build_portfolio_version | hard-coded label | available |

---

## 3. `regime_explainability`

```yaml
regime_explainability:
  current:
    portfolio_as_of_date: "YYYY-MM-DD"
    regime_signal_as_of_date: "YYYY-MM-DD"   # regime.as_of (월말)
    region: "G7"
    placement: float
    velocity: float
    regime: 1..4
    regime_label: "Expansion / Acceleration" 등
    quadrant_label: "Expansion / Acceleration"
  history:
    observations:
      - as_of: "YYYY-MM-DD"
        placement: float
        velocity: float
        regime: int
        regime_label: str
    count: int
    start_date: "YYYY-MM-DD"
    end_date: "YYYY-MM-DD"
    expected_full_history_months: 24
    actual_history_months: int
    full_history_available: bool
  transition_summary:
    previous_regime: int | null
    current_regime: int
    changed: bool
    direction: "regime_change" | "stable" | "unknown"
    comment: str
  asset_class_preference:
    by_asset:
      <asset_key>:
        preference: "overweight" | "neutral" | "underweight"
        tilt_pp: float                # taa_policy.yaml asset_tilts (×100)
        reason: str
        source: "rule_based"
```

### 데이터 출처 / 가용성

| 필드 | source | availability |
|---|---|:---:|
| current.* | `portfolio.diagnostics.regime` (E-6.2 그대로) | available |
| history.observations | `portfolio.diagnostics.regime.history` (latest 5) | **partial** — 5건만, 24개월 권장 |
| history.expected_full_history_months | hard-coded 24 | available |
| history.full_history_available | `len(history) >= expected` | computable |
| transition_summary | derive from history (last 2 obs 비교) | computable when len>=2 |
| asset_class_preference | `taa_policy.yaml::regime_tilts.regime_<n>.asset_tilts` | available (read-only) |

> **현재 한계 명시**: history 5 obs 만 (E-6.2 telemetry 한도). 24개월 timeline 은 후속
> telemetry enhancement 또는 sidecar regime backfill 필요. `missing_data` 에 명시.

---

## 4. `saa_explainability`

```yaml
saa_explainability:
  cma_inputs:
    expected_returns:        {asset_key: float}    # E-6.2 T-1
    volatilities:            {asset_key: float}    # E-6.2 T-2
    correlation_matrix:      {k: {k: float}}       # E-6.2 T-3
    covariance_matrix:       {k: {k: float}}       # E-6.2 T-4
  optimization:
    objective: "max_sharpe"
    objective_params: {rf: float}
    constraints:                                   # ConstraintSet read-only
      - constraint_id: str
        description: str
        lower_bound: float | null
        upper_bound: float | null
        applied: bool
        binding: "unknown"                         # 본 phase 미평가
    universe:
      asset_keys: [str]
      asset_names: [str]                           # cma.name_by_key
      ticker_by_key: {asset_key: str}
    selected_saa_weights:    {asset_key: float}    # E-6.2 T-6 (direct, NOT inferred)
    selected_point:
      expected_return: float                       # w · μ
      volatility:      float                       # sqrt(w' Σ w)
      sharpe:          float                       # (μ_p - rf) / σ_p
      utility_score:   null                        # 미사용 (max_sharpe)
    solver:
      status: str                                  # saa_diagnostics.solver_status
      message: str
      n_iter: int
      weight_sum: float
  efficient_frontier:                              # 본 phase 미산출
    points: []
    selected_point_index: null
    min_vol_point_index: null
    max_sharpe_point_index: null
    available: false
    deferred_to: "E-9"
  risk_contribution:                               # 본 phase 산출 (read-only)
    by_asset:
      <asset_key>:
        weight: float
        marginal_risk_contribution: float          # (Σw)_i
        total_risk_contribution: float             # w_i · (Σw)_i
        percent_risk_contribution: float           # 합 = 1.0
    portfolio_volatility: float                    # sqrt(w' Σ w)
    available: true
  diagnostics:
    warnings: [str]
    missing_data:
      - field: "efficient_frontier"
        impact: "Selected SAA point 의 frontier 위치를 시각화 불가"
        recommended_next_step: "E-9 phase: scipy.optimize 로 σ-grid scan"
```

### 데이터 출처 / 가용성

| 필드 | source | availability |
|---|---|:---:|
| cma_inputs.* | `saa_diagnostics.cma.*` (E-6.2 T-1~T-4) | available |
| optimization.objective / solver.* | `saa_diagnostics.{objective_name, solver_status, …}` | available |
| optimization.universe.* | `saa_diagnostics.cma.{asset_keys, name_by_key, ticker_by_key}` | available |
| optimization.selected_saa_weights | `saa_diagnostics.saa_weights` (E-6.2 T-6, direct) | available |
| optimization.selected_point.{return,vol,sharpe} | computed: `w · μ`, `sqrt(w'Σw)`, sharpe | computable |
| optimization.constraints | `tdf_2060.yaml::weight_bounds` + `optimization_constraints.yaml::{equity_sum,fixed_income_sum}` (read-only) — 단순 enumeration | computable, **binding 평가는 미수행** |
| efficient_frontier | — | **DEFERRED to E-9** |
| risk_contribution.* | computed: `mrc_i = (Σw)_i`, `trc_i = w_i · mrc_i`, `pct_i = trc_i / σ_p²` | computable |

---

## 5. `taa_explainability`

```yaml
taa_explainability:
  current_regime:
    regime: int
    regime_label: str
    placement: float
    velocity: float
  regime_conditioned_assumptions:                  # 현재 시스템 미보유
    by_asset: {}
    available: false
    note: "TAA = prototype heuristic rule overlay (not regime-MVO). regime-conditioned μ/σ는 미구현."
  tilt_policy:
    policy_id: "taa_policy.yaml::regime_tilts"
    policy_version: "phase-d frozen"
    method: "rule_based"
    description: "regime → asset_tilts (%p) lookup. SAA 에 ±%p 가산. tilt_sum=0 정합."
    per_asset_max_tilt: 1.0
    bucket_tilts_active: false                     # metadata only
  tilt_decisions:
    by_asset:
      <asset_key>:
        saa_weight: float                          # direct telemetry
        tilt: float                                # taa_target − saa
        taa_target_weight: float                   # taa_feasibility.target_weights_before_projection
        direction: "overweight" | "underweight" | "neutral"
        rationale: str                             # "Regime <n> → asset_tilts.<asset_key> = +Xpp"
        source: "rule_based"
        confidence: null                           # 미산출 (heuristic)
  taa_portfolio_summary:
    expected_return_before_tilt: float             # w_saa · μ
    volatility_before_tilt:      float             # sqrt(w_saa' Σ w_saa)
    sharpe_before_tilt:          float
    expected_return_after_tilt:  float             # w_taa_target · μ
    volatility_after_tilt:       float
    sharpe_after_tilt:           float
    improvement_summary:
      delta_expected_return: float
      delta_volatility:      float
      delta_sharpe:          float
      comment: str
  diagnostics:
    warnings: [str]
    missing_data:
      - field: "regime_conditioned_assumptions"
        impact: "regime-aware MVO / risk premia 분해 불가"
        recommended_next_step: "future phase — regime_mvo (현재 future_study only)"
      - field: "tilt_decisions.confidence"
        impact: "tilt 의 통계적 유의성 표시 불가"
        recommended_next_step: "future phase — confidence scaling"
```

### 한계 명시 (사용자 §5 의무)

```
TAA 는 현재 prototype heuristic rule-based overlay 입니다. 모델 기반 (regime-conditioned MVO,
confidence scaling, TAA optimizer) 이 아닙니다. tilt 수치는 운영자 정의 정책값
(taa_policy.yaml::regime_tilts.regime_<n>.asset_tilts) 에서 조회된 값이며, allocation 에는
SAA + tilt → projection (long-only + sum=1) 형태로 적용됩니다.
```

### 데이터 출처 / 가용성

| 필드 | source | availability |
|---|---|:---:|
| current_regime.* | `portfolio.diagnostics.regime.*` | available |
| regime_conditioned_assumptions | — | **unavailable** (시스템 미보유, 영구 한계) |
| tilt_policy.* | `taa_policy.yaml` + hard-coded label | available |
| tilt_decisions.by_asset.{saa_weight, tilt, taa_target_weight} | direct telemetry + taa_feasibility | available |
| tilt_decisions.by_asset.{direction, rationale, source} | derive | computable |
| taa_portfolio_summary.* | computed (w_saa · μ, sqrt(w'Σw), w_taa · μ 등) | computable |
| improvement_summary | computed | computable |

---

## 6. `product_selection_explainability`

```yaml
product_selection_explainability:
  universe:
    total_count: int                                # universe_diagnostics.total_products
    raw_count: int                                  # universe_diagnostics.raw_count
    passed_filter_count: int                        # universe_diagnostics.passed_filter_count
    classified_count: int
    by_asset_class:
      <asset_key>:
        classified_count: int
        match_reasons: [str]                        # match_reasons_by_asset_class
        products: []                                # 본 phase 미수록 (개별 universe full list)
        products_available: false
        deferred_to: "E-11"
  filtering:
    excluded_products: []                           # 본 phase 미수록 (전체 excluded sample)
    excluded_sample: [{asset_key,...}]              # universe_diagnostics.unclassified_samples (제한적)
    eligible_count_by_asset:
      <asset_key>: int                              # universe_diagnostics.classified_by_asset_class
  scoring:
    score_method: "quant_grade hard_filter (ETF) / score_penalty (Fund)"
    score_factors: []                               # 본 phase 미수록
    scored_products: []                             # 본 phase 미수록 (selection score 미보존)
    scoring_available: false
    deferred_to: "E-11 + selection/tool.py 수정"
    grade_filtered_count: int
    grade_penalized_count: int
  final_selection:
    selected_products:
      - product_id: str
        product_name: str
        ticker: str | null                          # etf_list/fund_list lookup (가능 시)
        manager: str
        asset_key: str
        bucket: str
        asset_weight: float                         # source_asset_weight
        product_weight: float                       # final_weight
        rank_within_asset: int                      # weight 내림차순 rank
        role: "core" | "satellite" | "fallback"
        selected_reason: str | null
        cap_applied: bool                           # warning_flags 에 fallback_absorber 포함
        constraint_notes: [str]                     # warning_flags
  diagnostics:
    warnings: [str]
    missing_data:
      - field: "by_asset_class.products / scoring.scored_products"
        impact: "ETF/Fund universe 전체 대비 selection 비율 시각화 불가, factor 별 score 분해 불가"
        recommended_next_step: "E-11 phase: ProductRepository read-only 호출 + selection/tool.py 의 score 보존"
```

### 데이터 출처 / 가용성

| 필드 | source | availability |
|---|---|:---:|
| universe.{total_count, raw_count, passed_filter_count, classified_count, by_asset_class.classified_count, match_reasons} | `portfolio.diagnostics.universe_diagnostics.*` | available |
| universe.by_asset_class.products | — | **deferred to E-11** |
| filtering.eligible_count_by_asset | `universe_diagnostics.classified_by_asset_class` | available |
| filtering.excluded_sample | `universe_diagnostics.unclassified_samples` (제한적) | available, partial |
| scoring.score_method / grade_*_count | `selection_diagnostics.{quant_grade_policy, grade_filtered_count, grade_penalized_count}` | available |
| scoring.score_factors / scored_products | — | **deferred to E-11** (`selection_diagnostics` 에 score 미보존) |
| final_selection.selected_products.{product_id, product_name, manager, asset_key, bucket, weight, role, ...} | `portfolio.product_allocation[]` | available |
| final_selection.selected_products.ticker | `etf_list` / `fund_list` 원본 lookup (product_id 매칭) | **partial** — list 파일 없으면 null |
| final_selection.selected_products.rank_within_asset | computed | computable |

> **사용자 §6 명시**: ticker / product_name / asset_key 가 반드시 데이터에 포함되어야 함.
> selection logic 은 변경하지 않고 metadata 만 expose.

---

## 7. `report_ready_summary`

향후 차트가 caption 으로 그대로 사용할 수 있는 한국어 텍스트 요약.

```yaml
report_ready_summary:
  regime_summary:
    title: "현재 경기국면 진단"
    current_location_text: "G7 region 의 ECI 좌표는 P=+0.7223 / V=+0.0586 으로
                            Regime 1 (Expansion / Acceleration) 에 위치합니다."
    transition_text: "직전 5개 관측 모두 Regime 1 — 국면 변화 없음."
    asset_implication_text: "현재 regime 의 자산군 선호: em_equity / kr_equity / us_high_yield 비중 확대,
                             kr_treasury_10y / us_treasury_30y 비중 축소."
  saa_summary:
    title: "SAA 도출 (max_sharpe MVO)"
    input_summary_text: "9개 자산 — μ vector 평균=8.2%, σ vector 평균=15.4%.
                         ρ matrix 9×9, Σ matrix 9×9 (E-6.2 telemetry)."
    selected_saa_text: "MVO 결과: us_growth 71.6% / us_value 28.4% / 나머지 0%.
                        E[R]=12.3% / σ=18.1% / Sharpe=0.55."
    frontier_summary_text: "Efficient frontier visualization 은 E-9 phase 대상 (현재 미산출)."
    constraint_summary_text: "Active constraints: long-only, sum=1.0 (hard).
                              비활성: weight_bounds, equity_sum/fixed_income_sum."
  taa_summary:
    title: "TAA Tilt 적용 (Regime 1)"
    current_regime_tilt_text: "Regime 1 (Expansion / Acceleration) 의 prototype heuristic tilt 적용."
    key_overweights: ["em_equity +2.0pp", "kr_equity +2.0pp", "us_high_yield +1.0pp"]
    key_underweights: ["kr_treasury_10y -2.0pp", "us_treasury_30y -3.0pp"]
    limitation_text: "Current tilt is generated from regime rule policy, not from
                      regime-conditioned MVO. Confidence/optimizer 미적용."
  product_selection_summary:
    title: "Product Selection"
    universe_summary_text: "ETF: total=932 / classified=N / passed=N (universe_diagnostics)."
    selection_method_text: "quant_grade hard_filter (ETF). single_product cap 20%, manager cap 60%."
    top_selected_products: ["{name} ({manager}, {asset_key}) {weight:.2%}"]
    limitation_text: "Score factor 분해 / universe 전체 표 는 E-11 phase 대상 (selection score 미보존)."
  warnings:
    - warning_code: "EFRONTIER_DEFERRED"
      message: "Efficient frontier 미산출 — E-9 phase 대상."
    - warning_code: "REGIME_HISTORY_PARTIAL"
      message: "Regime history 5 obs 한정 — 24개월 timeline 미산출."
  missing_data:
    - field: "saa.efficient_frontier"
      impact: "selected SAA point 의 frontier 위치 시각화 불가"
      recommended_next_step: "E-9 phase"
    - field: "regime.history (24m)"
      impact: "장기 regime timeline 시각화 불가"
      recommended_next_step: "regime backfill sidecar 또는 telemetry enhancement"
    - field: "product.scoring.scored_products"
      impact: "factor 별 score 분해 불가"
      recommended_next_step: "E-11 phase + selection/tool.py 에서 score 보존"
    - field: "taa.regime_conditioned_assumptions"
      impact: "regime-aware MVO 비교 불가"
      recommended_next_step: "future phase (regime_mvo, future study only)"
```

---

## 8. Hard Requirements (E-7 영구)

```
✗ allocation 결과 변경 금지
✗ optimizer / TAA / projection / selection / config 로직 변경 금지
✗ taa_policy.yaml 수치 변경 금지 (read-only 만)
✗ portfolio_*.json 변경 금지 (read 만)
✗ 기존 production 산출물 (out/db_*_relaxed/, out/db_review_relaxed/) overwrite 금지
✗ Decision Register count (14) 변경 금지
✗ SAA inferred (taa_target − asset_tilts) 사용 금지 — direct telemetry only
✗ 기존 MVP-X PNG / appendix 정책 변경 금지
✓ 신규 산출 = explainability JSON + summary md 만 (out/db_review_relaxed_e62/explainability/)
✓ read-only 추가 계산 (risk_contribution, return/vol/sharpe before/after tilt) 만 허용
```

---

## 9. 산출물

```
out/db_review_relaxed_e62/explainability/<as_of_run>/
├── explainability_etf_<as_of_run>.json
├── explainability_fund_<as_of_run>.json
└── explainability_summary_<as_of_run>.md
```

---

## 10. 다음 phase 후보 (E-7 산출 활용)

| candidate | 영역 | E-7 데이터 사용 |
|---|---|---|
| E-8 | Regime Clock Visualization | regime_explainability (history 24m 확보 후) |
| E-9 | SAA MVO / Efficient Frontier | saa_explainability + efficient_frontier 산출 |
| E-10 | TAA Regime Tilt Visualization | taa_explainability (tilt + before/after summary) |
| E-11 | Product Selection Explainability | product_selection_explainability (universe 전체 + score 보존 후) |

각 후속 phase 는 별도 spec + 사용자 sign-off 필요. 본 turn 은 데이터 계약 + dump 만.
