# -*- coding: utf-8 -*-
"""
🎛️ G-Code Workbench Page (Stable CNC Simulation)
------------------------------------------------
إصدار مستقر وآمن مع:
✅ حماية كاملة من الكراش (حتى لو G81 بدون X/Y/Z).
✅ احتفاظ بآخر موقع عند غياب الإحداثيات.
✅ أداة حفر مرئية على شكل أسطوانة حمراء.
✅ خطوط مسار زرقاء فوق البروفايل دون مسح الشكل.
"""

import re, time
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTextEdit,
    QHBoxLayout, QLabel, QMessageBox, QFileDialog
)
from PyQt5.QtCore import QTimer
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax2
from OCC.Core.Geom import Geom_CartesianPoint
from PyQt5.QtCore import QTimer
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax2
from OCC.Core.Geom import Geom_CartesianPoint
from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder

from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB


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

    # ------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("🧠 G-Code Workbench (CNC Simulation)")
        title.setStyleSheet("font-size:16px;font-weight:bold;margin-bottom:6px;")

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)
        self.text_box.setStyleSheet(
            "background-color:#1e1e1e;color:#00ff66;font-family:Consolas;font-size:12px;"
        )

        btns = QHBoxLayout()
        self.load_btn = QPushButton("📂 Load G-Code File")
        self.sim_btn = QPushButton("▶️ Run Simulation")
        self.load_btn.setStyleSheet("background-color:#3a3a3a;color:white;padding:6px 10px;border-radius:8px;")
        self.sim_btn.setStyleSheet("background-color:#3a3a3a;color:white;padding:6px 10px;border-radius:8px;")
        btns.addWidget(self.load_btn)
        btns.addWidget(self.sim_btn)

        layout.addWidget(title)
        layout.addLayout(btns)
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
        print(f"[SIM] Loaded {len(self.gcode_lines)} G-Code lines.")

    # ------------------------------------------------------------
    def _parse_gcode(self):
        coords = []
        x = y = z = 0.0
        last_valid = (0.0, 0.0, 0.0)
        for line in self.gcode_lines:
            line = line.strip()
            if not line or line.startswith("("):
                continue
            if any(cmd in line for cmd in ("G0", "G1", "G81")):
                mx = re.search(r"X([-+]?\d+\.?\d*)", line)
                my = re.search(r"Y([-+]?\d+\.?\d*)", line)
                mz = re.search(r"Z([-+]?\d+\.?\d*)", line)

                # تحديث الإحداثيات الحالية أو الاحتفاظ بالقيمة السابقة
                if mx:
                    x = float(mx.group(1))
                if my:
                    y = float(my.group(1))
                if mz:
                    z = float(mz.group(1))
                else:
                    z = last_valid[2]

                # تجاهل النقاط غير الصالحة
                if any(v is None for v in (x, y, z)):
                    print(f"[⚠️ Skipped invalid point] X={x}, Y={y}, Z={z}")
                    continue

                last_valid = (x, y, z)
                coords.append((x, y, z))

        self.path_points = coords
        print(f"[SIM] Parsed {len(coords)} G-Code points.")

    # ------------------------------------------------------------
    def _simulate(self):
        if not self.gcode_path or not self.gcode_path.exists():
            QMessageBox.warning(self, "Simulation", "⚠️ لا يوجد ملف G-Code بعد.")
            return

        self._parse_gcode()
        if len(self.path_points) < 2:
            QMessageBox.warning(self, "Simulation", "⚠️ عدد النقاط غير كافٍ للمحاكاة.")
            return

        ctx = getattr(self.display, "Context", None)
        if ctx is None:
            QMessageBox.critical(self, "Simulation", "❌ Context العرض غير جاهز.")
            return

        # 🧹 تنظيف المسار السابق فقط
        for s in getattr(self, "path_shapes", []):
            try:
                ctx.Remove(s, False)
            except Exception:
                pass
        self.path_shapes = []

        # 🟦 رسم المسار الأزرق
        color_path = Quantity_Color(0.0, 0.3, 1.0, Quantity_TOC_RGB)
        for i in range(len(self.path_points) - 1):
            p1 = gp_Pnt(*self.path_points[i])
            p2 = gp_Pnt(*self.path_points[i + 1])
            edge = BRepBuilderAPI_MakeEdge(p1, p2).Edge()
            ais_edge = AIS_Shape(edge)
            ais_edge.SetColor(color_path)
            ctx.Display(ais_edge, False)
            self.path_shapes.append(ais_edge)
        self.display.Context.UpdateCurrentViewer()
        self.display.Repaint()

        # 🔴 تحضير أداة الحفر (أسطوانة)
        self.current_index = 0
        self.tool_head = None

        def step():
            try:
                if self.current_index >= len(self.path_points):
                    timer.stop()
                    print("[SIM] ✅ Simulation finished safely.")
                    return

                x, y, z = self.path_points[self.current_index]

                # مسح الأداة السابقة
                if self.tool_head:
                    ctx.Remove(self.tool_head, False)

                # إنشاء أسطوانة تمثل رأس الحفر
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

        # ⏱️ استخدام QTimer لتشغيل المحاكاة بأمان في main thread
        timer = QTimer(self)
        timer.timeout.connect(step)
        timer.start(80)

        print(f"[SIM] Started safely with {len(self.path_points)} points.")
