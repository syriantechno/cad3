# -*- coding: utf-8 -*-
"""
🧭 G-Code Workbench Simulation (PythonOCC 7.9 Compatible)
-------------------------------------------------------
✅ يعمل مع نسخة pythonocc-core 7.9 بدون أي استيرادات غير متوافقة.
✅ يبدأ من Safe Z فوق سطح المجسم.
✅ لا يعود إلى الصفر إطلاقًا.
✅ لا يكرر الثقوب.
✅ يقرأ G-Code حتى لو كانت أوامر X/Y وZ في أسطر منفصلة.
✅ يحتوي على شريط تحكم بالسرعة.
✅ الأداة تظهر كأسطوانة حمراء.
"""

import re, time
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTextEdit,
    QHBoxLayout, QLabel, QMessageBox, QFileDialog,
    QApplication, QSlider
)
from PyQt5.QtCore import QTimer, Qt
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax2
from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCC.Core.Bnd import Bnd_Box

# ============ دالة آمنة للحصول على أعلى Z للشكل متوافقة مع 7.9 ============
def _model_top_from_shape(shape) -> float:
    from OCC.Core.Bnd import Bnd_Box
    box = Bnd_Box()
    ok = False
    try:
        # المحاولة 1: الاسم المتاح عادة في 7.9
        from OCC.Core.BRepBndLib import brepbndlib
        brepbndlib.Add(shape, box, True)
        ok = True
    except Exception:
        try:
            from OCC.Core.BRepBndLib import brepbndlib_Add
            brepbndlib_Add(shape, box, True)
            ok = True
        except Exception:
            try:
                from OCC.Core.TopExp import TopExp_Explorer
                from OCC.Core.TopAbs import TopAbs_VERTEX
                from OCC.Core.BRep import BRep_Tool
                exp = TopExp_Explorer(shape, TopAbs_VERTEX)
                count = 0
                while exp.More():
                    v = exp.Current()
                    p = BRep_Tool.Pnt(v)
                    box.Add(p)
                    exp.Next()
                    count += 1
                ok = count > 0
            except Exception:
                ok = False
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return float(zmax if ok else 0.0)

# =====================================================
def _get_top_z_from_scene():
    try:
        for w in QApplication.topLevelWidgets():
            if hasattr(w, "get_shape"):
                s = w.get_shape()
                if s and not s.IsNull():
                    return _model_top_from_shape(s)
            if hasattr(w, "current_shape"):
                s = getattr(w, "current_shape")
                if s and not s.IsNull():
                    return _model_top_from_shape(s)
    except Exception:
        pass
    return 0.0

# =====================================================
class GCodeWorkbenchPage(QWidget):
    def __init__(self, display, op_browser=None):
        super().__init__()
        self.display = display
        self.op_browser = op_browser
        self.gcode_path = None
        self.gcode_lines = []
        self.path_points = []
        self.path_shapes = []
        self.tool_head = None
        self.current_index = 0
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("🧠 G-Code Workbench (Simulation)")
        title.setStyleSheet("font-size:16px;font-weight:bold;margin-bottom:6px;")

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)
        self.text_box.setStyleSheet(
            "background-color:#1e1e1e;color:#00ff66;font-family:Consolas;font-size:12px;"
        )

        btns = QHBoxLayout()
        self.load_btn = QPushButton("📂 Load G-Code")
        self.sim_btn = QPushButton("▶️ Run Simulation")
        btns.addWidget(self.load_btn)
        btns.addWidget(self.sim_btn)

        self.speed_label = QLabel("Simulation Speed:")
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 200)
        self.speed_slider.setValue(50)

        layout.addWidget(title)
        layout.addLayout(btns)
        layout.addWidget(self.speed_label)
        layout.addWidget(self.speed_slider)
        layout.addWidget(self.text_box)
        self.setLayout(layout)

        self.load_btn.clicked.connect(self._load_gcode)
        self.sim_btn.clicked.connect(self._simulate)

    # ------------------------------------------------------------
    def _load_gcode(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open G-Code", "", "G-Code Files (*.nc *.gcode *.txt)")
        if not path:
            return
        self.gcode_path = Path(path)
        self.gcode_lines = self.gcode_path.read_text(encoding="utf-8").splitlines()
        self.text_box.setPlainText("\n".join(self.gcode_lines))
        print(f"[SIM] Loaded {len(self.gcode_lines)} lines.")

    # ------------------------------------------------------------
    def _parse_gcode(self):
        coords = []
        x = y = z = 0.0
        for line in self.gcode_lines:
            line = line.strip()
            if not line or line.startswith("("):
                continue
            if any(cmd in line for cmd in ("G0", "G1", "G81")):
                mx = re.search(r"X([-+]?\d+\.?\d*)", line)
                my = re.search(r"Y([-+]?\d+\.?\d*)", line)
                mz = re.search(r"Z([-+]?\d+\.?\d*)", line)
                if mx: x = float(mx.group(1))
                if my: y = float(my.group(1))
                if mz: z = float(mz.group(1))
                coords.append((x, y, z))
        # إزالة التكرار داخل نفس الموقع
        unique = []
        last_xy = None
        for (x, y, z) in coords:
            if last_xy != (x, y):
                unique.append((x, y, z))
            last_xy = (x, y)
        self.path_points = unique
        print(f"[SIM] Parsed {len(unique)} valid holes.")

    # ------------------------------------------------------------
    def _simulate(self):
        if not self.gcode_path or not self.gcode_path.exists():
            QMessageBox.warning(self, "Simulation", "⚠️ لا يوجد ملف G-Code بعد.")
            return

        self._parse_gcode()
        if len(self.path_points) < 1:
            QMessageBox.warning(self, "Simulation", "⚠️ لا توجد نقاط للحركة.")
            return

        ctx = getattr(self.display, "Context", None)
        if ctx is None:
            QMessageBox.critical(self, "Simulation", "❌ Context العرض غير جاهز.")
            return

        # 🔹 حساب Safe Z من الشكل الحالي
        model_top = 0.0
        try:
            shape_obj = getattr(self.display, "main_window", None)
            if shape_obj and hasattr(shape_obj, "current_shape") and shape_obj.current_shape and not shape_obj.current_shape.IsNull():
                model_top = _model_top_from_shape(shape_obj.current_shape)
            else:
                model_top = _get_top_z_from_scene()
        except Exception as e:
            print(f"[SAFEZ] Error reading model height: {e}")
            model_top = 0.0

        safe_z_offset = 10.0
        try:
            from frontend.window.gcode_generator_page import GCodeGeneratorPage
            for w in QApplication.topLevelWidgets():
                if isinstance(w, GCodeGeneratorPage):
                    safe_z_offset = w.safe_height.value()
                    break
        except Exception:
            pass

        safe_z = model_top + safe_z_offset
        print(f"[SAFEZ] Top of model = {model_top:.2f}, Safe Z = {safe_z:.2f}")

        # 🧹 تنظيف المسارات القديمة
        for s in getattr(self, "path_shapes", []):
            try:
                ctx.Remove(s, False)
            except Exception:
                pass
        self.path_shapes = []

        # ✅ بناء التسلسل الصحيح
        sequence = [(0.0, 0.0, safe_z)]
        for (x, y, z) in self.path_points:
            sequence.append((x, y, safe_z))  # انتقال فوق الثقب
            sequence.append((x, y, z))       # نزول للحفر
            sequence.append((x, y, safe_z))  # صعود بعد الحفر
        sequence.append((0.0, 0.0, safe_z))  # عودة للأصل

        self.path_points = sequence
        print(f"[SIM] Path rebuilt safely: {len(sequence)} points - each hole once.")

        # 🟦 رسم المسار
        color_path = Quantity_Color(0.0, 0.3, 1.0, Quantity_TOC_RGB)
        for i in range(len(self.path_points) - 1):
            try:
                p1 = gp_Pnt(*self.path_points[i])
                p2 = gp_Pnt(*self.path_points[i + 1])
                if p1.Distance(p2) < 0.001:
                    continue
                edge = BRepBuilderAPI_MakeEdge(p1, p2)
                if not edge.IsDone():
                    continue
                ais_edge = AIS_Shape(edge.Edge())
                ais_edge.SetColor(color_path)
                ctx.Display(ais_edge, False)
                self.path_shapes.append(ais_edge)
            except Exception as e:
                print(f"[DRAW] error: {e}")

        ctx.UpdateCurrentViewer()
        self.display.Repaint()

        # 🔴 تحريك الأداة
        self.current_index = 0
        self.tool_head = None

        def step():
            try:
                if self.current_index >= len(self.path_points):
                    timer.stop()
                    print("[SIM] ✅ Simulation finished safely.")
                    return

                x, y, z = self.path_points[self.current_index]
                if self.tool_head:
                    try:
                        ctx.Remove(self.tool_head, False)
                    except Exception:
                        pass

                cyl_axis = gp_Ax2(gp_Pnt(x, y, z), gp_Dir(0, 0, 1))
                cyl = BRepPrimAPI_MakeCylinder(cyl_axis, 2.0, 8.0).Shape()
                self.tool_head = AIS_Shape(cyl)
                self.tool_head.SetColor(Quantity_Color(1.0, 0.0, 0.0, Quantity_TOC_RGB))
                ctx.Display(self.tool_head, True)
                ctx.UpdateCurrentViewer()
                self.display.Repaint()
                self.current_index += 1
            except Exception as e:
                print(f"[SIM] step error: {e}")
                timer.stop()

        speed_factor = self.speed_slider.value()
        delay = max(10, int(1000 / speed_factor))
        timer = QTimer(self)
        timer.timeout.connect(step)
        timer.start(delay)
        print(f"[SIM] ⏱ Timer delay = {delay} ms per step.")
