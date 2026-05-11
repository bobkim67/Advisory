# Phase E — Relaxed Run Governance Log Template

작성일: 2026-05-08. **E-2 governance** 의 sign-off 결과를 누적 기록하기 위한 표준 양식.
본 문서는 template 정의용. 실제 run 기록은 본 template 을 복제하여 생성한다.

> **Phase D completed register-blocker resolution only.**
> **This does not mean production readiness.**
> **The engine remains in relaxed_diagnostic mode.**

> 본 template 은 relaxed_diagnostic 산출물의 누적 검토 / 승인 / 보류 기록을 위한 양식이다.
> Decision Register total count (14) / status / candidate 정식 등록 / production 전환은 본 template 과 무관하며 영구 변경 없음.

---

## 0. 사용 방법

1. 본 template 파일을 그대로 복사하여 `docs/governance_log/relaxed_run_<as_of_date>_<etf|fund>.md` 형식으로 저장.
2. §2 Run Metadata 부터 §8 Sign-off Template 까지 해당 run 의 실제 값으로 채움.
3. 운용역 sign-off 후 archive. 산출물 (`out/db_*_relaxed/`) 은 그대로 보존.
4. **본 template 자체는 수정하지 않음**. 양식 변경 필요 시 별도 Decision 항목으로 등록 후 갱신.
5. 누적된 log 는 후속 Phase E-1 (production 전환) 결정의 참고 자료로만 사용. 자동 전환 근거 아님.

---

## 1. Purpose

| 측면 | 내용 |
|---|---|
| **relaxed_diagnostic run 의 위상** | production portfolio **아님**. diagnostic baseline only. |
| **목적** | optimizer / TAA / selection / fallback 단계의 쏠림 / 한계 / 정책 영향을 **관찰** 하고 누적 기록. |
| **사용처** | 후속 Phase E-1 (production 전환) / E-3 (asset band) / E-4 (D-13/D-14) / E-5 (D-15/D-16/D-17) 정책 결정의 **참고 자료**. |
| **금지 사항** | 본 log 누적 자체를 production 전환 자동 근거로 사용 금지. 운용역 명시 결정 + Decision Register 갱신 후에만 정책 변경 가능. |

### 1.1 영구 핵심 문구 (인용 의무)

본 template 으로 생성된 모든 log 는 다음 문구를 그대로 유지:

> "Phase D completed register-blocker resolution only.
> This does not mean production readiness.
> The engine remains in relaxed_diagnostic mode."

---

## 2. Run Metadata

| 필드 | 값 (기재) | 비고 |
|---|---|---|
| `run_id` | `____` | 운영자 또는 시스템 부여 ID. 권장 형식: `relaxed_<YYYYMMDD>_<etf|fund>_<seq>` |
| `as_of_date` | `YYYY-MM-DD` | 산출 기준일 |
| `created_at` | `YYYY-MM-DD HH:MM (TZ)` | run 실행 시각 |
| `reviewer` | `____` | 운용역 (서명 / 시스템 ID) |
| `operating_mode` | `relaxed_diagnostic` | 고정 (`tdf_2060.yaml::operating_mode`) |
| `source_mode` | `db` / `file` | `--source` 옵션. db 권장 (D-04 BRFUT004) |
| `portfolio_type` | `etf` / `fund` / `comparison` | 산출 종류 |
| `config_version` | `____` | yaml git commit hash 또는 운영자 지정 버전 식별자 |
| `config_hash` | `____` | (선택) `tdf_engine/config/*.yaml` SHA-256 등 |
| `output_paths` | (아래 다중행) | 본 run 의 산출 파일 경로 |

```
output_paths:
  - out/db_<etf|fund>_relaxed/portfolio_<etf|fund>_<as_of_date>.csv
  - out/db_<etf|fund>_relaxed/portfolio_<etf|fund>_<as_of_date>.json
  - out/db_<etf|fund>_relaxed/review_<etf|fund>_<as_of_date>.md
  - out/db_review_relaxed/comparison_etf_vs_fund_<as_of_date>.md   (comparison run 시)
```

---

## 3. Hard Constraint Check

본 항목 중 **하나라도 ✗ 시 → §6 outcome = `reject_as_invalid`** (E-2 governance §5.4).

| # | 항목 | 통과 |
|---|---|:---:|
| H-1 | **long-only**: 모든 asset / product weight ≥ 0 (negative count = 0) | ☐ |
| H-2 | **sum-to-100%**: asset_weight_sum ≈ 1.0 ∧ product_weight_sum ≈ 1.0 (atol 1e-4) | ☐ |
| H-3 | **DB source 정상**: datasets_loaded = expected count, datasets_missing = [] | ☐ |
| H-4 | **BRFUT004 direct mapping 정상** (D-04): dataset_id=201, blob_key=totRtnIndex, ust30 obs 정상 | ☐ |
| H-5 | **NaN / invalid return 없음**: diagnostics.db_source.warnings 클린, suspicious_flags 없음 | ☐ |
| H-6 | **optimizer / projection convergence**: solver_status=0, projection_success=True | ☐ |

**보조 메모**: `____`

---

## 4. Diagnostic Summary

| 항목 | 값 | 비고 |
|---|---|---|
| equity bucket weight | `____ %` | sanity range [60, 95]% — 이탈 시 monitoring flag (fail 아님) |
| fixed_income bucket weight | `____ %` | sanity range [5, 40]% |
| top asset (자산명 / weight) | `____ / ____ %` | 단일 자산군 monitoring (D-12 / D-17 candidate 트리거) |
| zero-weight assets count | `____` | (D-10: 0% 허용) |
| zero-weight assets list | `____` | 예: `kr_aggregate, kr_t10, ust30, dm_ex_us, hy` |
| max_abs_projection_drift | `____ %` | drift_source 분류 7-source (taa/projection.py) |
| projection drift primary source | `____` | 예: `long_only_clipping`, `redistribution_from_long_only_clipping` |
| max_abs_asset_weight_drift (quality) | `____ %` | drift_source 분류 5-source (portfolio/quality.py) |
| quality / selection drift primary source | `____` | 예: `product_cap_clipping_outflow`, `fallback_redistribution_inflow` |
| **product concentration top 5** | (아래 표) | review §4 |
| **manager concentration top 5** | (아래 표) | comparison §5 |
| short-history telemetry | `____` | 예: `ust30 obs=87 (< max*0.8 = 96)` (D-03) |

### 4.1 Product concentration top 5

| 순위 | product_id / 종목명 | manager | weight | cap 도달 여부 |
|:---:|---|---|---:|:---:|
| 1 | `____` | `____` | `____ %` | ☐ |
| 2 | `____` | `____` | `____ %` | ☐ |
| 3 | `____` | `____` | `____ %` | ☐ |
| 4 | `____` | `____` | `____ %` | ☐ |
| 5 | `____` | `____` | `____ %` | ☐ |

### 4.2 Manager concentration top 5

| 순위 | manager | 합산 weight | (참고) ETF cap 60% / Fund cap 50% 도달 여부 |
|:---:|---|---:|:---:|
| 1 | `____` | `____ %` | ☐ |
| 2 | `____` | `____ %` | ☐ |
| 3 | `____` | `____ %` | ☐ |
| 4 | `____` | `____ %` | ☐ |
| 5 | `____` | `____ %` | ☐ |

> manager cap 은 D-14 monitoring (현재 cap / soft warning 미도입). 도달 표시는 informational.

---

## 5. Key Observations (운용역 자유 기재)

본 섹션은 운용역이 직접 기재. 정형 양식 없음. 누적 시 정책 결정의 근거 자료.

### 5.1 자산군 쏠림 (asset concentration)

```
____
```

(예시 영역: 단일 자산군 70%+ / 0% 자산 다수 / equity bucket 100% 등)

### 5.2 상품 쏠림 (product concentration)

```
____
```

(예시 영역: 단일 product 30%+ / cap 도달 product 다수 / 상위 5개 product 합산 비중 등)

### 5.3 운용사 쏠림 (manager concentration)

```
____
```

(예시 영역: 단일 manager 50%+ / cap 근접 / 누적 추세 등)

### 5.4 TAA prototype rule 관련 특이사항

```
____
```

(예시 영역: regime label / asset_tilts 적용 결과 / bucket_tilts 미사용 확인 / per_asset_max_tilt 1.0 영향 등. **TAA 엔진 / 정책 / 수치 변경 금지** — 본 섹션은 관찰 기록만.)

### 5.5 Fallback redistribution 특이사항

```
____
```

(예시 영역: fallback_redistribution_inflow 단일 자산 5%p 초과 / pro-rata → bucket sibling → cash placeholder 어느 단계에서 발생 / 빈도 등.)

### 5.6 데이터 이슈

```
____
```

(예시 영역: ust30 obs=87 short_history / regime label 직전 산출 대비 변경 / DB source flag / as_of_date staleness 등.)

---

## 6. Governance Outcome

E-2 governance §5 의 4 outcomes 중 **반드시 하나 선택**. 선택 outcome 의 사유 입력란 작성.

### 6.1 ☐ `approve_for_diagnostic_record`

**의미**: 본 산출을 diagnostic record 로 승인. production 자료 아님.
**조건**: §3 hard constraint 모두 ✓ + sanity 이슈 운용역 수용 + 정책 정합성 인지 완료.

```
사유:
____
```

### 6.2 ☐ `request_rerun`

**의미**: hard constraint 통과, 단 데이터 / 시점 / 환경 차이로 재실행 필요.

```
원인 (해당 항목 체크):
☐ as_of_date 변경 (current: ____ → target: ____)
☐ DB 데이터 갱신 (지표: ____)
☐ regime label 변경 (이전: ____ → 현재: ____)
☐ 기타: ____

후속:
- Engine owner 에게 rerun 요청
- 새 산출물에 대해 본 governance 처음부터 다시 적용
- 이전 산출물 archive (사유 위 기재)
```

### 6.3 ☐ `request_policy_change`

**의미**: 산출 정상이나 **정책 자체 변경 필요**.

```
변경 대상 정책 (해당 항목 체크):
☐ D-11 dm_ex_us lower bound (현재 deferred → reactivate?)
☐ D-12 us_value cap (현재 deferred → reactivate?)
☐ D-13 quant_grade_policy mode
☐ D-14 manager concentration cap
☐ D-15 candidate (asset target vs product allocation drift) 정식 등록?
☐ D-16 candidate (product single cap) 정식 등록?
☐ D-17 candidate (asset concentration monitoring) 정식 등록?
☐ 기타: ____

근거 (review packet / §5 Observations 참조):
____

후속:
- Decision Register 갱신
- config / 코드 변경 (Engine owner)
- 재산출 후 본 governance 처음부터 다시
```

### 6.4 ☐ `reject_as_invalid`

**의미**: 산출이 hard constraint / 데이터 무결성 위반. 사용 불가.

```
위반 사항 (해당 항목 체크):
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

## 7. Policy Candidate Notes

본 섹션은 **future candidate 기록용** 이며, **Decision Register total count 14 를 변경하지 않는다.**

정식 Decision 등록은 별도 절차 (Phase E-5 진입 시점) 에서만 가능. 본 섹션은 candidate 트리거 누적 관찰만.

### 7.1 D-15 candidate — Asset target vs product allocation drift

| 항목 | 값 |
|---|---|
| 트리거 발생 여부 | ☐ |
| 본 run 의 max drift | `____ %p` |
| primary source | `____` |
| 누적 정식 등록 권고? | ☐ Yes / ☐ No |
| 근거 / 메모 | `____` |

### 7.2 D-16 candidate — Product single cap policy

| 항목 | 값 |
|---|---|
| 트리거 발생 여부 (단일 product > 30%) | ☐ |
| 본 run 의 top product weight | `____ %` |
| ETF cap 20% / Fund cap 30% 도달 product 수 | `____` |
| 누적 정식 등록 권고? | ☐ Yes / ☐ No |
| 근거 / 메모 | `____` |

### 7.3 D-17 candidate — Asset concentration monitoring

| 항목 | 값 |
|---|---|
| 트리거 발생 여부 (단일 자산군 > 80%) | ☐ |
| 본 run 의 top asset weight | `____ %` |
| 누적 정식 등록 권고? | ☐ Yes / ☐ No |
| 근거 / 메모 | `____` |

### 7.4 명시 문구 (인용 의무)

> "본 섹션은 future candidate 기록용이며, Decision Register total count 14 를 변경하지 않는다."

---

## 8. Sign-off Template

운용역이 outcome 결정 후 **그대로 인용** 가능한 표준 문구.

### 8.1 표준 sign-off (approve_for_diagnostic_record)

```
─────────────────────────────────────────────────────────────────────────
RELAXED DIAGNOSTIC RUN — SIGN-OFF

본 relaxed_diagnostic run 은 production portfolio 가 아닌 diagnostic record
로 확인했습니다. long-only / sum-to-100% / data integrity (BRFUT004 mapping
포함) 를 확인했으며, concentration 및 drift 항목은 monitoring 대상으로
기록합니다. 본 run 을 approve_for_diagnostic_record 로 승인합니다.

확인 사항 (모두 인지 완료):
  ✓ Phase D completed register-blocker resolution only (production-ready 아님)
  ✓ engine 은 relaxed_diagnostic mode 로 산출
  ✓ TAA rule = prototype operator-defined heuristic overlay (NOT final quantitative)
  ✓ D-08 limitation: DRM 3 xlsx 영구 해제 불가 → SAA/TAA/Final Excel 1:1 parity 영구 waived
  ✓ regimeAnalysis_rt = 파일 자체가 canonical definition

run_id: ____________
as_of_date: ____________
operating_mode: relaxed_diagnostic
승인일: ____________
운용역: ____________ (서명 / 시스템 ID)
─────────────────────────────────────────────────────────────────────────
```

### 8.2 다른 outcome 의 sign-off

`request_rerun` / `request_policy_change` / `reject_as_invalid` outcome 의 sign-off 문구는
E-2 governance (`docs/phase_e_relaxed_governance.md §7.2 ~ §7.4`) 의 template 그대로 사용.

---

## 9. 변경 금지 / 본 template 의 범위

| 영역 | 변경 |
|---|:---:|
| `tdf_engine/` 코드 | ✗ 무변경 |
| `tdf_engine/config/*.yaml` | ✗ 무변경 |
| `tests/` | ✗ 무변경 |
| `out/` 산출물 | ✗ 무변경 |
| `docs/investment_decision_register.md` status / count | ✗ 무변경 |
| Decision Register total count (14) | ✗ 무변경 |
| D-15 / D-16 / D-17 정식 등록 | ✗ 금지 (본 template 은 candidate 관찰만) |
| production dry-run 진입 | ✗ 금지 (Phase E-1 별도 절차) |
| TAA engine / 정책 / 수치 | ✗ 무변경 |
| asset cap / floor / band / soft warning threshold 추가 | ✗ 금지 |
| 본 문서 신설 | ✓ `docs/phase_e_relaxed_run_log_template.md` |

pytest: `142 passed, 5 skipped, 1 xfailed` (sanity 차원, 본 문서 작성 영향 없음).

---

## 10. 한 줄 요약

> **E-2 governance log template — relaxed_diagnostic run 의 hard constraint check + diagnostic
> summary + 4 governance outcomes + D-15/D-16/D-17 candidate 관찰 기록 양식.
> Decision Register / 코드 / config / 산출물 모두 무변경. 누적 sign-off 는 후속 Phase E-1
> 진입의 참고 자료이며 자동 전환 근거 아님.**
