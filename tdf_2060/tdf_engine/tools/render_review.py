"""Phase D.2 — 기존 portfolio JSON 산출에서 review markdown 재생성 + ETF/Fund 비교.

용도
  (1) `out/db_etf/portfolio_etf_*.json`, `out/db_fund/portfolio_fund_*.json` 파일에서
      review packet 키 + diagnostics 를 읽어 reporting.review.render_markdown 으로
      재렌더. DB 재실행 없이 reporting 포맷 개선만 반영하고 싶을 때 사용.
  (2) ETF/Fund 두 산출을 비교한 comparison_etf_vs_fund_<date>.md 생성.

이 모듈은 엔진 로직 / 최적화 / TAA / selection 결과를 변경하지 않는다.
오직 이미 산출된 json 의 필드를 활용해 markdown 만 재생성한다.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── packet 재구성 ───────────────────────────────────────────────────────


def packet_from_json(json_path: Path) -> dict[str, Any]:
    """portfolio_*.json 에서 review packet 을 재구성.

    JSON 에는 review_summary / projection_summary / asset_allocation /
    product_allocation / policy_review_items 가 top-level 로 저장되어 있다.
    Phase D.2 신규 derive 키 (executive_summary / regime_context / bucket_summary /
    excluded_summary / warning_register / review_checklist / future_telemetry_notes)
    는 reporting.review 의 helper 로 diagnostics 를 보고 새로 만들어 붙인다.
    """
    from tdf_engine.reporting.review import (
        _build_executive_summary,
        _build_regime_context,
        _build_bucket_summary,
        _build_excluded_summary,
        _build_warning_register,
        _build_review_checklist,
        _build_future_telemetry_notes,
        _build_operating_mode_banner,
    )

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    diag = data.get("diagnostics") or {}
    val = diag.get("validation") or {}
    db = diag.get("db_source") or {}
    sel_diag = diag.get("selection_diagnostics") or {}
    universe_diag = diag.get("universe_diagnostics") or {}
    taa_diag = diag.get("taa_diagnostics") or {}
    regime_blob = diag.get("regime") or {}

    rs = data["review_summary"]

    # build_bucket_summary 는 portfolio.asset_weights 로 us_high_yield 를 찾는다.
    # 여기서는 asset_weights 가 dict 로 저장되어 있으므로 가짜 wrapper 사용.
    class _AssetWeightsView:
        def __init__(self, mapping: dict[str, float]):
            self._m = {str(k): float(v) for k, v in mapping.items()}

        def get(self, key, default=0.0):
            return self._m.get(key, default)

    class _PortfolioView:
        def __init__(self, asset_weights: dict[str, float]):
            self.asset_weights = _AssetWeightsView(asset_weights)

    pv = _PortfolioView(data.get("asset_weights") or {})

    # tdf_config 는 JSON 에 없으므로 ConfigLoader 로 default 로드 (taa_bounds 만 사용).
    from tdf_engine.config.loader import load_default_loader
    loader = load_default_loader()
    try:
        tdf_config = loader.load_tdf_config()
    except Exception:  # pragma: no cover
        tdf_config = {}

    # drift breakdown for §3.1 (Phase D — D-02)
    feas_blob = (taa_diag.get("taa_feasibility") or {})
    quality_blob = (diag.get("quality") or {})

    packet: dict[str, Any] = {
        "review_summary": rs,
        "projection_summary": data["projection_summary"],
        "asset_allocation": data["asset_allocation"],
        "product_allocation": data["product_allocation"],
        "policy_review_items": data["policy_review_items"],
        "operating_mode_banner": _build_operating_mode_banner(tdf_config),
        "_quality_diag": dict(quality_blob),
        "_diagnostics_drift": {
            "projection_clipping_summary": dict(feas_blob.get("clipping_summary") or {}),
            "projection_drift_source_by_asset": dict(feas_blob.get("drift_source_by_asset") or {}),
            "projection_asset_drift_from_target": dict(feas_blob.get("asset_weight_drift_from_target") or {}),
            "quality_drift_clipping_summary": dict(quality_blob.get("drift_clipping_summary") or {}),
            "quality_drift_source_by_asset": dict(quality_blob.get("drift_source_by_asset") or {}),
            "quality_asset_weight_drift": dict(quality_blob.get("asset_weight_drift") or {}),
        },
        "executive_summary": _build_executive_summary(rs),
        "regime_context": _build_regime_context(regime_blob, taa_diag),
        "bucket_summary": _build_bucket_summary(rs, tdf_config, pv),
        "excluded_summary": _build_excluded_summary(universe_diag, sel_diag),
        "warning_register": _build_warning_register(val, db, data["policy_review_items"]),
        "review_checklist": _build_review_checklist(),
        "future_telemetry_notes": _build_future_telemetry_notes(),
    }
    return packet


def rerender_one(json_path: Path, output_path: Path | None = None) -> Path:
    from tdf_engine.reporting.review import render_markdown

    packet = packet_from_json(json_path)
    text = render_markdown(packet)
    if output_path is None:
        # 기존 review_*.md 파일명 추정: portfolio_<pt>_<date>.json → review_<pt>_<date>.md
        stem = json_path.stem  # portfolio_etf_20260507
        parts = stem.split("_")
        if len(parts) >= 3 and parts[0] == "portfolio":
            md_name = f"review_{parts[1]}_{parts[2]}.md"
        else:
            md_name = f"{stem}_review.md"
        output_path = json_path.parent / md_name
    output_path.write_text(text, encoding="utf-8")
    return output_path


# ── ETF / Fund 비교 리포트 ─────────────────────────────────────────────


def render_comparison(etf_json: Path, fund_json: Path, output_path: Path) -> Path:
    """ETF/Fund 두 산출의 비교 리포트 생성."""
    with etf_json.open("r", encoding="utf-8") as f:
        etf = json.load(f)
    with fund_json.open("r", encoding="utf-8") as f:
        fund = json.load(f)

    L: list[str] = []
    ap = L.append

    as_of = etf.get("as_of_date") or fund.get("as_of_date") or "-"
    ap(f"# TDF 2060 ETF vs Fund 비교 리포트 — {as_of}")
    ap("")

    # Phase D — operating mode banner (current yaml 기준)
    from tdf_engine.config.loader import load_default_loader
    from tdf_engine.reporting.review import _build_operating_mode_banner as _omb
    try:
        _tdf = load_default_loader().load_tdf_config()
    except Exception:  # pragma: no cover
        _tdf = {}
    _banner = _omb(_tdf)
    if _banner.get("banner"):
        ap(f"> ⚠️ **{_banner['banner']}**")
        for line in _banner.get("disclaimer", []):
            ap(f"> - {line}")
        ap("")

    ap("두 산출은 동일한 SAA / TAA 흐름으로 산출되었으며 차이는 universe / selection 단계에서 발생한다.")
    ap("")

    # 1. 한눈 비교
    ap("## 1. 한눈 비교")
    ap("")
    ap("| 항목 | ETF | Fund |")
    ap("|---|---:|---:|")
    rs_e = etf.get("review_summary", {})
    rs_f = fund.get("review_summary", {})
    rows = [
        ("portfolio_type", rs_e.get("portfolio_type"), rs_f.get("portfolio_type")),
        ("constraints_passed", rs_e.get("constraints_passed"), rs_f.get("constraints_passed")),
        ("quality_status", rs_e.get("quality_status"), rs_f.get("quality_status")),
        ("asset_weight_sum",
         f"{float(rs_e.get('asset_weight_sum', 0.0)):.6f}",
         f"{float(rs_f.get('asset_weight_sum', 0.0)):.6f}"),
        ("product_weight_sum",
         f"{float(rs_e.get('product_weight_sum', 0.0)):.6f}",
         f"{float(rs_f.get('product_weight_sum', 0.0)):.6f}"),
        ("equity_bucket_weight",
         f"{float(rs_e.get('equity_bucket_weight', 0.0)):.4%}",
         f"{float(rs_f.get('equity_bucket_weight', 0.0)):.4%}"),
        ("fixed_income_bucket_weight",
         f"{float(rs_e.get('fixed_income_bucket_weight', 0.0)):.4%}",
         f"{float(rs_f.get('fixed_income_bucket_weight', 0.0)):.4%}"),
        ("validation_warnings_count",
         rs_e.get("validation_warnings_count"),
         rs_f.get("validation_warnings_count")),
        ("db_warnings_count",
         rs_e.get("db_warnings_count"), rs_f.get("db_warnings_count")),
        ("fallback_used", rs_e.get("fallback_used"), rs_f.get("fallback_used")),
        ("projection_used", rs_e.get("projection_used"), rs_f.get("projection_used")),
        ("max_abs_projection_drift",
         f"{float(rs_e.get('max_abs_projection_drift', 0.0)):.4%}",
         f"{float(rs_f.get('max_abs_projection_drift', 0.0)):.4%}"),
        ("n_products",
         len(etf.get("product_allocation") or []),
         len(fund.get("product_allocation") or [])),
    ]
    for label, e, f_ in rows:
        ap(f"| {label} | {e} | {f_} |")
    ap("")

    # 2. 자산군별 final weight 비교
    ap("## 2. 자산군별 final weight")
    ap("")
    aa_e = {r["asset_key"]: r for r in (etf.get("asset_allocation") or [])}
    aa_f = {r["asset_key"]: r for r in (fund.get("asset_allocation") or [])}
    keys = sorted(set(list(aa_e.keys()) + list(aa_f.keys())))
    ap("| asset_key | ETF | Fund | 차이 |")
    ap("|---|---:|---:|---:|")
    for k in keys:
        e = float((aa_e.get(k) or {}).get("final_asset_weight", 0.0))
        f_ = float((aa_f.get(k) or {}).get("final_asset_weight", 0.0))
        ap(f"| {k} | {e:>+8.4%} | {f_:>+8.4%} | {e - f_:>+8.4%} |")
    ap("")

    # 3. 공통 / 차별 warning
    ap("## 3. Validation warning — 공통 vs 차별")
    ap("")
    we = set(str(w) for w in (etf.get("diagnostics", {}).get("validation", {}).get("warnings") or []))
    wf = set(str(w) for w in (fund.get("diagnostics", {}).get("validation", {}).get("warnings") or []))
    common = sorted(we & wf)
    only_e = sorted(we - wf)
    only_f = sorted(wf - we)
    ap(f"- 공통 ({len(common)}건):")
    for w in common:
        ap(f"  - {w}")
    ap(f"- ETF 만 ({len(only_e)}건):")
    for w in only_e:
        ap(f"  - {w}")
    ap(f"- Fund 만 ({len(only_f)}건):")
    for w in only_f:
        ap(f"  - {w}")
    ap("")

    # 4. 상위 5개 상품 비중
    ap("## 4. 상위 5개 상품 비중")
    ap("")
    for label, payload in (("ETF", etf), ("Fund", fund)):
        pa = sorted(
            payload.get("product_allocation") or [],
            key=lambda r: -float(r.get("final_weight", 0.0)),
        )[:5]
        ap(f"**{label}**:")
        ap("")
        ap("| asset_key | product | manager | weight |")
        ap("|---|---|---|---:|")
        for p in pa:
            ap(
                f"| {p.get('asset_key')} | {p.get('product_name')} | "
                f"{p.get('manager')} | {float(p.get('final_weight', 0.0)):>+8.4%} |"
            )
        ap("")

    # 5. 운용사 concentration
    ap("## 5. 운용사 concentration")
    ap("")
    for label, payload in (("ETF", etf), ("Fund", fund)):
        by_mgr: dict[str, float] = {}
        for p in payload.get("product_allocation") or []:
            mgr = str(p.get("manager") or "-")
            by_mgr[mgr] = by_mgr.get(mgr, 0.0) + float(p.get("final_weight", 0.0))
        top = sorted(by_mgr.items(), key=lambda kv: -kv[1])[:5]
        ap(f"**{label}** top-5 운용사:")
        ap("")
        ap("| 운용사 | 합계 weight |")
        ap("|---|---:|")
        for mgr, w in top:
            ap(f"| {mgr} | {w:>+8.4%} |")
        ap("")

    output_path.write_text("\n".join(L), encoding="utf-8")
    return output_path


# ── CLI ────────────────────────────────────────────────────────────────


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Re-render review markdown from portfolio JSON (Phase D.2)."
    )
    p.add_argument("--json", required=False, help="단일 portfolio_*.json 경로")
    p.add_argument("--out-md", required=False, help="단일 출력 markdown 경로")
    p.add_argument("--etf-json", required=False, help="비교용 ETF json")
    p.add_argument("--fund-json", required=False, help="비교용 Fund json")
    p.add_argument("--comparison-out", required=False, help="비교 markdown 경로")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    if args.json:
        path = Path(args.json)
        out = Path(args.out_md) if args.out_md else None
        result = rerender_one(path, out)
        print(f"rendered: {result}")
    if args.etf_json and args.fund_json:
        out = Path(args.comparison_out) if args.comparison_out else (
            Path(args.etf_json).parent.parent / "db_review" / "comparison.md"
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        result = render_comparison(Path(args.etf_json), Path(args.fund_json), out)
        print(f"comparison: {result}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
