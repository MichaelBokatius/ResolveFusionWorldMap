"""Low-level helpers for reading ``BlankMap-World.svg`` with ElementTree."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Iterator, Set

SVG_NS = "http://www.w3.org/2000/svg"
NS = "{%s}" % SVG_NS


def local(tag: str) -> str:
    """Strip the XML namespace from a tag name."""
    return tag.split("}", 1)[-1] if "}" in tag else tag


def load(path: str) -> ET.Element:
    """Parse the SVG file and return its root element."""
    return ET.parse(path).getroot()


def classes_of(el: ET.Element) -> Set[str]:
    """Return the set of CSS class tokens on an element."""
    cls = el.get("class")
    return set(cls.split()) if cls else set()


def direct_title(el: ET.Element) -> str | None:
    """Return the text of a direct ``<title>`` child, if present."""
    t = el.find(f"{NS}title")
    return t.text.strip() if t is not None and t.text else None


def iter_child_elements(el: ET.Element) -> Iterator[ET.Element]:
    """Yield direct child elements."""
    for child in el:
        yield child


def descendant_path_classes(el: ET.Element) -> Set[str]:
    """Union of class tokens on every ``<path>`` in the subtree."""
    out: Set[str] = set()
    for p in el.iter(f"{NS}path"):
        out |= classes_of(p)
    return out
