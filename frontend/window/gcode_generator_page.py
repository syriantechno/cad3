# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QPushButton, QComboBox, QDoubleSpinBox, QGroupBox, QFormLayout, QMessageBox
)
from PyQt5.QtCore import Qt
from pathlib import Path
import os, datetime

class GCodeGeneratorPage(QWidget):
    """
    ✅ صفحة توليد الجي كود المحدثة:
    - تتلقى العمليات من OperationBrowser مباشرة.
    - تدعم التوليد اليدوي (Generate) والتوليد التلقائي من الشجرة.
    - تنسق الجي كود بخط واضح ونتائج محفوظة تلقائياً.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.detected_ops = []  # لتخزين العمليات المستلمة من الشجرة

    # ===================== 🧱 الواجهة =====================
    def _build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("⚙️ G-Code Generator")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: 600; font-size: 13pt; padding: 4px;")
        layout.addWidget(title)

        # إعدادات عامة
        settings_box = QGroupBox("General Settings")
        settings_layout = QFormLayout()

        self.machine_type = QComboBox()
        self.machine_type.addItems(["CNC Router", "CNC Mill", "Laser Cutter"])

        self.post_type = QComboBox()
        self.post_type.addItems(["GRBL", "Fanuc", "Mach3"])

        self.feed_rate = QDoubleSpinBox()
        self.feed_rate.setRange(10, 10000)
        self.feed_rate.setValue(1000)
        self.feed_rate.setSuffix(" mm/min")

        settings_layout.addRow("Machine:", self.machine_type)
        settings_layout.addRow("Post:", self.post_type)
        settings_layout.addRow("Feed rate:", self.feed_rate)
        settings_box.setLayout(settings_layout)
        layout.addWidget(settings_box)

        # منطقة النص
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        self.output_box.setStyleSheet("background-color: #f8f8f8; font-family: Consolas; font-size: 11pt;")
        layout.addWidget(self.output_box)

        # الأزرار
        btn_row = QHBoxLayout()
        self.btn_scan = QPushButton("🔍 Scan Operations")
        self.btn_generate = QPushButton("⚙️ Generate All")
        self.btn_save = QPushButton("💾 Save G-Code")

        for b in (self.btn_scan, self.btn_generate, self.btn_save):
            b.setFixedWidth(160)

        btn_row.addWidget(self.btn_scan)
        btn_row.addWidget(self.btn_generate)
        btn_row.addWidget(self.btn_save)
        layout.addLayout(btn_row)

        # روابط الأزرار
        self.btn_scan.clicked.connect(self._scan_operations)
        self.btn_generate.clicked.connect(self.generate_all)
        self.btn_save.clicked.connect(self._save_file)

        self.setLayout(layout)

    # ======================================================
    # 🔍 قراءة العمليات من OperationBrowser
    # ======================================================
    def _scan_operations(self):
        """تحاول قراءة العمليات من المتصفح المرتبط في النافذة الرئيسية."""
        try:
            from PyQt5.QtWidgets import QApplication
            for w in QApplication.topLevelWidgets():
                if hasattr(w, "op_browser"):
                    ops = w.op_browser.get_all_ops()
                    if not ops:
                        self.output_box.setPlainText("⚠️ لا توجد عمليات في المتصفح.")
                        print("[GCODE] No operations found.")
                        return
                    self.detected_ops = ops
                    self.output_box.setPlainText(
                        f"✅ تم العثور على {len(ops)} عملية.\nاضغط 'Generate All' لتوليد الجي كود."
                    )
                    print(f"[GCODE] Detected {len(ops)} operations.")
                    return
            self.output_box.setPlainText("⚠️ لا يوجد Operation Browser متصل.")
            print("[GCODE] No OperationBrowser found.")
        except Exception as e:
            self.output_box.setPlainText(f"❌ خطأ أثناء البحث عن العمليات:\n{e}")
            print(f"[❌ GCODE] Scan error: {e}")

    # ======================================================
    # ⚙️ التوليد من الشجرة مباشرة
    # ======================================================
    def generate_from_ops(self, ops_list):
        """
        تُستدعى من OperationBrowser (أو من الزر Generate في الشجرة)
        لتوليد الكود مباشرة من قائمة عمليات.
        """
        try:
            if not ops_list:
                self.output_box.setPlainText("⚠️ لا توجد عمليات لتوليد G-Code.")
                return
            self.detected_ops = ops_list
            self.generate_all()
        except Exception as e:
            print(f"[❌ GCODE] generate_from_ops failed: {e}")

    # ======================================================
    # 🧠 توليد الجي كود العام
    # ======================================================
    def generate_all(self):
        """توليد G-Code ذكي لكل عمليات الحفر."""
        try:
            if not self.detected_ops:
                self.output_box.setPlainText("⚠️ لا توجد عمليات.\nاضغط Scan أولاً.")
                return

            feed_rate = self.feed_rate.value()
            machine = self.machine_type.currentText()
            post = self.post_type.currentText()

            lines = [
                f"(Generated by AlumCam G-Code Generator)",
                f"(Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})",
                f"(Machine: {machine})",
                f"(Post: {post})",
                "G21  (Units: millimeters)",
                "G90  (Absolute positioning)",
                ""
            ]

            profile_id = None
            total_holes = 0

            for op in self.detected_ops:
                t = op.get("type", "").lower()
                if t != "hole":
                    continue
                total_holes += 1
                profile_id = op.get("profile", "N/A")
                x, y, z = float(op.get("x", 0)), float(op.get("y", 0)), float(op.get("z", 0))
                depth = float(op.get("depth", 0))
                dia = float(op.get("dia", 0))
                axis = op.get("axis", "Z").upper()
                tool = op.get("tool", "Unknown")

                lines.append(f"(--- Hole #{total_holes} ---)")
                lines.append(f"(Profile: {profile_id} | Tool: {tool})")
                lines.append(f"(Dia={dia:.2f}, Depth={depth:.2f}, Axis={axis})")

                if axis == "Z":
                    lines.append(f"G0 X{x:.3f} Y{y:.3f}")
                    lines.append(f"G81 Z-{depth:.3f} R2.0 F{feed_rate:.0f}")
                elif axis == "Y":
                    lines.append(f"G0 X{x:.3f} Z{z:.3f}")
                    lines.append(f"G81 Y-{depth:.3f} R2.0 F{feed_rate:.0f}")
                else:
                    lines.append(f"G0 Y{y:.3f} Z{z:.3f}")
                    lines.append(f"G81 X-{depth:.3f} R2.0 F{feed_rate:.0f}")

                lines.append("G80")
                lines.append("")

            lines.append("M30 (End of program)")

            gcode_text = "\n".join(lines)
            self.output_box.setPlainText(gcode_text)
            print(f"[GCODE] ✅ Generated successfully ({total_holes} holes).")

            # حفظ الملف تلقائيًا
            out_dir = Path("output/gcode")
            out_dir.mkdir(parents=True, exist_ok=True)
            file_path = out_dir / f"profile_{profile_id or 'unknown'}.nc"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(gcode_text)

            self.output_box.append(f"\n💾 Saved file:\n{file_path}")
            print(f"[GCODE] Saved: {file_path}")

        except Exception as e:
            print(f"[❌ GCODE] Generation error: {e}")
            self.output_box.setPlainText(f"❌ خطأ أثناء التوليد:\n{e}")

    # ======================================================
    # 💾 الحفظ اليدوي
    # ======================================================
    def _save_file(self):
        """يحفظ محتوى الـ G-Code في مجلد gcode/"""
        try:
            text = self.output_box.toPlainText()
            if not text.strip():
                QMessageBox.warning(self, "G-Code", "⚠️ لا يوجد محتوى للحفظ.")
                return
            out_dir = Path("output/gcode")
            out_dir.mkdir(parents=True, exist_ok=True)
            file_path = out_dir / f"manual_{datetime.datetime.now().strftime('%H%M%S')}.nc"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)
            QMessageBox.information(self, "Saved", f"✅ تم الحفظ في:\n{file_path}")
            print(f"[GCODE] Saved manually: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))
            print(f"[❌ GCODE] Save error: {e}")
