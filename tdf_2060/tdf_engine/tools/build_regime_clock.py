"""Phase E-8 — Regime Clock CLI (history backfill + clock PNG).

Example:
    python -m tdf_engine.tools.build_regime_clock \\
        --as-of-run 20260511 \\
        --input-etf  out/db_etf_relaxed_e62/portfolio_etf_20260511.json \\
        --input-fund out/db_fund_relaxed_e62/portfolio_fund_20260511.json \\
        --source-root C:/Users/user/Downloads/python/Advisory \\
        --output-history-dir out/db_review_relaxed_e62/regime_history/20260511 \\
        --output-figures-dir out/db_review_relaxed_e62/regime_history/20260511 \\
        --summary-md out/db_review_relaxed_e62/regime_history/20260511/regime_history_summary_20260511.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tdf_engine.reporting.regime_clock import (
    TARGET_MONTHS,
    build_regime_history,
    render_regime_clock,
    render_regime_clock_summary_md,
    write_regime_history_json,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdf_engine.tools.build_regime_clock",
        description="Phase E-8 — regime history backfill + 2D regime clock PNG.",
    )
    p.add_argument("--as-of-run", required=True, help="YYYYMMDD")
    p.add_argument("--input-etf", required=True, type=Path)
    p.add_argument("--input-fund", required=True, type=Path)
    p.add_argument(
        "--source-root", required=True, type=Path,
        help="Advisory/ — regime_src 가 있는 디렉터리",
    )
    p.add_argument("--output-history-dir", required=True, type=Path)
    p.add_argument("--output-figures-dir", required=True, type=Path)
    p.add_argument("--summary-md", required=True, type=Path)
    p.add_argument(
        "--target-months", type=int, default=TARGET_MONTHS,
        help=f"history window length (default {TARGET_MONTHS}m)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    for path in (args.input_etf, args.input_fund, args.source_root):
        if not path.exists():
            raise SystemExit(f"input not found: {path}")

    etf_history = build_regime_history(
        args.input_etf,
        source_root=args.source_root,
        target_months=args.target_months,
    )
    fund_history = build_regime_history(
        args.input_fund,
        source_root=args.source_root,
        target_months=args.target_months,
    )

    history_dir = Path(args.output_history_dir)
    figures_dir = Path(args.output_figures_dir)

    etf_json = write_regime_history_json(
        etf_history, history_dir / f"regime_history_etf_{args.as_of_run}.json"
    )
    fund_json = write_regime_history_json(
        fund_history, history_dir / f"regime_history_fund_{args.as_of_run}.json"
    )
    etf_png = render_regime_clock(
        etf_history, figures_dir / f"regime_clock_etf_{args.as_of_run}.png", label="ETF"
    )
    fund_png = render_regime_clock(
        fund_history, figures_dir / f"regime_clock_fund_{args.as_of_run}.png", label="Fund"
    )

    summary_md = Path(args.summary_md)

    def _rel(target: Path, start: Path) -> str:
        try:
            return Path(target).resolve().relative_to(Path(start).resolve()).as_posix()
        except ValueError:
            return Path(target).as_posix()

    render_regime_clock_summary_md(
        as_of_run=args.as_of_run,
        etf_history=etf_history,
        fund_history=fund_history,
        etf_png_rel=_rel(etf_png, summary_md.parent),
        fund_png_rel=_rel(fund_png, summary_md.parent),
        out_path=summary_md,
    )

    print("[build_regime_clock] generated:")
    print(f"  - {etf_json}")
    print(f"  - {fund_json}")
    print(f"  - {etf_png}")
    print(f"  - {fund_png}")
    print(f"  - {summary_md}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
