"""Phase E-9 — SAA Frontier CLI.

ETF + Fund portfolio_*.json → frontier JSON 2건 + SAA MVO PNG 2건 + summary md.
read-only diagnostic.

Example:
    python -m tdf_engine.tools.build_saa_frontier \\
        --as-of-run 20260511 \\
        --input-etf  out/db_etf_relaxed_e62/portfolio_etf_20260511.json \\
        --input-fund out/db_fund_relaxed_e62/portfolio_fund_20260511.json \\
        --output-dir out/db_review_relaxed_e62/saa_frontier/20260511 \\
        --summary-md out/db_review_relaxed_e62/saa_frontier/20260511/saa_frontier_summary_20260511.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tdf_engine.reporting.saa_frontier import (
    DEFAULT_GRID_POINTS,
    build_frontier_data,
    render_saa_frontier_summary_md,
    render_saa_mvo,
    write_frontier_json,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdf_engine.tools.build_saa_frontier",
        description="Phase E-9 — SAA MVO frontier diagnostic.",
    )
    p.add_argument("--as-of-run", required=True, help="YYYYMMDD")
    p.add_argument("--input-etf", required=True, type=Path)
    p.add_argument("--input-fund", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--summary-md", required=True, type=Path)
    p.add_argument(
        "--grid-points", type=int, default=DEFAULT_GRID_POINTS,
        help=f"frontier target-return grid size (default {DEFAULT_GRID_POINTS})",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    for path in (args.input_etf, args.input_fund):
        if not path.exists():
            raise SystemExit(f"input not found: {path}")

    etf = json.loads(args.input_etf.read_text(encoding="utf-8"))
    fund = json.loads(args.input_fund.read_text(encoding="utf-8"))

    etf_payload = build_frontier_data(etf, grid_points=args.grid_points)
    fund_payload = build_frontier_data(fund, grid_points=args.grid_points)

    out_dir = Path(args.output_dir)
    etf_json = write_frontier_json(
        etf_payload, out_dir / f"saa_frontier_etf_{args.as_of_run}.json"
    )
    fund_json = write_frontier_json(
        fund_payload, out_dir / f"saa_frontier_fund_{args.as_of_run}.json"
    )
    etf_png = render_saa_mvo(
        etf_payload, out_dir / f"saa_mvo_etf_{args.as_of_run}.png", label="ETF"
    )
    fund_png = render_saa_mvo(
        fund_payload, out_dir / f"saa_mvo_fund_{args.as_of_run}.png", label="Fund"
    )

    summary_md = Path(args.summary_md)

    def _rel(target: Path, start: Path) -> str:
        try:
            return Path(target).resolve().relative_to(Path(start).resolve()).as_posix()
        except ValueError:
            return Path(target).as_posix()

    render_saa_frontier_summary_md(
        as_of_run=args.as_of_run,
        etf_payload=etf_payload,
        fund_payload=fund_payload,
        etf_png_rel=_rel(etf_png, summary_md.parent),
        fund_png_rel=_rel(fund_png, summary_md.parent),
        out_path=summary_md,
    )

    print("[build_saa_frontier] generated:")
    for p in (etf_json, fund_json, etf_png, fund_png, summary_md):
        print(f"  - {p}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
