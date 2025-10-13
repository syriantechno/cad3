#gui_fusion
import logging
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QPushButton,
    QFileDialog, QHBoxLayout, QLabel, QComboBox,
    QDoubleSpinBox, QLineEdit
)
from PyQt5.QtCore import QTimer, Qt

from dxf_tools import load_dxf_file
from extrude_tools import extrude_shape, add_hole, preview_hole
from frontend.topbar_tabs import create_topbar_tabs
from frontend.floating_window import create_tool_window

logging.basicConfig(level=logging.DEBUG)

# OCC viewer
try:
    from OCC.Display.qtDisplay import qtViewer3d
    OCC_OK = True
except Exception:
    OCC_OK = False
    qtViewer3d = None

# ألوان العارض (خلفية بيضاء + حدود سوداء)
try:
    from tools.viewer_utils import setup_viewer_colors
except Exception:
    setup_viewer_colors = None

# وارد أن تختلف التواقيع بين إصدارات OCC لهذا نستورد ما نحتاجه هنا
from OCC.Core.gp import gp_Ax3, gp_Pnt, gp_Dir
from OCC.Core.V3d import V3d_RectangularGrid


class AlumCamGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AlumCam GUI - Stable V2")
        self.setGeometry(100, 100, 1400, 800)

        print("Initializing GUI and OCC viewer...")

        # ===== Main Layout =====
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        # ===== 3D Viewer =====
        if not OCC_OK:
            raise RuntimeError("pythonocc-core viewer not available.")

        self.viewer_widget = qtViewer3d(self)
        self.display = self.viewer_widget._display
        layout.addWidget(self.viewer_widget)

        # تهيئة المظهر + الشبكة/المحاور بعد اكتمال إنشاء الـ View
        QTimer.singleShot(100, self._late_init_view)

        # ===== Tool Floating Window (Extrude/Profile/Manager) =====
        self.tool_dialog, self.show_tool_page = create_tool_window(self)
        self.tool_dialog.hide()

        # ===== Top Tabs =====
        top_tabs = create_topbar_tabs(self)  # يحتوي زر Grid & Axes (Toggle) إن عرّفته بالتوب بار
        self.setMenuWidget(top_tabs)

        # ===== Control Buttons (Bottom Row) =====
        btn_layout = QHBoxLayout()

        self.load_button = QPushButton("📂 Load DXF")
        self.load_button.clicked.connect(self.load_dxf)
        btn_layout.addWidget(self.load_button)

        self.axis_combo = QComboBox()
        self.axis_combo.addItems(["Y", "Z", "X"])
        btn_layout.addWidget(QLabel("Extrude Axis:"))
        btn_layout.addWidget(self.axis_combo)

        self.distance_spin = QDoubleSpinBox()
        self.distance_spin.setRange(1, 9999)
        self.distance_spin.setValue(100)
        self.distance_spin.setSuffix(" mm")
        btn_layout.addWidget(QLabel("Distance (mm):"))
        btn_layout.addWidget(self.distance_spin)

        self.extrude_button = QPushButton("🧱 Extrude")
        self.extrude_button.clicked.connect(self.show_extrude_window)
        btn_layout.addWidget(self.extrude_button)

        layout.addLayout(btn_layout)

        # ===== Hole Controls =====
        for lbl in ["X", "Y", "Z", "Dia"]:
            btn_layout.addWidget(QLabel(f"Hole {lbl}:"))

        self.hole_x = QLineEdit("0")
        self.hole_y = QLineEdit("0")
        self.hole_z = QLineEdit("0")
        self.hole_dia = QLineEdit("6")

        for w in [self.hole_x, self.hole_y, self.hole_z, self.hole_dia]:
            btn_layout.addWidget(w)

        self.axis_hole_combo = QComboBox()
        self.axis_hole_combo.addItems(["X", "Y", "Z"])
        btn_layout.addWidget(QLabel("Hole Axis:"))
        btn_layout.addWidget(self.axis_hole_combo)

        self.add_hole_btn = QPushButton("🕳 Add Hole")
        self.add_hole_btn.clicked.connect(self.hole_clicked)
        btn_layout.addWidget(self.add_hole_btn)

        self.preview_hole_btn = QPushButton("👁 Preview Hole")
        self.preview_hole_btn.clicked.connect(self.preview_clicked)
        btn_layout.addWidget(self.preview_hole_btn)

        # ===== Profile Management Buttons =====
        profile_layout = QHBoxLayout()

        self.profile_button = QPushButton("📐 Profile")
        self.profile_button.clicked.connect(lambda: self.show_extrude_window(1))
        profile_layout.addWidget(self.profile_button)

        self.manage_profiles_button = QPushButton("📂 Manage Profiles")
        self.manage_profiles_button.clicked.connect(lambda: self.show_extrude_window(2))
        profile_layout.addWidget(self.manage_profiles_button)

        layout.addLayout(profile_layout)

        # ===== State =====
        self.loaded_shape = None
        self.hole_preview = None
        self.extrude_axis = "Y"

        # حالة الشبكة/المحاور (لزر التبديل)
        self._grid_axes_on = True

    # ========== تهيئة متأخرة للعرض ==========
    def _late_init_view(self):
        # خلفية بيضاء + حدود سوداء (إن وُجدت الدالة)
        try:
            if setup_viewer_colors:
                setup_viewer_colors(self.display)
        except Exception as e:
            print(f"[setup_viewer_colors] warning: {e}")

        # شبكة XY + أسماء المحاور في الركن السفلي الأيسر
        try:
            self._setup_grid_and_axes()
        except Exception as e:
            print(f"[setup_grid_and_axes] warning: {e}")

    # ========== Grid + Axes ==========
    def _setup_grid_and_axes(self):
        """
        تفعيل شبكة XY لا نهائية + Triedron (أسماء المحاور) في الركن السفلي الأيسر.
        """
        viewer = self.display.Viewer
        view = self.display.View

        # اجعل المستوى المميز هو XY (Z لأعلى)
        ax3 = gp_Ax3(gp_Pnt(0.0, 0.0, 0.0), gp_Dir(0.0, 0.0, 1.0))
        viewer.SetPrivilegedPlane(ax3)

        # تفعيل الشبكة (توقيع ActivateGrid يختلف حسب الإصدار — نجرب الأكثر شيوعًا أولًا)
        try:
            viewer.ActivateGrid(V3d_RectangularGrid, 0.0, 0.0)
        except TypeError:
            # بعض الإصدارات تحتاج Bool بدل الإحداثيات
            viewer.ActivateGrid(V3d_RectangularGrid, True, True)

        # لون الشبكة رمادي فاتح + تعطيل الـ echo
        try:
            from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
            grid_color = Quantity_Color(0.85, 0.85, 0.85, Quantity_TOC_RGB)
            view.SetGridColor(grid_color)
        except Exception:
            pass

        view.SetGridEcho(False)
        view.MustBeResized()

        # عرض أسماء المحاور في الركن (النداء بدون معاملات عادةً يكفي)
        try:
            view.TriedronDisplay()
        except Exception:
            # بدائل لبعض الإصدارات إن لزم
            try:
                from OCC.Core.V3d import V3d_TriedronOrigin, V3d_ZBUFFER
                view.TriedronDisplay(V3d_TriedronOrigin, 1, 0.08, V3d_ZBUFFER)
            except Exception:
                pass

        view.Redraw()
        self._grid_axes_on = True

    def _toggle_grid_and_axes(self, state: bool):
        """
        إظهار/إخفاء الشبكة + أسماء المحاور.
        """
        viewer = self.display.Viewer
        view = self.display.View

        if state:
            self._setup_grid_and_axes()
        else:
            try:
                viewer.DeactivateGrid()
            except Exception:
                pass
            try:
                view.TriedronErase()
            except Exception:
                pass
            view.Redraw()
            self._grid_axes_on = False

    # يستدعيها زر Grid & Axes (Toggle) من التوب بار
    def on_toggle_grid_axes(self, checked: bool):
        try:
            self._toggle_grid_and_axes(checked)
        except Exception as e:
            print(f"[toggle_grid_and_axes] error: {e}")

    # ==========================================================
    def show_extrude_window(self, page_index=0):
        """عرض النافذة العائمة للصفحة المطلوبة"""
        geo = self.geometry()
        if self.tool_dialog.width() == 0:
            self.tool_dialog.resize(360, 420)
        x = geo.x() + geo.width() - self.tool_dialog.width() - 20
        y = geo.y() + 100
        self.tool_dialog.move(x, y)
        self.show_tool_page(page_index)
        print(f"[✅] Floating tool window (page {page_index}) shown.")

    # ==========================================================
    def load_dxf(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open DXF", "", "DXF Files (*.dxf)")
        if not file_name:
            return
        shape = load_dxf_file(file_name)
        if shape is None:
            return
        self.loaded_shape = shape
        QTimer.singleShot(100, self._safe_display_shape)

    def _safe_display_shape(self):
        try:
            self.display.EraseAll()
            self.display.DisplayShape(self.loaded_shape, update=True)
            self.display.FitAll()
        except Exception as e:
            print(f"Display failed: {e}")

    # ==========================================================
    def extrude_clicked_from_window(self):
        """يُستدعى من زر Apply في نافذة الإكسترود"""
        try:
            if not self.loaded_shape:
                print("⚠️ No shape loaded for extrusion.")
                return
            axis = self.axis_combo.currentText()
            distance = self.distance_spin.value()
            self.loaded_shape = extrude_shape(self.loaded_shape, axis, distance)
            self.display.EraseAll()
            self.display.DisplayShape(self.loaded_shape, update=True)
            self.display.FitAll()
            if self.tool_dialog.isVisible():
                self.tool_dialog.hide()
        except Exception as e:
            print(f"extrude_clicked_from_window error: {e}")

    # ==========================================================
    def hole_clicked(self):
        if not self.loaded_shape:
            return
        x = float(self.hole_x.text())
        y = float(self.hole_y.text())
        z = float(self.hole_z.text())
        dia = float(self.hole_dia.text())
        axis = self.axis_hole_combo.currentText()
        self.loaded_shape = add_hole(self.loaded_shape, x, y, z, dia, axis)
        self.display.EraseAll()
        self.display.DisplayShape(self.loaded_shape, update=True)
        self.display.FitAll()

    def preview_clicked(self):
        if not self.loaded_shape:
            return
        x = float(self.hole_x.text())
        y = float(self.hole_y.text())
        z = float(self.hole_z.text())
        dia = float(self.hole_dia.text())
        axis = self.axis_hole_combo.currentText()
        if self.hole_preview:
            self.display.EraseAll()
            self.display.DisplayShape(self.loaded_shape, update=True)
        self.hole_preview = preview_hole(x, y, z, dia, axis)
        self.display.DisplayShape(self.loaded_shape, update=False)
        self.display.DisplayShape(self.hole_preview, color="RED", update=True)
