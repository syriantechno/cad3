# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QStackedWidget, QScrollArea,
    QPushButton, QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit, QLabel,
    QWidget, QFrame, QListWidget, QSizePolicy, QMessageBox, QFileDialog
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QPoint, QTimer
from pathlib import Path
import os, json, shutil

# ---- مشروعك ----
from dxf_tools import load_dxf_file
from tools.database import ProfileDB

# OCC (بيئة العرض)
try:
    from OCC.Display.qtDisplay import qtViewer3d
    from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
    from OCC.Core.Prs3d import Prs3d_LineAspect
    from OCC.Core.Aspect import Aspect_TOL_SOLID
except Exception:
    qtViewer3d = None  # يسمح بتشغيل الواجهة بدون OCC أثناء التطوير
    Quantity_Color = None
    Quantity_TOC_RGB = None
    Prs3d_LineAspect = None
    Aspect_TOL_SOLID = None


# ======================================================================
# نافذة عائمة قابلة للسحب
# ======================================================================
class DraggableDialog(QDialog):
    """Dialog بدون شريط عنوان وقابل للسحب."""
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
    """
    يضبط خلفية رمادي فاتح وحدود سوداء للعارض (بدون تدرج).
    نُعيد النداء مرتين عادة لضمان ثبات الإعدادات بعد Resize/Redraw.
    """
    try:
        if display is None or Quantity_Color is None:
            return

        light_gray = Quantity_Color(0.85, 0.85, 0.85, Quantity_TOC_RGB)
        black = Quantity_Color(0.0, 0.0, 0.0, Quantity_TOC_RGB)

        view = display.View
        view.SetBgGradientStyle(0)            # لون واحد
        view.SetBackgroundColor(light_gray)   # خلفية رمادي فاتح
        view.MustBeResized()
        view.Redraw()

        drawer = display.Context.DefaultDrawer()
        drawer.SetFaceBoundaryDraw(True)
        drawer.SetFaceBoundaryAspect(Prs3d_LineAspect(black, Aspect_TOL_SOLID, 1.0))
        display.Context.UpdateCurrentViewer()
        view.Redraw()

        print("[DEBUG] Viewer background set to light gray with black edges.")
    except Exception as e:
        print(f"[WARN] _setup_viewer_colors failed: {e}")


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
    layout.setLabelAlignment(Qt.AlignLeft)
    layout.setFormAlignment(Qt.AlignTop)

    axis_combo = QComboBox()
    axis_combo.addItems(["X", "Y", "Z"])
    distance_spin = QDoubleSpinBox()
    distance_spin.setRange(1, 9999)
    distance_spin.setValue(100)

    layout.addRow("Axis:", axis_combo)
    layout.addRow("Distance (mm):", distance_spin)

    page._axis_combo = axis_combo
    page._distance_spin = distance_spin
    return page


# ======================================================================
# صفحة: إنشاء/حفظ بروفايل جديد + معاينة
# ======================================================================
def create_profile_page():
    page = QWidget()
    form = QFormLayout(page)
    form.setLabelAlignment(Qt.AlignLeft)
    form.setFormAlignment(Qt.AlignTop)
    form.setHorizontalSpacing(12)
    form.setVerticalSpacing(8)

    p_name = QLineEdit()
    p_code = QLineEdit()
    p_dims = QLineEdit()
    p_notes = QLineEdit()

    dxf_path_edit = QLineEdit()
    dxf_path_edit.setReadOnly(True)
    choose_btn = QPushButton("Choose DXF")

    # عارض معاينة صغير
    small_display = None
    if qtViewer3d is not None:
        preview_container = QWidget()
        preview_container.setMinimumHeight(250)
        preview_container.setMaximumHeight(300)
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 6, 0, 6)
        viewer = qtViewer3d(preview_container)
        viewer.setMinimumSize(320, 240)
        preview_layout.addWidget(viewer)
        small_display = viewer._display

        # ضبط الألوان فورًا ثم تأكيد بعد 200ms
        _setup_viewer_colors(small_display)
        QTimer.singleShot(200, lambda: _setup_viewer_colors(small_display))
    else:
        preview_container = QLabel("OCC Preview not available in this environment.")
        preview_container.setStyleSheet("color:#666;")

    # عناصر الصفحة
    form.addRow("Name:", p_name)
    form.addRow("Code:", p_code)
    form.addRow("Dimensions:", p_dims)
    form.addRow("Notes:", p_notes)
    form.addRow("DXF File:", dxf_path_edit)
    form.addRow("", choose_btn)
    form.addRow(QLabel("Preview:"), preview_container)

    # حالة داخلية
    selected_shape = {"shape": None, "src": None}

    def on_choose_dxf():
        file_name, _ = QFileDialog.getOpenFileName(page, "Select DXF", "", "DXF Files (*.dxf)")
        if not file_name:
            return
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

        # عرض المعاينة بالأسود ومركزة
        try:
            if small_display is not None and Quantity_Color is not None:
                black = Quantity_Color(0.0, 0.0, 0.0, Quantity_TOC_RGB)
                small_display.EraseAll()
                small_display.DisplayShape(shp, color=black, update=True)
                small_display.FitAll()
                try:
                    small_display.View.ZFitAll()
                    small_display.View.SetZSize(0.9)
                except Exception:
                    pass
                small_display.View.Redraw()
        except Exception as e:
            QMessageBox.warning(page, "Preview", f"Failed to display preview:\n{e}")

        print(f"[DEBUG] DXF selected: {file_name}")

    choose_btn.clicked.connect(on_choose_dxf)

    # خزن الحقول للوصول من create_tool_window
    page._p_name = p_name
    page._p_code = p_code
    page._p_dims = p_dims
    page._p_notes = p_notes
    page._dxf_path_edit = dxf_path_edit
    page._small_display = small_display
    page._selected_shape = selected_shape
    return page


# ======================================================================
# صفحة: مدير البروفايلات (الجديدة - قائمة يمين + تفاصيل يسار + صورة + OK)
# ======================================================================
def create_profile_manager_page_v2(parent):
    """
    تصميم جديد:
    - يمين: قائمة أسماء البروفايلات (QListWidget)
    - يسار: صورة + تفاصيل + زر OK لتحميل البروفايل على العارض الرئيسي
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

    image_label = QLabel()
    image_label.setFixedSize(220, 220)
    image_label.setAlignment(Qt.AlignCenter)
    image_label.setStyleSheet("border: 1px solid #bbb; background: #f5f5f5;")
    left_layout.addWidget(image_label)

    lbl_name = QLabel("Name: —")
    lbl_code = QLabel("Code: —")
    lbl_size = QLabel("Size: —")
    lbl_desc = QLabel("Description: —")

    for w in (lbl_name, lbl_code, lbl_size, lbl_desc):
        w.setWordWrap(True)
        left_layout.addWidget(w)

    ok_btn = QPushButton("OK")
    ok_btn.setStyleSheet("background:#0078d4; color:white; font-weight:bold;")
    left_layout.addWidget(ok_btn)

    root.addWidget(left_container, alignment=Qt.AlignLeft)

    # ---------- تخزين مكونات الصفحة ----------
    page.profile_list = profile_list
    page.image_label = image_label
    page.lbl_name = lbl_name
    page.lbl_code = lbl_code
    page.lbl_size = lbl_size
    page.lbl_desc = lbl_desc
    page.selected = {"dxf": None}

    # ---------- دالة التحديث ----------
    def refresh_profiles_list_v2():
        """تحديث قائمة الأسماء من قاعدة البيانات (إعادة فتح الاتصال كل مرة)."""
        page.profile_list.clear()
        db_local = ProfileDB()
        profiles = db_local.list_profiles() or []
        page.profiles = profiles  # خزنها على الصفحة

        for prof in profiles:
            # prof = (id, name, code, dims, notes, dxf_path, brep_path, img_path, created)
            page.profile_list.addItem(prof[1])

        print("[DEBUG] Profile list refreshed (v2). count =", len(profiles))

    page.refresh_profiles_list_v2 = refresh_profiles_list_v2

    # ---------- اختيار عنصر ----------
    def on_select(index):
        if not hasattr(page, "profiles") or not page.profiles:
            return
        row = index
        if row < 0 or row >= len(page.profiles):
            return

        pid, name, code, dims, notes, dxf_path, brep, img, created = page.profiles[row]
        page.lbl_name.setText(f"Name: {name or '—'}")
        page.lbl_code.setText(f"Code: {code or '—'}")
        page.lbl_size.setText(f"Size: {dims or '—'}")
        page.lbl_desc.setText(f"Description: {notes or '—'}")

        if _safe_exists(img):
            pix = QPixmap(img).scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            page.image_label.setPixmap(pix)
        else:
            page.image_label.setPixmap(QPixmap())

        page.selected["dxf"] = dxf_path
        print(f"[DEBUG] Selected profile: {name}  dxf={dxf_path}")

    profile_list.currentRowChanged.connect(on_select)

    # ---------- زر OK: تحميل على العارض الرئيسي ----------
    def on_ok():
        dxf = page.selected.get("dxf")
        if not _safe_exists(dxf):
            QMessageBox.warning(page, "Profile", "No valid DXF selected.")
            return
        try:
            shape = load_dxf_file(Path(dxf))
            if shape is None:
                raise RuntimeError("DXF returned no shape.")

            main_window = parent
            if not hasattr(main_window, "display") or main_window.display is None:
                raise RuntimeError("Main display not initialized.")

            display = main_window.display
            display.EraseAll()

            if Quantity_Color is not None:
                black = Quantity_Color(0.0, 0.0, 0.0, Quantity_TOC_RGB)
                display.DisplayShape(shape, color=black, update=True)
            else:
                display.DisplayShape(shape, update=True)

            main_window.loaded_shape = shape
            display.FitAll()
            if hasattr(display, "View") and display.View is not None:
                try:
                    display.View.ZFitAll()
                    display.View.SetZSize(0.9)
                    display.View.Redraw()
                except Exception as e:
                    print("[WARN] View adjust failed:", e)

            # لو عندك متصفح عمليات
            if hasattr(main_window, "op_browser") and main_window.op_browser:
                profile_name = Path(dxf).stem
                main_window.op_browser.add_profile(profile_name)
                main_window.op_browser.expandAll()
                main_window.op_browser.update()
                main_window.op_browser.repaint()
                print(f"[DEBUG] Added profile to browser: {profile_name}")

            print(f"[DEBUG] Loaded profile from {dxf}")

        except Exception as e:
            QMessageBox.critical(page, "Error", f"Failed to load DXF:\n{e}")

    ok_btn.clicked.connect(on_ok)

    # أول تعبئة
    refresh_profiles_list_v2()

    return page


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
    layout.setLabelAlignment(Qt.AlignLeft)
    layout.setFormAlignment(Qt.AlignTop)

    name_input = QLineEdit()
    dia_input = QDoubleSpinBox(); dia_input.setSuffix(" mm"); dia_input.setMaximum(100)
    length_input = QDoubleSpinBox(); length_input.setSuffix(" mm"); length_input.setMaximum(200)
    type_combo = QComboBox(); type_combo.setEditable(True); type_combo.addItems(tool_types.keys())

    add_type_btn = QPushButton("➕"); add_type_btn.setFixedWidth(30)
    type_row = QHBoxLayout(); type_row.addWidget(type_combo); type_row.addWidget(add_type_btn)

    rpm_input = QSpinBox(); rpm_input.setMaximum(40000)
    steps_input = QSpinBox(); steps_input.setMaximum(100)

    image_label = QLabel("No image")
    image_label.setFixedSize(120, 120)
    image_label.setAlignment(Qt.AlignCenter)
    image_label.setStyleSheet("border: 1px solid gray;")

    layout.addRow("Tool Name:", name_input)
    layout.addRow("Diameter:", dia_input)
    layout.addRow("Length:", length_input)
    layout.addRow("Type:", type_row)
    layout.addRow("Default RPM:", rpm_input)
    layout.addRow("Default Steps:", steps_input)
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

    # تعيين صورة أولية إن وجدت
    if type_combo.currentText():
        update_tool_image(type_combo.currentText())

    # attach vars to page عند الحاجة
    page._name_input = name_input
    page._dia_input = dia_input
    page._length_input = length_input
    page._type_combo = type_combo
    page._rpm_input = rpm_input
    page._steps_input = steps_input

    return page


# ======================================================================
# نافذة: إضافة نوع أداة (مع صورة)
# ======================================================================
class AddToolTypeDialog(QDialog):
    def __init__(self, tool_types: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Tool Type")
        self.setFixedSize(300, 260)
        self.tool_types = tool_types
        self.image_path = ""

        layout = QVBoxLayout(self)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Tool type name")
        layout.addWidget(self.name_input)

        self.image_label = QLabel("No image")
        self.image_label.setFixedSize(120, 120)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid gray;")
        layout.addWidget(self.image_label)

        choose_btn = QPushButton("Choose Image")
        choose_btn.clicked.connect(self.choose_image)
        layout.addWidget(choose_btn)

        save_btn = QPushButton("Save Type")
        save_btn.clicked.connect(self.save_type)
        layout.addWidget(save_btn)

    def choose_image(self):
        base_dir = os.path.dirname(__file__)
        image_dir = os.path.join(base_dir, "..", "images")
        Path(image_dir).mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(self, "Choose image", image_dir)
        if path:
            # خزن المسار نسبياً لمجلد frontend/..
            rel_root = os.path.join(base_dir, "..")
            self.image_path = os.path.relpath(path, rel_root)
            pixmap = QPixmap(path).scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(pixmap)

    def save_type(self):
        name = self.name_input.text().strip()
        if not name or not self.image_path:
            QMessageBox.warning(self, "Tool Type", "Please enter a name and choose an image.")
            return
        self.tool_types[name] = self.image_path
        _save_tool_types(self.tool_types)
        self.accept()


# ======================================================================
# النافذة العائمة الرئيسية: تُجمّع كل الصفحات وتنسّقها
# ======================================================================
def create_tool_window(parent):
    # تحميل أنواع الأدوات
    tool_types = _load_tool_types()

    dialog = DraggableDialog(parent)
    dialog.setObjectName("ToolFloatingWindow")
    dialog.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    dialog.setFixedWidth(620)

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
    extrude_page = create_extrude_page()                  # index 0
    profile_page = create_profile_page()                  # index 1
    manager_page_v2 = create_profile_manager_page_v2(parent)  # index 2

    def _open_add_type_dialog(type_combo_widget, update_tool_image_cb):
        dlg = AddToolTypeDialog(tool_types, dialog)
        if dlg.exec_():
            type_combo_widget.clear()
            type_combo_widget.addItems(tool_types.keys())
            type_combo_widget.setCurrentText(dlg.name_input.text().strip())
            update_tool_image_cb(type_combo_widget.currentText())

    tools_page = create_tools_manager_page(tool_types, _open_add_type_dialog)  # index 3

    stacked.addWidget(extrude_page)       # 0
    stacked.addWidget(profile_page)       # 1
    stacked.addWidget(manager_page_v2)    # 2 ✅ الصفحة المعتمدة
    stacked.addWidget(tools_page)         # 3

    # خزّن مرجع صفحة v2 داخل الـ dialog لسهولة الوصول
    dialog.manager_page_v2 = manager_page_v2

    # ====== أزرار أسفل ======
    bottom_layout = QHBoxLayout()
    bottom_layout.addStretch()
    cancel_btn = QPushButton("Cancel");  cancel_btn.setObjectName("CancelBtn")
    apply_btn = QPushButton("Apply");    apply_btn.setObjectName("ApplyBtn")
    bottom_layout.addWidget(cancel_btn)
    bottom_layout.addWidget(apply_btn)
    main_layout.addLayout(bottom_layout)

    cancel_btn.clicked.connect(dialog.hide)

    # ====== قاعدة البيانات ======
    db = ProfileDB()

    # ====== منطق زر Apply ======
    def handle_apply():
        idx = stacked.currentIndex()

        # 0️⃣ Extrude
        if idx == 0:
            try:
                parent.extrude_clicked_from_window()
                # بعد الإكسترود: أضف العملية للوحة لو كانت متوفرة
                profile_name = getattr(parent, "active_profile_name", None)
                distance_val = getattr(parent, "last_extrude_distance", None)
                if profile_name and distance_val and hasattr(parent, "op_browser"):
                    parent.op_browser.add_extrude(profile_name, distance_val)
                dialog.hide()
            except Exception as e:
                QMessageBox.critical(dialog, "Extrude Error", str(e))
            return

        # 1️⃣ Profile: حفظ البروفايل وإنشاء الأصول (نسخ DXF + Snapshot)
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
                # حمّل الشكل للتحقق وللصورة
                shape = load_dxf_file(src_dxf)
                if shape is None:
                    raise RuntimeError("Invalid DXF shape.")

                # إعداد المسارات
                profile_dir = Path("profiles") / name
                profile_dir.mkdir(parents=True, exist_ok=True)
                dxf_dst = profile_dir / f"{name}.dxf"
                img_path = profile_dir / f"{name}.png"

                # تجهيز snapshot بالأسود وعلى خلفية رمادي
                small_display = profile_page._small_display
                if small_display is not None and Quantity_Color is not None:
                    black = Quantity_Color(0.0, 0.0, 0.0, Quantity_TOC_RGB)
                    _setup_viewer_colors(small_display)
                    small_display.EraseAll()
                    small_display.DisplayShape(shape, color=black, update=True)
                    small_display.FitAll()
                    try:
                        small_display.View.ZFitAll()
                        small_display.View.SetZSize(0.9)
                    except Exception:
                        pass
                    small_display.View.Redraw()
                    try:
                        from tools.profile_tools import _dump_display_png
                        _dump_display_png(small_display, shape, img_path)
                    except Exception as ex:
                        print("[WARN] Snapshot failed:", ex)
                        # يستمر الحفظ حتى لو snapshot فشل

                # نسخ ملف DXF
                shutil.copy2(src_dxf, dxf_dst)

                # حفظ في قاعدة البيانات
                db.add_profile(
                    name=name,
                    code=profile_page._p_code.text().strip(),
                    dimensions=profile_page._p_dims.text().strip(),
                    notes=profile_page._p_notes.text().strip(),
                    dxf_path=str(dxf_dst),
                    brep_path="",
                    image_path=str(img_path) if img_path.exists() else ""
                )

                print("[DEBUG] Profile saved to DB. Switching to manager v2 and refreshing...")

                # افتح صفحة v2 وحدّث القائمة بعد أن تظهر
                show_page(2)
                QTimer.singleShot(0, dialog.manager_page_v2.refresh_profiles_list_v2)

                QMessageBox.information(dialog, "Saved", "Profile saved successfully.")
                dialog.hide()

                # أضف إلى اللوحة الجانبية إن وجدت
                if hasattr(parent, "op_browser"):
                    parent.op_browser.add_profile(name)

            except Exception as e:
                QMessageBox.critical(dialog, "Error", f"Failed to save profile:\n{e}")
            return

        # 2️⃣ Profiles Manager v2 → لا حاجة لـ Apply (زر OK داخل الصفحة)
        elif idx == 2:
            QMessageBox.information(dialog, "Profiles", "Select a profile and press OK.")
            return

        # 3️⃣ Tools Page
        elif idx == 3:
            QMessageBox.information(dialog, "Tools", "Save Tool not implemented yet.")
            return

    apply_btn.clicked.connect(handle_apply)

    # ====== التنقل بين الصفحات ======
    def show_page(index: int):
        stacked.setCurrentIndex(index)
        if index == 2:
            header.setText("Profiles Manager")
            # استدعاء التحديث بعد أن تُعرض الصفحة فعلاً
            if hasattr(dialog, 'manager_page_v2') and hasattr(dialog.manager_page_v2, 'refresh_profiles_list_v2'):
                QTimer.singleShot(0, dialog.manager_page_v2.refresh_profiles_list_v2)
        elif index == 1:
            header.setText("Profile")
        elif index == 3:
            header.setText("Tools Manager")
        else:
            header.setText("Extrude")

        dialog.show()
        dialog.raise_()

    return dialog, show_page
