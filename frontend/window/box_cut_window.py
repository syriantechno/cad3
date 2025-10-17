from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QHBoxLayout, QPushButton, QComboBox
from PyQt5.QtCore import Qt

from tools.geometry_ops import add_box_cut, preview_box_cut
from tools.color_utils import display_with_fusion_style, display_preview_shape

class BoxCutWindow(QWidget):
    def __init__(self, parent=None, display=None, shape_getter=None, shape_setter=None):
        super().__init__(parent)
        self.display = display
        self.get_shape = shape_getter
        self.set_shape = shape_setter
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

        # الأزرار
        preview_btn = QPushButton("👁 Preview Box Cut")
        preview_btn.setObjectName("PreviewBtn")
        preview_btn.clicked.connect(self.preview_clicked)

        apply_btn = QPushButton("✂️ Apply Box Cut")
        apply_btn.setObjectName("ApplyBtn")
        apply_btn.clicked.connect(self.apply_cut)

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        btn_layout.addWidget(preview_btn)
        btn_layout.addSpacing(10)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)

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

    def preview_clicked(self):
        """معاينة يدوية بالزر"""
        self._update_preview()

    def _connect_live_preview(self):
        """ربط كل الحقول بدالة المعاينة التلقائية"""
        for field in [self.x_input, self.y_input, self.z_input,
                      self.width_input, self.height_input, self.depth_input]:
            field.textChanged.connect(self._update_preview)
        self.axis_combo.currentIndexChanged.connect(self._update_preview)

    def _update_preview(self):
        """تحديث المعاينة مباشرة عند تغيير أي قيمة"""
        vals = self._get_values()
        if not vals:
            return
        x, y, z, w, h, d, axis = vals

        shape = self.get_shape()
        if not shape:
            return

        box_shape = preview_box_cut(x, y, z, w, h, d, axis)
        self.display.EraseAll()
        display_with_fusion_style(shape, self.display)
        display_preview_shape(box_shape, self.display)

    def apply_cut(self):
        vals = self._get_values()
        if not vals:
            return
        x, y, z, w, h, d, axis = vals

        shape = self.get_shape()
        if not shape:
            print("⚠️ لا يوجد شكل للقص")
            return

        result = add_box_cut(shape, x, y, z, w, h, d, axis)
        if result:
            self.set_shape(result)
            display_with_fusion_style(result, self.display)
            print(f"✂️ Box cut applied on axis={axis}")
