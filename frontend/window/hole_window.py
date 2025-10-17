# frontend/window/hole_window.py — SAFE BUILD
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt

from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.gp import gp_Vec

from tools.geometry_ops import add_hole, preview_hole
from tools.color_utils import display_with_fusion_style
from tools.dimensions import (
    measure_shape,
    hole_reference_dimensions,
    hole_size_dimensions
)

ENABLE_PREVIEW_DIMS = False  # فعّله لاحقًا إن رغبت بقياسات المعاينة


class HoleWindow(QWidget):
    def __init__(self, parent=None, display=None, shape_getter=None, shape_setter=None):
        super().__init__(parent)
        self.display = display
        self.get_shape = shape_getter
        self.set_shape = shape_setter

        self._hole_preview_ais = None
        self._build_ui()
        self._connect_live_preview()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.x_input = QLineEdit("0")
        self.y_input = QLineEdit("0")
        self.z_input = QLineEdit("0")
        self.dia_input = QLineEdit("6")
        self.depth_input = QLineEdit("")  # اختياري

        self.axis_combo = QComboBox()
        self.axis_combo.addItems(["X", "Y", "Z"])

        form.addRow("X:", self.x_input)
        form.addRow("Y:", self.y_input)
        form.addRow("Z:", self.z_input)
        form.addRow("Diameter:", self.dia_input)
        form.addRow("Depth (opt):", self.depth_input)
        form.addRow("Axis:", self.axis_combo)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        preview_btn = QPushButton("👁 Preview Hole")
        apply_btn = QPushButton("🧱 Apply Hole")
        preview_btn.clicked.connect(self._update_preview)
        apply_btn.clicked.connect(self.apply_hole)
        btn_layout.addWidget(preview_btn)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)

    def _connect_live_preview(self):
        for w in (self.x_input, self.y_input, self.z_input, self.dia_input, self.depth_input):
            w.textChanged.connect(self._update_preview)
        self.axis_combo.currentIndexChanged.connect(self._update_preview)

    def _clear_hole_preview(self):
        if self._hole_preview_ais is not None:
            try:
                self.display.Context.Erase(self._hole_preview_ais, False)
            except Exception:
                pass
            self._hole_preview_ais = None

    def _update_preview(self):
        vals = self._get_values()
        if not vals:
            return
        x, y, z, dia, axis, depth = vals

        base_shape = self.get_shape()
        if not base_shape or base_shape.IsNull():
            return

        self._clear_hole_preview()

        hole_shape = preview_hole(x, y, z, dia, axis)
        if not hole_shape or hole_shape.IsNull():
            print("[⚠] Hole preview shape is null — skip")
            return

        ais = AIS_Shape(hole_shape)
        ais.SetColor(Quantity_Color(1.0, 0.0, 0.0, Quantity_TOC_RGB))  # أحمر معاينة
        try: ais.SetTransparency(0.5)
        except Exception: pass
        self.display.Context.Display(ais, False)
        self._hole_preview_ais = ais

        if ENABLE_PREVIEW_DIMS:
            try:
                hole_reference_dimensions(self.display, x, y, z, offset_above=10, preview=True)
                hole_size_dimensions(self.display, x, y, z, dia, axis, depth or 200, offset_above=10, preview=True)
            except Exception:
                pass

        self.display.Context.UpdateCurrentViewer()

    def _get_values(self):
        try:
            x = float(self.x_input.text())
            y = float(self.y_input.text())
            z = float(self.z_input.text())
            dia = float(self.dia_input.text())
            dep_txt = self.depth_input.text().strip()
            depth = float(dep_txt) if dep_txt else None
            axis = self.axis_combo.currentText()
            return x, y, z, dia, axis, depth
        except ValueError:
            return None

    def apply_hole(self):
        vals = self._get_values()
        if not vals:
            return
        x, y, z, dia, axis, depth = vals

        base_shape = self.get_shape()
        if not base_shape or base_shape.IsNull():
            print("⚠️ No shape to drill")
            return

        self._clear_hole_preview()

        try:
            result = add_hole(base_shape, x, y, z, dia, axis, depth=depth) if depth is not None \
                     else add_hole(base_shape, x, y, z, dia, axis)
        except Exception as e:
            print(f"[❌] add_hole failed: {e}")
            return

        if not result or result.IsNull():
            print("⚠️ Hole result is null")
            return

        self.set_shape(result)
        display_with_fusion_style(result, self.display)

        # قياسات نهائية فقط (آمنة)
        measure_shape(self.display, result)
        hole_reference_dimensions(self.display, x, y, z, offset_above=10, preview=False)
        hole_size_dimensions(self.display, x, y, z, dia, axis, depth or 200, offset_above=10, preview=False)

        self.display.Context.UpdateCurrentViewer()
        self.display.FitAll()
        print(f"🧱 Hole applied: axis={axis}, dia={dia}, depth={depth}, at ({x},{y},{z})")
