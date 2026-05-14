"""R-1F.1 — Manager-Selected SAA CLI (yaml-primary + argv-secondary).

Validates manager selection input and dumps `manager_selected_saa_{type}_{as_of}.json`.
NO downstream wiring (TAA / projection / product selection) — R-1F.2 범위.

Examples
--------
1) YAML input (primary, OD-9 default):

    python -m tdf_engine.tools.select_manager_saa \\
        --selection-yaml scratch/r1f1_manager_selection_etf.yaml \\
        --opportunity-json out/db_review_relaxed_e62/saa_opportunity_set/20260513/saa_opportunity_set_etf_20260513.json \\
        --as-of-run 20260513 \\
        --out-dir out/db_review_relaxed_e62/saa_opportunity_set/20260513

2) argv input (secondary):

    python -m tdf_engine.tools.select_manager_saa \\
        --opportunity-json ... \\
        --portfolio-type etf \\
        --candidate-id cand_008421 \\
        --selected-by r1f1_smoke_test \\
        --selected-at 2026-05-13T10:30:00+09:00 \\
        --selection-reason "R-1F.1 smoke validation sample; not an automated recommendation." \\
        --review-packet-path out/.../saa_opportunity_set_final_manager_review_20260513.md \\
        --review-packet-sha256 <sha256> \\
        --allow-downstream-dry-run \\
        --as-of-run 20260513 \\
        --out-dir out/...
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tdf_engine.optimization.manager_selected_saa import (
    build_manager_selected_saa,
    load_selection_yaml,
    write_manager_selected_saa_json,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdf_engine.tools.select_manager_saa",
        description=(
            "R-1F.1 — Validate manager-selected SAA candidate and dump "
            "manager_selected_saa JSON (NO downstream wiring). "
            "Use --selection-yaml (preferred) or argv flags."
        ),
    )
    p.add_argument("--opportunity-json", required=True, type=Path,
                   help="R-1B.2 opportunity_set JSON path")
    p.add_argument("--as-of-run", required=True, type=str, help="YYYYMMDD")
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--operating-mode", default="relaxed_diagnostic")

    # YAML input (primary)
    p.add_argument(
        "--selection-yaml", type=Path, default=None,
        help="Path to manager selection YAML (preferred). May contain "
             "`manager_selection` (single) or `manager_selection_set` (list).",
    )

    # argv input (secondary, single selection)
    p.add_argument("--portfolio-type", choices=("etf", "fund"), default=None)
    p.add_argument("--candidate-id", type=str, default=None)
    p.add_argument("--selected-by", type=str, default=None)
    p.add_argument("--selected-at", type=str, default=None)
    p.add_argument("--selection-reason", type=str, default=None)
    p.add_argument(
        "--manager-view-note", action="append", default=None,
        help="May be passed multiple times.",
    )
    p.add_argument("--review-packet-path", type=Path, default=None)
    p.add_argument("--review-packet-sha256", type=str, default=None)
    p.add_argument(
        "--allow-downstream-dry-run", action="store_true", default=False,
        help="V-15 gate. Must be set for argv-mode dump.",
    )

    return p


def _selection_from_argv(args: argparse.Namespace) -> dict[str, Any]:
    required = (
        ("portfolio_type", args.portfolio_type),
        ("candidate_id", args.candidate_id),
        ("selected_by", args.selected_by),
        ("selected_at", args.selected_at),
        ("selection_reason", args.selection_reason),
        ("review_packet_path", args.review_packet_path),
        ("review_packet_sha256", args.review_packet_sha256),
    )
    missing = [k for k, v in required if v in (None, "")]
    if missing:
        raise SystemExit(
            f"argv-mode requires all of: {[k for k, _ in required]}; missing {missing}"
        )
    return {
        "portfolio_type": args.portfolio_type,
        "candidate_id": args.candidate_id,
        "selected_by": args.selected_by,
        "selected_at": args.selected_at,
        "selection_reason": args.selection_reason,
        "manager_view_notes": list(args.manager_view_note or []),
        "source_review_packet": {
            "path": str(args.review_packet_path),
            "sha256": args.review_packet_sha256,
        },
        "allow_downstream_dry_run": bool(args.allow_downstream_dry_run),
    }


def _iter_selections(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.selection_yaml is not None:
        loaded = load_selection_yaml(args.selection_yaml)
        if "manager_selection_set" in loaded:
            return list(loaded["manager_selection_set"])
        return [loaded["manager_selection"]]
    # argv mode
    return [_selection_from_argv(args)]


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.opportunity_json.exists():
        raise SystemExit(f"opportunity JSON not found: {args.opportunity_json}")
    payload = json.loads(args.opportunity_json.read_text(encoding="utf-8"))

    out_dir = Path(args.out_dir)
    written: list[Path] = []
    for sel in _iter_selections(args):
        ptype = str(sel.get("portfolio_type") or "")
        dump = build_manager_selected_saa(
            sel, payload, args.opportunity_json,
            operating_mode=args.operating_mode,
        )
        out_path = out_dir / f"manager_selected_saa_{ptype}_{args.as_of_run}.json"
        written.append(write_manager_selected_saa_json(dump, out_path))

    print("[select_manager_saa] generated:")
    for p in written:
        print(f"  - {p}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
