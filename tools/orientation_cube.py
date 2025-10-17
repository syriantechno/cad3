# tools/orientation_cube.py
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.AIS import AIS_ColoredShape
from OCC.Core.Aspect import Aspect_TOTP_LEFT_LOWER
from OCC.Core.Graphic3d import (
    Graphic3d_TransformPers,
    Graphic3d_TMF_2d,
    Graphic3d_TMF_ZoomPers,
    Graphic3d_Vec2i,
)
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.BRep import BRep_Tool
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib


def create_orientation_cube(display, size=30, x_offset=20, y_offset=20):
    """
    إنشاء مكعب ثابت في زاوية الشاشة (HUD) مع ألوان مميزة لكل وجه.
    - X: أحمر
    - Y: أخضر
    - Z: أزرق
    - باقي الوجوه: رمادي باهت
    """
    ctx = display.Context

    # 🧱 إنشاء مكعب أساسي
    cube_shape = BRepPrimAPI_MakeBox(size, size, size).Shape()

    # 🧠 نستخدم AIS_ColoredShape لتلوين كل وجه على حدة
    colored_cube = AIS_ColoredShape(cube_shape)

    # الألوان
    red = Quantity_Color(1.0, 0.0, 0.0, Quantity_TOC_RGB)       # X
    green = Quantity_Color(0.0, 1.0, 0.0, Quantity_TOC_RGB)     # Y
    blue = Quantity_Color(0.0, 0.0, 1.0, Quantity_TOC_RGB)      # Z
    gray = Quantity_Color(0.8, 0.8, 0.8, Quantity_TOC_RGB)      # باقي

    # 📝 استكشاف وجوه المكعب وتلوينها حسب موضعها
    exp = TopExp_Explorer(cube_shape, TopAbs_FACE)
    while exp.More():
        face = exp.Current()
        bbox = Bnd_Box()
        brepbndlib.Add(face, bbox)
        xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
        cx = (xmin + xmax) / 2
        cy = (ymin + ymax) / 2
        cz = (zmin + zmax) / 2

        if abs(cx - size) < 1e-6:
            colored_cube.SetCustomColor(face, red)
        elif abs(cy - size) < 1e-6:
            colored_cube.SetCustomColor(face, green)
        elif abs(cz - size) < 1e-6:
            colored_cube.SetCustomColor(face, blue)
        else:
            colored_cube.SetCustomColor(face, gray)

        exp.Next()

    # 🧭 تثبيت المكعب في زاوية الشاشة باستخدام Vec2i
    offset_vec = Graphic3d_Vec2i(x_offset, y_offset)
    transform_pers = Graphic3d_TransformPers(
        Graphic3d_TMF_2d | Graphic3d_TMF_ZoomPers,
        Aspect_TOTP_LEFT_LOWER,
        offset_vec
    )
    colored_cube.SetTransformPersistence(transform_pers)

    ctx.Display(colored_cube, True)
    return colored_cube
