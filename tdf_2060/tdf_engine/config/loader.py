"""ConfigLoader — yaml → dataclass / dict.

Phase A: minimal. yaml 을 raw dict 로 읽고, 자주 사용하는 객체로 변환하는
helper 만 제공한다. 정합성 검증 (예: weight 합 = 1) 은 추후 Validator 에서.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from tdf_engine.domain.enums import Bucket, FallbackPolicy
from tdf_engine.domain.models import AssetClassInfo, AssetSourceNames

logger = logging.getLogger(__name__)


class ConfigLoader:
    """yaml 5종 로딩."""

    TDF_CONFIG = "tdf_2060.yaml"
    OPTIMIZATION_CONFIG = "optimization_constraints.yaml"
    UNIVERSE_CONFIG = "universe_filter.yaml"
    TAA_CONFIG = "taa_policy.yaml"
    ASSET_MAPPING = "asset_mapping.yaml"
    CLASSIFICATION_CONFIG = "universe_classification.yaml"
    DB_SOURCES_CONFIG = "db_sources.yaml"

    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        if not self.config_dir.exists():
            raise FileNotFoundError(f"config dir not found: {self.config_dir}")

    # ── 단일 yaml ────────────────────────────────────────────
    def _load_yaml(self, name: str) -> dict[str, Any]:
        path = self.config_dir / name
        if not path.exists():
            raise FileNotFoundError(f"config file not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data or {}

    def load_tdf_config(self) -> dict[str, Any]:
        return self._load_yaml(self.TDF_CONFIG)

    def load_optimization_config(self) -> dict[str, Any]:
        return self._load_yaml(self.OPTIMIZATION_CONFIG)

    def load_universe_config(self) -> dict[str, Any]:
        return self._load_yaml(self.UNIVERSE_CONFIG)

    def load_taa_config(self) -> dict[str, Any]:
        return self._load_yaml(self.TAA_CONFIG)

    def load_asset_mapping_raw(self) -> dict[str, Any]:
        return self._load_yaml(self.ASSET_MAPPING)

    def load_classification_rules_raw(self) -> dict[str, Any] | None:
        """Phase C-pre: classifier 룰 yaml. 파일 없으면 None (DEFAULT_RULES 폴백)."""
        path = self.config_dir / self.CLASSIFICATION_CONFIG
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data or {}

    def load_db_sources_raw(self) -> dict[str, Any] | None:
        """Phase C: DB 매핑 yaml. 파일 없으면 None (file repo 모드만 가능)."""
        path = self.config_dir / self.DB_SOURCES_CONFIG
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data or {}

    # ── domain 객체로 변환 ────────────────────────────────────
    def load_assets(self) -> list[AssetClassInfo]:
        """asset_mapping.yaml → list[AssetClassInfo]."""

        raw = self.load_asset_mapping_raw()
        result: list[AssetClassInfo] = []
        for entry in raw.get("assets", []):
            asset_key = entry["asset_key"]

            try:
                bucket = Bucket(entry["bucket"])
            except ValueError as e:
                raise ValueError(
                    f"asset '{asset_key}' 의 bucket '{entry.get('bucket')}' "
                    f"이 유효하지 않음. allowed={[b.value for b in Bucket]}"
                ) from e

            try:
                fp = FallbackPolicy(entry.get("fallback_policy", "error_if_missing"))
            except ValueError as e:
                raise ValueError(
                    f"asset '{asset_key}' 의 fallback_policy 가 유효하지 않음"
                ) from e

            sn_raw = entry.get("source_names") or {}
            source_names = AssetSourceNames(
                optimization=sn_raw.get("optimization"),
                regime_return=sn_raw.get("regime_return"),
            )

            proxy_block = entry.get("proxy") or {}
            proxy_enabled = bool(proxy_block.get("enabled", False))
            proxy_ticker = proxy_block.get("proxy_ticker")

            result.append(
                AssetClassInfo(
                    asset_key=asset_key,
                    display_name=entry["display_name"],
                    source_names=source_names,
                    bucket=bucket,
                    flags=frozenset(entry.get("flags") or []),
                    required=bool(entry.get("required", True)),
                    fallback_policy=fp,
                    db_dataset_id=entry.get("db_dataset_id"),
                    proxy_enabled=proxy_enabled,
                    proxy_ticker=proxy_ticker,
                    notes=entry.get("notes"),
                )
            )
        return result


def load_default_loader() -> ConfigLoader:
    """tdf_engine/config/ 디렉토리를 가리키는 default loader."""
    return ConfigLoader(Path(__file__).parent)
