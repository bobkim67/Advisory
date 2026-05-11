"""SAA 최적화 단독 실행 entry point."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run TDF 2060 SAA optimization")
    parser.add_argument(
        "--source-root",
        type=Path,
        required=True,
        help="Advisory/ 디렉토리 경로 (Asset_rt_vol, Corr_mat 등 직속).",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="config/ 디렉토리. 미지정 시 tdf_engine/config/ 사용.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from tdf_engine.config.loader import ConfigLoader, load_default_loader
    from tdf_engine.optimization.tool import OptimizationTool
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    loader = ConfigLoader(args.config_dir) if args.config_dir else load_default_loader()
    repo = FileMarketDataRepository(args.source_root)

    assets = loader.load_assets()
    tdf_config = loader.load_tdf_config()
    opt_config = loader.load_optimization_config()

    tool = OptimizationTool(repo, assets, tdf_config, opt_config)
    result = tool.run()

    # stdout 표
    print("=== SAA Optimization Result ===")
    print(f"objective       : {result.objective_name}")
    print(f"expected_return : {result.expected_return:.4%}")
    print(f"volatility      : {result.volatility:.4%}")
    print(f"sharpe          : {result.sharpe:.4f}")
    print(f"weight_sum      : {float(result.weights.sum()):.6f}")
    print("--- weights ---")
    for k, v in result.weights.items():
        print(f"  {k:<24s} {v:>8.4%}")
    print("--- diagnostics ---")
    print(json.dumps(result.diagnostics, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
