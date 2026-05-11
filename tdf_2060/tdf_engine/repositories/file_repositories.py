"""File 기반 Repository 구현체 (1차).

소스 파일 위치는 생성자 인자로 받는다 (하드코딩 금지).
이번 단계는 raw 로드만 한다 — 파싱/정규화는 Tool 안에서 처리.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

logger = logging.getLogger(__name__)


def _read_tsv(path: Path, **kwargs) -> "pd.DataFrame":
    import pandas as pd

    if not path.exists():
        raise FileNotFoundError(f"source file not found: {path}")
    return pd.read_csv(path, sep="\t", encoding="utf-8", **kwargs)


class FileMarketDataRepository:
    """`Asset_rt_vol`, `Corr_mat`, `regime_src`, `regimeAnalysis_src` 로드.

    Parameters
    ----------
    root : Path
        Advisory/ 디렉토리 (소스 파일들이 직속으로 있는 위치).
    """

    ASSET_RT_VOL = "Asset_rt_vol"
    CORR_MAT = "Corr_mat"
    REGIME_SRC = "regime_src"
    REGIME_RETURN_SRC = "regimeAnalysis_src"

    def __init__(self, root: Path):
        self.root = Path(root)
        if not self.root.exists():
            raise FileNotFoundError(f"market data root not found: {self.root}")

    def load_asset_rt_vol(self) -> "pd.DataFrame":
        return _read_tsv(self.root / self.ASSET_RT_VOL)

    def load_corr_matrix(self) -> "pd.DataFrame":
        return _read_tsv(self.root / self.CORR_MAT, index_col=0)

    def load_regime_source(self) -> "pd.DataFrame":
        # regime_src 는 헤더 메모 row 가 없는 raw 파일 — 그대로 읽음
        return _read_tsv(self.root / self.REGIME_SRC)

    def load_regime_return_source(self) -> "pd.DataFrame":
        return _read_tsv(self.root / self.REGIME_RETURN_SRC)


class FileProductRepository:
    """`etf_list`, `fund_list` 로드."""

    ETF = "etf_list"
    FUND = "fund_list"

    def __init__(self, root: Path):
        self.root = Path(root)
        if not self.root.exists():
            raise FileNotFoundError(f"product root not found: {self.root}")

    def load_etf_universe(self) -> "pd.DataFrame":
        return _read_tsv(self.root / self.ETF)

    def load_fund_universe(self) -> "pd.DataFrame":
        return _read_tsv(self.root / self.FUND)
