from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE

# ✅ لون الجسم الرمادي الفاتح (قريب من Fusion)
FUSION_BODY_COLOR = Quantity_Color(0.545, 0.533, 0.498, Quantity_TOC_RGB)
BLACK = Quantity_Color(0.0, 0.0, 0.0, Quantity_TOC_RGB)

def display_with_fusion_style(shape, display):
    """
    عرض الشكل بنفس نمط Fusion 360:
    - جسم رمادي فاتح
    - حواف سوداء بارزة
    """
    if shape is None or shape.IsNull():
        print("⚠️ لا يمكن عرض شكل فارغ")
        return

    display.EraseAll()

    # 🟡 الجسم الرئيسي
    body_ais = AIS_Shape(shape)
    body_ais.SetColor(FUSION_BODY_COLOR)
    body_ais.SetDisplayMode(3)  # shaded + edges mode
    display.Context.Display(body_ais, False)
    display.Context.Activate(body_ais, 0, True)
    display.Context.SetColor(body_ais, FUSION_BODY_COLOR, False)

    # ⚫ الحواف السوداء
    edge_explorer = TopExp_Explorer(shape, TopAbs_EDGE)
    while edge_explorer.More():
        edge = edge_explorer.Current()
        edge_ais = AIS_Shape(edge)
        display.Context.Display(edge_ais, False)
        display.Context.SetColor(edge_ais, BLACK, False)
        display.Context.Activate(edge_ais, 0, True)
        edge_explorer.Next()

    display.Context.UpdateCurrentViewer()

def display_preview_shape(shape, display):
        """
        عرض شكل المعاينة بلون مميز (أحمر) بدون تغيير لون الجسم الأساسي.
        """
        if shape is None or shape.IsNull():
            return

        from OCC.Core.AIS import AIS_Shape
        from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

        PREVIEW_COLOR = Quantity_Color(1.0, 0.0, 0.0, Quantity_TOC_RGB)  # أحمر

        ais_preview = AIS_Shape(shape)
        ais_preview.SetColor(PREVIEW_COLOR)
        ais_preview.SetTransparency(0.5)  # شفاف قليلاً لتمييزه
        display.Context.Display(ais_preview, True)

