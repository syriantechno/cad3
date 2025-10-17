# frontend/window/box_cut_window.py — SAFE BUILD
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QHBoxLayout, QPushButton, QComboBox
from PyQt5.QtCore import Qt

from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

from tools.geometry_ops import add_box_cut, preview_box_cut
from tools.color_utils import display_with_fusion_style
from tools.dimensions import (
    measure_shape,
    box_cut_reference_dimensions,
    box_cut_size_dimensions
)

ENABLE_PREVIEW_DIMS = False  # فعّله لاحقًا إن رغبت بقياسات المعاينة


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
        apply_btn   = QPushButton("✂️ Apply Box Cut")
        preview_btn.clicked.connect(self._update_preview)
        apply_btn.clicked.connect(self.apply_cut)

        btns = QHBoxLayout()
        btns.addWidget(preview_btn)
        btns.addWidget(apply_btn)
        layout.addLayout(btns)

    def _connect_live_preview(self):
        for w in [self.x_input, self.y_input, self.z_input, self.width_input, self.height_input, self.depth_input]:
            w.textChanged.connect(self._update_preview)
        self.axis_combo.currentIndexChanged.connect(self._update_preview)

    def _clear_box_preview(self):
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
            w = float(self.width_input.text())
            h = float(self.height_input.text())
            d = float(self.depth_input.text())
            axis = self.axis_combo.currentText()
            return x, y, z, w, h, d, axis
        except ValueError:
            return None

    def _update_preview(self):
        vals = self._get_values()
        if not vals:
            return
        x, y, z, w, h, d, axis = vals

        base_shape = self.get_shape()
        if not base_shape or base_shape.IsNull():
            return

        self._clear_box_preview()

        box_shape = preview_box_cut(x, y, z, w, h, d, axis)
        if not box_shape or box_shape.IsNull():
            print("[⚠] Box cut preview shape is null — skip")
            return

        ais = AIS_Shape(box_shape)
        ais.SetColor(Quantity_Color(0.0, 0.45, 1.0, Quantity_TOC_RGB))
        try: ais.SetTransparency(0.5)
        except Exception: pass
        self.display.Context.Display(ais, False)
        self._box_preview_ais = ais

        if ENABLE_PREVIEW_DIMS:
            try:
                box_cut_reference_dimensions(self.display, x, y, z, offset_above=10, preview=True)
                box_cut_size_dimensions(self.display, w, h, d, x, y, z, offset_above=10, preview=True)
            except Exception:
                pass

        self.display.Context.UpdateCurrentViewer()

    def apply_cut(self):
        vals = self._get_values()
        if not vals:
            return
        x, y, z, w, h, d, axis = vals

        shape = self.get_shape()
        if not shape or shape.IsNull():
            print("⚠️ لا يوجد شكل للقص")
            return

        self._clear_box_preview()

        result = add_box_cut(shape, x, y, z, w, h, d, axis)
        if not result or result.IsNull():
            print("⚠️ Box cut result is null")
            return

        self.set_shape(result)
        display_with_fusion_style(result, self.display)

        # قياسات نهائية فقط (آمنة)
        measure_shape(self.display, result)
        box_cut_reference_dimensions(self.display, x, y, z, offset_above=10, preview=False)
        box_cut_size_dimensions(self.display, w, h, d, x, y, z, offset_above=10, preview=False)

        self.display.Context.UpdateCurrentViewer()
        self.display.FitAll()
        print(f"✂️ Box cut applied on axis={axis} at ({x},{y},{z}) size=({w},{h},{d})")
