# Licensing

## Source map: `assets/BlankMap-World.svg`

The base map is the Wikimedia Commons **BlankMap-World** (Robinson projection)
political world map. On Wikimedia Commons this map is published in the **public
domain** (released by its authors), and the underlying country geometry is
factual data. It is included here unmodified as the geometry source.

If you redistribute this project, please retain attribution to Wikimedia
Commons / the BlankMap-World authors as a courtesy, and verify the current
status of the specific file on its Commons description page.

## Generated data: `generated/worldmap_data.lua`

Produced mechanically from the source SVG by `tools/build_worldmap_data.py`. It
is a coordinate transformation (SVG pixels → geographic lon/lat via an
independent Robinson implementation) and carries the same status as the source
map geometry.

## This project's code

The Fuse (`Fuses/WorldMap.fuse`), the Python build tools (`tools/`) and tests
(`tests/`) are original work for this repository.

### Independent implementation note

The Robinson forward/inverse projection, the SVG path flattening, the
country-grouping logic and the CPU rasteriser were implemented independently
from published references (the Robinson lookup table values are the standard
Wikipedia/NEC constants, which are factual). **No third-party GPL or other
copyleft code was copied** into this project. In particular, no code from any
existing "nugsl" / worldmap Python tool was used; such tools served only as a
behavioural/mathematical reference.

If you intend to redistribute, choose a license for the original code
(e.g. MIT) and add it here; the map geometry's public-domain status is
independent of your code license.
