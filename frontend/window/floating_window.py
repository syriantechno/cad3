from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QStackedWidget, QScrollArea, QPushButton,
                             QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit, QLabel, QWidget, QFrame, QListWidget,
                             QSizePolicy, QMessageBox, QFileDialog, QGridLayout)

from PyQt5.QtCore import Qt, QPoint, QTimer
from pathlib import Path
import os, json, shutil
from dxf_tools import load_dxf_file
from tools.database import ProfileDB
from frontend.style import TOOL_FLOATING_WINDOW_STYLE  # أو أي اسم للدالة اللي تستخدمها لتطبيق الستايل
from frontend.window.box_cut_window import BoxCutWindow
from frontend.window.profiles_manager_v2_window import create_profile_manager_page_v2
from frontend.window.hole_window import HoleWindow
from frontend.window.shape_manager_window import create_shape_manager_page
from frontend.window.gcode_generator_page import GCodeGeneratorPage
from frontend.window.gcode_workbench_page import GCodeWorkbenchPage



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
    print("[DEBUG] Entering create_shape_manager_page")

    tool_types = _load_tool_types()
    dialog = DraggableDialog(parent)
    dialog.setObjectName("ToolFloatingWindow")
    dialog.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    dialog.setMinimumWidth(380)
    dialog.setMaximumWidth(500)



    # 🟡 تأكد من وجود edit context
    dialog._edit_ctx = {
        "active": False,
        "pid": None,
        "orig_name": None,
        "orig_dxf": None,
        "orig_img": None
    }

    dialog.setStyleSheet(TOOL_FLOATING_WINDOW_STYLE)


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
    extrude_page = ExtrudeWindow(
        dialog,
        display=parent.display,
        shape_getter=lambda: parent.loaded_shape,
        shape_setter=lambda s: setattr(parent, "loaded_shape", s),
        op_browser=getattr(parent, "op_browser", None)
    )
    print("[DEBUG] Floating window is building pages...")

    profile_page = ProfileWindow(dialog, load_dxf=load_dxf_file, qtViewer3d=qtViewer3d)
    profiles_manager_v2_page = create_profile_manager_page_v2(parent, profile_page_getter=lambda: profile_page, stacked_getter=lambda: stacked )
    profiles_manager_page = ProfilesManagerWindow(dialog, load_dxf=load_dxf_file, parent_main=parent)
    tool_types = {
        "Drill": "frontend/icons/tools/drill.png",
        "Endmill": "frontend/icons/tools/endmill.png",
        "V-carve": "frontend/icons/tools/v.png",

    }
    tools_page = ToolsManagerWindow(tool_types)
  # لاحقًا تضيف الكول باك
    hole_page = HoleWindow(
        dialog,
        display=parent.display,
        shape_getter=lambda: parent.loaded_shape,
        shape_setter=lambda s: setattr(parent, "loaded_shape", s)
    )
    # 🧩 استيراد وتطبيق ستايل HoleWindow
    from frontend.style import HOLE_WINDOW_STYLE
    hole_page.setStyleSheet(HOLE_WINDOW_STYLE)

    box_cut_page = BoxCutWindow(
        dialog,
        display=parent.display,
        shape_getter=lambda: parent.loaded_shape,
        shape_setter=lambda s: setattr(parent, "loaded_shape", s)
    )
    print("[DEBUG] Shape Manager Page is being created")

    shape_page = create_shape_manager_page(parent)
    gcode_page = GCodeGeneratorPage(parent)
    # 🔗 تمرير مراجع التشغيل للنظام
    # ✅ ربط نافذة الجي كود مع المتصفح الحقيقي المستخدم في AlumCamGUI
    # 🔗 تمرير المراجع من النافذة الرئيسية
    if hasattr(parent, "op_browser"):
        gcode_page.operation_browser = parent.op_browser
    # ✅ تمرير معرف البروفايل النشط
    if hasattr(parent, "active_profile_id"):
        gcode_page.active_profile_id = parent.active_profile_id
    else:
        print("[DEBUG] No active_profile_id found in parent.")

    from frontend.window.gcode_simulator_page import GCodeSimulatorPage

    # داخل create_tool_window
    sim_page = GCodeSimulatorPage(parent)
    # 🧠 G-Code Workbench Page
    gcode_workbench_page = GCodeWorkbenchPage(parent.display, getattr(parent, "op_browser", None))

    # إضافة إلى الستاك
    stacked.addWidget(extrude_page)             # index 0
    stacked.addWidget(profile_page)             # index 1
    stacked.addWidget(profiles_manager_page)    # index 2
    stacked.addWidget(tools_page)               # index 3 ✅
    stacked.addWidget(profiles_manager_v2_page) # index 4 ✅
    stacked.addWidget(hole_page)                # index 5 🆕
    stacked.addWidget(box_cut_page)             # index 6 🆕
    stacked.addWidget(shape_page)               # index 7 🆕
    stacked.addWidget(gcode_page)               # index 8 🆕
    stacked.addWidget(sim_page)                 # index 9 🆕
    stacked.addWidget(gcode_workbench_page)                 # index 10 🆕


    # ✅ حفظ المراجع داخل الـ dialog
    dialog.extrude_page = extrude_page
    dialog.profile_page = profile_page
    dialog.profiles_manager_page = profiles_manager_page
    dialog.tools_page = tools_page
    dialog.profiles_manager_v2_page = profiles_manager_v2_page
    dialog.hole_page = hole_page
    dialog.box_cut_page = box_cut_page
    dialog.shape_page = shape_page
    dialog.gcode_page = gcode_page
    dialog.sim_page = sim_page
    dialog.gcode_workbench_page =gcode_workbench_page



    # أزرار أسفل
    bottom_layout = QHBoxLayout()
    bottom_layout.addStretch()
    shape_btn = QPushButton("Shape Cut")
    shape_btn.setObjectName("ShapeBtn")
    cancel_btn = QPushButton("Cancel")
    cancel_btn.setObjectName("CancelBtn")

    def handle_cancel():
        """تنظيف أي معاينة نشطة ثم إغلاق النافذة."""
        try:
            current_index = stacked.currentIndex()
            current_page = stacked.widget(current_index)

            # تنظيف AIS الخاصة بالمعاينة (مع التحقق من وجود Context)
            if hasattr(current_page, "display") and hasattr(current_page.display, "Context"):
                ctx = current_page.display.Context
                try:
                    # إزالة معاينات شائعة
                    if hasattr(current_page, "_hole_preview_ais") and current_page._hole_preview_ais:
                        ctx.Remove(current_page._hole_preview_ais, False)
                    if hasattr(current_page, "preview_actor") and current_page.preview_actor:
                        ctx.Remove(current_page.preview_actor, False)
                    # إزالة أبعاد المعاينة إن وُجدت (قائمة من AIS_InteractiveObjects)
                    if hasattr(current_page, "_preview_dim_shapes") and current_page._preview_dim_shapes:
                        for _ais in list(current_page._preview_dim_shapes):
                            try:
                                if _ais:
                                    ctx.Remove(_ais, False)
                            except Exception:
                                pass
                        current_page._preview_dim_shapes.clear()
                    ctx.UpdateCurrentViewer()
                    print(f"🧹 [Cancel] تمت إزالة المعاينة من الصفحة {current_index}.")
                except Exception as e:
                    print(f"⚠️ [Cancel] خطأ أثناء إزالة المعاينة: {e}")

            # تصفير مراجع المعاينة داخل الصفحة
            for name in ["_hole_preview_ais", "preview_actor", "preview_shape"]:
                if hasattr(current_page, name):
                    setattr(current_page, name, None)

        except Exception as e:
            print(f"⚠️ [Cancel] فشل في تنظيف الصفحة: {e}")
        finally:
            dialog.hide()
            print("✅ [Cancel] تم إغلاق النافذة بعد التنظيف.")

    cancel_btn.clicked.connect(handle_cancel)




    apply_btn = QPushButton("Apply")
    apply_btn.setObjectName("ApplyBtn")
    bottom_layout.addWidget(cancel_btn)
    bottom_layout.addWidget(apply_btn)
    main_layout.addLayout(bottom_layout)

    def handle_apply():
        """زر Apply العام لجميع الصفحات"""
        print("\n\n===== [DEBUG TRACK] handle_apply called =====")
        print("DEBUG -> parent:", parent)
        print("DEBUG -> has active_profile_name:", hasattr(parent, "active_profile_name"))
        if hasattr(parent, "active_profile_name"):
            print("DEBUG -> parent.active_profile_name =", getattr(parent, "active_profile_name"))

        idx = stacked.currentIndex()
        print(f"🟢 [Apply] Clicked on page index {idx}")

        # Extrude Page
        if idx == 0:
            try:
                print("🧱 [Apply] Running Extrude apply_extrude() safely...")
                dialog.extrude_page.apply_extrude()

                # 🟢 اجلب القيم الصحيحة من واجهة المستخدم
                distance_val = float(dialog.extrude_page.distance_input.text().strip() or 0)

                # 🧩 اربط العملية بالبروفايل الحالي
                profile_name = getattr(parent, "active_profile_name", None)
                if not profile_name:
                    QMessageBox.warning(dialog, "Extrude", "⚠️ الرجاء اختيار Profile أولاً.")
                    return

                # 🧱 أضف العملية إلى شجرة العمليات
                if hasattr(parent, "op_browser"):
                    parent.op_browser.add_extrude(profile_name, distance_val, axis="Y")

                dialog.hide()
                print(f"✅ [Apply] Extrude completed successfully for profile '{profile_name}', height={distance_val}")

            except Exception as e:
                QMessageBox.critical(dialog, "Extrude Error", str(e))
                print(f"🔥 [Apply] Extrude failed: {e}")

        # Profile Page
        elif idx == 1:
            try:
                prof = profile_page.get_profile_data()
                name = prof["name"]
                parent.active_profile_name = name
                print(f"✅ Active profile set to: {name}")

                if not name:
                    QMessageBox.information(dialog, "Profile", "Please enter profile Name.")
                    return
                src_dxf = prof["dxf"]
                if not src_dxf:
                    QMessageBox.information(dialog, "Profile", "Please choose a DXF file.")
                    return

                shape = load_dxf_file(src_dxf)
                if shape is None:
                    raise RuntimeError("Invalid DXF shape.")

                # حفظ في قاعدة البيانات/القرص (كما كان عندك)
                profile_dir = Path("profiles") / name
                profile_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_dxf, profile_dir / f"{name}.dxf")

                db = ProfileDB()
                db.add_profile(
                    name=name,
                    code=profile_page._p_code.text().strip(),
                    dimensions=profile_page._p_dims.text().strip(),
                    notes=profile_page._p_notes.text().strip(),
                    dxf_path=str(profile_dir / f"{name}.dxf"),
                    brep_path="",
                    image_path=""
                )

                if hasattr(parent, "op_browser"):
                    parent.op_browser.add_profile(name)

                QMessageBox.information(dialog, "Saved", "Profile saved successfully.")
                dialog.hide()
                print("✅ [Apply] Profile saved successfully.")
            except Exception as e:
                QMessageBox.critical(dialog, "Profile Error", str(e))
                print(f"🔥 [Apply] Profile failed: {e}")

        # Profiles Manager Page
        elif idx == 2:
            try:
                # ✅ الحصول على البروفايل المحدد من قائمة البروفايل مانجر
                selected_item = dialog.profiles_manager_page.list_widget.currentItem()
                if not selected_item:
                    QMessageBox.warning(dialog, "Profiles Manager", "⚠️ الرجاء اختيار بروفايل من القائمة.")
                    return

                profile_name = selected_item.text()
                parent.active_profile_name = profile_name
                print(f"✅ [Manager] Active profile set to: {profile_name}")
                print("✅ [DEBUG] Stored active_profile_name in parent:", profile_name)
                print("DEBUG parent id:", id(parent))
                # ✅ تحديث النافذة الرئيسية أيضاً
                from PyQt5.QtWidgets import QApplication
                from gui_fusion import AlumCamGUI
                for w in QApplication.topLevelWidgets():
                    if isinstance(w, AlumCamGUI):
                        w.active_profile_name = profile_name
                        print(f"✅ [GLOBAL] Profile '{profile_name}' registered in main window")
                        break

                QMessageBox.information(dialog, "Profile Manager", f"✅ تم تحميل البروفايل: {profile_name}")
                dialog.hide()

            except Exception as e:
                QMessageBox.critical(dialog, "Profile Manager Error", str(e))
                print(f"🔥 [Profile Manager] Failed to set active profile: {e}")



        # Hole Page
        elif idx == 5:
            try:
                vals = dialog.hole_page._get_values()
                if vals is None or len(vals) < 7:
                    QMessageBox.warning(dialog, "Hole", "⚠️ قيم غير مكتملة أو فارغة.")
                    return
                x, y, z, dia, depth, _, axis = vals

                # نفّذ الحفر في العارض
                result = dialog.hole_page.apply_hole()
                if result and hasattr(parent, "op_browser"):
                    profile_name = getattr(parent, "active_profile_name", "Unnamed")
                    parent.op_browser.add_hole(profile_name, (x, y, z), dia, depth, axis, tool=result.get("tool"))
                    print(f"✅ [OPS] Hole added to browser for profile '{profile_name}'")
                else:
                    print("⚠️ Hole not added (no result returned or no op_browser).")

                dialog.hide()
                print("✅ [Apply] Hole executed successfully and added to operation tree.")
            except Exception as e:
                QMessageBox.critical(dialog, "Hole Error", str(e))
                print(f"🔥 [Apply] Hole failed: {e}")

        # Shape Page (لو عندك)
        elif idx == 7:
            try:
                print("📦 [Apply] Shape library OK clicked.")
                dialog.shape_page._on_ok_clicked()
                dialog.hide()
                print("✅ [Apply] Shape loaded successfully.")
            except Exception as e:
                QMessageBox.critical(dialog, "Shape Error", str(e))
                print(f"🔥 [Apply] Shape failed: {e}")
        # Tools Manager Page
        elif idx == 3:  # Tools Manager page index
            try:
                print("🧰 [Apply] Tool Manager apply_tool() called.")
                result = dialog.tools_page.apply_tool()
                if result:
                    QMessageBox.information(dialog, "Tool Manager", "✅ Tool saved successfully.")
                    dialog.hide()
                    print("✅ [Apply] Tool saved via Tool Manager.")
                else:
                    print("⚠️ [Apply] Tool save returned False or failed.")
            except Exception as e:
                QMessageBox.critical(dialog, "Tool Error", f"Error while saving tool:\n{e}")
                print(f"🔥 [Apply] Tool Manager failed: {e}")


        else:
            QMessageBox.information(dialog, "Info", "No apply action for this page yet.")
            print(f"[Apply] No handler for page index {idx}.")

    apply_btn.clicked.connect(handle_apply)

    def show_page(index: int):
        count = stacked.count()
        print(f"[DEBUG] show_page called with index={index}, total={count}")
        if index < 0 or index >= count:
            print("[ERROR] Invalid stacked index:", index)
            return

        stacked.setCurrentIndex(index)

        if index == 2:
            profiles_manager_page.refresh_profiles_list()
            header.setText("Profiles Manager")
        elif index == 1:
            header.setText("Profile")
        elif index == 3:
            header.setText("Tools Manager")
        elif index == 5:
            header.setText("Hole")
        elif index == 7:
            header.setText("Shape")
        elif index == 8:
            header.setText("G-Code")
        elif index == 9:
            header.setText("sim page")
        elif index == 10:
            header.setText("gcode workbench page")
        else:
            header.setText("Extrude")
        dialog.show()
        dialog.raise_()

    dialog.stack = stacked
    dialog.show_page = show_page

    return dialog, show_page

