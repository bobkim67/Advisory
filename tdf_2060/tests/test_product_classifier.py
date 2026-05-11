"""ProductClassifier — Phase B + C-pre.

C-pre: classify() 가 (asset_key, match_reason) tuple 반환.
"""


def _classify_key(cls, row):
    ak, _ = cls.classify(row)
    return ak


def test_us_growth_etf_maps_to_us_growth_equity():
    from tdf_engine.universe.classifier import ProductClassifier

    cls = ProductClassifier()
    row = {
        "펀드명(Short)": "한국투자ACE미국나스닥100상장지수(주식)",
        "대유형(KIS MP)": "글로벌주식",
        "지역": "미국",
        "소유형": "북미주식",
    }
    assert _classify_key(cls, row) == "us_growth_equity"


def test_us_value_etf_maps_to_us_value_equity():
    from tdf_engine.universe.classifier import ProductClassifier

    cls = ProductClassifier()
    row = {
        "펀드명(Short)": "한국투자ACE미국배당다우존스",
        "대유형(KIS MP)": "글로벌주식",
        "지역": "미국",
        "소유형": "북미주식",
    }
    assert _classify_key(cls, row) == "us_value_equity"


def test_kr_equity_maps_correctly():
    from tdf_engine.universe.classifier import ProductClassifier

    cls = ProductClassifier()
    row = {
        "펀드명(Short)": "한국투자KOSPI200상장지수(주식)",
        "대유형(KIS MP)": "국내주식",
        "지역": "국내",
        "소유형": "K200인덱스",
    }
    assert _classify_key(cls, row) == "kr_equity"


def test_em_china_maps_to_em_equity():
    from tdf_engine.universe.classifier import ProductClassifier

    cls = ProductClassifier()
    row = {
        "펀드명(Short)": "한국투자ACE중국H상장지수(주식)",
        "대유형(KIS MP)": "신흥국주식",
        "지역": "중국",
        "소유형": "중국주식",
    }
    assert _classify_key(cls, row) == "em_equity"


def test_kr_treasury_10y_pulls_before_aggregate():
    from tdf_engine.universe.classifier import ProductClassifier

    cls = ProductClassifier()
    row = {
        "펀드명(Short)": "ACE 국고채10년 상장지수(채권)",
        "대유형(KIS MP)": "국내채권",
        "지역": "국내",
        "소유형": "중기채권",
    }
    assert _classify_key(cls, row) == "kr_treasury_10y"


def test_us_high_yield_takes_priority():
    from tdf_engine.universe.classifier import ProductClassifier

    cls = ProductClassifier()
    row = {
        "펀드명(Short)": "한국투자글로벌하이일드(채권)",
        "대유형(KIS MP)": "해외채권",
        "지역": "글로벌",
        "소유형": "글로벌하이일드채권",
    }
    assert _classify_key(cls, row) == "us_high_yield"


def test_unmatched_returns_none():
    from tdf_engine.universe.classifier import ProductClassifier

    cls = ProductClassifier()
    row = {
        "펀드명(Short)": "한국투자혼합형",
        "대유형(KIS MP)": "국내혼합",
        "지역": "국내",
        "소유형": "일반채권혼합",
    }
    ak, reason = cls.classify(row)
    assert ak is None
    assert reason is None
