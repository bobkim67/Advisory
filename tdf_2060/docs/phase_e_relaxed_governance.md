# Phase E-2 — Relaxed Diagnostic Governance

작성일: 2026-05-08. **E-2 (relaxed governance / sign-off flow)** — Phase E 진입 전 단계.
relaxed_diagnostic mode 산출물의 검토 / 승인 / 보류 / 재실행 절차를 영구 record.

> **Phase D completed register-blocker resolution only.**
> **This does not mean production readiness.**
> **The engine remains in relaxed_diagnostic mode.**
>
> 본 문서는 relaxed output 이 production portfolio 처럼 자동 사용되지 않도록
> governance 절차를 영구 잠그는 record. Phase E-1 (production 전환) 진입 전 필수 단계.

---

## 1. Purpose

| 측면 | 내용 |
|---|---|
| **relaxed_diagnostic output 의 위상** | production portfolio **아님**. diagnostic baseline only. |
| **목적** | optimizer / TAA / selection / fallback 단계의 쏠림 / 한계 / 정책 영향을 **진단**. production 전 정책 결정의 근거 자료. |
| **금지 사항** | (a) 자동 production 적용. (b) 고객 제안서 / 자료에 직접 사용. (c) 운용역 sign-off 없는 재배포. |
| **production 전환 조건** | 본 governance 의 sign-off → 운용역 정책 결정 (D-11/12/13/14 등) → Phase E-1 production 설계 → 운용역 final approval. |

### 1.1 영구 핵심 문구 (인용 필수)

본 문서를 인용·요약하는 모든 후속 문서 / handoff 에 다음을 그대로 유지:

> "Phase D completed register-blocker resolution only.
> This does not mean production readiness.
> The engine remains in relaxed_diagnostic mode."

---

## 2. Scope

### 2.1 적용 대상 (governance 필요)

| 산출물 / 위치 | 종류 |
|---|---|
| `out/db_etf_relaxed/portfolio_etf_*.{csv,json}` | relaxed ETF portfolio (asset / product weights) |
| `out/db_etf_relaxed/review_etf_*.md` | enhanced review packet (banner + §3.1 + §6) |
| `out/db_fund_relaxed/portfolio_fund_*.{csv,json}` | relaxed Fund portfolio |
| `out/db_fund_relaxed/review_fund_*.md` | 동 |
| `out/db_review_relaxed/comparison_etf_vs_fund_*.md` | ETF/Fund 비교 리포트 |
| 위 모든 파일을 `--source db --as-of-date <YYYY-MM-DD>` 로 재산출한 산출물 | 모든 후속 relaxed run |
| `tdf_engine/tools/render_review.py` 로 재렌더한 markdown | 동 |

### 2.2 비적용 대상 (별도 governance 또는 절대 금지)

| 영역 | 처리 |
|---|---|
| **실제 운용 포트폴리오 / production batch** | 본 governance 적용 **금지**. relaxed 산출 자체를 production 으로 사용 금지. Phase E-1 (production 모드 설계) 후 별도 governance 적용. |
| **고객 제안서 / 마케팅 자료** | relaxed 산출 직접 인용 **금지**. production sign-off 후 production 산출만 사용. |
| **regulatory / compliance 보고** | relaxed 산출 직접 사용 **금지**. |
| **historical record / archive** | relaxed 산출은 diagnostic record 로 보존 가능 (sign-off 후). 단 production 으로 reclassify 금지. |

### 2.3 산출물 식별 (governance 적용 자동 감지)

다음 중 하나라도 충족하면 governance 적용 대상:
- 산출물 파일 경로에 `_relaxed` 또는 `db_review_relaxed` 포함
- `portfolio_*.json::operating_mode_banner.mode == "relaxed_diagnostic"`
- `review_*.md` 헤더에 `RELAXED DIAGNOSTIC RUN — NOT a production portfolio` banner 존재
- `tdf_2060.yaml::operating_mode == "relaxed_diagnostic"` 인 환경에서 산출

---

## 3. Review Roles

| 역할 | 책임 | 권한 |
|---|---|---|
| **Engine owner** | 엔진 코드 / config / 산출 파이프라인 유지. relaxed run 실행 (CLI). 산출물 무결성 확인 (long-only / sum=1 / DB / BRFUT004). | rerun trigger. config 변경안 제안. |
| **Portfolio manager (운용역)** | relaxed 산출의 정책 정합성 검토. concentration / sanity range / 정책 sign-off. 운용 의도와의 부합 판단. | approve / request_rerun / request_policy_change / reject. policy decision 권한. |
| **Data operator** | DB 데이터 (BRFUT004 / regime / 시계열) 무결성. as_of_date 결정. file mode 데이터 갱신. | DB 이슈 시 escalation. as_of_date 변경 권한. |
| **Reviewer** (선택, 외부 검토자) | 산출 logic / governance 절차 준수 여부 외부 검토. compliance / risk 관점. | 의견 제시. binding decision 없음 (운용역이 최종). |

### 3.1 Role 별 review checkpoint

| 단계 | 책임 role | 산출 |
|---|---|---|
| (1) relaxed run 실행 | Engine owner | csv / json / md 3종 |
| (2) 산출 무결성 확인 | Engine owner | "기본 hard constraint 통과" 보고 (long-only / sum / DB / convergence) |
| (3) 데이터 무결성 확인 | Data operator | DB / as_of_date / BRFUT004 / regime data 정상 보고 |
| (4) 정책 정합성 검토 | Portfolio manager | review packet §0~§9 검토 + sanity range / concentration 평가 |
| (5) Decision 결정 | Portfolio manager | §5 의 4개 outcome 중 하나 선택 |
| (6) (선택) 외부 검토 | Reviewer | 의견 제출. 운용역 최종 결정에 반영 |

---

## 4. Review Checklist

운용역이 relaxed 산출 검토 시 **필수 확인** 항목. review packet `§0` (Executive Summary) ~ `§9` (Reviewer Checklist) 와 정합.

### 4.1 Hard constraint 통과 (모두 ✓ 필수)

| # | 항목 | 확인 위치 | pass 기준 |
|---|---|---|---|
| H-1 | **long-only** | review §1, §3.1(b) qual drift, validation issues | asset/product 모든 weight ≥ 0 (negative count = 0) |
| H-2 | **sum-to-100%** | review §1, §0 | asset_weight_sum ≈ 1.0 (atol 1e-4) ∧ product_weight_sum ≈ 1.0 |
| H-3 | **DB source 정상** | review §7, diagnostics.db_source | datasets_loaded = 9 (or expected count), datasets_missing = [], no `too_few_observations` flag |
| H-4 | **BRFUT004 direct mapping 정상** | review §7, db_sources.yaml::us_treasury_30y | dataset_id=201, blob_key=totRtnIndex, ust30 obs 시계열 정상 |
| H-5 | **NaN / invalid return data 없음** | diagnostics.db_source.warnings | 빈 배열 또는 explicit NaN 처리 명시 |
| H-6 | **optimizer / projection convergence** | diagnostics.saa_diagnostics.solver_status, taa_diagnostics.taa_feasibility.projection_success | solver_status=0, projection_success=True |

위 6 항목 중 **하나라도 실패** 시 → §6 escalation `reject_as_invalid` 또는 `request_rerun`.

### 4.2 Drift / Quality 분석 (telemetry 검토)

| # | 항목 | 확인 위치 | 검토 포인트 |
|---|---|---|---|
| D-1 | **projection drift source** | review §3.1 (a) | primary source 가 `long_only_clipping` / `redistribution_from_long_only_clipping` 인지. `bucket_constraint` / `asset_upper_bound` 가 발생했다면 의외 (relaxed mode 에서 0건 기대) |
| D-2 | **quality / selection drift source** | review §3.1 (b) | primary source 가 `product_cap_clipping_outflow` / `fallback_redistribution_inflow` 인지. selection_shortfall / selection_overflow 비중. |
| D-3 | **drift_source = unknown / unexplained** | §3.1 자산별 표 | 모든 자산이 알려진 source 분류 안에 들어가는지 |
| D-4 | **enforcement mode = telemetry_only 적용** | review §6 | "telemetry_only" 표기 확인. drift exceed 가 quality_status 에 영향 없음 검증 |

### 4.3 Sanity / Concentration monitoring

| # | 항목 | 확인 위치 | sanity range / 임계 |
|---|---|---|---|
| S-1 | **equity bucket sanity** | review §2.1 | [60%, 95%] 내 ⚠ flag 없으면 ✓. 이탈 시 monitoring flag (fail 아님). |
| S-2 | **fixed_income bucket sanity** | review §2.1 | [5%, 40%] 내 |
| S-3 | **자산군 concentration** | review §2 자산배분 표 | 단일 자산군 70%+ 시 monitoring flag (현재 us_growth 케이스) |
| S-4 | **product concentration** | review §4 + comparison §4 | top-1 product weight, top-5 합계. ETF=20% × 3 / Fund=30% 패턴 정상 |
| S-5 | **manager concentration** | comparison §5 | top-1 manager 비중. ETF cap 60% / Fund cap 50% 미달 여부. (D-14 영역) |
| S-6 | **short-history telemetry** | review §8 / policy_review_items | obs < max_obs * 0.8 자산 (현재 ust30 obs=87 < 96) → telemetry warning. fail 아님. |

### 4.4 정책 정합성

| # | 항목 | 확인 위치 | 기준 |
|---|---|---|---|
| P-1 | **TAA rule = prototype heuristic overlay** | review §1, comparison header banner | 본 결과의 TAA tilt 가 final quantitative TAA 모델 결과가 아님을 명시 / 인지 |
| P-2 | **operating_mode = relaxed_diagnostic** | review header banner | "RELAXED DIAGNOSTIC RUN — NOT a production portfolio" 5줄 disclaimer 확인 |
| P-3 | **D-08 limitation 인지** | (운용역 머릿속) | DRM 영구 해제 불가 → SAA/TAA/Final Excel 1:1 parity 영구 waived. 본 산출은 검증되지 않은 결과. |
| P-4 | **glidepath.yaml = reference only** | tdf_engine/config/glidepath.yaml | 4 vintage metadata. 코드 미사용. 다중 vintage 산출은 후속 Phase. |
| P-5 | **regimeAnalysis_rt = canonical file** | (운용역 머릿속) | 별도 정의 자료 영구 부재. 파일 자체가 정본. |

---

## 5. Decision Outcome (4종)

운용역이 본 review checklist 검토 후 **반드시 4 종 중 하나** 결정.

### 5.1 `approve_for_diagnostic_record`
- **의미**: 본 산출을 **diagnostic record** 로 승인. production 자료 아님.
- **조건**: §4 의 모든 hard constraint (H-1 ~ H-6) 통과 + sanity 이슈가 운용역 검토 후 수용 가능 + 정책 정합성 (P-1 ~ P-5) 인지 완료.
- **후속**:
  - 산출물 파일 그대로 archive (`out/db_*_relaxed/` 보존).
  - `docs/governance_log/` (또는 운영자 지정 위치) 에 sign-off 기록 (§7 template).
  - **production 자동 적용 금지**. 별도 Phase E-1 (production 전환) 시점까지 보류.

### 5.2 `request_rerun`
- **의미**: 산출 자체에는 정책 위반 / 위험 신호가 없으나 데이터 / 시점 / 환경 차이로 재실행 필요.
- **조건**: hard constraint 통과 but as_of_date 변경 / DB 갱신 / regime label 변경 등 외부 입력 변동.
- **후속**:
  - Engine owner 가 새 as_of_date 또는 새 DB 시점으로 `tools/build_portfolio.py` 재실행.
  - 새 산출물에 대해 본 governance 처음부터 다시 적용.
  - 이전 산출물은 archive (rerun 사유 기록).

### 5.3 `request_policy_change`
- **의미**: 산출은 정상이나 **정책 자체 변경 필요**. 자산군 cap / TAA tilt / quant_grade / manager cap 등.
- **조건**: hard constraint 통과 + concentration / drift 가 운용역 의도와 어긋남 + 정책 변경으로 해소 가능.
- **후속**:
  - 운용역이 변경할 정책을 명시 (D-11 / D-12 reactivate / D-13 quant grade / D-14 manager cap / 신규 candidate 등).
  - Decision Register 갱신 (status 변경 또는 candidate 정식 등록).
  - config / 코드 변경 후 재산출. 본 governance 처음부터 다시 적용.

### 5.4 `reject_as_invalid`
- **의미**: 산출이 hard constraint / 데이터 무결성 위반. 사용 불가.
- **조건**: §4 의 H-1 ~ H-6 중 **하나라도 실패** OR drift_source = unknown OR optimizer / projection convergence 실패 OR DB / BRFUT004 / NaN 이슈.
- **후속**:
  - 즉시 escalation (§6).
  - 산출물 사용 / 인용 / archive 금지 (또는 `rejected/` 격리 폴더 보존).
  - Engine owner 가 원인 진단 → 코드 / config / 데이터 수정 → 재산출 → 본 governance 처음부터 다시.
  - Phase D completion record 에 reject 사례 기록 (재발 방지).

### 5.5 Outcome 결정 매트릭스

| Hard pass | Sanity 이슈 | 정책 어긋남 | 데이터 / 시점 변경 필요 | → outcome |
|:---:|:---:|:---:|:---:|---|
| ✓ | 없음 또는 수용 | 없음 | 없음 | `approve_for_diagnostic_record` |
| ✓ | 무관 | 무관 | 있음 | `request_rerun` |
| ✓ | 무관 | 있음 | 무관 | `request_policy_change` |
| ✗ | — | — | — | `reject_as_invalid` |

---

## 6. Escalation Rules

다음 상황 발생 시 운용역 review_required 또는 rerun_required 로 자동 escalation. **자동 approve 절대 금지**.

### 6.1 즉시 reject (`reject_as_invalid` 후보)

| 트리거 | 검출 위치 |
|---|---|
| **negative weight 발생** (asset 또는 product) | validator.py issues, review §1 validation_issues_count > 0 |
| **total weight ≠ 1.0** (atol 1e-4 초과) | validator.py issues |
| **DB source missing** | diagnostics.db_source.datasets_missing 비어있지 않음 |
| **BRFUT004 mapping failure** | db_sources.yaml::us_treasury_30y 매핑 실패 (ValueError) |
| **NaN / invalid return data** | diagnostics.db_source.warnings 에 NaN 관련 / suspicious_flags 에 `extreme_return` / `zero_volatility` |
| **optimizer convergence failure** | saa_diagnostics.solver_status ≠ 0 |
| **projection convergence failure** | taa_feasibility.projection_success = False |

### 6.2 review_required (`request_rerun` 또는 `request_policy_change` 후보)

| 트리거 | 검출 위치 | 권장 outcome |
|---|---|---|
| **equity bucket > 95% 또는 < 60%** | review §2.1 sanity range 이탈 | request_policy_change (자산군 band 도입) |
| **fixed_income bucket > 40% 또는 < 5%** | 동 | 동 |
| **단일 자산군 > 80%** (예: us_growth 70.6% 같은 경계) | review §2 자산배분 표 | request_policy_change (D-12 reactivate or D-17 candidate) |
| **단일 product > 30%** | review §4 + comparison §4 | request_policy_change (D-16 candidate) |
| **단일 manager > 50% (Fund) / > 60% (ETF)** | comparison §5 | request_policy_change (D-14) |
| **drift_source = unknown / normalization** | review §3.1 자산별 표 | request_rerun + Engine owner 진단 |
| **product_cap_clipping_outflow 발생** | review §3.1 (b) | request_policy_change (D-15 / D-16) |
| **fallback_redistribution_inflow > 5%p** (단일 자산) | review §3.1 (b) | 동 |
| **as_of_date 가 6개월 초과 stale** | diagnostics.db_source.sanity 의 stale_data flag | request_rerun |
| **regime label 이 직전 산출 대비 변경** | (별도 추적) | request_rerun + 운용역 정책 정합성 검토 |

### 6.3 informational (escalation 아님, 단 sign-off 시 명시 필요)

| 트리거 | 처리 |
|---|---|
| **short_history telemetry** (obs < max * 0.8) | review §8 표기. 운용역이 "ust30 obs=87 인지 후 수용" 명시 |
| **TAA tilt = prototype heuristic** | banner / §1 표기 확인 |
| **D-08 limitation** (DRM 영구 해제 불가) | governance log 에 매번 명시 |

---

## 7. Sign-off Template

운용역이 outcome 결정 후 **그대로 인용** 가능한 표준 문구. governance log 또는 운영 시스템에 기록.

### 7.1 `approve_for_diagnostic_record` 표준 sign-off

```
─────────────────────────────────────────────────────────────────────────
RELAXED DIAGNOSTIC SIGN-OFF — APPROVE FOR DIAGNOSTIC RECORD

산출물:
  - out/db_etf_relaxed/portfolio_etf_<date>.{csv,json,md}
  - out/db_fund_relaxed/portfolio_fund_<date>.{csv,json,md}
  - out/db_review_relaxed/comparison_etf_vs_fund_<date>.md
as_of_date: <YYYY-MM-DD>
operating_mode: relaxed_diagnostic

본 relaxed_diagnostic 산출은 production portfolio 가 아니라 진단용 결과로
확인했습니다. long-only / sum-to-100% / data integrity (BRFUT004 mapping
포함) / optimizer · projection convergence 를 모두 확인했으며,
equity / fixed_income bucket 및 자산군 / product / manager concentration
항목은 monitoring 대상으로 기록합니다.

본 결과를 diagnostic record 로 승인합니다.
production 적용 또는 고객 자료 사용 금지를 동의합니다.

확인 사항 (모두 인지 완료):
  ✓ Phase D completed register-blocker resolution only (production-ready 아님)
  ✓ engine 은 relaxed_diagnostic mode 로 산출
  ✓ TAA rule = prototype operator-defined heuristic overlay (NOT final quantitative)
  ✓ D-08 limitation: DRM 3 xlsx 영구 해제 불가 → SAA/TAA/Final Excel 1:1 parity 영구 waived
  ✓ regimeAnalysis_rt = 파일 자체가 canonical definition

monitoring 기록 항목:
  - equity bucket: ____% (sanity [60-95]% 내/외 — 사유 ____)
  - 최대 자산군 비중: ____ ____% (단일 자산군 monitoring)
  - 최대 운용사 비중: ____ ____% (D-14 monitoring)
  - max_abs_projection_drift: ____% (long_only_clipping = ____)
  - max_abs_asset_weight_drift: ____% (product_cap_clipping_outflow = ____)
  - short-history: ust30 obs=87 (수용 / 보류)

추가 의견: ____________

승인일: ____________
운용역: ____________ (서명 / 시스템 ID)
─────────────────────────────────────────────────────────────────────────
```

### 7.2 `request_rerun` template

```
RELAXED DIAGNOSTIC SIGN-OFF — REQUEST RERUN

원인:
  ☐ as_of_date 변경 (current: ____, target: ____)
  ☐ DB 데이터 갱신 (지표: ____)
  ☐ regime label 변경 (이전: ____ → 현재: ____)
  ☐ 기타: ____

후속:
  - Engine owner 에게 rerun 요청
  - 새 산출물에 대해 본 governance 처음부터 다시 적용
  - 이전 산출물은 archive (사유: ____)
```

### 7.3 `request_policy_change` template

```
RELAXED DIAGNOSTIC SIGN-OFF — REQUEST POLICY CHANGE

변경 대상 정책:
  ☐ D-11 dm_ex_us lower bound (현재 deferred → reactivate?)
  ☐ D-12 us_value cap (현재 deferred → reactivate?)
  ☐ D-13 quant_grade_policy mode
  ☐ D-14 manager concentration cap
  ☐ D-15 candidate (asset target vs product allocation drift) 정식 등록?
  ☐ D-16 candidate (product single cap) 정식 등록?
  ☐ D-17 candidate (asset concentration monitoring) 정식 등록?
  ☐ 기타: ____

근거 (review packet 참조):
  ____

후속:
  - Decision Register 갱신
  - config / 코드 변경 (Engine owner)
  - 재산출 후 본 governance 처음부터 다시
```

### 7.4 `reject_as_invalid` template

```
RELAXED DIAGNOSTIC SIGN-OFF — REJECT AS INVALID

위반 사항:
  ☐ negative weight 발생 (위치: ____)
  ☐ total weight ≠ 1.0 (값: ____)
  ☐ DB source missing (자산: ____)
  ☐ BRFUT004 mapping failure
  ☐ NaN / invalid return data (자산: ____)
  ☐ optimizer convergence failure
  ☐ projection convergence failure
  ☐ drift_source = unknown / normalization (자산: ____)
  ☐ 기타: ____

후속:
  - 산출물 사용 / 인용 / archive 금지 (rejected/ 격리)
  - Engine owner 에게 즉시 escalation
  - 원인 진단 → 코드 / config / 데이터 수정 → 재산출
  - Phase D completion record 에 reject 사례 기록
```

---

## 8. Phase E 후보 연결

본 governance 가 Phase E 의 다른 후보와 어떻게 연결되는지 정리.

### 8.1 E-1 → Production Mode 전환 설계

본 governance (E-2) 의 sign-off flow 는 **E-1 진입의 전제 조건**.

- E-2 sign-off 가 일정 기간 (예: 3개월) `approve_for_diagnostic_record` 누적
- 누적된 sign-off 결과로 운용역이 production 정책 결정 (D-11 / D-12 reactivate, D-13 / D-14 운영값, D-15~17 정식 등록)
- 결정 결과를 yaml `operating_mode: relaxed_diagnostic → review → production` 단계 이행
- E-1 production governance 는 본 E-2 보다 더 strict (예: hard enforce, drift exceed → review_required)

### 8.2 E-3 → Asset Band 재도입 (D-11 / D-12)

본 governance §5.3 `request_policy_change` outcome 의 후속.

- relaxed sign-off 누적에서 자산군 쏠림 (us_growth 70%+, dm_ex_us 0% 등) 이 운용역 의도와 어긋남 확인
- D-11 (dm_ex_us lower bound) / D-12 (us_value cap) reactivate 결정
- yaml `final_asset_bounds` 의 `_reference_only` 값을 active 로 이동 → production 단계 진입 시 enforce

### 8.3 E-4 → D-13 / D-14 Policy

본 governance §6.2 의 manager / product concentration 트리거가 수개월 누적되면 E-4 진입.

- D-13 quant_grade_policy mode (ETF=hard_filter / Fund=score_penalty 유지 / 통일 / monitoring_only 등)
- D-14 manager concentration cap (현재 ETF 60% / Fund 50% — monitoring vs hard cap)
- 본 governance §7.3 `request_policy_change` template 의 D-13 / D-14 체크박스 결과를 모아 정식 결정

### 8.4 E-5 → Product Cap / Fallback Drift Policy (D-15 / D-16 / D-17 정식 등록)

본 governance §6.2 의 `product_cap_clipping_outflow` / `fallback_redistribution_inflow` 트리거가 일정 빈도로 발생하면 E-5 진입.

- D-15 candidate (asset target vs product allocation drift) 정식 등록
- D-16 candidate (product single cap policy) 정식 등록
- D-17 candidate (asset concentration monitoring) 정식 등록
- 정식 등록 시 Decision Register total count 14 → 17 갱신 + status distribution 갱신
- 본 governance §7.3 의 candidate 체크박스 결과를 근거로 사용

### 8.5 연결 흐름도

```
relaxed_diagnostic 산출
        ↓
  E-2 governance 적용 (본 문서)
        ↓
  운용역 sign-off (4 outcomes)
        ↓
  ┌─────────────┬──────────────────┬──────────────────────┐
  ↓             ↓                  ↓                      ↓
approve     request_rerun    request_policy_change   reject_as_invalid
diagnostic                          ↓                      ↓
record                       ┌──────┼──────┐         immediate fix
                             ↓      ↓      ↓               +
                            E-3    E-4    E-5         engine debug
                          (band)  (D-13/  (D-15-17
                                  D-14)   formal)
                                            ↓
                       누적 sign-off 결과 + 정책 결정
                                ↓
                      E-1 Production Mode 전환 설계
                                ↓
                      Phase E production governance
                          (별도 문서, E-2 보다 strict)
```

---

## 9. 본 문서 변경 범위

| 영역 | 변경 |
|---|:---:|
| `tdf_engine/` 코드 | ✗ 무변경 |
| `tdf_engine/config/*.yaml` | ✗ 무변경 |
| `tests/` | ✗ 무변경 |
| `out/` 산출물 | ✗ 무변경 |
| `docs/investment_decision_register.md` status / count | ✗ 무변경 |
| Decision Register total count (14) | ✗ 무변경 |
| 본 문서 신설 | ✓ `docs/phase_e_relaxed_governance.md` |

pytest: `142 passed, 5 skipped, 1 xfailed` (sanity 차원, 본 문서 작성 영향 없음).

---

## 10. 한 줄 요약

> **E-2 = relaxed_diagnostic 산출 governance. 4 outcomes (approve / request_rerun /
> request_policy_change / reject) + escalation rules + sign-off template.
> 자동 production 적용 금지. E-1 (production 전환) 진입 전 누적 sign-off 가 정책 결정의 근거.
> Phase D 의 `register blocker = 0 ≠ production-ready` 원칙 영구 강제.**
