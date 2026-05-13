"""R-1G.1 — Product Re-selection CLI (selection only, no PortfolioBuilder).

Reads:
  - manager_selected_saa JSON (R-1F.1)
  - R-1F.2 dry-run JSON
  - product file repo (etf_list / fund_list under source_root)
  - tdf_engine/config yaml

Writes ONLY to separate dry-run directory:
  - out/db_{etf,fund}_relaxed_e62_r1g_reselection/

Example:
    python -m tdf_engine.tools.run_product_reselection_dry_run \\
        --manager-selected-saa-json out/db_review_relaxed_e62/saa_opportunity_set/20260513/manager_selected_saa_etf_20260513.json \\
        --r1f2-dry-run-json         out/db_etf_relaxed_e62_r1e_dryrun/portfolio_etf_20260513.json \\
        --baseline-portfolio-json   out/db_etf_relaxed_e62/portfolio_etf_20260511.json \\
        --source-root ../ \\
        --selection-as-of 20260513 \\
        --output-as-of    20260513 \\
        --baseline-portfolio-as-of 20260511 \\
        --universe-as-of  20260511 \\
        --out-dir out/db_etf_relaxed_e62_r1g_reselection
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tdf_engine.optimization.product_reselection_dry_run import (
    TARGET_SOURCE_MANAGER_OVERRIDE,
    TARGET_SOURCE_PROJECTION,
    TARGET_SOURCE_TAA_PRE_PROJECTION,
    build_product_reselection,
    render_product_reselection_summary_md,
    write_product_reselection_json,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_DIR = REPO_ROOT / "tdf_engine" / "config"
DEFAULT_SOURCE_ROOT = REPO_ROOT.parent  # Advisory/ — etf_list / fund_list 위치


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdf_engine.tools.run_product_reselection_dry_run",
        description=(
            "R-1G.1 — Full product re-selection (selection only). "
            "Read-only; production/baseline/R-1F.* directories untouched."
        ),
    )
    p.add_argument("--manager-selected-saa-json", required=True, type=Path)
    p.add_argument("--r1f2-dry-run-json", required=True, type=Path)
    p.add_argument("--baseline-portfolio-json", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)

    p.add_argument(
        "--source-root", type=Path, default=DEFAULT_SOURCE_ROOT,
        help="etf_list / fund_list 가 위치한 디렉토리 (default = Advisory/)",
    )
    p.add_argument(
        "--config-dir", type=Path, default=DEFAULT_CONFIG_DIR,
        help="tdf_engine/config 디렉토리 (read-only)",
    )

    p.add_argument(
        "--target-source", type=str, default=TARGET_SOURCE_PROJECTION,
        choices=(TARGET_SOURCE_PROJECTION, TARGET_SOURCE_MANAGER_OVERRIDE,
                 TARGET_SOURCE_TAA_PRE_PROJECTION),
    )

    p.add_argument("--selection-as-of", type=str, default="")
    p.add_argument("--output-as-of", type=str, default="")
    p.add_argument("--universe-as-of", type=str, default="")
    p.add_argument("--baseline-portfolio-as-of", type=str, default="")
    p.add_argument("--operating-mode", type=str, default="relaxed_diagnostic")
    return p


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"input not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    manager_dump = _read_json(args.manager_selected_saa_json)
    r1f2_dump = _read_json(args.r1f2_dry_run_json)

    payload = build_product_reselection(
        manager_dump, r1f2_dump,
        source_root=args.source_root,
        config_dir=args.config_dir,
        manager_dump_path=args.manager_selected_saa_json,
        r1f2_dump_path=args.r1f2_dry_run_json,
        baseline_portfolio_path=args.baseline_portfolio_json,
        target_source=args.target_source,
        selection_as_of=args.selection_as_of,
        output_as_of=args.output_as_of,
        universe_as_of=args.universe_as_of,
        baseline_portfolio_as_of=args.baseline_portfolio_as_of,
        operating_mode=args.operating_mode,
    )

    portfolio_type = payload["meta"]["portfolio_type"]
    as_of = args.output_as_of or args.selection_as_of or "noasof"
    out_dir = Path(args.out_dir)
    json_out = write_product_reselection_json(
        payload, out_dir / f"product_reselection_{portfolio_type}_{as_of}.json",
    )
    md_out = render_product_reselection_summary_md(
        payload, out_dir / f"product_reselection_summary_{portfolio_type}_{as_of}.md",
    )
    print("[run_product_reselection_dry_run] generated:")
    print(f"  - json: {json_out}")
    print(f"  - md:   {md_out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
