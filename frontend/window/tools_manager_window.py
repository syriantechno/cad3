from PyQt5.QtWidgets import QWidget, QFormLayout, QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QPushButton, QHBoxLayout, QLabel
from pathlib import Path
from PyQt5.QtGui import QPixmap
from .utils_window import safe_exists
from PyQt5.QtCore import Qt


class ToolsManagerWindow(QWidget):
    def __init__(self, tool_types: dict, open_add_type_dialog_cb):
        super().__init__()
        self._tool_types = tool_types
        self._open_add_type_cb = open_add_type_dialog_cb
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        name_input = QLineEdit()
        dia_input = QDoubleSpinBox(); dia_input.setSuffix(" mm"); dia_input.setMaximum(100)
        length_input = QDoubleSpinBox(); length_input.setSuffix(" mm"); length_input.setMaximum(200)
        type_combo = QComboBox(); type_combo.setEditable(True); type_combo.addItems(self._tool_types.keys())
        add_type_btn = QPushButton("➕"); add_type_btn.setFixedWidth(30)
        type_row = QHBoxLayout(); type_row.addWidget(type_combo); type_row.addWidget(add_type_btn)

        layout.addRow("Tool Name:", name_input)
        layout.addRow("Diameter:", dia_input)
        layout.addRow("Length:", length_input)
        layout.addRow("Type:", type_row)

        rpm_input = QSpinBox(); rpm_input.setMaximum(40000)
        steps_input = QSpinBox(); steps_input.setMaximum(100)
        layout.addRow("Default RPM:", rpm_input)
        layout.addRow("Default Steps:", steps_input)

        image_label = QLabel("No image")
        image_label.setFixedSize(120, 120)
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setStyleSheet("border: 1px solid gray;")
        layout.addRow("Preview:", image_label)

        def update_tool_image(tool_type_name):
            img_path = self._tool_types.get(tool_type_name)
            if img_path and Path(img_path).exists():
                pix = QPixmap(str(img_path)).scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                image_label.setPixmap(pix)
            else:
                image_label.setText("No image")
                image_label.setPixmap(QPixmap())

        type_combo.currentTextChanged.connect(update_tool_image)
        add_type_btn.clicked.connect(lambda: self._open_add_type_cb(type_combo, update_tool_image))

        # حفظ المراجع إن احتجت
        self._name_input = name_input
        self._dia_input = dia_input
        self._length_input = length_input
        self._type_combo = type_combo
        self._rpm_input = rpm_input
        self._steps_input = steps_input
        self._update_tool_image = update_tool_image
