"""Phase E-7 — Explainability JSON CLI.

ETF + Fund portfolio_*.json + taa_policy.yaml → 5 블록 explainability JSON 2건 +
summary md 1건 생성. read-only.

Example:
    python -m tdf_engine.tools.build_explainability \\
        --as-of-run 20260511 \\
        --input-etf  out/db_etf_relaxed_e62/portfolio_etf_20260511.json \\
        --input-fund out/db_fund_relaxed_e62/portfolio_fund_20260511.json \\
        --taa-policy tdf_engine/config/taa_policy.yaml \\
        --etf-list   ../etf_list \\
        --fund-list  ../fund_list \\
        --output-dir out/db_review_relaxed_e62/explainability/20260511 \\
        --summary-md out/db_review_relaxed_e62/explainability_summary_20260511.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tdf_engine.reporting.explainability import (
    build_explainability,
    render_explainability_summary_md,
    write_explainability_json,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdf_engine.tools.build_explainability",
        description="Phase E-7 — read-only explainability JSON dump.",
    )
    p.add_argument("--as-of-run", required=True, help="YYYYMMDD")
    p.add_argument("--input-etf", required=True, type=Path)
    p.add_argument("--input-fund", required=True, type=Path)
    p.add_argument(
        "--taa-policy",
        required=True,
        type=Path,
        help="tdf_engine/config/taa_policy.yaml",
    )
    p.add_argument(
        "--etf-list",
        type=Path,
        default=None,
        help="원본 etf_list (TSV) — product metadata lookup. 미지정 시 lookup 건너뜀.",
    )
    p.add_argument(
        "--fund-list",
        type=Path,
        default=None,
        help="원본 fund_list (TSV) — product metadata lookup.",
    )
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--summary-md", required=True, type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    for path in (args.input_etf, args.input_fund, args.taa_policy):
        if not path.exists():
            raise SystemExit(f"input not found: {path}")

    etf_payload = build_explainability(
        args.input_etf,
        taa_policy_yaml=args.taa_policy,
        product_list=args.etf_list,
    )
    fund_payload = build_explainability(
        args.input_fund,
        taa_policy_yaml=args.taa_policy,
        product_list=args.fund_list,
    )

    out_dir = Path(args.output_dir)
    etf_path = write_explainability_json(
        etf_payload, out_dir / f"explainability_etf_{args.as_of_run}.json"
    )
    fund_path = write_explainability_json(
        fund_payload, out_dir / f"explainability_fund_{args.as_of_run}.json"
    )
    summary = render_explainability_summary_md(
        as_of_run=args.as_of_run,
        etf_payload=etf_payload,
        fund_payload=fund_payload,
        out_path=Path(args.summary_md),
    )

    print("[build_explainability] generated:")
    print(f"  - {etf_path}")
    print(f"  - {fund_path}")
    print(f"  - {summary}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
