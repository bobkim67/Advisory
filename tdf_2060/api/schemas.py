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
