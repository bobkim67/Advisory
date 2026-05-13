"""R-1C — SAA Opportunity Set scatter / cloud plot CLI.

ETF + Fund opportunity_set JSON → 3 PNG each + cloud review markdown.
read-only diagnostic. opportunity_set JSON / production allocation / TAA / product
selection / config / Decision Register / E-series baseline 모두 미변경.

Example:
    python -m tdf_engine.tools.plot_saa_opportunity_set \\
        --as-of-run 20260513 \\
        --input-etf  out/db_review_relaxed_e62/saa_opportunity_set/20260513/saa_opportunity_set_etf_20260513.json \\
        --input-fund out/db_review_relaxed_e62/saa_opportunity_set/20260513/saa_opportunity_set_fund_20260513.json \\
        --output-dir out/db_review_relaxed_e62/saa_opportunity_set/20260513 \\
        --review-md  out/db_review_relaxed_e62/saa_opportunity_set/20260513/saa_opportunity_set_cloud_review_20260513.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tdf_engine.optimization.opportunity_set_plot import (
    build_cloud_artifacts,
    render_cloud_review_md,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdf_engine.tools.plot_saa_opportunity_set",
        description=(
            "R-1C — SAA opportunity set scatter / cloud / overlap visualization. "
            "Read-only diagnostic; production allocation unchanged."
        ),
    )
    p.add_argument("--as-of-run", required=True, help="YYYYMMDD")
    p.add_argument("--input-etf", required=True, type=Path)
    p.add_argument("--input-fund", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--review-md", required=True, type=Path)
    p.add_argument(
        "--quantile", type=float, default=0.10,
        help="decile cut for cloud + overlap_score (default 0.10)",
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

    out_dir = Path(args.output_dir)

    etf_art = build_cloud_artifacts(
        etf, out_dir, as_of_run=args.as_of_run,
        portfolio_tag="etf", quantile=args.quantile,
    )
    fund_art = build_cloud_artifacts(
        fund, out_dir, as_of_run=args.as_of_run,
        portfolio_tag="fund", quantile=args.quantile,
    )

    review_md = render_cloud_review_md(
        as_of_run=args.as_of_run,
        etf_payload=etf,
        fund_payload=fund,
        etf_thresholds=etf_art["thresholds"],
        fund_thresholds=fund_art["thresholds"],
        etf_enriched_ranked=etf_art["enriched_ranked"],
        fund_enriched_ranked=fund_art["enriched_ranked"],
        plot_paths_etf=etf_art["plots"],
        plot_paths_fund=fund_art["plots"],
        out_path=Path(args.review_md),
    )

    print("[plot_saa_opportunity_set] generated:")
    for art in (etf_art, fund_art):
        for k, p in art["plots"].items():
            print(f"  - {k}: {p}")
    print(f"  - cloud_review_md: {review_md}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
