"""SVG parsing and geometry flattening."""

import pytest

from conftest import SVG_PATH
from worldmap import svg_parser as sp
from worldmap.geometry import FlattenOptions, parse_path


def test_source_loads():
    root = sp.load(str(SVG_PATH))
    assert root is not None
    assert sp.local(root.tag) == "svg"


def test_parse_relative_moveto_lineto():
    # "m 10,10 l 5,0 l 0,5 z" -> triangle-ish closed contour in absolute coords.
    contours = parse_path("m 10,10 l 5,0 l 0,5 z", FlattenOptions())
    assert len(contours) == 1
    pts = contours[0]
    assert pts[0] == pytest.approx((10.0, 10.0))
    assert pts[1] == pytest.approx((15.0, 10.0))
    assert pts[2] == pytest.approx((15.0, 15.0))


def test_parse_absolute_and_hv():
    contours = parse_path("M 0 0 H 10 V 10 H 0 Z", FlattenOptions())
    pts = contours[0]
    assert pts[0] == pytest.approx((0.0, 0.0))
    assert pts[1] == pytest.approx((10.0, 0.0))
    assert pts[2] == pytest.approx((10.0, 10.0))
    assert pts[3] == pytest.approx((0.0, 10.0))


def test_cubic_bezier_flattens_to_multiple_points():
    coarse = parse_path("M 0 0 C 0 100 100 100 100 0",
                        FlattenOptions(tolerance_px=5.0))[0]
    fine = parse_path("M 0 0 C 0 100 100 100 100 0",
                      FlattenOptions(tolerance_px=0.1))[0]
    assert len(coarse) >= 2
    # Tighter tolerance must not produce fewer vertices.
    assert len(fine) >= len(coarse)
    assert fine[0] == pytest.approx((0.0, 0.0))
    assert fine[-1] == pytest.approx((100.0, 0.0))


def test_multiple_subpaths():
    contours = parse_path("M 0 0 L 1 0 M 5 5 L 6 5", FlattenOptions())
    assert len(contours) == 2
