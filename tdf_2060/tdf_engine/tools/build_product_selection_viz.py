"""Phase E-11B — Product Selection Explainability Visualization CLI.

Inputs (E-11A telemetry):
    out/db_review_relaxed_e62/product_selection_telemetry/<as_of>/
        product_selection_telemetry_{etf,fund}_<as_of>.json

Outputs:
    out/db_review_relaxed_e62/product_selection_visualization/<as_of>/
        product_selection_{etf,fund}_<as_of>.png
        product_selection_visualization_{etf,fund}_<as_of>.json
        product_selection_visualization_summary_<as_of>.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tdf_engine.reporting.product_selection_viz import (
    build_visualization_data,
    render_product_selection,
    render_summary_md,
    write_viz_json,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdf_engine.tools.build_product_selection_viz",
        description="Phase E-11B — product selection visualization PNG + JSON.",
    )
    p.add_argument("--as-of-run", required=True, help="YYYYMMDD")
    p.add_argument(
        "--input-etf-telemetry", required=True, type=Path,
        help="E-11A product_selection_telemetry_etf_*.json",
    )
    p.add_argument(
        "--input-fund-telemetry", required=True, type=Path,
        help="E-11A product_selection_telemetry_fund_*.json",
    )
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--summary-md", required=True, type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    for path in (args.input_etf_telemetry, args.input_fund_telemetry):
        if not path.exists():
            raise SystemExit(f"input not found: {path}")

    etf_payload = build_visualization_data(args.input_etf_telemetry)
    fund_payload = build_visualization_data(args.input_fund_telemetry)

    out_dir = Path(args.output_dir)
    etf_json = write_viz_json(
        etf_payload,
        out_dir / f"product_selection_visualization_etf_{args.as_of_run}.json",
    )
    fund_json = write_viz_json(
        fund_payload,
        out_dir / f"product_selection_visualization_fund_{args.as_of_run}.json",
    )
    etf_png = render_product_selection(
        etf_payload,
        out_dir / f"product_selection_etf_{args.as_of_run}.png",
        label="ETF",
    )
    fund_png = render_product_selection(
        fund_payload,
        out_dir / f"product_selection_fund_{args.as_of_run}.png",
        label="Fund",
    )

    summary_md = Path(args.summary_md)

    def _rel(target: Path, start: Path) -> str:
        try:
            return Path(target).resolve().relative_to(Path(start).resolve()).as_posix()
        except ValueError:
            return Path(target).as_posix()

    render_summary_md(
        as_of_run=args.as_of_run,
        etf_payload=etf_payload,
        fund_payload=fund_payload,
        etf_png_rel=_rel(etf_png, summary_md.parent),
        fund_png_rel=_rel(fund_png, summary_md.parent),
        out_path=summary_md,
    )

    print("[build_product_selection_viz] generated:")
    for p in (etf_json, fund_json, etf_png, fund_png, summary_md):
        print(f"  - {p}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
