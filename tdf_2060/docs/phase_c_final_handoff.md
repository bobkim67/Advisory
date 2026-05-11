# Phase C Final Handoff — TDF 2060 Engine

작성일: 2026-05-07. 다음 세션/운용역 리뷰 진입점.

> Phase C.4 까지 완료. DB 기반 TDF 2060 ETF/Fund 포트폴리오가 운용역 검토 가능한 수준으로 산출됨. **이제 다음 게이트는 코드가 아니라 운용역 의사결정**.

---

## 1. 현재 완료 상태

| 단계 | 산출 | 핵심 결정 |
|---|---|---|
| Phase A | 코드 골격 + 44 smoke test | 17개 NotImplementedError 흐름 정의 |
| Phase B | minimal end-to-end (file 모드) | ust30 (b)강한 error 정책, GlidePath = reference_weights, csv/json 출력 |
| Phase B.5 | weight closure + fallback | 자산군 pro-rata → bucket sibling → cash placeholder |
| Phase B.5+ | drift / quality_status | clean / warning / review_required 분리 |
| Phase C-pre | classifier yaml 외부화, 채권 룰 보강, quant_grade_policy | Fund 매핑 사각지대 해소 |
| Phase C | DBMarketDataRepository 구조 + composite + fake DB 동등성 | --source file/db, --as-of-date |
| Phase C.1 | semantic_type / return_transform / sanity / dry-run / inspect CLI | yield/spread/macro의 MVO 오사용 차단 |
| Phase C.2 | 9개 자산 SCIP dataset 매핑 확정 | requires_decision 0건 |
| Phase C.3 | TAA feasibility projection (SLSQP) | long-only + bucket bound 항상 보장 |
| Phase C.4 | 운용역 review packet (json + Markdown) | 8 섹션 + policy_review_items 자동 추출 |
| Phase C.5 | Golden answer parity validation | Placement/Velocity/Regime classification PASS, 그 외 SKIP/xfail (답안지 부재/정의 미명시) — `docs/golden_answer_validation.md` |

**전체 테스트**: `pytest tests/ -q` → **124 passed, 5 skipped, 1 xfailed**.

분포: A(44) + B(33) + B.5(5) + B.5+(7) + C-pre(7) + C(7) + C.1(7) + C.3(7) + C.4(5) + C.5(2 PASS) = 124.

Phase C 는 **DB 기반 E2E 기능 구현 완료 상태**. 단, 기존 VBA/Excel 답안지와의 parity 검증은 Phase C.5 에서 별도 수행했으며, *DRM 보호 Excel 5건 + regimeAnalysis_rt 정의 명시* 가 끝나야 SAA/TAA/Final weights 1:1 parity 까지 검증 가능. 운용역 리뷰 전 `golden_answer_validation.md` 결과를 함께 보는 것을 권장.

---

## 2. 현재 엔진 흐름 (DB 모드)

```
SCIP back_datapoint (시계열)
    ↓ DBMarketDataRepository (semantic_type 검증, sanity check)
CMA (E[R], σ, Σ)
    ↓ MVOOptimizer (SLSQP, max_sharpe, weight_bounds, bucket bounds)
SAA weights
    ↓ RegimeAnalysisTool (regime_src → Placement → Velocity → ECI 1~4)
    ↓ TAAOverlayEngine (regime tilt 적용 + cash-neutral)
    ↓ project_to_feasible (SLSQP: min Σ(w-target)², long-only + bucket bound)
TAA weights (feasible)
    ↓ UniverseTool (yaml 룰, 9 자산군 매핑, classifier diagnostics)
    ↓ ProductSelectionTool (scoring + Core/Satellite + manager cap, quant_grade_policy)
Selection
    ↓ apply_fallback (pro-rata → bucket sibling → cash placeholder)
PortfolioBuilder + PortfolioValidator (weight sum / non-negative / fallback warnings)
    ↓ build_review_packet (review_summary / projection_summary / asset_allocation / product_allocation / policy_review_items)
Output: csv + json + review_<pt>_<date>.md
```

---

## 3. 주요 산출물 / 위치

### 3.1 코드

```
tdf_2060/tdf_engine/
├── config/
│   ├── tdf_2060.yaml                — strategic_allocation, weight_bounds, taa_bounds, final_asset_bounds
│   ├── optimization_constraints.yaml — MVO objective dispatch, SLSQP options
│   ├── universe_filter.yaml         — KIS MP 화이트리스트, exclude keywords, quant_grade_policy
│   ├── taa_policy.yaml              — regime 1~4 별 tilt, per_asset_max_tilt
│   ├── asset_mapping.yaml           — 9 자산군 + ust30 db_mapping_mode=direct
│   ├── universe_classification.yaml — Phase C-pre 신설, priority 기반 룰
│   └── db_sources.yaml              — Phase C.2 9 자산 dataset_id 확정
├── domain/                          — enums + dataclass
├── repositories/
│   ├── interfaces.py                — Protocol
│   ├── file_repositories.py
│   ├── db_market_data.py            — Phase C, C.1, C.3
│   ├── composite.py                 — DB + file 위임
│   ├── semantic.py                  — Phase C.1 정책 검증
│   └── _blob.py                     — SCIP blob 파서 (dict/단일/문자열, KIS dict)
├── optimization/                    — CMA, MVO (max_sharpe), constraints
├── regime/                          — placement / velocity / classifier / returns
├── taa/
│   ├── policy.py                    — RegimeTAAPolicy
│   ├── overlay.py                   — Phase C.3 projection 통합
│   ├── projection.py                — Phase C.3 SLSQP feasibility projection
│   └── tool.py
├── universe/                        — filters / classifier (yaml-driven) / tool
├── selection/                       — scoring (grade_policy) / selector / tool
├── portfolio/
│   ├── builder.py                   — fallback + quality 호출
│   ├── fallback.py                  — Phase B.5 + B.5+
│   ├── quality.py                   — Phase B.5+
│   ├── validator.py                 — projection / fallback / quality warnings
│   └── tool.py                      — orchestrator
├── reporting/
│   └── review.py                    — Phase C.4 build_review_packet + render_markdown
└── tools/
    ├── build_portfolio.py           — main CLI (--source / --as-of-date / --dry-run-db-check)
    ├── inspect_db_sources.py        — Phase C.1 read-only DB 탐색
    ├── run_optimization.py / run_regime.py / run_regime_return.py / run_universe.py
```

### 3.2 산출물 (실 DB 실행 결과)

```
tdf_2060/out/
├── db_etf/
│   ├── portfolio_etf_20260507.csv   — product 단위 26 row
│   ├── portfolio_etf_20260507.json  — 전체 + diagnostics + review packet
│   └── review_etf_20260507.md       — 8 섹션 운용역 리포트
└── db_fund/
    ├── portfolio_fund_20260507.csv
    ├── portfolio_fund_20260507.json
    └── review_fund_20260507.md
```

(file 모드 산출은 `out/file_etf/`, `out/file_fund/` 또는 별도 `--output-dir`)

### 3.3 문서

```
tdf_2060/docs/
├── tdf_2060_tech_spec.md
├── tdf_engine_architecture.md
├── db_schema.md                     — 4개 DB 142 테이블 카탈로그 (용도 중심)
├── phase_b_review_packet.md         — Phase A/B/B.5/B.5+/C-pre 누적 리뷰
├── phase_c_db_repository.md         — Phase C/C.1/C.2/C.3/C.4 누적 (12 섹션)
└── phase_c_final_handoff.md         — 본 문서
```

---

## 4. 운용역이 반드시 봐야 할 항목 (review packet 자동 감지 7건)

`review_etf_20260507.md` §8 / `review_fund_20260507.md` §8 에 동일 기록.

| # | 항목 | 현재 값 | 운용역 결정 |
|---|---|---|---|
| 1 | `kr_treasury_10y` final weight = **0.00%** | TAA tilt -2% 가 SAA 0%에 더해져 음수 → projection 으로 0 | 장기채 0% 수용 vs 강제 편입 (lower bound > 0?) |
| 2 | `us_treasury_30y` final weight = **0.00%** | TAA tilt -3% 가 SAA 0%에 더해져 음수 → projection 으로 0 | 동일 의사결정 |
| 3 | `dm_ex_us_equity` final = **4.29%** | TAA target 5% → projection 후 4.29% (final_asset_bound min=4%, near_bound) | 5% 의도였다면 lower bound 5%로 강화 |
| 4 | `us_value_equity` = **29.29%** (cap=30% 도달) | DB sharpe 매우 높아 SAA 가 cap 끝까지 | cap 30% 유지 vs 축소 (운용 다변화 정책) |
| 5 | `max_abs_projection_drift` = **3.00%** | ust30 −3% → 0% 가 가장 큰 drift | 3% drift 허용 가능 수준인지 |
| 6 | `us_treasury_30y` `obs=87` | 다른 자산 120 vs 87 (2018-12 ~) | lookback 통일 vs 자산별 차등 |
| 7 | DB σ/μ vs file σ/μ 차이 | DB 시계열 추정 vs file cross-section assumption | 운용 기준 정의 |

---

## 5. 현재 품질 상태 (실 DB ETF/Fund 동일)

```
constraints_passed        : True
quality_status            : warning            (review_required 아님)
asset_weight_sum          : 1.000000
product_weight_sum        : 1.000000
equity bucket             : 82.32%             (75~85 안)
fixed_income bucket       : 17.68%             (15~25 안)
fallback_used             : True               (us_growth_equity / us_value_equity product_cap_clipping)
projection_used           : True               (음수 자산 2개 → 0)
max_abs_projection_drift  : 3.00%
max_abs_asset_weight_drift: 0.00%              (자산군 fallback 0)
proxy_used                : False              (모두 직접 매핑)
db_warnings_count         : 0
validation_issues_count   : 0
validation_warnings_count : 8
```

**해석**: 제약 통과 + bucket bound 만족 + 음수 0 + sum=1.0. 다만 `warning`이고 7건의 정책 확인이 자동 감지됨 → 운용역 동의 후 적용 가능.

---

## 6. 운영 적용 전 결정 필요 사항

| # | 항목 | 결정 단위 | 의사결정 후 영향 |
|---|---|---|---|
| 1 | `final_asset_bounds` 운영 값 확정 | yaml 1줄 변경 | projection 결과 직접 변경 |
| 2 | 0% 허용 자산군 정책 (ust30 / kr_t10) | min 0% vs min > 0% | 강제 편입 시 projection 이 다른 자산에서 빌려옴 |
| 3 | projection drift 허용 기준 | 현재 3% (감지 임계 0%) | quality_status 결정 임계 |
| 4 | lookback 기간 정책 | 자산별 차등 vs 일괄 통일 | DB σ/μ 산출 결과 변경 |
| 5 | DB σ/μ 산출 기준 (월말 / 연환산 12 / lookback 10년) | computation_mode | 모든 SAA / TAA 결과 영향 |
| 6 | `us_value_equity` cap 30% | weight_bounds.max | DB 환경에서 cap 도달 빈번 — 축소 시 다른 자산 비중 ↑ |
| 7 | `quant_grade_policy` mode (Fund=score_penalty) | yaml | Fund 후보 풀 크기 |
| 8 | 운용사 concentration cap (ETF=60%, Fund=50%) | yaml | manager cap clipping 빈도 |

---

## 7. 다음 개발 후보 (운영자 결정 후 진행)

| 우선순위 | 항목 | 근거 |
|---|---|---|
| (선택) | regime DB 연결 (`solution.roboadvisorAPI_economicregime` 7,550행) | regime_src 파일 의존 제거 |
| (선택) | GlidePath DB/엑셀 연동 (`solution.roboadvisorAPI_glidepath` 1,017행 또는 DRM 해제 xlsx) | 단일 vintage(2060) → 다중 vintage |
| (선택) | HTML reporting (Plotly/Dash) | 현재 Markdown만. 대시보드는 운영 단계에서 |
| (작은 수정) | selection score 보존 | `product_allocation.score` 활성화 (selection.tool.py rows에 컬럼 추가) |
| (정책 결정 후) | `final_asset_bounds` hard enforce | 현재 warning만 → portfolio 단계에서 hard clip 옵션 |
| (보류) | duration_proxy 구현 | yield 시계열을 채권 수익률로 근사. 현 시점 SCIP의 모든 채권 자산이 TR index로 매핑되어 우선순위 낮음 |
| (보류) | synthetic mapping_mode 구현 | 합성 시계열. 현재 hook만 |

위 모두 *기능 추가*이고 운영 차단이 아님. **operational hold = 운용역 의사결정 (§6 1~8번)**.

---

End of handoff.
