import ezdxf
import math
from OCC.Core.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge, BRepBuilderAPI_Transform
)
from OCC.Core.BRep import BRep_Builder
from OCC.Core.TopoDS import TopoDS_Compound
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Trsf, gp_Ax1, gp_Circ, gp_Ax2
from OCC.Core.GeomAPI import GeomAPI_PointsToBSpline
from OCC.Core.TColgp import TColgp_Array1OfPnt
from OCC.Core.TopoDS import TopoDS_Shape

def load_dxf_file(file_path):
    """
    يحوّل DXF إلى شكل TopoDS_Compound يدعم:
    - LINE
    - LWPOLYLINE
    - CIRCLE
    - ARC
    - SPLINE
    """
    try:
        doc = ezdxf.readfile(file_path)
    except Exception as e:
        print("❌ Failed to read DXF:", e)
        return None

    msp = doc.modelspace()
    edges = []

    # --------- LINE ----------
    for line in msp.query("LINE"):
        s, e = line.dxf.start, line.dxf.end
        edges.append(
            BRepBuilderAPI_MakeEdge(
                gp_Pnt(s[0], s[1], 0),
                gp_Pnt(e[0], e[1], 0)
            ).Edge()
        )

    # --------- LWPOLYLINE ----------
    for poly in msp.query("LWPOLYLINE"):
        pts = poly.get_points("xy")
        n = len(pts)
        if n < 2:
            continue
        closed = poly.closed
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            if i == n - 1 and not closed:
                break
            edges.append(
                BRepBuilderAPI_MakeEdge(
                    gp_Pnt(x1, y1, 0),
                    gp_Pnt(x2, y2, 0)
                ).Edge()
            )

    # --------- CIRCLE ----------
    for circ in msp.query("CIRCLE"):
        c = circ.dxf.center
        r = circ.dxf.radius
        circ_ax2 = gp_Ax2(gp_Pnt(c[0], c[1], 0), gp_Dir(0, 0, 1))
        circle = gp_Circ(circ_ax2, r)
        edges.append(BRepBuilderAPI_MakeEdge(circle).Edge())

    # --------- ARC ----------
    for arc in msp.query("ARC"):
        c = arc.dxf.center
        r = arc.dxf.radius
        start_angle = math.radians(arc.dxf.start_angle)
        end_angle = math.radians(arc.dxf.end_angle)
        circ_ax2 = gp_Ax2(gp_Pnt(c[0], c[1], 0), gp_Dir(0, 0, 1))
        circle = gp_Circ(circ_ax2, r)
        edges.append(
            BRepBuilderAPI_MakeEdge(circle, start_angle, end_angle).Edge()
        )

    # --------- SPLINE ----------
    for spline in msp.query("SPLINE"):
        fit_points = spline.fit_points
        n = len(fit_points)
        if n >= 2:
            arr = TColgp_Array1OfPnt(1, n)
            for i, pt in enumerate(fit_points, start=1):
                arr.SetValue(i, gp_Pnt(pt[0], pt[1], 0))
            bspline = GeomAPI_PointsToBSpline(arr).Curve()
            edges.append(BRepBuilderAPI_MakeEdge(bspline).Edge())

    if not edges:
        print("❌ No valid geometry found in DXF.")
        return None

    # --------- COMPOUND ----------
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    for e in edges:
        builder.Add(compound, e)

    print(f"✅ DXF loaded with {len(edges)} edges")
    return compound

from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace

def make_face_from_edges(shape: TopoDS_Compound):
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_EDGE
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace

    wire_builder = BRepBuilderAPI_MakeWire()
    exp = TopExp_Explorer(shape, TopAbs_EDGE)
    edge_count = 0

    while exp.More():
        edge = exp.Current()
        wire_builder.Add(edge)
        edge_count += 1
        exp.Next()

    print(f"🔍 عدد الحواف المضافة إلى Wire: {edge_count}")

    if not wire_builder.IsDone():
        print("❌ فشل بناء Wire: الحواف غير متصلة أو غير صالحة")
        return None

    wire = wire_builder.Wire()
    if wire.IsNull():
        print("❌ Wire فارغ بعد البناء")
        return None

    face = BRepBuilderAPI_MakeFace(wire).Face()
    print("✅ تم بناء Face من الحواف بنجاح")
    return face

from OCC.Core.ShapeAnalysis import ShapeAnalysis_FreeBounds
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCC.Core.TopTools import TopTools_ListOfShape

from OCC.Core.ShapeAnalysis import ShapeAnalysis_FreeBounds
from OCC.Core.TopTools import TopTools_ListOfShape
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace

from OCC.Core.ShapeAnalysis import ShapeAnalysis_FreeBounds
from OCC.Core.TopAbs import TopAbs_WIRE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace

from OCC.Core.ShapeAnalysis import ShapeAnalysis_FreeBounds
from OCC.Core.TopAbs import TopAbs_WIRE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace

def build_face_from_loose_edges(shape: TopoDS_Shape):
    wire_builder = BRepBuilderAPI_MakeWire()
    exp = TopExp_Explorer(shape, TopAbs_EDGE)
    count = 0
    while exp.More():
        wire_builder.Add(exp.Current())
        count += 1
        exp.Next()

    if not wire_builder.IsDone():
        print("❌ فشل بناء Wire من الحواف غير المتصلة")
        return None

    wire = wire_builder.Wire()
    face = BRepBuilderAPI_MakeFace(wire).Face()
    if face.IsNull():
        print("❌ فشل بناء Face من Wire المفتوح")
        return None

    print(f"✅ تم بناء وجه من {count} حافة غير متصلة")
    return face


def extract_closed_faces_from_edges(shape: TopoDS_Shape):
    free_bounds = ShapeAnalysis_FreeBounds(shape, 1e-6, False, False)
    closed_wires_compound = free_bounds.GetClosedWires()
    faces = []

    exp = TopExp_Explorer(closed_wires_compound, TopAbs_WIRE)
    count = 0
    while exp.More():
        wire = exp.Current()
        face = BRepBuilderAPI_MakeFace(wire).Face()
        if not face.IsNull():
            faces.append(face)
            count += 1
        exp.Next()

    print(f"✅ تم استخراج {count} وجه مغلق من DXF")
    if not faces:
        print("⚠️ لا توجد حلقات مغلقة، محاولة بناء وجه من الحواف المفتوحة")
        return build_face_from_loose_edges(shape)

from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire
from OCC.Core.BRep import BRep_Tool
from OCC.Core.gp import gp_Pnt

def build_closed_wire_from_edges(shape: TopoDS_Shape, tolerance=1e-3):
    exp = TopExp_Explorer(shape, TopAbs_EDGE)
    edges = []
    points = []

    while exp.More():
        edge = exp.Current()
        curve = BRep_Tool.Curve(edge)[0]
        if curve is None:
            exp.Next()
            continue
        curve_handle, first_param, last_param = BRep_Tool.Curve(edge)
        if curve_handle is None:
            continue
        p1 = curve_handle.Value(first_param)
        p2 = curve_handle.Value(last_param)
        edges.append(edge)
        points.append((p1, p2))
        exp.Next()

    wire_builder = BRepBuilderAPI_MakeWire()
    for edge in edges:
        wire_builder.Add(edge)

    if not wire_builder.IsDone():
        print("❌ فشل بناء Wire يدويًا")
        return None

    wire = wire_builder.Wire()
    print(f"✅ تم بناء Wire يدويًا من {len(edges)} حافة")
    return wire

from OCC.Core.ShapeFix import ShapeFix_Wire
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire

def fix_and_build_wire(shape: TopoDS_Shape):
    wire_builder = BRepBuilderAPI_MakeWire()
    exp = TopExp_Explorer(shape, TopAbs_EDGE)
    while exp.More():
        wire_builder.Add(exp.Current())
        exp.Next()

    wire = wire_builder.Wire()
    if wire.IsNull():
        print("❌ Wire فارغ بعد التجميع")
        return None

    fixer = ShapeFix_Wire(wire)
    fixer.FixWire()
    fixed_wire = fixer.Wire()
    if fixed_wire.IsNull():
        print("❌ فشل إصلاح Wire")
        return None

    print("✅ تم إصلاح وبناء Wire مغلق باستخدام ShapeFix")
    return fixed_wire