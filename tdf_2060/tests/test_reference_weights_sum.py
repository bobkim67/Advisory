"""tdf_2060.yaml 의 reference_weights / weight_bounds 정합성."""

from tdf_engine.config.loader import ConfigLoader


def test_reference_weights_sum_to_one(loader: ConfigLoader):
    cfg = loader.load_tdf_config()
    s = sum(cfg["reference_weights"].values())
    assert abs(s - 1.0) < 1e-9, f"reference_weights 합 = {s}"


def test_equity_reference_sum_is_080(loader: ConfigLoader):
    cfg = loader.load_tdf_config()
    rw = cfg["reference_weights"]
    equity_keys = ("kr_equity", "us_growth_equity", "us_value_equity", "dm_ex_us_equity", "em_equity")
    s = sum(rw[k] for k in equity_keys)
    assert abs(s - 0.80) < 1e-9


def test_fixed_income_reference_sum_is_020(loader: ConfigLoader):
    cfg = loader.load_tdf_config()
    rw = cfg["reference_weights"]
    fi_keys = ("kr_aggregate_bond", "kr_treasury_10y", "us_treasury_30y", "us_high_yield")
    s = sum(rw[k] for k in fi_keys)
    assert abs(s - 0.20) < 1e-9


def test_each_reference_weight_is_within_bounds(loader: ConfigLoader):
    cfg = loader.load_tdf_config()
    rw = cfg["reference_weights"]
    wb = cfg["weight_bounds"]
    for k, w in rw.items():
        b = wb[k]
        assert b["min"] <= w <= b["max"], (
            f"{k}: weight {w} not in [{b['min']}, {b['max']}]"
        )
