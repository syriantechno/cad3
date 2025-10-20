# frontend/window/gcode_generator_page.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFormLayout, QComboBox, QSpinBox, QScrollArea, QMessageBox
)
import os

class GCodeGeneratorPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("G-Code Generator")

        layout = QVBoxLayout(self)

        # إعدادات عامة
        form = QFormLayout()
        self.machine_type = QComboBox()
        self.machine_type.addItems(["CNC Router", "Laser Cutter", "3D Printer"])
        self.post_type = QComboBox()
        self.post_type.addItems(["GRBL", "Mach3", "Fanuc", "Custom"])
        self.feed_rate = QSpinBox()
        self.feed_rate.setRange(50, 10000)
        self.feed_rate.setValue(1200)
        form.addRow("Machine Type:", self.machine_type)
        form.addRow("Post Processor:", self.post_type)
        form.addRow("Feed Rate (mm/min):", self.feed_rate)
        layout.addLayout(form)

        self.operation_manager = None
        self.operation_browser = None
        self.active_profile_id = None


        # عرض العمليات الحالية
        self.operations_view = QTextEdit()
        self.operations_view.setReadOnly(True)
        layout.addWidget(QLabel("Detected Operations:"))
        layout.addWidget(self.operations_view)

        # أزرار التحكم
        btns = QHBoxLayout()
        self.btn_scan = QPushButton("🔍 Scan Operations")
        self.btn_generate = QPushButton("⚙️ Generate All G-Code")
        self.btn_save = QPushButton("💾 Save to File")
        btns.addWidget(self.btn_scan)
        btns.addWidget(self.btn_generate)
        btns.addWidget(self.btn_save)
        layout.addLayout(btns)

        # ناتج الجي كود
        self.output_box = QTextEdit()
        layout.addWidget(QLabel("Generated G-Code:"))
        layout.addWidget(self.output_box)

        # ربط الإشارات
        self.btn_scan.clicked.connect(self.scan_operations)
        self.btn_generate.clicked.connect(self.generate_all)
        self.btn_save.clicked.connect(self.save_to_file)

        self.detected_ops = []

    def scan_operations(self):
        """🔍 البحث عن كل العمليات التصنيعية للبروفايل النشط (تجاهل Profile و Extrude)"""
        try:
            # 🧭 تحديد مصدر العمليات
            ops_source = None
            if hasattr(self, "operation_browser") and self.operation_browser is not None:
                ops_source = self.operation_browser
            elif hasattr(self.parent, "op_browser"):
                ops_source = self.parent.op_browser
            else:
                self.operations_view.setPlainText("⚠️ لم يتم العثور على Operation Browser متصل.")
                print("[GCODE] No operation browser available.")
                return

            # 🧱 جلب العمليات
            if hasattr(ops_source, "list_operations"):
                operations = ops_source.list_operations()
            elif hasattr(ops_source, "get_all_operations"):
                operations = ops_source.get_all_operations()
            else:
                operations = []

            if not operations:
                self.operations_view.setPlainText("ℹ️ لا توجد عمليات حالياً.")
                print("[GCODE] No operations found.")
                return

            # 🧹 تجاهل العمليات غير التصنيعية
            manufacturing_ops = []
            for op in operations:
                op_type = op.get("type", "").lower()
                if op_type in ("hole", "cut", "slot", "drill"):
                    manufacturing_ops.append(op)

            if not manufacturing_ops:
                self.operations_view.setPlainText("ℹ️ لا توجد عمليات تصنيعية (Hole / Cut / Slot).")
                print("[GCODE] No manufacturing operations found.")
                return

            # 🧩 عرض العمليات المقبولة فقط
            self.detected_ops = manufacturing_ops
            lines = []
            for op in manufacturing_ops:
                typ = op.get("type", "Unknown")
                profile = op.get("profile", "-")
                x, y, z = op.get("x", 0), op.get("y", 0), op.get("z", 0)
                depth = op.get("depth", 0)
                dia = op.get("dia", "-")
                axis = op.get("axis", "?")
                lines.append(
                    f"- {typ} | Profile {profile} | Axis={axis} | Pos=({x},{y},{z}) | Depth={depth} | Dia={dia}")

            self.operations_view.setPlainText("\n".join(lines))
            print(f"[GCODE] Scanned {len(manufacturing_ops)} manufacturing operations successfully.")

        except Exception as e:
            print(f"[❌ GCODE] Scan error: {e}")
            self.operations_view.setPlainText(f"❌ خطأ أثناء قراءة العمليات:\n{e}")

    def generate_all(self):
        """⚙️ توليد G-Code ذكي لكل عمليات الحفر (Hole) الحالية"""
        try:
            if not hasattr(self, "detected_ops") or not self.detected_ops:
                self.output_box.setPlainText("⚠️ لا توجد عمليات لتوليد G-Code.\nاضغط Scan أولاً.")
                print("[GCODE] No operations to generate.")
                return

            # ⚙️ إعدادات عامة
            feed_rate = self.feed_rate.value() if hasattr(self, "feed_rate") else 1000
            machine = self.machine_type.currentText() if hasattr(self, "machine_type") else "CNC Router"
            post = self.post_type.currentText() if hasattr(self, "post_type") else "GRBL"

            # 🔧 تجهيز الملف النصي
            lines = [
                f"(Generated by AlumCam G-Code Generator)",
                f"(Machine: {machine})",
                f"(Post: {post})",
                "G21  (Units: millimeters)",
                "G90  (Absolute positioning)",
                ""
            ]

            profile_id = None

            for op in self.detected_ops:
                if op.get("type", "").lower() != "hole":
                    continue

                profile_id = op.get("profile", "N/A")
                x, y, z = float(op.get("x", 0)), float(op.get("y", 0)), float(op.get("z", 0))
                depth = float(op.get("depth", 0))
                dia = float(op.get("dia", 0))
                axis = op.get("axis", "Z").upper()

                lines.append(f"(--- Hole ---)")
                lines.append(f"(Profile ID: {profile_id})")
                lines.append(f"(Dia={dia:.2f}, Depth={depth:.2f}, Axis={axis})")

                # 🧱 إعداد إحداثيات الحفر
                if axis == "Z":
                    lines.append(f"G0 X{x:.3f} Y{y:.3f}")
                    lines.append(f"G81 Z-{depth:.3f} R2.0 F{feed_rate}")
                elif axis == "Y":
                    lines.append(f"G0 X{x:.3f} Z{z:.3f}")
                    lines.append(f"G81 Y-{depth:.3f} R2.0 F{feed_rate}")
                else:  # X أو محاور مخصصة
                    lines.append(f"G0 Y{y:.3f} Z{z:.3f}")
                    lines.append(f"G81 X-{depth:.3f} R2.0 F{feed_rate}")

                lines.append("G80 (Cancel drilling cycle)")
                lines.append("")

            lines.append("M30 (End of program)")

            # 🧾 إخراج الجي كود للنص داخل الواجهة
            gcode_text = "\n".join(lines)
            self.output_box.setPlainText(gcode_text)
            print("[GCODE] G-Code generated successfully.")

            # 💾 حفظ الملف تلقائيًا
            from pathlib import Path
            import os

            out_dir = Path("output/gcode")
            out_dir.mkdir(parents=True, exist_ok=True)
            filename = f"profile_{profile_id or 'unknown'}.nc"
            file_path = out_dir / filename

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(gcode_text)

            print(f"[GCODE] Saved: {file_path}")
            self.output_box.append(f"\n💾 Saved file:\n{file_path}")

        except Exception as e:
            print(f"[❌ GCODE] Generation error: {e}")
            self.output_box.setPlainText(f"❌ خطأ أثناء توليد G-Code:\n{e}")

    def save_to_file(self):
        """حفظ الجي كود إلى ملف"""
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Save G-Code", "", "G-Code Files (*.nc *.gcode)")
        if not path:
            return
        with open(path, "w") as f:
            f.write(self.output_box.toPlainText())
        print(f"[GCODE] Saved file: {path}")
