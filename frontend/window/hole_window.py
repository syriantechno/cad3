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
        self._main_ais = None  # مقبض الشكل الأساسي (اختياري إن أرجعته دالة العرض)
        self._preview_ais = None
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

    # 🧰 أدوات إدارة المعاينة الموحدة
    def _clear_preview(self):
        """يمسح جميع المعاينات السابقة (AIS + قياسات)"""
        # 🧼 مسح كل الـ AIS الخاصة بالمعاينة
        if hasattr(self, "_preview_ais_list"):
            for ais in self._preview_ais_list:
                try:
                    self.display.Context.Erase(ais, False)
                except Exception:
                    pass
            self._preview_ais_list.clear()
        else:
            self._preview_ais_list = []

        # 🧼 مسح مجموعة قياسات المعاينة فقط
        if hasattr(self, "dim_mgr"):
            self.dim_mgr.clear_group("preview", update=False)

        self.display.Context.UpdateCurrentViewer()

    def _add_preview_shape(self, shape):
        """يعرض شكل معاينة جديد ويخزنه في القائمة لإزالته لاحقًا"""
        if not hasattr(self, "_preview_ais_list"):
            self._preview_ais_list = []

        try:
            ais = display_preview_shape(shape, self.display)
            if ais is not None:
                self._preview_ais_list.append(ais)
        except Exception:
            display_preview_shape(shape, self.display)

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

    def preview_clicked(self):
        self._update_preview()

    def _update_preview(self):
        vals = self._get_values()
        if not vals:
            return
        x, y, z, dia, axis, depth = vals

        base_shape = self.get_shape()
        if not base_shape:
            return

        # 🧼 مسح المعاينة السابقة
        self._clear_preview()

        # 🌀 إنشاء المعاينة الجديدة
        hole_shape = preview_hole(x, y, z, dia, axis)
        self._add_preview_shape(hole_shape)

        # 📏 قياسات المعاينة
        hole_reference_dimensions(self.display, base_shape, x, y, z,
                                  offset_above=10, manager=self.dim_mgr, preview=True)
        hole_size_dimensions(self.display, base_shape, x, y, z, dia, axis,
                             depth=depth, offset_above=10, manager=self.dim_mgr, preview=True)

        self.display.Context.UpdateCurrentViewer()

    # ========== APPLY ==========
    def apply_hole(self):
        vals = self._get_values()
        if not vals:
            return
        x, y, z, dia, axis, depth = vals

        base_shape = self.get_shape()
        if not base_shape:
            print("⚠️ لا يوجد شكل للحفر")
            return

        try:
            result = add_hole(base_shape, x, y, z, dia, axis, depth=depth) if "depth" in add_hole.__code__.co_varnames \
                else add_hole(base_shape, x, y, z, dia, axis)
            if not result:
                return

            self.set_shape(result)

            # امسح فقط المعاينة
            if self._preview_ais is not None:
                self.display.Context.Erase(self._preview_ais, False)
                self._preview_ais = None
            self.dim_mgr.clear_group("preview", update=False)

            # أعرض الشكل النهائي (ممكن ترجع AIS)
            ret = display_with_fusion_style(result, self.display)
            if ret is not None:
                self._main_ais = ret

            # قياسات عامة جديدة
            self.dim_mgr.clear_group("general", update=False)
            measure_shape(self.display, result, offset_above=10, manager=self.dim_mgr)

            # قياسات نهائية للحفرة
            self.dim_mgr.clear_group("holes", update=False)
            hole_reference_dimensions(self.display, result, x, y, z,
                                      offset_above=10, manager=self.dim_mgr, preview=False)
            hole_size_dimensions(self.display, result, x, y, z, dia, axis,
                                 depth=depth, offset_above=10, manager=self.dim_mgr, preview=False)

            self.display.Context.UpdateCurrentViewer()
            self.display.FitAll()
            print(f"🧱 Hole applied: axis={axis}, dia={dia}, depth={depth}, at ({x},{y},{z})")
        except Exception as e:
            print(f"[❌] apply_hole error: {e}")
            # داخل apply_hole / apply_cut / apply_extrude
            self._clear_preview()

