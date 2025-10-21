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
from OCC.Core.BRep import BRep_Builder
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Display.SimpleGui import init_display

def open_project_dialog(parent):
    """تحميل مشروع AlumCam بامتداد .alucam"""
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
            project_data = json.load(f)

        brep_path = project_data.get("brep_path", "")
        operations = project_data.get("operations", [])
        print(f"[📂] Project loaded -> {path}")

        if not brep_path or not os.path.exists(brep_path):
            print("[⚠️] No valid BREP path in project.")
            QMessageBox.warning(parent, "Open Project", "⚠️ No valid shape file found in project.")
        else:
            shape = TopoDS_Shape()
            from OCC.Core.BRep import BRep_Builder
            from OCC.Core.BRepTools import breptools_Read
            builder = BRep_Builder()
            breptools_Read(shape, str(brep_path), builder)
            if shape.IsNull():
                raise ValueError("Failed to load BREP shape (null shape)")

            # عرض الشكل
            if hasattr(parent, "display"):
                parent.display.EraseAll()
                from OCC.Core.AIS import AIS_Shape
                ais_shape = AIS_Shape(shape)
                parent.display.Context.Display(ais_shape, True)
                parent.display.FitAll()
                print(f"[✅] Shape restored and displayed from: {brep_path}")

            parent.current_shape = shape  # احتفاظ بالشكل في الذاكرة

        # 🧠 استرجاع العمليات مع تمرير params دائمًا
        if operations:
            if hasattr(parent, "op_browser") and parent.op_browser and hasattr(parent.op_browser, "add_operation"):
                print(f"[🔁] Found {len(operations)} stored operations.")
                for op in operations:
                    try:
                        op_type = op.get("type", "Unknown")
                        op_name = op.get("name", "Unnamed")
                        params  = op.get("params", {}) or {}

                        # تمرير الإحداثيات إن وجدت
                        if op_type.lower().startswith("hole"):
                            x = params.get("x", 0); y = params.get("y", 0); z = params.get("z", 0)
                            dia = params.get("dia", 0); depth = params.get("depth", 0)
                            axis = params.get("axis", "Z"); tool = params.get("tool", "")
                            print(f"[TRACE] Hole params -> name={op_name}, pos=({x},{y},{z}), dia={dia}, depth={depth}, axis={axis}, tool={tool}")

                        parent.op_browser.add_operation(op_type, op_name, params)
                    except Exception as e:
                        print(f"[⚠️] Failed to reload operation: {e}")
                print(f"[✅] Operations restored to op_browser.")
            else:
                print("[⚠️] No suitable op_browser.add_operation found.")
        else:
            print("[ℹ️] No operations saved in project.")

        QMessageBox.information(parent, "Open Project", f"✅ Project restored successfully.")

    except Exception as e:
        QMessageBox.critical(parent, "Open Project", f"❌ Failed to open project:\n{e}")
        print(f"[❌] Failed to open project: {e}")



