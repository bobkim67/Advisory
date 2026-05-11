"""Phase E-6.2 — Portfolio Construction Bridge figures CLI.

기존 portfolio_*.json 만 입력으로 사용한다. optimizer / projection /
selection / DB 를 호출하지 않으므로 allocation 결과는 변동하지 않는다.

기본 = MVP-X 1-page integrated bridge (ETF + Fund 각 1 PNG).
`--with-appendix` 시 기존 9 PNG (asset/drift/products/manager) 를 ## Appendix
섹션으로 추가 첨부.

Backward compat:
- `--mvp-only` 는 기존 9 PNG 세트만 (legacy E-6 MVP) 생성한다. summary md 는
  legacy 형태 (`render_summary_markdown`).

Examples:
    # MVP-X main (기본)
    python -m tdf_engine.tools.render_figures \\
        --as-of-date 20260511 \\
        --input-etf  out/db_etf_relaxed_e62/portfolio_etf_20260511.json \\
        --input-fund out/db_fund_relaxed_e62/portfolio_fund_20260511.json \\
        --output-dir out/db_review_relaxed/figures/20260511 \\
        --summary-md out/db_review_relaxed/figures_summary_20260511.md

    # MVP-X main + 9 PNG appendix
    python -m tdf_engine.tools.render_figures ... --with-appendix

    # legacy 9 PNG only (Phase E-6)
    python -m tdf_engine.tools.render_figures ... --mvp-only
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tdf_engine.reporting import figures


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdf_engine.tools.render_figures",
        description=(
            "Portfolio construction bridge figures (MVP-X) + optional appendix."
        ),
    )
    p.add_argument("--as-of-date", required=True, help="YYYYMMDD")
    p.add_argument("--input-etf", required=True, type=Path)
    p.add_argument("--input-fund", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--summary-md", required=True, type=Path)
    p.add_argument(
        "--with-appendix",
        action="store_true",
        help=(
            "Attach legacy 9 PNG set as ## Appendix section. "
            "Default = main MVP-X only."
        ),
    )
    p.add_argument(
        "--mvp-only",
        action="store_true",
        help=(
            "Legacy mode (Phase E-6) — generate the 9 PNG set only with the "
            "legacy summary md. MVP-X is NOT generated. Use only for backward "
            "compatibility / regression checks."
        ),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    for path in (args.input_etf, args.input_fund):
        if not path.exists():
            raise SystemExit(f"input json not found: {path}")

    if args.mvp_only:
        # legacy E-6 MVP — backward compat
        result = figures.render_mvp(
            as_of_date=args.as_of_date,
            etf_json=args.input_etf,
            fund_json=args.input_fund,
            output_dir=args.output_dir,
            summary_md=args.summary_md,
        )
        print(
            f"[render_figures legacy --mvp-only] generated {len(result['png_paths'])} PNGs"
        )
    else:
        result = figures.render_mvpx(
            as_of_date=args.as_of_date,
            etf_json=args.input_etf,
            fund_json=args.input_fund,
            output_dir=args.output_dir,
            summary_md=args.summary_md,
            with_appendix=bool(args.with_appendix),
        )
        mode = "MVP-X + appendix" if args.with_appendix else "MVP-X only"
        print(
            f"[render_figures {mode}] generated {len(result['png_paths'])} PNGs"
        )

    for p in result["png_paths"]:
        print(f"  - {p}")
    print(f"[render_figures] summary markdown: {result['summary_md']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
