# WorldMap — DaVinci Resolve Fusion Fuse

A single-node Fusion **Fuse** that renders the Wikimedia *BlankMap-World*
Robinson political world map. It draws every country outline and fills exactly
one selectable country, with full control over projection centring, zoom, pan,
stroke and fill. Output is transparent premultiplied RGBA, ready to composite.

<img width="1920" height="1080" alt="Example Animation South Korea with Inspector Panel" src="https://github.com/user-attachments/assets/529b7f27-706e-4e02-a219-226916458a5c" />


## What it does

- **All country outlines** drawn from the exact source SVG geometry.
- **One selectable country filled** (dropdown, ~257 countries and territories,
  including Taiwan, Kosovo, Crimea, Svalbard, French Guiana, etc.).
- **Constant screen-pixel stroke width** — outlines stay the same thickness on
  screen no matter how far you zoom in.
- **True Robinson re-centring** on any central meridian (not a pixel pan): the
  whole map is re-projected, with **antimeridian seam handling** so nothing
  streaks across the frame when you centre on the Pacific.
- **Transparent RGBA** output for clean compositing.
- Single clean node — no node trees, no per-country nodes.

## Architecture (two stages)

1. **Build time (Python, run once):** `tools/build_worldmap_data.py` parses
   `assets/BlankMap-World.svg`, flattens the Bézier paths, groups them into
   selectable countries, converts every vertex to geographic longitude/latitude
   via an inverse Robinson projection, and writes a compact, deterministic
   `generated/worldmap_data.lua`.
2. **Runtime (Lua, in Fusion):** `Fuses/WorldMap.fuse` loads that data file and
   renders it. **The Fuse never parses SVG** and has no Python dependency.

The projection constants are calibrated against the source map (longitude
residual σ ≈ 0.46°), and because the forward and inverse transforms share the
same constants, re-centring on Greenwich (0°) reproduces the source pixels
exactly.

## Installation

1. Copy `Fuses/WorldMap.fuse` **and** `generated/worldmap_data.lua` into your
   Fusion Fuses folder. The Fuse looks for the data file next to itself first,
   then in a sibling `../generated/` folder.

   | OS      | Fuses folder |
   |---------|--------------|
   | Windows | `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Fuses` |
   | macOS   | `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Fuses` |
   | Linux   | `~/.local/share/DaVinciResolve/Fusion/Fuses` |

   (Standalone Fusion Studio uses the equivalent `Fusion:/Fuses/` path shown in
   *Fusion → Fusion Settings → Path Map*.)

2. Restart DaVinci Resolve / Fusion.
3. In the Fusion page, add the tool from **Add Tool → Creator → World Map**
   (or search "World Map" in the Effects Library).

## Controls

**Projection**
- **Origin** — meridian preset: Greenwich (0°), Asia-Pacific (162°E),
  Pacific (180°E), Americas (90°W), or *Custom*.
- **Custom Meridian** — central meridian in degrees (shown when Origin = Custom).
- **Center** — pan the map (on-screen crosshair), normalised 0–1.
- **Zoom** — 0.01–100×. Geometry scales; stroke width does not.

**Outline**
- **Stroke Color / Stroke Width (px) / Stroke Opacity** — the country borders.
  Width is in **screen pixels** and stays constant across zoom.
- **Draw World Boundary** — draw the outer Robinson ocean frame.
- **Draw Disputed Borders** — draw limited-recognition / disputed border strokes.

**Fill**
- **Country** — the single country to fill (default South Korea).
- **Fill Color / Fill Opacity** — the fill (default red).

## Why the stroke stays constant

When you zoom, only the projected *geometry* is scaled. The stroke is rasterised
at a fixed half-width of `strokeWidth / 2` **output pixels** around each screen
segment, independent of the zoom factor — so a 1 px border is always 1 px on
screen whether you are looking at the whole globe or a single country.

## Regenerating the data

You only need this if you change the source SVG or the flattening quality.

```powershell
python tools/build_worldmap_data.py --quality normal
```

Options: `--quality {draft,normal,high}` (Bézier flattening tolerance),
`--precision N` (decimal places for stored coordinates), `--svg PATH`,
`--out PATH`. The output is deterministic for a given input and options.

The build tool and its library use **only the Python standard library**. The
dev/test extras (pytest, and lupa/Pillow for the optional Lua-runtime preview)
are listed in `requirements-dev.txt`.

## Development

```powershell
pip install -r requirements-dev.txt
python -m pytest tests -q                 # unit + integration tests
python tools/render_previews.py           # render preview PNGs to tests/output/
```

`tools/render_previews.py` executes the *actual* Fuse Lua through a Lua runtime
against a real framebuffer, so the previews faithfully match Fusion output.

## Repository layout

```
assets/BlankMap-World.svg      source map (unmodified)
tools/worldmap/                build-time library (projection, geometry, seam,
                               svg_parser, countries)
tools/build_worldmap_data.py   SVG -> Lua data builder
tools/render_previews.py       Lua-runtime preview renderer
generated/worldmap_data.lua    generated runtime data (DO NOT EDIT)
Fuses/WorldMap.fuse            the Fuse
tests/                         pytest suite (+ tests/output/ renders)
docs/IMPLEMENTATION_PLAN.md    design notes
```

## Supported versions

Developed against DaVinci Resolve 18/19 (Fusion, Lua 5.1 Fuse API). It uses only
stable, long-standing Fuse APIs (`FuRegisterClass`, `AddInput`/`AddOutput`,
`Image`/`Pixel`, `Process`) and should work on any recent Resolve or Fusion
Studio build.

## Limitations

- Rendering is a CPU scanline rasteriser written in Lua, because Fusion exposes
  no public antialiased vector-fill API to Fuses. It is efficient for HD/4K but
  is not GPU-accelerated; very high zoom with maximum quality data is heaviest.
- Stroke antialiasing is a 1 px coverage falloff (crisp, lightweight), not
  multi-sample supersampling.
- Country grouping follows the source SVG's own `<title>` structure; entities
  the map author did not title separately are not independently selectable.

## Troubleshooting

- **"data not loaded" / blank frame** — `generated/worldmap_data.lua` is not
  next to the `.fuse` (or in a sibling `../generated/`). Copy it there, or run
  the build tool. The Fuse prints the paths it tried to the Console.
- **Country list empty** — same cause: the data file could not be loaded.
- **Nothing fills** — check Fill Opacity > 0 and that a valid country is
  selected.

See `LICENSES.md` for map and code licensing and `CHANGELOG.md` for history.
