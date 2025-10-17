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
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QListWidget, QSizePolicy,
    QVBoxLayout, QLabel, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt

# استيراد أدوات DXF
from dxf_tools import load_dxf_file
from OCC.Core.gp import gp_Trsf, gp_Ax1, gp_Dir
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.gp import gp_Vec
from OCC.Display.SimpleGui import init_display

def create_shape_manager_page(parent):
    # 🟢 1. تعريف الصفحة أولاً + حارس التهيئة
    page = QWidget()
    page.is_ready = False

    # 🧭 2. التخطيط الأساسي (يمين/يسار)
    root = QHBoxLayout(page)
    root.setContentsMargins(10, 10, 10, 10)
    root.setSpacing(14)

    # ---------- اليمين: قائمة DXF ----------
    shape_list = QListWidget()
    shape_list.setMinimumWidth(200)
    shape_list.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    root.addWidget(shape_list, alignment=Qt.AlignRight)

    # تحميل ملفات DXF من مكتبة الأشكال
    shapes_dir = Path("frontend/window/library/shapes")  # عدّل المسار حسب مكان ملفاتك الحقيقي
    shapes_dir.mkdir(parents=True, exist_ok=True)
    print("[DEBUG] Scanning shapes dir:", shapes_dir.resolve())

    files = list(shapes_dir.glob("*.[dD][xX][fF]"))
    if not files:
        print("[DEBUG] No DXF files found in shape library folder.")
    else:
        for f in files:
            print("[DEBUG] found:", f.name)
            shape_list.addItem(f.name)

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

    left_layout.addLayout(form)

    apply_btn = QPushButton("✅ Apply Shape")
    left_layout.addWidget(apply_btn)

    root.addWidget(left_container, alignment=Qt.AlignLeft)

    # 🟡 متغيرات المعاينة
    page.shape_2d = None
    page.preview_ais = None

    # 🧭 3. الحصول على display من الـ parent
    display = getattr(parent, "display", None)
    if display is None:
        print("[DEBUG] Display is None! Shape preview will not work.")

    # 🧩 4. دالة تحديث المعاينة
    # 🧩 4. دالة تحديث المعاينة (Rotation + Move فقط)
    from OCC.Core.AIS import AIS_Shape

    from OCC.Core.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir, gp_Vec
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCC.Core.AIS import AIS_Shape

    def update_preview(page, display):
        """
        🧠 تحديث المعاينة التفاعلية لشكل DXF بعد اختيار المحور / الإزاحة.
        - يحذف المعاينة القديمة إن وجدت
        - يدور الشكل حسب المحور المختار
        - يطبّق إزاحة حسب قيم X/Y/Z
        - يعرض الشكل الجديد بأسلوب Wireframe
        """
        # 🟢 تأكد أن الصفحة مهيأة
        if not getattr(page, "is_ready", False):
            return

        if page.shape_2d is None or page.shape_2d.IsNull():
            print("[DEBUG] No base 2D shape for preview")
            return

        if display is None:
            print("[DEBUG] Display is None — cannot preview")
            return

        # 🧹 إزالة المعاينة القديمة بأمان
        if page.preview_ais is not None:
            try:
                if not page.preview_ais.IsNull():
                    display.Context.Remove(page.preview_ais, True)
            except Exception as e:
                print("[DEBUG] Failed to remove old preview:", e)
            page.preview_ais = None

        # 🧭 قراءة القيم من المدخلات
        try:
            x_val = float(page.x_input.text())
            y_val = float(page.y_input.text())
            z_val = float(page.z_input.text())
        except ValueError:
            print("[DEBUG] Invalid XYZ input values")
            return

        axis = page.axis_selector.currentText()
        depth_val = float(page.depth_input.text()) if page.depth_input.text() else 50.0

        try:
            # 🌀 إنشاء ترانسفورم للدوران
            trsf = gp_Trsf()
            if axis == "X":
                trsf.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), 1.5708)
            elif axis == "Y":
                trsf.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), -1.5708)
            # Z لا تحتاج دوران

            rotated_shape = BRepBuilderAPI_Transform(page.shape_2d, trsf, True).Shape()

            # 🧭 إزاحة الشكل للموقع المحدد
            move_trsf = gp_Trsf()
            move_trsf.SetTranslation(gp_Vec(x_val, y_val, z_val))
            moved_shape = BRepBuilderAPI_Transform(rotated_shape, move_trsf, True).Shape()

            # 🟡 عرض الشكل الجديد كـ Wireframe
            ais_preview = AIS_Shape(moved_shape)
            display.Context.Display(ais_preview, True)
            display.Context.SetDisplayMode(ais_preview, 0, False)  # 0 = Wireframe
            page.preview_ais = ais_preview

            display.FitAll()

        except Exception as e:
            print("[ERROR] update_preview failed:", e)
            return

    # 🧩 5. دالة تحميل الشكل عند الاختيار
    # 🧩 5. دالة تحميل الشكل عند الاختيار من القائمة
    def on_select(row):
        if row < 0:
            return
        fname = shape_list.item(row).text()
        fpath = shapes_dir / fname
        lbl_name.setText(f"Shape: {fname}")

        shape = load_dxf_file(str(fpath))
        if shape is None or shape.IsNull():
            QMessageBox.warning(page, "DXF", f"فشل تحميل الشكل: {fname}")
            return

        # ✅ حفظ الشكل بدون إكسترود
        page.shape_2d = shape

        if display:
            # إزالة أي معاينة قديمة
            if page.preview_ais is not None:
                display.Context.Remove(page.preview_ais, True)
                page.preview_ais = None
            ais = display.DisplayShape(page.shape_2d, update=True)
            page.preview_ais = ais
            display.FitAll()

    shape_list.currentRowChanged.connect(on_select)

    # ربط المعاينة بالمدخلات
    depth_input.textChanged.connect(update_preview)
    x_input.textChanged.connect(update_preview)
    y_input.textChanged.connect(update_preview)
    z_input.textChanged.connect(update_preview)
    axis_selector.currentTextChanged.connect(update_preview)

    # 🟢 تفعيل الصفحة بعد اكتمال التهيئة
    page.is_ready = True
    return page


