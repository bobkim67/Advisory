"""R-1B-lite — SAA Opportunity Set CLI.

ETF + Fund portfolio_*.json → opportunity set JSON 2건 + summary md.
read-only diagnostic. production allocation / TAA / product selection 미변경.

Example:
    python -m tdf_engine.tools.build_saa_opportunity_set \\
        --as-of-run 20260513 \\
        --input-etf  out/db_etf_relaxed_e62/portfolio_etf_20260511.json \\
        --input-fund out/db_fund_relaxed_e62/portfolio_fund_20260511.json \\
        --output-dir out/db_review_relaxed_e62/saa_opportunity_set/20260513 \\
        --summary-md out/db_review_relaxed_e62/saa_opportunity_set/20260513/saa_opportunity_set_summary_20260513.md \\
        --n 10000 --seed 42
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tdf_engine.optimization.opportunity_set import (
    DEFAULT_N_CANDIDATES,
    DEFAULT_SEED,
    FRONTIER_GRID_POINTS,
    build_opportunity_set,
    render_opportunity_set_summary_md,
    write_opportunity_set_json,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdf_engine.tools.build_saa_opportunity_set",
        description=(
            "R-1B-lite — SAA Opportunity Set diagnostic generator. "
            "Dirichlet candidates + 2 reference points (ref_max_sharpe, ref_80_20). "
            "Read-only; production allocation 미변경."
        ),
    )
    p.add_argument("--as-of-run", required=True, help="YYYYMMDD")
    p.add_argument("--input-etf", required=True, type=Path)
    p.add_argument("--input-fund", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--summary-md", required=True, type=Path)
    p.add_argument(
        "--n", type=int, default=DEFAULT_N_CANDIDATES,
        help=f"candidate count (default {DEFAULT_N_CANDIDATES})",
    )
    p.add_argument(
        "--seed", type=int, default=DEFAULT_SEED,
        help=f"deterministic seed (default {DEFAULT_SEED})",
    )
    p.add_argument(
        "--frontier-grid-points", type=int, default=FRONTIER_GRID_POINTS,
        help=(
            f"frontier sample grid points for mvo_efficiency_score "
            f"(default {FRONTIER_GRID_POINTS})"
        ),
    )
    return p


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"input not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    etf = _read_json(args.input_etf)
    fund = _read_json(args.input_fund)

    etf_payload = build_opportunity_set(
        etf,
        n_candidates=args.n,
        random_seed=args.seed,
        frontier_grid_points=args.frontier_grid_points,
    )
    fund_payload = build_opportunity_set(
        fund,
        n_candidates=args.n,
        random_seed=args.seed,
        frontier_grid_points=args.frontier_grid_points,
    )

    out_dir = Path(args.output_dir)
    etf_json = write_opportunity_set_json(
        etf_payload, out_dir / f"saa_opportunity_set_etf_{args.as_of_run}.json"
    )
    fund_json = write_opportunity_set_json(
        fund_payload, out_dir / f"saa_opportunity_set_fund_{args.as_of_run}.json"
    )

    summary_md = render_opportunity_set_summary_md(
        as_of_run=args.as_of_run,
        etf_payload=etf_payload,
        fund_payload=fund_payload,
        out_path=Path(args.summary_md),
    )

    print("[build_saa_opportunity_set] generated:")
    for p in (etf_json, fund_json, summary_md):
        print(f"  - {p}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
