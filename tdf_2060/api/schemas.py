"""Pydantic schemas for the lasso export endpoint."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LassoExportRequest(BaseModel):
    """C-2 lasso selection contract payload (review-only)."""

    x_metric: str = Field(default="volatility")
    y_metric: str = Field(default="expected_return")
    polygon_points: list[list[float]] = Field(default_factory=list)
    selection_mode: Literal[
        "lasso", "rectangle", "cloud_click", "manual_candidate_pick"
    ] = "lasso"
    active_overlays: list[str] = Field(default_factory=list)
    active_filters: dict[str, Any] = Field(default_factory=dict)
    post_selection_rule: Literal[
        "all", "top_sharpe", "min_hhi", "top_n_by_metric", "representative_3"
    ] = "all"
    post_selection_params: dict[str, Any] = Field(default_factory=dict)
    selected_by: str
    selection_reason: str
    portfolio_type: Literal["etf", "fund"] = "etf"
    source_opportunity_set_path: str
    batch_results_dir: str | None = None
    output_dir: str | None = None  # optional; rejected if under tdf_2060/out|tdf_engine|tests|docs|config
    emit_yaml_preview: bool = False
    # E-2: optional client-supplied review packet metadata for R-1F.1 V-11
    # traceability. Both fields must be provided together or both omitted.
    # Server does NOT validate the path exists — it is recorded verbatim into
    # the yaml preview; downstream R-1F.1 CLI is the layer that performs the
    # strict path/sha256 check at runtime.
    source_review_packet_path: str | None = None
    source_review_packet_sha256: str | None = None


class PermanentInvariants(BaseModel):
    operating_mode: str = "relaxed_diagnostic"
    is_production_selection: bool = False
    dry_run_only: bool = True
    implementation_ready: bool = False
    production_applied: bool = False
    phase_f_entered: bool = False


class LassoExportResponse(BaseModel):
    lasso_selection_export: dict[str, Any]
    representative_review: dict[str, Any]
    selected_count: int
    warning_labels: list[str]
    null_archetypes: list[str]
    permanent_invariants: PermanentInvariants = Field(default_factory=PermanentInvariants)
    manager_selection_yaml_preview: str | None = None
    notes: list[str] = Field(
        default_factory=lambda: [
            "Lasso/polygon selection is a rule-based EXPORT, not an automated recommendation.",
            "Final SAA selection requires 운용역 명시 input via R-1F.1 yaml schema.",
            "downstream R-1F.* / R-1G.* CLIs are NOT auto-triggered by this endpoint.",
        ]
    )


# D-11: scatter dataset projection — frontend reads this to render the base
# 10k scatter so representative markers land on real coordinates.
#
# Phase 6.2 (2026-05-26): optional weights + per-bucket fields gated behind
# the `include_weights` query flag. Default response (flag=false) keeps the
# original minimal shape; existing consumers see only `null` for the new
# keys (backward-compat: extra-key tolerant). When flag=true, the dataset
# response also carries `asset_keys / asset_labels / asset_buckets` so the
# UI can render asset-class detail without a second fetch.
class ScatterCandidate(BaseModel):
    candidate_id: str
    volatility: float
    expected_return: float
    sharpe: float
    concentration_hhi: float
    max_asset_weight: float
    mvo_efficiency_score: float
    feasibility_status: str
    overlap_score: int
    cloud_labels: str
    has_fallback: bool | None
    has_universe_warning: bool | None
    # Phase 6.2 optional fields — populated only when include_weights=true.
    weights: dict[str, float] | None = None
    equity_weight: float | None = None
    fixed_income_weight: float | None = None
    equity_intra_hhi: float | None = None
    fixed_income_intra_hhi: float | None = None
    equity_max_asset_weight: float | None = None
    fixed_income_max_asset_weight: float | None = None
    nonzero_asset_count: int | None = None


class ScatterDatasetResponse(BaseModel):
    schema_version: str = "r_track_2_scatter.1"
    source_opportunity_set_path: str
    source_opportunity_set_sha256: str
    candidate_count: int
    candidates: list[ScatterCandidate]
    is_production_selection: bool = False
    dry_run_only: bool = True
    notes: list[str] = Field(
        default_factory=lambda: [
            "Projection of R-1B.2 opportunity set for UI scatter rendering only.",
            "Drops weights / per-bucket HHI to keep payload small.",
            "is_production_selection=false / dry_run_only=true forced.",
        ]
    )
    # Phase 6.2 optional dataset-level metadata for shortlist / detail panel.
    # None when include_weights=false.
    include_weights: bool = False
    asset_keys: list[str] | None = None
    asset_labels: dict[str, str] | None = None
    asset_buckets: dict[str, str] | None = None
    # 2026-05-27 — Sharpe 계산에 사용된 연율 risk-free rate (출처:
    # optimization_constraints.yaml::objective_params.risk_free_rate).
    # frontend Sharpe 카드에 주석 표기용. opportunity_set 의 inputs.risk_free_rate
    # 값을 그대로 전달.
    risk_free_rate: float | None = None
    # Phase 6.5 — custom endpoint 응답시 partial result / 입력 echo.
    # GET scatter endpoint 응답에서는 None (precomputed JSON 이라 무관).
    sampling_warning: str | None = None
    equity_bucket_total: float | None = None
    fixed_income_bucket_total: float | None = None
    # Phase 6.5c — 외부 reference 포트폴리오 (예: Excel 해찾기 결과) 를 현재 CMA 로
    # 평가한 좌표. scatter 에 별도 마커로 오버레이. candidate_id = label.
    reference_points: list[ScatterCandidate] | None = None


class ReferencePortfolio(BaseModel):
    """현재 CMA 평면 위에 오버레이할 외부 reference 포트폴리오."""

    label: str
    weights: dict[str, float]  # {asset_key: weight} (합 1 권장; 누락 자산 = 0)


class CustomOpportunitySetRequest(BaseModel):
    """Phase 6.5 panel POST request payload (review-only).

    실행 버튼 클릭 시 좌측 자산 패널의 현재 상태를 보내 build_opportunity_set 을
    호출. 동일 입력에 대해 동일한 deterministic 결과를 반환 (seed 고정).
    """

    portfolio_source: str = Field(
        default="out/baseline_regen_20260527/portfolio_etf_20260527.json",
        description="CMA source portfolio JSON path (engine-root 상대)",
    )
    equity_total: float = Field(default=0.80, ge=0.0, le=1.0)
    fixed_income_total: float = Field(default=0.20, ge=0.0, le=1.0)
    # asset_constraints[asset_key] = [floor, cap]
    asset_constraints: dict[str, list[float]] | None = None
    selected_assets: list[str] | None = None
    n_candidates: int = Field(default=10000, ge=10, le=50000)
    random_seed: int = Field(default=42)
    max_attempts_multiplier: int = Field(default=5, ge=1, le=50)
    include_weights: bool = True
    # Sharpe 계산 rf override (연율). 기본 2.5% — 엔진 config (0.030) /
    # frozen baseline 미변경, 리뷰 도구 표시 rf 만 조정.
    risk_free_rate: float = Field(default=0.025, ge=0.0, le=0.2)
    # 외부 reference 포트폴리오 (Excel 해찾기 결과 등) — 현재 CMA 로 평가해 오버레이.
    reference_portfolios: list[ReferencePortfolio] | None = None
    # Phase 6.5c — 라이브 MVO (min-variance) 최적해. 현재 CMA + 제약으로 실시간 산출.
    mvo_enabled: bool = False
    mvo_target_return: float = Field(default=0.08, ge=0.0, le=0.5)
    mvo_risk_asset_cap: float = Field(default=0.79, ge=0.0, le=1.0)
    mvo_hy_cap: float = Field(default=0.07, ge=0.0, le=1.0)
    # Phase 6.5e — Dirichlet 집중도 α. 1.0=내부 균등(기본), <1=코너/sparse 선호,
    # >1=중심 집중. bit-identical 유지 위해 default 1.0.
    dirichlet_alpha: float = Field(default=1.0, ge=0.05, le=10.0)
    # Phase 6.5f — MVO 효율적 프론티어 스윕. target return 격자마다 min-var 최적해
    # (코너해 집합). risk/HY cap 은 mvo_* 와 동일 적용.
    mvo_frontier_enabled: bool = False
    mvo_frontier_min: float = Field(default=0.05, ge=0.0, le=0.5)
    mvo_frontier_max: float = Field(default=0.09, ge=0.0, le=0.5)
    mvo_frontier_step: float = Field(default=0.005, ge=0.001, le=0.05)


# ---------------------------------------------------------------------------
# Frontier Neighborhood Explorer (review-only)
#   efficient frontier 최적 포트 주변의 near-frontier feasible portfolio cloud.
#   제약 set = frontier_relaxed_hy_cap_only (long-only, sum=1, target, HY<=cap).
#   80:20 bucket / equity cap / asset-class band 미적용. Dirichlet cloud 와 별개.
# ---------------------------------------------------------------------------


class FrontierNeighborhoodRequest(BaseModel):
    """POST /api/r-track/frontier-neighborhood payload (review-only)."""

    portfolio_source: str = Field(
        default="out/file_mode_cma_20260528/portfolio_etf_20260528.json",
        description="CMA source portfolio JSON path (engine-root 상대)",
    )
    hy_key: str = Field(default="us_high_yield")
    hy_cap: float = Field(default=0.07, ge=0.0, le=1.0)
    # rf: None → portfolio saa rf 사용. Sharpe 표시에만 영향 (μ/Σ 불변).
    risk_free_rate: float | None = Field(default=0.025, ge=0.0, le=0.2)
    # target return 격자 (frontier point 생성). equality.
    target_return_min: float = Field(default=0.05, ge=0.0, le=0.5)
    target_return_max: float = Field(default=0.12, ge=0.0, le=0.5)
    target_return_step: float = Field(default=0.005, ge=0.001, le=0.05)
    # neighborhood shell (변동성 gap, bps) + return tolerance (bps).
    vol_gaps_bps: list[int] = Field(default_factory=lambda: [10, 25, 50, 100])
    return_tolerance_bps: float = Field(default=5.0, ge=0.0, le=200.0)
    # method A (perturbation) 강도.
    n_directions: int = Field(default=80, ge=1, le=2000)
    steps_per_direction: int = Field(default=2, ge=1, le=20)
    # method B (variance-gap shell asset weight max/min, QCQP) 포함 여부.
    method_b: bool = True
    random_seed: int = Field(default=42)
    include_weights: bool = True
    # Random Cloud + EF Overlay 모드 — relaxed region random cloud (long-only,
    # sum=1, HY<=cap) + EF overlay. neighborhood(exact-slice)는 advanced 용.
    include_neighborhood: bool = True
    include_random_cloud: bool = False
    n_random_samples: int = Field(default=4000, ge=10, le=50000)
    random_cloud_alpha: float = Field(default=1.0, ge=0.05, le=10.0)
    # 주식비중 밴드 (equity bucket=주식+금). random cloud + EF solver 양쪽에 동일
    # 제약으로 적용. 기본 0~1 = 무제약(relaxed). HY<=7% 와 같은 성격의 제약.
    equity_weight_min: float = Field(default=0.0, ge=0.0, le=1.0)
    equity_weight_max: float = Field(default=1.0, ge=0.0, le=1.0)
    # equity 밴드의 "주식비중" 정의 그룹 (asset_key 목록). None 이면 bucket=="equity"
    # (주식5+금) default. 3-mode 토글(주식 / 주식+금 / 주식+금+HY)을 frontend 가
    # 해당 키 목록으로 보냄. 밴드는 상한만 의미 있게 쓰지만 min/max 둘 다 지원.
    equity_weight_keys: list[str] | None = Field(default=None)
    # per-asset (floor, cap) 제약 — {asset_key: [floor, cap]}. EF solver + random cloud
    # + Method B 에 적용. 미지정 자산은 (0,1). HY 는 hy_cap 과 intersect.
    asset_constraints: dict[str, list[float]] | None = Field(default=None)
    # CMA 소스. "portfolio" = portfolio_source JSON 의 saa_diagnostics.cma 사용(default,
    # 기존 동작). "db_window" = SCIP DB 에서 [db_window_start, db_window_end] 구간으로
    # 라이브 재계산한 μ/Σ 로 교체(asset 순서·bucket·ticker 는 portfolio_source 유지).
    # review-only — frozen baseline JSON 미변경.
    cma_source: str = Field(default="portfolio")
    db_window_start: str | None = Field(default=None, description="YYYY-MM-DD (db_window 모드)")
    db_window_end: str | None = Field(default=None, description="YYYY-MM-DD (db_window 모드)")


class FrontierPoint(BaseModel):
    frontier_id: int
    target_return: float | None = None
    equity_weight: float | None = None
    min_volatility: float | None = None
    weights: dict[str, float] | None = None
    expected_return: float | None = None
    volatility: float | None = None
    sharpe: float | None = None
    active_asset_count: int | None = None
    zero_asset_count: int | None = None
    us_hy_weight: float | None = None
    optimizer_status: str


class FrontierNeighborhoodCandidate(BaseModel):
    candidate_id: str
    source_type: str = "frontier_neighborhood"
    frontier_id: int
    target_return: float
    frontier_min_volatility: float
    candidate_return: float
    candidate_volatility: float
    return_gap_bps: float
    vol_gap_bps: float
    vol_gap_bucket: int
    weights: dict[str, float] | None = None
    allocation_distance_l1_from_frontier: float
    allocation_distance_l2_from_frontier: float
    active_asset_count: int
    zero_asset_count: int
    hhi: float
    max_asset_weight: float
    us_hy_weight: float
    largest_weight_differences_vs_frontier: list[dict[str, Any]] = Field(default_factory=list)
    generation_method: str


class RandomCloudCandidate(BaseModel):
    candidate_id: str
    source_type: str = "random_cloud"
    volatility: float
    expected_return: float
    sharpe: float
    hhi: float
    max_asset_weight: float
    weights: dict[str, float] | None = None
    active_asset_count: int
    zero_asset_count: int
    us_hy_weight: float
    equity_weight: float | None = None


class FrontierNeighborhoodResponse(BaseModel):
    """near-frontier feasible portfolio cloud + per-frontier summary."""

    schema_version: str = "frontier_neighborhood.1"
    source_opportunity_set_path: str
    source_opportunity_set_sha256: str
    constraint_set: str = "frontier_relaxed_hy_cap_only"
    included_constraints: list[str] = Field(default_factory=list)
    excluded_constraints: list[str] = Field(default_factory=list)
    asset_keys: list[str] = Field(default_factory=list)
    asset_labels: dict[str, str] | None = None
    asset_buckets: dict[str, str] | None = None
    # per-asset CMA — 패널 표시용 (file/db 공통). db_window 모드면 라이브 window 값.
    asset_expected_returns: dict[str, float] | None = None
    asset_volatilities: dict[str, float] | None = None
    asset_tickers: dict[str, str] | None = None
    # CMA 출처 메타. cma_source="db_window" 일 때 db_window 에 window/per_asset/warnings.
    cma_source: str = "portfolio"
    db_window: dict[str, Any] | None = None
    frontier_points: list[FrontierPoint] = Field(default_factory=list)
    candidates: list[FrontierNeighborhoodCandidate] = Field(default_factory=list)
    random_cloud: list[RandomCloudCandidate] | None = None
    candidate_count: int = 0
    summary: list[dict[str, Any]] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)
    # review-only invariants (강제)
    is_production_selection: bool = False
    dry_run_only: bool = True
    notes: list[str] = Field(
        default_factory=lambda: [
            "frontier_relaxed_hy_cap_only: long-only + sum=1 + target return + US HY<=cap only.",
            "80:20 bucket / equity cap / asset-class band NOT applied — 기존 Dirichlet "
            "explorer cloud(80:20 hard)와 동일 feasible region 아님. 직접 혼합/비교 금지.",
            "review-only: is_production_selection=False, dry_run_only=True.",
        ]
    )
