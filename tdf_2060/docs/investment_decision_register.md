# Investment Decision Register — TDF 2060

작성일: 2026-05-08. Phase D 진입과 함께 신설.

> ⚠️ **현재 operating mode = `relaxed_diagnostic`**. 본 register 의 일부 항목 (D-01/D-10 closed, D-11/D-12 deferred)
> 은 relaxed 정책 하에서 결정된 것이며, **본 단계의 산출은 production 이 아닌 diagnostic baseline**.
> 자산군별 band / bucket range 재도입 시 별도 신규 Decision 항목으로 추가 예정.

> 운용역/운영자가 결정해야 할 항목과 현재 default·blocker 영향을 한 곳에 모은다.
> 항목별 진행 상태는 4종 중 하나: `open` / `pending_decision` / `pending_external` / `closed`.
> 본 register는 결정 전 가능한 작업이며 (`P-02`), 결정 수령 시마다 갱신된다.

---

## 1. 총괄 (총 14건)

| # | 항목 | 상태 | 책임 | blocker 종류 |
|---|---|---|---|---|
| D-01 | Hard constraint set definition | closed | — | (long-only + sum-to-100% + 데이터 무결성. final_asset_bounds·bucket range·per-asset band 는 reference/telemetry only) |
| D-02 | `max_abs_projection_drift` 임계 (projection drift only scope) | closed | — | (relaxed=telemetry_only / review=warning / production=review_required, asset 3% / bucket 5%) |
| D-03 | lookback 정책 (Hybrid: return/vol asset_specific, corr common) | closed | — | (Option C 채택, min_obs=12, short_history_warning_ratio=0.8) |
| D-04 | `us_treasury_30y` BRFUT004 mapping / fallback policy | closed | — | (BRFUT004 direct mapping 확정, 추가 proxy 금지) |
| D-05 | MVO objective 식 (Excel `$L$26`) | closed | — | (max_sharpe 확정, dispatch 4종) |
| D-06 | ERR 정의 | pending_external | 운영자 | Excel 원본 |
| D-07 | HY 처리 (risk_asset + credit) | closed | — | (yaml + test 회귀 방어 적용) |
| D-08 | Excel DRM 3건 — 운영자 직접 정보 + 기존 file 모드 데이터로 대체 | **closed_with_permanent_limitation** | — | (DRM 해제 영구 불가. SAA/TAA/Final 1:1 parity 검증 영구 보류) |
| D-09 | `regimeAnalysis_rt` 정의 (파일 자체가 정본) | closed | — | (별도 definition 자료 없음. 파일 = canonical definition) |
| D-10 | 자산군 0% 허용 여부 | closed | — | (모든 자산군 0% 허용. negative weight 만 금지) |
| D-11 | `dm_ex_us_equity` lower bound | deferred | — | (현 단계 미적용. 자산군별 band 도입 시 재논의) |
| D-12 | `us_value_equity` cap | deferred | — | (현 단계 미적용. 동일) |
| D-13 | `quant_grade_policy` mode (현행 유지: ETF=hard_filter, Fund=score_penalty) | closed | — | (현 단계 추가 제약 도입 안 함, 운용역 추인) |
| D-14 | 운용사 concentration cap | deferred | — | (cap / soft warning threshold 모두 미도입. monitoring telemetry only. 후속 Phase 에서 제약 도입 여부 재검토) |

상태 분포: `open` 0건, `pending_external` 1건, `pending_rerun` 0건, `deferred` 3건, `closed` 10건. **합계 14**. (2026-05-08 sign-off: D-13 closed (현행 유지), D-14 deferred (cap 도입 후속 Phase). `open 2 → 0`, `deferred 2 → 3`, `closed 9 → 10`.)

내역:
- `open` (0): —
- `pending_external` (1): D-06 (ERR 정의)
- `pending_rerun` (0): —
- `deferred` (3): D-11, D-12, **D-14** (manager concentration — 제약 도입 미정, monitoring only)
- `closed` (10): D-01, D-02, D-03, D-04, D-05, D-07, D-08 (closed_with_permanent_limitation), D-09, D-10, **D-13**

**Phase D register blocker = 0건** (D-08 + D-09 closed by 운용역 sign-off 2026-05-08). 단 **"production-ready" 가 아니며 register blocker 만 해소** 된 상태. 엔진은 여전히 `relaxed_diagnostic` mode. Production 전환은 별도 단계. 본 단계 추가 제약 (manager cap / soft warning threshold / product cap / asset band) 도입 안 함 — 후속 Phase 에서 re-evaluate.

이전 blocker 변화: 8 → 4 → 3 → 2 → **0**.

---

## 2. 항목별 상세

### D-01. Hard constraint set definition — **closed (2026-05-08)**
- **decision**: 본 단계 hard constraint = `long-only` + `sum-to-100%` + 데이터 무결성 (BRFUT004 mapping / DB / NaN / optimizer · projection convergence)
- **non-enforcement**: `final_asset_bounds`, `taa_bounds` (bucket 75-85/15-25), `weight_bounds` (per-asset min/max), `taa_policy.constraints.per_asset_max_tilt 0.03` 모두 **reference / telemetry only**
- **glide path 80/20**: `tdf_2060.yaml.strategic_allocation` + `reference_weights` 그대로 — initial SAA / MVO warm-start 용도로 보존
- **변경 위치**: `config/tdf_2060.yaml`, `config/optimization_constraints.yaml`, `config/taa_policy.yaml`, `portfolio/validator.py`, `portfolio/quality.py`, `reporting/review.py`
- **재도입 경로**: 자산군별 band / bucket range / TAA 허용범위는 추후 별도 Decision 항목으로 신설 후 도입

### D-02. `max_abs_projection_drift` 임계 (projection drift only scope) — **closed (2026-05-08, 운용역 sign-off)**
- **decision (운용역 승인)**:
  - `relaxed_diagnostic` → `enforcement: telemetry_only` (drift 초과는 quality_status 영향 없음. 값만 telemetry 보존)
  - `review` → `enforcement: warning` (drift threshold 초과 → WARNING)
  - `production` → `enforcement: review_required` (drift threshold 초과 → REVIEW_REQUIRED)
  - **asset drift threshold = 3%, bucket drift threshold = 5%**
- **scope**: **projection drift 만 대상**. product cap / selection fallback drift 는 D-15/D-16/D-17 candidate 로 분리 (정식 등록은 별도 결정).
- **closure 근거** (4 조건 모두 충족):
  1. ✅ projection drift source 가 `long_only_clipping` (ust30 / kr_t10) 으로 설명 가능
  2. ✅ relaxed mode 에서 `bucket_constraint` / `asset_upper_bound` source 발생 0건
  3. ✅ production / review enforcement 운영값 확정 (운용역 승인 2026-05-08)
  4. ✅ selection / product cap drift 가 D-15/D-16/D-17 candidate 로 분리
- **현재 적용 상태**:
  - yaml `tdf_2060.yaml::drift_thresholds.modes` 에 5-mode 매핑 구조화 (production / review_required / review / warning / telemetry_only)
  - `quality.py` DEFAULT 0.03 / 0.05 (Phase B.5+ 운영값 그대로)
  - `taa/projection.py::_classify_projection_drift_source` 7-source taxonomy + `clipping_summary`
  - `portfolio/quality.py::_classify_quality_drift_source` 5-source taxonomy + `drift_clipping_summary`
  - review packet §3.1 Drift source breakdown
- **참조**: `docs/phase_d_d02_drift_closure_brief.md`, `docs/phase_d_d02_signoff_patch_plan.md`.
- **회귀 방어**: `tests/test_phase_d_relaxed.py` 의 13 테스트 (Option A 7 + drift_source 6).
- **승인 코드 변경 없음**: yaml `drift_thresholds` 가 이미 본 정책과 정합. 본 closure 는 status / 본문 갱신만.

### D-03. lookback 정책 (Option C — Hybrid) — **closed (2026-05-08, 운용역 sign-off)**
- **decision (운용역 승인)**: Option C — Hybrid
  - **return / volatility**: `intersection_policy: asset_specific` (자산별 max history. lookback_years=10 은 절단 상한)
  - **correlation**: `intersection_policy: common` (공통 기간 — `dropna(how="any")` 동작 유지)
  - **min_obs**: 12 (Phase B.5+ 운영값 / `SanityThresholds` default 와 정합)
  - **short_history_warning_ratio**: 0.8 (max_obs * 0.8 미만 → review packet warning)
- **scope**: ust30 / BRFUT004 obs=87 같은 짧은 history 자산 **허용**. 단 telemetry / warning 으로 노출.
- **closure 근거** (5 조건 모두 충족):
  1. ✅ lookback policy 옵션 선택 (Option C 채택)
  2. ✅ min_observation threshold 확정 (12)
  3. ✅ ust30 / BRFUT004 짧은 history 허용 (telemetry)
  4. ✅ warning vs review_required 기준 = D-02 enforcement 모드 따름 (relaxed=telemetry_only / review=warning / production=review_required)
  5. ✅ config/test 변경 정리 (yaml 4 line 추가, 코드/test 무변경)
- **DB sanity flag vs review warning 구분**:
  - **DB sanity flag** (hard data integrity): `min_obs=12` 미충족 시 `too_few_observations` flag. 현재 ust30 obs=87 ≥ 12 → flag = []. **hard issue 아님**.
  - **Review / policy warning** (telemetry): `obs < max_obs * 0.8` 시 short-history warning. 현재 ust30 87 < 120*0.8 = 96 → review packet 의 `policy_review_items` 에 표시. **운용역 검토 telemetry**.
  - 두 기준은 서로 모순 아님. 같은 자산이 sanity flag 통과하면서 review warning 대상이 될 수 있음.
- **변경 위치 (적용됨)**:
  - `tdf_engine/config/db_sources.yaml` — `asset_rt_vol.intersection_policy / min_obs`, `corr_matrix.intersection_policy / short_history_warning_ratio` 4 line 추가
- **변경하지 않은 위치 (코드 무변경)**:
  - `db_market_data.py` — 기존 `dropna(how="any")` (corr) 와 자산별 `_monthly_returns` (asset_rt_vol) 동작 그대로
  - `quality.py` / `review.py` — 기존 short_history 휴리스틱 그대로
- **회귀 방어**: pytest 142 passed / 5 skipped / 1 xfailed (yaml 추가 후 무회귀).
- **참조**: `docs/phase_d_d03_lookback_policy_review.md`.

### D-04. `us_treasury_30y` BRFUT004 mapping / fallback policy — **closed (2026-05-08)**
- **current_setting**: BRFUT004 direct mapping
  - `db_dataset_id=201` ('KIS 미국채 30Y TR 지수'), `dataseries_id=33`, blob key `totRtnIndex`
  - `asset_mapping.yaml::us_treasury_30y.db_mapping_mode: direct`
- **decision**: BRFUT004 사용 확정, 추가 proxy 금지
  - 정본 벤치마크 = KIS 미국채 30Y TR 지수 BRFUT004
  - DB 모드(`--source db`)에서 direct mapping을 정본으로 유지
  - **TLT / EDV / USGG10YR 등 사용 금지**
  - BRFUT004 외 다른 지표나 ETF로 자동 fallback 하지 않음
- **fallback_policy**: `no_fallback` / `hard_error`
  - yaml의 `fallback_policy: explicit_proxy_only` 표현은 의미상 `no_silent_fallback` (= 운영자가 명시 지정 없으면 자동 대체 금지, 데이터 부재 시 hard error) 와 동일
  - file 모드(Asset_rt_vol/Corr_mat)에 BRFUT004 row가 없을 경우 **fallback 하지 말고 명시적 ValueError 발생**이 정책상 정답
- **risk_if_wrong**: silent proxy 사용 시 MVO 결과 왜곡 가능 (장기 미국채 듀레이션 특성을 다른 자산이 대체할 수 없음)
- **code_change_required**: 없음. 이미 DB direct mapping 반영됨 (`asset_mapping.yaml`, `db_sources.yaml`, `repositories/db_market_data.py`, `repositories/_blob.py`).
- **note**: file 모드는 BRFUT004 row 부재 시 ValueError 발생. **운영 실행은 `--source db` 권장.** `out/db_etf/`, `out/db_fund/` 산출물이 모두 BRFUT004 direct mapping으로 생성됨.
- **회귀 방어**: `tests/test_config_loader.py::test_us_treasury_30y_explicit_proxy_only`

### D-05. MVO objective ($L$26) — closed
- **결정 완료**: `max_sharpe` 기본 + dispatch 4종 (max_sharpe / utility / min_volatility / max_return_under_risk_limit)
- **회귀 방어**: `tests/test_optimization_objective_dispatch.py`, `optimization/optimizer.py::OBJECTIVE_REGISTRY`
- **추가 검증 시점**: D-08 해소 시 Excel `$L$26` 직접 확인 가능

### D-06. ERR 정의
- **현재 정책**: `err.enabled: false`, placeholder 만 보존
- **상태**: pending_external — Excel 원본 검토 필요
- **변경 위치**: `config/optimization_constraints.yaml`, `OptimizationResult.diagnostics`

### D-07. HY 처리 — closed
- **결정 완료**: `fixed_income` bucket + `risk_asset` flag + `credit` flag
- **회귀 방어**: `tests/test_config_loader.py::test_hy_has_risk_asset_and_credit_flags`

### D-08. Excel DRM 3건 — **closed_with_permanent_limitation (2026-05-08, 운용역 sign-off)**
- **closure type**: `closed_with_permanent_limitation` — 일반 closed 와 구분.
- **운영자 정보 (2026-05-08)**:
  - DRM 보호 xlsx 3건 (`0. 정리 - GlidePath 값.xlsx`, `RegimeAnalysis_2602.xlsx`, `ECI_Neo_202603.xlsx`) 은 **영구 해제 불가**.
  - 핵심 정보는 운영자가 직접 제공 (GlidePath 4 vintage 비중) + 나머지는 기존 file 모드 데이터 (`Advisory/regime_*` + `regimeAnalysis_*`) 가 정본임을 운영자 확인.
- **각 파일별 처리**:
  - `0. 정리 - GlidePath 값.xlsx` → 운영자 직접 정보 (2060=80%/2050=70%/2040=60%/2030=50% 주식 편입비) → `tdf_engine/config/glidepath.yaml` 신설 (reference metadata, enforced=false)
  - `RegimeAnalysis_2602.xlsx` → 기존 `regime_*` + `regimeAnalysis_*` file 의 결합물. 추가 정보 없음. file mode 데이터 = 정본.
  - `ECI_Neo_202603.xlsx` → 동일.
- **permanent limitation (영구 보류 사항)**:
  - **SAA / TAA / Final weights 의 Excel 1:1 parity 검증**: DRM 해제 불가로 영구 waived.
  - **MVO objective Excel `$L$26` 직접 확인**: 동일 사유로 영구 waived (D-05 의 max_sharpe 정책은 그대로 유효).
  - 단 Placement / Velocity / Regime classification parity 는 Phase C.5 에서 이미 PASS (USA region) — 본 limitation 영향 없음.
- **closure 영향**:
  - GlidePath 다중 vintage = `glidepath.yaml` reference metadata 로 보존. 실제 다중 vintage 산출은 후속 Phase.
  - `out/db_etf_relaxed/`, `out/db_fund_relaxed/` 산출의 SAA/TAA/Final weights 는 **Excel 답안지 검증 없이 운용** (운용역이 사용 시 본 limitation 인지 필요).
- **변경 위치 (적용됨)**:
  - `tdf_engine/config/glidepath.yaml` (신설, reference only)
  - `docs/investment_decision_register.md` (status / 본문 / 변경 이력)
  - `HANDOFF.md`, `memory/project_state.md` (분포 / blocker)
  - `docs/source_review/regime_source_review.md` (DRM limitation 명시)
- **변경하지 않은 위치**:
  - `tdf_engine/` 코드 (glidepath.yaml 은 reference. 코드에서 읽지 않음)
  - 기존 `tdf_2060.yaml::strategic_allocation` (equity 0.80 그대로 — glidepath_reference.2060 과 정합)

### D-09. `regimeAnalysis_rt` 정의 — **closed (2026-05-08, 운용역 sign-off)**
- **decision (운용역 확인)**: **`Advisory/regimeAnalysis_rt` 파일 자체가 canonical definition**. 별도 definition 문서 없음.
- **closure 근거**:
  - 운영자 확인 (2026-05-08): regimeAnalysis_rt 의 region / annualization / regime base 에 대한 **별도 정의 자료가 존재하지 않음**.
  - 파일 자체 (file mode 사용 중) = 정본.
- **Phase C.5 xfail 1건 처리**:
  - 기존 사유: "regimeAnalysis_rt 정의 미명시"
  - 갱신 사유: **"외부 Excel parity 답안지 부재 / DRM 해제 불가"** (D-08 limitation 과 동일 근원)
  - xfail 자체는 **유지** (testcase 가 의미 없는 게 아니라 영구 답안지 부재를 reflect)
- **변경 위치 (적용됨)**:
  - `docs/investment_decision_register.md` (status / 본문 / 변경 이력)
  - `HANDOFF.md`, `memory/project_state.md` (분포 / blocker)
  - `docs/golden_answer_validation.md` (xfail 사유 갱신)

### D-10. 자산군 0% 허용 여부 — **closed (2026-05-08)**
- **decision**: 모든 개별 자산군 0% 허용. **음수 비중만 금지** (final portfolio long-only).
- **중간 TAA target 음수**: 발생 가능. projection 으로 0% 로 보정. pre-projection negative 는 telemetry / info warning 으로만 노출.
- **변경 위치**: `config/tdf_2060.yaml` (final_asset_bounds.*.min = 0.0), validator non_negative_ok (post-projection)
- **회귀 방어**: `test_phase_d_relaxed_long_only`, `test_phase_d_relaxed_sum_to_one` (신규)

### D-11. `dm_ex_us_equity` lower bound — **deferred (2026-05-08)**
- **decision**: 현 단계 미적용. TAA target 4% bound 도, final lower bound 도 적용 안 함.
- **재논의 시점**: 자산군별 band 도입 단계 (별도 신규 Decision 항목)
- **변경 위치**: 변경 없음 (config 의 final_asset_bounds.dm_ex_us_equity 는 [0.0, 1.0] 로 완화)

### D-12. `us_value_equity` cap — **deferred (2026-05-08)**
- **decision**: 현 단계 미적용. weight_bounds.max 와 final_asset_bounds.max 모두 [0.0, 1.0] 로 완화.
- **재논의 시점**: 자산군별 band 도입 단계
- **변경 위치**: 변경 없음 (config 완화로 자동 비활성)
- **운영 모니터링**: 자산 쏠림 (예: us_value 50%+) 발생 시 sanity monitoring section 에서 flag

### D-13. `quant_grade_policy` mode — **closed (2026-05-08, 운용역 sign-off)**
- **decision (운용역 승인)**: 현행 유지. ETF=`hard_filter`, Fund=`score_penalty`. 추가 제약 도입 안 함.
- **근거**: relaxed concentration 의 1차 원인은 quant grade 정책이 아닌 자산군 쏠림 (D-11/D-12 deferred 영역). 변경 시 후보 풀 / fallback 빈도 변동 위험 → production 전환 전 추가 변동 = 위험.
- **현재 효과** (참고): ETF hard_filter → 64 후보 제외. Fund score_penalty → 117 후보에 grade penalty.
- **변경 위치**: 없음 (`config/universe_filter.yaml::quant_grade_policy.{etf,fund}.mode` 그대로).
- **참조**: `docs/phase_e_d13_d14_policy_brief.md`.

### D-14. 운용사 concentration cap — **deferred (2026-05-08, 운용역 sign-off)**
- **decision (운용역 승인)**: 현 단계 **제약 도입 안 함**. cap / soft warning threshold 모두 미도입. **monitoring telemetry only**.
- **근거**:
  - 현재 concentration 1차 원인 = `relaxed_diagnostic` mode 의 자산군 쏠림 (us_growth 70.6%) + product cap binding 부산물. **manager cap 부재가 원인 아님**.
  - manager hard cap 또는 soft warning 만 먼저 도입 → 진짜 risk (자산 쏠림) 가림 + 상품 선정 왜곡 가능 → 비추천.
  - 일관 정책: "현 단계는 제약을 붙이는 단계가 아니라 relaxed 결과를 관찰하는 단계. cap / threshold 는 후속 Phase 에서 도입."
- **현재 default 보존** (참고, enforce 안 함): `universe_filter.yaml::*.product_constraints.single_manager_max_weight` (ETF=0.60 / Fund=0.50). yaml 변경 없음.
- **현재 산출 manager concentration** (telemetry only, fail 아님):
  - ETF: 미래에셋 25.73% / 삼성 23.69% / 한투 23.09% / 타임폴리오 20.00% (cap 60% 미발동)
  - Fund: KB 30.00% / 한투 27.40% / 삼성 20.30% / AB 20.30% (cap 50% 미발동, KB 30% 는 product cap 부산물)
- **재검토 시점**: 후속 Phase (E-3 자산군 band 재도입 여부 결정 후 또는 production dry-run 결과 누적 후).
- **변경 위치**: 없음 (yaml / 코드 / tests 모두 무변경).
- **참조**: `docs/phase_e_d13_d14_policy_brief.md`, `docs/phase_d_concentration_brief.md`.

---

## 3. 결정 흐름

```
[D-08 해소] → Phase C.5 SKIP 5건 중 일부 closed → SAA/TAA/Final parity 검증 활성
[D-09 해소] → Phase C.5 xfail 1건 closed
[D-05 closed]  ← (D-08 해소 시 Excel $L$26 직접 검증 가능)
[D-07 closed]  ← (이미 적용)
[D-04 closed]  ← (BRFUT004 direct mapping + 추가 proxy 금지 — 2026-05-08)

[D-10 / D-11 / D-12 결정] → D-01 final_asset_bounds 운영값 확정 가능
[D-02 / D-03 결정] → quality / lookback 정책 적용 가능
[D-13 / D-14 결정] → universe_filter 정책 적용 가능

[D-01 운영값 적용 + 운용역 사인] → Phase D 종료
```

---

## 4. Phase D 작업 분류 (재기록 — 자세한 표는 phase_d_declaration.md §4)

### 4.1 결정 없이 진행 가능 (`P-` 접두)

- P-01 문서 정합성 보정
- P-02 본 register 갱신
- P-03 review packet 표현 보강 (산출 동일, 표현만)
- P-04 운영 절차 문서화 (`docs/operations_runbook.md` 신설 가능)
- P-05 추가 sanity 진단 (값 변경 없음)

### 4.2 결정 후 진행 (`A`~`J`)

- A `final_asset_bounds` 운영값 확정 ← D-10/11/12
- B ust30/kr_t10 정책 ← D-10
- C projection drift 임계 변경 ← D-02
- D lookback 정책 ← D-03
- E DB σ/μ 산출 기준 ← D-03
- F `final_asset_bounds` hard enforce ← D-01
- G selection score 보존 (운영자)
- H regime DB 연결 (운영자)
- I GlidePath 다중 vintage ← D-08
- J HTML/Dash reporting (운영자)

---

## 5. 변경 이력

| 일자 | 변경 | 담당 |
|---|---|---|
| 2026-05-08 | 신설. 14개 항목 초안. D-05 / D-07 closed 기록. | (Phase D 진입) |
| 2026-05-08 | D-04 `us_treasury_30y` proxy 정책 closed. BRFUT004 direct mapping 확정, 추가 proxy 금지, file 모드 hard error 정책 명시. 코드 변경 없음. | (사용자 결정) |
| 2026-05-08 | 분포 카운트 정정: `open 9` → `open 8` (D-04 closure 이전부터 산정 오류였음, 합계 14 일치). | (정합성 보정) |
| 2026-05-08 | D-04 제목 변경: `proxy 정책` → `BRFUT004 mapping / fallback policy`. 의미 명확화 (D-04는 BRFUT004 direct mapping/fallback policy. ust30 zero/near bound는 D-10). | (D.2 review revise) |
| 2026-05-08 | review packet warning→D-ID heuristic 개선: substring 우선순위 → predicate 함수. ust30 final 0%·near bound·negative 는 D-10, BRFUT004/proxy/file mode 만 D-04. lookback/obs는 D-03. | (D.2 review revise, reporting only) |
| 2026-05-08 | **Phase D relaxed constraints 적용**: D-01 closed (재정의: hard constraint = long-only + sum-to-100% + 데이터 무결성), D-02 pending_rerun, D-10 closed, D-11/D-12 deferred. status 신규 도입: `pending_rerun`, `deferred`. 분포: open 8/3, pe 3/3, pr 0/1, dfd 0/2, closed 3/5. blocker 8건 → 4건. config 3종 완화 + 코드 변경 + tests 갱신 + 신규 4 + relaxed rerun. | (운용역 정책 확정) |
| 2026-05-08 | **Operating mode = `relaxed_diagnostic`** 명시 (yaml `operating_mode` 신설 + review packet banner). relaxed 산출은 production 아닌 diagnostic baseline. D-13/D-14 brief 신설(`docs/phase_d_concentration_brief.md`). D-02 telemetry/threshold 구조 재검토 제안(`docs/phase_d_drift_telemetry_proposal.md`, 변경안만). | (D 보정) |
| 2026-05-08 | **D-02 Option A 적용**: `quality.py` DEFAULT 0.03/0.05 복원, yaml `drift_thresholds.modes` 도입, `evaluate_quality(enforcement)` 신규 인자 (production / review_required / review / warning / telemetry_only 5 mode). relaxed_diagnostic → telemetry_only 매핑. drift exceed 시 quality_status 분기는 enforcement 모드에 따라. drift 값 자체는 모든 모드에서 telemetry 보존. tests 7건 신규. pytest 129 → 136. | (D-02 구조화) |
| 2026-05-08 | **D-02 drift_source 분류 적용**: `taa/projection.py` 에 7-source taxonomy + `clipping_summary` (long_only_clipping / redistribution / bucket_constraint / asset_upper_bound / asset_lower_bound / normalization / none). `portfolio/quality.py` 에 5-source taxonomy + `drift_clipping_summary` (product_cap_clipping_outflow / fallback_redistribution_inflow / selection_shortfall / selection_overflow / none). review packet §3.1 Drift source breakdown 신설. relaxed ETF: projection drift 3% = redistribution from long_only clipping (ust30/kr_t10), quality drift 10.60% = product_cap_clipping at us_growth (cap 20% × 3 상품). bucket [0,1] no-op 케이스 false-positive 차단. tests 6건 신규. pytest 136 → 142. **D-02 status pending_rerun 유지** (closure 위해 drift_source 분포의 반복성 검증 필요). | (D-02 telemetry 보강) |
| 2026-05-08 | **D-02 closed by 운용역 sign-off**: 정책 = relaxed=telemetry_only / review=warning / production=review_required / asset drift 3% / bucket drift 5% / scope=projection drift only. product cap drift 는 D-15/D-16/D-17 candidate 로 분리. closure 4 조건 모두 충족. status `pending_rerun → closed`, 분포 `pr 1→0 / closed 5→6`, blocker 4→3 (D-03/D-08/D-09). 코드/config/tests/out 무변경. | (운용역 승인) |
| 2026-05-08 | **D-03 closed by 운용역 sign-off**: Option C — Hybrid lookback policy. return/vol = asset_specific, corr = common intersection. min_obs=12, short_history_warning_ratio=0.8. ust30 obs=87 허용 (telemetry). status `open → closed`, 분포 `open 3→2 / closed 6→7`, blocker 3→2 (D-08/D-09). yaml 4 line 추가 (db_sources.yaml). 코드/tests/out 무변경. | (운용역 승인) |
| 2026-05-08 | **D-08 closed_with_permanent_limitation by 운용역 sign-off**: DRM 3건 영구 해제 불가. 운영자 직접 정보 (GlidePath 4 vintage) + 기존 file 모드 데이터로 대체 closure. SAA/TAA/Final 1:1 parity 검증 영구 waived. `tdf_engine/config/glidepath.yaml` 신설 (reference metadata, enforced=false). 분포 `pe 3→2 / closed 7→8`. **D-09 closed by 운용역 sign-off**: regimeAnalysis_rt 파일 자체가 canonical definition. 별도 자료 없음. Phase C.5 xfail 사유 갱신 (정의 미명시 → DRM 해제 불가). 분포 `pe 2→1 / closed 8→9`. **Phase D register blocker = 0 (8→4→3→2→0)**. 단 production-ready 아님. relaxed_diagnostic mode 유지. 코드/tests/out/기존 config policy 값 무변경. | (운용역 승인 — 옵션 A 동시 closure) |
| 2026-05-08 | **D-13 closed by 운용역 sign-off**: 현행 유지 (ETF=hard_filter / Fund=score_penalty). 추가 제약 도입 안 함. **D-14 deferred by 운용역 sign-off**: manager concentration cap / soft warning threshold 모두 미도입. monitoring telemetry only. 후속 Phase 에서 제약 도입 여부 재검토. 정정: 직전 turn 의 Option B (soft warning ETF 50% / Fund 40%) 는 현 정책 ("제약 도입 안 함, monitoring 만") 과 부합하지 않아 채택하지 않음. 분포 `open 2→0 / deferred 2→3 / closed 9→10`. **yaml / 코드 / tests / out 모두 무변경**. | (운용역 정정 sign-off) |
