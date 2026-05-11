"""RegimeTAAPolicy + RegimeTilt — taa_policy.yaml 의 dataclass 표현."""

from __future__ import annotations

from dataclasses import dataclass, field

from tdf_engine.domain.enums import Regime


@dataclass(frozen=True)
class RegimeTilt:
    """단일 regime 의 tilt 정의.

    bucket_tilts:  bucket key → tilt (예: {"equity": +0.05, "fixed_income": -0.05})
    asset_tilts:   asset_key → tilt
    reason:        사유 텍스트
    """

    bucket_tilts: dict[str, float] = field(default_factory=dict)
    asset_tilts: dict[str, float] = field(default_factory=dict)
    reason: str = ""


@dataclass(frozen=True)
class RegimeTAAPolicy:
    """1~4 regime 별 tilt 정책 묶음."""

    tilts_by_regime: dict[int, RegimeTilt] = field(default_factory=dict)

    def get(self, regime: int | Regime) -> RegimeTilt:
        key = int(regime)
        if key not in self.tilts_by_regime:
            raise KeyError(f"regime {key} 의 tilt 정책이 정의되지 않음")
        return self.tilts_by_regime[key]

    @classmethod
    def from_dict(cls, raw: dict) -> "RegimeTAAPolicy":
        """taa_policy.yaml 의 'regime_tilts' block → RegimeTAAPolicy."""
        tilts: dict[int, RegimeTilt] = {}
        for regime_str, body in (raw or {}).items():
            tilts[int(regime_str)] = RegimeTilt(
                bucket_tilts=dict(body.get("bucket_tilts") or {}),
                asset_tilts=dict(body.get("asset_tilts") or {}),
                reason=str(body.get("reason", "")),
            )
        return cls(tilts_by_regime=tilts)
