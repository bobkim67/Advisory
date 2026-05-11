"""Phase E-10 — TAA Regime Tilt CLI.

ETF + Fund portfolio_*.json + (옵션) taa_policy.yaml → tilt JSON 2 + PNG 2 + summary md.
read-only.

Example:
    python -m tdf_engine.tools.build_taa_tilt \\
        --as-of-run 20260511 \\
        --input-etf  out/db_etf_relaxed_e62/portfolio_etf_20260511.json \\
        --input-fund out/db_fund_relaxed_e62/portfolio_fund_20260511.json \\
        --taa-policy tdf_engine/config/taa_policy.yaml \\
        --output-dir out/db_review_relaxed_e62/taa_tilt/20260511 \\
        --summary-md out/db_review_relaxed_e62/taa_tilt/20260511/taa_tilt_summary_20260511.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tdf_engine.reporting.taa_tilt import (
    build_taa_tilt,
    render_taa_tilt,
    render_taa_tilt_summary_md,
    write_taa_tilt_json,
)


def _load_yaml(path: Path | None) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    import yaml

    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdf_engine.tools.build_taa_tilt",
        description="Phase E-10 — rule-based TAA tilt diagnostic + PNG.",
    )
    p.add_argument("--as-of-run", required=True, help="YYYYMMDD")
    p.add_argument("--input-etf", required=True, type=Path)
    p.add_argument("--input-fund", required=True, type=Path)
    p.add_argument(
        "--taa-policy",
        type=Path,
        default=None,
        help="tdf_engine/config/taa_policy.yaml (per-regime asset_tilts source).",
    )
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--summary-md", required=True, type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    for path in (args.input_etf, args.input_fund):
        if not path.exists():
            raise SystemExit(f"input not found: {path}")

    taa_policy = _load_yaml(args.taa_policy)

    etf = json.loads(args.input_etf.read_text(encoding="utf-8"))
    fund = json.loads(args.input_fund.read_text(encoding="utf-8"))

    etf_payload = build_taa_tilt(etf, taa_policy=taa_policy)
    fund_payload = build_taa_tilt(fund, taa_policy=taa_policy)

    out_dir = Path(args.output_dir)
    etf_json = write_taa_tilt_json(
        etf_payload, out_dir / f"taa_tilt_etf_{args.as_of_run}.json"
    )
    fund_json = write_taa_tilt_json(
        fund_payload, out_dir / f"taa_tilt_fund_{args.as_of_run}.json"
    )
    etf_png = render_taa_tilt(
        etf_payload, out_dir / f"taa_tilt_etf_{args.as_of_run}.png", label="ETF"
    )
    fund_png = render_taa_tilt(
        fund_payload, out_dir / f"taa_tilt_fund_{args.as_of_run}.png", label="Fund"
    )

    summary_md = Path(args.summary_md)

    def _rel(target: Path, start: Path) -> str:
        try:
            return Path(target).resolve().relative_to(Path(start).resolve()).as_posix()
        except ValueError:
            return Path(target).as_posix()

    render_taa_tilt_summary_md(
        as_of_run=args.as_of_run,
        etf_payload=etf_payload,
        fund_payload=fund_payload,
        etf_png_rel=_rel(etf_png, summary_md.parent),
        fund_png_rel=_rel(fund_png, summary_md.parent),
        out_path=summary_md,
    )

    print("[build_taa_tilt] generated:")
    for p in (etf_json, fund_json, etf_png, fund_png, summary_md):
        print(f"  - {p}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
