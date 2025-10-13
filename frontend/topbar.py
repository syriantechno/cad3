# toolbar.py

from PyQt5.QtWidgets import QToolBar, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize

def create_topbar(parent, display):
    """
    ترجع Toolbar أيقوني جاهز للاستخدام داخل أي نافذة.
    parent: QWidget أو QMainWindow
    display: كائن العرض OCC لربطه بالأزرار
    """
    toolbar = QToolBar("Main Toolbar", parent)
    toolbar.setIconSize(QSize(32, 32))
    toolbar.setStyleSheet("""
        QToolBar {
            background-color: #2c2f33;
            spacing: 10px;
        }
        QToolButton {
            background-color: #2c2f33;
            border: none;
        }
        QToolButton:hover {
            background-color: #40444b;
        }
    """)

    # ===== أيقونة فتح DXF =====
    open_action = QAction(QIcon(), "Open DXF", parent)
    open_action.setToolTip("📂 Load DXF")
    open_action.triggered.connect(parent.load_dxf)
    toolbar.addAction(open_action)

    # ===== أيقونة Fit All =====
    fit_action = QAction(QIcon(), "Fit All", parent)
    fit_action.setToolTip("🔍 Fit All")
    fit_action.triggered.connect(lambda: display.FitAll())
    toolbar.addAction(fit_action)

    # ===== أيقونة Extrude =====
    extrude_action = QAction(QIcon(), "Extrude", parent)
    extrude_action.setToolTip("🧱 Extrude")
    extrude_action.triggered.connect(parent.extrude_clicked)
    toolbar.addAction(extrude_action)

    # ===== أيقونة Preview Hole =====
    preview_action = QAction(QIcon(), "Preview Hole", parent)
    preview_action.setToolTip("👁 Preview Hole")
    preview_action.triggered.connect(parent.preview_clicked)
    toolbar.addAction(preview_action)

    return toolbar
