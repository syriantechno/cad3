from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QGridLayout, QPushButton, QFrame, QMessageBox
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from pathlib import Path
from .utils_window import safe_exists

class ProfilesManagerWindow(QWidget):
    def __init__(self, dialog_parent, load_dxf=None, parent_main=None):
        """
        :param dialog_parent: والد الـ dialog (المتحكم في النافذة العائمة)
        :param load_dxf: دالة تحميل DXF
        :param parent_main: النافذة الرئيسية التي تحتوي display و op_browser
        """
        super().__init__(dialog_parent)
        self._dialog_parent = dialog_parent
        self._load_dxf = load_dxf
        self._main_parent = parent_main
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        container = QWidget()
        scroll.setWidget(container)
        grid = QGridLayout(container)

        from tools.database import ProfileDB
        self._db = ProfileDB()

        def _make_loader(dxf_path_local, profile_name):
            def _loader():
                try:
                    shape = self._load_dxf(Path(dxf_path_local))
                    mwin = self._main_parent
                    mwin.display.EraseAll()
                    mwin.display.DisplayShape(shape, update=True)
                    mwin.loaded_shape = shape
                    mwin.display.FitAll()
                    if hasattr(mwin, "op_browser"):
                        mwin.op_browser.add_profile(profile_name)
                except Exception as e:
                    QMessageBox.critical(self, "Load Error", str(e))
            return _loader

        def refresh_profiles_list():
            # مسح الموجودين
            while grid.count():
                item = grid.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            profiles = self._db.list_profiles()
            if not profiles:
                grid.addWidget(QLabel("لا توجد بروفايلات."), 0, 0)
                return

            for row_idx, prof in enumerate(profiles):
                pid, name, code, dims, notes, dxf_path, brep, img, created = prof
                img_label = QLabel()
                img_label.setFixedSize(64, 64)
                img_label.setFrameShape(QFrame.Box)
                if _safe_exists(img):
                    pix = QPixmap(img).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    img_label.setPixmap(pix)
                else:
                    img_label.setText("No\nImage")
                    img_label.setAlignment(Qt.AlignCenter)

                text = QLabel(f"{name}\nCode: {code}\nDims: {dims}\n{notes}")
                text.setWordWrap(True)
                load_btn = QPushButton("Load")
                load_btn.clicked.connect(_make_loader(dxf_path, name))

                grid.addWidget(img_label, row_idx, 0)
                grid.addWidget(text, row_idx, 1)
                grid.addWidget(load_btn, row_idx, 2)

        # حفظ المراجع للوصول منها من floating_window
        self._grid = grid
        self.refresh_profiles_list = refresh_profiles_list
