"""Regime × 자산 평균수익률 단독 실행 entry point."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Regime asset returns")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from tdf_engine.config.loader import ConfigLoader, load_default_loader
    from tdf_engine.regime.tool import RegimeAnalysisTool, RegimeReturnTool
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    loader = ConfigLoader(args.config_dir) if args.config_dir else load_default_loader()
    repo = FileMarketDataRepository(args.source_root)

    assets = loader.load_assets()
    taa_config = loader.load_taa_config()

    regime_tool = RegimeAnalysisTool(repo, taa_config)
    regime_result = regime_tool.run()

    return_tool = RegimeReturnTool(repo, assets)
    rr_result = return_tool.run(regime_result.regime[regime_result.diagnostics["region"]])

    print("=== Regime × Asset Return (mean) ===")
    print(rr_result.regime_avg.to_string(float_format=lambda v: f"{v:.4%}"))
    print("--- diagnostics ---")
    print(json.dumps(rr_result.diagnostics, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
