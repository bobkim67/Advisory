"""Golden answer parity helpers.

기존 VBA/Excel 산출물 (텍스트 추출본) 위치 + tolerance 정책.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd


# 답안지 (텍스트 추출본) — Advisory/ 루트 기준
GOLDEN_FILES = {
    "regime_dashboard": "regime_Dashboard",      # ECI Dashboard 시계열 (Displacement/Velocity/Phase)
    "regime_return_rt": "regimeAnalysis_rt",     # 4 regime × N 자산 평균수익률 (연환산 %)
}

# Excel 원본 (DRM 보호 — 직접 read 불가)
DRM_PROTECTED_FILES = {
    "ECI_Neo_202603.xlsx",
    "RegimeAnalysis_2602.xlsx",
    "0. 정리 - GlidePath 값.xlsx",
}

# Dashboard 가 추출된 region (Phase C.5-1 탐색 결과: USA 기준)
DASHBOARD_REGION = "USA"


# ── tolerance 정책 ─────────────────────────────────────────────────────


class Tol:
    """단계별 허용오차.

    VBA Solver(GRG Nonlinear) vs scipy SLSQP 차이로 MVO weight 는 완전 일치 X →
    명시 tolerance 로 비교. 상위 단계 (CMA/Corr) 는 numerical 일치 기대.
    """

    # cross-section / numerical
    weight = 1.0e-4              # 1bp
    return_pct = 1.0e-6
    vol_pct = 1.0e-6
    correlation = 1.0e-6
    sharpe = 1.0e-4

    # Dashboard 와의 numerical (golden 이 소수점 3자리 반올림이라 1e-3 이 현실)
    placement_velocity_abs = 1.5e-3   # golden 이 0.001 자리 반올림

    # regime 분류 정수 일치 (절대 일치 기대)
    regime_match_ratio = 1.0       # 100% (numerical edge case 면 0.95 까지 허용)

    # regime return analysis (자산별 4 regime × N → 산술/기하/연환산 정의 차이 있음)
    regime_return_pct_abs = 0.05    # 5%p — 정의 차이 / region 기준 차이 흡수


# ── 답안지 로더 ────────────────────────────────────────────────────────


def golden_dir() -> Path:
    """golden 파일이 있는 Advisory/ 루트 경로."""
    return Path(__file__).resolve().parent.parent.parent


def load_regime_dashboard():
    """regime_Dashboard 텍스트 추출본 로드 → DataFrame.

    columns: Index, Date, Displacement, Velocity, Adj. Radius, Angle, Angle(x Pi),
             Phase(R), Displacement.1, Velocity.1, Phase(N)
    Date 는 YYYY-MM 월말 datetime 으로 변환.
    """
    import pandas as pd
    p = golden_dir() / GOLDEN_FILES["regime_dashboard"]
    if not p.exists():
        return None
    df = pd.read_csv(p, sep="\t", encoding="utf-8")
    df["Date"] = pd.to_datetime(
        df["Date"].astype(str).str.replace("년 ", "-").str.replace("월", "").str.strip(),
        format="%Y-%m"
    ).dt.to_period("M").dt.to_timestamp("M")
    return df


def load_regime_return_rt():
    """regimeAnalysis_rt 텍스트 추출본 로드 → DataFrame.

    행 0~3: Regime 1~4
    행 4  : Total
    columns: Regime + 24 자산명 (한글). 값은 '%' 부착 문자열.
    반환 시 % 제거 + /100 (decimal). columns 의 한글명 그대로 유지.
    """
    import pandas as pd
    p = golden_dir() / GOLDEN_FILES["regime_return_rt"]
    if not p.exists():
        return None
    df = pd.read_csv(p, sep="\t", encoding="utf-8")
    for c in df.columns:
        if c == "Regime":
            continue
        df[c] = (
            df[c].astype(str).str.replace("%", "", regex=False).str.replace(",", "", regex=False)
            .astype(float) / 100.0
        )
    return df


# 한글 컬럼명 → asset_key 매핑 (regimeAnalysis_rt 와 일치하는 것만)
GOLDEN_RT_NAME_TO_KEY = {
    "한국주식": "kr_equity",
    "미국성장주": "us_growth_equity",
    "미국가치주": "us_value_equity",
    "미국외 선진국": "dm_ex_us_equity",
    "신흥국주식": "em_equity",
    "한국채권": "kr_aggregate_bond",        # 둘 중 첫 번째 한국채권 컬럼
    "미국하이일드": "us_high_yield",
    # 답안지에 있지만 우리 9 자산군에 없는 것: 글로벌주식/미국주식/미국나스닥/호주/미국채권/
    #                                          미국물가채/미국투자등급/미국외채권/신흥국달러표시/
    #                                          원자재/금/미국리츠/미국외리츠/글로벌인프라/한국채권.1
}
