"""pytest conftest — 공통 fixture.

- sys.path 보정.
- ConfigLoader 기본 fixture.
- 임시 source_root fixture (Asset_rt_vol/Corr_mat 등 source copy).
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
    """Advisory/ 의 모든 source 파일을 tmp_path 로 복사한 디렉토리.

    2026-05-27 — us_aggregate_bond (LBUSTRUU Index) / gold (XAU Curncy) 모두
    Asset_rt_vol + Corr_mat 본체에 이미 존재. row 주입 step 제거 — 단순 복사만.
    fixture 이름은 호출 사이트 호환을 위해 유지.
    """
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
    return tmp_path


@pytest.fixture
def augmented_assets(loader):
    """fixture 호환용 wrapper. assets list 그대로 반환."""
    return loader.load_assets()
