from PyQt5.QtWidgets import QWidget, QFormLayout, QLineEdit, QPushButton, QLabel, QVBoxLayout, QFileDialog, QMessageBox
from PyQt5.QtCore import QTimer
from pathlib import Path
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

# إذا تستخدم OCC / qtViewer3d من floating_window، يمكنك استيرادها من هناك أو من مكتبة مشتركة

class ProfileWindow(QWidget):
    def __init__(self, parent=None, load_dxf=None, qtViewer3d=None):
        """
        :param load_dxf: دالة تحميل dxf من المشروع
        :param qtViewer3d: فئة العارض إن متوفرة
        """
        super().__init__(parent)
        self._load_dxf = load_dxf
        self._qtViewer3d = qtViewer3d
        self._small_display = None
        self._selected_shape = {"shape": None, "src": None}
        self._build_ui()

    def _build_ui(self):
        form = QFormLayout(self)

        p_name = QLineEdit()
        p_code = QLineEdit()
        p_dims = QLineEdit()
        p_notes = QLineEdit()
        dxf_path_edit = QLineEdit()
        dxf_path_edit.setReadOnly(True)
        choose_btn = QPushButton("Choose DXF")

        form.addRow("Name:", p_name)
        form.addRow("Code:", p_code)
        form.addRow("Dimensions:", p_dims)
        form.addRow("Notes:", p_notes)
        form.addRow("DXF File:", dxf_path_edit)
        form.addRow("", choose_btn)

        # المعاينة
        if self._qtViewer3d:
            preview_container = QWidget()
            from PyQt5.QtWidgets import QVBoxLayout
            preview_layout = QVBoxLayout(preview_container)
            viewer = self._qtViewer3d(preview_container)
            viewer.setMinimumSize(320, 240)
            preview_layout.addWidget(viewer)
            self._small_display = viewer._display

            # ضبط الألوان فوريًا ومؤقت
            from .floating_window import _setup_viewer_colors
            _setup_viewer_colors(self._small_display)
            QTimer.singleShot(200, lambda: _setup_viewer_colors(self._small_display))
        else:
            preview_container = QLabel("OCC Preview not available.")
            preview_container.setStyleSheet("color:#666;")

        form.addRow("Preview:", preview_container)

        # ربط اختيار DXF
        def on_choose_dxf():
            fname, _ = QFileDialog.getOpenFileName(self, "Select DXF", "", "DXF Files (*.dxf)")
            if not fname:
                return
            dxf_path_edit.setText(fname)
            try:
                shp = self._load_dxf(fname)
            except Exception as ex:
                QMessageBox.warning(self, "DXF", f"Failed to import dxf_tools:\n{ex}")
                return
            if shp is None:
                QMessageBox.warning(self, "DXF", "Failed to parse DXF file.")
                return
            self._selected_shape["shape"] = shp
            self._selected_shape["src"] = fname
            if self._small_display:
                self._small_display.EraseAll()
                self._small_display.DisplayShape(shp, update=True)
                self._small_display.FitAll()
                print(f"[DEBUG] DXF selected: {fname}")

        choose_btn.clicked.connect(on_choose_dxf)

        # حفظ الحقول كمُتغيرات للوصول لاحقًا
        self._p_name = p_name
        self._p_code = p_code
        self._p_dims = p_dims
        self._p_notes = p_notes
        self._dxf_path_edit = dxf_path_edit
        self._selected_shape = self._selected_shape

    def get_profile_data(self):
        """إرجاع بيانات البروفايل المختارة."""
        return {
            "name": self._p_name.text().strip(),
            "code": self._p_code.text().strip(),
            "dimensions": self._p_dims.text().strip(),
            "notes": self._p_notes.text().strip(),
            "dxf": self._dxf_path_edit.text().strip(),
            "shape": self._selected_shape.get("shape"),
        }
