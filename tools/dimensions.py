import math
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax2
from OCC.Core.Geom import Geom_CartesianPoint
from OCC.Core.AIS import AIS_Line, AIS_TextLabel
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

DIM_COLOR = Quantity_Color(1.0, 0.0, 0.0, Quantity_TOC_RGB)  # أحمر واضح

def _is_collinear(d1: gp_Dir, d2: gp_Dir, tol: float = 1e-9) -> bool:
    # |dot| ≈ 1 => متوازي/عكسي
    return abs(abs(d1.Dot(d2)) - 1.0) <= tol

def draw_dimension(display, p1: gp_Pnt, p2: gp_Pnt, label: str = None, lift_z: float = 20.0):
    """
    يرسم خط قياس بين نقطتين:
      - يرفع النقطتين على Z بمقدار lift_z (من دون تغيير اتجاههما).
      - يوجه النص موازيًا للخط (مع معالجة حالة Z العمودية).
      - يتجنب مشاكل gp_Dir/ gp_Ax2 عندما يكون الاتجاه موازيًا لمحور VDir.
    """
    # طول فعلي لتجنب اتجاه صفري
    length = p1.Distance(p2)
    if length <= 1e-9:
        print("[WARN] dimension skipped (zero length)")
        return None, None

    # ارفع النقطتين على Z
    p1_up = gp_Pnt(p1.X(), p1.Y(), p1.Z() + lift_z)
    p2_up = gp_Pnt(p2.X(), p2.Y(), p2.Z() + lift_z)

    # خط القياس
    gp1 = Geom_CartesianPoint(p1_up)
    gp2 = Geom_CartesianPoint(p2_up)
    line = AIS_Line(gp1, gp2)
    line.SetColor(DIM_COLOR)
    display.Context.Display(line, True)

    # منتصف الخط
    mid = gp_Pnt(
        0.5 * (p1_up.X() + p2_up.X()),
        0.5 * (p1_up.Y() + p2_up.Y()),
        0.5 * (p1_up.Z() + p2_up.Z()),
    )

    # اتجاه الخط
    dx, dy, dz = (p2_up.X() - p1_up.X(), p2_up.Y() - p1_up.Y(), p2_up.Z() - p1_up.Z())
    dir_vec = gp_Dir(dx, dy, dz)  # آمن لأن الطول > 0

    # النص
    txt = AIS_TextLabel()
    txt.SetPosition(mid)
    if label is None:
        label = f"{length:.1f} mm"
    txt.SetText(label)

    # اختيار VDir لا يكون موازيًا لاتجاه الخط
    z_dir = gp_Dir(0, 0, 1)
    if _is_collinear(dir_vec, z_dir):      # لو الخط موازي لـ Z
        v_dir = gp_Dir(1, 0, 0)            # اختَر محورًا عموديًا (X) كـ VDir
    else:
        v_dir = z_dir

    # اضبط المحاذاة ثلاثية الأبعاد (XDir موازي للخط)
    try:
        orient = gp_Ax2(mid, v_dir, dir_vec)
        txt.SetOrientation3D(orient)
    except Exception:
        # لو نسخة OCC لا تدعم Orientation3D بشكل كامل، استخدم زاوية إسقاط تقريبية
        angle = math.atan2(dy, dx)  # إسقاط على XY
        try:
            txt.SetAngle(angle)
        except Exception:
            pass

    # تنسيق النص
    txt_aspect = txt.Attributes().TextAspect()
    txt_aspect.SetColor(DIM_COLOR)
    txt_aspect.SetHeight(24)

    display.Context.Display(txt, True)
    return line, txt
