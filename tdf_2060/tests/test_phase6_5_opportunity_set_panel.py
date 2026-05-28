"""Phase 6.5 — opportunity_set panel 확장 테스트.

검증 범위:
- backward compat: default args 호출 시 candidate / metric 변동 없음 (구조 무결성)
- free bucket totals (equity_total / fixed_income_total 자유 입력)
- per-asset cap/floor (asset_constraints) rejection sampling
- selected_assets subset
- edge cases: single bucket (100:0, 0:100), single asset, partial result
- invalid input → ValueError
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
ETF_PORTFOLIO_JSON = (
    REPO_ROOT / "out" / "baseline_regen_20260527" / "portfolio_etf_20260527.json"
)


pytestmark = pytest.mark.skipif(
    not ETF_PORTFOLIO_JSON.exists(),
    reason="10-asset baseline portfolio not present",
)


SMALL_N = 200
FRONT_GRID_TEST = 11
TOL = 1e-9


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def portfolio() -> dict:
    return json.loads(ETF_PORTFOLIO_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def all_asset_keys(portfolio: dict) -> list:
    return list(portfolio["diagnostics"]["saa_diagnostics"]["cma"]["asset_keys"])


# ---------------------------------------------------------------------------
# 1. Backward compat — default args 호출
# ---------------------------------------------------------------------------


def test_default_args_yields_legacy_structure(portfolio: dict) -> None:
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    out = build_opportunity_set(
        portfolio, n_candidates=SMALL_N, random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
    )
    assert out["generation"]["equity_bucket_total"] == 0.80
    assert out["generation"]["fixed_income_bucket_total"] == 0.20
    assert out["diagnostics"]["sampling_warning"] is None
    assert out["diagnostics"]["n_actual"] == SMALL_N
    # backward-compat 신규 필드 존재
    assert "asset_constraints" in out["constraints"]
    assert "selected_assets" in out["constraints"]
    # default cap/floor = (0, bucket_total)
    for k in out["inputs"]["asset_keys"]:
        fl, cp = out["constraints"]["asset_constraints"][k]
        assert fl == 0.0
        bucket = out["inputs"]["asset_bucket_map"][k]
        expected_cap = 0.80 if bucket == "equity" else 0.20
        assert abs(cp - expected_cap) < TOL


def test_default_args_bucket_constraint_hard(portfolio: dict) -> None:
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    out = build_opportunity_set(
        portfolio, n_candidates=SMALL_N, random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
    )
    for c in out["candidates"]:
        assert abs(c["equity_weight"] - 0.80) < TOL
        assert abs(c["fixed_income_weight"] - 0.20) < TOL


def test_determinism_default_args(portfolio: dict) -> None:
    """동일 seed → bit-identical 후보."""
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    a = build_opportunity_set(
        portfolio, n_candidates=SMALL_N, random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
    )
    b = build_opportunity_set(
        portfolio, n_candidates=SMALL_N, random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
    )
    keys = a["inputs"]["asset_keys"]
    for ca, cb in zip(a["candidates"], b["candidates"]):
        for k in keys:
            assert abs(ca["weights"][k] - cb["weights"][k]) < 1e-15


# ---------------------------------------------------------------------------
# 2. Free bucket totals
# ---------------------------------------------------------------------------


def test_free_bucket_70_30(portfolio: dict) -> None:
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    out = build_opportunity_set(
        portfolio, n_candidates=SMALL_N, random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
        equity_total=0.70, fixed_income_total=0.30,
    )
    assert out["generation"]["equity_bucket_total"] == 0.70
    assert out["generation"]["fixed_income_bucket_total"] == 0.30
    for c in out["candidates"]:
        assert abs(c["equity_weight"] - 0.70) < TOL
        assert abs(c["fixed_income_weight"] - 0.30) < TOL


def test_bucket_totals_must_sum_to_one(portfolio: dict) -> None:
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    with pytest.raises(ValueError, match="must equal 1.0"):
        build_opportunity_set(
            portfolio, n_candidates=SMALL_N, random_seed=42,
            equity_total=0.70, fixed_income_total=0.25,
        )


def test_bucket_totals_negative_rejected(portfolio: dict) -> None:
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    with pytest.raises(ValueError, match=">= 0"):
        build_opportunity_set(
            portfolio, n_candidates=SMALL_N, random_seed=42,
            equity_total=1.1, fixed_income_total=-0.1,
        )


# ---------------------------------------------------------------------------
# 3. Single bucket edge cases (100:0, 0:100)
# ---------------------------------------------------------------------------


def test_full_equity_bucket(portfolio: dict) -> None:
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    out = build_opportunity_set(
        portfolio, n_candidates=SMALL_N, random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
        equity_total=1.0, fixed_income_total=0.0,
    )
    for c in out["candidates"]:
        assert abs(c["equity_weight"] - 1.0) < TOL
        assert abs(c["fixed_income_weight"] - 0.0) < TOL


def test_full_fi_bucket(portfolio: dict) -> None:
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    out = build_opportunity_set(
        portfolio, n_candidates=SMALL_N, random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
        equity_total=0.0, fixed_income_total=1.0,
    )
    for c in out["candidates"]:
        assert abs(c["equity_weight"] - 0.0) < TOL
        assert abs(c["fixed_income_weight"] - 1.0) < TOL


# ---------------------------------------------------------------------------
# 4. Per-asset cap/floor
# ---------------------------------------------------------------------------


def test_asset_cap_enforced(portfolio: dict) -> None:
    """kr_equity cap=0.10 → 모든 candidate weight <= 0.10."""
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    constraints = {"kr_equity": (0.0, 0.10)}
    out = build_opportunity_set(
        portfolio, n_candidates=SMALL_N, random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
        asset_constraints=constraints,
    )
    for c in out["candidates"]:
        assert c["weights"]["kr_equity"] <= 0.10 + 1e-12


def test_asset_floor_enforced(portfolio: dict) -> None:
    """us_growth_equity floor=0.05 → 모든 candidate weight >= 0.05."""
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    constraints = {"us_growth_equity": (0.05, 0.80)}
    out = build_opportunity_set(
        portfolio, n_candidates=SMALL_N, random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
        asset_constraints=constraints,
    )
    for c in out["candidates"]:
        assert c["weights"]["us_growth_equity"] >= 0.05 - 1e-12


def test_invalid_constraint_floor_gt_cap(portfolio: dict) -> None:
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    with pytest.raises(ValueError, match="invalid constraint"):
        build_opportunity_set(
            portfolio, n_candidates=SMALL_N, random_seed=42,
            asset_constraints={"kr_equity": (0.5, 0.1)},
        )


def test_bucket_infeasible_sum_caps_lt_total(portfolio: dict) -> None:
    """Equity 자산 6개 모두 cap=0.10 → sum=0.60 < 0.80 (infeasible)."""
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    eq_assets = [
        "kr_equity", "us_growth_equity", "us_value_equity",
        "dm_ex_us_equity", "em_equity", "gold",
    ]
    constraints = {k: (0.0, 0.10) for k in eq_assets}
    with pytest.raises(ValueError, match="equity bucket infeasible"):
        build_opportunity_set(
            portfolio, n_candidates=SMALL_N, random_seed=42,
            asset_constraints=constraints,
        )


def test_partial_result_on_tight_constraints(portfolio: dict) -> None:
    """매우 좁은 cap 범위로 partial result + sampling_warning."""
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    # equity 6개에 매우 좁은 범위 → 대부분 rejection
    eq_assets = [
        "kr_equity", "us_growth_equity", "us_value_equity",
        "dm_ex_us_equity", "em_equity", "gold",
    ]
    constraints = {k: (0.13, 0.135) for k in eq_assets}
    out = build_opportunity_set(
        portfolio, n_candidates=SMALL_N, random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
        asset_constraints=constraints,
        max_attempts_multiplier=2,  # 작은 budget
    )
    # accepted 가 SMALL_N 미만이면 warning
    if out["diagnostics"]["n_actual"] < SMALL_N:
        assert out["diagnostics"]["sampling_warning"] is not None
        assert "partial result" in out["diagnostics"]["sampling_warning"]
    # 어떻든 모든 accepted 후보는 제약 만족
    for c in out["candidates"]:
        for k in eq_assets:
            w = c["weights"][k]
            assert 0.13 - 1e-12 <= w <= 0.135 + 1e-12


# ---------------------------------------------------------------------------
# 5. selected_assets subset
# ---------------------------------------------------------------------------


def test_selected_assets_subset(portfolio: dict) -> None:
    """subset 선택 시 제외 자산은 weight 0, 선택된 자산만 출력."""
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    subset = [
        "kr_equity", "us_growth_equity", "us_value_equity",  # 3 equity
        "us_aggregate_bond", "us_high_yield",                # 2 fi
    ]
    out = build_opportunity_set(
        portfolio, n_candidates=SMALL_N, random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
        selected_assets=subset,
    )
    # 출력 asset_keys 가 subset 과 일치 (순서는 원본 cma 순서 보존)
    assert set(out["inputs"]["asset_keys"]) == set(subset)
    assert out["constraints"]["selected_assets"] == out["inputs"]["asset_keys"]

    # 각 candidate weights dict 가 정확히 subset 만
    for c in out["candidates"]:
        assert set(c["weights"].keys()) == set(subset)


def test_selected_assets_unknown_key_raises(portfolio: dict) -> None:
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    with pytest.raises(ValueError, match="unknown keys"):
        build_opportunity_set(
            portfolio, n_candidates=SMALL_N, random_seed=42,
            selected_assets=["kr_equity", "no_such_asset"],
        )


def test_selected_assets_empty_bucket_with_nonzero_total(portfolio: dict) -> None:
    """선택된 자산에 equity 가 없는데 equity_total > 0 → ValueError."""
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    with pytest.raises(ValueError, match="no equity asset selected"):
        build_opportunity_set(
            portfolio, n_candidates=SMALL_N, random_seed=42,
            selected_assets=["us_aggregate_bond", "us_high_yield"],  # FI only
            # equity_total default 0.80 > 0
        )


def test_selected_fi_only_with_full_fi_bucket(portfolio: dict) -> None:
    """FI 자산만 선택 + equity_total=0 → 정상 동작."""
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    out = build_opportunity_set(
        portfolio, n_candidates=SMALL_N, random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
        selected_assets=["us_aggregate_bond", "us_high_yield", "kr_aggregate_bond"],
        equity_total=0.0, fixed_income_total=1.0,
    )
    for c in out["candidates"]:
        assert abs(c["fixed_income_weight"] - 1.0) < TOL
        assert abs(c["equity_weight"] - 0.0) < TOL
