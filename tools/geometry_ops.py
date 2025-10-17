from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeCylinder
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.gp import gp_Vec, gp_Dir, gp_Pnt, gp_Ax2
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.gp import gp_Trsf, gp_Vec
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.gp import gp_Pnt


def add_hole(shape, x, y, z, dia, axis='Y'):
    if axis == "Y":
        dir_vec = gp_Dir(0,1,0)
    elif axis == "Z":
        dir_vec = gp_Dir(0,0,1)
    else:
        dir_vec = gp_Dir(1,0,0)
    height = 10000
    cyl = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,z), dir_vec), dia/2, height).Shape()
    new_shape = BRepAlgoAPI_Cut(shape, cyl).Shape()
    return new_shape

def preview_hole(x, y, z, dia, axis='Y'):
    if axis == "Y":
        dir_vec = gp_Dir(0, 1, 0)
    elif axis == "Z":
        dir_vec = gp_Dir(0, 0, 1)
    else:
        dir_vec = gp_Dir(1, 0, 0)

    height = 50  # طول المعاينة فقط
    cyl = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x, y, z), dir_vec), dia / 2, height).Shape()
    return cyl


def extrude_shape(shape, axis='Y', distance=100):
    """تنفيذ عملية الإكسترود على شكل حسب المحور والمسافة المحددين"""
    if shape is None or shape.IsNull():
        return None

    # حساب حدود الشكل
    bbox = Bnd_Box()
    brepbndlib.Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

    # نقل الشكل إلى (0,0,0)
    dx = -xmin
    dy = -ymin
    dz = -zmin
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(dx, dy, dz))
    moved = BRepBuilderAPI_Transform(shape, trsf, True).Shape()

    # اتجاه الإكسترود
    axis = axis.upper()
    if axis == "Y":
        vec = gp_Vec(0, distance, 0)
    elif axis == "Z":
        vec = gp_Vec(0, 0, distance)
    else:
        vec = gp_Vec(distance, 0, 0)

    prism = BRepPrimAPI_MakePrism(moved, vec).Shape()
    return prism




def add_box_cut(shape, x, y, z, width, height, depth, axis='Z'):
    """
    قص شكل Box ممتد في اتجاه محور X أو Y أو Z لمسافة كبيرة.
    يشبه add_hole ولكن بصندوق مستطيل بدلاً من أسطوانة.
    """
    if shape is None or shape.IsNull():
        return None

    axis = axis.upper()

    # نحدد اتجاه الامتداد
    if axis == "Y":
        vec = gp_Vec(0, 1, 0)
    elif axis == "Z":
        vec = gp_Vec(0, 0, 1)
    else:
        vec = gp_Vec(1, 0, 0)

    # نصنع الصندوق
    long_length = 10000  # امتداد كبير للقص
    if axis == "X":
        box_shape = BRepPrimAPI_MakeBox(long_length, height, depth).Shape()
    elif axis == "Y":
        box_shape = BRepPrimAPI_MakeBox(width, long_length, depth).Shape()
    else:  # Z
        box_shape = BRepPrimAPI_MakeBox(width, height, long_length).Shape()

    # نحرك الصندوق إلى الموضع المطلوب
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(x, y, z))
    moved_box = BRepBuilderAPI_Transform(box_shape, trsf, True).Shape()

    # نطبق القطع
    result = BRepAlgoAPI_Cut(shape, moved_box).Shape()
    return result


def preview_box_cut(x, y, z, width, height, depth, axis='Z'):
    axis = axis.upper()

    if axis == "X":
        box_shape = BRepPrimAPI_MakeBox(50, height, depth).Shape()
    elif axis == "Y":
        box_shape = BRepPrimAPI_MakeBox(width, 50, depth).Shape()
    else:  # Z
        box_shape = BRepPrimAPI_MakeBox(width, height, 50).Shape()

    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(x, y, z))
    moved_box = BRepBuilderAPI_Transform(box_shape, trsf, True).Shape()
    return moved_box

from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.gp import gp_Vec

def preview_extrude(shape, axis='Y', distance=100):
    """
    إنشاء شكل معاينة للإكسترود دون تغيير الشكل الأصلي.
    لا يُستخدم لنقل الشكل أو حفظه.
    """
    if axis == "Y":
        vec = gp_Vec(0, distance, 0)
    elif axis == "Z":
        vec = gp_Vec(0, 0, distance)
    else:
        vec = gp_Vec(distance, 0, 0)

    return BRepPrimAPI_MakePrism(shape, vec).Shape()


