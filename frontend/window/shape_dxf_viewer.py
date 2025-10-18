# ============================================================
# shape_dxf_viewer.py — نسخة ثابتة تمنع التكرار
# ============================================================

import ezdxf
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax1, gp_Trsf
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_Transform
from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

def _load_edges(dxf_path: str):
    edges = []
    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
    except Exception as e:
        print(f"[DXF] Load failed: {e}")
        return edges

    for ent in msp:
        t = ent.dxftype()
        if t == "LINE":
            pts = [ent.dxf.start, ent.dxf.end]
        elif t in ("LWPOLYLINE", "POLYLINE"):
            try:
                pts = ent.get_points("xy")
            except Exception:
                continue
        else:
            continue

        last = None
        for p in pts:
            pnt = gp_Pnt(p[0], p[1], 0)
            if last:
                try:
                    edges.append(BRepBuilderAPI_MakeEdge(last, pnt).Edge())
                except Exception as ex:
                    print("[DXF] Edge fail:", ex)
            last = pnt
    print(f"[DXF] edges: {len(edges)}")
    return edges


def show_dxf(display, dxf_path: str, plane: str = "xy"):
    """
    plane: 'xy' لعرض أمامي (عمودي على Z)
           'yz' لعرض جانبي (عمودي على X)
    يعيد قائمة AIS معروضة لسهولة المسح لاحقًا.
    """
    edges = _load_edges(dxf_path)
    ais_list = []
    if not edges:
        return ais_list

    blue = Quantity_Color(0.1, 0.6, 1.0, Quantity_TOC_RGB)   # XY
    yellow = Quantity_Color(1.0, 0.8, 0.0, Quantity_TOC_RGB) # YZ

    rotY90 = gp_Trsf()
    rotY90.SetRotation(gp_Ax1(gp_Pnt(), gp_Dir(0, 1, 0)), +1.5708)  # +90° حول Y

    for e in edges:
        if plane == "xy":
            ais = AIS_Shape(e)
            ais.SetColor(blue)
            display.Context.Display(ais, False)
            ais_list.append(ais)

        elif plane == "yz":
            e2 = BRepBuilderAPI_Transform(e, rotY90, True).Shape()
            ais = AIS_Shape(e2)
            ais.SetColor(yellow)
            display.Context.Display(ais, False)
            ais_list.append(ais)

    display.FitAll()
    display.Context.UpdateCurrentViewer()
    print(f"[DXF] draw plane={plane} (ais={len(ais_list)})")
    return ais_list
