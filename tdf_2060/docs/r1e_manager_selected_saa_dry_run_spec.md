# R-1E — Manager-Selected SAA Dry-Run Wiring Spec

작성일: 2026-05-13. **spec only.** 코드 / config / tests / 산출물 / Decision Register
변경 0. R-1A 와 동일 패턴 — 다음 구현자가 바로 읽고 R-1E 구현 가능한 수준.

> **Phase D completed register-blocker resolution only.
> This does not mean production readiness. The engine remains in relaxed_diagnostic mode.**

> **R-1E 는 production wiring 이 아니라 dry-run contract 정의.**
> 운용역이 Final Manager Review Packet (R-track 최종) 에서 선택한 candidate 를
> downstream SAA / TAA / product selection 흐름에 어떻게 연결할지를 **계약** 으로
> 명문화하되, 실제 production 반영은 별도 sign-off 후로 미룬다.

---

## 0. TL;DR

| 항목 | 결정 |
|---|---|
| **Scope** | spec 작성만. 구현 / config / tests / output 생성 **금지**. |
| **출력 (R-1E)** | 본 문서 1건. |
| **다음 단계 (R-1F)** | `tdf_engine/optimization/manager_selected_saa.py` + CLI + tests + dry-run JSON dump |
| **방향성** | 운용역 명시 선택 → validation → dry-run JSON dump (production_applied=false) → 별도 sign-off 이후에만 production 반영 검토. |
| **자동 선택** | **금지**. ETF/Fund 각각 운용역 candidate_id 명시 입력 필수. |
| **Production 영향** | 0. 본 spec 및 후속 R-1F dry-run 모두 production allocation / TAA / product selection / config / Decision Register / E-series baseline 변경 없음. |

---

## 1. Purpose

R-track 의 목적은 **SAA 자동 선택이 아니라 운용역 선택 보조**다.

- R-1A ~ Final Manager Review Packet 까지 모든 산출은 **후보 집합 + 비교 + 검토표**
  제공이 끝이었다. 자동 final SAA 확정 0.
- R-1E 는 운용역이 **명시적으로** 선택한 candidate_id 를 받아, downstream (TAA overlay
  + projection + product selection + portfolio builder) 에 **연결할 수 있는지** 만
  검증하고 dry-run JSON 으로 dump 한다.
- **production allocation 반영은 본 R-1E 범위 밖**. 별도 사용자 sign-off + 운용역
  서명 + Decision Register 신규 entry 후로 미룬다.

핵심 명제:
> **운용역이 선택하기 전에는 downstream 변경 없음.**
> **운용역이 선택해도 dry-run 까지만. production 은 별도 sign-off.**

---

## 2. Manager Selection Input Contract

운용역 입력은 명시적 / 기록 가능 / 재현 가능 / 검증 가능해야 한다.

### 2.1 Schema (YAML 예시)

```yaml
manager_selection:
  portfolio_type: "etf"                    # "etf" | "fund"
  candidate_id: "cand_008421"              # opportunity_set JSON 의 sampled candidate id
  selected_by: "kim_solution1212@..."      # 운용역 식별자 (이메일 / 사번 / 별칭)
  selected_at: "2026-05-13T10:30:00+09:00" # ISO8601 datetime (timezone 필수)
  selection_reason: "us_growth tilt 정합, max_w 25.6% 운용 정책 내 수용 가능"
  manager_view_notes:                      # 자유 텍스트 (배경 / 정성 view)
    - "macro view: us large-cap growth 우호적 (Q3-Q4)"
    - "em 14% 는 신흥국 view 와 정합"
    - "HY 10% 는 credit cycle 후반부 부담 — 차후 TAA 로 조정 검토"
  source_review_packet:                    # 본 선택의 근거 review packet 경로 / sha256
    path: "out/db_review_relaxed_e62/saa_opportunity_set/20260513/saa_opportunity_set_final_manager_review_20260513.md"
    sha256: "<sha256 hex of review packet>"
  allow_downstream_dry_run: true           # false 면 R-1F dry-run 실행 금지
```

### 2.2 JSON 등가 (CLI / 시스템 입력용)

```json
{
  "manager_selection": {
    "portfolio_type": "etf",
    "candidate_id": "cand_008421",
    "selected_by": "...",
    "selected_at": "2026-05-13T10:30:00+09:00",
    "selection_reason": "...",
    "manager_view_notes": ["..."],
    "source_review_packet": {"path": "...", "sha256": "..."},
    "allow_downstream_dry_run": true
  }
}
```

### 2.3 ETF / Fund 동시 선택 (옵션)

`manager_selection_set` 형태로 ETF / Fund 를 동일 또는 다른 candidate_id 로 입력
가능:

```yaml
manager_selection_set:
  - portfolio_type: "etf"
    candidate_id: "cand_008421"
    # ... 동일 필드
  - portfolio_type: "fund"
    candidate_id: "cand_008421"   # 동일 또는 다른 id
    # ...
```

R-1F 구현 시 두 경우 (single / set) 모두 지원.

---

## 3. Validation Rules

선택 candidate 가 dry-run 진입 자격을 갖는지 검증. 모든 rule **fail-fast** —
하나라도 실패하면 dry-run JSON 생성 거부.

### 3.1 Identity / Existence

| # | rule | 위반 시 |
|:---:|---|---|
| V-1 | `candidate_id` 가 `opportunity_set_<portfolio_type>_<as_of>.json::candidates` 에 존재 | ValueError("candidate_id not in opportunity set") |
| V-2 | candidate 가 **sampled** 후보 (= candidate_id 패턴 `cand_NNNNNN`) | ValueError("not a sampled candidate; reference points are not selectable") |
| V-3 | `candidate_id == "ref_max_sharpe"` 명시 차단 | ValueError("ref_max_sharpe is unconstrained MVO reference; not selectable") |
| V-4 | `candidate_id == "ref_80_20_equal_intra_bucket"` 명시 차단 (anchor 용, sampled 후보 아님) | ValueError("reference anchor not selectable as final SAA") |

### 3.2 Quality / Bucket Constraint

| # | rule | 위반 시 |
|:---:|---|---|
| V-5 | `feasibility_status == "feasible"` | ValueError("candidate is degenerate / not feasible") |
| V-6 | `equity_weight` ∈ [0.80 − tol, 0.80 + tol] (tol = 1e-9, R-1B.2 hard) | ValueError("bucket constraint violated: equity != 0.80") |
| V-7 | `fixed_income_weight` ∈ [0.20 − tol, 0.20 + tol] (tol = 1e-9) | ValueError("bucket constraint violated: fi != 0.20") |
| V-8 | weights sum ≈ 1.0 (tol = 1e-9) | ValueError("weights do not sum to 1") |
| V-9 | 모든 자산 weight ≥ 0 (long-only) | ValueError("negative weight detected") |

### 3.3 Hygiene / Anti-regression

| # | rule | 위반 시 |
|:---:|---|---|
| V-10 | candidate 에 **제거된 metric** (`bucket_distance_from_80_20`, `full_weight_distance_from_80_20_equal_bucket_reference`) 가 등장하지 않음 (R-1B.2 정합성) | ValueError("removed metric resurrected — schema regression") |
| V-11 | `source_review_packet.sha256` 가 실제 파일 hash 와 일치 (선택 근거 추적성) | ValueError("review packet sha256 mismatch — stale or modified") |
| V-12 | `selected_at` 가 `opportunity_set::meta.generated_at` 이후 | ValueError("selection timestamp predates opportunity set generation") |
| V-13 | `selected_by` 비어있지 않음 | ValueError("selected_by required") |
| V-14 | `selection_reason` 비어있지 않음 (정성 근거 강제) | ValueError("selection_reason required") |
| V-15 | `allow_downstream_dry_run == True` (false 면 dry-run JSON 생성 거부) | abort (no error, just no-op) |

### 3.4 Operating Mode Guard

| # | rule | 위반 시 |
|:---:|---|---|
| V-16 | 본 dry-run 은 `operating_mode == "relaxed_diagnostic"` 환경에서만 허용. production mode 환경에서는 거부 | ValueError("R-1E dry-run forbidden in production mode") |

---

## 4. Dry-Run Output Contract

검증 통과 시 별도 JSON 으로 dump. **production_applied = false** 가 본 산출의 핵심
signal.

### 4.1 Output path

```
out/db_review_relaxed_e62/saa_opportunity_set/<as_of_run>/manager_selected_saa_{portfolio_type}_<as_of_run>.json
```

ETF / Fund 가 동시 선택되면 2 파일 dump.

### 4.2 Schema (R-1F 구현 후 확정)

```yaml
manager_selected_saa:
  meta:
    schema_version: "r1e.1"
    generated_at: ISO8601
    operating_mode: "relaxed_diagnostic"
    production_applied: false                          # ★ 본 dump 의 핵심 단언
    sign_off_required_for_production: true

  selection_input:                                     # §2.1 schema 그대로 echo
    portfolio_type: "etf" | "fund"
    candidate_id: "cand_NNNNNN"
    selected_by: <str>
    selected_at: ISO8601
    selection_reason: <str>
    manager_view_notes: [<str>, ...]
    source_review_packet: {path: <str>, sha256: <str>}
    allow_downstream_dry_run: true

  selected_candidate:                                  # opportunity_set 에서 발췌
    candidate_id: "cand_NNNNNN"
    weights: {asset_key: float, ...}                   # 9 자산, sum=1
    expected_return: float
    volatility: float
    sharpe: float
    equity_weight: 0.80                                # hard
    fixed_income_weight: 0.20                          # hard
    max_asset_weight: float
    concentration_hhi: float
    equity_intra_hhi: float
    fixed_income_intra_hhi: float
    equity_max_asset_weight: float
    fixed_income_max_asset_weight: float
    mvo_efficiency_score: float
    feasibility_status: "feasible"
    overlap_score: int                                 # R-1C 에서 재계산

  validation_summary:
    rules_evaluated: 16                                # §3 의 V-1 ~ V-16
    rules_passed: 16
    rules_failed: 0
    bucket_constraint_check:
      equity_deviation_from_080: float                 # |eq - 0.80|
      fixed_income_deviation_from_020: float
    weight_sum_deviation_from_1: float
    removed_metric_check: "absent"                     # bucket_distance / full_weight_distance 미존재
    review_packet_sha256_match: true
    timestamp_after_opportunity_generation: true

  source_opportunity_json:
    path: <str>                                        # 입력 opportunity_set JSON 경로
    sha256: <str>                                      # 추적성

  downstream_dry_run_allowed: true
  downstream_dry_run_executed: false                   # §5 dry-run wiring 실행 여부
```

### 4.3 Naming Convention

- `manager_selected_saa_<portfolio_type>_<as_of_run>.json` — 운용역 선택 dump
- 추후 R-1F 에서 dry-run wiring 결과는 별도 파일:
  - `manager_selected_saa_<portfolio_type>_dry_run_result_<as_of_run>.json`

---

## 5. Downstream Wiring Design (dry-run only)

검증 통과 후, selected candidate 의 weights 를 **downstream 흐름의 SAA 자리에**
넣었을 때 어떤 변화가 일어나는지 **읽기 전용으로 시뮬레이션**.

### 5.1 Wiring 흐름 (논리적 순서)

```
selected_candidate.weights (asset-level)
  ──▶ TAA overlay (rule-based regime tilts)
       ──▶ projection (long-only + bucket bound, SLSQP)
            ──▶ universe filter + product selection
                 ──▶ portfolio builder
                      ──▶ portfolio JSON (dry-run, separate output dir)
```

### 5.2 Dry-run 적용 항목

| 단계 | 적용 / 미적용 | 비고 |
|---|---|---|
| TAA overlay | **적용** (기존 rule-based 그대로) | overlay 후 weight 변화 dump |
| projection | **적용** (기존 SLSQP 그대로) | drift 측정 |
| universe filter + product selection | **적용** (기존 그대로) | 제품 분배 결과 dump |
| portfolio builder | **적용** | 최종 portfolio JSON dry-run dump |
| TAA / selection 로직 변경 | **금지** (Phase C.4+ 정책 유지) | 본 R-1E 도 코어 변경 없음 |
| production output 디렉토리 (`out/db_etf_relaxed/` 등) 쓰기 | **금지** | dry-run 은 별도 디렉토리 (예: `out/db_etf_relaxed_e62_r1e_dryrun/`) |

### 5.3 Dry-run vs 기존 max-Sharpe 비교

R-1F 구현 시 dry-run 결과를 기존 `portfolio_<type>_<as_of>.json` 과 비교 리포트:

| 비교 dimension | dry-run (manager-selected) | 기존 (max-Sharpe SAA) | delta |
|---|---|---|---|
| SAA asset_weights | selected_candidate.weights | `saa_diagnostics.saa_weights` | 자산별 weight 차이 |
| Sharpe (SAA-level) | 후보 sharpe | ref_max_sharpe sharpe | Sharpe 차이 |
| TAA overlay 후 weights | dry-run 산출 | 기존 `target_weights_before_projection` | overlay 효과 차이 |
| projection 후 final asset weights | dry-run 산출 | 기존 `asset_allocation[*].final_asset_weight` | drift / projection 차이 |
| product allocation | dry-run 산출 | 기존 `product_allocation` | 제품 분배 차이 |
| max_abs_projection_drift | dry-run 산출 | 기존 drift | drift 비교 |

### 5.4 Hard Boundaries (production 보호)

- dry-run 결과는 별도 디렉토리에 dump. 기존 `out/db_etf_relaxed*/` / `out/db_fund_relaxed*/`
  / `out/db_review_relaxed*/` 산출물 덮어쓰기 **금지**.
- `tests/_phase_e62_baseline.json` sha256 변경 **금지**.
- 기존 production CLI (`build_portfolio.py`) 의 default 동작 변경 **금지**. R-1F 는
  별도 CLI (예: `run_manager_selected_dry_run.py`).
- TAA overlay / product selection / projection 코어 로직 변경 **금지**.

---

## 6. Required Tests for Future R-1F Implementation

R-1F 구현 시 다음 tests 를 최소 포함:

| # | test | scope |
|:---:|---|---|
| T-1 | valid candidate selection → dry-run JSON 생성, production_applied=false | happy path |
| T-2 | unknown candidate_id → ValueError | V-1 |
| T-3 | `candidate_id="ref_max_sharpe"` → ValueError | V-3 |
| T-4 | `candidate_id="ref_80_20_equal_intra_bucket"` → ValueError | V-4 |
| T-5 | degenerate candidate (manually patched) → ValueError | V-5 |
| T-6 | bucket constraint 위반 후보 (manual) → ValueError | V-6, V-7 |
| T-7 | weights sum != 1 → ValueError | V-8 |
| T-8 | 음수 weight → ValueError | V-9 |
| T-9 | candidate dict 에 `bucket_distance_from_80_20` 강제 주입 → ValueError | V-10 |
| T-10 | review packet sha256 mismatch → ValueError | V-11 |
| T-11 | `selected_at` < opportunity_set generated_at → ValueError | V-12 |
| T-12 | empty `selected_by` → ValueError | V-13 |
| T-13 | empty `selection_reason` → ValueError | V-14 |
| T-14 | `allow_downstream_dry_run=False` → no-op (dump 생성 안 함) | V-15 |
| T-15 | output JSON schema check (meta / selection_input / selected_candidate / validation_summary / source_opportunity_json) | schema |
| T-16 | output JSON 의 `production_applied == false` strict | safety |
| T-17 | bit-identical baseline (`tests/_phase_e62_baseline.json`) sha256 unchanged 후 dry-run | regression |
| T-18 | 기존 portfolio JSON / E-series 산출물 mutation 없음 | regression |
| T-19 | dry-run 디렉토리가 기존 production 디렉토리와 분리됨 | safety |
| T-20 | (옵션) ETF + Fund 동시 dump 케이스 | multi-input |

---

## 7. Non-goals

본 R-1E spec / 후속 R-1F dry-run 범위에서 **명시적으로 하지 않는 것**:

```
✗ production SAA 교체
✗ TAA 변경 (rule-based 그대로)
✗ product selection 변경
✗ config 변경
✗ Decision Register count (14) 변경
✗ operating_mode = "production" 전환
✗ 자동 candidate 추천 / 추천 점수
✗ final SAA 자동 확정 (운용역 명시 선택 필수)
✗ 80:20 distance metric 부활 (R-1B.2 영구 제거 정합)
✗ 기존 portfolio JSON / E-series 산출물 덮어쓰기
✗ tests/_phase_e62_baseline.json sha256 변경
✗ "optimized TAA" / "regime-conditioned MVO" 라벨 사용
✗ 본 dry-run 결과를 production 으로 자동 승격
```

---

## 8. Open Decisions

운용역 / 사용자가 결정해야 할 항목 (R-1F 진입 전 sign-off 권장):

| # | 결정 항목 | 옵션 |
|:---:|---|---|
| OD-1 | 8 shortlist 중 어떤 candidate 를 선택할지 | cand_008421 / cand_005995 / cand_009678 / cand_005991 / cand_000758 / cand_007510 / cand_004225 / cand_007699 중 1 (또는 sweet pool 71건 중 별도 선택) |
| OD-2 | ETF / Fund 를 동일 candidate 로 갈지, 별도 선택할지 | (a) 동일 candidate (b) 별도 candidate (CMA·SAA 동일하므로 분석 결과는 같지만 운용 정책상 분리 가능) |
| OD-3 | selected candidate 를 TAA 적용 전 SAA 로 볼지, 별도 layer 로 볼지 | (a) SAA 자리에 직접 대체 (b) "manager_override_saa" 라는 별도 layer 신설 후 비교 |
| OD-4 | 기존 max-Sharpe SAA 와 병렬 비교만 할지, 직접 대체 검토할지 | (a) 병렬 비교만 (dry-run 산출 + 기존 산출 둘 다 보존) (b) 대체 검토 (별도 sign-off 후) |
| OD-5 | dry-run 결과를 Final Manager Review Packet 또는 별도 packet 에 포함할지 | (a) Final Manager Review Packet appendix 추가 (b) 신규 R-1F dry-run review packet 분리 |
| OD-6 | `source_review_packet.sha256` 검증을 strict 로 갈지 advisory 로 갈지 | (a) strict (V-11) — fail-fast (b) advisory — warning 만 |
| OD-7 | R-1F 진입 시 Decision Register 신규 entry 작성 필요 여부 | (a) 작성 (D-15 등 신규) (b) 미작성 (dry-run 만이므로 register 변경 불필요) |
| OD-8 | dry-run 결과 보관 기간 / retention 정책 | (a) 영구 보존 (b) 90일 (c) 분기별 archive |
| OD-9 | 운용역 선택 입력을 yaml 파일로 받을지, CLI argv 로 받을지, 두 방식 모두 지원할지 | (a) yaml 만 (b) CLI argv 만 (c) 두 방식 모두 |
| OD-10 | dry-run 결과를 production 으로 승격할 때의 게이트 | (a) 운용역 서명 (b) 운용본부장 + 위험관리 동시 서명 (c) Decision Register 신규 entry + Phase F 진입 |

---

## 8.1 R-1F Default Implementation Choices

> **본 섹션의 default 값은 production 결정이 아니라 R-1F 구현 기본값이다.**
> 운용역 / 사용자가 후속 turn 에서 override 가능하며, **자동 candidate 추천이 아니다** —
> 본 default 는 R-1F smoke / dry-run 예시 흐름을 정의하기 위한 implementation parameter
> 일 뿐 production SAA 자동 확정과 무관하다.

| OD | default | 이유 / 안전장치 |
|:---:|---|---|
| **OD-1** | **`cand_008421` 을 R-1F smoke / dry-run 예시 candidate 로 사용** | 운용역 final 선택이 아닌 **테스트용 manager-selected sample input**. 실제 운용 시에는 운용역이 §2 schema 로 직접 candidate_id 명시. 자동 추천 아님. |
| **OD-2** | **ETF / Fund 동일 `candidate_id` 기본** | CMA·SAA·bucket·seed 동일하므로 두 portfolio 의 후보 metric 도 동일. 단 §2 input schema 는 **별도 candidate 선택도 허용** (운용 정책상 ETF/Fund 분리 필요 시). |
| **OD-3** | **`manager_override_saa` 별도 layer 도입** — 기존 SAA telemetry 보존, 덮어쓰기 금지 | dry-run 에서 `manager_override_saa.weights` 를 SAA input 자리에 주입하되, 기존 `saa_diagnostics.saa_weights` 는 병렬 비교용으로 함께 dump. 기존 max-Sharpe SAA telemetry **변경 0**. |
| **OD-4** | **병렬 비교만 (직접 대체 X)** | R-1F 는 dry-run 산출 + 기존 산출 모두 보존. **직접 대체는 별도 sign-off 후 R-1G/Phase F** 에서 검토. |
| **OD-5** | **별도 R-1F dry-run review packet 분리** | Final Manager Review Packet 은 appendix 추가하지 않고 그대로 유지. 신규 packet: `manager_selected_saa_dry_run_review_<as_of>.md` (R-1F 산출). |
| **OD-6** | **`source_review_packet.sha256` strict** (V-11 fail-fast) | mismatch 시 `ValueError` — stale 또는 변경된 review packet 으로 부터의 선택 차단. 추적성 강제. |
| **OD-7** | **R-1F dry-run 만으로는 Decision Register 신규 entry 미작성** | dry-run = production 미반영이므로 register count (14) 유지. **production 승격 검토 시 비로소 D-15 등 신규 entry 신설** (OD-10 게이트와 연동). |
| **OD-8** | **dry-run 결과 영구 보존** (default) | archive 정책은 별도 운영 결정. 일단 retention=∞. |
| **OD-9** | **yaml 우선 + CLI argv 보조** | R-1F 구현은 yaml input (`--selection-yaml <path>`) 이 primary. CLI argv 직접 입력 (`--candidate-id <id> --selected-by ...`) 은 secondary. 두 방식 모두 동일 validation (§3) 통과 필요. |
| **OD-10** | **production 승격은 R-1F 범위 밖** | 최소 게이트: **(a) 운용역 명시 선택 + (b) Decision Register 신규 entry + (c) 별도 Phase F sign-off**. R-1F 는 dry-run JSON 의 `production_applied: false` / `sign_off_required_for_production: true` 단언만 강제. |

### 8.1.1 핵심 안전 원칙 (재확인)

| 원칙 | 적용 |
|---|---|
| 기존 SAA 절대 덮어쓰지 않음 | OD-3 manager_override_saa 별도 layer / OD-4 병렬 비교 |
| dry-run 결과 별도 디렉토리 | §5.4 hard boundaries — `out/db_{etf,fund}_relaxed_e62_r1e_dryrun/` |
| production 결정과 분리 | OD-7 (register 미변경) + OD-10 (별도 Phase F gate) |
| 자동 candidate 추천 아님 | OD-1 default = 테스트용 예시 input; 실제 운용 시 운용역 명시 선택 필수 |
| 추적성 | OD-6 strict sha256 / V-11 fail-fast |
| 입력 유연성 | OD-9 yaml + CLI argv 둘 다 지원 |

### 8.1.2 본 default 가 향후 변경될 수 있는 시점

| 시점 | 변경 가능 항목 |
|---|---|
| R-1F 구현 직전 사용자 turn | OD-1 ~ OD-10 어떤 항목이든 override 가능 |
| R-1F 구현 직후 first sanity | 운용역 정성 review 후 OD-1 (선택 candidate) / OD-2 (ETF·Fund 분리) override 가능 |
| Phase F production 승격 검토 시 | OD-4 (대체 검토) / OD-7 (register entry 신설) / OD-10 (게이트 강도) 재검토 필수 |

---

## 9. R-1F Implementation Plan (R-1E 승인 후 진입)

구현 후보 파일:

```
tdf_engine/optimization/
└── manager_selected_saa.py             (validation + dry-run JSON builder)

tdf_engine/tools/
├── select_manager_saa.py               (CLI: validation + dump only)
└── run_manager_selected_dry_run.py     (CLI: dry-run wiring 실행 — TAA + projection + selection 까지)

tests/
├── test_r1e_manager_selected_validation.py    (T-1 ~ T-14)
└── test_r1f_manager_selected_dry_run.py       (T-15 ~ T-20)
```

예상 산출 디렉토리:

```
out/db_review_relaxed_e62/saa_opportunity_set/<as_of_run>/
├── manager_selected_saa_etf_<as_of_run>.json              (R-1F validation 결과)
└── manager_selected_saa_fund_<as_of_run>.json

out/db_etf_relaxed_e62_r1e_dryrun/                         (R-1F dry-run wiring 결과 — 별도 디렉토리)
├── portfolio_etf_<as_of_run>.csv
├── portfolio_etf_<as_of_run>.json
└── review_etf_<as_of_run>.md (선택, dry-run 결과 vs 기존 비교)

out/db_fund_relaxed_e62_r1e_dryrun/
└── ...
```

R-1F 작업 분량 예상:

| 작업 | 예상 |
|---|---|
| validation 모듈 + CLI | 1.5h |
| dry-run wiring (기존 module 호출) + 비교 리포트 | 2.0h |
| tests 20건 | 1.5h |
| ETF/Fund dump + sanity | 0.5h |
| **합계** | **~5h (1~2 turn)** |

---

## 10. Hard Requirements (R-1E turn)

| 영역 | 변경 |
|---|:---:|
| 본 spec 문서 신규 작성 | ✓ |
| `tdf_engine/` 코드 | ✗ |
| `tdf_engine/config/*.yaml` | ✗ |
| `tests/` | ✗ |
| `out/` 산출물 | ✗ |
| `docs/investment_decision_register.md` | ✗ |
| Decision Register total count (14) | ✗ |
| E-8 ~ E-12 산출물 | ✗ |
| Final Manager Review Packet / opportunity set / R-1C/R-1C.1/R-1D 산출물 | ✗ |
| `tests/_phase_e62_baseline.json` sha256 | ✗ |
| operating_mode | ✗ `relaxed_diagnostic` 유지 |
| 80:20 distance metric | ✗ 부활 없음 |
| 자동 candidate 추천 / final SAA 자동 확정 | ✗ 금지 |

---

## 11. 한 줄 요약

> **R-1E = spec only. Manager-selected candidate 를 downstream SAA / TAA / product
> selection 흐름에 연결하기 위한 dry-run contract 정의. Input contract (§2) +
> Validation rules 16건 (§3) + Output schema (§4, `production_applied=false`) +
> Wiring 흐름 (§5) + Required tests 20건 (§6) + Open decisions 10건 (§8) +
> **R-1F default implementation choices (§8.1)** 포함. 핵심 default:
> `manager_override_saa` 별도 layer / 병렬 비교 / strict sha256 / yaml 우선 / production
> 승격은 별도 Phase F. 자동 final SAA 확정 금지. production allocation / TAA / product
> selection / config / Decision Register / E-series baseline 미변경. R-1F 진입은 §8.1
> default 기반 + 운용역 candidate 입력 후.**
