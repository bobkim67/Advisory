# Phase E-6.1 — Portfolio Construction Visualization Redesign

작성일: 2026-05-08. **E-6 MVP (9 PNG) 재분류 + 신규 main visualization 구조 설계**.
본 turn = 설계 + 데이터 가용성 점검만. 코드 / config / tests / out 일체 무변경.

> **Phase D completed register-blocker resolution only.**
> **This does not mean production readiness.**
> **The engine remains in relaxed_diagnostic mode.**

> 본 문서는 운용역 review 의 핵심을 "최종 비중 확인"에서 "포트폴리오가 어떻게 만들어졌는지
> 의사결정 과정 설명"으로 옮기기 위한 시각화 구조 재설계. allocation / optimizer / TAA /
> selection 로직 / cap·band·threshold / Decision Register / production mode 모두 무변경.

---

## 0. TL;DR

| 항목 | 결과 |
|---|---|
| **기존 9 PNG 위상** | **partial / downstream-only**. main review 부적격, **appendix 한정**. |
| **신규 main 5 블록** | A. Regime / B. MVO Input & SAA / C. TAA Overlay / D. Projection & Drift / E. Product Final |
| **데이터 가용성 (4분류)** | available 9 / available_but_inferred 2 / **missing telemetry 5** / not_needed_for_mvp 2 |
| **Telemetry gap** | μ / σ / ρ / Σ / regime history 5건 — 다음 구현 전 telemetry enhancement **필요**. allocation 재계산 없이 diagnostics 에 추가 가능. |
| **새 MVP 제안** | 기존 PNG 데이터로 즉시 가능: A.1 quadrant + A.2 regime card + C.1 tilt table + C/D bridge + D drift attribution. B (MVO input) 는 telemetry 확보 후 다음 phase. |
| **본 turn 산출** | `docs/phase_e_output_visualization_redesign.md` 1건. 코드 무변경, pytest 미실행 (직전 baseline `151 passed, 5 skipped, 1 xfailed`). |

---

## 1. 기존 차트 재분류

E-6 MVP 에서 생성한 9 PNG 의 위상을 **appendix only** 로 재분류.

| # | PNG | 기존 위상 | 재분류 후 위상 |
|:---:|---|---|---|
| 1 | `etf/01_asset_allocation.png` | MVP main | **Appendix-E.1** (final asset result check) |
| 2 | `etf/02_drift_summary.png` | MVP main | **Appendix-E.4 partial** (D 블록 일부 — full 재구성 필요) |
| 3 | `etf/03_top_products.png` | MVP main | **Appendix-E.5** (final product check) |
| 4 | `etf/04_manager_concentration.png` | MVP main | **Appendix-E.5** |
| 5 | `fund/01_asset_allocation.png` | MVP main | **Appendix-E.1** |
| 6 | `fund/02_drift_summary.png` | MVP main | **Appendix-E.4 partial** |
| 7 | `fund/03_top_products.png` | MVP main | **Appendix-E.5** |
| 8 | `fund/04_manager_concentration.png` | MVP main | **Appendix-E.5** |
| 9 | `comparison/01_asset_allocation_etf_vs_fund.png` | MVP main | **Appendix-E.1** |

**결론**: 기존 9 PNG 모두 **Investment Process Review 부적격**. 운용역에게 "**무엇을** 담았는가"
는 보여주지만 "**왜** 그렇게 담겼는가"를 설명하지 못함.

기존 산출물은 **삭제하지 않음**. 신규 main 시각화 산출 시 같은 figures_summary 의 `## Appendix`
섹션에서 참조하여 보존.

---

## 2. 신규 main visualization 구조 설계

운용역 review 의 흐름 = **Regime → MVO → SAA → TAA → Projection → Product → Final**.

블록 5종 (A ~ E). 각 블록은 1 ~ 3 차트.

### 2.A Regime Diagnosis (블록 A)

| # | 차트 | 종류 | 핵심 데이터 | 운용역 질문 답변 |
|:---:|---|---|---|---|
| A.1 | Placement / Velocity quadrant | 2D scatter (점 1개) | `diagnostics.regime.placement`, `velocity` | 현재 어느 사분면? |
| A.2 | Current regime card | text card panel | `regime`, `regime_label`, `placement`, `velocity`, `region`, `as_of` + 해석 1줄 | 현재 국면이 뭔지 / 위험자산 우호성 |
| A.3 | Regime timeline | line + 색상 stripe | regime history 시계열 (12-36개월) | 직전 분기에 변화 있었나? |

**A.1 quadrant 영역 정의** (regime_classifier 의 ECI rule 그대로):

```
Placement > 0, Velocity > 0  →  Regime 1 (Expansion / Acceleration)
Placement > 0, Velocity ≤ 0  →  Regime 2 (Expansion / Deceleration)
Placement ≤ 0, Velocity ≤ 0  →  Regime 3 (Contraction / Deceleration)
Placement ≤ 0, Velocity > 0  →  Regime 4 (Contraction / Acceleration)
```

현재 ETF/Fund: placement=0.7223, velocity=0.0586 → Regime 1, region=G7.

### 2.B MVO Input & SAA Construction (블록 B)

| # | 차트 | 종류 | 핵심 데이터 | 운용역 질문 답변 |
|:---:|---|---|---|---|
| B.1 | Expected return vs volatility scatter | 9-point scatter + Sharpe label | μ, σ by asset | 어떤 자산이 risk-return 우월? |
| B.2 | Correlation heatmap | 9×9 heatmap | ρ matrix | us_growth/us_value 분산효과? HY-equity 상관? |
| B.3 | MVO objective / constraint summary | text card | objective_name (max_sharpe), n_iter, rf, weight_sum, solver_status, hard constraint set | objective 와 입력 검증 통과 |
| B.4 | SAA weight bar | horizontal bar | SAA weight by asset (long-only, sum=1) | MVO 결과 SAA 분포 |

> **B.1 / B.2 / B.4 데이터 미공개** (§3 참조). B.3 만 즉시 가능. 나머지 telemetry 확보 후.

### 2.C TAA Prototype Overlay (블록 C)

| # | 차트 | 종류 | 핵심 데이터 | 운용역 질문 답변 |
|:---:|---|---|---|---|
| C.1 | Regime asset_tilts table | 9-row table | `taa_policy.yaml::regime_tilts.regime_<n>.asset_tilts` | 현재 regime 의 적용 tilt |
| C.2 | SAA + tilt = pre-projection TAA bridge | grouped bar (3 series) | SAA(inferred) + tilt + TAA target | tilt 적용 효과 |
| C.3 | TAA method banner | text card | "prototype heuristic overlay, NOT optimizer" + `bucket_tilts metadata-only` + `per_asset_max_tilt=1.0` | 이 결과의 위상 |

**C.1 의 Regime 1 적용 tilt** (taa_policy.yaml 확인 필요, 사용자 참조값):

```
em_equity         +2.0%p
kr_equity         +2.0%p
us_high_yield     +1.0%p
kr_treasury_10y   -2.0%p
us_treasury_30y   -3.0%p
(나머지 자산: 0.0%p)
```

`tilt_sum_must_be_zero=true` 정합 (sum = +5 - 5 = 0).

### 2.D Projection & Drift Attribution (블록 D)

| # | 차트 | 종류 | 핵심 데이터 | 운용역 질문 답변 |
|:---:|---|---|---|---|
| D.1 | Pre-projection TAA → Post-projection bridge | dual horizontal bar + diff arrow | `target_weights_before_projection`, `final_weights_after_projection` | projection 으로 무엇이 바뀜? |
| D.2 | Long-only clipping by asset | bar (음수 자산만) | `clipping_summary.long_only_clipping_by_asset` | kr_t10 / ust30 가 왜 0? |
| D.3 | Redistribution by recipient | bar | `clipping_summary.redistribution_by_recipient` | 흡수된 자산 |
| D.4 | Quality / Product fallback drift (분리) | 2-panel | `diagnostics.quality.drift_clipping_summary` (별도) | product cap 영향 (D-02 와 분리) |

**핵심**: D-02 projection drift (long-only clipping) 와 D-15 candidate (product cap clipping
outflow + fallback redistribution inflow) **두 layer 를 명시 분리**. 기존 9 PNG 의 drift_summary
는 두 layer 를 한 화면에 섞어서 표현해 운용역 혼동 가능성.

### 2.E Product Selection & Final Portfolio (블록 E, appendix)

기존 9 PNG 활용. 신규 차트 추가 안 함.

| # | 차트 | 위치 | 출처 |
|:---:|---|---|---|
| E.1 | ETF / Fund / Comparison asset allocation (3 PNG) | Appendix | 기존 PNG 1·5·9 |
| E.2 | ETF / Fund drift summary (2 PNG) | Appendix (D 블록 보조) | 기존 PNG 2·6 |
| E.3 | ETF / Fund top products (2 PNG) | Appendix | 기존 PNG 3·7 |
| E.4 | ETF / Fund manager concentration (2 PNG) | Appendix | 기존 PNG 4·8 |

### 2.F 흐름 다이어그램

```
[A. Regime]                             ← 현재 국면 진단 (왜 이 tilt?)
    ↓
[B. MVO Input]   →   [B.4 SAA]          ← 자산군 자체 매력 (μ/σ/ρ → SAA)
    ↓                    ↓
                     [C. TAA Overlay]   ← regime tilt 적용 (SAA → TAA)
                         ↓
                     [D. Projection]    ← long-only / sum=1 강제 (TAA → final asset)
                         ↓
                     [E. Product]       ← selection + fallback (asset → product)
                         ↓
                     [Final Portfolio]
```

---

## 3. 데이터 가용성 점검 (현재 portfolio_*.json 기준)

각 항목을 4 상태로 분류: **available** / **available_but_inferred** / **missing_requires_telemetry** / **not_needed_for_mvp**.

### 3.1 Regime 데이터

| 필드 | 위치 | 상태 |
|---|---|---|
| `as_of_date` | `diagnostics.regime.as_of` (= "2026-02-01") | **available** |
| `region` | `diagnostics.regime.region` (= "G7") | **available** |
| `Placement` | `diagnostics.regime.placement` (= 0.7223) | **available** |
| `Velocity` | `diagnostics.regime.velocity` (= 0.0586) | **available** |
| `regime number` | `diagnostics.regime.regime` (= 1) | **available** |
| `regime label` | `diagnostics.regime.regime_label` (= "Expansion / Acceleration") | **available** |
| `regime history / timeline` | — | **missing_requires_telemetry** |

> Regime timeline 은 단일 run json 에 없음. `regimeAnalysis_src` (월말 지수) → placement/velocity
> 시계열 재계산은 가능하나 **다음 run 시점부터** diagnostics 에 추가 telemetry 로 보존 권장.

### 3.2 MVO 데이터

| 필드 | 위치 | 상태 |
|---|---|---|
| `objective name` | `diagnostics.saa_diagnostics.objective_name` (= "max_sharpe") | **available** |
| `solver_status / n_iter / rf / weight_sum / solver_message` | `diagnostics.saa_diagnostics.*` | **available** |
| `n_assets / asset_keys / ticker_by_key / name_by_key / missing_assets / ust30_policy` | `diagnostics.saa_diagnostics.cma` | **available** |
| **expected return by asset** (μ vector, len 9) | — | **missing_requires_telemetry** |
| **volatility by asset** (σ vector, len 9) | — | **missing_requires_telemetry** |
| **correlation matrix** (ρ, 9×9) | — | **missing_requires_telemetry** |
| **covariance matrix** (Σ, 9×9) | — | **missing_requires_telemetry** |
| **SAA / MVO weights** (post-MVO, pre-TAA) | — | **available_but_inferred** (= `taa_feasibility.target_weights_before_projection` − `asset_tilts`) |

> **핵심 telemetry gap**. CMA (μ/σ/ρ/Σ) 가 `saa_diagnostics.cma` 에 metadata 만 남고 수치 vector
> 는 노출 안 됨. 시각화 의도가 "SAA 가 왜 이렇게 나왔는지" 설명이라면 μ/σ/ρ 노출 필요.

### 3.3 TAA 데이터

| 필드 | 위치 | 상태 |
|---|---|---|
| `regime` (TAA 기준) | `diagnostics.taa_diagnostics.regime` (= 1) | **available** |
| `regime_label` | `diagnostics.taa_diagnostics.regime_label` | **available** |
| `asset_tilts` (regime 별) | `taa_policy.yaml::regime_tilts.regime_<n>.asset_tilts` | **available** (config read-only OK) |
| `bucket_tilts` (metadata only) | `taa_policy.yaml::regime_tilts.regime_<n>.bucket_tilts` | **available** (단 활성화 금지 명시) |
| `pre-projection TAA target` | `diagnostics.taa_diagnostics.taa_feasibility.target_weights_before_projection` | **available** |
| `tilt_sum_must_be_zero check` | `diagnostics.taa_diagnostics.tilt_sum_after_adjust` (= -1.7e-18) | **available** |
| `residual_before_adjust` | `diagnostics.taa_diagnostics.residual_before_adjust` | **available** |
| `violations` | `diagnostics.taa_diagnostics.violations` (= []) | **available** |
| `bucket_sums` (TAA target) | `diagnostics.taa_diagnostics.bucket_sums` | **available** |

### 3.4 Projection 데이터

| 필드 | 위치 | 상태 |
|---|---|---|
| `projection_used / projection_success / projection_message` | `taa_feasibility.*` | **available** |
| `final_weights_after_projection` | `taa_feasibility.final_weights_after_projection` | **available** |
| `negative_weight_assets_before_projection` | `taa_feasibility.negative_weight_assets_before_projection` | **available** |
| `bucket_weights_before_projection / after_projection` | `taa_feasibility.bucket_weights_*` | **available** |
| `asset_weight_drift_from_target` (signed by asset) | `taa_feasibility.asset_weight_drift_from_target` | **available** |
| `max_abs_projection_drift` | `taa_feasibility.max_abs_projection_drift` | **available** |
| `drift_source_by_asset` (long_only_clipping / redistribution_*) | `taa_feasibility.drift_source_by_asset` | **available** |
| `clipping_summary` (clipped_assets, by_asset, redistribution_by_recipient, drift_source_primary, counts) | `taa_feasibility.clipping_summary` | **available** |
| `clipped_weight_total` | `taa_feasibility.clipped_weight_total` | **available** |

### 3.5 Product / Selection 데이터

| 필드 | 위치 | 상태 |
|---|---|---|
| `product_allocation` (17 entries with manager / weight / asset_key / fallback) | top-level `product_allocation[]` | **available** |
| `selection_diagnostics` (n_picks, unfilled_by_asset_class, grade_filtered/penalized) | `diagnostics.selection_diagnostics` | **available** |
| `fallback` (reasons / reallocations / absorbers) | `diagnostics.fallback` | **available** |
| `quality.drift_clipping_summary` (product cap outflow / inflow / drift_source_primary) | `diagnostics.quality.drift_clipping_summary` | **available** |
| `universe_diagnostics` (raw / passed / classified / by_asset_class) | `diagnostics.universe_diagnostics` | **available** |

### 3.6 Not needed for MVP

| 필드 | 사유 |
|---|---|
| Backtest 시계열 / drawdown / IR | main process review 범위 외. 별도 backtest tool. |
| Monte-Carlo 분포 / scenario | 동. |

### 3.7 점검 요약 (4 상태 카운트)

| 상태 | 건수 | 영역 |
|---|---:|---|
| **available** | 25 | regime 6 / MVO meta 6 / TAA 8 / projection 10 / product 5 (중복 제거 후 ~25) |
| **available_but_inferred** | 2 | SAA weight (= TAA target − asset_tilts), bucket-level SAA |
| **missing_requires_telemetry** | 5 | μ vector, σ vector, ρ matrix, Σ matrix, regime history |
| **not_needed_for_mvp** | 2 | backtest, MC |

---

## 4. Telemetry Gap 정리

본 5건은 시각화 main 블록 (특히 B) 구현 전 **diagnostics 에 추가 노출** 필요. 모두 **allocation
재계산 없이 기존 산출 흐름에 telemetry 만 추가** 가능.

| ID | gap | 권장 diagnostics key | 영향 영역 |
|:---:|---|---|---|
| T-1 | μ vector | `diagnostics.saa_diagnostics.cma.expected_returns` | B.1 (return-vol scatter) |
| T-2 | σ vector | `diagnostics.saa_diagnostics.cma.volatilities` | B.1 |
| T-3 | ρ matrix | `diagnostics.saa_diagnostics.cma.correlation_matrix` | B.2 (heatmap) |
| T-4 | Σ matrix | `diagnostics.saa_diagnostics.cma.covariance_matrix` | B.1 risk axis 보조 (또는 σ 만으로 충분) |
| T-5 | regime history | `diagnostics.regime.history` (또는 별도 시계열 산출 sidecar) | A.3 (timeline) |

### 4.1 Telemetry 추가 작업 위상

| 항목 | 위상 |
|---|---|
| allocation 결과 변동 | ✗ 없음. CMA / regime 산출은 이미 build_portfolio.py 내부에서 계산되며, 본 telemetry 는 같은 객체를 추가로 dict 로 dump 하는 것. |
| 코드 변경 영역 | `tdf_engine/optimization/cma.py` (build 결과를 saa_diagnostics 에 추가 dump) + `tdf_engine/regime/` (history 산출 보존) |
| config 변경 | ✗ 불필요 |
| 정책 변경 | ✗ 불필요 |
| 기존 산출물 backward compat | 신규 키 추가만 — 기존 키 변경 없음. JSON consumer 영향 없음. |

> **본 turn 에서는 telemetry 작업 진행 안 함.** §6 금지 항목 정합. 단 다음 turn 의 구현 phase
> 진입 전 별도 검토 필요.

### 4.2 Telemetry 없이도 가능한 main 차트

| 블록 | 가능 여부 | 사유 |
|---|---|---|
| **A. Regime** | A.1 ✓ / A.2 ✓ / A.3 ✗ (timeline) | placement/velocity 단일 시점은 가능, history 부재 |
| **B. MVO Input** | B.1 ✗ / B.2 ✗ / B.3 ✓ / B.4 ◐ (inferred) | μ/σ/ρ 부재. SAA 는 inferred (asset_tilts 역산) |
| **C. TAA Overlay** | C.1 ✓ / C.2 ◐ (SAA inferred) / C.3 ✓ | asset_tilts 는 config 에서, pre-projection TAA 는 diagnostics 에서 |
| **D. Projection & Drift** | D.1 ✓ / D.2 ✓ / D.3 ✓ / D.4 ✓ | 모두 taa_feasibility + quality 에 있음 |
| **E. Product (appendix)** | ✓ | 기존 9 PNG 그대로 |

→ **B 블록만 telemetry 의존**. A / C / D / E 는 즉시 가능.

---

## 5. 새 MVP 제안

기존 5종 (asset / asset_compare / drift / top_products / manager) 은 **Appendix-only** 로 격하.

### 5.1 main MVP (즉시 가능, 코드 구현 시)

| MVP # | 차트 | 블록 | 데이터 의존 |
|:---:|---|---|---|
| MVP-A1 | Placement / Velocity quadrant | A.1 | available |
| MVP-A2 | Current regime card | A.2 | available |
| MVP-C1 | Regime asset_tilts table | C.1 | available (config) |
| MVP-C2 | SAA(inferred) → TAA bridge | C.2 | inferred (asset_tilts 역산) — **inferred** 라벨 강제 |
| MVP-C3 | TAA method banner | C.3 | available |
| MVP-D1 | Pre-projection TAA → Post-projection bridge | D.1 | available |
| MVP-D2 | Long-only clipping by asset | D.2 | available |
| MVP-D3 | Quality / product fallback drift (별도 panel) | D.4 | available |
| MVP-X | "How was this portfolio built?" 통합 1-page bridge (SAA → TAA → projection → final asset → product top) | C+D+E 결합 | available + inferred |

main MVP 산출 = **9 차트 (1-page integrated 1 + 개별 8)** + appendix (기존 9 PNG 유지).

### 5.2 main MVP 제외 (telemetry 확보 후)

| 차트 | 사유 |
|---|---|
| A.3 Regime timeline | regime history telemetry 부재 (T-5) |
| B.1 Return-vol scatter | μ/σ telemetry 부재 (T-1, T-2) |
| B.2 Correlation heatmap | ρ telemetry 부재 (T-3) |
| B.4 SAA weight bar (직접 노출) | 현재는 inferred 만 가능. 별도 SAA telemetry 추가 시 직접 노출. |

위 4종은 **다음 phase E-6.2** 후보.

### 5.3 추천 진입 순서

```
E-6.1 (본 문서) — 설계 + 데이터 가용성 점검            ← 본 turn
E-6.2 — Telemetry enhancement
        (saa_diagnostics.cma.expected_returns 등 5건 추가)
E-6.3 — main MVP 구현 (A1·A2·C1·C2·C3·D1·D2·D3·통합 bridge)
E-6.4 — telemetry 의존 차트 추가 (A3·B1·B2·B4)
E-6.5 — appendix 통합 (기존 9 PNG 그대로 + 새 main 1-page)
```

각 단계 사이마다 사용자 sign-off. 본 turn 은 E-6.1 만.

---

## 6. 본 turn 의 변경 범위

| 영역 | 본 turn |
|---|:---:|
| `tdf_engine/` 코드 (optimization / taa / selection / portfolio / regime / reporting) | ✗ 무변경 |
| `tdf_engine/config/*.yaml` | ✗ 무변경 |
| `tdf_engine/reporting/figures.py` | ✗ 무변경 (E-6 그대로) |
| `tdf_engine/tools/render_figures.py` | ✗ 무변경 |
| `tests/` | ✗ 무변경 |
| `out/` 산출물 (portfolio_* / review_* / comparison_* / figures_summary_* / figures/* / governance_log/*) | ✗ 무변경 |
| Decision Register status / count (14) | ✗ 무변경 |
| operating_mode (`relaxed_diagnostic`) | ✗ 무변경 |
| TAA engine / 정책 / 수치 | ✗ 무변경 |
| asset cap / band / threshold | ✗ 무변경 |
| production dry-run | ✗ 미진입 |
| 본 문서 신설 | ✓ `docs/phase_e_output_visualization_redesign.md` |

pytest: `151 passed, 5 skipped, 1 xfailed` (직전 baseline. 본 문서 작성으로 미실행, 영향 없음).

---

## 7. 다음 turn 결정 사항 (사용자 sign-off 필요)

| # | 결정 항목 | 옵션 |
|:---:|---|---|
| 1 | E-6.2 telemetry enhancement 진입 여부 | (a) 진입 — μ/σ/ρ/regime history 추가 (코드 변경 영역 cma.py + regime). 산출 결과 bit-identical 보장. / (b) 보류 — telemetry 없이 가능한 main MVP (A/C/D/E 만) 먼저 구현. |
| 2 | SAA inferred (TAA target − asset_tilts) 사용 허용 | (a) 허용 — "inferred" 라벨 강제 표기 + footer. / (b) 미허용 — telemetry 직접 노출 후만 사용. |
| 3 | 1-page integrated bridge (MVP-X) 우선순위 | (a) MVP 의 핵심 — 가장 먼저. / (b) 개별 차트 (A/C/D) 완성 후. |
| 4 | 기존 9 PNG appendix 자동 첨부 | (a) figures_summary 의 `## Appendix` 섹션으로 항상 첨부. / (b) 별도 옵션 (`--with-appendix`) 으로만. |

---

## 8. 한 줄 요약

> **E-6 MVP (9 PNG) 는 downstream-only / appendix 한정으로 재분류. main visualization 은
> Regime → MVO → SAA → TAA → Projection → Product 흐름의 5 블록으로 재설계.
> 데이터 가용성: 즉시 가능 25건 / inferred 2건 / telemetry 추가 필요 5건 (μ / σ / ρ / Σ / regime history).
> Telemetry 5건은 allocation 재계산 없이 diagnostics 에 추가 가능. 본 turn = 설계 + 점검만.
> 코드 / config / tests / out / Decision Register / TAA / cap / band / threshold 모두 무변경.**
