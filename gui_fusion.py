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




from OCC.Core.AIS import AIS_Trihedron
from OCC.Core.gp import gp_Ax3, gp_Pnt
from OCC.Core.Prs3d import Prs3d_Drawer
from OCC.Core.Quantity import Quantity_Color, Quantity_NOC_BLACK

from OCC.Core.AIS import AIS_Trihedron
from OCC.Core.gp import gp_Ax3, gp_Pnt

def setup_viewer_grid_and_axes(display):
    """إعداد الشبكة والمحاور لتكون ثابتة، غير قابلة للاختيار أو الهوفر"""
    try:
        # 🧭 إنشاء المحاور (Trihedron)
        ax = gp_Ax3(gp_Pnt(0, 0, 0))
        axes_ais = AIS_Trihedron(ax)
        axes_ais.SetDatumDisplayMode(2)
        display.Context.Display(axes_ais, True)

        # ⚙️ إنشاء الشبكة
        display.DisplayGrid()
        grid_ais = getattr(display, "_grid_ais", None)

        # 🔒 تعطيل التفاعل
        if grid_ais:
            display.Context.Deactivate(grid_ais)
            # إلغاء التحديد والهوفر نهائيًا
            try:
                grid_ais.UnsetSelectionMode()
                grid_ais.SetHilightMode(-1)
            except Exception:
                pass

        display.Context.Deactivate(axes_ais)
        try:
            axes_ais.UnsetSelectionMode()
            axes_ais.SetHilightMode(-1)
        except Exception:
            pass

        # 🔧 تعطيل النظام التلقائي للاختيار
        display.Context.SetAutoActivateSelection(False)

        # 🧱 حفظهم بعد EraseAll
        display.persistent_items = [axes_ais, grid_ais]

        print("✅ الشبكة والمحاور الآن غير قابلة للتحديد أو التظليل (hover)")
        return axes_ais, grid_ais

    except Exception as e:
        print(f"⚠️ خطأ أثناء إعداد الشبكة والمحاور: {e}")
        return None, None



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
        setup_viewer_grid_and_axes(self.display)

        self.setup_fusion_environment()


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

    # ============================================================
    # 🎨 تهيئة الخلفية والشبكة بأسلوب Fusion (متوافق مع Viewer3d)
    # ============================================================
    def setup_fusion_environment(self):
        """تهيئة الخلفية والشبكة والمحاور بأسلوب Fusion (ثابتة في المشهد)."""
        from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
        from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax1
        from OCC.Core.AIS import AIS_Axis, AIS_Shape
        from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
        from OCC.Core.TopoDS import TopoDS_Compound
        from OCC.Core.BRep import BRep_Builder

        try:
            viewer = self.display.Viewer
            view = self.display.View
            ctx = self.display.Context

            # 🌄 خلفية رمادية متدرجة مثل Fusion
            top = Quantity_Color(0.95, 0.96, 0.97, Quantity_TOC_RGB)
            bottom = Quantity_Color(0.80, 0.82, 0.85, Quantity_TOC_RGB)
            view.SetBgGradientColors(top, bottom, True)
            viewer.SetDefaultLights()
            viewer.SetLightOn()
            print("[Fusion] ✅ الخلفية المتدرجة مفعلة.")

            # 🧹 تعطيل الشبكة الافتراضية
            try:
                viewer.DeactivateGrid()
            except Exception:
                pass

            # 🕸 إنشاء شبكة من خطوط BRep
            step = 25.0
            half_size = 500
            gray = Quantity_Color(0.82, 0.82, 0.82, Quantity_TOC_RGB)
            builder = BRep_Builder()
            comp = TopoDS_Compound()
            builder.MakeCompound(comp)

            n_lines = int(half_size // step)
            for i in range(-n_lines, n_lines + 1):
                y = i * step
                x = i * step
                e1 = BRepBuilderAPI_MakeEdge(gp_Pnt(-half_size, y, 0), gp_Pnt(half_size, y, 0)).Edge()
                e2 = BRepBuilderAPI_MakeEdge(gp_Pnt(x, -half_size, 0), gp_Pnt(x, half_size, 0)).Edge()
                builder.Add(comp, e1)
                builder.Add(comp, e2)

            grid_shape = AIS_Shape(comp)
            grid_shape.SetColor(gray)
            grid_shape.SetTransparency(0.85)
            self._fusion_grid = grid_shape  # حفظها كمُتغير دائم
            ctx.Display(self._fusion_grid, False)
            print("[Fusion] ✅ الشبكة مفعّلة.")

            # 🧭 إنشاء المحاور X/Y/Z وتخزينها
            red = Quantity_Color(1, 0, 0, Quantity_TOC_RGB)
            green = Quantity_Color(0, 1, 0, Quantity_TOC_RGB)
            blue = Quantity_Color(0, 0, 1, Quantity_TOC_RGB)

            x_axis = AIS_Axis(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)))
            y_axis = AIS_Axis(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)))
            z_axis = AIS_Axis(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)))
            x_axis.SetColor(red)
            y_axis.SetColor(green)
            z_axis.SetColor(blue)

            self._fusion_axes = [x_axis, y_axis, z_axis]
            for ax in self._fusion_axes:
                ctx.Display(ax, False)
            print("[Fusion] ✅ المحاور مفعّلة.")

            view.MustBeResized()
            view.Redraw()
            # 🧠 تغليف EraseAll الأصلي ليعيد عرض الشبكة والمحاور تلقائيًا
            if not hasattr(self.display, "_fusion_wrapped"):
                original_erase_all = self.display.EraseAll

                def erase_all_with_fusion():
                    """مسح كامل المشهد مع إعادة عرض الشبكة والمحاور بعده مباشرة."""
                    try:
                        # استدعاء المسح الأصلي
                        original_erase_all()
                        # إعادة عرض الشبكة والمحاور
                        if hasattr(self, "_fusion_grid"):
                            self.display.Context.Display(self._fusion_grid, False)
                        if hasattr(self, "_fusion_axes"):
                            for ax in self._fusion_axes:
                                self.display.Context.Display(ax, False)
                        self.display.View.Redraw()
                        print("[Fusion] ♻️ تمت إعادة عرض الشبكة والمحاور بعد EraseAll.")
                    except Exception as e:
                        print(f"[Fusion] ⚠ فشل أثناء إعادة عرض البيئة بعد EraseAll: {e}")

                # استبدال دالة EraseAll الأصلية بالنسخة الجديدة
                self.display.EraseAll = erase_all_with_fusion
                self.display._fusion_wrapped = True
                print("[Fusion] 🧩 تم تغليف EraseAll بنسخة Fusion.")


        except Exception as e:
            print(f"[⚠] Failed to setup Fusion environment: {e}")

    def redraw_fusion_environment(self):
        """إعادة عرض الشبكة والمحاور في حال تم مسحها بعد تحميل شكل."""
        try:
            if hasattr(self, "_fusion_grid"):
                self.display.Context.Display(self._fusion_grid, False)
            if hasattr(self, "_fusion_axes"):
                for ax in self._fusion_axes:
                    self.display.Context.Display(ax, False)
            self.display.View.Redraw()
            print("[Fusion] ♻️ تمت إعادة عرض الشبكة والمحاور.")
        except Exception as e:
            print(f"[Fusion] ⚠ فشل إعادة عرض الشبكة والمحاور: {e}")

    # استيرادات مكتبة PythonOCC الأساسية


















