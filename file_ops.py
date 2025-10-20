import os, json, zipfile
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QTimer
from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_Reader, STEPControl_AsIs
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.TopoDS import TopoDS_Shape
# ========== تأكد من وجود لاحقة ==========
def ensure_extension(path, ext):
    if not path.lower().endswith(ext):
        path += ext
    return path

# ========== حفظ مشروع بصيغة alucam (STEP داخليًا) ==========
def save_file(shape, path, metadata):
    path = ensure_extension(path, ".alucam")

    if shape is None or shape.IsNull():
        print("❌ الشكل غير صالح للحفظ")
        return

    temp_dir = ".__alucam_temp__"
    os.makedirs(temp_dir, exist_ok=True)

    step_path = os.path.join(temp_dir, "model.step")
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    status = writer.Write(step_path)

    if status != IFSelect_RetDone:
        print("❌ فشل في حفظ STEP داخل المشروع")
        return

    meta_path = os.path.join(temp_dir, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(step_path, "model.step")
        zf.write(meta_path, "metadata.json")

    for f in [step_path, meta_path]:
        if os.path.exists(f):
            os.remove(f)
    os.rmdir(temp_dir)

    print(f"✅ تم حفظ المشروع بصيغة alucam: {path}")

# ========== فتح نافذة الحفظ ==========
def save_file_dialog(parent):
    dlg = QFileDialog(parent, "Save Project")
    dlg.setAcceptMode(QFileDialog.AcceptSave)
    dlg.setNameFilter("Alucam Project (*.alucam)")
    dlg.setOption(QFileDialog.DontUseNativeDialog, True)
    dlg.selectFile("untitled.alucam")

    if dlg.exec_():
        path = dlg.selectedFiles()[0]
        path = ensure_extension(path, ".alucam")

        def _do_save():
            shape = getattr(parent, "loaded_shape", None)
            if shape is None or shape.IsNull():
                print("❌ لا يوجد شكل للحفظ")
                return

            metadata = {"name": "My Project"}
            save_file(shape, path, metadata)

        QTimer.singleShot(0, _do_save)


import os, json, zipfile
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.IFSelect import IFSelect_RetDone

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

    step_file = os.path.join(temp_dir, "model.step")
    reader = STEPControl_Reader()
    status = reader.ReadFile(step_file)
    if status != IFSelect_RetDone:
        print("❌ فشل في قراءة STEP داخل المشروع")
        return None, None

    reader.TransferRoots()
    shape = reader.OneShape()

    meta_file = os.path.join(temp_dir, "metadata.json")
    metadata = {}
    if os.path.exists(meta_file):
        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

    for f in [step_file, meta_file]:
        if os.path.exists(f):
            os.remove(f)
    os.rmdir(temp_dir)

    print(f"✅ تم فتح المشروع: {project_path}")
    return shape, metadata

from OCC.Core.StlAPI import StlAPI_Writer
from OCC.Core.TopoDS import TopoDS_Shape

def export_stl(shape: TopoDS_Shape, file_path: str):
    if shape is None or shape.IsNull():
        print("❌ الشكل غير صالح للتصدير")
        return

    writer = StlAPI_Writer()
    success = writer.Write(shape, file_path)

    if success:
        print(f"✅ تم تصدير STL إلى: {file_path}")
    else:
        print("❌ فشل في تصدير STL")


def open_file_dialog(parent):
    """فتح مشروع alucam من نافذة Open File بشكل آمن"""
    dlg = QFileDialog(parent, "Open Project")
    dlg.setAcceptMode(QFileDialog.AcceptOpen)
    dlg.setNameFilter("Alucam Project (*.alucam)")
    dlg.setOption(QFileDialog.DontUseNativeDialog, True)

    if dlg.exec_():
        path = dlg.selectedFiles()[0]

        def _do_load():
            try:
                shape, metadata = load_project(path)
                if shape:
                    parent.loaded_shape = shape

                    # ✅ عرض الشكل بطريقة آمنة
                    if hasattr(parent, "display_shape_with_axes"):
                        parent.display_shape_with_axes(shape)
                    elif hasattr(parent, "display") and hasattr(parent.display, "DisplayShape"):
                        parent.display.DisplayShape(shape, update=True)
                        print("🧭 تم عرض الشكل باستخدام DisplayShape")
                    else:
                        print("⚠️ لا توجد دالة عرض متاحة")

                    parent.metadata = metadata
                    print(f"📂 Metadata: {metadata}")
                else:
                    print("❌ فشل في تحميل المشروع")
            except Exception as e:
                print(f"🔥 خطأ أثناء تحميل المشروع: {e}")

        QTimer.singleShot(0, _do_load)




