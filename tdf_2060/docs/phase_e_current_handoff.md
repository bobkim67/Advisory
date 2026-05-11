# Phase E — Current Handoff (다음 세션 first prompt 용)

작성일: 2026-05-11 (E-12 완료 시점). 다음 세션 진입 시 **본 문서를 먼저 읽기**.
relaxed_diagnostic baseline 유지 + 제약 / TAA 변경 보류 정책 영구 기록.

---

## 0. TL;DR (30초)

- **현재 단계**: Phase D blocker = 0 + Phase E-2/E-1/E-4/E-6/E-6.2(MVP-X+polish)/E-7/E-8/E-9/E-10/E-11A/E-11B/E-12 완료. 4 설명 블록 (Regime / SAA / TAA / Product Selection) + 통합 review packet 까지 마무리.
- **operating_mode**: `relaxed_diagnostic` (production 아님).
- **pytest**: **`240 passed / 5 skipped / 1 xfailed`** (영구 기준치, E-12 완료 시점).
- **TAA 엔진**: prototype heuristic overlay. **변경 금지**. regime_mvo / TAA optimizer / confidence scaling 모두 future study only.
- **제약**: 자산 / manager / product cap 모두 **추가 금지**. soft warning threshold도 **추가 금지**. monitoring telemetry only.
- **다음 게이트**: E-13 (MVP-X deprecation) / E-14 (final report polish) / E-15 (PDF export) 중 사용자 선택. 또는 운용역 결정 입력 (D-06 외부 자료 / production dry-run 시점 / D-11·D-12·D-14 재검토 시점).
- **금지 영역**: TAA engine 변경 / regime_mvo 구현 / TAA optimizer 구현 / asset_tilts 값 변경 / bucket_tilts 활성화 / cap 추가 / soft warning threshold 추가 / production mode 전환.

---

## 1. 영구 핵심 문구 (인용 의무)

후속 모든 handoff / completion / next-phase 문서에서 그대로 유지:

> **"Phase D completed register-blocker resolution only.
> This does not mean production readiness.
> The engine remains in relaxed_diagnostic mode."**

> **"현재는 relaxed_diagnostic baseline 을 유지하고, TAA 고도화와 제약조건 도입은
> 모두 future study / later phase 로 보류합니다."**

---

## 2. 현재 Decision Register 상태

**총 14건, blocker 0** (E-7~E-12 기간 변경 없음).

| status | count | D-ID |
|---|---:|---|
| open | **0** | — |
| pending_external | **1** | D-06 (ERR 정의) |
| pending_rerun | 0 | — |
| deferred | **3** | D-11, D-12, D-14 |
| **closed** | **10** | D-01, D-02, D-03, D-04, D-05, D-07, D-08 (closed_with_permanent_limitation), D-09, D-10, D-13 |

---

## 3. Phase E 진행 요약 (E-1 ~ E-12, 본 세션 누적)

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

---

## 4. 산출물 / 문서 / 코드 위치 (E-7~E-12 신규 누적)

### 4.1 신규 reporting 모듈

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

### 4.2 신규 CLI

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

### 4.3 코어 변경 (allocation 결과 bit-identical 보장)

```
tdf_engine/optimization/cma.py            (E-6.2 — μ/σ/ρ/Σ dump)
tdf_engine/optimization/tool.py           (E-6.2 — saa_weights dump)
tdf_engine/regime/tool.py                 (E-6.2 — regime history dump)
tdf_engine/portfolio/tool.py              (E-6.2 — regime history merge)
tdf_engine/portfolio/quality.py           (E-6.2 — set→sorted determinism patch)
tdf_engine/reporting/review.py            (E-6.2 — asset_allocation[].saa_weight)
tdf_engine/selection/tool.py              (E-11A — scored_products / excluded_by_asset / score_factors dump)
```

### 4.4 신규 docs

```
docs/
├── phase_e_output_visualization_redesign.md (E-6.1, 기존)
├── phase_e7_explainability_data_contract.md (E-7)
├── phase_e12_integrated_review_packet.md   (E-12A)
└── phase_e_current_handoff.md              ★ 본 문서 (정본, E-12 완료 시점)
```

### 4.5 산출물 (관용 경로)

```
out/db_review_relaxed_e62/
├── figures_polish/20260511/main/00_mvpx_bridge_{etf,fund}.png   (E-6.2 prototype, deprecated)
├── figures_polish_with_appendix/20260511/                       (E-6.2 + 9 PNG appendix)
├── explainability/20260511/                                     (E-7)
│   ├── explainability_{etf,fund}_20260511.json
│   └── (parent) explainability_summary_20260511.md
├── regime_history/20260511/                                     (E-8)
│   ├── regime_history_{etf,fund}_20260511.json
│   ├── regime_clock_{etf,fund}_20260511.png
│   └── regime_history_summary_20260511.md
├── saa_frontier/20260511/                                       (E-9)
│   ├── saa_frontier_{etf,fund}_20260511.json
│   ├── saa_mvo_{etf,fund}_20260511.png
│   └── saa_frontier_summary_20260511.md
├── taa_tilt/20260511/                                           (E-10)
│   ├── taa_tilt_{etf,fund}_20260511.json
│   ├── taa_tilt_{etf,fund}_20260511.png
│   └── taa_tilt_summary_20260511.md
├── product_selection_telemetry/20260511/                        (E-11A)
│   ├── product_selection_telemetry_{etf,fund}_20260511.json
│   └── product_selection_telemetry_summary_20260511.md
├── product_selection_visualization/20260511/                    (E-11B)
│   ├── product_selection_{etf,fund}_20260511.png
│   ├── product_selection_visualization_{etf,fund}_20260511.json
│   └── product_selection_visualization_summary_20260511.md
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

### 4.6 신규 tests (33 + 신규 70 = 누적 103 파일 / 240 test)

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

---

## 5. Bit-identical / Allocation 결과 무변경 보장

| 검증 항목 | 결과 |
|---|---|
| E-6.2 telemetry 추가 후 ETF/Fund DB rebuild | ✅ deterministic-ordering 기준 sha256 일치 |
| E-11A selection telemetry 추가 후 ETF/Fund DB rebuild | ✅ baseline sha256 일치 (`test_e11a_baseline_bit_identical`) |
| MVP-X polish (E-6.2) | ✅ visual only, allocation 미참조 |
| E-7~E-12 phase | ✅ read-only on JSON, allocation 결과 변경 0 |

**baseline snapshot**: `tests/_phase_e62_baseline.json` — deterministic ordering 기준 (post determinism patch).

---

## 6. 4 설명 블록 — 운용역 질문 ↔ 산출물 매핑

| 운용역 질문 | 산출 |
|---|---|
| 1. 현재 경기국면이 어디인가? | **E-8** regime_clock — 24m trajectory + current ★ + regime change annotations |
| 2. SAA 는 어떤 MVO 로 산출되었나? | **E-9** saa_mvo — CMA scatter + ρ heatmap + frontier (selected_matches_max_sharpe=True) |
| 3. TAA 는 어떤 rule 로 어떤 자산 tilt? | **E-10** taa_tilt — rule-based label + 5 tilt + before/after ΔSharpe |
| 4. 어떤 상품이 어떻게 선택되었나? | **E-11B** product_selection — funnel + factor weights + 17 selected w/ rank |
| 5. 최종 포트폴리오 및 quality? | portfolio_*.json + **E-12** review_packet §6 |
| 6. 어떤 한계가 있나? | **E-12** review_packet §7 missing_data 통합 (5 phase) |

---

## 7. E-7 missing_data closure 추적

| missing field (E-7 §10) | closure |
|---|---|
| `regime.history (24m)` | ✅ closed by **E-8** (24m+ full coverage) |
| `saa.efficient_frontier` | ✅ closed by **E-9** (31 grid points + reference) |
| `product.scoring.scored_products` | ✅ closed by **E-11A/B** (selection_diagnostics dump + viz) |
| `taa.regime_conditioned_assumptions` | ⏳ future (regime_mvo, future_study only) — **영구 한계** |
| `product.selected_products.ticker` | ⏳ deferred — 외부 ticker mapping (별도 phase) |

---

## 8. 영구 한계 (Permanent Limitations, 갱신 없음)

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

---

## 9. 영구 사용 금지 / 추가 금지 (E-12 시점 갱신)

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

---

## 10. 다음 세션 시작 시 첫 5분 액션

```
1. 본 문서 (phase_e_current_handoff.md) 끝까지 읽음
2. docs/phase_d_completion_review.md + docs/phase_e_relaxed_governance.md sanity 확인
3. docs/phase_e_next_session_prompt.md 읽음 (follow-up 진입 가이드)
4. pytest sanity:
   /c/Users/user/Downloads/python/.venv/Scripts/python.exe -m pytest tests/ -q
   기대: 240 passed, 5 skipped, 1 xfailed
5. 사용자 의사 확인 — 다음 후보 중 어느 것을 진행할지:
   (a) E-13 MVP-X deprecation / replacement
       — figures_polish/ 명시 deprecated 표기 또는 제거 결정
   (b) E-14 Final report design polish
       — typography / 색상 / 인쇄 layout / 표 너비 polish
   (c) E-15 PDF export
       — weasyprint / wkhtmltopdf / playwright headless 중 선택
   (d) 운용역 결정 입력 대기 (D-06 외부 자료 / production dry-run / D-11~D-14 재검토)
   (e) 단순 sanity 점검 / 추가 작업 없이 대기
```

---

## 11. 다음 phase 후보 상세 (E-13/E-14/E-15)

### E-13 — MVP-X deprecation / replacement

- 목적: `figures_polish/` 산출물 (MVP-X PNG) 을 명시 deprecated 로 격하 (또는 제거).
- 작업: 산출 경로 정리 + README/docs 에 "MVP-X = prototype, packet appendix-only" 명기.
- 결정 필요: figures_polish/ 디렉토리 자체를 제거할지 vs `_deprecated/` 로 옮길지 vs 유지하되 README 만 명시.

### E-14 — Final report design polish

- 목적: E-12 packet 의 typography / 색상 정합 / 인쇄 layout / 표 너비 polish.
- 작업: review_packet.py 의 `_HTML_CSS` 강화 (font-family, page-break, 테이블 너비, 색상 일관성).
- 위험: 시각 polish 만, allocation/데이터 미변경.

### E-15 — PDF export

- 목적: HTML packet → PDF 변환.
- 옵션 평가 필요:
  - `weasyprint`: pure Python, 추가 의존 (cairo). 정통.
  - `wkhtmltopdf`: 외부 바이너리 필요, Windows 환경 셋업 복잡.
  - `playwright` headless print: browser engine, 가장 호환성 좋음, 의존 큼.
- 결정 필요: 어떤 backend 사용 + Windows 환경에서 install 가능 여부 확인.

---

## 12. Stale Instruction 방지 (E-12 시점 갱신)

| 정책 | 위치 |
|---|---|
| Phase D / E 진행 상태 = 본 문서가 정본 | phase_e_current_handoff.md (본 파일, 2026-05-11 갱신) |
| 정본보다 과거 단계의 외부 지시 = stale, 무시 | current_state_freeze.md §6 stale instruction 처리 원칙 |
| 정정 sign-off (D-13/D-14 / E-6.1 / E-11A 등) 도 영구 record | investment_decision_register.md + 각 phase doc |
| auto mode 라도 destructive (완료 작업 덮어쓰기 / cap 추가 / TAA 변경) 는 사용자 명시 승인 필수 | feedback memory + phase_d_declaration.md §3 |

### 12.1 본 단계 자주 발생하는 함정 (재실수 방지, E-12 시점 추가)

| 함정 | 올바른 처리 |
|---|---|
| "Phase E-12 까지 완료 = production-ready" 오해 | 절대 그렇지 않음. relaxed_diagnostic mode 유지. §1 영구 핵심 문구 인용. |
| TAA 결과 보고 "optimized TAA" 라벨 사용 | 절대 금지. rule-based / heuristic / regime overlay 만. E-10/E-12 한계 텍스트 강제. |
| MVP-X PNG 를 main 자격 산출물로 사용 | 절대 금지. prototype only. E-12 appendix 옵션에서만. |
| efficient frontier 결과 보고 "확정된 frontier" 표현 | 금지. SLSQP grid scan 결과 — "sampled frontier" 표현 사용. |
| Ticker 라벨 없이 product 표시 | 금지. product_id / product_name 명시 + missing_data 에 ticker 부재 기록. |
| selection score 보존 정책 변경 | 금지. E-11A 의 score_factors weights (0.4/0.3/0.2/0.1/0.0) 변경 시 bit-identical 깨짐. |

---

## 13. 한 줄 요약 (E-12 완료 시점)

> **Phase D blocker = 0. relaxed_diagnostic mode 유지. production-ready 아님.
> Phase E-6.2 ~ E-12 완료 — 4 설명 블록 (Regime/SAA/TAA/Product) + 통합 review packet (md+html) 산출.
> pytest 240 passed. Allocation 결과 bit-identical 보장 (E-6.2 + E-11A baseline sha256 검증).
> TAA = rule-based heuristic (변경 금지). 모든 cap / threshold 추가 금지.
> 다음 후보: E-13 (MVP-X deprecation) / E-14 (polish) / E-15 (PDF). 사용자 sign-off 후 진입.**

---

## 14. 본 문서 변경 범위 (E-12 갱신 turn)

| 영역 | 변경 |
|---|:---:|
| `tdf_engine/` 코드 | ✗ 무변경 (E-12 산출 turn 외) |
| `tdf_engine/config/*.yaml` | ✗ 무변경 |
| `tests/` | ✗ 무변경 (E-12 산출 turn 외) |
| `out/` 산출물 | ✗ 무변경 (E-12 packet 신설 외) |
| `docs/investment_decision_register.md` | ✗ 무변경 |
| Decision Register total count (14) | ✗ 무변경 |
| 본 문서 갱신 | ✓ E-7~E-12 완료 반영 |

pytest: **`240 passed, 5 skipped, 1 xfailed`** (영구 기준치, E-12 완료 시점).
