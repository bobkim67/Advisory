"""CompositeMarketDataRepository — 일부 메서드는 DB, 일부는 file 로 위임.

Phase C 1차에서는 asset_rt_vol/corr_matrix 만 DB 모드 활성, regime_*/regime_return_*
는 file 로 위임하는 케이스가 많음. 본 wrapper 가 그 분기를 흡수한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd
    from tdf_engine.repositories.interfaces import MarketDataRepository


class CompositeMarketDataRepository:
    def __init__(
        self,
        primary: "MarketDataRepository",
        fallback: "MarketDataRepository",
        delegate_to_primary: tuple[str, ...] = ("load_asset_rt_vol", "load_corr_matrix"),
    ):
        self.primary = primary
        self.fallback = fallback
        self.delegate_to_primary = delegate_to_primary

    def _call(self, name: str):
        target = self.primary if name in self.delegate_to_primary else self.fallback
        try:
            return getattr(target, name)()
        except NotImplementedError:
            return getattr(self.fallback, name)()

    def load_asset_rt_vol(self) -> "pd.DataFrame":
        return self._call("load_asset_rt_vol")

    def load_corr_matrix(self) -> "pd.DataFrame":
        return self._call("load_corr_matrix")

    def load_regime_source(self) -> "pd.DataFrame":
        return self._call("load_regime_source")

    def load_regime_return_source(self) -> "pd.DataFrame":
        return self._call("load_regime_return_source")
