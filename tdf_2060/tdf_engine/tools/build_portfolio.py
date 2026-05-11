"""TDF 2060 포트폴리오 end-to-end 실행 entry point.

산출물:
  - {output_dir}/portfolio_<etf|fund>_<YYYYMMDD>.csv  : product 단위
  - {output_dir}/portfolio_<etf|fund>_<YYYYMMDD>.json : asset_weights / product_weights / diagnostics

Phase C: --source {file|db} 옵션 + --as-of-date.
  - file (기본): FileMarketDataRepository (Phase B).
  - db        : DBMarketDataRepository (asset_rt_vol/corr_matrix). regime_* 는 자동으로 file 폴백.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date as _date
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from tdf_engine.domain.models import PortfolioResult

logger = logging.getLogger(__name__)


def _build_market_repo(loader, source_root: Path, source: str, as_of_date):
    """source = 'file' | 'db'. 반환: market_repo, db_diagnostics(dict|None)."""
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    file_repo = FileMarketDataRepository(source_root)
    if source == "file":
        return file_repo, None

    # db 모드
    raw_sources = loader.load_db_sources_raw()
    if not raw_sources:
        raise RuntimeError(
            "--source db 인데 db_sources.yaml 이 없음. config_dir 확인 필요."
        )

    # SQLAlchemy 엔진 생성 — credential 은 환경변수 우선, 없으면 yaml/CLAUDE 의 운영 default.
    db_user = os.environ.get("TDF_DB_USER", \"${DB_USER}\")
    db_pw = os.environ.get("TDF_DB_PASSWORD", "${DB_PASSWORD}")
    db_host = os.environ.get("TDF_DB_HOST", "${DB_HOST}")
    db_name = os.environ.get("TDF_DB_NAME", "SCIP")

    try:
        from sqlalchemy import create_engine
        url = f"mysql+pymysql://{db_user}:{db_pw}@{db_host}/{db_name}?charset=utf8mb4"
        engine = create_engine(url, pool_pre_ping=True)
        # 헬스체크
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
    except Exception as e:
        raise RuntimeError(
            f"DB 연결 실패 (host={db_host}, db={db_name}): {e}. "
            f"내부망/VPN 연결 또는 환경변수 (TDF_DB_HOST/USER/PASSWORD/NAME) 확인."
        ) from e

    from tdf_engine.repositories.composite import CompositeMarketDataRepository
    from tdf_engine.repositories.db_market_data import DBMarketDataRepository

    db_repo = DBMarketDataRepository(engine, raw_sources, as_of_date=as_of_date)
    composite = CompositeMarketDataRepository(primary=db_repo, fallback=file_repo)
    return composite, db_repo  # db_repo 자체를 넘겨 diagnostics 접근 가능


def build(
    source_root: Path,
    config_dir: Path | None,
    product_type_value: str,
    source: str = "file",
    as_of_date: str | None = None,
) -> "PortfolioResult":
    from tdf_engine.config.loader import ConfigLoader, load_default_loader
    from tdf_engine.domain.enums import ProductType
    from tdf_engine.repositories.file_repositories import FileProductRepository

    loader = ConfigLoader(config_dir) if config_dir else load_default_loader()
    market_repo, db_repo_for_diag = _build_market_repo(
        loader, source_root, source, as_of_date
    )
    product_repo = FileProductRepository(source_root)

    portfolio = _build_with_repos(
        loader=loader,
        market_repo=market_repo,
        product_repo=product_repo,
        product_type=ProductType(product_type_value),
    )

    # source_type 진단 주입
    if db_repo_for_diag is not None:
        # CompositeMarketDataRepository 일 경우 .diag 가 db_repo 안에 있음
        from tdf_engine.repositories.db_market_data import DBMarketDataRepository
        db = db_repo_for_diag if isinstance(db_repo_for_diag, DBMarketDataRepository) else None
        if db is not None:
            portfolio.diagnostics["db_source"] = db.diag.as_dict()
    else:
        portfolio.diagnostics["db_source"] = {"source_type": "file", "as_of_date": as_of_date}

    return portfolio


def _build_with_repos(loader, market_repo, product_repo, product_type) -> "PortfolioResult":
    from tdf_engine.optimization.tool import OptimizationTool
    from tdf_engine.portfolio.tool import PortfolioConstructionTool
    from tdf_engine.regime.tool import RegimeAnalysisTool
    from tdf_engine.selection.tool import ProductSelectionTool
    from tdf_engine.taa.tool import TAAOverlayTool
    from tdf_engine.universe.classifier import ProductClassifier, load_rules
    from tdf_engine.universe.tool import UniverseTool

    assets = loader.load_assets()
    tdf_config = loader.load_tdf_config()
    opt_config = loader.load_optimization_config()
    taa_config = loader.load_taa_config()
    universe_config = loader.load_universe_config()

    raw_rules = loader.load_classification_rules_raw()
    classifier = ProductClassifier(load_rules(raw_rules))

    opt_tool = OptimizationTool(market_repo, assets, tdf_config, opt_config)
    regime_tool = RegimeAnalysisTool(market_repo, taa_config)
    taa_tool = TAAOverlayTool(taa_config, assets=assets, tdf_config=tdf_config)
    universe_tool = UniverseTool(product_repo, universe_config, product_type, classifier=classifier)

    def selection_factory(universe_result):
        return ProductSelectionTool(universe_result, universe_config, product_type)

    construction_tool = PortfolioConstructionTool(
        optimization_tool=opt_tool,
        regime_tool=regime_tool,
        taa_tool=taa_tool,
        universe_tool=universe_tool,
        selection_tool_factory=selection_factory,
        tdf_config=tdf_config,
        universe_config=universe_config,
        assets=assets,
    )
    return construction_tool.run(product_type)


def write_outputs(
    portfolio,
    output_dir: Path,
    product_type_value: str,
    assets=None,
    tdf_config: dict | None = None,
) -> tuple[Path, Path]:
    """csv (product 단위) + json (요약+상세+review packet) + review_*.md 출력.

    반환: (csv_path, json_path). markdown 경로는 동일 디렉토리에 review_<pt>_<date>.md.
    """
    from tdf_engine.reporting.review import build_review_packet, render_markdown

    output_dir.mkdir(parents=True, exist_ok=True)
    today = _date.today().strftime("%Y%m%d")
    base = f"portfolio_{product_type_value}_{today}"
    csv_path = output_dir / f"{base}.csv"
    json_path = output_dir / f"{base}.json"
    md_path = output_dir / f"review_{product_type_value}_{today}.md"

    portfolio.product_weights.to_csv(csv_path, index=False, encoding="utf-8-sig")

    fb = portfolio.diagnostics.get("fallback") or {}
    quality = portfolio.diagnostics.get("quality") or {}
    db = portfolio.diagnostics.get("db_source") or {}

    # Phase C.4 — review packet
    review_packet = build_review_packet(portfolio, assets=assets, tdf_config=tdf_config)

    payload = {
        "as_of": today,
        "portfolio_type": product_type_value,
        "source_type": db.get("source_type", "file"),
        "as_of_date": db.get("as_of_date"),
        "constraints_passed": bool(portfolio.constraints_passed),
        "quality_status": quality.get("quality_status"),
        "max_abs_asset_weight_drift": float(quality.get("max_abs_asset_weight_drift", 0.0)),
        "max_abs_bucket_drift": float(quality.get("max_abs_bucket_drift", 0.0)),
        "drift_by_bucket": dict(quality.get("drift_by_bucket") or {}),
        "fallback_used": bool(fb.get("fallback_used", False)),
        "fallback_reasons": dict(fb.get("fallback_reasons") or {}),
        "review_reasons": list(quality.get("review_reasons") or []),
        # Phase C.4 — 운용자 검토용 정리 키
        "review_summary": review_packet["review_summary"],
        "projection_summary": review_packet["projection_summary"],
        "asset_allocation": review_packet["asset_allocation"],
        "product_allocation": review_packet["product_allocation"],
        "policy_review_items": review_packet["policy_review_items"],
        # 원본 — 디버그/감사용
        "asset_weights": {k: float(v) for k, v in portfolio.asset_weights.items()},
        "asset_weight_sum": float(portfolio.asset_weights.sum()),
        "product_weights": portfolio.product_weights.to_dict(orient="records"),
        "product_weight_sum": (
            float(portfolio.product_weights["weight"].sum())
            if not portfolio.product_weights.empty
            else 0.0
        ),
        "diagnostics": portfolio.diagnostics,
    }
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    md_path.write_text(render_markdown(review_packet), encoding="utf-8")

    return csv_path, json_path


def dry_run_db_check(
    source_root: Path,
    config_dir: Path | None,
    as_of_date: str | None,
) -> dict:
    """Phase C.1 — DB load + sanity 까지만 수행. portfolio 만들지 않음.

    반환: {load_ok, asset_rt_vol_rows, corr_shape, db_source_diag}
    """
    from tdf_engine.config.loader import ConfigLoader, load_default_loader
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    loader = ConfigLoader(config_dir) if config_dir else load_default_loader()
    file_repo = FileMarketDataRepository(source_root)

    raw_sources = loader.load_db_sources_raw()
    if not raw_sources:
        return {
            "load_ok": False,
            "error": "db_sources.yaml not found",
        }

    db_user = os.environ.get("TDF_DB_USER", \"${DB_USER}\")
    db_pw = os.environ.get("TDF_DB_PASSWORD", "${DB_PASSWORD}")
    db_host = os.environ.get("TDF_DB_HOST", "${DB_HOST}")
    db_name = os.environ.get("TDF_DB_NAME", "SCIP")
    try:
        from sqlalchemy import create_engine, text
        url = f"mysql+pymysql://{db_user}:{db_pw}@{db_host}/{db_name}?charset=utf8mb4"
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        return {"load_ok": False, "error": f"DB 연결 실패: {e}"}

    from tdf_engine.repositories.db_market_data import DBMarketDataRepository

    db_repo = DBMarketDataRepository(
        engine, raw_sources, as_of_date=as_of_date, permissive=True
    )
    result: dict = {"load_ok": True, "as_of_date": as_of_date}
    try:
        rt = db_repo.load_asset_rt_vol()
        result["asset_rt_vol_rows"] = int(len(rt))
    except (ValueError, NotImplementedError) as e:
        result["asset_rt_vol_error"] = str(e)
    try:
        corr = db_repo.load_corr_matrix()
        result["corr_shape"] = list(corr.shape)
    except (ValueError, NotImplementedError) as e:
        result["corr_error"] = str(e)
    result["db_source_diag"] = db_repo.diag.as_dict()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build TDF 2060 portfolio (ETF or fund)")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, default=None)
    parser.add_argument("--product-type", choices=["etf", "fund"], default=None)
    parser.add_argument(
        "--source",
        choices=["file", "db"],
        default="file",
        help="market data source. file (default) = Asset_rt_vol/Corr_mat 등 파일. "
             "db = SCIP back_datapoint 시계열에서 σ/Σ 계산.",
    )
    parser.add_argument(
        "--as-of-date",
        default=None,
        help="YYYY-MM-DD. db 모드에서 해당 날짜 이전까지 시계열만 사용.",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--dry-run-db-check",
        action="store_true",
        help="포트폴리오 산출 없이 DB load + sanity 만 실행. "
             "missing dataset / semantic 문제 / stale data 요약 출력.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.dry_run_db_check:
        result = dry_run_db_check(args.source_root, args.config_dir, args.as_of_date)
        print("=== DB dry-run ===")
        print(f"load_ok            : {result.get('load_ok')}")
        print(f"as_of_date         : {result.get('as_of_date')}")
        if result.get("error"):
            print(f"error              : {result['error']}")
        if "asset_rt_vol_rows" in result:
            print(f"asset_rt_vol_rows  : {result['asset_rt_vol_rows']}")
        if "asset_rt_vol_error" in result:
            print(f"asset_rt_vol_error : {result['asset_rt_vol_error']}")
        if "corr_shape" in result:
            print(f"corr_shape         : {result['corr_shape']}")
        if "corr_error" in result:
            print(f"corr_error         : {result['corr_error']}")
        diag = result.get("db_source_diag") or {}
        print(f"datasets_loaded    : {diag.get('datasets_loaded')}")
        print(f"datasets_missing   : {diag.get('datasets_missing')}")
        print(f"proxy_used         : {diag.get('proxy_used')}")
        print(f"warnings ({len(diag.get('warnings') or [])}):")
        for w in (diag.get("warnings") or [])[:30]:
            print(f"  - {w}")
        sanity = diag.get("sanity") or {}
        if sanity:
            print(f"--- sanity per asset ---")
            for ak, s in sanity.items():
                flags = s.get("suspicious_flags") or []
                print(f"  {ak:<24s} obs={s.get('obs_count'):>3} "
                      f"latest={s.get('latest_date')} "
                      f"ann_vol={s.get('annualized_vol'):>+.4f} "
                      f"flags={flags}")
        if args.output_dir is not None:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            out_path = args.output_dir / "db_dry_run.json"
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n[saved] {out_path}")
        return 0 if result.get("load_ok") else 2

    if args.product_type is None:
        parser.error("--product-type {etf|fund} is required (without --dry-run-db-check)")

    portfolio = build(
        args.source_root,
        args.config_dir,
        args.product_type,
        source=args.source,
        as_of_date=args.as_of_date,
    )

    quality = portfolio.diagnostics.get("quality") or {}
    db = portfolio.diagnostics.get("db_source") or {}
    print(f"=== TDF 2060 Portfolio ({args.product_type}) ===")
    print(f"source_type        : {db.get('source_type', 'file')}")
    print(f"as_of_date         : {db.get('as_of_date')}")
    print(f"constraints_passed : {portfolio.constraints_passed}")
    print(f"quality_status     : {quality.get('quality_status')}")
    print(f"max_abs_asset_drift: {float(quality.get('max_abs_asset_weight_drift', 0.0)):.4%}")
    print(f"asset_weight_sum   : {float(portfolio.asset_weights.sum()):.6f}")
    print()
    print("--- asset weights ---")
    for k, v in portfolio.asset_weights.items():
        print(f"  {k:<24s} {v:>8.4%}")
    print()
    print(f"--- products ({len(portfolio.product_weights)}) ---")
    if not portfolio.product_weights.empty:
        cols = ["asset_key", "product_id", "name", "manager", "weight", "role"]
        print(portfolio.product_weights[cols].to_string(index=False))

    if args.output_dir is not None:
        from tdf_engine.config.loader import ConfigLoader, load_default_loader
        _loader = ConfigLoader(args.config_dir) if args.config_dir else load_default_loader()
        csv_path, json_path = write_outputs(
            portfolio, args.output_dir, args.product_type,
            assets=_loader.load_assets(),
            tdf_config=_loader.load_tdf_config(),
        )
        md_path = args.output_dir / f"review_{args.product_type}_{csv_path.stem.split('_')[-1]}.md"
        print(f"\n[saved] {csv_path}")
        print(f"[saved] {json_path}")
        print(f"[saved] {md_path}")

    if not portfolio.constraints_passed:
        print("\n[warning] constraints not fully passed — see diagnostics.validation.issues")
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
