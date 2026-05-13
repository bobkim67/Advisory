"""R-1F.2 — Manager-Selected SAA downstream dry-run CLI.

Read-only. Writes ONLY to a separate dry-run directory; production / baseline
directories untouched.

Example:
    python -m tdf_engine.tools.run_manager_selected_dry_run \\
        --manager-selected-saa-json out/db_review_relaxed_e62/saa_opportunity_set/20260513/manager_selected_saa_etf_20260513.json \\
        --baseline-portfolio-json   out/db_etf_relaxed_e62/portfolio_etf_20260511.json \\
        --as-of-run 20260513 \\
        --out-dir out/db_etf_relaxed_e62_r1e_dryrun
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tdf_engine.optimization.manager_selected_dry_run import (
    build_dry_run_portfolio,
    render_comparison_md,
    write_dry_run_portfolio_json,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_DIR = REPO_ROOT / "tdf_engine" / "config"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdf_engine.tools.run_manager_selected_dry_run",
        description=(
            "R-1F.2 — Manager-Selected SAA downstream dry-run wiring "
            "(TAA + projection asset-level + product proportional scaling). "
            "Read-only; production/baseline directories untouched."
        ),
    )
    p.add_argument("--manager-selected-saa-json", required=True, type=Path)
    p.add_argument("--baseline-portfolio-json", required=True, type=Path)
    p.add_argument("--as-of-run", required=True, type=str)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--operating-mode", default="relaxed_diagnostic")
    p.add_argument(
        "--config-dir", type=Path, default=DEFAULT_CONFIG_DIR,
        help="tdf_engine/config 경로 (default: 프로젝트 기본).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.manager_selected_saa_json.exists():
        raise SystemExit(f"manager_selected_saa JSON not found: {args.manager_selected_saa_json}")
    if not args.baseline_portfolio_json.exists():
        raise SystemExit(f"baseline portfolio JSON not found: {args.baseline_portfolio_json}")

    manager_dump = json.loads(args.manager_selected_saa_json.read_text(encoding="utf-8"))
    baseline = json.loads(args.baseline_portfolio_json.read_text(encoding="utf-8"))

    payload = build_dry_run_portfolio(
        manager_dump, baseline,
        config_dir=args.config_dir,
        manager_dump_path=args.manager_selected_saa_json,
        baseline_path=args.baseline_portfolio_json,
        operating_mode=args.operating_mode,
    )

    portfolio_type = payload["meta"]["portfolio_type"]
    out_dir = Path(args.out_dir)
    portfolio_json = write_dry_run_portfolio_json(
        payload, out_dir / f"portfolio_{portfolio_type}_{args.as_of_run}.json",
    )
    compare_md = render_comparison_md(
        payload, baseline,
        out_dir / f"manager_selected_saa_dry_run_compare_{portfolio_type}_{args.as_of_run}.md",
    )

    print("[run_manager_selected_dry_run] generated:")
    print(f"  - portfolio JSON (dry-run): {portfolio_json}")
    print(f"  - comparison md:            {compare_md}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
