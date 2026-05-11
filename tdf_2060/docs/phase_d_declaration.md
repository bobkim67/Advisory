# Phase D — Portfolio Governance & Operation Readiness

선언일: 2026-05-08.

> Phase C.5 완료(124 passed / 5 skipped / 1 xfailed) 시점에서 진입.
> **추가 구현이 목적이 아닌 운용역 검토, 의사결정, 운영 준비성 검증 단계.**

---

## 1. 목적

Phase A~C.5 까지 코드 동작 검증은 완료됨. 다음 게이트는 **운용역 의사결정 + 운영 절차 정합성**이다.

구체적으로:

1. Phase C.4 review packet의 7개 자동 감지 항목에 대한 운용역 결정 수령
   - ust30/kr_t10 final 0% 허용 여부, dm_ex_us 4% lower bound 의도, us_value 30% cap 적정성, projection drift 3% 허용, lookback 정책 등
2. 외부 자료 확보로 Phase C.5 SKIP/xfail 해소
   - Excel DRM 3건 해제 → SAA/TAA/Final weights 1:1 parity 검증 활성
   - `regimeAnalysis_rt` 정의 명시 (region / annualization / regime base)
3. `final_asset_bounds` 운영값 확정 + hard enforce 정책 결정
4. 운영 사이클 정의 (재실행 빈도, 입력 요건, 산출 검증, 로그 보관, 회귀 트리거)

---

## 2. Freeze 정책

다음을 freeze 상태로 둔다. **변경 금지**:

| 대상 | 범위 |
|---|---|
| `tdf_engine/` | 11개 서브패키지 전체 (domain / repositories / optimization / regime / taa / universe / selection / portfolio / reporting / tools / config) |
| `tests/` | 35 파일, 기대치 124 passed / 5 skipped / 1 xfailed |
| `tdf_engine/config/` 정책값 | 7 yaml의 매핑/bounds/policy 값 |

예외 (허용):

- `docs/`, `HANDOFF.md`, `CLAUDE.md` 정합성 보정
- 운용역 결정 후 yaml 단순 값 교체 (`final_asset_bounds` 운영값 등) → 별도 PR로 진행, register에 결정 기록 후

Phase A 재생성·코드 골격 재작성·기존 테스트 삭제·재구조화는 **불가**.

---

## 3. Stale instruction 처리 원칙

이전 Phase 지시가 뒤늦게 재유입되는 경우 다음 원칙을 적용한다 (2026-05-08 정합성 확인 시 적용한 원칙을 영구 기록).

1. 정본 = 본 디렉토리의 `CLAUDE.md`, `HANDOFF.md`, 실제 `tdf_engine/` 패키지, `tests/` 결과의 일치 상태
2. 정본보다 과거 단계의 외부 지시(이전 Phase 진입 지시 등)는 **stale로 판정하고 무시**
3. stale instruction 발견 시:
   - 사용자에게 충돌 사실 명시
   - 정본 상태와 외부 지시의 차이를 항목별 정리
   - 사용자가 폐기/적용 여부를 명시할 때까지 코드/config/테스트 무변경
4. Auto Mode가 켜져 있어도 destructive(=완료된 작업 덮어쓰기) 작업은 **사용자 명시 승인 필요**
5. 충돌 해소 후 결정은 본 문서 또는 `investment_decision_register.md` 에 기록

---

## 4. 결정 전 가능 작업 / 결정 후 가능 작업

### 4.1 운용역 결정 없이도 진행 가능

| # | 작업 | 변경 위치 | 영향 |
|---|---|---|---|
| P-01 | 문서 정합성 보정 | `docs/`, `CLAUDE.md`, `HANDOFF.md` | 문서만 |
| P-02 | Investment Decision Register 유지·갱신 | `docs/investment_decision_register.md` | 문서만 |
| P-03 | review packet 표현 보강 (코드 산출 변경 없이 출력 표현만) | `reporting/review.py` 의 render | 산출 동일, 표현만 |
| P-04 | 운영 절차 문서화 (재실행 빈도, 입력 요건, 로그 보관 정책) | `docs/operations_runbook.md` (신설 가능) | 문서만 |
| P-05 | 추가 sanity 진단 (값 변경 없음, 진단만 노출) | reporting / diagnostics 출력 | 진단 출력만 |

위 5건 모두 yaml 정책값·코드 결과·테스트 기대치를 바꾸지 않는다.

### 4.2 운용역 결정 후에만 진행

| # | 작업 | 의존 결정 | 변경 위치 |
|---|---|---|---|
| A | `final_asset_bounds` 운영값 확정 | D-10 / D-11 / D-12 | `config/tdf_2060.yaml` |
| B | ust30/kr_t10 0% 허용 vs 강제 편입 | D-10 | `config/asset_mapping.yaml` |
| C | projection drift 임계 변경 | D-02 | `portfolio/quality.py`, `config/tdf_2060.yaml` |
| D | lookback 정책 (자산별 vs 일괄) | D-03 | `config/db_sources.yaml` 또는 `optimization/cma.py` |
| E | DB σ/μ 산출 기준 (computation_mode) | D-03 | `optimization/cma.py` |
| F | `final_asset_bounds` hard enforce | D-01 | `portfolio/validator.py` |
| G | selection score 보존 | (운영자) | `selection/tool.py` |
| H | regime DB 연결 (`solution.roboadvisorAPI_economicregime`) | (운영자) | `repositories/` 추가 |
| I | GlidePath 다중 vintage | D-08 (DRM 해제) | `repositories/`, `tools/build_portfolio.py` |
| J | HTML/Dash reporting | (운영자) | `reporting/` 추가 |

`A`~`F` 는 정책 결정에 의존하므로 결정 수령 전 진행 불가.

---

## 5. 진입/종료 조건

| 조건 | 기준 |
|---|---|
| 진입 | Phase C.5 완료 (현재 충족: 2026-05-08 기준 124 passed / 5 skipped / 1 xfailed) |
| 종료 | Decision Register의 blocker 항목(D-01 / D-02 / D-03 / D-08 / D-09 / D-10 / D-11 / D-12) 모두 closed + `final_asset_bounds` 운영값 적용된 산출이 운용역 사인 받음 |

---

## 6. 본 Phase에서 절대 하지 말 것

- `tdf_engine/` 패키지 재생성
- 기존 domain / repositories / optimization / regime / taa / universe / selection / portfolio / reporting / tools 덮어쓰기
- tests 삭제 또는 재작성
- 기존 passing 코드 구조 단순화
- Phase A 수준으로 롤백
- 파일을 대량으로 새 skeleton 으로 교체
- 기존 Phase C.5 결과물 훼손
- 상위 Advisory/, python/CLAUDE.md 수정
- DB credential을 코드/yaml에 직접 작성

---

## 7. 참조 문서

| 문서 | 역할 |
|---|---|
| `current_state_freeze.md` | 동결된 상태 스냅샷 (코드 구조, 산출물, 품질 수치) |
| `investment_decision_register.md` | 결정 항목 + 상태 + 변경 위치 |
| `phase_c_final_handoff.md` | Phase C.5 시점의 직전 진입점 |
| `golden_answer_validation.md` | Phase C.5 parity 분해 분석 |
| `CLAUDE.md`, `HANDOFF.md` | Phase 진행 현황 + 다음 세션 진입점 |
