# Phase D — D-02 Sign-off Patch Plan

작성일: 2026-05-08. **운용역 승인 대기**. 본 문서는 patch plan 만 — 실제 변경 없음.

> 운용역 승인 포인트 (단 1건):
> **`relaxed_diagnostic = telemetry_only` / `review = warning` / `production = review_required` /
> asset drift threshold = 3% / bucket drift threshold = 5%** 를 D-02 의 공식 운영 정책으로
> 승인할지 여부.
>
> 승인 시 본 plan 의 §3 변경 예정 파일에 §1 의 sign-off 문구 적용.
> 승인 전까지 모든 파일 무변경.

---

## 1. D-02 최종 sign-off 문구 (운용역 검토 대상)

```
─────────────────────────────────────────────────────────────────────────
D-02 — Projection drift threshold (운영 정책)

scope:
  D-02 는 **projection 단계의 drift 임계** 만 다룬다.
  product cap / selection fallback 으로 발생하는 drift 는 본 결정의 범위 밖이며,
  D-15 / D-16 / D-17 candidate 로 분리한다 (정식 등록은 별도 결정).

operating_mode 별 enforcement:
  - relaxed_diagnostic  → enforcement = telemetry_only
                          drift 초과는 quality_status 에 영향 없음.
                          drift 값은 telemetry 로만 보존.
  - review              → enforcement = warning
                          drift threshold 초과 시 warning 표시 (review_required 까지 안 감).
  - production          → enforcement = review_required
                          drift threshold 초과 시 운용역 검토 필요 상태로 전환.

threshold (production / review 모드 공통):
  - asset drift threshold  = 3%   (max_abs_asset_weight_drift)
  - bucket drift threshold = 5%   (max_abs_bucket_drift)

closure 근거:
  - projection drift 의 source 가 long_only_clipping (ust30 / kr_t10) 으로 설명 가능
  - relaxed mode 에서 bucket_constraint / asset_upper_bound source 발생 0건
  - product cap drift 는 D-15 / D-16 / D-17 candidate 로 분리되어 D-02 영역 밖

본 정책은 yaml `tdf_2060.yaml::drift_thresholds` 에 이미 구조화되어 있으며,
승인 시 closure 외 추가 코드/config 변경 불필요.

승인일: ____________ (운용역)
─────────────────────────────────────────────────────────────────────────
```

---

## 2. D-02 status 변경안

| 항목 | 변경 전 | 변경 후 |
|---|---|---|
| status | `pending_rerun` | **`closed`** |
| 분포 | open 3 / pe 3 / **pr 1** / dfd 2 / closed 5 (합계 14) | open 3 / pe 3 / **pr 0** / dfd 2 / **closed 6** (합계 14) |
| Phase D blocker | D-02 / D-03 / D-08 / D-09 (4건) | **D-03 / D-08 / D-09 (3건)** |

⚠️ **승인 전까지 register 의 실제 status / count 는 변경하지 않음.**

`closed` 시 본문에 들어갈 텍스트:

```
### D-02. `max_abs_projection_drift` 임계 — closed (YYYY-MM-DD, 운용역 승인)
- decision: §1 sign-off 문구 그대로 (운영 정책 확정).
- enforcement modes: relaxed_diagnostic=telemetry_only / review=warning /
  production=review_required.
- thresholds: asset=3%, bucket=5%.
- scope: projection drift 한정. product cap drift 는 D-15/D-16/D-17 candidate.
- closure 근거: phase_d_d02_drift_closure_brief.md §5 의 4 조건 모두 만족.
- 변경 위치 (이미 적용됨, 승인 시 추가 변경 없음):
  - tdf_2060.yaml::drift_thresholds.modes
  - portfolio/quality.py::evaluate_quality(enforcement=...)
  - taa/projection.py::_classify_projection_drift_source
  - reporting/review.py §3.1 Drift source breakdown
- 회귀 방어: tests/test_phase_d_relaxed.py 13 테스트 (Option A 7 + drift_source 6).
```

---

## 3. 변경 예정 파일 (승인 후)

| # | 파일 | 변경 |
|---|---|---|
| 1 | `docs/investment_decision_register.md` | (a) §1 표 D-02 행: `pending_rerun` → `closed`. (b) 분포 라인: `pr 1 → pr 0`, `closed 5 → closed 6`. (c) blocker 표기: D-02/03/08/09 → D-03/08/09. (d) §2 D-02 본문: 위 §2 의 closed 텍스트로 교체. (e) §5 변경 이력 한 줄 추가 (D-02 closed by 운용역 sign-off, 정책 §1 인용). |
| 2 | `HANDOFF.md` | §0 TL;DR 의 blocker 명시: "D-02/D-03/D-08/D-09 (4건)" → "D-03/D-08/D-09 (3건)". |
| 3 | `memory/project_state.md` | Decision Register 분포 + blocker 라인 갱신. D-02 closure 결정 기록 한 줄 추가. |
| 4 | `docs/phase_d_d02_drift_closure_brief.md` | §1 Executive Summary 의 "D-02 status: pending_rerun 유지" → "closed (YYYY-MM-DD 운용역 sign-off)". §5 closure 조건 표의 미충족 2건 → 충족 처리. sign-off note 한 블록 추가. |

(선택, 승인 후 별도 turn) `tdf_engine/config/tdf_2060.yaml::drift_thresholds` 의 운영값이
default 0.03 / 0.05 와 다르게 결정되면 yaml 수정. **본 plan 의 권장은 default 그대로 유지** 이므로
config 변경 불필요.

---

## 4. 변경하지 않을 것

- ✗ `tdf_engine/` 코드 (optimization / regime / TAA / projection / quality / selection / portfolio / reporting / repositories) 무변경
- ✗ `tdf_engine/config/*.yaml` 무변경 (이미 `drift_thresholds.modes` 구조화 완료. 본 plan 의 권장값과 정합)
- ✗ `tests/` 무변경 (기존 142 통과 유지)
- ✗ `out/db_*` 산출물 무변경
- ✗ **D-15 / D-16 / D-17 정식 등록 안 함** (§5 처리 참조)
- ✗ Decision Register **total count 14 무변경**
- ✗ asset weight 산출 결과 무변경 (분류 / 표현 / 진단만 적용 완료, 산출 자체는 동일)

---

## 5. D-15 / D-16 / D-17 처리

본 turn 에서도 **future decision candidate 유지**.

| candidate | 영역 | 현재 상태 |
|---|---|---|
| D-15 | Asset target vs product allocation drift policy | candidate 유지. 정식 등록 보류. |
| D-16 | Product-level single cap policy | candidate 유지. 정식 등록 보류. |
| D-17 | Asset concentration monitoring | candidate 유지. 정식 등록 보류. |

**중요**: D-02 closure 와 D-15/16/17 정식 등록은 **독립적인 결정**.

```
잘못된 해석:
  D-02 를 닫으려면 D-15/16/17 을 정식 등록해야 한다.

정확한 해석:
  product cap drift 가 D-02 범위 밖이라는 분리 자체는 본 brief / candidate 표기로 이미 완료.
  D-15/16/17 정식 등록은 D-02 closure 의 필수 조건이 아닌 후속 governance 선택사항.
  운용역이 별도 결정 시점에 등록 여부를 판단하면 됨.
```

정식 등록 시점 작업 (참고, 본 plan 범위 외):
- register total count 14 → 17 갱신
- 각 candidate 의 책임 / 변경 위치 / 결정 옵션 명세 확정
- §5 변경 이력에 등록 사유 기록

---

## 6. 운용역 승인 요청 — 단일 의사결정

> **D-02 를 §1 정책 (`relaxed=telemetry_only` / `review=warning` / `production=review_required`,
> asset 3% / bucket 5%, scope = projection drift only) 으로 `closed` 처리할지 승인.**

승인 옵션:

| 옵션 | 의미 | 후속 |
|---|---|---|
| **A. 승인** | §1 정책 그대로 D-02 closed. | 본 plan §3 의 4개 파일 갱신 (별도 turn). 코드/config/test 무변경. |
| B. 정책 일부 수정 후 승인 | threshold / enforcement 모드 매핑 변경 후 closed. | yaml `drift_thresholds` 운영값 갱신 + 본 plan 갱신 후 다시 승인. |
| C. 보류 | 승인하지 않음. | D-02 `pending_rerun` 유지. 추가 분석 또는 외부 자료 대기. |

승인 결과를 사용자가 명시하면 별도 turn 에서 §3 patch 적용.

---

## 7. Sign-off

| 역할 | 이름 | 일자 | 비고 |
|---|---|---|---|
| 운용역 | ________ | ________ | (승인 / 보류) |
| 운영자 | ________ | ________ | (참조) |

본 plan 은 텍스트 patch plan 입니다. 본 turn 까지 실제 변경 0건.
