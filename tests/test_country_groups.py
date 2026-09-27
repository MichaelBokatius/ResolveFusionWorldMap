"""Country grouping: selectability, separation and uniqueness."""

import pytest

from conftest import SVG_PATH
from worldmap import svg_parser as sp
from worldmap.countries import build_countries
from worldmap.geometry import FlattenOptions


@pytest.fixture(scope="module")
def grouped():
    root = sp.load(str(SVG_PATH))
    countries, world, disputed = build_countries(root, FlattenOptions(0.8))
    by_code = {c.code: c for c in countries}
    return countries, world, disputed, by_code


REQUIRED = ["kr", "kp", "jp", "us", "ru", "de", "fr", "cn", "in"]


@pytest.mark.parametrize("code", REQUIRED)
def test_required_countries_present(grouped, code):
    _, _, _, by_code = grouped
    assert code in by_code
    assert by_code[code].vertex_count > 0


def test_no_duplicate_selector_ids(grouped):
    countries, _, _, _ = grouped
    codes = [c.code for c in countries]
    assert len(codes) == len(set(codes))


def test_south_korea_distinct_from_north(grouped):
    _, _, _, by_code = grouped
    kr, kp = by_code["kr"], by_code["kp"]
    assert kr.name != kp.name
    # Their fill geometry must not be shared object instances.
    assert kr.polys_px is not kp.polys_px
    assert kr.vertex_count > 0 and kp.vertex_count > 0


def test_titled_subterritories_split_out(grouped):
    _, _, _, by_code = grouped
    for code in ("tw", "xk", "xq", "xv", "gf"):
        assert code in by_code, f"missing separate territory {code}"


def test_cnx_folds_into_china(grouped):
    _, _, _, by_code = grouped
    assert "cn" in by_code
    assert "cnx" not in by_code  # same canonical code as China


def test_kinds(grouped):
    _, _, _, by_code = grouped
    assert by_code["aq"].kind == "ant"
    assert by_code["xk"].kind == "limit"
    assert by_code["us"].kind == "land"


def test_world_outline_present(grouped):
    _, world, _, _ = grouped
    assert world is not None
    assert world.vertex_count > 100


def test_multipart_country_retains_all_parts(grouped):
    # Japan/US/Russia are multi-island; must keep many vertices, not just one ring.
    _, _, _, by_code = grouped
    assert by_code["jp"].vertex_count > 50
    assert len(by_code["us"].polys_px) > 3
