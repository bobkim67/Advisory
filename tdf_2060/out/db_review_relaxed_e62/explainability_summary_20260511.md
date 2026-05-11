# Portfolio Explainability Summary (20260511)

> schema_version: e7.1
> Read-only diagnostic. Allocation logic was not re-executed.

## ETF

### 현재 경기국면 진단

- **current_location_text**: G7 region 의 ECI 좌표는 P=+0.7223 / V=+0.0586 으로 Regime 1 (Expansion / Acceleration) 에 위치합니다.
- **transition_text**: prev=R1 → curr=R1 (stable) (history 5 obs, 5/24 months)
- **asset_implication_text**: 현재 regime 의 자산군 선호 — 비중 확대: em_equity +2.0pp, kr_equity +2.0pp, us_high_yield +1.0pp / 비중 축소: us_treasury_30y -3.0pp, kr_treasury_10y -2.0pp.

### SAA 도출 (max_sharpe MVO)

- **input_summary_text**: 9개 자산 — μ vector 평균=7.60%, σ vector 평균=13.53%. ρ matrix 9×9, Σ matrix 9×9 (E-6.2 telemetry, direct dump).
- **selected_saa_text**: MVO 결과 (top weights): us_growth_equity 71.6% / us_value_equity 28.4%. E[R]=15.40% / σ=15.96% / Sharpe=0.7769.
- **frontier_summary_text**: Efficient frontier visualization 은 E-9 phase 대상 (현재 미산출).
- **constraint_summary_text**: Active constraints: long_only, weight_sum=1.0 (hard). 비활성 (Phase D relaxed): weight_bounds, equity_sum, fixed_income_sum.

### TAA Tilt 적용

- **current_regime_tilt_text**: Regime 1 (Expansion / Acceleration) 의 prototype heuristic tilt 적용.
- **key_overweights**:
  - em_equity +2.00pp
  - kr_equity +2.00pp
  - us_high_yield +1.00pp
- **key_underweights**:
  - kr_treasury_10y -2.00pp
  - us_treasury_30y -3.00pp
- **before_after_text**: Before: E[R]=15.40% / σ=15.96% / Sharpe=0.7769. After:  E[R]=15.93% / σ=16.40% / Sharpe=0.7879.
- **limitation_text**: Current tilt is generated from regime rule policy, not from regime-conditioned MVO. Confidence/optimizer 미적용.

### Product Selection

- **universe_summary_text**: raw=932 / passed_filter=736 / classified=572 (by_asset_class 카운트만 노출).
- **selection_method_text**: score_method={'mode': 'hard_filter', 'min_grade': 'C', 'penalty_per_grade': 0.1}. single_product/manager cap 은 selection logic 내부에서 적용 (E-7 read-only 미평가).
- **top_selected_products**:
  - 타임폴리오TIME미국나스닥100액티브상장지수(주식) (타임폴리오자산운용, us_growth_equity) 20.00%
  - 삼성KODEX미국나스닥AI테크액티브상장지수[주식] (삼성운용, us_growth_equity) 20.00%
  - 미래에셋TIGER미국필라델피아반도체나스닥상장지수(주식) (미래에셋운용, us_growth_equity) 20.00%
  - 한국투자ACE미국배당다우존스상장지수(주식) (한국투자신탁운용, us_value_equity) 20.00%
  - 신한SOL미국배당다우존스상장지수[주식] (신한자산운용, us_value_equity) 4.66%
- **limitation_text**: Score factor 분해 / universe 전체 표 는 E-11 phase 대상 (selection score 미보존, ticker 미수록).

### Warnings

- `EFRONTIER_DEFERRED` — Efficient frontier 미산출 — E-9 phase 대상.
- `REGIME_HISTORY_PARTIAL` — Regime history 5 obs 한정 — 24m timeline 미산출.
- `TAA_RULE_BASED` — TAA 는 rule-based heuristic prototype — regime-conditioned MVO 미적용.
- `PRODUCT_SCORE_MISSING` — selection score / factor values 미보존 — universe 전체 대비 분석 불가.

### Missing data (deferred)

- **saa.efficient_frontier** — selected SAA point 의 frontier 위치 시각화 불가  → next: E-9 phase
- **regime.history (24m)** — 장기 regime timeline 시각화 불가  → next: regime backfill sidecar 또는 telemetry enhancement
- **product.scoring.scored_products** — factor 별 score 분해 불가  → next: E-11 phase + selection/tool.py 에서 score 보존
- **taa.regime_conditioned_assumptions** — regime-aware MVO 비교 불가  → next: future phase (regime_mvo, future study only)
- **product.selected_products.ticker** — Bloomberg/Reuters ticker 표기 불가  → next: 외부 ticker mapping table 도입 또는 DBProductRepository 확장

## Fund

### 현재 경기국면 진단

- **current_location_text**: G7 region 의 ECI 좌표는 P=+0.7223 / V=+0.0586 으로 Regime 1 (Expansion / Acceleration) 에 위치합니다.
- **transition_text**: prev=R1 → curr=R1 (stable) (history 5 obs, 5/24 months)
- **asset_implication_text**: 현재 regime 의 자산군 선호 — 비중 확대: em_equity +2.0pp, kr_equity +2.0pp, us_high_yield +1.0pp / 비중 축소: us_treasury_30y -3.0pp, kr_treasury_10y -2.0pp.

### SAA 도출 (max_sharpe MVO)

- **input_summary_text**: 9개 자산 — μ vector 평균=7.60%, σ vector 평균=13.53%. ρ matrix 9×9, Σ matrix 9×9 (E-6.2 telemetry, direct dump).
- **selected_saa_text**: MVO 결과 (top weights): us_growth_equity 71.6% / us_value_equity 28.4%. E[R]=15.40% / σ=15.96% / Sharpe=0.7769.
- **frontier_summary_text**: Efficient frontier visualization 은 E-9 phase 대상 (현재 미산출).
- **constraint_summary_text**: Active constraints: long_only, weight_sum=1.0 (hard). 비활성 (Phase D relaxed): weight_bounds, equity_sum, fixed_income_sum.

### TAA Tilt 적용

- **current_regime_tilt_text**: Regime 1 (Expansion / Acceleration) 의 prototype heuristic tilt 적용.
- **key_overweights**:
  - em_equity +2.00pp
  - kr_equity +2.00pp
  - us_high_yield +1.00pp
- **key_underweights**:
  - kr_treasury_10y -2.00pp
  - us_treasury_30y -3.00pp
- **before_after_text**: Before: E[R]=15.40% / σ=15.96% / Sharpe=0.7769. After:  E[R]=15.93% / σ=16.40% / Sharpe=0.7879.
- **limitation_text**: Current tilt is generated from regime rule policy, not from regime-conditioned MVO. Confidence/optimizer 미적용.

### Product Selection

- **universe_summary_text**: raw=781 / passed_filter=414 / classified=262 (by_asset_class 카운트만 노출).
- **selection_method_text**: score_method={'mode': 'score_penalty', 'min_grade': 'B', 'penalty_per_grade': 0.1}. single_product/manager cap 은 selection logic 내부에서 적용 (E-7 read-only 미평가).
- **top_selected_products**:
  - KB미국대표성장주자(주식)(UH)C-퇴직 (KB운용, us_growth_equity) 30.00%
  - 한국투자미국배당귀족자UH(주식)(C-R) (한국투자신탁운용, us_value_equity) 21.92%
  - 삼성미국그로스자UH[주식-재간접]_Cp(퇴직연금) (삼성운용, us_growth_equity) 20.30%
  - AB미국그로스UH(주식-재간접)종류C-P2 (AB자산운용, us_growth_equity) 20.30%
  - 한국투자미국배당귀족자H(주식)(C-R) (한국투자신탁운용, us_value_equity) 5.48%
- **limitation_text**: Score factor 분해 / universe 전체 표 는 E-11 phase 대상 (selection score 미보존, ticker 미수록).

### Warnings

- `EFRONTIER_DEFERRED` — Efficient frontier 미산출 — E-9 phase 대상.
- `REGIME_HISTORY_PARTIAL` — Regime history 5 obs 한정 — 24m timeline 미산출.
- `TAA_RULE_BASED` — TAA 는 rule-based heuristic prototype — regime-conditioned MVO 미적용.
- `PRODUCT_SCORE_MISSING` — selection score / factor values 미보존 — universe 전체 대비 분석 불가.

### Missing data (deferred)

- **saa.efficient_frontier** — selected SAA point 의 frontier 위치 시각화 불가  → next: E-9 phase
- **regime.history (24m)** — 장기 regime timeline 시각화 불가  → next: regime backfill sidecar 또는 telemetry enhancement
- **product.scoring.scored_products** — factor 별 score 분해 불가  → next: E-11 phase + selection/tool.py 에서 score 보존
- **taa.regime_conditioned_assumptions** — regime-aware MVO 비교 불가  → next: future phase (regime_mvo, future study only)
- **product.selected_products.ticker** — Bloomberg/Reuters ticker 표기 불가  → next: 외부 ticker mapping table 도입 또는 DBProductRepository 확장
