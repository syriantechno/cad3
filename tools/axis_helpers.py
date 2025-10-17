# tools/axis_helpers.py
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax1
from OCC.Core.AIS import AIS_Axis, AIS_TextLabel
from OCC.Core.Quantity import (
    Quantity_Color,
    Quantity_TOC_RGB,
    Quantity_NOC_RED,
    Quantity_NOC_GREEN,
    Quantity_NOC_BLUE,
)

# ✍️ إعداد لون النص
TEXT_COLOR = Quantity_Color(0.0, 0.0, 0.0, Quantity_TOC_RGB)  # أسود

def _make_label(text: str, pos: gp_Pnt, color: Quantity_Color = TEXT_COLOR, height: int = 22):
    """إنشاء تسمية نصية ثلاثية الأبعاد للمحاور."""
    lbl = AIS_TextLabel()
    lbl.SetPosition(pos)
    lbl.SetText(text)
    aspect = lbl.Attributes().TextAspect()
    aspect.SetColor(color)
    aspect.SetHeight(height)
    return lbl

def create_axes_with_labels(length: float = 500.0):
    """
    إنشاء محاور X/Y/Z بأسهم + تسميات.
    - length: الطول من نقطة الأصل إلى طرف كل محور.
    """
    origin = gp_Pnt(0, 0, 0)

    # 🟥 محور X
    x_axis = AIS_Axis(gp_Ax1(origin, gp_Dir(1, 0, 0)))
    x_axis.SetColor(Quantity_Color(Quantity_NOC_RED))

    # 🟩 محور Y
    y_axis = AIS_Axis(gp_Ax1(origin, gp_Dir(0, 1, 0)))
    y_axis.SetColor(Quantity_Color(Quantity_NOC_GREEN))

    # 🟦 محور Z
    z_axis = AIS_Axis(gp_Ax1(origin, gp_Dir(0, 0, 1)))
    z_axis.SetColor(Quantity_Color(Quantity_NOC_BLUE))

    # ✍️ تسميات
    label_x = _make_label("X", gp_Pnt(length, 0, 0))
    label_y = _make_label("Y", gp_Pnt(0, length, 0))
    label_z = _make_label("Z", gp_Pnt(0, 0, length))

    return x_axis, y_axis, z_axis, label_x, label_y, label_z
# tools/axis_helpers.py

def show_axes(display, axes_tuple):
    """عرض المحاور والتسميات على العارض من جديد بعد أي EraseAll()."""
    if not display:
        return
    ctx = display.Context
    for obj in axes_tuple:
        if obj:
            ctx.Display(obj, True)
