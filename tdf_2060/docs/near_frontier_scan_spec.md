# Near-Frontier Scan — 스펙 (batch frontier line scan)

> R-track 2 SAA 리뷰 도구. **review-only** (`is_production_selection=false`, `dry_run_only=true`).
> 목적: 단일 optimal 1점이 아니라 **녹색 MVO EF 라인 전체**를 따라, 각 expected-return
> node(anchor) 근처에 "성과 손실 거의 없이(near-frontier) 자산배분이 실질적으로 다른
> (active_share 큰)" 대안 포트가 존재하는지 **결정론적**으로 스캔한다.
> "각 수익률 수준에서 얼마나 다른 포트가 가능한가?"

## 1. Anchor = EF node (단일 w_star 폐기)
- anchor 집합 = EF 라인의 target-return 격자 node들 (`solve_frontier_point` per node, default 5%~12% @0.5%, 패널 target-return min/max/step 재사용).
- 각 anchor: `anchor_node_id`(=격자 index), `anchor_return`(=w@μ 실현), `anchor_vol`, `anchor_weights`, `anchor_sharpe`.
- infeasible anchor 는 skip + `infeasible_anchors` 로그.
- **max-Sharpe single-anchor diagnostic** 은 optional flag(`single_anchor_max_sharpe`)로만, 기본 off.

## 2. Anchor별 near-frontier band
- `abs(candidate_return − anchor_return) ≤ tol_return`
- `candidate_vol ≤ anchor_vol + tol_vol`
- + 기존 제약 동일: long-only, sum=1, HY≤cap, **per-asset floor/cap**, **위험자산 그룹 cap**(패널 입력 그대로).

## 3. Anchor별 directional optimization (band 안 SLSQP/QCQP)
| 방향 | objective | search_direction 라벨 |
|------|-----------|----------------------|
| asset over-weight | max wᵢ (anchor wᵢ>eps) | `overweight:{k}` |
| zero-weight forced entry | max wᵢ (anchor wᵢ≤eps) | `force_entry:{k}` |
| asset under-weight / active reduction | min wᵢ (anchor wᵢ>eps) | `underweight:{k}` |
| HHI 최소화 | min Σwᵢ² | `min_hhi` |
| random direction maximize | max dᵀw (d~N(0,1), K개) | `random:{j}` |

## 4. 후보 메트릭
- `active_share_vs_anchor = 0.5·Σ|w_candidate − w_anchor|`
- `return_gap_vs_anchor = candidate_return − anchor_return`
- `vol_gap_vs_anchor = candidate_vol − anchor_vol`
- `hhi = Σwᵢ²`, `zero_count`, `active_asset_count`, `max_asset_weight`, `us_hy_weight`

## 5. 후처리 파이프라인
1. **0.5% grid snap** (largest-remainder → sum=1·격자 유지, 기본 on) → return/vol/Sharpe/HHI/active_share **재계산** → band 재검증(이탈 시 drop).
2. **active_share filter**: `< active_share_min`(5%) drop, `≥ active_share_emphasis`(10%) 강조 flag.
3. **anchor_node_id별 dedupe (우선)**: 같은 anchor 내에서 `candidate_distance = 0.5·Σ|w_a − w_b| < dedupe_threshold`(1.5%) 면 병합(active_share 큰 쪽 유지).
4. **cross-anchor dedupe = summary/표시용 옵션** (`cross_anchor_dedupe` flag, 기본 off): main 후보는 per-anchor 유지(같은 후보가 여러 anchor 근처에 걸려도 보존 — 어느 target-return 구간에서 대안성이 나타나는지 정보 유지). flag on 시 후보에 `cross_anchor_duplicate_of`(더 낮은 anchor 후보와 근접 시 그 anchor_node_id) 만 표기, 제거하지 않음. summary 에 `cross_anchor_unique_count` 항상 포함.

## 6. 응답 컬럼 (frontier-node 기준)
`anchor_node_id, anchor_return, anchor_vol, candidate_return, candidate_vol, sharpe,`
`return_gap_vs_anchor, vol_gap_vs_anchor, active_share_vs_anchor, hhi, zero_count,`
`active_asset_count, max_asset_weight, us_hy_weight, search_direction, emphasis,`
`cross_anchor_duplicate_of, weights`

## 7. Backend
- 신규 모듈 `tdf_engine/optimization/near_frontier_scan.py` — `build_near_frontier_scan(...)`. `frontier_neighborhood` 의 `solve_frontier_point`/`_build_bounds`/`_within_bounds`/`_vol` 재사용. anchor solver + band directional solver + snap/active_share/dedupe.
- 신규 endpoint **`POST /api/r-track/near-frontier-scan`** — CMA추출(file/db_window)·asset_bounds·equity그룹 plumbing 은 `frontier_neighborhood` endpoint 와 동일(헬퍼 재사용). SHA 캐시. frozen `db_market_data`/baseline 미변경.
- `api/schemas.py` — `NearFrontierScanRequest/Response`, `NearFrontierScanAnchor`, `NearFrontierScanCandidate`.

## 8. Frontend (scratch) — 전용 secondary plot
- x=`anchor_return`, y=`active_share_vs_anchor`, color=`vol_gap_vs_anchor`(또는 return_gap 토글), size=`HHI`(또는 zero_count 토글).
- anchor 라인은 y≈0 기준선(초록). 후보는 위로 퍼짐 → "각 수익률에서 가능한 배분 다양성".
- hover = anchor_node_id/return + gap들 + active_share + search_direction + weights 요약. lasso/shortlist 연동.

## 9. Default 파라미터
`tol_return=10bps`, `tol_vol=25bps`, active_share drop `<5%` / 강조 `≥10%`, random `K=30`,
grid `0.5%`(snap on), dedupe `1.5%`, anchor grid = 패널 target-return min/max/step,
`single_anchor_max_sharpe=false`, `cross_anchor_dedupe=false`.

## 10. 검증
- 단위(fake CMA): anchor별 band 준수, active_share_vs_anchor 계산, snap sum=1/격자/band, per-anchor dedupe(candidate_distance), drop<min, infeasible anchor/direction skip 로그.
- endpoint smoke(file CMA): anchor ≥2, 후보 `candidate_vol ≤ anchor_vol + tol_vol + eps`(**vol_gap 부호 강제 금지** — snap/SLSQP/return-band 차이로 미세 음수 가능, 핵심은 band 준수), `abs(return_gap) ≤ tol_return + eps`, active_share≥min, 컬럼 스키마.
- 기존 frontier/per-asset/db_cma 회귀 0. tsc+vite + 라이브.

## 리스크/메모
- anchor ~15 × 방향 ~80 ≈ 수백~천 SLSQP → 수 초. K=30·SHA 캐시로 관리.
- snap 이 band/cap 미세 이탈 가능 → 재검증 drop 으로 흡수.
- random/perturbation 은 보조 — directional + active_share 가 본질.
