"""POST /api/r-track/lasso/export — review-only chain wrapper.

Internally runs C-2 ``build_export`` → C-4 ``extract_archetypes`` →
``build_review_export`` against the supplied opportunity set JSON. Optional
``output_dir`` for scratch persistence; out tracked / engine / tests / docs /
config paths are explicitly rejected. R-1F.* / R-1G.* downstream CLIs are
NEVER auto-triggered from this endpoint.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any

from fastapi import APIRouter, HTTPException

from tdf_engine.optimization.lasso_review import (
    LassoReviewError,
    build_review_export,
    dedup_archetypes,
    extract_archetypes,
)
from tdf_engine.optimization.lasso_selection import (
    ASSETS,
    DEFAULT_CORE_SATELLITE,
    PolygonError,
    SelectionConfigError,
    build_export,
    compute_cloud_tags,
    sha256_file,
    to_r1f1_yaml,
)

from .schemas import LassoExportRequest, LassoExportResponse, PermanentInvariants

router = APIRouter(prefix="/api/r-track", tags=["r-track"])

# Forbidden output_dir roots — relative to tdf_2060/ (engine root).
ENGINE_ROOT = pathlib.Path(__file__).resolve().parents[1]
FORBIDDEN_WRITE_ROOTS: tuple[str, ...] = ("out", "tdf_engine", "tests", "docs", "config")


def _resolve_under_engine(p: str | pathlib.Path) -> pathlib.Path:
    """Resolve to an absolute path; relative paths are resolved against engine root."""
    pp = pathlib.Path(p)
    if not pp.is_absolute():
        pp = ENGINE_ROOT / pp
    return pp.resolve()


def _validate_output_dir(out_dir_str: str) -> pathlib.Path:
    p = _resolve_under_engine(out_dir_str)
    for forb in FORBIDDEN_WRITE_ROOTS:
        forb_abs = (ENGINE_ROOT / forb).resolve()
        try:
            p.relative_to(forb_abs)
        except ValueError:
            continue
        raise HTTPException(
            status_code=400,
            detail=f"output_dir is forbidden: must not be under '{forb}/'",
        )
    return p


def _load_batch_signals(batch_dir_str: str) -> dict[str, dict[str, Any]]:
    batch_dir = _resolve_under_engine(batch_dir_str)
    if not batch_dir.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for cand_dir in sorted(batch_dir.iterdir()):
        if not cand_dir.is_dir():
            continue
        cid = cand_dir.name
        for jpath in cand_dir.glob("portfolio_*.json"):
            try:
                d = json.loads(jpath.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if d.get("meta", {}).get("scope", "").startswith("R-1G.2"):
                fb = d["diagnostics"]["portfolio_builder"]["fallback"]
                sc_by = d.get("selected_count_by_asset", {})
                warn_assets = [a for a in ASSETS if sc_by.get(a, 0) < DEFAULT_CORE_SATELLITE]
                out[cid] = {
                    "has_fallback": bool(fb.get("fallback_used", False)),
                    "has_universe_warning": bool(warn_assets),
                    "universe_warn_assets": ",".join(warn_assets),
                }
                break
    return out


@router.post("/lasso/export", response_model=LassoExportResponse)
def lasso_export(req: LassoExportRequest) -> LassoExportResponse:
    src = _resolve_under_engine(req.source_opportunity_set_path)
    if not src.exists():
        raise HTTPException(status_code=404, detail=f"opportunity set not found: {src}")
    if not src.is_file():
        raise HTTPException(status_code=400, detail=f"source_opportunity_set_path is not a file: {src}")

    out_dir: pathlib.Path | None = None
    if req.output_dir:
        out_dir = _validate_output_dir(req.output_dir)

    try:
        opp = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"invalid JSON in opportunity set: {e}")
    cands = opp.get("candidates", [])
    if not isinstance(cands, list) or not cands:
        raise HTTPException(status_code=400, detail="opportunity set has no candidates")

    batch_signals: dict[str, Any] = {}
    if req.batch_results_dir:
        batch_signals = _load_batch_signals(req.batch_results_dir)

    tagged = compute_cloud_tags(cands, batch_signals=batch_signals or None)
    opp_sha = sha256_file(src)

    try:
        export = build_export(
            candidates_with_tags=tagged,
            opportunity_set_path=str(src.relative_to(ENGINE_ROOT)) if src.is_relative_to(ENGINE_ROOT) else str(src),
            opportunity_set_sha256=opp_sha,
            polygon_points=req.polygon_points,
            x_metric=req.x_metric,
            y_metric=req.y_metric,
            active_overlays=req.active_overlays,
            active_filters=req.active_filters,
            selection_mode=req.selection_mode,
            post_selection_rule=req.post_selection_rule,
            post_selection_params=req.post_selection_params,
            selected_by=req.selected_by,
            selection_reason=req.selection_reason,
        )
    except PolygonError as e:
        raise HTTPException(status_code=400, detail=f"polygon validation failed: {e}")
    except SelectionConfigError as e:
        raise HTTPException(status_code=400, detail=f"selection config error: {e}")

    selected_ids = list(export["selected_candidate_ids"])
    by_id = {c["candidate_id"]: c for c in tagged}
    selected = [by_id[cid] for cid in selected_ids if cid in by_id]

    review: dict[str, Any] = {}
    null_arches: list[str] = []
    if selected:
        try:
            archetypes = extract_archetypes(selected)
        except LassoReviewError:
            archetypes = []
        if archetypes:
            dedup = dedup_archetypes(archetypes)
            review = build_review_export(
                lasso_export=export,
                candidates=selected,
                archetypes=archetypes,
                dedup=dedup,
            )
            null_arches = [a["archetype"] for a in archetypes if a.get("candidate_id") is None]

    yaml_preview: str | None = None
    if req.emit_yaml_preview and export["selected_count"] == 1:
        # E-2: client-supplied review packet (both path+sha required together).
        rp_supplied = (
            req.source_review_packet_path is not None
            or req.source_review_packet_sha256 is not None
        )
        if rp_supplied:
            if not req.source_review_packet_path or not req.source_review_packet_sha256:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "source_review_packet_path and source_review_packet_sha256 "
                        "must be provided together (or both omitted)"
                    ),
                )
            sha = req.source_review_packet_sha256.strip().lower()
            if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "source_review_packet_sha256 must be a 64-char "
                        "lowercase hex string"
                    ),
                )
            rp_path = req.source_review_packet_path
            rp_sha = sha
        else:
            # Fallback (C-3a default): lasso JSON self-referential placeholder.
            rp_path = (
                str(src.relative_to(ENGINE_ROOT))
                if src.is_relative_to(ENGINE_ROOT)
                else str(src)
            )
            rp_sha = opp_sha
        try:
            yaml_preview = to_r1f1_yaml(
                export,
                portfolio_type=req.portfolio_type,
                source_review_packet_path=rp_path,
                source_review_packet_sha256=rp_sha,
            )
        except SelectionConfigError as e:
            yaml_preview = f"# yaml preview skipped: {e}"

    # Optional scratch persistence
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        sel_id = export["selection_id"]
        (out_dir / f"lasso_selection_{sel_id}.json").write_text(
            json.dumps(export, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if review:
            (out_dir / "representative_candidates.json").write_text(
                json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )

    return LassoExportResponse(
        lasso_selection_export=export,
        representative_review=review,
        selected_count=int(export["selected_count"]),
        warning_labels=list(export["warning_labels"]),
        null_archetypes=null_arches,
        permanent_invariants=PermanentInvariants(),
        manager_selection_yaml_preview=yaml_preview,
    )
