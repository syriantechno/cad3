from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.gp import gp_Pnt, gp_Trsf
from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

def create_orientation_cube(display):
    ctx = display.Context

    # مكعب صغير
    cube = BRepPrimAPI_MakeBox(10, 10, 10).Shape()
    cube_ais = AIS_Shape(cube)
    cube_ais.SetColor(Quantity_Color(0.8, 0.8, 0.8, Quantity_TOC_RGB))
    cube_ais.SetTransparency(0.4)

    # نقل المكعب إلى زاوية المشهد (مثلاً −500, −500, −500)
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Pnt(0, 0, 0), gp_Pnt(-500, -500, -500))
    cube_ais.SetLocalTransformation(trsf)

    ctx.Display(cube_ais, True)

    return cube_ais