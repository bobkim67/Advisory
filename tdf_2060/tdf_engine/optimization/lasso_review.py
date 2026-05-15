"""R-track 2 post-lasso representative review layer (archetype extraction).

Reads a lasso selection export + opportunity set, extracts representative
archetype candidates from the selected set. **NOT a recommendation engine /**
**NOT a final SAA selection.** Archetypes are review-only categories so 운용역
can compare a manageable handful of representative candidates instead of
inspecting a wide polygon set one by one.

Contract: tdf_2060/docs/r_track_2_lasso_selection_contract.md (selection
schema). This module operates on the selection result, never on raw
production allocation.

Permanent invariants:
  is_production_selection=False, dry_run_only=True,
  implementation_ready=False (strict, propagated from upstream).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import pathlib
from typing import Any, Mapping, Sequence

from tdf_engine.optimization.lasso_selection import compute_cloud_tags


SCHEMA_VERSION = "r_track_2_review.1"

# 7 archetype names (review-only roles, NOT rankings or recommendations)
ARCHETYPES_PRIMARY: tuple[str, ...] = (
    "top_sharpe",
    "min_volatility",
    "max_expected_return",
    "min_hhi",
    "mvo_frontier_near",
    "clean_implementation",
    "medoid_candidate",
)

# Standardized metrics used for medoid (centroid-nearest in z-score space)
MEDOID_METRICS: tuple[str, ...] = (
    "expected_return",
    "volatility",
    "sharpe",
    "concentration_hhi",
    "max_asset_weight",
)


class LassoReviewError(ValueError):
    """Empty selection / invalid lasso export / data resolution failure."""


# ---------- Helpers ----------


def _zscore(values: Sequence[float]) -> list[float]:
    if not values:
        return []
    mu = sum(values) / len(values)
    var = sum((x - mu) ** 2 for x in values) / len(values)
    sd = math.sqrt(var)
    if sd == 0.0:
        return [0.0] * len(values)
    return [(x - mu) / sd for x in values]


def load_lasso_selection(path: pathlib.Path | str) -> dict[str, Any]:
    p = pathlib.Path(path)
    if not p.exists():
        raise LassoReviewError(f"lasso selection JSON not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def resolve_selected_candidates(
    lasso_export: Mapping[str, Any],
    opportunity_set: Mapping[str, Any],
    batch_signals: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Look up full candidate metrics + cloud tags for each selected_candidate_ids.

    Returns enriched candidate dicts (same format as compute_cloud_tags entries),
    filtered to the lasso `selected_candidate_ids`. Missing ids are silently
    dropped — caller may check len() against expected.
    """
    selected_ids = list(lasso_export.get("selected_candidate_ids", []))
    raw_candidates = opportunity_set.get("candidates", [])
    all_tagged = compute_cloud_tags(raw_candidates, batch_signals=batch_signals)
    by_id = {c["candidate_id"]: c for c in all_tagged}
    out: list[dict[str, Any]] = []
    for cid in selected_ids:
        if cid in by_id:
            out.append(by_id[cid])
    return out


# ---------- Medoid ----------


def find_medoid(candidates: Sequence[Mapping[str, Any]]) -> tuple[str | None, float | None]:
    """Z-score-standardized centroid-nearest candidate across MEDOID_METRICS.

    Returns (candidate_id, distance_from_centroid). For len(candidates) == 1,
    returns (id, 0.0). For empty, returns (None, None).
    """
    n = len(candidates)
    if n == 0:
        return None, None
    if n == 1:
        return candidates[0]["candidate_id"], 0.0
    standardized: list[list[float]] = []
    for m in MEDOID_METRICS:
        vals = [float(c[m]) for c in candidates]
        standardized.append(_zscore(vals))
    best_idx = 0
    best_d2 = float("inf")
    for i in range(n):
        d2 = sum(standardized[k][i] ** 2 for k in range(len(MEDOID_METRICS)))
        if d2 < best_d2:
            best_d2 = d2
            best_idx = i
    return candidates[best_idx]["candidate_id"], math.sqrt(best_d2)


# ---------- Archetype extraction ----------


def _make_archetype(
    name: str,
    cand: Mapping[str, Any] | None,
    rationale: str,
    metric_value: float | None,
    reason_if_null: str | None = None,
) -> dict[str, Any]:
    if cand is None:
        return {
            "archetype": name,
            "candidate_id": None,
            "rationale": rationale,
            "metric_value": None,
            "reason_if_null": reason_if_null,
        }
    return {
        "archetype": name,
        "candidate_id": cand["candidate_id"],
        "rationale": rationale,
        "metric_value": metric_value,
        "reason_if_null": None,
    }


def extract_archetypes(candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return per-archetype representative records (7 entries, in ARCHETYPES_PRIMARY order).

    Policy (2026-05-15):
      Candidates with ``has_fallback is True`` are NOT eligible for SAA review
      and are dropped before archetype extraction. Universe warnings are NOT
      considered here — that is a product-selection concern, surfaced as a
      note on the candidate via ``product_universe_note`` cloud label.

    clean_implementation may be null with reason_if_null filled. Other archetypes
    are always populated when at least one eligible candidate remains.

    For ``len(eligible) == 1``, all 7 archetypes point to the single candidate
    (single-review degenerate mode); medoid distance is 0.0.

    Raises LassoReviewError when the input is empty OR when every input
    candidate is excluded by the fallback policy.
    """
    if not candidates:
        raise LassoReviewError(
            "selected_candidate_ids is empty — cannot extract archetypes"
        )

    # Policy filter: drop fallback_used candidates.
    eligible = [c for c in candidates if c.get("has_fallback") is not True]
    if not eligible:
        raise LassoReviewError(
            "all selected candidates have has_fallback=True — none are eligible "
            "for SAA review (policy: fallback_used candidates are excluded)"
        )

    archetypes: list[dict[str, Any]] = []

    # Helpful alias so the existing body below keeps reading naturally.
    candidates = eligible  # type: ignore[assignment]

    top_s = max(candidates, key=lambda c: c["sharpe"])
    archetypes.append(_make_archetype(
        "top_sharpe", top_s, "max sharpe in selection set", float(top_s["sharpe"]),
    ))

    min_v = min(candidates, key=lambda c: c["volatility"])
    archetypes.append(_make_archetype(
        "min_volatility", min_v, "min volatility in selection set", float(min_v["volatility"]),
    ))

    max_e = max(candidates, key=lambda c: c["expected_return"])
    archetypes.append(_make_archetype(
        "max_expected_return", max_e,
        "max expected_return in selection set", float(max_e["expected_return"]),
    ))

    min_h = min(candidates, key=lambda c: c["concentration_hhi"])
    archetypes.append(_make_archetype(
        "min_hhi", min_h, "min concentration_hhi in selection set",
        float(min_h["concentration_hhi"]),
    ))

    mvo_n = min(candidates, key=lambda c: c["mvo_efficiency_score"])
    archetypes.append(_make_archetype(
        "mvo_frontier_near", mvo_n,
        "min mvo_efficiency_score (closest to MVO frontier)",
        float(mvo_n["mvo_efficiency_score"]),
    ))

    # clean_implementation: has_fallback=False (batch only).
    # Policy (2026-05-15): has_universe_warning is NOT a SAA-clean criterion —
    # universe constraints are a product-selection concern, not an SAA one.
    # (Note: candidates with has_fallback=True were already filtered out
    # above, so the eligible set here is at most a mix of False / None.)
    clean = [c for c in candidates if c.get("has_fallback") is False]
    if clean:
        best_clean = max(clean, key=lambda c: c["sharpe"])
        archetypes.append(_make_archetype(
            "clean_implementation", best_clean,
            "max sharpe among eligible candidates with has_fallback=False",
            float(best_clean["sharpe"]),
        ))
    else:
        # Eligible set is entirely None (unknown) after fallback filter — no
        # batch dry-run data to confirm clean status for any candidate.
        reason = (
            "no R-1G.2 batch dry-run data for any eligible candidate "
            "(all has_fallback values are unknown after fallback filter)"
        )
        archetypes.append(_make_archetype(
            "clean_implementation", None,
            "max sharpe among eligible candidates with has_fallback=False",
            None,
            reason_if_null=reason,
        ))

    medoid_id, medoid_dist = find_medoid(candidates)
    if medoid_id is not None:
        medoid_cand = next(c for c in candidates if c["candidate_id"] == medoid_id)
        archetypes.append(_make_archetype(
            "medoid_candidate", medoid_cand,
            "z-score-standardized centroid-nearest across "
            "(expected_return, volatility, sharpe, concentration_hhi, max_asset_weight)",
            medoid_dist,
        ))
    else:
        archetypes.append(_make_archetype(
            "medoid_candidate", None,
            "z-score-standardized centroid-nearest", None,
            reason_if_null="empty candidate set",
        ))

    return archetypes


def dedup_archetypes(archetypes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Group archetypes by candidate_id, preserving multi-role information.

    Returns list of {candidate_id, roles: [str], rationales: [str]} sorted by
    candidate_id. Null-candidate archetypes (e.g., clean_implementation absent)
    are NOT included in dedup — they live in archetypes list only.
    """
    by_id: dict[str, dict[str, Any]] = {}
    for a in archetypes:
        cid = a.get("candidate_id")
        if cid is None:
            continue
        if cid not in by_id:
            by_id[cid] = {"candidate_id": cid, "roles": [], "rationales": []}
        by_id[cid]["roles"].append(a["archetype"])
        by_id[cid]["rationales"].append(a["rationale"])
    return sorted(by_id.values(), key=lambda r: r["candidate_id"])


# ---------- Warning propagation ----------


def _collect_warning_labels(candidates: Sequence[Mapping[str, Any]]) -> list[str]:
    s: set[str] = set()
    for c in candidates:
        for lab in str(c.get("cloud_labels", "")).split(","):
            if "WARN" in lab:
                s.add(lab)
    return sorted(s)


def _per_archetype_warnings(
    archetypes: Sequence[Mapping[str, Any]],
    candidates_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for a in archetypes:
        cid = a.get("candidate_id")
        if cid is None or cid not in candidates_by_id:
            out[a["archetype"]] = []
            continue
        labels = str(candidates_by_id[cid].get("cloud_labels", "")).split(",")
        out[a["archetype"]] = sorted({lab for lab in labels if "WARN" in lab})
    return out


# ---------- Build outputs ----------


def build_review_export(
    *,
    lasso_export: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    archetypes: Sequence[Mapping[str, Any]],
    dedup: Sequence[Mapping[str, Any]],
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Build representative_candidates.json content."""
    if now is None:
        now = dt.datetime.now(dt.timezone.utc)
    iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    selected_count = len(candidates)
    single_review = selected_count == 1
    by_id = {c["candidate_id"]: c for c in candidates}
    selection_level_warns = _collect_warning_labels(candidates)
    per_archetype_warns = _per_archetype_warnings(archetypes, by_id)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso,
        "source_lasso_selection_id": lasso_export.get("selection_id"),
        "source_lasso_selection_file": None,  # filled by CLI when reading from disk
        "source_opportunity_set_path": lasso_export.get("source_opportunity_set_path"),
        "source_opportunity_set_sha256": lasso_export.get("source_opportunity_set_sha256"),
        "selected_count": selected_count,
        "single_review_mode": single_review,
        "archetypes": list(archetypes),
        "representatives": list(dedup),
        "selection_level_warning_labels": selection_level_warns,
        "per_archetype_warning_labels": per_archetype_warns,
        "is_production_selection": False,
        "dry_run_only": True,
        "permanent_invariants": {
            "operating_mode": "relaxed_diagnostic",
            "implementation_ready": False,
            "production_applied": False,
            "manager_override_saa_layer": True,
            "phase_f_entered": False,
        },
        "notes": [
            "Archetypes are review-only roles — NOT a recommendation / ranking / final SAA.",
            "clean_implementation can be null when no R-1G.2 batch data exists or no "
            "candidate clears both has_fallback=False AND has_universe_warning=False.",
            "Multiple archetypes pointing to the same candidate_id are deduplicated in "
            "`representatives`, preserving each role in `roles`.",
            "warning_labels are propagated per-archetype and at the selection level.",
        ],
    }


def build_review_csv(
    candidates: Sequence[Mapping[str, Any]],
    archetypes: Sequence[Mapping[str, Any]],
) -> str:
    """One row per archetype, with metrics looked up for non-null candidates."""
    by_id = {c["candidate_id"]: c for c in candidates}
    cols = [
        "archetype", "candidate_id", "rationale", "metric_value",
        "expected_return", "volatility", "sharpe",
        "concentration_hhi", "max_asset_weight", "mvo_efficiency_score",
        "has_fallback", "has_universe_warning", "cloud_labels",
        "reason_if_null",
    ]
    lines = [",".join(cols)]
    for a in archetypes:
        cid = a.get("candidate_id")
        mv = a.get("metric_value")
        row: list[str] = [
            a["archetype"],
            "" if cid is None else cid,
            _csv_escape(a.get("rationale", "")),
            "" if mv is None else f"{mv:.6f}",
        ]
        if cid is None or cid not in by_id:
            row.extend([""] * 9)
        else:
            c = by_id[cid]
            row.extend([
                f"{c['expected_return']:.6f}",
                f"{c['volatility']:.6f}",
                f"{c['sharpe']:.6f}",
                f"{c['concentration_hhi']:.6f}",
                f"{c['max_asset_weight']:.6f}",
                f"{c['mvo_efficiency_score']:.6f}",
                "" if c.get("has_fallback") is None else str(c["has_fallback"]),
                "" if c.get("has_universe_warning") is None else str(c["has_universe_warning"]),
                _csv_escape(str(c.get("cloud_labels", ""))),
            ])
        row.append(_csv_escape(a.get("reason_if_null") or ""))
        lines.append(",".join(row))
    return "\n".join(lines) + "\n"


def _csv_escape(s: str) -> str:
    if any(ch in s for ch in (",", "\"", "\n")):
        return "\"" + s.replace("\"", "\"\"") + "\""
    return s


def build_review_md(
    review_export: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
) -> str:
    by_id = {c["candidate_id"]: c for c in candidates}
    n = review_export["selected_count"]
    single = review_export["single_review_mode"]
    lines = [
        "# Lasso Representative Review (C-4 archetype extraction)",
        "",
        f"> **Review-only.** Archetypes are categories for 운용역 inspection,",
        f"> NOT a recommendation / ranking / final SAA selection.",
        f"> `is_production_selection=False`, `dry_run_only=True`.",
        "",
        f"- source lasso selection_id: `{review_export.get('source_lasso_selection_id')}`",
        f"- selected_count: **{n}**",
        f"- mode: **{'single-review (degenerate)' if single else 'archetype-extraction'}**",
        f"- generated_at: `{review_export['generated_at']}`",
        "",
    ]
    sl_warn = review_export.get("selection_level_warning_labels", [])
    if sl_warn:
        lines.append("## Selection-level WARN")
        for w in sl_warn:
            lines.append(f"- `{w}`")
        lines.append("")

    lines.append("## Archetypes")
    lines.append("")
    lines.append("| archetype | candidate_id | metric | rationale | per-archetype WARN |")
    lines.append("|---|---|---:|---|---|")
    per_arch_warn = review_export.get("per_archetype_warning_labels", {})
    for a in review_export["archetypes"]:
        cid = a.get("candidate_id") or "(null)"
        mv = a.get("metric_value")
        mv_str = "" if mv is None else f"{mv:.4f}"
        warns = per_arch_warn.get(a["archetype"], [])
        warn_str = ", ".join(warns) if warns else "—"
        lines.append(
            f"| `{a['archetype']}` | `{cid}` | {mv_str} | {a['rationale']} | {warn_str} |"
        )
    lines.append("")

    null_arches = [a for a in review_export["archetypes"] if a.get("candidate_id") is None]
    if null_arches:
        lines.append("## Null archetypes (no candidate satisfies)")
        for a in null_arches:
            lines.append(f"- `{a['archetype']}` — {a.get('reason_if_null','')}")
        lines.append("")

    lines.append("## Representatives (dedup by candidate_id)")
    lines.append("")
    if not review_export["representatives"]:
        lines.append("(none)")
    else:
        lines.append("| candidate_id | roles | E[R] | σ | Sharpe | HHI | max_w |")
        lines.append("|---|---|---:|---:|---:|---:|---:|")
        for r in review_export["representatives"]:
            cid = r["candidate_id"]
            c = by_id.get(cid, {})
            roles = ", ".join(r["roles"])
            lines.append(
                f"| `{cid}` | {roles} | "
                f"{c.get('expected_return',0)*100:.2f}% | "
                f"{c.get('volatility',0)*100:.2f}% | "
                f"{c.get('sharpe',0):.4f} | "
                f"{c.get('concentration_hhi',0):.4f} | "
                f"{c.get('max_asset_weight',0)*100:.2f}% |"
            )
    lines.append("")

    lines.append("## Permanent invariants")
    lines.append("")
    inv = review_export["permanent_invariants"]
    for k in ("operating_mode", "implementation_ready", "production_applied",
              "manager_override_saa_layer", "phase_f_entered"):
        lines.append(f"- `{k}`: `{inv[k]}`")
    lines.append("")
    return "\n".join(lines)
