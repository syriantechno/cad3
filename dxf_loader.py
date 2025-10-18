import ezdxf
import numpy as np
from OCC.Core.gp import gp_Pnt
from OCC.Core.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_MakeFace,
)
from OCC.Core.BRep import BRep_Builder
from OCC.Core.TopoDS import TopoDS_Compound, TopoDS_Shape


def build_closed_wire(pts, close_tol=1e-3):
    mk = BRepBuilderAPI_MakeWire()
    clean = []
    for p in pts:
        if not clean or (abs(p[0] - clean[-1][0]) + abs(p[1] - clean[-1][1])) > 1e-9:
            clean.append(p)

    if len(clean) < 2:
        print("❌ عدد النقاط غير كافٍ لبناء Wire")
        return None

    if abs(clean[0][0] - clean[-1][0]) + abs(clean[0][1] - clean[-1][1]) > close_tol:
        print("🔁 تم إغلاق المسار تلقائيًا")
        clean.append(clean[0])

    for i in range(len(clean) - 1):
        p1, p2 = clean[i], clean[i + 1]
        e = BRepBuilderAPI_MakeEdge(gp_Pnt(p1[0], p1[1], 0), gp_Pnt(p2[0], p2[1], 0))
        if e.IsDone():
            mk.Add(e.Edge())
    return mk.Wire()


def make_edge_from_points(p1, p2):
    return BRepBuilderAPI_MakeEdge(gp_Pnt(*p1), gp_Pnt(*p2)).Edge()


def make_compound_from_edges(edges):
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    for edge in edges:
        builder.Add(compound, edge)
    return compound


def smart_load_dxf(path: str) -> TopoDS_Shape:
    print(f"📂 تحميل وتحليل ملف DXF: {path}")
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
    except Exception as e:
        print(f"❌ فشل قراءة الملف: {e}")
        return None

    edges = []
    for e in msp:
        try:
            if e.dxftype() == "LINE":
                start, end = e.dxf.start, e.dxf.end
                edges.append(make_edge_from_points(start, end))

            elif e.dxftype() == "SPLINE":
                bs = e.construction_tool()
                knots = bs.knots()
                t_min, t_max = knots[0], knots[-1]
                T = np.linspace(t_min, t_max, 800)
                pts = [(float(bs.point(t).x), float(bs.point(t).y)) for t in T]

                # فحص الإغلاق هندسيًا بدل .closed
                if np.allclose(bs.point(t_min), bs.point(t_max), atol=1e-3):
                    pts.append(pts[0])
                    print("🔁 المسار مغلق هندسيًا")
                else:
                    print("🔓 المسار مفتوح هندسيًا")

                wire = build_closed_wire(pts)
                if wire:
                    face = BRepBuilderAPI_MakeFace(wire).Face()
                    if not face.IsNull():
                        print("✅ تم بناء وجه هندسي من Spline")
                        return face
                    else:
                        print("⚠️ فشل بناء Face من Spline")
                else:
                    print("⚠️ فشل بناء Wire من Spline")

            else:
                print(f"⚠️ تجاهل الكائن: {e.dxftype()}")

        except Exception as ex:
            print(f"❌ كائن غير صالح: {e.dxftype()} → {ex}")

    if not edges:
        print("❌ لا يوجد هندسة قابلة للتحميل")
        return None

    compound = make_compound_from_edges(edges)
    print(f"✅ تم بناء Compound من {len(edges)} حافة")
    return compound