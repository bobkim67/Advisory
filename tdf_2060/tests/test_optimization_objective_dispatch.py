"""Objective dispatch table 검증.

사용자 결정 #4: objective 는 config-driven. MVOOptimizer 가 enum 으로만 받음.
"""

import pytest

from tdf_engine.domain.enums import Objective
from tdf_engine.optimization.optimizer import MVOOptimizer, OBJECTIVE_REGISTRY


def test_default_objective_is_max_sharpe():
    opt = MVOOptimizer()
    assert opt.objective is Objective.MAX_SHARPE


def test_all_objectives_have_dispatch_entry():
    for obj in Objective:
        assert obj in OBJECTIVE_REGISTRY


def test_unknown_objective_rejected():
    # 비-Objective 값을 직접 전달하면 등록 안 됨 → ValueError
    class FakeObjective:
        value = "fake"

    with pytest.raises((ValueError, KeyError, TypeError)):
        MVOOptimizer(objective=FakeObjective())


def test_stub_objective_still_not_implemented():
    """Phase B 에서 max_sharpe 만 활성. 나머지는 stub 유지."""
    for stub in (
        Objective.UTILITY,
        Objective.MIN_VOLATILITY,
        Objective.MAX_RETURN_UNDER_RISK_LIMIT,
    ):
        opt = MVOOptimizer(objective=stub)
        with pytest.raises(NotImplementedError):
            opt.objective_fn()
