# tools/dimensions.py
from typing import Tuple, Optional
from OCC.Core.gp import gp_Pnt
from OCC.Core.Bnd import Bnd_Box
# توافق 7.9: استخدام الواجهة الحديثة إن توفرت
try:
    from OCC.Core.BRepBndLib import brepbndlib  # >= 7.8
    def _bbox_add(shape, box): brepbndlib.Add(shape, box)
except Exception:
    # fallback قديم
    from OCC.Core import BRepBndLib
    def _bbox_add(shape, box): BRepBndLib.brepbndlib_Add(shape, box)

from .dimension_draw import (
    draw_dimension, DIM_COLOR_GEN, DIM_COLOR_HOLE, DIM_COLOR_PREVIEW
)
from .dimension_manager import DimensionManager

# ========== أدوات Bounding Box ==========
def get_bbox(shape) -> Tuple[float, float, float, float, float, float]:
    box = Bnd_Box()
    _bbox_add(shape, box)
    return box.Get()  # xmin, ymin, zmin, xmax, ymax, zmax

def get_zmax(shape) -> float:
    _, _, _, _, _, zmax = get_bbox(shape)
    return zmax

# ========== قياسات عامة (Bounding Box) ==========
def measure_shape(display, shape, *, offset_above: float = 10.0, manager: Optional[DimensionManager] = None):
    """
    يرسم أبعاد X/Y على مستوى أعلى نقطة (zmax + offset_above)
    وأبعاد Z من القاعدة إلى الأعلى. يسجل العناصر في manager إن وُجد.
    """
    if shape is None:
        print("⚠️ لا يوجد شكل للقياس.")
        return

    xmin, ymin, zmin, xmax, ymax, zmax = get_bbox(shape)
    x_len, y_len, z_len = (xmax-xmin), (ymax-ymin), (zmax-zmin)
    top_z = zmax + offset_above

    # نقاط أبعاد X/Y (على المستوى العلوي)
    p_x1 = gp_Pnt(xmin, ymin, top_z)
    p_x2 = gp_Pnt(xmax, ymin, top_z)
    p_y1 = gp_Pnt(xmin, ymin, top_z)
    p_y2 = gp_Pnt(xmin, ymax, top_z)
    # نقاط بعد Z (من القاعدة لأعلى)
    p_z1 = gp_Pnt(xmin, ymin, zmin)
    p_z2 = gp_Pnt(xmin, ymin, zmax)

    print(f"📐 قياسات الشكل (BoundingBox): X={x_len:.1f}, Y={y_len:.1f}, Z={z_len:.1f}")

    objs = []
    objs += list(draw_dimension(display, p_x1, p_x2, f"{x_len:.1f} mm", lift_z=0, color=DIM_COLOR_GEN))
    objs += list(draw_dimension(display, p_y1, p_y2, f"{y_len:.1f} mm", lift_z=0, color=DIM_COLOR_GEN))
    objs += list(draw_dimension(display, p_z1, p_z2, f"{z_len:.1f} mm", lift_z=0, color=DIM_COLOR_GEN))

    if manager:
        for o in objs:
            manager.add(o, "general")

# ========== قياسات مرجعية للحفرة (من الأصل إلى المركز على X و Y) ==========
def hole_reference_dimensions(display, current_shape, x: float, y: float, z: float,
                              *, offset_above: float = 10.0, manager: Optional[DimensionManager] = None,
                              preview: bool = False):
    """
    يرسم خطي قياس متعامدين على مستوى (zmax + offset) من (0,0) -> (x,0) -> (x,y).
    اللون يختلف إن كان Preview.
    """
    if abs(x) < 1e-9 and abs(y) < 1e-9:
        return

    zmax = get_zmax(current_shape) if current_shape else 0.0
    base_z = zmax + offset_above

    color = DIM_COLOR_PREVIEW if preview else DIM_COLOR_HOLE

    origin = gp_Pnt(0, 0, base_z)
    x_point = gp_Pnt(x, 0, base_z)
    y_point = gp_Pnt(x, y, base_z)

    objs = []
    if abs(x) > 1e-9:
        objs += list(draw_dimension(display, origin, x_point, f"X: {x:.1f} mm", color=color))
    if abs(y) > 1e-9:
        objs += list(draw_dimension(display, x_point, y_point, f"Y: {y:.1f} mm", color=color))

    if manager:
        for o in objs:
            manager.add(o, "preview" if preview else "holes")

# ========== قياسات قطر وعمق الحفرة ==========
def hole_size_dimensions(display, current_shape, x: float, y: float, z: float, dia: float, axis: str,
                         *, depth: Optional[float] = None, offset_above: float = 10.0,
                         manager: Optional[DimensionManager] = None, preview: bool = False):
    """
    يرسم:
      - قطر الحفرة بخط أفقي على مستوى أعلى الشكل (zmax+offset) إن كانت Z، أو على المستوى الموازي للمحور.
      - عمق الحفرة بخط موجه مع المحور (إن توفرت قيمة depth).
    """
    color = DIM_COLOR_PREVIEW if preview else DIM_COLOR_HOLE
    zmax = get_zmax(current_shape) if current_shape else 0.0
    top_z = zmax + offset_above
    r = dia / 2.0
    axis = (axis or "Z").upper()

    # قطر
    if axis == "Z":
        p1 = gp_Pnt(x - r, y, top_z)
        p2 = gp_Pnt(x + r, y, top_z)
    elif axis == "X":
        p1 = gp_Pnt(x, y - r, z)
        p2 = gp_Pnt(x, y + r, z)
    else:  # Y
        p1 = gp_Pnt(x, y, z - r)
        p2 = gp_Pnt(x, y, z + r)

    objs = []
    objs += list(draw_dimension(display, p1, p2, f"⌀ {dia:.1f} mm", color=color))

    # عمق (إن متاح)
    if depth is not None and depth > 1e-9:
        if axis == "Z":
            d1 = gp_Pnt(x, y, top_z)
            d2 = gp_Pnt(x, y, top_z - depth)
        elif axis == "X":
            d1 = gp_Pnt(x, y, z)
            d2 = gp_Pnt(x - depth, y, z)
        else:  # Y
            d1 = gp_Pnt(x, y, z)
            d2 = gp_Pnt(x, y - depth, z)
        objs += list(draw_dimension(display, d1, d2, f"Depth {depth:.1f} mm", color=color))

    if manager:
        for o in objs:
            manager.add(o, "preview" if preview else "holes")
