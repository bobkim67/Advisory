"""GET /api/r-track/opportunity-set/scatter — frontend scatter dataset.

Projects the R-1B.2 opportunity set + cloud tags to a small per-candidate
dict (no weights, no full tag dump) so the React scatter and the
representative-marker overlay share a single coordinate source. Review-only
endpoint; permanent invariants forced.
"""
from __future__ import annotations

import json
import pathlib

from fastapi import APIRouter, HTTPException

from tdf_engine.optimization.lasso_selection import compute_cloud_tags, sha256_file

from .lasso import ENGINE_ROOT, _load_batch_signals, _resolve_under_engine
from .schemas import ScatterCandidate, ScatterDatasetResponse

router = APIRouter(prefix="/api/r-track", tags=["r-track"])


@router.get("/opportunity-set/scatter", response_model=ScatterDatasetResponse)
def opportunity_set_scatter(
    source_opportunity_set_path: str,
    batch_results_dir: str | None = None,
) -> ScatterDatasetResponse:
    src = _resolve_under_engine(source_opportunity_set_path)
    if not src.exists():
        raise HTTPException(status_code=404, detail=f"opportunity set not found: {src}")
    if not src.is_file():
        raise HTTPException(status_code=400, detail=f"source_opportunity_set_path is not a file: {src}")

    try:
        opp = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"invalid JSON in opportunity set: {e}")

    cands = opp.get("candidates", [])
    if not isinstance(cands, list) or not cands:
        raise HTTPException(status_code=400, detail="opportunity set has no candidates")

    batch_signals = _load_batch_signals(batch_results_dir) if batch_results_dir else {}
    tagged = compute_cloud_tags(cands, batch_signals=batch_signals or None)

    projected = [
        ScatterCandidate(
            candidate_id=c["candidate_id"],
            volatility=float(c["volatility"]),
            expected_return=float(c["expected_return"]),
            sharpe=float(c["sharpe"]),
            concentration_hhi=float(c["concentration_hhi"]),
            max_asset_weight=float(c["max_asset_weight"]),
            mvo_efficiency_score=float(c["mvo_efficiency_score"]),
            feasibility_status=str(c.get("feasibility_status", "unknown")),
            overlap_score=int(c["overlap_score"]),
            cloud_labels=str(c.get("cloud_labels", "")),
            has_fallback=(None if c.get("has_fallback") is None else bool(c["has_fallback"])),
            has_universe_warning=(
                None if c.get("has_universe_warning") is None else bool(c["has_universe_warning"])
            ),
        )
        for c in tagged
    ]

    return ScatterDatasetResponse(
        source_opportunity_set_path=str(src.relative_to(ENGINE_ROOT))
        if src.is_relative_to(ENGINE_ROOT)
        else str(src),
        source_opportunity_set_sha256=sha256_file(src),
        candidate_count=len(projected),
        candidates=projected,
    )
