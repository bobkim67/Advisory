"""R-1D — SAA Opportunity Set similar_search (read-only).

Two search modes:
  A. coordinate search   — nearest by (volatility, expected_return) plane
  B. weight search       — nearest by 9-asset weight L2 (+ intra-bucket L2)

Plus batch helper:
  C. shortlist neighborhood — for each manager review shortlist candidate, return
                              k nearest by both A and B.

Hard requirements:
- read-only; opportunity_set JSON / production / config / E-series 산출물 미변경
- ref_max_sharpe 는 항상 검색 결과에서 제외 (unconstrained reference)
- ref_80_20_equal_intra_bucket 는 기본 제외, 명시 옵션 시에만 포함
- 80:20 distance metric 부활 금지 (bucket_distance / full_weight_distance)
- 자동 final SAA 선택 금지 — 검색 결과만 제공
"""

from __future__ import annotations

import json
import math
import statistics
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from tdf_engine.optimization.opportunity_set_plot import (
    attach_overlap_scores,
    compute_thresholds,
)


R1D_SCHEMA_VERSION = "r1d.1"

# Manager review shortlist (frozen from R-1C.1; ETF/Fund identical).
SHORTLIST_CANDIDATE_IDS: tuple[str, ...] = (
    "cand_008421",
    "cand_005995",
    "cand_009678",
    "cand_005991",
    "cand_000758",
    "cand_007510",
    "cand_004225",
    "cand_007699",
)

REF_MAX_SHARPE_ID = "ref_max_sharpe"
REF_80_20_ID = "ref_80_20_equal_intra_bucket"


# ---------------------------------------------------------------------------
# Pool preparation
# ---------------------------------------------------------------------------


def _enrich_candidates_with_overlap(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Attach overlap_score / overlap_flags to candidates (shallow-copy each).

    Reference points are NOT enriched here — they remain in payload['reference_points'].
    """
    th = compute_thresholds(payload["candidates"], quantile=0.10)
    return attach_overlap_scores(payload["candidates"], th)


def _build_search_pool(
    payload: dict[str, Any],
    *,
    feasible_only: bool,
    sampled_only: bool,
    include_ref_80_20: bool = False,
) -> list[dict[str, Any]]:
    """Return enriched candidate list for search.

    - sampled_only=True (default): only sampled candidates (overlap_score 가 attach 된
      후보들). ref_max_sharpe / ref_80_20_equal_intra_bucket 모두 제외.
    - sampled_only=False: sampled candidates + ref_80_20_equal_intra_bucket (단,
      ref_max_sharpe 는 항상 제외).
    - include_ref_80_20 = True 면 ref_80_20 도 포함 (sampled_only=True 와 무관하게).
    - feasible_only=True: feasibility_status == "feasible" 인 후보만.
    """
    enriched = _enrich_candidates_with_overlap(payload)
    if feasible_only:
        enriched = [c for c in enriched if c.get("feasibility_status") == "feasible"]
    pool: list[dict[str, Any]] = list(enriched)
    if (not sampled_only) or include_ref_80_20:
        refs = payload.get("reference_points") or {}
        ref80 = refs.get(REF_80_20_ID)
        if ref80 is not None:
            if (not feasible_only) or ref80.get("feasibility_status") == "feasible":
                # Reference 도 overlap_score 부여 (검색 결과 일관성)
                th = compute_thresholds(payload["candidates"], quantile=0.10)
                pool.extend(attach_overlap_scores([ref80], th))
    # ref_max_sharpe 는 어떤 옵션에서도 절대 포함 안 함.
    return pool


# ---------------------------------------------------------------------------
# Coordinate search (mode A)
# ---------------------------------------------------------------------------


def _pool_std_for_return_vol(
    pool: list[dict[str, Any]],
) -> tuple[float, float]:
    """Population std for normalization."""
    ers = [float(c["expected_return"]) for c in pool if c.get("expected_return") is not None]
    vols = [float(c["volatility"]) for c in pool if c.get("volatility") is not None]
    if len(ers) < 2:
        return 1.0, 1.0
    er_std = statistics.pstdev(ers)
    vol_std = statistics.pstdev(vols)
    return (er_std if er_std > 1e-12 else 1.0,
            vol_std if vol_std > 1e-12 else 1.0)


def _coordinate_distance(
    c: dict[str, Any],
    target_return: float,
    target_volatility: float,
    er_std: float,
    vol_std: float,
) -> float:
    dr = (float(c["expected_return"]) - target_return) / er_std
    dv = (float(c["volatility"]) - target_volatility) / vol_std
    return math.sqrt(dr * dr + dv * dv)


def find_similar_by_risk_return(
    payload: dict[str, Any],
    *,
    target_return: float,
    target_volatility: float,
    k: int = 20,
    feasible_only: bool = True,
    sampled_only: bool = True,
    include_ref_80_20: bool = False,
) -> dict[str, Any]:
    """Mode A — nearest k by normalized (E[R], σ) distance.

    Tie-breakers:
      1) distance asc
      2) overlap_score desc (if present)
      3) feasibility_status == "feasible" 우선
      4) sharpe desc
      5) concentration_hhi asc
      6) max_asset_weight asc
      7) candidate_id asc
    """
    pool = _build_search_pool(
        payload, feasible_only=feasible_only, sampled_only=sampled_only,
        include_ref_80_20=include_ref_80_20,
    )
    er_std, vol_std = _pool_std_for_return_vol(pool)

    enriched: list[tuple[tuple, dict[str, Any]]] = []
    for c in pool:
        d = _coordinate_distance(c, target_return, target_volatility, er_std, vol_std)
        sort_key = (
            d,                                                  # 1) distance asc
            -int(c.get("overlap_score") or 0),                  # 2) overlap desc
            0 if c.get("feasibility_status") == "feasible" else 1,  # 3) feasible 우선
            -(float(c["sharpe"]) if c.get("sharpe") is not None else -1e18),  # 4) sharpe desc
            float(c.get("concentration_hhi") or 1.0),           # 5) HHI asc
            float(c.get("max_asset_weight") or 1.0),            # 6) max_w asc
            str(c.get("candidate_id") or ""),                   # 7) id asc
        )
        new = dict(c)
        new["search_distance"] = float(d)
        enriched.append((sort_key, new))
    enriched.sort(key=lambda t: t[0])
    return {
        "mode": "coordinate",
        "query": {
            "target_return": float(target_return),
            "target_volatility": float(target_volatility),
            "k": int(k),
            "feasible_only": bool(feasible_only),
            "sampled_only": bool(sampled_only),
            "include_ref_80_20": bool(include_ref_80_20),
        },
        "normalization": {
            "expected_return_std": float(er_std),
            "volatility_std": float(vol_std),
        },
        "pool_size": len(pool),
        "results": [t[1] for t in enriched[:int(k)]],
    }


# ---------------------------------------------------------------------------
# Weight search (mode B)
# ---------------------------------------------------------------------------


def _weight_l2(a: dict[str, float], b: dict[str, float], keys: Iterable[str]) -> float:
    s = 0.0
    for k in keys:
        d = float(a.get(k, 0.0)) - float(b.get(k, 0.0))
        s += d * d
    return math.sqrt(s)


def _intra_bucket_l2(
    a: dict[str, float],
    b: dict[str, float],
    bucket_keys: list[str],
    a_total: float,
    b_total: float,
) -> float | None:
    """L2 distance between bucket-internal renormalized weights.

    a / b: weight dicts (raw, 9-asset).
    bucket_keys: subset (equity 또는 FI).
    *_total: bucket sum for that side (raw).
    """
    if a_total <= 1e-12 or b_total <= 1e-12:
        return None  # bucket=0 인 reference 의 경우 정의 불가
    s = 0.0
    for k in bucket_keys:
        da = float(a.get(k, 0.0)) / a_total
        db = float(b.get(k, 0.0)) / b_total
        diff = da - db
        s += diff * diff
    return math.sqrt(s)


def _find_candidate_by_id(
    pool: list[dict[str, Any]],
    candidate_id: str,
) -> dict[str, Any] | None:
    for c in pool:
        if c.get("candidate_id") == candidate_id:
            return c
    return None


def find_similar_by_weights(
    payload: dict[str, Any],
    *,
    target_candidate_id: str,
    k: int = 20,
    feasible_only: bool = True,
    sampled_only: bool = True,
    include_ref_80_20: bool = False,
) -> dict[str, Any]:
    """Mode B — nearest k by 9-asset weight L2 distance.

    Includes 3 distance metrics in result rows:
      full_weight_l2_distance, equity_intra_weight_l2_distance,
      fixed_income_intra_weight_l2_distance.

    Tie-breakers:
      1) full_weight_l2_distance asc
      2) equity_intra_weight_l2_distance asc (None → +inf)
      3) fixed_income_intra_weight_l2_distance asc (None → +inf)
      4) sharpe desc
      5) concentration_hhi asc
      6) candidate_id asc

    Target candidate 자기 자신은 결과에서 제외. target 이 ref_max_sharpe 이면
    먼저 references 에서 찾는다 (검색 결과에는 등장 안 함).
    """
    # target 후보는 검색 제외 대상까지 포함하여 lookup 가능
    asset_keys = list(payload["inputs"]["asset_keys"])
    eq_keys = list(payload["inputs"]["equity_asset_keys"])
    fi_keys = list(payload["inputs"]["fixed_income_asset_keys"])

    enriched_all = _enrich_candidates_with_overlap(payload)
    target = _find_candidate_by_id(enriched_all, target_candidate_id)
    if target is None:
        # try references
        refs = payload.get("reference_points") or {}
        for rid, rc in refs.items():
            if rid == target_candidate_id:
                target = rc
                break
    if target is None:
        raise ValueError(
            f"target_candidate_id={target_candidate_id!r} not found in "
            "candidates / reference_points."
        )

    pool = _build_search_pool(
        payload, feasible_only=feasible_only, sampled_only=sampled_only,
        include_ref_80_20=include_ref_80_20,
    )
    # target 자기 자신 제외
    pool = [c for c in pool if c.get("candidate_id") != target_candidate_id]

    t_w = target.get("weights") or {}
    t_eq_total = float(target.get("equity_weight") or 0.0)
    t_fi_total = float(target.get("fixed_income_weight") or 0.0)

    enriched: list[tuple[tuple, dict[str, Any]]] = []
    for c in pool:
        c_w = c.get("weights") or {}
        c_eq_total = float(c.get("equity_weight") or 0.0)
        c_fi_total = float(c.get("fixed_income_weight") or 0.0)
        full_l2 = _weight_l2(t_w, c_w, asset_keys)
        eq_l2 = _intra_bucket_l2(t_w, c_w, eq_keys, t_eq_total, c_eq_total)
        fi_l2 = _intra_bucket_l2(t_w, c_w, fi_keys, t_fi_total, c_fi_total)

        sort_key = (
            full_l2,                                                # 1) full L2 asc
            (eq_l2 if eq_l2 is not None else float("inf")),         # 2) eq intra L2 asc
            (fi_l2 if fi_l2 is not None else float("inf")),         # 3) fi intra L2 asc
            -(float(c["sharpe"]) if c.get("sharpe") is not None else -1e18),  # 4) sharpe desc
            float(c.get("concentration_hhi") or 1.0),               # 5) HHI asc
            str(c.get("candidate_id") or ""),                       # 6) id asc
        )
        new = dict(c)
        new["full_weight_l2_distance"] = float(full_l2)
        new["equity_intra_weight_l2_distance"] = (
            float(eq_l2) if eq_l2 is not None else None
        )
        new["fixed_income_intra_weight_l2_distance"] = (
            float(fi_l2) if fi_l2 is not None else None
        )
        enriched.append((sort_key, new))
    enriched.sort(key=lambda t: t[0])

    return {
        "mode": "candidate",
        "query": {
            "target_candidate_id": str(target_candidate_id),
            "k": int(k),
            "feasible_only": bool(feasible_only),
            "sampled_only": bool(sampled_only),
            "include_ref_80_20": bool(include_ref_80_20),
        },
        "target_summary": {
            "candidate_id": target.get("candidate_id"),
            "expected_return": float(target.get("expected_return") or 0.0),
            "volatility": float(target.get("volatility") or 0.0),
            "sharpe": (float(target["sharpe"]) if target.get("sharpe") is not None else None),
            "equity_weight": float(target.get("equity_weight") or 0.0),
            "fixed_income_weight": float(target.get("fixed_income_weight") or 0.0),
            "concentration_hhi": float(target.get("concentration_hhi") or 0.0),
            "max_asset_weight": float(target.get("max_asset_weight") or 0.0),
        },
        "pool_size": len(pool),
        "results": [t[1] for t in enriched[:int(k)]],
    }


# ---------------------------------------------------------------------------
# Shortlist neighborhood (mode C)
# ---------------------------------------------------------------------------


def build_shortlist_neighborhood(
    payload: dict[str, Any],
    *,
    shortlist_ids: tuple[str, ...] = SHORTLIST_CANDIDATE_IDS,
    k: int = 5,
    feasible_only: bool = True,
    sampled_only: bool = True,
) -> dict[str, Any]:
    """For each shortlist id: coordinate-nearest k + weight-nearest k."""
    enriched_all = _enrich_candidates_with_overlap(payload)
    by_id = {c["candidate_id"]: c for c in enriched_all}
    refs = payload.get("reference_points") or {}

    results: dict[str, Any] = {}
    for sid in shortlist_ids:
        target = by_id.get(sid) or refs.get(sid)
        if target is None:
            results[sid] = {
                "missing": True,
                "reason": "candidate_id not found in pool or references",
            }
            continue
        coord = find_similar_by_risk_return(
            payload,
            target_return=float(target["expected_return"]),
            target_volatility=float(target["volatility"]),
            k=k + 1,  # 자기 자신 포함될 수 있어 +1
            feasible_only=feasible_only,
            sampled_only=sampled_only,
        )
        # 자기 자신 제외
        coord_results = [
            r for r in coord["results"] if r.get("candidate_id") != sid
        ][:k]
        wt = find_similar_by_weights(
            payload,
            target_candidate_id=sid,
            k=k,
            feasible_only=feasible_only,
            sampled_only=sampled_only,
        )
        results[sid] = {
            "target_summary": wt["target_summary"],
            "by_risk_return": coord_results,
            "by_weights": wt["results"],
        }
    return {
        "mode": "shortlist-neighborhood",
        "query": {
            "shortlist_ids": list(shortlist_ids),
            "k": int(k),
            "feasible_only": bool(feasible_only),
            "sampled_only": bool(sampled_only),
        },
        "results": results,
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _fmt_pct(v: float | None) -> str:
    if v is None or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        return "n/a"
    return f"{float(v) * 100:.2f}%"


def _fmt_num(v: float | None, digits: int = 4) -> str:
    if v is None or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        return "n/a"
    return f"{float(v):.{digits}f}"


def _row(c: dict[str, Any]) -> str:
    return (
        f"| {c['candidate_id']} "
        f"| {_fmt_pct(c.get('expected_return'))} "
        f"| {_fmt_pct(c.get('volatility'))} "
        f"| {_fmt_num(c.get('sharpe'))} "
        f"| {_fmt_pct(c.get('equity_weight'))} "
        f"| {_fmt_pct(c.get('fixed_income_weight'))} "
        f"| {_fmt_num(c.get('concentration_hhi'))} "
        f"| {_fmt_num(c.get('equity_intra_hhi'))} "
        f"| {_fmt_num(c.get('fixed_income_intra_hhi'))} "
        f"| {_fmt_pct(c.get('max_asset_weight'))} "
        f"| {c.get('overlap_score', 'n/a')} "
        f"| {c.get('feasibility_status', 'n/a')} |"
    )


_COLS = (
    "| candidate_id | E[R] | σ | Sharpe | eq | fi | HHI | eq_iHHI | fi_iHHI | "
    "max_w | overlap | feas |"
)
_SEP = "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"


def render_search_result_md(result: dict[str, Any], out_path: Path) -> Path:
    out_path = Path(out_path)
    lines: list[str] = []
    mode = result.get("mode")
    lines.append(f"# SAA Opportunity Set — Search Result (R-1D, {mode})")
    lines.append("")
    lines.append(f"> R-1D schema_version: {R1D_SCHEMA_VERSION}")
    lines.append(
        "> Read-only search. ref_max_sharpe 는 항상 결과에서 제외; "
        "ref_80_20_equal_intra_bucket 은 옵션."
    )
    lines.append("")
    lines.append(f"## Query")
    lines.append("")
    q = result.get("query") or {}
    for k, v in q.items():
        lines.append(f"- **{k}**: `{v}`")
    if mode == "coordinate":
        norm = result.get("normalization") or {}
        lines.append(
            f"- normalization (pool std): E[R] σ={norm.get('expected_return_std'):.6f}, "
            f"vol σ={norm.get('volatility_std'):.6f}"
        )
    if mode == "candidate":
        t = result.get("target_summary") or {}
        lines.append("")
        lines.append("### Target")
        lines.append("")
        lines.append(
            f"- **{t.get('candidate_id')}**: "
            f"E[R]={_fmt_pct(t.get('expected_return'))}, "
            f"σ={_fmt_pct(t.get('volatility'))}, "
            f"Sharpe={_fmt_num(t.get('sharpe'))}, "
            f"eq={_fmt_pct(t.get('equity_weight'))}, "
            f"fi={_fmt_pct(t.get('fixed_income_weight'))}, "
            f"HHI={_fmt_num(t.get('concentration_hhi'))}, "
            f"max_w={_fmt_pct(t.get('max_asset_weight'))}"
        )
    lines.append("")
    lines.append(f"## Top-K Results  (pool_size={result.get('pool_size')})")
    lines.append("")
    if mode == "coordinate":
        lines.append("| # | candidate_id | distance | E[R] | σ | Sharpe | eq | fi | "
                     "HHI | eq_iHHI | fi_iHHI | max_w | overlap | feas |")
        lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
        for i, c in enumerate(result.get("results") or [], 1):
            lines.append(
                f"| {i} | {c['candidate_id']} "
                f"| {_fmt_num(c.get('search_distance'))} "
                f"| {_fmt_pct(c.get('expected_return'))} "
                f"| {_fmt_pct(c.get('volatility'))} "
                f"| {_fmt_num(c.get('sharpe'))} "
                f"| {_fmt_pct(c.get('equity_weight'))} "
                f"| {_fmt_pct(c.get('fixed_income_weight'))} "
                f"| {_fmt_num(c.get('concentration_hhi'))} "
                f"| {_fmt_num(c.get('equity_intra_hhi'))} "
                f"| {_fmt_num(c.get('fixed_income_intra_hhi'))} "
                f"| {_fmt_pct(c.get('max_asset_weight'))} "
                f"| {c.get('overlap_score', 'n/a')} "
                f"| {c.get('feasibility_status', 'n/a')} |"
            )
    elif mode == "candidate":
        lines.append("| # | candidate_id | full_L2 | eq_iL2 | fi_iL2 | E[R] | σ | "
                     "Sharpe | HHI | eq_iHHI | fi_iHHI | max_w | overlap |")
        lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for i, c in enumerate(result.get("results") or [], 1):
            lines.append(
                f"| {i} | {c['candidate_id']} "
                f"| {_fmt_num(c.get('full_weight_l2_distance'))} "
                f"| {_fmt_num(c.get('equity_intra_weight_l2_distance'))} "
                f"| {_fmt_num(c.get('fixed_income_intra_weight_l2_distance'))} "
                f"| {_fmt_pct(c.get('expected_return'))} "
                f"| {_fmt_pct(c.get('volatility'))} "
                f"| {_fmt_num(c.get('sharpe'))} "
                f"| {_fmt_num(c.get('concentration_hhi'))} "
                f"| {_fmt_num(c.get('equity_intra_hhi'))} "
                f"| {_fmt_num(c.get('fixed_income_intra_hhi'))} "
                f"| {_fmt_pct(c.get('max_asset_weight'))} "
                f"| {c.get('overlap_score', 'n/a')} |"
            )
    lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def render_shortlist_neighborhood_md(
    result: dict[str, Any],
    payload: dict[str, Any],
    out_path: Path,
) -> Path:
    """Mode C — for each shortlist candidate, dump 2 nearest tables."""
    out_path = Path(out_path)
    lines: list[str] = []
    mode = result.get("mode")
    q = result.get("query") or {}
    lines.append("# SAA Opportunity Set — Shortlist Neighborhood (R-1D)")
    lines.append("")
    lines.append(f"> R-1D schema_version: {R1D_SCHEMA_VERSION}")
    lines.append(
        f"> For each of the {len(q.get('shortlist_ids') or [])} R-1C.1 manager review "
        f"shortlist candidates, list nearest **k = {q.get('k')}** by:"
    )
    lines.append("> - **(A) risk-return distance**: normalized (E[R], σ) L2 in pool std units")
    lines.append("> - **(B) weight similarity distance**: 9-asset raw weight L2 + intra-bucket renormalized L2")
    lines.append(
        "> ref_max_sharpe 는 항상 결과 제외. ref_80_20_equal_intra_bucket 은 옵션."
    )
    lines.append(
        f"> feasible_only={q.get('feasible_only')}, sampled_only={q.get('sampled_only')}"
    )
    lines.append("")

    for sid, entry in (result.get("results") or {}).items():
        lines.append(f"## {sid}")
        lines.append("")
        if entry.get("missing"):
            lines.append(f"> **MISSING**: {entry.get('reason')}")
            lines.append("")
            continue
        t = entry.get("target_summary") or {}
        lines.append(
            f"- target: **{t.get('candidate_id')}** — "
            f"E[R]={_fmt_pct(t.get('expected_return'))}, "
            f"σ={_fmt_pct(t.get('volatility'))}, "
            f"Sharpe={_fmt_num(t.get('sharpe'))}, "
            f"eq={_fmt_pct(t.get('equity_weight'))}, "
            f"fi={_fmt_pct(t.get('fixed_income_weight'))}, "
            f"HHI={_fmt_num(t.get('concentration_hhi'))}, "
            f"max_w={_fmt_pct(t.get('max_asset_weight'))}"
        )
        lines.append("")
        lines.append(f"### {sid} · Nearest by risk-return")
        lines.append("")
        lines.append("| # | candidate_id | distance | E[R] | σ | Sharpe | HHI | max_w | overlap |")
        lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|")
        for i, c in enumerate(entry.get("by_risk_return") or [], 1):
            lines.append(
                f"| {i} | {c['candidate_id']} "
                f"| {_fmt_num(c.get('search_distance'))} "
                f"| {_fmt_pct(c.get('expected_return'))} "
                f"| {_fmt_pct(c.get('volatility'))} "
                f"| {_fmt_num(c.get('sharpe'))} "
                f"| {_fmt_num(c.get('concentration_hhi'))} "
                f"| {_fmt_pct(c.get('max_asset_weight'))} "
                f"| {c.get('overlap_score', 'n/a')} |"
            )
        lines.append("")
        lines.append(f"### {sid} · Nearest by weight similarity")
        lines.append("")
        lines.append("| # | candidate_id | full_L2 | eq_iL2 | fi_iL2 | E[R] | σ | Sharpe | HHI | max_w | overlap |")
        lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for i, c in enumerate(entry.get("by_weights") or [], 1):
            lines.append(
                f"| {i} | {c['candidate_id']} "
                f"| {_fmt_num(c.get('full_weight_l2_distance'))} "
                f"| {_fmt_num(c.get('equity_intra_weight_l2_distance'))} "
                f"| {_fmt_num(c.get('fixed_income_intra_weight_l2_distance'))} "
                f"| {_fmt_pct(c.get('expected_return'))} "
                f"| {_fmt_pct(c.get('volatility'))} "
                f"| {_fmt_num(c.get('sharpe'))} "
                f"| {_fmt_num(c.get('concentration_hhi'))} "
                f"| {_fmt_pct(c.get('max_asset_weight'))} "
                f"| {c.get('overlap_score', 'n/a')} |"
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "> **Note**: 본 산출은 후보 탐색 결과이며 final SAA 자동 선택이 아니다. "
        "운용역이 정성 view 와 함께 검토 후 결정."
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


__all__ = [
    "R1D_SCHEMA_VERSION",
    "SHORTLIST_CANDIDATE_IDS",
    "find_similar_by_risk_return",
    "find_similar_by_weights",
    "build_shortlist_neighborhood",
    "render_search_result_md",
    "render_shortlist_neighborhood_md",
]
