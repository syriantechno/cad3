# ✅ Patched v10: Use SetBgGradientColors for safe background on OCC 7.9, no grid
# ✅ Patched v9: Disabled grid/axes entirely for OCC 7.9 stability
# ✅ Patched v8: Safe grid setup with fallback for OCC 7.9 (no crash)
# ✅ Patched v7: Use SetBackgroundColors in _late_init_view (compatible with pythonocc 7.9)
# ✅ Patched v6: Restored original layout, SetBackgroundColor for light gray, kept triedron
# ✅ Patched v4: Moved QWidget import to top, fixed UnboundLocalError
# ✅ Patched v3: Fixed viewer layout + Fusion background + Triedron
# ✅ Patched v2: Fixed indentation + Fusion-style background (QFrame) + Triedron
# ✅ Patched: Fusion-style background (QFrame) + Triedron only — original logic untouched
# gui_fusion.py
import logging
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton,
    QFileDialog, QHBoxLayout, QLabel, QComboBox,
    QDoubleSpinBox, QLineEdit, QToolBar, QAction
)
from PyQt5.QtCore import QTimer, Qt
import sys

# Project tools (expected to exist in your repo)
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

# Optional viewer color util if you have it
try:
    from tools.viewer_utils import setup_viewer_colors
except Exception:
    setup_viewer_colors = None

# OCC types
from OCC.Core.gp import gp_Ax3, gp_Pnt, gp_Dir

from OCC.Core.Quantity import (
    Quantity_NOC_WHITE, Quantity_NOC_BLACK, Quantity_Color, Quantity_TOC_RGB
)


class AlumCamGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AlumCam GUI - Fusion‑style Viewer")
        self.setGeometry(100, 100, 1400, 800)

        if not OCC_OK:
            raise RuntimeError("pythonocc-core viewer not available.")

        # ===== Central layout =====
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        # ===== 3D Viewer =====
        # ✅ v6: Use original layout + OCC background color
        self.viewer_widget = qtViewer3d(self)
        layout.addWidget(self.viewer_widget)
        self.display = self.viewer_widget._display
        # Set Fusion-like light gray backgroundlayout.addWidget(self.viewer_widget)

        # Init later after view is ready
        QTimer.singleShot(100, self._late_init_view)

        # ===== Floating tool window =====
        self.tool_dialog, self.show_tool_page = create_tool_window(self)
        self.tool_dialog.hide()

        # ===== Tabs (existing top bar from your project) =====
        top_tabs = create_topbar_tabs(self)
        self.setMenuWidget(top_tabs)

        # ===== Toolbar (Grid & Axes toggle) =====
        self._grid_axes_on = True
        self._add_toolbar()


        self._axis_x = None
        self._axis_y = None
        self._axis_z = None

        # ===== Bottom controls =====
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

        # Hole controls
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

        # Profile Management Buttons
        profile_layout = QHBoxLayout()

        self.profile_button = QPushButton("📐 Profile")
        self.profile_button.clicked.connect(lambda: self.show_extrude_window(1))
        profile_layout.addWidget(self.profile_button)

        self.manage_profiles_button = QPushButton("📂 Manage Profiles")
        self.manage_profiles_button.clicked.connect(lambda: self.show_extrude_window(2))
        profile_layout.addWidget(self.manage_profiles_button)

        layout.addLayout(profile_layout)

        # State
        self.loaded_shape = None
        self.hole_preview = None
        self.extrude_axis = "Y"

    def draw_axes(self):
        from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax1
        from OCC.Core.Geom import Geom_Line
        from OCC.Core.AIS import AIS_Line
        from OCC.Core.Quantity import Quantity_Color
        from OCC.Core.Quantity import Quantity_NOC_RED, Quantity_NOC_GREEN, Quantity_NOC_BLUE

        origin = gp_Pnt(0, 0, 0)

        # X axis
        x_line = Geom_Line(gp_Ax1(origin, gp_Dir(1, 0, 0)))
        self._axis_x = AIS_Line(x_line)
        self._axis_x.SetColor(Quantity_Color(Quantity_NOC_RED))
        self._axis_x.SetWidth(2.0)
        self.display.Context.Display(self._axis_x, True)

        # Y axis
        y_line = Geom_Line(gp_Ax1(origin, gp_Dir(0, 1, 0)))
        self._axis_y = AIS_Line(y_line)
        self._axis_y.SetColor(Quantity_Color(Quantity_NOC_GREEN))
        self._axis_y.SetWidth(2.0)
        self.display.Context.Display(self._axis_y, True)

        # Z axis
        z_line = Geom_Line(gp_Ax1(origin, gp_Dir(0, 0, 1)))
        self._axis_z = AIS_Line(z_line)
        self._axis_z.SetColor(Quantity_Color(Quantity_NOC_BLUE))
        self._axis_z.SetWidth(2.0)
        self.display.Context.Display(self._axis_z, True)

    # ===== Toolbar =====
    def _add_toolbar(self):
        tb = QToolBar("View")
        self.addToolBar(Qt.TopToolBarArea, tb)

        self.act_toggle_ga = QAction("Grid & Axes", self)
        self.act_toggle_ga.setCheckable(True)
        self.act_toggle_ga.setChecked(True)
        self.act_toggle_ga.triggered.connect(self.on_toggle_grid_axes)
        tb.addAction(self.act_toggle_ga)

        from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax1
        from OCC.Core.Geom import Geom_Line
        from OCC.Core.AIS import AIS_Line
        from OCC.Core.Quantity import Quantity_NOC_RED, Quantity_NOC_GREEN, Quantity_NOC_BLUE

        def draw_axes(context):
            origin = gp_Pnt(0, 0, 0)

            # X axis (red)
            x_line = Geom_Line(gp_Ax1(origin, gp_Dir(1, 0, 0)))
            x_ais = AIS_Line(x_line)
            x_ais.SetColor(Quantity_Color(Quantity_NOC_RED))
            x_ais.SetWidth(2.0)
            context.Display(x_ais, True)

            # Y axis (green)
            y_line = Geom_Line(gp_Ax1(origin, gp_Dir(0, 1, 0)))
            y_ais = AIS_Line(y_line)
            y_ais.SetColor(Quantity_Color(Quantity_NOC_GREEN))
            y_ais.SetWidth(2.0)
            context.Display(y_ais, True)

            # Z axis (blue)
            z_line = Geom_Line(gp_Ax1(origin, gp_Dir(0, 0, 1)))
            z_ais = AIS_Line(z_line)
            z_ais.SetColor(Quantity_Color(Quantity_NOC_BLUE))
            z_ais.SetWidth(2.0)
            context.Display(z_ais, True)

        # استدعِ الدالة بعد التهيئة
        draw_axes(self.display.Context)

        # ===== Late init =====
    def _late_init_view(self):

        from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB, Quantity_NOC_GRAY
        from OCC.Core.V3d import V3d_TypeOfOrientation

        view = self.display.View
        viewer = self.display.Viewer

        # خلفية رمادية
        light_gray = Quantity_Color(0.85, 0.85, 0.85, Quantity_TOC_RGB)
        view.SetBackgroundColor(light_gray)

        # تفعيل المحاور
        try:
            view.TriedronDisplay(True)
            view.SetTrihedronPosition(V3d_TypeOfOrientation.V3d_TOB_BOTTOM_LEFT)
            view.SetTrihedronSize(0.5)  # حجم كبير وواضح
            view.SetTrihedronVisibility(True)

        except Exception as e:
            print(f"[trihedron] error: {e}")

        # تفعيل الشبكة
        try:
            viewer.ActivateGrid(0)
            viewer.SetGridColor(Quantity_NOC_GRAY)
        except Exception as e:
            print(f"[grid] error: {e}")

        # تحديث العارض
        self.display.Context.UpdateCurrentViewer()
        self.draw_axes()
    # ===== Grid + Axes =====
        # ✅ v7: Set background color after viewer is initializeddef _setup_grid_and_axes(self):

    pass
    def _toggle_grid_and_axes(self, state: bool):
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
            try:
                view.Redraw()
            except Exception:
                pass
            self._grid_axes_on = False
            if hasattr(self, "act_toggle_ga"):
                self.act_toggle_ga.setChecked(False)
        # ✅ v10: Set background using SetBgGradientColors (safe for OCC 7.9)
        from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
        light_gray = Quantity_Color(0.85, 0.85, 0.85, Quantity_TOC_RGB)
        self.display.View.SetBackgroundColor(light_gray)


    def on_toggle_grid_axes(self, checked: bool):
        try:
            self._toggle_grid_and_axes(checked)
        except Exception as e:
            print(f"[toggle_grid_and_axes] error: {e}")

    # ===== Floating windows / features =====
    def show_extrude_window(self, page_index=0):
        """Show the floating tool window for a given page (0: Extrude, 1: Profile, 2: Manager)."""
        geo = self.geometry()
        if self.tool_dialog.width() == 0:
            self.tool_dialog.resize(360, 420)
        x = geo.x() + geo.width() - self.tool_dialog.width() - 20
        y = geo.y() + 100
        self.tool_dialog.move(x, y)
        self.show_tool_page(page_index)
        print(f"[✅] Floating tool window (page {page_index}) shown.")

    def load_dxf(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open DXF", "", "DXF Files (*.dxf)")
        if not file_name:
            return
        shape = load_dxf_file(file_name)
        if shape is None:
            return
        self.loaded_shape = shape
        QTimer.singleShot(100, self._safe_display_shape)
        if self._axis_x:
            self.display.Context.Display(self._axis_x, True)
        if self._axis_y:
            self.display.Context.Display(self._axis_y, True)
        if self._axis_z:
            self.display.Context.Display(self._axis_z, True)

    def _safe_display_shape(self):
        try:
            self.display.EraseAll()
            self.display.DisplayShape(self.loaded_shape, update=True)
            self.display.FitAll()
        except Exception as e:
            print(f"Display failed: {e}")

    def extrude_clicked_from_window(self):
        """Called from Apply button in extrude floating window."""
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

