"""Reusable pieces of the WorldMap build pipeline.

Kept as small, independently testable modules:

* :mod:`projection` – Robinson forward/inverse and re-centering maths.
* :mod:`geometry`   – SVG path parsing and adaptive Bezier flattening.
* :mod:`seam`       – antimeridian (dateline) splitting of polylines.
* :mod:`svg_parser` – turn the Wikimedia SVG into structured records.
* :mod:`countries`  – group records into selectable countries/territories.
"""

from __future__ import annotations

__all__ = [
    "projection",
    "geometry",
    "seam",
    "svg_parser",
    "countries",
]
