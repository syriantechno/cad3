from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QComboBox, QDoubleSpinBox, QPushButton
from PyQt5.QtCore import Qt
from OCC.Core.gp import gp_Pnt
from tools.dimensions import measure_shape
from tools.geometry_ops import extrude_shape
from tools.color_utils import display_with_fusion_style

class ExtrudeWindow(QWidget):
    def __init__(self, parent=None, display=None, shape_getter=None, shape_setter=None, op_browser=None):
        super().__init__(parent)
        self.display = display
        self.get_shape = shape_getter
        self.set_shape = shape_setter
        self.op_browser = op_browser
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.axis_combo = QComboBox()
        self.axis_combo.addItems(["Y"])

        self.distance_spin = QDoubleSpinBox()
        self.distance_spin.setRange(-100000, 100000)
        self.distance_spin.setDecimals(2)
        self.distance_spin.setValue(50.0)

        form.addRow("Axis:", self.axis_combo)
        form.addRow("Distance:", self.distance_spin)
        layout.addLayout(form)

        # زر التنفيذ
        apply_btn = QPushButton("Apply Extrude")
        apply_btn.setObjectName("ApplyBtn")
        apply_btn.clicked.connect(self.apply_extrude)

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)

    def apply_extrude(self):
        shape = self.get_shape()
        if not shape:
            print("⚠️ No shape loaded for extrusion.")
            return

        axis = self.axis_combo.currentText()
        distance = self.distance_spin.value()

        try:
            result_shape = extrude_shape(shape, axis, distance)


            # عرض الشكل
            display_with_fusion_style(result_shape, self.display)

            # تحديث الشكل في الواجهة
            self.set_shape(result_shape)
            # 🟡 قياس تلقائي بعد الإكسترود
            if result_shape is not None:
                print("📏 Auto-dimension after extrude")
                measure_shape(display, result_shape)


            # حفظ العملية في op_browser إن وجد
            if self.op_browser:
                extrude_item = self.op_browser.add_extrude("Extrude", distance)
                extrude_item.shape = result_shape

            self.display.FitAll()
            print(f"[✅] Extrude applied: axis={axis}, distance={distance}")

        except Exception as e:
            print(f"[❌] apply_extrude error: {e}")
