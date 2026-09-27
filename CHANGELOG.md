# Changelog

All notable changes to this project are documented here.
This project adheres to a simple Keep-a-Changelog style.

## [1.0.0] — Initial release

### Added
- `Fuses/WorldMap.fuse` — single-node Fusion Fuse rendering the Robinson
  political world map: draws all country outlines and fills one selectable
  country, with transparent premultiplied RGBA output.
  - Controls: Origin (meridian presets + Custom), Custom Meridian, Center (pan),
    Zoom, Stroke Color/Width/Opacity, Draw World Boundary, Draw Disputed
    Borders, Country selector, Fill Color/Opacity.
  - Constant screen-pixel stroke width at any zoom level.
  - True Robinson re-centring on any central meridian with antimeridian seam
    splitting (no frame-spanning artifacts).
  - CPU scanline fill + antialiased polyline stroke.
  - Graceful failure to a transparent frame with a Console message if the data
    file is missing; invalid country selection falls back to a default.
- Build pipeline (`tools/`):
  - `worldmap` library: `projection`, `geometry`, `seam`, `svg_parser`,
    `countries`.
  - `build_worldmap_data.py` — converts `assets/BlankMap-World.svg` into a
    compact, deterministic `generated/worldmap_data.lua`.
  - `render_previews.py` — renders faithful preview PNGs by running the real
    Fuse Lua through a Lua runtime.
- `generated/worldmap_data.lua` — 257 selectable countries/territories.
- Test suite (`tests/`): projection round-trip and presets, SVG/geometry
  parsing, country grouping and uniqueness, antimeridian seam behaviour,
  constant stroke-width maths, generated-data structure, and end-to-end Fuse
  execution.
- Documentation: `README.md`, `LICENSES.md`, `docs/IMPLEMENTATION_PLAN.md`,
  `requirements-dev.txt`.

### Calibration
- Robinson pixel mapping calibrated to the source map
  (CX=1302.75, KX=439.11, CY=698.79, KY=697.77), longitude residual σ ≈ 0.46°;
  Greenwich (0°) re-projection reproduces the source pixels exactly.
