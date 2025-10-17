# frontend/window/extrude_window.py — SAFE BUILD
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QComboBox, QLineEdit
from PyQt5.QtCore import Qt

from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

from tools.geometry_ops import extrude_shape, preview_extrude
from tools.color_utils import display_with_fusion_style
from tools.dimensions import measure_shape

ENABLE_PREVIEW_DIMS = False  # اجعله True لاحقًا إن رغبت بقياسات المعاينة


class ExtrudeWindow(QWidget):
    def __init__(self, parent=None, display=None, shape_getter=None, shape_setter=None, op_browser=None):
        super().__init__(parent)
        self.display = display
        self.get_shape = shape_getter
        self.set_shape = shape_setter
        self.op_browser = op_browser

        self._preview_ais = None
        self._build_ui()
        self._connect_live_preview()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        axis_label = QLabel("Axis:")
        self.axis_combo = QComboBox()
        self.axis_combo.addItems(["X", "Y", "Z"])

        dist_label = QLabel("Distance:")
        self.distance_input = QLineEdit("100")

        apply_btn = QPushButton("🧱 Apply Extrude")
        apply_btn.clicked.connect(self.apply_extrude)

        hlayout = QHBoxLayout()
        hlayout.addWidget(axis_label)
        hlayout.addWidget(self.axis_combo)
        hlayout.addWidget(dist_label)
        hlayout.addWidget(self.distance_input)
        hlayout.addStretch()

        layout.addLayout(hlayout)
        layout.addWidget(apply_btn)

    def _connect_live_preview(self):
        self.distance_input.textChanged.connect(self._update_preview)
        self.axis_combo.currentIndexChanged.connect(self._update_preview)

    def _clear_preview(self):
        if self._preview_ais is not None:
            try:
                self.display.Context.Erase(self._preview_ais, False)
            except Exception:
                pass
            self._preview_ais = None

    def _update_preview(self):
        # قراءة القيم
        try:
            dist = float(self.distance_input.text())
        except ValueError:
            return
        axis = self.axis_combo.currentText()

        base_shape = self.get_shape()
        if not base_shape or base_shape.IsNull():
            return

        self._clear_preview()

        # توليد شكل المعاينة
        preview_shape = preview_extrude(base_shape, axis, dist)
        if not preview_shape or preview_shape.IsNull():
            print("[⚠] Preview extrude shape is null — skip")
            return

        # AIS واحد للمعاينة
        ais = AIS_Shape(preview_shape)
        ais.SetColor(Quantity_Color(0.0, 0.45, 1.0, Quantity_TOC_RGB))
        try: ais.SetTransparency(0.5)
        except Exception: pass
        self.display.Context.Display(ais, False)
        self._preview_ais = ais

        # (اختياري آمن) لا نرسم قياسات معاينة افتراضيًا
        if ENABLE_PREVIEW_DIMS:
            try:
                measure_shape(self.display, preview_shape)
            except Exception:
                pass

        self.display.Context.UpdateCurrentViewer()

    def apply_extrude(self):
        try:
            dist = float(self.distance_input.text())
        except ValueError:
            print("⚠️ Distance value is invalid")
            return

        axis = self.axis_combo.currentText()
        base_shape = self.get_shape()
        if not base_shape or base_shape.IsNull():
            print("⚠️ No shape to extrude")
            return

        self._clear_preview()

        result = extrude_shape(base_shape, axis, dist)
        if not result or result.IsNull():
            print("⚠️ Extrude failed (null result)")
            return

        self.set_shape(result)

        display_with_fusion_style(result, self.display)
        measure_shape(self.display, result)

        self.display.Context.UpdateCurrentViewer()
        self.display.FitAll()
        print(f"[✅] Extrude applied: axis={axis}, distance={dist}")
