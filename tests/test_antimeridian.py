"""Antimeridian (seam) splitting after re-centring."""

import pytest

from conftest import SVG_PATH  # noqa: F401
from worldmap import projection as pj
from worldmap import seam
from worldmap.svg_parser import load
from worldmap.countries import build_countries
from worldmap.geometry import FlattenOptions


def test_crosses_detection():
    assert seam.crosses((170.0, 0.0), (-170.0, 0.0))
    assert not seam.crosses((10.0, 0.0), (20.0, 0.0))


def test_split_inserts_boundary_points():
    contour = [(170.0, 10.0), (-170.0, 20.0)]
    pieces = seam.split(contour)
    assert len(pieces) == 2
    # First piece ends on +180, second starts on -180.
    assert pieces[0][-1][0] == pytest.approx(180.0)
    assert pieces[1][0][0] == pytest.approx(-180.0)
    # Interpolated latitude is shared and between the endpoints.
    assert pieces[0][-1][1] == pytest.approx(pieces[1][0][1])
    assert 10.0 <= pieces[0][-1][1] <= 20.0


def test_no_piece_spans_frame_after_split():
    contour = [(150.0, 0.0), (175.0, 5.0), (-175.0, 8.0), (-150.0, 10.0)]
    for piece in seam.split(contour):
        assert seam.max_edge_lon_span(piece) <= 180.0 + 1e-6


def test_russia_has_no_frame_spanning_segment_when_recentred():
    # Re-centre the map on the Pacific (180E). Russia + Alaska span the dateline;
    # after wrap + split no polyline edge may jump the whole frame.
    root = load(str(SVG_PATH))
    countries, _, _ = build_countries(root, FlattenOptions(0.8))
    by_code = {c.code: c for c in countries}
    meridian = 180.0
    for code in ("ru", "us"):
        country = by_code[code]
        for ring_px in country.polys_px:
            # px -> geo -> recentre -> wrap
            geo = [pj.inverse(px, py) for px, py in ring_px]
            wrapped = [(pj.wrap180(lon - meridian), lat) for lon, lat in geo]
            for piece in seam.split(wrapped):
                assert seam.max_edge_lon_span(piece) <= 180.0 + 1e-6
