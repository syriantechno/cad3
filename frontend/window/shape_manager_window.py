from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QLabel, QSizePolicy,
    QPushButton, QFormLayout, QComboBox, QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt
from pathlib import Path

from OCC.Core.AIS import AIS_Shape
from OCC.Core.gp import gp_Trsf, gp_Ax1, gp_Dir, gp_Vec
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

from dxf_tools import load_dxf_file


# ==============================
# 🧠 الدوال الهندسية
# ==============================

from OCC.Core.gp import gp_Trsf, gp_Ax1, gp_Vec, gp_Dir
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform

def prepare_shape_for_axis(shape, axis: str, x=0, y=0, z=0):
    """
    تجهيز الشكل حسب المحور المحدد:
    - تدوير الشكل إذا كان المحور X أو Z.
    - ترجمة الشكل إلى موضع الإسقاط (x, y, z).
    """
    axis = axis.upper()

    # 🌀 التدوير
    trsf_rot = gp_Trsf()
    if axis == "X":
        trsf_rot.SetRotation(gp_Ax1(gp_Vec(0, 0, 0), gp_Dir(0, 0, 1)), 1.5708)
    elif axis == "Z":
        trsf_rot.SetRotation(gp_Ax1(gp_Vec(0, 0, 0), gp_Dir(1, 0, 0)), -1.5708)
    # Y → لا حاجة للتدوير

    rotated = BRepBuilderAPI_Transform(shape, trsf_rot, True).Shape()

    # 📍 الترجمة لموضع الإسقاط
    trsf_move = gp_Trsf()
    trsf_move.SetTranslation(gp_Vec(x, y, z))
    moved = BRepBuilderAPI_Transform(rotated, trsf_move, True).Shape()

    return moved




def extrude_shape(shape, depth: float):
    return BRepPrimAPI_MakePrism(shape, gp_Vec(0, depth, 0)).Shape()


def cut_from_base(base_shape, tool_shape):
    return BRepAlgoAPI_Cut(base_shape, tool_shape).Shape()


# ==============================
# 🧭 الصفحة الرئيسية
# ==============================
def create_shape_manager_page(parent):
    # 🟢 1. تعريف الصفحة أولاً + حارس التهيئة
    page = QWidget()
    page.is_ready = False

    # تحديد مسار جذر المشروع تلقائيًا
    import os
    from pathlib import Path

    # 📌 المسار المطلق من مكان هذا الملف (shape_manager_window.py)
    CURRENT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
    shapes_dir = CURRENT_DIR / "library" / "shapes"
    shapes_dir.mkdir(parents=True, exist_ok=True)

    print("[DEBUG] shapes_dir =", shapes_dir)
    print("[DEBUG] Exists?", shapes_dir.exists())

    for f in shapes_dir.glob("*.dxf"):
        print("[DEBUG] DXF found:", f)

    # 🧭 2. التخطيط الأساسي (يمين/يسار)
    root = QHBoxLayout(page)
    root.setContentsMargins(10, 10, 10, 10)
    root.setSpacing(14)

    # ---------- اليمين: قائمة DXF ----------
    shape_list = QListWidget()
    shape_list.setMinimumWidth(200)
    shape_list.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    root.addWidget(shape_list, alignment=Qt.AlignRight)





    # ---------- اليسار: إعدادات الإسقاط ----------
    left_container = QWidget()
    left_layout = QVBoxLayout(left_container)
    left_layout.setAlignment(Qt.AlignTop)
    left_layout.setSpacing(10)

    lbl_name = QLabel("Shape: —")
    left_layout.addWidget(lbl_name)

    form = QFormLayout()

    # محور + عمق
    axis_selector = QComboBox()
    axis_selector.addItems(["Z", "Y", "X"])
    depth_input = QLineEdit("50")
    form.addRow("Axis:", axis_selector)
    form.addRow("Depth:", depth_input)

    # إدخال الإحداثيات
    x_input = QLineEdit("0")
    y_input = QLineEdit("0")
    z_input = QLineEdit("0")
    form.addRow("X:", x_input)
    form.addRow("Y:", y_input)
    form.addRow("Z:", z_input)

    # ربط المدخلات بالصفحة
    page.axis_selector = axis_selector
    page.depth_input = depth_input
    page.x_input = x_input
    page.y_input = y_input
    page.z_input = z_input

    left_layout.addLayout(form)

    apply_btn = QPushButton("✅ Apply Shape")
    left_layout.addWidget(apply_btn)

    root.addWidget(left_container, alignment=Qt.AlignLeft)

    # 🟡 متغيرات المعاينة
    page.shape_2d = None
    page.preview_ais = None

    display = parent.display

    # 🧠 3. دالة المعاينة الآمنة (مع الحارس)
    def update_preview():
        if not page.is_ready:
            return
        if page.shape_2d is None or page.shape_2d.IsNull():
            return

        # باقي منطق المعاينة...
        # (قراءة X/Y/Z, axis, depth + prepare_shape_for_axis + extrude + AIS_Shape)

    # 🧠 4. دالة تطبيق القص
    def on_apply():
        if page.shape_2d is None or page.shape_2d.IsNull():
            QMessageBox.warning(page, "Shape", "اختر شكل DXF أولاً.")
            return
        # باقي منطق القص باستخدام X/Y/Z والمحور...

    apply_btn.clicked.connect(on_apply)

    # 🧠 5. تحميل DXF من القائمة
    def on_select(row):
        if row < 0:
            return
        fname = shape_list.item(row).text()
        fpath = shapes_dir / fname
        lbl_name.setText(f"Shape: {fname}")
        print("[DEBUG] Trying to load:", fpath, "Exists?", fpath.exists())

        shape = load_dxf_file(str(fpath))
        if shape is None or shape.IsNull():
            QMessageBox.warning(page, "DXF", "فشل تحميل الشكل.")
            return

        page.shape_2d = shape
        update_preview()

    shape_list.currentRowChanged.connect(on_select)

    # 🧠 6. ربط الإشارات للمعاينة ← في النهاية فقط
    axis_selector.currentTextChanged.connect(update_preview)
    depth_input.textChanged.connect(update_preview)
    x_input.textChanged.connect(update_preview)
    y_input.textChanged.connect(update_preview)
    z_input.textChanged.connect(update_preview)

    # ✅ الصفحة أصبحت جاهزة الآن
    page.is_ready = True
    return page

