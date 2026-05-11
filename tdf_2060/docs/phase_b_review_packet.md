# Phase B Review Packet — TDF 2060 Minimal End-to-End

작성일: 2026-05-07 (Phase B.5 + B.5+ + C-pre 반영) · 대상 리뷰어: OpenAI (`gpt-4.1-mini`).

> **Phase B.5**: Fund `product_weight_sum=0.6929` 이슈 해소. 미배분 원인 진단 + 3단계 fallback (자산군 pro-rata → bucket sibling → cash placeholder) + Validator 강화. ETF/Fund 모두 `product_weight_sum=1.0` closure. §12 참조.
>
> **Phase B.5+**: fallback이 SAA/TAA 의도를 얼마나 흐렸는지 정량화. `target_asset_weights / final_asset_weights / asset_weight_drift / drift_by_bucket / fallback_absorbers` 노출 + `quality_status: clean | warning | review_required` 분리. §13 참조.
>
> **Phase C-pre**: classifier 룰 yaml 외부화 + 채권 펀드 룰 보강 + `quant_grade_policy` 옵션화 (`hard_filter | score_penalty | disabled`). Fund의 `no_candidates_in_universe` 사각지대 해소. Fund quality_status `review_required → warning`, `max_abs_asset_drift 19.98% → 0.00%`. §14 참조.

---

## 0. TL;DR

- **목표**: ETF/펀드 TDF 2060 포트폴리오를 산출하는 minimal end-to-end 파이프라인 구축. DB 연결과 고도화는 의도적 제외.
- **구현 완료 범위**: CMA → MVO SAA → Regime → TAA → Universe (yaml-driven 룰) → Selection (quant_grade_policy) → Portfolio (fallback + quality) → CSV/JSON.
- **테스트**: `pytest tests/` → **96 passed** (A 44 + B 33 + B.5 5 + B.5+ 7 + **C-pre 7**).
- **실제 실행**: ETF/Fund 모두 `quality_status: warning`, `max_abs_asset_drift: 0.00%`, `product_weight_sum=1.0`, `constraints_passed=True`. 실 `Advisory/` 데이터로는 ust30 부재로 ValueError(의도된 (b) 정책).
- **C-pre 핵심 효과**: Fund `no_candidates_in_universe` 사각지대 해소 (kr_treasury_10y 0→4, us_treasury_30y 0→10, us_high_yield 1→10). Fund `quality_status: review_required → warning`, `max_abs_asset_drift: 19.98% → 0.00%`. cross-bucket reallocation 다수 → 0건.
- **Known limitation**: ust30 fixture만 (Phase C SCIP 매핑 대기), classifier 룰은 키워드 기반(소수 모호 케이스 잔존), `final_asset_bounds`는 warning만, GlidePath xlsx 미연동, reporting 모듈 비어있음.
- **리뷰 핵심**: `optimization/cma.py`, `optimization/optimizer.py`, `taa/overlay.py`, `universe/classifier.py` (yaml-driven), `selection/scoring.py` + `selection/tool.py` (grade policy), `portfolio/fallback.py`, `portfolio/quality.py`, `portfolio/validator.py`, `portfolio/builder.py`, `tools/build_portfolio.py`, `config/universe_classification.yaml` (신규). minimal end-to-end 검증용 — 운영 모델 아님.

---

## 1. Phase B Scope

### 1.1 목표

| # | 항목 | 구현 위치 |
|---|---|---|
| 1 | file/source-root 기반 repository | `repositories/file_repositories.py` (Phase A 그대로 사용) |
| 2 | GlidePath / reference_weights 로딩 | `tdf_2060.yaml.reference_weights` → `OptimizationTool._resolve_warm_start` |
| 3 | Asset assumption / covariance 구성 | `optimization/cma.py::CapitalMarketAssumptionBuilder.build` |
| 4 | MVO 기반 SAA 산출 | `optimization/optimizer.py::MVOOptimizer.optimize` (max Sharpe / SLSQP) |
| 5 | Regime 기반 TAA overlay | `regime/tool.py::RegimeAnalysisTool` + `taa/overlay.py::TAAOverlayEngine` |
| 6 | ETF/Fund universe filtering | `universe/tool.py::UniverseTool` |
| 7 | 자산군별 대표 상품 선정 | `selection/{scoring,selector,tool}.py` |
| 8 | 최종 portfolio csv/json 출력 | `tools/build_portfolio.py::write_outputs` |
| 9 | CLI build_portfolio 연결 | `tools/build_portfolio.py::main` |
| 10 | E2E 테스트 | `tests/test_e2e_{etf,fund}.py` |

### 1.2 제외 범위 (의도적)

- DB 연결 (SCIP/dt/solution/cream) → Phase C
- 고도화된 리포팅 (HTML/PDF/대시보드)
- 실시간 데이터 연동
- 추가 MVO 목적함수 연구 (utility/min_volatility/ERR 등은 stub 유지)
- Regime 모델 고도화 (per_asset_region, 동적 window 등)
- 실제 운용 승인 workflow (검토/승인/실행)

---

## 2. High-Level Pipeline

```
GlidePath ────────────────────────────────────────────────┐
  (tdf_2060.yaml.reference_weights)                       │
                                                          ▼
Asset_rt_vol + Corr_mat ──► CapitalMarketAssumptionBuilder
                              │
                              ▼  CapitalMarketAssumption (E[R], σ, ρ, Σ)
                              ▼
asset_mapping.yaml ────► MVOOptimizer (SLSQP / max_sharpe)
                              │  + warm_start = reference_weights
                              ▼  OptimizationResult.weights  ── SAA
                              ▼
regime_src ─► RegimeAnalysisTool ──► RegimeState (latest)
                              │
                              ▼  taa_policy.yaml.regime_tilts
                              ▼
                       TAAOverlayEngine
                              │  asset_tilts 적용 + cash-neutral
                              ▼  TAAResult.taa_weights
                              ▼
etf_list / fund_list ─► UniverseTool
                              │  filter + ProductClassifier (9 자산군)
                              ▼  UniverseResult.products
                              ▼
                       ProductSelectionTool
                              │  ProductScorer + CoreSatelliteSelector
                              ▼  ProductSelectionResult.selected (DataFrame)
                              ▼
                       PortfolioBuilder.build
                              │  + PortfolioValidator.validate
                              ▼  PortfolioResult
                              ▼
                       write_outputs(output_dir)
                              │
                              ▼
                portfolio_<etf|fund>_<YYYYMMDD>.csv  (product 단위 행)
                portfolio_<etf|fund>_<YYYYMMDD>.json (asset+product+diagnostics)
```

각 단계 객체 키 컬럼:

| 객체 | 핵심 필드 |
|---|---|
| `CapitalMarketAssumption` | `expected_returns: Series`, `volatilities: Series`, `correlation: DataFrame`, `covariance: DataFrame`, `diagnostics: dict` |
| `OptimizationResult` | `weights: Series`, `sharpe: float`, `expected_return`, `volatility`, `constraints_passed`, `diagnostics` |
| `RegimeState` | `as_of: date`, `region: str`, `placement: float`, `velocity: float`, `regime: Regime` |
| `TAAResult` | `saa_weights`, `taa_weights`, `tilts`, `reasons`, `diagnostics` |
| `UniverseResult` | `raw_count`, `filtered_count`, `products: list[ProductInfo]`, `excluded`, `diagnostics` |
| `ProductSelectionResult` | `selected: DataFrame[asset_key, product_id, fund_code, name, manager, weight, role]`, `diagnostics` |
| `PortfolioResult` | `asset_weights: Series`, `product_weights: DataFrame`, `portfolio_type`, `constraints_passed`, `diagnostics` |

---

## 3. Changed Files Summary

| Area | File | Main change | Review priority |
|---|---|---|---|
| Optimization | `tdf_engine/optimization/cma.py` | `CapitalMarketAssumptionBuilder.build` 신구현 — Asset_rt_vol ffill/% strip, Ticker/Name 매칭, Corr_mat 한글→asset_key reindex, ust30 부재 시 `ValueError` (정책 b) | P0 |
| Optimization | `tdf_engine/optimization/optimizer.py` | `_objective_max_sharpe` 활성, `MVOOptimizer.optimize` 구현 (SLSQP, sum=1, bounds, bucket_sum, region_lb 옵션). 나머지 3개 objective는 stub 유지 | P0 |
| Optimization | `tdf_engine/optimization/tool.py` | `bucket_to_assets` 빌드, `warm_start = reference_weights` 변환, `cma.diagnostics` merge | P1 |
| Regime | `tdf_engine/regime/classifier.py` | `classify_frame` vectorized (`np.where`), NaN 보존 | P0 |
| Regime | `tdf_engine/regime/returns.py` | `AssetReturnCalculator.monthly_returns`, `RegimeReturnAnalyzer.analyze` (월말 timestamp 정규화 후 group-by mean) | P0 |
| Regime | `tdf_engine/regime/tool.py` | `_ensure_date_index` 헬퍼, `RegimeAnalysisTool.run`, `RegimeReturnTool.run` (dataseries label 매칭) | P1 |
| TAA | `tdf_engine/taa/overlay.py` | `TAAOverlayEngine.apply` 신구현 — asset_tilts 적용, cash-neutral 균등 보정, bucket bound + per-asset cap 검증, reasons 기록 | P0 |
| TAA | `tdf_engine/taa/tool.py` | `assets` 인자 추가 → `bucket_by_asset` 매핑 주입 | P2 |
| Universe | `tdf_engine/universe/classifier.py` | `DEFAULT_RULES` 9개 자산군 키워드 룰. `name_excludes`, `kis_mp_categories`, `regions` 조건 결합. 첫 매칭 우선 | P1 |
| Universe | `tdf_engine/universe/tool.py` | `_parse_float`/`_parse_date_yyyymmdd`, `_row_to_product_info`, `UniverseTool.run` (raw → 정규화 → filter → classify) | P1 |
| Selection | `tdf_engine/selection/scoring.py` | `ProductScorer.score` (quant + sharpe + return_3y + log(aum) 가중합), `passes_filter` (grade/aum) | P1 |
| Selection | `tdf_engine/selection/selector.py` | `CoreSatelliteSelector.select` — score 정렬, n_core=1 + n_satellite=2, single_product cap clipping | P1 |
| Selection | `tdf_engine/selection/tool.py` | `ProductSelectionTool.run` (asset_key 그룹핑 → manager cap 비례 축소 → DataFrame 산출) | P1 |
| Portfolio | `tdf_engine/portfolio/builder.py` | `PortfolioBuilder.build` (TAAResult + ProductSelectionResult → PortfolioResult) | P2 |
| Portfolio | `tdf_engine/portfolio/validator.py` | `validate(전체)` — sum + bucket bounds. **asset bounds 검증 의도적 제외** (SAA용 bound 이고 TAA 결과는 별도 통제) | P0 |
| Portfolio | `tdf_engine/portfolio/tool.py` | `PortfolioConstructionTool` orchestrator, factory 패턴으로 `ProductSelectionTool` 주입 | P0 |
| CLI | `tdf_engine/tools/build_portfolio.py` | `main`, `build`, `_build_with_repos`, `write_outputs` (csv: product DataFrame, json: asset_weights+product_weights+diagnostics) | P0 |
| CLI | `tdf_engine/tools/run_optimization.py` | minimal body — OptimizationTool.run + stdout 표 + diagnostics | P2 |
| CLI | `tdf_engine/tools/run_regime.py` | minimal body — RegimeAnalysisTool.run + latest_state | P2 |
| CLI | `tdf_engine/tools/run_regime_return.py` | minimal body — RegimeAnalysisTool + RegimeReturnTool 연결 | P2 |
| CLI | `tdf_engine/tools/run_universe.py` | minimal body — UniverseTool.run + asset_key 별 카운트 | P2 |
| Tests (수정) | `tests/test_optimization_objective_dispatch.py` | `test_objective_fn_not_implemented_yet` → `test_stub_objective_still_not_implemented` (max_sharpe 활성에 맞춤) | P2 |
| Tests (수정) | `tests/conftest.py` | `augmented_source_root`, `augmented_assets` fixture 추가 — Asset_rt_vol/Corr_mat 에 ust30 row/col 주입, asset_mapping ust30 source_names 임시 수정 | P0 |
| Tests (신규) | `tests/test_cma_builder.py` | 4 tests | P0 |
| Tests (신규) | `tests/test_mvo_max_sharpe.py` | 5 tests | P0 |
| Tests (신규) | `tests/test_regime_analysis_tool.py` | 3 tests | P1 |
| Tests (신규) | `tests/test_regime_return.py` | 3 tests | P1 |
| Tests (신규) | `tests/test_taa_overlay.py` | 4 tests | P0 |
| Tests (신규) | `tests/test_product_classifier.py` | 7 tests | P1 |
| Tests (신규) | `tests/test_universe_tool.py` | 3 tests | P1 |
| Tests (신규) | `tests/test_product_selection.py` | 2 tests | P1 |
| Tests (신규) | `tests/test_e2e_etf.py` | 1 test (full pipeline + csv/json 검증) | P0 |
| Tests (신규) | `tests/test_e2e_fund.py` | 1 test | P0 |

---

## 4. Key Design Decisions

### 4.1 GlidePath 처리

- **결정**: `tdf_2060.yaml.reference_weights` 9 자산군 비중을 단일 vintage(2060)의 baseline으로 사용. `OptimizationTool._resolve_warm_start`가 SLSQP의 x0으로 전달.
- **이유**: `0. 정리 - GlidePath 값.xlsx` 파일이 "DOCUMENT SAFER V2010 R2" DRM 보호되어 Python(openpyxl/xlrd)으로 직접 읽기 불가. HANDOFF.md도 "본 단계는 2060 단일 vintage만 다룸"이라고 명시.
- **리스크**: 다른 vintage(2030/2040/2050)는 미지원. reference_weights가 사용자에 의해 수동 갱신되어야 함.
- **향후 개선**: Phase C에서 DRM 해제된 GlidePath 데이터 연동 또는 `config/glidepath.yaml` 신설하여 vintage별 SAA 정의.

### 4.2 ust30 누락 처리

- **결정**: 사용자 결정 #10 = (b) 강한 error. `CapitalMarketAssumptionBuilder.build`에서 `required=True` + `source_names.optimization is None`이면 즉시 `ValueError`. silent fallback / 자동 proxy 사용 금지.
- **이유**: `asset_mapping.yaml`의 `fallback_policy: explicit_proxy_only` 정책과 정합. 데이터 무결성을 우선. ust30은 Phase C에서 SCIP DB로 채울 예정 (사용자 명시).
- **happy-path 처리**: `tests/conftest.py::augmented_source_root` fixture가 임시 디렉토리에 ust30 row(`USGG30YR Index`, σ=13.0%, E[R]=3.50%) + Corr_mat 행/열을 주입. 실제 운영 수치 아님 — placeholder.
- **운영 관점**:
  - 실 `Advisory/` 데이터로 CLI 실행 시 정확히 ValueError로 멈춤 (의도된 동작, returncode≠0).
  - happy-path는 fixture에서만 검증.
  - Phase C에서 `DBMarketDataRepository`가 SCIP `back_dataset` (예: id 후보 결정 필요)를 통해 채워야 정상 동작.

### 4.3 MVO 목적함수

- **결정**: max Sharpe만 활성. SLSQP. 제약: sum=1 (eq), per-asset bounds (`tdf_2060.yaml.weight_bounds`), bucket sum bounds (equity 0.75~0.85, fixed_income 0.15~0.25), region_lower_bounds(옵션, Phase B 비활성).
- **warm_start**: `reference_weights`를 그대로 x0으로 변환 (CMA에 존재하는 자산만). 없으면 equal weight.
- **dispatch**: `OBJECTIVE_REGISTRY` dict 유지. `utility / min_volatility / max_return_under_risk_limit`는 `NotImplementedError` stub.
- **현재 한계**:
  - `risk_aversion_lambda`, `target_volatility` 미사용.
  - `multi_start: 5` config 값이 있지만 실제는 단일 시작점.
  - ERR 제약(`err_enabled=False`)은 Phase A 그대로.
  - `region_lower_bounds`는 ConstraintSet에 인자만 있고 yaml에서는 비활성.

### 4.4 TAA Overlay

- **결정**: regime별 `asset_tilts` 그대로 적용, 합이 0이 아니면 자산 수에 균등 분배해 cash-neutral 보정. bucket bound (`equity_total_min/max`, `fixed_income_total_min/max`)와 `per_asset_max_tilt` 위반 시 `diagnostics["violations"]`에 로그 + warning. 강한 error는 안 함.
- **`reasons`**: regime의 `asset_tilts`에 등장한 자산만 reason 텍스트 기록.
- **Validator에서 weight_bounds 검증 제거**: `tdf_2060.yaml.weight_bounds`는 SAA(MVO)의 제약. TAA는 그 위에 ±tilt를 적용하므로 SAA 상한을 약간 넘는 결과가 정상적일 수 있음. 예: us_high_yield SAA=0.07 (max), regime 1 tilt +0.01 → TAA=0.08. 따라서 `PortfolioValidator.validate`는 sum + bucket만 체크.
- **리스크**:
  - cash-neutral 균등 보정이 자산 수에 비례 분배 → 비중이 작은 자산도 동일 +/− adj. bucket 비례나 가중치 비례가 더 자연스러울 수 있음.
  - bucket cap 위반 시 강한 강제 보정 없이 warning만. 운영에서는 강제 clipping이 필요할 수 있음.

### 4.5 Universe Classification

- **결정**: `universe/classifier.py::DEFAULT_RULES` 코드 룰. 우선순위(첫 매칭 우선): `us_high_yield → us_treasury_30y → kr_treasury_10y → kr_aggregate_bond → us_growth_equity → us_value_equity → em_equity → dm_ex_us_equity → kr_equity`. 키워드 + KIS MP 카테고리 + 지역 + name_excludes 결합.
- **이유**: 키워드는 펀드명에서 가장 명확. 가장 좁은 카테고리(HY → 30Y → 10Y → 종합채)부터 우선.
- **오분류 가능성**:
  - 미국 S&P500 ETF (성장/가치 키워드 없음, 지역="미국") → `us_growth_equity` 룰의 키워드 미매칭, `us_value_equity`도 미매칭 → 결국 `dm_ex_us_equity`(글로벌주식+regions 미국 누락)도 미매칭 → unclassified로 빠질 가능성. 실제 데이터 검증 필요.
  - "한국투자ACE국채선물" 같은 채권 ETF는 `kr_treasury_10y`/`kr_aggregate_bond` 둘 다 미매칭 가능.
  - "다우존스" 미국 가치주 vs 배당주 분리 모호.
- **현재 출력**: ETF 932→572 통과. 자산군별 카운트는 `run_universe`로 직접 검토 가능.
- **향후**: 룰 외부화(`config/classification_rules.yaml`) + 미매칭 자산을 사람이 검토할 수 있는 리포트.

### 4.6 Product Selection

- **결정**:
  - score = `0.4*quant_score + 0.3*sharpe_1y + 0.2*return_3y + 0.1*log1p(aum)`. 결측치는 0.
  - n_core=1, n_satellite=2 고정. core_ratio=(0.60, 0.80) → core 비중에 0.80 적용.
  - `single_product_max_weight` clipping (overflow는 미배분, 자산군 내 후보 부족 시그널).
  - manager cap 위반 시 비례 scale 적용 (운용사 단위 합계 = cap이 되도록).
- **현재 한계**:
  - score weight가 임의값. 백테스트 검증 전. 튜닝 필요.
  - `quant_score`가 `정량평가` 컬럼(0~100점) 그대로 사용 → log(aum)와 스케일 차이로 score 지배.
  - core 비중을 `core_ratio[1]` 고정 사용 → 항상 80%. 자산군 특성/유동성 미반영.
  - manager cap 위반 시 비례 축소만 하고, 누락된 비중을 다른 운용사로 재배정하지 않음 → 결과 sum이 자산 weight보다 작아질 수 있음.

---

## 5. Current E2E Behavior

### 5.1 실행 명령어 (augmented 시나리오)

```bash
cd C:/Users/user/Downloads/python/Advisory/tdf_2060
# (augmented_source_root와 동등한 처리: ust30 row를 Asset_rt_vol/Corr_mat에 주입,
#  asset_mapping의 ust30.source_names.optimization을 'USGG30YR Index'로 임시 수정)

python -m tdf_engine.tools.build_portfolio \
    --source-root <augmented_root> \
    --config-dir <augmented_config> \
    --product-type etf \
    --output-dir <out_dir>
```

### 5.2 ETF 시나리오 결과 (augmented)

| 항목 | 값 |
|---|---|
| Universe | 932 raw → **572 passed** (excluded 360) |
| 9 자산군 매핑 카운트 | etf 절반 이상이 분류됨 (정확 카운트는 `run_universe` 출력) |
| SAA Sharpe | **0.5642** (rf=0.030 가정) |
| SAA weight sum | 1.000000 |
| equity bucket | 79.00% (75~85 OK) |
| fixed_income bucket | 21.00% (15~25 OK) |
| Regime | P=+0.7223, V=+0.0586, as_of=2026-02-01 → **Regime 1 (Expansion / Acceleration)** |
| TAA tilt sum | 0.000000 (cash-neutral) |
| TAA violations | 0 |
| Selection | 26 picks (자산군 9 × core 1 + satellite 2 ≈ 27, 일부 자산군 후보 부족) |
| Selection weight sum | 0.88 (asset weight 합 = 1.0 중 88%만 product에 매핑됨; manager cap clipping 등 영향) |
| `constraints_passed` | True |
| 파일 출력 | `portfolio_etf_20260507.csv`, `portfolio_etf_20260507.json` |

### 5.3 Fund 시나리오 결과 (augmented)

| 항목 | 값 |
|---|---|
| Universe | 781 raw → 통과 (정확 카운트는 `run_universe` 출력) |
| asset_weight sum | 0.9999999999999999 |
| product_weight sum | **0.6929** (자산군 일부에서 후보 부족 또는 manager cap 영향) |
| `constraints_passed` | True |
| 파일 출력 | `portfolio_fund_20260507.csv`, `portfolio_fund_20260507.json` |

> **주의**: `product_weight_sum < asset_weight_sum`인 점은 일부 자산군에서 manager cap clipping 또는 후보 부족으로 비중 미배분이 발생했음을 시사. 운영 적용 전 자산군 매칭 정확도와 cap 정책 재검토 필요.

### 5.4 실제 `Advisory/` 데이터 (ust30 row 없음)

```
ValueError: required 자산의 source_names.optimization 이 None 입니다
(asset_mapping.yaml 의 fallback_policy=explicit_proxy_only 정책 위반): ['us_treasury_30y'].
```

→ 의도된 동작. returncode≠0. Phase C DB 연결 후 자동 해소 예상.

---

## 6. Test Result Summary

### 6.1 전체

```
$ pytest tests/ -q
77 passed in 2.02s
```

- Phase A 기존: **44** (모두 그대로 통과)
- Phase B 신규: **33**
- 총: **77**

### 6.2 신규 테스트 분포

| Test file | Count | Purpose |
|---|---:|---|
| `test_cma_builder.py` | 4 | CMA 9자산 빌드 / ust30 누락 시 ValueError / diagnostics 메타데이터 / covariance 대칭성 |
| `test_mvo_max_sharpe.py` | 5 | weights sum=1 / per-asset bounds / bucket bounds / constraints_passed / objective_name |
| `test_regime_analysis_tool.py` | 3 | G7 default latest_state / classify_frame ↔ scalar 일관성 / unknown region ValueError |
| `test_regime_return.py` | 3 | monthly_returns drop 첫 행 / group-by mean / Tool 통합 (월말 정규화 후) |
| `test_taa_overlay.py` | 4 | regime 1 equity bucket 증가 / 4 regime 모두 sum=1 / per_asset cap / reasons attached |
| `test_product_classifier.py` | 7 | growth/value/kr/em/treasury/HY/unmatched 매핑 케이스 |
| `test_universe_tool.py` | 3 | etf/fund 실행 + diagnostics 노출 |
| `test_product_selection.py` | 2 | 단순 universe selection / unfilled_asset 기록 |
| `test_e2e_etf.py` | 1 | full pipeline + sum/bucket + csv/json payload 검증 |
| `test_e2e_fund.py` | 1 | full pipeline + sum 검증 |

### 6.3 수정 테스트

- `tests/test_optimization_objective_dispatch.py::test_stub_objective_still_not_implemented`: max_sharpe 활성화에 맞춰 stub 검증을 utility/min_volatility/max_return_under_risk_limit 로 변경.

---

## 7. Review Focus for OpenAI

### P0 — correctness

1. **`optimization/cma.py::CapitalMarketAssumptionBuilder.build`**
   - Asset Class ffill, σ/E[R] `%` strip 파싱이 Asset_rt_vol의 모든 케이스를 커버하는지.
   - Ticker / Name 이중 lookup 우선순위 (`by_ticker` 먼저)가 잘못된 매칭을 일으키지 않는지.
   - Corr_mat 한글 인덱스 → asset_key reindex가 누락 자산을 명확히 검출하는지 (`corr_missing_in_corr`).
   - ust30 (b) 정책 ValueError 메시지가 운영자가 즉시 조치할 수 있을 만큼 구체적인지.

2. **`optimization/optimizer.py::MVOOptimizer.optimize`**
   - SLSQP의 `bounds` + `constraints` (eq + ineq) 조합이 의도대로 동작하는지.
   - `bucket_to_assets` lambda closure에서 `lb=lb` default 캡처가 모든 bucket에 일관되게 작동하는지.
   - `weight_sum_must_equal`이 1.0이 아닌 경우(예: 향후 cash 비중 분리)에도 잘 동작하는지.
   - `init.sum() <= 0`일 때 equal weight fallback이 의도한 동작인지.

3. **`taa/overlay.py::TAAOverlayEngine.apply`**
   - cash-neutral 보정이 `len(tilts)`에 균등 분배되는 것이 정책으로 맞는지 (bucket 비례가 더 자연스러울 수도).
   - per_asset_max_tilt 검증이 `tilt`(after cash-neutral adj)에 적용되는데, 사용자 의도에는 정책상 정의된 raw tilt에 적용되어야 할 수도.
   - bucket bound 위반 시 warning만 하는 정책이 적절한지.

4. **`portfolio/validator.py::PortfolioValidator.validate`**
   - asset bounds 체크 의도적 제외(SAA용 bound와 TAA 결과를 분리)가 운영 검증 관점에서 충분한지.
   - bucket bound가 `taa_diagnostics.bucket_sums`에 의존하는데 이게 None인 경우 silently 스킵되는 이슈는 없는지.

5. **E2E determinism**
   - `tests/test_e2e_etf.py`, `tests/test_e2e_fund.py`가 augmented_source_root 사용 시 항상 같은 결과를 내는지. SLSQP는 init과 numerical 환경에 sensitive할 수 있음.

### P1 — design quality

1. **SAA bound vs TAA bound 분리**: Validator가 weight_bounds를 안 보는 게 적절한가, 아니면 별도 `taa_bounds_per_asset`을 두어야 하는가.
2. **Repository / Tool / Orchestrator 경계**:
   - `RegimeReturnTool`은 `regime_series`를 인자로 받음(외부 `RegimeAnalysisResult.regime`에 의존). 이 의존을 그대로 유지할지, Tool 자체가 RegimeAnalysisTool을 호출하게 묶을지.
   - `PortfolioConstructionTool.selection_tool_factory`는 ProductSelectionTool 시그니처(`UniverseResult` 필요) 때문에 factory 패턴인데, 명시적 단계로 분리하는 게 더 readable일지.
3. **`ProductInfo` 정규화 위치**: `universe/tool.py::_row_to_product_info`가 raw row 정규화 책임을 짊. Repository에서 이미 정규화 후 ProductInfo로 넘겨주는 게 더 자연스러운지.
4. **`ProductScorer`의 임의성**: scoring weight 0.4/0.3/0.2/0.1이 백테스트 미검증. 적어도 ETF/Fund별 다른 default 또는 yaml 외부화가 필요한지.
5. **`ProductClassifier` 룰의 코드 위치**: 9자산군 룰을 코드(`DEFAULT_RULES`)에 둔 것이 적절한지, yaml로 빼야 하는지.

### P2 — future extensibility

1. **Phase C DB 연결**:
   - `repositories/db_repositories.py`(현 NotImplementedError)에 `DBMarketDataRepository`/`DBProductRepository` 구현 시, `load_asset_rt_vol/load_corr_matrix` 시그니처가 그대로 사용 가능한지.
   - SCIP `back_datapoint.data` JSON blob 파싱 → DataFrame 형태가 file repo와 호환되는지.
   - asset_mapping.yaml의 `db_dataset_id`가 모든 자산에 대해 채워질 때, `CapitalMarketAssumptionBuilder`가 별도 분기 없이 동작 가능한지.
2. **GlidePath 엑셀 연동**: DRM 해제 후 별도 `GlidePathLoader`를 `tdf_engine/config/glidepath.py`에 두고 vintage별 reference_weights를 주입하는 hook 위치.
3. **reporting 확장**: 현재 `tdf_engine/reporting/`은 비어있음. PortfolioResult → HTML/PDF/대시보드 변환 진입점.
4. **regime 모델 고도화**: per_asset_region 모드, 동적 window 등은 `RegimeAnalysisTool` 변경 없이 `taa_config` 기반으로 분기 가능한 구조로 둠.

---

## 8. Known Limitations

1. **DB 미연결**: `repositories/db_repositories.py`는 NotImplementedError 상태. SCIP/dt/solution/cream 매핑은 Phase C.
2. **GlidePath xlsx 미연동**: `0. 정리 - GlidePath 값.xlsx`가 DRM 보호되어 직접 로딩 불가. 현재는 yaml의 reference_weights가 단일 vintage(2060) baseline 역할.
3. **ust30 placeholder**: augmented_source_root fixture에서만 채움 (σ=13.0%, E[R]=3.50%, Corr는 USGG10YR=0.85 등 추정값). 실 운영 수치가 아니며, 실 `Advisory/` 데이터로 CLI 실행 시 ValueError로 멈춤.
4. **Universe classification**: 키워드 룰 기반. 미매칭 가능 케이스 다수 (S&P500 ETF, 채권 선물 ETF 등). 운영 전 분류 정확도 검토 필요.
5. **ProductScorer 가중합**: 0.4/0.3/0.2/0.1은 임시값. 백테스트 검증 없음. quant_score(0~100)와 sharpe(보통 ~1)의 스케일 차이 미보정.
6. **TAA policy rule-based**: regime 1~4별 고정 tilt. dynamic / data-driven TAA 미구현.
7. **Output report**: csv/json 수준. 시각화/대시보드/PDF 없음.
8. **Reporting 모듈**: `tdf_engine/reporting/` 디렉토리는 `__init__.py`만 있고 비어있음.
9. **Fund 시나리오 product_weight_sum=0.6929**: 자산군 매칭 부족 또는 manager cap clipping의 결과. 운영 전 원인 분석 필요.
10. **단일 시나리오만 실행**: `optimization_constraints.yaml.scenarios.enabled: false`. multi-scenario / sensitivity 분석 미지원.
11. **multi-start 미적용**: yaml에 `multi_start: 5` 있으나 실제는 단일 SLSQP 호출.
12. **운용 적용 금지**: minimal end-to-end 검증 단계. 운용 포트폴리오로 사용하기 전에 백테스트 + 운용역 검토 필수.

---

## 9. Acceptance Criteria Check

| Criteria | Status | Evidence |
|---|---|---|
| `build_portfolio` CLI 실행 가능 | ✅ | augmented 시나리오에서 returncode=0, 실 데이터에선 ValueError(의도) |
| ETF형 portfolio csv/json 생성 | ✅ | `portfolio_etf_20260507.csv`, `portfolio_etf_20260507.json`. `tests/test_e2e_etf.py` 검증 |
| Fund형 portfolio csv/json 생성 | ✅ | `portfolio_fund_20260507.csv`, `portfolio_fund_20260507.json`. `tests/test_e2e_fund.py` 검증 |
| SAA → TAA → Selection → Portfolio 흐름 연결 | ✅ | `portfolio/tool.py::PortfolioConstructionTool.run`, `tools/build_portfolio.py::_build_with_repos` |
| 최종 weight sum = 1.0 | ✅ | ETF=1.000000, Fund=0.9999999999999999 (1e-4 tolerance 내) |
| `constraints_passed = True` | ✅ | augmented ETF/Fund 모두 True. `diagnostics.validation.issues = []` |
| 77 tests passed | ✅ | `pytest tests/` → 77 passed in 2.02s |
| Actual Advisory data missing ust30 raises ValueError | ✅ | `tests/test_cma_builder.py::test_raises_when_required_asset_missing` + 실 CLI 실행 확인 |
| Augmented fixture happy-path passes | ✅ | `tests/test_e2e_{etf,fund}.py` |
| Regime detection 동작 | ✅ | `RegimeAnalysisTool` G7, 2026-02-01 → Regime 1 |
| Universe classification 동작 | ✅ | ETF 932→572, 자산군 매핑 |
| Product selection 동작 | ✅ | ETF 26 picks, manager cap 적용 |
| 신규 단독 CLI 4종 body 채움 | ✅ | run_optimization/regime/regime_return/universe |

---

## 10. Open Questions

리뷰어 판단 요청:

1. **ust30 (b) 정책의 적절성**: required 자산 누락 시 즉시 ValueError로 막는 것이, Phase B(데모 진행 가능성을 떨어뜨림)와 Phase C(DB가 아직 unverified) 관점 모두에서 적절한가? augmented fixture를 통한 happy-path 검증이 진짜 신뢰 가능한가?
2. **GlidePath = reference_weights 단일 vintage**: 2060만 다루고 다른 vintage는 미지원 상태로 Phase C 진입해도 되는가? glidepath.yaml 신설 vs DRM 해제 후 xlsx 연동 중 어느 쪽이 우선순위?
3. **TAA 이후 weight_bounds 검증 제거**: SAA용 bound와 TAA 결과를 분리한 설계가 맞는가? 아니면 `taa_bounds_per_asset`을 별도로 두고 검증해야 하는가? (us_high_yield 0.07 → 0.08 케이스가 운영에서 허용 가능한가?)
4. **Universe classification keyword-first-match**: 룰 우선순위가 us_high_yield → 30Y → 10Y → 종합 → growth → value → em → dm_ex_us → kr 순서인데, 이 순서로 충분한가? S&P500 ETF처럼 키워드 단서가 약한 상품은 어떻게 처리할지?
5. **Core/Satellite + manager cap**: n_core=1, n_satellite=2 고정과 비례 manager cap clipping이 향후 ETF 60% / Fund 50% 정책 강화 시 그대로 확장 가능한가? overflow 비중을 다른 운용사로 재배정하지 않는 것이 정책으로 맞나?
6. **Phase C DB interface**: 현재 `MarketDataRepository` Protocol (`load_asset_rt_vol/load_corr_matrix/load_regime_source/load_regime_return_source`)이 SCIP DB 매핑에 충분한가? `load_asset_rt_vol`이 SCIP에서는 dataseries 6/15(가격) + 시계열 통계 계산 결과를 반환해야 하는데, 이 형태가 file repo와 호환 가능한가?
7. **Fund product_weight_sum = 0.6929 원인**: 운영 적용 전 unfilled_assets 또는 manager cap clipping 중 어느 쪽이 dominant인지 진단 필요한가? Phase B 범위에서 추가 진단 도구가 필요한가?
8. **scoring weight 0.4/0.3/0.2/0.1**: 백테스트 검증 전인데 임시값 그대로 두는 것이 타당한가? 아니면 yaml 외부화 + 운용역 동의 후 진행이 맞는가?

---

## 11. Appendix

### 11.1 주요 CLI

```bash
# Full pipeline
python -m tdf_engine.tools.build_portfolio \
    --source-root <Advisory_root> \
    [--config-dir <config_dir>] \
    --product-type {etf|fund} \
    [--output-dir <out_dir>]

# 단독 실행
python -m tdf_engine.tools.run_optimization --source-root <root>
python -m tdf_engine.tools.run_regime         --source-root <root>
python -m tdf_engine.tools.run_regime_return  --source-root <root>
python -m tdf_engine.tools.run_universe       --source-root <root> --product-type {etf|fund}
```

### 11.2 pytest

```bash
cd C:/Users/user/Downloads/python/Advisory/tdf_2060
C:/Users/user/Downloads/python/.venv/Scripts/python.exe -m pytest tests/ -v
# 기대: 77 passed
```

### 11.3 샘플 output JSON 키

```json
{
  "as_of": "20260507",
  "portfolio_type": "etf",
  "constraints_passed": true,
  "asset_weights": {"kr_equity": 0.05, "us_growth_equity": 0.40, ...},
  "asset_weight_sum": 1.0,
  "product_weights": [
    {"asset_key": "kr_equity", "product_id": "434730",
     "fund_code": "...", "name": "...", "manager": "...",
     "kis_asset_class": "국내주식", "sub_type": "기타인덱스",
     "weight": 0.04, "role": "core"},
    ...
  ],
  "product_weight_sum": 0.88,
  "diagnostics": {
    "regime": {"as_of": "2026-02-01", "region": "G7", "placement": 0.7223,
                "velocity": 0.0586, "regime": 1, "regime_label": "Expansion / Acceleration"},
    "saa_diagnostics": {...},
    "taa_diagnostics": {"violations": [], "bucket_sums": {"equity": 0.79, "fixed_income": 0.21}, ...},
    "universe_diagnostics": {...},
    "selection_diagnostics": {...},
    "validation": {"passed": true, "issues": []}
  }
}
```

### 11.4 샘플 CSV 컬럼

```
asset_key, product_id, fund_code, name, manager, kis_asset_class, sub_type, weight, role
```

### 11.5 디렉토리 구조 (Phase B 끝 시점)

```
tdf_2060/
├── CLAUDE.md
├── HANDOFF.md
├── docs/
│   ├── tdf_2060_tech_spec.md
│   ├── tdf_engine_architecture.md
│   └── phase_b_review_packet.md   ← 본 문서
├── source_review/                  (Phase A 시점, 변경 없음)
├── config_draft/                   (Phase A 시점, 변경 없음)
├── tdf_engine/
│   ├── __init__.py
│   ├── config/                     (yaml 5종 + loader.py — 변경 없음)
│   ├── domain/                     (enums.py, models.py — 변경 없음)
│   ├── optimization/
│   │   ├── cma.py                  ★ 신구현
│   │   ├── constraints.py          (변경 없음)
│   │   ├── covariance.py           (Phase A 동작 그대로)
│   │   ├── optimizer.py            ★ max_sharpe + optimize
│   │   └── tool.py                 ★ bucket/warm_start
│   ├── regime/
│   │   ├── classifier.py           ★ classify_frame
│   │   ├── placement.py            (변경 없음)
│   │   ├── velocity.py             (변경 없음)
│   │   ├── returns.py              ★ 전체 신구현
│   │   └── tool.py                 ★ 전체 신구현
│   ├── taa/
│   │   ├── policy.py               (변경 없음)
│   │   ├── overlay.py              ★ apply
│   │   └── tool.py                 ★ assets/bucket_by_asset
│   ├── universe/
│   │   ├── filters.py              (변경 없음)
│   │   ├── classifier.py           ★ DEFAULT_RULES + classify
│   │   └── tool.py                 ★ 전체 신구현
│   ├── selection/
│   │   ├── scoring.py              ★ score
│   │   ├── selector.py             ★ select
│   │   └── tool.py                 ★ run
│   ├── portfolio/
│   │   ├── builder.py              ★ build
│   │   ├── validator.py            ★ validate
│   │   └── tool.py                 ★ run
│   ├── repositories/
│   │   ├── interfaces.py           (변경 없음)
│   │   ├── file_repositories.py    (Phase A 그대로)
│   │   └── db_repositories.py      (NotImplementedError 유지 — Phase C)
│   ├── tools/
│   │   ├── build_portfolio.py      ★ 신구현 (main + write_outputs)
│   │   ├── run_optimization.py     ★ minimal body
│   │   ├── run_regime.py           ★ minimal body
│   │   ├── run_regime_return.py    ★ minimal body
│   │   └── run_universe.py         ★ minimal body
│   └── reporting/                  (비어있음)
└── tests/
    ├── conftest.py                 ★ augmented_source_root, augmented_assets fixture
    ├── test_cma_builder.py         ★ 신규 (4)
    ├── test_config_loader.py       (Phase A)
    ├── test_covariance_estimator.py (Phase A)
    ├── test_e2e_etf.py             ★ 신규 (1)
    ├── test_e2e_fund.py            ★ 신규 (1)
    ├── test_imports.py             (Phase A)
    ├── test_mvo_max_sharpe.py      ★ 신규 (5)
    ├── test_optimization_objective_dispatch.py ★ stub 테스트로 변경
    ├── test_placement_velocity.py  (Phase A)
    ├── test_portfolio_validator.py (Phase A)
    ├── test_product_classifier.py  ★ 신규 (7)
    ├── test_product_selection.py   ★ 신규 (2)
    ├── test_reference_weights_sum.py (Phase A)
    ├── test_regime_analysis_tool.py ★ 신규 (3)
    ├── test_regime_classifier.py   (Phase A)
    ├── test_regime_return.py       ★ 신규 (3)
    ├── test_repository_protocols.py (Phase A)
    ├── test_taa_overlay.py         ★ 신규 (4)
    ├── test_taa_policy.py          (Phase A)
    ├── test_universe_filter.py     (Phase A)
    └── test_universe_tool.py       ★ 신규 (3)
```

### 11.6 신규 테스트 목록 (33개)

```
test_cma_builder.py
  - test_builds_cma_for_9_assets
  - test_raises_when_required_asset_missing
  - test_diagnostics_contains_metadata
  - test_covariance_is_symmetric

test_mvo_max_sharpe.py
  - test_weights_sum_to_one
  - test_each_weight_within_bounds
  - test_equity_sum_in_bucket_bounds
  - test_constraints_passed
  - test_objective_name_max_sharpe

test_regime_analysis_tool.py
  - test_returns_latest_state_with_g7_default
  - test_classify_frame_matches_scalar_for_each_row
  - test_unknown_region_raises

test_regime_return.py
  - test_monthly_returns_drops_first_row
  - test_regime_return_groupby_mean
  - test_regime_return_tool_runs

test_taa_overlay.py
  - test_regime1_increases_equity_bucket
  - test_taa_weights_sum_to_one
  - test_per_asset_tilt_within_cap
  - test_reasons_attached

test_product_classifier.py
  - test_us_growth_etf_maps_to_us_growth_equity
  - test_us_value_etf_maps_to_us_value_equity
  - test_kr_equity_maps_correctly
  - test_em_china_maps_to_em_equity
  - test_kr_treasury_10y_pulls_before_aggregate
  - test_us_high_yield_takes_priority
  - test_unmatched_returns_none

test_universe_tool.py
  - test_etf_universe_runs
  - test_fund_universe_runs
  - test_excluded_threshold_visible

test_product_selection.py
  - test_selection_runs_for_simple_universe
  - test_unfilled_asset_recorded

test_e2e_etf.py
  - test_e2e_etf_pipeline

test_e2e_fund.py
  - test_e2e_fund_pipeline
```

---

---

## 12. Phase B.5 — Weight Closure / Fallback / Validator (안정화)

### 12.1 트리거: Fund `product_weight_sum=0.6929` 이슈

Phase B 종료 시점에서 Fund 시나리오의 product 단위 비중 합이 1.0이 아니라 **0.6929** (30.7% 미배분). 자산 비중(TAA)은 1.0이지만 product 단위로는 closure가 깨짐. Phase C(DB)에 진입하기 전에 데이터/분류기/selector 어디가 원인인지 명확히 잡고 가야 한다는 판단으로 B.5 안정화 단계 추가.

### 12.2 미배분 원인 진단 (Fund augmented 시나리오)

| 자산군 | target | unfilled | 원인 분류 | 후보 카운트 |
|---|---:|---:|---|---|
| us_value_equity | 19.98% | 19.98% | `filtered_out_by_scoring` | universe=2 (전체), `passes_filter` 후 ≤2 |
| kr_treasury_10y | 8.00% | 8.00% | `no_candidates_in_universe` | universe=0 (분류 매칭 없음) |
| us_treasury_30y | 0.72% | 0.72% | `no_candidates_in_universe` | universe=0 |
| us_growth_equity | 2.00% | 2.00% | `product_cap_clipping` (B.5 진단) / `satellite_short` (실제 결과) | universe=10, B등급 통과=2 → satellite 1개 부족 |

총 미배분 = **30.70%** ≈ 1 − 0.6929.

핵심 driver:
1. **Fund의 `target_quant_grade_min='B'` 필터**가 us_growth_equity 후보 10개 중 8개를 제외 → satellite n_target=2 미달.
2. **Fund universe에 한국 채권 ETF/펀드의 매핑 부족** (kr_treasury_10y, us_treasury_30y는 분류 매칭 0).
3. **`single_product_max_weight=0.30` cap clipping** — us_growth_equity core 의도값 32% → 30%로 잘림 (overflow 2%).

진단 정보는 `selection.diagnostics["unfilled_by_asset_class"]`에 자산군별 `{target, n_universe, n_after_filter, n_picks, allocated, unfilled, cause}`로 기록.

### 12.3 Fallback 정책 (`portfolio/fallback.py::apply_fallback`)

미배분 비중을 다음 순서로 처리. silent drop 금지.

```
(1) 동일 자산군 내 selected product 에 pro-rata 재배분
    └ single_product_max_weight cap 재적용. 이미 cap 인 row 는 건너뛰고 남은 row 균등 분배 (최대 5회 반복).
(2) 동일 bucket 내 다른 자산군의 selected product 에 pro-rata 분배
    └ 예: us_value_equity 미배분 → 같은 equity bucket의 kr_equity / us_growth / dm_ex_us / em_equity 의 picks에 분배.
(3) 그래도 남은 비중은 cash placeholder row (asset_key="cash", product_id="__CASH__", role="cash") 추가
```

기록: `portfolio.diagnostics["fallback"]` →
- `fallback_used: bool`
- `fallback_reasons: {asset_key: cause}`
- `reallocations: [{asset_key, mode, amount, target}, ...]` (mode ∈ `same_asset_class_pro_rata` / `same_bucket_sibling_pro_rata` / `cash_placeholder`)
- `cash_placeholder_weight: float`
- `product_weight_sum_before/after: float`

CLI JSON 최상위에도 `fallback_used`, `fallback_reasons` 노출.

### 12.4 Validator 강화 (`portfolio/validator.py`)

`ValidationReport`에 신규 필드:
- `non_negative_ok: bool`
- `product_sum_ok: bool`
- `warnings: list[str]` (issues와 별개)

검증 항목:
1. `asset_weight sum ≈ 1.0` (atol=1e-4, TAA cash-neutral 잔차 허용)
2. `product_weight sum ≈ 1.0` (atol=1e-4)
3. asset/product 모두 음수 weight 없음
4. bucket bounds (taa_bounds 기준, taa_diagnostics.bucket_sums 활용)
5. **final_asset_bounds** (옵션, warning만)
6. fallback 사용 시 `warnings`에 자산군별 cause + cash placeholder 노출

→ `constraints_passed`는 issues 0개 시 True. fallback warnings는 통과를 막지 않음.

### 12.5 Bounds 개념 분리 (config 문서화)

`tdf_2060.yaml` 헤더 주석에 명시:

| 개념 | 위치 | 용도 |
|---|---|---|
| `optimization_bounds` | `tdf_2060.yaml.weight_bounds` | MVO 입력 제약. SLSQP `bounds`로 사용 |
| `taa_tilt_bounds` | `taa_policy.yaml.constraints.per_asset_max_tilt` | TAA 자산별 조정폭 |
| bucket bounds | `tdf_2060.yaml.taa_bounds` + `taa_policy.yaml.constraints` | TAA 결과 bucket 합 검증 |
| `final_asset_bounds` | `tdf_2060.yaml.final_asset_bounds` (B.5 신설) | TAA 이후 최종 자산군 비중. **B.5는 warning만**, hard enforce 미정 |

`final_asset_bounds` 초안 (per-asset min/max). 위반 시 `validation.warnings`에 노출.

### 12.6 Phase B.5 결과

```
$ pytest tests/ -q
82 passed in 2.42s
```

- Phase A 44 + Phase B 33 + Phase B.5 신규 5 = 82
- 신규: `tests/test_phase_b5_closure.py` (5개)
  - `test_e2e_fund_product_weight_sum_is_one`
  - `test_selection_diagnostics_reports_unfilled_weight`
  - `test_fallback_allocates_unfilled_to_cash_placeholder`
  - `test_validator_warns_on_fallback`
  - `test_etf_e2e_still_passes_after_b5`
- 기존 수정: `tests/test_product_selection.py::test_unfilled_asset_recorded` — 키 이름을 `unfilled_assets` → `unfilled_by_asset_class`로 갱신.

### 12.7 CLI 검증 결과 (Phase B.5 적용 후)

| 항목 | ETF | Fund |
|---|---|---|
| `constraints_passed` | True | True |
| `asset_weight_sum` | 1.000000 | 1.000000 |
| `product_weight_sum` | **1.000000** | **1.000000** |
| `fallback_used` | True | True |
| `fallback_reasons` | `us_growth_equity: product_cap_clipping` | `us_growth_equity: satellite_short`, `us_value_equity: filtered_out_by_scoring`, `kr_treasury_10y: no_candidates_in_universe`, `us_treasury_30y: no_candidates_in_universe` |
| `cash_placeholder_weight` | 0.000000 | 0.000000 |
| `reallocations` | 1건 | 4건 |
| `returncode` | 0 | 0 |

> **주목**: cash placeholder가 0인 것은 모든 미배분이 (1) 또는 (2) 단계에서 흡수됐기 때문. 즉 ETF는 us_growth_equity 자산군 내 pro-rata로, Fund는 같은 bucket의 sibling 자산군 picks로 모두 분배됨. cash까지 도달하는 케이스는 추가 진단/decision이 필요.

### 12.8 Phase B.5 변경 파일

- 신규
  - `tdf_engine/portfolio/fallback.py` (apply_fallback)
  - `tests/test_phase_b5_closure.py` (5)
- 수정
  - `tdf_engine/selection/tool.py` — diagnostics["unfilled_by_asset_class"] 자산군별 cause 추적, manager_cap_scaling 분류
  - `tdf_engine/portfolio/builder.py` — `assets`/`single_product_max_weight` 인자 받아 fallback 호출
  - `tdf_engine/portfolio/validator.py` — non_negative/product_sum/warnings + final_asset_bounds warning
  - `tdf_engine/portfolio/tool.py` — `assets` 보유, `validation.warnings` 노출, single_product_cap 추출 후 builder에 주입
  - `tdf_engine/tools/build_portfolio.py` — `_build_with_repos`가 assets 전달, payload에 fallback_used/fallback_reasons 추가
  - `tdf_engine/config/tdf_2060.yaml` — Bounds 개념 주석 + `final_asset_bounds` 초안
  - `tests/test_product_selection.py::test_unfilled_asset_recorded` — 키 이름 갱신

### 12.9 남은 한계 (Phase B.5 이후)

1. **fallback이 자산 의도를 흐림**: us_value_equity 미배분이 같은 equity bucket의 kr_equity/us_growth/dm/em picks로 흡수되면, 결과 product 비중이 SAA 의도와 다름. Phase B.5는 이를 명시 warning으로 노출하지만, 운영 적용 전엔 자산군 closure가 우선이고 `final_asset_bounds` hard enforce 정책 결정이 필요.
2. **`target_quant_grade_min='B'` 정책의 사이드 이펙트**: us_growth_equity의 8/10 펀드가 B등급 미달로 후보에서 제외. 운영 정책으로 B등급 미달을 진짜 배제하는 게 맞는지 vs. 자산군 closure를 위해 일부 완화하는지 결정 필요.
3. **kr_treasury_10y / us_treasury_30y가 펀드 universe에서 분류 매칭 0**: classifier 룰 자체가 ETF 중심. 채권 펀드는 키워드("국고채10년", "미국30년" 등)로 매칭이 어려움. universe classifier yaml 외부화 + 채권 펀드 룰 보강 필요.
4. **`final_asset_bounds`는 현재 warning만**: hard enforce 시 fallback 자체가 위반 가능 (e.g. us_value_equity 0.20 → 0.00). 정책 합의 후 단계적 enforce.
5. **fallback의 `single_product_max_weight` cap 재적용**: 같은 자산군 pro-rata에서만 cap 재검증. bucket sibling 분배에서는 cap을 다시 안 봄 (sibling 후보들의 기존 weight + 추가분이 cap 넘을 가능성). 운영 적용 전 추가 검증 필요.
6. **cash_placeholder 가 발생하는 경우 후속 처리**: 현재는 row만 추가하고 위/아래로 통과. 실제 운용에선 MMF/단기채 등 cash equivalent 상품으로 매핑되어야 함.

### 12.10 Phase C 진입 전 반드시 결정할 이슈 (B.5 반영)

1. **(B에서 이월) ust30 SCIP 매핑** — `asset_mapping.yaml::us_treasury_30y.db_dataset_id` 확정. 현재 `null`.
2. **(B에서 이월) `final_asset_bounds` hard enforce 정책** — 운영 가능 weight band를 운용역과 합의. B.5는 warning만.
3. **(B에서 이월) Universe classifier yaml 외부화 + 채권 펀드 매칭 보강** — Fund의 kr_treasury_10y/us_treasury_30y 매칭 0 케이스를 미리 잡지 않으면 Phase C에서 데이터 vs 분류기 원인 구분 어려움.
4. **(B.5 신규) Fund `target_quant_grade_min='B'` 완화 여부** — 8/10 펀드 제외 효과가 운영 의도와 일치하는지 검토. 완화/비활성/등급별 가중 등 옵션.
5. **(B.5 신규) Fallback 정책의 운영 적용 가능성** — 자산 의도를 흐리는 부분을 다음 중 어느 방식으로 다룰지: (a) 그대로 + 명시 warning, (b) bucket sibling 단계까지만 허용 + 잔여는 cash, (c) cash placeholder를 즉시 MMF/단기채로 매핑하는 hook 추가.

---

---

## 13. Phase B.5+ — Drift Diagnostics & quality_status

### 13.1 트리거

Phase B.5에서 Fund product_weight_sum이 1.0으로 닫혔지만, 미배분 30.7%가 같은 bucket sibling으로 흡수되었기 때문에 **자산 단위 의도는 흐려질 가능성**이 남았다. 운영자가 `constraints_passed=True`만 보고 정상 포트폴리오로 오해하지 않도록, fallback 전후 자산 비중 차이(drift)와 품질 등급(`quality_status`)을 별도 노출.

### 13.2 신규 모듈 / 객체

- `tdf_engine/portfolio/quality.py::evaluate_quality` (신규) — `QualityReport` dataclass 반환.
- `portfolio.diagnostics["quality"]` 키 신설:
  - `quality_status: "clean" | "warning" | "review_required"`
  - `target_asset_weights: dict[str, float]` — TAA 결과 (의도)
  - `final_asset_weights: dict[str, float]` — product 단위 재집계
  - `asset_weight_drift: dict[str, float]` — final − target
  - `max_abs_asset_weight_drift: float`
  - `drift_by_bucket: dict[str, float]` — equity / fixed_income / cash / unmapped
  - `max_abs_bucket_drift: float`
  - `cash_placeholder_weight: float`
  - `review_reasons: list[str]`
  - `fallback_absorbers: list[dict]` — `{source_asset_key, absorber_asset_key, absorbed_weight, product_id, product_name, mode}`
  - `thresholds: {asset_drift, bucket_drift}`

### 13.3 quality_status 결정 규칙

```
review_required 조건 (어느 하나라도) :
  - max_abs_asset_weight_drift  ≥ 0.03 (3%p)
  - max_abs_bucket_drift        ≥ 0.05 (5%p)
  - cash_placeholder_weight     >  0
  - any selection.unfilled_by_asset_class.cause == "no_candidates_in_universe"

warning :
  - 위 review_required 조건에 해당하지 않으면서 fallback_used=True

clean :
  - fallback_used=False AND drift 거의 없음
```

threshold 는 `PortfolioBuilder.build(asset_drift_threshold=, bucket_drift_threshold=)` 인자로 조정 가능.

### 13.4 fallback._redistribute → absorbers 추적

`_redistribute` 시그니처 변경: `(placed, leftover, additions: list[(idx, amount)])` 반환. `apply_fallback`이 `additions`를 통해 product 단위로 `fallback_absorbers` 누적.

`reallocations` (자산군 단위 합산)는 B.5 호환을 위해 유지.

### 13.5 Validator 메시지 구체화 (`portfolio/validator.py`)

기존 `"fallback applied to <ak> (cause=...)"` → B.5+에서:

```
fallback_used: <ak> <amount%> redistributed → [<absorber_keys>] (cause=<cause>)
no_candidates: [<ak1>, <ak2>, ...]
cash_placeholder_weight: <%>
max_abs_asset_weight_drift: <%>
max_abs_bucket_drift: <%>
quality_status: <status>
```

### 13.6 CLI payload 변경 (`tools/build_portfolio.py::write_outputs`)

JSON 최상위에 추가된 필드:
- `quality_status`
- `max_abs_asset_weight_drift`
- `max_abs_bucket_drift`
- `drift_by_bucket`
- `review_reasons`

stdout에도 `quality_status`, `max_abs_asset_drift` 한 줄씩 추가.

### 13.7 ETF / Fund 비교 (실제 CLI 결과)

| 항목 | ETF | Fund |
|---|---|---|
| `constraints_passed` | True | True |
| `product_weight_sum` | 1.000000 | 1.000000 |
| **`quality_status`** | **warning** | **review_required** |
| `max_abs_asset_weight_drift` | **0.00%** | **19.98%** |
| `max_abs_bucket_drift` | 0.00% | 0.00% |
| `fallback_used` | True | True |
| `fallback_reasons` | us_growth_equity: product_cap_clipping | 4건 (us_growth/value, kr_treasury_10y, us_treasury_30y) |
| `review_reasons` | fallback used (drift=0) | asset drift 19.98% ≥ 3% / no_candidates_in_universe: [kr_treasury_10y, us_treasury_30y] |
| `cash_placeholder_weight` | 0 | 0 |
| `fallback_absorbers` | 2건 (자산군 내) | 19건 (대부분 bucket sibling) |

**해석**:
- ETF는 fallback이 같은 자산군 내에서만 분배 → 운영 의도 보존. `warning`은 단지 fallback 사용 사실을 알림.
- Fund는 us_value_equity 19.98% / kr_treasury_10y 8% / us_treasury_30y 0.72%가 **다른 자산군으로 재분배**되어 자산 단위 의도 손상. `review_required`로 운용역 검토 필요.
- 두 시나리오 모두 **bucket drift=0** — equity bucket 내에서만 흐름 유지. 즉 운용 정책의 큰 틀(equity 79% / fixed_income 21%)은 보존됨.

Fund 미배분 흡수 흐름 (top 6):
```
us_growth_equity → us_growth_equity   +2.00%   (product_id=70622, same_asset_class)
us_value_equity  → kr_equity          +2.00% × 3 (kr 펀드 3개로 분배)
us_value_equity  → us_growth_equity   +2.00%
us_value_equity  → dm_ex_us_equity    +2.00%
... 총 19건
```

### 13.8 테스트

```
$ pytest tests/ -q
89 passed in 2.87s
```

- Phase A 44 + Phase B 33 + Phase B.5 5 + **Phase B.5+ 7** = 89
- 신규: `tests/test_phase_b5plus_quality.py`
  - 단위: `test_quality_status_clean_when_no_fallback`, `test_quality_status_review_required_when_drift_exceeds_threshold`, `test_quality_status_review_required_when_cash_placeholder_used`, `test_quality_status_warning_when_fallback_used_with_small_drift`
  - E2E: `test_fallback_records_asset_weight_drift`, `test_fund_e2e_quality_status_is_review_required`, `test_validator_warning_includes_drift_and_quality_status`
- 기존 `test_phase_b5_closure.py::test_validator_warns_on_fallback`은 메시지 포맷 변경에 맞춰 keyword 갱신.

### 13.9 변경 파일 (B.5+)

신규
- `tdf_engine/portfolio/quality.py` (~150 lines)
- `tests/test_phase_b5plus_quality.py` (7 tests)

수정
- `tdf_engine/portfolio/fallback.py` — `_redistribute` 반환값에 `additions`, `_record_absorbers`, `_add_or_top_up_cash` 가 idx 반환, `fallback_absorbers` 누적
- `tdf_engine/portfolio/builder.py` — `evaluate_quality` 호출 + `diagnostics["quality"]` 주입, threshold 인자 노출
- `tdf_engine/portfolio/validator.py` — fallback warning 메시지 구체화 + drift/quality_status 노출
- `tdf_engine/tools/build_portfolio.py` — payload에 quality_status/max_abs_drift/drift_by_bucket/review_reasons 추가, stdout 요약 추가
- `tests/test_phase_b5_closure.py::test_validator_warns_on_fallback` — keyword 갱신

### 13.10 Phase C 진입 가능 여부에 대한 판단

진입 **가능**. 단 Phase C 첫 작업은 DB 연결이 아니라 **classifier/scoring 보강**이 우선.

근거:
1. ETF/Fund 모두 `product_weight_sum=1.0` closure 확보 (B.5).
2. `quality_status`로 ETF(`warning`)와 Fund(`review_required`) 차이 명확히 분리됨 (B.5+).
3. fallback의 자산 단위 영향이 `asset_weight_drift` + `fallback_absorbers`로 product 단위까지 추적 가능.
4. Validator가 `constraints_passed`(제약 통과)와 `quality_status`(품질 경고)를 분리하여 운영자가 오해할 가능성 차단.

다만 Fund의 `review_required` 원인 중 다음은 DB 연결로 자동 해소되지 않음:
- `kr_treasury_10y`, `us_treasury_30y`의 펀드 universe 매칭 0 → classifier 룰 보강 필요.
- `us_value_equity` 후보 부족 + `target_quant_grade_min='B'` 필터 → scoring 정책 결정 필요.

따라서 권장 순서:
```
Phase B.5+ 완료 (현 상태)
  → Phase C-pre: classifier yaml 외부화 + 채권 펀드 룰 보강
  → Phase C-pre: scoring 정책 (B등급 필터) 결정
  → Phase C: SCIP DBRepository 연결 (ust30 db_dataset_id 확정 포함)
  → GlidePath 엑셀 연동
  → final_asset_bounds hard enforce 정책 합의
```

---

---

## 14. Phase C-pre — Classifier 외부화 + 채권 룰 보강 + Scoring 정책 옵션화

### 14.1 트리거

Phase B.5+ 결과:
- Fund `quality_status: review_required`, `max_abs_asset_drift: 19.98%`.
- 원인: classifier가 ETF 중심 + Fund 채권 펀드 매칭 0 + `target_quant_grade_min='B'`가 hard filter로 us_growth_equity 8/10 펀드 제외.

이 원인은 DB 연결로 자동 해소되지 않음 → Phase C(DB) 진입 전 분류기/스코어링 정비.

### 14.2 변경 요약

1. **Classifier 룰 yaml 외부화**
   - 신규: `tdf_engine/config/universe_classification.yaml` (priority 기반 11개 룰 entry).
   - `ConfigLoader.load_classification_rules_raw()`, `universe/classifier.py::load_rules`, `rules_from_yaml`.
   - DEFAULT_RULES는 yaml 부재 시 폴백으로 유지.
   - `ProductClassifier.classify()`가 `(asset_key, match_reason)` 튜플 반환.

2. **Fund 채권 룰 보강**
   - `kr_treasury_10y`: `kis_mp=국내채권` + 키워드 `[국공채, 국채, 국고채10, 장기국공채, 중기국공채, ...]` + 제외 `[단기, 초단기, MMF, 머니마켓]`.
   - `us_treasury_30y`: 키워드 `[미국장기국채, 미국장기채, 미국투자등급장기채권, 30년국채, TLT, EDV, ...]` + 제외 `[하이일드]`.
   - `kr_aggregate_bond`: `kis_mp=국내채권` + 제외 `[국고채10, 미국, 하이일드]`.
   - `us_high_yield`: `[하이일드, High Yield, HY, Hi-Yield]`.

3. **Universe diagnostics 강화 (`universe/tool.py`)**
   - `total_products`, `passed_filter_count`, `classified_count`, `unclassified_count`
   - `classified_by_asset_class: {asset_key: count}`
   - `asset_classes_with_zero_count: list`
   - `unclassified_samples: list[dict]` (top 25)
   - `match_reasons_by_asset_class: dict[asset_key, list[str]]` (top 5 per class)

4. **`quant_grade_policy` 옵션화 (`universe_filter.yaml`, `selection/scoring.py`)**
   - `mode: hard_filter | score_penalty | disabled`
   - `min_grade`, `penalty_per_grade`
   - default: ETF=`hard_filter` (min=C), Fund=`score_penalty` (min=B, penalty=0.10)
   - `ProductScorer.is_grade_below_min`, `score()`가 penalty 모드일 때 `(min_rank - cur_rank) × penalty_per_grade` 비율로 base 감점
   - Selection diagnostics: `grade_filtered_count`, `grade_penalized_count`, `quant_grade_policy` 노출

### 14.3 Fund E2E 전후 비교 (augmented 시나리오)

| 지표 | Phase B.5+ | **Phase C-pre** | 변화 |
|---|---:|---:|---|
| `product_weight_sum` | 1.000000 | 1.000000 | 유지 |
| `quality_status` | **review_required** | **warning** | ↓ 개선 |
| `max_abs_asset_weight_drift` | **19.9834%** | **0.0000%** | ↓↓ 거의 0 |
| `max_abs_bucket_drift` | ~0 | 0.0000% | 유지 |
| `fallback_reasons` | 4건 (us_growth/value, kr_treasury_10y, us_treasury_30y) | **1건** (us_growth_equity: product_cap_clipping) | ↓ |
| no_candidates_in_universe | `[kr_treasury_10y, us_treasury_30y]` | **`[]`** | ↓ 해소 |
| `kr_treasury_10y` 분류 | 0 | **4** | ↑ |
| `us_treasury_30y` 분류 | 0 | **10** | ↑ |
| `us_high_yield` 분류 | 1 | **10** | ↑ |
| us_growth_equity 후보 (B등급↑) | 2/10 | **156** penalized + 통과 | hard→score_penalty로 후보 보존 |
| cross-bucket reallocation | 다수 (us_value 19.98%) | **0건** (자산군 내 흡수만) | 의도 보존 |
| `grade_filtered_count` | N/A | 0 | hard_filter 미사용 |
| `grade_penalized_count` | N/A | **156** | score_penalty 적용 |

### 14.4 ETF E2E (참조)

| 지표 | B.5+ | C-pre |
|---|---:|---:|
| `quality_status` | warning | warning |
| `max_abs_asset_drift` | 0.00% | 0.00% |
| `fallback_reasons` | us_growth_equity: product_cap_clipping (2%) | us_growth_equity: product_cap_clipping (12%) |
| `grade_filtered_count` | (없음) | **75** (hard_filter 유지) |

> ETF는 cap 정책 자체가 강하고(`single_product_max_weight=0.20`), `hard_filter` 유지. 룰 보강 후 후보 풀이 늘어 unfilled가 12%로 보이지만 자산군 내 pro-rata로 흡수되어 `max_drift=0` 유지.

### 14.5 남은 review_required 가능성

현 시점에서는 ETF/Fund 모두 `warning`. 다만 조건이 바뀌면 다시 `review_required`로 떨어질 수 있음:
- 펀드 universe에 us_treasury_30y 매칭이 일시적으로 줄어들면 fallback 재발생.
- `final_asset_bounds`를 hard enforce로 전환하면 cap 위반 시 `review_required`.
- TAA tilt가 SAA bound를 크게 넘어 `single_product_max_weight cap`이 깊게 clipping되면 cross-bucket reallocation 발생.

### 14.6 변경 파일 (C-pre)

신규
- `tdf_engine/config/universe_classification.yaml`
- `tests/test_phase_cpre.py` (7 tests)

수정
- `tdf_engine/config/loader.py` — `CLASSIFICATION_CONFIG`, `load_classification_rules_raw()`
- `tdf_engine/config/universe_filter.yaml` — etf/fund 블록에 `quant_grade_policy` 추가
- `tdf_engine/universe/classifier.py` — `rules_from_yaml`, `load_rules`, `ClassificationRule.priority`, `classify()` 튜플 반환, DEFAULT_RULES 보강
- `tdf_engine/universe/tool.py` — diagnostics 8개 키 추가, `classify` 튜플 분리
- `tdf_engine/selection/scoring.py` — `grade_policy_mode`, `is_grade_below_min`, `score()` penalty 분기
- `tdf_engine/selection/tool.py` — yaml policy 우선 + `grade_filtered_count/grade_penalized_count`
- `tdf_engine/tools/build_portfolio.py` — `_build_with_repos`가 yaml 룰 → ProductClassifier 주입
- `tests/test_product_classifier.py` — `classify()` 튜플 반환 갱신
- `tests/test_phase_b5plus_quality.py` — Fund quality_status 가정 완화 (룰 보강으로 warning 가능)

### 14.7 테스트

```
$ pytest tests/ -q
96 passed in 3.06s
```

- Phase A 44 + B 33 + B.5 5 + B.5+ 7 + **C-pre 7** = 96
- 신규 (`tests/test_phase_cpre.py`):
  - `test_classifier_loads_yaml_rules`
  - `test_classifier_records_match_reason`
  - `test_fund_bond_products_are_classified_when_keywords_match`
  - `test_universe_diagnostics_reports_unclassified_samples`
  - `test_selection_quant_grade_policy_score_penalty_keeps_candidates`
  - `test_selection_quant_grade_policy_hard_filter_excludes_candidates`
  - `test_fund_e2e_quality_improves_or_reports_remaining_causes`

### 14.8 Phase C 진입 가능 여부 — Claude 판단

**진입 가능. C-pre가 핵심 사각지대를 사실상 닫았음.**

근거:
1. Fund의 `no_candidates_in_universe`가 사라짐 (`asset_classes_with_zero_count = []`).
2. Fund `quality_status: warning`, `max_abs_asset_drift: 0.00%` — 자산 의도 보존.
3. fallback이 자산군 *내* pro-rata로만 동작 (cross-bucket reallocation 0).
4. classifier 룰이 yaml에 외부화되어 운영 중 룰 추가/수정 가능.
5. 96개 테스트 통과 + 전후 비교 차이 명확.

DB 연결(Phase C)에서 처리할 항목:
- ust30 SCIP `back_dataset` 매핑 확정 → asset_mapping.yaml `db_dataset_id` 채움.
- DBMarketDataRepository 구현 + file repo와 동등한 인터페이스 검증.
- Asset_rt_vol/Corr_mat 자체를 SCIP 시계열에서 자동 산출하는 파이프라인.
- regime_src/regimeAnalysis_src도 SCIP/OECD/FactSet에서 자동 갱신.

순서 권장:
```
Phase C-pre (현재) 완료
  → Phase C: SCIP DBRepository 연결 (ust30 db_dataset_id 확정 포함)
  → GlidePath 엑셀 연동 (DRM 해제 후)
  → final_asset_bounds hard enforce 정책 합의
  → reporting 모듈 (HTML/대시보드)
```

---

End of packet.
