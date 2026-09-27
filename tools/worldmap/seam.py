"""Antimeridian (dateline) handling for re-centred geographic polylines.

After a polyline's longitudes are shifted by the chosen central meridian and
wrapped into ``[-180, 180)``, an edge whose endpoints differ by more than 180
degrees is a *seam crossing*: on screen it would draw a spurious segment across
the whole frame.  :func:`split` breaks such polylines into pieces at the seam,
interpolating the latitude at the crossing, so the renderer never connects two
points across the map.  This is what keeps Russia, Alaska/Aleutians, Fiji and
the Pacific island chains intact when the map is re-centred.
"""

from __future__ import annotations

from typing import List, Tuple

Point = Tuple[float, float]  # (lon, lat)
Contour = List[Point]

SEAM = 180.0


def _crossing_latitude(a: Point, b: Point) -> Tuple[float, float, float]:
    """Return ``(seam_a, seam_b, lat)`` for an edge that crosses the seam.

    ``seam_a`` is the +/-180 boundary the edge leaves through from ``a`` and
    ``seam_b = -seam_a`` is where it re-enters toward ``b``; ``lat`` is the
    interpolated latitude at that crossing.
    """
    a_lon, a_lat = a
    b_lon, b_lat = b
    # Unwrap b relative to a so the edge is monotonic in longitude.
    b_un = b_lon
    while b_un - a_lon > 180.0:
        b_un -= 360.0
    while b_un - a_lon < -180.0:
        b_un += 360.0
    seam_a = 180.0 if b_un > a_lon else -180.0
    span = b_un - a_lon
    if abs(span) < 1e-12:
        t = 0.0
    else:
        t = (seam_a - a_lon) / span
    t = min(1.0, max(0.0, t))
    lat = a_lat + t * (b_lat - a_lat)
    return seam_a, -seam_a, lat


def crosses(a: Point, b: Point) -> bool:
    """True if the edge ``a -> b`` jumps across the seam."""
    return abs(b[0] - a[0]) > 180.0


def split(contour: Contour) -> List[Contour]:
    """Split a wrapped polyline into seam-free pieces.

    Input longitudes must already be wrapped into ``[-180, 180)``.  Output
    pieces contain no edge spanning the seam; crossing points are added exactly
    on the ``+/-180`` boundary with interpolated latitude.
    """
    if len(contour) < 2:
        return [list(contour)] if contour else []
    pieces: List[Contour] = []
    cur: Contour = [contour[0]]
    for i in range(1, len(contour)):
        a = contour[i - 1]
        b = contour[i]
        if crosses(a, b):
            seam_a, seam_b, lat = _crossing_latitude(a, b)
            cur.append((seam_a, lat))
            pieces.append(cur)
            cur = [(seam_b, lat), b]
        else:
            cur.append(b)
    if cur:
        pieces.append(cur)
    return pieces


def max_edge_lon_span(contour: Contour) -> float:
    """Largest absolute longitude jump between consecutive points (degrees)."""
    if len(contour) < 2:
        return 0.0
    return max(abs(contour[i][0] - contour[i - 1][0]) for i in range(1, len(contour)))
