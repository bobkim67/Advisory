# Phase E-1 — Production Mode Transition Design

작성일: 2026-05-08. **설계 문서만**. 코드 / config / test / out 변경 없음.

> **Phase D completed register-blocker resolution only.**
> **This does not mean production readiness.**
> **The engine remains in relaxed_diagnostic mode.**
>
> 본 문서는 **production 전환을 위한 설계** 만 정리. 실제 전환은 **별도 운용역 승인 + E-4/E-5/E-3 선행 정리** 필요.
> E-2 sign-off 누적은 production 전환의 **참고 근거이지 충분조건이 아님**.

---

## 1. Purpose

| 측면 | 내용 |
|---|---|
| **relaxed_diagnostic 위상** | 진단용 baseline. production portfolio 아님. |
| **production mode 위상** | 실제 운용 검토 가능한 portfolio 산출 모드. 운용역이 production 의 의사결정 근거로 사용. |
| **전환 조건** | E-2 governance sign-off 누적 + D-13/D-14 정책 + D-15/D-16/D-17 candidate 정식 등록 + 운용역 별도 승인. **자동 전환 금지**. |
| **본 문서 범위** | 전환 조건 / config 변경 후보 / governance 차이 / test impact / roadmap **설계만**. 실제 전환 적용 ✗. |

### 1.1 영구 핵심 문구 (인용 필수)

후속 모든 production 관련 문서에서 그대로 유지:

> "E-2 sign-off 누적은 production 전환의 충분조건이 아니라 참고 근거다.
> Production 전환은 별도 E-1 설계와 운용역 승인이 필요하다."

---

## 2. Current mode vs Production mode 비교

| 측면 | **relaxed_diagnostic (현재)** | **production (E-1 후보)** |
|---|---|---|
| `operating_mode` | `relaxed_diagnostic` | `production` |
| **drift enforcement** | `telemetry_only` (drift 초과 → quality_status 영향 없음) | `review_required` (drift 초과 → review_required) |
| **drift threshold** | asset 3% / bucket 5% (값은 동일) | asset 3% / bucket 5% (변경 가능, 운용역 결정) |
| **asset bounds** | 모두 [0, 1] (사실상 비활성). reference 만 보존. | **운용역 결정 필요** (비활성 유지 vs D-11/D-12 reactivate vs 신규값) |
| **bucket range (equity/FI)** | 모두 [0, 1]. sanity range [60-95]/[5-40] 는 monitoring only. | **운용역 결정 필요** (monitoring 유지 vs hard 75-85/15-25 vs 다른 운영값) |
| **per_asset_max_tilt** | 1.0 (사실상 비활성) | 운용역 결정 필요 (0.03 복원 vs 다른 운영값) |
| **`final_asset_bounds`** | [0, 1] (사실상 비활성) | 운용역 결정 필요 |
| **TAA rule status** | prototype operator-defined heuristic overlay | 동일 (heuristic 그대로). final quantitative TAA 는 후속 (TAA cand-A/B/C, 별도 Phase) |
| **review requirement** | E-2 governance — 4 outcomes, sign-off 매번 필수 | production governance — 더 strict. approve_for_model_portfolio_review 위주. reject 기준 동일하지만 정책 위반 (concentration / drift) 기준이 hard fail 가능. |
| **output usage** | diagnostic record only. archive / 정책 결정 근거. **고객 자료 / production 사용 금지**. | model portfolio review 자료. 운용역 sign-off 후 운용 의사결정 근거. **단 production = "자동 운영" 이 아님** (별도 운영 시스템 승인 필요). |
| **governance 의무** | 모든 산출에 E-2 sign-off | 모든 산출에 production governance sign-off (E-2 보다 strict) |
| **review packet banner** | "RELAXED DIAGNOSTIC RUN — NOT a production portfolio" | "PRODUCTION REVIEW RUN — Model portfolio for operator review" (또는 운용역 결정 문구) |

### 2.1 변경되지 않는 것 (relaxed → production 모두 동일)

| 영역 | 이유 |
|---|---|
| **hard constraint = long-only + sum-to-100% + 데이터 무결성** | D-01 closed. production 에서도 동일. |
| **BRFUT004 direct mapping** | D-04 closed. production 에서도 동일. proxy 추가 금지. |
| **MVO objective = max_sharpe + dispatch** | D-05 closed. production 에서도 동일. (Excel `$L$26` 영구 waived) |
| **HY = fixed_income + risk_asset + credit** | D-07 closed. |
| **자산군 0% 허용** | D-10 closed. negative weight 만 금지 (이는 long-only 정책). |
| **lookback policy = Hybrid** | D-03 closed. return/vol asset_specific, corr common. min_obs=12. |
| **D-08 영구 한계** | DRM 영구 해제 불가 → SAA/TAA/Final Excel 1:1 parity 영구 waived. production 모드에서도 동일. |
| **regimeAnalysis_rt = canonical file** | D-09 closed. production 에서도 별도 정의 자료 없음. |
| **TAA tilt = prototype heuristic overlay** | 본 단계 TAA cand-A/B/C 미구현. production 모드에서도 동일 (별도 Phase 까지). |

---

## 3. Production mode 전환 조건

### 3.1 최소 조건 (모두 충족 필요)

| # | 조건 | 검증 위치 | 현재 상태 |
|---|---|---|:---:|
| 1 | **long-only 통과** | `tests/test_phase_d_relaxed.py::test_phase_d_relaxed_long_only` + production rerun | ✓ |
| 2 | **sum-to-100% 통과** | 동 + `test_phase_d_relaxed_sum_to_one` | ✓ |
| 3 | **data integrity 통과** | DB sanity / NaN / extreme return 검증 | ✓ |
| 4 | **BRFUT004 mapping 정상** | `tests/test_phase_c_db.py` + relaxed run sanity | ✓ |
| 5 | **D-08 limitation 인지** | E-1 sign-off template 에 명시 + 운용역 동의 | ⏳ E-1 sign-off 시 |
| 6 | **D-09 canonical file 인지** | 동 | ⏳ E-1 sign-off 시 |
| 7 | **relaxed governance sign-off 기록 존재** | `governance_log/` (또는 운영자 지정) 에 누적 sign-off | ⏳ E-2 운영 후 |
| 8 | **D-13 / D-14 또는 concentration policy 처리 방향 결정** | Decision Register D-13 / D-14 → status `open → closed` 또는 `monitoring_only` 결정 | ⏳ E-4 단계 |
| 9 | **product cap / fallback drift policy 처리 방향 결정** | D-15 / D-16 / D-17 candidate → 정식 등록 또는 informational record | ⏳ E-5 단계 |
| 10 | **production review packet 승인 절차 정의** | E-1 governance (본 문서 §5) + 운영 시스템 절차 | ⏳ 본 문서 작성 + 운영 결정 |

**현재 충족** = 4건 (1~4) + 1건 부분 충족 (10 일부). **운용역 결정 대기** = 5~9.

### 3.2 권장 순서 (사용자 판단 반영)

> "production dry-run 설계까지만 먼저 만들고, 실제 전환 전에는 D-13/D-14 와 product cap / fallback drift 정책을 먼저 정리"

1. **본 문서 (E-1 design) 완료** — production 전환 설계 / governance / config 후보 record
2. **E-2 governance 운영 시작** — relaxed sign-off 누적 (3개월 권장)
3. **E-4 진행** — D-13 / D-14 정책 결정 (운용역)
4. **E-5 진행** — D-15 / D-16 / D-17 정식 등록 또는 informational record (운용역)
5. **E-3 (선택)** — D-11 / D-12 reactivate 결정 (운용역)
6. **Production dry-run** — `operating_mode: production` 으로 산출 1회. yaml 변경 후 재산출. **운용 적용은 안 함**. 이 결과를 production governance 로 검토.
7. **Production 정식 전환** — dry-run 결과 운용역 sign-off → 운영 시스템 적용.

---

## 4. Config 전환 설계 (**변경 후보만**, 적용 ✗)

### 4.1 yaml 변경 후보

#### `tdf_2060.yaml`

| 키 | 현재 | production 후보 | 결정자 |
|---|---|---|---|
| `operating_mode` | `relaxed_diagnostic` | `production` (또는 중간 단계 `review`) | 운용역 (E-1 sign-off) |
| `taa_bounds.equity_min/max` | 0.0 / 1.0 (사실상 비활성) | (a) 0.0 / 1.0 유지 (자유) <br> (b) 0.75 / 0.85 (Phase B/C 운영값) <br> (c) 다른 운영값 | 운용역 (E-3) |
| `taa_bounds.fixed_income_min/max` | 0.0 / 1.0 | (a) 동 / (b) 0.15 / 0.25 / (c) 운영값 | 운용역 (E-3) |
| `weight_bounds.<asset>.min/max` | 모두 [0, 1] | (a) 비활성 유지 <br> (b) `_reference_only` 의 값 (Phase B/C) reactivate <br> (c) 새 운영값 | 운용역 (E-3 + D-11/D-12 영향) |
| `final_asset_bounds.<asset>.min/max` | 모두 [0, 1] | 동 | 동 |
| `taa_sanity_range` | [60-95] / [5-40] (monitoring only) | 유지 (production 에서도 monitoring) 또는 hard bound 로 승격 | 운용역 (E-3 결정 시) |

#### `optimization_constraints.yaml`

| 키 | 현재 | production 후보 |
|---|---|---|
| `equity_sum.min/max` | 0.0 / 1.0 | 0.75 / 0.85 또는 운영값 (E-3) |
| `fixed_income_sum.min/max` | 0.0 / 1.0 | 0.15 / 0.25 또는 운영값 |

#### `taa_policy.yaml`

| 키 | 현재 | production 후보 |
|---|---|---|
| `equity_total_min/max` | 0.0 / 1.0 | E-3 결정 |
| `fixed_income_total_min/max` | 0.0 / 1.0 | E-3 결정 |
| `per_asset_max_tilt` | 1.0 (비활성) | (a) 0.03 (Phase B/C 운영값) <br> (b) 다른 값 <br> (c) 비활성 유지 (TAA prototype 정책상) | 운용역 |
| `tilt_sum_must_be_zero` | true | true 유지 (회계 정합성, 정책 제약 아님) |
| `warn_if_bucket_bound_violated` | false | true (bucket bound 활성 시) |
| `warn_if_per_asset_tilt_violated` | false | true (per_asset_max_tilt 활성 시) |

#### `glidepath.yaml`

| 키 | 현재 | production 후보 |
|---|---|---|
| `glidepath_reference.enforced` | false (reference only) | (a) false 유지 (단일 vintage) <br> (b) true 로 승격 (다중 vintage 산출 시) — E-8 / 후속 Phase | 운용역 |

#### `db_sources.yaml`

| 키 | 현재 | production 후보 |
|---|---|---|
| `asset_rt_vol.intersection_policy` | asset_specific | 유지 (D-03 closed) |
| `asset_rt_vol.min_obs` | 12 | 유지 또는 운용역 결정 (예: 36 / 60) |
| `corr_matrix.intersection_policy` | common | 유지 (D-03 closed) |
| `corr_matrix.short_history_warning_ratio` | 0.8 | 유지 또는 운용역 결정 |

#### 신규 yaml 검토 (E-4 / E-5 결정 후)

- `concentration_policy.yaml` (또는 `universe_filter.yaml` 확장): D-13 / D-14 운영값
- `product_cap_policy.yaml` (또는 `universe_filter.yaml` 확장): D-15 / D-16 / D-17 정식 등록 시

### 4.2 코드 변경 후보 (적용 ✗, 설계만)

| 파일 | 변경 후보 |
|---|---|
| `tdf_engine/portfolio/quality.py` | 변경 없음 (enforcement 모드는 yaml drift_thresholds.modes.production 가 결정. 코드는 이미 5 모드 분기 구조화됨) |
| `tdf_engine/taa/projection.py` | 변경 없음 (drift_source 분류 그대로) |
| `tdf_engine/portfolio/builder.py` | 변경 없음 |
| `tdf_engine/reporting/review.py` | banner 문구 (production mode 시 "PRODUCTION REVIEW RUN" 으로). `_build_operating_mode_banner` 의 production 분기 추가 1줄 |
| `tdf_engine/tools/build_portfolio.py` | 변경 없음 (yaml 만 읽으면 자동 production 모드 동작) |

→ **production 전환은 yaml 변경 위주, 코드 변경 최소**.

---

## 5. Production Governance (E-2 와 비교)

### 5.1 Production outcome 4종

| outcome | 의미 | 후속 |
|---|---|---|
| **`approve_for_model_portfolio_review`** | model portfolio 로 운용역 검토 승인 | 운용 의사결정 근거로 사용 가능. 단 production = "자동 운영" 이 아님 — 별도 운영 시스템 승인 필요. |
| **`request_policy_change`** | 산출 정상이나 정책 변경 필요 (E-3/E-4/E-5 영역) | Decision Register 갱신 → config 변경 → 재산출 → governance 재적용. (relaxed 와 동일) |
| **`request_rerun`** | 데이터 / 시점 / 환경 변경 재실행 | 재산출 후 governance 재적용. (relaxed 와 동일) |
| **`reject_as_invalid`** | hard constraint / 데이터 무결성 위반 | rejected/ 격리. 운영 사용 절대 금지. (relaxed 와 동일) |

### 5.2 Relaxed (E-2) vs Production (E-1) 비교

| 항목 | E-2 (relaxed) | E-1 (production) |
|---|---|---|
| approve outcome | `approve_for_diagnostic_record` | `approve_for_model_portfolio_review` |
| approve 의미 | diagnostic record only. archive / 정책 근거. | model portfolio. 운용 검토 근거. |
| 사용 가능 범위 | governance log, 정책 결정 회의, 진단 자료 | + 운용 의사결정 회의, 운용 시스템 검토 |
| **사용 금지** | production 자동 적용, 고객 자료, regulatory 보고 | (production = 자동 운영 아님) 자동 batch, 고객 자료 직접 인용, regulatory 직접 사용 |
| reject 기준 | hard constraint 위반 + 데이터 무결성 위반 | 동일 + 정책 위반 (concentration cap 등 hard fail 시) |
| escalation 강도 | sanity range 이탈 → request_policy_change | sanity range 이탈 → 더 strict (운용역 결정 정책상 hard cap 이면 즉시 reject 가능) |
| sign-off 빈도 | 매 산출마다 | 동 (단 production 운영 시점은 운영 시스템 별도) |
| sign-off template | E-2 §7 | 동일 구조 + production 5 영구 인지 사항 (D-08 / D-09 / TAA prototype 등) |
| Excel 1:1 parity | 영구 waived | 동 (D-08) |
| TAA model | prototype heuristic | 동 |

### 5.3 Production sign-off template (인용 가능 초안)

```
─────────────────────────────────────────────────────────────────────────
PRODUCTION REVIEW SIGN-OFF — APPROVE FOR MODEL PORTFOLIO REVIEW

산출물:
  - out/db_etf_production/portfolio_etf_<date>.{csv,json,md}
  - out/db_fund_production/portfolio_fund_<date>.{csv,json,md}
as_of_date: <YYYY-MM-DD>
operating_mode: production

본 production 산출은 model portfolio 검토 자료로 확인했습니다.
long-only / sum-to-100% / data integrity (BRFUT004 mapping 포함) /
optimizer · projection convergence 를 모두 확인했으며, 정책 위반 /
concentration / drift 항목을 검토 완료했습니다.

본 결과를 model portfolio review 로 승인합니다.
운영 시스템 자동 적용 또는 고객 자료 직접 인용 금지를 동의합니다.

영구 한계 인지 (D-08 / D-09):
  ✓ DRM 3 xlsx 영구 해제 불가
  ✓ SAA / TAA / Final weights Excel 1:1 parity 영구 waived
  ✓ MVO objective Excel $L$26 직접 확인 영구 waived
  ✓ regimeAnalysis_rt = 파일 자체가 canonical definition (별도 자료 영구 부재)
  ✓ xfail 1건 영구 유지 (외부 답안지 영구 부재 reflect)

TAA rule 인지:
  ✓ TAA tilt = prototype operator-defined heuristic overlay (NOT final
    quantitative model, NOT second-stage optimizer)
  ✓ asset_tilts 만 적용 (bucket_tilts = metadata only)

production policy 인지 (E-1 sign-off 시점에 결정된 정책):
  - operating_mode: production
  - drift enforcement: review_required (asset ____% / bucket ____%)
  - asset bounds: ____ (E-3 결정)
  - bucket range: ____ (E-3 결정)
  - manager concentration cap: ____ (E-4 / D-14 결정)
  - quant_grade_policy: ____ (E-4 / D-13 결정)
  - product cap / fallback drift policy: ____ (E-5 / D-15-17 결정)

monitoring 기록 항목:
  - equity / fixed_income bucket: ____ / ____
  - 최대 자산군 비중: ____ ____%
  - 최대 운용사 비중: ____ ____%
  - max_abs_projection_drift: ____% (source: ____)
  - max_abs_asset_weight_drift: ____% (source: ____)
  - drift enforcement 결과: ____

승인일: ____________
운용역: ____________ (서명 / 시스템 ID)
─────────────────────────────────────────────────────────────────────────
```

---

## 6. Risk Controls to Decide Before Production

production 전환 전 운용역이 결정해야 할 risk control 항목 분류.

### 6.1 필수 (production 전환 전 반드시 결정)

| 항목 | 영역 | Decision 연결 |
|---|---|---|
| **Manager concentration cap** | D-14 | E-4. monitoring vs hard cap (ETF 60% / Fund 50% 또는 변경) |
| **quant_grade_policy mode** | D-13 | E-4. ETF=hard_filter / Fund=score_penalty 유지 vs 통일 vs monitoring_only |
| **Product single cap** | D-16 candidate | E-5. ETF 20% / Fund 30% 유지 vs 변경 vs 자산군별 차등 |
| **Asset target vs product allocation drift policy** | D-15 candidate | E-5. fallback 허용 여부 / 임계 |
| **Asset concentration monitoring** | D-17 candidate | E-5. 자산 70%+ 쏠림 monitoring vs band 도입 |
| **drift enforcement 운영값** | D-02 (이미 closed 정책 따름) | yaml `drift_thresholds.modes.production.enforcement = review_required`, threshold = asset 3% / bucket 5% (변경 가능) |

### 6.2 선택 (production 전환 시 권장 결정, 미결정 시 default 동작)

| 항목 | 영역 | default (relaxed 동작 그대로) |
|---|---|---|
| **자산군 band (per-asset bounds)** | D-11 / D-12 | 비활성 유지 (모두 [0, 1]). production 에서도 sharpe-driven 쏠림 가능 |
| **equity / fixed_income bucket range** | E-3 | 비활성 유지. monitoring [60-95]/[5-40] |
| **per_asset_max_tilt** | (TAA prototype 영역) | 1.0 (비활성). |
| **fallback redistribution policy 세분화** | D-15 candidate | 현재 동작 유지 (same_asset → bucket_sibling → cash) |

### 6.3 후순위 (production 안정화 후 검토)

| 항목 | 영역 |
|---|---|
| **TAA confidence scaling** | TAA cand-A. 별도 Phase. |
| **TAA optimizer (second-stage)** | TAA cand-B. 별도 Phase. |
| **Multi-vintage glidepath integration** | E-8. 단일 vintage (2060) 안정화 후. |
| **bucket_tilts 활성화** | TAA cand-D. asset_tilts 와 결합 방식 정의 후. |
| **TAA 백테스트 / parameter sensitivity** | TAA cand-E. |
| **selection score 노출** | Telemetry candidate. |
| **자동 batch 운영 / 시스템 통합** | 운영 시스템 영역. 본 Phase 외. |

---

## 7. Test Impact

production 전환 전 추가 / 갱신 권장 테스트.

### 7.1 신규 테스트 (production 전환 후 추가)

| 테스트 | 검증 |
|---|---|
| `test_production_mode_drift_review_required` | yaml `operating_mode=production` 시 drift threshold 초과 → quality_status = `review_required` |
| `test_production_mode_banner_renders` | review packet 헤더가 production banner 로 변경 (relaxed 와 다름) |
| `test_production_mode_long_only` | production 산출도 long-only 보장 (D-01 그대로) |
| `test_production_mode_sum_to_one` | production 산출도 sum-to-100% 보장 |
| `test_relaxed_vs_production_output_separation` | `out/db_*_relaxed/` 와 `out/db_*_production/` 가 분리되어 산출되는지 (output_dir 옵션 동작) |
| `test_config_operating_mode_transition` | yaml `operating_mode` 값 변경 시 enforcement 자동 전환 (이미 142 통과 테스트의 일부) |
| `test_production_governance_outcome_metadata` | production 산출의 review packet 에 `approve_for_model_portfolio_review` 등 outcome 후보가 명시되는지 |

### 7.2 기존 테스트 영향

| 테스트 | 영향 |
|---|---|
| `test_phase_d_relaxed_*` (test_phase_d_relaxed.py) | 영향 없음. relaxed mode 검증은 그대로. operating_mode 가 relaxed 일 때만 동작 검증. |
| `test_phase_b5plus_quality::test_quality_status_review_required_when_drift_exceeds_threshold` | 영향 없음. explicit threshold + enforcement=production 으로 검증 (이미 그렇게 동작). |
| `test_e2e_etf` / `test_phase_c_db` | 영향 없음. operating_mode 무관하게 long-only + sum=1 검증. |
| Hard constraint 테스트 (long-only / sum / DB / BRFUT004) | 영향 없음. production 에서도 동일 hard. |

### 7.3 전환 전 정합성 확인

production yaml 변경 후 pytest 실행 시:
- 142 passed 그대로 유지 (전환 자체는 기존 테스트 망가뜨리지 않아야 함)
- 신규 테스트 추가 시 142 → 142 + N

만약 142 가 깨지면 전환 design 또는 yaml 에 문제. **production 운영 금지 + 즉시 진단**.

---

## 8. Phase E Roadmap (사용자 판단 반영)

### 8.1 권장 흐름

```
[현재] Phase D completion + E-2 governance documented
   ↓
1. E-1 production transition design  ← 본 문서
   ↓
2. E-2 governance 운영 시작 (relaxed sign-off 누적, 약 3개월)
   ↓
3. E-4 D-13 / D-14 policy decision (운용역)
   ↓
4. E-5 D-15 / D-16 / D-17 정식 등록 또는 informational record (운용역)
   ↓
5. E-3 D-11 / D-12 reactivate 결정 (선택, 운용역)
   ↓
6. Production dry-run (operating_mode=production yaml 변경 1회 산출. 운영 적용 X)
   ↓
7. Production governance review (본 문서 §5 sign-off)
   ↓
8. Production 정식 전환 (운용 시스템 적용 — 본 Phase 범위 외)
```

### 8.2 사용자 판단 (영구 기록)

> "Production 전환 전에 자산군 band 와 concentration policy 를 먼저 정할 것인가, 아니면 production dry-run 을 먼저 돌리고 그 결과를 보고 band 를 도입할 것인가?
>
> **판단 = production dry-run 설계까지만 먼저 만들고, 실제 전환 전에는 D-13/D-14 와 product cap / fallback drift 정책을 먼저 정리하는 것이 안전.**"

본 문서는 **dry-run 설계까지** 정리. 실제 전환은 E-4 / E-5 (D-13/D-14 + D-15-17) 정리 후.

### 8.3 Roadmap 후순위 (E-1 ~ E-8 외)

본 문서는 본 Phase E 의 production 전환에 집중. 아래는 후순위:

- TAA cand-A ~ E (regime confidence / optimizer / signal-based / bucket_tilts / 백테스트) — 별도 Phase F
- Telemetry candidate (SAA / TAA tilt / 제외 상품 / selection score) — 별도 Phase F 또는 E-1 후 안정화 시점
- 자동 batch 운영 / 시스템 통합 — 운영 시스템 영역, 본 엔진 Phase 외
- 다중 vintage glidepath 산출 (2050 / 2040 / 2030) — E-8

---

## 9. Production Dry-run 설계 (E-1 핵심)

본 문서의 핵심 산출. 실제 전환 전 **단 1회의 dry-run** 으로 production 모드 동작 확인.

### 9.1 dry-run 절차

```
Step 1. yaml 변경 (운용역 승인 후 별도 turn)
  - tdf_2060.yaml::operating_mode: relaxed_diagnostic → production
  - drift_thresholds.modes.production 의 운영값 확정 (default 0.03 / 0.05 또는 운용역 결정)
  - (선택) E-3/E-4/E-5 결정에 따른 자산군 cap / manager cap / product cap 운영값 yaml 적용
  - 코드 변경 1줄: review.py::_build_operating_mode_banner 의 production 분기 추가

Step 2. dry-run 산출
  - python -m tdf_engine.tools.build_portfolio --source db --as-of-date <YYYY-MM-DD>
      --product-type etf --output-dir out/db_etf_production_dryrun
  - 동 (Fund)
  - python -m tdf_engine.tools.render_review --etf-json ... --fund-json ...
      --comparison-out out/db_review_production_dryrun/comparison_<date>.md

Step 3. dry-run 검증
  - hard constraint 통과 확인 (long-only / sum / DB / convergence)
  - drift enforcement 가 review_required 분기로 동작 확인
  - drift exceed 시 quality_status = review_required 인지 확인
  - banner 문구 변경 확인 (production)
  - relaxed 산출 (out/db_*_relaxed/) 와 분리 보존 확인
  - pytest 실행 (142 + 신규 테스트 통과)

Step 4. dry-run 결과 governance
  - production governance §5 sign-off (본 문서)
  - approve_for_model_portfolio_review / request_policy_change / request_rerun / reject_as_invalid
  - approve 시 → production 정식 전환 후보로 운영 시스템 영역 인계
  - 다른 outcome 시 → yaml / 정책 / 코드 수정 후 dry-run 재실행

Step 5. 정식 전환 (별도, 본 Phase 범위 외)
  - 운영 시스템 / batch 관리 / 자동화 영역
  - 본 엔진 Phase 책임 완료 시점은 dry-run governance approve 까지
```

### 9.2 dry-run output 분리

```
out/
├── db_etf_relaxed/                         relaxed 산출 (보존)
├── db_fund_relaxed/
├── db_review_relaxed/
├── db_etf_production_dryrun/               ★ E-1 신설
├── db_fund_production_dryrun/              ★ E-1 신설
└── db_review_production_dryrun/            ★ E-1 신설
```

production_dryrun 디렉토리는 명시적으로 `_dryrun` 접미사로 production 운영 산출과 분리. 정식 운영 산출은 별도 시스템 영역.

---

## 10. 본 문서 변경 범위

| 영역 | 변경 |
|---|:---:|
| `tdf_engine/` 코드 | ✗ 무변경 |
| `tdf_engine/config/*.yaml` | ✗ 무변경 (변경 후보만 §4 에 정리) |
| `tests/` | ✗ 무변경 (신규 테스트 후보만 §7 에 정리) |
| `out/` 산출물 | ✗ 무변경 |
| `docs/investment_decision_register.md` status / count | ✗ 무변경 |
| Decision Register total count (14) | ✗ 무변경 |
| 본 문서 신설 | ✓ `docs/phase_e_production_transition_design.md` |

pytest: `142 passed, 5 skipped, 1 xfailed` (sanity 차원, 본 문서 작성 영향 없음).

---

## 11. 한 줄 요약

> **E-1 = production 전환 설계. 자동 전환 금지. 전환 전 E-4 (D-13/D-14) + E-5 (D-15-17) 정리 우선.
> 실제 전환은 yaml 변경 위주 (코드 변경 최소). dry-run 1회 → governance approve → 운영 시스템 인계.
> 영구 한계 (D-08 / D-09 / TAA prototype) 는 production 모드에서도 동일.**
