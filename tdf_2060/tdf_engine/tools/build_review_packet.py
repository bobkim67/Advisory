"""Phase E-12 — Integrated Review Packet CLI.

E-8/E-9/E-10/E-11B/portfolio JSON → markdown + html packet.

Example (single product):
    python -m tdf_engine.tools.build_review_packet \\
        --as-of-run 20260511 \\
        --product-type etf \\
        --review-root out/db_review_relaxed_e62 \\
        --portfolio-json out/db_etf_relaxed_e62_e11a/portfolio_etf_20260511.json \\
        --output-dir out/db_review_relaxed_e62/review_packet/20260511 \\
        --format both

Example (both):
    python -m tdf_engine.tools.build_review_packet \\
        --as-of-run 20260511 \\
        --product-type both \\
        --review-root out/db_review_relaxed_e62 \\
        --portfolio-json out/db_etf_relaxed_e62_e11a/portfolio_etf_20260511.json \\
        --portfolio-json-fund out/db_fund_relaxed_e62_e11a/portfolio_fund_20260511.json \\
        --output-dir out/db_review_relaxed_e62/review_packet/20260511 \\
        --format both
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tdf_engine.reporting.review_packet import (
    build_review_packet,
    build_review_packet_both,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdf_engine.tools.build_review_packet",
        description="Phase E-12 — integrated review packet (md + html).",
    )
    p.add_argument("--as-of-run", required=True, help="YYYYMMDD")
    p.add_argument(
        "--product-type", required=True, choices=("etf", "fund", "both"),
    )
    p.add_argument(
        "--review-root", required=True, type=Path,
        help="out/db_review_relaxed_e62 (E-7~E-11B artifact root)",
    )
    p.add_argument(
        "--portfolio-json", type=Path, default=None,
        help="ETF portfolio JSON (etf 또는 both 시 필수)",
    )
    p.add_argument(
        "--portfolio-json-fund", type=Path, default=None,
        help="Fund portfolio JSON (fund 또는 both 시 필수)",
    )
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument(
        "--format", default="both", choices=("md", "html", "both"),
    )
    p.add_argument(
        "--include-appendix", action="store_true",
        help="MVP-X / E-6 legacy 9 PNG 을 appendix 로 포함 (deprecated 라벨).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.product_type in ("etf", "both") and args.portfolio_json is None:
        raise SystemExit("--portfolio-json (ETF) is required for product-type etf or both")
    if args.product_type in ("fund", "both") and args.portfolio_json_fund is None:
        # fund 단독 시 portfolio_json (deprecated reuse) 또는 portfolio_json_fund 필수
        if args.product_type == "fund" and args.portfolio_json is not None:
            args.portfolio_json_fund = args.portfolio_json
        else:
            raise SystemExit(
                "--portfolio-json-fund is required for product-type fund or both"
            )

    written_paths: list[Path] = []

    if args.product_type in ("etf", "fund"):
        portfolio_path = (
            args.portfolio_json if args.product_type == "etf" else args.portfolio_json_fund
        )
        result = build_review_packet(
            review_root=args.review_root,
            as_of_run=args.as_of_run,
            product_type=args.product_type,
            portfolio_json=portfolio_path,
            output_dir=args.output_dir,
            fmt=args.format,
            include_appendix=args.include_appendix,
        )
        for k in ("md_path", "html_path"):
            if result.get(k):
                written_paths.append(result[k])
    else:
        result = build_review_packet_both(
            review_root=args.review_root,
            as_of_run=args.as_of_run,
            portfolio_json_etf=args.portfolio_json,
            portfolio_json_fund=args.portfolio_json_fund,
            output_dir=args.output_dir,
            fmt=args.format,
            include_appendix=args.include_appendix,
        )
        for k in ("md_path", "html_path"):
            if result.get(k):
                written_paths.append(result[k])

    print("[build_review_packet] generated:")
    for p in written_paths:
        print(f"  - {p}")
    print(f"  - assets dir: {args.output_dir / 'assets'}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
