# tools/dimension_draw.py
import math
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax2
from OCC.Core.Geom import Geom_CartesianPoint
from OCC.Core.AIS import AIS_Line, AIS_TextLabel
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

DIM_COLOR_GEN = Quantity_Color(1.0, 0.0, 0.0, Quantity_TOC_RGB)   # أحمر - عام
DIM_COLOR_HOLE = Quantity_Color(1.0, 0.8, 0.0, Quantity_TOC_RGB)  # 🟡 أصفر ذهبي واضح
DIM_COLOR_PREVIEW = Quantity_Color(0.0, 0.3, 1.0, Quantity_TOC_RGB)


def _is_collinear(d1: gp_Dir, d2: gp_Dir, tol: float = 1e-9) -> bool:
    return abs(abs(d1.Dot(d2)) - 1.0) <= tol

def draw_dimension(display, p1: gp_Pnt, p2: gp_Pnt, label: str = None,
                   lift_z: float = 0.0, color: Quantity_Color = None):
    """
    يرسم خط قياس + نص بين نقطتين. يرفع Z بمقدار lift_z (يُضاف إلى النقطتين).
    يرجع (AIS_Line, AIS_TextLabel).
    """
    length = p1.Distance(p2)
    if length <= 1e-9:
        # print("[WARN] dimension skipped (zero length)")
        return None, None

    if color is None:
        color = DIM_COLOR_GEN

    # ارفع Z
    p1u = gp_Pnt(p1.X(), p1.Y(), p1.Z() + lift_z)
    p2u = gp_Pnt(p2.X(), p2.Y(), p2.Z() + lift_z)

    # خط القياس
    gp1 = Geom_CartesianPoint(p1u)
    gp2 = Geom_CartesianPoint(p2u)
    line = AIS_Line(gp1, gp2)
    line.SetColor(color)
    display.Context.Display(line, False)

    # منتصف + اتجاه
    mid = gp_Pnt(0.5*(p1u.X()+p2u.X()), 0.5*(p1u.Y()+p2u.Y()), 0.5*(p1u.Z()+p2u.Z()))
    dx, dy, dz = (p2u.X()-p1u.X(), p2u.Y()-p1u.Y(), p2u.Z()-p1u.Z())

    txt = AIS_TextLabel()
    txt.SetPosition(mid)
    txt.SetText(f"{length:.1f} mm" if label is None else label)

    z_dir = gp_Dir(0, 0, 1)
    try:
        dir_vec = gp_Dir(dx, dy, dz)
        v_dir = gp_Dir(1, 0, 0) if _is_collinear(dir_vec, z_dir) else z_dir
        txt.SetOrientation3D(gp_Ax2(mid, v_dir, dir_vec))
    except Exception:
        try:
            txt.SetAngle(math.atan2(dy, dx))
        except Exception:
            pass

    ta = txt.Attributes().TextAspect()
    ta.SetColor(color)
    ta.SetHeight(24)

    display.Context.Display(txt, True)
    return line, txt

