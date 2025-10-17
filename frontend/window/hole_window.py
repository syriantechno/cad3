from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QComboBox, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt

from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from tools.geometry_ops import (preview_hole, add_hole)
from tools.color_utils import (display_with_fusion_style, display_preview_shape)
from frontend.style import TOOL_FLOATING_WINDOW_STYLE
from PyQt5.QtWidgets import QHBoxLayout, QPushButton



class HoleWindow(QWidget):
    def __init__(self, parent=None, display=None, shape_getter=None, shape_setter=None):
        """
        display: كائن العرض الرئيسي (qtViewer3d)
        shape_getter: دالة ترجع الشكل الحالي (self.loaded_shape)
        shape_setter: دالة لتحديث الشكل بعد الحفر
        """
        super().__init__(parent)
        self.display = display
        self.get_shape = shape_getter
        self.set_shape = shape_setter
        self.setStyleSheet(TOOL_FLOATING_WINDOW_STYLE)
        self._build_ui()
        self.hole_preview = None

    def _build_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.hole_x = QLineEdit("0")
        self.hole_y = QLineEdit("0")
        self.hole_z = QLineEdit("0")
        self.hole_dia = QLineEdit("6")
        self.axis_hole_combo = QComboBox()
        self.axis_hole_combo.addItems(["X", "Y", "Z"])

        form.addRow("X:", self.hole_x)
        form.addRow("Y:", self.hole_y)
        form.addRow("Z:", self.hole_z)
        form.addRow("Diameter:", self.hole_dia)
        form.addRow("Axis:", self.axis_hole_combo)

        layout.addLayout(form)

        # 🧱 زر التنفيذ
        apply_btn = QPushButton("Apply Hole")
        apply_btn.setObjectName("ApplyBtn")
        apply_btn.clicked.connect(self.hole_clicked)

        # 👁 زر المعاينة
        preview_btn = QPushButton("Preview Hole")
        preview_btn.setObjectName("PreviewBtn")
        preview_btn.clicked.connect(self.preview_clicked)


        # 🔸 صف أفقي للأزرار
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)  # ⬅️ يوسّط الأزرار في المنتصف
        btn_layout.addWidget(apply_btn)
        btn_layout.addSpacing(10)  # مسافة بين الزرين
        btn_layout.addWidget(preview_btn)

        # 🔸 إضافة الـ layout مباشرة تحت حقول الإدخال
        layout.addLayout(btn_layout)

    def hole_clicked(self):
        shape = self.get_shape()
        if not shape:
            print("⚠️ لا يوجد شكل محمّل")
            return
        try:
            x = float(self.hole_x.text())
            y = float(self.hole_y.text())
            z = float(self.hole_z.text())
            dia = float(self.hole_dia.text())
        except ValueError:
            QMessageBox.warning(self, "Hole", "الرجاء إدخال قيم رقمية صحيحة.")
            return

        axis = self.axis_hole_combo.currentText()


        new_shape = add_hole(shape, x, y, z, dia, axis)
        self.set_shape(new_shape)
        display_with_fusion_style(new_shape, self.display)
        self.display_shape_with_axes(new_shape)

    def preview_clicked(self):
        shape = self.get_shape()
        if not shape:
            print("⚠️ لا يوجد شكل محمّل للمعاينة")
            return

        try:
            x = float(self.hole_x.text())
            y = float(self.hole_y.text())
            z = float(self.hole_z.text())
            dia = float(self.hole_dia.text())
        except ValueError:
            print("❌ قيم الحفر غير صالحة (يجب أن تكون أرقام)")
            return

        axis = self.axis_hole_combo.currentText()

        # تنظيف العرض
        self.display.EraseAll()

        display_with_fusion_style(shape, self.display)
        display_preview_shape(self.hole_preview, self.display)

        # إنشاء شكل المعاينة

        self.hole_preview = preview_hole(x, y, z, dia, axis)
        if not self.hole_preview or self.hole_preview.IsNull():
            print("❌ فشل في إنشاء معاينة الحفرة")
            return

        self.display.DisplayShape(self.hole_preview, color="RED", update=True)

    def display_shape_with_axes(self, shape):
        """مساعد لعرض الشكل بعد الحفر مع المحاور (نفس اللي تستخدمه بالـ GUI الرئيسي)."""
        self.display.EraseAll()
        self.display.DisplayShape(shape, update=True)
