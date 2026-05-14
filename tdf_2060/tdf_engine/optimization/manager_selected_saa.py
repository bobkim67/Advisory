"""R-1F.1 — Manager-Selected SAA validation + JSON dump (read-only).

Spec: tdf_2060/docs/r1e_manager_selected_saa_dry_run_spec.md (§3 V-1 ~ V-16,
§4 Output schema, §8.1 default implementation choices).

R-1F.1 scope:
- Validate manager selection input against opportunity_set JSON
- Dump validated selection to `manager_selected_saa_{type}_{as_of}.json`
- production_applied: false (always)
- manager_override_saa_layer: true (separate from existing SAA telemetry)
- NO downstream wiring (TAA / projection / product selection) — R-1F.2 범위.

Hard requirements:
- 기존 SAA telemetry 덮어쓰기 금지 → manager_override_saa 별도 layer
- ref_max_sharpe / ref_80_20_equal_intra_bucket 선택 차단
- 80:20 distance metric 부활 금지 (R-1B.2 정합)
- production_applied: false / downstream_dry_run_executed: false 단언
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


SCHEMA_VERSION = "r1f1.1"

REQUIRED_SELECTION_FIELDS = (
    "portfolio_type",
    "candidate_id",
    "selected_by",
    "selected_at",
    "selection_reason",
    "source_review_packet",
    "allow_downstream_dry_run",
)

# R-1B.2 hard constraint
EQUITY_TOTAL = 0.80
FIXED_INCOME_TOTAL = 0.20
BUCKET_TOL = 1e-9
WEIGHT_SUM_TOL = 1e-9
NEGATIVE_TOL = -1e-12  # treat tiny negative noise as zero

REMOVED_METRIC_KEYS = (
    "bucket_distance_from_80_20",
    "full_weight_distance_from_80_20_equal_bucket_reference",
)

REF_NON_SELECTABLE_IDS = (
    "ref_max_sharpe",
    "ref_80_20_equal_intra_bucket",
)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_selection_yaml(path: Path) -> dict[str, Any]:
    """Load selection YAML and return the inner `manager_selection` dict.

    Supports both single (top-level `manager_selection`) and set forms
    (`manager_selection_set` — list of selections). The set form is returned
    as-is; the caller routes per portfolio_type.
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"selection yaml at {path} did not parse to a dict.")
    if "manager_selection_set" in raw:
        sel_set = raw["manager_selection_set"]
        if not isinstance(sel_set, list) or not sel_set:
            raise ValueError("manager_selection_set must be a non-empty list.")
        return {"manager_selection_set": sel_set}
    sel = raw.get("manager_selection")
    if sel is None:
        raise ValueError(
            "selection yaml requires top-level `manager_selection` (single) "
            "or `manager_selection_set` (list)."
        )
    return {"manager_selection": sel}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _find_candidate(
    opportunity_payload: dict[str, Any], candidate_id: str
) -> dict[str, Any] | None:
    for c in opportunity_payload.get("candidates") or []:
        if c.get("candidate_id") == candidate_id:
            return c
    return None


def _parse_iso(dt_str: str) -> datetime:
    # tolerate trailing Z
    s = str(dt_str)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def _check_required_fields(selection: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_SELECTION_FIELDS if k not in selection]
    if missing:
        raise ValueError(
            f"R-1F.1 selection input missing required fields: {missing}"
        )
    src = selection["source_review_packet"]
    if not isinstance(src, dict) or "path" not in src or "sha256" not in src:
        raise ValueError(
            "selection.source_review_packet must have keys: path, sha256"
        )


def _check_portfolio_type(selection: dict[str, Any], opportunity_payload: dict[str, Any]) -> None:
    sel_type = str(selection.get("portfolio_type") or "")
    if sel_type not in ("etf", "fund"):
        raise ValueError(
            f"portfolio_type must be 'etf' or 'fund', got {sel_type!r}"
        )
    opp_type = str((opportunity_payload.get("meta") or {}).get("product_type") or "")
    if opp_type and opp_type != sel_type:
        raise ValueError(
            f"portfolio_type mismatch: selection={sel_type!r}, "
            f"opportunity_set meta.product_type={opp_type!r}"
        )


def _check_identity(
    selection: dict[str, Any], opportunity_payload: dict[str, Any]
) -> dict[str, Any]:
    """V-1 ~ V-4."""
    cid = str(selection["candidate_id"])
    # V-3, V-4: explicit reference block
    if cid in REF_NON_SELECTABLE_IDS:
        if cid == "ref_max_sharpe":
            raise ValueError(
                "V-3: ref_max_sharpe is unconstrained MVO reference; not selectable."
            )
        if cid == "ref_80_20_equal_intra_bucket":
            raise ValueError(
                "V-4: reference anchor ref_80_20_equal_intra_bucket not selectable as final SAA."
            )
    # V-2: must be sampled (id pattern)
    if not cid.startswith("cand_"):
        raise ValueError(
            f"V-2: candidate_id {cid!r} is not a sampled candidate "
            "(reference points / non-cand IDs are not selectable)."
        )
    # V-1: must exist in candidates
    cand = _find_candidate(opportunity_payload, cid)
    if cand is None:
        raise ValueError(
            f"V-1: candidate_id {cid!r} not found in opportunity set "
            f"({len(opportunity_payload.get('candidates') or [])} candidates)."
        )
    return cand


def _check_bucket_and_weights(
    candidate: dict[str, Any], opportunity_payload: dict[str, Any]
) -> dict[str, Any]:
    """V-5 ~ V-9. Returns measurement dict for validation_summary."""
    feas = str(candidate.get("feasibility_status") or "")
    if feas != "feasible":
        raise ValueError(
            f"V-5: candidate.feasibility_status={feas!r}; must be 'feasible'."
        )
    eq = float(candidate.get("equity_weight") or 0.0)
    fi = float(candidate.get("fixed_income_weight") or 0.0)
    if abs(eq - EQUITY_TOTAL) > BUCKET_TOL:
        raise ValueError(
            f"V-6: bucket constraint violated: equity_weight={eq}, "
            f"expected {EQUITY_TOTAL} (tol {BUCKET_TOL})."
        )
    if abs(fi - FIXED_INCOME_TOTAL) > BUCKET_TOL:
        raise ValueError(
            f"V-7: bucket constraint violated: fixed_income_weight={fi}, "
            f"expected {FIXED_INCOME_TOTAL} (tol {BUCKET_TOL})."
        )
    asset_keys = list((opportunity_payload.get("inputs") or {}).get("asset_keys") or [])
    weights = candidate.get("weights") or {}
    sum_w = sum(float(weights.get(k, 0.0)) for k in asset_keys)
    if abs(sum_w - 1.0) > WEIGHT_SUM_TOL:
        raise ValueError(
            f"V-8: weights sum {sum_w} not in [1 ± {WEIGHT_SUM_TOL}]."
        )
    for k in asset_keys:
        w = float(weights.get(k, 0.0))
        if w < NEGATIVE_TOL:
            raise ValueError(
                f"V-9: negative weight for {k}: {w} (tol {NEGATIVE_TOL})."
            )
    return {
        "equity_deviation_from_080": abs(eq - EQUITY_TOTAL),
        "fixed_income_deviation_from_020": abs(fi - FIXED_INCOME_TOTAL),
        "weight_sum_deviation_from_1": abs(sum_w - 1.0),
    }


def _check_removed_metrics(candidate: dict[str, Any]) -> None:
    """V-10."""
    for k in REMOVED_METRIC_KEYS:
        if k in candidate:
            raise ValueError(
                f"V-10: removed metric {k!r} resurrected in candidate — schema regression."
            )


def _check_review_packet_sha256(selection: dict[str, Any]) -> str:
    """V-11 strict (OD-6 default). Returns actual sha256."""
    src = selection["source_review_packet"]
    path = Path(str(src["path"]))
    expected = str(src["sha256"])
    if not path.exists():
        raise ValueError(
            f"V-11: source_review_packet path not found: {path}"
        )
    actual = _sha256_file(path)
    if actual != expected:
        raise ValueError(
            f"V-11: review packet sha256 mismatch — stale or modified.\n"
            f"  expected: {expected}\n"
            f"  actual:   {actual}\n"
            f"  path:     {path}"
        )
    return actual


def _check_timestamp_ordering(
    selection: dict[str, Any], opportunity_payload: dict[str, Any]
) -> None:
    """V-12. selected_at >= opportunity_set.meta.generated_at."""
    sel_at_raw = selection["selected_at"]
    opp_at_raw = (opportunity_payload.get("meta") or {}).get("generated_at")
    if not opp_at_raw:
        raise ValueError(
            "V-12: opportunity_set.meta.generated_at missing — cannot enforce ordering."
        )
    try:
        sel_at = _parse_iso(sel_at_raw)
        opp_at = _parse_iso(opp_at_raw)
    except (TypeError, ValueError) as e:
        raise ValueError(f"V-12: failed to parse timestamp: {e}")
    if sel_at < opp_at:
        raise ValueError(
            f"V-12: selected_at ({sel_at_raw}) predates opportunity_set "
            f"generated_at ({opp_at_raw})."
        )


def _check_non_empty(selection: dict[str, Any]) -> None:
    """V-13, V-14."""
    if not str(selection.get("selected_by") or "").strip():
        raise ValueError("V-13: selected_by required (non-empty).")
    if not str(selection.get("selection_reason") or "").strip():
        raise ValueError("V-14: selection_reason required (non-empty).")


def _check_allow_dry_run(selection: dict[str, Any]) -> None:
    """V-15."""
    flag = selection.get("allow_downstream_dry_run")
    if flag is not True:
        raise ValueError(
            "V-15: allow_downstream_dry_run must be true to dump manager_selected_saa JSON."
        )


def _check_operating_mode(operating_mode: str) -> None:
    """V-16."""
    if operating_mode != "relaxed_diagnostic":
        raise ValueError(
            f"V-16: R-1F.1 dry-run forbidden in operating_mode={operating_mode!r}; "
            "require 'relaxed_diagnostic'."
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_selection(
    selection: dict[str, Any],
    opportunity_payload: dict[str, Any],
    *,
    operating_mode: str = "relaxed_diagnostic",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run V-1 ~ V-16 fail-fast.

    Returns (selected_candidate_dict, validation_summary_dict) when all pass.
    Raises ValueError on first failed rule.
    """
    _check_required_fields(selection)
    _check_portfolio_type(selection, opportunity_payload)
    # V-15 먼저 — false 면 빠른 abort (이미 user 결정)
    _check_allow_dry_run(selection)
    # V-16 — environment guard
    _check_operating_mode(operating_mode)
    # V-1 ~ V-4
    candidate = _check_identity(selection, opportunity_payload)
    # V-5 ~ V-9
    bucket_meas = _check_bucket_and_weights(candidate, opportunity_payload)
    # V-10
    _check_removed_metrics(candidate)
    # V-11 (strict, OD-6 default)
    actual_sha = _check_review_packet_sha256(selection)
    # V-12
    _check_timestamp_ordering(selection, opportunity_payload)
    # V-13 / V-14
    _check_non_empty(selection)

    summary = {
        "rules_evaluated": 16,
        "rules_passed": 16,
        "rules_failed": 0,
        "bucket_constraint_check": {
            "equity_deviation_from_080": bucket_meas["equity_deviation_from_080"],
            "fixed_income_deviation_from_020": bucket_meas[
                "fixed_income_deviation_from_020"
            ],
        },
        "weight_sum_deviation_from_1": bucket_meas["weight_sum_deviation_from_1"],
        "removed_metric_check": "absent",
        "review_packet_sha256_match": True,
        "review_packet_sha256_actual": actual_sha,
        "timestamp_after_opportunity_generation": True,
        "operating_mode": operating_mode,
        "operating_mode_check": "relaxed_diagnostic_confirmed",
    }
    return candidate, summary


def build_manager_selected_saa(
    selection: dict[str, Any],
    opportunity_payload: dict[str, Any],
    opportunity_json_path: Path,
    *,
    operating_mode: str = "relaxed_diagnostic",
) -> dict[str, Any]:
    """Validate + assemble the manager_selected_saa dump payload."""
    candidate, summary = validate_selection(
        selection, opportunity_payload, operating_mode=operating_mode,
    )
    opp_path = Path(opportunity_json_path)
    opp_sha = _sha256_file(opp_path) if opp_path.exists() else None

    payload: dict[str, Any] = {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "operating_mode": operating_mode,
            "production_applied": False,
            "sign_off_required_for_production": True,
            "manager_override_saa_layer": True,
            "scope": "R-1F.1 (validation + dump only; no downstream wiring)",
        },
        "selection_input": {
            "portfolio_type": selection["portfolio_type"],
            "candidate_id": selection["candidate_id"],
            "selected_by": selection["selected_by"],
            "selected_at": selection["selected_at"],
            "selection_reason": selection["selection_reason"],
            "manager_view_notes": list(selection.get("manager_view_notes") or []),
            "source_review_packet": {
                "path": str(selection["source_review_packet"]["path"]),
                "sha256": str(selection["source_review_packet"]["sha256"]),
            },
            "allow_downstream_dry_run": bool(selection["allow_downstream_dry_run"]),
        },
        "selected_candidate": {
            "candidate_id": candidate["candidate_id"],
            "weights": dict(candidate.get("weights") or {}),
            "expected_return": float(candidate.get("expected_return") or 0.0),
            "volatility": float(candidate.get("volatility") or 0.0),
            "sharpe": (
                float(candidate["sharpe"]) if candidate.get("sharpe") is not None else None
            ),
            "equity_weight": float(candidate.get("equity_weight") or 0.0),
            "fixed_income_weight": float(candidate.get("fixed_income_weight") or 0.0),
            "max_asset_weight": float(candidate.get("max_asset_weight") or 0.0),
            "nonzero_asset_count": int(candidate.get("nonzero_asset_count") or 0),
            "concentration_hhi": float(candidate.get("concentration_hhi") or 0.0),
            "equity_intra_hhi": (
                float(candidate["equity_intra_hhi"])
                if candidate.get("equity_intra_hhi") is not None else None
            ),
            "fixed_income_intra_hhi": (
                float(candidate["fixed_income_intra_hhi"])
                if candidate.get("fixed_income_intra_hhi") is not None else None
            ),
            "equity_max_asset_weight": float(candidate.get("equity_max_asset_weight") or 0.0),
            "fixed_income_max_asset_weight": float(
                candidate.get("fixed_income_max_asset_weight") or 0.0
            ),
            "mvo_efficiency_score": (
                float(candidate["mvo_efficiency_score"])
                if candidate.get("mvo_efficiency_score") is not None else None
            ),
            "feasibility_status": candidate["feasibility_status"],
        },
        "validation_summary": summary,
        "source_opportunity_json": {
            "path": str(opp_path),
            "sha256": opp_sha,
        },
        "downstream_dry_run_allowed": True,
        "downstream_dry_run_executed": False,
        "notes": [
            "manager_override_saa is a SEPARATE LAYER — existing SAA telemetry "
            "(`saa_diagnostics.saa_weights`) MUST NOT be overwritten.",
            "Production reflection requires (a) explicit manager selection, "
            "(b) Decision Register new entry, (c) separate Phase F sign-off.",
            "automated candidate recommendation is forbidden; this dump only records "
            "an explicit manager-provided selection.",
        ],
    }
    return payload


def write_manager_selected_saa_json(payload: dict[str, Any], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return out_path


__all__ = [
    "SCHEMA_VERSION",
    "REQUIRED_SELECTION_FIELDS",
    "load_selection_yaml",
    "validate_selection",
    "build_manager_selected_saa",
    "write_manager_selected_saa_json",
]
