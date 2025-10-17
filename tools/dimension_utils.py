# ===========================================
# 📄 dimension_utils.py
# أدوات القياسات بين مركز الشكل والحواف (X/Y)
# ===========================================

from OCC.Core.gp import gp_Pnt
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.AIS import AIS_LengthDimension
from OCC.Core.TCollection import TCollection_ExtendedString

def add_measurements_between_edges_and_center(display, dim_mgr, shape, group="preview"):
    """
    يرسم قياسات بين مركز الشكل (هول أو بوكس) وأقرب الحواف (X و Y)
    تظهر القياسات فوق المجسم، وتعمل في المعاينة والتطبيق النهائي.

    :param display: كائن العرض الرئيسي (AIS_InteractiveContext)
    :param dim_mgr: مدير القياسات الذي يحتوي على add() و clear_group()
    :param shape: الشكل الهدف (TopoDS_Shape)
    :param group: اسم المجموعة التي ستضاف إليها القياسات (preview / final)
    """
    if shape is None:
        print("⚠️ add_measurements_between_edges_and_center: shape is None")
        return

    # 🧭 حساب الـ Bounding Box
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

    # 📍 مركز الشكل
    center = gp_Pnt(
        (xmax + xmin) / 2.0,
        (ymax + ymin) / 2.0,
        (zmax + zmin) / 2.0
    )

    # 🧮 أقرب حافة على محور X
    dist_x_min = abs(center.X() - xmin)
    dist_x_max = abs(center.X() - xmax)
    x_edge = xmin if dist_x_min < dist_x_max else xmax
    p_edge_x = gp_Pnt(x_edge, center.Y(), center.Z())

    # 🧮 أقرب حافة على محور Y
    dist_y_min = abs(center.Y() - ymin)
    dist_y_max = abs(center.Y() - ymax)
    y_edge = ymin if dist_y_min < dist_y_max else ymax
    p_edge_y = gp_Pnt(center.X(), y_edge, center.Z())

    # 📏 قياس X
    length_x = abs(center.X() - x_edge)
    dim_x = AIS_LengthDimension(
        p_edge_x, center,
        TCollection_ExtendedString(f"X: {length_x:.2f}")
    )
    text_pos_x = gp_Pnt((center.X() + x_edge) / 2.0, center.Y(), zmax + 5)
    dim_x.SetTextPosition(text_pos_x)

    # 📏 قياس Y
    length_y = abs(center.Y() - y_edge)
    dim_y = AIS_LengthDimension(
        p_edge_y, center,
        TCollection_ExtendedString(f"Y: {length_y:.2f}")
    )
    text_pos_y = gp_Pnt(center.X(), (center.Y() + y_edge) / 2.0, zmax + 5)
    dim_y.SetTextPosition(text_pos_y)

    # ➕ إضافتها للمجموعة
    dim_mgr.add(dim_x, group=group)
    dim_mgr.add(dim_y, group=group)

    # ✅ إعادة رسم
    display.Repaint()
    print(f"✅ [dimension_utils] تم توليد قياسات X/Y لمجموعة: {group}")
