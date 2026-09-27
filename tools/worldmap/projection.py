"""Robinson projection maths for the Wikimedia ``BlankMap-World.svg``.

The map is a standard Robinson projection with central meridian 0 (Greenwich).
The pixel mapping (validated by least squares against 29 single-part country
area centroids, longitude residual sigma = 0.46 deg) is::

    px = CX + KX * X(lat) * radians(lon)
    py = CY - KY * Y(lat) * sign(lat)

where ``X`` / ``Y`` come from the Robinson lookup table.  Because the forward
and inverse transforms share the same constants the round trip is numerically
exact, so re-projecting at central meridian 0 reproduces the source pixels.
"""

from __future__ import annotations

import math
from typing import Tuple

# --- Calibration constants (see docs/IMPLEMENTATION_PLAN.md) -----------------
CX = 1302.75
KX = 439.11
CY = 698.79
KY = 697.77

SVG_WIDTH = 2754.0
SVG_HEIGHT = 1398.0

# Robinson table: latitude(deg) -> (X = parallel length, Y = meridian distance).
# Standard Wikipedia / NEC values, 0..90 in 5 degree steps.
_ROBINSON = (
    (0.0, 1.0000, 0.0000), (5.0, 0.9986, 0.0620), (10.0, 0.9954, 0.1240),
    (15.0, 0.9900, 0.1860), (20.0, 0.9822, 0.2480), (25.0, 0.9730, 0.3100),
    (30.0, 0.9600, 0.3720), (35.0, 0.9427, 0.4340), (40.0, 0.9216, 0.4958),
    (45.0, 0.8962, 0.5571), (50.0, 0.8679, 0.6176), (55.0, 0.8350, 0.6769),
    (60.0, 0.7986, 0.7346), (65.0, 0.7597, 0.7903), (70.0, 0.7186, 0.8435),
    (75.0, 0.6732, 0.8936), (80.0, 0.6213, 0.9394), (85.0, 0.5722, 0.9761),
    (90.0, 0.5322, 1.0000),
)

LATS: Tuple[float, ...] = tuple(r[0] for r in _ROBINSON)
XS: Tuple[float, ...] = tuple(r[1] for r in _ROBINSON)
YS: Tuple[float, ...] = tuple(r[2] for r in _ROBINSON)


def _interp(arr: Tuple[float, ...], lat: float) -> float:
    """Linearly interpolate a Robinson column at ``lat`` (degrees)."""
    lat = abs(lat)
    if lat >= 90.0:
        return arr[-1]
    i = int(lat // 5.0)
    t = (lat - LATS[i]) / 5.0
    return arr[i] * (1.0 - t) + arr[i + 1] * t


def x_factor(lat: float) -> float:
    """Robinson parallel-length factor at latitude ``lat``."""
    return _interp(XS, lat)


def y_factor(lat: float) -> float:
    """Robinson meridian-distance factor at latitude ``lat``."""
    return _interp(YS, lat)


def wrap180(lon: float) -> float:
    """Wrap a longitude into the half-open range [-180, 180)."""
    return (lon + 180.0) % 360.0 - 180.0


def forward(lon: float, lat: float) -> Tuple[float, float]:
    """Project geographic ``(lon, lat)`` degrees to SVG pixel ``(px, py)``."""
    xf = x_factor(lat)
    yf = y_factor(lat)
    px = CX + KX * xf * math.radians(lon)
    py = CY - KY * yf * (1.0 if lat >= 0.0 else -1.0)
    return px, py


def inverse(px: float, py: float) -> Tuple[float, float]:
    """Un-project an SVG pixel ``(px, py)`` back to geographic ``(lon, lat)``."""
    yr = (CY - py) / KY  # target Y-factor magnitude, signed
    mag = min(abs(yr), 1.0)
    lat = 90.0
    for i in range(len(YS) - 1):
        if YS[i] <= mag <= YS[i + 1]:
            t = (mag - YS[i]) / (YS[i + 1] - YS[i])
            lat = LATS[i] * (1.0 - t) + LATS[i + 1] * t
            break
    if yr < 0.0:
        lat = -lat
    xf = x_factor(lat)
    lon = math.degrees((px - CX) / (KX * xf))
    return lon, lat


def forward_norm(lon: float, lat: float) -> Tuple[float, float]:
    """Project to normalised map space in ``[0, 1]`` (y down, like the SVG)."""
    px, py = forward(lon, lat)
    return px / SVG_WIDTH, py / SVG_HEIGHT
