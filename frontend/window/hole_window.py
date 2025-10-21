from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QHBoxLayout, QSpacerItem, QSizePolicy, QLabel,
    QMessageBox, QFrame, QApplication
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer
from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

# === مشروعك: لا تغييرات على الاستيرادات الموجودة لديك ===
from tools.geometry_ops import add_hole, preview_hole
from tools.color_utils import display_with_fusion_style
from tools.dimensions import measure_shape, hole_reference_dimensions, hole_size_dimensions
from frontend.window.tools_db import ToolsDB


# ✅ توافق 7.9: لا نعتمد على اسم دالة واحد للـ bbox
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.TopAbs import TopAbs_VERTEX
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.BRep import BRep_Tool

import os, json
from pathlib import Path

ENABLE_PREVIEW_DIMS = True
PREFS_PATH = Path("data/hole_prefs.json")
IMAGES_DIR = Path("tools/images")


# ==============================
# 🧩 طبقة توافق لاستخراج حدود الشكل (bbox)
# ==============================
def _bbox_extents(shape):
    """
    ترجع حدود الشكل: (xmin, ymin, zmin, xmax, ymax, zmax)
    تحاول عدة طرق متوافقة مع إصدارات pythonocc المختلفة.
    """
    # 1) نحاول عبر BRepBndLib (قد تختلف أسماء الدوال بين الإصدارات)
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

    # 2) بديل مضمون: مسح جميع الرؤوس لاستخراج أقل/أعلى XYZ
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

    # 3) فشل — نعيد صندوق افتراضي
    print("[BBOX] ⚠️ Failed to compute bbox with all strategies.")
    return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def get_axis_top_coord(shape, axis: str) -> float:
    """
    السطح الأعلى على محور معين:
    - Z => zmax
    - Y => ymax
    - X => xmax
    """
    xmin, ymin, zmin, xmax, ymax, zmax = _bbox_extents(shape)
    if axis == "Z":
        return zmax
    if axis == "Y":
        return ymax
    if axis == "X":
        return xmax
    # افتراضيًا اعتبر Z
    return zmax


class HoleWindow(QWidget):
    """
    نسخة نهائية بعد التعديل:
    - الصفر للأداة = أعلى سطح للمجسم على المحور المختار (Z/Y/X).
    - المعاينة والـ G-code تعتمد على هذا السطح الأعلى.
    - طباعة debug للقيم الفعلية.
    """
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

    # ==============================
    # 🧱 بناء الواجهة
    # ==============================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # 🧰 اختيار الأداة + زر تحديث
        top_tools_layout = QHBoxLayout()
        self.tool_combo = QComboBox()
        self.tool_combo.setToolTip("اختر أداة الحفر من المكتبة")
        btn_refresh = QPushButton("↻ Refresh")
        btn_refresh.setToolTip("تحديث قائمة الأدوات من المكتبة")
        btn_refresh.clicked.connect(self._load_tools)
        top_tools_layout.addWidget(self.tool_combo)
        top_tools_layout.addWidget(btn_refresh)
        form.addRow("Tool:", top_tools_layout)

        # 🖼️ صورة الأداة
        self.tool_image = QLabel("(No Image)")
        self.tool_image.setAlignment(Qt.AlignCenter)
        self.tool_image.setStyleSheet("""
            QLabel {
                background-color: #f8f8f8;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                padding: 6px;
                min-height: 120px;
            }
        """)
        form.addRow("Tool Preview:", self.tool_image)

        # 🧩 مدخلات الحفر
        self.x_input = QLineEdit("0");   self.x_input.setToolTip("إحداثي X لمركز الثقب")
        self.y_input = QLineEdit("0");   self.y_input.setToolTip("إحداثي Y لمركز الثقب")
        self.z_input = QLineEdit("0");   self.z_input.setToolTip("إحداثي Z لمركز الثقب")
        self.dia_input = QLineEdit("6"); self.dia_input.setToolTip("قطر الثقب بالمليمتر")
        self.depth_input = QLineEdit("20"); self.depth_input.setToolTip("عمق الثقب بالمليمتر")
        self.preview_len_input = QLineEdit("50"); self.preview_len_input.setToolTip("طول خط المعاينة")
        self.axis_combo = QComboBox(); self.axis_combo.addItems(["Z", "Y", "X"])
        self.axis_combo.setToolTip("محور اتجاه الحفر")

        form.addRow("X:", self.x_input)
        form.addRow("Y:", self.y_input)
        form.addRow("Z:", self.z_input)
        form.addRow("Diameter:", self.dia_input)
        form.addRow("Depth:", self.depth_input)
        form.addRow("Preview Length:", self.preview_len_input)
        form.addRow("Axis:", self.axis_combo)

        layout.addLayout(form)

        # 🎨 فاصل
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #c0c0c0; margin: 8px 0;")
        layout.addWidget(separator)

        # 📋 ملخص الأداة
        self.tool_summary = QLabel("🧰 Tool Summary: None selected")
        self.tool_summary.setAlignment(Qt.AlignCenter)
        self.tool_summary.setStyleSheet("""
            QLabel {
                color: #333;
                background-color: #f0f0f0;
                border-radius: 6px;
                padding: 6px;
                font-size: 11pt;
            }
        """)
        layout.addWidget(self.tool_summary)

        # 🎛️ أزرار
        btns_row = QHBoxLayout(); btns_row.setAlignment(Qt.AlignCenter)
        self.preview_btn = QPushButton("Preview Hole")
        self.apply_btn = QPushButton("Apply Hole")
        self.center_btn = QPushButton("Center View")
        self.preview_btn.setObjectName("btnPreview")
        self.apply_btn.setObjectName("btnApply")
        self.preview_btn.setFixedWidth(150)
        self.apply_btn.setFixedWidth(150)
        self.center_btn.setFixedWidth(130)
        self.center_btn.setToolTip("تركيز العرض على المشهد (Fit All)")

        btns_row.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        btns_row.addWidget(self.preview_btn); btns_row.addSpacing(12)
        btns_row.addWidget(self.apply_btn);   btns_row.addSpacing(12)
        btns_row.addWidget(self.center_btn)
        btns_row.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        layout.addSpacing(10)
        layout.addLayout(btns_row)
        self.setLayout(layout)

        # 🔗 ربط الأحداث
        self.preview_btn.clicked.connect(self._update_preview)
        self.apply_btn.clicked.connect(self.apply_hole)
        self.center_btn.clicked.connect(self._center_view)
        self.tool_combo.currentIndexChanged.connect(self._on_tool_changed)

        # ✅ تحميل الأدوات بعد تجهيز الواجهة
        self._load_tools()

    # ===================================================
    # 🔄 الأدوات
    # ===================================================
    def _load_tools(self):
        try:
            db = ToolsDB()
            tools = db.list_tools()
            self.tool_combo.blockSignals(True)
            self.tool_combo.clear()
            if not tools:
                self.tool_combo.addItem("— No Tools —", None)
                self.tool_combo.blockSignals(False)
                self._update_tool_summary(None)
                self._update_tool_image(None)
                return

            found_last = False
            for t in tools:
                label = f"{t['name']} ({t['type']} ⌀{t['diameter']}mm)"
                self.tool_combo.addItem(label, t)
                if self._last_tool_id and t.get("id") == self._last_tool_id:
                    self.tool_combo.setCurrentIndex(self.tool_combo.count() - 1)
                    found_last = True

            if not found_last:
                self.tool_combo.setCurrentIndex(0)

            self._on_tool_changed()
            self.tool_combo.blockSignals(False)
            print(f"[TOOLS] ✅ Loaded {len(tools)} tools into HoleWindow.")
        except Exception as e:
            print(f"[❌ TOOLS] Load failed: {e}")
            self.tool_combo.addItem("Error loading tools", None)

    def _on_tool_changed(self):
        tool = self.tool_combo.currentData()
        if tool and "diameter" in tool:
            self.dia_input.setText(str(tool["diameter"]))
        self._update_tool_image(tool)
        self._update_tool_summary(tool)
        self._save_last_tool(tool)

    def _update_tool_summary(self, tool):
        if not tool:
            self.tool_summary.setText("🧰 Tool Summary: None selected")
            return
        feed = tool.get("feedrate", "—")
        rpm = tool.get("rpm", "—")
        length = tool.get("length", "—")
        self.tool_summary.setText(
            f"🧰 Tool: {tool['name']} | Type: {tool['type']} | Ø {tool['diameter']}mm | "
            f"Length: {length} | RPM: {rpm} | Feed: {feed}"
        )

    def _update_tool_image(self, tool):
        if not tool:
            self.tool_image.setPixmap(QPixmap()); self.tool_image.setText("(No Image)")
            return
        img_path = IMAGES_DIR / f"{tool['name']}.png"
        if img_path.exists():
            pix = QPixmap(str(img_path))
            self.tool_image.setPixmap(pix.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.tool_image.setPixmap(QPixmap()); self.tool_image.setText("(No Image)")

    # ===================================================
    # ⚙️ المعاينة والتنفيذ
    # ===================================================
    def _connect_live_preview(self):
        for w in (
            self.x_input, self.y_input, self.z_input,
            self.dia_input, self.depth_input, self.preview_len_input
        ):
            w.textChanged.connect(self._update_preview)
        self.axis_combo.currentIndexChanged.connect(self._update_preview)

    def _get_values(self):
        try:
            x = float(self.x_input.text())
            y = float(self.y_input.text())
            z = float(self.z_input.text())
            dia = float(self.dia_input.text())
            depth = float(self.depth_input.text())
            preview_len = float(self.preview_len_input.text())
            axis = self.axis_combo.currentText()
            tool = self.tool_combo.currentData()
            return x, y, z, dia, depth, preview_len, axis, tool
        except ValueError:
            return None

    def _safe_dims_preview(self, base_shape, x, y, z, dia, axis, depth):
        elems = []
        try:
            ref_dims = hole_reference_dimensions(
                self.display, x, y, z, base_shape, offset_above=10, preview=True
            )
            if isinstance(ref_dims, (list, tuple)):
                elems += list(ref_dims)
            elif ref_dims is not None:
                elems.append(ref_dims)
        except Exception as e:
            print(f"[dims] reference failed: {e}")

        try:
            size_dims = hole_size_dimensions(
                self.display, x, y, z, dia, axis, depth, base_shape, offset_above=10, preview=True
            )
            if isinstance(size_dims, (list, tuple)):
                elems += list(size_dims)
            elif size_dims is not None:
                elems.append(size_dims)
        except Exception as e:
            print(f"[dims] size failed: {e}")

        self._preview_dim_shapes = [e for e in elems if e]

    def _update_preview(self):
        vals = self._get_values()
        if not vals:
            return
        x, y, z, dia, depth, preview_len, axis, tool = vals

        base_shape = self.get_shape()
        if not base_shape or base_shape.IsNull():
            print("[PREVIEW] ⚠️ No valid base shape for preview.")
            return

        # 🧭 احصل على أعلى إحداثي على المحور المختار
        top = get_axis_top_coord(base_shape, axis)

        # عدّل الإحداثي الموافق للمحور
        if axis == "Z":
            cx, cy, cz = x, y, top
        elif axis == "Y":
            cx, cy, cz = x, top, z
        else:  # X
            cx, cy, cz = top, y, z

        # امسح المعاينة السابقة
        try:
            if self._hole_preview_ais:
                self.display.Context.Erase(self._hole_preview_ais, False)
        except Exception:
            pass
        self._hole_preview_ais = None
        self._preview_dim_shapes.clear()

        # أنشئ معاينة

        # 🧭 احصل على أعلى إحداثي على المحور المختار
        # ✅ نرفع مركز الأسطوانة للأعلى حتى تلامس قاعدتها السطح العلوي للمجسم
        if axis == "Z":
            cz = top + preview_len
            hole_shape = preview_hole(base_shape, cx, cy, cz, dia, axis, preview_len)
        elif axis == "Y":
            cy = top + (preview_len / 2.0)
            hole_shape = preview_hole(base_shape, cx, cy, cz, dia, axis, preview_len)
        elif axis == "X":
            cx = top + (preview_len / 2.0)
            hole_shape = preview_hole(base_shape, cx, cy, cz, dia, axis, preview_len)
        else:
            hole_shape = preview_hole(base_shape, cx, cy, top, dia, axis, preview_len)

        if not hole_shape or hole_shape.IsNull():
            print("[⚠] Hole preview shape is null — skip")
            return

        ais = AIS_Shape(hole_shape)
        ais.SetColor(Quantity_Color(1.0, 0.0, 0.0, Quantity_TOC_RGB))
        try:
            ais.SetTransparency(0.5)
        except Exception:
            pass
        self.display.Context.Display(ais, False)
        self._hole_preview_ais = ais

        if ENABLE_PREVIEW_DIMS:
            self._safe_dims_preview(base_shape, cx, cy, cz, dia, axis, depth)

        self.display.Context.UpdateCurrentViewer()
        print(f"[PREVIEW] Hole preview at top({axis})={top:.3f} -> ({cx:.3f},{cy:.3f},{cz:.3f})")

    def apply_hole(self):
        vals = self._get_values()
        if not vals:
            QMessageBox.warning(self, "Hole", "⚠️ قيم غير صالحة.")
            return None

        x, y, z, dia, depth, _, axis, tool = vals
        base_shape = self.get_shape()
        if not base_shape or base_shape.IsNull():
            QMessageBox.warning(self, "Hole", "⚠️ لا يوجد شكل صالح للحفر.")
            return None

        try:
            # 🧭 حساب أعلى إحداثي على المحور المختار
            top = get_axis_top_coord(base_shape, axis)

            if axis == "Z":
                cx, cy, cz = x, y, top
                start = (cx, cy, cz)
                end = (cx, cy, cz - depth)
            elif axis == "Y":
                cx, cy, cz = x, top, z
                start = (cx, cy, cz)
                end = (cx, cy - depth, cz)
            else:  # X
                cx, cy, cz = top, y, z
                start = (cx, cy, cz)
                end = (cx - depth, cy, cz)

            print(f"[HOLE] Axis={axis} | Top={top:.3f} | Start={start} | End={end}")

            # إنشاء الثقب بناءً على السطح الأعلى على المحور
            result = add_hole(base_shape, cx, cy, cz, dia, axis, depth=depth)
            if not result or result.IsNull():
                print("[❌] add_hole returned null result.")
                return None

            # تنظيف المعاينة القديمة
            try:
                if self._hole_preview_ais:
                    self.display.Context.Erase(self._hole_preview_ais, False)
                    self._hole_preview_ais = None
            except Exception:
                pass
            self._preview_dim_shapes.clear()

            # تحديث الشكل في العارض
            self.set_shape(result)
            display_with_fusion_style(result, self.display)
            measure_shape(self.display, result)
            hole_reference_dimensions(self.display, cx, cy, cz, result, offset_above=10)
            hole_size_dimensions(self.display, cx, cy, cz, dia, axis, depth, result, offset_above=10)
            self.display.Context.UpdateCurrentViewer()
            self.display.Repaint()

            # وميض سريع بعد التنفيذ
            try:
                blink_shape = preview_hole(result, cx, cy, cz, dia, axis, 8.0)
                if blink_shape and not blink_shape.IsNull():
                    blink_ais = AIS_Shape(blink_shape)
                    blink_ais.SetColor(Quantity_Color(0.0, 0.8, 0.0, Quantity_TOC_RGB))
                    blink_ais.SetTransparency(0.2)
                    self.display.Context.Display(blink_ais, False)
                    QTimer.singleShot(400, lambda: self.display.Context.Erase(blink_ais, False))
            except Exception:
                pass

            if tool:
                print(f"🪛 Tool used: {tool['name']} | ⌀{tool['diameter']}mm | Feed={tool.get('feedrate','—')}")

            print(f"🧱 Hole applied: axis={axis}, dia={dia}, depth={depth}, at ({cx},{cy},{cz})")

            # ⛓️ أضف العملية إلى Operation Browser إن وُجد
            try:
                for w in QApplication.topLevelWidgets():
                    if hasattr(w, "op_browser"):
                        profile_name = getattr(w, "active_profile_name", "Unnamed")
                        try:
                            w.op_browser.add_hole(profile_name, (cx, cy, cz), dia, depth, axis,
                                                  tool=(tool["name"] if tool else None))
                            print(f"🕳 [OPS] Added Hole to {profile_name}: "
                                  f"{{'type':'Hole','x':{cx},'y':{cy},'z':{cz},'dia':{dia},'depth':{depth},'axis':'{axis}'}}")
                        except TypeError:
                            w.op_browser.add_hole(profile_name, (cx, cy, cz), dia, depth, axis)
                        break
            except Exception as e:
                print(f"[OPS] add to browser failed: {e}")

            return {
                "type": "Hole",
                "x": cx, "y": cy, "z": cz,
                "dia": dia, "depth": depth,
                "axis": axis,
                "tool": tool["name"] if tool else "Unknown"
            }

        except Exception as e:
            print(f"[❌ APPLY] Hole failed: {e}")
            return None

    def _center_view(self):
        try:
            if hasattr(self.display, "FitAll"):
                self.display.FitAll()
            elif hasattr(self.display, "Repaint"):
                self.display.Repaint()
        except Exception as e:
            print(f"[view] center failed: {e}")

    # ==============================
    # 💾 تذكّر آخر أداة
    # ==============================
    def _save_last_tool(self, tool):
        try:
            PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
            json.dump({"last_tool_id": tool.get("id") if tool else None}, open(PREFS_PATH, "w"))
        except Exception:
            pass

    def _restore_last_tool(self):
        try:
            if PREFS_PATH.exists():
                self._last_tool_id = json.load(open(PREFS_PATH, "r")).get("last_tool_id")
        except Exception:
            pass
