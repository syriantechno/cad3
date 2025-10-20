from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax2
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.GC import GC_MakeCircle
from OCC.Core.Geom import Geom_Circle
from OCC.Core.GeomAPI import GeomAPI_PointsToBSpline
from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_NOC_RED, Quantity_NOC_WHITE
from OCC.Core.GC import GC_MakeArcOfCircle
from OCC.Core.Geom import Geom_TrimmedCurve
from OCC.Core.gp import gp_Vec
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeEdge
from OCC.Display.SimpleGui import init_display

# ========== 🔩 إنشاء ثقب فعلي في المجسم ==========
def add_hole(base_shape, x, y, z, dia, axis="Z", depth=10.0):
    """إنشاء ثقب داخل الشكل باستخدام القطع المنطقي."""
    try:
        radius = dia / 2.0
        dir_map = {
            "X": gp_Dir(1, 0, 0),
            "Y": gp_Dir(0, 1, 0),
            "Z": gp_Dir(0, 0, 1)
        }
        direction = dir_map.get(axis.upper(), gp_Dir(0, 0, 1))
        pos = gp_Pnt(x, y, z)

        # ✅ بناء محور الأسطوانة
        cyl_axis = gp_Ax2(pos, direction)

        # ✅ إنشاء الثقب (أسطوانة)
        tool_cylinder = BRepPrimAPI_MakeCylinder(cyl_axis, radius, depth).Shape()

        # ✅ تنفيذ عملية القطع
        cut_shape = BRepAlgoAPI_Cut(base_shape, tool_cylinder).Shape()
        return cut_shape
    except Exception as e:
        print(f"[❌ add_hole] Failed to create hole: {e}")
        return None


# ========== 📏 قياس الشكل وإظهار النقاط المرجعية ==========
def measure_shape(display, shape):
    """عرض الشكل بقياسات مرجعية بسيطة (النقاط الرئيسية)."""
    try:
        v = BRepBuilderAPI_MakeVertex(gp_Pnt(0, 0, 0)).Vertex()
        ais_v = AIS_Shape(v)
        ais_v.SetColor(Quantity_Color(Quantity_NOC_RED))
        display.Context.Display(ais_v, False)
        return ais_v
    except Exception as e:
        print(f"[❌ measure_shape] {e}")


# ========== 📐 رسم أبعاد مرجعية للثقب ==========
def hole_reference_dimensions(display, x, y, z, shape, offset_above=10, preview=True):
    """إنشاء خطوط مرجعية من نقطة الثقب للمساعدة في التوضيح."""
    try:
        p_start = gp_Pnt(x, y, z)
        p_end = gp_Pnt(x, y, z + offset_above)
        edge = BRepBuilderAPI_MakeEdge(p_start, p_end).Edge()
        ais_edge = AIS_Shape(edge)
        ais_edge.SetColor(Quantity_Color(Quantity_NOC_WHITE))
        display.Context.Display(ais_edge, False)
        return ais_edge
    except Exception as e:
        print(f"[❌ hole_reference_dimensions] {e}")
        return None


# ========== 📏 أبعاد الحجم (القطر والعمق) ==========
def hole_size_dimensions(display, x, y, z, dia, axis, depth, shape, offset_above=10, preview=True):
    """عرض خطوط بسيطة توضح عمق وقطر الثقب."""
    try:
        if axis.upper() == "Z":
            p1 = gp_Pnt(x, y, z)
            p2 = gp_Pnt(x, y, z - depth)
        elif axis.upper() == "Y":
            p1 = gp_Pnt(x, y, z)
            p2 = gp_Pnt(x, y - depth, z)
        else:
            p1 = gp_Pnt(x, y, z)
            p2 = gp_Pnt(x - depth, y, z)

        edge = BRepBuilderAPI_MakeEdge(p1, p2).Edge()
        ais_edge = AIS_Shape(edge)
        ais_edge.SetColor(Quantity_Color(Quantity_NOC_RED))
        display.Context.Display(ais_edge, False)
        return ais_edge
    except Exception as e:
        print(f"[❌ hole_size_dimensions] {e}")
        return None
