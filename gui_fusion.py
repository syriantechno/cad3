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
    QMainWindow, QPushButton,
    QFileDialog
)
from PyQt5.QtCore import QTimer, Qt

# Project tools (expected to exist in your repo)
from dxf_tools import load_dxf_file

from frontend.topbar_tabs import create_topbar_tabs
from tools.axis_helpers import show_axes

from tools.tool_db import init_db

logging.basicConfig(level=logging.DEBUG)
from frontend.window.floating_window import create_tool_window


from file_ops import ( load_project, save_file)
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
from tools.axis_helpers import create_axes_with_labels

class AlumCamGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        init_db()
        self.setWindowTitle("AlumCam GUI - Fusion‑style Viewer")
        self.setGeometry(100, 100, 1400, 800)

        if not OCC_OK:
            raise RuntimeError("pythonocc-core viewer not available.")

        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter

        # ===== Viewer & Browser =====

        self.viewer_widget = qtViewer3d(self)
        self.display = self.viewer_widget._display

        # 🧭 إنشاء المحاور مرة واحدة
        (
            self._axis_x,
            self._axis_y,
            self._axis_z,
            self._axis_lbl_x,
            self._axis_lbl_y,
            self._axis_lbl_z
        ) = create_axes_with_labels(500.0)

        # 🧰 خزنهم في tuple لسهولة الاستخدام
        self._axes_tuple = (
            self._axis_x,
            self._axis_y,
            self._axis_z,
            self._axis_lbl_x,
            self._axis_lbl_y,
            self._axis_lbl_z
        )

        # 🟡 عرضهم لأول مرة
        show_axes(self.display, self._axes_tuple)

        # 🧠 تغليف EraseAll الأصلي ليعيد عرض المحاور تلقائيًا بعد كل عملية مسح
        original_erase_all = self.display.EraseAll

        def erase_all_with_axes():
            original_erase_all()
            show_axes(self.display, self._axes_tuple)

        self.display.EraseAll = erase_all_with_axes

        # 1) فعّل event filter على ويدجت العارض
        self.viewer_widget.installEventFilter(self)

        # 2) اطبع حالة الـ Context بعد 1.5 ثانية (بعد ما يجهز العرض)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1500, self._debug_hover_state)


        self.op_browser = OperationBrowser()
        self.op_browser.setStyleSheet("background-color: rgba(220, 220, 220, 180);")
        self.op_browser.setFixedWidth(250)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.op_browser)
        splitter.addWidget(self.viewer_widget)






        # ===== Final Layout =====
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.addWidget(splitter)

        self.setCentralWidget(main_widget)

        self.delete_btn = QPushButton("🗑 Delete Operation")
        self.delete_btn.clicked.connect(self.delete_selected_operation)


        # ===== Background Setup =====
        # def apply_background():
        #     print("⚡ Applying background color...")
        #
        #     try:
        #
        #         self.display.set_bg_gradient_color(
        #             Quantity_Color(0.92, 0.92, 0.92, Quantity_TOC_RGB),
        #             Quantity_Color(0.92, 0.92, 0.92, Quantity_TOC_RGB),
        #             True
        #         )
        #         self.display._display.View.FitAll()  # ✅ الصحيح
        #         self.display._display.View.Update()  # مهم لتحديث الفيو
        #         print("✅ الخلفية تم تطبيقها")
        #     except Exception as e:
        #         print(f"❌ خطأ أثناء تطبيق الخلفية: {e}")


        self.draw_axes()

        # def _apply_view_theme_once(self):
        #     """تطبيق الخلفية + الشبكة + ألوان الهوفر/التحديد مرة واحدة فقط بعد أول عرض شكل."""
        #     if getattr(self, "_theme_applied", False):
        #         return
        #
        #     view = self.display.View
        #     ctx = self.display.Context
        #     viewer = self.display.Viewer
        #
        #     try:
        #         # الخلفية (تدرّج رأسي لطيف)
        #         from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
        #         top = Quantity_Color(0.92, 0.92, 0.92, Quantity_TOC_RGB)
        #         bottom = Quantity_Color(1.00, 1.00, 1.00, Quantity_TOC_RGB)
        #         try:
        #             # 1 = Vertical (أعلى → أسفل)
        #             view.SetBgGradientColors(top, bottom, 1, True)
        #             view.Redraw()
        #         except Exception:
        #             pass
        #
        #         # الشبكة (على مستوى الـ Viewer)
        #         try:
        #             from OCC.Core.Aspect import Aspect_GT_Rectangular, Aspect_GDM_Lines
        #             from OCC.Core.Quantity import Quantity_NOC_BLACK
        #             viewer.ActivateGrid(Aspect_GT_Rectangular, Aspect_GDM_Lines)
        #             viewer.SetPrivilegedPlane(0.0, 0.0, 1.0, 0.0)
        #             viewer.SetGridColor(Quantity_NOC_BLACK)
        #             viewer.DisplayGrid()
        #         except Exception:
        #             pass
        #
        #         # ألوان hover و selection
        #         try:
        #             hover = Quantity_Color(0.85, 0.85, 0.85, Quantity_TOC_RGB)  # رمادي فاتح بدل التركواز
        #             select = Quantity_Color(1.0, 0.6, 0.0, Quantity_TOC_RGB)  # برتقالي باهت
        #             ctx.SetHighlightColor(hover)
        #             ctx.SetSelectionColor(select)
        #             ctx.SetAutomaticHighlight(True)
        #         except Exception:
        #             pass
        #
        #         self._theme_applied = True
        #         print("✅ View theme applied once (background, grid, hover/selection).")
        #     except Exception as e:
        #         print(f"[WARN] theme apply skipped: {e}")

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

    def on_operation_selected(self, category, name):
        item = self.op_browser.currentItem()
        shape = getattr(item, "shape", None)
        if shape and not shape.IsNull():
            self.display_shape_with_axes(shape)

    def display_shape(self, shape):
        self.display.EraseAll()

        self.display.FitAll()


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
            item = self.op_browser.add_profile("DXF Profile")
            item.shape = self.loaded_shape

    def _safe_display_shape(self):
        try:
            self.display_shape_with_axes(self.loaded_shape)
        except Exception as e:
            print(f"Display failed: {e}")


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

        # دوال تغليف تستخدمها الأزرار في التوب بار:

    def save_file(self):
        from file_ops import save_file_dialog
        save_file_dialog(self)

    def save_project(self, shape, path, metadata):
        return save_file(shape, path, metadata)

    def load_project(self, path):
        return load_project(path)

    def new_file(self):
        self.loaded_shape = None
        self.display.EraseAll()
        self.display.Repaint()
        self.metadata = {}
        print("🆕 تم إنشاء مشروع جديد فارغ")

    def delete_selected_operation(self):
        item = self.op_browser.currentItem()
        if item and item.parent():
            parent = item.parent()
            parent.removeChild(item)

            # عرض آخر عنصر متبقي
            remaining = parent.childCount()
            if remaining > 0:
                last_item = parent.child(remaining - 1)
                shape = getattr(last_item, "shape", None)
                if shape and not shape.IsNull():
                    self.display_shape_with_axes(shape)
                else:
                    self.display.EraseAll()
            else:
                self.display.EraseAll()
