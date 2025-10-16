# ✅ Patched v10: Use SetBgGradientColors for safe background on OCC 7.9, no grid1
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
from frontend.utils.viewer_colors import setup_viewer_colors
# Project tools (expected to exist in your repo)
from dxf_tools import load_dxf_file
from extrude_tools import extrude_shape, add_hole, preview_hole
from frontend.topbar_tabs import create_topbar_tabs
from frontend.window.floating_window import create_tool_window
from frontend.tree import Tree
from frontend.operation_browser import OperationBrowser
from tools.tool_db import init_db, insert_tool, get_all_tools
logging.basicConfig(level=logging.DEBUG)
from frontend.window.floating_window import create_tool_window
from viewer import OCCViewer
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB


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
from frontend.operation_browser import OperationBrowser


class AlumCamGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        init_db()
        self.setWindowTitle("AlumCam GUI - Fusion‑style Viewer")
        self.setGeometry(100, 100, 1400, 800)

        if not OCC_OK:
            raise RuntimeError("pythonocc-core viewer not available.")

        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter
        from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

        # ===== Viewer & Browser =====

        self.viewer_widget = qtViewer3d(self)
        self.display = self.viewer_widget._display


        # 1) فعّل event filter على ويدجت العارض
        self.viewer_widget.installEventFilter(self)

        # 2) اطبع حالة الـ Context بعد 1.5 ثانية (بعد ما يجهز العرض)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1500, self._debug_hover_state)

        self.draw_axes()

        self.op_browser = OperationBrowser()
        self.op_browser.setStyleSheet("background-color: rgba(220, 220, 220, 180);")
        self.op_browser.setFixedWidth(250)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.op_browser)
        splitter.addWidget(self.viewer_widget)

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

        profile_layout = QHBoxLayout()
        self.profile_button = QPushButton("📐 Profile")
        self.profile_button.clicked.connect(self.open_add_profile_page)   # ✅ فتح صفحة Profile
        profile_layout.addWidget(self.profile_button)

        self.manage_profiles_button = QPushButton("📂 Manage Profiles")
        self.manage_profiles_button.clicked.connect(lambda: self.show_tool_page(4))  # ✅ صفحة إدارة البروفايلات
        profile_layout.addWidget(self.manage_profiles_button)

        # ===== Final Layout =====
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.addWidget(splitter)
        main_layout.addLayout(btn_layout)
        main_layout.addLayout(profile_layout)
        self.setCentralWidget(main_widget)




        # ===== Background Setup =====
        def apply_background():
            print("⚡ Applying background color...")

            try:

                self.display.set_bg_gradient_color(
                    Quantity_Color(0.92, 0.92, 0.92, Quantity_TOC_RGB),
                    Quantity_Color(0.92, 0.92, 0.92, Quantity_TOC_RGB),
                    True
                )
                self.display._display.View.FitAll()  # ✅ الصحيح
                self.display._display.View.Update()  # مهم لتحديث الفيو
                print("✅ الخلفية تم تطبيقها")
            except Exception as e:
                print(f"❌ خطأ أثناء تطبيق الخلفية: {e}")


        self.draw_axes()

        def _apply_view_theme_once(self):
            """تطبيق الخلفية + الشبكة + ألوان الهوفر/التحديد مرة واحدة فقط بعد أول عرض شكل."""
            if getattr(self, "_theme_applied", False):
                return

            view = self.display.View
            ctx = self.display.Context
            viewer = self.display.Viewer

            try:
                # الخلفية (تدرّج رأسي لطيف)
                from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
                top = Quantity_Color(0.92, 0.92, 0.92, Quantity_TOC_RGB)
                bottom = Quantity_Color(1.00, 1.00, 1.00, Quantity_TOC_RGB)
                try:
                    # 1 = Vertical (أعلى → أسفل)
                    view.SetBgGradientColors(top, bottom, 1, True)
                    view.Redraw()
                except Exception:
                    pass

                # الشبكة (على مستوى الـ Viewer)
                try:
                    from OCC.Core.Aspect import Aspect_GT_Rectangular, Aspect_GDM_Lines
                    from OCC.Core.Quantity import Quantity_NOC_BLACK
                    viewer.ActivateGrid(Aspect_GT_Rectangular, Aspect_GDM_Lines)
                    viewer.SetPrivilegedPlane(0.0, 0.0, 1.0, 0.0)
                    viewer.SetGridColor(Quantity_NOC_BLACK)
                    viewer.DisplayGrid()
                except Exception:
                    pass

                # ألوان hover و selection
                try:
                    hover = Quantity_Color(0.85, 0.85, 0.85, Quantity_TOC_RGB)  # رمادي فاتح بدل التركواز
                    select = Quantity_Color(1.0, 0.6, 0.0, Quantity_TOC_RGB)  # برتقالي باهت
                    ctx.SetHighlightColor(hover)
                    ctx.SetSelectionColor(select)
                    ctx.SetAutomaticHighlight(True)
                except Exception:
                    pass

                self._theme_applied = True
                print("✅ View theme applied once (background, grid, hover/selection).")
            except Exception as e:
                print(f"[WARN] theme apply skipped: {e}")

        # ===== Floating tool window =====
        self.tool_dialog, self.show_tool_page = create_tool_window(self)
        self.tool_dialog.hide()

        # ===== Tabs =====
        top_tabs = create_topbar_tabs(self)
        self.setMenuWidget(top_tabs)

        # ===== Toolbar =====
        self._grid_axes_on = True

        # ===== Axes State =====
        self._axis_x = None
        self._axis_y = None
        self._axis_z = None

        # ===== Geometry State =====
        self.loaded_shape = None
        self.hole_preview = None
        self.extrude_axis = "Y"

    def display_shape(self, shape):
        self.display.EraseAll()

        from OCC.Core.AIS import AIS_Shape
        from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

        # جسم واحد مظلل + حواف (OCCT يتكفل بالحواف تلقائيًا)
        ais_shape = AIS_Shape(shape)
        ais_shape.SetDisplayMode(1)  # 0=wireframe, 1=shaded (مع حواف)

        light_gray = Quantity_Color(0.85, 0.85, 0.85, Quantity_TOC_RGB)

        ctx = self.display.Context
        ctx.Display(ais_shape, True)
        ctx.SetColor(ais_shape, light_gray, False)

        # ✅ طبّق ستايل الهوفر/التحديد الآن (بعد أن صار هناك AIS في المشهد)
        self.apply_hover_and_selection_style()
        c = ctx.HighlightStyle().Color()
        print("[DEBUG] Hover style after applying:", c.Red(), c.Green(), c.Blue())

        # أعِد عرض المحاور إذا كانت موجودة
        if getattr(self, "_axis_x", None) and getattr(self, "_axis_y", None) and getattr(self, "_axis_z", None):
            ctx.Display(self._axis_x, True)
            ctx.Display(self._axis_y, True)
            ctx.Display(self._axis_z, True)

        self.display.FitAll()
        ctx.UpdateCurrentViewer()

    def _debug_hover_state(self):
        """يطبع حالة الـ Context للتأكد من تفعيل الهوفر ورؤية ألوان الستايل."""
        try:
            ctx = self.display.Context
        except Exception:
            print("[DEBUG] display.Context غير جاهز")
            return

        print("=== [DEBUG] Hover State ===")
        # هل الهوفر التلقائي مفعّل؟
        try:
            print("AutomaticHighlight:", ctx.AutomaticHighlight())
        except Exception:
            print("AutomaticHighlight: (غير مدعوم في الإصدار الحالي)")

        # هل هناك جسم تحت المؤشر أو جسم مُختار؟
        try:
            print("HasCurrent:", ctx.HasCurrent())
            print("HasSelected:", ctx.HasSelected())
        except Exception as e:
            print("HasCurrent/HasSelected check failed:", e)

        # اطبع لون ستايل الهوفر الحالي
        try:
            hs = ctx.HighlightStyle()  # Prs3d_Drawer
            col = hs.Color()
            print("Hover color:", col.Red(), col.Green(), col.Blue())
        except Exception:
            # بعض الإصدارات القديمة
            try:
                c = ctx.HighlightColor()
                print("Hover color:", c.Red(), c.Green(), c.Blue())
            except Exception:
                print("Hover color: (غير متاح للقراءة)")

        # اطبع لون ستايل التحديد
        try:
            ss = ctx.SelectionStyle()
            col = ss.Color()
            print("Selection color:", col.Red(), col.Green(), col.Blue())
        except Exception:
            print("Selection color: (غير متاح للقراءة)")
        print("===========================")

    def eventFilter(self, obj, event):
        """تتبّع حركة الماوس فوق نافذة العرض لمعرفة إن كان يلتقط AIS أم لا."""
        from PyQt5.QtCore import QEvent
        if obj is self.viewer_widget and event.type() == QEvent.MouseMove:
            try:
                ctx = self.display.Context
                if ctx.HasCurrent():
                    # يوجد كائن تحت المؤشر
                    try:
                        ais = ctx.Current()  # قد يرمي استثناء، لذا نحوطه
                        print("[DEBUG] Hovering AIS object:", ais)
                    except Exception:
                        print("[DEBUG] Hovering: has current (AIS موجود)")
                else:
                    print("[DEBUG] Hovering over empty space")
            except Exception:
                pass
        return super().eventFilter(obj, event)

    def apply_hover_and_selection_style(self):
        """تهيئة لون الهوفر والتحديد (متوافقة مع OCCT 7.9)."""
        print("[🎨] Applying hover & selection styles (OCCT 7.9)...")

        from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
        from OCC.Core.Prs3d import Prs3d_Drawer

        ctx = self.display.Context

        # ⚪ لون الهوفر: رمادي فاتح
        hover_color = Quantity_Color(0.85, 0.85, 0.85, Quantity_TOC_RGB)
        hover_style = Prs3d_Drawer()
        hover_style.SetColor(hover_color)
        hover_style.SetDisplayMode(1)
        hover_style.SetTransparency(0.0)
        ctx.SetHighlightStyle(hover_style)

        # 🟠 لون التحديد: برتقالي
        select_color = Quantity_Color(1.0, 0.6, 0.0, Quantity_TOC_RGB)
        select_style = Prs3d_Drawer()
        select_style.SetColor(select_color)
        select_style.SetDisplayMode(1)
        select_style.SetTransparency(0.0)
        ctx.SetSelectionStyle(select_style)

        try:
            ctx.SetAutomaticHighlight(True)
        except Exception:
            pass
        c = self.display.Context.HighlightStyle().Color()
        print("[DEBUG] New hover color:", c.Red(), c.Green(), c.Blue())

        print("[✅] Hover & selection styles applied for OCCT 7.9")

    def draw_axes(self):
        from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax1
        from OCC.Core.Geom import Geom_Line
        from OCC.Core.AIS import AIS_Line
        from OCC.Core.Quantity import Quantity_Color
        from OCC.Core.Quantity import Quantity_NOC_RED, Quantity_NOC_GREEN, Quantity_NOC_BLUE

        origin = gp_Pnt(0, 0, 0)

        # X
        x_line = Geom_Line(gp_Ax1(origin, gp_Dir(1, 0, 0)))
        self._axis_x = AIS_Line(x_line)
        self._axis_x.SetColor(Quantity_Color(Quantity_NOC_RED))
        self._axis_x.SetWidth(0.5)

        # Y
        y_line = Geom_Line(gp_Ax1(origin, gp_Dir(0, 1, 0)))
        self._axis_y = AIS_Line(y_line)
        self._axis_y.SetColor(Quantity_Color(Quantity_NOC_GREEN))
        self._axis_y.SetWidth(0.5)

        # Z
        z_line = Geom_Line(gp_Ax1(origin, gp_Dir(0, 0, 1)))
        self._axis_z = AIS_Line(z_line)
        self._axis_z.SetColor(Quantity_Color(Quantity_NOC_BLUE))
        self._axis_z.SetWidth(0.5)

        ctx = self.display.Context
        ctx.Display(self._axis_x, True)
        ctx.Display(self._axis_y, True)
        ctx.Display(self._axis_z, True)

    # ===== Late init =====





        from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB, Quantity_NOC_BLACK
        from OCC.Core.Aspect import Aspect_GT_Rectangular, Aspect_GDM_Lines

        view = self.display.View
        viewer = self.display.Viewer

        print("[init] بدء تهيئة العرض الثلاثي")

        # خلفية رمادية
        light_gray = Quantity_Color(0.85, 0.85, 0.85, Quantity_TOC_RGB)
        view.SetBackgroundColor(light_gray)
        print("[background] تم تعيين الخلفية إلى رمادي فاتح")

        # تفعيل المحاور
        try:
            print("[trihedron] جاري تفعيل المحاور...")
            view.TriedronDisplay(True)
            view.SetTrihedronSize(0.05)

            print("[trihedron] تم تفعيل المحاور")
        except Exception as e:
            print(f"[trihedron] error: {e}")

        # تفعيل الشبكة
        try:
            print("[grid] تفعيل الشبكة...")
            viewer.ActivateGrid(Aspect_GT_Rectangular, Aspect_GDM_Lines)
            viewer.SetPrivilegedPlane(0.0, 0.0, 1.0, 0.0)
            viewer.DisplayGrid()
            viewer.SetGridColor(Quantity_NOC_BLACK)
            print("[grid] الشبكة مفعّلة")
        except Exception as e:
            print(f"[grid] خطأ في الشبكة: {e}")

        view.MustBeResized()
        view.Redraw()
        from OCC.Core.V3d import V3d_TypeOfOrientation
        view.SetProj(V3d_TypeOfOrientation.V3d_XposYnegZpos)
        view.SetZoom(1.0)
        view.Redraw()

        print("[view] تم إعادة رسم العرض")

        self.display.Context.UpdateCurrentViewer()

        print("[context] تم تحديث السياق")

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
            self.tree.add_item("DXF Profile", shape=self.loaded_shape, callback=self.display_shape)

    def _safe_display_shape(self):
        try:
            self.display_shape_with_axes(self.loaded_shape)
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
            result_shape = extrude_shape(self.loaded_shape, axis, distance)

            from OCC.Core.AIS import AIS_Shape
            from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
            from OCC.Core.TopExp import TopExp_Explorer
            from OCC.Core.TopAbs import TopAbs_EDGE

            # ✅ لون الجسم رمادي فاتح (قريب من Fusion)
            body_color = Quantity_Color(0.545, 0.533, 0.498, Quantity_TOC_RGB)
            ais_shape = AIS_Shape(result_shape)
            ais_shape.SetColor(body_color)
            ais_shape.SetDisplayMode(1)  # عرض الحواف تلقائيًا

            self.display.EraseAll()

            # ✅ عرض الجسم
            self.display.Context.Display(ais_shape, False)
            self.display.Context.Activate(ais_shape, 0, True)
            self.display.Context.SetColor(ais_shape, body_color, False)


            # ✅ عرض الحواف بلون أسود نقي
            black = Quantity_Color(0.0, 0.0, 0.0, Quantity_TOC_RGB)
            edge_explorer = TopExp_Explorer(result_shape, TopAbs_EDGE)
            while edge_explorer.More():
                edge = edge_explorer.Current()
                edge_shape = AIS_Shape(edge)
                self.display.Context.Display(edge_shape, False)
                self.display.Context.SetColor(edge_shape, black, False)
                self.display.Context.Activate(edge_shape, 0, True)
                edge_explorer.Next()

            self.loaded_shape = result_shape

            # ✅ إعادة عرض المحاور
            ctx = self.display.Context
            for axis in [self._axis_x, self._axis_y, self._axis_z]:
                if axis:
                    ctx.Display(axis, True)

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
        self.display_shape_with_axes(self.loaded_shape)

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

        # عرض الشكل الأساسي بلون رمادي غامق
        from OCC.Core.AIS import AIS_Shape
        from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

        dark_gray = Quantity_Color(0.3, 0.3, 0.3, Quantity_TOC_RGB)
        ais_loaded = AIS_Shape(self.loaded_shape)
        ais_loaded.SetColor(dark_gray)
        self.display.Context.Display(ais_loaded, True)

        self.display_shape_with_axes(self.loaded_shape)

        # عرض المعاينة باللون الأحمر
        self.hole_preview = preview_hole(x, y, z, dia, axis)
        self.display.DisplayShape(self.hole_preview, color="RED", update=True)

    def open_add_profile_page(self):
        print("[DEBUG] تم الضغط على زر Profile")

        if not hasattr(self, "tool_dialog") or self.tool_dialog is None:
            print("[ERROR] tool_dialog غير جاهز")
            return

        dialog = self.tool_dialog

        if not hasattr(dialog, "profile_page") or dialog.profile_page is None:
            print("[ERROR] profile_page غير جاهزة")
            return

        profile_page = dialog.profile_page
        print("[DEBUG] tool_dialog و profile_page جاهزين")

        # تصفير سياق التعديل
        dialog._edit_ctx.update({
            "active": False,
            "pid": None,
            "orig_name": None,
            "orig_dxf": None,
            "orig_img": None
        })

        # تصفير حقول الإدخال
        profile_page._p_name.clear()
        profile_page._p_code.clear()
        profile_page._p_dims.clear()
        profile_page._p_notes.clear()
        profile_page._dxf_path_edit.clear()

        # فتح صفحة البروفايل (index 1)
        self.show_tool_page(1)
        print("[DEBUG] تم استدعاء show_tool_page(1) لكن لن ننفذه مؤقتاً للاختبار")


