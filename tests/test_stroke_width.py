"""Constant screen-pixel stroke width maths (mirrors the Fuse render logic).

The Fuse draws every outline at a fixed *screen* pixel width regardless of the
zoom factor.  For an output image of ``out_w`` x ``out_h`` pixels, a requested
stroke of ``stroke_px`` screen pixels corresponds to a half-width in normalised
image space of ``stroke_px / 2 / out_w`` (x) and ``/ out_h`` (y) — crucially
this does *not* depend on the zoom applied to the geometry.  These tests pin
that invariance so the Lua implementation can be verified against them.
"""

import pytest


def stroke_halfwidth_norm(stroke_px: float, out_w: float, out_h: float):
    """Return (hx, hy): half stroke width in normalised image space."""
    return (stroke_px * 0.5) / out_w, (stroke_px * 0.5) / out_h


def stroke_halfwidth_px(stroke_px: float, zoom: float):
    """Screen stroke half-width in output pixels is independent of zoom."""
    return stroke_px * 0.5


@pytest.mark.parametrize("res", [(1920, 1080), (3840, 2160), (1280, 720)])
def test_one_pixel_stroke_matches_resolution(res):
    w, h = res
    hx, hy = stroke_halfwidth_norm(1.0, w, h)
    assert hx == pytest.approx(0.5 / w)
    assert hy == pytest.approx(0.5 / h)


@pytest.mark.parametrize("zoom", [0.1, 1.0, 5.0, 100.0])
def test_pixel_stroke_independent_of_zoom(zoom):
    # The screen stroke width must be constant across all zoom levels.
    assert stroke_halfwidth_px(3.0, zoom) == pytest.approx(1.5)


def test_stroke_scales_linearly_with_requested_px():
    hx1, _ = stroke_halfwidth_norm(1.0, 1920, 1080)
    hx4, _ = stroke_halfwidth_norm(4.0, 1920, 1080)
    assert hx4 == pytest.approx(hx1 * 4.0)
