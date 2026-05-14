"""R-1G.2 — Build reselected portfolio (PortfolioBuilder wiring) + 3-way comparison CLI.

Reads:
  - manager_selected_saa JSON (R-1F.1)
  - R-1F.2 dry-run JSON
  - baseline portfolio JSON
  - (optional) R-1G.1 product_reselection JSON (for sha256 tracking)

Writes ONLY to a separate dry-run directory:
  - out/db_{etf,fund}_relaxed_e62_r1g_reselection/portfolio_{type}_{as_of}.json
  - out/db_{etf,fund}_relaxed_e62_r1g_reselection/r1g_three_way_compare_{type}_{as_of}.md

Read-only with respect to production / baseline / R-1B.2 ~ R-1G.1 산출물.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tdf_engine.optimization.product_reselection_dry_run import (
    TARGET_SOURCE_MANAGER_OVERRIDE,
    TARGET_SOURCE_PROJECTION,
    TARGET_SOURCE_TAA_PRE_PROJECTION,
)
from tdf_engine.optimization.r1g2_reselected_portfolio import (
    build_r1g2_portfolio,
    render_three_way_compare_md,
    write_r1g2_portfolio_json,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_DIR = REPO_ROOT / "tdf_engine" / "config"
DEFAULT_SOURCE_ROOT = REPO_ROOT.parent


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdf_engine.tools.build_r1g_reselected_portfolio",
        description=(
            "R-1G.2 — Full re-selection + PortfolioBuilder + 3-way comparison. "
            "Read-only; production / baseline / R-1B.2 ~ R-1G.1 산출물 변경 없음."
        ),
    )
    p.add_argument("--manager-selected-saa-json", required=True, type=Path)
    p.add_argument("--r1f2-dry-run-json", required=True, type=Path)
    p.add_argument("--baseline-portfolio-json", required=True, type=Path)
    p.add_argument(
        "--r1g1-reselection-json", type=Path, default=None,
        help="R-1G.1 product_reselection JSON path (옵션, 추적성).",
    )
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument(
        "--source-root", type=Path, default=DEFAULT_SOURCE_ROOT,
        help="etf_list / fund_list 위치 (default = Advisory/)",
    )
    p.add_argument(
        "--config-dir", type=Path, default=DEFAULT_CONFIG_DIR,
        help="tdf_engine/config (read-only)",
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
    baseline = _read_json(args.baseline_portfolio_json)

    payload = build_r1g2_portfolio(
        manager_dump, r1f2_dump, baseline,
        source_root=args.source_root,
        config_dir=args.config_dir,
        manager_dump_path=args.manager_selected_saa_json,
        r1f2_dump_path=args.r1f2_dry_run_json,
        baseline_portfolio_path=args.baseline_portfolio_json,
        r1g1_reselection_path=args.r1g1_reselection_json,
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
    json_path = write_r1g2_portfolio_json(
        payload, out_dir / f"portfolio_{portfolio_type}_{as_of}.json",
    )
    md_path = render_three_way_compare_md(
        payload, baseline, r1f2_dump,
        out_dir / f"r1g_three_way_compare_{portfolio_type}_{as_of}.md",
    )
    print("[build_r1g_reselected_portfolio] generated:")
    print(f"  - portfolio JSON: {json_path}")
    print(f"  - compare md:     {md_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
