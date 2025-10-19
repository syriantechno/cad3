# frontend/window/hole_window.py — FINAL (Z Fixed + Correct Order)

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt

from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

from tools.geometry_ops import add_hole, preview_hole
from tools.color_utils import display_with_fusion_style
from tools.dimensions import (
    measure_shape,
    hole_reference_dimensions,
    hole_size_dimensions
)

ENABLE_PREVIEW_DIMS = True


class HoleWindow(QWidget):
    def __init__(self, parent=None, display=None, shape_getter=None, shape_setter=None):
        super().__init__(parent)
        self.display = display
        self.get_shape = shape_getter
        self.set_shape = shape_setter

        self._hole_preview_ais = None
        self._preview_dim_shapes = []

        self._build_ui()
        self._connect_live_preview()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # 📝 مدخلات الحفر
        self.x_input = QLineEdit("0")
        self.y_input = QLineEdit("0")
        self.z_input = QLineEdit("0")  # Z رجعناها للتحكم في النزول

        self.dia_input = QLineEdit("6")
        self.depth_input = QLineEdit("20")       # عمق الحفر الحقيقي
        self.preview_len_input = QLineEdit("50") # طول الاسطوانة للمعاينة

        self.axis_combo = QComboBox()
        self.axis_combo.addItems(["Z", "Y", "X"])

        form.addRow("X:", self.x_input)
        form.addRow("Y:", self.y_input)
        form.addRow("Z:", self.z_input)
        form.addRow("Diameter:", self.dia_input)
        form.addRow("Depth:", self.depth_input)
        form.addRow("Preview Length:", self.preview_len_input)
        form.addRow("Axis:", self.axis_combo)

        layout.addLayout(form)

        # 🧱 أزرار المعاينة والتطبيق
        btn_layout = QHBoxLayout()
        preview_btn = QPushButton("👁 Preview Hole")

        preview_btn.clicked.connect(self._update_preview)

        btn_layout.addWidget(preview_btn)

        layout.addLayout(btn_layout)

    def _connect_live_preview(self):
        for w in (self.x_input, self.y_input, self.z_input, self.dia_input, self.depth_input, self.preview_len_input):
            w.textChanged.connect(self._update_preview)
        self.axis_combo.currentIndexChanged.connect(self._update_preview)

    def _clear_hole_preview(self):
        if self._hole_preview_ais is not None:
            try:
                self.display.Context.Erase(self._hole_preview_ais, False)
            except Exception:
                pass
            self._hole_preview_ais = None

    def _clear_preview_dimensions(self):
        if self._preview_dim_shapes:
            for dim in self._preview_dim_shapes:
                if dim is not None:
                    try:
                        self.display.Context.Erase(dim, False)
                    except Exception:
                        pass
            self._preview_dim_shapes.clear()

    def _get_values(self):
        """
        إرجاع القيم بترتيب واضح:
        x, y, z, dia, depth, preview_len, axis
        """
        try:
            x = float(self.x_input.text())
            y = float(self.y_input.text())
            z = float(self.z_input.text())
            dia = float(self.dia_input.text())
            depth = float(self.depth_input.text())
            preview_len = float(self.preview_len_input.text())
            axis = self.axis_combo.currentText()
            return x, y, z, dia, depth, preview_len, axis
        except ValueError:
            return None

    def _update_preview(self):
        vals = self._get_values()
        if not vals:
            return
        x, y, z, dia, depth, preview_len, axis = vals

        base_shape = self.get_shape()
        if not base_shape or base_shape.IsNull():
            return

        self._clear_hole_preview()
        self._clear_preview_dimensions()

        print(f"[PREVIEW] x={x}, y={y}, z={z}, axis={axis}, depth={depth}")

        hole_shape = preview_hole(base_shape, x, y, z, dia, axis, preview_len)
        if not hole_shape or hole_shape.IsNull():
            print("[⚠] Hole preview shape is null — skip")
            return

        ais = AIS_Shape(hole_shape)
        ais.SetColor(Quantity_Color(1.0, 0.0, 0.0, Quantity_TOC_RGB))  # أحمر
        try:
            ais.SetTransparency(0.5)
        except Exception:
            pass
        self.display.Context.Display(ais, False)
        self._hole_preview_ais = ais

        if ENABLE_PREVIEW_DIMS:
            try:
                elems = []
                line1, txt1 = hole_reference_dimensions(self.display, x, y, z, base_shape, offset_above=10, preview=True)
                elems += [line1, txt1]
                elems += list(hole_size_dimensions(self.display, x, y, z, dia, axis, depth, base_shape, offset_above=10, preview=True))
                self._preview_dim_shapes.extend([e for e in elems if e is not None])
            except Exception as e:
                print(f"[⚠] Preview dims failed: {e}")

        self.display.Context.UpdateCurrentViewer()

    def apply_hole(self):
        vals = self._get_values()
        if not vals:
            return
        x, y, z, dia, depth, _, axis = vals

        print(f"[APPLY] x={x}, y={y}, z={z}, axis={axis}, depth={depth}")

        base_shape = self.get_shape()
        if not base_shape or base_shape.IsNull():
            print("⚠️ No shape to drill")
            return

        self._clear_hole_preview()
        self._clear_preview_dimensions()

        try:
            result = add_hole(base_shape, x, y, z, dia, axis, depth=depth)
        except Exception as e:
            print(f"[❌] add_hole failed: {e}")
            return

        if not result or result.IsNull():
            print("⚠️ Hole result is null")
            return

        self.set_shape(result)
        display_with_fusion_style(result, self.display)

        measure_shape(self.display, result)
        hole_reference_dimensions(self.display, x, y, z, result, offset_above=10, preview=False)
        hole_size_dimensions(self.display, x, y, z, dia, axis, depth, result, offset_above=10, preview=False)

        self.display.Context.UpdateCurrentViewer()
        self.display.Repaint()
        print(f"🧱 Hole applied: axis={axis}, dia={dia}, depth={depth}, at ({x},{y},{z})")
