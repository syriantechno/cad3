# -*- coding: utf-8 -*-
"""
⚙️ G-Code Generator Page with A-axis Support
------------------------------------------
✅ يدعم توليد كود G0/G1 للمحاور X,Y,Z بالإضافة للمحور الرابع A (دوران السبيندل).
✅ يمكن إدخال زاوية A يدويًا من الواجهة.
✅ متوافق مع PythonOCC 7.9.
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit, QFormLayout,
    QDoubleSpinBox, QFileDialog, QMessageBox
)

class GCodeGeneratorPage(QWidget):
    def __init__(self, display=None):
        super().__init__()
        self.display = display
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("🧩 G-Code Generator (A-axis Support)")
        title.setStyleSheet("font-size:16px;font-weight:bold;margin-bottom:6px;")
        layout.addWidget(title)

        form = QFormLayout()

        self.safe_height = QDoubleSpinBox()
        self.safe_height.setRange(0, 200)
        self.safe_height.setValue(10.0)
        form.addRow("Safe Z Height (mm):", self.safe_height)

        self.feed_rate = QDoubleSpinBox()
        self.feed_rate.setRange(1, 10000)
        self.feed_rate.setValue(300)
        form.addRow("Feed Rate (mm/min):", self.feed_rate)

        # 🔹 زاوية دوران السبيندل A-axis
        self.angle_a = QDoubleSpinBox()
        self.angle_a.setRange(-180.0, 180.0)
        self.angle_a.setSingleStep(1.0)
        self.angle_a.setValue(0.0)
        form.addRow("Spindle Angle A (deg):", self.angle_a)

        layout.addLayout(form)

        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        layout.addWidget(self.output_box)

        btn_generate = QPushButton("⚙️ Generate G-Code")
        btn_generate.clicked.connect(self.generate_all)
        layout.addWidget(btn_generate)

        btn_save = QPushButton("💾 Save to File")
        btn_save.clicked.connect(self.save_gcode)
        layout.addWidget(btn_save)

        self.setLayout(layout)

    # ==================================================
    def generate_all(self):
        safe_z = self.safe_height.value()
        feed = self.feed_rate.value()
        a_angle = self.angle_a.value()

        lines = []
        lines.append(f"(G-CODE GENERATED WITH A-AXIS SUPPORT)")
        lines.append(f"G21 ; Units in mm")
        lines.append(f"G90 ; Absolute positioning")
        lines.append(f"G0 Z{safe_z:.3f} A{a_angle:.3f}")

        # مثال لحركة بسيطة — في التطبيق الحقيقي يُستبدل بنقاط فعلية
        points = [(0,0,0), (50,0,-5), (50,50,-5), (0,50,-5), (0,0,-5)]

        for (x, y, z) in points:
            lines.append(f"G1 X{x:.3f} Y{y:.3f} Z{z:.3f} A{a_angle:.3f} F{feed:.0f}")

        lines.append(f"G0 Z{safe_z:.3f} A{a_angle:.3f}")
        lines.append(f"M30 ; End of program")

        code = "\n".join(lines)
        self.output_box.setPlainText(code)
        print("[GCODE] Generated with A-axis")

    # ==================================================
    def save_gcode(self):
        text = self.output_box.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Save", "⚠️ لا يوجد كود لتخزينه.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save G-Code", "gcode_output.nc", "G-Code Files (*.nc *.txt *.gcode)")
        if not path:
            return

        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)

        QMessageBox.information(self, "Save", f"✅ تم حفظ الملف بنجاح:\n{path}")
        print(f"[GCODE] Saved to {path}")