"""CLI: post-lasso representative review (archetype extraction).

Reads a lasso selection export + opportunity set JSON, optionally a R-1G.2
batch results directory, and writes:
  - representative_candidates.json   (schema r_track_2_review.1)
  - lasso_review_table.csv           (per-archetype row)
  - lasso_review_summary.md          (human-readable summary)

Required args:
  --lasso-selection-json    PATH
  --opportunity-set-json    PATH
  --output-dir              PATH

Optional:
  --batch-results-dir       PATH   (R-1G.2 batch root for fallback / universe signals)

Permanent: is_production_selection=False, dry_run_only=True. NOT a
recommendation; archetypes are review-only categories.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from tdf_engine.optimization.lasso_review import (
    LassoReviewError,
    build_review_csv,
    build_review_export,
    build_review_md,
    dedup_archetypes,
    extract_archetypes,
    load_lasso_selection,
    resolve_selected_candidates,
)
from tdf_engine.optimization.lasso_selection import ASSETS, DEFAULT_CORE_SATELLITE


def _load_batch_signals(batch_dir: pathlib.Path | None) -> dict[str, dict]:
    """Re-implementation of export_lasso_selection's batch loader (kept local to
    avoid coupling to the CLI module)."""
    if batch_dir is None or not batch_dir.exists():
        return {}
    out: dict[str, dict] = {}
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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="C-4 post-lasso representative review (review-only archetype extraction, "
                    "NOT a recommendation)."
    )
    p.add_argument("--lasso-selection-json", required=True, type=pathlib.Path)
    p.add_argument("--opportunity-set-json", required=True, type=pathlib.Path)
    p.add_argument("--output-dir", required=True, type=pathlib.Path)
    p.add_argument("--batch-results-dir", type=pathlib.Path, default=None)
    args = p.parse_args(argv)

    lasso = load_lasso_selection(args.lasso_selection_json)
    if not args.opportunity_set_json.exists():
        print(f"ERR: opportunity set not found: {args.opportunity_set_json}", file=sys.stderr)
        return 2
    opp = json.loads(args.opportunity_set_json.read_text(encoding="utf-8"))
    batch = _load_batch_signals(args.batch_results_dir)

    try:
        candidates = resolve_selected_candidates(lasso, opp, batch_signals=batch or None)
        archetypes = extract_archetypes(candidates)
    except LassoReviewError as e:
        print(f"ERR: {e}", file=sys.stderr)
        return 3

    dedup = dedup_archetypes(archetypes)
    review = build_review_export(
        lasso_export=lasso,
        candidates=candidates,
        archetypes=archetypes,
        dedup=dedup,
    )
    review["source_lasso_selection_file"] = str(args.lasso_selection_json).replace("\\", "/")

    out_dir: pathlib.Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "representative_candidates.json"
    json_path.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    csv_path = out_dir / "lasso_review_table.csv"
    csv_path.write_text(build_review_csv(candidates, archetypes), encoding="utf-8")
    md_path = out_dir / "lasso_review_summary.md"
    md_path.write_text(build_review_md(review, candidates), encoding="utf-8")

    print(f"wrote {json_path}")
    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")
    print(f"  selected_count   = {review['selected_count']}")
    print(f"  single_review    = {review['single_review_mode']}")
    print(f"  unique reps      = {len(review['representatives'])}")
    null_arches = [a['archetype'] for a in review['archetypes'] if a.get('candidate_id') is None]
    if null_arches:
        print(f"  null archetypes  = {null_arches}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
