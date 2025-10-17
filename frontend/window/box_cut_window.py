# frontend/window/box_cut_window.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QHBoxLayout, QPushButton, QComboBox
from PyQt5.QtCore import Qt

from tools.geometry_ops import add_box_cut, preview_box_cut
from tools.color_utils import display_with_fusion_style, display_preview_shape

from tools.dimension_manager import DimensionManager
from tools.dimensions import (
    measure_shape,
    hole_reference_dimensions,   # نستخدمه لرسم قياسات X/Y المرجعية
    hole_size_dimensions,        # نستخدمه لرسم W/H/D للصندوق أيضاً
    get_zmax
)
from tools.dimension_draw import draw_dimension, DIM_COLOR_PREVIEW, DIM_COLOR_HOLE
from OCC.Core.gp import gp_Pnt


class BoxCutWindow(QWidget):
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
        self.width_input = QLineEdit("20")
        self.height_input = QLineEdit("20")
        self.depth_input = QLineEdit("20")

        self.axis_combo = QComboBox()
        self.axis_combo.addItems(["X", "Y", "Z"])

        form.addRow("X:", self.x_input)
        form.addRow("Y:", self.y_input)
        form.addRow("Z:", self.z_input)
        form.addRow("Width:", self.width_input)
        form.addRow("Height:", self.height_input)
        form.addRow("Depth:", self.depth_input)
        form.addRow("Axis:", self.axis_combo)
        layout.addLayout(form)

        preview_btn = QPushButton("👁 Preview Box Cut")
        preview_btn.clicked.connect(self.preview_clicked)

        apply_btn = QPushButton("✂️ Apply Box Cut")
        apply_btn.clicked.connect(self.apply_cut)

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        btn_layout.addWidget(preview_btn)
        btn_layout.addSpacing(10)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)

    def _get_values(self):
        try:
            x = float(self.x_input.text())
            y = float(self.y_input.text())
            z = float(self.z_input.text())
            w = float(self.width_input.text())
            h = float(self.height_input.text())
            d = float(self.depth_input.text())
            axis = self.axis_combo.currentText()
            return x, y, z, w, h, d, axis
        except ValueError:
            print("⚠️ قيم غير صالحة للـ Box Cut")
            return None

    def _connect_live_preview(self):
        for field in [
            self.x_input, self.y_input, self.z_input,
            self.width_input, self.height_input, self.depth_input
        ]:
            field.textChanged.connect(self._update_preview)
        self.axis_combo.currentIndexChanged.connect(self._update_preview)

    # ===================== PREVIEW =====================
    def _update_preview(self):
        vals = self._get_values()
        if not vals:
            return
        x, y, z, w, h, d, axis = vals

        shape = self.get_shape()
        if not shape:
            return

        # نظّف فقط القياسات السابقة للمعاينة
        self.dim_mgr.clear_group("preview")

        # معاينة الصندوق
        box_shape = preview_box_cut(x, y, z, w, h, d, axis)

        # لا تمسح كل شيء
        display_with_fusion_style(shape, self.display)
        display_preview_shape(box_shape, self.display)

        # قياسات مرجعية X/Y (من الأصل إلى موقع الصندوق)
        hole_reference_dimensions(
            self.display, shape, x, y, z,
            offset_above=10,
            manager=self.dim_mgr,
            preview=True
        )

        # قياسات أبعاد الصندوق (W/H/D)
        self._draw_box_dimensions(x, y, z, w, h, d, axis, preview=True)

        self.display.Context.UpdateCurrentViewer()

    def preview_clicked(self):
        self._update_preview()

    # ===================== APPLY =====================
    def apply_cut(self):
        vals = self._get_values()
        if not vals:
            return
        x, y, z, w, h, d, axis = vals

        shape = self.get_shape()
        if not shape:
            print("⚠️ لا يوجد شكل للقص")
            return

        try:
            result = add_box_cut(shape, x, y, z, w, h, d, axis)
            if result:
                self.set_shape(result)

                # نظّف معاينة القياسات فقط
                self.dim_mgr.clear_group("preview")

                # عرض الشكل
                display_with_fusion_style(result, self.display)

                # قياسات عامة جديدة بعد القص
                self.dim_mgr.clear_group("general")
                measure_shape(self.display, result, offset_above=10, manager=self.dim_mgr)

                # قياسات مرجعية وأبعاد الصندوق النهائية
                self.dim_mgr.clear_group("holes")
                hole_reference_dimensions(
                    self.display, result, x, y, z,
                    offset_above=10,
                    manager=self.dim_mgr,
                    preview=False
                )
                self._draw_box_dimensions(x, y, z, w, h, d, axis, preview=False)

                self.display.FitAll()
                print(f"✂️ Box cut applied: ({x},{y},{z}) size=({w},{h},{d}) axis={axis}")

        except Exception as e:
            print(f"[❌] apply_box_cut error: {e}")

    # ===================== قياسات أبعاد الصندوق =====================
    def _draw_box_dimensions(self, x, y, z, w, h, d, axis, preview: bool):
        """
        رسم أبعاد Width / Height / Depth للصندوق على أعلى مستوى من الشكل.
        """
        color = DIM_COLOR_PREVIEW if preview else DIM_COLOR_HOLE
        shape = self.get_shape()
        base_z = get_zmax(shape) + 10 if shape else z + 10

        # نقاط على مستوى علوي
        corner = gp_Pnt(x, y, base_z)
        x_end = gp_Pnt(x + w, y, base_z)
        y_end = gp_Pnt(x, y + h, base_z)
        z_start = gp_Pnt(x, y, base_z)
        z_end = gp_Pnt(x, y, base_z - d)  # العمق للأسفل

        objs = []
        objs += list(draw_dimension(self.display, corner, x_end, f"W: {w:.1f} mm", color=color))
        objs += list(draw_dimension(self.display, corner, y_end, f"H: {h:.1f} mm", color=color))
        objs += list(draw_dimension(self.display, z_start, z_end, f"D: {d:.1f} mm", color=color))

        for o in objs:
            self.dim_mgr.add(o, "preview" if preview else "holes")
