# Phase D — TAA Tilt Design Review

작성일: 2026-05-08. **현재 TAA tilt rule 의 지위 / 적용 메커니즘 / 향후 개선 후보** 를 단일 문서로 정리.
코드 / config / test 변경 없음.

> **결론 미리**: 현재 `taa_policy.yaml::regime_tilts` 는 **prototype operator-defined heuristic**.
> 최종 quantitative TAA 모델 또는 second-stage optimizer 가 **아니다**. 본 단계에서는 그대로 유지.

---

## 1. 현재 TAA rule 의 지위

| 측면 | 분류 | 의미 |
|---|---|---|
| 형식 | **prototype** | 백테스트로 검증된 운영값이 아님. 초안 (draft). |
| 도출 방식 | **operator-defined heuristic** | regime 별 자산군 부호·강도를 운영자가 정성 판단으로 설정. |
| 위치 | config-driven (`taa_policy.yaml::regime_tilts`) | code 하드코딩은 아님. 단 수치 자체는 휴리스틱. |
| 모델 종류 | **NOT a final quantitative TAA model** | 통계/계량 모델로 도출된 tilt 가 아님. |
| 알고리즘 | **NOT a second-stage optimizer** | TAA target 을 별도 최적화로 풀지 않고 단순 overlay. |
| 위상 | diagnostic / workflow validation 용 | regime → tilt → projection → portfolio 흐름의 정합성 검증용. |

### 1.1 사용자 정책 명시 문구 (영문 원문 보존)

본 문서가 운용역 / 외부 검토자 / 후속 Phase 에 전달할 때 **그대로 인용** 가능한 핵심 명제:

> - **"Current regime_tilts are prototype operator-defined rules."**
> - **"They are used for diagnostic and workflow validation."**
> - **"Final TAA methodology may later be replaced by regime-confidence scaling or optimization-based TAA."**

### 1.2 본 단계에서 하지 않는 것 (명시)

- TAA optimizer 구현 (objective / constraints 정의 후 별도 풀이)
- regime confidence scaling (regime label → confidence score 로 tilt 강도 가중)
- signal-based TAA (시장 지표를 입력으로 받는 dynamic tilt)
- `taa_policy.yaml::regime_tilts` 의 **수치 자체** 변경
- `bucket_tilts` 의 실제 적용 (현재 코드 미적용 상태 유지)

---

## 2. 현재 적용 메커니즘

### 2.1 공식

```
TAA target = SAA + asset_tilts          (regime 별)
```

`tdf_engine/taa/overlay.py::TAAOverlayEngine.apply` (line 53-65) 발췌:

```python
tilts = pd.Series(0.0, index=saa_weights.index, name="tilt")
for k, v in tilt_def.asset_tilts.items():
    if k in tilts.index:
        tilts.loc[k] = float(v)

# residual (sum ≠ 0) 이면 모든 자산에 균등 분배 (cash-neutral 보정)
residual = float(tilts.sum())
if abs(residual) > 1e-12:
    adj = -residual / float(len(tilts))
    tilts = tilts + adj

target = saa_weights + tilts
```

핵심 동작:
- `asset_tilts` 의 **명시 자산만** SAA 에 더함. 미명시 자산은 tilt = 0.
- `asset_tilts` 합 ≠ 0 이면 모든 자산에 균등 분배로 cash-neutral 보정.
- 합 = 0 (현재 4 regime 모두 그러함) → residual 보정 미발동.
- 결과 target 은 sum-to-100% 보장 (Phase D 정책 #6).

### 2.2 bucket_tilts 의 위상 — **미적용 metadata**

`taa_policy.yaml::regime_tilts.<regime>.bucket_tilts` 는 yaml 에 정의되어 있으나
**overlay 코드에서 읽지 않음** (위 §2.1 코드 참조).

| regime | bucket_tilts (yaml) | overlay 적용 여부 |
|---:|---|:---:|
| 1 (확장/가속) | equity +5%p / fixed_income −5%p | ❌ 미적용 |
| 2 (회복/개선) | equity +3%p / fixed_income −3%p | ❌ 미적용 |
| 3 (둔화/침체) | equity −5%p / fixed_income +5%p | ❌ 미적용 |
| 4 (후기/감속) | equity +1%p / fixed_income −1%p | ❌ 미적용 |

**용도**: 정책 의도 표기용 metadata.
- 운영자 / 운용역이 regime 별 큰 그림 (위험자산 vs 안전자산 방향성) 을 한눈에 파악
- asset_tilts 가 운영자가 의도한 bucket 방향과 정합한지 사람이 검토할 때 참고
- **코드 동작에는 영향 없음**

**현재 4 regime 모두 asset_tilts 합 = 0** 이므로 bucket_tilts 적용 여부와 무관하게 cash-neutral.

### 2.3 sum-to-100% 회계 정합성

`taa_policy.yaml::constraints.tilt_sum_must_be_zero: true` 는 정책 제약이 아닌
**sum-to-100% 회계 정합성 장치** (Phase D D-01 §4.1 영구 기록).

- SAA 합 = 1.0 + tilt 합 = 0 → TAA 합 = 1.0 (정책 #6 보장)
- false 로 풀면 별도 normalization 로직 필요 — 현재 미구현. 본 단계 변경 없음.

### 2.4 per_asset_max_tilt 의 위상

`taa_policy.yaml::constraints.per_asset_max_tilt: 1.0` (Phase D relaxed 시 1.0 으로 완화).
- relaxed_diagnostic 시점: **사실상 비제약** (1.0 = 100%p, ineq trivially 만족).
- production 전환 시 yaml 1줄 (예: 0.03) 으로 복원하면 재활성.
- 본 단계 변경 없음.

---

## 3. 4 regime asset_tilts 요약 (수치 변경 없음, 참조용)

상세는 `docs/phase_d_d02_drift_closure_brief.md` 및 별도 표 (이전 turn 응답) 참조. 본 문서는 지위 명시.

| regime | label | risk_on bias | safe_asset bias | tilt 강도 |
|---:|---|:---:|:---:|:---:|
| 1 | 확장 / 가속 | em+kr_eq+hy 강화 (+5%) | ust30/kr_t10 약화 (−5%) | 강 (sum=±5%) |
| 2 | 회복 / 개선 | em+hy 강화 (+3%) | kr_aggregate/kr_t10 약화 (−3%) | 중 (sum=±3%) |
| 3 | 둔화 / 침체 | kr_eq+em+hy 약화 (−5%) | ust30+kr_aggregate 강화 (+5%) | 강 (sum=±5%) |
| 4 | 후기 / 감속 | us_growth/value/dm_ex_us +3%, kr_eq/em −3% | (안전자산 변경 없음) | 약 (sum=±3% 이내) |

각 regime asset_tilts 합 = 0 ✓ (cash-neutral 자체 만족).

---

## 4. 향후 개선 후보 (본 단계 미구현, 후속 Phase)

본 candidate 는 **정식 Decision Register 항목 아님** — Phase D D-02 brief / D-15~17 candidate 와 동일한
"future enhancement" 위상. 정식 등록은 별도 결정.

| candidate | 영역 | 후속 Phase 검토 사항 |
|---|---|---|
| **TAA candidate-A** | regime confidence scaling | regime classifier 의 confidence (예: P, V 의 magnitude) 를 입력으로 받아 tilt 강도를 스케일. 약한 신호 → 작은 tilt, 강한 신호 → 큰 tilt. 현재 binary regime → fixed tilt 구조 대체. |
| **TAA candidate-B** | optimization-based TAA | TAA target 을 SAA + tilt 단순 합이 아닌 별도 최적화로 풀이. objective: regime expected return ↔ tracking error to SAA tradeoff. constraint: bucket bound / per-asset band. |
| **TAA candidate-C** | signal-based TAA | macro/시장 지표 (PMI, credit spread, yield curve 등) 를 입력으로 dynamic tilt 산출. regime 라벨 의존도 ↓. |
| **TAA candidate-D** | bucket_tilts 활성화 | 현재 metadata only 인 bucket_tilts 를 코드에서 실제 적용. asset_tilts 와 결합 방식 (additive vs proportional) 정의 필요. |
| **TAA candidate-E** | tilt 백테스트 / parameter sensitivity | 4 regime × 9 자산 tilt 의 백테스트 검증. parameter sweep 으로 regime label 변경 빈도 / drawdown 영향 분석. |

⚠️ 본 5 candidate 모두 본 Phase D 의 우선순위가 아님. 후속 Phase 진입 시점에 운용역 결정 후 정식화.

---

## 5. 본 단계 우선순위 (TAA tilt 변경 없이 진행)

```
1. D-02 sign-off                               (운용역 승인 대기 — phase_d_d02_signoff_patch_plan.md §1)
2. D-03 lookback policy                        (open. 자산별 차등 vs 일괄 통일 결정 필요)
3. D-08 Excel DRM 해제                          (pending_external — 운영자)
4. D-09 regimeAnalysis_rt 정의                  (pending_external — 운영자)
5. relaxed_diagnostic output governance        (운영 절차 / 검토 주기 / sign-off 문서화)
```

각 항목은 **TAA tilt 수치 / 메커니즘 변경 없이** 진행. TAA 관련 작업은 Phase D 종료 후 별도 Phase 에서 검토.

---

## 6. 본 단계 금지 사항 (재확인)

본 turn 까지의 약속을 명시 기록 (위반 방지용).

- ✗ TAA optimizer 구현
- ✗ regime confidence scaling 구현
- ✗ signal-based TAA 구현
- ✗ `taa_policy.yaml::regime_tilts.<regime>.asset_tilts` 의 **수치 자체** 변경
- ✗ `bucket_tilts` 의 **실제 적용** (현재 코드 미적용 상태 유지)
- ✗ Decision Register **total count 변경** (현재 14 유지). 단 본 문서에서 candidate 언급은 가능.
- ✗ TAA tilt 가 **production 운영값으로 검증되었다는 표기** 금지 — 항상 prototype / heuristic 으로 명시.

---

## 7. 한 줄 요약

> **현재 `regime_tilts` 는 prototype operator-defined heuristic. 적용 공식 = `TAA target = SAA + asset_tilts`.
> `bucket_tilts` 는 metadata only (코드 미적용). 최종 quantitative TAA / second-stage optimizer 가 아니며,
> 향후 Phase 에서 regime-confidence scaling 또는 optimization-based TAA 로 대체 검토.**
