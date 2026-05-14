"""R-track 2 lasso/polygon candidate selection (schema export only).

Contract: tdf_2060/docs/r_track_2_lasso_selection_contract.md

본 모듈은 SAA opportunity set scatter plot 위에서 운용역이 lasso/polygon 으로
그린 영역의 candidate_id 들을 추출하여 downstream R-1F.1 yaml 입력으로 변환하는
rule-based EXPORT 파이프라인. **자동 candidate 추천 / final SAA 라벨 /**
**production-ready 라벨 / Phase F 진입 선언 모두 본 모듈에서 발생하지 않는다.**

영구 invariant (코드에서 강제):
- `is_production_selection = False`
- `dry_run_only = True`
- `selected_by` 가 "automated" / "smoke" / "r1f1_smoke_test" 류 substring 을
  포함하면 `SelectionConfigError` 로 거부.
- React UI 본구현 / 백엔드 endpoint 미포함 (별도 작업).
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import pathlib
import uuid
from typing import Any, Mapping, Sequence


# ---------- Schema / catalogs ----------

SCHEMA_VERSION = "r_track_2_lasso.1"

ASSETS: tuple[str, ...] = (
    "kr_equity",
    "us_growth_equity",
    "us_value_equity",
    "dm_ex_us_equity",
    "em_equity",
    "kr_aggregate_bond",
    "kr_treasury_10y",
    "us_treasury_30y",
    "us_high_yield",
)

DECILE_TOP = 90.0
DECILE_BOT = 10.0
CORNER_THRESHOLD = 0.50
DEFAULT_CORE_SATELLITE = 3

SELECTION_MODES = frozenset({"lasso", "rectangle", "cloud_click", "manual_candidate_pick"})
POST_SELECTION_RULES = frozenset({"all", "top_sharpe", "min_hhi", "top_n_by_metric", "representative_3"})
PORTFOLIO_TYPES = frozenset({"etf", "fund"})

VALID_METRICS = frozenset({
    "expected_return",
    "volatility",
    "sharpe",
    "concentration_hhi",
    "max_asset_weight",
    "mvo_efficiency_score",
    "equity_intra_hhi",
    "fixed_income_intra_hhi",
    "equity_weight",
    "fixed_income_weight",
})

FORBIDDEN_SELECTED_BY_SUBSTRINGS = ("automated", "smoke", "r1f1_smoke_test")


# ---------- Errors ----------


class PolygonError(ValueError):
    """Polygon validation failure (too few vertices / self-intersection)."""


class SelectionConfigError(ValueError):
    """Invalid selection mode / rule / metric / filter / selected_by."""


# ---------- Stats helpers ----------


def _percentile(values: Sequence[float], pct: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    k = (len(s) - 1) * (pct / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    frac = k - lo
    return s[lo] * (1 - frac) + s[hi] * frac


# ---------- Cloud tag computation ----------


@dataclasses.dataclass(frozen=True)
class DecileThresholds:
    sharpe_top: float
    er_top: float
    vol_low: float
    hhi_high: float
    hhi_low: float
    maxw_top: float
    maxw_low: float
    mvo_frontier_near: float
    eq_intra_low: float
    fi_intra_low: float


def compute_decile_thresholds(candidates: Sequence[Mapping[str, Any]]) -> DecileThresholds:
    sharpes = [c["sharpe"] for c in candidates]
    er = [c["expected_return"] for c in candidates]
    vols = [c["volatility"] for c in candidates]
    hhi = [c["concentration_hhi"] for c in candidates]
    maxw = [c["max_asset_weight"] for c in candidates]
    mvo = [c["mvo_efficiency_score"] for c in candidates]
    eq_intra = [c["equity_intra_hhi"] for c in candidates]
    fi_intra = [c["fixed_income_intra_hhi"] for c in candidates]
    return DecileThresholds(
        sharpe_top=_percentile(sharpes, DECILE_TOP),
        er_top=_percentile(er, DECILE_TOP),
        vol_low=_percentile(vols, DECILE_BOT),
        hhi_high=_percentile(hhi, DECILE_TOP),
        hhi_low=_percentile(hhi, DECILE_BOT),
        maxw_top=_percentile(maxw, DECILE_TOP),
        maxw_low=_percentile(maxw, DECILE_BOT),
        mvo_frontier_near=_percentile(mvo, DECILE_BOT),
        eq_intra_low=_percentile(eq_intra, DECILE_BOT),
        fi_intra_low=_percentile(fi_intra, DECILE_BOT),
    )


def compute_cloud_tags(
    candidates: Sequence[Mapping[str, Any]],
    batch_signals: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Compute per-candidate cloud tags + overlap_score + cloud_labels.

    See contract §3 for tag definitions.

    batch_signals (optional): map candidate_id -> {has_fallback: bool,
        has_universe_warning: bool, universe_warn_assets: str}. Candidates
        not present in this map receive has_fallback=None, has_universe_warning=None
        (treated as UNKNOWN, distinct from False).
    """
    th = compute_decile_thresholds(candidates)
    out: list[dict[str, Any]] = []
    for c in candidates:
        cid = c["candidate_id"]
        s = c["sharpe"]
        e = c["expected_return"]
        v = c["volatility"]
        h = c["concentration_hhi"]
        m = c["mvo_efficiency_score"]
        mw = c["max_asset_weight"]
        eh = c["equity_intra_hhi"]
        fh = c["fixed_income_intra_hhi"]

        is_sharpe_top = s >= th.sharpe_top
        is_return_top = e >= th.er_top
        is_low_vol = v <= th.vol_low
        is_hhi_high = h >= th.hhi_high
        is_hhi_low = h <= th.hhi_low
        is_concentration_high = mw >= th.maxw_top
        is_mvo_frontier_near = m <= th.mvo_frontier_near
        is_corner_like = (
            mw > CORNER_THRESHOLD
            or h > CORNER_THRESHOLD
            or eh > CORNER_THRESHOLD
            or fh > CORNER_THRESHOLD
        )

        overlap_score = (
            int(s >= th.sharpe_top)
            + int(m <= th.mvo_frontier_near)
            + int(h <= th.hhi_low)
            + int(eh <= th.eq_intra_low)
            + int(fh <= th.fi_intra_low)
            + int(mw <= th.maxw_low)
        )

        has_fallback: bool | None
        has_universe_warning: bool | None
        if batch_signals and cid in batch_signals:
            b = batch_signals[cid]
            has_fallback = bool(b.get("has_fallback", False))
            has_universe_warning = bool(b.get("has_universe_warning", False))
            universe_warn_assets = str(b.get("universe_warn_assets", ""))
        else:
            has_fallback = None
            has_universe_warning = None
            universe_warn_assets = ""

        labels: list[str] = []
        if is_sharpe_top:
            labels.append("sharpe_top")
        if is_return_top:
            labels.append("return_top")
        if is_low_vol:
            labels.append("low_vol")
        if is_hhi_high:
            labels.append("hhi_high_WARN")
        if is_hhi_low:
            labels.append("hhi_low")
        if is_concentration_high:
            labels.append("concentration_high_WARN")
        if is_mvo_frontier_near:
            labels.append("mvo_frontier_near")
        if is_corner_like:
            labels.append("corner_like_WARN")
        if has_fallback is True:
            labels.append("fallback_WARN")
        if has_universe_warning is True:
            labels.append("universe_WARN")

        out.append({
            "candidate_id": cid,
            "expected_return": e,
            "volatility": v,
            "sharpe": s,
            "equity_weight": c.get("equity_weight", float("nan")),
            "fixed_income_weight": c.get("fixed_income_weight", float("nan")),
            "concentration_hhi": h,
            "max_asset_weight": mw,
            "equity_intra_hhi": eh,
            "fixed_income_intra_hhi": fh,
            "mvo_efficiency_score": m,
            "feasibility_status": c.get("feasibility_status", "unknown"),
            "weights": dict(c.get("weights", {})),
            "overlap_score": overlap_score,
            "is_sharpe_top": is_sharpe_top,
            "is_return_top": is_return_top,
            "is_low_vol": is_low_vol,
            "is_hhi_high": is_hhi_high,
            "is_hhi_low": is_hhi_low,
            "is_concentration_high": is_concentration_high,
            "is_mvo_frontier_near": is_mvo_frontier_near,
            "is_corner_like": is_corner_like,
            "has_fallback": has_fallback,
            "has_universe_warning": has_universe_warning,
            "universe_warn_assets": universe_warn_assets,
            "cloud_labels": ",".join(labels),
        })
    return out


# ---------- Polygon ----------


def _segments_intersect(
    p1: Sequence[float],
    p2: Sequence[float],
    p3: Sequence[float],
    p4: Sequence[float],
) -> bool:
    """True if open segments p1-p2 and p3-p4 properly cross (endpoints excluded)."""
    def ccw(a: Sequence[float], b: Sequence[float], c: Sequence[float]) -> float:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    d1 = ccw(p3, p4, p1)
    d2 = ccw(p3, p4, p2)
    d3 = ccw(p1, p2, p3)
    d4 = ccw(p1, p2, p4)

    return (
        ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0))
        and ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))
    )


def validate_polygon(points: Sequence[Sequence[float]]) -> None:
    """Reject polygons with < 3 vertices or self-intersecting edges.

    Raises:
        PolygonError on violation.
    """
    n = len(points)
    if n < 3:
        raise PolygonError(f"polygon requires >= 3 vertices, got {n}")
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                # Adjacent through wraparound; skip
                continue
            p1, p2 = points[i], points[(i + 1) % n]
            p3, p4 = points[j], points[(j + 1) % n]
            if _segments_intersect(p1, p2, p3, p4):
                raise PolygonError(
                    f"polygon edges {i}-{(i+1)%n} and {j}-{(j+1)%n} intersect"
                )


def point_in_polygon(x: float, y: float, polygon: Sequence[Sequence[float]]) -> bool:
    """Ray-casting point-in-polygon. Boundary points included."""
    n = len(polygon)
    # Boundary check first
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        cross = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
        if abs(cross) < 1e-12:
            if (
                min(x1, x2) - 1e-12 <= x <= max(x1, x2) + 1e-12
                and min(y1, y2) - 1e-12 <= y <= max(y1, y2) + 1e-12
            ):
                return True

    # Ray-casting
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > y) != (yj > y):
            x_intersect = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_intersect:
                inside = not inside
        j = i
    return inside


# ---------- Selection / filters ----------


def _matches_filters(c: Mapping[str, Any], filters: Mapping[str, Any]) -> bool:
    """Apply filter dict to candidate. Supported keys:

    - "feasibility_status": str — exact match
    - "min_overlap_score": int — >=
    - "max_overlap_score": int — <=
    - "min_<metric>" / "max_<metric>" for any VALID_METRICS
    - "require_tag_<tag>" — tag (is_X) must be True
    - "manual_ids": list[str] — used by manual_candidate_pick mode only
    """
    for key, want in filters.items():
        if key == "feasibility_status":
            if c.get("feasibility_status") != want:
                return False
        elif key == "min_overlap_score":
            if c.get("overlap_score", 0) < want:
                return False
        elif key == "max_overlap_score":
            if c.get("overlap_score", 0) > want:
                return False
        elif key == "manual_ids":
            # consumed elsewhere
            continue
        elif key.startswith("min_"):
            metric = key[4:]
            if metric not in VALID_METRICS:
                raise SelectionConfigError(f"unknown filter metric: {metric}")
            if c.get(metric, float("-inf")) < want:
                return False
        elif key.startswith("max_"):
            metric = key[4:]
            if metric not in VALID_METRICS:
                raise SelectionConfigError(f"unknown filter metric: {metric}")
            if c.get(metric, float("inf")) > want:
                return False
        elif key.startswith("require_tag_"):
            tag = "is_" + key[len("require_tag_"):]
            if not c.get(tag, False):
                return False
        else:
            raise SelectionConfigError(f"unknown filter key: {key}")
    return True


def select_in_polygon(
    candidates: Sequence[Mapping[str, Any]],
    polygon: Sequence[Sequence[float]],
    *,
    x_metric: str,
    y_metric: str,
    active_filters: Mapping[str, Any] | None = None,
) -> list[Mapping[str, Any]]:
    """Filter candidates then keep those inside polygon (boundary included)."""
    if x_metric not in VALID_METRICS:
        raise SelectionConfigError(f"invalid x_metric: {x_metric}")
    if y_metric not in VALID_METRICS:
        raise SelectionConfigError(f"invalid y_metric: {y_metric}")
    validate_polygon(polygon)
    filters = dict(active_filters or {})
    out: list[Mapping[str, Any]] = []
    for c in candidates:
        if not _matches_filters(c, filters):
            continue
        x = c.get(x_metric)
        y = c.get(y_metric)
        if x is None or y is None:
            continue
        if point_in_polygon(float(x), float(y), polygon):
            out.append(c)
    return out


# ---------- Post-selection rules ----------


def apply_post_selection_rule(
    selected: Sequence[Mapping[str, Any]],
    rule: str,
    params: Mapping[str, Any] | None = None,
) -> list[Mapping[str, Any]]:
    """Narrow selected set via rule.

    Note: rule-based EXPORT, NOT automated recommendation. Final SAA selection
    requires 운용역 명시 input via R-1F.1 yaml. See contract §7.
    """
    if rule not in POST_SELECTION_RULES:
        raise SelectionConfigError(f"unknown post_selection_rule: {rule}")
    if not selected:
        return []
    if rule == "all":
        return list(selected)
    if rule == "top_sharpe":
        return [max(selected, key=lambda c: c["sharpe"])]
    if rule == "min_hhi":
        return [min(selected, key=lambda c: c["concentration_hhi"])]
    if rule == "top_n_by_metric":
        p = dict(params or {})
        metric = p.get("metric", "sharpe")
        if metric not in VALID_METRICS:
            raise SelectionConfigError(f"invalid metric for top_n_by_metric: {metric}")
        n = int(p.get("n", 3))
        descending = bool(p.get("descending", True))
        sorted_ = sorted(selected, key=lambda c: c[metric], reverse=descending)
        return sorted_[:n]
    if rule == "representative_3":
        # 3 named axes: max sharpe / min hhi / min max_asset_weight (deterministic).
        picks: list[Mapping[str, Any]] = []
        seen: set[str] = set()
        sort_keys = (
            ("max sharpe", lambda c: -c["sharpe"]),
            ("min hhi", lambda c: c["concentration_hhi"]),
            ("min max_w", lambda c: c["max_asset_weight"]),
        )
        for _name, key_fn in sort_keys:
            for c in sorted(selected, key=key_fn):
                if c["candidate_id"] not in seen:
                    picks.append(c)
                    seen.add(c["candidate_id"])
                    break
        return picks
    return []  # unreachable


# ---------- Export ----------


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _collect_warning_labels(selected_before_rule: Sequence[Mapping[str, Any]]) -> list[str]:
    s: set[str] = set()
    for c in selected_before_rule:
        labels = c.get("cloud_labels", "")
        if not labels:
            continue
        for lab in labels.split(","):
            if "WARN" in lab:
                s.add(lab)
    return sorted(s)


def _validate_selected_by(selected_by: str) -> None:
    if not selected_by or not selected_by.strip():
        raise SelectionConfigError("selected_by must be non-empty")
    lower = selected_by.lower()
    for sub in FORBIDDEN_SELECTED_BY_SUBSTRINGS:
        if sub in lower:
            raise SelectionConfigError(
                f"selected_by contains forbidden substring '{sub}': {selected_by!r}"
            )


def build_export(
    *,
    candidates_with_tags: Sequence[Mapping[str, Any]],
    opportunity_set_path: pathlib.Path | str,
    opportunity_set_sha256: str,
    polygon_points: Sequence[Sequence[float]],
    x_metric: str,
    y_metric: str,
    active_overlays: Sequence[str],
    active_filters: Mapping[str, Any],
    selection_mode: str,
    post_selection_rule: str,
    post_selection_params: Mapping[str, Any] | None,
    selected_by: str,
    selection_reason: str,
    now: dt.datetime | None = None,
    selection_id: str | None = None,
) -> dict[str, Any]:
    """Build lasso selection export dict (schema_version r_track_2_lasso.1).

    is_production_selection=False and dry_run_only=True are forced.
    selected_by must not contain forbidden substrings (see FORBIDDEN_SELECTED_BY_SUBSTRINGS).
    """
    if selection_mode not in SELECTION_MODES:
        raise SelectionConfigError(f"invalid selection_mode: {selection_mode}")
    if post_selection_rule not in POST_SELECTION_RULES:
        raise SelectionConfigError(f"invalid post_selection_rule: {post_selection_rule}")
    _validate_selected_by(selected_by)

    filters = dict(active_filters or {})

    if selection_mode in ("lasso", "rectangle"):
        selected_before_rule = select_in_polygon(
            candidates_with_tags,
            polygon_points,
            x_metric=x_metric,
            y_metric=y_metric,
            active_filters=filters,
        )
    elif selection_mode == "cloud_click":
        if not active_overlays:
            raise SelectionConfigError("cloud_click requires at least one active_overlay tag")
        selected_before_rule = [
            c for c in candidates_with_tags
            if _matches_filters(c, filters)
            and all(c.get(tag, False) for tag in active_overlays)
        ]
    elif selection_mode == "manual_candidate_pick":
        wanted_ids = set(filters.get("manual_ids", []))
        if not wanted_ids:
            raise SelectionConfigError("manual_candidate_pick requires active_filters['manual_ids']")
        selected_before_rule = [
            c for c in candidates_with_tags if c["candidate_id"] in wanted_ids
        ]
    else:
        raise SelectionConfigError(f"unhandled selection_mode: {selection_mode}")

    final = apply_post_selection_rule(selected_before_rule, post_selection_rule, post_selection_params)
    warning_labels = _collect_warning_labels(selected_before_rule)

    if now is None:
        now = dt.datetime.now(dt.timezone.utc)
    iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    if selection_id is None:
        selection_id = f"lasso_{now.strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"

    opp_path_str = str(opportunity_set_path).replace("\\", "/")

    return {
        "schema_version": SCHEMA_VERSION,
        "selection_id": selection_id,
        "created_at": iso,
        "source_opportunity_set_path": opp_path_str,
        "source_opportunity_set_sha256": opportunity_set_sha256,
        "coordinate_system": {
            "x_metric": x_metric,
            "y_metric": y_metric,
            "x_unit": "decimal",
            "y_unit": "decimal",
        },
        "x_metric": x_metric,
        "y_metric": y_metric,
        "polygon_points": [[float(p[0]), float(p[1])] for p in polygon_points],
        "active_overlays": list(active_overlays),
        "active_filters": dict(filters),
        "selection_mode": selection_mode,
        "post_selection_rule": post_selection_rule,
        "post_selection_params": dict(post_selection_params or {}),
        "selected_candidate_ids_before_rule": [c["candidate_id"] for c in selected_before_rule],
        "selected_candidate_ids": [c["candidate_id"] for c in final],
        "selected_count_before_rule": len(selected_before_rule),
        "selected_count": len(final),
        "warning_labels": warning_labels,
        "is_production_selection": False,
        "dry_run_only": True,
        "selected_by": selected_by,
        "selection_reason": selection_reason,
        "permanent_invariants": {
            "operating_mode": "relaxed_diagnostic",
            "implementation_ready": False,
            "production_applied": False,
            "manager_override_saa_layer": True,
            "phase_f_entered": False,
        },
        "notes": [
            "Lasso/polygon selection is a rule-based EXPORT, not an automated recommendation.",
            "Final SAA selection requires 운용역 명시 input via R-1F.1 yaml schema.",
            "WARN labels propagated from candidates inside polygon (before post_selection_rule).",
        ],
    }


# ---------- R-1F.1 yaml conversion ----------


def to_r1f1_yaml(
    export: Mapping[str, Any],
    *,
    portfolio_type: str = "etf",
    source_review_packet_path: str = "",
    source_review_packet_sha256: str = "",
    require_single_candidate: bool = True,
) -> str:
    """Convert lasso export → R-1F.1 manager_selected_saa yaml string.

    Single-candidate flow only (require_single_candidate=True default). For
    multi-candidate batch (top_n / representative_3 / all > 1), use R-1I
    batch flow separately.
    """
    if portfolio_type not in PORTFOLIO_TYPES:
        raise SelectionConfigError(f"invalid portfolio_type: {portfolio_type}")

    ids = list(export.get("selected_candidate_ids", []))
    if require_single_candidate and len(ids) != 1:
        raise SelectionConfigError(
            f"to_r1f1_yaml requires exactly 1 selected candidate, got {len(ids)} "
            f"(post_selection_rule={export.get('post_selection_rule')})"
        )

    cand_id = ids[0] if ids else ""
    sel_id = export.get("selection_id", "")
    overlays = ", ".join(export.get("active_overlays", []))
    warn = list(export.get("warning_labels", []))
    n_before = int(export.get("selected_count_before_rule", 0))
    rule = export.get("post_selection_rule", "")
    opp_path = export.get("source_opportunity_set_path", "")
    opp_sha = export.get("source_opportunity_set_sha256", "")

    lines: list[str] = [
        "# Manager Selection Input — derived from lasso selection",
        f"# source_selection_id: {sel_id}",
        f"# generated_at:        {export.get('created_at','')}",
        "# 영구 라벨: production_applied=false, dry_run_only=true,",
        "#           implementation_ready=false (strict).",
        "",
        "schema_version: r1f1.1",
        "",
        "selection_input:",
        f"  portfolio_type: {portfolio_type}",
        f"  candidate_id: \"{cand_id}\"",
        f"  selected_by: \"{_yaml_escape(str(export.get('selected_by','')))}\"",
        f"  selected_at: \"{export.get('created_at','')}\"",
        "  selection_reason: |",
    ]
    reason = str(export.get("selection_reason", ""))
    for line in (reason.splitlines() or [""]):
        lines.append(f"    {line}")
    lines.extend([
        "  manager_view_notes:",
        f"    - \"source: lasso selection {sel_id}\"",
        f"    - \"selected before rule: {n_before} candidates / post_rule = {rule} -> 1\"",
        f"    - \"active_overlays at selection: {_yaml_escape(overlays)}\"",
    ])
    for w in warn:
        lines.append(f"    - \"WARN from selection set: {w}\"")
    lines.extend([
        "  source_review_packet:",
        f"    path: \"{_yaml_escape(source_review_packet_path)}\"",
        f"    sha256: \"{source_review_packet_sha256}\"",
        "  allow_downstream_dry_run: true",
        "",
        "meta:",
        "  operating_mode: relaxed_diagnostic",
        "  production_applied: false",
        "  sign_off_required_for_production: true",
        "  manager_override_saa_layer: true",
        "  scope: \"R-1F.1 (manager selection input from lasso)\"",
        "",
        "phase_f_entry_status:",
        "  manager_signoff_recorded: false",
        "  candidate_finalized: false",
        "  r1g2_outcome_accepted: false",
        "  decision_register_d15_added: false",
        "  production_gate_confirmed: false",
        "  operating_mode_transition_signoff: false",
        "",
        "provenance:",
        f"  source_lasso_selection_id: \"{sel_id}\"",
        f"  source_opportunity_set_path: \"{opp_path}\"",
        f"  source_opportunity_set_sha256: \"{opp_sha}\"",
        f"  selected_count_before_rule: {n_before}",
        f"  post_selection_rule: \"{rule}\"",
        "",
    ])
    return "\n".join(lines)


def _yaml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("\"", "\\\"")
