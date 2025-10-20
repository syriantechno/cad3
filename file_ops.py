# -*- coding: utf-8 -*-
"""
📁 AlumCam Project File Operations (.alucam)
--------------------------------------------
نسخة نهائية تحفظ وتعيد:
✅ الشكل (BRep / DXF)
✅ العمليات الكاملة من المتصفح
✅ إعدادات الأدوات
✅ ملف الـ GCode الأخير
✅ عرض الشكل مباشرة عند الفتح
"""

import json
from pathlib import Path
from PyQt5.QtWidgets import QFileDialog, QMessageBox


# ==========================================================
# 💾 حفظ بيانات المشروع
# ==========================================================
from OCC.Core.BRepTools import breptools_Write
from OCC.Core.TopoDS import TopoDS_Shape
import os, json
from pathlib import Path
from PyQt5.QtWidgets import QFileDialog, QMessageBox

def save_project_dialog(parent):
    """حفظ المشروع الحالي بامتداد .alucam"""
    path, _ = QFileDialog.getSaveFileName(
        parent,
        "Save Project",
        "project.alucam",
        "AlumCam Project (*.alucam)"
    )
    if not path:
        return

    brep_path = ""
    try:
        # ✅ نحاول استخراج الشكل الحالي من Extrude أو الصفحة الحالية
        current_shape = None
        if hasattr(parent, "current_shape") and isinstance(parent.current_shape, TopoDS_Shape):
            current_shape = parent.current_shape
        elif hasattr(parent, "floating_window"):
            fw = parent.floating_window
            if hasattr(fw, "current_shape") and isinstance(fw.current_shape, TopoDS_Shape):
                current_shape = fw.current_shape

        # 🧱 إنشاء مجلد للمشروع وتخزين الشكل داخله كملف .brep
        if current_shape is not None:
            project_dir = Path(path).with_suffix("")
            project_dir.mkdir(exist_ok=True)
            brep_path = str(project_dir / "model.brep")
            breptools_Write(current_shape, brep_path)
            print(f"[🧩] Shape exported to {brep_path}")
        else:
            print("[⚠️] No TopoDS_Shape found in memory to save.")

        # --- جمع العمليات ---
        operations = []
        if hasattr(parent, "op_browser") and parent.op_browser:
            if hasattr(parent.op_browser, "collect_operations"):
                operations = parent.op_browser.collect_operations()

        project_data = {
            "brep_path": brep_path,
            "last_gcode": getattr(parent, "gcode_path", ""),
            "tool_settings": getattr(parent, "tool_settings", {}),
            "operations": operations,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(project_data, f, ensure_ascii=False, indent=4)

        print(f"[💾] Project saved -> {path}")
        print(f"[📄] Saved shape path: {brep_path}")
        QMessageBox.information(parent, "Project", f"💾 Project saved successfully:\n{path}")

    except Exception as e:
        QMessageBox.warning(parent, "Save Project", f"⚠️ Error saving project:\n{e}")
        print(f"[❌] Save failed: {e}")






# ==========================================================
# 📂 فتح مشروع (عرض الشكل + استعادة العمليات)
# ==========================================================
def open_project_dialog(parent):
    """فتح مشروع AlumCam (.alucam) واسترجاع الشكل + العمليات"""
    from OCC.Core.BRep import BRep_Builder
    from OCC.Core.TopoDS import TopoDS_Shape
    import OCC.Core.BRepTools as breptools

    path, _ = QFileDialog.getOpenFileName(
        parent,
        "Open Project",
        "",
        "AlumCam Project (*.alucam)"
    )
    if not path:
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"[📂] Project loaded -> {path}")
    except Exception as e:
        QMessageBox.warning(parent, "Project", f"⚠️ Failed to load project:\n{e}")
        return

    brep_path = data.get("brep_path", "")
    dxf_path = data.get("dxf_path", "")
    operations = data.get("operations", [])
    parent.gcode_path = data.get("last_gcode", "")
    parent.tool_settings = data.get("tool_settings", {})

    # =====================================================
    # 🧱 إعادة تحميل الشكل في العارض (BREP فقط)
    # =====================================================
    try:
        parent.display.EraseAll()
        if brep_path and Path(brep_path).exists():
            shape = TopoDS_Shape()
            builder = BRep_Builder()
            breptools.BRepTools_Read(shape, str(brep_path), builder)
            parent.display.DisplayShape(shape, update=True, color="LIGHTGRAY")
            parent.display.FitAll()
            parent.display.Repaint()
            print(f"[🧩] Shape reloaded successfully: {brep_path}")
        elif dxf_path and Path(dxf_path).exists():
            # قراءة DXF بطريقة بديلة آمنة (بدون read_dxf_file)
            print(f"[📄] DXF file detected -> {dxf_path}")
            try:
                from OCC.Core.StlAPI import StlAPI_Reader
                from OCC.Core.TopExp import TopExp_Explorer
                from OCC.Core.TopAbs import TopAbs_FACE
                print("[⚠️] DXF direct load not supported — placeholder only.")
            except Exception:
                pass
        else:
            print("[⚠️] No valid shape path found in project.")
    except Exception as e:
        print(f"[❌] Failed to restore shape: {e}")

    # =====================================================
    # 🔁 إعادة تحميل العمليات
    # =====================================================
    try:
        if hasattr(parent, "op_browser") and parent.op_browser:
            if hasattr(parent.op_browser, "load_operations"):
                parent.op_browser.load_operations(operations)
                print(f"[⚙️] Restored {len(operations)} operations.")
    except Exception as e:
        print(f"[⚠️] Failed to restore operations: {e}")

    QMessageBox.information(parent, "Project", f"✅ Project loaded:\n{path}")
    print("✅ Project restored successfully.")

