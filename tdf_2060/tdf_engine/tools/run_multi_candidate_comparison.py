"""R-1I — Multi-candidate dry-run comparison CLI.

Iterates R-1F.1 validation + R-1G.2 PortfolioBuilder wiring across sweet_spot_5 +
boundary candidates, then renders a single multi-candidate comparison packet.

Read-only with respect to production / baseline / R-1B.2 ~ R-1H 산출물.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tdf_engine.optimization.multi_candidate_comparison import (
    render_multi_candidate_comparison_md,
    run_multi_candidate_batch,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_DIR = REPO_ROOT / "tdf_engine" / "config"
DEFAULT_SOURCE_ROOT = REPO_ROOT.parent


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdf_engine.tools.run_multi_candidate_comparison",
        description=(
            "R-1I — multi-candidate batch dry-run + comparison packet. "
            "Read-only; existing R-1G.2 outputs untouched (별도 dir)."
        ),
    )
    p.add_argument("--opportunity-etf-json", required=True, type=Path)
    p.add_argument("--opportunity-fund-json", required=True, type=Path)
    p.add_argument("--baseline-etf-json", required=True, type=Path)
    p.add_argument("--baseline-fund-json", required=True, type=Path)
    p.add_argument("--review-packet-md", required=True, type=Path,
                   help="R-1H final review packet path (for sha256 strict check)")
    p.add_argument("--multi-candidate-review-dir", required=True, type=Path)
    p.add_argument("--etf-out-root", required=True, type=Path,
                   help="e.g. out/db_etf_relaxed_e62_r1i_multi_candidate")
    p.add_argument("--fund-out-root", required=True, type=Path,
                   help="e.g. out/db_fund_relaxed_e62_r1i_multi_candidate")
    p.add_argument("--comparison-md-out", required=True, type=Path)
    p.add_argument("--as-of", required=True, type=str)
    p.add_argument(
        "--source-root", type=Path, default=DEFAULT_SOURCE_ROOT,
        help="etf_list / fund_list 위치 (default = Advisory/)",
    )
    p.add_argument(
        "--config-dir", type=Path, default=DEFAULT_CONFIG_DIR,
        help="tdf_engine/config (read-only)",
    )
    p.add_argument(
        "--selected-at", type=str, default=None,
        help="ISO8601; default = now (UTC)",
    )
    p.add_argument(
        "--target-return-advisory", type=float, default=None,
        help="optional advisory only (no auto-filter)",
    )
    p.add_argument(
        "--target-return-tolerance", type=float, default=0.0025,
    )
    p.add_argument("--operating-mode", type=str, default="relaxed_diagnostic")
    return p


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"input not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    opp_etf = _read_json(args.opportunity_etf_json)
    opp_fund = _read_json(args.opportunity_fund_json)
    baseline_etf = _read_json(args.baseline_etf_json)
    baseline_fund = _read_json(args.baseline_fund_json)

    advisory = None
    if args.target_return_advisory is not None:
        advisory = {
            "value": float(args.target_return_advisory),
            "mode": "advisory",
            "tolerance": float(args.target_return_tolerance),
        }

    packet = run_multi_candidate_batch(
        opp_etf=opp_etf,
        opp_fund=opp_fund,
        opp_etf_path=args.opportunity_etf_json,
        opp_fund_path=args.opportunity_fund_json,
        baseline_etf=baseline_etf,
        baseline_fund=baseline_fund,
        baseline_etf_path=args.baseline_etf_json,
        baseline_fund_path=args.baseline_fund_json,
        review_packet_path=args.review_packet_md,
        source_root=args.source_root,
        config_dir=args.config_dir,
        multi_candidate_review_dir=args.multi_candidate_review_dir,
        etf_portfolio_dir=args.etf_out_root,
        fund_portfolio_dir=args.fund_out_root,
        as_of=args.as_of,
        selected_at=args.selected_at,
        operating_mode=args.operating_mode,
        target_return_advisory=advisory,
    )

    md_path = render_multi_candidate_comparison_md(
        packet, opp_etf=opp_etf, out_path=args.comparison_md_out,
    )

    print(f"[run_multi_candidate_comparison] generated comparison: {md_path}")
    print(f"  candidate count (sampled): {len(packet['candidate_set'])}")
    print(f"  ETF per-candidate dir: {args.etf_out_root}")
    print(f"  Fund per-candidate dir: {args.fund_out_root}")
    print(f"  selection dumps dir:    {args.multi_candidate_review_dir}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
