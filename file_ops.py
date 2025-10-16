# frontend/file_ops.py
import os, json, zipfile
from OCC.Core import BRepTools
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.STEPControl import STEPControl_Reader, STEPControl_Writer, STEPControl_AsIs
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.StlAPI import StlAPI_Writer

# ========== حفظ مشروع بصيغة alucam ==========

from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QTimer

# frontend/file_ops.py


def save_file_dialog(parent):
    print("🟡 save_file_dialog() CALLED")

    dlg = QFileDialog(parent, "Save Project")
    dlg.setAcceptMode(QFileDialog.AcceptSave)
    dlg.setNameFilter("Alucam Project (*.alucam)")
    dlg.setOption(QFileDialog.DontUseNativeDialog, True)
    dlg.selectFile("untitled.alucam")

    if dlg.exec_():
        path = dlg.selectedFiles()[0]
        print("🟢 Path selected:", path)

        def _do_save():
            shape = parent.current_shape
            if shape is None or shape.IsNull():
                print("❌ الشكل غير صالح للحفظ")
                return

            metadata = parent.get_metadata() if hasattr(parent, "get_metadata") else {"name": "My Project"}
            save_file(shape, path, metadata)

        QTimer.singleShot(0, _do_save)


def save_file(shape, file_path):
    if shape is None or shape.IsNull():
        print("❌ الشكل غير صالح للحفظ")
        return

    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    status = writer.Write(file_path)

    if status == IFSelect_RetDone:
        print(f"✅ تم حفظ STEP إلى: {file_path}")
    else:
        print("❌ فشل في حفظ STEP")





# ========== فتح مشروع alucam ==========
def load_project(project_path: str):
    if not project_path.endswith(".alucam"):
        print("⚠️ الملف ليس بصيغة alucam")
        return None, None

    if not zipfile.is_zipfile(project_path):
        print("❌ الملف ليس أرشيف alucam صالح")
        return None, None

    temp_dir = ".__alucam_temp__"
    os.makedirs(temp_dir, exist_ok=True)

    with zipfile.ZipFile(project_path, "r") as zf:
        zf.extractall(temp_dir)

    shape = TopoDS_Shape()
    brep_file = os.path.join(temp_dir, "model.brep")
    if not BRepTools.breptools_Read(shape, brep_file, None):
        print("❌ فشل في قراءة model.brep")
        return None, None

    meta_file = os.path.join(temp_dir, "metadata.json")
    metadata = {}
    if os.path.exists(meta_file):
        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

    for f in [brep_file, meta_file]:
        if os.path.exists(f):
            os.remove(f)
    os.rmdir(temp_dir)

    print(f"✅ تم فتح المشروع: {project_path}")
    return shape, metadata


# ========== استيراد STEP ==========
def import_step(file_path: str):
    reader = STEPControl_Reader()
    status = reader.ReadFile(file_path)
    if status == IFSelect_RetDone:
        reader.TransferRoots()
        shape = reader.OneShape()
        print(f"✅ تم استيراد STEP: {file_path}")
        return shape
    else:
        print("❌ فشل في استيراد STEP")
        return None


# ========== تصدير STEP ==========
def export_step(shape: TopoDS_Shape, file_path: str):
    if shape.IsNull():
        print("⚠️ لا يوجد شكل لتصديره")
        return
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    status = writer.Write(file_path)
    if status == IFSelect_RetDone:
        print(f"✅ تم تصدير STEP إلى: {file_path}")
    else:
        print("❌ فشل في تصدير STEP")


# ========== تصدير STL ==========
def export_stl(shape: TopoDS_Shape, file_path: str):
    if shape.IsNull():
        print("⚠️ لا يوجد شكل لتصديره")
        return
    writer = StlAPI_Writer()
    writer.Write(shape, file_path)
    print(f"✅ تم تصدير STL إلى: {file_path}")
