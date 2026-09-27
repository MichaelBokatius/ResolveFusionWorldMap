"""Group parsed SVG paths into selectable countries and territories.

Grouping rule (derived from the real source structure — see
``docs/IMPLEMENTATION_PLAN.md``):

* The SVG author marks every selectable entity with a direct ``<title>`` child.
  An element (``<g>`` or ``<path>``) that owns a title starts a new entity keyed
  by the canonical form of its ``id``.
* An entity is *distinct* from its titled ancestor only when its canonical code
  differs.  This folds same-country duplicates such as ``cnx`` (China PRC) into
  ``cn`` while splitting genuinely separate titled territories such as ``tw``
  (Taiwan), ``xq`` (Crimea), ``xv`` (Svalbard) and ``gf`` (French Guiana).
* Fill geometry is every descendant ``<path>`` that is not inside a deeper
  distinct entity.  ``limitxx`` overlay strokes inside a *land* country are
  routed to a separate ``disputed`` collection (for the optional disputed-border
  overlay); for a limited-recognition territory that is itself titled (Kosovo,
  Abkhazia, ...) those ``limitxx`` paths are its fill.
* The ocean boundary (``id="ocean"`` / ``oceanxx``) is returned separately as
  the world outline.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from . import svg_parser as sp
from .geometry import Contour, FlattenOptions, parse_path

# Fallback English names for codes whose SVG element lacks a <title>.
ISO_NAMES: Dict[str, str] = {
    "xk": "Kosovo", "xc": "Northern Cyprus", "xa": "Abkhazia",
    "xo": "South Ossetia", "xn": "Nagorno-Karabakh", "xp": "Transnistria",
    "xs": "Somaliland", "xq": "Crimea", "xv": "Svalbard",
}

_FILL_CLASSES = {"landxx", "coastxx", "antxx"}


@dataclass
class Country:
    """A selectable country or territory with grouped fill geometry (pixels)."""

    code: str
    name: str
    kind: str = "land"  # "land" | "ant" | "limit" | "ocean"
    polys_px: List[Contour] = field(default_factory=list)
    classes: Set[str] = field(default_factory=set)

    @property
    def vertex_count(self) -> int:
        return sum(len(c) for c in self.polys_px)


def canonical_code(code: str | None, parent: str | None) -> str | None:
    """Normalise a code so a country's own sub-parts fold into the parent.

    Trailing ``-`` is stripped (``ma-`` -> ``ma``); a ``<parent>x`` id such as
    ``cnx``/``frx``/``nlx`` folds to ``<parent>``.
    """
    if not code:
        return parent
    c = code.rstrip("-")
    if parent and c == parent + "x":
        return parent
    return c


def _kind_from_classes(classes: Set[str]) -> str:
    if "antxx" in classes:
        return "ant"
    if classes & {"landxx", "coastxx"}:
        return "land"
    if "limitxx" in classes:
        return "limit"
    return "land"


def _is_fill_path(cls: Set[str], owner_kind: str) -> bool:
    """A path is fill unless it is a bare ``limitxx`` overlay on a land country."""
    if "limitxx" in cls and not (cls & _FILL_CLASSES):
        return owner_kind == "limit"
    return True


def _get_or_create(
    registry: Dict[str, Country],
    order: List[Country],
    code: str,
    title: str | None,
    cls: Set[str],
) -> Country:
    c = registry.get(code)
    if c is None:
        name = title or ISO_NAMES.get(code, code.upper())
        c = Country(code=code, name=name, kind=_kind_from_classes(cls),
                    classes=set(cls))
        registry[code] = c
        order.append(c)
    else:
        c.classes |= cls
        if title and (c.name == code.upper() or c.name == ISO_NAMES.get(code)):
            c.name = title
        c.kind = _kind_from_classes(c.classes)
    return c


def _add_path(
    country: Country,
    el: ET.Element,
    cls: Set[str],
    disputed: List[Contour],
    opts: FlattenOptions,
) -> None:
    d = el.get("d")
    if not d:
        return
    contours = parse_path(d, opts)
    if _is_fill_path(cls, country.kind):
        country.polys_px.extend(contours)
    else:
        disputed.extend(contours)


def _walk(
    el: ET.Element,
    owner_code: str | None,
    owner: Country | None,
    registry: Dict[str, Country],
    order: List[Country],
    disputed: List[Contour],
    world_ref: List[Country],
    opts: FlattenOptions,
) -> None:
    for child in sp.iter_child_elements(el):
        tag = sp.local(child.tag)
        if tag not in ("g", "path"):
            continue
        cls = sp.classes_of(child)
        title = sp.direct_title(child)
        cid = child.get("id")

        # Ocean boundary: capture as the world outline, do not treat as owner.
        if owner is None and (cid == "ocean" or "oceanxx" in cls):
            world = world_ref[0]
            world.classes |= cls
            if tag == "path":
                if child.get("d"):
                    world.polys_px.extend(parse_path(child.get("d"), opts))
            else:
                _walk(child, "ocean", world, registry, order, disputed,
                      world_ref, opts)
            continue

        if title is not None:
            canon = canonical_code(cid, owner_code)
            if canon and canon != owner_code:
                entity = _get_or_create(registry, order, canon, title, cls)
                if tag == "path":
                    _add_path(entity, child, cls, disputed, opts)
                else:
                    _walk(child, canon, entity, registry, order, disputed,
                          world_ref, opts)
                continue

        # Not a distinct new entity: belongs to the current owner.
        if owner is not None:
            owner.classes |= cls
            owner.kind = _kind_from_classes(owner.classes)
        if tag == "path":
            if owner is not None:
                _add_path(owner, child, cls, disputed, opts)
        else:
            _walk(child, owner_code, owner, registry, order, disputed,
                  world_ref, opts)


def build_countries(
    root: ET.Element, opts: FlattenOptions | None = None
) -> Tuple[List[Country], Country | None, List[Contour]]:
    """Return ``(countries, world_outline, disputed)`` from the SVG root.

    * ``countries`` — selectable entities in document order (each with a unique
      canonical code and its grouped fill geometry, in SVG pixels).
    * ``world_outline`` — the ocean boundary, or ``None`` if absent.
    * ``disputed`` — flattened pixel contours of ``limitxx`` disputed borders.
    """
    if opts is None:
        opts = FlattenOptions()
    registry: Dict[str, Country] = {}
    order: List[Country] = []
    disputed: List[Contour] = []
    world = Country(code="ocean", name="World Boundary", kind="ocean")
    world_ref = [world]

    _walk(root, None, None, registry, order, disputed, world_ref, opts)

    countries = [c for c in order if c.polys_px]
    world_out = world if world.polys_px else None
    return countries, world_out, disputed
