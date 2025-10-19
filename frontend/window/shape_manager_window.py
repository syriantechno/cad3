# -*- coding: utf-8 -*-

# ===============================
# Shape Manager (with Image Preview)
# - PyQt5 page with left controls & right image preview
# - Auto-load DXF from: frontend/window/library/shapes/
# - Auto-generate PNG preview next to each DXF if missing
# - Clean buttons (no icons) with unified style
# - Keeps 3D ops (extrude/rotate/scale/cut) for main viewer usage
# ===============================

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QListWidget, QLabel,
    QLineEdit, QComboBox, QPushButton, QFileDialog, QSizePolicy
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap, QImage, QPainter, QFont, QColor

from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.gp import gp_Vec, gp_Trsf, gp_Ax1, gp_Dir, gp_Pnt
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

import os
from os.path import basename, dirname, join, splitext, exists

import json
from dxf_loader import smart_load_dxf

# للمعاينة التلقائية في العارض الرئيسي (ليست للعارض المصغّر)
from frontend.window.shape_auto_preview import safe_auto_preview, connect_auto_preview


# ===============================
# هندسة مساعدة (كما كانت لديك)
# ===============================

def orient_shape_to_axis(shape: TopoDS_Shape, axis: str) -> TopoDS_Shape:
    trsf = gp_Trsf()
    if axis.upper() == 'X':
        trsf.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), -1.5708)
    elif axis.upper() == 'Y':
        trsf.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), 1.5708)
    return BRepBuilderAPI_Transform(shape, trsf, True).Shape()


def extrude_shape(shape_2d: TopoDS_Shape, depth: float, axis: str) -> TopoDS_Shape:
    # تُبقي دوران الشكل كما هو (حسب منطقك الحالي) ثم تمده باتجاه المحور
    shape_oriented = orient_shape_to_axis(shape_2d, axis)
    axis_map = {
        'X': gp_Vec(depth, 0, 0),
        'Y': gp_Vec(0, depth, 0),
        'Z': gp_Vec(0, 0, depth)
    }
    vec = axis_map.get(axis.upper(), gp_Vec(0, 0, depth))
    return BRepPrimAPI_MakePrism(shape_oriented, vec).Shape()


def translate_shape(shape: TopoDS_Shape, x: float, y: float, z: float) -> TopoDS_Shape:
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(x, y, z))
    return BRepBuilderAPI_Transform(shape, trsf, True).Shape()


def rotate_shape(shape: TopoDS_Shape, axis: str, angle_deg: float) -> TopoDS_Shape:
    angle_rad = angle_deg * 3.14159265 / 180.0
    trsf = gp_Trsf()
    axis_map = {
        'X': gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)),
        'Y': gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)),
        'Z': gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)),
    }
    ax = axis_map.get(axis.upper())
    if ax is None:
        print(f"❌ محور غير معروف: {axis}")
        return shape
    trsf.SetRotation(ax, angle_rad)
    return BRepBuilderAPI_Transform(shape, trsf, True).Shape()


def get_shape_center(shape: TopoDS_Shape) -> gp_Pnt:
    box = Bnd_Box()
    brepbndlib.Add(shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return gp_Pnt((xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2)


def scale_shape(shape: TopoDS_Shape, factor: float) -> TopoDS_Shape:
    center = get_shape_center(shape)
    trsf = gp_Trsf()
    trsf.SetScale(center, factor)
    return BRepBuilderAPI_Transform(shape, trsf, True).Shape()


def get_shape_size(shape: TopoDS_Shape, axis: str) -> float:
    box = Bnd_Box()
    brepbndlib.Add(shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    if axis.upper() == "X":
        return xmax - xmin
    elif axis.upper() == "Y":
        return ymax - ymin
    elif axis.upper() == "Z":
        return zmax - zmin
    return 0


def get_z_min(shape: TopoDS_Shape) -> float:
    box = Bnd_Box()
    brepbndlib.Add(shape, box)
    _, _, zmin, _, _, _ = box.Get()
    return zmin


def show_shape(display, shape: TopoDS_Shape):
    actor = AIS_Shape(shape)
    actor.SetColor(Quantity_Color(0.2, 0.4, 0.8, Quantity_TOC_RGB))
    display.Context.Display(actor, True)
    return actor


def apply_transformations(shape: TopoDS_Shape, scale_factor: float, rotation_axis: str, rotation_angle: float,
                          x: float, y: float, z: float) -> TopoDS_Shape:
    if scale_factor != 1.0:
        shape = scale_shape(shape, scale_factor)
    if rotation_angle != 0:
        shape = rotate_shape(shape, rotation_axis, rotation_angle)
    shape = translate_shape(shape, x, y, z)
    return shape


# ===============================
# معاينة الإكسترود (للعرض الرئيسي)
# ===============================

def preview_extrude(page, display):
    """
    تُنشئ معاينة 3D في العارض الرئيسي (وليس العارض المصغّر).
    تُستخدم عند الإدراج الفعلي أو زر "Preview".
    """
    try:
        if page.shape_2d is None or page.shape_2d.IsNull():
            print("❌ لا يوجد شكل 2D للمعاينة")
            return

        depth = float(page.depth_input.text())
        axis = page.axis_selector.currentText()
        x = float(page.x_input.text())
        y = float(page.y_input.text())
        z = float(page.z_input.text())
        rotation_angle = float(page.rotate_angle_input.text())
        scale_target = float(page.scale_input.text())
        scale_axis = page.scale_axis_selector.currentText()

        # إزالة المعاينة القديمة
        if hasattr(page, "preview_actor") and page.preview_actor:
            display.Context.Remove(page.preview_actor, False)

        # توسيط 2D حول الأصل
        center = get_shape_center(page.shape_2d)
        trsf = gp_Trsf()
        trsf.SetTranslation(gp_Vec(-center.X(), -center.Y(), -center.Z()))
        shape_centered = BRepBuilderAPI_Transform(page.shape_2d, trsf, True).Shape()

        # إنشاء 3D
        shape_3d = extrude_shape(shape_centered, depth, axis)

        # توسيط 3D النهائي حول الأصل
        center3d = get_shape_center(shape_3d)
        trsf_center = gp_Trsf()
        trsf_center.SetTranslation(gp_Vec(-center3d.X(), -center3d.Y(), -center3d.Z()))
        shape_3d = BRepBuilderAPI_Transform(shape_3d, trsf_center, True).Shape()

        print(f"[Centering] ΔX={center3d.X():.3f}, ΔY={center3d.Y():.3f}, ΔZ={center3d.Z():.3f}")

        # التحويلات الإضافية
        current_size = get_shape_size(shape_3d, scale_axis)
        scale_factor = scale_target / current_size if current_size > 0 else 1.0
        shape_3d = apply_transformations(shape_3d, scale_factor, axis, rotation_angle, x, y, z)

        page.preview_shape = shape_3d
        page.preview_actor = show_shape(display, shape_3d)
        page.cutter_shape = shape_3d

        print("✅ تم عرض الشكل بعد تطبيق كل التحويلات")

    except Exception as e:
        print(f"🔥 كراش أثناء المعاينة: {e}")


# ===============================
# قص من الإكسترود (في العارض الرئيسي)
# ===============================

def apply_cut_core(parent, page):
    """
    قص الشكل الأساسي (parent.loaded_shape) باستخدام page.preview_shape
    ثم عرض النتيجة بلون Fusion.
    """
    try:
        cutter = page.preview_shape
        base = getattr(parent, "loaded_shape", None)

        print("💥 بدء تنفيذ عملية القص...")

        if not cutter or cutter.IsNull():
            print("❌ لا يوجد شكل Cutter صالح للقص.")
            return
        if not base or base.IsNull():
            print("❌ لا يوجد شكل Base صالح للقص.")
            return

        # عملية القص
        result = BRepAlgoAPI_Cut(base, cutter).Shape()
        parent.loaded_shape = result

        # عرض النتيجة في العارض الرئيسي
        parent.display.Context.RemoveAll(True)
        ais_shape = AIS_Shape(result)

        # لون Fusion إن توفّر
        try:
            from tools.color_utils import FUSION_BODY_COLOR, BLACK
            ais_shape.SetColor(FUSION_BODY_COLOR)
        except Exception:
            ais_shape.SetColor(Quantity_Color(0.545, 0.533, 0.498, Quantity_TOC_RGB))

        parent.display.Context.Display(ais_shape, True)
        parent.display.FitAll()
        print("✅ تم تنفيذ القص وعرض النتيجة بلون Fusion.")

    except Exception as e:
        print(f"🔥 كراش أثناء تنفيذ عملية القص: {e}")


# ===============================
# معاينة صور DXF (يمين الصفحة)
# ===============================

def png_path_for_dxf(dxf_path: str) -> str:
    root, _ = splitext(dxf_path)
    return root + ".png"


def _draw_text_thumbnail(png_path: str, title: str, size=(480, 320)):
    """Fallback: صورة نصية بسيطة تحمل اسم الشكل إن لم تتوفر آلية توليد حقيقية."""
    w, h = size
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(QColor(245, 245, 245))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    font = QFont("Segoe UI", 18, QFont.Bold)
    p.setFont(font)
    p.setPen(QColor(70, 70, 70))
    text = f"{title}\n(preview)"
    p.drawText(0, 0, w, h, Qt.AlignCenter, text)
    p.end()
    img.save(png_path)


def ensure_preview_image(dxf_path: str):
    """
    توليد صورة المعاينة PNG بجانب DXF إن لم تكن موجودة:
    - لو عندك مولّد جاهز مثل البروفايل مانجر: tools.preview_utils.generate_dxf_preview_png
    - وإلا: نصنع صورة نصّية بديلة تحمل اسم الشكل.
    """
    png_path = png_path_for_dxf(dxf_path)
    if exists(png_path):
        return png_path

    # محاولة استخدام مولّد جاهز (إن وُجد)
    try:
        from tools.preview_utils import generate_dxf_preview_png  # هوك اختياري
        ok = generate_dxf_preview_png(dxf_path, png_path)
        if ok and exists(png_path):
            return png_path
    except Exception:
        pass

    # بديل مبسّط: صورة نصّية باسم الملف
    _draw_text_thumbnail(png_path, basename(dxf_path).replace(".dxf", ""))
    return png_path


# ===============================
# صفحة Shape Manager (واجهة)
# ===============================
def rotate_selected_shape_wrapper(page, parent):
    try:
        shape = page.preview_shape
        if shape and not shape.IsNull():
            if page.preview_actor:
                parent.display.Context.Remove(page.preview_actor, False)
            axis = page.axis_selector.currentText()
            angle = float(page.rotate_angle_input.text())
            rotated = rotate_shape(shape, axis, angle)
            page.preview_shape = rotated
            page.preview_actor = show_shape(parent.display, rotated)
            print("✅ تم تدوير الشكل وعرضه داخل العارض")
    except Exception as e:
        print(f"🔥 كراش أثناء التدوير: {e}")

def scale_preview_shape_wrapper(page, parent):
    try:
        shape = page.preview_shape
        if shape and not shape.IsNull():
            if page.preview_actor:
                parent.display.Context.Remove(page.preview_actor, False)
            target_size = float(page.scale_input.text())
            axis = page.scale_axis_selector.currentText()
            current_size = get_shape_size(shape, axis)
            if current_size == 0:
                print("❌ لا يمكن حساب حجم الشكل الحالي")
                return
            factor = target_size / current_size
            scaled = scale_shape(shape, factor)
            page.preview_shape = scaled
            page.preview_actor = show_shape(parent.display, scaled)
            print(f"✅ تم تغيير حجم الشكل إلى {target_size} ملم على المحور {axis}")
    except Exception as e:
        print(f"🔥 كراش أثناء تغيير الحجم: {e}")

def create_shape_manager_page(parent):
    from PyQt5.QtWidgets import (
        QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QListWidget, QLabel,
        QLineEdit, QComboBox, QPushButton, QFileDialog, QSizePolicy, QFrame
    )
    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtGui import QPixmap
    import os
    from os.path import basename, join, splitext, exists
    import logging
    from dxf_loader import smart_load_dxf

    page = QWidget()
    main = QHBoxLayout(page)
    main.setContentsMargins(8, 8, 8, 8)
    main.setSpacing(8)

    # ====== يسار: قائمة الأشكال ======
    left_panel = QWidget()
    left_v = QVBoxLayout(left_panel)
    left_v.setContentsMargins(0, 0, 0, 0)
    left_v.setSpacing(6)

    title_list = QLabel("📚 مكتبة الأشكال")
    title_list.setStyleSheet("font-weight: bold; margin-bottom: 4px;")
    shape_list = QListWidget()
    shape_list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

    left_v.addWidget(title_list)
    left_v.addWidget(shape_list)

    # ====== يمين: عارض صورة + أزرار + مدخلات ======
    right_panel = QWidget()
    right_v = QVBoxLayout(right_panel)
    right_v.setSpacing(8)

    preview_label = QLabel("Preview")
    preview_label.setStyleSheet("font-weight: bold;")
    img_view = QLabel()
    img_view.setAlignment(Qt.AlignCenter)
    img_view.setMinimumHeight(200)
    img_view.setMaximumHeight(240)
    img_view.setStyleSheet("background:#f3f3f3; border:1px solid #ddd; border-radius:6px;")

    right_v.addWidget(preview_label)
    right_v.addWidget(img_view)

    # خط فاصل
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    right_v.addWidget(line)

    # ====== الأزرار ======
    preview_btn = QPushButton("Preview")
    rotate_btn  = QPushButton("Rotate")
    scale_btn   = QPushButton("Scale")
    cut_btn     = QPushButton("Apply Cut")
    import_btn  = QPushButton("Import DXF")
    reload_btn  = QPushButton("⟳ Reload")

    def style_buttons(*buttons):
        for btn in buttons:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #5A5A5A;
                    color: white;
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-weight: bold;
                    border: 1px solid #3A3A3A;
                }
                QPushButton:hover { background-color: #707070; }
                QPushButton:pressed { background-color: #4A4A4A; }
            """)
            btn.setMinimumHeight(32)
    style_buttons(preview_btn, rotate_btn, scale_btn, cut_btn, import_btn, reload_btn)

    row_btns1 = QHBoxLayout()
    for b in (preview_btn, rotate_btn, scale_btn):
        row_btns1.addWidget(b)
    row_btns2 = QHBoxLayout()
    for b in (cut_btn, import_btn, reload_btn):
        row_btns2.addWidget(b)
    right_v.addLayout(row_btns1)
    right_v.addLayout(row_btns2)

    # ====== المدخلات ======
    form = QFormLayout()
    depth_input = QLineEdit("20")
    axis_selector = QComboBox(); axis_selector.addItems(["X", "Y", "Z"])
    x_input = QLineEdit("0"); y_input = QLineEdit("0"); z_input = QLineEdit("0")
    rotate_angle_input = QLineEdit("0")
    scale_input = QLineEdit("30")
    scale_axis_selector = QComboBox(); scale_axis_selector.addItems(["X", "Y", "Z"])

    for label, widget in [
        ("Depth:", depth_input),
        ("Axis:", axis_selector),
        ("X:", x_input), ("Y:", y_input), ("Z:", z_input),
        ("Rotate (°):", rotate_angle_input),
        ("Target Size:", scale_input),
        ("Scale Axis:", scale_axis_selector)
    ]:
        form.addRow(label, widget)
    right_v.addLayout(form)

    main.addWidget(left_panel, 2)
    main.addWidget(right_panel, 3)

    # ====== ربط الصفحة ======
    page.shape_list = shape_list
    page.depth_input = depth_input
    page.axis_selector = axis_selector
    page.x_input = x_input
    page.y_input = y_input
    page.z_input = z_input
    page.rotate_angle_input = rotate_angle_input
    page.scale_input = scale_input
    page.scale_axis_selector = scale_axis_selector
    page.shape_2d = None
    page.preview_shape = None
    page.preview_actor = None
    page.test_shapes = {}
    page.display = parent.display

    shapes_folder = os.path.join("frontend", "window", "library", "shapes")
    os.makedirs(shapes_folder, exist_ok=True)

    from frontend.window.tools.preview_utils import generate_dxf_preview_png
    logging.getLogger("ezdxf").setLevel(logging.ERROR)

    def ensure_preview_image(dxf_path: str):
        png_path = os.path.splitext(dxf_path)[0] + ".png"
        if os.path.exists(png_path):
            return png_path
        try:
            ok = generate_dxf_preview_png(dxf_path, png_path)
            if ok and os.path.exists(png_path):
                return png_path
        except Exception:
            pass
        return None

    def show_image_preview(name: str):
        dxf_path = os.path.join(shapes_folder, name + ".dxf")
        png_path = ensure_preview_image(dxf_path)
        if png_path and os.path.exists(png_path):
            pix = QPixmap(png_path)
            scaled = pix.scaled(img_view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_view.setPixmap(scaled)
        else:
            img_view.clear()

    def load_all_shapes_from_folder():
        """تحميل ملفات DXF فقط عند الطلب."""
        print("📂 [Manual Load] بدء تحميل مكتبة الأشكال...")
        page.shape_list.clear()
        page.test_shapes.clear()
        dxf_files = [f for f in os.listdir(shapes_folder) if f.lower().endswith(".dxf")]
        for fname in dxf_files:
            dxf_path = os.path.join(shapes_folder, fname)
            shape = smart_load_dxf(dxf_path)
            if shape and not shape.IsNull():
                key = os.path.splitext(fname)[0]
                page.test_shapes[key] = shape
                page.shape_list.addItem(key)
                ensure_preview_image(dxf_path)
        print(f"✅ تم تحميل {len(dxf_files)} ملف DXF من {shapes_folder}")

    def on_select(row):
        if row < 0:
            img_view.clear()
            return
        name = shape_list.item(row).text()
        shape = page.test_shapes.get(name)
        if shape and not shape.IsNull():
            page.shape_2d = shape
            show_image_preview(name)
            print(f"📐 تم اختيار الشكل: {name}")

    shape_list.currentRowChanged.connect(on_select)

    def import_dxf_file():
        dxf_path, _ = QFileDialog.getOpenFileName(None, "اختر ملف DXF", "", "DXF Files (*.dxf)")
        if not dxf_path:
            return
        target = os.path.join(shapes_folder, os.path.basename(dxf_path))
        if dxf_path != target:
            with open(dxf_path, "rb") as src, open(target, "wb") as dst:
                dst.write(src.read())
        print(f"✅ تم استيراد: {os.path.basename(dxf_path)}")
        load_all_shapes_from_folder()

    reload_btn.clicked.connect(load_all_shapes_from_folder)
    import_btn.clicked.connect(import_dxf_file)
    preview_btn.clicked.connect(lambda: preview_extrude(page, parent.display))
    rotate_btn.clicked.connect(lambda: rotate_selected_shape_wrapper(page, parent))
    scale_btn.clicked.connect(lambda: scale_preview_shape_wrapper(page, parent))
    cut_btn.clicked.connect(lambda: apply_cut_core(parent, page))

    # ⚠️ لا تحميل عند البدء — فقط عند الضغط على "Reload" أو استيراد جديد
    print("⏸️ تم إنشاء صفحة Shape Manager بدون تحميل تلقائي للملفات.")
    if any(f.lower().endswith(".dxf") for f in os.listdir(shapes_folder)):
        print("🔍 [Startup] تم العثور على ملفات DXF — تحميل أولي...")
        load_all_shapes_from_folder()
    else:
        print("⏸️ [Startup] لا توجد ملفات DXF — الصفحة جاهزة بدون تحميل.")
    return page


