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
