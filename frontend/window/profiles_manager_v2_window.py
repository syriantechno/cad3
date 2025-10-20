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
    page = QWidget()
    root = QHBoxLayout(page)
    root.setContentsMargins(10, 10, 10, 10)
    root.setSpacing(14)

    # ---------- قائمة الأسماء ----------
    profile_list = QListWidget()
    profile_list.setMinimumWidth(200)
    profile_list.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    root.addWidget(profile_list, alignment=Qt.AlignRight)

    # ---------- تفاصيل ----------
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

    page.profile_list = profile_list
    page.image_label = image_label
    page.lbl_name = lbl_name
    page.lbl_code = lbl_code
    page.lbl_size = lbl_size
    page.lbl_desc = lbl_desc
    page.selected = {"dxf": None, "pid": None, "name": None, "img": None}

    # ======================================================
    #  🧹 أداة مسح آمنة لكائنات AIS
    # ======================================================
    def _erase_ais_list(display, lst):
        if not lst:
            return
        for ais in lst:
            try:
                display.Context.Remove(ais, False)
                display.Context.Erase(ais, True)
            except Exception:
                pass
        lst.clear()

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

            from OCC.Core.Bnd import Bnd_Box
            from OCC.Core.BRepBndLib import brepbndlib
            from OCC.Core.gp import gp_Trsf, gp_Vec
            from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform

            bbox = Bnd_Box()
            brepbndlib.Add(shape, bbox)
            xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

            trsf = gp_Trsf()
            trsf.SetTranslation(gp_Vec(-xmin, -ymin, -zmin))
            moved_shape = BRepBuilderAPI_Transform(shape, trsf, True).Shape()
            shape = moved_shape

            main_window = parent
            display = main_window.display
            # ✅ تسجيل معرف البروفايل النشط في النافذة الرئيسية
            try:
                main_window.active_profile_id = page.selected.get("pid")
                print(f"✅ [PROFILE] Active profile set to ID = {main_window.active_profile_id}")
            except Exception as e:
                print(f"⚠️ Failed to set active profile ID: {e}")

            # ✅ تنظيف أي عرض قديم من البروفايل نفسه
            if not hasattr(main_window, "profile_ais_list"):
                main_window.profile_ais_list = []
            else:
                _erase_ais_list(display, main_window.profile_ais_list)

            display.EraseAll()

            # 🖤 عرض الشكل باللون الأسود وتخزين المرجع
            black = Quantity_Color(0.0, 0.0, 0.0, Quantity_TOC_RGB)
            ais = display.DisplayShape(shape, color=black, update=True)
            if ais:
                main_window.profile_ais_list.append(ais)

            # حفظ الشكل في الواجهة
            main_window.loaded_shape = shape
            # ✅ تسجيل اسم البروفايل النشط في النافذة الرئيسية
            try:
                profile_name = page.selected.get("name")
                from PyQt5.QtWidgets import QApplication
                from gui_fusion import AlumCamGUI
                for w in QApplication.topLevelWidgets():
                    if isinstance(w, AlumCamGUI):
                        w.active_profile_name = profile_name
                        print(f"✅ [GLOBAL] Active profile set via Profile Manager v2: {profile_name}")
                        break
                else:
                    print("⚠️ [GLOBAL] AlumCamGUI not found while setting profile name (v2)")
            except Exception as e:
                print(f"⚠️ Failed to register active profile (v2): {e}")

            # ✨ قياسات X + Z (تبقى كما هي)
            from OCC.Core.Bnd import Bnd_Box
            from OCC.Core.BRepBndLib import brepbndlib
            from OCC.Core.gp import gp_Pnt
            from tools.dimensions import draw_dimension
            from math import isclose

            bbox = Bnd_Box()
            brepbndlib.Add(shape, bbox)
            xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
            x_len = xmax - xmin
            z_len = zmax - zmin

            def compute_lift(p1, p2, top_z, extra=20.0):
                current_top = max(p1.Z(), p2.Z())
                return (top_z - current_top) + extra

            if not isclose(x_len, 0.0, abs_tol=1e-9):
                p1_x = gp_Pnt(xmin, ymin, zmax)
                p2_x = gp_Pnt(xmax, ymin, zmax)
                lift_x = compute_lift(p1_x, p2_x, zmax, 20.0)
                draw_dimension(display, p1_x, p2_x, f"{x_len:.1f} mm", lift_z=lift_x)
            if not isclose(z_len, 0.0, abs_tol=1e-9):
                z_offset_x = (xmax - xmin) * 0.3
                p1_z = gp_Pnt(xmin - z_offset_x, ymin, zmin)
                p2_z = gp_Pnt(xmin - z_offset_x, ymin, zmax)
                lift_z = compute_lift(p1_z, p2_z, zmax, 20.0)
                draw_dimension(display, p1_z, p2_z, f"{z_len:.1f} mm", lift_z=lift_z)

            display.FitAll()

            if hasattr(main_window, "op_browser"):
                profile_name = Path(dxf).stem
                main_window.op_browser.add_profile(profile_name)
                print(f"[DEBUG] Added profile to browser: {profile_name}")

        except Exception as e:
            QMessageBox.critical(page, "Error", f"Failed to load DXF:\n{e}")

    ok_btn.clicked.connect(on_ok)

    # (زر Edit و Delete يبقيان كما هما)
    # ...

    page.refresh_profiles_list_v2()
    return page
