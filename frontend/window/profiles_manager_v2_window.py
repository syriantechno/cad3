# ================= profiles_manager_v2_window.py =================
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QLabel, QSizePolicy,
    QPushButton, QMessageBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from pathlib import Path
from tools.database import ProfileDB
from frontend.window.floating_window import load_dxf_file
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from .utils_window import safe_exists  # استخدم safe_exists بدل _safe_exists

def create_profile_manager_page_v2(parent, profile_page_getter=None, stacked_getter=None):
    """
    تصميم:
    - يمين: قائمة أسماء البروفايلات (QListWidget)
    - يسار: صورة + تفاصيل + أزرار [OK] [Edit] [Delete]
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

    # أزرار العمليات
    btn_row = QHBoxLayout()
    ok_btn = QPushButton("OK")
    ok_btn.setStyleSheet("background:#0078d4; color:white; font-weight:bold;")
    edit_btn = QPushButton("✏️ Edit")
    del_btn = QPushButton("🗑 Delete")
    btn_row.addWidget(ok_btn)
    btn_row.addWidget(edit_btn)
    btn_row.addWidget(del_btn)
    left_layout.addLayout(btn_row)

    root.addWidget(left_container, alignment=Qt.AlignLeft)

    # ---------- تخزين ----------
    page.profile_list = profile_list
    page.image_label = image_label
    page.lbl_name = lbl_name
    page.lbl_code = lbl_code
    page.lbl_size = lbl_size
    page.lbl_desc = lbl_desc
    page.selected = {"dxf": None, "pid": None, "name": None, "img": None}

    # ---------- تحديث القائمة ----------
    def refresh_profiles_list_v2():
        page.profile_list.clear()
        db_local = ProfileDB()
        profiles = db_local.list_profiles() or []
        page.profiles = profiles
        for prof in profiles:
            page.profile_list.addItem(prof[1])
        print("[DEBUG] Profile list refreshed (v2). count =", len(profiles))

    page.refresh_profiles_list_v2 = refresh_profiles_list_v2

    # ---------- عند اختيار عنصر ----------
    def on_select(row):
        if not hasattr(page, "profiles") or not page.profiles:
            return
        if row < 0 or row >= len(page.profiles):
            return

        pid, name, code, dims, notes, dxf_path, brep, img, created = page.profiles[row]
        lbl_name.setText(f"Name: {name or '—'}")
        lbl_code.setText(f"Code: {code or '—'}")
        lbl_size.setText(f"Size: {dims or '—'}")
        lbl_desc.setText(f"Description: {notes or '—'}")

        if safe_exists(img):
            pix = QPixmap(img).scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_label.setPixmap(pix)
        else:
            image_label.setPixmap(QPixmap())

        page.selected.update({"dxf": dxf_path, "pid": pid, "name": name, "img": img})
        print(f"[DEBUG] Selected profile: id={pid} name={name} dxf={dxf_path}")

    profile_list.currentRowChanged.connect(on_select)

    # ---------- زر OK ----------
    def on_ok():
        dxf = page.selected.get("dxf")
        if not safe_exists(dxf):
            QMessageBox.warning(page, "Profile", "No valid DXF selected.")
            return
        try:
            shape = load_dxf_file(Path(dxf))
            if shape is None:
                raise RuntimeError("DXF returned no shape.")

            main_window = parent
            display = main_window.display
            display.EraseAll()
            black = Quantity_Color(0.0, 0.0, 0.0, Quantity_TOC_RGB)
            display.DisplayShape(shape, color=black, update=True)
            main_window.loaded_shape = shape
            display.FitAll()

            if hasattr(main_window, "op_browser"):
                profile_name = Path(dxf).stem
                main_window.op_browser.add_profile(profile_name)
                print(f"[DEBUG] Added profile to browser: {profile_name}")

        except Exception as e:
            QMessageBox.critical(page, "Error", f"Failed to load DXF:\n{e}")

    ok_btn.clicked.connect(on_ok)

    # ---------- زر Edit ----------
    def on_edit():
        if not hasattr(page, "profiles") or not page.profiles:
            return
        row = page.profile_list.currentRow()
        if row < 0 or row >= len(page.profiles):
            QMessageBox.information(page, "Edit", "Please select a profile to edit.")
            return

        pid, name, code, dims, notes, dxf_path, brep, img, created = page.profiles[row]
        p_page = profile_page_getter() if callable(profile_page_getter) else None
        stk = stacked_getter() if callable(stacked_getter) else None
        if p_page is None or stk is None:
            QMessageBox.critical(page, "Edit", "Profile page not available.")
            return

        dialog = stk.parent()
        if not hasattr(dialog, "_edit_ctx"):
            dialog._edit_ctx = {}
        dialog._edit_ctx.update({
            "active": True,
            "pid": pid,
            "orig_name": name,
            "orig_dxf": dxf_path,
            "orig_img": img
        })

        p_page._p_name.setText(name or "")
        p_page._p_code.setText(code or "")
        p_page._p_dims.setText(dims or "")
        p_page._p_notes.setText(notes or "")
        p_page._dxf_path_edit.setText(dxf_path or "")

        print(f"[DEBUG] Edit profile -> id={pid}, name={name}")
        stk.setCurrentIndex(1)

    edit_btn.clicked.connect(on_edit)

    # ---------- زر Delete ----------
    def on_delete():
        row = page.profile_list.currentRow()
        if row < 0 or row >= len(page.profiles):
            QMessageBox.information(page, "Delete", "Please select a profile to delete.")
            return

        pid, name, code, dims, notes, dxf_path, brep, img, created = page.profiles[row]
        ans = QMessageBox.question(
            page, "Confirm Delete",
            f"Are you sure you want to delete profile:\n\n{name}",
            QMessageBox.Yes | QMessageBox.No
        )
        if ans != QMessageBox.Yes:
            return

        try:
            if safe_exists(dxf_path):
                Path(dxf_path).unlink(missing_ok=True)
            if safe_exists(img):
                Path(img).unlink(missing_ok=True)
            prof_dir = Path("profiles") / name
            if prof_dir.exists():
                prof_dir.rmdir()
        except Exception as e:
            print("[WARN] file deletion failed:", e)

        db = ProfileDB()
        db.delete_profile(pid)
        print(f"[DEBUG] Profile deleted from DB: id={pid}, name={name}")

        page.refresh_profiles_list_v2()
        page.profile_list.setCurrentRow(-1)
        image_label.setPixmap(QPixmap())
        lbl_name.setText("Name: —")
        lbl_code.setText("Code: —")
        lbl_size.setText("Size: —")
        lbl_desc.setText("Description: —")
        page.selected.update({"dxf": None, "pid": None, "name": None, "img": None})

    del_btn.clicked.connect(on_delete)

    page.refresh_profiles_list_v2()
    return page
