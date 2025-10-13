from PyQt5.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QLabel, QComboBox, QDoubleSpinBox, QPushButton
from PyQt5.QtCore import Qt
from frontend.style import DOCK_STYLE

def create_extrude_dock(parent):
    dock = QDockWidget("Extrude Settings", parent)
    dock.setAllowedAreas(Qt.RightDockWidgetArea)
    dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable)

    widget = QWidget()
    widget.setStyleSheet(DOCK_STYLE)

    layout = QVBoxLayout(widget)
    layout.setContentsMargins(10,10,10,10)
    layout.setSpacing(10)

    layout.addWidget(QLabel("Extrude Axis:"))
    axis_combo = QComboBox()
    axis_combo.addItems(["X", "Y", "Z"])
    layout.addWidget(axis_combo)

    layout.addWidget(QLabel("Distance (mm):"))
    distance_spin = QDoubleSpinBox()
    distance_spin.setRange(1, 9999)
    distance_spin.setValue(100)
    layout.addWidget(distance_spin)

    apply_btn = QPushButton("Apply Extrude")
    layout.addWidget(apply_btn)

    # ربط الزر بالإجراء

    apply_btn.clicked.connect(parent.extrude_clicked)

    dock.setWidget(widget)
    dock.hide()  # مخفي افتراضيًا

    return dock, axis_combo, distance_spin, apply_btn
