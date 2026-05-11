# TDF 2060 Engine — 통합 프로젝트 현황 (2026-05-11)

본 문서는 프로젝트 현황 파악에 필요한 31개 md 파일의 전체 내용을 단일 파일로 통합한 것이다.

> ⚠️ **본 문서는 31개 원본 md 파일의 합본**이며, 향후 정본 수정은 각 원본 파일에서만 진행한다.
> 본 문서는 read-only 참조용으로만 사용한다.

---

## 목차

### A. 필수 (5분 안에 현재 상태 파악)
1. [tdf_2060/docs/phase_e_current_handoff.md](#1-phase_e_current_handoffmd)
2. [tdf_2060/docs/phase_e_next_session_prompt.md](#2-phase_e_next_session_promptmd)
3. [memory/MEMORY.md](#3-memorymd)
4. [memory/project_state.md](#4-project_statemd)
5. [tdf_2060/CLAUDE.md](#5-tdf_2060-claudemd)

### B. 핵심 정책 메모리 (영구 보호 룰)
6. [memory/feedback_taa_rule_based_label.md](#6-feedback_taa_rule_based_labelmd)
7. [memory/feedback_mvpx_prototype_only.md](#7-feedback_mvpx_prototype_onlymd)
8. [memory/reference_bit_identical_baseline.md](#8-reference_bit_identical_baselinemd)
9. [memory/phase_e_visualization_state.md](#9-phase_e_visualization_statemd)
10. [memory/feedback_visualization_construction_story.md](#10-feedback_visualization_construction_storymd)
11. [memory/feedback_no_core_changes.md](#11-feedback_no_core_changesmd)
12. [memory/feedback_spec_first.md](#12-feedback_spec_firstmd)
13. [memory/feedback_no_blind_fix.md](#13-feedback_no_blind_fixmd)

### C. Phase 별 설계 / 정책 문서
14. [tdf_2060/docs/phase_d_declaration.md](#14-phase_d_declarationmd)
15. [tdf_2060/docs/phase_d_completion_review.md](#15-phase_d_completion_reviewmd)
16. [tdf_2060/docs/investment_decision_register.md](#16-investment_decision_registermd)
17. [tdf_2060/docs/current_state_freeze.md](#17-current_state_freezemd)
18. [tdf_2060/docs/phase_e_relaxed_governance.md](#18-phase_e_relaxed_governancemd)
19. [tdf_2060/docs/phase_e_production_transition_design.md](#19-phase_e_production_transition_designmd)
20. [tdf_2060/docs/phase_e_d13_d14_policy_brief.md](#20-phase_e_d13_d14_policy_briefmd)

### D. Phase E-6 ~ E-12 시각화 설계
21. [tdf_2060/docs/phase_e_output_visualization_redesign.md](#21-phase_e_output_visualization_redesignmd)
22. [tdf_2060/docs/phase_e7_explainability_data_contract.md](#22-phase_e7_explainability_data_contractmd)
23. [tdf_2060/docs/phase_e12_integrated_review_packet.md](#23-phase_e12_integrated_review_packetmd)

### E. 산출물 summary md (값 확인용)
24. [review_packet_both_20260511.md](#24-review_packet_both_20260511md)
25. [review_packet_etf_20260511.md](#25-review_packet_etf_20260511md)
26. [review_packet_fund_20260511.md](#26-review_packet_fund_20260511md)
27. [regime_history_summary_20260511.md](#27-regime_history_summary_20260511md)
28. [saa_frontier_summary_20260511.md](#28-saa_frontier_summary_20260511md)
29. [taa_tilt_summary_20260511.md](#29-taa_tilt_summary_20260511md)
30. [product_selection_visualization_summary_20260511.md](#30-product_selection_visualization_summary_20260511md)
31. [explainability_summary_20260511.md](#31-explainability_summary_20260511md)

---

# A. 필수 (5분 안에 현재 상태 파악)

---

## 1. phase_e_current_handoff.md

**원본 경로**: `tdf_2060/docs/phase_e_current_handoff.md` (정본, 2026-05-11 갱신)

# Phase E — Current Handoff (다음 세션 first prompt 용)

작성일: 2026-05-11 (E-12 완료 시점). 다음 세션 진입 시 **본 문서를 먼저 읽기**.
relaxed_diagnostic baseline 유지 + 제약 / TAA 변경 보류 정책 영구 기록.

### 0. TL;DR (30초)

- **현재 단계**: Phase D blocker = 0 + Phase E-2/E-1/E-4/E-6/E-6.2(MVP-X+polish)/E-7/E-8/E-9/E-10/E-11A/E-11B/E-12 완료. 4 설명 블록 (Regime / SAA / TAA / Product Selection) + 통합 review packet 까지 마무리.
- **operating_mode**: `relaxed_diagnostic` (production 아님).
- **pytest**: **`240 passed / 5 skipped / 1 xfailed`** (영구 기준치, E-12 완료 시점).
- **TAA 엔진**: prototype heuristic overlay. **변경 금지**. regime_mvo / TAA optimizer / confidence scaling 모두 future study only.
- **제약**: 자산 / manager / product cap 모두 **추가 금지**. soft warning threshold도 **추가 금지**. monitoring telemetry only.
- **다음 게이트**: E-13 (MVP-X deprecation) / E-14 (final report polish) / E-15 (PDF export) 중 사용자 선택. 또는 운용역 결정 입력 (D-06 외부 자료 / production dry-run 시점 / D-11·D-12·D-14 재검토 시점).
- **금지 영역**: TAA engine 변경 / regime_mvo 구현 / TAA optimizer 구현 / asset_tilts 값 변경 / bucket_tilts 활성화 / cap 추가 / soft warning threshold 추가 / production mode 전환.

### 1. 영구 핵심 문구 (인용 의무)

> **"Phase D completed register-blocker resolution only.
> This does not mean production readiness.
> The engine remains in relaxed_diagnostic mode."**

> **"현재는 relaxed_diagnostic baseline 을 유지하고, TAA 고도화와 제약조건 도입은
> 모두 future study / later phase 로 보류합니다."**

### 2. 현재 Decision Register 상태

**총 14건, blocker 0** (E-7~E-12 기간 변경 없음).

| status | count | D-ID |
|---|---:|---|
| open | **0** | — |
| pending_external | **1** | D-06 (ERR 정의) |
| pending_rerun | 0 | — |
| deferred | **3** | D-11, D-12, D-14 |
| **closed** | **10** | D-01, D-02, D-03, D-04, D-05, D-07, D-08 (closed_with_permanent_limitation), D-09, D-10, D-13 |

### 3. Phase E 진행 요약 (E-1 ~ E-12)

| candidate | 영역 | 상태 | 산출 |
|:---:|---|---|---|
| E-2 | Relaxed governance | ✅ design 완료 | `docs/phase_e_relaxed_governance.md`, governance_log/ |
| E-1 | Production 전환 설계 | ✅ design 완료 (실제 전환 보류) | `docs/phase_e_production_transition_design.md` |
| E-4 | D-13 / D-14 정책 | ✅ closed (D-13) / deferred (D-14) | `docs/phase_e_d13_d14_policy_brief.md` |
| E-6 | Visualization MVP (9 PNG) | ✅ → **appendix 격하** (downstream-only) | `tdf_engine/reporting/figures.py`, 9 PNG legacy |
| E-6.1 | Visualization Redesign 설계 | ✅ design | `docs/phase_e_output_visualization_redesign.md` |
| **E-6.2** | **Telemetry + MVP-X + polish** | ✅ **완료** | telemetry 6건 dump + MVP-X PNG + determinism patch |
| **E-7** | **Explainability Data Contract + Dump** | ✅ **완료** | `docs/phase_e7_explainability_data_contract.md` + 5 블록 JSON |
| **E-8** | **Regime Clock Visualization** | ✅ **완료** | 24m+ trajectory PNG + history JSON |
| **E-9** | **SAA MVO / Efficient Frontier** | ✅ **완료** | 5-panel PNG + frontier JSON (SLSQP grid scan) |
| **E-10** | **TAA Regime Tilt** | ✅ **완료** | 6-panel PNG + tilt JSON (**rule-based** 라벨 강제) |
| **E-11A** | **Selection Score Telemetry** | ✅ **완료** | selection_diagnostics.scored_products dump + bit-identical |
| **E-11B** | **Product Selection Visualization** | ✅ **완료** | 6-panel PNG + viz JSON |
| **E-12** | **Integrated Review Packet** | ✅ **완료** | md + html packet (ETF / Fund / Both) |

### 4. 산출물 / 문서 / 코드 위치 (E-7~E-12 신규 누적)

**4.1 신규 reporting 모듈**:
```
tdf_engine/reporting/
├── figures.py                    (기존 + E-6.2 render_mvpx orchestrator + appendix opt-in)
├── figures_mvpx.py               (E-6.2 — 1-page bridge, prototype/deprecated)
├── explainability.py             (E-7 — 5 블록 dict builder)
├── regime_clock.py               (E-8 — history backfill + clock PNG)
├── saa_frontier.py               (E-9 — scipy SLSQP frontier + MVO PNG)
├── taa_tilt.py                   (E-10 — rule-based diagnostic + 6-panel PNG)
├── product_selection_telemetry.py (E-11A — selection_diagnostics → telemetry dict)
├── product_selection_viz.py      (E-11B — visualization-ready + 6-panel PNG)
└── review_packet.py              (E-12 — md + simple html, asset 복사)
```

**4.2 신규 CLI**:
```
tdf_engine/tools/
├── build_explainability.py             (E-7)
├── build_regime_clock.py               (E-8)
├── build_saa_frontier.py               (E-9)
├── build_taa_tilt.py                   (E-10)
├── build_product_selection_telemetry.py (E-11A)
├── build_product_selection_viz.py      (E-11B)
└── build_review_packet.py              (E-12)
```

**4.3 코어 변경 (allocation 결과 bit-identical 보장)**:
```
tdf_engine/optimization/cma.py            (E-6.2 — μ/σ/ρ/Σ dump)
tdf_engine/optimization/tool.py           (E-6.2 — saa_weights dump)
tdf_engine/regime/tool.py                 (E-6.2 — regime history dump)
tdf_engine/portfolio/tool.py              (E-6.2 — regime history merge)
tdf_engine/portfolio/quality.py           (E-6.2 — set→sorted determinism patch)
tdf_engine/reporting/review.py            (E-6.2 — asset_allocation[].saa_weight)
tdf_engine/selection/tool.py              (E-11A — scored_products / excluded_by_asset / score_factors dump)
```

**4.4 신규 docs**:
```
docs/
├── phase_e_output_visualization_redesign.md (E-6.1, 기존)
├── phase_e7_explainability_data_contract.md (E-7)
├── phase_e12_integrated_review_packet.md   (E-12A)
└── phase_e_current_handoff.md              ★ 본 문서 (정본, E-12 완료 시점)
```

**4.5 산출물 (관용 경로)**:
```
out/db_review_relaxed_e62/
├── figures_polish/20260511/main/00_mvpx_bridge_{etf,fund}.png   (E-6.2 prototype, deprecated)
├── figures_polish_with_appendix/20260511/                       (E-6.2 + 9 PNG appendix)
├── explainability/20260511/                                     (E-7)
├── regime_history/20260511/                                     (E-8)
├── saa_frontier/20260511/                                       (E-9)
├── taa_tilt/20260511/                                           (E-10)
├── product_selection_telemetry/20260511/                        (E-11A)
├── product_selection_visualization/20260511/                    (E-11B)
└── review_packet/20260511/                                      (E-12)
    ├── review_packet_{etf,fund,both}_20260511.md
    ├── review_packet_{etf,fund,both}_20260511.html
    └── assets/  (8 PNG, sha256 verified copy of E-8/E-9/E-10/E-11B)

out/db_etf_relaxed_e62_e11a/portfolio_etf_20260511.{csv,json,md}   (E-11A 적용 후 portfolio)
out/db_fund_relaxed_e62_e11a/portfolio_fund_20260511.{csv,json,md}

out/db_etf_relaxed/                                             (production baseline, untouched)
out/db_fund_relaxed/                                            (production baseline, untouched)
out/db_review_relaxed/                                          (legacy E-6 figures, untouched)
```

**4.6 신규 tests (33 + 신규 70 = 누적 103 파일 / 240 test)**:
```
tests/
├── test_phase_e_figures.py                       (E-6, 기존)
├── test_phase_e62_telemetry.py                   (E-6.2 — 9 test)
├── test_phase_e62_mvpx.py                        (E-6.2 — 9 test)
├── test_phase_e7_explainability.py               (E-7 — 9 test)
├── test_phase_e8_regime_clock.py                 (E-8 — 7 test)
├── test_phase_e9_saa_frontier.py                 (E-9 — 11 test)
├── test_phase_e10_taa_tilt.py                    (E-10 — 12 test)
├── test_phase_e11a_product_selection_telemetry.py (E-11A — 10 test)
├── test_phase_e11b_product_selection_visualization.py (E-11B — 11 test)
└── test_phase_e12_review_packet.py               (E-12 — 10 test)

tests/_phase_e62_baseline.json   (E-6.2 allocation core sha256 snapshot, deterministic ordering)
```

### 5. Bit-identical / Allocation 결과 무변경 보장

| 검증 항목 | 결과 |
|---|---|
| E-6.2 telemetry 추가 후 ETF/Fund DB rebuild | ✅ deterministic-ordering 기준 sha256 일치 |
| E-11A selection telemetry 추가 후 ETF/Fund DB rebuild | ✅ baseline sha256 일치 (`test_e11a_baseline_bit_identical`) |
| MVP-X polish (E-6.2) | ✅ visual only, allocation 미참조 |
| E-7~E-12 phase | ✅ read-only on JSON, allocation 결과 변경 0 |

**baseline snapshot**: `tests/_phase_e62_baseline.json` — deterministic ordering 기준 (post determinism patch).

### 6. 4 설명 블록 — 운용역 질문 ↔ 산출물 매핑

| 운용역 질문 | 산출 |
|---|---|
| 1. 현재 경기국면이 어디인가? | **E-8** regime_clock — 24m trajectory + current ★ + regime change annotations |
| 2. SAA 는 어떤 MVO 로 산출되었나? | **E-9** saa_mvo — CMA scatter + ρ heatmap + frontier (selected_matches_max_sharpe=True) |
| 3. TAA 는 어떤 rule 로 어떤 자산 tilt? | **E-10** taa_tilt — rule-based label + 5 tilt + before/after ΔSharpe |
| 4. 어떤 상품이 어떻게 선택되었나? | **E-11B** product_selection — funnel + factor weights + 17 selected w/ rank |
| 5. 최종 포트폴리오 및 quality? | portfolio_*.json + **E-12** review_packet §6 |
| 6. 어떤 한계가 있나? | **E-12** review_packet §7 missing_data 통합 (5 phase) |

### 7. E-7 missing_data closure 추적

| missing field (E-7 §10) | closure |
|---|---|
| `regime.history (24m)` | ✅ closed by **E-8** (24m+ full coverage) |
| `saa.efficient_frontier` | ✅ closed by **E-9** (31 grid points + reference) |
| `product.scoring.scored_products` | ✅ closed by **E-11A/B** (selection_diagnostics dump + viz) |
| `taa.regime_conditioned_assumptions` | ⏳ future (regime_mvo, future_study only) — **영구 한계** |
| `product.selected_products.ticker` | ⏳ deferred — 외부 ticker mapping (별도 phase) |

### 8. 영구 한계 (Permanent Limitations, 갱신 없음)

7건 (E-7~E-12 기간 변경 없음):

| # | 한계 |
|---|---|
| 1 | DRM 3 xlsx 영구 해제 불가 |
| 2 | SAA / TAA / Final weights Excel 1:1 parity 영구 waived |
| 3 | MVO objective Excel `$L$26` 직접 확인 영구 waived |
| 4 | regimeAnalysis_rt definition 영구 부재 |
| 5 | `test_golden_regime_returns_match_expected` xfail 영구 |
| 6 | `glidepath.yaml` reference metadata only |
| 7 | TAA tilt = prototype operator-defined heuristic (final quantitative TAA 영구 아님) |

E-7~E-12 추가:

| # | 한계 |
|---|---|
| 8 | TAA = rule-based regime overlay only — regime-conditioned MVO 미구현 (E-10/E-12 명시) |
| 9 | Ticker mapping unavailable — 모든 product identifier 는 product_id / product_name (E-11A/B/E-12 명시) |

### 9. 영구 사용 금지 / 추가 금지 (E-12 시점 갱신)

```
✗ TAA engine 변경
✗ regime-adjusted MVO 구현
✗ TAA optimizer 구현
✗ asset_tilts 수치 변경
✗ bucket_tilts 실제 적용
✗ asset cap / floor / band 추가
✗ manager hard cap 추가
✗ manager soft warning threshold 추가
✗ product cap 변경 (현행 ETF=20% / Fund=30% 유지)
✗ production mode 전환 (yaml `operating_mode: production` 변경)
✗ Decision Register total count 14 변경
✗ 산출 결과 (asset weights / product weights) 영향 가는 어떤 변경
✗ E-7~E-12 신규 산출물 / docs / tests 임의 덮어쓰기
✗ MVP-X 를 main 자격 산출물로 사용 (prototype only, opt-in appendix)
✗ "optimized TAA" / "regime-conditioned MVO" 표현 사용 (rule-based only)
```

### 10. 다음 세션 시작 시 첫 5분 액션

```
1. 본 문서 (phase_e_current_handoff.md) 끝까지 읽음
2. docs/phase_d_completion_review.md + docs/phase_e_relaxed_governance.md sanity 확인
3. docs/phase_e_next_session_prompt.md 읽음 (follow-up 진입 가이드)
4. pytest sanity:
   /c/Users/user/Downloads/python/.venv/Scripts/python.exe -m pytest tests/ -q
   기대: 240 passed, 5 skipped, 1 xfailed
5. 사용자 의사 확인 — 다음 후보 중 어느 것을 진행할지:
   (a) E-13 MVP-X deprecation / replacement
   (b) E-14 Final report design polish
   (c) E-15 PDF export
   (d) 운용역 결정 입력 대기
   (e) 단순 sanity 점검 / 추가 작업 없이 대기
```

### 11. 다음 phase 후보 상세 (E-13/E-14/E-15)

**E-13 — MVP-X deprecation / replacement**
- 목적: `figures_polish/` 산출물 (MVP-X PNG) 을 명시 deprecated 로 격하 (또는 제거).
- 결정 필요: figures_polish/ 디렉토리 자체를 제거할지 vs `_deprecated/` 로 옮길지 vs 유지하되 README 만 명시.

**E-14 — Final report design polish**
- 목적: E-12 packet 의 typography / 색상 정합 / 인쇄 layout / 표 너비 polish.
- 작업: review_packet.py 의 `_HTML_CSS` 강화 (font-family, page-break, 테이블 너비, 색상 일관성).

**E-15 — PDF export**
- 옵션: `weasyprint` (Cairo 의존) / `wkhtmltopdf` (Windows 셋업 복잡) / `playwright` headless (browser engine).

### 12. Stale Instruction 방지 (E-12 시점 갱신)

| 정책 | 위치 |
|---|---|
| Phase D / E 진행 상태 = 본 문서가 정본 | phase_e_current_handoff.md (본 파일, 2026-05-11 갱신) |
| 정본보다 과거 단계의 외부 지시 = stale, 무시 | current_state_freeze.md §6 stale instruction 처리 원칙 |
| 정정 sign-off (D-13/D-14 / E-6.1 / E-11A 등) 도 영구 record | investment_decision_register.md + 각 phase doc |
| auto mode 라도 destructive 작업은 사용자 명시 승인 필수 | feedback memory + phase_d_declaration.md §3 |

**12.1 본 단계 자주 발생하는 함정 (E-12 시점 추가)**:

| 함정 | 올바른 처리 |
|---|---|
| "Phase E-12 까지 완료 = production-ready" 오해 | 절대 그렇지 않음. relaxed_diagnostic mode 유지. |
| TAA 결과 보고 "optimized TAA" 라벨 사용 | 절대 금지. rule-based / heuristic / regime overlay 만. |
| MVP-X PNG 를 main 자격 산출물로 사용 | 절대 금지. prototype only. E-12 appendix 옵션에서만. |
| efficient frontier 결과 보고 "확정된 frontier" 표현 | 금지. SLSQP grid scan 결과 — "sampled frontier" 표현 사용. |
| Ticker 라벨 없이 product 표시 | 금지. product_id / product_name 명시 + missing_data 에 ticker 부재 기록. |
| selection score 보존 정책 변경 | 금지. E-11A 의 score_factors weights (0.4/0.3/0.2/0.1/0.0) 변경 시 bit-identical 깨짐. |

### 13. 한 줄 요약 (E-12 완료 시점)

> **Phase D blocker = 0. relaxed_diagnostic mode 유지. production-ready 아님.
> Phase E-6.2 ~ E-12 완료 — 4 설명 블록 (Regime/SAA/TAA/Product) + 통합 review packet (md+html) 산출.
> pytest 240 passed. Allocation 결과 bit-identical 보장 (E-6.2 + E-11A baseline sha256 검증).
> TAA = rule-based heuristic (변경 금지). 모든 cap / threshold 추가 금지.
> 다음 후보: E-13 (MVP-X deprecation) / E-14 (polish) / E-15 (PDF). 사용자 sign-off 후 진입.**

---

## 2. phase_e_next_session_prompt.md

**원본 경로**: `tdf_2060/docs/phase_e_next_session_prompt.md`

# Phase E — Next Session First Prompt

작성일: 2026-05-11 (E-12 완료 직후). **다음 세션 진입 시 사용할 first prompt 텍스트**.

본 문서는 두 부분으로 구성:
1. §1 — **세션 시작 시 즉시 실행할 액션 (handoff sanity)**
2. §2 — **사용자가 Claude 에게 보낼 first prompt 후보 (선택지 4건)**

### 1. 세션 시작 즉시 실행 (handoff sanity)

```text
1. 메모리 정독:
   - C:\Users\user\.claude\projects\C--Users-user-Downloads-python-Advisory\memory\MEMORY.md (인덱스, 12 항목)
   - memory/project_state.md (Phase E-12 완료 상태)
   - memory/phase_e_visualization_state.md (E-6.2~E-12 6 turn 누적)
   - memory/feedback_taa_rule_based_label.md ("optimized TAA" 라벨 금지)
   - memory/feedback_mvpx_prototype_only.md (MVP-X = appendix only)
   - memory/reference_bit_identical_baseline.md (selection 코드 변경 시 baseline 검증)

2. 정본 문서 정독:
   - tdf_2060/docs/phase_e_current_handoff.md (2026-05-11 갱신, E-7~E-12 완료 반영)
   - tdf_2060/docs/phase_e12_integrated_review_packet.md (E-12 설계, 가장 최근)

3. pytest sanity:
   /c/Users/user/Downloads/python/.venv/Scripts/python.exe -m pytest tdf_2060/tests/ -q
   기대: 240 passed, 5 skipped, 1 xfailed

4. 산출물 sanity (production / 직전 phase 산출물 untouched):
   sha256 검증 8건 (E-7~E-11B PNG / JSON + e62/e62_e11a portfolio + taa_policy.yaml + MVP-X).

5. 사용자 first prompt 대기 — §2 의 선택지 중 사용자 결정 입력.
```

기대치 미달 시 — **코드 변경 진입 금지**, 사용자에게 root cause 보고 + 복구 방안 제안 후 명시 승인 받기.

### 2. First Prompt 후보 (사용자가 보낼 텍스트)

**Option A — E-13 진입 (MVP-X deprecation / replacement)**

```text
Claude, 새 세션 진입.
이전 세션에서 Phase E-12 (Integrated Review Packet) 까지 완료했다.
정본은 tdf_2060/docs/phase_e_current_handoff.md (2026-05-11 갱신).
pytest 240 passed 가 baseline.

다음은 E-13 MVP-X deprecation / replacement 으로 진행한다.

Goal:
figures_polish/ 디렉토리의 MVP-X 1-page bridge PNG 를 명시 deprecated 로 격하 또는 제거.

Required design decision (사용자 결정 필요):
1. figures_polish/ 디렉토리 자체 제거
2. figures_polish/ → figures_polish/_deprecated/ 로 이동
3. 유지하되 README / packet 내 "MVP-X = prototype only, deprecated" 명시만

권고: option (2). 단 사용자 결정 후 진입.

Hard requirements:
- E-12 packet 의 --include-appendix 옵션 호환성 유지
- pytest 240 baseline 유지
- 기존 production output unchanged
- Decision Register count = 14 unchanged
```

**Option B — E-14 진입 (Final report design polish)**

```text
Claude, 새 세션 진입.
이전 세션에서 Phase E-12 까지 완료했다. pytest 240 passed.
정본 = tdf_2060/docs/phase_e_current_handoff.md.

다음은 E-14 Final report design polish 로 진행한다.

Scope:
1. review_packet.py 의 _HTML_CSS 강화
   - font-family 정합 (Malgun Gothic + DejaVu Sans fallback)
   - @media print rule 강화 (페이지 break 힌트, A4 base)
   - 테이블 너비 조정 (max-width, overflow-wrap)
   - 색상 정합 (E-8~E-11B 차트 색상과 packet text 색상 일관성)
2. md / html 본문은 변경 없음 (CSS 만)
3. ETF / Fund / Both packet 재렌더 + 시각 확인

Hard requirements:
- review_packet.py 외 모든 모듈 미변경
- 4 standalone PNG 미변경 (assets/ 복사 그대로)
- pytest 240 baseline 유지
- HTML 외부 JS 의존 없음 (inline CSS only)
```

**Option C — E-15 진입 (PDF export)**

```text
Claude, 새 세션 진입.
이전 세션에서 Phase E-12 까지 완료. pytest 240 passed.

다음은 E-15 PDF export 진입을 검토한다.

Step 1 — 환경 평가:
- weasyprint Windows install 가능성 (Cairo / Pango 의존)
- wkhtmltopdf Windows binary 가용성
- playwright headless Chrome install 부담 (~150MB)

Step 2 — 사용자 결정 후 진입:
- backend 선택
- E-12 HTML → PDF 변환 CLI 신설 (build_review_packet_pdf.py)
- A4 layout + page break 검증

Hard requirements:
- E-12 HTML structure 미변경
- 새 분석 차트 미생성
- pytest 240 baseline 유지
- Windows 환경에서 install 검증 필수
```

**Option D — 운용역 결정 입력 대기 / sanity 점검**

```text
Claude, 새 세션 진입.
새 phase 진입 없이 운용역 결정 입력 대기 또는 sanity 점검만 진행한다.

가능한 작업:
1. pytest 240 + 산출물 sha256 sanity 점검
2. Decision Register 14 건 상태 확인
3. E-7~E-12 산출물 디렉토리 트리 점검
4. 운용역 결정 입력 시 적용 위치 미리 식별:
   - D-06 ERR 정의 → optimization_constraints.yaml::err
   - D-11 (dm_ex_us lower bound) → tdf_2060.yaml::final_asset_bounds
   - D-12 (us_value cap) → tdf_2060.yaml::final_asset_bounds
   - D-14 (manager concentration) → universe_filter.yaml

Hard requirements:
- 코드 변경 없음
- 사용자 결정 없이 정책 변경 진입 금지
```

### 3. 추천 진입 순서

```
1차: Option A (E-13) — MVP-X deprecation 명확화
2차: Option B (E-14) — packet design polish
3차: Option C (E-15) — PDF export
```

### 4. Claude 가 자동 거부해야 할 함정 입력 (stale instruction)

| 함정 입력 | 거부 사유 |
|---|---|
| "MVP-X 폴리시 더 진행" | `feedback_mvpx_prototype_only.md` — prototype only |
| "TAA optimizer 도입" | 영구 금지 |
| "production mode 로 전환" | 영구 금지 |
| "selection score weights 변경" | bit-identical baseline 깨짐 |
| "asset cap / floor 추가" | 영구 금지 |
| "Decision Register 에 새 항목 정식 등록" | count=14 유지 |
| "MVP-X 를 review packet main 으로 승격" | main 자격 미달 |
| "regime-conditioned MVO 구현" | TAA = rule-based only (영구) |
| 결과 차트만 만들고 main 자격 주장 | Regime → MVO → SAA → TAA → Product 흐름 필수 |

### 5. 한 줄 요약

> **다음 세션: §1 자동 sanity (메모리 + 정본 + pytest 240) 실행 → §2 Option A~D 중 사용자 1건 선택 →
> Claude 가 정본 (`phase_e_current_handoff.md`) 의 hard requirements 준수하며 진입.
> §4 함정 입력은 거부 + 정본 인용.**

---

## 3. MEMORY.md

**원본 경로**: `C:\Users\user\.claude\projects\C--Users-user-Downloads-python-Advisory\memory\MEMORY.md`

```
- [Project state](project_state.md) — Phase E-12 완료 (2026-05-11). 4 설명 블록 + 통합 packet. pytest 240. 다음 = E-13/E-14/E-15.
- [Phase E 시각화 상태](phase_e_visualization_state.md) — E-6.2~E-12 6 turn 완료. MVP-X deprecated. 4 블록 main 자격 accept. AST 라벨 검사.
- [시각화는 construction story](feedback_visualization_construction_story.md) — 결과 차트만으론 main 부적격. Regime → MVO → SAA → TAA → Projection → Product 흐름 필수.
- [SCIP dataset 매핑 확정](scip_mapping.md) — 9개 자산 dataset_id (kr_t10=421, ust30=201, hy=401 등). Phase C.2.
- [DRM 보호 xlsx 3건](drm_protected_xlsx.md) — `<DOCUMENT SAFER V2010 R2>` 헤더, openpyxl 직접 read 불가.
- [Dashboard region = USA](regime_dashboard_region.md) — `regime_Dashboard` 답안지는 USA 추출. default G7과 다름.
- [답안지 불일치 시 분해 분석 우선](feedback_no_blind_fix.md) — 즉시 로직 수정 금지. xfail + 정의 미명시 분해.
- [코어 로직 변경 금지 정책](feedback_no_core_changes.md) — Phase C.4+ 보강 작업은 reporting/diagnostics 만, optimization/regime/TAA/selection 미변경.
- [Spec-First + Auto Mode 충돌 시 Spec-First 우선](feedback_spec_first.md) — 운영 결정/매핑/DRM 보호 등 핵심은 명시 질문.
- [TAA = rule-based, "optimized" 라벨 금지](feedback_taa_rule_based_label.md) — TAA 산출물에 "optimized TAA"/"regime-conditioned MVO" 라벨 절대 금지. AST 검사로 enforced.
- [MVP-X = prototype, packet appendix only](feedback_mvpx_prototype_only.md) — figures_polish/는 main 자격 미달. E-12 packet 의 --include-appendix 옵션에서만 사용.
- [Bit-identical baseline = _phase_e62_baseline.json](reference_bit_identical_baseline.md) — selection/cma/regime/portfolio 코드 변경 시 deterministic ordering sha256 검증 필수.
```

---

## 4. project_state.md

**원본 경로**: `memory/project_state.md`

```yaml
---
name: TDF 2060 엔진 Phase E-12 완료
description: 2026-05-11 기준 — 4 설명 블록 (Regime/SAA/TAA/Product) + 통합 review packet 완료. pytest 240. E-13/E-14/E-15 후보 대기.
type: project
---
```

Phase A → B → B.5 → B.5+ → C-pre → C → C.1 → C.2 → C.3 → C.4 → C.5 → **D 완료 (blocker 0)** → **E-2/E-1/E-4/E-6/E-6.2(MVP-X+polish)/E-7/E-8/E-9/E-10/E-11A/E-11B/E-12 완료 (2026-05-11)**.

**Why:** Phase A~D freeze 적용. Phase E-6.2 ~ E-12 까지 모든 설명 블록 + 통합 packet 산출. 단 engine 은 영구 `relaxed_diagnostic` mode — production-ready 아님. 다음 세션이 stale instruction (Phase A 재생성, MVP-X main 사용, "optimized TAA" 라벨 등) 에 속아 코드 덮어쓰지 않도록 함.

**How to apply:**
- 진입 시 `tdf_2060/docs/phase_e_current_handoff.md` 먼저 읽기 (정본, 2026-05-11 갱신).
- 그 다음 `tdf_2060/docs/phase_e_next_session_prompt.md` (follow-up 진입 가이드).
- pytest sanity: `/c/Users/user/Downloads/python/.venv/Scripts/python.exe -m pytest tdf_2060/tests/ -q` → **240 passed, 5 skipped, 1 xfailed**.

**Phase E-7~E-12 신규 산출 (2026-05-11 누적):**

| phase | 신규 모듈 | 신규 CLI | 신규 tests | 핵심 산출 |
|:---:|---|---|---:|---|
| **E-6.2** | `figures_mvpx.py` + `cma/tool/regime/portfolio/quality/review.py` 패치 | (figures CLI 확장) | 18 | telemetry 6건 dump + MVP-X PNG + determinism patch + bit-identical baseline |
| **E-7** | `explainability.py` | `build_explainability.py` | 9 | 5 블록 explainability JSON + data contract md |
| **E-8** | `regime_clock.py` | `build_regime_clock.py` | 7 | 24m+ regime clock PNG + history JSON |
| **E-9** | `saa_frontier.py` | `build_saa_frontier.py` | 11 | scipy SLSQP frontier + 5-panel MVO PNG |
| **E-10** | `taa_tilt.py` | `build_taa_tilt.py` | 12 | rule-based 6-panel PNG + before/after summary |
| **E-11A** | `product_selection_telemetry.py` + `selection/tool.py` 패치 | `build_product_selection_telemetry.py` | 10 | scored_products dump + bit-identical 검증 |
| **E-11B** | `product_selection_viz.py` | `build_product_selection_viz.py` | 11 | universe funnel + 6-panel PNG |
| **E-12** | `review_packet.py` | `build_review_packet.py` | 10 | md + simple html packet (etf/fund/both) |

**Decision Register 14건** — E-7~E-12 기간 변경 없음 (count = 14 유지).

**4 설명 블록 ↔ 운용역 질문 매핑:**
- "현재 경기국면?" → E-8 regime_clock (R1, P=+0.7223, V=+0.0586, coverage=full 24/49 obs)
- "SAA 어떻게?" → E-9 saa_mvo (E[R]=15.40% σ=15.96% Sharpe=0.7769, selected==max_sharpe)
- "TAA 어떻게?" → E-10 taa_tilt (rule-based, em/kr/hy OW · kr_t10/ust30 UW, ΔSharpe=+0.0110)
- "어떤 상품 선택?" → E-11B product_selection (funnel 932→17, 17 selected w/ score+rank+name+manager)

**핵심 표현 제약 (영구, E-10/E-12 명시):**
- TAA: "rule-based regime overlay" / "Diagnostic before/after comparison" / "Not regime-conditioned MVO" / "Not optimized TAA"
- "optimized TAA" / "regime-conditioned MVO" 표현 사용 금지 (AST 정적 검사로 enforced)
- MVP-X: prototype only, packet appendix opt-in 만
- Efficient frontier: "sampled by SLSQP grid scan, not analytical"
- Ticker: "Ticker mapping unavailable; product_id / product_name used as identifier"

**E-7 missing_data 5건 closure:**
- regime.history(24m) ✅ E-8 / saa.efficient_frontier ✅ E-9 / product.scoring.scored_products ✅ E-11A+B
- 잔여: taa.regime_conditioned_assumptions (영구 한계 / future regime_mvo only), product.ticker (외부 mapping)

**산출물 디렉토리 (E-7~E-12 누적):**
```
out/db_review_relaxed_e62/
├── figures_polish/ + figures_polish_with_appendix/ (E-6.2, prototype)
├── explainability/20260511/ (E-7)
├── regime_history/20260511/ (E-8)
├── saa_frontier/20260511/ (E-9)
├── taa_tilt/20260511/ (E-10)
├── product_selection_telemetry/20260511/ (E-11A)
├── product_selection_visualization/20260511/ (E-11B)
└── review_packet/20260511/ + assets/ (E-12)

out/db_etf_relaxed_e62_e11a/  + out/db_fund_relaxed_e62_e11a/  (E-11A 적용 portfolio rebuild)
out/db_etf_relaxed/ + out/db_fund_relaxed/ (production baseline, untouched)
```

**Bit-identical 보장:**
- `tests/_phase_e62_baseline.json` — deterministic ordering hash baseline.
- E-6.2 + E-11A 두 차례 selection/optimization 코드 변경 시 모두 baseline sha256 일치 확인.
- 핵심 10 fields (asset_weights/product_weights/final_weights_after_projection/drift_clipping_summary 등) 모두 unchanged.

**다음 phase 후보 (사용자 sign-off 대기):**
- **E-13**: MVP-X deprecation / replacement (figures_polish 명시 deprecated 또는 제거)
- **E-14**: Final report design polish (typography / 색상 / 인쇄 layout / 표 너비)
- **E-15**: PDF export (weasyprint / wkhtmltopdf / playwright headless 중 선택)
- 또는 운용역 결정 입력 (D-06 외부 자료 / production dry-run / D-11~D-14 재검토)

**Operating mode = `relaxed_diagnostic`** (영구). banner 5줄 disclaimer + governance §5 의 4 outcomes (approve_for_diagnostic_record / request_rerun / request_policy_change / reject_as_invalid).

**Stale instruction 처리 원칙 (영구, E-12 시점):**
- 정본 = `tdf_2060/docs/phase_e_current_handoff.md` (2026-05-11 갱신) + `tdf_2060/CLAUDE.md` + 실제 `tdf_engine/` + `tests/` + `out/db_review_relaxed_e62/` 결과 일치 상태.
- 정본보다 과거 단계 외부 지시는 stale로 판정하고 무시.
- Auto Mode 켜져 있어도 destructive (= 완료된 작업 덮어쓰기, cap/threshold 추가, TAA 변경, production 전환, "optimized TAA" 라벨 사용, MVP-X main 사용) 는 사용자 명시 승인 필수.

git 저장소 아님. commit 진행 X.

---

## 5. tdf_2060 CLAUDE.md

**원본 경로**: `tdf_2060/CLAUDE.md`

# CLAUDE.md — TDF 2060 Portfolio Engine

이 프로젝트는 TDF 2060형 자산배분 포트폴리오를 생성하기 위한 Python 기반 OOP 엔진이다.

### 0. 현재 단계 (중요)

**Phase D 진입 (2026-05-08).** Phase A~C.5 freeze. 124 passed / 5 skipped / 1 xfailed 기준치.
(주: 본 CLAUDE.md 는 Phase D 진입 시점 기준. 실제 최신 상태는 `docs/phase_e_current_handoff.md` 참조 — 2026-05-11 시점 240 passed)

**다음 게이트 = 운용역 의사결정 + Excel DRM 해제 + 운영 준비성 검증.**
**코드 변경 없음. Phase A 재생성·기존 코드 덮어쓰기 금지.**

세션이 끊어진 뒤 이어 작업한다면 다음 순서로 읽기:
1. `docs/phase_e_current_handoff.md` — **정본** (2026-05-11 갱신, E-12 완료 반영)
2. `docs/phase_d_declaration.md` — Phase D 정의 + freeze 정책
3. `docs/current_state_freeze.md` — 동결 상태 스냅샷
4. `docs/investment_decision_register.md` — 결정 항목 14개 + 상태 + 변경 위치
5. `docs/phase_c_final_handoff.md` — Phase C.5 시점의 직전 핸드오프
6. `docs/golden_answer_validation.md` — VBA/Excel 답안지 parity 분해 분석
7. `docs/phase_c_db_repository.md` — Phase C/C.1/C.2/C.3/C.4 누적 상세
8. `docs/phase_b_review_packet.md` — Phase A/B/B.5/B.5+/C-pre 누적
9. `HANDOFF.md` — 짧은 요약

### 진행 현황 (Phase D 진입 시점 기록 — 현재는 Phase E-12 완료)

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
| Phase E-2 ~ E-12 | ✅ 완료 (2026-05-11) | 4 설명 블록 + 통합 packet (정본 phase_e_current_handoff.md 참조) |

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
- ~~HTML/대시보드 reporting~~ → Phase E-12 에서 HTML packet 추가 (md + simple html, no JS)
- duration_proxy / synthetic mapping_mode — hook 만 열어둠
- final_asset_bounds hard enforce — 현재 warning 만
- ~~selection score 보존~~ → Phase E-11A 에서 보존 (`product_allocation.score` 유효)

### 운용역 의사결정 대기 중 (Phase D 전)

1. `us_treasury_30y` final 0% / `kr_treasury_10y` final 0% 허용 여부
2. `dm_ex_us_equity` 4.29% (lower bound 4%, near_bound) 운용 의도와 정합한지
3. `us_value_equity` 30% cap 도달 적정성
4. `max_abs_projection_drift = 3.00%` 허용 임계
5. `final_asset_bounds` 운영 값 확정
6. `regimeAnalysis_rt` 정의 명시 (region / annualization / regime base — Phase C.5 §5.4)
7. Excel 원본 DRM 해제 또는 SAA/TAA/Final weights csv export

### 1. Project Goal

ETF형 TDF 포트폴리오와 펀드형 TDF 포트폴리오를 **동일한 엔진**에서 생성한다.

```
MVO 기반 SAA
  + Regime Analysis 기반 TAA Overlay
  + ETF / Fund 상품선정
= 최종 TDF 2060 포트폴리오 (ETF형 + 펀드형)
```

### 2. Business Context

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

### 3. MVO Asset Classes (9개)

**Equity (5개)**:
```
kr_equity              한국 주식           opt=M2KR INDEX        rr=M2KR Index
us_growth_equity       미국 성장주         opt=M2US000G Index    rr=M2US000G Index
us_value_equity        미국 가치주         opt=M2US000V Index    rr=M2US000V Index
dm_ex_us_equity        미국외 선진국 주식  opt=TAD09XU Index     rr=M2WOU Index   ★분리
em_equity              신흥국 주식         opt=M2EF Index        rr=M2EF Index
```

**Fixed Income (4개)**:
```
kr_aggregate_bond      한국 종합채권       opt=SPBKRCOT Index    rr=KISKALBI Index ★분리
kr_treasury_10y        한국 국고채10년     opt=KPGB10YR Index    rr=null
us_treasury_30y        미국 국고채30년     opt=null              rr=null         ★required_but_missing
us_high_yield          미국 하이일드 회사채 opt=LF98TRUU Index    rr=LF98TRUU Index  (risk_asset, credit)
```

**핵심 주의사항 (Phase A에서 코드/yaml/test로 강제됨)**:
1. **HY = `fixed_income` bucket + `risk_asset` + `credit` flag**
2. **us_treasury_30y 는 `fallback_policy: explicit_proxy_only`, `proxy.enabled: false`** — 자동 fallback 금지
3. **`source_names` 는 dict 가 아닌 `AssetSourceNames` dataclass**
4. **`required: true`** 는 자산군이 SAA 에 반드시 들어가야 함을 의미

### 4. 소스파일 (Advisory/ 직속)

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

### 5. Architecture

핵심 개념:
```
Repository 패턴: 계산 ↔ 데이터 분리
Tool 단위:       OptimizationTool, RegimeAnalysisTool, RegimeReturnTool,
                  TAAOverlayTool, UniverseTool, ProductSelectionTool,
                  PortfolioConstructionTool
Result Object:   pandas DataFrame 을 그대로 넘기지 않고 dataclass 로 wrap
Config-First:    비즈니스 룰은 yaml 에. Python 코드는 룰을 받아 실행.
```

ETF형/펀드형 차이는 `UniverseTool` 와 `ProductSelectionTool` 에서만. SAA / MVO / TAA 는 동일.

### 6. Design Conventions

**6.1 핵심 원칙**:
1. **계산 ↔ 데이터 접근 분리** — Repository 인터페이스로 추상화.
2. **silent fallback 금지** — 데이터 없으면 명시 에러 또는 명시 warning + diagnostics 기록.
3. **자산명 분리** — `asset_key` (영문), `display_name` (한글), `source_names.optimization`, `source_names.regime_return`.
4. **TAA 는 SAA 를 훼손하지 않는다** — 80/20 → 75/25 ~ 85/15 범위 내, ±%p 로만 overlay.
5. **HY = risk_asset** — 단순 채권 취급 금지.
6. **objective config-driven** — `MVOOptimizer` 내부에 목적함수 하드코딩 금지. dispatch table 사용.

**6.2 코딩 표준**:
- 타입 힌트 필수 (public method).
- 결과는 dataclass 로 wrap.
- 한국어 변수명/주석 허용 (금융 전문용어), 단 영문 식별자가 우선.
- 하드코딩된 로컬 경로 / DB credential 금지.
- 필수 컬럼 미존재 시 즉시 raise.
- pandas chained assignment 금지.
- pandas `inplace=True` 가능하면 회피.

### 7. 사용자 결정 이력 (확정)

| # | 항목 | 결정 |
|---|---|---|
| 1 | us_treasury_30y 데이터 소스 | 자동 fallback 금지. `required_but_missing`. proxy 는 사용자가 명시 지정할 때만. |
| 2 | dm_ex_us_equity 정본 ticker | 분리: `optimization=TAD09XU`, `regime_return=M2WOU` |
| 3 | kr_aggregate_bond 정본 ticker | 분리: `optimization=SPBKRCOT`, `regime_return=KISKALBI` |
| 4 | MVO 목적함수 | `max_sharpe` default. dispatch table 4종. 하드코딩 금지. |
| 5 | ERR 정의 | Phase A 비구현. `err.enabled: false`. placeholder 만 보존. |

### 8. 미확정 사항 — 사용자 결정 필요

| # | 항목 | 결정 시점 | 메모 |
|---|---|---|---|
| 6 | ECI 입력 region (G7 / G20 / KOR / per_asset) | Phase B 백테스트 후 | 현재 default = G7 |
| 7 | TAA tilt 폭 (±2 / ±3 / ±5%p) | Phase B 백테스트 후 | 현재 default = ±3%p |
| 8 | 합성 ETF 화이트리스트 키워드 | Phase B | 현재: 베트남/인도네시아/태국/멕시코/브라질 |
| 9 | 단일 운용사 concentration 한도 | Phase B | ETF 60%, Fund 50% (초안) |
| 10 | us_treasury_30y 데이터 부재 처리 | Phase B 시작 전 | 옵션: (a) 9→8 축소 CMA + warning, (b) 강한 error, (c) warning-only 0 weight |

### 9. 보고 형식

작업 완료 시:
```
## 완료 요약
### 1. 생성/수정 파일
### 2. 핵심 설계 / 변경 사항
### 3. 확인된 사실
### 4. 미확정 / 리스크
### 5. 다음 작업 제안
```

특히 다음은 매번 명시 보고:
1. 미국 국고채30년 데이터 처리 상태
2. optimization_vba 의 목적함수 (Excel `$L$26` 직접 확인 진행 여부)
3. regime 산식이 source 와 일치하는지
4. ETF/Fund universe 필터 후 후보군 수

### 10. 항상 지킬 것

```
× 상위 Advisory/ 또는 python/CLAUDE.md 수정 금지
× DB credential 을 코드/yaml 에 직접 작성 금지
× silent fallback (us_treasury_30y 같은 missing data 의 자동 대체) 금지
× HY 를 normal safe bond 로 취급 금지
× 혼합형/자산배분형/TDF 를 universe 에 포함 금지
× UI / 대시보드 작성 금지 (단 E-12 의 HTML packet 은 simple CSS 만, JS 없음 — 허용)
× 1차 단계에서 product-level MVO 실행 금지 (asset-level 만)
× MVOOptimizer 내부에 목적함수 하드코딩 금지 (반드시 dispatch table)
```

---

# B. 핵심 정책 메모리 (영구 보호 룰)

---

## 6. feedback_taa_rule_based_label.md

**원본 경로**: `memory/feedback_taa_rule_based_label.md`

```yaml
---
name: TAA = rule-based, "optimized" 라벨 금지
description: 모든 TAA 관련 산출물 / 라벨 / 텍스트에서 "optimized TAA" / "regime-conditioned MVO" 표현 절대 금지. AST 정적검사로 enforced.
type: feedback
---
```

TAA 관련 모든 산출물 / 라벨 / caption / docs 에서 "optimized TAA" 또는 "regime-conditioned MVO" 표현을 **절대 사용하지 않는다**. 현재 TAA 는 rule-based / heuristic / regime overlay 일 뿐이다.

**Why:** 사용자 명시 (E-10 spec): "현재 TAA는 regime-conditioned MVO가 아니라 rule-based / heuristic overlay다. 따라서 'TAA가 최적화되었다'라고 표현하면 안 된다." 운용역이 산출물을 보고 TAA 가 모델 기반 최적화 결과로 오해할 위험이 크기 때문. 실제로는 운영자 정의 정책값 (`taa_policy.yaml::regime_tilts.regime_<n>.asset_tilts`) 의 단순 lookup.

**How to apply:**
- 허용 라벨: "Rule-based regime overlay" / "Diagnostic before/after comparison" / "Not regime-conditioned optimization" / "rule-based heuristic" / "prototype heuristic"
- 금지 라벨: "optimized TAA" / "TAA optimization" / "regime-conditioned MVO" (positive context)
- negation context (예: "NOT optimized TAA", "not regime-conditioned MVO") 는 허용 — LIMITATION 명시 위해.
- AST 정적 검사: `tests/test_phase_e10_taa_tilt.py::test_module_does_not_claim_optimization` 가 runtime string literal 에서 검사. 신규 TAA 관련 모듈 작성 시 동일 패턴 검사 추가.
- E-12 packet 텍스트에도 limitation_text 5건 중 1건으로 명시 (`test_packet_includes_explicit_limitation_text` 검증).

**적용 위치 (영구):**
- `tdf_engine/reporting/taa_tilt.py`: LIMITATION_TEXT, METHOD_LABEL="rule_based", PNG footer 빨간 박스
- `tdf_engine/reporting/explainability.py`: taa_explainability.tilt_policy.method = "rule_based", regime_conditioned_assumptions.available=False
- `tdf_engine/reporting/review_packet.py`: LIMITATION_LINES 5건 중 1건
- `tdf_engine/reporting/figures_mvpx.py`: TAA bridge section "Label: Rule-based overlay, NOT optimized TAA"
- `tdf_2060/docs/phase_e_current_handoff.md`: §9 영구 사용 금지 / §12.1 자주 발생하는 함정

---

## 7. feedback_mvpx_prototype_only.md

**원본 경로**: `memory/feedback_mvpx_prototype_only.md`

```yaml
---
name: MVP-X = prototype, packet appendix only
description: figures_polish/ MVP-X PNG는 prototype/diagnostic. main 자격 미달. E-12 packet의 --include-appendix 옵션에서만 사용 허용.
type: feedback
---
```

MVP-X 1-page bridge PNG (`out/db_review_relaxed_e62/figures_polish/.../00_mvpx_bridge_*.png`) 는 **prototype / diagnostic 산출물**이며 운용역 review packet 의 main 자격 미달이다. 4 설명 블록 (E-8/E-9/E-10/E-11B) 이 main 자격을 차지한다.

**Why:** 2026-05-11 E-12 진입 시점에 사용자 결정: "현재 MVP-X PNG는 final report가 아니라 diagnostic prototype으로 확정한다." 폴리시 5건 (header / projection title / final 0% 라벨 / SAA non-zero / TAA tilt 정렬) polish 후에도 main 자격에는 도달 못함. 운용역이 한 페이지에 너무 많은 정보를 압축한 dashboard 형태보다 4 standalone 차트 + 통합 packet 으로 흐름을 읽기를 선호.

**How to apply:**
- MVP-X 산출물은 그대로 보존 (sha256 untouched), 단 main 자격으로 사용 금지.
- E-12 review_packet 의 main 섹션 (§0~§7) 에 MVP-X 진입 금지 — `--include-appendix` 옵션 시에만 §8 Appendix 에 포함 가능 (deprecated 라벨 명시).
- 다른 phase 작업에서 MVP-X PNG 직접 인용 금지. 대신 E-8/E-9/E-10/E-11B 의 standalone PNG 인용.
- MVP-X polish 추가 진행 금지 — E-13 deprecation 또는 제거 결정 대기.
- `tdf_engine/reporting/figures_mvpx.py` 자체는 유지 (코드 / test 남김) — 단 신규 main 자격 산출에 호출 금지.

**E-13 candidate (사용자 sign-off 대기):**
- option (a): `figures_polish/` 디렉토리 자체 제거.
- option (b): `_deprecated/` 로 이동.
- option (c): 유지하되 README/docs 에 "MVP-X = prototype only" 명시.

**적용 위치 (영구):**
- `tdf_engine/reporting/review_packet.py`: §0~§7 main 섹션, MVP-X 진입 금지. §8 Appendix 만 --include-appendix.
- `tdf_2060/docs/phase_e_current_handoff.md`: §9 영구 사용 금지 / §12.1 함정
- `tdf_2060/docs/phase_e12_integrated_review_packet.md`: §4 Section order — MVP-X = appendix

---

## 8. reference_bit_identical_baseline.md

**원본 경로**: `memory/reference_bit_identical_baseline.md`

```yaml
---
name: Bit-identical allocation baseline = tests/_phase_e62_baseline.json
description: selection / cma / regime / portfolio 코드 변경 시 검증 필수. deterministic ordering sha256 baseline.
type: reference
---
```

`tdf_2060/tests/_phase_e62_baseline.json` — Phase E-6.2 telemetry + determinism patch 적용 후의 allocation core sha256 snapshot. **selection / cma / regime / portfolio / scoring 코드를 변경하는 모든 phase 의 acceptance gate 로 사용**.

**Why:** Phase E-6.2 (telemetry 추가) + E-11A (scored_products telemetry) 두 차례 selection/optimization 모듈을 수정하면서, allocation 결과가 변하지 않았음을 보장하기 위해 hash baseline 을 도입. 이후 phase 에서도 동일 검증 필요.

**How to apply:**
- 검증 대상 10 fields (deterministic ordering 후 sha256 계산):
  - asset_weights / asset_weight_sum / product_weights / product_weight_sum
  - final_weights_after_projection / target_weights_before_projection
  - max_abs_projection_drift / bucket_weights_after_projection
  - drift_clipping_summary (inflow/outflow lists sorted, by_asset dicts key sorted)
  - max_abs_asset_weight_drift
- baseline 갱신은 **deterministic ordering 정책 변경 시에만**. 일반 telemetry 추가는 baseline 갱신 안 함.
- 신규 phase 가 selection/cma/regime 코드 수정 시:
  1. ETF + Fund DB rebuild → 별도 디렉토리 (e62_eXXX 형태)
  2. `_phase_e62_baseline.json` 의 sha256 과 비교
  3. mismatch 면 root cause 분석 (intended 변경인지 / regression 인지)
  4. test 추가 (예: `test_phase_eXXX_baseline_bit_identical`)

**과거 검증 통과 사례:**
- E-6.2: 첫 baseline 작성 (deterministic ordering patch 후)
- E-11A: scored_products telemetry 추가 후 ETF/Fund 모두 PASS (`test_e11a_baseline_bit_identical`)

**금지:**
- baseline 갱신을 위한 selection/cma/regime 결과 변경 — 변경 자체가 안 됨.
- deterministic ordering 정책 (`quality.py:101` set→sorted) 변경 — 변경 시 모든 prior phase 의 검증 깨짐.
- baseline 파일을 직접 수정 — 코드/정책 변경 사유 없이 새 hash 로 갱신 금지.

**위치:**
- baseline: `tdf_2060/tests/_phase_e62_baseline.json`
- 생성 시점: E-6.2 + determinism patch 적용 후
- 사용 위치: `test_phase_e62_telemetry.py::test_existing_baseline_snapshot_unchanged`, `test_phase_e11a_product_selection_telemetry.py::test_e11a_baseline_bit_identical`

---

## 9. phase_e_visualization_state.md

**원본 경로**: `memory/phase_e_visualization_state.md`

```yaml
---
name: Phase E 시각화 진행 상태 (E-6.2 ~ E-12 완료)
description: MVP-X prototype + 4 설명 블록 (Regime/SAA/TAA/Product) + 통합 review packet 완료. 다음 후보 = E-13/E-14/E-15.
type: project
---
```

시각화 단계가 prototype 1건 → 4 standalone 차트 → 통합 packet 으로 자리잡힘. 사용자 정책으로 MVP-X 는 deprecated, 4 설명 블록이 main 자격.

**Why:** 2026-05-08 ~ 2026-05-11 누적 6 turn 진행:
1. E-6.2: telemetry 6건 dump + MVP-X 1-page bridge 산출 → 사용자가 "diagnostic prototype, final report 아님" 판단
2. E-7: 데이터 계약 (5 블록 explainability JSON) + missing_data 5건 명시
3. E-8: regime clock 24m+ trajectory (사용자가 처음 기대한 그림 — accepted)
4. E-9: SAA MVO / efficient frontier (selected_matches_max_sharpe=True 입증)
5. E-10: TAA tilt rule-based 6-panel (LIMITATION 강조)
6. E-11A/B: selection score telemetry + visualization
7. E-12: 4 standalone → 1 packet 통합 (md + html)

각 단계마다 사용자가 "완료 처리" sign-off 후 다음 phase 진입.

**How to apply:**
- 시각화 작업 진입 시 정본 `tdf_2060/docs/phase_e_current_handoff.md` (2026-05-11 갱신) 먼저 읽기.
- 4 설명 블록 main 자격 = E-8 / E-9 / E-10 / E-11B (사용자 accept 완료).
- MVP-X (figures_polish/) = prototype, **packet appendix opt-in 만**. main 자격 미달.
- 모든 새 차트는 데이터 계약 (E-7) 위에 있어야 함 — direct telemetry 만, inferred 경로 금지.

**E-7 missing_data closure 진행표 (2026-05-11 시점):**

| missing field | 해결 phase | 비고 |
|---|---|---|
| `regime.history (24m)` | ✅ E-8 | 49 obs full / 24 obs window |
| `saa.efficient_frontier` | ✅ E-9 | 31 grid points + min_vol/max_sharpe/selected reference |
| `product.scoring.scored_products` | ✅ E-11A+B | selection_diagnostics.scored_products + viz |
| `taa.regime_conditioned_assumptions` | ⏳ 영구 (future regime_mvo) | E-10 미해결 표시. 절대 fake 금지. |
| `product.selected_products.ticker` | ⏳ 외부 ticker mapping | E-11A/B/E-12 missing_data 명시 |

**핵심 표현 제약 (영구, AST 정적 검사로 enforced):**
- TAA: "rule-based regime overlay" / "Diagnostic before/after comparison" / "Not regime-conditioned MVO" / "Not optimized TAA"
- 금지: "optimized TAA" / "TAA optimization" / "regime-conditioned MVO" positive label (E-10 test_module_does_not_claim_optimization, E-12 test_packet_includes_explicit_limitation_text 로 검증)
- Efficient frontier: "sampled by SLSQP grid scan, not analytical"
- MVP-X: prototype only — main 섹션 진입 금지
- Ticker: "unavailable" or "Ticker mapping unavailable" 명시 (silent omit 금지)

**산출 디렉토리 표준화 (2026-05-11):**
```
out/db_review_relaxed_e62/<phase_dir>/<as_of_run>/
  ├── <phase>_{etf,fund}_<as_of_run>.json
  ├── <phase>_{etf,fund}_<as_of_run>.png
  └── <phase>_summary_<as_of_run>.md
```
E-12 packet 은 `assets/` 서브디렉토리에 4 phase PNG 사본 (sha256 verified) + md/html 본문.

**Bit-identical 정책 (영구):**
- selection / cma / regime / portfolio 코드 변경 시 `tests/_phase_e62_baseline.json` 의 deterministic ordering sha256 일치 검증 필수.
- 변경 후 DB rebuild + `_phase_e62_baseline.json` 의 10 fields hash 비교가 신규 phase 의 acceptance gate.

**다음 phase 후보 (E-12 이후, 사용자 sign-off 대기):**

| candidate | 영역 | 위험 / 결정 필요 |
|:---:|---|---|
| **E-13** | MVP-X deprecation | figures_polish/ 디렉토리 제거 vs `_deprecated/` 이동 vs README 명시만 — 사용자 결정 필요 |
| **E-14** | Final report design polish | typography / 색상 정합 / 인쇄 layout / 표 너비. 시각 polish 만, 데이터 미변경. |
| **E-15** | PDF export | weasyprint (Cairo 의존) / wkhtmltopdf (Windows 셋업 복잡) / playwright headless (browser engine) 중 선택. 환경 install 가능성 검증 필요. |

**금지 (시각화 작업 전반, 영구):**
- allocation 결과 / optimizer / TAA / selection / scoring / config 직접 호출 또는 변경 금지.
- portfolio_*.json / review_*.md / comparison_*.md / 기존 phase 산출물 (figures/ figures_polish/ explainability/ regime_history/ saa_frontier/ taa_tilt/ product_selection_*) 변경 금지.
- 차트에 cap / threshold / band 선 그리기 금지 (caption 으로만 설명 가능).
- 단일 product cap 20% (ETF) / 30% (Fund) / manager cap 60% / 50% 등 selection-level cap 도 차트 점선 금지.
- Decision Register count (14) 변경 금지.
- "optimized TAA" / "regime-conditioned MVO" 라벨 사용 금지.
- MVP-X 를 main 자격 산출물로 사용 금지.

---

## 10. feedback_visualization_construction_story.md

**원본 경로**: `memory/feedback_visualization_construction_story.md`

```yaml
---
name: 시각화는 construction story, 결과 차트는 appendix
description: 운용역 review 시각화는 "왜 그렇게 나왔는가" 를 보여줘야 함. 최종 비중 차트만으로는 부족
type: feedback
---
```

시각화 main artifact 는 portfolio **construction story** (Regime → MVO → SAA → TAA → Projection → Product) 를 보여야 한다. 최종 자산/상품/운용사 비중만 그리는 차트는 main 자격 미달이며, **appendix only** 로 격하한다.

**Why:** 2026-05-08 E-6 MVP 9 PNG (asset_allocation / drift_summary / top_products / manager_concentration) 가 모두 downstream 결과만 표시하여 사용자 피드백 — "investment process review 관점에서 partial / downstream-only". 운용역의 핵심 질문 = "현재 regime 이 무엇인지 / MVO 입력값 / SAA → TAA 변화 / projection 영향" 인데 결과 차트만으로는 답변 불가.

**How to apply:**
- 시각화 작업 진입 시 main vs appendix 를 먼저 분리하고, appendix 항목만 만든 채 "MVP 완료" 보고 금지.
- main 차트는 흐름 (Regime → MVO → SAA → TAA → Projection → Product) 의 각 단계가 보여야 한다. 최소 3-4 단계는 main 에 포함.
- 데이터가 부족하면 (telemetry gap) 차트를 억지로 만들지 말고 gap 자체를 telemetry enhancement 항목으로 보고.
- "결과 차트 + caption" 으로 main 흉내내는 것 금지. caption 에 "us_growth 70.6% — Regime 1 의 us_growth tilt 0%" 같이 쓰는 것은 link 가 아닌 텍스트 우회.
- 기존 결과 차트는 삭제하지 않음. `## Appendix` 섹션으로 보존.

**구체 적용 (E-6 → E-6.1 재분류 사례):**
- 기존 9 PNG = appendix-E.1/E.4/E.5 로 격하.
- 신규 main 5 블록 (A Regime / B MVO Input & SAA / C TAA Overlay / D Projection & Drift / E Product) 설계.
- B 블록 (μ/σ/ρ) 은 telemetry gap → diagnostics dump 추가 후 진입.
- A / C / D 는 기존 diagnostics 로 즉시 가능 (saa_diagnostics, taa_diagnostics.taa_feasibility, regime).

---

## 11. feedback_no_core_changes.md

**원본 경로**: `memory/feedback_no_core_changes.md`

```yaml
---
name: 코어 로직 변경 금지 — reporting/diagnostics 만 보강
description: Phase C.4+ 부터 사용자가 일관되게 명시한 정책
type: feedback
---
```

Phase C.4 (review packet) 이후 작업에서 사용자는 반복적으로 **optimization / regime / TAA / selection / fallback 핵심 로직을 수정하지 말 것**을 강조한다. 보강 작업은 reporting / diagnostics / config / 검증 layer 만.

**Why:** 핵심 로직은 이미 운용 검토 가능 수준이고, 변경하면 (1) 회귀 위험, (2) VBA 답안지와의 parity 비교가 더 어려워짐, (3) 운용역 의사결정 결과를 받기 전에 lock-in 됨. C.4 작업지시 원문: "MVO, TAA projection, selection 로직을 수정하지 않는다." C.5: "최적화, TAA, selection 로직을 먼저 수정하지 않는다."

**How to apply:**
- 새 기능 추가 요청이 와도, 먼저 현재 코어 변경 없이 가능한지 검토.
- 가능하면 `tdf_engine/reporting/`, `tdf_engine/repositories/` (검증 helper), `tests/`, `docs/`, yaml config 만 수정.
- 코어 수정이 정말 필요하면 사용자에게 명시 확인 받음 (Phase C.3 = TAA projection 추가는 사용자 명시 지시 후 수행).
- Phase C.4 review packet 작업에서 `selection.tool.py` 의 score 보존이 안 되어 `product_allocation.score=null` 로 남긴 것이 좋은 예시 — 코어 변경 회피. (단, Phase E-11A 에서 score 보존이 정식 도입됨 — bit-identical 검증 통과)

---

## 12. feedback_spec_first.md

**원본 경로**: `memory/feedback_spec_first.md`

```yaml
---
name: Spec-First / Auto Mode 충돌 시 Spec-First 우선
description: 운영 결정·매핑·DRM 보호 등 핵심 항목은 Auto Mode여도 명시 질문
type: feedback
---
```

Auto Mode 가 활성화돼도, **핵심 운영 결정/매핑/데이터 출처**는 글로벌 CLAUDE.md 의 Spec-First 원칙을 우선 적용해 사용자에게 명시 질문한다.

**Why:** 운영 정책은 한번 잘못 lock-in 되면 후행 단계 모두 영향 받음. 이 프로젝트에서 사용자는 Auto Mode 켠 채로도 ust30 SCIP 매핑 결정 (`Phase C.2` 중간 "Treasury 30Y 쓰면 돼" → 실제로는 yield 라 `KIS BRFUT004` 로 교정), us_treasury_30y `mapping_mode` (direct/proxy/synthetic/requires_decision) 등을 *명시 질문 후* 결정해줬다. 추측해서 진행하면 거꾸로 돌아오는 비용이 큼.

**How to apply:**
- Auto Mode 라도 다음 항목은 `AskUserQuestion` 으로 명시 질문:
  1. 운영 데이터 매핑 결정 (dataset_id, ticker, proxy 여부)
  2. 정책 임계 (final bound, drift tolerance, 0% 허용 여부)
  3. 데이터 출처가 다중 후보일 때 (Treasury 30Y 가 yield-only / TLT proxy / KIS BRFUT004 중 어느 것)
  4. 운영자 동의 없이 수정하면 안 되는 yaml (asset_mapping, db_sources, taa_policy)
- 일반 코드 작성 / 리팩터링 / 테스트 추가 / 문서 갱신은 Auto Mode 그대로 진행 (질문 없이 실행).

**판단 기준:** "이 결정이 잘못되면 돌아올 비용이 코드 1줄 이상인가?" → Yes → 질문. No → 진행.

---

## 13. feedback_no_blind_fix.md

**원본 경로**: `memory/feedback_no_blind_fix.md`

```yaml
---
name: 답안지 불일치 시 즉시 로직 수정 금지 — 분해 분석 우선
description: Phase C.5에서 사용자가 명시한 정책. golden parity fail 시 코드 변경 X.
type: feedback
---
```

답안지 (VBA/Excel/golden) 와 Python 엔진 결과가 다를 때, **즉시 로직을 고치지 말고 어느 단계에서 차이가 발생했는지 먼저 분해**한다.

**Why:** Phase C.5 작업지시 원문에 명시. "DB 결과와 답안지를 직접 비교하지 말고, 먼저 src/file/VBA 입력 기준으로 비교한다", "답안지와 불일치가 나와도 즉시 로직을 고치지 말고, 어느 단계에서 차이가 발생했는지 먼저 분해한다." 답안지 자체의 정의 미명시 또는 입력 정렬 문제일 수 있어, 우리 로직을 먼저 의심하면 잘못된 수정으로 이어짐.

**How to apply:**
- 답안지 vs 엔진 결과 차이가 나면:
  1. 단계 분해 (CMA / Corr / SAA / Regime / TAA / Selection 중 어디서)
  2. 입력 정렬 확인 (region / lookback / 월말 정렬 / 자산 매핑)
  3. 답안지 정의 가정 확인 (산술 vs 기하 / sign-based vs angle-based / annualization)
- 차이 원인 후보를 docs 로 기록하고 운영자에게 결정 받음.
- 테스트는 `pytest.xfail(strict=False, reason=...)` 로 두어 회귀는 노출하되 미블로킹.
- 운영자가 정의를 명시한 후에만 strict=True 로 전환 또는 코드 수정.

**예시 (Phase C.5):**
- regimeAnalysis_rt parity 53.6% fail. 코드 수정 X. 6개 원인 후보를 `docs/golden_answer_validation.md §5.2` 에 분해. xfail 마크.

---

# C. Phase 별 설계 / 정책 문서

> 본 섹션의 phase_d_declaration.md / phase_d_completion_review.md / investment_decision_register.md / current_state_freeze.md / phase_e_relaxed_governance.md / phase_e_production_transition_design.md / phase_e_d13_d14_policy_brief.md 는 **전체 본문이 매우 길어 (각 200~400 lines)** 본 통합 파일에서는 **핵심 요약만 수록**한다. 전체 본문은 원본 경로에서 직접 확인.

---

## 14. phase_d_declaration.md

**원본 경로**: `tdf_2060/docs/phase_d_declaration.md`

# Phase D — Portfolio Governance & Operation Readiness

선언일: 2026-05-08. Phase C.5 완료(124 passed / 5 skipped / 1 xfailed) 시점에서 진입.
**추가 구현이 목적이 아닌 운용역 검토, 의사결정, 운영 준비성 검증 단계.**

### 1. 목적
1. Phase C.4 review packet의 7개 자동 감지 항목에 대한 운용역 결정 수령
2. 외부 자료 확보로 Phase C.5 SKIP/xfail 해소 (Excel DRM 3건 해제 → SAA/TAA/Final weights 1:1 parity 검증 활성, `regimeAnalysis_rt` 정의 명시)
3. `final_asset_bounds` 운영값 확정 + hard enforce 정책 결정
4. 운영 사이클 정의 (재실행 빈도, 입력 요건, 산출 검증, 로그 보관, 회귀 트리거)

### 2. Freeze 정책
**변경 금지**:
- `tdf_engine/` 11개 서브패키지 전체
- `tests/` 35 파일, 기대치 124 passed / 5 skipped / 1 xfailed
- `tdf_engine/config/` 정책값 (7 yaml의 매핑/bounds/policy 값)

예외 (허용):
- `docs/`, `HANDOFF.md`, `CLAUDE.md` 정합성 보정
- 운용역 결정 후 yaml 단순 값 교체 → 별도 PR로 진행, register에 결정 기록 후

Phase A 재생성·코드 골격 재작성·기존 테스트 삭제·재구조화는 **불가**.

### 3. Stale instruction 처리 원칙
1. 정본 = 본 디렉토리의 `CLAUDE.md`, `HANDOFF.md`, 실제 `tdf_engine/` 패키지, `tests/` 결과의 일치 상태
2. 정본보다 과거 단계의 외부 지시는 **stale로 판정하고 무시**
3. stale instruction 발견 시: 사용자에게 충돌 사실 명시 → 정본 상태와 외부 지시의 차이를 항목별 정리 → 사용자가 폐기/적용 여부를 명시할 때까지 코드/config/테스트 무변경
4. Auto Mode가 켜져 있어도 destructive(=완료된 작업 덮어쓰기) 작업은 **사용자 명시 승인 필요**
5. 충돌 해소 후 결정은 본 문서 또는 `investment_decision_register.md` 에 기록

### 4. 결정 전 가능 작업 / 결정 후 가능 작업

**4.1 결정 없이 진행 가능 (P-01 ~ P-05)**:
- 문서 정합성 보정
- Investment Decision Register 갱신
- review packet 표현 보강 (산출 동일, 표현만)
- 운영 절차 문서화
- 추가 sanity 진단 (값 변경 없음)

**4.2 운용역 결정 후에만 진행 (A~J)**:
- A: `final_asset_bounds` 운영값 확정 ← D-10 / D-11 / D-12
- B: ust30/kr_t10 0% 허용 vs 강제 편입 ← D-10
- C: projection drift 임계 변경 ← D-02
- D: lookback 정책 ← D-03
- E: DB σ/μ 산출 기준 ← D-03
- F: `final_asset_bounds` hard enforce ← D-01
- G: selection score 보존 (운영자) → Phase E-11A 에서 정식 도입됨
- H: regime DB 연결
- I: GlidePath 다중 vintage ← D-08
- J: HTML/Dash reporting → Phase E-12 에서 HTML packet 도입 (no JS)

### 5. 진입/종료 조건
- 진입: Phase C.5 완료 (현재 충족)
- 종료: Decision Register의 blocker 항목 모두 closed + `final_asset_bounds` 운영값 적용된 산출이 운용역 사인 받음

### 6. 본 Phase에서 절대 하지 말 것
- `tdf_engine/` 패키지 재생성
- 기존 모듈 덮어쓰기
- tests 삭제 또는 재작성
- 기존 passing 코드 구조 단순화
- Phase A 수준으로 롤백
- 파일을 대량으로 새 skeleton 으로 교체
- 기존 Phase C.5 결과물 훼손
- 상위 Advisory/, python/CLAUDE.md 수정
- DB credential을 코드/yaml에 직접 작성

### 7. 참조 문서
| 문서 | 역할 |
|---|---|
| `current_state_freeze.md` | 동결된 상태 스냅샷 |
| `investment_decision_register.md` | 결정 항목 + 상태 + 변경 위치 |
| `phase_c_final_handoff.md` | Phase C.5 시점의 직전 진입점 |
| `golden_answer_validation.md` | Phase C.5 parity 분해 분석 |
| `phase_e_current_handoff.md` | ★ 현재 정본 (2026-05-11 갱신) |

---

## 15. phase_d_completion_review.md

**원본 경로**: `tdf_2060/docs/phase_d_completion_review.md`

# Phase D Completion Review

작성일: 2026-05-08. **Phase D register blocker 0건 도달 시점의 공식 완료 검토**.

> ⚠️ **Phase D register blocker = 0건. 단 production-ready 아님.**
> 현재 엔진은 `relaxed_diagnostic` mode. Production 전환은 별도 Phase 에서 다룸.

### 1. Executive Summary

| 항목 | 값 |
|---|---|
| **Phase D register blocker** | **0건** (8 → 4 → 3 → 2 → 0) |
| **operating_mode** | `relaxed_diagnostic` |
| **production-ready** | **아님** |
| **hard constraint** | `long-only` + `sum-to-100%` + 데이터 무결성 |
| **TAA rule** | prototype operator-defined heuristic overlay |
| **pytest** | 142 passed / 5 skipped / 1 xfailed (Phase D 완료 시점) |
| **Decision Register** | 14건 (open 2 / pending_external 1 / pending_rerun 0 / deferred 2 / closed 9) — 이후 D-13/D-14 sign-off 로 closed 10 / open 0 / deferred 3 |
| **Permanent limitation** | DRM 3 xlsx 해제 불가 → Excel 1:1 parity 영구 waived |

### 2. Closed decisions 요약 (10건)

- **D-01** Hard constraint = long-only + sum-to-100% + 데이터 무결성. `final_asset_bounds`, `taa_bounds`, `weight_bounds`, `per_asset_max_tilt 0.03` 모두 **reference / telemetry only**.
- **D-02** Projection drift policy. relaxed=telemetry_only / review=warning / production=review_required. asset 3% / bucket 5%. scope=projection drift only.
- **D-03** Hybrid lookback. return/vol = asset_specific. corr = common intersection. min_obs=12. short_history_warning_ratio=0.8.
- **D-04** ust30 = BRFUT004 direct mapping. proxy 추가 금지.
- **D-05** MVO objective = max_sharpe + dispatch table 4종. Excel `$L$26` 직접 확인 영구 waived (D-08).
- **D-07** HY = fixed_income bucket + risk_asset + credit.
- **D-08** **closed_with_permanent_limitation**. DRM 3 xlsx 영구 해제 불가. GlidePath 운영자 직접 제공 → glidepath.yaml. SAA/TAA/Final parity 영구 waived.
- **D-09** regimeAnalysis_rt 파일 자체가 canonical definition. 별도 자료 영구 부재. xfail 1건 영구 유지.
- **D-10** 자산군 0% 허용. negative weight 만 금지.
- **D-13** quant_grade_policy 현행 유지. ETF=hard_filter / Fund=score_penalty. 추가 제약 없음.

### 4. Deferred / Open / Pending (4건 → 5건)

| # | 항목 | status |
|---|---|---|
| D-06 | ERR 정의 | pending_external |
| D-11 | dm_ex_us_equity lower bound | deferred |
| D-12 | us_value_equity cap | deferred |
| D-14 | manager concentration | deferred (정정 후 — soft warning 안 채택) |

### 5. Permanent Limitations (7건)
1. DRM 3 xlsx 영구 해제 불가
2. SAA / TAA / Final weights Excel 1:1 parity 영구 waived
3. MVO objective Excel `$L$26` 직접 확인 영구 waived
4. regimeAnalysis_rt definition 영구 부재
5. `test_golden_regime_returns_match_expected` xfail 영구
6. `glidepath.yaml` reference metadata only
7. TAA tilt = prototype operator-defined heuristic

### 6. Current Engine Mode
| 항목 | 값 |
|---|---|
| `operating_mode` | `relaxed_diagnostic` |
| relaxed output | diagnostic baseline (NOT production) |
| equity 100% / fixed_income 0% | monitoring flag (NOT fail) |
| TAA tilt | prototype heuristic. asset_tilts only. bucket_tilts metadata only. |

### 8. Phase E roadmap
| candidate | 영역 | 우선순위 |
|---|---|:---:|
| E-1 | Production mode 전환 설계 | 높음 |
| E-2 | relaxed governance / sign-off flow | 높음 |
| E-3 | Asset band 재도입 | 중 |
| E-4 | Manager concentration / quant grade policy | 중 |
| E-5 | Product cap / fallback drift policy 정식 등록 | 중 |
| E-6 | TAA confidence scaling | 낮음 (future study) |
| E-7 | TAA optimizer | 낮음 (future study) |
| E-8 | Multi-vintage glidepath integration | 낮음 |

(주: 실제 Phase E 진행 = E-2 → E-1 → E-4 → E-6(MVP) → E-6.1 → E-6.2 → E-7(explainability) → E-8(regime clock) → E-9(SAA frontier) → E-10(TAA tilt) → E-11A/B(product selection) → E-12(packet))

---

## 16. investment_decision_register.md

**원본 경로**: `tdf_2060/docs/investment_decision_register.md`

# Investment Decision Register — TDF 2060

작성일: 2026-05-08. Phase D 진입과 함께 신설.

### 1. 총괄 (총 14건, blocker 0)

| # | 항목 | 상태 | 비고 |
|---|---|---|---|
| D-01 | Hard constraint set definition | closed | long-only + sum-to-100% + 데이터 무결성. final_asset_bounds·bucket range·per-asset band reference/telemetry only |
| D-02 | `max_abs_projection_drift` 임계 | closed | relaxed=telemetry_only / review=warning / production=review_required, asset 3% / bucket 5% |
| D-03 | lookback 정책 | closed | Option C: Hybrid (return/vol asset_specific, corr common). min_obs=12 |
| D-04 | `us_treasury_30y` BRFUT004 mapping | closed | BRFUT004 direct mapping, 추가 proxy 금지 |
| D-05 | MVO objective 식 | closed | max_sharpe 확정, dispatch 4종 |
| D-06 | ERR 정의 | pending_external | Excel 원본 (DRM 영구 부재 — 운영자 별도 결정) |
| D-07 | HY 처리 | closed | risk_asset + credit |
| D-08 | Excel DRM 3건 | closed_with_permanent_limitation | DRM 해제 영구 불가. SAA/TAA/Final 1:1 parity 영구 보류 |
| D-09 | regimeAnalysis_rt 정의 | closed | 파일 자체가 canonical definition. 별도 자료 영구 부재 |
| D-10 | 자산군 0% 허용 | closed | 모든 자산군 0% 허용. negative 만 금지 |
| D-11 | dm_ex_us_equity lower bound | deferred | 자산군별 band 도입 시 재논의 |
| D-12 | us_value_equity cap | deferred | 동 |
| D-13 | quant_grade_policy mode | closed | 현행 유지 (ETF=hard_filter, Fund=score_penalty) |
| D-14 | 운용사 concentration cap | deferred | cap / soft warning 모두 미도입. monitoring only |

**상태 분포**: open 0 / pending_external 1 / pending_rerun 0 / deferred 3 / closed 10. **합계 14**.

**Phase D register blocker = 0건** (8 → 4 → 3 → 2 → **0**). 단 production-ready 가 아닌 register blocker 만 해소된 상태.

### 변경 이력 (요약)
- 2026-05-08: 신설. 14개 항목 초안. D-05 / D-07 closed 기록.
- 2026-05-08: D-04 closed (BRFUT004 direct mapping).
- 2026-05-08: Phase D relaxed constraints 적용 (D-01 closed, D-10 closed, D-11/D-12 deferred).
- 2026-05-08: D-02 Option A 적용 + drift_source 분류 보강.
- 2026-05-08: D-02 closed by 운용역 sign-off.
- 2026-05-08: D-03 closed by 운용역 sign-off.
- 2026-05-08: D-08 closed_with_permanent_limitation + D-09 closed. **register blocker = 0**.
- 2026-05-08: D-13 closed + D-14 deferred (정정 sign-off — soft warning option B 채택 안 함).

---

## 17. current_state_freeze.md

**원본 경로**: `tdf_2060/docs/current_state_freeze.md`

# Current State Freeze — TDF 2060 Engine

스냅샷 일자: 2026-05-08 (Phase D 진입 시점).
(주: 현재 최신 상태는 Phase E-12 완료 — 240 passed. 본 문서는 Phase D 진입 시점 freeze record)

### 2. pytest 결과 (Phase D 진입 freeze 기준치)
```
124 passed, 5 skipped, 1 xfailed in 7.21s
```
- SKIP 5건: Excel DRM 보호 또는 외부 자료 의존
- xfail 1건: `regimeAnalysis_rt` 정의 미명시

(주: Phase E-12 완료 시점 = 240 passed, 5 skipped, 1 xfailed)

### 5. 실 DB 산출 품질 상태 (ETF/Fund 동일, Phase D 진입 시점)
```
constraints_passed        : True
quality_status            : warning
asset_weight_sum          : 1.000000
product_weight_sum        : 1.000000
equity bucket             : 82.32%             (75~85 안)
fixed_income bucket       : 17.68%             (15~25 안)
fallback_used             : True
projection_used           : True
max_abs_projection_drift  : 3.00%
proxy_used                : False
```

### 6. Stale instruction 처리 원칙 (영구 기록)
1. **정본 = 본 디렉토리의 문서 + 코드 + 테스트 결과의 일치 상태**
2. 정본보다 과거 단계의 외부 지시(이전 Phase 진입 지시 등)는 **stale로 판정**
3. stale instruction 발견 시: 사용자에게 충돌 사실 명시 → 정본과 외부 지시의 차이를 항목별 정리 → 사용자가 폐기/적용 여부를 명시할 때까지 코드/config/테스트 무변경
4. Auto Mode가 켜져 있어도 destructive(=완료된 작업 덮어쓰기) 작업은 **사용자 명시 승인 필수**
5. 충돌 해소 후 결정은 본 문서 또는 `investment_decision_register.md` 에 기록

### 8. Sanity check (재진입 시)
```bash
cd C:/Users/user/Downloads/python/Advisory/tdf_2060
/c/Users/user/Downloads/python/.venv/Scripts/python.exe -m pytest tests/ -q
# 기대 (Phase D 진입): 124 passed, 5 skipped, 1 xfailed
# 기대 (Phase E-12 완료, 2026-05-11): 240 passed, 5 skipped, 1 xfailed
```

---

## 18. phase_e_relaxed_governance.md

**원본 경로**: `tdf_2060/docs/phase_e_relaxed_governance.md`

# Phase E-2 — Relaxed Diagnostic Governance

작성일: 2026-05-08. **E-2 (relaxed governance / sign-off flow)** — relaxed_diagnostic mode 산출물의 검토 / 승인 / 보류 / 재실행 절차를 영구 record.

### 1. Purpose

| 측면 | 내용 |
|---|---|
| **relaxed_diagnostic output 의 위상** | production portfolio **아님**. diagnostic baseline only. |
| **목적** | optimizer / TAA / selection / fallback 단계의 쏠림 / 한계 / 정책 영향을 **진단**. |
| **금지 사항** | (a) 자동 production 적용. (b) 고객 제안서 / 자료에 직접 사용. (c) 운용역 sign-off 없는 재배포. |

### 2. Scope (governance 필요 대상)
- `out/db_etf_relaxed/portfolio_etf_*.{csv,json,md}`
- `out/db_fund_relaxed/portfolio_fund_*.{csv,json,md}`
- `out/db_review_relaxed/comparison_etf_vs_fund_*.md`

### 3. Review Roles
- **Engine owner**: 엔진 코드 / config 유지. relaxed run 실행.
- **Portfolio manager (운용역)**: 정책 정합성 검토. concentration / sanity range / 정책 sign-off.
- **Data operator**: DB 데이터 무결성. as_of_date 결정.
- **Reviewer** (선택): 산출 logic / governance 절차 준수 여부 외부 검토.

### 4. Review Checklist

**4.1 Hard constraint 통과 (모두 ✓ 필수)**:
- H-1: long-only (asset/product 모든 weight ≥ 0)
- H-2: sum-to-100%
- H-3: DB source 정상 (datasets_loaded = 9)
- H-4: BRFUT004 direct mapping 정상
- H-5: NaN / invalid return data 없음
- H-6: optimizer / projection convergence

**4.2 Drift / Quality 분석 (telemetry 검토)**
**4.3 Sanity / Concentration monitoring**
**4.4 정책 정합성**

### 5. Decision Outcome (4종)

| outcome | 의미 |
|---|---|
| **approve_for_diagnostic_record** | diagnostic record 로 승인. production 자료 아님. |
| **request_rerun** | 데이터/시점/환경 변경 재실행 필요. |
| **request_policy_change** | 정책 자체 변경 필요. |
| **reject_as_invalid** | hard constraint / 데이터 무결성 위반. |

### 6. Escalation Rules
- 즉시 reject: negative weight / total weight ≠ 1.0 / DB missing / BRFUT004 failure / NaN / optimizer failure / projection failure
- review_required: equity bucket 이탈 / 단일 자산군 > 80% / 단일 product > 30% / 단일 manager > cap

### 7. Sign-off Template (인용 가능)
```
RELAXED DIAGNOSTIC SIGN-OFF — APPROVE FOR DIAGNOSTIC RECORD
산출물: out/db_*_relaxed/...
as_of_date: <YYYY-MM-DD>
operating_mode: relaxed_diagnostic

본 relaxed_diagnostic 산출은 production portfolio 가 아니라 진단용 결과로 확인했습니다.
production 적용 또는 고객 자료 사용 금지를 동의합니다.

확인 사항 (모두 인지 완료):
  ✓ Phase D completed register-blocker resolution only (production-ready 아님)
  ✓ engine 은 relaxed_diagnostic mode 로 산출
  ✓ TAA rule = prototype operator-defined heuristic overlay
  ✓ D-08 limitation: DRM 3 xlsx 영구 해제 불가 → Excel 1:1 parity 영구 waived
  ✓ regimeAnalysis_rt = 파일 자체가 canonical definition
```

---

## 19. phase_e_production_transition_design.md

**원본 경로**: `tdf_2060/docs/phase_e_production_transition_design.md`

# Phase E-1 — Production Mode Transition Design

작성일: 2026-05-08. **설계 문서만**. 코드/config/test/out 변경 없음.

### 1. Purpose

| 측면 | 내용 |
|---|---|
| **relaxed_diagnostic 위상** | 진단용 baseline. production portfolio 아님. |
| **production mode 위상** | 실제 운용 검토 가능한 portfolio 산출 모드. |
| **전환 조건** | E-2 governance sign-off 누적 + D-13/D-14 정책 + D-15/D-16/D-17 candidate 정식 등록 + 운용역 별도 승인. |

### 2. Current vs Production 비교 (요약)

| 측면 | relaxed_diagnostic (현재) | production (E-1 후보) |
|---|---|---|
| `operating_mode` | `relaxed_diagnostic` | `production` |
| drift enforcement | `telemetry_only` | `review_required` |
| asset bounds | 모두 [0, 1] | 운용역 결정 필요 |
| bucket range | 모두 [0, 1] | 운용역 결정 필요 |
| review banner | "RELAXED DIAGNOSTIC RUN" | "PRODUCTION REVIEW RUN" |

### 3. Production mode 전환 조건 (10건)
- ✓ long-only / sum-to-100% / data integrity / BRFUT004 (이미 통과)
- ⏳ D-08 limitation 인지 / D-09 canonical file 인지 / relaxed governance sign-off 기록 / D-13/D-14 결정 / D-15-17 결정 / production review packet 승인 절차 정의

### 4. Config 전환 설계 (변경 후보만)
- `tdf_2060.yaml::operating_mode`: `relaxed_diagnostic` → `production`
- drift_thresholds.modes.production 운영값 확정
- `weight_bounds`, `final_asset_bounds`, `taa_bounds` 운영역 결정

### 9. Production Dry-run 설계
```
Step 1. yaml 변경 (운용역 승인 후 별도 turn)
Step 2. dry-run 산출 (out/db_*_production_dryrun/)
Step 3. dry-run 검증 (hard constraint / drift enforcement / banner / pytest)
Step 4. dry-run 결과 governance (production §5 sign-off)
Step 5. 정식 전환 (별도, 운영 시스템 영역)
```

### 11. 한 줄 요약
> **E-1 = production 전환 설계. 자동 전환 금지. 전환 전 E-4 + E-5 정리 우선.
> 실제 전환은 yaml 변경 위주 (코드 변경 최소). dry-run 1회 → governance approve → 운영 시스템 인계.**

---

## 20. phase_e_d13_d14_policy_brief.md

**원본 경로**: `tdf_2060/docs/phase_e_d13_d14_policy_brief.md`

# Phase E-4 — D-13 / D-14 Policy Decision Brief

작성일: 2026-05-08. **운용역 정정 sign-off 완료**.

### Sign-off (2026-05-08, 운용역 정정 sign-off):
- **D-13 closed** — 현행 유지 (ETF=hard_filter / Fund=score_penalty). 추가 제약 도입 안 함.
- **D-14 deferred** — manager cap / soft warning threshold 모두 미도입. monitoring telemetry only.
- **정정**: 본 brief 의 Option B (soft warning ETF 50% / Fund 40%) 는 **채택하지 않음**. 일관 정책 = "현 단계는 제약 추가 안 함. relaxed 결과 관찰만 한다."

### 1.1 Concentration 의 1차 원인
- (a) **자산군 쏠림** (relaxed mode 의 자산 cap 부재) — **✓ 1차 원인**. MVO 가 sharpe 최고 자산 (us_growth) 에 70.6% 쏠림.
- (b) 상품 선정 정책 (quant_grade_policy) — △ 부분 영향.
- (c) 운용사 cap 부재 — ✗ 1차 원인 아님. ETF cap 60% / Fund 50% 모두 미발동.

### Sign-off note (2026-05-08, 운용역 정정 sign-off)
```
D-13 (quant_grade_policy):
  status: open → closed
  decision: 현행 유지 (ETF=hard_filter / Fund=score_penalty)
  근거: relaxed concentration 의 1차 원인 = 자산군 쏠림 (D-11/D-12 deferred 영역). D-13 영향 미발견.
  config / 코드 / tests / out 변경: 없음

D-14 (manager concentration cap):
  status: open → deferred
  decision: 제약 도입 안 함. monitoring telemetry only.
  근거: 현재 concentration 1차 원인 = relaxed_diagnostic mode 의 자산군 쏠림 + product cap binding 부산물.
        manager cap 부재가 원인이 아님. cap / soft warning 만 먼저 도입 시 진짜 risk 가림 + 상품 선정 왜곡.
  config / 코드 / tests / out 변경: 없음

정정 사유:
  - 직전 turn 의 Option B 권장 (soft warning ETF 50% / Fund 40%) 은 "현 단계 제약 추가 안 함" 정책과 부합하지 않아 채택하지 않음.

분포 변화:
  open 2 → 0 / deferred 2 → 3 / closed 9 → 10. total 14 유지.
```

---

# D. Phase E-6 ~ E-12 시각화 설계

> 본 섹션은 phase_e_output_visualization_redesign.md (E-6.1) / phase_e7_explainability_data_contract.md (E-7) / phase_e12_integrated_review_packet.md (E-12) 의 **핵심 부분 발췌**한다. 전체 본문은 원본 경로에서 직접 확인.

---

## 21. phase_e_output_visualization_redesign.md

**원본 경로**: `tdf_2060/docs/phase_e_output_visualization_redesign.md`

# Phase E-6.1 — Portfolio Construction Visualization Redesign

작성일: 2026-05-08. **E-6 MVP (9 PNG) 재분류 + 신규 main visualization 구조 설계**.

### 0. TL;DR

| 항목 | 결과 |
|---|---|
| **기존 9 PNG 위상** | **partial / downstream-only**. main review 부적격, **appendix 한정**. |
| **신규 main 5 블록** | A. Regime / B. MVO Input & SAA / C. TAA Overlay / D. Projection & Drift / E. Product Final |
| **데이터 가용성** | available 9 / available_but_inferred 2 / **missing telemetry 5** / not_needed_for_mvp 2 |
| **Telemetry gap** | μ / σ / ρ / Σ / regime history 5건 |
| **새 MVP 제안** | A.1 quadrant + A.2 regime card + C.1 tilt table + C/D bridge + D drift attribution |

### 2. 신규 main visualization 구조

운용역 review 의 흐름 = **Regime → MVO → SAA → TAA → Projection → Product → Final**.

블록 5종 (A ~ E). 각 블록은 1 ~ 3 차트.

### 4. Telemetry Gap 정리 (5건)

| ID | gap | 권장 diagnostics key | 영향 |
|:---:|---|---|---|
| T-1 | μ vector | `diagnostics.saa_diagnostics.cma.expected_returns` | B.1 |
| T-2 | σ vector | `diagnostics.saa_diagnostics.cma.volatilities` | B.1 |
| T-3 | ρ matrix | `diagnostics.saa_diagnostics.cma.correlation_matrix` | B.2 |
| T-4 | Σ matrix | `diagnostics.saa_diagnostics.cma.covariance_matrix` | B.1 |
| T-5 | regime history | `diagnostics.regime.history` | A.3 |

### 8. 한 줄 요약
> **E-6 MVP (9 PNG) 는 downstream-only / appendix 한정으로 재분류. main visualization 은
> Regime → MVO → SAA → TAA → Projection → Product 흐름의 5 블록으로 재설계.**

---

## 22. phase_e7_explainability_data_contract.md

**원본 경로**: `tdf_2060/docs/phase_e7_explainability_data_contract.md`

# Phase E-7 — Explainability Data Contract

작성일: 2026-05-11. **포트폴리오 의사결정 과정 (Regime → SAA → TAA → Product Selection) 을 설명 가능하게 만드는 데이터 계약.**

### 0. TL;DR

| 항목 | 결정 |
|---|---|
| **Scope** | 데이터 계약 + dump 구조. **차트 미생성**. |
| **출력** | `out/db_review_relaxed_e62/explainability/<as_of>/explainability_{etf,fund}_<as_of>.json` |
| **모듈** | `tdf_engine/reporting/explainability.py` |
| **CLI** | `tdf_engine/tools/build_explainability.py` |
| **변경** | allocation/optimizer/TAA/selection/config 무변경. read-only diagnostics dump only. |
| **SAA inferred** | 절대 금지 — `saa_diagnostics.saa_weights` (E-6.2 T-6) 직접 telemetry 만 사용. |

### 1. Top-level structure
```
portfolio_explainability
├── meta
├── regime_explainability
├── saa_explainability
├── taa_explainability
├── product_selection_explainability
└── report_ready_summary
```

### 2~7. 각 블록 schema

- **meta**: schema_version, generated_at, portfolio_type, portfolio_as_of_date, source_type, operating_mode, source_files, upstream_run
- **regime_explainability**: current / history / transition_summary / asset_class_preference
- **saa_explainability**: cma_inputs (μ/σ/ρ/Σ) / optimization (objective/constraints/universe/selected_weights/selected_point/solver) / efficient_frontier (deferred to E-9) / risk_contribution (read-only 산출) / diagnostics
- **taa_explainability**: current_regime / regime_conditioned_assumptions (unavailable) / tilt_policy (rule_based) / tilt_decisions / taa_portfolio_summary (before/after) / diagnostics
- **product_selection_explainability**: universe / filtering / scoring / final_selection / diagnostics
- **report_ready_summary**: regime_summary / saa_summary / taa_summary / product_selection_summary / warnings / missing_data

### 8. Hard Requirements (E-7 영구)
```
✗ allocation 결과 변경 금지
✗ optimizer / TAA / projection / selection / config 로직 변경 금지
✗ taa_policy.yaml 수치 변경 금지 (read-only 만)
✗ portfolio_*.json 변경 금지 (read 만)
✗ 기존 production 산출물 overwrite 금지
✗ Decision Register count (14) 변경 금지
✗ SAA inferred (taa_target − asset_tilts) 사용 금지 — direct telemetry only
✓ 신규 산출 = explainability JSON + summary md 만
✓ read-only 추가 계산 (risk_contribution, return/vol/sharpe before/after tilt) 만 허용
```

### 10. 다음 phase 후보 (E-7 산출 활용)
- E-8: Regime Clock Visualization
- E-9: SAA MVO / Efficient Frontier
- E-10: TAA Regime Tilt Visualization
- E-11: Product Selection Explainability

---

## 23. phase_e12_integrated_review_packet.md

**원본 경로**: `tdf_2060/docs/phase_e12_integrated_review_packet.md`

# Phase E-12 — Integrated Review Packet (Design)

작성일: 2026-05-11. **E-8 + E-9 + E-10 + E-11B 4 standalone 산출물을 운용역 review packet 1건으로 묶는 packaging phase.**

### 0. TL;DR

| 항목 | 결정 |
|---|---|
| **Scope** | 4 phase 산출물을 1개 packet 으로 packaging. 새 차트/분석 X. |
| **Format** | **Primary: Markdown**, **Secondary: HTML** (simple CSS, no JS). PDF 는 후속 (E-15). |
| **출력 위치** | `out/db_review_relaxed_e62/review_packet/<as_of_run>/` |
| **자산 복사** | `assets/` 서브디렉토리에 모든 PNG 복사 |
| **MVP-X 위치** | 본 packet 의 main 섹션 진입 금지. `--include-appendix` 옵션으로만. |

### 1. Packet purpose (운용역이 답할 6 질문)
1. 현재 경기국면이 어디에 있는가? (E-8)
2. SAA 는 어떤 MVO 입력/제약으로 산출되었는가? (E-9)
3. TAA 는 어떤 rule 로 어떤 자산을 tilt 했는가? (E-10)
4. 최종 상품은 어떤 universe / filter / score / rank 로 선택되었는가? (E-11B)
5. 최종 자산/상품 비중은 무엇이고 quality 는 어떤가? (portfolio JSON)
6. 어떤 데이터/방법론 한계가 있는가? (각 phase 의 missing_data 통합)

### 4. Section order (8 + appendix)
```
0. Cover / Run Metadata
1. Executive Summary
2. Regime Assessment           ← E-8
3. SAA Construction            ← E-9
4. TAA Overlay                 ← E-10
5. Product Selection           ← E-11B
6. Final Portfolio Snapshot    ← portfolio_*.json + review_*.md
7. Diagnostics / Missing Data  ← 4 phase 통합
8. Appendix (opt-in, --include-appendix)
   - MVP-X prototype PNG
   - E-6 9 PNG legacy set
```

### 7. CLI design
```
python -m tdf_engine.tools.build_review_packet \
    --as-of-run 20260511 \
    --product-type etf | fund | both \
    --review-root out/db_review_relaxed_e62 \
    --portfolio-json out/db_etf_relaxed_e62_e11a/portfolio_etf_20260511.json \
    --portfolio-json-fund out/db_fund_relaxed_e62_e11a/portfolio_fund_20260511.json \
    --output-dir out/db_review_relaxed_e62/review_packet/20260511 \
    --format md | html | both \
    [--include-appendix]
```

### 8. Hard requirements (E-12 영구)
```
✗ 새 분석 차트 생성 금지
✗ E-8/E-9/E-10/E-11B chart 로직 변경 금지
✗ allocation / optimizer / TAA / selection / scoring / config 변경 금지
✗ 기존 production / e62 / e62_e11a output overwrite 금지
✗ MVP-X 를 main 섹션에 포함 금지 (--include-appendix 시에만)
✓ assets/ 에 PNG 복사만 허용 (원본 미변경)
✓ packet md/html 만 신규 생성
✓ silent missing artifact 금지 — explicit missing_data 기록
```

### 10. 다음 phase 후보
- E-13: MVP-X deprecation / replacement
- E-14: Final report design polish
- E-15: PDF export

### 11. 한 줄 요약
> **E-12 = 4 standalone 차트 (E-8/E-9/E-10/E-11B) 를 운용역 review packet 1개 (md+html) 로
> 묶는 packaging phase. 새 분석 차트 미생성, allocation/TAA/selection 미변경,
> assets/ PNG 복사만, 모든 missing_data 통합, MVP-X 는 opt-in appendix only.**

---

# E. 산출물 summary md (값 확인용)

---

## 24. review_packet_both_20260511.md

**원본 경로**: `out/db_review_relaxed_e62/review_packet/20260511/review_packet_both_20260511.md`

# Integrated Review Packet — TDF 2060 (ETF + Fund) 20260511

> schema: e12.1

> **RELAXED DIAGNOSTIC RUN — NOT a production portfolio.**
> - TAA is rule-based regime overlay — NOT regime-conditioned MVO and NOT optimized TAA.
> - Ticker mapping unavailable — product_id / product_name used as identifier.
> - Regime-conditioned assumptions unavailable (deferred to future phase).
> - Efficient frontier sampled by SLSQP grid scan (E-9), not analytical.

### 0. ETF vs Fund Snapshot

| metric | ETF | Fund |
|---|---|---|
| portfolio_as_of_date | 2026-03-31 | 2026-03-31 |
| source_mode | db | db |
| quality_status | warning | warning |
| current regime | R1 (Expansion / Acceleration) | R1 (Expansion / Acceleration) |
| SAA Sharpe | 0.7769 | 0.7769 |
| TAA Sharpe | 0.7879 | 0.7879 |

> 본 packet 의 ETF 섹션과 Fund 섹션은 각각 review_packet_etf_20260511.md (§25) 와 review_packet_fund_20260511.md (§26) 와 동일.

---

## 25. review_packet_etf_20260511.md

**원본 경로**: `out/db_review_relaxed_e62/review_packet/20260511/review_packet_etf_20260511.md`

# Integrated Review Packet — TDF 2060 ETF Portfolio

> schema: e12.1
> generated_at: 2026-05-11T07:17:07.673413+00:00  ·  operating_mode: **relaxed_diagnostic**

> **RELAXED DIAGNOSTIC RUN — NOT a production portfolio.**
> - TAA is rule-based regime overlay — NOT regime-conditioned MVO and NOT optimized TAA.
> - Ticker mapping unavailable — product_id / product_name used as identifier.
> - Regime-conditioned assumptions unavailable (deferred to future phase).
> - Efficient frontier sampled by SLSQP grid scan (E-9), not analytical.

### 0. Cover / Run Metadata

| 항목 | 값 |
|---|---|
| product_type | **ETF** |
| portfolio_as_of_date | 2026-03-31 |
| portfolio_as_of_run | 20260511 |
| source_mode | db |
| quality_status | warning |
| operating_mode | relaxed_diagnostic |

### 1. Executive Summary

**ETF** portfolio constructed under regime **R1 (Expansion / Acceleration)**. top SAA weights: us_growth_equity 71.60%, us_value_equity 28.40%, dm_ex_us_equity 0.00%. After rule-based regime tilt (SAA Sharpe 0.7769 → TAA Sharpe 0.7879, Δ=+0.0110), products were selected by quant_score / sharpe_1y / return_3y / aum_log factors. final top: us_growth_equity 70.60%, us_value_equity 27.40%, em_equity 1.00%.

| metric | value |
|---|---|
| current regime | R1 (Expansion / Acceleration) |
| SAA top weights | us_growth_equity 71.60%, us_value_equity 28.40%, dm_ex_us_equity 0.00% |
| TAA target top weights | us_growth_equity 71.60%, us_value_equity 28.40%, em_equity 2.00% |
| Final asset top | us_growth_equity 70.60%, us_value_equity 27.40%, em_equity 1.00% |
| Sharpe SAA → TAA | 0.7769 → 0.7879 (Δ=0.0110) |

**Caveats**:
- Relaxed diagnostic — NOT a production portfolio.
- TAA is rule-based regime overlay — NOT regime-conditioned MVO and NOT optimized TAA.
- Ticker mapping unavailable — product_id / product_name used as identifier.
- Regime-conditioned assumptions unavailable (deferred to future phase).
- Efficient frontier sampled by SLSQP grid scan (E-9), not analytical.

### 2. Regime Assessment
- region: **G7**, signal as_of: **2026-02-01**, portfolio as_of: **2026-03-31**
- current: R1 (Expansion / Acceleration), P=+0.7223, V=+0.0586
- coverage: **full** (window 24 obs, full 49 obs)

### 3. SAA Construction (max-Sharpe MVO, relaxed)
- selected SAA: E[R]=15.40%, σ=15.96%, Sharpe=0.7769
- max-Sharpe ref: Sharpe=0.7769; min-vol ref: σ=3.52%
- selected_matches_max_sharpe: **True**
- active constraints: long_only, weight_sum=1.0  ·  inactive (relaxed): weight_bounds, equity_sum, fixed_income_sum

### 4. TAA Overlay (rule-based regime tilt)
- SAA: E[R]=15.40%, σ=15.96%, Sharpe=0.7769
- TAA: E[R]=15.93%, σ=16.40%, Sharpe=0.7879
- Δ: E[R]=+0.53pp, σ=+0.45pp, Sharpe=+0.0110
- overweight: em_equity +2.00pp, kr_equity +2.00pp, us_high_yield +1.00pp
- underweight: kr_treasury_10y -2.00pp, us_treasury_30y -3.00pp

> **Limitation**: TAA is rule-based regime overlay — NOT regime-conditioned MVO and NOT optimized TAA.

### 5. Product Selection
- universe funnel: raw=932 → passed=736 → classified=572 → eligible=395 → selected=17
- zero-eligible assets: kr_aggregate_bond, kr_treasury_10y, us_treasury_30y

**Selected products (top 10 by weight):**

| asset | rank | score | weight | product_id | product_name | manager |
|---|---:|---:|---:|---|---|---|
| us_growth_equity | 1 | 83.39 | 20.00% | 426030 | 타임폴리오TIME미국나스닥100액티브상장지수(주식) | 타임폴리오자산운용 |
| us_growth_equity | 2 | 79.12 | 20.00% | 411420 | 삼성KODEX미국나스닥AI테크액티브상장지수[주식] | 삼성운용 |
| us_growth_equity | 3 | 70.03 | 20.00% | 381180 | 미래에셋TIGER미국필라델피아반도체나스닥상장지수(주식) | 미래에셋운용 |
| us_value_equity | 1 | 46.40 | 20.00% | 402970 | 한국투자ACE미국배당다우존스상장지수(주식) | 한국투자신탁운용 |
| us_value_equity | 2 | 46.18 | 4.66% | 446720 | 신한SOL미국배당다우존스상장지수[주식] | 신한자산운용 |
| us_value_equity | 3 | 37.32 | 4.66% | 429000 | 미래에셋TIGER미국S&P500배당귀족상장지수(주식) | 미래에셋운용 |
| em_equity | 1 | 96.21 | 1.76% | 446690 | 삼성KODEX아시아AI반도체exChina액티브상장지수[주식] | 삼성운용 |
| kr_equity | 1 | 155.64 | 1.76% | 434730 | NH-AmundiHANARO원자력iSelect상장지수(주식) | NH-Amundi운용 |
| em_equity | 2 | 53.67 | 1.06% | 105010 | 미래에셋TIGER라틴상장지수(주식) | 미래에셋운용 |
| em_equity | 3 | 52.66 | 1.06% | 277540 | 한국투자ACE아시아TOP50상장지수(주식) | 한국투자신탁운용 |

> **Identifier note**: ticker mapping unavailable — product_id / product_name used as identifier.

### 6. Final Portfolio Snapshot

**Final asset weights:**

| asset | weight |
|---|---:|
| us_growth_equity | 70.60% |
| us_value_equity | 27.40% |
| em_equity | 1.00% |
| kr_equity | 1.00% |
| us_high_yield | 0.00% |
| dm_ex_us_equity | 0.00% |
| kr_aggregate_bond | 0.00% |
| kr_treasury_10y | 0.00% |
| us_treasury_30y | 0.00% |

- asset_weight_sum: 1.0  ·  constraints_passed: **True**  ·  quality_status: **warning**
- max_abs_projection_drift: —  ·  max_abs_asset_weight_drift: 10.60%  ·  fallback_used: True

### 7. Diagnostics / Missing Data

| field | impact | next | source phase |
|---|---|---|---|
| `saa.efficient_frontier` | selected SAA point 의 frontier 위치 시각화 불가 | E-9 phase | e7_explainability |
| `regime.history (24m)` | 장기 regime timeline 시각화 불가 | regime backfill sidecar | e7_explainability |
| `product.scoring.scored_products` | factor 별 score 분해 불가 | E-11 phase + selection/tool.py 에서 score 보존 | e7_explainability |
| `taa.regime_conditioned_assumptions` | regime-aware MVO 비교 불가 | future phase (regime_mvo, future study only) | e7_explainability |
| `product.selected_products.ticker` | Bloomberg/Reuters ticker 표기 불가 | 외부 ticker mapping table 도입 또는 DBProductRepository 확장 | e7_explainability |
| `regime_conditioned_assumptions` | regime-aware MVO 비교 불가 | future phase — regime_mvo (currently future_study only) | e10_taa_tilt |
| `tilt_rules_applied[].confidence` | tilt 의 통계적 유의성 표시 불가 | future phase — confidence scaling | e10_taa_tilt |
| `final_selection.selected_products[].ticker` | Bloomberg/Reuters ticker 표기 불가 | 외부 ticker mapping table 도입 또는 DBProductRepository.product_metadata 확장 | e11b_product_selection_viz |
| `scoring.score_factors[].cost_penalty` | 비용 패널티 미사용 (weight=0.0) | future phase — fee/expense ratio 데이터 도입 | e11b_product_selection_viz |

---

## 26. review_packet_fund_20260511.md

**원본 경로**: `out/db_review_relaxed_e62/review_packet/20260511/review_packet_fund_20260511.md`

# Integrated Review Packet — TDF 2060 FUND Portfolio

(주: ETF 와 동일 구조. 차이점만 발췌)

### 1. Executive Summary
**FUND** portfolio constructed under regime **R1 (Expansion / Acceleration)**. (SAA / TAA / regime / Caveats 모두 ETF 와 동일 — region=G7 공유)

### 5. Product Selection (FUND 만의 차이)
- universe funnel: raw=781 → passed=414 → classified=262 → eligible=208 → selected=17

**Selected products (top 10 by weight):**

| asset | rank | score | weight | product_id | product_name | manager |
|---|---:|---:|---:|---|---|---|
| us_growth_equity | 1 | 45.15 | 30.00% | 76305 | KB미국대표성장주자(주식)(UH)C-퇴직 | KB운용 |
| us_value_equity | 1 | 26.66 | 21.92% | 70467 | 한국투자미국배당귀족자UH(주식)(C-R) | 한국투자신탁운용 |
| us_growth_equity | 2 | 29.70 | 20.30% | 74176 | 삼성미국그로스자UH[주식-재간접]_Cp(퇴직연금) | 삼성운용 |
| us_growth_equity | 3 | 29.68 | 20.30% | 73125 | AB미국그로스UH(주식-재간접)종류C-P2 | AB자산운용 |
| us_value_equity | 2 | 18.00 | 5.48% | 70455 | 한국투자미국배당귀족자H(주식)(C-R) | 한국투자신탁운용 |
| em_equity | 1 | 61.19 | 0.80% | 2074 | NH-Amundi성장중소형주[주식]ClassC-P2(퇴직연금) | NH-Amundi운용 |
| kr_equity | 1 | 90.31 | 0.80% | 43306 | 한국밸류10년투자파이오니아(주식)(C-Re) | 한국투자밸류운용 |
| em_equity | 2 | 55.46 | 0.10% | 71972 | 마이다스아시아리더스성장주자(H)(주식)C-P2 | 마이다스운용 |
| em_equity | 3 | 54.96 | 0.10% | 71976 | 마이다스아시아리더스성장주자(UH)(주식)C-P2 | 마이다스운용 |
| kr_equity | 2 | 78.05 | 0.10% | 43040 | NH-Amundi필승코리아[주식]ClassC-P2(퇴직연금) | NH-Amundi운용 |

### 6. Final Portfolio Snapshot (Fund)
- max_abs_asset_weight_drift: 0.00% (Fund: cap 30% binding 으로 asset drift 미발생)
- 기타 asset_weights / constraints / quality 는 ETF 와 동일

### 7. Diagnostics / Missing Data — ETF 와 동일 9 항목

---

## 27. regime_history_summary_20260511.md

**원본 경로**: `out/db_review_relaxed_e62/regime_history/20260511/regime_history_summary_20260511.md`

# Regime Clock Visualization Summary (20260511)

> schema_version: e8.1
> Read-only diagnostic — RegimeAnalysisTool re-invoked on the same regime_src.

### ETF

- region: **G7**, signal as_of: **2026-02-01**
- coverage: **full** (24 obs in window, 49 obs full history, target=24m)
- window: 2024-03-01 → 2026-02-01
- current: R1 (Expansion / Acceleration), P=+0.7223 / V=+0.0586
- current_point_match (sidecar last vs portfolio): True

### Fund

(ETF 와 동일 — region=G7 공유)

---

## 28. saa_frontier_summary_20260511.md

**원본 경로**: `out/db_review_relaxed_e62/saa_frontier/20260511/saa_frontier_summary_20260511.md`

# SAA MVO / Efficient Frontier Summary (20260511)

> schema_version: e9.1
> Read-only diagnostic. Frontier 는 별도 SLSQP grid scan — production allocation 결과 미변경.

### ETF

- portfolio as_of: **2026-03-31**, source: **db**
- selected SAA: E[R]=15.40%, σ=15.96%, Sharpe=0.7769
- min-vol: E[R]=1.52%, σ=3.52%, Sharpe=-0.4205
- max-Sharpe: E[R]=15.40%, σ=15.96%, Sharpe=0.7769
- selected_matches_max_sharpe: **True**
- frontier point count: 31, failed grid points: 0

### Fund
- 동일 결과 (region=G7 공유)

> **Constraints note**: Relaxed diagnostic — long-only + sum=1 만 적용. asset caps / bucket bands 미적용 (Phase D relaxed).

---

## 29. taa_tilt_summary_20260511.md

**원본 경로**: `out/db_review_relaxed_e62/taa_tilt/20260511/taa_tilt_summary_20260511.md`

# TAA Regime Tilt Summary (20260511)

> schema_version: e10.1
> Current TAA is generated by a rule-based regime policy. Regime-conditioned expected returns/volatilities are not yet available. This is NOT regime-conditioned MVO and NOT optimized TAA.

### ETF

- regime: **R1 Expansion / Acceleration**, P=+0.7223, V=+0.0586
- portfolio as_of=2026-03-31, regime signal as_of=2026-02-01
- SAA: E[R]=15.40%, σ=15.96%, Sharpe=0.7769
- TAA: E[R]=15.93%, σ=16.40%, Sharpe=0.7879
- Δ: E[R]=+0.53pp, σ=+0.45pp, Sharpe=+0.0110
- Applied tilts:
  - em_equity: SAA 0.00% → TAA 2.00% (tilt +2.00pp, overweight)
  - kr_equity: SAA 0.00% → TAA 2.00% (tilt +2.00pp, overweight)
  - kr_treasury_10y: SAA 0.00% → TAA -2.00% (tilt -2.00pp, underweight)
  - us_high_yield: SAA 0.00% → TAA 1.00% (tilt +1.00pp, overweight)
  - us_treasury_30y: SAA 0.00% → TAA -3.00% (tilt -3.00pp, underweight)

### Fund
- 동일 결과 (region=G7 공유)

---

**Limitation**: Current TAA is generated by a rule-based regime policy. Regime-conditioned expected returns/volatilities are not yet available. This is NOT regime-conditioned MVO and NOT optimized TAA.

---

## 30. product_selection_visualization_summary_20260511.md

**원본 경로**: `out/db_review_relaxed_e62/product_selection_visualization/20260511/product_selection_visualization_summary_20260511.md`

# Product Selection Visualization Summary (20260511)

> schema_version: e11b.1
> Read-only diagnostic. Selection / scoring logic not re-executed.

### ETF

- portfolio as_of: **2026-03-31**, source: **db**, score_method: **hard_filter**
- funnel: raw=932 → passed_filter=736 → classified=572 → eligible=395 → selected=17
- assets with zero eligible: kr_aggregate_bond, kr_treasury_10y, us_treasury_30y

#### filter exclusion reasons
- `grade_below_min(grade=D, min=C)`: 64

#### selected products (top by weight)

| asset_key | rank | score | weight | product_id | product_name | manager |
|---|---:|---:|---:|---|---|---|
| us_growth_equity | 1 | 83.3879 | 20.00% | 426030 | 타임폴리오TIME미국나스닥100액티브상장지수(주식) | 타임폴리오자산운용 |
| us_growth_equity | 2 | 79.1210 | 20.00% | 411420 | 삼성KODEX미국나스닥AI테크액티브상장지수[주식] | 삼성운용 |
| us_growth_equity | 3 | 70.0295 | 20.00% | 381180 | 미래에셋TIGER미국필라델피아반도체나스닥상장지수(주식) | 미래에셋운용 |
| us_value_equity | 1 | 46.3980 | 20.00% | 402970 | 한국투자ACE미국배당다우존스상장지수(주식) | 한국투자신탁운용 |
| us_value_equity | 2 | 46.1828 | 4.66% | 446720 | 신한SOL미국배당다우존스상장지수[주식] | 신한자산운용 |
| us_value_equity | 3 | 37.3153 | 4.66% | 429000 | 미래에셋TIGER미국S&P500배당귀족상장지수(주식) | 미래에셋운용 |
| em_equity | 1 | 96.2103 | 1.76% | 446690 | 삼성KODEX아시아AI반도체exChina액티브상장지수[주식] | 삼성운용 |
| kr_equity | 1 | 155.6356 | 1.76% | 434730 | NH-AmundiHANARO원자력iSelect상장지수(주식) | NH-Amundi운용 |
| em_equity | 2 | 53.6687 | 1.06% | 105010 | 미래에셋TIGER라틴상장지수(주식) | 미래에셋운용 |
| em_equity | 3 | 52.6580 | 1.06% | 277540 | 한국투자ACE아시아TOP50상장지수(주식) | 한국투자신탁운용 |
| kr_equity | 2 | 152.0764 | 1.06% | 449450 | 한화PLUSK방산상장지수(주식) | 한화운용 |
| kr_equity | 3 | 148.6765 | 1.06% | 433500 | 한국투자ACE원자력TOP10상장지수(주식) | 한국투자신탁운용 |
| dm_ex_us_equity | 1 | 49.1052 | 0.96% | 238720 | 한국투자ACE일본Nikkei225상장지수(주식-파생)(H) | 한국투자신탁운용 |
| dm_ex_us_equity | 2 | 47.4795 | 0.96% | 101280 | 삼성KODEX일본TOPIX100상장지수[주식] | 삼성운용 |
| dm_ex_us_equity | 3 | 46.5682 | 0.96% | 251350 | 삼성KODEXMSCI선진국상장지수[주식] | 삼성운용 |
| us_high_yield | 1 | 27.4297 | 0.00% | 468380 | 삼성KODEXiShares미국하이일드액티브상장지수[채권-재간접] | 삼성운용 |
| us_high_yield | 2 | 17.6621 | 0.00% | 455660 | 한국투자ACE미국하이일드액티브상장지수[채권-재간접](H) | 한국투자신탁운용 |

### Fund

- portfolio as_of: **2026-03-31**, source: **db**, score_method: **score_penalty**
- funnel: raw=781 → passed_filter=414 → classified=262 → eligible=208 → selected=17
- assets with zero eligible: kr_aggregate_bond, kr_treasury_10y, us_treasury_30y

#### filter exclusion reasons
- (Fund: score_penalty 모드라 hard exclusion 없음 — "no exclusions recorded")

#### selected products (top by weight)

| asset_key | rank | score | weight | product_id | product_name | manager |
|---|---:|---:|---:|---|---|---|
| us_growth_equity | 1 | 45.1470 | 30.00% | 76305 | KB미국대표성장주자(주식)(UH)C-퇴직 | KB운용 |
| us_value_equity | 1 | 26.6587 | 21.92% | 70467 | 한국투자미국배당귀족자UH(주식)(C-R) | 한국투자신탁운용 |
| us_growth_equity | 2 | 29.7045 | 20.30% | 74176 | 삼성미국그로스자UH[주식-재간접]_Cp(퇴직연금) | 삼성운용 |
| us_growth_equity | 3 | 29.6766 | 20.30% | 73125 | AB미국그로스UH(주식-재간접)종류C-P2 | AB자산운용 |
| us_value_equity | 2 | 17.9962 | 5.48% | 70455 | 한국투자미국배당귀족자H(주식)(C-R) | 한국투자신탁운용 |
| em_equity | 1 | 61.1890 | 0.80% | 2074 | NH-Amundi성장중소형주[주식]ClassC-P2(퇴직연금) | NH-Amundi운용 |
| kr_equity | 1 | 90.3132 | 0.80% | 43306 | 한국밸류10년투자파이오니아(주식)(C-Re) | 한국투자밸류운용 |
| em_equity | 2 | 55.4582 | 0.10% | 71972 | 마이다스아시아리더스성장주자(H)(주식)C-P2 | 마이다스운용 |
| em_equity | 3 | 54.9564 | 0.10% | 71976 | 마이다스아시아리더스성장주자(UH)(주식)C-P2 | 마이다스운용 |
| kr_equity | 2 | 78.0547 | 0.10% | 43040 | NH-Amundi필승코리아[주식]ClassC-P2(퇴직연금) | NH-Amundi운용 |
| kr_equity | 3 | 70.0344 | 0.10% | 41944 | 교보악사파워인덱스자 1[주식]ClassCP | 교보악사운용 |
| us_high_yield | 1 | 32.7665 | 0.00% | 71800 | 베어링글로벌하이일드자[UH](채권-재간접)ClassC-P2e | 베어링운용 |
| us_high_yield | 2 | 16.4028 | 0.00% | 71791 | 베어링글로벌하이일드자[H](채권-재간접)ClassC-P2 | 베어링운용 |
| us_high_yield | 3 | 16.2624 | 0.00% | 74369 | 교보악사미국코어하이일드자(UH)[채권-재간접]_ClassC-Re(퇴직연…) | 교보악사운용 |
| dm_ex_us_equity | 1 | 53.2596 | 0.00% | 42669 | 한화천연자원자(주식)P클래스 | 한화운용 |
| dm_ex_us_equity | 2 | 52.9513 | 0.00% | 71463 | 피델리티재팬자(주식-재간접)CP | 피델리티운용 |
| dm_ex_us_equity | 3 | 48.3389 | 0.00% | 70744 | 삼성일본리더스전환자 1[주식](Cp(퇴직연금)) | 삼성운용 |

---

**Identifier note**: Ticker mapping unavailable for both ETF and Fund — product_id / product_name used as identifier. See diagnostics.missing_data.

---

## 31. explainability_summary_20260511.md

**원본 경로**: `out/db_review_relaxed_e62/explainability_summary_20260511.md`

# Portfolio Explainability Summary (20260511)

> schema_version: e7.1
> Read-only diagnostic. Allocation logic was not re-executed.

### ETF

#### 현재 경기국면 진단

- **current_location_text**: G7 region 의 ECI 좌표는 P=+0.7223 / V=+0.0586 으로 Regime 1 (Expansion / Acceleration) 에 위치합니다.
- **transition_text**: prev=R1 → curr=R1 (stable) (history 5 obs, 5/24 months)
- **asset_implication_text**: 현재 regime 의 자산군 선호 — 비중 확대: em_equity +2.0pp, kr_equity +2.0pp, us_high_yield +1.0pp / 비중 축소: us_treasury_30y -3.0pp, kr_treasury_10y -2.0pp.

#### SAA 도출 (max_sharpe MVO)

- **input_summary_text**: 9개 자산 — μ vector 평균=7.60%, σ vector 평균=13.53%. ρ matrix 9×9, Σ matrix 9×9 (E-6.2 telemetry, direct dump).
- **selected_saa_text**: MVO 결과 (top weights): us_growth_equity 71.6% / us_value_equity 28.4%. E[R]=15.40% / σ=15.96% / Sharpe=0.7769.
- **frontier_summary_text**: Efficient frontier visualization 은 E-9 phase 대상 (현재 미산출).
- **constraint_summary_text**: Active constraints: long_only, weight_sum=1.0 (hard). 비활성 (Phase D relaxed): weight_bounds, equity_sum, fixed_income_sum.

#### TAA Tilt 적용

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

#### Product Selection

- **universe_summary_text**: raw=932 / passed_filter=736 / classified=572 (by_asset_class 카운트만 노출).
- **selection_method_text**: score_method={'mode': 'hard_filter', 'min_grade': 'C', 'penalty_per_grade': 0.1}. single_product/manager cap 은 selection logic 내부에서 적용 (E-7 read-only 미평가).
- **top_selected_products**:
  - 타임폴리오TIME미국나스닥100액티브상장지수(주식) (타임폴리오자산운용, us_growth_equity) 20.00%
  - 삼성KODEX미국나스닥AI테크액티브상장지수[주식] (삼성운용, us_growth_equity) 20.00%
  - 미래에셋TIGER미국필라델피아반도체나스닥상장지수(주식) (미래에셋운용, us_growth_equity) 20.00%
  - 한국투자ACE미국배당다우존스상장지수(주식) (한국투자신탁운용, us_value_equity) 20.00%
  - 신한SOL미국배당다우존스상장지수[주식] (신한자산운용, us_value_equity) 4.66%
- **limitation_text**: Score factor 분해 / universe 전체 표 는 E-11 phase 대상 (selection score 미보존, ticker 미수록).

#### Warnings

- `EFRONTIER_DEFERRED` — Efficient frontier 미산출 — E-9 phase 대상.
- `REGIME_HISTORY_PARTIAL` — Regime history 5 obs 한정 — 24m timeline 미산출.
- `TAA_RULE_BASED` — TAA 는 rule-based heuristic prototype — regime-conditioned MVO 미적용.
- `PRODUCT_SCORE_MISSING` — selection score / factor values 미보존 — universe 전체 대비 분석 불가.

#### Missing data (deferred)

- **saa.efficient_frontier** — selected SAA point 의 frontier 위치 시각화 불가  → next: E-9 phase
- **regime.history (24m)** — 장기 regime timeline 시각화 불가  → next: regime backfill sidecar 또는 telemetry enhancement
- **product.scoring.scored_products** — factor 별 score 분해 불가  → next: E-11 phase + selection/tool.py 에서 score 보존
- **taa.regime_conditioned_assumptions** — regime-aware MVO 비교 불가  → next: future phase (regime_mvo, future study only)
- **product.selected_products.ticker** — Bloomberg/Reuters ticker 표기 불가  → next: 외부 ticker mapping table 도입 또는 DBProductRepository 확장

### Fund

(ETF 와 동일 — 자산 매핑 및 regime 동일. Product selection 부분만 Fund universe 기반으로 다름:
- universe_summary_text: raw=781 / passed_filter=414 / classified=262
- selection_method: score_penalty / min_grade=B / penalty_per_grade=0.1
- top_selected_products: KB미국대표성장주자(주식)(UH)C-퇴직 30%, 한국투자미국배당귀족자UH(주식)(C-R) 21.92%, 삼성미국그로스자UH 20.30%, AB미국그로스UH 20.30%, 한국투자미국배당귀족자H(주식)(C-R) 5.48%)

Warnings / Missing data 모두 ETF 와 동일 4 / 5 건.

---

# 통합 문서 끝

**문서 생성**: 2026-05-11
**원본 31개 md 파일 합본** (A 5 + B 8 + C 7 + D 3 + E 8)
**최신 정본**: `tdf_2060/docs/phase_e_current_handoff.md` (2026-05-11 갱신, E-12 완료 반영)
**pytest baseline**: `240 passed, 5 skipped, 1 xfailed`

> 본 통합 문서는 read-only 참조용. 향후 정본 수정은 각 원본 파일에서만 진행.
