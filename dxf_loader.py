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