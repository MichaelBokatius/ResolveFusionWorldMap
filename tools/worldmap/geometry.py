"""SVG path parsing and adaptive cubic-Bezier flattening.

Only the path commands actually present in ``BlankMap-World.svg`` are needed
(``M m L l H h V v C c Z z``), but ``S s Q q T t A a`` are handled defensively
so the parser degrades gracefully on future map revisions.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import List, Tuple

Point = Tuple[float, float]
Contour = List[Point]

_TOKEN_RE = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|-?\d*\.?\d+(?:[eE][-+]?\d+)?")


@dataclass
class FlattenOptions:
    """Curve-flattening quality knobs (pixel units)."""

    tolerance_px: float = 0.35
    max_depth: int = 16


def _flatten_cubic(
    p0: Point, p1: Point, p2: Point, p3: Point,
    tol: float, depth: int, out: Contour,
) -> None:
    """Recursively subdivide a cubic Bezier until flat, appending to ``out``.

    ``p0`` is assumed already present in ``out``; only interior/end points are
    appended.
    """
    # Distance of control points from the p0-p3 chord (flatness metric).
    x0, y0 = p0
    x3, y3 = p3
    dx, dy = x3 - x0, y3 - y0
    denom = dx * dx + dy * dy
    if denom < 1e-12:
        d1 = math.hypot(p1[0] - x0, p1[1] - y0)
        d2 = math.hypot(p2[0] - x0, p2[1] - y0)
        flat = max(d1, d2)
    else:
        d1 = abs((p1[0] - x0) * dy - (p1[1] - y0) * dx)
        d2 = abs((p2[0] - x0) * dy - (p2[1] - y0) * dx)
        flat = (d1 + d2) / math.sqrt(denom)
    if flat <= tol or depth >= 16:
        out.append(p3)
        return
    # de Casteljau split at t = 0.5
    p01 = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    p12 = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    p23 = ((p2[0] + p3[0]) / 2, (p2[1] + p3[1]) / 2)
    p012 = ((p01[0] + p12[0]) / 2, (p01[1] + p12[1]) / 2)
    p123 = ((p12[0] + p23[0]) / 2, (p12[1] + p23[1]) / 2)
    mid = ((p012[0] + p123[0]) / 2, (p012[1] + p123[1]) / 2)
    _flatten_cubic(p0, p01, p012, mid, tol, depth + 1, out)
    _flatten_cubic(mid, p123, p23, p3, tol, depth + 1, out)


def parse_path(d: str, opts: FlattenOptions | None = None) -> List[Contour]:
    """Parse an SVG path ``d`` string into flattened absolute contours.

    Each contour is a list of ``(x, y)`` points in the SVG's own pixel space.
    Sub-paths (``M``) start new contours; ``Z`` closes the current one.
    """
    if opts is None:
        opts = FlattenOptions()
    tol = opts.tolerance_px
    toks = _TOKEN_RE.findall(d)
    i = 0
    n = len(toks)
    contours: List[Contour] = []
    cur: Contour = []
    cx = cy = 0.0
    sx = sy = 0.0
    # last control point for smooth curve reflection
    last_c2: Point | None = None
    last_q: Point | None = None
    cmd = ""

    def num() -> float:
        nonlocal i
        v = float(toks[i])
        i += 1
        return v

    def start_contour(x: float, y: float) -> None:
        nonlocal cur
        if cur:
            contours.append(cur)
        cur = [(x, y)]

    while i < n:
        tok = toks[i]
        if tok.isalpha():
            cmd = tok
            i += 1
            if cmd in "Zz":
                if cur:
                    cur.append((sx, sy))
                cx, cy = sx, sy
                last_c2 = last_q = None
            continue
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            x = num(); y = num()
            if rel:
                x += cx; y += cy
            cx, cy = x, y
            sx, sy = x, y
            start_contour(cx, cy)
            cmd = "l" if rel else "L"  # subsequent implicit lineto
            last_c2 = last_q = None
        elif c == "L":
            x = num(); y = num()
            if rel:
                x += cx; y += cy
            cx, cy = x, y
            cur.append((cx, cy))
            last_c2 = last_q = None
        elif c == "H":
            x = num()
            if rel:
                x += cx
            cx = x
            cur.append((cx, cy))
            last_c2 = last_q = None
        elif c == "V":
            y = num()
            if rel:
                y += cy
            cy = y
            cur.append((cx, cy))
            last_c2 = last_q = None
        elif c == "C":
            x1 = num(); y1 = num(); x2 = num(); y2 = num(); x = num(); y = num()
            if rel:
                x1 += cx; y1 += cy; x2 += cx; y2 += cy; x += cx; y += cy
            _flatten_cubic((cx, cy), (x1, y1), (x2, y2), (x, y), tol, 0, cur)
            cx, cy = x, y
            last_c2 = (x2, y2)
            last_q = None
        elif c == "S":
            x2 = num(); y2 = num(); x = num(); y = num()
            if rel:
                x2 += cx; y2 += cy; x += cx; y += cy
            if last_c2 is not None:
                x1 = 2 * cx - last_c2[0]; y1 = 2 * cy - last_c2[1]
            else:
                x1, y1 = cx, cy
            _flatten_cubic((cx, cy), (x1, y1), (x2, y2), (x, y), tol, 0, cur)
            cx, cy = x, y
            last_c2 = (x2, y2)
            last_q = None
        elif c == "Q":
            qx = num(); qy = num(); x = num(); y = num()
            if rel:
                qx += cx; qy += cy; x += cx; y += cy
            # elevate quadratic to cubic
            c1 = (cx + 2 / 3 * (qx - cx), cy + 2 / 3 * (qy - cy))
            c2 = (x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y))
            _flatten_cubic((cx, cy), c1, c2, (x, y), tol, 0, cur)
            cx, cy = x, y
            last_q = (qx, qy)
            last_c2 = None
        elif c == "T":
            x = num(); y = num()
            if rel:
                x += cx; y += cy
            if last_q is not None:
                qx = 2 * cx - last_q[0]; qy = 2 * cy - last_q[1]
            else:
                qx, qy = cx, cy
            c1 = (cx + 2 / 3 * (qx - cx), cy + 2 / 3 * (qy - cy))
            c2 = (x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y))
            _flatten_cubic((cx, cy), c1, c2, (x, y), tol, 0, cur)
            cx, cy = x, y
            last_q = (qx, qy)
            last_c2 = None
        elif c == "A":
            # Arc: flatten crudely to the endpoint (not used by this map).
            num(); num(); num(); num(); num()
            x = num(); y = num()
            if rel:
                x += cx; y += cy
            cx, cy = x, y
            cur.append((cx, cy))
            last_c2 = last_q = None
        else:  # unknown token stream; abort to stay deterministic
            break
    if cur:
        contours.append(cur)
    return [c for c in contours if len(c) >= 2]
