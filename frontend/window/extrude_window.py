from PyQt5.QtWidgets import QWidget, QFormLayout, QComboBox, QDoubleSpinBox

class ExtrudeWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        axis_combo = QComboBox()
        axis_combo.addItems(["X", "Y", "Z"])
        distance_spin = QDoubleSpinBox()
        distance_spin.setRange(1, 9999)
        distance_spin.setValue(100)

        layout.addRow("Axis:", axis_combo)
        layout.addRow("Distance (mm):", distance_spin)

        # حفظ المراجع داخل الـ widget
        self._axis_combo = axis_combo
        self._distance_spin = distance_spin

    def get_values(self):
        """إرجاع القيم المختارة: المحور والمسافة."""
        return self._axis_combo.currentText(), self._distance_spin.value()
