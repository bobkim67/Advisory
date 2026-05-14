# R-1G.0 — Full Product Re-selection Mini-Spec / Entrypoint Probe

작성일: 2026-05-13. **spec + entrypoint 조사만.** 구현 / config / tests / 산출물 변경 0.
R-1A · R-1E 와 동일 패턴 — 다음 turn 의 R-1G 구현자가 바로 읽고 작업 가능한 수준.

> **Phase D completed register-blocker resolution only.
> This does not mean production readiness. The engine remains in relaxed_diagnostic mode.**

> R-1F.2.1 결과 = `valid_asset_level_dry_run=true`, but `valid_product_level_portfolio=false`,
> `product_weight_sum_dry_run` 이 ETF 1.4448 / Fund 0.7209 → 운용 가능 portfolio 아님.
> R-1G 는 이 product-level invalid 문제를 **full product re-selection** 으로 해소한다.

---

## 0. TL;DR

| 항목 | 결정 |
|---|---|
| **Scope (R-1G.0)** | spec + 기존 entrypoint 조사 only. 구현 없음. |
| **출력 (R-1G.0)** | 본 문서 1건. |
| **다음 단계 (R-1G)** | `tdf_engine/optimization/manager_selected_reselection.py` + CLI + tests + dry-run JSON + comparison md |
| **Target weights** | **R-1F.2 dry-run 의 `asset_weights_dry_run`** (= TAA + projection 후 final asset weights) |
| **Adapter 가능 여부** | **YES.** 기존 `ProductSelectionTool.run(asset_weights)` 가 이미 임의 asset_weights 를 받는다 — 핵심 selection logic 무수정 가능. |
| **Universe 재구성** | `UniverseTool.run()` 재호출 필요 (DB or file repo). 본 단계의 유일한 외부 의존. |
| **Production 영향** | 0. R-1G 도 별도 디렉토리에만 dump, baseline / E-series / config / Decision Register 미변경. |

---

## 1. Background — R-1F.2.1 한계 재확인

| flag (ETF) | 값 | 의미 |
|---|---|---|
| `valid_asset_level_dry_run` | **true** | TAA + projection asset-level 검토 가능 |
| `valid_product_level_portfolio` | **false** | product weight sum ≠ 1.0 |
| `product_weight_sum_valid` | **false** | `\|sum − 1.0\| > 1e-3` |
| `needs_full_product_reselection` | **true** | R-1G 필요 |
| `implementation_ready` | **false** | 운용 불가 |
| `needs_selection_rerun_assets` | `['dm_ex_us_equity', 'us_high_yield']` | baseline 0% 였던 자산 |
| `product_weight_sum_dry_run` | **1.4448** (ETF) / **0.7209** (Fund) | proportional scaling 한계 |

근본 원인: R-1F.2 는 baseline `product_allocation` 을 `dry_run_asset_weight / baseline_asset_weight` 로 scaling. baseline 이 0% 인 자산은 분모가 0 → scaling 불가. 또한 baseline 이 비중 큰 자산 (us_growth 70.6%) 의 product weight 가 dry-run (25.3%) 으로 축소되지 못하고 비례 잔여가 남아 sum ≠ 1.

해결: target 자산 weight 분포 자체에서 universe + scoring 을 **다시** 돌려 product 를 새로 picking.

---

## 2. Existing Product Selection Entrypoint (조사 결과)

### 2.1 호출 체인 (production: `PortfolioConstructionTool.run`)

```
PortfolioConstructionTool.run(product_type)
  ├─ 1. optimization_tool.run() → SAA (asset weights pd.Series + diagnostics)
  ├─ 2. regime_tool.run() → regime_result
  ├─ 3. taa_tool.run(saa.weights, regime) → TAAResult (taa.taa_weights pd.Series)
  ├─ 4. universe_tool.run() → UniverseResult (products[] with mvo_asset_class)
  ├─ 5. selection_tool_factory(universe_result).run(taa.taa_weights) → ProductSelectionResult
  └─ 6. PortfolioBuilder.build(taa, selection, ...) → PortfolioResult
```

R-1G 의 seam = **단계 5** 직전: 다른 target asset weights 를 `selection_tool.run()` 에 주입.

### 2.2 핵심 모듈 위치

| 역할 | 파일 | 핵심 entry |
|---|---|---|
| Universe load + filter + classify | `tdf_engine/universe/tool.py` | `UniverseTool(repo, universe_config, product_type, classifier).run()` |
| Universe filter rules | `tdf_engine/universe/filters.py` | `UniverseFilter(FilterConfig)` |
| Asset classifier (제품→`mvo_asset_class`) | `tdf_engine/universe/classifier.py` | `ProductClassifier` (+ yaml rules) |
| Scoring | `tdf_engine/selection/scoring.py` | `ProductScorer(ScoringConfig)` (grade hard/penalty + AUM filter) |
| Core/Satellite selection | `tdf_engine/selection/selector.py` | `CoreSatelliteSelector(constraints).select(...)` |
| **Selection facade** | `tdf_engine/selection/tool.py` | **`ProductSelectionTool(universe_result, universe_config, product_type).run(asset_weights)`** |
| Portfolio assembly | `tdf_engine/portfolio/builder.py` | `PortfolioBuilder.build(taa, selection, ...)` |
| Production CLI (참고용) | `tdf_engine/tools/build_portfolio.py` | `_build_with_repos(loader, market_repo, product_repo, product_type)` |

### 2.3 ETF / Fund universe 로딩

```
ProductRepository (interface)
  ├─ DBProductRepository  (production, DB 의존)
  └─ FileProductRepository (CSV / fixture)
```

`UniverseTool._load_raw()` 가 `product_type` 에 따라 `repo.load_etf_universe()` / `repo.load_fund_universe()` 호출. R-1G dry-run 도 동일하게 사용하면 됨 (production CLI 와 동일한 repo).

baseline `out/db_etf_relaxed_e62/` 의 universe 는 `db_source` 정보가 `diagnostics["db_source"]` 에 남아 있음 — R-1G 도 동일 source 를 재호출 해야 결과가 정합.

### 2.4 자산군별 후보 필터링 / scoring (현재 정책)

| 단계 | 정책 (Phase D relaxed 기준) |
|---|---|
| universe filter | `kis_mp_categories` include / `exclude_keywords` / synthetic whitelist (`universe_filter.yaml`) |
| classifier | yaml rules (`universe_classification.yaml`) — 키워드 / region / sub_type 으로 `mvo_asset_class` 부여 |
| scoring `min_quant_grade` | `quant_grade_policy.mode` = "hard_filter" 또는 "score_penalty" (자산군별 미차등) |
| scoring `min_aum` | (있다면) AUM 하한선 |
| selector | `n_core_target=1`, `n_satellite_target=2`, `core_ratio=(0.6, 0.8)` → core 1건 + satellite 2건 = 자산당 3 products default |
| `single_product_max_weight` | ETF 0.20 (universe_filter.yaml etf.product_constraints), Fund 0.30 |
| `single_manager_max_weight` | ETF 0.60, Fund 0.50 |

### 2.5 Target asset weights → product weights 변환 (이미 구현)

`ProductSelectionTool.run(asset_weights)` 내부 (per asset):

```python
for asset_key, target_w in asset_weights.items():
    if target_w <= 0:
        continue
    in_universe = groups[asset_key]                          # mvo_asset_class 매칭
    after_filter = [p for p in in_universe if passes_filter(p)]
    candidates = scorer.score_and_sort(after_filter)         # score desc
    picks = selector.select(candidates, asset_key, target_w) # core + satellite + caps
    rows.extend(picks)
result = manager_cap_enforce(rows)                           # manager 60%/50% scale
return ProductSelectionResult(selected=result, ...)
```

→ 핵심 진단: **`asset_weights` 가 임의 분포여도 작동**. baseline 0% 였던 자산도 `target_w > 0` 이면 그 universe 에서 정상 picking. **selection core 무수정으로 R-1G 가능.**

### 2.6 `product_weight_sum = 1.0` 보장 위치

- selection 결과 합 ≤ target asset weight 합 (cap 으로 잘리면 unfilled).
- portfolio builder 가 unfilled 를 fallback (cash placeholder / pro-rata / bucket sibling) 으로 흡수.
- 최종 `product_allocation` 합 ≈ 1.0 (validator 가 atol=1e-6 으로 검증).

R-1G 도 동일 흐름 — `PortfolioBuilder.build(taa_substitute, selection_result, ...)` 호출하면 자동 sum=1 보장.

### 2.7 baseline 0% 자산도 universe 에서 재선택 가능?

**YES.** `universe_diagnostics.classified_by_asset_class` (baseline JSON 발췌):

```
kr_equity:         347
us_growth_equity:   22
us_value_equity:    18
dm_ex_us_equity:    15      ← baseline 0% 였지만 universe 에는 15건 분류됨
em_equity:          55
kr_aggregate_bond:  97
kr_treasury_10y:    10
us_treasury_30y:    6
us_high_yield:      2       ← baseline 0% 였지만 universe 에 2건 (ETF 기준)
```

dry-run target 으로 dm_ex_us_equity 10.64% / us_high_yield 10.89% 주면 selection 이 정상 picking. 단 us_high_yield 는 universe 2건 만으로 핵심+위성 채우기 어려울 수 있어 partial unfilled → fallback 처리. **R-1G warning 으로 표시 필요**.

---

## 3. R-1G Target Weights 정의

세 가지 후보:

| 후보 | source | 장점 | 단점 |
|---|---|---|---|
| (a) manager_override SAA weights | R-1F.1 manager_selected_saa JSON, `selected_candidate.weights` | 가장 raw / 정성 view 직접 반영 | TAA / projection 효과 미반영 |
| (b) TAA overlay 후 weights (pre-projection) | R-1F.2 `taa_target_weights` | TAA tilt 반영 | bucket bound 미적용 (Phase D relaxed 에서는 동일) |
| **(c) Projection 후 final asset weights** | **R-1F.2 `asset_weights_dry_run` (= `taa_after_projection_weights`)** | **실제 운용 시 구현해야 할 최종 asset allocation** | (없음) |

**기본값 (R-1G default): (c) `asset_weights_dry_run`** — production 흐름의 마지막 SAA-level signal 이며 product allocation 의 자연스러운 target.

> Override 가능: R-1G CLI 에 `--target-source {asset_weights_dry_run | taa_target_weights | manager_override}` 옵션을 두되, default = `asset_weights_dry_run`.

---

## 4. Required Adapter Design (core 수정 0)

### 4.1 흐름

```
R-1F.2 dry-run JSON  +  manager_selected_saa JSON  +  baseline portfolio JSON
                                  │
                                  ▼
            R-1G CLI: run_manager_selected_reselection
                                  │
   ┌──────────────────────────────┼──────────────────────────────┐
   ▼                              ▼                              ▼
target_asset_weights         UniverseTool.run()            TAAResult 재구성
  = asset_weights_dry_run    (DB/file repo)                 (PortfolioBuilder 호출용)
                                  │                              │
                                  ▼                              │
                            UniverseResult                       │
                                  │                              │
                                  ▼                              │
                ProductSelectionTool(uni, cfg, ptype)            │
                  .run(target_asset_weights)                     │
                                  │                              │
                                  ▼                              │
                          ProductSelectionResult ◀───────────────┘
                                  │
                                  ▼
                PortfolioBuilder.build(taa, sel, ...)
                                  │
                                  ▼
                 dry-run portfolio JSON + comparison md
                       (별도 dir: db_*_r1g_reselection)
```

### 4.2 Adapter 구성요소

| 구성 | source |
|---|---|
| `target_asset_weights` (pd.Series) | R-1F.2 dry-run JSON `asset_weights_dry_run` |
| `ProductRepository` | 기존 `_make_market_and_product_repos()` 재사용 (DB / file) |
| `universe_config` | `ConfigLoader.load_universe_config()` (= `universe_filter.yaml`) |
| `classifier` | `ProductClassifier(load_rules(yaml))` |
| `product_type` | manager_selected_saa.selection_input.portfolio_type |
| `TAAResult` (PortfolioBuilder 인자) | **재구성**: `saa_weights=target_asset_weights`, `taa_weights=target_asset_weights`, `tilts=0`, `diagnostics={"method": "r1g_target_substitute"}` (projection 은 R-1F.2 에서 이미 적용됨) |
| `single_product_max_weight` / `bucket_drift` 등 | 기존 yaml 그대로 |

### 4.3 핵심 안전 원칙

- **selection core 무수정** — `ProductSelectionTool.run(asset_weights)` 호출만.
- **production yaml 무수정** — read-only.
- **별도 output dir** — `out/db_{etf,fund}_relaxed_e62_r1g_reselection/`.
- **baseline portfolio JSON 무수정** — sha256 검증.
- **`tests/_phase_e62_baseline.json` sha256 무수정** — bit-identical regression test 유지.
- **manager_selected_saa 별도 layer 유지** — 기존 `saa_diagnostics.saa_weights` 보존, R-1G 결과는 `manager_override_saa` 로만 라벨링.

---

## 5. R-1G Output Contract

### 5.1 Output paths

```
out/db_etf_relaxed_e62_r1g_reselection/
├── portfolio_etf_20260513.json
└── product_reselection_compare_etf_20260513.md

out/db_fund_relaxed_e62_r1g_reselection/
├── portfolio_fund_20260513.json
└── product_reselection_compare_fund_20260513.md
```

### 5.2 JSON `meta` 필수 플래그 (R-1G 산출)

| flag | default 값 | 정책 |
|---|---|---|
| `schema_version` | `"r1g.1"` | R-1G 식별 |
| `production_applied` | **false** | 강제 |
| `dry_run_only` | **true** | 강제 |
| `manager_override_saa_layer` | **true** | 강제 |
| `product_allocation_method` | **`"full_reselection"`** | R-1G 식별 |
| `valid_asset_level_dry_run` | **true** | TAA + projection 이미 R-1F.2 에서 적용 |
| `valid_product_level_portfolio` | **true (조건부)** | `product_weight_sum_valid` 가 true 일 때만 |
| `product_weight_sum_valid` | **true (목표)** | `\|sum − 1.0\| ≤ 1e-3` |
| `product_weight_sum` | float (~1.0) | 실제 값 |
| `implementation_ready` | **`"review_required"`** (string) 또는 **false** | **운용역 review 전이면 absolute true 금지** |
| `sign_off_required_for_production` | **true** | 강제 |
| `needs_full_product_reselection` | **false** | R-1G 가 해소 |
| `needs_selection_rerun_assets` | `[]` (목표) | 해소된 경우 빈 list |

### 5.3 `implementation_ready` 의 신중한 처리 (사용자 지시)

> "product sum이 1.0이어도 바로 true로 두지 말고, 운용역 review 전이면 'review_required' 또는 false 를 유지하는 쪽을 검토."

**채택**: `implementation_ready: "review_required"` (string) 을 default 로. boolean 자리에 string 을 두면 downstream 의 `if implementation_ready:` 가 truthy 로 잡힐 위험이 있으므로, **`implementation_ready: false` + 별도 필드 `implementation_review_status: "review_required"`** 로 분리 권장.

대안 (R-1G 구현 turn 결정):

| option | flag 조합 |
|---|---|
| (a) 단순 | `implementation_ready: false` + `implementation_review_status: "review_required"` (별도 필드) |
| (b) trinary | `implementation_ready: "review_required" \| "approved" \| "rejected" \| false` (string union) |

**default: (a)** — boolean 의 명확성 보존.

### 5.4 추가 필드 (R-1G 산출물)

| 필드 | 의미 |
|---|---|
| `source_manager_selected_saa_json` | R-1F.1 결과 path + sha256 |
| `source_r1f2_dry_run_json` | R-1F.2 결과 path + sha256 (target_asset_weights 추적) |
| `baseline_portfolio_json` | path + sha256 |
| `target_asset_weights` | dict[asset_key, float] (= R-1F.2 `asset_weights_dry_run`) |
| `target_source_field` | `"asset_weights_dry_run"` (또는 override 시 다른 값) |
| `universe_source` | `db` / `file` + db_source 정보 |
| `asset_allocation` | R-1G product selection 결과 기반 자산별 합산 |
| `product_allocation` | R-1G 신규 선정 product 리스트 |
| `selection_diagnostics` | `unfilled_by_asset_class` / `n_picks` / `warnings` / `scored_products` (E-11A 호환) |
| `comparison_to_r1f2_proportional` | proportional scaling 결과 vs full reselection 결과 비교 요약 |
| `comparison_to_baseline_max_sharpe` | baseline 결과 vs R-1G 비교 요약 |
| `needs_selection_rerun_assets` | (목표 빈 list — 단 universe coverage 부족 자산 잔여 가능, 그 경우 명시) |
| `warnings` | universe 부족 (예: us_high_yield 2건만) / cap 충돌 등 |

### 5.5 `valid_product_level_portfolio` 단언 조건

R-1G 산출이 `true` 가 되려면 **모두** 만족:

1. `product_weight_sum_valid == true` (|sum - 1.0| ≤ 1e-3)
2. `needs_selection_rerun_assets == []`
3. **모든** target asset (target_w > 0) 에 대해 `n_picks >= 1`
4. `selection_diagnostics.unfilled_total ≤ tolerance` (R-1G turn 에서 tolerance 확정 — 안 0.01 ~ 0.05)

위 조건 중 하나라도 어기면 `valid_product_level_portfolio = false` + `warnings` 에 사유 추가.

---

## 6. R-1G Comparison Report 설계

### 6.1 비교 대상 3종

| label | source |
|---|---|
| **A. baseline max-Sharpe portfolio** | `out/db_{etf,fund}_relaxed_e62/portfolio_{type}_20260511.json` |
| **B. R-1F.2 proportional scaling dry-run** | `out/db_{etf,fund}_relaxed_e62_r1e_dryrun/portfolio_{type}_20260513.json` |
| **C. R-1G full re-selection dry-run** | (본 R-1G 산출) `out/db_{etf,fund}_relaxed_e62_r1g_reselection/portfolio_{type}_20260513.json` |

### 6.2 비교 dimension

| dimension | A | B | C | 비고 |
|---|---|---|---|---|
| asset weights (final) | baseline | R-1F.2 projection | R-1G 결과 자산 합산 | B 와 C 는 동일해야 (같은 target_asset_weights) |
| product_weight_sum | 1.0 | 1.4448 / 0.7209 | ~1.0 (목표) | **C 의 정합성 검증 핵심** |
| product count (n_picks) | 자산당 1~3건 | 비례 scaling → 비정상 | 자산당 1~3건 (full reselection) | C 의 unfilled 표시 |
| 신규 편입 자산 상품 | dm_ex_us 0건, hy 0건 | scaling 불가 | dm_ex_us / hy 자산의 신규 선정 product 리스트 | R-1G 의 핵심 효과 |
| top changed products | — | scaling 왜곡 | A 대비 +/- 추가/제거 product 리스트 | 운용역 review 입력 |
| 자산군별 상품 수 | universe_diagnostics 동일 | 동일 | 동일 | universe 자체는 미변경 |
| ETF/Fund universe coverage | 동일 | 동일 | 동일 | repo 동일 |
| selection limitation 해소 여부 | n/a | needs_full_product_reselection=true | **needs_full_product_reselection=false 목표** | R-1G 의 의의 |
| remaining warnings | baseline 의 잔여 warning | 없음 | universe 부족 (us_high_yield 2건) 등 표기 | R-1G 의 새 한계 명시 |

### 6.3 Comparison md 구조 (제안)

```
# Manager-Selected SAA Product Re-selection Comparison ({type}, R-1G)

> validity warning + R-1G flags
> baseline / R-1F.2 / R-1G 3-way 비교

## §1. Selected Candidate (recap)
## §2. Target Asset Weights (= R-1F.2 dry-run final)
## §3. Product Selection Result Summary
  - product_weight_sum (3 columns)
  - product count per asset
  - newly added assets' products
## §4. Top Changed Products (vs baseline)
  - added / removed / weight-shifted
## §5. Selection Diagnostics
  - n_picks, unfilled, warnings, manager cap impacts
## §6. Universe Coverage Note
  - asset 별 universe count (특히 us_high_yield=2 처럼 적은 자산)
## §7. 운용역 검토 포인트
## §8. Limitations / 잔여 한계
  - us_high_yield universe 부족 시 fallback 사용 표기
  - implementation_ready=false / review_required 유지 사유
```

---

## 7. Required Tests for Future R-1G Implementation

R-1G 구현 시 최소 포함:

| # | test | scope |
|:---:|---|---|
| T-1 | valid manager_selected_saa + R-1F.2 dry-run JSON → R-1G output 생성 (ETF) | happy path |
| T-2 | 동일 (Fund) | happy path |
| T-3 | `product_weight_sum_dry_run` ≈ 1.0 (target tolerance 1e-3 이내) | core invariant |
| T-4 | `needs_selection_rerun_assets == []` (모든 target>0 자산이 selection 성공) | core invariant |
| T-5 | `dm_ex_us_equity` 에 product 가 1건 이상 allocated (target > 0 이므로) | R-1F.2.1 한계 해소 검증 |
| T-6 | `us_high_yield` 에 product 가 1건 이상 allocated (universe 2건 fallback 가능) | 동일 |
| T-7 | `valid_product_level_portfolio == true` (조건 충족 시) | flag |
| T-8 | `production_applied == false` (강제) | safety |
| T-9 | `dry_run_only == true` (강제) | safety |
| T-10 | `implementation_ready == false` (또는 `"review_required"`) — 운용역 sign-off 전 강제 | safety (사용자 지시) |
| T-11 | baseline portfolio JSON sha256 unchanged | mutation guard |
| T-12 | config (`universe_filter.yaml` / `taa_policy.yaml`) sha256 unchanged | mutation guard |
| T-13 | Decision Register count (14) 변경 없음 | governance |
| T-14 | E-series baseline (`_phase_e62_baseline.json`) sha256 unchanged | regression |
| T-15 | 80:20 distance metric 부활 없음 (output JSON / md grep) | R-1B.2 정합 |
| T-16 | manager_selected_saa JSON / R-1F.2 JSON mutation 없음 | mutation guard |
| T-17 | R-1G output dir 가 production / baseline dir 와 다름 | safety |
| T-18 | universe 부족 자산 (us_high_yield 등) 시 fallback warning 출력 | universe 한계 가시화 |
| T-19 | `target_source_field == "asset_weights_dry_run"` (default) | input contract |
| T-20 | ref_max_sharpe / ref_80_20_equal_intra_bucket 가 target 으로 들어오면 차단 (recursive check from R-1F.1) | safety |

---

## 8. Non-goals (R-1G 범위 밖)

```
✗ production SAA 교체
✗ TAA / projection / selection / portfolio_builder core 로직 수정
✗ config 변경 (universe_filter / taa_policy / asset_mapping / tdf_2060 yaml)
✗ Decision Register count (14) 변경
✗ 기존 production output (`out/db_{etf,fund}_relaxed_e62/`) 덮어쓰기
✗ R-1B.2 ~ R-1F.2.1 산출물 덮어쓰기
✗ 자동 final SAA 확정 / 자동 candidate 추천
✗ 80:20 distance metric 부활 (R-1B.2 영구 제거 정합)
✗ implementation_ready=true 자동 부여 (review_required / false 유지)
✗ E-series baseline 변경
✗ universe 자체 수정 (rules / filter yaml)
```

---

## 9. R-1G Implementation Plan (R-1G.0 승인 후 진입)

### 9.1 구현 후보 파일

```
tdf_engine/optimization/
└── manager_selected_reselection.py     (Adapter + validity check + builder + comparison)

tdf_engine/tools/
└── run_manager_selected_reselection.py (CLI)

tests/
└── test_r1g_manager_selected_reselection.py
```

### 9.2 예상 작업 시간

| 작업 | 예상 |
|---|---|
| Universe repo wiring (재호출) + ProductSelectionTool 어댑터 | 1.5h |
| TAAResult 재구성 + PortfolioBuilder 호출 | 0.5h |
| Validity flag 계산 + R-1G JSON schema | 0.5h |
| Comparison md (3-way: baseline / R-1F.2 / R-1G) | 1.5h |
| Tests 20건 | 1.5h |
| ETF/Fund dump + sanity | 0.5h |
| **합계** | **~6h (1~2 turn)** |

---

## 10. 구현 시 Blocker / Risk

| # | 항목 | 영향 | 완화 |
|:---:|---|---|---|
| **B-1** | DB 의존 — `UniverseTool.run()` 이 production repo 호출 필요 | DB 미가용 시 R-1G 실행 불가 | (a) FileProductRepository 로 fallback (b) baseline build 시 universe pickle dump 추가 (별도 turn) |
| **B-2** | us_high_yield universe 2건만 — core (1) + satellite (2) 채우기 부족 | n_picks < 3 → unfilled / fallback weight | warning 출력 + needs_selection_rerun_assets 에는 미포함 (universe 자체 한계) |
| **B-3** | `single_manager_max_weight` 충돌 — re-selection 후 한 manager 비중 cap 초과 가능 | manager scale 적용 → 후순위 미선정 product 증가 | 기존 `_enforce_manager_cap` 자동 처리, warning 보존 |
| **B-4** | TAAResult 재구성 — PortfolioBuilder 가 `taa.taa_weights` 와 `taa.saa_weights` 둘 다 요구. `tilts=0` 으로 둘 다 동일 series 면 builder 가 정상 작동? | 미검증 | R-1G 구현 시 unit test 로 첫 검증 (T-1 happy path) |
| **B-5** | `valid_product_level_portfolio=true` 단언 시 cascade 위험 | downstream 코드가 이를 보고 잘못 production reflect | `implementation_ready=false` + `sign_off_required_for_production=true` 두 flag 로 이중 차단 |
| **B-6** | Fund universe coverage 차이 | ETF / Fund 결과 다를 가능성 (지금까지는 동일했음) | R-1G turn 에서 ETF/Fund 각각 sanity 후 비교 md 에 명시 |
| **B-7** | E-11A `scored_products` telemetry — 새 universe 결과 가 baseline 과 다를 수 있음 | E-11A bit-identical baseline 검증 영향 가능성 | R-1G 출력은 **별도 디렉토리** — `_phase_e62_baseline.json` 미접촉. T-14 로 강제. |
| B-8 | as_of_date 정합 — R-1F.2 가 20260513, baseline 이 20260511. universe load 의 as_of_date 어떤 것을 쓸지 | as_of 차이로 universe 변동 | default = baseline (20260511) — universe 변경 최소화. R-1G CLI 에 `--universe-as-of` override 가능. |

---

## 11. Hard Requirements (R-1G.0 turn)

| 영역 | 변경 |
|---|:---:|
| 본 spec 문서 신규 작성 | ✓ |
| `tdf_engine/` 코드 | ✗ |
| `tdf_engine/config/*.yaml` | ✗ |
| `tests/` | ✗ |
| `out/` 산출물 | ✗ |
| `docs/investment_decision_register.md` | ✗ |
| Decision Register total count (14) | ✗ |
| E-8 ~ E-12 산출물 | ✗ |
| R-1B.2 ~ R-1F.2.1 산출물 (opportunity_set / cloud_review / sweet_pool / shortlist / search / Final Manager Review Packet / manager_selected_saa / R-1F.2 dry-run) | ✗ |
| `tests/_phase_e62_baseline.json` | ✗ |
| operating_mode | ✗ `relaxed_diagnostic` 유지 |
| 80:20 distance metric | ✗ 부활 없음 |
| 자동 final SAA 확정 / 자동 candidate 추천 | ✗ |

---

## 12. 한 줄 요약

> **R-1G.0 = spec + entrypoint probe only.** 기존 `ProductSelectionTool.run(asset_weights)`
> 가 임의 asset_weights 입력을 이미 지원 → **selection core 무수정 R-1G 가능**. Target =
> R-1F.2 `asset_weights_dry_run`. 유일한 외부 의존 = `UniverseTool.run()` 재호출 (DB 또는
> file repo). 출력은 별도 dir, `production_applied=false / dry_run_only=true /
> manager_override_saa_layer=true / implementation_ready=false (또는
> implementation_review_status="review_required")`. 핵심 risk = (B-1) DB 가용성 /
> (B-2) us_high_yield universe 2건 한계 / (B-5) validity flag cascade 방지. R-1G 진입은
> 사용자 sign-off 후.
