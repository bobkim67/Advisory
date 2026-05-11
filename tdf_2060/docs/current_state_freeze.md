# Current State Freeze — TDF 2060 Engine

스냅샷 일자: 2026-05-08.

> Phase C.5 완료 시점의 코드, 테스트, 산출물, 정책을 동결한다.
> 본 문서는 Phase D 진입과 함께 신설되며, 이후 변경은 Investment Decision Register를 거쳐야 한다.

---

## 1. 완료 단계

| 단계 | 상태 | 핵심 산출 |
|---|---|---|
| Phase A — 코드 골격 | ✅ 완료 | 17개 NotImplementedError 흐름 정의, 44 smoke test |
| Phase B — minimal end-to-end (file) | ✅ 완료 | csv/json 출력, ust30 (b)강한 error |
| Phase B.5 — weight closure + fallback | ✅ 완료 | pro-rata → bucket sibling → cash placeholder |
| Phase B.5+ — drift / quality_status | ✅ 완료 | clean / warning / review_required 분리 |
| Phase C-pre — classifier yaml + scoring policy | ✅ 완료 | Fund 채권 매칭 사각지대 해소 |
| Phase C — DB repository | ✅ 완료 | DBMarketDataRepository, --source file/db, fake DB 동등성 |
| Phase C.1 — semantic / sanity / dry-run | ✅ 완료 | semantic_type / return_transform 검증, inspect_db_sources CLI |
| Phase C.2 — SCIP dataset 매핑 확정 | ✅ 완료 | 9개 자산 모두 dataset_id 확정 |
| Phase C.3 — TAA feasibility projection | ✅ 완료 | SLSQP projection, long-only + bucket bound 보장 |
| Phase C.4 — 운용역 review packet | ✅ 완료 | review_*.md 자동 생성 (8 섹션 + policy_review_items) |
| Phase C.5 — Golden answer parity | ✅ 완료 | Placement/Velocity/Regime classification 100% 일치 (USA region) |

---

## 2. pytest 결과 (freeze 기준치)

```
$ /c/Users/user/Downloads/python/.venv/Scripts/python.exe -m pytest tests/ -q
.........................................................sss..ssx....... [ 55%]
..........................................................               [100%]
124 passed, 5 skipped, 1 xfailed in 7.21s
```

분포: A(44) + B(33) + B.5(5) + B.5+(7) + C-pre(7) + C(7) + C.1(7) + C.3(7) + C.4(5) + C.5(2 PASS) = 124.

- SKIP 5건: Excel DRM 보호 또는 외부 자료 의존 (D-08 / D-09 해소 시 활성화)
- xfail 1건: `regimeAnalysis_rt` 정의 미명시 (D-09 해소 시 PASS 전환)

본 수치는 Phase D 종료 전까지 freeze 기준치로 유지된다.

---

## 3. 코드 구조 (freeze 대상)

```
tdf_2060/tdf_engine/
├── __init__.py
├── config/                            (7 yaml)
│   ├── tdf_2060.yaml                   strategic_allocation, weight_bounds, taa_bounds, final_asset_bounds
│   ├── optimization_constraints.yaml   MVO objective dispatch, SLSQP options
│   ├── universe_filter.yaml            KIS MP 화이트리스트, exclude keywords, quant_grade_policy
│   ├── taa_policy.yaml                 regime 1~4 별 tilt, per_asset_max_tilt
│   ├── asset_mapping.yaml              9 자산군 + ust30 db_mapping_mode=direct
│   ├── universe_classification.yaml    Phase C-pre 신설, priority 기반 룰
│   └── db_sources.yaml                 Phase C.2 9 자산 dataset_id 확정
├── domain/                            (enums, models)
├── repositories/
│   ├── interfaces.py                   Protocol
│   ├── file_repositories.py
│   ├── db_market_data.py               Phase C, C.1, C.3
│   ├── composite.py                    DB + file 위임
│   ├── semantic.py                     Phase C.1 정책 검증
│   ├── _blob.py                        SCIP blob 파서
│   └── db_repositories.py
├── optimization/                      (cma, covariance, constraints, optimizer, tool)
├── regime/                            (placement, velocity, classifier, returns, tool)
├── taa/
│   ├── policy.py                       RegimeTAAPolicy
│   ├── overlay.py                      Phase C.3 projection 통합
│   ├── projection.py                   Phase C.3 SLSQP feasibility projection
│   └── tool.py
├── universe/                          (filters, classifier yaml-driven, tool)
├── selection/                         (scoring grade_policy, selector, tool)
├── portfolio/
│   ├── builder.py                      fallback + quality 호출
│   ├── fallback.py                     Phase B.5 + B.5+
│   ├── quality.py                      Phase B.5+
│   ├── validator.py                    projection / fallback / quality warnings
│   └── tool.py
├── reporting/
│   └── review.py                       Phase C.4 build_review_packet + render_markdown
└── tools/
    ├── build_portfolio.py              main CLI (--source / --as-of-date / --dry-run-db-check)
    ├── inspect_db_sources.py           Phase C.1 read-only DB 탐색
    ├── run_optimization.py
    ├── run_regime.py
    ├── run_regime_return.py
    └── run_universe.py
```

`tests/` 35 파일도 freeze.

---

## 4. 산출물 위치

### 4.1 실 DB 실행 결과 (Phase C.4 기준)

```
tdf_2060/out/
├── db_etf/
│   ├── portfolio_etf_20260507.csv      product 단위 26 row
│   ├── portfolio_etf_20260507.json     전체 + diagnostics + review packet
│   └── review_etf_20260507.md          8 섹션 운용역 리포트
├── db_fund/
│   ├── portfolio_fund_20260507.csv
│   ├── portfolio_fund_20260507.json
│   └── review_fund_20260507.md
└── db_dry_run/
    └── db_dry_run.json                  DB sanity 사전 검증
```

### 4.2 문서

```
tdf_2060/docs/
├── tdf_2060_tech_spec.md
├── tdf_engine_architecture.md
├── db_schema.md                        4개 DB 142 테이블 카탈로그
├── phase_b_review_packet.md            Phase A/B/B.5/B.5+/C-pre 누적
├── phase_c_db_repository.md            Phase C/C.1/C.2/C.3/C.4 누적 (12 섹션)
├── phase_c_final_handoff.md            Phase C 최종 핸드오프
├── golden_answer_validation.md         Phase C.5 분해 분석
├── phase_d_declaration.md              ★ Phase D 신설
├── current_state_freeze.md             ★ 본 문서 (Phase D 신설)
└── investment_decision_register.md     ★ Phase D 신설
```

### 4.3 source review

```
tdf_2060/source_review/
├── source_file_inventory.md
├── mvo_source_review.md
└── regime_source_review.md
```

---

## 5. 실 DB 산출 품질 상태 (ETF/Fund 동일)

```
constraints_passed        : True
quality_status            : warning
asset_weight_sum          : 1.000000
product_weight_sum        : 1.000000
equity bucket             : 82.32%             (75~85 안)
fixed_income bucket       : 17.68%             (15~25 안)
fallback_used             : True               (us_growth_equity / us_value_equity product_cap_clipping)
projection_used           : True               (음수 자산 2개 → 0)
max_abs_projection_drift  : 3.00%
max_abs_asset_weight_drift: 0.00%              (자산군 fallback 0)
proxy_used                : False              (모두 직접 매핑)
db_warnings_count         : 0
validation_issues_count   : 0
validation_warnings_count : 8
```

해석: 제약 통과 + bucket bound 만족 + 음수 0 + sum=1.0. `warning`이고 7건의 정책 확인이 자동 감지됨 → 운용역 동의 후 적용 가능.

---

## 6. Stale instruction 처리 원칙 (영구 기록)

이번 정합성 확인 결과(2026-05-08) 적용한 원칙. Phase D 이후에도 적용.

1. **정본 = 본 디렉토리의 문서 + 코드 + 테스트 결과의 일치 상태**
2. 정본보다 과거 단계의 외부 지시(이전 Phase 진입 지시 등)는 **stale로 판정**
3. stale instruction 발견 시:
   1. 사용자에게 충돌 사실 명시
   2. 정본과 외부 지시의 차이를 항목별 정리
   3. 사용자가 폐기/적용 여부를 명시할 때까지 코드/config/테스트 무변경
4. Auto Mode가 켜져 있어도 destructive(=완료된 작업 덮어쓰기) 작업은 **사용자 명시 승인 필수**
5. 충돌 해소 후 결정은 본 문서 또는 `investment_decision_register.md` 에 기록

---

## 7. 변경 통제

본 동결 시점 이후 변경은 다음 절차를 따른다:

| 변경 종류 | 절차 |
|---|---|
| yaml 정책값 변경 | Investment Decision Register 항목 closed → 별도 PR로 변경 |
| 코드 변경 | Phase 명시 + 별도 PR |
| 문서만 변경 | 자유 (단, freeze 표·수치는 보존) |
| 테스트 기대치 변경 | 코드 변경에 종속 + Decision Register 기록 |

---

## 8. Sanity check (재진입 시)

```bash
cd C:/Users/user/Downloads/python/Advisory/tdf_2060
/c/Users/user/Downloads/python/.venv/Scripts/python.exe -m pytest tests/ -q
# 기대: 124 passed, 5 skipped, 1 xfailed
```

수치가 맞지 않으면 즉시 회귀 원인 식별. **임의 수정 금지**, 원인 보고가 우선.
