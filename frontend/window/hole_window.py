# frontend/window/hole_window.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt

from tools.geometry_ops import add_hole, preview_hole
from tools.color_utils import display_with_fusion_style, display_preview_shape

from tools.dimension_manager import DimensionManager
from tools.dimensions import (
    measure_shape,
    hole_reference_dimensions,
    hole_size_dimensions,
)

class HoleWindow(QWidget):
    def __init__(self, parent=None, display=None, shape_getter=None, shape_setter=None):
        super().__init__(parent)
        self.display = display
        self.get_shape = shape_getter
        self.set_shape = shape_setter

        # مدير القياسات
        self.dim_mgr = DimensionManager(self.display)

        self._build_ui()
        self._connect_live_preview()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.x_input = QLineEdit("0")
        self.y_input = QLineEdit("0")
        self.z_input = QLineEdit("0")
        self.dia_input = QLineEdit("6")
        self.depth_input = QLineEdit("")  # اختياري: فارغ يعني غير محدد

        self.axis_combo = QComboBox()
        self.axis_combo.addItems(["X", "Y", "Z"])

        form.addRow("X:", self.x_input)
        form.addRow("Y:", self.y_input)
        form.addRow("Z:", self.z_input)
        form.addRow("Diameter:", self.dia_input)
        form.addRow("Depth (opt):", self.depth_input)
        form.addRow("Axis:", self.axis_combo)

        layout.addLayout(form)

        preview_btn = QPushButton("👁 Preview Hole")
        preview_btn.clicked.connect(self.preview_clicked)

        apply_btn = QPushButton("🧱 Apply Hole")
        apply_btn.clicked.connect(self.apply_hole)

        btns = QHBoxLayout()
        btns.setAlignment(Qt.AlignCenter)
        btns.addWidget(preview_btn)
        btns.addSpacing(10)
        btns.addWidget(apply_btn)
        layout.addLayout(btns)

    def _get_values(self):
        try:
            x = float(self.x_input.text())
            y = float(self.y_input.text())
            z = float(self.z_input.text())
            dia = float(self.dia_input.text())
            axis = self.axis_combo.currentText()
            dep_txt = self.depth_input.text().strip()
            depth = float(dep_txt) if dep_txt else None
            return x, y, z, dia, axis, depth
        except ValueError:
            print("⚠️ قيم غير صالحة للـ Hole.")
            return None

    def _connect_live_preview(self):
        for w in (self.x_input, self.y_input, self.z_input, self.dia_input, self.depth_input):
            w.textChanged.connect(self._update_preview)
        self.axis_combo.currentIndexChanged.connect(self._update_preview)

    # ========== PREVIEW ==========
    def _update_preview(self):
        vals = self._get_values()
        if not vals:
            return
        x, y, z, dia, axis, depth = vals

        shape = self.get_shape()
        if not shape:
            return

        # مسح قياسات المعاينة فقط (تبقى العامة/النهائية)
        self.dim_mgr.clear_group("preview", update=False)

        hole_shape = preview_hole(x, y, z, dia, axis)

        # لا نستخدم EraseAll — لا نريد حذف القياسات العامة
        display_with_fusion_style(shape, self.display)
        display_preview_shape(hole_shape, self.display)

        # قياسات مرجعية + قطر/عمق (معاينة)
        hole_reference_dimensions(self.display, shape, x, y, z, offset_above=10,
                                  manager=self.dim_mgr, preview=True)
        hole_size_dimensions(self.display, shape, x, y, z, dia, axis,
                             depth=depth, offset_above=10, manager=self.dim_mgr, preview=True)

        self.display.Context.UpdateCurrentViewer()

    def preview_clicked(self):
        self._update_preview()

    # ========== APPLY ==========
    def apply_hole(self):
        vals = self._get_values()
        if not vals:
            return
        x, y, z, dia, axis, depth = vals

        shape = self.get_shape()
        if not shape:
            print("⚠️ لا يوجد شكل للحفر")
            return

        try:
            result = add_hole(shape, x, y, z, dia, axis, depth=depth) if "depth" in add_hole.__code__.co_varnames \
                     else add_hole(shape, x, y, z, dia, axis)

            if result:
                self.set_shape(result)

                # نظّف فقط معاينة القياسات
                self.dim_mgr.clear_group("preview")
                # لا تمسح العامّة: سنعيد احتسابها الآن

                # عرض الشكل
                display_with_fusion_style(result, self.display)

                # قياسات عامة فوق الجسم
                self.dim_mgr.clear_group("general")
                measure_shape(self.display, result, offset_above=10, manager=self.dim_mgr)

                # قياسات الحفرة النهائية
                self.dim_mgr.clear_group("holes")
                hole_reference_dimensions(self.display, result, x, y, z, offset_above=10,
                                          manager=self.dim_mgr, preview=False)
                hole_size_dimensions(self.display, result, x, y, z, dia, axis,
                                     depth=depth, offset_above=10, manager=self.dim_mgr, preview=False)

                self.display.FitAll()
                print(f"🧱 Hole applied: axis={axis}, dia={dia}, depth={depth}, at ({x},{y},{z})")

        except Exception as e:
            print(f"[❌] apply_hole error: {e}")
