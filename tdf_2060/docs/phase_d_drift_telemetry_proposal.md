# Phase D — D-02 Drift Telemetry & Quality Threshold 구조 재검토

작성일: 2026-05-08. **변경안 / 분석만**. 코드 / config / test 변경 없음. 운용역 승인 후 별도 PR로 적용.

> 목적: relaxed mode 에서 projection_used=True 가 그대로 발생하는데 (regime 1 의 ust30 −3%p / kr_t10 −2%p tilt
> 가 long-only 에 의해 0% 로 clipping), 이 drift 를 단순 accept 하지 않고 명시 telemetry 로 관리.
> 또한 quality.py 의 global default threshold (1.0) 변경이 위험할 수 있다는 지적에 대한 재구조화안.

---

## 1. 현재 telemetry 인벤토리 (이미 노출됨)

`taa_diagnostics.taa_feasibility` 블록 (`out/db_*/portfolio_*.json`):

| 필드 | 의미 | 현재 |
|---|---|---|
| `projection_used` | bool | ✓ |
| `projection_success` | bool | ✓ |
| `projection_message` | str | ✓ |
| `target_weights_before_projection` | dict[asset_key, weight] | ✓ (= pre_projection_weight by asset) |
| `final_weights_after_projection` | dict[asset_key, weight] | ✓ (= post_projection_weight by asset) |
| `negative_weight_assets_before_projection` | dict[asset_key, weight] | ✓ |
| `clipped_weight_total` | float | ✓ (음수 weight 들의 합 절대값. = negative_magnitude **(이미 있음)**) |
| `bucket_weights_before_projection` | dict[bucket, sum] | ✓ |
| `bucket_weights_after_projection` | dict[bucket, sum] | ✓ |
| `asset_weight_drift_from_target` | dict[asset_key, drift] | ✓ (= projection drift by asset) |
| `max_abs_projection_drift` | float | ✓ |
| `constraints_after_projection` | dict | ✓ |

> 사용자 요청 항목 7개 중 6개 이미 존재. 누락은 1개: **drift 가 long-only clipping 에서 왔는지 여부**.

---

## 2. 누락 telemetry — 신규 필드 제안

### 2.1 `drift_source` per asset

각 자산의 projection drift 가 어디서 왔는지 분류:

| source 값 | 의미 |
|---|---|
| `long_only_clipping` | target<0 인 자산이 0% 로 clip 됨 (현 relaxed 정책의 주요 원인) |
| `bucket_constraint` | bucket bound 강제로 인한 재분배 (현 relaxed 에서 bucket [0,1] → 발생 거의 안 함) |
| `asset_upper_bound` | per-asset upper bound 도달 (현 relaxed 에서 [0,1] → 발생 안 함) |
| `redistribution_from_others` | 다른 자산이 clip 되며 sum=1 유지 위해 본 자산이 받은 spillover |
| `none` | drift = 0 |

**구현 위치**: `tdf_engine/taa/projection.py` 의 `project_to_feasible` 결과를 `ProjectionDiagnostics` 에 추가. 분류 로직:
- target_i < 0 이고 final_i ≈ 0 → `long_only_clipping`
- target_i 가 bucket bound 안인데 final_i 가 더 작거나 큰 → `bucket_constraint` (현 relaxed 에서는 발생 X)
- target_i 가 asset bound 안인데 final_i 가 다름 → `asset_upper_bound` 또는 `redistribution_from_others`
- |drift_i| < 1e-9 → `none`

### 2.2 `projection_clipping_summary`

projection 직후 한눈 요약:

```python
{
    "n_assets_clipped_long_only": 2,           # ust30, kr_t10
    "total_long_only_clipping_magnitude": 0.05, # |−0.03| + |−0.02|
    "max_long_only_clipping": 0.03,            # ust30 −3%
    "redistribution_total": 0.05,              # 0% 가 된 자산의 weight 가 다른 자산에 분배된 총량
    "redistribution_by_recipient": {           # 누가 받았는지
        "kr_equity": -0.0071,
        "us_growth_equity": -0.0071,
        ...
    },
    "drift_came_from_long_only_clipping": True,  # 명시 플래그
}
```

### 2.3 review packet rendering

reporting/review.py 의 `projection_summary` 또는 별도 §3.1 Section 으로 노출:

```markdown
### 3.1 Projection clipping breakdown

| asset_key | pre | post | drift | source |
|---|---:|---:|---:|---|
| us_treasury_30y | -3.0000% | +0.0000% | +3.0000% | long_only_clipping |
| kr_treasury_10y | -2.0000% | +0.0000% | +2.0000% | long_only_clipping |
| us_growth_equity | +40.0000% | +39.2857% | -0.7143% | redistribution_from_others |
...

> drift_came_from_long_only_clipping = True (총 5%p clipping → 다른 자산에 분배)
```

이를 통해 운용역이 drift 가 "정책상 정상" (long_only 보장) 인지 "이상 신호" (asset bound / bucket 강제) 인지 즉시 판단 가능.

---

## 3. quality threshold 구조 재검토

### 3.1 현재 상태 (Phase D relaxed 적용 시점)

| 항목 | 위치 | 값 | 문제 |
|---|---|---|---|
| `DEFAULT_ASSET_DRIFT_THRESHOLD` | `quality.py:29` (module global) | **1.0** (이전 0.03) | 다른 mode (production) 에서 수입 시 잘못된 default |
| `DEFAULT_BUCKET_DRIFT_THRESHOLD` | `quality.py:30` (module global) | **1.0** (이전 0.05) | 동일 |
| 사용처 | `builder.py` `__init__` 의 default kwarg | DEFAULT_*를 임포트 | yaml 무시, 항상 module global 사용 |

**위험**: module global 변경은 모든 import 에 영향. relaxed 의도와 무관한 production 코드 path 에서도 1.0 을 받아 drift 를 영구 무시.

### 3.2 제안 구조 — 4단 옵션

#### 옵션 A — config-driven thresholds (권장)

1. `quality.py` global default 를 **0.03 / 0.05 로 복원** (Phase B.5+ 운영값).
2. `tdf_2060.yaml` 에 신규 키 `drift_thresholds`:
   ```yaml
   drift_thresholds:
     asset: 0.03            # operating_mode=production 의 운영값 (참고)
     bucket: 0.05
     enforcement: telemetry_only   # production | warning | review_required_threshold | telemetry_only
   ```
3. `portfolio/builder.py` 의 `__init__` 이 yaml 의 `tdf_config["drift_thresholds"]` 를 우선 사용 (없으면 global default).
4. `portfolio/quality.py::evaluate_quality` 가 enforcement 모드를 받아:
   - `production` / `warning` / `review_required_threshold`: 기존 동작 (drift > threshold → review_required)
   - `telemetry_only`: drift 값을 report 에는 포함하되 quality_status 분기에서 제외
5. relaxed 시점 yaml: `enforcement: telemetry_only` → drift 의 fail/warning 분기 비활성, telemetry 표시는 유지.
6. D-02 는 `pending_rerun` 유지. relaxed rerun 결과 분포를 수개월 모니터링 후 production threshold 확정 시 closed.

**테스트 영향**:
- `test_phase_b5plus_quality::test_quality_status_review_required_when_drift_exceeds_threshold` 가 explicit threshold 전달 중 → 그대로 통과.
- 기존 default 인용 부분 (`assert drift < DEFAULT_ASSET_DRIFT_THRESHOLD`) — 0.03 으로 복원되면 자연 통과 (relaxed 산출의 drift 0~3% 가 0.03 와 거의 같음, 작은 epsilon 으로 통과).

#### 옵션 B — module global 복원 + relaxed override 인자

1. `quality.py` global 0.03 / 0.05 복원.
2. `evaluate_quality` 호출자 (`builder.py`) 가 mode-aware override 만 명시 전달.
3. yaml 변경 없음, 코드 변경만.

장점: yaml 없이도 가능. 단점: 호출자가 mode 를 알아야 → 결합도 ↑.

#### 옵션 C — 현재 유지 (1.0)

장점: 즉시 effort 0. 단점: production 시점에 다시 손봐야 함. 다른 코드가 import 시 영향.

#### 옵션 D — drift threshold 자체 폐기, telemetry only

1. `quality.py` 의 drift 분기 자체 제거.
2. quality_status 는 fallback / cash_placeholder / no_candidates / projection_failure 로만 분기.
3. drift 는 review packet 의 telemetry section 으로만 노출.
4. D-02 closed 가능 (분기 자체 없음).

장점: 가장 단순. 단점: production 시점에 drift 임계 분기를 다시 넣을 때 코드 추가 필요.

### 3.3 추천

**옵션 A (config-driven)**. 이유:
- Phase D relaxed → production 전환 시 yaml 1줄 변경 (`enforcement` 값) 만으로 동작 전환.
- module global 0.03/0.05 복원 → 다른 코드 import 시 안전한 default.
- D-02 pending_rerun 의 의미 유지 (rerun 후 production threshold 확정 시 yaml 갱신 + closed).
- relaxed 시점은 `enforcement: telemetry_only` 로 명시 → "임시 비활성" 의도가 yaml 에 명시되어 추적 가능.

### 3.4 변경 범위 (옵션 A 채택 시)

| 파일 | 변경 |
|---|---|
| `tdf_engine/portfolio/quality.py` | DEFAULT 1.0 → 0.03 / 0.05 복원. `evaluate_quality` 가 `enforcement` 인자 받음 (`production` / `telemetry_only` 등). drift 분기를 enforcement 에 따라 조건부. |
| `tdf_engine/config/tdf_2060.yaml` | `drift_thresholds: {asset, bucket, enforcement}` 신규 키. relaxed 시점 `enforcement: telemetry_only`. |
| `tdf_engine/portfolio/builder.py` | yaml 의 drift_thresholds 를 `evaluate_quality` 로 전달. |
| `tdf_engine/reporting/review.py` | `enforcement: telemetry_only` 일 때 review packet 의 quality 섹션에 "drift threshold disabled (Phase D relaxed)" 표기. |
| `tests/` | `test_phase_b5plus_quality` 의 explicit threshold=0.03 → default 와 동일하므로 unchanged. 신규 test: `test_quality_threshold_telemetry_only_mode` 추가 권장. |

### 3.5 D-02 status 매트릭스

| 시점 | yaml `enforcement` | DEFAULT | quality_status 분기 |
|---|---|---|---|
| Phase D relaxed (현재) | `telemetry_only` | 0.03 / 0.05 (복원) | drift 무시. telemetry 만. |
| relaxed rerun 분석 후 | `warning` | 0.03 / 0.05 | drift > threshold → warning |
| production 확정 | `production` | 0.03 / 0.05 (또는 운용역 결정값) | drift > threshold → review_required |

D-02 는 production 단계 yaml 확정 시 closed.

---

## 4. 변경 우선순위 / 순서

| # | 작업 | 추정 영향 |
|---|---|---|
| 1 | 옵션 A 의 yaml `drift_thresholds` 키 + builder.py / quality.py 변경 | 코드 + yaml 작은 변경. 테스트 1건 추가. |
| 2 | projection.py `drift_source` 분류 + ProjectionDiagnostics 확장 (§2) | 코드 변경 + diagnostics 스키마 확장. test_phase_c3_projection 갱신 |
| 3 | reporting/review.py 의 §3.1 Projection clipping breakdown 신설 (§2.3) | 표현 보강. 테스트 영향 없음. |
| 4 | review packet 의 quality 섹션에 enforcement 모드 표기 | 표현 보강. |

---

## 5. 본 turn 까지의 변경 vs 본 문서가 제안하는 변경

| 변경 | 본 turn (적용됨) | 본 문서 제안 (미적용) |
|---|---|---|
| `quality.py DEFAULT_*_THRESHOLD = 1.0` | ✓ | → **0.03 / 0.05 복원** (옵션 A) |
| yaml `drift_thresholds` 키 | ✗ | → **신설** |
| `evaluate_quality` enforcement 인자 | ✗ | → **신설** |
| `projection.py drift_source` 분류 | ✗ | → **신설** |
| review packet projection clipping breakdown | ✗ | → **신설** |
| review packet operating_mode banner | ✓ (본 turn) | (유지) |

본 문서의 §2 (drift telemetry) 와 §3 (옵션 A) 는 **사용자 승인 후 별도 PR** 로 진행 권장.

---

## 6. 결론 / 다음 단계

| Decision | 권장 |
|---|---|
| D-02 status | **`pending_rerun` 유지** (현 상태 정합) |
| drift threshold 구조 | **옵션 A 채택 후 별도 PR** (yaml-driven, telemetry_only 모드 추가) |
| projection.py drift_source | **별도 PR 로 추가** (운용역의 drift 출처 판별 도구) |
| review packet | operating_mode banner 는 본 turn 적용 완료. clipping breakdown 은 별도 PR. |
