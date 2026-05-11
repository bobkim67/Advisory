# Phase D Decision Review Brief — TDF 2060

작성일: 2026-05-08 · 산출 기준일: 2026-03-31 · 1~2페이지 분량의 운용역 판단용 요약.

> 본 brief 는 enhanced review packet (out/db_etf/review_etf_20260507.md, out/db_fund/review_fund_20260507.md),
> ETF/Fund 비교 (out/db_review/comparison_etf_vs_fund_20260507.md), Decision Register
> (docs/investment_decision_register.md) 4개 산출을 단일 의사결정 시트로 압축한다.
> 코드/엔진 산출 변경 없음. 결정 후 yaml 1줄 변경 + 회귀 테스트로 반영.

---

## 0. Executive Summary

| 항목 | ETF | Fund |
|---|---:|---:|
| constraints_passed | True | True |
| quality_status | **warning** | **warning** |
| asset_weight_sum | 1.000000 | 1.000000 |
| equity bucket | 82.32% (목표 75~85% ✓) | 82.32% (✓) |
| fixed_income bucket | 17.68% (목표 15~25% ✓) | 17.68% (✓) |
| projection_used | True (drift 3.00%) | True (drift 3.00%) |
| validation_warnings | 8 | 7 |

ETF/Fund 자산군 final weight 동일 (차이 0.00%p, 모두 SAA/TAA 동일 흐름). 차이는 운용사·상품 단계뿐.
ETF top 운용사: 한국투자신탁운용 26.87% / 삼성운용 20.80% / 타임폴리오 20.00%.
Fund top 운용사: **KB운용 30.00%** / 한국투자신탁운용 29.29% / HDC운용 8.32%.

**운용역 결정 5건 일괄 처리 권장**. blocker 8건 중 D-01/02/10/11/12 (5건) 가 본 brief 대상이며,
D-03 (lookback) / D-08 (DRM) / D-09 (regimeAnalysis_rt) 는 외부 자료 / 정의 의존이라 별도.

---

## 1. D-10 — ust30 / kr_t10 final 0% 허용 여부

| 항목 | 내용 |
|---|---|
| current setting | `final_asset_bounds.us_treasury_30y = [0%, 17%]`, `kr_treasury_10y = [0%, 12%]`. lower bound = 0% 이므로 0% 허용. |
| observed | regime 1 (Expansion) tilt: ust30 −3%p, kr_t10 −2%p → SAA(≈0) + tilt → 음수 → projection 으로 0%. |
| warning | VAL-02 negative weights before projection; POL-01/02 final 0%; POL-04/05 near final bound. |
| ETF/Fund 영향 | ETF/Fund 모두 ust30=0.00%, kr_t10=0.00% (동일). |
| 선택지 A | **0% 허용 (current).** lower bound 0% 유지. projection 으로 음수 → 0% 자연스럽게 처리. |
| 선택지 B | **강제 최소 편입 (예: lower bound 2~3%).** projection 이 다른 자산에서 빌려와 채움. |
| **recommended default** | **A — 0% 허용.** TDF 2060 은 risk-on profile 이고 regime 1 에서 안전채권 underweight 가 정책 의도와 정합. ust30 obs=87 (D-03 lookback 짧음) 도 강제 편입의 근거 약화. |
| risk if A 수용 | regime 3 (slowdown) 진입 시 long-duration safe asset 부재 → equity drawdown 직격. regime classifier 변경 후 재산출 시 자동 보강은 됨 (TAA tilt +3%p 들어가니 SAA + tilt > 0 가 되어 정상 편입). |
| risk if B 수용 | regime 1 에서 의도와 어긋남 (over-defensive). MVO sharpe 가장 좋은 us_value/growth 에서 빌려와야 하므로 projection drift 가 더 커짐. |
| code/config change | A: 변경 없음. B: `config/tdf_2060.yaml` final_asset_bounds 의 ust30/kr_t10 min 값 변경 + 테스트 갱신. |

---

## 2. D-02 — max_abs_projection_drift 3% 허용 여부

| 항목 | 내용 |
|---|---|
| current setting | drift 임계값 미정. quality_status 결정 임계 = 0% 초과 시 `warning` (현재). |
| observed | drift 3.00% (ust30 −3% → 0% 가 최대). projection_used=True. quality_status=warning. |
| warning | VAL-01 taa_projection_used drift=3.00%; POL-06 confirm acceptable. |
| ETF/Fund 영향 | 동일 (3.00%). |
| 선택지 A | **≤3% 허용 (current behavior).** drift 0~3% → warning, >3% → review_required. |
| 선택지 B | **≤2% 로 타이트하게.** 0~2% → clean, 2~3% → warning, >3% → review_required. 운영 friction 증가. |
| 선택지 C | **≤5% 까지 clean.** 거의 모든 산출이 clean. drift 의미 약화. |
| **recommended default** | **A — ≤3% 허용 + warning 유지.** 현재 drift 의 100% 가 D-10 zero-clipping 에서 발생. D-10 결정과 직접 연동. |
| risk if A 수용 | regime 3 등에서 tilt 가 더 강하게 작용하면 drift 가 5%+ 가능. 임계 미설정이면 quality_status 가 항상 warning 으로 고정 → signal-to-noise 저하. |
| risk if B 수용 | 정상 운용 산출도 review_required 로 빈번 분류 → 운용역 검토 피로. |
| code/config change | A: 변경 없음 (현재 동작). B/C: `tdf_engine/portfolio/quality.py` thresholds + `config/tdf_2060.yaml` 신설 키 + 테스트. |

---

## 3. D-11 — dm_ex_us_equity 4% lower bound 유지 여부

| 항목 | 내용 |
|---|---|
| current setting | `final_asset_bounds.dm_ex_us_equity = [4%, 27%]`. |
| observed | TAA target 5.00% → projection drift −0.71% → final **4.29%**. status=`near_bound`. |
| warning | POL-03 dm_ex_us 4.2857% near a final bound; confirm cap appropriateness. |
| ETF/Fund 영향 | 동일 (4.29%). |
| 선택지 A | **lower bound 4% 유지 (current).** near_bound 경고 영구. |
| 선택지 B | **lower bound 5% 로 강화.** TAA target 5% 운영 의도 반영. projection 이 다른 equity 에서 0.71%p 만큼 빌려옴. |
| 선택지 C | **lower bound 3% 로 완화.** near_bound 해소 + 자유도 증가. 단 TAA target 의도와 멀어짐. |
| **recommended default** | **B — lower bound 5%.** Phase C.4 review §4 4번에서 "5% 의도였다면 lower bound 5%로 강화" 운용역 후보 명시됨. near_bound 영구 발생 = 의도 일치 안 한다는 신호. |
| risk if B 수용 | tilt 가 강하게 음수일 때 (regime 변경) projection 이 더 큰 drift 를 발생시킴 → D-02 임계값 영향. us_growth/value 같은 cap 도달 자산에서 빌려오기 어려워 kr_aggregate 같은 곳에서 차감. |
| risk if A 유지 | near_bound 경고 누적 → 운용역이 "허용된 정상 상태" 인지 "수정 필요한 경계" 인지 매번 판단해야 함. |
| code/config change | B: `config/tdf_2060.yaml` `final_asset_bounds.dm_ex_us_equity.min: 0.04 → 0.05` 1줄 + 회귀 테스트 (final 4.29% → 5.00% 갱신, drift 변경). |

---

## 4. D-12 — us_value_equity 30% cap 유지 여부

| 항목 | 내용 |
|---|---|
| current setting | `weight_bounds.us_value_equity.max = 30%`. `final_asset_bounds.us_value_equity = [4%, 32%]`. |
| observed | SAA 가 cap 30% 끝까지 (DB sharpe 매우 높음). TAA target 30% → projection 후 **29.29%**. cap 거의 도달. product_cap_clipping 발생 (3 상품에서 redistribution). |
| warning | VAL-05 fallback_used: us_value 3.43% redistributed; POL: 직접 항목 없음 (cap 도달 자체는 정상 동작). |
| ETF/Fund 영향 | 동일 자산비중 (29.29%). 상품 단계: ETF/Fund 모두 product_cap_clipping → fallback_absorber. |
| 선택지 A | **cap 30% 유지 (current).** sharpe-driven concentration 수용. |
| 선택지 B | **cap 25% 로 축소.** 다변화 강화. 다른 자산(kr_equity / dm_ex_us / 채권) 이 흡수. sharpe efficient frontier 에서 후퇴. |
| 선택지 C | **cap 35% 로 확대.** product_cap_clipping 해소. 단일 자산 의존 강화. |
| **recommended default** | **A — cap 30% 유지.** 현재 사이클(regime 1) 에서 us_value sharpe 우위는 운용 의도. 다만 quarterly review 에서 가치/성장 rotation 점검 권장. |
| risk if A 수용 | us_value drawdown 시 portfolio 30% 직접 노출. correlation 높은 us_growth 와 합쳐 미국주식 70%+ → 미국 시장 systemic risk 집중. |
| risk if B 수용 | sharpe 가장 높은 자산 축소 → 기대수익 직접 하락. kr_aggregate 같이 sharpe 낮은 자산이 흡수 → 효율성 손실. |
| code/config change | A: 변경 없음. B/C: `config/tdf_2060.yaml` `weight_bounds.us_value_equity.max` + `final_asset_bounds.us_value_equity.max` 2줄 + 회귀 테스트. |

---

## 5. D-01 — final_asset_bounds 운영값 확정 (hard enforce 정책)

| 항목 | 내용 |
|---|---|
| current setting | `final_asset_bounds` 정의는 있으나 `validator.py` 에서 **warning only**, hard enforce 미적용. |
| observed | 현재 산출은 모든 자산이 bound 내부 (near_bound 1건). 정책상 violation 발생 시 warning 만 발생. |
| warning | VAL-04/05 fallback_used (cap clipping 관련, 단 직접 violation 아님). |
| ETF/Fund 영향 | 동일. |
| 선택지 A | **warning only 유지.** runtime 실패 없음. 운용역이 산출 후 사후 판단. |
| 선택지 B | **hard enforce.** violation 시 issue 분류 + portfolio.validator 가 raise / quality_status=review_required. |
| 의존 | D-10 / D-11 / D-12 결정 후에 bounds 운영값 확정 가능 (B 시점은 자연스럽게 그 이후). |
| **recommended default** | **단계적: 첫 3개월 A 유지 → 운영 안정 후 B 전환.** D-10/11/12 결정 적용 후 산출 안정성 점검 시간 필요. |
| risk if A 영구 유지 | 잠재적 violation 이 silent 하게 통과. quality_status=warning 이 표지 역할 못 함 (이미 다른 사유로 warning 빈번). |
| risk if B 즉시 적용 | 운용역 결정 (D-10/11/12) 미수령 상태에서 hard enforce 시 산출 자체가 fail 할 수 있음. 운영 차단. |
| code/config change | A: 변경 없음. B: `tdf_engine/portfolio/validator.py` 의 final_asset_bounds 처리 분기 (warning → issue 승격) + `config/tdf_2060.yaml` 운영값 확정 + 회귀 테스트. |

---

## 6. Decision Dependency Map

```
D-10 (ust30/kr_t10 0% 정책)
   └─ 결정 → final_asset_bounds.{ust30,kr_t10}.min 확정 ──┐
D-11 (dm_ex_us 4% bound)                                    │
   └─ 결정 → final_asset_bounds.dm_ex_us_equity.min 확정 ──┤
D-12 (us_value 30% cap)                                     ├─→ D-01 운영값 확정 → (선택) hard enforce 전환
   └─ 결정 → weight_bounds + final_asset_bounds.us_value ──┤
D-02 (drift 임계)                                           │
   └─ 결정 → quality.py thresholds 확정 ────────────────────┘
```

---

## 7. Recommended Defaults (한 줄 요약)

| Decision | recommended | 코드 변경 필요? |
|---|---|:---:|
| D-10 ust30/kr_t10 0% | **A — 허용 유지** | ✗ |
| D-02 drift 3% | **A — 3% 허용 + warning 유지** | ✗ |
| D-11 dm_ex_us 4% bound | **B — 5% 로 강화** | ✓ (yaml 1줄) |
| D-12 us_value 30% cap | **A — 30% 유지** | ✗ |
| D-01 hard enforce | **단계적: A 우선, 추후 B** | ✗ (현 단계) |

순수 권장안 채택 시 **yaml 1줄 변경 (D-11)** 만 발생. 나머지 4건은 현재 동작을 정책으로 추인.

---

## 8. 추가로 필요한 운용역 판단 (본 brief 범위 외)

| # | 항목 | 비고 |
|---|---|---|
| D-03 | lookback 정책 (자산별 차등 vs 일괄) | ust30 obs=87 vs 다른 자산 120. 운용역 + DB σ/μ 산출 기준 결정 필요 |
| D-08 | Excel DRM 해제 (3건) | 운영자. SAA/TAA/Final parity 활성화 |
| D-09 | regimeAnalysis_rt 정의 (region/annualization/regime base) | 운영자. xfail 1건 PASS 전환 |
| D-13 | quant_grade_policy mode | ETF=hard_filter (75건 제외), Fund=score_penalty. 운용역 검토 |
| D-14 | 운용사 concentration cap | Fund 의 KB운용 30% / 한국투자신탁운용 29.29% — 50% cap 내이지만 TWO 운용사 합 59.29% |

---

## 9. Sign-off Sheet

다음 표를 운용역이 직접 작성. 결정 수령 후 register 갱신 + (필요시) yaml 변경 + 회귀 테스트.

| Decision | 선택 (A/B/C) | 운영값 확정 | 의견 |
|---|:---:|---|---|
| D-10 ust30/kr_t10 | ☐ A  ☐ B | min = ___% | |
| D-02 drift | ☐ A  ☐ B  ☐ C | 임계 = ___% | |
| D-11 dm_ex_us | ☐ A  ☐ B  ☐ C | min = ___% | |
| D-12 us_value | ☐ A  ☐ B  ☐ C | cap = ___% | |
| D-01 hard enforce | ☐ A  ☐ B  ☐ 단계적 | 시점 = ____ | |

작성: ____________ (운용역) · 일자: __________
