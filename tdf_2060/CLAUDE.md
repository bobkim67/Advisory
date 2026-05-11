# CLAUDE.md — TDF 2060 Portfolio Engine

이 프로젝트는 TDF 2060형 자산배분 포트폴리오를 생성하기 위한 Python 기반 OOP 엔진이다.

## 0. 현재 단계 (중요)

**Phase D 진입 (2026-05-08).** Phase A~C.5 freeze. 124 passed / 5 skipped / 1 xfailed 기준치.
**다음 게이트 = 운용역 의사결정 + Excel DRM 해제 + 운영 준비성 검증.**
**코드 변경 없음. Phase A 재생성·기존 코드 덮어쓰기 금지.**

세션이 끊어진 뒤 이어 작업한다면 다음 순서로 읽기:
1. `docs/phase_d_declaration.md` — **현재 진입점**. Phase D 정의 + freeze 정책 + 결정 전/후 작업 분리.
2. `docs/current_state_freeze.md` — 동결 상태 스냅샷 (코드/테스트/산출물/품질).
3. `docs/investment_decision_register.md` — 결정 항목 14개 + 상태 + 변경 위치.
4. `docs/phase_c_final_handoff.md` — Phase C.5 시점의 직전 핸드오프.
5. `docs/golden_answer_validation.md` — VBA/Excel 답안지 parity 분해 분석.
6. `docs/phase_c_db_repository.md` — Phase C/C.1/C.2/C.3/C.4 누적 상세.
7. `docs/phase_b_review_packet.md` — Phase A/B/B.5/B.5+/C-pre 누적.
8. `HANDOFF.md` — 짧은 요약 (본 파일과 정합).

### 진행 현황

| 단계 | 상태 | 핵심 산출 |
|---|---|---|
| Phase A — 코드 골격 | ✅ 완료 | 17개 NotImplementedError 흐름 정의, 44 smoke test |
| Phase B — minimal end-to-end (file) | ✅ 완료 | csv/json 출력, ust30 (b)강한 error |
| Phase B.5 — weight closure + fallback | ✅ 완료 | pro-rata → bucket sibling → cash placeholder |
| Phase B.5+ — drift / quality_status | ✅ 완료 | clean / warning / review_required 분리 |
| Phase C-pre — classifier yaml + scoring policy | ✅ 완료 | Fund 채권 매칭 사각지대 해소 |
| Phase C — DB repository | ✅ 완료 | DBMarketDataRepository, --source file/db, fake DB 동등성 |
| Phase C.1 — semantic / sanity / dry-run | ✅ 완료 | semantic_type / return_transform 검증, inspect_db_sources CLI |
| Phase C.2 — SCIP dataset 매핑 확정 | ✅ 완료 | 9개 자산 모두 dataset_id 확정 (requires_decision=0) |
| Phase C.3 — TAA feasibility projection | ✅ 완료 | SLSQP projection, long-only + bucket bound 보장 |
| Phase C.4 — 운용역 review packet | ✅ 완료 | review_*.md 자동 생성 (8 섹션 + policy_review_items) |
| Phase C.5 — Golden answer parity | ✅ 완료 | Placement/Velocity/Regime classification 100% 일치 (USA region) |
| Phase D — Governance & Op Readiness | ▶ 진입 (2026-05-08) | freeze + Decision Register 14건. 코드 변경 없음. |

### 현재 운영 상태 (DB 기반 ETF/Fund 모두)

```
constraints_passed        : True
quality_status            : warning
asset_weight_sum          : 1.000000
product_weight_sum        : 1.000000
equity bucket             : 82.32%   (75~85 안)
fixed_income bucket       : 17.68%   (15~25 안)
projection_used           : True (음수 자산 → 0)
max_abs_projection_drift  : 3.00%
proxy_used                : False
```

### 본 단계까지 **하지 않은** 것 (의도적)

- regime DB 연결 (`solution.roboadvisorAPI_economicregime`) — 현재 file 폴백
- GlidePath xlsx 연동 — DRM 보호 (`0. 정리 - GlidePath 값.xlsx`)
- HTML/대시보드 reporting — Markdown 까지만
- duration_proxy / synthetic mapping_mode — hook 만 열어둠
- final_asset_bounds hard enforce — 현재 warning 만
- selection score 보존 — `product_allocation.score = null`

### 운용역 의사결정 대기 중 (Phase D 전)

1. `us_treasury_30y` final 0% / `kr_treasury_10y` final 0% 허용 여부
2. `dm_ex_us_equity` 4.29% (lower bound 4%, near_bound) 운용 의도와 정합한지
3. `us_value_equity` 30% cap 도달 적정성
4. `max_abs_projection_drift = 3.00%` 허용 임계
5. `final_asset_bounds` 운영 값 확정
6. `regimeAnalysis_rt` 정의 명시 (region / annualization / regime base — Phase C.5 §5.4)
7. Excel 원본 DRM 해제 또는 SAA/TAA/Final weights csv export

---

## 1. Project Goal

ETF형 TDF 포트폴리오와 펀드형 TDF 포트폴리오를 **동일한 엔진**에서 생성한다.

```
MVO 기반 SAA
  + Regime Analysis 기반 TAA Overlay
  + ETF / Fund 상품선정
= 최종 TDF 2060 포트폴리오 (ETF형 + 펀드형)
```

---

## 2. Business Context

본 프로젝트의 포트폴리오는 **자산배분형 상품을 편입하는 것이 아니라**, 주식형/채권형 ETF 또는 펀드를 조합하여 직접 자산배분형 포트폴리오를 구성한다.

따라서 다음은 모두 제외한다.

```
혼합형, 자산배분형, TDF, TIF, TRF, 멀티에셋형, 글로벌라이프싸이클,
재간접 혼합형, 레버리지, 인버스, 커버드콜, 타겟커버드콜, 과도한 합성형
```

TDF 2060 의 기본 자산배분:

| 구분 | 비중 |
|---|---:|
| 주식 | 80% |
| 채권 | 20% |

TAA 적용 후에도 75/25 ~ 85/15 범위 안에서만 조정한다.

---

## 3. MVO Asset Classes (9개)

### Equity (5개)

```
kr_equity              한국 주식           opt=M2KR INDEX        rr=M2KR Index
us_growth_equity       미국 성장주         opt=M2US000G Index    rr=M2US000G Index
us_value_equity        미국 가치주         opt=M2US000V Index    rr=M2US000V Index
dm_ex_us_equity        미국외 선진국 주식  opt=TAD09XU Index     rr=M2WOU Index   ★분리
em_equity              신흥국 주식         opt=M2EF Index        rr=M2EF Index
```

### Fixed Income (4개)

```
kr_aggregate_bond      한국 종합채권       opt=SPBKRCOT Index    rr=KISKALBI Index ★분리
kr_treasury_10y        한국 국고채10년     opt=KPGB10YR Index    rr=null
us_treasury_30y        미국 국고채30년     opt=null              rr=null         ★required_but_missing
us_high_yield          미국 하이일드 회사채 opt=LF98TRUU Index    rr=LF98TRUU Index  (risk_asset, credit)
```

> `opt` = `source_names.optimization` (Asset_rt_vol/Corr_mat 매칭용)
> `rr` = `source_names.regime_return` (regimeAnalysis_src 매칭용)

### 핵심 주의사항 (Phase A에서 코드/yaml/test로 강제됨)

1. **HY = `fixed_income` bucket + `risk_asset` + `credit` flag** — `test_config_loader.py::test_hy_has_risk_asset_and_credit_flags` 로 회귀 방어.
2. **us_treasury_30y 는 `fallback_policy: explicit_proxy_only`, `proxy.enabled: false`** — 자동 fallback 금지. `test_config_loader.py::test_us_treasury_30y_explicit_proxy_only` 로 강제.
3. **`source_names` 는 dict 가 아닌 `AssetSourceNames` dataclass** — `optimization`, `regime_return` 두 필드.
4. **`required: true`** 는 자산군이 SAA 에 반드시 들어가야 함을 의미. 데이터 부재여도 자산군 자체는 살아있어야 함 → Phase B 에서 "축소 CMA + 명시 warning" 정책 결정 필요 (HANDOFF.md 참조).

---

## 4. 소스파일 (Advisory/ 직속 — 본 프로젝트 외부)

```
Asset_rt_vol           자산군별 E[R], σ
Corr_mat               자산군 간 상관계수
optimization_vba       Excel Solver 매크로 (GRG Nonlinear, Maximize $L$26, ByChange rCurrWeight)
regime_src             22개 국가/지역 OECD CLI (월별)
regime_Placement       메타 row 1: B13=Src!B13-AVERAGE(Src!B2:B13)
regime_Velocity        메타 row 1: B14=Placement!B14-Placement!B13
regime_ECI             메타 row 1: IF(P>0, IF(V>0,1,4), IF(V>0,2,3))
regime_Dashboard       단일 composite phase (시각화 보조, 미사용)
regimeAnalysis_src     24+종 자산 월말 지수 레벨 (2004-10 ~)
regimeAnalysis_rt      Regime 1/2/3/4 별 자산 평균수익률
etf_list               ETF 932건 (38 컬럼)
fund_list              펀드 781건 (38 컬럼)
```

상세 분석은 `source_review/` 3개 md 참조.

---

## 5. Architecture (Phase A 시점)

### 디렉토리 (현재 상태)

```
tdf_2060/
  CLAUDE.md
  HANDOFF.md                          ← 다음 세션 진입점 (반드시 먼저 읽기)
  docs/                               (2 md)
    tdf_2060_tech_spec.md
    tdf_engine_architecture.md
  source_review/                      (3 md)
    source_file_inventory.md
    mvo_source_review.md
    regime_source_review.md
  config_draft/                       (5 yaml — 작업용 초안 보관)
  tdf_engine/                         (Phase A 골격)
    __init__.py
    domain/{__init__,enums,models}.py
    repositories/{__init__,interfaces,file_repositories,db_repositories}.py
    config/{__init__,loader}.py + 5 yaml (정본)
    optimization/{cma,covariance,constraints,optimizer,tool}.py
    regime/{placement,velocity,classifier,returns,tool}.py
    taa/{policy,overlay,tool}.py
    universe/{filters,classifier,tool}.py
    selection/{scoring,selector,tool}.py
    portfolio/{builder,validator,rebalance,tool}.py
    reporting/__init__.py
    tools/{run_optimization,run_regime,run_regime_return,run_universe,build_portfolio}.py
  tests/                              (10 file, 44 test)
```

### 핵심 개념

```
Repository 패턴: 계산 ↔ 데이터 분리
Tool 단위:       OptimizationTool, RegimeAnalysisTool, RegimeReturnTool,
                  TAAOverlayTool, UniverseTool, ProductSelectionTool,
                  PortfolioConstructionTool
Result Object:   pandas DataFrame 을 그대로 넘기지 않고 dataclass 로 wrap
Config-First:    비즈니스 룰은 yaml 에. Python 코드는 룰을 받아 실행.
```

ETF형/펀드형 차이는 `UniverseTool` (ProductRepository, 키워드 필터) 와 `ProductSelectionTool` (single max weight, manager concentration) 에서만. SAA / MVO / TAA 는 동일.

### Phase A에서 "동작" 하는 작은 primitive

다음은 NotImplementedError가 아니며 smoke test로 검증된다.

- `CovarianceEstimator.estimate(σ, ρ)` → Σ = D·C·D
- `CovarianceEstimator.is_symmetric(M)`
- `PlacementCalculator(window=12).calc(s)` → s − rolling12.mean
- `VelocityCalculator.calc(p)` → p.diff(1)
- `ECIRegimeClassifier.classify_scalar(p, v)` → Regime
- `RegimeTAAPolicy.from_dict(raw) / .get(regime)`
- `UniverseFilter(config).is_excluded(row)`
- `PortfolioValidator.validate_weights(w)`
- `ConfigLoader.load_*()` 5종 + `load_assets()`
- `MVOOptimizer.__init__(objective)` + dispatch table (식 자체는 stub)

### Phase A에서 NotImplementedError로 남은 것

`MVOOptimizer.optimize`, `CapitalMarketAssumptionBuilder.build`, 모든 Tool 의 `run()`, `ECIRegimeClassifier.classify_frame`, `AssetReturnCalculator.monthly_returns`, `RegimeReturnAnalyzer.analyze`, `TAAOverlayEngine.apply`, `ProductClassifier.classify`, `ProductScorer.score`, `CoreSatelliteSelector.select`, `PortfolioBuilder.build`, `PortfolioValidator.validate (전체)`, `RebalanceEngine.diff`, `PortfolioConstructionTool.run`, `tools/run_*.py` 전부, `DbMarketDataRepository`, `DbProductRepository`.

---

## 6. Design Conventions

### 6.1 핵심 원칙

1. **계산 ↔ 데이터 접근 분리** — Repository 인터페이스로 추상화.
2. **silent fallback 금지** — 데이터 없으면 명시 에러 또는 명시 warning + diagnostics 기록.
3. **자산명 분리** — `asset_key` (영문), `display_name` (한글), `source_names.optimization`, `source_names.regime_return`.
4. **TAA 는 SAA 를 훼손하지 않는다** — 80/20 → 75/25 ~ 85/15 범위 내, ±%p 로만 overlay.
5. **HY = risk_asset** — 단순 채권 취급 금지.
6. **objective config-driven** — `MVOOptimizer` 내부에 목적함수 하드코딩 금지. dispatch table 사용.

### 6.2 코딩 표준

- 타입 힌트 필수 (public method).
- 결과는 dataclass 로 wrap.
- 한국어 변수명/주석 허용 (금융 전문용어), 단 영문 식별자가 우선.
- 하드코딩된 로컬 경로 / DB credential 금지.
- 필수 컬럼 미존재 시 즉시 raise.
- pandas chained assignment 금지.
- pandas `inplace=True` 가능하면 회피.

---

## 7. 사용자 결정 이력 (확정)

| # | 항목 | 결정 |
|---|---|---|
| 1 | us_treasury_30y 데이터 소스 | 자동 fallback 금지. `required_but_missing`. proxy 는 사용자가 명시 지정할 때만. |
| 2 | dm_ex_us_equity 정본 ticker | 분리: `optimization=TAD09XU`, `regime_return=M2WOU` |
| 3 | kr_aggregate_bond 정본 ticker | 분리: `optimization=SPBKRCOT`, `regime_return=KISKALBI` |
| 4 | MVO 목적함수 | `max_sharpe` default. dispatch table 4종 (max_sharpe / utility / min_volatility / max_return_under_risk_limit). 하드코딩 금지. |
| 5 | ERR 정의 | Phase A 비구현. `err.enabled: false`. placeholder 만 보존. |

---

## 8. 미확정 사항 — 사용자 결정 필요

| # | 항목 | 결정 시점 | 메모 |
|---|---|---|---|
| 6 | ECI 입력 region (G7 / G20 / KOR / per_asset) | Phase B 백테스트 후 | 현재 default = G7 |
| 7 | TAA tilt 폭 (±2 / ±3 / ±5%p) | Phase B 백테스트 후 | 현재 default = ±3%p |
| 8 | 합성 ETF 화이트리스트 키워드 | Phase B | 현재: 베트남/인도네시아/태국/멕시코/브라질 |
| 9 | 단일 운용사 concentration 한도 | Phase B | ETF 60%, Fund 50% (초안) |
| 10 | us_treasury_30y 데이터 부재 처리 | Phase B 시작 전 | 옵션: (a) 9→8 축소 CMA + warning, (b) 강한 error, (c) warning-only 0 weight |

---

## 9. 보고 형식

작업 완료 시:

```
## 완료 요약

### 1. 생성/수정 파일
- ...

### 2. 핵심 설계 / 변경 사항
- ...

### 3. 확인된 사실
- ...

### 4. 미확정 / 리스크
- ...

### 5. 다음 작업 제안
- ...
```

특히 다음은 매번 명시 보고:

1. 미국 국고채30년 데이터 처리 상태
2. optimization_vba 의 목적함수 (Excel `$L$26` 직접 확인 진행 여부)
3. regime 산식이 source 와 일치하는지
4. ETF/Fund universe 필터 후 후보군 수

산출물 카운팅 시에는 반드시 **카테고리별로 구분** (docs / source_review / config / code / test).

---

## 10. 항상 지킬 것

```
× 상위 Advisory/ 또는 python/CLAUDE.md 수정 금지
× DB credential 을 코드/yaml 에 직접 작성 금지
× silent fallback (us_treasury_30y 같은 missing data 의 자동 대체) 금지
× HY 를 normal safe bond 로 취급 금지
× 혼합형/자산배분형/TDF 를 universe 에 포함 금지
× UI / 대시보드 작성 금지
× 1차 단계에서 product-level MVO 실행 금지 (asset-level 만)
× MVOOptimizer 내부에 목적함수 하드코딩 금지 (반드시 dispatch table)
```

---

## 11. 다음 단계 — Phase D 진입점

**현재는 Phase D (Governance & Operation Readiness).** 코드 작업이 아니라 운용역 결정 + 외부 자료 + 운영 준비.

다음 세션 시작 시 다음 순서로 진행:

1. `docs/phase_d_declaration.md` 읽기 — freeze 정책, 결정 전/후 작업 분리
2. `docs/investment_decision_register.md` 읽기 — 14개 결정 항목 상태
3. `docs/current_state_freeze.md` 읽기 — 동결 상태 확인
4. `pytest tests/ -q` sanity (124 passed / 5 skipped / 1 xfailed 기대)
5. 사용자에게 다음 중 어디부터 진행할지 확인:
   - (P) 결정 없이 가능 작업: 문서 정합성 / Decision Register 갱신 / review packet 표현 보강 / 운영 절차 문서화 / sanity 진단 추가
   - (A~F) 운용역 결정 수령 후 yaml 정책값 적용
   - (H~J) 운영자 결정 수령 후 외부 연동 (regime DB, GlidePath, HTML reporting)

> **Phase B/C 작업 순서는 Phase C.5 완료로 만료됨. 본 섹션은 더 이상 Phase B 진입점이 아님.**

이전 Phase B 진입 시점의 작업 순서는 `docs/phase_b_review_packet.md` 에 보존.

요약 (자세한 내용은 HANDOFF.md):

```
Step 1. us_treasury_30y 처리 정책 사용자 확인 (a/b/c 선택)
Step 2. CapitalMarketAssumptionBuilder.build() 구현
Step 3. MVOOptimizer.optimize() max_sharpe 분기 구현
Step 4. RegimeAnalysisTool.run() 구현 (G7 default)
Step 5. TAAOverlayEngine.apply() 구현
Step 6. UniverseTool.run() + ProductClassifier.classify() 구현
Step 7. tools/run_optimization.py 동작
Step 8. smoke test 추가 (SAA weight 합=1, bound, equity 합 ∈ [0.75, 0.85])
```

각 Step은 작은 독립 PR 단위로 가능. 사용자 검토 포인트는 Step 1, Step 3 후 (max_sharpe 결과 sanity check), Step 8 후 (전체 통과).
