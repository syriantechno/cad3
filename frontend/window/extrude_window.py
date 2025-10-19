# frontend/window/extrude_window.py — FINAL BUILD (Y Axis + Safe Extrude + Box Cut Dimensions)

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt

from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

from tools.geometry_ops import extrude_shape, preview_extrude
from tools.color_utils import display_with_fusion_style
from tools.dimensions import (
    measure_shape,
    box_cut_reference_dimensions,
    box_cut_size_dimensions
)


class ExtrudeWindow(QWidget):
    def __init__(self, parent=None, display=None, shape_getter=None, shape_setter=None, op_browser=None):
        super().__init__(parent)
        self.display = display
        self.get_shape = shape_getter
        self.set_shape = shape_setter
        self.op_browser = op_browser

        self._extrude_preview_ais = None
        self._build_ui()
        self._connect_live_preview()

    # ================================
    # 🧱 بناء واجهة المستخدم
    # ================================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        dist_label = QLabel("Distance:")
        self.distance_input = QLineEdit("100")

        hlayout = QHBoxLayout()
        hlayout.addWidget(dist_label)
        hlayout.addWidget(self.distance_input)
        layout.addLayout(hlayout)



    # ================================
    # 🧠 تحديث المعاينة الفورية
    # ================================
    def _connect_live_preview(self):
        self.distance_input.textChanged.connect(self._update_preview)

    def _clear_preview(self):
        if self._extrude_preview_ais is not None:
            try:
                self.display.Context.Erase(self._extrude_preview_ais, False)
            except Exception:
                pass
            self._extrude_preview_ais = None

    def _update_preview(self):
        """معاينة فورية آمنة عند تغيير قيمة المسافة"""
        text = self.distance_input.text().strip()
        if text == "":
            self._clear_preview()
            return

        try:
            height = float(text)
        except ValueError:
            print("[⚠] Extrude preview: invalid number")
            return

        base_shape = self.get_shape()
        if not base_shape or base_shape.IsNull():
            return

        self._clear_preview()

        shape = preview_extrude(base_shape, height)
        if not shape or shape.IsNull():
            print("[⚠] Preview extrude shape is null — skip")
            return

        ais = AIS_Shape(shape)
        ais.SetColor(Quantity_Color(0.0, 1.0, 0.0, Quantity_TOC_RGB))  # أخضر للمعاينة
        try:
            ais.SetTransparency(0.5)
        except Exception:
            pass

        self.display.Context.Display(ais, False)
        self._extrude_preview_ais = ais
        self.display.Context.UpdateCurrentViewer()

    # ================================
    # 🧱 تطبيق الإكسترود
    # ================================
    def apply_extrude(self):
        text = self.distance_input.text().strip()
        if text == "":
            print("[⚠] No distance provided")
            return

        try:
            height = float(text)
        except ValueError:
            print("[⚠] Invalid distance")
            return

        base_shape = self.get_shape()
        if not base_shape or base_shape.IsNull():
            print("[⚠] No base shape to extrude")
            return

        self._clear_preview()

        # 🧱 تنفيذ الإكسترود بمحور Y فقط
        result = extrude_shape(base_shape, height)
        if not result or result.IsNull():
            print("[❌] Extrude failed (null result)")
            return

        # تحديث الشكل في العارض
        self.set_shape(result)
        display_with_fusion_style(result, self.display)

        # 📐 قياسات تلقائية بعد الإكسترود
        try:
            measure_shape(self.display, result)
            box_cut_reference_dimensions(self.display, 0, 0, 0, shape=result, offset_above=10, preview=False)
            box_cut_size_dimensions(self.display, 0, height, 0, 0, 0, 0, shape=result, offset_above=10, preview=False)
        except Exception as e:
            print(f"[⚠] Dimension drawing failed after extrude: {e}")

        try:
            # تحديث العرض فقط بدون FitAll
            self.display.Context.UpdateCurrentViewer()
            self.display.Repaint()
            print("🎯 Extrude done (camera unchanged)")
        except Exception as e:
            print(f"⚠️ Display update failed: {e}")
        print(f"🟦 Extruded along Y by {height} mm")
