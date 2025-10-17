# tools/dimensions.py  — SAFE BUILD
import math
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax2
from OCC.Core.Geom import Geom_CartesianPoint
from OCC.Core.AIS import AIS_Line, AIS_TextLabel
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib

# ألوان القياسات
_DIM_COLOR_FINAL = Quantity_Color(1.0, 0.0, 0.0, Quantity_TOC_RGB)      # أحمر نهائي
_DIM_COLOR_PREV  = Quantity_Color(0.0, 0.45, 1.0, Quantity_TOC_RGB)     # أزرق للمعاينة

def _color(preview: bool):
    return _DIM_COLOR_PREV if preview else _DIM_COLOR_FINAL

def draw_dimension(display, p1: gp_Pnt, p2: gp_Pnt, label: str = None, lift_z: float = 10.0, preview: bool=False):
    """
    يرسم بعدًا بسيطًا بين نقطتين + نص في المنتصف. آمن ولا يعتمد على أي Shape.
    """
    length = p1.Distance(p2)
    if length <= 1e-9:
        return None, None

    p1u = gp_Pnt(p1.X(), p1.Y(), p1.Z() + lift_z)
    p2u = gp_Pnt(p2.X(), p2.Y(), p2.Z() + lift_z)

    line = AIS_Line(Geom_CartesianPoint(p1u), Geom_CartesianPoint(p2u))
    line.SetColor(_color(preview))
    display.Context.Display(line, False)

    # الوسم النصي في المنتصف
    mid = gp_Pnt(0.5*(p1u.X()+p2u.X()), 0.5*(p1u.Y()+p2u.Y()), 0.5*(p1u.Z()+p2u.Z()))
    txt = AIS_TextLabel()
    txt.SetPosition(mid)
    txt.SetText(label if label is not None else f"{length:.1f} mm")

    # محاذاة تقريبية
    dx, dy, dz = (p2u.X()-p1u.X(), p2u.Y()-p1u.Y(), p2u.Z()-p1u.Z())
    try:
        orient = gp_Ax2(mid, gp_Dir(0,0,1), gp_Dir(dx,dy,dz))
        txt.SetOrientation3D(orient)
    except Exception:
        pass

    asp = txt.Attributes().TextAspect()
    asp.SetColor(_color(preview))
    asp.SetHeight(24)
    display.Context.Display(txt, False)
    return line, txt

# توافُق مع أي كود قديم
_draw_dimension = draw_dimension

def measure_shape(display, shape):
    """
    قياسات Bounding Box (X/Y/Z) — آمنة وبسيطة.
    """
    if shape is None or shape.IsNull():
        return
    box = Bnd_Box()
    brepbndlib.Add(shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()

    # X
    draw_dimension(display, gp_Pnt(xmin,ymin,zmin), gp_Pnt(xmax,ymin,zmin), f"X={xmax-xmin:.1f} mm")
    # Y
    draw_dimension(display, gp_Pnt(xmin,ymin,zmin), gp_Pnt(xmin,ymax,zmin), f"Y={ymax-ymin:.1f} mm")
    # Z
    draw_dimension(display, gp_Pnt(xmin,ymin,zmin), gp_Pnt(xmin,ymin,zmax), f"Z={zmax-zmin:.1f} mm")

# ------- Hole dimensions (لا تعتمد على الـ Shape) -------
def hole_reference_dimensions(display, x, y, z, offset_above: float=10.0, preview: bool=False):
    draw_dimension(display, gp_Pnt(0,0,0), gp_Pnt(x,y,z), None, lift_z=offset_above, preview=preview)

def hole_size_dimensions(display, x, y, z, dia, axis: str, depth: float, offset_above: float=10.0, preview: bool=False):
    # القطر
    draw_dimension(display,
                   gp_Pnt(x - dia/2.0, y, z),
                   gp_Pnt(x + dia/2.0, y, z),
                   f"⌀{dia:.1f}", lift_z=offset_above, preview=preview)
    # العمق حسب المحور
    if axis == "Z":
        p3, p4 = gp_Pnt(x,y,z), gp_Pnt(x,y,z - depth)
    elif axis == "Y":
        p3, p4 = gp_Pnt(x,y,z), gp_Pnt(x,y - depth,z)
    else:
        p3, p4 = gp_Pnt(x,y,z), gp_Pnt(x - depth,y,z)
    draw_dimension(display, p3, p4, f"D={depth:.1f}", lift_z=offset_above, preview=preview)

# ------- Box cut dimensions (لا تعتمد على الـ Shape) -------
def box_cut_reference_dimensions(display, x, y, z, offset_above: float=10.0, preview: bool=False):
    draw_dimension(display, gp_Pnt(0,0,0), gp_Pnt(x,y,z), None, lift_z=offset_above, preview=preview)

def box_cut_size_dimensions(display, w, h, d, x, y, z, offset_above: float=10.0, preview: bool=False):
    p0 = gp_Pnt(x,y,z)
    draw_dimension(display, p0, gp_Pnt(x+w,y,z), f"W={w:.1f}", lift_z=offset_above, preview=preview)
    draw_dimension(display, p0, gp_Pnt(x,y+h,z), f"H={h:.1f}", lift_z=offset_above, preview=preview)
    draw_dimension(display, p0, gp_Pnt(x,y,z+d), f"D={d:.1f}", lift_z=offset_above, preview=preview)
