# -*- coding: utf-8 -*-
# graphics_kit.py
# =========================================
# ⚙️ GraphicsKit — “باكيج” عرض ورسم شبيه Fusion 360
# - مستقل 100% عن كودك الحالي (لا يغيّر شيء)
# - يوفّر: رسم بدائيات + طبقات + شبكة + محاور + معاينة + أوامر
# - مناسب لـ pythonocc 7.9
#
# ملاحظات الالتزام بطلباتك:
# 1) كود جديد في ملف مستقل ✅
# 2) ما نكسر شي موجود ✅
# 3) فصل واضح + شروح + طباعة Debug ✅

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

# gp / topo / builders
from OCC.Core.gp import gp_Pnt, gp_Ax2, gp_Dir
from OCC.Core.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
)
from OCC.Core.GC import GC_MakeCircle, GC_MakeArcOfCircle
from OCC.Core.TopoDS import TopoDS_Shape

# AIS / View
from OCC.Core.AIS import AIS_Shape, AIS_Trihedron
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.Graphic3d import Graphic3d_NOM_DEFAULT

# =========================================
# 🎨 الأنماط (Styles)
# =========================================
@dataclass
class Style:
    rgb: Tuple[float, float, float] = (0.1, 0.1, 0.1)  # أسود رقيق
    transparency: float = 0.0  # 0 صلب — 1 شفاف
    material: int = Graphic3d_NOM_DEFAULT  # خامة افتراضية

    def as_color(self) -> Quantity_Color:
        r, g, b = self.rgb
        return Quantity_Color(r, g, b, Quantity_TOC_RGB)

# =========================================
# 🗂️ الطبقات (Layers)
# =========================================
class LayerManager:
    def __init__(self, ctx):
        self.ctx = ctx
        self.layers: Dict[str, List[AIS_Shape]] = {}
        print("[LayerManager] Initialized")

    def create(self, name: str):
        if name not in self.layers:
            self.layers[name] = []
            print(f"[LayerManager] Created layer: {name}")

    def add(self, name: str, ais: AIS_Shape):
        if name not in self.layers:
            self.create(name)
        self.layers[name].append(ais)
        print(f"[LayerManager] Added object to layer '{name}', count={len(self.layers[name])}")

    def set_visible(self, name: str, visible: bool, update: bool = True):
        if name not in self.layers:
            print(f"[LayerManager] WARN: layer '{name}' not found")
            return
        for obj in self.layers[name]:
            if visible:
                if not self.ctx.IsDisplayed(obj):
                    self.ctx.Display(obj, update)
            else:
                if self.ctx.IsDisplayed(obj):
                    self.ctx.Erase(obj, update)
        print(f"[LayerManager] Layer '{name}' visible={visible}")

    def clear(self, name: str):
        if name in self.layers:
            for obj in self.layers[name]:
                if self.ctx.IsDisplayed(obj):
                    self.ctx.Erase(obj, False)
            self.layers[name].clear()
            print(f"[LayerManager] Cleared layer '{name}'")

# =========================================
# 👻 المعاينة (Ghost Preview)
# =========================================
class PreviewManager:
    def __init__(self, ctx):
        self.ctx = ctx
        self._ghost: Optional[AIS_Shape] = None
        print("[PreviewManager] Initialized")

    def show(self, shape: TopoDS_Shape, transparency: float = 0.75):
        self.clear()
        self._ghost = AIS_Shape(shape)
        self.ctx.Display(self._ghost, False)
        self.ctx.SetTransparency(self._ghost, transparency, True)
        print(f"[Preview] Showing ghost with transparency={transparency}")

    def update(self, shape: TopoDS_Shape):
        if self._ghost is None:
            self.show(shape)
        else:
            self.ctx.Erase(self._ghost, False)
            self._ghost = AIS_Shape(shape)
            self.ctx.Display(self._ghost, False)
            self.ctx.SetTransparency(self._ghost, 0.75, True)
            print("[Preview] Updated ghost")

    def clear(self):
        if self._ghost is not None:
            if self.ctx.IsDisplayed(self._ghost):
                self.ctx.Erase(self._ghost, False)
            self._ghost = None
            print("[Preview] Cleared")

# =========================================
# 📐 بدائيات الرسم (Primitives)
# =========================================
def make_line(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> TopoDS_Shape:
    print(f"[Primitive] line: {p1} -> {p2}")
    return BRepBuilderAPI_MakeEdge(gp_Pnt(*p1), gp_Pnt(*p2)).Edge()

def make_polyline(points: List[Tuple[float, float, float]], close: bool = False) -> TopoDS_Shape:
    print(f"[Primitive] polyline: n={len(points)}, close={close}")
    edges = []
    for i in range(len(points) - 1):
        edges.append(BRepBuilderAPI_MakeEdge(gp_Pnt(*points[i]), gp_Pnt(*points[i+1])).Edge())
    if close and len(points) > 2:
        edges.append(BRepBuilderAPI_MakeEdge(gp_Pnt(*points[-1]), gp_Pnt(*points[0])).Edge())
    wire_mk = BRepBuilderAPI_MakeWire()
    for e in edges:
        wire_mk.Add(e)
    return wire_mk.Wire()

def make_rectangle(origin: Tuple[float, float, float], w: float, h: float) -> TopoDS_Shape:
    x, y, z = origin
    p1 = (x, y, z)
    p2 = (x + w, y, z)
    p3 = (x + w, y + h, z)
    p4 = (x, y + h, z)
    print(f"[Primitive] rectangle: origin={origin}, w={w}, h={h}")
    return make_polyline([p1, p2, p3, p4], close=True)

def make_circle(center: Tuple[float, float, float], radius: float) -> TopoDS_Shape:
    print(f"[Primitive] circle: center={center}, r={radius}")
    from OCC.Core.gp import gp_Dir
    axis_dir = gp_Dir(0, 0, 1)  # رسم دائرة في المستوى XY
    circ_geom = GC_MakeCircle(gp_Pnt(*center), axis_dir, radius).Value()
    edge = BRepBuilderAPI_MakeEdge(circ_geom).Edge()
    return BRepBuilderAPI_MakeWire(edge).Wire()


def make_arc_3pts(p1: Tuple[float, float, float], p2: Tuple[float, float, float], p3: Tuple[float, float, float]) -> TopoDS_Shape:
    print(f"[Primitive] arc: {p1} -> {p2} -> {p3}")
    arc = GC_MakeArcOfCircle(gp_Pnt(*p1), gp_Pnt(*p2), gp_Pnt(*p3)).Value()
    edge = BRepBuilderAPI_MakeEdge(arc).Edge()
    return BRepBuilderAPI_MakeWire(edge).Wire()

# =========================================
# 🧭 الشبكة والمحاور
# =========================================
class GridXY:
    def __init__(self, ctx, size: float = 500.0, step: float = 25.0, z: float = 0.0,
                 color: Tuple[float, float, float] = (0.75, 0.75, 0.75)):
        self.ctx = ctx
        self.size = size
        self.step = step
        self.z = z
        self.color = Quantity_Color(*color, Quantity_TOC_RGB)
        self.lines: List[AIS_Shape] = []
        self.visible = False
        print(f"[GridXY] Initialized size={size}, step={step}, z={z}")

    def _build(self):
        if self.lines:
            return
        half = self.size / 2.0
        # خطوط X ثابتة على y
        y = -half
        while y <= half:
            e = make_line((-half, y, self.z), (half, y, self.z))
            ais = AIS_Shape(e)
            self.ctx.Display(ais, False)
            self.ctx.SetColor(ais, self.color, False)
            self.ctx.SetTransparency(ais, 0.6, False)
            self.lines.append(ais)
            y += self.step
        # خطوط Y ثابتة على x
        x = -half
        while x <= half:
            e = make_line((x, -half, self.z), (x, half, self.z))
            ais = AIS_Shape(e)
            self.ctx.Display(ais, False)
            self.ctx.SetColor(ais, self.color, False)
            self.ctx.SetTransparency(ais, 0.6, False)
            self.lines.append(ais)
            x += self.step
        print(f"[GridXY] Built {len(self.lines)} lines")

    def set_visible(self, on: bool):
        self._build()
        for ln in self.lines:
            if on:
                if not self.ctx.IsDisplayed(ln):
                    self.ctx.Display(ln, False)
            else:
                if self.ctx.IsDisplayed(ln):
                    self.ctx.Erase(ln, False)
        self.visible = on
        print(f"[GridXY] visible={on}")
        self.ctx.UpdateCurrentViewer()

class AxesTrihedron:
    def __init__(self, ctx, origin: Tuple[float, float, float] = (0, 0, 0)):
        self.ctx = ctx
        from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax2
        from OCC.Core.Geom import Geom_Axis2Placement

        ax = gp_Ax2(gp_Pnt(*origin), gp_Dir(0, 0, 1), gp_Dir(1, 0, 0))
        geom_ax = Geom_Axis2Placement(ax)
        self.tri = AIS_Trihedron(geom_ax)   # ✅ بدون Handle
        print("[AxesTrihedron] Initialized")

    def show(self):
        self.ctx.Display(self.tri, True)
        print("[AxesTrihedron] Displayed")

    def hide(self):
        self.ctx.Erase(self.tri, True)
        print("[AxesTrihedron] Hidden")




# =========================================
# 🧰 حزمة عليا: GraphicsKit
# =========================================
class GraphicsKit:
    def __init__(self, display):
        """
        display: كائن العرض من pythonocc (init_display()[0])
        """
        self.display = display
        self.ctx = display.Context
        print("[GraphicsKit] Init: context ready")

        # أنظمة فرعية
        self.layers = LayerManager(self.ctx)
        self.preview = PreviewManager(self.ctx)
        self.grid = GridXY(self.ctx)
        self.axes = AxesTrihedron(self.ctx)

        # طبقات افتراضية
        self.layers.create("Default")
        self.layers.create("Construction")
        self.layers.create("Dimensions")

    # ======= عرض عام =======
    def fit_all(self):
        print("[GraphicsKit] FitAll")
        self.display.FitAll()

    # ======= شبكة/محاور =======
    def toggle_grid(self, on: Optional[bool] = None):
        if on is None:
            on = not self.grid.visible
        print(f"[GraphicsKit] toggle_grid -> {on}")
        self.grid.set_visible(on)

    def show_axes(self, on: bool = True):
        print(f"[GraphicsKit] show_axes -> {on}")
        if on:
            self.axes.show()
        else:
            self.axes.hide()

    # ======= رسم + عرض =======
    def _apply_style_and_display(self, shape: TopoDS_Shape, style: Style, layer: str, update=True) -> AIS_Shape:
        ais = AIS_Shape(shape)
        self.ctx.Display(ais, False)
        from OCC.Core.Graphic3d import Graphic3d_MaterialAspect

        material_aspect = Graphic3d_MaterialAspect(style.material)
        self.ctx.SetMaterial(ais, material_aspect, False)
        self.ctx.SetColor(ais, style.as_color(), False)

        if style.transparency > 0.0:
            self.ctx.SetTransparency(ais, style.transparency, False)
        self.layers.add(layer, ais)
        if update:
            self.ctx.UpdateCurrentViewer()
        print(f"[GraphicsKit] Displayed on layer='{layer}', style={style}")
        return ais

    # أوامر عالية المستوى (مثل Fusion)
    def add_line(self, p1, p2, layer="Default", style: Style = Style()):
        shp = make_line(p1, p2)
        return self._apply_style_and_display(shp, style, layer)

    def add_rectangle(self, origin, w, h, layer="Default", style: Style = Style()):
        shp = make_rectangle(origin, w, h)
        return self._apply_style_and_display(shp, style, layer)

    def add_circle(self, center, r, layer="Default", style: Style = Style()):
        shp = make_circle(center, r)
        return self._apply_style_and_display(shp, style, layer)

    def add_arc_3pts(self, p1, p2, p3, layer="Default", style: Style = Style()):
        shp = make_arc_3pts(p1, p2, p3)
        return self._apply_style_and_display(shp, style, layer)

    def add_polyline(self, points: List[Tuple[float, float, float]], close=False, layer="Default", style: Style = Style()):
        shp = make_polyline(points, close=close)
        return self._apply_style_and_display(shp, style, layer)

    # معاينة “Ghost”
    def preview_shape(self, shape: TopoDS_Shape):
        self.preview.show(shape)

    def clear_preview(self):
        self.preview.clear()
