from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit, QFileDialog, QHBoxLayout
from OCC.Core.gp import gp_Pnt
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeVertex
from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Display.SimpleGui import init_display
import re, time

class GCodeSimulatorPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.display = parent.display

        layout = QVBoxLayout(self)
        self.load_btn = QPushButton("📂 Load G-Code File")
        self.sim_btn = QPushButton("▶️ Start Simulation")
        self.text_box = QTextEdit()
        self.text_box.setPlaceholderText("G-Code content will appear here...")

        btns = QHBoxLayout()
        btns.addWidget(self.load_btn)
        btns.addWidget(self.sim_btn)
        layout.addLayout(btns)
        layout.addWidget(self.text_box)

        self.load_btn.clicked.connect(self.load_gcode)
        self.sim_btn.clicked.connect(self.simulate)
        self.gcode_lines = []
        self.path_points = []
        self.tool_shape = None

    def load_gcode(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open G-Code", "", "G-Code Files (*.nc *.gcode *.txt)")
        if not path:
            return
        with open(path, "r") as f:
            lines = f.readlines()
        self.gcode_lines = [ln.strip() for ln in lines if ln.strip()]
        self.text_box.setPlainText("\n".join(self.gcode_lines))
        print(f"[SIM] Loaded {len(self.gcode_lines)} G-Code lines.")

    def parse_gcode(self):
        coords = []
        x = y = z = 0.0
        for line in self.gcode_lines:
            if line.startswith("(") or not line:
                continue
            if "G0" in line or "G1" in line or "G81" in line:
                if "X" in line:
                    x = float(re.findall(r"X([-+]?[0-9]*\.?[0-9]+)", line)[0])
                if "Y" in line:
                    y = float(re.findall(r"Y([-+]?[0-9]*\.?[0-9]+)", line)[0])
                if "Z" in line:
                    z = float(re.findall(r"Z[-]?([0-9]*\.?[0-9]+)", line)[0]) * (-1 if "Z-" in line else 1)
                coords.append((x, y, z))
        self.path_points = coords
        print(f"[SIM] Parsed {len(coords)} points from G-Code.")

    def simulate(self):
        """▶️ محاكاة حركة الأداة بناء على G-Code (آمن ومستقر تماماً)"""
        if not self.gcode_lines:
            print("[SIM] No G-Code loaded.")
            return

        self.parse_gcode()
        if not self.path_points or len(self.path_points) < 2:
            print("[SIM] Not enough points to simulate.")
            return

        from OCC.Core.gp import gp_Pnt
        from OCC.Core.Geom import Geom_CartesianPoint
        from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
        from OCC.Core.AIS import AIS_Shape, AIS_Point
        from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
        from PyQt5.QtCore import QCoreApplication
        import time

        disp, ctx = self.display, self.display.Context

        # 🧹 تنظيف أي مسار سابق
        try:
            if hasattr(self, "path_shapes"):
                for s in self.path_shapes:
                    ctx.Remove(s, False)
        except Exception:
            pass
        self.path_shapes = []

        # ✅ إدخال نقطة البداية عند الأصل 0,0,0 لرؤية مسار الوصول
        if self.path_points and self.path_points[0] != (0.0, 0.0, 0.0):
            self.path_points.insert(0, (0.0, 0.0, 0.0))
            print("[SIM] Origin (0,0,0) inserted as start point.")

        # 🟦 رسم خطوط المسار
        color_path = Quantity_Color(0.0, 0.0, 1.0, Quantity_TOC_RGB)
        for i in range(len(self.path_points) - 1):
            p1 = gp_Pnt(*self.path_points[i])
            p2 = gp_Pnt(*self.path_points[i + 1])
            edge = BRepBuilderAPI_MakeEdge(p1, p2).Edge()
            ais = AIS_Shape(edge)
            ais.SetColor(color_path)
            ctx.Display(ais, False)
            self.path_shapes.append(ais)
        disp.FitAll()
        disp.Repaint()
        # 🔴 إنشاء أداة المحاكاة كنقطة هندسية
        color_tool = Quantity_Color(1.0, 0.0, 0.0, Quantity_TOC_RGB)
        last_point = None
        print(f"[SIM] Starting animation with {len(self.path_points)} points...")

        for (x, y, z) in self.path_points:
            try:
                # إزالة النقطة القديمة
                if last_point:
                    ctx.Remove(last_point, False)

                # إنشاء نقطة هندسية جديدة (Geom_CartesianPoint)
                geom_pt = Geom_CartesianPoint(gp_Pnt(x, y, z))
                pnt = AIS_Point(geom_pt)
                pnt.SetColor(color_tool)
                ctx.Display(pnt, True)
                last_point = pnt

                ctx.UpdateCurrentViewer()
                QCoreApplication.processEvents()
                time.sleep(0.05)


            except Exception as e:
                print(f"[SIM] step error: {e}")
                continue

        # تنظيف النقطة الأخيرة
        try:
            if last_point:
                ctx.Remove(last_point, False)
        except Exception:
            pass

        disp.Repaint()
        print("[SIM] Simulation finished safely.")



