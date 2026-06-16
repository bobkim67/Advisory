# Frontier Neighborhood Explorer — 상태 (Status)

> R-track 2 SAA 리뷰 도구의 하위 기능. **review-only** (`is_production_selection=false`, `dry_run_only=true`).
> 목적: efficient frontier 최적 포트(min-var) 주변에 **동일 μ/Σ·동일 제약 하** risk-return 이
> 거의 같은 near-frontier feasible portfolio 가 얼마나 존재하는지 탐색·시각화.
> (Dirichlet / alpha / sparse 샘플러와는 무관한 별개 region.)

## 제약 set — `frontier_relaxed_hy_cap_only`

- long-only + sum=1 + target return(equality) + **US HY ≤ 7%**
- **80:20 bucket · equity cap · asset-class band 미적용** → 기존 Dirichlet explorer(80:20 hard)와 **다른 feasible region**.
- 두 region 의 후보를 같은 set 으로 **혼합/직접비교 금지**. metadata 에 `included`/`excluded_constraints` 기록.
- frontier point = target equality, neighborhood = return tolerance(default 5bps).

## Phase 1 — backend ✅ (origin/main `154b2ae` 커밋·푸시 완료)

- `tdf_engine/optimization/frontier_neighborhood.py` (numpy/scipy)
  - `solve_frontier_point` — SLSQP min-var, target equality.
  - **Method A** `local_feasible_perturbation` — null([1ᵀ;μᵀ]) 방향, **활성 자산(support) 내 재분배**만
    (코너해 0% 자산이 전체 null 방향을 막아서). shell 이차식으로 t 범위를 풀어 vol ≤ min_vol + max_gap 보장.
  - **Method B** `asset_weight_maximizer / minimizer` — variance-gap shell QCQP, 자산별 weight max/min
    (0% 자산의 활성화 가능 여부를 여기서 포착).
- `api/frontier_neighborhood.py` — **POST `/api/r-track/frontier-neighborhood`** (`main.py` 등록).
  - μ/Σ 는 기존 explorer 와 동일하게 `saa_diagnostics.cma` 에서 추출 → frontier·neighborhood 동일 CMA 보장.
  - SHA256 FIFO 캐시. review-only 강제.
- `api/schemas.py` — `FrontierNeighborhoodRequest/Response`, `FrontierPoint`, `FrontierNeighborhoodCandidate`.
- `tests/test_frontier_neighborhood.py` — **21 passed.** 신규 회귀 0.
- 실측(file CMA): frontier 9점, fp8 vol 7.07% · HY 7% cap. **dm(frontier 0%)이 +100bp 안에서 max 29.7%까지 양수화**.

## Phase 2 — frontend UI wiring ✅ (scratch, gitignored — repo 미추적)

> 위치: `scratch/r_track_2_candidate_review/d5_react_lasso_spike/`.
> `.gitignore` 의 `**/scratch/` 패턴으로 **git 추적 대상 아님 — 로컬 워킹트리에만 존재.**
> tsc + vite build PASS.

- `SourceTypeFilter.tsx` (신규) — 4 layer 독립 토글
  (efficient_frontier / frontier_optimal / frontier_neighborhood / dirichlet_background) + feasible-region 경고문. OverlayPanel 대체.
- `App.tsx` — `loadFrontierNeighborhood()` POST fetch + `fnState`.
  candidates = frontier neighborhood 후보(lasso/shortlist 대상), dirichlet 은 background 로 강등.
  **α 슬라이더 제거 → α=1.0 config-only 상수화.**
- `LassoScatter.tsx` — layered 렌더링: dirichlet background(흐린 회색) + neighborhood(vol_gap shell 별 색상 +10/25/50/100bp)
  + efficient frontier line(녹색) + frontier optimal(◆).
- `types.ts` — `FrontierPoint` / `FrontierNeighborhoodResponse` / `SourceType` 등 추가.

## Phase 3 — 미진행

- secondary plot (frontier_gap × allocation_distance, L1 × vol_gap)
- frontier detail panel
- **lasso export 통합** — 현재 "Build representative review" 는 dirichlet oppPath 참조 →
  frontier neighborhood 선택 export 시 mismatch 가능. Phase 3 에서 통합.
- §10.9 테스트.
- 불변 원칙: **frontier neighborhood 와 Dirichlet 후보를 같은 set 으로 섞지 말 것.**

## 운영 메모

- 신규 endpoint/스키마 변경마다 **uvicorn 재시작 필요** (`--reload` 권장). stale uvicorn 이 "frontier 안 됨" 오진의 반복 원인.
- FastAPI entry = `api.main:app` (port 8000). frontend dev = Vite (port 5173).
