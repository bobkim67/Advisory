# R-track 2 Lasso/Polygon Selection — Data Contract (2026-05-14)

> **Schema 설계 문서.** SAA opportunity set scatter plot 위에서 운용역이
> lasso/polygon 으로 후보 영역을 그려 downstream dry-run 입력으로 export 하는
> 구조의 data contract. **실제 React UI 본구현 / final SAA 추천 / Phase F**
> **진입 선언 / production-ready 라벨 모두 본 문서 범위 밖.**
>
> 영구 라벨: `is_production_selection=false`, `dry_run_only=true`,
> `implementation_ready=false (strict)`. operating_mode `relaxed_diagnostic`.

---

## §0. TL;DR

- 10,000 후보 (R-1B.2 opportunity set) 위에 scatter plot 띄우고 **overlay cloud** 들 (Sharpe top / HHI high WARN / fallback WARN 등) 토글.
- 운용역이 마우스로 **polygon / lasso** 영역을 그리면 그 안의 candidate_id 들이 선택됨.
- 선택 결과 → JSON 으로 export (polygon 좌표 / 활성 overlay / selected ids 포함).
- Downstream: 단일 candidate 선택 → R-1F.1 yaml 변환 → R-1F.2 / R-1G.1 / R-1G.2 dry-run 흐름.
- **본 contract 는 schema 만 규정.** 실제 UI 구현, 라이브러리 선택, 백엔드 endpoint 모두 본 문서 범위 밖.

---

## §1. UI / Data Model Overview

### §1.1 Scatter plot mental model

| 요소 | 설명 |
|---|---|
| 점 (point) | 1 candidate (10,000 점) |
| x 축 | 사용자 선택 metric (default `volatility`) |
| y 축 | 사용자 선택 metric (default `expected_return`) |
| 색 / shape | 활성 overlay 의 tag flag 에 따라 변경 |
| reference points | `ref_max_sharpe`, `ref_80_20_equal_intra_bucket` (별도 marker) |

### §1.2 인터랙션 순서

```
1. 사용자가 x, y 축 metric 선택 (드롭다운)
2. overlay cloud 들 토글 (체크박스, 다중 선택 가능)
3. filter 조건 입력 (선택사항: feasibility=feasible 만, sharpe>=0.5, eq_intra<0.3 등)
4. lasso 또는 polygon 그리기 (UI 라이브러리 제공 도구)
5. 영역 내부 candidate_id 추출
6. post-selection rule 선택 (all / top_sharpe / min_hhi / representative_3 등)
7. JSON export → downstream
```

---

## §2. Source Data Prerequisites

| 데이터 | 경로 | 의미 |
|---|---|---|
| opportunity set JSON | `out/db_review_relaxed_e62/saa_opportunity_set/20260513/saa_opportunity_set_{etf,fund}_20260513.json` | 10,000 후보 raw metrics + reference points |
| cloud tags CSV (precomputed) | `scratch/r_track_2_candidate_review/candidate_cloud_tags.csv` | 후보별 overlay tag flags (본 contract §3 정의) |
| R-1G.2 batch outputs (8 cand) | `out/db_{etf,fund}_relaxed_e62_r1i_multi_candidate/cand_*/portfolio_*_20260513.json` | `has_fallback`, `has_universe_warning` 산출 입력 (batch 만) |

`source_opportunity_set_sha256` 필드로 lasso 결과가 어느 opportunity set 위에서 그려졌는지 추적.

---

## §3. Cloud Overlay Catalog

각 tag 는 candidate 단위 boolean. 사용자는 다중 overlay 동시 토글 가능 (시각적 색/모양 mix).

### §3.1 Performance overlays (neutral / informational)

| tag | 정의 | 임계 (10k pool 기준) | semantic |
|---|---|---|---|
| `is_sharpe_top` | top 10% by `sharpe` | `sharpe >= 0.6270` | Sharpe 상위. **자동 추천 아님 — overlay 만.** |
| `is_return_top` | top 10% by `expected_return` | `E[R] >= 11.42%` | E[R] 상위. **자동 추천 아님 — overlay 만.** |
| `is_low_vol` | bottom 10% by `volatility` | `σ <= 12.14%` | 저변동성. **자동 추천 아님 — overlay 만.** |
| `is_mvo_frontier_near` | bottom 10% by `mvo_efficiency_score` (작을수록 frontier 근접) | `score <= 0.0147` | MVO frontier 근접. R-1C 의 1 차원. |

### §3.2 Concentration / risk overlays (some WARN)

| tag | 정의 | 임계 | semantic |
|---|---|---|---|
| `is_hhi_low` | bottom 10% by `concentration_hhi` | `HHI <= 0.1717` | **분산형** (informational) |
| `is_hhi_high` | top 10% by `concentration_hhi` | `HHI >= 0.3035` | **WARN — 집중 cloud** (UI 색 = 경고색 권장) |
| `is_concentration_high` | top 10% by `max_asset_weight` | (10k pool 의 90th 백분위) | **WARN — single-asset 집중 cloud** |
| `is_corner_like` | `max_w > 0.50` OR `HHI > 0.50` OR `eq_intra_hhi > 0.50` OR `fi_intra_hhi > 0.50` | multi-criterion OR | **WARN — corner solution 가능성** |

### §3.3 Downstream signal overlays (batch only)

R-1G.2 dry-run 산출이 있는 후보 (현재 8 batch sample) 에만 정의됨. 그 외 후보는 **unknown** (CSV 빈 셀).

| tag | 정의 | semantic |
|---|---|---|
| `has_fallback` | `R-1G.2 diagnostics.portfolio_builder.fallback.fallback_used == true` | **WARN — cap clipping fallback 흡수 발생** |
| `has_universe_warning` | `R-1G.2 selected_count_by_asset[asset] < 3` (default core+satellite=3) | **WARN — product universe 한계** |

> 이 둘은 사전 R-1G.2 dry-run 이 돌아야만 알 수 있으므로, **lasso 선택 후 추가
> R-1G.2 batch 가 가능해야 완성된다**. 본 contract 는 batch=8 까지의 사전 데이터만
> overlay 로 사용.

### §3.4 Sweet spot overlay (R-1C 정합)

| tag | 정의 | semantic |
|---|---|---|
| `overlap_score` | R-1C 6 metric 중 만족하는 수 (0~6) | sweet spot proxy. UI 에서 size / opacity 로 표현 가능. |

R-1C `saa_opportunity_set_cloud_review_20260513.md` 의 decile 정의와 일치:
- `sharpe >= 0.6270`
- `mvo_efficiency_score <= 0.0147`
- `concentration_hhi <= 0.1717`
- `equity_intra_hhi <= 0.2435`
- `fixed_income_intra_hhi <= 0.2888`
- `max_asset_weight <= 25.66%`

(distribution: overlap≥3: 773건, ≥4: 71건, ≥5: 1건 = cand_008421 smoke, =6: 0건)

### §3.5 Warning vs neutral label 처리 원칙

- **WARN** 마킹된 tag (`is_hhi_high`, `is_concentration_high`, `is_corner_like`, `has_fallback`, `has_universe_warning`) 는 **자동 추천 candidate 아님**. UI 색은 경고색 (예: 빨강/주황) 권장.
- neutral tag (`is_sharpe_top`, `is_return_top`, `is_low_vol`, `is_mvo_frontier_near`, `is_hhi_low`) 는 informational. **Sharpe top 도 자동 추천 아님 — overlay 만.**
- 사용자가 WARN cloud 안의 후보를 의도적으로 선택하는 것은 허용 (운용 의도가 명시되어 있을 때). 하지만 선택 결과의 `warning_labels` 에 반드시 표기.

---

## §4. Selection Export Schema

### §4.1 Required fields

| field | type | 의미 |
|---|---|---|
| `selection_id` | string (UUID 또는 timestamp-based) | 선택 단위 식별자 (예: `lasso_20260514T103045Z_a1b2`) |
| `created_at` | ISO-8601 datetime | 선택 생성 시각 |
| `source_opportunity_set_path` | string | 사용된 opportunity set JSON 경로 |
| `source_opportunity_set_sha256` | string | 위 파일 sha256 |
| `coordinate_system` | object | `{x_metric, y_metric, x_unit, y_unit}` |
| `x_metric` | string | scatter x 축 metric (예: `"volatility"`) |
| `y_metric` | string | scatter y 축 metric (예: `"expected_return"`) |
| `polygon_points` | array of `[x, y]` | lasso/polygon vertex 좌표 (data space) |
| `active_overlays` | array of string | 선택 당시 토글된 overlay tag 들 |
| `active_filters` | object | 선택 당시 filter 조건 (예: `{feasibility_status: "feasible", min_sharpe: 0.5}`) |
| `selected_candidate_ids` | array of string | polygon 내부 candidate_id 목록 |
| `selected_count` | integer | `len(selected_candidate_ids)` |
| `selection_mode` | enum | `lasso` / `rectangle` / `cloud_click` / `manual_candidate_pick` |
| `post_selection_rule` | enum | `all` / `top_sharpe` / `min_hhi` / `representative_3` / `top_n_by_metric` |
| `is_production_selection` | bool **고정 false** | **영구 false.** runtime 에서 변경 금지. |
| `dry_run_only` | bool **고정 true** | **영구 true.** |
| `selected_by` | string | 운용역 식별자 (자유 텍스트, "automated" / "smoke" 등 금지) |
| `selection_reason` | string | 선택 사유 (자유 텍스트) |
| `warning_labels` | array of string | 본 선택에 포함된 WARN tag (`hhi_high_WARN`, `fallback_WARN` 등). UI 가 자동 채움. |

### §4.2 Selection mode

| mode | 입력 | 동작 |
|---|---|---|
| `lasso` | polygon_points (n>=3) | 다각형 내부 candidate 추출 (point-in-polygon) |
| `rectangle` | polygon_points (4점) | 직사각형 내부 추출 |
| `cloud_click` | active_overlays 만 | 활성 overlay tag 모두 만족하는 후보 추출 (polygon 없음) |
| `manual_candidate_pick` | selected_candidate_ids 직접 입력 | 운용역이 ID 명시 |

### §4.3 Post-selection rule

| rule | 동작 |
|---|---|
| `all` | polygon 내부 전체 ids 그대로 |
| `top_sharpe` | Sharpe 내림차순 1건 |
| `min_hhi` | HHI 오름차순 1건 (가장 분산된 1건) |
| `top_n_by_metric` | 추가 파라미터 `{metric: "sharpe", n: 5}` 로 top n |
| `representative_3` | polygon 내 weight 공간 클러스터링 후 3 대표 |

### §4.4 폴리곤 점-내부 판정 (point-in-polygon)

- 알고리즘: ray-casting (Jordan curve theorem)
- 경계선상 점은 **내부 포함** 처리
- self-intersecting polygon 은 거부 (UI 에서 차단 권장)

---

## §5. Polygon Coordinate Semantics

- 좌표는 **data space** (raw metric 값). pixel space 아님.
- `x_metric` / `y_metric` 변경 시 polygon_points 는 **그 좌표계에서 그려진 것**. 다른 metric 으로 재해석 금지.
- unit:
  - `volatility`, `expected_return`, `sharpe` → unitless decimal (예: `0.1269` = 12.69%)
  - `concentration_hhi`, `mvo_efficiency_score` → unitless
  - `max_asset_weight` → decimal (예: `0.2556` = 25.56%)

---

## §6. Downstream Connection (R-1F / R-1G)

### §6.1 단일 candidate 모드

`post_selection_rule = top_sharpe` 또는 `min_hhi` 또는 `manual_candidate_pick` 으로 1건 확정.
→ `manager_selection_input_skeleton.yaml` 의 `candidate_id` 필드에 채움.
→ R-1F.1 CLI (`tools/select_manager_saa.py`) 입력.
→ R-1F.2 (`run_manager_selected_dry_run.py`) → R-1G.1 (`run_product_reselection_dry_run.py`) → R-1G.2 (`build_r1g_reselected_portfolio.py`) 흐름.

### §6.2 다중 candidate 모드

`post_selection_rule = all` 또는 `top_n_by_metric` 으로 N건.
→ R-1I (`run_multi_candidate_comparison.py`) 입력 (batch comparison).

### §6.3 변환 흐름 (mock example 참조)

```
lasso_selection_example.json (§4 schema 따름)
  ↓ post_selection_rule 적용
manager_selection_from_lasso_example.yaml (R-1F.1 schema)
  ↓ tools/select_manager_saa.py
out/.../manager_selected_saa_<type>_<cand>_<as_of>.json (R-1F.1 dump)
  ↓ tools/run_manager_selected_dry_run.py
out/.../r1f2_dry_run_<type>_<as_of>.json (R-1F.2 asset-level)
  ↓ tools/build_r1g_reselected_portfolio.py
out/.../portfolio_<type>_<as_of>.json (R-1G.2 product-level + builder)
```

R-1F.1 yaml 변환은 mock example `manager_selection_from_lasso_example.yaml` 에서 시연.

---

## §7. Permanent Invariants

| 항목 | 값 |
|---|---|
| `is_production_selection` | **false (strict)** |
| `dry_run_only` | **true (strict)** |
| 자동 candidate 추천 | **금지** (overlay 도 informational 만) |
| `selected_by` 의 "automated" / "smoke" / "r1f1_smoke_test" 문자열 | **금지** (운용역 명시 식별자만) |
| Sharpe top / 기타 metric top 라벨로 자동 final SAA 확정 | **금지** |
| WARN cloud 내 선택 시 `warning_labels` 미기재 | **금지** (UI 가 자동 채워야 함) |
| `source_opportunity_set_sha256` 미일치 (재계산 후 입력) | **거부** — 일치하는 opportunity set 에서만 선택 유효 |

---

## §8. Non-Goals (본 contract 범위 밖)

- React / Vue / Streamlit / Dash 등 **실제 UI 본구현** — 별도 작업.
- 백엔드 endpoint / persistence (DB 저장 등) — 별도 작업.
- WebSocket / 실시간 collaboration — 별도 작업.
- 자동 candidate 추천 / scoring / ranking → 의도적으로 미정의.
- final SAA 확정 / Phase F 진입 / production 승격 — 본 schema 로 발생하지 않음.

---

## §9. Mock / Example Files

본 contract 를 검증하기 위한 mock (scratch, gitignored):

| 파일 | 용도 |
|---|---|
| `scratch/r_track_2_candidate_review/candidate_cloud_tags.csv` | 10,000 후보 cloud tag CSV (precomputed) |
| `scratch/r_track_2_candidate_review/lasso_selection_example.json` | §4 schema 예시 (polygon + selected ids + active overlays) |
| `scratch/r_track_2_candidate_review/manager_selection_from_lasso_example.yaml` | lasso 결과 → R-1F.1 yaml 변환 mock |
| `scratch/r_track_2_candidate_review/mock_lasso_selection.py` | point-in-polygon mock 함수 (검증용) |

mock 산출물은 **schema 검증 목적**. 실제 운용 입력 / 후보 추천 아님.

---

## §10. 본 문서 변경 범위

| 영역 | 변경 |
|---|:-:|
| 본 contract 문서 신규 (`tdf_2060/docs/r_track_2_lasso_selection_contract.md`) | ✓ 1건 |
| scratch 산출물 (cloud tags CSV + mock JSON/YAML/PY) | ✓ gitignored |
| 코드 (`tdf_engine/`) / config / out tracked 167 / Decision Register / phase_e_current_handoff.md / tests | ✗ 무변경 |
| React UI 본구현 / 백엔드 endpoint | ✗ 본 문서 범위 밖 |
| 자동 candidate 추천 / final SAA 확정 / Phase F 진입 선언 | ✗ 영구 금지 |

---

## §11. 한 줄 요약

> **Lasso/polygon 은 선택 입력 도구, 자동 추천 도구 아님.**
> 운용역의 명시 선택이 §4 schema 로 export → §6 downstream 으로 연결.
> WARN cloud 내 선택은 `warning_labels` 로 추적. 모든 export 는 `is_production_selection=false`, `dry_run_only=true` 영구.
