from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.gp import gp_Trsf, gp_Vec
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism

def extrude_shape(shape, axis='Y', distance=100):


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

    # تنفيذ الإكسترود مباشرة
    if axis == "Y":
        vec = gp_Vec(0, distance, 0)
    elif axis == "Z":
        vec = gp_Vec(0, 0, distance)
    else:
        vec = gp_Vec(distance, 0, 0)

    prism = BRepPrimAPI_MakePrism(moved, vec).Shape()
    return prism

