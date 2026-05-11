# Phase E-6 — Relaxed Output Visualization Design

작성일: 2026-05-08. **E-6 (relaxed_diagnostic 산출물 시각화 설계)**.
설계 + 최소 구현 범위 제안만. 본 문서로 인한 코드 / config / 산출물 변경 없음.

> **Phase D completed register-blocker resolution only.**
> **This does not mean production readiness.**
> **The engine remains in relaxed_diagnostic mode.**

> 본 문서는 relaxed_diagnostic 산출의 **해석 보조 시각화** 설계. allocation 결과 / optimizer / TAA / selection 로직 / cap·band·threshold / Decision Register / production mode 모두 무변경.

---

## 0. TL;DR

- 정적 차트(matplotlib PNG) 6종 설계. 그 중 **MVP 5종** 확정.
- 신설 모듈 `tdf_engine/reporting/figures.py` (단일 파일, review.py 패턴 일관).
- 신설 CLI `tdf_engine/tools/render_figures.py` (기존 `render_review.py` 와 짝).
- 출력 위치 `out/db_review_relaxed/figures/<as_of_date>/*.png` + `figures_summary_<as_of_date>.md`.
- **기존 review_*.md 변경 없음** — 별도 figures_summary 로 분리.
- 입력 = `portfolio_*.json` 만. allocation 결과 미수정 보장.
- 추천 진행 범위: **이번 턴 = 설계까지**, 다음 턴 = 최소 구현 (사용자 선호와 정합).

---

## A. 시각화 목적

| 측면 | 내용 |
|---|---|
| **위상** | 본 시각화는 relaxed_diagnostic 산출의 **해석 보조 자료**. production portfolio 처럼 보이게 하려는 것이 **아님**. |
| **목적** | optimizer / TAA / selection / fallback 단계의 쏠림 / 한계 / 정책 영향을 **한눈에 파악**. 운용역 review packet 정독 시간 단축. |
| **사용처** | E-2 governance review (특히 §4 Review Checklist), E-3/E-4/E-5 candidate 트리거 누적 관찰. |
| **금지 사항** | (a) 차트 자체를 production 자료 / 고객 자료에 직접 사용. (b) 차트 결과로 allocation 자동 변경. (c) 시각적 인상으로 sign-off 결정 (체크리스트 + 수치 우선). |
| **핵심 표기** | 모든 차트에 `RELAXED DIAGNOSTIC RUN — NOT a production portfolio` 워터마크 또는 footer 강제. |

---

## B. 필수 시각화 6종

### B-1. Asset Allocation Bar Chart

| 항목 | 값 |
|---|---|
| 종류 | vertical or horizontal bar |
| 입력 | `asset_allocation[].final_asset_weight`, `asset_key`, `asset_name`, `bucket` |
| x | asset_key (9 자산, bucket 그룹 → weight 내림차순 정렬) |
| y | weight (0~100%) |
| 색상 | bucket — equity / fixed_income 2 색 |
| 표기 | bar 위 weight 라벨, equity·fixed_income bucket 합계 가로선 (sanity range [60-95] / [5-40] 점선) |

### B-2. SAA → TAA → Final Transition Chart

| 항목 | 값 |
|---|---|
| 종류 | grouped bar (asset 별 3 bar) 또는 slope chart |
| 입력 | `saa_weight` (None → strategic_allocation reference 보완), `taa_target_weight_before_projection`, `final_asset_weight` |
| 의도 | TAA tilt 방향 + projection clipping 효과 시각화 |
| 표기 | "TAA = prototype heuristic overlay" footer + projection_drift 음수 자산 (kr_t10 / ust30) 강조 |
| 주의 | saa_weight = None 케이스 다수 → reference value 사용 명시. raw vs reference 출처 라벨 분리 |

### B-3. Drift Decomposition Chart

| 항목 | 값 |
|---|---|
| 종류 | horizontal diverging bar 또는 waterfall |
| 입력 | `drift_clipping_summary.outflow_by_asset` (음수), `inflow_by_asset` (양수), `drift_source_by_asset` (5-source taxonomy) |
| 색상 | drift_source 별 (`product_cap_clipping_outflow`, `fallback_redistribution_inflow`, `long_only_clipping`, `redistribution_from_long_only_clipping`, `none`) |
| 의도 | 어느 자산이 어떤 source 로 얼마나 drift 했는지 한눈에 |
| 표기 | total outflow / inflow 합계 (mass conservation 확인), enforcement_mode = telemetry_only banner |

### B-4. Top Product Concentration Chart

| 항목 | 값 |
|---|---|
| 종류 | horizontal bar (top 5 또는 top 10) |
| 입력 | `product_allocation[].final_weight` 내림차순 |
| x | weight |
| y | product_name (manager 표기) |
| 색상 | asset_key (9 자산) |
| 표기 | ETF cap 20% / Fund cap 30% 점선, fallback_absorbed_weight 별도 hatching 또는 stacked 표시 |

### B-5. Manager Concentration Chart

| 항목 | 값 |
|---|---|
| 종류 | horizontal bar |
| 입력 | `product_allocation` 을 `manager` 로 group + sum(`final_weight`) |
| x | weight |
| y | manager (top N) |
| 색상 | bucket 또는 단색 |
| 표기 | ETF cap 60% / Fund cap 50% reference 점선 (D-14 monitoring), cap 도달 시 별도 색상 |

### B-6. Diagnostic Status Cards

| 항목 | 값 |
|---|---|
| 종류 | matplotlib subplot grid (3×3 또는 2×4) |
| 입력 | `review_summary.*`, `diagnostics.regime.*` |
| 카드 | (1) constraints_passed, (2) quality_status, (3) asset_weight_sum, (4) equity bucket %, (5) fixed_income bucket %, (6) max_abs_projection_drift, (7) max_abs_asset_weight_drift, (8) fallback_used, (9) regime_label / placement / velocity |
| 색상 | 통과 / 주의 / 실패 3 단계 (relaxed_diagnostic mode 에서 sanity 이탈은 ⚠ 황색만, 적색 없음) |
| 표기 | enforcement_mode = telemetry_only 명시. operating_mode banner 상단 고정 |

---

## C. ETF / Fund / Comparison 별 차트 매트릭스

| # | 차트 | ETF run | Fund run | Comparison |
|:---:|---|:---:|:---:|:---:|
| B-1 | Asset Allocation Bar | ✓ | ✓ | ✓ (ETF / Fund 좌우 병치) |
| B-2 | SAA → TAA → Final | ✓ | ✓ | — (SAA / TAA 동일하므로 비교 의미 적음) |
| B-3 | Drift Decomposition | ✓ | ✓ | △ (drift 합계 비교만 — 부록) |
| B-4 | Top Product Concentration | ✓ | ✓ | ✓ (top 5 ETF vs top 5 Fund) |
| B-5 | Manager Concentration | ✓ | ✓ | ✓ (top 5 manager 비교) |
| B-6 | Diagnostic Status Cards | ✓ | ✓ | △ (요약 1 카드 — 부록) |

> ✓ = 필수, △ = 선택, — = 미생성.
> Comparison 의 △ 항목은 MVP 범위에서 제외.

---

## D. 입력 데이터 소스

### D.1 1차 소스 (필수, json — 정밀)

| 소스 | 차트 | 세부 필드 |
|---|---|---|
| `out/db_etf_relaxed/portfolio_etf_<date>.json` | B-1 ~ B-6 (ETF) | `asset_allocation`, `product_allocation`, `diagnostics.quality.{drift_source_by_asset,drift_clipping_summary,asset_weight_drift}`, `projection_summary`, `review_summary`, `diagnostics.regime` |
| `out/db_fund_relaxed/portfolio_fund_<date>.json` | B-1 ~ B-6 (Fund) | 동일 schema |

### D.2 2차 소스 (보조, optional)

| 소스 | 사용 |
|---|---|
| `out/db_etf_relaxed/review_etf_<date>.md` | figures_summary 작성 시 banner / §3.1 표 정성 인용 (선택) |
| `out/db_fund_relaxed/review_fund_<date>.md` | 동 |
| `out/db_review_relaxed/comparison_etf_vs_fund_<date>.md` | comparison 차트 footer 의 정성 메모 (선택) |
| `tdf_engine/config/tdf_2060.yaml::strategic_allocation` + `taa_sanity_range` | B-1 sanity range 점선 / B-2 SAA reference 보완 |
| `tdf_engine/config/taa_policy.yaml::regime_tilts` | B-2 footer (TAA = prototype heuristic 명시) |

### D.3 사용 금지 (allocation 변경 위험)

| 소스 | 사유 |
|---|---|
| `tdf_engine` 의 optimizer / projection / selection 직접 호출 | 산출 재계산 위험 → allocation 결과 변동 가능. **금지**. |
| DB 직접 query | 산출 시점 외부 데이터 → run 결과와 불일치 위험. 시각화는 산출 json 한정. |

---

## E. 출력 형식

### E.1 디렉터리 구조

```
out/db_review_relaxed/
├── comparison_etf_vs_fund_<date>.md           (기존 — 변경 없음)
└── figures/                                    (신설)
    └── <as_of_date>/                           (신설, run 별)
        ├── etf/
        │   ├── 01_asset_allocation.png
        │   ├── 02_saa_taa_final.png
        │   ├── 03_drift_decomposition.png
        │   ├── 04_top_products.png
        │   ├── 05_manager_concentration.png
        │   └── 06_status_cards.png
        ├── fund/
        │   └── (동 6 파일)
        └── comparison/
            ├── 01_asset_allocation_compare.png
            ├── 04_top_products_compare.png
            └── 05_manager_concentration_compare.png

out/db_review_relaxed/figures_summary_<date>.md  (신설)
```

### E.2 파일 명명 규칙

| 항목 | 규칙 |
|---|---|
| 파일 prefix | `01_` ~ `06_` (B-1 ~ B-6 와 1:1 매핑, 정렬 고정) |
| 파일 형식 | PNG (정적, dpi=150 기본) |
| 파일 크기 | 1280 × 720 기본, status cards 만 1600 × 1000 |
| polarity | 본 단계에서는 PNG 만. SVG / PDF 는 후속. |

### E.3 figures_summary_<date>.md

기존 review_*.md 와 별도 신설. 6 차트 이미지 링크 + 1줄 캡션 + relaxed banner. **review_*.md 자체는 변경 안 함**.

```markdown
# Relaxed Diagnostic Run — Visualization Summary
> RELAXED DIAGNOSTIC RUN — NOT a production portfolio
> as_of_date: <date>, operating_mode: relaxed_diagnostic

## ETF
![asset allocation](figures/<date>/etf/01_asset_allocation.png)
![SAA → TAA → Final](figures/<date>/etf/02_saa_taa_final.png)
...

## Fund
...

## Comparison
...

## 출처
- portfolio_etf_<date>.json
- portfolio_fund_<date>.json
- comparison_etf_vs_fund_<date>.md
```

### E.4 향후 dashboard 확장 가능성 (부록 only)

본 단계에서는 **정적 PNG + markdown** 만. 다음은 **부록 언급만** (정식 합의 아님):

- (E-6 후속 candidate) plotly / dash 기반 interactive 대시보드
- (E-6 후속) HTML 통합 리포트 (figures_summary 를 HTML 로 렌더)
- (E-6 후속) 시계열 누적 차트 (run 누적 후, governance log 와 결합)

위 모두 정식 candidate 아님. 본 설계 범위 = 정적 PNG 만.

---

## F. 차트별 표시 항목 (상세)

### F-1. asset allocation chart (B-1)

| 표시 항목 | 출처 |
|---|---|
| asset_key (x label) | `asset_allocation[].asset_key` |
| weight (y, %) | `asset_allocation[].final_asset_weight × 100` |
| bucket 그룹 색상 | `asset_allocation[].bucket` (equity=색1, fixed_income=색2) |
| equity bucket 합계 가로선 | `review_summary.equity_bucket_weight × 100` |
| fixed_income bucket 합계 가로선 | `review_summary.fixed_income_bucket_weight × 100` |
| sanity range 점선 | `tdf_2060.yaml::taa_sanity_range` (equity [60, 95], fixed_income [5, 40]) |
| relaxed banner | `tdf_2060.yaml::operating_mode` |

### F-2. SAA → TAA → Final transition (B-2)

| 표시 항목 | 출처 |
|---|---|
| asset_key (x or y) | `asset_allocation[].asset_key` |
| SAA weight | `asset_allocation[].saa_weight` (None 시 `tdf_2060.yaml::strategic_allocation` reference) |
| TAA target weight | `asset_allocation[].taa_target_weight_before_projection` |
| Final weight | `asset_allocation[].final_asset_weight` |
| projection drift 강조 | `asset_allocation[].projection_drift` (절대값 0.01 이상 음영) |
| TAA prototype footer | `taa_policy.yaml::policy_metadata` 또는 고정 문구 |

### F-3. drift decomposition (B-3)

| 표시 항목 | 출처 |
|---|---|
| asset_key | `drift_clipping_summary.outflow_assets` ∪ `inflow_assets` |
| outflow magnitude | `drift_clipping_summary.outflow_by_asset[asset]` (음수 표기) |
| inflow magnitude | `drift_clipping_summary.inflow_by_asset[asset]` (양수 표기) |
| drift source 색상 | `drift_source_by_asset[asset]` (5-source taxonomy) |
| total outflow / inflow | `drift_clipping_summary.total_outflow_magnitude`, `total_inflow_magnitude` |
| primary source | `drift_clipping_summary.drift_source_primary` |
| enforcement_mode banner | `diagnostics.quality.enforcement_mode` (telemetry_only) |

### F-4. top product concentration (B-4)

| 표시 항목 | 출처 |
|---|---|
| product_name (y) | `product_allocation[].product_name` (top N) |
| weight (x, %) | `product_allocation[].final_weight × 100` |
| asset_key 색상 | `product_allocation[].asset_key` |
| manager 부기 | `product_allocation[].manager` (label 끝 괄호) |
| fallback 표시 | `product_allocation[].fallback_absorbed_weight` (hatching 또는 별도 layer) |
| product cap 점선 | ETF=20%, Fund=30% (`tdf_2060.yaml::product_caps` 또는 selection 정책) |

### F-5. manager concentration (B-5)

| 표시 항목 | 출처 |
|---|---|
| manager (y) | groupby `product_allocation[].manager` |
| 합산 weight (x, %) | `sum(final_weight) by manager × 100` |
| product 수 (label 부기) | `count(product_id) by manager` |
| manager cap reference 점선 | ETF=60%, Fund=50% (D-14 monitoring) |
| cap 도달 manager 별도 색 | weight ≥ cap 시 강조 (D-14 monitoring) |

### F-6. diagnostic status cards (B-6)

| 카드 | 출처 | 통과 기준 |
|---|---|---|
| constraints_passed | `review_summary.constraints_passed` | True |
| quality_status | `review_summary.quality_status` | clean / warning (relaxed 에서는 warning 허용) |
| asset_weight_sum | `review_summary.asset_weight_sum` | ≈ 1.0 (atol 1e-4) |
| equity bucket % | `review_summary.equity_bucket_weight × 100` | sanity [60, 95] |
| fixed_income bucket % | `review_summary.fixed_income_bucket_weight × 100` | sanity [5, 40] |
| max_abs_projection_drift | `review_summary.max_abs_projection_drift` | telemetry only (threshold 3%) |
| max_abs_asset_weight_drift | `review_summary.max_abs_asset_weight_drift` | telemetry only |
| fallback_used | `review_summary.fallback_used` | informational (False=clean, True=warning) |
| regime_label | `diagnostics.regime.regime_label` (+ placement / velocity) | informational |

---

## G. MVP (현재 단계 구현 최소 범위)

권장 MVP 5종 = 사용자 권장 그대로 채택.

| MVP # | 차트 | 대상 |
|:---:|---|---|
| MVP-1 | B-1 Asset Allocation | ETF + Fund |
| MVP-2 | B-1 Asset Allocation Compare | ETF vs Fund (병치) |
| MVP-3 | B-3 Drift Summary | ETF + Fund |
| MVP-4 | B-4 Top Products | ETF + Fund |
| MVP-5 | B-5 Manager Concentration | ETF + Fund |

**MVP 제외**:
- B-2 SAA → TAA → Final (saa_weight=None 처리 추가 작업 필요 → 후순위)
- B-6 Status Cards (다중 subplot 레이아웃 → 후순위)
- B-3 / B-4 / B-5 의 Comparison 차트 (병치 1종만 MVP)

**MVP 산출 파일** (총 11 파일):

```
out/db_review_relaxed/figures/<as_of_date>/
├── etf/
│   ├── 01_asset_allocation.png
│   ├── 03_drift_decomposition.png
│   ├── 04_top_products.png
│   └── 05_manager_concentration.png
├── fund/
│   ├── 01_asset_allocation.png
│   ├── 03_drift_decomposition.png
│   ├── 04_top_products.png
│   └── 05_manager_concentration.png
└── comparison/
    └── 01_asset_allocation_compare.png

out/db_review_relaxed/figures_summary_<as_of_date>.md
```

---

## H. 구현 범위 점검

### H.1 모듈 위치

| 항목 | 권장 |
|---|---|
| 차트 생성 모듈 | **`tdf_engine/reporting/figures.py`** (단일 파일, review.py 패턴 일관) |
| (대안) | `tdf_engine/reporting/visualization/` 패키지 분리 — 차트 종류 5+ 늘어날 때 채택. 본 MVP 단계에서는 over-engineering. |
| 데이터 어댑터 | 같은 파일 내 함수 — `_load_portfolio_json(path) -> dict`, `_extract_drift_records(diagnostics_quality) -> list`, `_group_by_manager(product_allocation) -> dict` |
| 차트 함수 시그니처 | `def plot_asset_allocation(portfolio_json: dict, out_path: Path, *, banner: str) -> Path:` 형태로 통일. 입력은 json dict + out_path, 출력은 PNG 경로. |
| 의존성 | matplotlib (이미 3.10.8 설치). seaborn 사용 안 함 (의존성 최소화). |

### H.2 reporting 패키지 vs tools 패키지

| 책임 | 위치 |
|---|---|
| **순수 시각화 함수** (json → PNG) | `tdf_engine/reporting/figures.py` |
| **CLI orchestration** (CLI 인자 → run paths → 함수 호출 → figures_summary 생성) | `tdf_engine/tools/render_figures.py` (신설) |

review.py 와 동일한 분리. **figures.py 는 build_portfolio.py 흐름과 분리** — allocation 결과 재계산 위험 차단.

### H.3 CLI 설계

신설 `tdf_engine/tools/render_figures.py`:

```
python -m tdf_engine.tools.render_figures \
    --as-of-date 20260508 \
    --portfolio-type etf,fund,comparison \
    --in-dir out \
    --out-dir out/db_review_relaxed/figures \
    --summary-md out/db_review_relaxed/figures_summary_20260508.md
```

| 인자 | 기본값 | 설명 |
|---|---|---|
| `--as-of-date` | 필수 | YYYYMMDD |
| `--portfolio-type` | `etf,fund,comparison` | comma-separated |
| `--in-dir` | `out` | portfolio_*.json 검색 root |
| `--out-dir` | `out/db_review_relaxed/figures` | PNG 저장 root |
| `--summary-md` | `out/db_review_relaxed/figures_summary_<date>.md` | 출력 markdown 경로 |
| `--mvp-only` | False | MVP 5종만 생성 (default 추천) |
| `--dry-run` | False | 파일 생성 없이 plan 출력 |

### H.4 markdown 이미지 삽입 정책

**기존 review_*.md / comparison_*.md 변경 안 함**. 별도 figures_summary_<date>.md 신설.

| 항목 | 규칙 |
|---|---|
| 이미지 경로 | figures_summary_<date>.md 와 같은 디렉터리 (`out/db_review_relaxed/`) 기준 상대 경로 → `figures/<date>/etf/01_asset_allocation.png` |
| alt text | 차트 제목 (예: "ETF Asset Allocation") |
| caption | 1줄 (예: "Equity 100% / Fixed Income 0%, us_growth_equity 60% (cap 도달)") — `review_summary` 에서 추출 |
| section 순서 | ETF → Fund → Comparison |
| banner | summary md 상단에 5줄 disclaimer 강제 (review.md 와 동일 문구) |

### H.5 단위 테스트 / 회귀 방어 (구현 단계 시)

| 테스트 | 위치 | 목적 |
|---|---|---|
| `test_figures_smoke.py` | `tests/` | 차트 함수 호출 → PNG 파일 생성 확인 (matplotlib backend Agg 강제) |
| 입력 검증 | 동 | empty `asset_allocation` / 빠진 키에 대한 ValueError |
| 비교 차트 정렬 | 동 | ETF / Fund asset_key 순서 일관성 |
| **portfolio json 미수정 보장** | 동 | 함수 호출 전후 json dict 동일성 (assert deep equal) |

위 테스트는 **본 설계의 일부가 아니라 구현 단계 (다음 턴) 의 산출**.

---

## I. 추천 진행 범위

### I.1 옵션 비교

| 옵션 | 범위 | 장점 | 단점 |
|---|---|---|---|
| **A. 설계만 (이번 턴)** | 본 문서까지 | spec-first 정합. 구현 전 stakeholder 검토 가능. 코드 변경 0. | 시각적 결과물 없음. |
| B. 설계 + 최소 구현 (이번 턴) | 본 문서 + figures.py + render_figures.py + figures_summary | 즉시 결과 확인. | turn 1 회 분량 초과 위험. 검증 부족 시 rework. |

### I.2 추천 = **옵션 A (설계만)**

근거:
1. 사용자 기본 선호: "이번 턴은 설계 + 구현안 제안까지" (요청 §3) — 일치.
2. 차트별 데이터 매핑은 schema 의존 → 설계 검토 후 구현 시 misalignment 위험 최소화.
3. matplotlib 차트 색상 / 레이아웃 / 정렬 / banner 문구는 검토 1 round 가 효율적.
4. `saa_weight=None` 처리, drift_source 색상 매핑, manager grouping rule 등은 운용역 1차 검토 후 확정 권장.

### I.3 다음 턴 (구현 turn) 의 작업 순서 (제안)

```
1. tdf_engine/reporting/figures.py 신설
   - load 함수 (json 파일 → dict)
   - 차트 함수 5종 (MVP)
   - banner / footer / 색상 팔레트 상수
2. tdf_engine/tools/render_figures.py 신설
   - argparse
   - run paths 검색
   - 차트 함수 호출
   - figures_summary_<date>.md 생성
3. tests/test_figures_smoke.py 신설
   - matplotlib backend=Agg
   - PNG 파일 생성 확인
   - portfolio json 미수정 assertion
4. 실제 run (현재 20260508) 으로 PNG 11 개 + summary md 생성
5. pytest 142 + α passed 확인
```

---

## J. 영향 / 변경 범위

| 영역 | 본 문서 | 다음 턴 (구현 시) |
|---|:---:|:---:|
| `tdf_engine/optimization/` | ✗ 무변경 | ✗ 무변경 |
| `tdf_engine/taa/` | ✗ 무변경 | ✗ 무변경 |
| `tdf_engine/selection/` | ✗ 무변경 | ✗ 무변경 |
| `tdf_engine/portfolio/` | ✗ 무변경 | ✗ 무변경 |
| `tdf_engine/reporting/review.py` | ✗ 무변경 | ✗ 무변경 |
| `tdf_engine/reporting/figures.py` | ✗ 미신설 | ✓ 신설 |
| `tdf_engine/tools/render_figures.py` | ✗ 미신설 | ✓ 신설 |
| `tdf_engine/config/*.yaml` | ✗ 무변경 | ✗ 무변경 |
| `tests/` | ✗ 무변경 | ✓ test_figures_smoke.py 신설 |
| `out/` 산출물 (portfolio_*, review_*, comparison_*) | ✗ 무변경 | ✗ 무변경 |
| `out/db_review_relaxed/figures/` | ✗ 미신설 | ✓ 신설 (PNG) |
| `out/db_review_relaxed/figures_summary_<date>.md` | ✗ 미신설 | ✓ 신설 |
| Decision Register status / count (14) | ✗ 무변경 | ✗ 무변경 |
| operating_mode (`relaxed_diagnostic`) | ✗ 무변경 | ✗ 무변경 |
| asset cap / band / threshold | ✗ 무변경 | ✗ 무변경 |
| TAA engine / 정책 / 수치 | ✗ 무변경 | ✗ 무변경 |
| 본 문서 신설 | ✓ `docs/phase_e_output_visualization_design.md` | — |

pytest: `142 passed, 5 skipped, 1 xfailed` (직전 baseline. 본 문서 작성으로 미실행, 영향 없음).

---

## K. 한 줄 요약

> **E-6 시각화 설계 — 정적 matplotlib PNG 6 차트 (MVP 5) + figures_summary md.
> 모듈 = `tdf_engine/reporting/figures.py`, CLI = `tdf_engine/tools/render_figures.py`.
> 입력 = portfolio_*.json 만, allocation 결과 미수정 보장.
> 기존 review / comparison md 변경 없음. 본 턴 = 설계까지, 다음 턴 = 최소 구현 (사용자 선호).
> Decision Register / TAA / cap / band / production mode 모두 무변경.**
