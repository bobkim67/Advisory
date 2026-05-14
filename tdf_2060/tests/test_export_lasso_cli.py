"""C-6 CLI chain integration tests for tdf_engine.tools.export_lasso_selection.

Builds a small synthetic opportunity_set JSON + input config in tmp_path,
invokes the CLI ``main([...])`` directly, and asserts the file output
structure / invariants.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from tdf_engine.tools.export_lasso_selection import main as cli_main


def _mk_cand(cid, sharpe, er, vol, hhi, maxw, mvo=0.02,
             eq_intra=0.25, fi_intra=0.30):
    return {
        "candidate_id": cid,
        "weights": {
            "kr_equity": 0.1, "us_growth_equity": 0.15, "us_value_equity": 0.15,
            "dm_ex_us_equity": 0.1, "em_equity": 0.1,  # eq = 0.6 — only synthetic
            "kr_aggregate_bond": 0.1, "kr_treasury_10y": 0.05,
            "us_treasury_30y": 0.025, "us_high_yield": 0.025,  # fi = 0.2
        },
        "sharpe": sharpe,
        "expected_return": er,
        "volatility": vol,
        "concentration_hhi": hhi,
        "max_asset_weight": maxw,
        "equity_intra_hhi": eq_intra,
        "fixed_income_intra_hhi": fi_intra,
        "equity_weight": 0.8,
        "fixed_income_weight": 0.2,
        "equity_max_asset_weight": maxw,
        "fixed_income_max_asset_weight": 0.10,
        "mvo_efficiency_score": mvo,
        "feasibility_status": "feasible",
    }


@pytest.fixture
def synthetic_opp_json(tmp_path):
    cands = [
        _mk_cand("c1", 0.50, 0.09, 0.13, 0.20, 0.22),
        _mk_cand("c2", 0.55, 0.10, 0.12, 0.18, 0.20),
        _mk_cand("c3", 0.60, 0.115, 0.14, 0.16, 0.24),
        _mk_cand("c4", 0.45, 0.085, 0.15, 0.30, 0.40),
        _mk_cand("c5", 0.70, 0.13, 0.11, 0.14, 0.18, mvo=0.014),
        _mk_cand("c6", 0.65, 0.135, 0.135, 0.17, 0.21, mvo=0.013),
        _mk_cand("c7", 0.58, 0.105, 0.125, 0.19, 0.23),
        _mk_cand("c8", 0.62, 0.12, 0.13, 0.165, 0.22),
    ]
    opp = {
        "meta": {
            "generated_at": "2026-05-01T00:00:00Z",
            "product_type": "etf",
        },
        "candidates": cands,
    }
    p = tmp_path / "opp.json"
    p.write_text(json.dumps(opp), encoding="utf-8")
    return p


@pytest.fixture
def input_config_all(tmp_path):
    """Wide polygon catching most synthetic candidates; rule=all."""
    cfg = {
        "x_metric": "volatility",
        "y_metric": "expected_return",
        "polygon_points": [
            [0.10, 0.07], [0.10, 0.15], [0.16, 0.15], [0.16, 0.07]
        ],
        "active_overlays": [],
        "active_filters": {"feasibility_status": "feasible"},
        "selection_mode": "lasso",
        "post_selection_rule": "all",
        "post_selection_params": {},
    }
    p = tmp_path / "input_all.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return p


@pytest.fixture
def input_config_top_sharpe(tmp_path):
    """Same polygon; rule=top_sharpe → 1 candidate."""
    cfg = {
        "x_metric": "volatility",
        "y_metric": "expected_return",
        "polygon_points": [
            [0.10, 0.07], [0.10, 0.15], [0.16, 0.15], [0.16, 0.07]
        ],
        "active_overlays": [],
        "active_filters": {"feasibility_status": "feasible"},
        "selection_mode": "lasso",
        "post_selection_rule": "top_sharpe",
        "post_selection_params": {},
    }
    p = tmp_path / "input_top.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return p


def _run_cli(opp, cfg, out_dir, *, emit_review=False, review_dir=None, skip_yaml=False):
    args = [
        "--opportunity-set", str(opp),
        "--input-config", str(cfg),
        "--output-dir", str(out_dir),
        "--portfolio-type", "etf",
        "--selected-by", "cli_chain_tester",
        "--selection-reason", "test",
    ]
    if emit_review:
        args.append("--emit-review")
    if review_dir is not None:
        args.extend(["--review-output-dir", str(review_dir)])
    if skip_yaml:
        args.append("--skip-yaml")
    rc = cli_main(args)
    assert rc == 0
    return rc


def _find_one(dirpath: pathlib.Path, pattern: str) -> pathlib.Path:
    matches = list(dirpath.glob(pattern))
    assert len(matches) == 1, f"expected one match for {pattern} in {dirpath}, got {matches}"
    return matches[0]


# ---------- Tests ----------


def test_cli_default_no_emit_review(synthetic_opp_json, input_config_top_sharpe, tmp_path):
    """Without --emit-review, only lasso JSON + yaml exist; no review/ dir."""
    out_dir = tmp_path / "out"
    _run_cli(synthetic_opp_json, input_config_top_sharpe, out_dir, emit_review=False)
    # Lasso JSON + yaml present
    _find_one(out_dir, "lasso_selection_*.json")
    _find_one(out_dir, "manager_selection_from_lasso_*.yaml")
    # No review/ dir
    assert not (out_dir / "review").exists()


def test_cli_emit_review_creates_3_files(synthetic_opp_json, input_config_all, tmp_path):
    """With --emit-review, the 3 review files appear in default review/ dir."""
    out_dir = tmp_path / "out"
    _run_cli(synthetic_opp_json, input_config_all, out_dir, emit_review=True, skip_yaml=True)
    rev = out_dir / "review"
    assert rev.is_dir()
    assert (rev / "representative_candidates.json").exists()
    assert (rev / "lasso_review_table.csv").exists()
    assert (rev / "lasso_review_summary.md").exists()


def test_cli_emit_review_custom_output_dir(synthetic_opp_json, input_config_all, tmp_path):
    """--review-output-dir overrides default review/ location."""
    out_dir = tmp_path / "out"
    rev_dir = tmp_path / "elsewhere"
    _run_cli(synthetic_opp_json, input_config_all, out_dir,
             emit_review=True, review_dir=rev_dir, skip_yaml=True)
    assert (rev_dir / "representative_candidates.json").exists()
    assert not (out_dir / "review").exists()


def test_cli_emit_review_top_sharpe_single_review(synthetic_opp_json, input_config_top_sharpe, tmp_path):
    """post_rule=top_sharpe yields selected_count=1 → review emits with single_review_mode=True."""
    out_dir = tmp_path / "out"
    _run_cli(synthetic_opp_json, input_config_top_sharpe, out_dir, emit_review=True)
    rev_json = out_dir / "review" / "representative_candidates.json"
    review = json.loads(rev_json.read_text(encoding="utf-8"))
    assert review["selected_count"] == 1
    assert review["single_review_mode"] is True
    assert len(review["representatives"]) == 1


def test_cli_emit_review_post_rule_all_multi_reps(synthetic_opp_json, input_config_all, tmp_path):
    """post_rule=all yields wide set → review has multiple unique representatives."""
    out_dir = tmp_path / "out"
    _run_cli(synthetic_opp_json, input_config_all, out_dir, emit_review=True, skip_yaml=True)
    review = json.loads((out_dir / "review" / "representative_candidates.json").read_text(encoding="utf-8"))
    assert review["selected_count"] > 1
    assert review["single_review_mode"] is False
    # At least 2 unique representatives (some archetypes may share a candidate)
    assert len(review["representatives"]) >= 2


def test_cli_emit_review_warning_propagation(synthetic_opp_json, input_config_all, tmp_path):
    """Review export carries selection-level WARN labels and per-archetype WARN map."""
    out_dir = tmp_path / "out"
    _run_cli(synthetic_opp_json, input_config_all, out_dir, emit_review=True, skip_yaml=True)
    lasso_json = _find_one(out_dir, "lasso_selection_*.json")
    lasso = json.loads(lasso_json.read_text(encoding="utf-8"))
    review = json.loads((out_dir / "review" / "representative_candidates.json").read_text(encoding="utf-8"))
    # Every WARN that appeared in the lasso export must appear at the review selection level
    for w in lasso["warning_labels"]:
        assert w in review["selection_level_warning_labels"], f"{w} missing from review WARN"
    # Per-archetype WARN map must include all 7 archetypes
    per = review["per_archetype_warning_labels"]
    for arch in ("top_sharpe", "min_volatility", "max_expected_return",
                 "min_hhi", "mvo_frontier_near", "clean_implementation", "medoid_candidate"):
        assert arch in per


def test_cli_emit_review_invariants_locked(synthetic_opp_json, input_config_all, tmp_path):
    """Review export forces production_applied=False / dry_run_only=True / phase_f_entered=False."""
    out_dir = tmp_path / "out"
    _run_cli(synthetic_opp_json, input_config_all, out_dir, emit_review=True, skip_yaml=True)
    review = json.loads((out_dir / "review" / "representative_candidates.json").read_text(encoding="utf-8"))
    assert review["is_production_selection"] is False
    assert review["dry_run_only"] is True
    inv = review["permanent_invariants"]
    assert inv["production_applied"] is False
    assert inv["implementation_ready"] is False
    assert inv["phase_f_entered"] is False
    assert inv["operating_mode"] == "relaxed_diagnostic"


def test_cli_no_production_flag_exists():
    """The CLI argparse must NOT expose any --production* style flag."""
    from tdf_engine.tools import export_lasso_selection as mod
    # Inspect the parser by patching argv with --help suppressed; use the module's
    # SystemExit-throwing parser via parse_known_args
    # Cheaper check: scan the module source for forbidden flag patterns.
    src = pathlib.Path(mod.__file__).read_text(encoding="utf-8")
    for forbidden in ("--production", "--prod-flag", "production_flag"):
        assert forbidden not in src, f"forbidden flag {forbidden!r} found in CLI source"
