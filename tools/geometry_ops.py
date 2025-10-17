# tools/geometry_ops.py — FINAL BUILD (Box + Extrude + Hole + BoxCut)
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax2, gp_Vec
from OCC.Core.BRepPrimAPI import (
    BRepPrimAPI_MakeBox,
    BRepPrimAPI_MakePrism,
    BRepPrimAPI_MakeCylinder
)
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib

# ==================== 📦 Box ====================
def make_box(x, y, z, dx, dy, dz):
    """إنشاء مجسم بوكس"""
    return BRepPrimAPI_MakeBox(gp_Pnt(x, y, z), dx, dy, dz).Shape()

def preview_box(x, y, z, dx, dy, dz):
    """معاينة صندوق"""
    return make_box(x, y, z, dx, dy, dz)

def make_hole_cylinder(base_shape, x, y, z, dia, axis, depth=None):
    """
    إنشاء أسطوانة الحفر بحيث يبدأ أعلاها من السطح العلوي للجسم
    وتمتد للأسفل بالعمق المحدد.
    """
    radius = dia / 2.0
    zmax, zmin = _get_shape_top_z(base_shape)

    if depth is None:
        depth = (zmax - zmin) + 5.0  # افتراضي

    # نقطة البداية = أعلى سطح الجسم
    if axis == "Z":
        start = gp_Pnt(x, y, zmax)
        direction = gp_Dir(0, 0, -1)
    elif axis == "Y":
        start = gp_Pnt(x, y, zmax)
        direction = gp_Dir(0, -1, 0)
    else:
        start = gp_Pnt(x, y, zmax)
        direction = gp_Dir(-1, 0, 0)

    ax = gp_Ax2(start, direction)
    cyl = BRepPrimAPI_MakeCylinder(ax, radius, depth).Shape()
    return cyl
# ==================== ✂️ Box Cut ====================
def make_box_cut_shape(x, y, z, dx, dy, dz):
    """إنشاء شكل الصندوق المستخدم كأداة طرح (وضع حر)"""
    return BRepPrimAPI_MakeBox(gp_Pnt(x, y, z), dx, dy, dz).Shape()

def preview_box_cut(x, y, z, dx, dy, dz):
    """معاينة صندوق الطرح (شفاف أو بلون مميز لاحقاً في الواجهة)"""
    return make_box_cut_shape(x, y, z, dx, dy, dz)

def apply_box_cut(base_shape, x, y, z, dx, dy, dz):
    """تطبيق عملية طرح صندوق من الشكل الأساسي"""
    box_shape = make_box_cut_shape(x, y, z, dx, dy, dz)
    if box_shape is None or box_shape.IsNull():
        print("[❌] apply_box_cut: box shape is null")
        return None

    try:
        cut = BRepAlgoAPI_Cut(base_shape, box_shape).Shape()
        return cut
    except Exception as e:
        print(f"[❌] BoxCut failed: {e}")
        return None

def _get_shape_top_z(shape):
    """إرجاع أعلى نقطة Z للشكل"""
    box = Bnd_Box()
    brepbndlib.Add(shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return zmax

def get_top_z(shape):
    """إرجاع أعلى قيمة Z للمجسم (سقف الشكل)."""
    box = Bnd_Box()
    brepbndlib.Add(shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return zmax

#-----------------------------------------------------------------
def preview_extrude(shape, distance: float):
    """
    إنشاء نسخة معاينة من الشكل عن طريق الإكسترود على محور Y فقط.
    """
    if shape is None or shape.IsNull():
        return None
    vec = gp_Vec(0, distance, 0)
    return BRepPrimAPI_MakePrism(shape, vec).Shape()
def extrude_shape(shape, distance: float):
    """
    تطبيق إكسترود فعلي للشكل على محور Y فقط.
    """
    if shape is None or shape.IsNull():
        return None
    vec = gp_Vec(0, distance, 0)
    return BRepPrimAPI_MakePrism(shape, vec).Shape()
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax2
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder

def preview_hole(base_shape, x, y, z, dia, axis, preview_len):
    """
    إنشاء أسطوانة المعاينة بنفس موضع واتجاه القص الحقيقي
    👈 موضع البداية = Z المحدد
    👈 الطول = preview_len (يمثل طول الريشة)
    """
    if base_shape is None or base_shape.IsNull():
        return None

    if z == 0:
        z = get_top_z(base_shape)

    radius = dia / 2.0
    origin = gp_Pnt(x, y, z)

    if axis == "Z":
        direction = gp_Dir(0, 0, -1)
    elif axis == "Y":
        direction = gp_Dir(0, -1, 0)
    elif axis == "X":
        direction = gp_Dir(-1, 0, 0)
    else:
        print("[❌] preview_hole: invalid axis")
        return None

    cyl_ax2 = gp_Ax2(origin, direction)
    cyl_shape = BRepPrimAPI_MakeCylinder(cyl_ax2, radius, preview_len).Shape()
    return cyl_shape




def add_hole(base_shape, x, y, z, dia, axis, depth):
    """
    القص يبدأ من Z المعاينة نفسها (وليس top_z - depth).
    العمق يحدد فقط طول الاسطوانة للأسفل.
    """
    if base_shape is None or base_shape.IsNull():
        print("[❌] add_hole: base_shape is null")
        return None

    # إذا المستخدم لم يدخل Z → نأخذ top_z فقط كقيمة افتراضية
    if z == 0:
        z = get_top_z(base_shape)

    radius = dia / 2.0
    origin = gp_Pnt(x, y, z)

    if axis == "Z":
        direction = gp_Dir(0, 0, -1)
    elif axis == "Y":
        direction = gp_Dir(0, -1, 0)
    elif axis == "X":
        direction = gp_Dir(-1, 0, 0)
    else:
        print("[❌] add_hole: invalid axis")
        return None

    # ✅ العمق يحدد فقط طول الاسطوانة، نقطة البداية تبقى origin نفسها
    cyl_ax2 = gp_Ax2(origin, direction)
    cyl_shape = BRepPrimAPI_MakeCylinder(cyl_ax2, radius, depth).Shape()

    if cyl_shape is None or cyl_shape.IsNull():
        print("[❌] add_hole: cylinder shape is null")
        return None

    try:
        cut_shape = BRepAlgoAPI_Cut(base_shape, cyl_shape).Shape()
        return cut_shape
    except Exception as e:
        print(f"[❌] add_hole: cut failed: {e}")
        return None










