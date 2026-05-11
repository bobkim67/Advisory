"""Phase E-11A — Product Selection Score Telemetry CLI.

ETF + Fund portfolio_*.json (E-11A patched) → telemetry JSON 2 + summary md.
read-only.

Example:
    python -m tdf_engine.tools.build_product_selection_telemetry \\
        --as-of-run 20260511 \\
        --input-etf  out/db_etf_relaxed_e62_e11a/portfolio_etf_20260511.json \\
        --input-fund out/db_fund_relaxed_e62_e11a/portfolio_fund_20260511.json \\
        --output-dir out/db_review_relaxed_e62/product_selection_telemetry/20260511 \\
        --summary-md out/db_review_relaxed_e62/product_selection_telemetry/20260511/product_selection_telemetry_summary_20260511.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tdf_engine.reporting.product_selection_telemetry import (
    build_product_selection_telemetry,
    render_summary_md,
    write_telemetry_json,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdf_engine.tools.build_product_selection_telemetry",
        description="Phase E-11A — read-only product selection score telemetry.",
    )
    p.add_argument("--as-of-run", required=True, help="YYYYMMDD")
    p.add_argument("--input-etf", required=True, type=Path)
    p.add_argument("--input-fund", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--summary-md", required=True, type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    for path in (args.input_etf, args.input_fund):
        if not path.exists():
            raise SystemExit(f"input not found: {path}")

    etf_payload = build_product_selection_telemetry(args.input_etf)
    fund_payload = build_product_selection_telemetry(args.input_fund)

    out_dir = Path(args.output_dir)
    etf_json = write_telemetry_json(
        etf_payload,
        out_dir / f"product_selection_telemetry_etf_{args.as_of_run}.json",
    )
    fund_json = write_telemetry_json(
        fund_payload,
        out_dir / f"product_selection_telemetry_fund_{args.as_of_run}.json",
    )
    summary_md = render_summary_md(
        as_of_run=args.as_of_run,
        etf_payload=etf_payload,
        fund_payload=fund_payload,
        out_path=Path(args.summary_md),
    )

    print("[build_product_selection_telemetry] generated:")
    for p in (etf_json, fund_json, summary_md):
        print(f"  - {p}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
