"""pytest conftest — 공통 fixture.

- sys.path 보정.
- ConfigLoader 기본 fixture.
- ust30 데이터를 보강한 임시 source_root fixture (Phase B happy-path).
"""

from __future__ import annotations

import sys
import shutil
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_DIR = PROJECT_ROOT / "tdf_engine" / "config"
ADVISORY_ROOT = PROJECT_ROOT.parent  # C:/.../Advisory/


@pytest.fixture
def config_dir() -> Path:
    return CONFIG_DIR


@pytest.fixture
def advisory_root() -> Path:
    """소스파일들이 직속으로 있는 디렉토리 (`Advisory/`)."""
    return ADVISORY_ROOT


@pytest.fixture
def loader(config_dir):
    from tdf_engine.config.loader import ConfigLoader

    return ConfigLoader(config_dir)


@pytest.fixture
def augmented_source_root(tmp_path, advisory_root) -> Path:
    """Advisory/ 의 모든 source 파일을 tmp_path 로 복사하고
    Asset_rt_vol / Corr_mat 에 us_treasury_30y row/column 을 주입한 디렉토리.

    Phase B happy-path 테스트용. (b) 강한 error 정책을 우회하기 위함.

    수치는 placeholder (USGG10YR 보다 σ 더 큼, E[R] 약간 높음).
    실제 운영 수치는 Phase C(DB 연결) 에서 SCIP 로 채움.
    """
    import pandas as pd

    src_files = [
        "Asset_rt_vol",
        "Corr_mat",
        "regime_src",
        "regimeAnalysis_src",
        "etf_list",
        "fund_list",
    ]
    for fn in src_files:
        shutil.copy(advisory_root / fn, tmp_path / fn)

    # Asset_rt_vol 에 ust30 row 추가
    df = pd.read_csv(tmp_path / "Asset_rt_vol", sep="\t", encoding="utf-8")
    new_row = {
        "Asset Class": None,  # ffill 로 채워질 자리
        # Phase C.2 — asset_mapping ust30.source_names.optimization = "BRFUT004"
        "Ticker": "BRFUT004",
        "Name": "미국 국고채 30년",
        "σ": "13.0%",
        "E[R]": "3.50%",
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(tmp_path / "Asset_rt_vol", sep="\t", index=False, encoding="utf-8")

    # Corr_mat 에 ust30 행/열 추가 — USGG10YR 한국명 '미국 채권 10년' 대비 약간 보수적 default
    corr = pd.read_csv(tmp_path / "Corr_mat", sep="\t", encoding="utf-8", index_col=0)
    new_name = "미국 국고채 30년"
    # 기본값: 다른 자산과 0 (안전 default). 미국 채권 10년 / 미국 채권 5년 / 한국국고채10년 과는 양의 상관.
    new_col = pd.Series(0.0, index=corr.index, name=new_name)
    if "미국 채권 10년" in corr.index:
        new_col["미국 채권 10년"] = 0.85
    if "미국 채권 5년" in corr.index:
        new_col["미국 채권 5년"] = 0.65
    if "한국국고채10년" in corr.index:
        new_col["한국국고채10년"] = 0.30
    corr[new_name] = new_col
    new_row = {c: corr.loc[c, new_name] if c in corr.index else 0.0 for c in corr.columns}
    new_row[new_name] = 1.0
    corr.loc[new_name] = new_row
    corr.to_csv(tmp_path / "Corr_mat", sep="\t", encoding="utf-8")

    return tmp_path


@pytest.fixture
def augmented_assets(loader):
    """ust30 의 source_names.optimization 을 fixture row 와 정합하게 유지한 assets list.

    Phase C.2 부터 yaml 자체가 'BRFUT004' 로 채워졌으므로 별도 수정 불필요.
    fixture 호환을 위해 그대로 반환 (호출 사이트 코드 변경 최소화).
    """
    return loader.load_assets()
