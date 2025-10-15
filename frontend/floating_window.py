from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QStackedWidget, QScrollArea,
    QPushButton, QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit, QLabel,
    QWidget, QFrame, QListWidget, QSizePolicy, QMessageBox, QFileDialog, QGridLayout
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QPoint, QTimer
from pathlib import Path
import os, json, shutil

# ---- Project imports ----
from dxf_tools import load_dxf_file
from tools.database import ProfileDB

try:
    from OCC.Display.qtDisplay import qtViewer3d
    from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
    from OCC.Core.Prs3d import Prs3d_LineAspect
    from OCC.Core.Aspect import Aspect_TOL_SOLID
except Exception:
    qtViewer3d = None  # يسمح بتحميل الملف بدون بيئة OCC أثناء التطوير


# ======================================================================
# نافذة عائمة قابلة للسحب
# ======================================================================
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


# ======================================================================
# دوال مساعدة
# ======================================================================
def _safe_exists(p):
    try:
        return p and Path(p).exists()
    except Exception:
        return False

def _setup_viewer_colors(display):
    """يضبط خلفية رمادية فاتحة وحدود سوداء للعارض (دون تدرج)."""
    try:
        if display is None:
            return

        # رمادي فاتح للخلفية (بدون تدرج)
        light_gray = Quantity_Color(0.85, 0.85, 0.85, Quantity_TOC_RGB)
        black = Quantity_Color(0.0, 0.0, 0.0, Quantity_TOC_RGB)

        view = display.View

        # ❌ أولاً: ألغِ أي تدرج موجود
        view.SetBgGradientStyle(0)  # 0 = لون واحد فقط
        view.SetBackgroundColor(light_gray)  # خلفية موحدة

        # تحديث الحجم والرسم
        view.MustBeResized()
        view.Redraw()

        # تفعيل الحدود السوداء حول الأشكال
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


# ======================================================================
# صفحة: Extrude
# ======================================================================
def create_extrude_page():
    page = QWidget()
    layout = QFormLayout(page)
    axis_combo = QComboBox(); axis_combo.addItems(["X", "Y", "Z"])
    distance_spin = QDoubleSpinBox(); distance_spin.setRange(1, 9999); distance_spin.setValue(100)
    layout.addRow("Axis:", axis_combo)
    layout.addRow("Distance (mm):", distance_spin)
    page._axis_combo = axis_combo
    page._distance_spin = distance_spin
    return page


# ======================================================================
# صفحة: إنشاء بروفايل جديد
# ======================================================================
def create_profile_page():
    page = QWidget()
    form = QFormLayout(page)
    p_name = QLineEdit(); p_code = QLineEdit(); p_dims = QLineEdit(); p_notes = QLineEdit()
    dxf_path_edit = QLineEdit(); dxf_path_edit.setReadOnly(True)
    choose_btn = QPushButton("Choose DXF")

    # Preview
    small_display = None
    if qtViewer3d is not None:
        preview_container = QWidget()
        preview_container.setMinimumHeight(250)
        preview_layout = QVBoxLayout(preview_container)
        viewer = qtViewer3d(preview_container)
        viewer.setMinimumSize(320, 240)
        preview_layout.addWidget(viewer)

        small_display = viewer._display

        # 🟡 ضبط الألوان فورًا بعد إنشاء العارض
        _setup_viewer_colors(small_display)

        # 🟡 تأكيد ضبط الألوان بعد 200ms للتأكد أنها لم تُستبدل افتراضيًا
        QTimer.singleShot(200, lambda: _setup_viewer_colors(small_display))

    else:
        preview_container = QLabel("OCC Preview not available.")
        preview_container.setStyleSheet("color:#666;")

    form.addRow("Name:", p_name)
    form.addRow("Code:", p_code)
    form.addRow("Dimensions:", p_dims)
    form.addRow("Notes:", p_notes)
    form.addRow("DXF File:", dxf_path_edit)
    form.addRow("", choose_btn)
    form.addRow("Preview:", preview_container)

    selected_shape = {"shape": None, "src": None}

    def on_choose_dxf():
        file_name, _ = QFileDialog.getOpenFileName(page, "Select DXF", "", "DXF Files (*.dxf)")
        if not file_name: return
        dxf_path_edit.setText(file_name)
        try:
            shp = load_dxf_file(file_name)
        except Exception as ex:
            QMessageBox.warning(page, "DXF", f"Failed to import dxf_tools:\n{ex}")
            return
        if shp is None:
            QMessageBox.warning(page, "DXF", "Failed to parse DXF file.")
            return
        selected_shape["shape"] = shp
        selected_shape["src"] = file_name
        if small_display:
            small_display.EraseAll()
            small_display.DisplayShape(shp, update=True)
            small_display.FitAll()
        print(f"[DEBUG] DXF selected: {file_name}")

    choose_btn.clicked.connect(on_choose_dxf)

    # attach to page for access
    page._p_name = p_name
    page._p_code = p_code
    page._p_dims = p_dims
    page._p_notes = p_notes
    page._dxf_path_edit = dxf_path_edit
    page._small_display = small_display
    page._selected_shape = selected_shape
    return page


# ======================================================================
# صفحة: مدير البروفايلات (القديم - شبكة Load)
# ======================================================================
def create_profile_manager_page(dialog_parent):
    page = QWidget()
    layout = QVBoxLayout(page)
    scroll = QScrollArea(); scroll.setWidgetResizable(True)
    layout.addWidget(scroll)
    container = QWidget(); scroll.setWidget(container)
    grid = QGridLayout(container)
    db = ProfileDB()

    def _make_loader(dxf_path_local, profile_name):
        def _loader():
            main_window = dialog_parent.parent()
            try:
                shape = load_dxf_file(Path(dxf_path_local))
                main_window.display.EraseAll()
                main_window.display.DisplayShape(shape, update=True)
                main_window.loaded_shape = shape
                main_window.display.FitAll()
                if hasattr(main_window, "op_browser"):
                    main_window.op_browser.add_profile(profile_name)
            except Exception as e:
                QMessageBox.critical(page, "Load Error", str(e))
        return _loader

    def refresh_profiles_list():
        while grid.count():
            item = grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        profiles = db.list_profiles()
        if not profiles:
            grid.addWidget(QLabel("لا توجد بروفايلات."), 0, 0); return
        for row_idx, prof in enumerate(profiles):
            pid, name, code, dims, notes, dxf_path, brep, img, created = prof
            img_label = QLabel(); img_label.setFixedSize(64, 64); img_label.setFrameShape(QFrame.Box)
            if _safe_exists(img):
                pix = QPixmap(img).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_label.setPixmap(pix)
            else:
                img_label.setText("No\nImage"); img_label.setAlignment(Qt.AlignCenter)
            text = QLabel(f"<b>{name}</b><br>Code: {code}<br>Dims: {dims}<br><i>{notes}</i>")
            text.setWordWrap(True)
            load_btn = QPushButton("Load")
            load_btn.clicked.connect(_make_loader(dxf_path, name))
            grid.addWidget(img_label, row_idx, 0)
            grid.addWidget(text, row_idx, 1)
            grid.addWidget(load_btn, row_idx, 2)

    return page, refresh_profiles_list


# ======================================================================
# 🟡 صفحة: مدير البروفايلات (الجديدة - قائمة يمين + تفاصيل يسار)
# ======================================================================
def create_profile_manager_page_v2(parent):
    """
    تصميم جديد: قائمة أسماء على اليمين - تفاصيل وصورة على اليسار
    """
    page = QWidget()
    root = QHBoxLayout(page)
    root.setContentsMargins(10, 10, 10, 10)
    root.setSpacing(14)

    # ---------- اليمين: قائمة الأسماء ----------
    profile_list = QListWidget()
    profile_list.setMinimumWidth(200)
    profile_list.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    root.addWidget(profile_list, alignment=Qt.AlignRight)

    # ---------- اليسار: تفاصيل ----------
    left_container = QWidget()
    left_layout = QVBoxLayout(left_container)
    left_layout.setAlignment(Qt.AlignTop)
    left_layout.setSpacing(10)

    img_label = QLabel()
    img_label.setFixedSize(280, 280)
    img_label.setAlignment(Qt.AlignCenter)
    img_label.setStyleSheet("border: 1px solid #bbb; background: #fafafa;")
    left_layout.addWidget(img_label)

    lbl_name = QLabel("Name: -")
    lbl_code = QLabel("Code: -")
    lbl_size = QLabel("Size: -")
    lbl_desc = QLabel("Description: -")

    left_layout.addWidget(lbl_name)
    left_layout.addWidget(lbl_code)
    left_layout.addWidget(lbl_size)
    left_layout.addWidget(lbl_desc)

    ok_btn = QPushButton("OK")
    ok_btn.setStyleSheet("background:#0078d4; color:white; font-weight:bold;")
    left_layout.addWidget(ok_btn)

    root.addWidget(left_container, alignment=Qt.AlignLeft)

    # ---------- البيانات ----------
    db = ProfileDB()
    profiles = []

    def refresh_profiles_list_v2():
        nonlocal profiles
        profile_list.clear()
        profiles = db.list_profiles()
        for prof in profiles:
            profile_list.addItem(prof[1])  # الاسم
        print("[DEBUG] Profile list refreshed")

    # أول تحميل
    refresh_profiles_list_v2()

    selected = {"dxf": None}

    def on_select(index):
        row = index
        if row < 0 or row >= len(profiles): return
        pid, name, code, dims, notes, dxf_path, brep, img, created = profiles[row]
        lbl_name.setText(f"Name: {name}")
        lbl_code.setText(f"Code: {code}")
        lbl_size.setText(f"Size: {dims}")
        lbl_desc.setText(f"Description: {notes}")
        if _safe_exists(img):
            pix = QPixmap(img).scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_label.setPixmap(pix)
        else:
            img_label.clear()
        selected["dxf"] = dxf_path
        print(f"[DEBUG] Selected profile: {name}")

    profile_list.currentRowChanged.connect(on_select)

    def on_ok():
        dxf = selected.get("dxf")
        if not _safe_exists(dxf):
            QMessageBox.warning(page, "Profile", "No valid DXF selected.")
            return
        try:
            print(f"[DEBUG] Loading profile from: {dxf}")
            shape = load_dxf_file(Path(dxf))
            if shape is None or shape.IsNull():
                raise RuntimeError("DXF returned no shape.")

            main_window = parent
            if not hasattr(main_window, "display") or main_window.display is None:
                raise RuntimeError("Main display not initialized.")

            main_window.display.EraseAll()
            main_window.display.DisplayShape(shape, update=True)
            main_window.loaded_shape = shape
            main_window.display.FitAll()

            # إذا كان لديك op_browser
            if hasattr(main_window, "op_browser"):
                profile_name = Path(dxf).stem
                main_window.op_browser.add_profile(profile_name)
                main_window.op_browser.expandAll()
                main_window.op_browser.update()
                main_window.op_browser.repaint()
                print(f"[DEBUG] Added profile to browser: {profile_name}")

        except Exception as e:
            print(f"[ERROR] Failed to load profile: {e}")
            QMessageBox.critical(page, "Load Error", str(e))

    ok_btn.clicked.connect(on_ok)

    return page


# ======================================================================
# نافذة العائمة الرئيسية: تُجمّع كل الصفحات وتنسّقها
# ======================================================================
def create_tool_window(parent):
    # تحميل أنواع الأدوات من JSON
    tool_types = _load_tool_types()

    dialog = DraggableDialog(parent)
    dialog.setObjectName("ToolFloatingWindow")
    dialog.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    dialog.setFixedWidth(600)

    dialog.setStyleSheet("""
        QDialog#ToolFloatingWindow {
            background-color: #ffffff;
            border: 1px solid #b4b4b4;
            border-radius: 8px;
        }
        QLabel { font-size: 13px; color: #333; }
        QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit {
            min-height: 28px; font-size: 13px; border: 1px solid #ccc;
            border-radius: 4px; background: white;
        }
        QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QLineEdit:focus {
            border: 1px solid #0078d4;
        }
        QPushButton {
            min-height: 30px; min-width: 100px; font-size: 13px; border-radius: 4px;
        }
        QPushButton#ApplyBtn {
            background-color: #0078d4; color: white;
        }
        QPushButton#ApplyBtn:hover { background-color: #005ea2; }
        QPushButton#CancelBtn {
            background-color: #e0e0e0; color: black;
        }
        QPushButton#CancelBtn:hover { background-color: #cacaca; }
        QFrame#line { background:#dcdcdc; height:1px; }
    """)

    # ====== Layout ======
    main_layout = QVBoxLayout(dialog)
    main_layout.setContentsMargins(10, 10, 10, 10)
    main_layout.setSpacing(8)

    # ====== Header ======
    header = QLabel("Tool Options")
    header.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 4px;")
    main_layout.addWidget(header)

    line = QFrame()
    line.setObjectName("line")
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    main_layout.addWidget(line)

    # ====== Stack ======
    stacked = QStackedWidget(dialog)
    main_layout.addWidget(stacked)

    # ====== الصفحات ======
    extrude_page = create_extrude_page()  # index 0
    profile_page = create_profile_page()  # index 1
    manager_page_old, refresh_profiles_list = create_profile_manager_page(dialog)  # index 2 (القديم)
    manager_page_v2 = create_profile_manager_page_v2(parent)  # index 3 (الجديد)

    # ======================================================================
    # صفحة: أدوات القطع (Tools Manager)
    # ======================================================================
    def create_tools_manager_page(tool_types, open_add_type_dialog_cb):
        """
        صفحة إدارة أدوات القطع.
        - tool_types: dict من أنواع الأدوات (محمّلة من JSON)
        - open_add_type_dialog_cb: callback لفتح نافذة إضافة نوع أداة جديدة
        """
        page = QWidget()
        layout = QFormLayout(page)

        name_input = QLineEdit()
        dia_input = QDoubleSpinBox();
        dia_input.setSuffix(" mm");
        dia_input.setMaximum(100)
        length_input = QDoubleSpinBox();
        length_input.setSuffix(" mm");
        length_input.setMaximum(200)
        type_combo = QComboBox();
        type_combo.setEditable(True);
        type_combo.addItems(tool_types.keys())

        add_type_btn = QPushButton("➕")
        add_type_btn.setFixedWidth(30)

        # صف لاختيار النوع مع زر إضافة
        type_row = QHBoxLayout()
        type_row.addWidget(type_combo)
        type_row.addWidget(add_type_btn)

        layout.addRow("Tool Name:", name_input)
        layout.addRow("Diameter:", dia_input)
        layout.addRow("Length:", length_input)
        layout.addRow("Type:", type_row)

        rpm_input = QSpinBox();
        rpm_input.setMaximum(40000)
        steps_input = QSpinBox();
        steps_input.setMaximum(100)
        layout.addRow("Default RPM:", rpm_input)
        layout.addRow("Default Steps:", steps_input)

        image_label = QLabel("No image")
        image_label.setFixedSize(120, 120)
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setStyleSheet("border: 1px solid gray;")
        layout.addRow("Preview:", image_label)

        def update_tool_image(tool_type_name):
            img_path = tool_types.get(tool_type_name)
            if img_path and Path(img_path).exists():
                pix = QPixmap(str(img_path)).scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                image_label.setPixmap(pix)
            else:
                image_label.setText("No image")
                image_label.setPixmap(QPixmap())

        def on_type_changed(text):
            update_tool_image(text)

        type_combo.currentTextChanged.connect(on_type_changed)
        add_type_btn.clicked.connect(lambda: open_add_type_dialog_cb(type_combo, update_tool_image))

        # attach vars to page for later use if needed
        page._name_input = name_input
        page._dia_input = dia_input
        page._length_input = length_input
        page._type_combo = type_combo
        page._rpm_input = rpm_input
        page._steps_input = steps_input

        return page

    # لاحقاً: صفحة الأدوات
    def _open_add_type_dialog(type_combo_widget, update_tool_image_cb):
        dlg = AddToolTypeDialog(tool_types, dialog)
        if dlg.exec_():
            type_combo_widget.clear()
            type_combo_widget.addItems(tool_types.keys())
            type_combo_widget.setCurrentText(dlg.name_input.text().strip())
            update_tool_image_cb(type_combo_widget.currentText())

    tools_page = create_tools_manager_page(tool_types, _open_add_type_dialog)  # index 4

    # إضافة الصفحات إلى stacked
    stacked.addWidget(extrude_page)  # 0
    stacked.addWidget(profile_page)  # 1
    stacked.addWidget(manager_page_old)  # 2
    stacked.addWidget(manager_page_v2)  # 3 ✅
    stacked.addWidget(tools_page)  # 4

    # ====== أزرار أسفل ======
    bottom_layout = QHBoxLayout()
    bottom_layout.addStretch()
    cancel_btn = QPushButton("Cancel");
    cancel_btn.setObjectName("CancelBtn")
    apply_btn = QPushButton("Apply");
    apply_btn.setObjectName("ApplyBtn")
    bottom_layout.addWidget(cancel_btn)
    bottom_layout.addWidget(apply_btn)
    main_layout.addLayout(bottom_layout)

    cancel_btn.clicked.connect(dialog.hide)

    # قاعدة البيانات
    db = ProfileDB()

    # ====== منطق زر Apply ======
    def handle_apply():
        idx = stacked.currentIndex()

        # Extrude Page
        if idx == 0:
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

        # Profile Page (حفظ بروفايل جديد)
        elif idx == 1:
            name = profile_page._p_name.text().strip()
            if not name:
                QMessageBox.information(dialog, "Profile", "Please enter profile Name.")
                return
            src_dxf = profile_page._dxf_path_edit.text().strip()
            if not src_dxf:
                QMessageBox.information(dialog, "Profile", "Please choose a DXF file.")
                return
            try:
                shape = load_dxf_file(src_dxf)
                if shape is None:
                    raise RuntimeError("Invalid DXF shape.")
                # snapshot
                small_display = profile_page._small_display
                if small_display is not None:
                    small_display.EraseAll()
                    small_display.DisplayShape(shape, update=True)
                    small_display.FitAll()
                # مسارات الحفظ
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

        # Profiles Manager (القديم)
        elif idx == 2:
            QMessageBox.information(dialog, "Profiles", "Use Load button on each profile.")
            return

        # Profiles Manager v2 → لا حاجة لـ Apply، لأن زر OK داخل الصفحة
        elif idx == 3:
            QMessageBox.information(dialog, "Profiles", "Select profile and press OK.")
            return

        # Tools Page
        elif idx == 4:
            QMessageBox.information(dialog, "Tools", "Save Tool not implemented.")
            return

    apply_btn.clicked.connect(handle_apply)

    # ====== التنقل بين الصفحات ======
    def show_page(index: int):
        stacked.setCurrentIndex(index)
        if index == 2:
            refresh_profiles_list()
            header.setText("Profiles Manager (old)")
        elif index == 3:
            header.setText("Profiles Manager (v2)")
            manager_page_v2.refresh_profiles_list_v2()
        elif index == 1:
            header.setText("Profile")
        elif index == 4:
            header.setText("Tools Manager")
        else:
            header.setText("Extrude")
        dialog.show()
        dialog.raise_()

    return dialog, show_page
