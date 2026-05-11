# Phase D Completion Review

작성일: 2026-05-08. **Phase D register blocker 0건 도달 시점의 공식 완료 검토**.
본 문서는 Phase D 의 완료 상태 / 영구 한계 / 후속 Phase 후보를 단일 문서로 잠그는 record.

> ⚠️ **Phase D register blocker = 0건. 단 production-ready 아님.**
> 현재 엔진은 `relaxed_diagnostic` mode. Production 전환은 별도 Phase 에서 다룸.
> 본 문서는 Phase E 진입 전 Phase D 의 closure 상태를 영구 기록한다.

---

## 1. Executive Summary

| 항목 | 값 |
|---|---|
| **Phase D register blocker** | **0건** (8 → 4 → 3 → 2 → 0) |
| **operating_mode** | `relaxed_diagnostic` |
| **production-ready** | **아님** (별도 Phase 필요) |
| **hard constraint** | `long-only` + `sum-to-100%` + 데이터 무결성 (BRFUT004 / DB / NaN / convergence) |
| **TAA rule** | prototype operator-defined heuristic overlay (NOT final quantitative model, NOT second-stage optimizer) |
| **pytest** | 142 passed / 5 skipped / 1 xfailed (xfail 영구 보류 — 외부 답안지 부재) |
| **Decision Register** | 14건 (open 2 / pending_external 1 / pending_rerun 0 / deferred 2 / closed 9) |
| **Permanent limitation** | DRM 3 xlsx 해제 불가 → Excel 1:1 parity 영구 waived |

---

## 2. Decision Register 최종 상태

**총 14건**, blocker 0건.

| status | count | D-ID |
|---|---:|---|
| open | **2** | D-13, D-14 |
| pending_external | **1** | D-06 |
| pending_rerun | 0 | — |
| deferred | **2** | D-11, D-12 |
| **closed** | **9** | D-01, D-02, D-03, D-04, D-05, D-07, **D-08 (closed_with_permanent_limitation)**, D-09, D-10 |

**Phase D blocker 변화 (영구 기록)**:

```
초기 정의:    D-01 / D-02 / D-03 / D-08 / D-09 / D-10 / D-11 / D-12   (8건)
Phase D 진입: D-01 / D-02 / D-03 / D-08 / D-09 / D-10 / D-11 / D-12   (8건)
relaxed 적용: D-02 / D-03 / D-08 / D-09                              (4건; D-01·D-10 closed, D-11·D-12 deferred)
D-02 sign-off: D-03 / D-08 / D-09                                    (3건)
D-03 sign-off: D-08 / D-09                                           (2건)
D-08+D-09 sign-off: —                                                (0건) ← 현재
```

**Phase D 종료 조건** (`docs/phase_d_declaration.md §5`):
- ✅ Decision Register blocker 항목 모두 closed
- ⏳ `final_asset_bounds` 운영값 적용된 산출의 운용역 사인 → relaxed_diagnostic 정책상 final_asset_bounds 비활성. 본 조건은 production 전환 단계 (Phase E 후보) 에서 재해석.

---

## 3. Closed decisions 요약 (9건, 영구 기록)

각 항목의 정책 / 적용 위치 / 한계를 영구 기록.

### D-01 — Hard constraint set definition (closed 2026-05-08)
- **decision**: 본 단계 hard constraint = `long-only` + `sum-to-100%` + 데이터 무결성.
- **non-enforcement**: `final_asset_bounds`, `taa_bounds` (bucket 75-85/15-25), `weight_bounds` (per-asset min/max), `taa_policy.constraints.per_asset_max_tilt 0.03` 모두 **reference / telemetry only**.
- **glide path 80/20**: `tdf_2060.yaml::strategic_allocation` + `reference_weights` 그대로 — initial SAA / MVO warm-start 용도.
- **재도입 경로**: 자산군별 band / bucket range / TAA 허용범위는 별도 신규 Decision 항목 (Phase E 후보).

### D-02 — Projection drift policy (closed 2026-05-08, projection drift only scope)
- **enforcement modes**: `relaxed_diagnostic=telemetry_only` / `review=warning` / `production=review_required`
- **threshold**: asset 3% / bucket 5%
- **scope**: **projection drift only**. product cap / selection fallback drift 는 D-15/D-16/D-17 candidate 로 분리.
- **drift_source taxonomy** (적용됨): `taa/projection.py` 7-source + `quality.py` 5-source.
- **참조**: `docs/phase_d_d02_drift_closure_brief.md`, `docs/phase_d_d02_signoff_patch_plan.md`.

### D-03 — Lookback policy (closed 2026-05-08, Option C — Hybrid)
- **decision**: `return/vol = asset_specific` + `corr = common intersection`
- **min_obs** = 12, **short_history_warning_ratio** = 0.8
- **ust30 obs=87**: 허용 (telemetry only). DB sanity flag (hard) vs review warning (telemetry) 구분 명시.
- **참조**: `docs/phase_d_d03_lookback_policy_review.md`.

### D-04 — `us_treasury_30y` BRFUT004 mapping / fallback policy (closed 2026-05-08)
- **decision**: BRFUT004 direct mapping (db_dataset_id=201, dataseries_id=33, blob key totRtnIndex). **추가 proxy 금지**. TLT/EDV/USGG10YR 사용 금지.
- **fallback_policy**: `no_fallback` / `hard_error` (`fallback_policy: explicit_proxy_only` = `no_silent_fallback`).
- **file mode**: BRFUT004 row 부재 시 `ValueError`. 운영 실행은 `--source db` 권장.

### D-05 — MVO objective (closed)
- **decision**: `max_sharpe` 기본 + dispatch table 4종 (max_sharpe / utility / min_volatility / max_return_under_risk_limit).
- **회귀 방어**: `tests/test_optimization_objective_dispatch.py`, `OBJECTIVE_REGISTRY`.
- **D-08 limitation 영향**: Excel `$L$26` 직접 확인 **영구 waived** (DRM 해제 불가).

### D-07 — HY classification (closed)
- **decision**: `us_high_yield` = `fixed_income` bucket + `risk_asset` flag + `credit` flag.
- **회귀 방어**: `tests/test_config_loader.py::test_hy_has_risk_asset_and_credit_flags`.

### D-08 — Excel DRM 3건 (closed_with_permanent_limitation 2026-05-08)
- **closure type**: `closed_with_permanent_limitation` — 일반 closed 와 구분.
- **운영자 정보 (2026-05-08)**:
  - DRM 3 xlsx 영구 해제 불가
  - GlidePath 4 vintage 운영자 직접 제공 (2060=80% / 2050=70% / 2040=60% / 2030=50%) → `tdf_engine/config/glidepath.yaml` 신설 (reference only, enforced=false)
  - `RegimeAnalysis_2602.xlsx` / `ECI_Neo_202603.xlsx` 내용 = 기존 `regime_*` + `regimeAnalysis_*` file 결합물. 추가 정보 없음.
- **permanent limitation**:
  - SAA / TAA / Final weights Excel 1:1 parity 검증 **영구 waived**
  - MVO objective Excel `$L$26` 직접 확인 **영구 waived** (D-05 의 max_sharpe 정책은 그대로 유효)
  - 단 Placement / Velocity / Regime classification parity 는 Phase C.5 에서 PASS (USA region) — 영향 없음
- **참조**: `docs/phase_d_d08_d09_closure_plan.md`.

### D-09 — `regimeAnalysis_rt` definition (closed 2026-05-08)
- **decision**: `Advisory/regimeAnalysis_rt` 파일 자체 = canonical definition. 별도 definition 자료 없음 (운영자 확인).
- **Phase C.5 xfail 1건**: **유지**. 사유 갱신 (정의 미명시 → "외부 Excel parity 답안지 영구 부재 / DRM 해제 불가").
- **참조**: `docs/golden_answer_validation.md §5.5`.

### D-10 — 자산군 0% 허용 (closed 2026-05-08)
- **decision**: 모든 개별 자산군 0% 허용. **음수 비중만 금지** (final portfolio long-only).
- **중간 TAA target 음수**: 발생 가능. projection 으로 0% 보정. pre-projection negative 는 telemetry / info warning.
- **회귀 방어**: `tests/test_phase_d_relaxed.py` (long_only / sum_to_one).

---

## 4. Deferred / Open / Pending 항목 (5건, 후속 Phase 검토)

| # | 항목 | status | 책임 | 검토 시점 |
|---|---|---|---|---|
| D-06 | ERR 정의 | pending_external | 운영자 | Excel 원본 (DRM) 영구 부재로 운용역 별도 결정 필요. D-08 limitation 영향. |
| D-11 | `dm_ex_us_equity` lower bound | deferred | — | 자산군별 band 재도입 단계 (Phase E 후보) |
| D-12 | `us_value_equity` cap | deferred | — | 동일 |
| D-13 | `quant_grade_policy` mode | open | 운용역 | relaxed governance 또는 Phase E |
| D-14 | manager concentration cap | open | 운용역 | 동일. relaxed run 결과 (Fund: KB 30% / 한투 27.4%) 참고용 brief = `docs/phase_d_concentration_brief.md` |

### 4.1 Future candidates (정식 register 항목 아님)

| candidate | 영역 | 위상 |
|---|---|---|
| **D-15** | Asset target vs product allocation drift policy | candidate. 정식 등록 시 register total count 14 → 15+ 갱신 필요 |
| **D-16** | Product-level single cap policy | 동 |
| **D-17** | Asset concentration monitoring | 동 |
| TAA cand-A | regime confidence scaling | candidate. `phase_d_taa_tilt_design_review.md §4` |
| TAA cand-B | optimization-based TAA | 동 |
| TAA cand-C | signal-based TAA | 동 |
| TAA cand-D | bucket_tilts 활성화 | 동 |
| TAA cand-E | tilt 백테스트 / parameter sensitivity | 동 |
| Telemetry cand | SAA weights / TAA tilt by asset / 제외 상품 ID / selection score 노출 | `phase_d_drift_telemetry_proposal.md §1, §10` |

⚠️ 위 candidate 모두 **정식 Decision Register 등록 시 total count / status distribution 별도 갱신 필요**. 본 단계까지 등록 0건.

---

## 5. Permanent Limitations (영구 기록)

본 Phase D 가 다루지 못하고 **영구 보류** 된 사항. 후속 Phase 에서도 해소 불가.

| # | 한계 | 근원 |
|---|---|---|
| 1 | DRM 3 xlsx 영구 해제 불가 | `0. 정리 - GlidePath 값.xlsx`, `RegimeAnalysis_2602.xlsx`, `ECI_Neo_202603.xlsx` 의 `<DOCUMENT SAFER V2010 R2>` DRM 보호 |
| 2 | SAA / TAA / Final weights Excel 1:1 parity 검증 영구 waived | DRM 으로 답안지 자체 부재. 검증 불가능. |
| 3 | MVO objective Excel `$L$26` 직접 확인 영구 waived | 동 |
| 4 | regimeAnalysis_rt 의 region / annualization / regime base 정의 자료 영구 부재 | 운영자 확인 (2026-05-08): 별도 자료 없음. 파일 자체가 정본. |
| 5 | `tests/test_phase_c5_golden_parity::test_golden_regime_returns_match_expected` xfail 영구 유지 | 답안지 영구 부재 → testcase 자체는 의미 있음 (영구 답안지 부재 reflect). strict=False. |
| 6 | `glidepath.yaml` 은 **reference metadata only** | enforced=false. 코드에서 읽지 않음. 다중 vintage 산출은 후속 Phase. |
| 7 | `regimeAnalysis_rt` 파일 자체가 정본 | 별도 definition 문서 없음. 후속 Phase 에서도 동일. |

본 7개 한계는 후속 Phase 에서도 변경되지 않음. **Phase D 의 register blocker 해소 = parity 검증 완료 가 아님**.

---

## 6. Current Engine Mode

| 항목 | 값 |
|---|---|
| `tdf_2060.yaml::operating_mode` | **`relaxed_diagnostic`** |
| relaxed output 위상 | **diagnostic baseline** (NOT production portfolio) |
| equity 100% / fixed_income 0% | **monitoring flag** (NOT fail) |
| D-02 drift | telemetry 구조화 완료 (`drift_thresholds.modes` config-driven, telemetry_only 모드) |
| product cap drift (10.60% at us_growth) | D-02 가 아닌 D-15/D-16/D-17 candidate 영역 |
| review packet | banner + §3.1 Drift source breakdown + §6 enforcement mode 표시 |
| TAA tilt | prototype operator-defined heuristic. asset_tilts 만 적용. bucket_tilts 는 metadata only. |
| Hard constraint | long-only + sum-to-100% + BRFUT004 mapping + DB / NaN / convergence |

### 6.1 relaxed run 산출 핵심 수치 (참조)

ETF / Fund 동일 (universe / selection 단계 product 차이만):
- equity bucket = 100% (sanity range [60-95]% ⚠ 이탈, fail 아님)
- fixed_income bucket = 0%
- us_growth = 70.60% (asset target) → 60.00% (product cap clipping)
- max_abs_projection_drift = 3.00% (long_only_clipping at ust30/kr_t10)
- max_abs_asset_weight_drift = 10.60% (product_cap_clipping_outflow at us_growth)
- 0% 자산 = 5건 (kr_aggregate, kr_t10, ust30, dm_ex_us, hy)
- negative count = 0 (long-only 보장)
- sum = 1.000000

---

## 7. Review Artifacts (현재 기준 주요 산출물 / 문서 경로)

### 7.1 산출물

```
out/db_etf_relaxed/
├── portfolio_etf_20260508.csv
├── portfolio_etf_20260508.json
└── review_etf_20260508.md           (banner + §3.1 drift source + §6 enforcement)
out/db_fund_relaxed/
├── portfolio_fund_20260508.csv
├── portfolio_fund_20260508.json
└── review_fund_20260508.md          (동일)
out/db_review_relaxed/
└── comparison_etf_vs_fund_20260508.md
```

### 7.2 Phase D 문서 (영구 record)

```
docs/
├── phase_d_declaration.md                       Phase D 진입 / freeze / stale instruction 정책
├── current_state_freeze.md                      C.5 동결 스냅샷
├── investment_decision_register.md              14건 결정 + 변경 이력
├── phase_d_relaxed_constraints_proposal.md      D-01 정책 도출 (Option B 근거)
├── phase_d_decision_brief.md                    운용역 5 결정 brief (D-02/10/11/12/01)
├── phase_d_concentration_brief.md               D-13/D-14 검토 brief
├── phase_d_drift_telemetry_proposal.md          D-02 telemetry 구조 분석
├── phase_d_taa_tilt_design_review.md            TAA tilt = prototype heuristic 명시
├── phase_d_d02_drift_closure_brief.md           D-02 closure brief + sign-off
├── phase_d_d02_signoff_patch_plan.md            D-02 patch plan
├── phase_d_d03_lookback_policy_review.md        D-03 review + sign-off
├── phase_d_d08_d09_closure_plan.md              D-08+D-09 closure plan
├── phase_d_completion_review.md                 ★ 본 문서 (Phase D 완료 record)
├── golden_answer_validation.md                  Phase C.5 + D-08/D-09 closure note
├── phase_c_final_handoff.md                     Phase C.5 시점 handoff
├── phase_c_db_repository.md                     Phase C 누적
└── phase_b_review_packet.md                     Phase A/B/B.5/B.5+/C-pre 누적

source_review/
├── source_file_inventory.md
├── mvo_source_review.md
└── regime_source_review.md                      D-08/D-09 운영자 확인 note 포함
```

### 7.3 핵심 코드 / config

```
tdf_engine/
├── config/
│   ├── tdf_2060.yaml                            operating_mode=relaxed_diagnostic + drift_thresholds.modes + taa_sanity_range
│   ├── glidepath.yaml                           ★ D-08 closure 시 신설 (4 vintage reference)
│   ├── db_sources.yaml                          intersection_policy / min_obs / short_history_warning_ratio (D-03)
│   ├── optimization_constraints.yaml            equity_sum / fixed_income_sum 완화 [0,1]
│   ├── taa_policy.yaml                          per_asset_max_tilt=1.0, warn_if_*=false
│   ├── asset_mapping.yaml                       BRFUT004 direct mapping (D-04)
│   ├── universe_filter.yaml
│   └── universe_classification.yaml
├── taa/projection.py                            7-source drift_source taxonomy + clipping_summary
├── portfolio/quality.py                         5-source drift_source + 5 enforcement modes
├── portfolio/builder.py                         enforcement / drift_source 보존
├── portfolio/tool.py                            yaml drift_thresholds.modes 매핑
└── reporting/review.py                          banner + §3.1 + §6 enforcement
```

---

## 8. Phase E 후보 (정의만, 정식 합의 아님)

본 candidate 들은 Phase E 진입 전 **별도 검토** 가 필요. 본 문서는 candidate 정의만.

| candidate | 영역 | 우선순위 후보 |
|---|---|:---:|
| **E-1** | Production mode 전환 설계 (relaxed_diagnostic → review → production 단계적 이행) | 높음 |
| **E-2** | relaxed governance / sign-off flow (운영자가 누가 / 언제 / 어떤 기준으로 보고 승인·보류·재실행) | 높음 |
| E-3 | Asset band 재도입 (D-11 / D-12 reactivate) | 중 |
| E-4 | Manager concentration / quant grade policy (D-13 / D-14) | 중 |
| E-5 | Product cap / fallback drift policy (D-15 / D-16 / D-17 정식 등록) | 중 |
| E-6 | TAA confidence scaling (TAA cand-A) | 낮음 |
| E-7 | TAA optimizer (TAA cand-B) | 낮음 |
| E-8 | Multi-vintage glidepath integration (2050 / 2040 / 2030 산출) | 낮음 (`glidepath.yaml` 출발점 확보) |

추천 시작 순서: **E-2 → E-1 → E-4 / E-5 (병렬) → E-3 → E-8 → E-6 / E-7**.

---

## 9. 한 줄 요약

> **Phase D register blocker 0건 도달 (8 → 4 → 3 → 2 → 0). 단 production-ready 아님 — engine 은 relaxed_diagnostic.
> Closed 9건 + Deferred 2 + Pending external 1 + Open 2 (D-13/D-14) = 14.
> Permanent limitation: DRM 3 xlsx 해제 불가 → Excel 1:1 parity 영구 waived.
> 다음 단계 = Phase D 종료 선언 전 relaxed governance (E-2) 정리, 그 후 Phase E 진입.**

---

## 10. 본 문서 변경 범위

| 영역 | 변경 |
|---|:---:|
| `tdf_engine/` 코드 | ✗ 무변경 |
| `tdf_engine/config/*.yaml` | ✗ 무변경 |
| `tests/` | ✗ 무변경 |
| `out/` 산출물 | ✗ 무변경 |
| `docs/investment_decision_register.md` status | ✗ 무변경 (현재 분포 그대로 record) |
| Decision Register total count | ✗ 무변경 (14) |
| 본 문서 신설 | ✓ `docs/phase_d_completion_review.md` |

pytest: `142 passed, 5 skipped, 1 xfailed` (sanity 차원, 본 문서 작성 영향 없음).
