"""ECIRegimeClassifier sign-based 분류 검증.

산식 (시트 메타 row 검증 완료):
    IF(P>0, IF(V>0, 1, 4), IF(V>0, 2, 3))
"""

import pytest

from tdf_engine.domain.enums import Regime
from tdf_engine.regime.classifier import ECIRegimeClassifier


@pytest.mark.parametrize(
    "p,v,expected",
    [
        (+0.1, +0.1, Regime.EXPANSION),     # 1
        (+0.1, -0.1, Regime.DECELERATION),  # 4
        (-0.1, +0.1, Regime.RECOVERY),      # 2
        (-0.1, -0.1, Regime.SLOWDOWN),      # 3
        # 경계: P/V = 0 은 spec 상 P>0 / V>0 모두 false → 3
        (0.0, 0.0, Regime.SLOWDOWN),
        (0.0, +0.1, Regime.RECOVERY),       # P>0 false → IF(V>0, 2, 3) → 2
    ],
)
def test_classify_scalar(p: float, v: float, expected: Regime):
    assert ECIRegimeClassifier.classify_scalar(p, v) is expected


def test_regime_int_values():
    assert int(Regime.EXPANSION) == 1
    assert int(Regime.RECOVERY) == 2
    assert int(Regime.SLOWDOWN) == 3
    assert int(Regime.DECELERATION) == 4


def test_regime_label_present():
    for r in Regime:
        assert isinstance(r.label, str) and len(r.label) > 0
