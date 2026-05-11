"""Universe 필터 단독 실행 entry point."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Universe filter")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, default=None)
    parser.add_argument("--product-type", choices=["etf", "fund"], required=True)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from tdf_engine.config.loader import ConfigLoader, load_default_loader
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.repositories.file_repositories import FileProductRepository
    from tdf_engine.universe.tool import UniverseTool

    loader = ConfigLoader(args.config_dir) if args.config_dir else load_default_loader()
    repo = FileProductRepository(args.source_root)
    universe_config = loader.load_universe_config()

    pt = ProductType(args.product_type)
    tool = UniverseTool(repo, universe_config, pt)
    result = tool.run()

    print(f"=== Universe ({pt.value}) ===")
    print(f"raw      : {result.raw_count}")
    print(f"passed   : {result.filtered_count}")
    print(f"excluded : {len(result.excluded)}")
    print()
    print("--- by asset_key ---")
    counter = Counter(p.mvo_asset_class for p in result.products)
    for k, n in sorted(counter.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<24s} {n:>4d}")
    print()
    print("--- diagnostics ---")
    print(json.dumps(result.diagnostics, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
