"""MVOOptimizer max_sharpe — Phase B."""

import pytest


@pytest.fixture
def saa_result(augmented_source_root, augmented_assets, loader):
    from tdf_engine.optimization.tool import OptimizationTool
    from tdf_engine.repositories.file_repositories import FileMarketDataRepository

    repo = FileMarketDataRepository(augmented_source_root)
    tdf = loader.load_tdf_config()
    opt = loader.load_optimization_config()
    tool = OptimizationTool(repo, augmented_assets, tdf, opt)
    return tool.run()


def test_weights_sum_to_one(saa_result):
    assert abs(float(saa_result.weights.sum()) - 1.0) < 1e-6


def test_each_weight_within_bounds(saa_result, loader):
    tdf = loader.load_tdf_config()
    bounds = tdf["weight_bounds"]
    for k, v in saa_result.weights.items():
        b = bounds.get(k)
        if not b:
            continue
        assert v >= float(b["min"]) - 1e-6, f"{k} below lb"
        assert v <= float(b["max"]) + 1e-6, f"{k} above ub"


def test_equity_sum_in_bucket_bounds(saa_result, augmented_assets):
    """Phase D relaxed (D-01 closed): bucket range hard bound 비활성.
    bucket 합계 자체는 [0, 1] 범위 내이고 (long-only + sum=1 의 자연 결과),
    equity + fixed_income = 1.0 만 검증. monitoring 용 sanity range 는
    별도 telemetry 로 노출.
    """
    eq_keys = [a.asset_key for a in augmented_assets if a.bucket.value == "equity"]
    fi_keys = [a.asset_key for a in augmented_assets if a.bucket.value == "fixed_income"]
    eq_sum = float(saa_result.weights.loc[eq_keys].sum())
    fi_sum = float(saa_result.weights.loc[fi_keys].sum())
    # hard: 양쪽 모두 [0, 1] + 합 = 1.0
    assert 0.0 <= eq_sum <= 1.0
    assert 0.0 <= fi_sum <= 1.0
    assert abs((eq_sum + fi_sum) - 1.0) < 1e-6


def test_constraints_passed(saa_result):
    assert saa_result.constraints_passed is True


def test_objective_name_max_sharpe(saa_result):
    assert saa_result.objective_name == "max_sharpe"
    assert saa_result.sharpe == saa_result.sharpe  # not nan
