# HANDOFF — TDF 2060 Engine

> **★ Current basepoint (2026-05-14, R-track 1차 close 후)**
> - `main = origin/main = 6d570d5` (R-track 1 close PR #1 머지 + `.gitignore` hotfix 통합 후)
> - 작업 브랜치 모두 정리, `main` 단독
> - R-track 2차 진입 전 framework 정리: [`docs/r_track_2_entry_brief.md`](docs/r_track_2_entry_brief.md)
> - operating_mode `relaxed_diagnostic` 유지, Decision Register count **14 유지**, Phase F **미진입**
> - 본 ★ 블록이 최신 기준점. 아래 § 이하는 Phase D 시점 (2026-05-08) 의 stale 정보를 일부 포함.

---

다음 세션 진입점. **Phase D (Governance & Operation Readiness) 진입 — 2026-05-08**.
Phase A~C.5 freeze. 코드 변경 없음.

---

## 0. TL;DR — 30초

- **현재 단계**: Phase D **relaxed + operating_mode=relaxed_diagnostic + D-02 Option A + drift_source 분류** (2026-05-08). 142 passed / 5 skipped / 1 xfailed. 본 산출은 **production 아닌 diagnostic baseline**. drift 두 단계 분해: projection drift 3% = redistribution_from_long_only_clipping, quality drift 10.60% = product_cap_clipping at us_growth.
- **테스트**: `pytest tests/` → **142 passed, 5 skipped, 1 xfailed** (124 + 5 relaxed + 7 Option A + 6 drift_source).
- **Hard constraint (현 단계)**: `long-only` + `sum-to-100%` + 데이터 무결성 (BRFUT004 / DB / NaN / optimizer · projection convergence). 그 외 모두 비활성 (bucket range, per-asset bounds, final_asset_bounds, per_asset_max_tilt 0.03).
- **DB 기반 ETF/Fund (relaxed)**: `constraints_passed=True`, `product_weight_sum=1.0`, **us_growth 70.6% 쏠림**, equity 100% (sanity flag ⚠), 0% 자산 5건. 산출: `out/db_etf_relaxed/`, `out/db_fund_relaxed/`, `out/db_review_relaxed/`.
- **Phase D register blocker = 0건** (D-02 / D-03 / D-08 / D-09 모두 closed by 운용역 sign-off 2026-05-08). 단 **"production-ready" 가 아니며 register blocker 만 해소** 된 상태. 엔진은 여전히 `relaxed_diagnostic` mode. Production 전환은 별도 단계. 다음 후보: Phase D completion review / non-blocker 정리 (D-06 ERR / D-13 / D-14) / relaxed governance / Phase E 정의.
- **D-08 limitation**: DRM 영구 해제 불가 → SAA/TAA/Final 1:1 parity 검증 영구 waived. GlidePath 정보는 운영자 직접 제공 → `tdf_engine/config/glidepath.yaml` (reference only).
- **금지**: optimization/regime/taa/selection/portfolio 로직 변경 (승인 없이), Phase A~C.5 코드 덮어쓰기.
- **읽을 문서 (우선순위, 다음 세션 first prompt 용)**:
  1. **`docs/phase_e_current_handoff.md`** ★ 본 시점 진입 정본. Phase D blocker 0 + Phase E design 완료 상태 + 변경 금지 영역 + 자주 발생하는 함정.
  2. `docs/phase_d_completion_review.md` — Phase D 완료 record + 7 영구 한계 + Phase E roadmap
  3. `docs/phase_e_relaxed_governance.md` — relaxed sign-off flow (E-2 design)
  4. `docs/phase_e_production_transition_design.md` — production 전환 설계 (E-1, 실제 전환 보류)
  5. `docs/investment_decision_register.md` — 결정 14건 (open 0 / pe 1 / pr 0 / dfd 3 / closed 10. D-08=closed_with_permanent_limitation)
  6. `docs/phase_d_declaration.md` — Phase D 정의 + freeze 정책 (stale instruction 처리 영구 원칙)
- **본 단계 변경 금지 (영구)**: TAA engine / regime_mvo / TAA optimizer / asset_tilts 수치 / bucket_tilts 활성화 / asset cap / manager cap / soft warning threshold / product cap / production mode 전환.
  4. `docs/phase_c_final_handoff.md` — Phase C.5 시점 직전 핸드오프
  5. `docs/golden_answer_validation.md` — Phase C.5 답안지 parity 분해 분석
  6. `CLAUDE.md` (본 디렉토리) — Phase 진행 현황 + 미완료 항목
  7. `docs/phase_c_db_repository.md` — Phase C/C.1/C.2/C.3/C.4 누적 (12 섹션)
  8. `docs/phase_b_review_packet.md` — Phase A/B/B.5/B.5+/C-pre 누적 (14 섹션)

---

## 1. 빠른 sanity check (세션 시작 시)

```bash
cd C:/Users/user/Downloads/python/Advisory/tdf_2060
/c/Users/user/Downloads/python/.venv/Scripts/python.exe -m pytest tests/ -q
# 기대: 124 passed, 5 skipped, 1 xfailed
```

수치가 맞지 않으면 무엇이 깨졌는지 먼저 확인 후 진행.

---

## 2. 작업 디렉토리 / 환경

```
PROJECT_ROOT  = C:/Users/user/Downloads/python/Advisory/tdf_2060
ADVISORY_ROOT = C:/Users/user/Downloads/python/Advisory   (소스 파일 직속, 외부)
VENV_PYTHON   = C:/Users/user/Downloads/python/.venv/Scripts/python.exe
```

git 저장소 아님 (현재 시점). commit 진행 X.

---

## 3. 현재 산출물

### 3.1 코드 (`tdf_engine/`)

```
config/                — yaml 7종 (tdf_2060, optimization, universe_filter, taa_policy,
                          asset_mapping, universe_classification, db_sources)
domain/                — enums + dataclass
repositories/          — file_repositories, db_market_data, composite, semantic, _blob
optimization/          — CMA, MVO (max_sharpe), constraints
regime/                — placement, velocity, classifier, returns, tool
taa/                   — policy, overlay (+projection 통합), projection, tool
universe/              — filters, classifier (yaml-driven), tool
selection/             — scoring (grade_policy), selector, tool
portfolio/             — builder (+fallback +quality), fallback, quality, validator, tool
reporting/             — review (Phase C.4 build_review_packet + render_markdown)
tools/                 — build_portfolio (--source/--as-of-date/--dry-run-db-check),
                          inspect_db_sources, run_optimization, run_regime, run_regime_return,
                          run_universe
```

### 3.2 실 DB 산출물 (운영자 검토 대상)

```
out/db_etf/   — portfolio_etf_20260507.csv / .json / review_etf_20260507.md
out/db_fund/  — portfolio_fund_20260507.csv / .json / review_fund_20260507.md
out/db_dry_run/db_dry_run.json   — DB sanity 사전 검증
```

### 3.3 문서 (`docs/`)

```
phase_c_final_handoff.md        ← 다음 세션 진입점
golden_answer_validation.md     ← Phase C.5 분해 분석
phase_c_db_repository.md        ← Phase C/C.1/C.2/C.3/C.4 누적
phase_b_review_packet.md        ← Phase A/B/B.5/B.5+/C-pre 누적
db_schema.md                    ← 4개 DB 142 테이블 카탈로그
tdf_2060_tech_spec.md           ← 초기 기술 스펙
tdf_engine_architecture.md      ← 초기 아키텍처
```

---

## 4. 다음 세션 시작 시 첫 5분 액션

```
1. 본 HANDOFF.md 끝까지 1번 읽음
2. docs/phase_c_final_handoff.md 읽음 (전체 상태)
3. pytest sanity (§1)
4. 사용자 의사 확인:
   (a) 운용역 리뷰 결과 수령 → 정책 적용
   (b) Excel DRM 해제 → SAA/TAA/Final parity 활성
   (c) regime DB 연결 (solution.roboadvisorAPI_economicregime)
   (d) GlidePath 연동
   (e) HTML/대시보드 reporting
   (f) 그 외
```

---

## 5. 절대 잊지 말 것

| 정책 | 적용 위치 |
|---|---|
| ust30 (b) 강한 error | `cma.py`, `db_market_data.py` |
| `final_asset_bounds`는 warning 만 | `validator.py` (hard enforce 정책 미정) |
| `quant_grade_policy`: ETF=hard_filter, Fund=score_penalty | `universe_filter.yaml` |
| TAA projection: SLSQP min Σ(w-target)² + long-only + bucket bound | `taa/projection.py` |
| 9개 SCIP dataset 매핑 확정 | `db_sources.yaml` (kr_aggregate=59, kr_t10=421, ust30=201, hy=401, ...) |
| Dashboard region = USA (Phase C.5 식별) | `tests/golden_helpers.py::DASHBOARD_REGION` |
| MVO objective dispatch (사용자 결정 #4) | `optimization/optimizer.py::OBJECTIVE_REGISTRY` (max_sharpe 만 활성, 나머지 stub) |

---

## 6. 미해결 결정 항목 (운용역 / 운영자)

§ phase_c_final_handoff.md §4·§6 + golden_answer_validation.md §5.4·§10 참조.

핵심:
1. ust30 / kr_t10 0% 허용 여부
2. dm_ex_us_equity 4.29% (lower bound 4%) 의도와 정합?
3. us_value_equity 30% cap 적정성
4. projection drift 3% 허용 임계
5. Excel DRM 3건 해제 또는 SAA/TAA/Final csv export
6. regimeAnalysis_rt 정의 명시 (region / annualization / regime base)
7. final_asset_bounds 운영 값
8. lookback 정책 (자산별 vs 일괄)

---

이상.
