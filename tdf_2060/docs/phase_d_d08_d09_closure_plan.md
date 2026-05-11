# Phase D — D-08 / D-09 Closure Plan

작성일: 2026-05-08. 운용역 정보 수령 (2026-05-08) 으로 외부 자료 의존 해소. 본 문서는 **plan 만** — 실제 변경 없음.

> **운영자 정보 수령 (2026-05-08)**:
> - DRM 3 xlsx 는 **풀 수 없음** — 단 정보 자체는 운영자가 직접 제공.
> - GlidePath: 2060=주식 80% / 2050=70% / 2040=60% / 2030=50%
> - `RegimeAnalysis_2602.xlsx` + `ECI_Neo_202603.xlsx` 내용 = 기존 `regime_*` + `regimeAnalysis_*` file 의 결합물. 추가 정보 없음.
>
> 따라서 **D-08 / D-09 의 closure 사유는 "DRM 해제" 가 아니라 "운영자 직접 정보 + 기존 file 데이터로 대체"** 가 정확.

---

## 1. 운영자 수령 정보 — 정본 데이터 위치 매핑

### 1.1 D-08 — DRM 3 xlsx 의 처리

| DRM 파일 | 운영자 수령 정보 | 정본 위치 |
|---|---|---|
| `0. 정리 - GlidePath 값.xlsx` | **2060=80% / 2050=70% / 2040=60% / 2030=50% (주식 편입비)** | 신규 yaml `glidepath.yaml` 또는 `tdf_2060.yaml::glidepath_reference` 로 코드화 |
| `RegimeAnalysis_2602.xlsx` | "기존 `regime_*` + `regimeAnalysis_*` 시트의 결합물. 추가 정보 없음" | **`Advisory/regime_src` + `regime_Placement` + `regime_Velocity` + `regime_ECI` + `regime_Dashboard` + `regimeAnalysis_src` + `regimeAnalysis_rt`** (이미 file 모드 사용 중) |
| `ECI_Neo_202603.xlsx` | 동일 (regime_* + regimeAnalysis_* 결합물) | 동일 (위 7개 file) |

### 1.2 D-09 — `regimeAnalysis_rt` 정의

운영자 정보: **별도 정의 자료 없음. `Advisory/regimeAnalysis_rt` 파일 자체가 정의.**

→ Phase C.5 시점의 "regimeAnalysis_rt 정의 미명시" 미해결 사항은 "파일 자체가 정본" 으로 해소.

---

## 2. D-08 Closure Plan

### 2.1 D-08 sign-off 문구 (운용역 검토 대상)

```
─────────────────────────────────────────────────────────────────────────
D-08 — Excel DRM 해제 (3건) — 정책 변경 closure

원래 closure 조건: DRM 3건 해제 → SAA/TAA/Final parity 검증 활성
실제 상황:        DRM 자체는 풀 수 없음
대체 closure 사유: 운영자가 DRM 보호 파일의 핵심 정보를 직접 제공 +
                  나머지 내용은 기존 file 모드 데이터 (Advisory/regime_*,
                  regimeAnalysis_*) 가 정본으로 확인됨

각 파일별 처리:
  1. 0. 정리 - GlidePath 값.xlsx
     → 운영자 직접 정보: 2060=80% / 2050=70% / 2040=60% / 2030=50%
     → 처리: glidepath.yaml 또는 tdf_2060.yaml::glidepath_reference 신설
              (4 vintage 주식 편입비 metadata)

  2. RegimeAnalysis_2602.xlsx
     → 운영자 확인: 기존 regime_* + regimeAnalysis_* 시트 결합물.
                    추가 정보 없음.
     → 처리: 별도 코드/yaml 변경 없음. 기존 file mode 데이터가 정본임을
              docs/source_review/regime_source_review.md 에 명시.

  3. ECI_Neo_202603.xlsx
     → 운영자 확인: 동일.
     → 처리: 동일.

영향:
  - SAA/TAA/Final parity 검증 ⚠ 부분 한정 활성:
      Placement / Velocity / Regime classification = Phase C.5 PASS (이미 검증)
      SAA / TAA / Final weights 1:1 parity = DRM 해제 불가능 → 검증 영구 보류
                                              (운용역 결정 필요시 별도 candidate)
  - GlidePath 다중 vintage = yaml 신설 후 metadata 로 보존 (실제 vintage 별
    portfolio 산출은 후속 Phase)

승인일: ____________ (운용역)
─────────────────────────────────────────────────────────────────────────
```

### 2.2 D-08 status 변경안

| 항목 | 변경 전 | 변경 후 |
|---|---|---|
| status | `pending_external` | **`closed`** |
| description | Excel DRM 해제 (3건) | Excel DRM 3건 — 운영자 직접 정보 + 기존 file 모드 데이터로 대체 closure |
| 분포 | open 2 / pe 3 / closed 7 | open 2 / **pe 2** / **closed 8** |
| Phase D blocker | D-08 / D-09 (2건) | **D-09 (1건)** |

### 2.3 D-08 closure 시 변경 예정 파일

| # | 파일 | 변경 |
|---|---|---|
| 1 | `tdf_engine/config/glidepath.yaml` (신설) **또는** `tdf_engine/config/tdf_2060.yaml::glidepath_reference` 추가 | 4 vintage 주식 편입비 metadata: 2060=0.80 / 2050=0.70 / 2040=0.60 / 2030=0.50 |
| 2 | `docs/investment_decision_register.md` | D-08 status `pending_external → closed` + 본문 + 분포 + blocker + 변경 이력 |
| 3 | `HANDOFF.md` | blocker 2건 → 1건 |
| 4 | `memory/project_state.md` | closure 기록 |
| 5 | `docs/source_review/regime_source_review.md` (또는 `source_file_inventory.md`) | RegimeAnalysis/ECI_Neo xlsx 가 기존 file 의 결합물임을 명시 |

### 2.4 glidepath yaml 구조 옵션

**옵션 A — 별도 yaml** (권장):
```yaml
# tdf_engine/config/glidepath.yaml — 신설
# 운영자 수령 정보 (2026-05-08, D-08 closure):
# DRM 보호 xlsx (`0. 정리 - GlidePath 값.xlsx`) 의 핵심 정보를 metadata 로 보존.
# 본 단계에서는 reference 만. 다중 vintage 산출은 후속 Phase.
glidepath_reference:
  source: "운영자 직접 정보 (DRM xlsx 해제 불가)"
  as_of: "2026-05-08"
  unit: "주식 편입비 (equity bucket weight)"
  vintages:
    "2060": 0.80   # 현재 산출 대상 vintage (tdf_2060.yaml::strategic_allocation 와 정합)
    "2050": 0.70
    "2040": 0.60
    "2030": 0.50
  fixed_income_implied:    # 100% - 주식. (alternative bucket 도입 전 기준)
    "2060": 0.20
    "2050": 0.30
    "2040": 0.40
    "2030": 0.50
  enforced: false          # Phase D relaxed_diagnostic — reference only
  notes: |
    - 본 정보는 DRM 보호 파일의 metadata 대체.
    - 현재 단계에서는 2060 vintage 만 산출 (tdf_2060.yaml). 나머지 3 vintage 는
      reference 로만 보존. 다중 vintage 엔진은 후속 Phase.
    - tdf_2060.yaml::strategic_allocation (equity 0.80) 과 정합 ✓.
```

**옵션 B — `tdf_2060.yaml::glidepath_reference`** (단일 파일 통합):
- 기존 yaml 에 키 추가만. 신규 파일 없음. 단 yaml 파일이 더 길어짐.

**옵션 A 추천** — 다중 vintage 정보가 단일 vintage yaml (tdf_2060) 에 들어가는 구조 모순 방지.

### 2.5 D-08 변경하지 않을 것

- ✗ `tdf_engine/` 코드 (glidepath yaml 은 reference metadata. 코드에서 읽지 않음)
- ✗ 기존 `tdf_2060.yaml::strategic_allocation` (equity 0.80 / fixed_income 0.20 그대로 — glidepath_reference.2060 과 정합)
- ✗ `tests/`
- ✗ `out/` 산출물
- ✗ Decision Register total count (14 무변경)

---

## 3. D-09 Closure Plan

### 3.1 D-09 sign-off 문구

```
─────────────────────────────────────────────────────────────────────────
D-09 — regimeAnalysis_rt 정의

원래 closure 조건: 운영자가 region / annualization / regime base 정의 명시
실제 상황:        별도 정의 자료 없음. 파일 자체가 정의.
대체 closure 사유: Advisory/regimeAnalysis_rt 파일이 정본 정의.
                   Phase C.5 의 xfail 1건은 "정의 미명시" 가 아니라
                   "파일 자체를 정의로 인정" 으로 해소.

처리:
  - 파일 위치: Advisory/regimeAnalysis_rt (텍스트, file mode 사용 중)
  - 정의 명시 방식: 파일 자체 = canonical definition
  - tests/test_phase_c5_golden_parity.py 의 xfail 1건 검토:
      현재 xfail = "regimeAnalysis_rt 정의 미명시 — Regime 1/2/3/4 별
                  자산 평균수익률의 region/annualization/regime base 미공개"
      처리 옵션:
        (a) xfail 유지 + 사유 갱신 ("DRM 자료 부재. 파일 자체가 정의")
        (b) xfail 제거 (testcase 자체가 의미 없음 — 정의 자료가 영구히 없음)

승인일: ____________ (운용역)
─────────────────────────────────────────────────────────────────────────
```

### 3.2 D-09 status 변경안

| 항목 | 변경 전 | 변경 후 |
|---|---|---|
| status | `pending_external` | **`closed`** |
| description | `regimeAnalysis_rt` 정의 | `regimeAnalysis_rt` 정의 — 파일 자체가 정본 (운영자 확인) |
| 분포 (D-08 + D-09 함께 closure 시) | open 2 / pe 3 / closed 7 | open 2 / **pe 1** / **closed 9** |
| Phase D blocker (D-08 closure 후) | D-09 (1건) | **0건 — Phase D 종료 후보** |

### 3.3 D-09 closure 시 변경 예정 파일

| # | 파일 | 변경 |
|---|---|---|
| 1 | `docs/investment_decision_register.md` | D-09 status `pending_external → closed` + 본문 + 분포 + blocker + 변경 이력 |
| 2 | `HANDOFF.md` | blocker 1건 → **0건** (D-08 closure 후) |
| 3 | `memory/project_state.md` | closure 기록 |
| 4 | `docs/golden_answer_validation.md` §5.4 또는 신설 섹션 | "regimeAnalysis_rt 파일이 정본 정의. 추가 자료 없음" 명시 |
| 5 | `tests/test_phase_c5_golden_parity.py` xfail 1건 | sign-off 옵션 (a) 사유 갱신 또는 (b) 제거. **권장 = (a)** (xfail 유지, 사유를 "DRM 부재로 추가 정의 자료 없음" 으로 갱신) |

### 3.4 D-09 변경하지 않을 것

- ✗ `tdf_engine/` 코드 (regime/regime_return 산출 로직 무변경)
- ✗ `tdf_engine/config/*.yaml` (regime_source / regime_return_source 그대로)
- ✗ `out/` 산출물
- ✗ Decision Register total count (14 무변경)

---

## 4. 통합 patch 영향 — D-08 + D-09 동시 closure 시

### 4.1 status distribution

```
변경 전 (현재):           open 2 / pe 3 / pr 0 / dfd 2 / closed 7  = 14
D-08 only closure:        open 2 / pe 2 / pr 0 / dfd 2 / closed 8  = 14
D-08 + D-09 closure:      open 2 / pe 1 / pr 0 / dfd 2 / closed 9  = 14
```

### 4.2 Phase D blocker

```
변경 전: D-08 / D-09  (2건)
D-08 only: D-09       (1건)
D-08 + D-09: —        (0건. Phase D 종료 조건 만족 후보)
```

### 4.3 Phase D 종료 조건 (D-08 + D-09 둘 다 closure 시)

`docs/phase_d_declaration.md §5` 의 Phase D 종료 조건:
- ✅ Decision Register blocker 항목 (D-01/02/03/08/09/10/11/12) 모두 closed → **충족 (D-08+D-09 closure 시)**
- ⏳ `final_asset_bounds` 운영값 적용된 산출이 운용역 사인 → relaxed_diagnostic 정책상 final_asset_bounds 비활성. 본 조건은 Phase D 종료 시점에 재해석 필요 (별도 결정).

따라서 D-08 + D-09 closure 후 Phase D 종료 여부는 운용역 별도 결정.

---

## 5. 운용역 승인 요청 — 4 옵션

| 옵션 | 의미 | 후속 |
|---|---|---|
| **A. D-08 + D-09 동시 closure** | 두 항목 모두 closed. blocker 0건. | §2 + §3 patch 동시 적용. glidepath.yaml 신설. |
| B. D-08 만 closure | DRM 3건 해소 + glidepath yaml 신설. blocker 1건 (D-09). | §2 patch 만. D-09 는 별도 검토. |
| C. D-09 만 closure | regimeAnalysis_rt 파일 = 정본 명시. blocker 1건 (D-08). | §3 patch 만. D-08 는 별도 검토. |
| D. 둘 다 보류 | 추가 검토 후 결정. | 둘 다 pending_external 유지. |

### 5.1 본 plan 의 추천 = **옵션 A (동시 closure)**

근거:
1. 외부 자료 의존이 두 항목 모두 운영자 정보 수령으로 해소
2. blocker 0건 → Phase D 종료 조건 한 단계 진입
3. glidepath 정보가 yaml 에 명시되어 후속 다중 vintage Phase 진입 시 출발점 확보
4. test_phase_c5 xfail 1건의 사유가 명확해짐 (DRM 영구 불가)

---

## 6. 본 plan 까지의 변경

**없음**. 본 turn 은 plan 만.

- ✗ `tdf_engine/` 코드 무변경
- ✗ `tdf_engine/config/*.yaml` 무변경 (glidepath.yaml 신설 plan 만)
- ✗ `tests/` 무변경
- ✗ `out/` 산출물 무변경
- ✗ `docs/investment_decision_register.md` D-08/D-09 status 무변경 (둘 다 pending_external)
- ✓ `docs/phase_d_d08_d09_closure_plan.md` 신설만

승인 시 별도 turn 에서 §2 / §3 patch 4~5 파일 적용.

---

## 7. 한 줄 요약

> **D-08 / D-09 외부 자료 의존이 운영자 정보 수령 (2026-05-08) 으로 해소.
> DRM 자체는 풀 수 없으나, GlidePath = 운영자 직접 정보 (4 vintage 주식 비중),
> RegimeAnalysis/ECI_Neo = 기존 regime_*/regimeAnalysis_* file 의 결합물 = 추가 정보 없음.
> regimeAnalysis_rt = 파일 자체가 정의.
> → 두 항목 모두 closure 가능. 추천 = 동시 closure (Phase D blocker 0건).**
