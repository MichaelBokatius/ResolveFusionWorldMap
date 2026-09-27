"""Render preview PNGs by executing the real WorldMap.fuse under a Lua runtime.

This drives the actual Fuse code (projection, seam split, fill and stroke) with
a real RGBA framebuffer, so the PNGs are faithful previews of what Fusion will
produce.  It is both a manual visual check and part of the validation suite.

Run:  python tools/render_previews.py
Output: tests/output/*.png
"""

import sys
from pathlib import Path

from lupa import LuaRuntime
from PIL import Image as PILImage

REPO = Path(__file__).resolve().parent.parent
FUSE = REPO / "Fuses" / "WorldMap.fuse"
OUT = REPO / "tests" / "output"

# Preset (label, origin_index, custom_meridian) and country code samples.
PRESETS = [
    ("greenwich", 0, 0.0),
    ("asia_pacific_162e", 1, 0.0),
    ("pacific_180e", 2, 0.0),
    ("americas_90w", 3, 0.0),
]
COUNTRIES = ["kr", "jp", "de", "us", "ru"]

W, H = 1102, 560  # ~ half the source resolution, 2:1-ish


def build_runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(r"""
CT_Tool = "CT_Tool"
function FuRegisterClass(name, ctype, regs) _registered = name end

local Input = {}; Input.__index = Input
function Input.new(d) return setmetatable({_v = d or 0, _x = 0.5, _y = 0.5}, Input) end
function Input:GetValue(req) return { Value = self._v, X = self._x, Y = self._y } end
function Input:SetAttrs(a) end

local Output = {}; Output.__index = Output
function Output.new() return setmetatable({}, Output) end
function Output:Set(req, img) _last_output = img end

self = {}; self.Comp = {}; self.Inputs = {}
function self:AddInput(name, id, attrs)
    local i = Input.new(attrs and attrs.INP_Default or 0)
    if attrs and attrs.INP_DefaultX then i._x = attrs.INP_DefaultX end
    if attrs and attrs.INP_DefaultY then i._y = attrs.INP_DefaultY end
    self.Inputs[id] = i; return i
end
function self:AddOutput(n, id, a) return Output.new() end
function self:BeginControlNest(...) end
function self:EndControlNest(...) end

local Req = {}; Req.__index = Req
function Req.new() return setmetatable({}, Req) end
function Req:IsQuick() return false end
function Req:IsNoMotionBlur() return true end
function Req:IsStampOnly() return false end
_req_factory = Req.new

function Pixel(t) return { R = (t and t.R) or 0, G = (t and t.G) or 0, B = (t and t.B) or 0, A = (t and t.A) or 0 } end

local Img = {}; Img.__index = Img
function Image(attrs)
    local w, h = attrs.IMG_Width, attrs.IMG_Height
    return setmetatable({ w = w, h = h, R = {}, G = {}, B = {}, A = {} }, Img)
end
function Img:Clear() end
function Img:Fill(p)
    for i = 0, self.w * self.h - 1 do
        self.R[i] = p.R; self.G[i] = p.G; self.B[i] = p.B; self.A[i] = p.A
    end
end
local function idx(self, x, y) return y * self.w + x end
function Img:GetPixel(x, y, p)
    local i = idx(self, x, y)
    p.R = self.R[i] or 0; p.G = self.G[i] or 0
    p.B = self.B[i] or 0; p.A = self.A[i] or 0
    return true
end
function Img:SetPixel(x, y, p)
    local i = idx(self, x, y)
    self.R[i] = p.R; self.G[i] = p.G; self.B[i] = p.B; self.A[i] = p.A
    return true
end

XScale, YScale = 1, 1
XAspect, YAspect = 1, 1
""")
    lua.globals().Width = W
    lua.globals().Height = H
    src = FUSE.read_text(encoding="utf-8")
    compile_fuse = lua.eval(
        "function(code, name) local f, e = load(code, name); return f, (e or false) end"
    )
    fn, err = compile_fuse("do " + src + "\nend",
                           "@" + str(FUSE).replace("\\", "/"))
    if fn is None:
        raise RuntimeError("Fuse failed to compile: %s" % err)
    fn()
    lua.eval("Create")()
    return lua


def combo_order(lua):
    """Reproduce the Fuse's combo order: non-ocean countries sorted by name."""
    data_path = (REPO / "generated" / "worldmap_data.lua").as_posix()
    mod = lua.eval("function(p) return dofile(p) end")(data_path)
    entries = []
    n = len(list(mod.countries.items()))
    for i in range(1, n + 1):
        c = mod.countries[i]
        if c.kind != "ocean":
            entries.append((c.name, c.code))
    entries.sort(key=lambda e: e[0].lower())
    return [code for _, code in entries]


def country_combo_index(order, code):
    for i, c in enumerate(order):
        if c == code:
            return i  # combo is 0-based
    return 0


def city_combo_index(lua, name):
    """Combo value for a city by name (0 = none, 1..N follow cities_data order)."""
    data_path = (REPO / "generated" / "cities_data.lua").as_posix()
    mod = lua.eval("function(p) return dofile(p) end")(data_path)
    cities = mod.cities
    n = len(list(cities.items()))
    for i in range(1, n + 1):
        if cities[i].name == name:
            return i
    return 0


def set_input(lua, iid, value):
    lua.globals().self.Inputs[iid]._v = value


def render(lua):
    req = lua.eval("_req_factory")()
    lua.eval("Process")(req)
    img = lua.eval("_last_output")
    out = PILImage.new("RGBA", (W, H))
    px = out.load()
    R, G, B, A = img.R, img.G, img.B, img.A
    for y in range(H):
        base = y * W
        for x in range(W):
            i = base + x
            a = A[i] or 0.0
            r = R[i] or 0.0
            g = G[i] or 0.0
            b = B[i] or 0.0
            # stored premultiplied -> un-premultiply for display
            if a > 0.0:
                r, g, b = r / a, g / a, b / a
            # Fuse writes with a bottom-left origin (Fusion convention); flip
            # back to top-left for the PNG so previews match Fusion's display.
            px[x, H - 1 - y] = (
                min(255, int(r * 255 + 0.5)),
                min(255, int(g * 255 + 0.5)),
                min(255, int(b * 255 + 0.5)),
                min(255, int(a * 255 + 0.5)),
            )
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    lua = build_runtime()
    order = combo_order(lua)

    # 1) Each meridian preset, highlighting South Korea.
    kr = country_combo_index(order, "kr")
    for label, origin, custom in PRESETS:
        set_input(lua, "Origin", origin)
        set_input(lua, "CustomMeridian", custom)
        set_input(lua, "Country", kr)
        img = render(lua)
        p = OUT / f"preset_{label}_kr.png"
        img.save(p)
        print("wrote", p.name)

    # 2) Greenwich, highlighting each sample country.
    set_input(lua, "Origin", 0)
    for code in COUNTRIES:
        set_input(lua, "Country", country_combo_index(order, code))
        img = render(lua)
        p = OUT / f"greenwich_{code}.png"
        img.save(p)
        print("wrote", p.name)

    # 3) City marker dot: Seoul on a Korea-filled Greenwich map.
    set_input(lua, "Country", kr)
    set_input(lua, "City", city_combo_index(lua, "Seoul"))
    img = render(lua)
    p = OUT / "greenwich_kr_seoul.png"
    img.save(p)
    print("wrote", p.name)
    set_input(lua, "City", 0)

    # 4) Custom-position dot (a city not in the list): 48.85N, 2.35E (Paris).
    set_input(lua, "UseCustomDot", 1)
    set_input(lua, "CustomLat", 48.85)
    set_input(lua, "CustomLon", 2.35)
    img = render(lua)
    p = OUT / "greenwich_custom_dot.png"
    img.save(p)
    print("wrote", p.name)
    set_input(lua, "UseCustomDot", 0)

    # 5) All-country base fill (light grey) with Korea overwritten by its fill.
    set_input(lua, "Country", kr)
    set_input(lua, "BaseFillOpacity", 1.0)
    img = render(lua)
    p = OUT / "greenwich_basefill.png"
    img.save(p)
    print("wrote", p.name)
    set_input(lua, "BaseFillOpacity", 0.0)

    print("previews in", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
