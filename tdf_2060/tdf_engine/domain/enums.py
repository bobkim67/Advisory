"""Enum 정의."""

from __future__ import annotations

from enum import Enum, IntEnum


class Bucket(str, Enum):
    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    ALTERNATIVE = "alternative"
    CURRENCY = "currency"


class ProductType(str, Enum):
    ETF = "etf"
    FUND = "fund"


class Regime(IntEnum):
    EXPANSION = 1     # P>0, V>0
    RECOVERY = 2      # P<0, V>0
    SLOWDOWN = 3      # P<0, V<0
    DECELERATION = 4  # P>0, V<0

    @property
    def label(self) -> str:
        return {
            Regime.EXPANSION: "Expansion / Acceleration",
            Regime.RECOVERY: "Recovery / Improvement",
            Regime.SLOWDOWN: "Slowdown / Contraction",
            Regime.DECELERATION: "Late Cycle / Deceleration",
        }[self]


class FallbackPolicy(str, Enum):
    ERROR_IF_MISSING = "error_if_missing"
    WARN_IF_MISSING = "warn_if_missing"
    EXPLICIT_PROXY_ONLY = "explicit_proxy_only"  # 사용자 결정 #1


class Objective(str, Enum):
    MAX_SHARPE = "max_sharpe"
    UTILITY = "utility"
    MIN_VOLATILITY = "min_volatility"
    MAX_RETURN_UNDER_RISK_LIMIT = "max_return_under_risk_limit"
