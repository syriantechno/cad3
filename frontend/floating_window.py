from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QComboBox, QDoubleSpinBox,
    QPushButton, QLineEdit, QFormLayout, QWidget,
    QStackedWidget, QLabel, QHBoxLayout, QFrame, QFileDialog, QMessageBox,
    QScrollArea, QGridLayout
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPixmap
from dxf_tools import  load_dxf_file
from pathlib import Path
import shutil
from tools.database import ProfileDB
from tools.profile_tools import process_dxf_to_assets
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
try:
    from OCC.Display.qtDisplay import qtViewer3d
except Exception:
    qtViewer3d = None  # يسمح بتحميل الملف حتى بدون بيئة OCC أثناء التطوير


class DraggableDialog(QDialog):
    """نافذة عائمة قابلة للسحب بدون شريط عنوان"""
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


def create_tool_window(parent):
    """
    نافذة عائمة متعددة الصفحات (Extrude / Profile / Manager)
    تعيد: dialog, show_page
    """
    dialog = DraggableDialog(parent)
    dialog.setObjectName("ToolFloatingWindow")
    dialog.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    dialog.setFixedWidth(360)

    dialog.setStyleSheet("""
        QDialog#ToolFloatingWindow {
            background-color: #f2f2f2;
            border: 1px solid #b4b4b4;
            border-radius: 8px;
        }
        QLabel {
            font-size: 13px;
            color: #333;
        }
        QComboBox, QDoubleSpinBox, QLineEdit {
            min-height: 28px;
            font-size: 13px;
            border: 1px solid #ccc;
            border-radius: 4px;
            background: white;
        }
        QComboBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {
            border: 1px solid #0078d4;
        }
        QPushButton {
            min-height: 30px;
            min-width: 100px;
            font-size: 13px;
            border-radius: 4px;
        }
        QPushButton#ApplyBtn {
            background-color: #0078d4;
            color: white;
        }
        QPushButton#ApplyBtn:hover { background-color: #005ea2; }
        QPushButton#CancelBtn {
            background-color: #e0e0e0;
            color: black;
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

    # ==================== Extrude Page ====================
    extrude_page = QWidget()
    extrude_layout = QFormLayout(extrude_page)
    extrude_layout.setLabelAlignment(Qt.AlignLeft)
    extrude_layout.setFormAlignment(Qt.AlignTop)

    axis_combo = QComboBox()
    axis_combo.addItems(["X", "Y", "Z"])
    distance_spin = QDoubleSpinBox()
    distance_spin.setRange(1, 9999)
    distance_spin.setValue(100)

    extrude_layout.addRow("Axis:", axis_combo)
    extrude_layout.addRow("Distance (mm):", distance_spin)
    stacked.addWidget(extrude_page)

    # ==================== Profile Page ====================
    profile_page = QWidget()
    pform = QFormLayout(profile_page)
    pform.setLabelAlignment(Qt.AlignLeft)
    pform.setFormAlignment(Qt.AlignTop)
    pform.setHorizontalSpacing(12)
    pform.setVerticalSpacing(8)

    p_name = QLineEdit()
    p_code = QLineEdit()
    p_dims = QLineEdit()
    p_notes = QLineEdit()

    dxf_path_edit = QLineEdit()
    dxf_path_edit.setReadOnly(True)
    choose_btn = QPushButton("Choose DXF")

    # عارض صغير للمعاينة
    # عارض مصغر للمعاينة (بحجم واضح وثابت)
    if qtViewer3d is not None:
        preview_container = QWidget()
        preview_container.setMinimumHeight(250)  # 👈 ارتفاع مناسب
        preview_container.setMaximumHeight(300)  # 👈 لا يزيد عن هذا
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 6, 0, 6)
        viewer = qtViewer3d(preview_container)
        viewer.setMinimumSize(320, 240)  # 👈 حجم أولي واضح
        preview_layout.addWidget(viewer)
        small_display = viewer._display  # سنستخدمه للحفظ كصورة أيضًا
        from PyQt5.QtCore import QTimer
        from tools.viewer_utils import setup_viewer_colors

        # تأخير تهيئة مظهر العارض المصغّر
        QTimer.singleShot(100, lambda: setup_viewer_colors(small_display))

        # ===== إعدادات مظهر العارض المصغر (Preview) =====
        # إعداد خلفية العارض الرئيسي وحدود الرسم
        from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
        from OCC.Core.Prs3d import Prs3d_LineAspect
        from OCC.Core.Aspect import Aspect_TOL_SOLID

        def setup_viewer_colors(display):
            """يضبط خلفية بيضاء وحدود سوداء لأي عارض OCC."""
            white = Quantity_Color(1.0, 1.0, 1.0, Quantity_TOC_RGB)
            black = Quantity_Color(0.0, 0.0, 0.0, Quantity_TOC_RGB)

            # خلفية بيضاء
            view = display.View
            view.SetBgGradientColors(white, white, True)
            view.SetBgGradientStyle(0)
            view.MustBeResized()

            # تفعيل رسم الحدود باللون الأسود
            drawer = display.Context.DefaultDrawer()
            drawer.SetFaceBoundaryDraw(True)
            line_aspect = Prs3d_LineAspect(black, Aspect_TOL_SOLID, 1.0)
            drawer.SetFaceBoundaryAspect(line_aspect)

            # إعادة تحديث العارض
            display.Context.UpdateCurrentViewer()
            view.Redraw()

        setup_viewer_colors(small_display)




    else:
        preview_container = QLabel("OCC Preview not available in this environment.")
        small_display = None



    pform.addRow("Name:", p_name)
    pform.addRow("Code:", p_code)
    pform.addRow("Dimensions:", p_dims)
    pform.addRow("Notes:", p_notes)
    pform.addRow("DXF File:", dxf_path_edit)
    pform.addRow("", choose_btn)
    pform.addRow(QLabel("Preview:"), preview_container)

    stacked.addWidget(profile_page)

    # ==================== Profiles Manager Page ====================
    manager_page = QWidget()
    manager_layout = QVBoxLayout(manager_page)
    manager_layout.setContentsMargins(0, 0, 0, 0)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    manager_layout.addWidget(scroll)

    container = QWidget()
    scroll.setWidget(container)
    grid = QGridLayout(container)
    grid.setContentsMargins(8, 8, 8, 8)
    grid.setHorizontalSpacing(12)
    grid.setVerticalSpacing(8)

    stacked.addWidget(manager_page)

    # ====== Bottom Buttons ======
    bottom_layout = QHBoxLayout()
    bottom_layout.addStretch()
    cancel_btn = QPushButton("Cancel");  cancel_btn.setObjectName("CancelBtn")
    apply_btn = QPushButton("Apply");    apply_btn.setObjectName("ApplyBtn")
    bottom_layout.addWidget(cancel_btn)
    bottom_layout.addWidget(apply_btn)
    main_layout.addLayout(bottom_layout)

    cancel_btn.clicked.connect(dialog.hide)

    # ====== DB ======
    db = ProfileDB()

    # ====== Handlers ======
    selected_shape = {"shape": None, "src": None}

    def on_choose_dxf():
        file_name, _ = QFileDialog.getOpenFileName(dialog, "Select DXF", "", "DXF Files (*.dxf)")
        if not file_name:
            return
        dxf_path_edit.setText(file_name)
        # حلّل DXF واعرضه في العارض المصغّر
        try:
            from dxf_tools import load_dxf_file
            shp = load_dxf_file(file_name)
        except Exception as ex:
            QMessageBox.warning(dialog, "DXF", f"Failed to import dxf_tools:\n{ex}")
            return
        if shp is None:
            QMessageBox.warning(dialog, "DXF", "Failed to parse DXF file.")
            return
        selected_shape["shape"] = shp
        selected_shape["src"] = file_name
        try:
            if small_display is not None:
                small_display.EraseAll()
                small_display.DisplayShape(shp, update=True)
                small_display.FitAll()
        except Exception as e:
            QMessageBox.warning(dialog, "Preview", f"Failed to display preview:\n{e}")

    choose_btn.clicked.connect(on_choose_dxf)

    # ---------- Profiles Manager helpers ----------
    def refresh_profiles_list():
        # نظف المحتوى أولًا
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        profiles = db.list_profiles()
        if not profiles:
            grid.addWidget(QLabel("لا توجد بروفايلات محفوظة."), 0, 0)
            return

        for row_idx, prof in enumerate(profiles):
            pid, name, code, dims, notes, dxf_path, brep_path, img_path, created = prof

            img_label = QLabel()
            img_label.setFixedSize(64, 64)
            img_label.setFrameShape(QFrame.Box)
            img_label.setLineWidth(1)

            pix = QPixmap()
            if Path(img_path).exists():
                pix.load(str(img_path))
            if not pix.isNull():
                img_label.setPixmap(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                img_label.setText("No\nImage")
                img_label.setAlignment(Qt.AlignCenter)

            text_label = QLabel(
                f"<b>{name}</b><br>"
                f"Code: {code or '-'}<br>"
                f"Dims: {dims or '-'}<br>"
                f"<i>{notes or ''}</i>"
            )
            text_label.setWordWrap(True)

            load_btn = QPushButton("Load")
            load_btn.setFixedWidth(70)

            def make_loader(dxf_path_local):
                def _loader():
                    try:
                        if not dxf_path_local or not str(dxf_path_local).strip():
                            raise RuntimeError("❌ DXF path is empty or undefined.")

                        print(f"🔍 محاولة تحميل DXF من: {dxf_path_local}")
                        path_obj = Path(dxf_path_local).resolve()

                        if not path_obj.exists():
                            raise RuntimeError(f"❌ DXF file not found at: {path_obj}")
                        if not path_obj.is_file():
                            raise RuntimeError(f"❌ Expected a DXF file, but got a folder: {path_obj}")
                        if not str(path_obj).lower().endswith(".dxf"):
                            raise RuntimeError(f"❌ Invalid file type: {path_obj.name}")

                        shape = load_dxf_file(path_obj)
                        if shape is None or shape.IsNull():
                            raise RuntimeError("❌ DXF parsing returned no shape.")

                        if self.parent.display is None:
                            raise RuntimeError("❌ Main display not initialized.")
                        self.parent.display.EraseAll()
                        self.parent.display.DisplayShape(shape, update=True)
                        self.parent.display.FitAll()
                        print(f"📦 بروفايل: {name}, DXF: {dxf_path}")

                        print(f"✅ تم تحميل وعرض الشكل من: {path_obj}")
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to load DXF:\n{e}")

                return _loader

            load_btn.clicked.connect(make_loader(dxf_path if dxf_path and Path(dxf_path).exists() else None))

            grid.addWidget(img_label, row_idx, 0)
            grid.addWidget(text_label, row_idx, 1)
            grid.addWidget(load_btn, row_idx, 2)

    # ================== زر Apply ==================
    def handle_apply():
        current_page = stacked.currentIndex()

        # 0️⃣ Extrude page → استدعاء دالة الواجهة الرئيسية
        if current_page == 0:
            try:
                parent.extrude_clicked_from_window()
                dialog.hide()
            except Exception as e:
                QMessageBox.critical(dialog, "Extrude Error", str(e))
            return

        # 1️⃣ Profile page → حفظ البروفايل في القاعدة وإنشاء الأصول
        elif current_page == 1:
            name = p_name.text().strip()
            if not name:
                QMessageBox.information(dialog, "Profile", "Please enter profile Name.")
                return
            if not dxf_path_edit.text():
                QMessageBox.information(dialog, "Profile", "Please choose a DXF file.")
                return
            try:
                # تحميل الشكل
                shape = load_dxf_file(dxf_path_edit.text())
                if shape is None or shape.IsNull():
                    raise RuntimeError("Invalid DXF shape.")

                # عرض الشكل على العارض الصغير
                if small_display is not None:
                    small_display.EraseAll()
                    small_display.DisplayShape(shape, update=True)
                    small_display.FitAll()

                # إعداد المسارات
                profile_dir = Path("profiles") / name
                profile_dir.mkdir(parents=True, exist_ok=True)
                dxf_dst = profile_dir / f"{name}.dxf"
                img_path = profile_dir / f"{name}.png"

                # أخذ صورة من العارض
                from tools.profile_tools import _dump_display_png
                _dump_display_png(small_display, shape, img_path)

                # نسخ ملف DXF كما هو
                shutil.copy2(dxf_path_edit.text(), dxf_dst)

                # حفظ في قاعدة البيانات
                db.add_profile(
                    name=name,
                    code=p_code.text().strip(),
                    dimensions=p_dims.text().strip(),
                    notes=p_notes.text().strip(),
                    dxf_path=str(dxf_dst),
                    brep_path="",
                    image_path=str(img_path)
                )

                QMessageBox.information(dialog, "Saved", "Profile saved successfully.")
                dialog.hide()
            except Exception as e:
                QMessageBox.critical(dialog, "Error", f"Failed to save profile:\n{e}")
                return

    apply_btn.clicked.connect(handle_apply)

    def show_page(index: int):
        stacked.setCurrentIndex(index)
        if index == 2:
            refresh_profiles_list()
            header.setText("Profiles Manager")
        elif index == 1:
            header.setText("Profile")
        else:
            header.setText("Extrude")
        dialog.show()
        dialog.raise_()

    return dialog, show_page