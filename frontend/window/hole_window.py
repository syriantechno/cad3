from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QHBoxLayout, QSpacerItem, QSizePolicy, QLabel,
    QMessageBox, QFrame, QApplication, QDoubleSpinBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer
from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

from tools.geometry_ops import add_hole, preview_hole
from tools.color_utils import display_with_fusion_style
from tools.dimensions import measure_shape, hole_reference_dimensions, hole_size_dimensions
from frontend.window.tools_db import ToolsDB

from OCC.Core.Bnd import Bnd_Box
from OCC.Core.TopAbs import TopAbs_VERTEX
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.BRep import BRep_Tool

import os, json
from pathlib import Path

ENABLE_PREVIEW_DIMS = True
PREFS_PATH = Path("data/hole_prefs.json")
IMAGES_DIR = Path("tools/images")

def _bbox_extents(shape):
    try:
        from OCC.Core.BRepBndLib import brepbndlib
        box = Bnd_Box()
        brepbndlib.Add(shape, box, True)
        return box.Get()
    except Exception:
        pass
    try:
        from OCC.Core.BRepBndLib import BRepBndLib_Add
        box = Bnd_Box()
        try:
            BRepBndLib_Add(shape, box, True)
        except TypeError:
            BRepBndLib_Add(shape, box)
        return box.Get()
    except Exception:
        pass
    try:
        xmin = ymin = zmin = float("inf")
        xmax = ymax = zmax = float("-inf")
        exp = TopExp_Explorer(shape, TopAbs_VERTEX)
        any_vertex = False
        while exp.More():
            v = exp.Current()
            p = BRep_Tool.Pnt(v)
            x, y, z = p.X(), p.Y(), p.Z()
            xmin = min(xmin, x); ymin = min(ymin, y); zmin = min(zmin, z)
            xmax = max(xmax, x); ymax = max(ymax, y); zmax = max(zmax, z)
            any_vertex = True
            exp.Next()
        if any_vertex:
            return (xmin, ymin, zmin, xmax, ymax, zmax)
    except Exception:
        pass
    print("[BBOX] ⚠️ Failed to compute bbox.")
    return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

SAFE_A_CLEARANCE = 30.0

class HoleWindow(QWidget):
    def __init__(self, parent=None, display=None, shape_getter=None, shape_setter=None):
        super().__init__(parent)
        self.display = display
        self.get_shape = shape_getter
        self.set_shape = shape_setter
        self._hole_preview_ais = None
        self._preview_dim_shapes = []
        self._last_tool_id = None

        self._build_ui()
        self._connect_live_preview()
        self._restore_last_tool()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # أدوات الحفر
        top_tools_layout = QHBoxLayout()
        self.tool_combo = QComboBox()
        btn_refresh = QPushButton("↻ Refresh")
        btn_refresh.clicked.connect(self._load_tools)
        top_tools_layout.addWidget(self.tool_combo)
        top_tools_layout.addWidget(btn_refresh)
        form.addRow("Tool:", top_tools_layout)

        self.tool_image = QLabel("(No Image)")
        self.tool_image.setAlignment(Qt.AlignCenter)
        self.tool_image.setStyleSheet("background:#f8f8f8;border:1px solid #ccc;border-radius:6px;min-height:100px;")
        form.addRow("Tool Preview:", self.tool_image)

        # المدخلات
        self.x_input = QLineEdit("0")
        self.y_input = QLineEdit("0")
        self.z_input = QLineEdit("0")
        self.dia_input = QLineEdit("6")
        self.depth_input = QLineEdit("20")
        self.preview_len_input = QLineEdit("50")
        self.angle_a_combo = QComboBox()
        self.angle_a_combo.addItems(["-90°", "0°", "+90°"])
        self.angle_a_combo.setCurrentText("0°")

        # ✨ حقل المسافة الآمنة
        self.clearance_input = QDoubleSpinBox()
        self.clearance_input.setRange(0.0, 200.0)
        self.clearance_input.setValue(SAFE_A_CLEARANCE)
        self.clearance_input.setSuffix(" mm")
        self.clearance_input.setSingleStep(5.0)

        form.addRow("X:", self.x_input)
        form.addRow("Y:", self.y_input)
        form.addRow("Z:", self.z_input)
        form.addRow("Diameter:", self.dia_input)
        form.addRow("Depth:", self.depth_input)
        form.addRow("Preview Length:", self.preview_len_input)
        form.addRow("Spindle Angle (A):", self.angle_a_combo)
        form.addRow("Safe Clearance:", self.clearance_input)
        layout.addLayout(form)

        self.preview_btn = QPushButton("Preview Hole")
        self.apply_btn = QPushButton("Apply Hole")
        self.center_btn = QPushButton("Center View")

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.preview_btn)
        btn_row.addWidget(self.apply_btn)
        btn_row.addWidget(self.center_btn)
        layout.addLayout(btn_row)
        self.setLayout(layout)

        self.preview_btn.clicked.connect(self._update_preview)
        self.apply_btn.clicked.connect(self.apply_hole)
        self.center_btn.clicked.connect(self._center_view)
        self._load_tools()

    def _connect_live_preview(self):
        for w in (
            self.x_input, self.y_input, self.z_input,
            self.dia_input, self.depth_input, self.preview_len_input
        ):
            w.textChanged.connect(self._update_preview)
        self.angle_a_combo.currentIndexChanged.connect(self._update_preview)
        self.clearance_input.valueChanged.connect(self._update_preview)

    def _get_values(self):
        try:
            x = float(self.x_input.text())
            y = float(self.y_input.text())
            z = float(self.z_input.text())
            dia = float(self.dia_input.text())
            depth = float(self.depth_input.text())
            preview_len = float(self.preview_len_input.text())
            tool = self.tool_combo.currentData()
            angle_map = {"-90°": -90.0, "0°": 0.0, "+90°": 90.0}
            a_angle = angle_map.get(self.angle_a_combo.currentText(), 0.0)
            axis = "Z" if abs(a_angle) < 1e-6 else "Y"
            self._a_angle = a_angle
            clearance = self.clearance_input.value()
            return x, y, z, dia, depth, preview_len, axis, tool, clearance
        except ValueError:
            return None

    def _load_tools(self):
        """تحميل أدوات الحفر من قاعدة البيانات وعرض الصور."""
        try:
            db = ToolsDB()
            tools = db.list_tools()
            self.tool_combo.clear()
            for t in tools:
                display_name = f"{t['name']} ⌀{t['diameter']}mm"
                self.tool_combo.addItem(display_name, t)
            if tools:
                self._show_tool_image(tools[0])
        except Exception as e:
            print(f"[TOOLS] فشل تحميل الأدوات: {e}")

    def _show_tool_image(self, tool):
        """عرض صورة الأداة المحددة."""
        try:
            img_path = tool.get("image_path", "")
            if not img_path or not os.path.exists(img_path):
                self.tool_image.setText("(No Image)")
                self.tool_image.setPixmap(QPixmap())
                return
            pix = QPixmap(img_path)
            self.tool_image.setPixmap(pix.scaledToHeight(100, Qt.SmoothTransformation))
        except Exception as e:
            print(f"[IMG] Error displaying tool image: {e}")

    def _restore_last_tool(self):
        """استرجاع آخر أداة تم استخدامها من الإعدادات السابقة."""
        try:
            if not PREFS_PATH.exists():
                return
            with open(PREFS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            last_tool_id = data.get("last_tool_id")
            if not last_tool_id:
                return
            for i in range(self.tool_combo.count()):
                tool = self.tool_combo.itemData(i)
                if tool and tool.get("id") == last_tool_id:
                    self.tool_combo.setCurrentIndex(i)
                    self._show_tool_image(tool)
                    break
        except Exception as e:
            print(f"[RESTORE] فشل استرجاع آخر أداة: {e}")

    def _save_last_tool(self):
        """حفظ آخر أداة تم اختيارها في ملف الإعدادات."""
        try:
            tool = self.tool_combo.currentData()
            if not tool:
                return
            data = {"last_tool_id": tool.get("id")}
            with open(PREFS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[SAVE] فشل حفظ آخر أداة: {e}")

    def _update_preview(self):
        """عرض المعاينة الحية مع دوران الأداة حسب زاوية A ومنع التصادم."""
        vals = self._get_values()
        if not vals:
            return
        x, y, z, dia, depth, preview_len, axis, tool, clearance = vals
        base_shape = self.get_shape()
        if not base_shape or base_shape.IsNull():
            return

        a_angle = getattr(self, "_a_angle", 0.0)
        xmin, ymin, zmin, xmax, ymax, zmax = _bbox_extents(base_shape)

        # 🔧 حساب المركز واتجاه المعاينة
        if abs(a_angle) < 1e-3:
            # 🔹 A = 0° (من الأعلى)
            top = zmax
            cx, cy, cz = x, y, top + clearance + (preview_len / 2.0)
            axis = "Z"
            print(f"[PREVIEW] A=0° → Z-axis, top={top:.2f}, cz={cz:.2f}")


        elif a_angle > 0:

            # 🔹 A = +90° (من جهة اليمين - حول Y)

            side = xmin

            cx = side + clearance + (preview_len / 2.0)

            cy, cz = y, z

            axis = "X"

            print(f"[PREVIEW] A=+90° → +X, side={side:.2f}, cx={cx:.2f}")


        else:

            # 🔹 A = -90° (من جهة اليسار - حول Y)

            side = xmax

            cx = side - clearance - (preview_len / 2.0)

            cy, cz = y, z

            axis = "X"

            print(f"[PREVIEW] A=-90° → -X, side={side:.2f}, cx={cx:.2f}")

        # 🧹 تنظيف المعاينة السابقة
        try:
            if self._hole_preview_ais:
                self.display.Context.Erase(self._hole_preview_ais, False)
        except Exception:
            pass
        self._hole_preview_ais = None

        # 🧱 إنشاء الشكل التمهيدي للمعاينة
        hole_shape = preview_hole(base_shape, cx, cy, cz, dia, axis, preview_len)
        if not hole_shape or hole_shape.IsNull():
            print("[PREVIEW] ⚠️ فشل إنشاء شكل المعاينة.")
            return

        # 🎨 عرض المعاينة باللون الأحمر الشفاف
        ais = AIS_Shape(hole_shape)
        ais.SetColor(Quantity_Color(1.0, 0.0, 0.0, Quantity_TOC_RGB))
        ais.SetTransparency(0.5)
        self.display.Context.Display(ais, False)
        self._hole_preview_ais = ais

        self.display.Context.UpdateCurrentViewer()
        print(f"[PREVIEW] ✅ Angle={a_angle}°, Axis={axis}, Clearance={clearance:.1f}mm, Len={preview_len:.1f}mm")

    def apply_hole(self):
        """تطبيق عملية الحفر فعليًا داخل المجسم حسب زاوية A (تسجيل هندسي صحيح)."""
        vals = self._get_values()
        if not vals:
            QMessageBox.warning(self, "Hole", "⚠️ قيم غير صالحة.")
            return None

        x, y, z, dia, depth, _, axis, tool, _clearance_unused = vals
        base_shape = self.get_shape()
        if not base_shape or base_shape.IsNull():
            QMessageBox.warning(self, "Hole", "⚠️ لا يوجد شكل صالح للحفر.")
            return None

        try:
            # زاوية محور A المحددة (-90 / 0 / +90)
            a_angle = getattr(self, "_a_angle", 0.0)

            # حدود المجسم (اعتمادًا على الشكل فقط)
            xmin, ymin, zmin, xmax, ymax, zmax = _bbox_extents(base_shape)

            # 🔁 في بعض النماذج "اليمين" هو Xmin، وفي أخرى Xmax.
            # غيّر هذه القيمة إلى False لو لاحظت انعكاسًا في اتجاه +90/-90.
            RIGHT_IS_XMIN = True

            if abs(a_angle) < 1e-3:
                # A = 0° → الحفر من السطح العلوي Z
                cz = zmax - (depth / 2.0)  # مركز الأسطوانة داخل الجسم بنصف العمق
                cx, cy = x, y
                axis = "Z"
                print(f"[A0] zmax={zmax:.3f}  -> center.z={cz:.3f}")

            elif a_angle > 0:
                # A = +90° → من جهة اليمين باتجاه +X
                side_right = xmin if RIGHT_IS_XMIN else xmax
                cx = side_right + (depth / 2.0) if RIGHT_IS_XMIN else side_right - (depth / 2.0)
                cy, cz = y, z
                axis = "X"
                print(f"[A+90] right side={side_right:.3f}  -> center.x={cx:.3f}  (dir +X)")

            else:
                # A = -90° → من جهة اليسار باتجاه −X
                side_left = xmax if RIGHT_IS_XMIN else xmin
                cx = side_left - (depth / 2.0) if RIGHT_IS_XMIN else side_left + (depth / 2.0)
                cy, cz = y, z
                axis = "X"
                print(f"[A-90] left side={side_left:.3f}  -> center.x={cx:.3f}  (dir -X)")

            # 🧱 إنشاء الثقب (Boolean cut) بمركز واتجاه صحيحين
            result = add_hole(base_shape, cx, cy, cz, dia, axis, depth=depth)
            if not result or result.IsNull():
                print("[❌] add_hole أرجعت نتيجة فارغة.")
                return None

            # تنظيف أي معاينة قديمة
            try:
                if self._hole_preview_ais:
                    self.display.Context.Erase(self._hole_preview_ais, False)
                    self._hole_preview_ais = None
            except Exception:
                pass
            self._preview_dim_shapes.clear()

            # عرض الشكل الجديد
            self.set_shape(result)
            display_with_fusion_style(result, self.display)
            measure_shape(self.display, result)
            self.display.Context.UpdateCurrentViewer()
            self.display.Repaint()

            print(f"🧱 Hole applied: A={a_angle}°, axis={axis}, dia={dia}, depth={depth}, "
                  f"center=({cx:.3f},{cy:.3f},{cz:.3f})")
            print(f"[BBOX] xmin={xmin:.3f} xmax={xmax:.3f}  zmax={zmax:.3f}  RIGHT_IS_XMIN={RIGHT_IS_XMIN}")

            # حفظ في سجل العمليات إن وُجد
            try:
                for w in QApplication.topLevelWidgets():
                    if hasattr(w, "op_browser"):
                        profile_name = getattr(w, "active_profile_name", "Unnamed")
                        w.op_browser.add_hole(
                            profile_name, (cx, cy, cz), dia, depth, axis,
                            tool=(tool['name'] if tool else None)
                        )
                        break
            except Exception as e:
                print(f"[OPS] إضافة العملية فشلت: {e}")

            return {
                "type": "Hole",
                "x": cx, "y": cy, "z": cz,
                "dia": dia, "depth": depth,
                "axis": axis,
                "A": a_angle,
                "tool": tool["name"] if tool else "Unknown"
            }

        except Exception as e:
            print(f"[❌ APPLY] فشل تطبيق الثقب: {e}")
            return None

    def _center_view(self):
        try:
            if hasattr(self.display, "FitAll"): self.display.FitAll()
            elif hasattr(self.display, "Repaint"): self.display.Repaint()
        except Exception as e:
            print(f"[view] failed: {e}")
