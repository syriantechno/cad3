from OCC.Display.SimpleGui import init_display
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCC.Core.gp import gp_Pnt, gp_Pln, gp_Dir
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.AIS import AIS_TextLabel, AIS_ColoredShape
from OCC.Core.TCollection import TCollection_ExtendedString


class OperationPanel3D:
    """لوحة عمليات زجاجية داخل العارض"""
    def __init__(self, display):
        self.display = display
        self.ctx = display.Context
        self.elements = {}

        # 🎨 إنشاء اللوحة الزجاجية الأساسية
        self.panel = self._create_glass_panel(0, 0, 60, width=180, height=90)
        self.elements["panel"] = self.panel

        # 🧱 نصوص ديناميكية
        self.title_label = self._create_text("🔧 عملية: Extrude", 0, 0, 63, 16)
        self.status_label = self._create_text("⚙️ الحالة: قيد التنفيذ...", 0, 0, 53, 12)

        # 🟦 زرّ تفاعلي وهمي (مكعب صغير)
        self.button = self._create_button(0, 40, 60)
        self.elements["button"] = self.button

        display.FitAll()
        display.Repaint()

    def _create_glass_panel(self, x, y, z, width=100, height=60):
        """إنشاء وجه شفاف كلوحة"""
        pln = gp_Pln(gp_Pnt(x, y, z), gp_Dir(0, 0, 1))
        face = BRepBuilderAPI_MakeFace(pln, -width/2, width/2, -height/2, height/2).Face()
        ais = self.display.DisplayShape(face, update=False)[0]
        ais.SetColor(Quantity_Color(0.9, 0.95, 1.0, Quantity_TOC_RGB))
        ais.SetTransparency(0.7)
        return ais

    def _create_text(self, text, x, y, z, size=14):
        """إضافة نص 3D فوق اللوحة"""
        label = AIS_TextLabel()
        label.SetText(TCollection_ExtendedString(text))
        label.SetPosition(gp_Pnt(x, y, z))
        label.SetHeight(size)
        label.SetColor(Quantity_Color(0.2, 0.2, 0.3, Quantity_TOC_RGB))
        self.ctx.Display(label, False)
        return label

    def _create_button(self, x, y, z, size=12):
        """زر 3D بسيط"""
        box = BRepPrimAPI_MakeBox(gp_Pnt(x - size/2, y - size/2, z - 2), size, size, 4).Shape()
        ais_box = self.display.DisplayShape(box, update=False)[0]
        ais_box.SetColor(Quantity_Color(0.3, 0.5, 0.9, Quantity_TOC_RGB))
        ais_box.SetTransparency(0.2)
        return ais_box

    def update_status(self, new_text, color=(0.3, 0.5, 0.3)):
        """تحديث نص الحالة"""
        self.status_label.SetText(TCollection_ExtendedString(new_text))
        self.status_label.SetColor(Quantity_Color(*color, Quantity_TOC_RGB))
        self.display.Repaint()

    def handle_click(self, picked_shape):
        """رد فعل عند النقر"""
        if picked_shape == self.button.Shape():
            print("🟢 تم الضغط على الزرّ داخل العارض!")
            self.update_status("✅ الاكتمال: تمت العملية بنجاح", (0.1, 0.6, 0.2))
        else:
            print("👆 تم الضغط على شكل آخر.")


def main():
    display, start_display, add_menu, add_function = init_display("pyqt5")

    # 📦 مجسم رئيسي
    box = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), 80, 80, 80).Shape()
    display.DisplayShape(box, update=False)

    # 🧊 إنشاء اللوحة الزجاجية
    panel = OperationPanel3D(display)

    # 🖱️ دعم النقر داخل العارض
    def on_click(event):
        picked = display.Context.DetectedShape()
        if not picked.IsNull():
            panel.handle_click(picked)

    display.register_mouse_press(on_click)
    display.FitAll()
    start_display()


if __name__ == "__main__":
    main()
