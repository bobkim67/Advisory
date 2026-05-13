"""R-1B-lite (R-1B.2 corrected) — SAA Opportunity Set tests.

Scope (R-1B.2 corrected — bucket-constrained):
- determinism (seed=42)
- bucket constraint: equity == 0.80 hard, fixed_income == 0.20 hard
- weights sum-to-1, non-negative
- intra-bucket HHI / max_w consistency
- metric correctness (E[R], σ, Sharpe, HHI)
- ref_max_sharpe inclusion + source 검증 (saa_diagnostics.saa_weights)
- ref_80_20_equal_intra_bucket inclusion + intra 분배
- removed metric absence: bucket_distance_from_80_20 / full_weight_distance_*
- schema shape (reference_points 2개만, similar_search 키 없음)
- diagnostics pool_size_total = n + 2
- source portfolio JSON mutation 없음
- summary markdown 생성
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
ETF_E62_JSON = (
    REPO_ROOT / "out" / "db_etf_relaxed_e62" / "portfolio_etf_20260511.json"
)
FUND_E62_JSON = (
    REPO_ROOT / "out" / "db_fund_relaxed_e62" / "portfolio_fund_20260511.json"
)


pytestmark = pytest.mark.skipif(
    not (ETF_E62_JSON.exists() and FUND_E62_JSON.exists()),
    reason="E-6.2 portfolio JSON not present",
)

# 테스트 비용 절감을 위해 작은 n. determinism / bucket constraint 자체는 동일하게 보장.
SMALL_N = 200
FRONT_GRID_TEST = 11

EQUITY_TOTAL = 0.80
FI_TOTAL = 0.20
BUCKET_TOL = 1e-9


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def etf_portfolio() -> dict:
    return json.loads(ETF_E62_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fund_portfolio() -> dict:
    return json.loads(FUND_E62_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def etf_payload(etf_portfolio: dict) -> dict:
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    return build_opportunity_set(
        etf_portfolio,
        n_candidates=SMALL_N,
        random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
    )


@pytest.fixture(scope="module")
def fund_payload(fund_portfolio: dict) -> dict:
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    return build_opportunity_set(
        fund_portfolio,
        n_candidates=SMALL_N,
        random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
    )


# ---------------------------------------------------------------------------
# 1. Determinism
# ---------------------------------------------------------------------------


def test_determinism_with_seed_42(etf_portfolio: dict) -> None:
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    p1 = build_opportunity_set(
        etf_portfolio, n_candidates=SMALL_N, random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
    )
    p2 = build_opportunity_set(
        etf_portfolio, n_candidates=SMALL_N, random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
    )
    keys = p1["inputs"]["asset_keys"]
    for c1, c2 in zip(p1["candidates"], p2["candidates"]):
        assert c1["candidate_id"] == c2["candidate_id"]
        for k in keys:
            assert abs(c1["weights"][k] - c2["weights"][k]) < 1e-15


# ---------------------------------------------------------------------------
# 2. Bucket constraint (R-1B.2 hard)
# ---------------------------------------------------------------------------


def test_all_sampled_candidates_satisfy_equity_080(etf_payload: dict) -> None:
    for c in etf_payload["candidates"]:
        assert abs(c["equity_weight"] - EQUITY_TOTAL) < BUCKET_TOL, (
            f"{c['candidate_id']} equity_weight={c['equity_weight']}"
        )


def test_all_sampled_candidates_satisfy_fi_020(etf_payload: dict) -> None:
    for c in etf_payload["candidates"]:
        assert abs(c["fixed_income_weight"] - FI_TOTAL) < BUCKET_TOL, (
            f"{c['candidate_id']} fi_weight={c['fixed_income_weight']}"
        )


def test_all_candidate_weights_sum_to_one(etf_payload: dict) -> None:
    keys = etf_payload["inputs"]["asset_keys"]
    for c in etf_payload["candidates"]:
        s = sum(c["weights"][k] for k in keys)
        assert abs(s - 1.0) < 1e-9, f"{c['candidate_id']} sum={s}"


def test_all_candidate_weights_non_negative(etf_payload: dict) -> None:
    keys = etf_payload["inputs"]["asset_keys"]
    for c in etf_payload["candidates"]:
        for k in keys:
            assert c["weights"][k] >= 0.0, f"{c['candidate_id']} {k} < 0"


# ---------------------------------------------------------------------------
# 3. Metric correctness vs μ, Σ
# ---------------------------------------------------------------------------


def test_metric_consistency_with_mu_sigma(etf_payload: dict) -> None:
    keys = etf_payload["inputs"]["asset_keys"]
    er = etf_payload["inputs"]["expected_returns"]
    cov = etf_payload["inputs"]["covariance_matrix"]
    rf = float(etf_payload["inputs"]["risk_free_rate"])

    for c in etf_payload["candidates"][:5]:
        w = [c["weights"][k] for k in keys]
        ret = sum(w[i] * float(er[keys[i]]) for i in range(len(keys)))
        var = 0.0
        for i, ki in enumerate(keys):
            for j, kj in enumerate(keys):
                var += w[i] * w[j] * float(cov[ki][kj])
        vol = math.sqrt(max(var, 0.0))
        assert abs(c["expected_return"] - ret) < 1e-9
        assert abs(c["volatility"] - vol) < 1e-9
        if vol > 1e-12:
            sh = (ret - rf) / vol
            assert c["sharpe"] is not None
            assert abs(c["sharpe"] - sh) < 1e-9


def test_concentration_hhi_consistency(etf_payload: dict) -> None:
    keys = etf_payload["inputs"]["asset_keys"]
    for c in etf_payload["candidates"][:5]:
        w = [c["weights"][k] for k in keys]
        hhi = sum(x * x for x in w)
        assert abs(c["concentration_hhi"] - hhi) < 1e-12


def test_intra_bucket_hhi_consistency(etf_payload: dict) -> None:
    eq_keys = etf_payload["inputs"]["equity_asset_keys"]
    fi_keys = etf_payload["inputs"]["fixed_income_asset_keys"]
    for c in etf_payload["candidates"][:5]:
        eq_total = c["equity_weight"]
        fi_total = c["fixed_income_weight"]
        eq_intra = sum((c["weights"][k] / eq_total) ** 2 for k in eq_keys)
        fi_intra = sum((c["weights"][k] / fi_total) ** 2 for k in fi_keys)
        assert c["equity_intra_hhi"] is not None
        assert c["fixed_income_intra_hhi"] is not None
        assert abs(c["equity_intra_hhi"] - eq_intra) < 1e-12
        assert abs(c["fixed_income_intra_hhi"] - fi_intra) < 1e-12


def test_intra_bucket_max_w_consistency(etf_payload: dict) -> None:
    eq_keys = etf_payload["inputs"]["equity_asset_keys"]
    fi_keys = etf_payload["inputs"]["fixed_income_asset_keys"]
    for c in etf_payload["candidates"][:5]:
        eq_max = max(c["weights"][k] for k in eq_keys)
        fi_max = max(c["weights"][k] for k in fi_keys)
        assert abs(c["equity_max_asset_weight"] - eq_max) < 1e-12
        assert abs(c["fixed_income_max_asset_weight"] - fi_max) < 1e-12


# ---------------------------------------------------------------------------
# 4. Removed metric absence (R-1B.2)
# ---------------------------------------------------------------------------


def test_bucket_distance_metric_removed(etf_payload: dict) -> None:
    for c in etf_payload["candidates"][:3]:
        assert "bucket_distance_from_80_20" not in c
    for ref in etf_payload["reference_points"].values():
        assert "bucket_distance_from_80_20" not in ref


def test_full_weight_distance_metric_removed(etf_payload: dict) -> None:
    for c in etf_payload["candidates"][:3]:
        assert "full_weight_distance_from_80_20_equal_bucket_reference" not in c
    for ref in etf_payload["reference_points"].values():
        assert "full_weight_distance_from_80_20_equal_bucket_reference" not in ref


# ---------------------------------------------------------------------------
# 5. ref_max_sharpe — source + bucket constraint 위반 가능 명시
# ---------------------------------------------------------------------------


def test_ref_max_sharpe_inclusion_and_source(
    etf_portfolio: dict, etf_payload: dict
) -> None:
    refs = etf_payload["reference_points"]
    assert "ref_max_sharpe" in refs
    ref = refs["ref_max_sharpe"]
    assert ref["candidate_id"] == "ref_max_sharpe"

    direct = etf_portfolio["diagnostics"]["saa_diagnostics"]["saa_weights"]
    for k, v in direct.items():
        assert abs(ref["weights"][k] - float(v)) < 1e-12, (
            f"ref_max_sharpe weight for {k} must equal "
            "saa_diagnostics.saa_weights (not portfolio.asset_allocation)"
        )


def test_ref_max_sharpe_may_violate_bucket_constraint(etf_payload: dict) -> None:
    """e62 baseline 의 ref_max_sharpe 는 unconstrained MVO 결과 (eq≈100%, fi≈0%).

    R-1B.2 정책: reference 는 bucket constraint 위반 가능. 본 테스트는 그 사실을
    spec 으로 강제 (만약 baseline 이 미래에 80:20 만족하도록 바뀌면 본 테스트는
    fail — spec docs 의 'bucket 위반 가능' 문구를 재확인해야 함).
    """
    ref = etf_payload["reference_points"]["ref_max_sharpe"]
    # e62 baseline: eq ≈ 1.0
    assert abs(ref["equity_weight"] - 1.0) < 1e-9
    assert abs(ref["fixed_income_weight"]) < 1e-9
    # fixed_income_intra_hhi 는 None (fi total=0)
    assert ref["fixed_income_intra_hhi"] is None
    # equity_intra_hhi 는 정의 가능 (fi 자산은 제외, equity 자산만으로 HHI)
    assert ref["equity_intra_hhi"] is not None


# ---------------------------------------------------------------------------
# 6. ref_80_20_equal_intra_bucket
# ---------------------------------------------------------------------------


def test_ref_80_20_equal_intra_bucket_inclusion(etf_payload: dict) -> None:
    refs = etf_payload["reference_points"]
    assert "ref_80_20_equal_intra_bucket" in refs
    # 옛 이름 'ref_80_20' 잔존 금지
    assert "ref_80_20" not in refs


def test_ref_80_20_equal_intra_bucket_distribution(etf_payload: dict) -> None:
    ref = etf_payload["reference_points"]["ref_80_20_equal_intra_bucket"]
    assert ref["candidate_id"] == "ref_80_20_equal_intra_bucket"
    assert abs(ref["equity_weight"] - EQUITY_TOTAL) < 1e-12
    assert abs(ref["fixed_income_weight"] - FI_TOTAL) < 1e-12
    eq_keys = etf_payload["inputs"]["equity_asset_keys"]
    fi_keys = etf_payload["inputs"]["fixed_income_asset_keys"]
    # equity 각 16%, FI 각 5%
    for k in eq_keys:
        assert abs(ref["weights"][k] - (EQUITY_TOTAL / len(eq_keys))) < 1e-12
    for k in fi_keys:
        assert abs(ref["weights"][k] - (FI_TOTAL / len(fi_keys))) < 1e-12
    # intra HHI: 5×(1/5)^2 = 0.20, 4×(1/4)^2 = 0.25
    assert abs(ref["equity_intra_hhi"] - 1.0 / len(eq_keys)) < 1e-12
    assert abs(ref["fixed_income_intra_hhi"] - 1.0 / len(fi_keys)) < 1e-12


# ---------------------------------------------------------------------------
# 7. Schema shape (R-1B-lite, R-1B.2 corrected)
# ---------------------------------------------------------------------------


def test_schema_has_only_two_reference_points(etf_payload: dict) -> None:
    refs = etf_payload["reference_points"]
    assert set(refs.keys()) == {"ref_max_sharpe", "ref_80_20_equal_intra_bucket"}


def test_schema_excludes_deferred_reference_keys(etf_payload: dict) -> None:
    refs = etf_payload["reference_points"]
    for forbidden in ("ref_min_vol", "ref_equal_weight", "ref_user_selected", "ref_80_20"):
        assert forbidden not in refs


def test_schema_does_not_have_similar_search_key(etf_payload: dict) -> None:
    assert "similar_search" not in etf_payload


def test_diagnostics_pool_size_total_is_n_plus_two(etf_payload: dict) -> None:
    diag = etf_payload["diagnostics"]
    assert diag["pool_size_total"] == SMALL_N + 2


def test_diagnostics_sum_check(etf_payload: dict) -> None:
    diag = etf_payload["diagnostics"]
    rejected_filter_total = sum(diag["rejected_by_filter"].values())
    assert (
        diag["feasible_count"]
        + diag["rejected_by_degeneracy"]
        + rejected_filter_total
        == diag["pool_size_total"]
    )


def test_meta_has_r1b2_scope_label(etf_payload: dict) -> None:
    assert etf_payload["meta"]["scope"].startswith("R-1B-lite")
    assert "R-1B.2" in etf_payload["meta"]["scope"]
    assert etf_payload["meta"]["schema_version"] == "r1b_lite.2"


def test_generation_method_is_bucket_constrained(etf_payload: dict) -> None:
    gen = etf_payload["generation"]
    assert gen["method"] == "dirichlet_bucket_constrained"
    assert gen["equity_bucket_total"] == EQUITY_TOTAL
    assert gen["fixed_income_bucket_total"] == FI_TOTAL


# ---------------------------------------------------------------------------
# 8. Source portfolio mutation 없음
# ---------------------------------------------------------------------------


def test_source_portfolio_json_not_mutated(etf_portfolio: dict) -> None:
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    snapshot = copy.deepcopy(etf_portfolio)
    _ = build_opportunity_set(
        etf_portfolio, n_candidates=SMALL_N, random_seed=42,
        frontier_grid_points=FRONT_GRID_TEST,
    )
    assert etf_portfolio == snapshot


# ---------------------------------------------------------------------------
# 9. Telemetry guard
# ---------------------------------------------------------------------------


def test_missing_saa_weights_raises(etf_portfolio: dict) -> None:
    from tdf_engine.optimization.opportunity_set import build_opportunity_set

    broken = copy.deepcopy(etf_portfolio)
    broken["diagnostics"]["saa_diagnostics"]["saa_weights"] = {}
    with pytest.raises(ValueError, match="saa_diagnostics.saa_weights"):
        build_opportunity_set(broken, n_candidates=10, random_seed=42)


# ---------------------------------------------------------------------------
# 10. JSON write + summary md
# ---------------------------------------------------------------------------


def test_json_write_and_summary_md(
    etf_payload: dict, fund_payload: dict, tmp_path: Path
) -> None:
    from tdf_engine.optimization.opportunity_set import (
        render_opportunity_set_summary_md,
        write_opportunity_set_json,
    )

    etf_json = write_opportunity_set_json(
        etf_payload, tmp_path / "saa_opportunity_set_etf_20260513.json"
    )
    fund_json = write_opportunity_set_json(
        fund_payload, tmp_path / "saa_opportunity_set_fund_20260513.json"
    )
    summary = render_opportunity_set_summary_md(
        as_of_run="20260513",
        etf_payload=etf_payload,
        fund_payload=fund_payload,
        out_path=tmp_path / "saa_opportunity_set_summary_20260513.md",
    )
    assert etf_json.exists() and etf_json.stat().st_size > 100
    assert fund_json.exists() and fund_json.stat().st_size > 100
    assert summary.exists()
    text = summary.read_text(encoding="utf-8")
    assert "ref_max_sharpe" in text
    assert "ref_80_20_equal_intra_bucket" in text
    # R-1B.2 표기: bucket-constrained 명시
    assert "R-1B.2" in text or "bucket-constrained" in text or "80%" in text


def test_fund_payload_basic_shape(fund_payload: dict) -> None:
    assert fund_payload["meta"]["product_type"] == "fund"
    assert len(fund_payload["candidates"]) == SMALL_N
    assert set(fund_payload["reference_points"].keys()) == {
        "ref_max_sharpe", "ref_80_20_equal_intra_bucket"
    }
    # bucket constraint
    for c in fund_payload["candidates"]:
        assert abs(c["equity_weight"] - EQUITY_TOTAL) < BUCKET_TOL
        assert abs(c["fixed_income_weight"] - FI_TOTAL) < BUCKET_TOL
