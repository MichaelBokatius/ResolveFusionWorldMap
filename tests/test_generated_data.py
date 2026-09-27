"""Validate the generated Lua data file: presence, header and structure.

The runtime Fuse loads this file, so it must exist, carry the DO-NOT-EDIT
warning and the expected top-level tables.  We validate structurally (regex),
and if a ``lua`` interpreter is available we additionally parse it for real.
"""

import re
import shutil
import subprocess

import pytest

from conftest import REPO_ROOT

DATA = REPO_ROOT / "generated" / "worldmap_data.lua"


@pytest.fixture(scope="module")
def text():
    if not DATA.exists():
        pytest.skip("generated/worldmap_data.lua not built")
    return DATA.read_text(encoding="utf-8")


def test_has_do_not_edit_header(text):
    assert "DO NOT EDIT" in text.splitlines()[2].upper() or "DO NOT EDIT" in text[:400].upper()


def test_declares_expected_tables(text):
    for token in ("M.meta", "M.robinson", "M.world", "M.countries", "return M"):
        assert token in text, f"missing {token}"


def test_meta_has_calibration(text):
    for key in ("projection", "CX=", "KX=", "CY=", "KY=", "src_hash="):
        assert key in text, f"meta missing {key}"


def test_contains_required_country_codes(text):
    for code in ("kr", "kp", "jp", "us", "ru", "tw"):
        assert re.search(rf'code="{code}"', text), f"country {code} not in data"


def test_parses_as_lua_if_interpreter_available(text):
    lua = shutil.which("lua") or shutil.which("lua5.1")
    if not lua:
        pytest.skip("no lua interpreter on PATH")
    script = (
        f'local M = dofile([[{DATA.as_posix()}]]); '
        'assert(type(M.countries) == "table"); '
        'assert(#M.countries > 100); '
        'assert(type(M.meta.CX) == "number"); '
        'print("ok", #M.countries)'
    )
    result = subprocess.run([lua, "-e", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
