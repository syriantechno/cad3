# tools/dimensions.py — FINAL BUILD (Preview-Safe + Returns Drawn Objects)
import math
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax2
from OCC.Core.Geom import Geom_CartesianPoint
from OCC.Core.AIS import AIS_Line, AIS_TextLabel
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib

# ==================== 🎨 ألوان القياسات ====================
_DIM_COLOR_FINAL = Quantity_Color(1.0, 0.0, 0.0, Quantity_TOC_RGB)     # أحمر - للقياسات النهائية
_DIM_COLOR_PREV  = Quantity_Color(0.0, 0.45, 1.0, Quantity_TOC_RGB)    # أزرق - للمعاينة

def _color(preview: bool):
    return _DIM_COLOR_PREV if preview else _DIM_COLOR_FINAL


# ==================== 🧠 حساب مستوى Z العلوي ====================
def _get_z_level_for_shape(shape, extra_lift: float = 10.0):
    """يرجع مستوى Z أعلى المجسم بقليل لعرض القياسات فوق الشكل."""
    if shape is None or shape.IsNull():
        return extra_lift
    box = Bnd_Box()
    brepbndlib.Add(shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return zmax + extra_lift


# ==================== 📝 أداة رسم البُعد الأساسية ====================
def draw_dimension(display, p1: gp_Pnt, p2: gp_Pnt, label: str = None,
                   lift_z: float = 0.0, preview: bool = False):
    """
    يرسم بعدًا (خط + نص) بين نقطتين.
    يرجع كائن الخط وكائن النص لسهولة المسح لاحقًا.
    """
    length = p1.Distance(p2)
    if length <= 1e-9:
        return None, None

    # نرفع النقاط إذا لزم الأمر
    p1u = gp_Pnt(p1.X(), p1.Y(), p1.Z() + lift_z)
    p2u = gp_Pnt(p2.X(), p2.Y(), p2.Z() + lift_z)

    line = AIS_Line(Geom_CartesianPoint(p1u), Geom_CartesianPoint(p2u))
    line.SetColor(_color(preview))
    display.Context.Display(line, False)

    mid = gp_Pnt(
        0.5 * (p1u.X() + p2u.X()),
        0.5 * (p1u.Y() + p2u.Y()),
        0.5 * (p1u.Z() + p2u.Z())
    )

    txt = AIS_TextLabel()
    txt.SetPosition(mid)
    txt.SetText(label if label else f"{length:.1f} mm")

    dx, dy, dz = (p2u.X()-p1u.X(), p2u.Y()-p1u.Y(), p2u.Z()-p1u.Z())
    try:
        orient = gp_Ax2(mid, gp_Dir(0, 0, 1), gp_Dir(dx, dy, dz))
        txt.SetOrientation3D(orient)
    except Exception:
        pass

    asp = txt.Attributes().TextAspect()
    asp.SetColor(_color(preview))
    asp.SetHeight(24)
    display.Context.Display(txt, False)
    return line, txt


# ==================== 📐 قياسات Bounding Box العامة ====================
def measure_shape(display, shape):
    """يرسم قياسات الطول والعرض والارتفاع للشكل، مرفوعة فوقه."""
    if shape is None or shape.IsNull():
        return
    box = Bnd_Box()
    brepbndlib.Add(shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()

    z_level = zmax + 10.0

    draw_dimension(display, gp_Pnt(xmin, ymin, z_level), gp_Pnt(xmax, ymin, z_level), f"X={xmax - xmin:.1f} mm")
    draw_dimension(display, gp_Pnt(xmin, ymin, z_level), gp_Pnt(xmin, ymax, z_level), f"Y={ymax - ymin:.1f} mm")
    draw_dimension(display, gp_Pnt(xmin, ymin, z_level), gp_Pnt(xmin, ymin, zmax),   f"Z={zmax - zmin:.1f} mm")


# ==================== 🕳 قياسات الحفر ====================
def hole_reference_dimensions(display, x, y, z, shape=None, offset_above: float=10.0, preview: bool=False):
    """
    قياسات مرجعية من نقطة الأصل (0,0) على محوري X وY فقط، ثابتة دائماً مثل Fusion.
    """
    z_level = z + offset_above
    if shape:
        from OCC.Core.Bnd import Bnd_Box
        from OCC.Core.BRepBndLib import brepbndlib
        box = Bnd_Box()
        brepbndlib.Add(shape, box)
        xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
        z_level = zmax + offset_above

    # X reference line
    draw_dimension(
        display,
        gp_Pnt(0, 0, z_level),
        gp_Pnt(x, 0, z_level),
        f"X={x:.1f}",
        lift_z=0,
        preview=preview
    )

    # Y reference line
    draw_dimension(
        display,
        gp_Pnt(x, 0, z_level),
        gp_Pnt(x, y, z_level),
        f"Y={y:.1f}",
        lift_z=0,
        preview=preview
    )


def hole_size_dimensions(display, x, y, z, dia, axis: str, depth: float,
                         shape=None, offset_above: float=10.0, preview: bool=False):
    """القطر والعمق للحفرة، مرفوعة للأعلى."""
    z_level = _get_z_level_for_shape(shape, offset_above)
    drawn = []

    # القطر
    line1, txt1 = draw_dimension(
        display,
        gp_Pnt(x - dia/2.0, y, z_level),
        gp_Pnt(x + dia/2.0, y, z_level),
        f"⌀{dia:.1f}",
        lift_z=0,
        preview=preview
    )
    drawn.extend([line1, txt1])

    # العمق حسب المحور
    if axis == "Z":
        p1 = gp_Pnt(x, y, z_level)
        p2 = gp_Pnt(x, y, z_level - depth)
    elif axis == "Y":
        p1 = gp_Pnt(x, y, z_level)
        p2 = gp_Pnt(x, y - depth, z_level)
    else:
        p1 = gp_Pnt(x, y, z_level)
        p2 = gp_Pnt(x - depth, y, z_level)

    line2, txt2 = draw_dimension(display, p1, p2, f"D={depth:.1f}", lift_z=0, preview=preview)
    drawn.extend([line2, txt2])
    return tuple(drawn)


# ==================== 🧱 قياسات Box Cut ====================
def box_cut_reference_dimensions(display, x, y, z, shape=None, offset_above: float=10.0, preview: bool=False):
    """قياس من الأصل إلى نقطة بداية البوكس، مرفوع للأعلى."""
    z_level = _get_z_level_for_shape(shape, offset_above)
    return draw_dimension(
        display,
        gp_Pnt(0, 0, z_level),
        gp_Pnt(x, y, z_level),
        None,
        lift_z=0,
        preview=preview
    )


def box_cut_size_dimensions(display, w, h, d, x, y, z, shape=None, offset_above: float=10.0, preview: bool=False):
    """قياسات البوكس (W/H/D) مرفوعة للأعلى."""
    z_level = _get_z_level_for_shape(shape, offset_above)
    drawn = []

    # W
    line1, txt1 = draw_dimension(
        display,
        gp_Pnt(x, y, z_level),
        gp_Pnt(x + w, y, z_level),
        f"W={w:.1f}",
        lift_z=0,
        preview=preview
    )
    drawn.extend([line1, txt1])

    # H
    line2, txt2 = draw_dimension(
        display,
        gp_Pnt(x, y, z_level),
        gp_Pnt(x, y + h, z_level),
        f"H={h:.1f}",
        lift_z=0,
        preview=preview
    )
    drawn.extend([line2, txt2])

    # D
    line3, txt3 = draw_dimension(
        display,
        gp_Pnt(x, y, z_level),
        gp_Pnt(x, y, z_level + d),
        f"D={d:.1f}",
        lift_z=0,
        preview=preview
    )
    drawn.extend([line3, txt3])
    return tuple(drawn)
