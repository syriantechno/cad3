# ===============================================================
# tools/axis_helpers.py — Fusion 360 Style 3D Scene Setup (v2)
# ===============================================================
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax1
from OCC.Core.AIS import AIS_Axis, AIS_TextLabel, AIS_ViewCube
from OCC.Core.Quantity import (
    Quantity_Color,
    Quantity_TOC_RGB,
    Quantity_NOC_RED,
    Quantity_NOC_GREEN,
    Quantity_NOC_BLUE,
)
from OCC.Core.Graphic3d import (
    Graphic3d_TransformPers,
    Graphic3d_TMF_2d,
    Graphic3d_TMF_ZoomPers,
    Graphic3d_NameOfMaterial,
)
from OCC.Core.Aspect import Aspect_TOTP_LEFT_LOWER, Aspect_TOTP_RIGHT_UPPER

from OCC.Core.Aspect import Aspect_GDM_Lines
from OCC.Core.V3d import  V3d_TypeOfOrientation
from OCC.Core.AIS import AIS_ViewController
from OCC.Core.Quantity import Quantity_ColorRGBA

# ✍️ لون النص الافتراضي
TEXT_COLOR = Quantity_Color(0.1, 0.1, 0.1, Quantity_TOC_RGB)


# ======================================================
# 🔹 إنشاء تسميات نصية ثابتة للمحاور
# ======================================================
def _make_label(text: str, pos: gp_Pnt, color: Quantity_Color = TEXT_COLOR, height: int = 22):
    lbl = AIS_TextLabel()
    lbl.SetPosition(pos)
    lbl.SetText(text)
    aspect = lbl.Attributes().TextAspect()
    aspect.SetColor(color)
    aspect.SetHeight(height)
    lbl.SetTransformPersistence(
        Graphic3d_TransformPers(Graphic3d_TMF_2d | Graphic3d_TMF_ZoomPers, Aspect_TOTP_LEFT_LOWER)
    )
    return lbl


# ======================================================
# 🧭 إنشاء محاور X/Y/Z + تسميات ملونة
# ======================================================
def create_axes_with_labels(length: float = 500.0):
    """إنشاء محاور X/Y/Z ثابتة بالحجم في الزاوية السفلى اليسرى"""
    origin = gp_Pnt(0, 0, 0)

    # 🟥 محور X
    x_axis = AIS_Axis(gp_Ax1(origin, gp_Dir(1, 0, 0)))
    x_axis.SetColor(Quantity_Color(Quantity_NOC_RED))
    x_axis.SetTransformPersistence(
        Graphic3d_TransformPers(Graphic3d_TMF_2d | Graphic3d_TMF_ZoomPers, Aspect_TOTP_LEFT_LOWER)
    )

    # 🟩 محور Y
    y_axis = AIS_Axis(gp_Ax1(origin, gp_Dir(0, 1, 0)))
    y_axis.SetColor(Quantity_Color(Quantity_NOC_GREEN))
    y_axis.SetTransformPersistence(
        Graphic3d_TransformPers(Graphic3d_TMF_2d | Graphic3d_TMF_ZoomPers, Aspect_TOTP_LEFT_LOWER)
    )

    # 🟦 محور Z
    z_axis = AIS_Axis(gp_Ax1(origin, gp_Dir(0, 0, 1)))
    z_axis.SetColor(Quantity_Color(Quantity_NOC_BLUE))
    z_axis.SetTransformPersistence(
        Graphic3d_TransformPers(Graphic3d_TMF_2d | Graphic3d_TMF_ZoomPers, Aspect_TOTP_LEFT_LOWER)
    )

    # ✍️ التسميات
    label_x = _make_label("X", gp_Pnt(length, 0, 0), Quantity_Color(1.0, 0.0, 0.0, Quantity_TOC_RGB))
    label_y = _make_label("Y", gp_Pnt(0, length, 0), Quantity_Color(0.0, 1.0, 0.0, Quantity_TOC_RGB))
    label_z = _make_label("Z", gp_Pnt(0, 0, length), Quantity_Color(0.0, 0.4, 1.0, Quantity_TOC_RGB))

    return x_axis, y_axis, z_axis, label_x, label_y, label_z


# ======================================================
# 🧱 عرض المحاور بعد أي EraseAll()
# ======================================================
def show_axes(display, axes_tuple):
    """عرض المحاور والتسميات على العارض من جديد"""
    if not display:
        return
    ctx = display.Context
    for obj in axes_tuple:
        if obj:
            ctx.Display(obj, True)
    ctx.UpdateCurrentViewer()
    print("🧭 Axes displayed successfully.")


# ======================================================
# 🕸 إعداد الشبكة الرمادية المتكيفة
# ======================================================
# 🕸 شبكة أنيقة متكيفة – متوافقة مع جميع إصدارات pythonOCC
from OCC.Core.gp import gp_Pln, gp_Ax3, gp_Pnt, gp_Dir
from OCC.Core.Aspect import Aspect_GDM_Lines, Aspect_GT_Rectangular

def setup_grid(display):
    """إعداد شبكة ناعمة متكيفة، على طائرة الأرض (XY) بدون استخدام V3d_CoordinateSystem."""
    try:
        viewer = display._display.Viewer

        # 1) ضبط الطائرة المميزة للعارض: XY (Z للأعلى)
        ground_xy = gp_Pln(gp_Ax3(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)))  # Normal = +Z  → شبكة على XY
        viewer.SetPrivilegedPlane(ground_xy)

        # 2) تفعيل شبكة مستطيلة بخطوط (ممكن تغير القيم حسب رغبتك)
        viewer.ActivateGrid(Aspect_GT_Rectangular, Aspect_GDM_Lines)

        # 3) ضبط مظهر الشبكة
        grid = viewer.Grid()
        grid.SetGraphicValues(100.0, 10.0, Aspect_GDM_Lines)  # مسافة خطوط رئيسية/ثانوية
        # لون رمادي مريح
        from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
        grid.SetColor(Quantity_Color(0.75, 0.75, 0.75, Quantity_TOC_RGB))

        # 4) جعل الشبكة تتفاعل مع التحريك/التكبير
        viewer.SetGridEcho(True)

        print("🕸 Adaptive grid ready (XY plane).")
    except Exception as e:
        print(f"[⚠] Grid setup failed: {e}")



# ======================================================
# 🧊 ViewCube تفاعلي مثل Fusion
# ======================================================
def show_view_cube(display):
    """عرض Cube للتحكم بالاتجاه في الزاوية العليا اليمنى"""
    try:
        ctx = display.Context
        cube = AIS_ViewCube()
        cube.SetSize(75)
        cube.SetFixedAnimation(True)
        cube.SetBoxColor(Quantity_Color(0.95, 0.95, 0.95, Quantity_TOC_RGB))
        cube.SetTransformPersistence(
            Graphic3d_TransformPers(Graphic3d_TMF_2d | Graphic3d_TMF_ZoomPers, Aspect_TOTP_RIGHT_UPPER)
        )
        ctx.Display(cube, False)
        ctx.UpdateCurrentViewer()
        print("🧊 ViewCube displayed (top-right corner).")
    except Exception as e:
        print(f"[⚠] ViewCube creation failed: {e}")


# ======================================================
# 🌅 إعداد المشهد الكامل (خلفية + إضاءة + دوران سلس)
# ======================================================
def setup_fusion_scene(display):
    """تهيئة مشهد كامل بأسلوب Fusion 360"""
    try:
        view = display.View
        ctx = display.Context
        viewer = display._display.Viewer

        # 🎨 خلفية متدرجة (gradient)
        top = Quantity_Color(0.95, 0.96, 0.97, Quantity_TOC_RGB)
        bottom = Quantity_Color(0.78, 0.81, 0.85, Quantity_TOC_RGB)
        view.SetBgGradientColors(top, bottom, True)
        view.MustBeResized()

        # 💡 إضاءة محسنة (ثلاثية الاتجاهات)
        viewer.SetDefaultLights()
        viewer.SetLightOn()
        viewer.SetDefaultBackgroundColor(Quantity_Color(0.93, 0.93, 0.93, Quantity_TOC_RGB))
        viewer.Update()

        # 🧭 إسقاط أيزومتري مريح
        view.SetProj(V3d_TypeOfOrientation.V3d_XposYnegZpos)
        view.SetAt(0, 0, 0)
        view.SetEye(500, -500, 400)
        view.SetImmediateUpdate(True)

        # 🎞 دوران سلس حول مركز الشكل
        view.Rotation(1.5, 1.5)
        display._display.View.SetZClippingType(0)

        # 📦 Cube + Grid + Axes
        setup_grid(display)
        show_view_cube(display)
        axes = create_axes_with_labels()
        show_axes(display, axes)

        print("✅ Fusion-style scene ready.")
    except Exception as e:
        print(f"[⚠] Fusion scene setup failed: {e}")
