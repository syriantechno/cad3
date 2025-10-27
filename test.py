# -*- coding: utf-8 -*-
"""
Fusion-style Viewer (pythonocc-core 7.8 / 7.9)
- Grid limited & clean
- Colored axes with labels
- Metal gray cube
- Custom hover/select colors
"""

from OCC.Display.backend import load_backend
load_backend("pyqt5")

from OCC.Display.qtDisplay import qtViewer3d
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCC.Core.AIS import AIS_Shape, AIS_Line, AIS_TextLabel
from OCC.Core.gp import gp_Pnt, gp_Dir
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
import sys

GRID_SIZE = 300   # نصف عرض الشبكة
GRID_STEP = 20    # المسافة بين الخطوط

class FusionViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.viewer = qtViewer3d(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.viewer)
        self.setLayout(layout)
        self.init_scene()

    def init_scene(self):
        self.display = self.viewer._display
        self.ctx = self.display.Context
        self.view = self.display.View

        # 🎨 Hover / Select
        try:
            hl_style = self.ctx.HighlightStyle()
            hl_style.SetColor(Quantity_Color(1.0, 0.6, 0.1, Quantity_TOC_RGB))  # Fusion orange
            self.ctx.SetHighlightStyle(hl_style)
            sel_style = self.ctx.SelectionStyle()
            sel_style.SetColor(Quantity_Color(0.2, 0.6, 1.0, Quantity_TOC_RGB))  # blue
            self.ctx.SetSelectionStyle(sel_style)
        except Exception:
            pass

        # 🧱 Cube
        cube = AIS_Shape(BRepPrimAPI_MakeBox(100, 60, 40).Shape())
        metal = Quantity_Color(0.7, 0.7, 0.72, Quantity_TOC_RGB)
        cube.SetColor(metal)
        cube.SetTransparency(0.05)
        self.ctx.Display(cube, True)

        # 🩶 Grid
        self._draw_grid(size=GRID_SIZE, step=GRID_STEP)

        # 🧭 Axes with labels
        self._draw_axes_with_labels(length=200)

        # ⚙️ Scene setup
        self.display.Viewer.SetDefaultLights()
        self.display.Viewer.SetLightOn()
        self.view.SetBackgroundColor(Quantity_Color(0.96, 0.96, 0.96, Quantity_TOC_RGB))
        self.view.FitAll()
        self.view.Redraw()
        print("✅ Fusion viewer جاهز — Grid + Axes + Cube + Highlight colors.")

    # ---------------------------------------------------------------------
    def _draw_grid(self, size=300, step=20):
        """شبكة XY محدودة باستخدام Edges حقيقية"""
        base = Quantity_Color(0.90, 0.90, 0.90, Quantity_TOC_RGB)
        major = Quantity_Color(0.75, 0.75, 0.75, Quantity_TOC_RGB)
        border = Quantity_Color(0.55, 0.55, 0.55, Quantity_TOC_RGB)

        def draw_segment(p1, p2, color, width=1.0):
            edge = BRepBuilderAPI_MakeEdge(p1, p2).Edge()
            shape = AIS_Shape(edge)
            shape.SetColor(color)
            shape.SetWidth(width)
            self.ctx.Display(shape, False)
            self.ctx.SetAutoActivateSelection(False)

        for x in range(-size, size + step, step):
            col = major if x % (step * 10) == 0 else base
            draw_segment(gp_Pnt(x, -size, 0), gp_Pnt(x, size, 0),
                         col, 1.5 if col is major else 1.0)

        for y in range(-size, size + step, step):
            col = major if y % (step * 10) == 0 else base
            draw_segment(gp_Pnt(-size, y, 0), gp_Pnt(size, y, 0),
                         col, 1.5 if col is major else 1.0)

        # إطار خارجي
        draw_segment(gp_Pnt(-size, -size, 0), gp_Pnt(size, -size, 0), border, 2.0)
        draw_segment(gp_Pnt(size, -size, 0), gp_Pnt(size, size, 0), border, 2.0)
        draw_segment(gp_Pnt(size, size, 0), gp_Pnt(-size, size, 0), border, 2.0)
        draw_segment(gp_Pnt(-size, size, 0), gp_Pnt(-size, -size, 0), border, 2.0)
        print(f"🩶 Grid ready ({size*2}x{size*2}mm)")

    # ---------------------------------------------------------------------
    def _draw_axes_with_labels(self, length=200):
        """محاور ملونة مع تسميات X/Y/Z"""
        colX = Quantity_Color(1, 0, 0, Quantity_TOC_RGB)
        colY = Quantity_Color(0, 0.85, 0, Quantity_TOC_RGB)
        colZ = Quantity_Color(0, 0.4, 1, Quantity_TOC_RGB)

        def line(p1, p2, color):
            edge = BRepBuilderAPI_MakeEdge(p1, p2).Edge()
            shape = AIS_Shape(edge)
            shape.SetColor(color)
            shape.SetWidth(3.0)
            self.ctx.Display(shape, False)

        origin = gp_Pnt(0, 0, 0)
        line(origin, gp_Pnt(length, 0, 0), colX)
        line(origin, gp_Pnt(0, length, 0), colY)
        line(origin, gp_Pnt(0, 0, length), colZ)

        # Labels
        def label(txt, pos, color):
            t = AIS_TextLabel()
            t.SetColor(color)
            t.SetHeight(16.0)
            t.SetPosition(pos)
            t.SetText(txt)
            self.ctx.Display(t, False)

        label("X", gp_Pnt(length + 10, 0, 0), colX)
        label("Y", gp_Pnt(0, length + 10, 0), colY)
        label("Z", gp_Pnt(0, 0, length + 10), colZ)

# ---------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = FusionViewer()
    w.setWindowTitle("Fusion-style Viewer (Grid + Axes + Cube)")
    w.resize(1000, 800)
    w.show()
    sys.exit(app.exec_())
