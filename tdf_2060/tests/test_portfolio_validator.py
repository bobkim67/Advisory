"""PortfolioValidator weight sum 검증."""

import pandas as pd

from tdf_engine.portfolio.validator import PortfolioValidator


def test_weight_sum_passes_when_one():
    w = pd.Series({"a": 0.3, "b": 0.7})
    rep = PortfolioValidator().validate_weights(w)
    assert rep.weight_sum_ok


def test_weight_sum_fails_when_off():
    w = pd.Series({"a": 0.3, "b": 0.6})
    rep = PortfolioValidator().validate_weights(w)
    assert not rep.weight_sum_ok
    assert any("weight sum" in i for i in rep.issues)
