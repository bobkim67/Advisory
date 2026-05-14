# R-track 1차 Closeout Handoff (2026-05-13)

**한 장짜리 closeout.** R-1A ~ R-1H 까지의 기술 개발이 완료됐고, 이후는 코딩이 아니라
**운용역 / 거버넌스 판단** 단계임을 확정한다.

---

## §1. Completion Status

| 항목 | 값 |
|---|---|
| R-track 1차 기술 개발 | ✅ **완료** |
| production 반영 | ✗ **아님** |
| `operating_mode` | `relaxed_diagnostic` (유지) |
| `implementation_ready` | **false (strict)** |
| Decision Register count | **14 (유지)** |
| 80:20 distance metric 부활 | 없음 (R-1B.2 영구 제거 정합) |
| 자동 final SAA 확정 / candidate 추천 | 없음 (영구 금지) |

---

## §2. Completed Flow

```
R-1A spec
 ├─ R-1B / R-1B.2 bucket-constrained candidate pool (10,000)
 ├─ R-1C scatter / cloud / overlap visualization
 ├─ R-1C.1 sweet pool review (71 → 8 shortlist)
 ├─ R-1D similar_search (coordinate + weight)
 ├─ Final Manager Review Packet (8 manager review candidates)
 ├─ R-1E manager-selected dry-run contract spec
 ├─ R-1F.1 manager selection validation (16 rules + JSON dump)
 ├─ R-1F.2 + R-1F.2.1 downstream dry-run (asset-level valid, product-level invalid 라벨)
 ├─ R-1G.0 full re-selection mini-spec
 ├─ R-1G.1 product re-selection only
 ├─ R-1G.2 PortfolioBuilder wiring + 3-way comparison (valid product-level dry-run)
 └─ R-1H manager final review packet  ← R-track 1차 closeout 입력
```

---

## §3. Key Outputs (운용역 검토 진입점)

| 산출물 | 경로 |
|---|---|
| **R-1H final review packet** ★ | `out/db_review_relaxed_e62/saa_opportunity_set/20260513/r1h_manager_selected_saa_final_review_20260513.md` |
| R-1G.2 portfolio JSON (ETF) | `out/db_etf_relaxed_e62_r1g_reselection/portfolio_etf_20260513.json` |
| R-1G.2 portfolio JSON (Fund) | `out/db_fund_relaxed_e62_r1g_reselection/portfolio_fund_20260513.json` |
| R-1G.2 3-way compare md | `out/db_{etf,fund}_relaxed_e62_r1g_reselection/r1g_three_way_compare_{type}_20260513.md` |
| R-1G.1 product re-selection (selection only) | `out/db_{etf,fund}_relaxed_e62_r1g_reselection/product_reselection_{type}_20260513.json` |
| R-1F.2 dry-run (asset-level valid, product invalid) | `out/db_{etf,fund}_relaxed_e62_r1e_dryrun/portfolio_{type}_20260513.json` |
| R-1F.1 manager_selected_saa JSON | `out/db_review_relaxed_e62/saa_opportunity_set/20260513/manager_selected_saa_{etf,fund}_20260513.json` |
| Final Manager Review Packet (8 후보) | `out/db_review_relaxed_e62/saa_opportunity_set/20260513/saa_opportunity_set_final_manager_review_20260513.md` |
| R-1C cloud review | `out/db_review_relaxed_e62/saa_opportunity_set/20260513/saa_opportunity_set_cloud_review_20260513.md` |
| R-1B.2 opportunity set JSON | `out/db_review_relaxed_e62/saa_opportunity_set/20260513/saa_opportunity_set_{etf,fund}_20260513.json` |
| Spec docs | `tdf_2060/docs/r1_saa_opportunity_set_explorer_spec.md` + `r1e_manager_selected_saa_dry_run_spec.md` + `r1g_full_product_reselection_spec.md` |

---

## §4. Current Selected Candidate

| 항목 | 값 |
|---|---|
| candidate_id | **`cand_008421`** |
| 선택 방식 | manager-selected (R-1F.1 yaml input), **자동 추천 아님** |
| 입력 형태 | R-1F.1 smoke sample (`selected_by="r1f1_smoke_test"`, "not an automated recommendation" 명시) |
| ETF / Fund 적용 | **동일 candidate** |
| SAA 적용 layer | `manager_override_saa` **별도 layer** (기존 max-Sharpe SAA telemetry 보존) |
| Sharpe / ER / σ | 0.6277 / 10.97% / 12.69% |
| equity / FI bucket | 80% / 20% (hard) |

---

## §5. Important Findings

1. **baseline max-Sharpe** = corner solution (us_growth 70.6% + us_value 28.4%, eq=100% / fi=0%). 운용 정책 80:20 미만족.
2. **R-1G.2 dry-run portfolio** = `product_weight_sum = 1.000000` (ETF/Fund), `valid_product_level_portfolio = true`. R-1F.2 의 product-level invalid 한계 해소.
3. **dm_ex_us_equity / us_high_yield 신규 편입** — baseline 0% 였던 자산이 R-1G.2 에서 정상 picking (ETF us_high_yield 는 universe 2건 한계).
4. **ETF us_high_yield universe 2건 한계** — core 1 + satellite 1 로만 충당 (default 3 미달, 대체 후보 부족).
5. **ETF 0.24%p shortfall** — R-1G.1 cap clipping 잔여를 R-1G.2 `PortfolioBuilder.apply_fallback()` (pro-rata / cash placeholder) 가 흡수하여 sum 1.000000 달성.
6. `implementation_ready = false` **strict 유지** — `valid_product_level_portfolio = true` 가 production 가능을 의미하지 않음.

---

## §6. Not Changed (R-track 전체 turn 누적)

- **production SAA / TAA / product selection / portfolio builder / quality / fallback / optimization 코어** — 호출만, 수정 0
- production allocation (`out/db_etf_relaxed_e62/`, `out/db_fund_relaxed_e62/`) — byte size 그대로
- `tdf_engine/config/*.yaml` (8 yaml read-only, sha 검증 PASS)
- E-8 ~ E-12 산출물
- `docs/investment_decision_register.md` / Decision Register count (14)
- `tests/_phase_e62_baseline.json` sha (bit-identical baseline 11 test PASS)
- pytest 기준치 — R-track 진입 전 240 → 종료 시점 **381 passed / 5 skipped / 1 xfailed** (R-track 신규 141 test, regression 0)
- `saa_diagnostics.saa_weights` (기존 SAA telemetry 보존; `manager_override_saa` 별도 layer)
- 80:20 distance metric (R-1B.2 영구 제거 정합)

---

## §7. Required Manager Decisions

| # | 결정 항목 |
|:---:|---|
| 1 | **R-1H §8 checklist 12 항목 작성** (cand_008421 SAA 구조 / 자산 tilt / universe 한계 / fallback 흡수 / Phase F 상정 등) |
| 2 | **R-1H §10 옵션 A/B/C 선택**: A 보류 / B 다른 candidate 로 R-1F~R-1G 반복 / C cand_008421 결과를 Phase F 후보로 상정 |
| 3 | OD-2 ETF/Fund 분리 candidate 사용 여부 (현 default = 동일) — 본 결정 시 별도 R-1F.1 yaml 입력 필요 |

---

## §8. Phase F Entry Criteria

Phase F (production 승격) 진입 전 모두 만족 필요:

| # | 조건 |
|---|---|
| 1 | 운용역 **명시 sign-off** (서명 / 이메일 / 회의록 등 기록 가능 형태) |
| 2 | **선택 candidate 확정** (R-1F.1 yaml schema 로 `selected_by` / `selection_reason` / `source_review_packet.sha256` 명시) |
| 3 | **R-1G.2 결과 수용 여부** 명시 (§7.1 ETF us_high_yield universe / §7.2 fallback 흡수 처리 포함) |
| 4 | **Decision Register 신규 entry** 신설 결정 (D-15 등, OD-7 기본은 미작성이지만 production 승격 시 작성 필수) |
| 5 | **production 승격 gate** 확정 (OD-10 default: 운용역 sign-off + Decision Register entry + 별도 Phase F gate 3 단계) |
| 6 | `operating_mode` 전환 결정 (`relaxed_diagnostic` → `production`) — 별도 sign-off, R-1H 범위 밖 |

Phase F 진입 후에야 `implementation_ready` 가 검토 대상이 되며, 자동 승격은 영구 금지.

---

## §9. 한 줄 요약

> **R-track 1차 기술 개발 완료 (R-1A ~ R-1H). production 반영 없음.**
> R-1G.2 valid product-level dry-run portfolio (cand_008421, ETF/Fund 모두 sum=1.000000) 산출.
> 다음은 **운용역 §7 결정 + Phase F entry criteria 충족** — 코딩 아님.
> 본 closeout 으로 R-track 기술 채널 닫고, 거버넌스 채널로 전환.

---

## §10. Next Steps (2026-05-14 추가)

- **R-track 2 entry brief 생성됨**: [`tdf_2060/docs/r_track_2_entry_brief.md`](r_track_2_entry_brief.md) — R-track 2차 진입 전 운용역 판단 기준 framework (lightweight checklist + selection criteria + R-track 1차 산출물 분류 + gap).
- 본 framework 는 R-track 2차 진입 **prerequisite** 만 정리. **Phase F 진입 선언 / 후보 추천 / production 승격 모두 본 §10 추가로 발생하지 않음.**
- main 통합 상태: `main = origin/main = 6d570d5` (PR #1 머지 후 `.gitignore` hotfix fast-forward 통합).
