from PyQt5.QtWidgets import QWidget, QFormLayout, QListWidget, QLineEdit, QComboBox, QPushButton
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.gp import gp_Vec, gp_Trsf, gp_Ax1, gp_Dir, gp_Pnt
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from os.path import join
from dxf_loader import (load_dxf_file, extract_closed_faces_from_edges)  # تأكد أن الملف موجود في الجذر

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
        # تدوير 90° حول Y → من XY إلى YZ
        trsf.SetRotation(gp_Ax1(gp_Pnt(0,0,0), gp_Dir(0,1,0)), -1.5708)
    elif axis.upper() == 'Y':
        # تدوير 90° حول X → من XY إلى XZ
        trsf.SetRotation(gp_Ax1(gp_Pnt(0,0,0), gp_Dir(1,0,0)), 1.5708)
    # Z لا يحتاج تدوير
    return BRepBuilderAPI_Transform(shape, trsf, True).Shape()

def translate_shape(shape: TopoDS_Shape, x: float, y: float, z: float) -> TopoDS_Shape:
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(x, y, z))
    return BRepBuilderAPI_Transform(shape, trsf, True).Shape()

def cut_shape(base: TopoDS_Shape, cutter: TopoDS_Shape) -> TopoDS_Shape:
    return BRepAlgoAPI_Cut(base, cutter).Shape()

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

        shape_3d = extrude_shape(page.shape_2d, depth, axis)
        shape_3d = translate_shape(shape_3d, x, y, z)

        display.Context.EraseAll(False)
        display.DisplayShape(shape_3d, update=True)
        print("✅ تم عرض الشكل المسقط بنجاح")

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

    layout.addRow("Depth:", depth_input)
    layout.addRow("Axis:", axis_selector)
    layout.addRow("X:", x_input)
    layout.addRow("Y:", y_input)
    layout.addRow("Z:", z_input)

    preview_btn = QPushButton("👁 Preview Extrude")
    apply_cut_btn = QPushButton("💥 Apply Cut")
    layout.addRow(preview_btn)
    layout.addRow(apply_cut_btn)

    page.shape_list = shape_list
    page.depth_input = depth_input
    page.axis_selector = axis_selector
    page.x_input = x_input
    page.y_input = y_input
    page.z_input = z_input
    page.shape_2d = None
    page.test_shapes = {}

    # تحميل شكل DXF من المكتبة

    dxf_path = join("frontend", "window", "library", "shapes", "60X60 8N.dxf")
    raw_shape = load_dxf_file(dxf_path)
    face_shape = extract_closed_faces_from_edges(raw_shape)

    if face_shape and not face_shape.IsNull():
        page.test_shapes["60X60 8N"] = face_shape
        shape_list.addItem("60X60 8N")
        print("✅ تم تحميل وتحويل الشكل إلى Face")
    elif raw_shape and not raw_shape.IsNull():
        page.test_shapes["60X60 8N"] = raw_shape
        shape_list.addItem("60X60 8N")
        print("⚠️ تم تحميل الشكل كـ Compound بدون تحويل إلى Face")
    else:
        print("❌ فشل في تحميل أو تحويل شكل DXF")

    def on_select(row):
        name = shape_list.item(row).text()
        shape = page.test_shapes.get(name)
        if shape is None or shape.IsNull():
            print(f"❌ الشكل {name} غير صالح")
            return
        page.shape_2d = shape
        print(f"📐 تم اختيار الشكل: {name}")

    shape_list.currentRowChanged.connect(on_select)

    def apply_cut():
        try:
            if page.shape_2d is None or page.shape_2d.IsNull():
                print("❌ لا يوجد شكل 2D صالح")
                return

            depth = float(depth_input.text())
            axis = axis_selector.currentText()
            x = float(x_input.text())
            y = float(y_input.text())
            z = float(z_input.text())

            cutter = extrude_shape(page.shape_2d, depth, axis)
            cutter = translate_shape(cutter, x, y, z)

            base = getattr(parent, "loaded_shape", None)
            if base is None or base.IsNull():
                print("❌ لا يوجد شكل أساسي للقطع")
                return

            result = cut_shape(base, cutter)
            parent.loaded_shape = result
            parent.display_shape_with_axes(result)
            print("✅ تم تنفيذ القطع بنجاح")

        except Exception as e:
            print(f"🔥 كراش أثناء تنفيذ القطع: {e}")

    preview_btn.clicked.connect(lambda: preview_extrude(page, parent.display))
    apply_cut_btn.clicked.connect(apply_cut)

    return page