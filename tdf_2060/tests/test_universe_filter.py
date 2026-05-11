"""UniverseFilter 의 핵심 제외 룰 검증."""

import pytest

from tdf_engine.universe.filters import FilterConfig, UniverseFilter


@pytest.fixture
def etf_filter() -> UniverseFilter:
    return UniverseFilter(
        FilterConfig(
            include_kis_mp_categories=("국내주식", "글로벌주식", "신흥국주식", "국내채권", "해외채권"),
            exclude_keywords=(
                "TDF", "TIF", "TRF", "멀티에셋", "자산배분", "혼합", "라이프싸이클",
                "레버리지", "인버스", "커버드콜", "타겟커버드콜", "합성",
            ),
            exclude_sub_types=("글로벌라이프싸이클", "보수적자산배분"),
            synthetic_mode="whitelist",
            synthetic_whitelist=("베트남", "인도네시아"),
        )
    )


def _row(name="", kis="국내주식", sub_type="기타인덱스") -> dict:
    return {
        "펀드명(Short)": name,
        "대유형(KIS MP)": kis,
        "소유형": sub_type,
    }


def test_pure_equity_etf_passes(etf_filter):
    excluded, _ = etf_filter.is_excluded(
        _row(name="한국투자ACE미국나스닥100", kis="글로벌주식")
    )
    assert excluded is False


def test_tdf_excluded(etf_filter):
    excluded, reason = etf_filter.is_excluded(
        _row(name="한국투자ACETDF2050", kis="글로벌주식")
    )
    assert excluded is True
    assert "TDF" in (reason or "")


def test_target_covered_call_excluded(etf_filter):
    excluded, reason = etf_filter.is_excluded(
        _row(name="한국투자ACE미국30년국채타겟커버드콜", kis="해외채권")
    )
    assert excluded is True


def test_kis_mp_mixed_excluded(etf_filter):
    excluded, reason = etf_filter.is_excluded(
        _row(name="ACE안전혼합", kis="해외혼합")
    )
    assert excluded is True
    assert "KIS MP" in (reason or "")


def test_synthetic_whitelist(etf_filter):
    # 베트남 + 합성 → whitelist 에 있으므로 통과
    excluded, _ = etf_filter.is_excluded(
        _row(name="ACE베트남VN30(주식-파생)(합성)", kis="신흥국주식")
    )
    assert excluded is False


def test_synthetic_not_in_whitelist(etf_filter):
    # 합성인데 whitelist 키워드 없음 → 제외
    excluded, reason = etf_filter.is_excluded(
        _row(name="합성ETF미국에너지", kis="글로벌주식")
    )
    assert excluded is True


def test_glide_path_sub_type_excluded(etf_filter):
    excluded, _ = etf_filter.is_excluded(
        _row(name="ACE생애주기펀드", kis="글로벌주식", sub_type="글로벌라이프싸이클")
    )
    assert excluded is True
