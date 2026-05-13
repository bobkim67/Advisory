"""R-1D — SAA Opportunity Set similar_search CLI.

Three modes:
  --mode coordinate              (require --target-return, --target-volatility)
  --mode candidate               (require --candidate-id)
  --mode shortlist-neighborhood  (batch over R-1C.1 fixed shortlist ids)

Read-only. Opportunity_set JSON / production / config / E-series 산출물 미변경.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tdf_engine.optimization.opportunity_set_search import (
    SHORTLIST_CANDIDATE_IDS,
    build_shortlist_neighborhood,
    find_similar_by_risk_return,
    find_similar_by_weights,
    render_search_result_md,
    render_shortlist_neighborhood_md,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdf_engine.tools.search_saa_opportunity_set",
        description=(
            "R-1D — SAA opportunity set similar_search "
            "(coordinate / candidate / shortlist-neighborhood). "
            "Read-only; production allocation unchanged."
        ),
    )
    p.add_argument("--opportunity-json", required=True, type=Path)
    p.add_argument(
        "--mode", required=True,
        choices=("coordinate", "candidate", "shortlist-neighborhood"),
    )
    p.add_argument("--out-md", required=True, type=Path)
    p.add_argument("--k", type=int, default=20)
    p.add_argument("--target-return", type=float, default=None)
    p.add_argument("--target-volatility", type=float, default=None)
    p.add_argument("--candidate-id", type=str, default=None)
    p.add_argument(
        "--feasible-only", action="store_true", default=True,
        help="Exclude degenerate (default True). Use --include-degenerate to disable.",
    )
    p.add_argument("--include-degenerate", action="store_true", default=False)
    p.add_argument(
        "--include-ref-80-20", action="store_true", default=False,
        help="Include ref_80_20_equal_intra_bucket in search pool (default off).",
    )
    p.add_argument(
        "--include-sampled-only-off", action="store_true", default=False,
        help="If set, include references (still excludes ref_max_sharpe).",
    )
    return p


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"input not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = _read_json(args.opportunity_json)
    feasible_only = (not args.include_degenerate)
    sampled_only = (not args.include_sampled_only_off)

    if args.mode == "coordinate":
        if args.target_return is None or args.target_volatility is None:
            raise SystemExit(
                "--mode coordinate requires --target-return and --target-volatility"
            )
        result = find_similar_by_risk_return(
            payload,
            target_return=args.target_return,
            target_volatility=args.target_volatility,
            k=args.k,
            feasible_only=feasible_only,
            sampled_only=sampled_only,
            include_ref_80_20=args.include_ref_80_20,
        )
        render_search_result_md(result, args.out_md)

    elif args.mode == "candidate":
        if not args.candidate_id:
            raise SystemExit("--mode candidate requires --candidate-id")
        result = find_similar_by_weights(
            payload,
            target_candidate_id=args.candidate_id,
            k=args.k,
            feasible_only=feasible_only,
            sampled_only=sampled_only,
            include_ref_80_20=args.include_ref_80_20,
        )
        render_search_result_md(result, args.out_md)

    else:  # shortlist-neighborhood
        # k for neighborhood defaults to 5
        k_neighbors = args.k if args.k != 20 else 5
        result = build_shortlist_neighborhood(
            payload,
            shortlist_ids=SHORTLIST_CANDIDATE_IDS,
            k=k_neighbors,
            feasible_only=feasible_only,
            sampled_only=sampled_only,
        )
        render_shortlist_neighborhood_md(result, payload, args.out_md)

    print(f"[search_saa_opportunity_set] mode={args.mode} → {args.out_md}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
