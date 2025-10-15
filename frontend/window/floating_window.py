from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QStackedWidget, QScrollArea, QPushButton,
                             QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit, QLabel, QWidget, QFrame, QListWidget,
                             QSizePolicy, QMessageBox, QFileDialog, QGridLayout)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QPoint, QTimer
from pathlib import Path
import os, json, shutil

from dxf_tools import load_dxf_file
from tools.database import ProfileDB

# قبل
# extrude_page = create_extrude_page()

# بعد
from frontend.window.extrude_window import ExtrudeWindow
from frontend.window.profile_window import ProfileWindow
from frontend.window.profiles_manager_window import ProfilesManagerWindow
from frontend.window.tools_manager_window import ToolsManagerWindow


try:
    from OCC.Display.qtDisplay import qtViewer3d
    from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
    from OCC.Core.Prs3d import Prs3d_LineAspect
    from OCC.Core.Aspect import Aspect_TOL_SOLID
except Exception:
    qtViewer3d = None



# ========== الدوال المساعدة ==========



def _setup_viewer_colors(display):
    try:
        if display is None:
            return
        light_gray = Quantity_Color(0.85, 0.85, 0.85, Quantity_TOC_RGB)
        black = Quantity_Color(0.0, 0.0, 0.0, Quantity_TOC_RGB)
        view = display.View
        view.SetBgGradientStyle(0)
        view.SetBackgroundColor(light_gray)
        view.MustBeResized()
        view.Redraw()
        drawer = display.Context.DefaultDrawer()
        drawer.SetFaceBoundaryDraw(True)
        drawer.SetFaceBoundaryAspect(Prs3d_LineAspect(black, Aspect_TOL_SOLID, 1.0))
        display.Context.UpdateCurrentViewer()
        view.Redraw()
        print("[DEBUG] Viewer background set to light gray with black edges.")
    except Exception as e:
        print(f"[ERROR] _setup_viewer_colors failed: {e}")

def _load_tool_types():
    try:
        with open("data/tool_types.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_tool_types(tool_types: dict):
    Path("data").mkdir(parents=True, exist_ok=True)
    with open("data/tool_types.json", "w", encoding="utf-8") as f:
        json.dump(tool_types, f, indent=2, ensure_ascii=False)

# ========== النافذة القابلة للسحب ==========

class DraggableDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_dragging = False
        self._drag_pos = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False

# ========== دالة الإنشاء الرئيسية ==========

from .extrude_window import ExtrudeWindow
from .profile_window import ProfileWindow
from .profiles_manager_window import ProfilesManagerWindow
from .tools_manager_window import ToolsManagerWindow

def create_tool_window(parent):
    tool_types = _load_tool_types()
    dialog = DraggableDialog(parent)
    dialog.setObjectName("ToolFloatingWindow")
    dialog.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    dialog.setFixedWidth(600)
    dialog.setStyleSheet(""" /* … stylesheet كما في الكود الأصلي … */ """)

    main_layout = QVBoxLayout(dialog)
    main_layout.setContentsMargins(10, 10, 10, 10)
    main_layout.setSpacing(8)

    header = QLabel("Tool Options")
    header.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 4px;")
    main_layout.addWidget(header)

    line = QFrame()
    line.setObjectName("line")
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    main_layout.addWidget(line)

    stacked = QStackedWidget(dialog)
    main_layout.addWidget(stacked)

    # إنشاء الصفحات
    extrude_page = ExtrudeWindow(parent)
    profile_page = ProfileWindow(dialog, load_dxf=load_dxf_file, qtViewer3d=qtViewer3d)

    profiles_manager_page = ProfilesManagerWindow(dialog, load_dxf=load_dxf_file, parent_main=parent)
    tools_page = ToolsManagerWindow(tool_types, open_add_type_dialog_cb=None)  # لاحقًا تضيف الكول باك

    # إضافة إلى الستاك
    stacked.addWidget(extrude_page)             # index 0
    stacked.addWidget(profile_page)             # index 1
    stacked.addWidget(profiles_manager_page)    # index 2
    stacked.addWidget(tools_page)               # index 3 ✅

    # ✅ حفظ المراجع داخل الـ dialog
    dialog.extrude_page = extrude_page
    dialog.profile_page = profile_page
    dialog.profiles_manager_page = profiles_manager_page
    dialog.tools_page = tools_page

    # أزرار أسفل
    bottom_layout = QHBoxLayout()
    bottom_layout.addStretch()
    cancel_btn = QPushButton("Cancel")
    cancel_btn.setObjectName("CancelBtn")
    apply_btn = QPushButton("Apply")
    apply_btn.setObjectName("ApplyBtn")
    bottom_layout.addWidget(cancel_btn)
    bottom_layout.addWidget(apply_btn)
    main_layout.addLayout(bottom_layout)

    cancel_btn.clicked.connect(dialog.hide)

    def handle_apply():
        idx = stacked.currentIndex()

        if idx == 0:
            # Extrude
            try:
                parent.extrude_clicked_from_window()
                profile_name = getattr(parent, "active_profile_name", None)
                distance_val = getattr(parent, "last_extrude_distance", None)
                if profile_name and distance_val and hasattr(parent, "op_browser"):
                    parent.op_browser.add_extrude(profile_name, distance_val)
                dialog.hide()
            except Exception as e:
                QMessageBox.critical(dialog, "Extrude Error", str(e))
                return

        elif idx == 1:
            # Profile Page
            prof = profile_page.get_profile_data()
            name = prof["name"]
            if not name:
                QMessageBox.information(dialog, "Profile", "Please enter profile Name.")
                return
            src_dxf = prof["dxf"]
            if not src_dxf:
                QMessageBox.information(dialog, "Profile", "Please choose a DXF file.")
                return
            try:
                shape = load_dxf_file(src_dxf)
                if shape is None:
                    raise RuntimeError("Invalid DXF shape.")
                small_display = profile_page._small_display
                if small_display is not None:
                    small_display.EraseAll()
                    small_display.DisplayShape(shape, update=True)
                    small_display.FitAll()

                profile_dir = Path("profiles") / name
                profile_dir.mkdir(parents=True, exist_ok=True)
                dxf_dst = profile_dir / f"{name}.dxf"
                img_path = profile_dir / f"{name}.png"
                try:
                    from tools.profile_tools import _dump_display_png
                    _dump_display_png(small_display, shape, img_path)
                except Exception:
                    pass
                shutil.copy2(src_dxf, dxf_dst)
                db = ProfileDB()
                db.add_profile(
                    name=name,
                    code=profile_page._p_code.text().strip(),
                    dimensions=profile_page._p_dims.text().strip(),
                    notes=profile_page._p_notes.text().strip(),
                    dxf_path=str(dxf_dst),
                    brep_path="",
                    image_path=str(img_path) if img_path.exists() else ""
                )
                QMessageBox.information(dialog, "Saved", "Profile saved successfully.")
                if hasattr(parent, "op_browser"):
                    parent.op_browser.add_profile(name)
                dialog.hide()
            except Exception as e:
                QMessageBox.critical(dialog, "Error", f"Failed to save profile:\n{e}")
                return

        elif idx == 2:
            QMessageBox.information(dialog, "Profiles", "Use Load / OK button in page.")
            return

        elif idx == 3:
            QMessageBox.information(dialog, "Tools", "Save Tool not implemented.")
            return

    apply_btn.clicked.connect(handle_apply)

    def show_page(index: int):
        stacked.setCurrentIndex(index)
        if index == 2:
            profiles_manager_page.refresh_profiles_list()
            header.setText("Profiles Manager")
        elif index == 1:
            header.setText("Profile")
        elif index == 3:
            header.setText("Tools Manager")
        else:
            header.setText("Extrude")
        dialog.show()
        dialog.raise_()

    dialog.stack = stacked
    dialog.show_page = show_page

    return dialog, show_page

