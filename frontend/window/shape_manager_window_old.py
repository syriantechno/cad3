from PyQt5.QtWidgets import QWidget, QFormLayout, QListWidget, QLineEdit, QComboBox, QPushButton, QFileDialog
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.gp import gp_Vec, gp_Trsf, gp_Ax1, gp_Dir, gp_Pnt
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from os.path import basename
import json
from dxf_loader import smart_load_dxf

def extrude_shape(shape_2d: TopoDS_Shape, depth: float, axis: str) -> TopoDS_Shape:
    shape_oriented = orient_shape_to_axis(shape_2d, axis)
    axis_map = {
        'X': gp_Vec(depth, 0, 0),
        'Y': gp_Vec(0, depth, 0),
        'Z': gp_Vec(0, 0, depth)
    }
    vec = axis_map.get(axis.upper(), gp_Vec(0, 0, depth))
    return BRepPrimAPI_MakePrism(shape_oriented, vec).Shape()

def orient_shape_to_axis(shape: TopoDS_Shape, axis: str) -> TopoDS_Shape:
    trsf = gp_Trsf()
    if axis.upper() == 'X':
        trsf.SetRotation(gp_Ax1(gp_Pnt(0,0,0), gp_Dir(0,1,0)), -1.5708)
    elif axis.upper() == 'Y':
        trsf.SetRotation(gp_Ax1(gp_Pnt(0,0,0), gp_Dir(1,0,0)), 1.5708)
    return BRepBuilderAPI_Transform(shape, trsf, True).Shape()

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
    brepbndlib_Add(shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return gp_Pnt((xmin + xmax)/2, (ymin + ymax)/2, (zmin + zmax)/2)

def scale_shape(shape: TopoDS_Shape, factor: float) -> TopoDS_Shape:
    center = get_shape_center(shape)
    trsf = gp_Trsf()
    trsf.SetScale(center, factor)
    return BRepBuilderAPI_Transform(shape, trsf, True).Shape()

def get_shape_size(shape: TopoDS_Shape, axis: str) -> float:
    box = Bnd_Box()
    brepbndlib_Add(shape, box)
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
    brepbndlib_Add(shape, box)
    _, _, zmin, _, _, _ = box.Get()
    return zmin

def show_shape(display, shape: TopoDS_Shape):
    actor = AIS_Shape(shape)
    actor.SetColor(Quantity_Color(0.2, 0.4, 0.8, Quantity_TOC_RGB))
    display.Context.Display(actor, True)
    return actor

def apply_transformations(shape: TopoDS_Shape, scale_factor: float, rotation_axis: str, rotation_angle: float, x: float, y: float, z: float) -> TopoDS_Shape:
    if scale_factor != 1.0:
        shape = scale_shape(shape, scale_factor)
    if rotation_angle != 0:
        shape = rotate_shape(shape, rotation_axis, rotation_angle)
    shape = translate_shape(shape, x, y, z)
    return shape

def preview_extrude(page, display):
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

        if hasattr(page, "preview_actor") and page.preview_actor:
            display.Context.Remove(page.preview_actor, False)

        shape_3d = extrude_shape(page.shape_2d, depth, axis)

        current_size = get_shape_size(shape_3d, scale_axis)
        scale_factor = scale_target / current_size if current_size > 0 else 1.0

        zmin = get_z_min(shape_3d)
        shape_3d = apply_transformations(shape_3d, scale_factor, axis, rotation_angle, x, y, z - zmin)

        page.preview_shape = shape_3d
        page.preview_actor = show_shape(display, shape_3d)
        print("✅ تم عرض الشكل بعد تطبيق كل التحويلات")

    except Exception as e:
        print(f"🔥 كراش أثناء المعاينة: {e}")

def create_shape_manager_page(parent):
    page = QWidget()
    layout = QFormLayout(page)

    shape_list = QListWidget()
    layout.addRow("📚 Shape Library:", shape_list)

    depth_input = QLineEdit("20")
    axis_selector = QComboBox()
    axis_selector.addItems(["X", "Y", "Z"])
    x_input = QLineEdit("0")
    y_input = QLineEdit("0")
    z_input = QLineEdit("0")
    rotate_angle_input = QLineEdit("90")
    scale_input = QLineEdit("30")
    scale_axis_selector = QComboBox()
    scale_axis_selector.addItems(["X", "Y", "Z"])

    layout.addRow("Depth:", depth_input)
    layout.addRow("Axis:", axis_selector)
    layout.addRow("X:", x_input)
    layout.addRow("Y:", y_input)
    layout.addRow("Z:", z_input)
    layout.addRow("Rotation Angle (°):", rotate_angle_input)
    layout.addRow("Target Size (mm):", scale_input)
    layout.addRow("Scale Axis:", scale_axis_selector)

    preview_btn = QPushButton("👁 Preview Extrude")
    rotate_btn = QPushButton("🔄 Rotate Shape")
    scale_btn = QPushButton("📐 Scale Shape")
    apply_cut_btn = QPushButton("💥 Apply Cut")
    btn_import_dxf = QPushButton("📂 استيراد ملف DXF")

    layout.addRow(preview_btn)
    layout.addRow(rotate_btn)
    layout.addRow(scale_btn)
    layout.addRow(apply_cut_btn)
    layout.addRow(btn_import_dxf)

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

    def on_select(row):
        name = shape_list.item(row).text()
        shape = page.test_shapes.get(name)
        if shape and not shape.IsNull():
            page.shape_2d = shape
            print(f"📐 تم اختيار الشكل: {name}")

    def apply_cut():
        try:
            cutter = page.preview_shape
            base = getattr(parent, "loaded_shape", None)
            if cutter and base and not cutter.IsNull() and not base.IsNull():
                result = BRepAlgoAPI_Cut(base, cutter).Shape()
                parent.loaded_shape = result
                parent.display_shape_with_axes(result)
                print("✅ تم تنفيذ القطع بنجاح")
        except Exception as e:
            print(f"🔥 كراش أثناء تنفيذ القطع: {e}")

    def rotate_selected_shape():
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

    def scale_preview_shape():
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

    def import_dxf_file(page, shape_list):
        dxf_path, _ = QFileDialog.getOpenFileName(None, "اختر ملف DXF", "", "DXF Files (*.dxf)")
        if not dxf_path:
            return
        shape = smart_load_dxf(dxf_path)
        if shape and not shape.IsNull():
            name = basename(dxf_path).replace(".dxf", "")
            page.test_shapes[name] = shape
            shape_list.addItem(name)
            page.shape_2d = shape
            with open("recent_shapes.json", "w") as f:
                json.dump({"last_dxf": dxf_path}, f)
            print(f"✅ تم تحميل الشكل '{name}' من DXF")

    def load_last_shape():
        try:
            with open("recent_shapes.json", "r") as f:
                path = json.load(f).get("last_dxf")
                if path:
                    shape = smart_load_dxf(path)
                    if shape and not shape.IsNull():
                        name = basename(path).replace(".dxf", "")
                        page.test_shapes[name] = shape
                        shape_list.addItem(name)
                        page.shape_2d = shape
                        print(f"✅ تم تحميل الشكل السابق '{name}' تلقائيًا")
        except Exception as e:
            print(f"⚠️ لا يوجد شكل محفوظ أو فشل التحميل: {e}")

    preview_btn.clicked.connect(lambda: preview_extrude(page, parent.display))
    rotate_btn.clicked.connect(rotate_selected_shape)
    scale_btn.clicked.connect(scale_preview_shape)
    apply_cut_btn.clicked.connect(apply_cut)
    btn_import_dxf.clicked.connect(lambda: import_dxf_file(page, shape_list))
    shape_list.currentRowChanged.connect(on_select)

    load_last_shape()
    return page