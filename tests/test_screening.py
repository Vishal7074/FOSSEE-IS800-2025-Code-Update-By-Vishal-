"""Boundary checks at the public Osdag import, using independent expected values."""
import pytest

from osdag_core.utils.common.is800_2025 import IS800_2025 as Steel


@pytest.mark.parametrize("depth, expected", [
    (700, "Plastic"), (701, "Compact"), (800, "Compact"),
    (801, "Semi-Compact"), (1200, "Semi-Compact"), (1201, "Slender"),
])
def test_mid_depth_web_boundaries(depth, expected):
    assert Steel.web_class(depth, 10, 250, loading="mid-depth") == expected


@pytest.mark.parametrize("thickness, expected", [(6, 1), (10, 0.875), (40, 0.5)])
def test_packing_factor(thickness, expected):
    assert Steel.packing_factor(thickness) == pytest.approx(expected)


@pytest.mark.parametrize("thickness", [-1, 80])
def test_invalid_packing(thickness):
    with pytest.raises(ValueError):
        Steel.packing_factor(thickness)
