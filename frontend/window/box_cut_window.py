# frontend/window/box_cut_window.py — FINAL BUILD (Manual Box Cut)
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt

from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

from tools.geometry_ops import preview_box_cut, apply_box_cut
from tools.color_utils import display_with_fusion_style
from tools.dimensions import (
    measure_shape,
    box_cut_reference_dimensions,
    box_cut_size_dimensions
)

ENABLE_PREVIEW_DIMS = True

class BoxCutWindow(QWidget):
    def __init__(self, parent=None, display=None, shape_getter=None, shape_setter=None):
        super().__init__(parent)
        self.display = display
        self.get_shape = shape_getter
        self.set_shape = shape_setter

        self._box_preview_ais = None
        self._build_ui()
        self._connect_live_preview()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.x_input = QLineEdit("0")
        self.y_input = QLineEdit("0")
        self.z_input = QLineEdit("0")
        self.dx_input = QLineEdit("20")
        self.dy_input = QLineEdit("20")
        self.dz_input = QLineEdit("20")

        form.addRow("X:", self.x_input)
        form.addRow("Y:", self.y_input)
        form.addRow("Z:", self.z_input)
        form.addRow("DX:", self.dx_input)
        form.addRow("DY:", self.dy_input)
        form.addRow("DZ:", self.dz_input)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        preview_btn = QPushButton("👁 Preview Box Cut")
        apply_btn = QPushButton("✂️ Apply Box Cut")
        preview_btn.clicked.connect(self._update_preview)
        apply_btn.clicked.connect(self.apply_box_cut)
        btn_layout.addWidget(preview_btn)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)

    def _connect_live_preview(self):
        for w in (
            self.x_input, self.y_input, self.z_input,
            self.dx_input, self.dy_input, self.dz_input
        ):
            w.textChanged.connect(self._update_preview)

    def _clear_preview(self):
        if self._box_preview_ais is not None:
            try:
                self.display.Context.Erase(self._box_preview_ais, False)
            except Exception:
                pass
            self._box_preview_ais = None

    def _get_values(self):
        try:
            x = float(self.x_input.text())
            y = float(self.y_input.text())
            z = float(self.z_input.text())
            dx = float(self.dx_input.text())
            dy = float(self.dy_input.text())
            dz = float(self.dz_input.text())
            return x, y, z, dx, dy, dz
        except ValueError:
            return None

    def _update_preview(self):
        vals = self._get_values()
        if not vals:
            self._clear_preview()
            return
        x, y, z, dx, dy, dz = vals

        base_shape = self.get_shape()
        if not base_shape or base_shape.IsNull():
            return

        self._clear_preview()

        # 🟥 معاينة الصندوق الطارح
        box_shape = preview_box_cut(x, y, z, dx, dy, dz)
        if not box_shape or box_shape.IsNull():
            return

        ais = AIS_Shape(box_shape)
        ais.SetColor(Quantity_Color(1, 0, 0, Quantity_TOC_RGB))  # أحمر
        ais.SetTransparency(0.5)
        self.display.Context.Display(ais, False)
        self._box_preview_ais = ais

        if ENABLE_PREVIEW_DIMS:
            box_cut_reference_dimensions(self.display, x, y, z, base_shape, offset_above=10, preview=True)
            box_cut_size_dimensions(self.display, dx, dy, dz, x, y, z, base_shape, offset_above=10, preview=True)

        self.display.Context.UpdateCurrentViewer()

    def apply_box_cut(self):
        vals = self._get_values()
        if not vals:
            return
        x, y, z, dx, dy, dz = vals

        base_shape = self.get_shape()
        if not base_shape or base_shape.IsNull():
            print("⚠️ No base shape to cut")
            return

        self._clear_preview()

        result = apply_box_cut(base_shape, x, y, z, dx, dy, dz)
        if not result or result.IsNull():
            print("[❌] Box cut failed")
            return

        self.set_shape(result)
        display_with_fusion_style(result, self.display)

        # قياسات بعد التطبيق
        measure_shape(self.display, result)
        box_cut_reference_dimensions(self.display, x, y, z, result, offset_above=10, preview=False)
        box_cut_size_dimensions(self.display, dx, dy, dz, x, y, z, result, offset_above=10, preview=False)

        self.display.Context.UpdateCurrentViewer()
        self.display.FitAll()
        print(f"✂️ Box cut applied at ({x}, {y}, {z}) with size ({dx}, {dy}, {dz})")
