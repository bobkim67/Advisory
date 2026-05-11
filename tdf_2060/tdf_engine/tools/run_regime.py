"""Regime 분석 단독 실행 entry point."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Regime analysis")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from tdf_engine.config.loader import ConfigLoader, load_default_loader
    from tdf_engine.regime.tool import RegimeAnalysisTool
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    loader = ConfigLoader(args.config_dir) if args.config_dir else load_default_loader()
    repo = FileMarketDataRepository(args.source_root)
    taa_config = loader.load_taa_config()

    tool = RegimeAnalysisTool(repo, taa_config)
    result = tool.run()
    state = result.latest_state

    print("=== Regime Analysis ===")
    print(f"region        : {state.region}")
    print(f"as_of         : {state.as_of}")
    print(f"placement     : {state.placement:+.6f}")
    print(f"velocity      : {state.velocity:+.6f}")
    print(f"regime        : {int(state.regime)} ({state.label})")
    print("--- diagnostics ---")
    print(json.dumps(result.diagnostics, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
