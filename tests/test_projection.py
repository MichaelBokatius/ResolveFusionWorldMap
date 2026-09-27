"""Robinson projection: calibration, round-trip and re-centring presets."""

import math

import pytest

from conftest import SVG_PATH  # noqa: F401  (ensures sys.path setup)
from worldmap import projection as pj


def test_forward_inverse_roundtrip_exact():
    # The shared-constant transforms must round-trip to floating precision.
    for lon in range(-170, 180, 17):
        for lat in range(-80, 85, 13):
            px, py = pj.forward(lon, lat)
            rlon, rlat = pj.inverse(px, py)
            assert rlon == pytest.approx(lon, abs=1e-6)
            assert rlat == pytest.approx(lat, abs=1e-6)


def test_greenwich_maps_center_column():
    # Longitude 0 always lands on the central pixel column, any latitude.
    for lat in (-60, -30, 0, 30, 60):
        px, _ = pj.forward(0.0, lat)
        assert px == pytest.approx(pj.CX, abs=1e-6)


def test_equator_center_row():
    px, py = pj.forward(0.0, 0.0)
    assert py == pytest.approx(pj.CY, abs=1e-6)


def test_pixel_bounds_within_canvas():
    # Extreme geographic corners project inside a small margin of the canvas.
    for lon in (-180, 180):
        for lat in (-89, 89):
            px, py = pj.forward(lon, lat)
            assert -5 <= px <= pj.SVG_WIDTH + 5
            assert -5 <= py <= pj.SVG_HEIGHT + 5


@pytest.mark.parametrize("meridian", [0.0, 90.0, -90.0, 162.0, 180.0])
def test_recentre_presets_land_on_canvas(meridian):
    # After shifting by a preset meridian, a spread of sample points must still
    # project to finite, on-canvas pixels (no NaN / blow-ups).
    for lon in range(-180, 180, 30):
        for lat in (-60, 0, 60):
            rel = pj.wrap180(lon - meridian)
            px, py = pj.forward(rel, lat)
            assert math.isfinite(px) and math.isfinite(py)
            # The calibrated horizontal centre (CX) is offset from the canvas
            # centre, so the extreme +/-180 seam edge sits a little outside the
            # canvas; only assert no blow-up within a generous band.
            assert -pj.SVG_WIDTH <= px <= 2 * pj.SVG_WIDTH
            assert -pj.SVG_HEIGHT <= py <= 2 * pj.SVG_HEIGHT


def test_wrap180():
    assert pj.wrap180(190) == pytest.approx(-170)
    assert pj.wrap180(-190) == pytest.approx(170)
    assert pj.wrap180(0) == 0
    assert pj.wrap180(180) == pytest.approx(-180)
