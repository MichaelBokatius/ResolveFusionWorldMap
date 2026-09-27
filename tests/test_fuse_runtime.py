"""Execute the real WorldMap.fuse under a Lua runtime (skipped without lupa).

Validates that the Fuse compiles, registers, wires its controls and rasterises a
frame end-to-end using the generated data — without needing DaVinci Resolve.
"""

import pytest

from conftest import REPO_ROOT

lupa = pytest.importorskip("lupa")

FUSE = REPO_ROOT / "Fuses" / "WorldMap.fuse"
DATA = REPO_ROOT / "generated" / "worldmap_data.lua"

STUBS = r"""
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
function self:AddInput(n, id, a)
    local i = Input.new(a and a.INP_Default or 0); self.Inputs[id] = i; return i
end
function self:AddOutput(n, id, a) return Output.new() end
function self:BeginControlNest(...) end
function self:EndControlNest(...) end
local Req = {}; Req.__index = Req
function Req.new() return setmetatable({}, Req) end
function Req:IsQuick() return true end
function Req:IsNoMotionBlur() return true end
function Req:IsStampOnly() return false end
_req_factory = Req.new
function Pixel(t) return { R = (t and t.R) or 0, G = (t and t.G) or 0, B = (t and t.B) or 0, A = (t and t.A) or 0 } end
local Img = {}; Img.__index = Img
function Image(a) return setmetatable({ w = a.IMG_Width, h = a.IMG_Height }, Img) end
function Img:Clear() end
function Img:Fill(p) end
function Img:GetPixel(x, y, p) p.R=0; p.G=0; p.B=0; p.A=0; return true end
function Img:SetPixel(x, y, p) if p.A > 0 then _plotted = (_plotted or 0) + 1 end; return true end
XScale, YScale = 1, 1
XAspect, YAspect = 1, 1
"""


@pytest.fixture(scope="module")
def runtime():
    if not DATA.exists():
        pytest.skip("generated data not built")
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(STUBS)
    lua.globals().Width = 120
    lua.globals().Height = 60
    src = FUSE.read_text(encoding="utf-8")
    compile_fuse = lua.eval(
        "function(c, n) local f, e = load(c, n); return f, (e or false) end"
    )
    fn, err = compile_fuse("do " + src + "\nend",
                           "@" + str(FUSE).replace("\\", "/"))
    assert fn is not None, f"Fuse failed to compile: {err}"
    fn()
    return lua


def test_registers(runtime):
    assert runtime.eval("_registered") == "WorldMap"


def test_create_wires_inputs(runtime):
    runtime.eval("Create")()
    inputs = dict(runtime.globals().self.Inputs)
    for iid in ("Origin", "Zoom", "Center", "StrokeWidth", "Country",
                "FillColor", "DrawWorld"):
        assert iid in inputs, f"missing input {iid}"


def test_process_rasterises(runtime):
    runtime.eval("Create")()
    req = runtime.eval("_req_factory")()
    runtime.eval("Process")(req)
    plotted = runtime.eval("_plotted") or 0
    assert plotted > 1000, "Fuse produced an (almost) empty frame"
