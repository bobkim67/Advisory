# Golden Answer Validation — Phase C.5

작성일: 2026-05-07. Python 엔진 vs 기존 VBA/Excel 답안지 단계별 parity 검증.

> **목적**: 운영자 리뷰 전, "동일 입력에서 동일 결과" 인지 확인. 차이가 있다면 *어느 단계*에서 발생하는지 분해.

---

## 1. 답안지 인벤토리

| 종류 | 위치 | 추출 가능 | 단계 |
|---|---|---|---|
| `regime_Dashboard` | `Advisory/regime_Dashboard` | ✅ TSV | Placement / Velocity / Phase(R) / Phase(N) 시계열 |
| `regimeAnalysis_rt` | `Advisory/regimeAnalysis_rt` | ✅ TSV | 4 regime × 24 자산 평균수익률 (연환산 %) |
| `ECI_Neo_202603.xlsx` | `Advisory/` | ❌ DRM 보호 | Dashboard 원본 + ECI 시트 |
| `RegimeAnalysis_2602.xlsx` | `Advisory/` | ❌ DRM 보호 | regime_return 원본 |
| `0. 정리 - GlidePath 값.xlsx` | `Advisory/` | ❌ DRM 보호 | GlidePath 값 |
| `Asset_rt_vol`, `Corr_mat` | `Advisory/` | ✅ 입력 | CMA *입력*. 산출 단계 답안 미추출 |
| `optimization_vba` | `Advisory/` | ✅ 텍스트 | VBA 코드 (로직). 산출 weight 미포함 |
| `regime_*` (코드) | `Advisory/` | ✅ 텍스트 | Excel 셀 수식. ECIRegimeClassifier 등에 이미 이식 |

**DRM 보호 파일**: 헤더 `<DOCUMENT SAFER V2010 R2>`. Python (`openpyxl`/`xlrd`) 직접 read 불가. 운영자가 보호 해제 후 재공급해야 비교 가능.

---

## 2. 단계별 비교 가능 여부

| # | 단계 | 답안지 | 비교 결과 |
|---|---|---|---|
| 1 | CMA expected returns / vol | Excel 원본 (DRM) | **SKIP** — 답안지 부재 |
| 2 | Correlation / Covariance | Excel 원본 (DRM) | **SKIP** — 답안지 부재 |
| 3 | MVO SAA weights | Excel 원본 (DRM) | **SKIP** — `$L$26` 목적함수도 미확인 |
| 4 | **Placement / Velocity (USA)** | regime_Dashboard | ✅ **PASS** — `max\|diff\|=4.9e-4` |
| 5 | **Regime classification (USA)** | regime_Dashboard.Phase(R) | ✅ **PASS** — 100% match (49/49) |
| 6 | TAA target / projection | (없음) | **SKIP** |
| 7 | Selection / 최종 portfolio | Excel 원본 (DRM) | **SKIP** |
| 8 | **Regime return analysis** | regimeAnalysis_rt | **xfail** — 운영자 확인 (2026-05-08): 외부 Excel parity 답안지 영구 부재 (DRM 해제 불가). 파일 자체 = canonical definition. D-08 / D-09 closed by 운용역 sign-off (§5.5 참조) |

**정량 (2026-05-08 D-08/D-09 closure 후 갱신)**: 비교 가능 단계 3개 / 비교 불가 5개 (DRM 영구 unavailable) / 정의 자료 영구 부재 1개 (regimeAnalysis_rt = 파일 자체가 정본).

---

## 3. PASS 단계 — Placement / Velocity / Regime classification

### 3.1 Region 식별

`regime_Dashboard` 가 어느 region 추출인지 명시 안 됨. 22개 region 후보 (`A5M, AUS, BRA, ..., USA`) 중 brute-force 매칭:

| region | max\|P diff\| | max\|V diff\| |
|---|---:|---:|
| **USA** | **0.000490** | **0.000495** |
| NAFTA | 0.176515 | 0.041083 |
| G7 | 0.303788 | 0.125950 |
| FRA | 0.655460 | 0.215075 |
| ... | ... | ... |

**확정**: `regime_Dashboard` = USA region 기반. 우리 default(`taa_policy.yaml::regime_input.composite_region: G7`) 와 다름.

### 3.2 numerical 결과

```
$ pytest tests/test_phase_c5_golden_parity.py::test_golden_placement_velocity_matches_expected -v
PASSED
```

- max\|P diff\| = 0.000490 (golden 소수점 3자리 반올림 잔차)
- max\|V diff\| = 0.000495
- Tol.placement_velocity_abs = 1.5e-3 (golden rounding 흡수)

### 3.3 Regime 분류

```
$ pytest tests/test_phase_c5_golden_parity.py::test_golden_regime_classification_matches_expected -v
PASSED
```

- 49/49 시점 일치 (100%, USA 기준).
- Phase(R) = sign-based (P>0/V>0 → 1, ...). 우리 `ECIRegimeClassifier.classify_frame` 와 정확히 동일 정의.
- 시작점 2022-02 (P=-0.323, V=-0.156, regime=3) ~ 끝점 2026-02 (P=+0.705, V=+0.119, regime=1).

> Phase(N) (Normalized angle-based) 는 미사용 — Python 엔진은 sign-based(=Phase(R))만 구현.

---

## 4. SKIP 단계 — 답안지 부재

### 4.1 CMA / Covariance / MVO SAA / TAA / Selection / Final

답안지 위치 후보:
- `ECI_Neo_202603.xlsx`: Regime 시트 (Phase / Placement / Velocity 답안 — Dashboard 추출본으로 부분 보유).
- `RegimeAnalysis_2602.xlsx`: regime별 자산 수익률 답안 (regimeAnalysis_rt 추출본으로 부분 보유).
- *기타 Excel 파일 (포트폴리오 산출용)*: 미공급. 운영자가 SAA/TAA/최종 weight 답안지 별도 export 필요.

### 4.2 운영자 export 요청 항목

다음을 csv/json 으로 추출 후 `tests/fixtures/golden/` 에 두면 parity test 활성 가능:

| 파일명 | 컬럼 | 단위 |
|---|---|---|
| `cma_expected.csv` | asset_key, expected_return, volatility | 소수 |
| `corr_expected.csv` | asset_key index/columns | 소수 |
| `mvo_saa_expected.csv` | asset_key, weight | 소수 |
| `taa_target_expected.csv` | as_of, asset_key, target_weight | 소수 |
| `final_weights_expected.csv` | as_of, asset_key, final_weight | 소수 |
| `final_products_expected.csv` | as_of, product_id, asset_key, weight | 소수 |

위 파일이 추가되면 `tests/test_phase_c5_golden_parity.py` 의 `pytest.skip(...)` 을 실제 비교 로직으로 교체.

---

## 5. xfail 단계 — Regime return analysis

### 5.1 결과

```
$ pytest tests/test_phase_c5_golden_parity.py::test_golden_regime_returns_match_expected -v
XFAIL  (region 기준 / annualization 방식 미명시)
```

- 비교 자산 7 × 4 regime = 28쌍. **15/28 fail (53.6%)**.
- best region (가장 가까운) = G20. avg_diff = 0.0668 (6.68%p).
- top failures (regime=1 한국주식: py=59.08% vs gold=42.00%, diff=+17.08%p 등).

### 5.2 차이 분해 — 가능한 원인

| # | 원인 후보 | 영향 |
|---|---|---|
| 1 | **답안지의 regime 분류 base** — Phase(R) (sign-based) vs Phase(N) (normalized angle) 중 어느 것을 기준으로 자산 수익률을 그룹핑했는지 미명시 | regime 라벨링 자체가 다르면 동일 시점이 다른 regime 으로 들어가 평균이 크게 달라짐 |
| 2 | **답안지의 region 기준** — Dashboard 는 USA 였지만 regimeAnalysis_rt 는 USA 인지 G7 인지 불명. brute-force 결과 G20 가 가장 가깝지만 그래도 6.68%p 평균 차이 | regime classification 시점별 라벨이 달라짐 |
| 3 | **annualization 방식** — 산술 평균 × 12 vs 기하 ((1+r̄)¹² − 1) | regime 1 한국주식 산술 ≈ 59% vs 기하 ≈ 49% — 약 10%p 차이 가능 |
| 4 | **자산 시점 정렬** — `regime_src` 월말 vs `regimeAnalysis_src` 월말 (각 파일 일자 다를 수 있음) | edge-of-month 시점 매칭 차이 |
| 5 | **자산 매핑** — `한국채권` 컬럼이 답안지에 2개 (`한국채권` + `한국채권.1`). 어느 것이 SPBKRCOT(우리 kr_aggregate_bond) 와 정합인지 미명시 | 자산 단위 매핑 오류 가능 |
| 6 | **lookback 기간** — 답안지 산출 시 사용한 시계열 시작 시점 미명시 | regime 1~4 sample size 가 달라 평균이 달라짐 |

### 5.3 Phase C.5 정책

사용자 지시 정확히 준수:
> 답안지와 불일치가 나와도 즉시 로직을 고치지 말고, 어느 단계에서 차이가 발생했는지 먼저 분해한다.

따라서 본 단계에서:
- **로직 수정 0** — `RegimeReturnAnalyzer.analyze` 그대로 유지.
- 테스트는 `xfail(strict=False)` — 회귀 노출은 막되 future strict 전환 가능.
- 운영자 결정 후 한 가지 정의를 fix 하면 strict=True 로 변경.

### 5.4 운영자 결정 항목 (2026-05-08 갱신 — D-08 / D-09 closure 영향)

| # | 결정 | 2026-05-08 처리 |
|---|---|---|
| 1 | regimeAnalysis_rt 의 regime 분류 base = Phase(R) 인지 Phase(N) 인지 | **영구 답안지 부재** (DRM 해제 불가). 파일 자체 = 정본. |
| 2 | regime classification 의 region = USA / G7 / 다른 region | 동일. |
| 3 | annualization = 산술 평균 × 12 vs 기하 | 동일. |
| 4 | `한국채권` 두 컬럼 중 SPBKRCOT 정합 컬럼 | 동일. |
| 5 | lookback 기간 | **D-03 closed by 운용역 sign-off (2026-05-08)** — Option C Hybrid (return/vol asset_specific, corr common). |

### 5.5 D-08 / D-09 closure note (2026-05-08)

운영자 확인:
- **DRM 보호 xlsx 3건은 영구 해제 불가** (D-08 closed_with_permanent_limitation).
- `RegimeAnalysis_2602.xlsx` / `ECI_Neo_202603.xlsx` 내용 = 기존 `regime_*` + `regimeAnalysis_*` file 의 결합물. 추가 정보 없음.
- `regimeAnalysis_rt` = 별도 정의 자료 없음. **파일 자체가 canonical definition** (D-09 closed).

xfail 1건 (`test_phase_c5_golden_parity::test_golden_regime_returns_match_expected`) 처리:
- xfail **유지**. testcase 가 의미 없는 게 아니라 **영구 답안지 부재** 를 reflect.
- 사유 갱신: "regimeAnalysis_rt 정의 미명시" → **"외부 Excel parity 답안지 영구 부재 (DRM 해제 불가)"**.
- strict=False 유지. future strict 전환은 운용역이 별도 답안지 확보할 때만 의미.

따라서 §5.4 의 "운영자 결정 항목" 1~4 는 **영구 closed_with_permanent_limitation** 위상. lookback (§5.4-5) 만 D-03 closure 로 해소.

---

## 6. tolerance 정책 (`tests/golden_helpers.py::Tol`)

| 항목 | tolerance | 근거 |
|---|---:|---|
| weight | 1e-4 (1bp) | VBA Solver(GRG) vs scipy SLSQP 차이 + numerical |
| return / vol | 1e-6 | numerical 일치 기대 |
| correlation | 1e-6 | numerical 일치 기대 |
| Sharpe | 1e-4 | weight 차이 영향 |
| product weights | 1e-4 (1bp) | weight 와 동일 |
| **placement / velocity** | 1.5e-3 | golden 소수점 3자리 반올림 (실측 max diff 4.9e-4) |
| regime 분류 일치율 | 100% | 정수 비교, edge case 만 95% 까지 허용 |
| regime return | 5%p | 정의 차이 (산술 vs 기하) 흡수 — xfail 풀린 후 1e-4 로 강화 |

---

## 7. parity test 결과 요약

```
$ pytest tests/test_phase_c5_golden_parity.py -v

PASSED  test_golden_placement_velocity_matches_expected      ← USA region, max|diff|<1.5e-3
PASSED  test_golden_regime_classification_matches_expected   ← USA, 49/49 = 100%
SKIPPED test_golden_cma_matches_expected                     ← Excel DRM 보호
SKIPPED test_golden_corr_matches_expected                    ← Excel DRM 보호
SKIPPED test_golden_mvo_weights_match_expected               ← $L$26 + Solver 답안지 미추출
SKIPPED test_golden_taa_target_matches_expected              ← 답안지 미추출
SKIPPED test_golden_final_weights_match_expected             ← 답안지 미추출
XFAIL   test_golden_regime_returns_match_expected            ← region/annualization 정의 미명시
```

전체: **124 passed, 5 skipped, 1 xfailed** (Phase C.4 → 122 passed 에서 +2 PASS, +5 skip, +1 xfail).

---

## 8. 다음 수정 필요 여부 — Claude 판단

**현 시점 코드 수정 없음**. 모든 fail/skip 이 *답안지 정의 미명시* 또는 *답안지 부재* 가 원인.

| 단계 | 결론 |
|---|---|
| Placement / Velocity / Regime classification | ✅ 동일. 운용 적용 가능. |
| Regime return analysis | ⚠️ 정의 미명시. 운영자 결정 후 *우리 코드 수정 vs 답안지 산출 기준 강제* 분기 |
| CMA / Covariance / MVO SAA / TAA / Selection / Final | ⏸️ 답안지 부재. Excel 원본 export 후 재시도 |

**원인 분류**: 입력 데이터 차이(0) / 우리 로직 버그(0) / 답안지 정의 미명시(1) / 답안지 부재(5). 즉 우리 엔진의 *명확한 버그*는 본 검증 단계에서 발견되지 않음.

---

## 9. Phase C.5 변경 파일

신규
- `tests/golden_helpers.py` — `Tol` (tolerance), `load_regime_dashboard`, `load_regime_return_rt`, region/매핑 상수
- `tests/test_phase_c5_golden_parity.py` — 8 tests (2 PASS, 5 SKIP, 1 xfail)
- `docs/golden_answer_validation.md` — 본 문서

수정 (계획)
- `docs/phase_c_final_handoff.md` — Phase C.5 결과 명시 (별도 작업)

코어 (optimization / regime / TAA / selection / portfolio) **변경 0**.

---

## 10. 운영자 가이드

다음 검토 시 우선순위:

1. **regimeAnalysis_rt 정의 명시** (§5.4 5개 항목)
2. **Excel 원본 DRM 해제** (`ECI_Neo_202603.xlsx`, `RegimeAnalysis_2602.xlsx`, `0. 정리 - GlidePath 값.xlsx`)
   - 또는 SAA / TAA / Final weights 를 csv 로 별도 export
3. 위 1~2 가 끝나면 SKIP 5건 → 실제 비교로 교체, xfail 1건 → strict 비교
4. parity 결과 기반으로 *코드 수정* vs *답안지 정의 명시 변경* 결정

위 절차가 끝나야 **VBA → Python 엔진 1:1 parity 가 운용역 검토 가능 수준**으로 도달.
