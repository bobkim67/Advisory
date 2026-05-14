# R-track 2 Entry Brief — Selection Criteria Framework (2026-05-14)

> **운용역 내부 검토 메모 / decision framework.** R-track 1차 (R-1A ~ R-1H + closeout) 완료
> 후, R-track 2차 (실제 SAA 후보 검토) 진입 전 운용역이 사용할 판단 기준을 정리.
> 본 문서는 final report 도 production proposal 도 candidate 추천서도 아니다.
>
> 영구 라벨: `production_applied=false`, `dry_run_only=true`, `implementation_ready=false (strict)`,
> Decision Register count = **14 (유지)**, operating_mode `relaxed_diagnostic`,
> Phase F **미진입**.

---

## §0. 문서 목적 및 범위

- R-track 1차 결과를 **lens** 로 활용하여 R-track 2차 진입 시 판단 기준을 운용역이 사용할 수 있도록 framework 화.
- 본 문서가 다루지 **않는** 것:
  - final SAA 추천 / 후보 우선순위 부여
  - production 승격 / Phase F 진입 선언
  - `cand_*` 를 우수 후보로 표현
  - "optimized TAA" / "production-ready" 라벨
  - 코드 / config / out 산출물 / Decision Register 변경

---

## §1. Current Basepoint (2026-05-14)

| 항목 | 값 |
|---|---|
| `main` / `origin/main` | `6d570d5` (.gitignore hotfix 머지 후) |
| R-track 1차 close | 완료 (2026-05-13, PR #1 → `214d7dc` → `6d570d5`) |
| 작업 브랜치 | 모두 정리, `main` 단독 |
| operating_mode | `relaxed_diagnostic` (production 아님) |
| Decision Register count | **14 (유지)** |
| Phase F | **미진입** |
| 본 문서가 영향 주는 영역 | 코드 / config / out / Decision Register **0** |

---

## §2. Lightweight Checklist

### §2.1 R-1H §7 운용역 결정 3건 — 현 상태

| # | 결정 항목 | 상태 | 코멘트 |
|:-:|---|:-:|---|
| 1 | R-1H §8 checklist 12 항목 작성 (SAA 구조 / 자산 tilt / universe 한계 / fallback 흡수 / Phase F 상정 등) | check-needed | smoke sample (`cand_008421`) 대상이므로 실제 final 선택 candidate 에 대해 12 항목 재작성 필요 |
| 2 | R-1H §10 옵션 A/B/C 선택 (A 보류 / B 다른 candidate 로 R-1F~R-1G 반복 / C 결과를 Phase F 후보로 상정) | check-needed | `cand_008421` 은 smoke 이므로 옵션 C 는 본 후보 그대로 진입 아님. 실제 선택 candidate 로 재실행 후 결정. |
| 3 | OD-2 ETF/Fund 분리 candidate 사용 여부 (현 default = 동일) | check-needed | 분리 시 R-1F.1 yaml 2건 별도 입력 필요. ETF universe 한계 (us_high_yield 2건) 가 분리 결정에 영향. |

### §2.2 Phase F Entry 6 조건 (closeout §8) — 현 상태

| # | 조건 | 상태 | 코멘트 |
|:-:|---|:-:|---|
| 1 | 운용역 명시 sign-off (서명/이메일/회의록) | no | R-track 2차 후보 확정 후 진행 |
| 2 | 선택 candidate 확정 (R-1F.1 yaml schema `selected_by` / `selection_reason` / `source_review_packet.sha256`) | no | smoke `"r1f1_smoke_test"` 외 실제 input 없음 |
| 3 | R-1G.2 결과 수용 여부 (§7.1 ETF us_high_yield universe 한계 / §7.2 fallback 흡수) | check-needed | 본 framework §3.1 / §3.2 lens 로 평가 |
| 4 | Decision Register 신규 entry (D-15 등) 신설 | no | D-15 정의 필요 |
| 5 | production 승격 gate 확정 (운용역 sign-off + Decision Register entry + Phase F gate 3 단계) | check-needed | OD-10 default 외 운영 정책 명시 필요 |
| 6 | `operating_mode` 전환 결정 (`relaxed_diagnostic` → `production`) | no | 별도 sign-off |

> 9 항목 중 **yes = 0건**. 본 단계에서 Phase F 진입은 불가능.

---

## §3. Selection Criteria Framework

본 framework 는 운용역이 R-track 2차 후보 비교 시 **lens** 로 사용. **점수 합산용이 아니며 단일 metric 절대 컷오프 사용 금지.** 운용역 판단의 정합성 chain 을 유지하기 위한 구조.

### §3.1 정량 기준 (lens — 가중치 / 절대 컷오프 없음)

| 카테고리 | metric | 출처 / 위치 | 사용 lens |
|---|---|---|---|
| **Risk/return** | `expected_return` | candidate JSON `selected_candidate.expected_return` | 후보 간 상대 비교 + glide path 목표 부합성 |
| | `volatility` | `selected_candidate.volatility` | σ ceiling 정책 정합성 (정책 미확정 시 §5.3) |
| | `sharpe` | `selected_candidate.sharpe` | reference (`ref_80_20_equal_intra_bucket`, `ref_max_sharpe`) 대비 차분 |
| **Bucket constraint** | `equity_weight` | `selected_candidate.equity_weight` | 80% hard 만족 여부 (R-1B.2 이후 hard) |
| | `fixed_income_weight` | `selected_candidate.fixed_income_weight` | 20% hard 만족 여부 |
| **Concentration** | `max_asset_weight` | `selected_candidate.max_asset_weight` | 운용 정책 cap (정책 미확정 시 §5.3) |
| | `concentration_hhi` | `selected_candidate.concentration_hhi` | corner solution 의심 신호 (예: HHI > 0.5) |
| | `equity_intra_hhi` / `fixed_income_intra_hhi` | candidate JSON 동상 | bucket 내 집중도 lens |
| **Product universe** | `n_products` | R-1G.2 portfolio JSON `summary.n_products` | 운용 부담 vs 분산 trade-off |
| | universe 한계 자산군 | 후보별 metadata + closeout §7.1 | ETF `us_high_yield` (현 2건) 류 한계가 후보별로 다른지 |
| **Fallback / shortfall** | `product_weight_sum` | R-1G.2 portfolio JSON | 1.000000 도달 여부 |
| | fallback 흡수 분량 | `diagnostics.portfolio_builder.fallback` | cap 충돌 정도 (예: R-1G.2 ETF 0.24%p) |
| **ETF/Fund consistency** | 동일 candidate 산출 차이 | ETF vs Fund portfolio JSON 비교 | universe 차이 (us_high_yield ETF 2 vs Fund 3 등) 가 산출 차이로 이어지는 정도 |
| **Implementation telemetry** | `implementation_ready` | 모든 R-track JSON | **false (strict) 유지 — 자동 승격 신호 아님** |
| | `feasibility_status` | candidate JSON | `"feasible"` 라벨이라도 production 가능 의미 아님 |

> **주의**: 위 정량 metric 어느 하나도 절대 컷오프로 사용하지 말 것. **운용역 판단 보조 lens 일 뿐.**

### §3.2 정성 기준 (lens — 6 항목)

| # | 카테고리 | 판단 질문 | 근거 자료 |
|:-:|---|---|---|
| 1 | 운용 의도 정합성 | 후보의 자산군 tilt 가 현재 운용 의도 / 시장 view 와 부합하는가? | 운용역 view, 외부 macro |
| 2 | TDF 2060 glide path 설명력 | 본 시점 (2060 만기까지 ~34년) glide path 에서 후보의 equity 비중 (80%) 과 자산군 분산 구조가 설명 가능한가? | 운용본부 glide path 정책 + 운영자 직접 제공 glidepath (D-08 limitation 으로 DRM 보호 xlsx 미사용) |
| 3 | 자산군 tilt 납득 가능성 | `us_growth_equity` 대 `us_value_equity` / `dm_ex_us_equity` 비중이 운용역에게 설명 가능한가? `em` / `kr` / `us_high_yield` 신규 편입 사유 설명 가능한가? | 후보 candidate JSON §3 + R-1G.2 vs baseline 차분 |
| 4 | rule-based TAA 정합성 | 본 후보 위에 적용될 rule-based TAA tilt (현 default ±3%p, regime 1~4) 가 SAA tilt 방향과 충돌하지 않는가? | TAA tilt JSON, regime tool 출력 |
| 5 | 운용역 override 필요성 | `manager_override_saa` layer 외 추가 정책 (cap, exclusion, tilt 한도) 가 필요한가? | 운용 정책 + 후보 weights |
| 6 | Governance / sign-off 경로 | 본 후보 진입 시 D-15 등 Decision Register 신규 entry 필요 항목이 무엇인가? Phase F 3 단계 (운용역 sign-off + Decision Register + Phase F gate) 모두 통과 가능한가? | closeout §8 + OD-10 |

---

## §4. R-track 1차 산출물 분류

### §4.1 재사용 가능 (R-track 2차 lens / pipeline 으로 그대로 사용)

| 자산 | 형태 | 용도 |
|---|---|---|
| `optimization/opportunity_set.py` (R-1B.2) | 모듈 + CLI | 10,000 후보 Dirichlet pool 재생성 (80:20 hard, seed 변경 가능) |
| `optimization/opportunity_set_plot.py` (R-1C) | 모듈 + CLI | scatter / cloud / overlap-score 시각화 lens |
| `optimization/opportunity_set_search.py` (R-1D) | 모듈 + CLI | coordinate / weight 기반 후보 탐색 |
| `optimization/manager_selected_saa.py` (R-1F.1) | 모듈 + CLI | 16 validation rules — 운용역 실제 candidate 입력 검증 |
| `optimization/manager_selected_dry_run.py` (R-1F.2) | 모듈 + CLI | asset-level dry-run (TAA + projection) |
| `optimization/product_reselection_dry_run.py` (R-1G.1) | 모듈 + CLI | product re-selection only |
| `optimization/r1g2_reselected_portfolio.py` (R-1G.2) | 모듈 + CLI | PortfolioBuilder wiring + 3-way compare |
| `optimization/multi_candidate_comparison.py` (R-1I) | 모듈 + CLI | batch comparison (다중 후보 동시 평가) |
| `out/.../saa_opportunity_set_{etf,fund}_20260513.json` | data | 10,000 후보 pool data (재실행 비교 reference) |
| `out/.../saa_opportunity_set_{etf,fund}_*.png` | 시각화 | 후보 분포 lens (scatter / clouds / overlap) |
| `out/.../saa_opportunity_set_cloud_review_20260513.md` | doc | overlap-score 분석 lens |
| `docs/r1_saa_opportunity_set_explorer_spec.md` / `r1e_manager_selected_saa_dry_run_spec.md` / `r1g_full_product_reselection_spec.md` | spec | R-track 2차 흐름 contract |

### §4.2 Smoke / Comparison Sample (실제 후보 아님 — 운용 판단 input 금지)

| 자산 | 라벨 |
|---|---|
| `cand_008421`, `cand_004225`, `cand_007317`, `cand_006926`, `cand_007510`, `cand_009678`, `cand_000758`, `cand_006604` | 모두 smoke sample. `selected_by="r1f1_smoke_test"`, `"not an automated recommendation"` 명시. |
| `out/.../manager_selected_saa_{etf,fund}_20260513.json` | R-1F.1 smoke validation dump (cand_008421) |
| `out/.../r1i_multi_candidate/manager_selected_saa_*_cand_*_20260513.json` (16건) | R-1I batch smoke dump |
| `out/db_{etf,fund}_relaxed_e62_r1e_dryrun/portfolio_*_20260513.json` | R-1F.2 asset-level dry-run (product-level invalid) |
| `out/db_{etf,fund}_relaxed_e62_r1g_reselection/portfolio_*_20260513.json` | R-1G.2 dry-run (cand_008421 smoke) |
| `out/db_{etf,fund}_relaxed_e62_r1i_multi_candidate/cand_*/portfolio_*_20260513.json` (16건) | R-1I batch dry-run smoke |
| `out/.../r1h_manager_selected_saa_final_review_20260513.md` | R-1H final review packet (smoke decision worksheet) |
| `out/.../r1i_decision_summary_4candidates_20260513.md` | R-1I synthesis (smoke) |
| `out/.../r1i_multi_candidate_comparison_20260513.md` | R-1I batch comparison (smoke) |
| `out/.../saa_opportunity_set_final_manager_review_20260513.md` | Final Manager Review Packet (8 후보 worksheet, smoke decision support) |
| `out/.../saa_opportunity_set_sweet_pool_review_20260513.md` / `_shortlist_neighbors_20260513.md` / `_search_demo_*_20260513.md` | R-1C.1 / R-1D scratch / demo (smoke) |

### §4.3 Production 판단에 쓰면 안 되는 산출물 (영구 라벨)

- 모든 `cand_*` 후보 — **smoke sample only**.
- R-track 1차 모든 dry-run portfolio (R-1F.2 / R-1G.2 / R-1I) — `dry_run_only=true`, `implementation_ready=false (strict)`, `production_applied=false`.
- `"feasible"` / `"valid_product_level_portfolio=true"` / `"product_weight_sum_valid=true"` 라벨 — **포트폴리오 구조 정합성 만 의미하며 production 가능 의미 아님**.

---

## §5. Gap (R-track 2차 진입 전 부족한 것)

### §5.1 필요한데 R-track 1차에 없는 정보

| 카테고리 | gap | 영향 |
|---|---|---|
| 실제 candidate input | 운용역 명시 선택 (R-1F.1 yaml schema 의 `selected_by` / `selection_reason` / `source_review_packet.sha256` 채워진 production version) | R-track 2차 진입 첫 단계 |
| Glide path 시계열 | DRM 보호 xlsx → 운영자 직접 제공 필요 (D-08 closed_with_permanent_limitation) | §3.2 #2 정성 lens 활용 시 필요 |
| `regimeAnalysis_rt` 정의 | region / annualization / regime base 명시 (D-06 pending external) | TAA tilt 정합성 검증 |
| `final_asset_bounds` 운영 값 | 정책 확정 (D-11 deferred) | §3.1 정량 cap lens |

### §5.2 Phase F 전 필요한 운용역 결정

| # | 결정 | 위치 |
|:-:|---|---|
| 1 | D-06 ERR 정의 명시 (외부 자료) | Decision Register |
| 2 | D-11 `final_asset_bounds` 운영 값 (deferred → confirm) | Decision Register |
| 3 | D-12 deferred 항목 confirm | Decision Register |
| 4 | D-14 deferred 항목 confirm | Decision Register |
| 5 | D-15 신규 entry 정의 (R-track 2차 candidate 확정) | Decision Register 신규 |
| 6 | OD-2 ETF/Fund 분리 candidate 정책 (default 동일) | OD register |
| 7 | OD-7 R-1G.2 결과만으로 Decision Register entry 미작성 default 확인 | OD register |
| 8 | OD-10 production 승격 gate 3 단계 운영 정책 확정 | OD register |
| 9 | `operating_mode` 전환 별도 sign-off 프로세스 | 신규 |

### §5.3 Pipeline 설명력이 약한 부분 (R-track 2차 진입 전 명시화 권장)

| 항목 | 현 상태 | 명시화 권장 사유 |
|---|---|---|
| TAA tilt 폭 (현 default ±3%p) | 코드 default | 백테스트 검증 / 운용 정책 명시 부재 (D-07 deferred) |
| Regime 입력 region (현 default G7) | yaml default | regime 분류 결과가 region 에 따라 달라짐 (Dashboard region = USA 식별, 별도 lens) |
| 합성 ETF 화이트리스트 키워드 | yaml | 베트남/인도네시아/태국/멕시코/브라질 외 운용 정책 명시 부재 |
| Manager concentration 한도 (ETF 60% / Fund 50% 초안) | yaml | 운용 정책 확정 시점 명시 부재 |
| `max_abs_projection_drift` 3% 임계 | code default | D-02 Option A closed (운용역 sign-off 2026-05-08) 하지만 production 전환 시 재검토 권장 |

---

## §6. R-track 2차 진입 전 남은 결정사항 (one-page summary)

R-track 2차 (실제 SAA 후보 검토) 진입 전 운용역이 결정해야 할 항목:

1. **OD-2 ETF/Fund 분리 candidate 정책** — default 유지 vs 분리
2. **R-1F.1 yaml schema 실제 입력** — `selected_by` / `selection_reason` / `source_review_packet.sha256` 채울 source
3. **§3.1 정량 lens 사용 우선순위** — 본 framework 기준 vs 운용역 별도 lens
4. **§3.2 정성 lens #1 (운용 의도) / #2 (glide path) 답 정리** — 운용본부 view 입력
5. **§5.1 gap 의 glide path / `regimeAnalysis_rt` 정의** — 운영자 제공 필요
6. **D-15 신규 entry 정의** — Decision Register 추가 시기 / 작성자 / 내용

위 6 항목 결정 후에야 R-track 2차 candidate 검토 진입 의미 있음. 그 전까지 R-track 1차 산출물은 framework lens 용도 (§4.1) 로만 활용.

---

## §7. 본 문서의 변경 범위 / 안전장치

| 영역 | 변경 |
|---|:-:|
| 본 문서 신규 생성 | ✓ 1건 |
| `tdf_2060/HANDOFF.md` (현재 기준점 + 본 문서 링크 짧게) | ✓ 1 블록 추가 |
| `tdf_2060/docs/r_track_1_closeout_handoff.md` (§10 링크) | ✓ 1 섹션 추가 |
| 코드 (`tdf_engine/`) / config (`*.yaml`) / out 산출물 | ✗ 무변경 |
| `docs/investment_decision_register.md` | ✗ 무변경 (count 14 유지) |
| `docs/phase_e_current_handoff.md` | ✗ 무변경 (Phase E 정본 보호) |
| `tests/_phase_e62_baseline.json` | ✗ 무변경 |
| operating_mode | ✗ `relaxed_diagnostic` 유지 |
| Phase F 진입 선언 | ✗ 없음 |
| 자동 candidate 추천 / final SAA 라벨 / "optimized TAA" / "production-ready" | ✗ 금지 명시 |

---

## §8. 한 줄 요약

> **R-track 2차 진입 = framework lens 적용 + 운용역 explicit input.**
> R-track 1차 산출물은 lens (§4.1) 로만 사용. smoke sample (§4.2 / §4.3) 은 운용 판단 input 절대 금지.
> §3 framework + §5 gap closure + §6 결정 6항 통과 후에야 R-track 2차 candidate 검토 의미.
