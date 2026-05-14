"""CLI: lasso/polygon selection export.

Input:
  --opportunity-set    PATH   : R-1B.2 opportunity set JSON (10,000 후보)
  --input-config       PATH   : selection config JSON (polygon / overlays / filters / rule)
  --output-dir         PATH   : directory to write export JSON + yaml
  --portfolio-type     etf|fund : default 'etf' (SAA is identical between types)
  --selected-by        STR    : 운용역 식별자 (forbidden substrings: automated/smoke)
  --selection-reason   STR    : 자유 텍스트
  --batch-results-dir  PATH   : optional R-1G.2 batch root for has_fallback/universe (e.g., out/db_etf_relaxed_e62_r1i_multi_candidate)
  --source-review-packet-path STR : for R-1F.1 yaml provenance (optional)
  --source-review-packet-sha256 STR : for R-1F.1 yaml provenance (optional)

Output:
  <output-dir>/lasso_selection_<selection_id>.json
  <output-dir>/manager_selection_from_lasso_<selection_id>.yaml

Defaults: dry-run only. No production flag.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from tdf_engine.optimization.lasso_selection import (
    build_export,
    compute_cloud_tags,
    sha256_file,
    to_r1f1_yaml,
)


def _load_batch_signals(batch_dir: pathlib.Path | None) -> dict[str, dict]:
    """Read R-1G.2 batch results to extract has_fallback / has_universe_warning per candidate.

    Expects layout: <batch_dir>/<cand_id>/portfolio_<type>_*.json (R-1G.2 schema).
    """
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
                from tdf_engine.optimization.lasso_selection import DEFAULT_CORE_SATELLITE, ASSETS
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
        description="R-track 2 lasso/polygon candidate selection export "
                    "(rule-based EXPORT, NOT automated recommendation)."
    )
    p.add_argument("--opportunity-set", required=True, type=pathlib.Path)
    p.add_argument("--input-config", required=True, type=pathlib.Path)
    p.add_argument("--output-dir", required=True, type=pathlib.Path)
    p.add_argument("--portfolio-type", choices=["etf", "fund"], default="etf")
    p.add_argument("--selected-by", required=True)
    p.add_argument("--selection-reason", required=True)
    p.add_argument("--batch-results-dir", type=pathlib.Path, default=None)
    p.add_argument("--source-review-packet-path", default="")
    p.add_argument("--source-review-packet-sha256", default="")
    p.add_argument("--skip-yaml", action="store_true",
                   help="skip R-1F.1 yaml emission (use when post_selection_rule yields >1 candidate)")
    args = p.parse_args(argv)

    opp_path: pathlib.Path = args.opportunity_set
    if not opp_path.exists():
        print(f"ERR: opportunity set not found: {opp_path}", file=sys.stderr)
        return 2
    cfg_path: pathlib.Path = args.input_config
    if not cfg_path.exists():
        print(f"ERR: input config not found: {cfg_path}", file=sys.stderr)
        return 2
    out_dir: pathlib.Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    opp = json.loads(opp_path.read_text(encoding="utf-8"))
    cands = opp["candidates"]

    batch_signals = _load_batch_signals(args.batch_results_dir)
    tagged = compute_cloud_tags(cands, batch_signals=batch_signals or None)

    opp_sha = sha256_file(opp_path)

    export = build_export(
        candidates_with_tags=tagged,
        opportunity_set_path=str(opp_path),
        opportunity_set_sha256=opp_sha,
        polygon_points=cfg.get("polygon_points", []),
        x_metric=cfg.get("x_metric", "volatility"),
        y_metric=cfg.get("y_metric", "expected_return"),
        active_overlays=cfg.get("active_overlays", []),
        active_filters=cfg.get("active_filters", {}),
        selection_mode=cfg.get("selection_mode", "lasso"),
        post_selection_rule=cfg.get("post_selection_rule", "all"),
        post_selection_params=cfg.get("post_selection_params", {}),
        selected_by=args.selected_by,
        selection_reason=args.selection_reason,
    )

    sel_id = export["selection_id"]
    json_path = out_dir / f"lasso_selection_{sel_id}.json"
    json_path.write_text(
        json.dumps(export, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {json_path}")
    print(f"  selection_mode      = {export['selection_mode']}")
    print(f"  post_selection_rule = {export['post_selection_rule']}")
    print(f"  selected_before_rule= {export['selected_count_before_rule']}")
    print(f"  selected_count      = {export['selected_count']}")
    print(f"  warning_labels      = {export['warning_labels']}")

    if not args.skip_yaml:
        if export["selected_count"] == 1:
            yaml_text = to_r1f1_yaml(
                export,
                portfolio_type=args.portfolio_type,
                source_review_packet_path=args.source_review_packet_path,
                source_review_packet_sha256=args.source_review_packet_sha256,
            )
            yaml_path = out_dir / f"manager_selection_from_lasso_{sel_id}.yaml"
            yaml_path.write_text(yaml_text, encoding="utf-8")
            print(f"wrote {yaml_path}")
        else:
            print(
                f"  NOTE: selected_count={export['selected_count']} != 1 — "
                f"skipping R-1F.1 yaml (use --skip-yaml or change post_selection_rule)"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
