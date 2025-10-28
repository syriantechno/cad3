import traceback
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QPoint
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax2
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCC.Core.GC import GC_MakeCircle
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

class SketchPage(QWidget):
    """وضع الرسم بالنقر والسحب داخل العارض."""
    def __init__(self, parent=None, viewer=None):
        super().__init__(parent)
        self.parent = parent
        self.viewer = viewer
        self.display = getattr(viewer.display, "_display", None)
        print(f"[SketchPage] Initialized — display={self.display}")

        # حالات الرسم
        self.mode = None
        self._is_drawing = False
        self._start_pnt = None
        self._preview_shape = None

        # ربط أحداث الماوس بالـ viewer.canvas (واجهة PyQt)
        canvas = getattr(self.viewer, "canvas", None)
        if canvas:
            canvas.mousePressEvent = self._mouse_press
            canvas.mouseMoveEvent = self._mouse_move
            canvas.mouseReleaseEvent = self._mouse_release
            print("🧷 [SketchPage] Mouse hooks installed on viewer.canvas")
        else:
            print("⚠️ [SketchPage] viewer.canvas غير متاح")

    # === اختيار الأداة ===
    def set_mode(self, mode: str):
        self.mode = mode
        print(f"✏️ [Sketch] تفعيل أداة: {mode}")

    # === نقر الفأرة ===
    def _mouse_press(self, event):
        if event.button() == Qt.LeftButton and self.mode:
            self._is_drawing = True
            self._start_pnt = self._to_3d_point(event)
            print(f"🎯 [Sketch] نقطة البداية: {self._start_pnt.Coord()}")

    # === أثناء السحب ===
    def _mouse_move(self, event):
        if not self._is_drawing or not self.mode:
            return
        try:
            current_pnt = self._to_3d_point(event)

            # احذف المعاينة السابقة
            if self._preview_shape:
                self.display.Context.Erase(self._preview_shape, False)

            if self.mode == "circle":
                self._preview_shape = self._make_circle_preview(self._start_pnt, current_pnt)
            elif self.mode == "line":
                self._preview_shape = self._make_line_preview(self._start_pnt, current_pnt)

            self.display.Context.Display(self._preview_shape, False)
            self.display.Context.UpdateCurrentViewer()
        except Exception as e:
            print(f"⚠️ [Sketch.mouse_move] {e}")

    # === إفلات الفأرة ===
    def _mouse_release(self, event):
        if event.button() == Qt.LeftButton and self._is_drawing:
            self._is_drawing = False
            end_pnt = self._to_3d_point(event)
            print(f"✅ [Sketch] نقطة النهاية: {end_pnt.Coord()}")

            if self.mode == "circle":
                self._finalize_circle(self._start_pnt, end_pnt)
            elif self.mode == "line":
                self._finalize_line(self._start_pnt, end_pnt)

            self._preview_shape = None

    # === تحويل الإحداثيات من الشاشة إلى 3D ===
    def _to_3d_point(self, event):
        """يبسّط تحويل الماوس إلى نقطة 3D تقريبية."""
        x, y = event.x(), event.y()
        try:
            # OCC يعطي Z ثابت (0.0) هنا كمستوى الرسم
            proj = self.display.View.ConvertToGrid(x, y)
            return gp_Pnt(proj.X(), proj.Y(), 0)
        except Exception:
            return gp_Pnt(0, 0, 0)

    # === إنشاء معاينة ===
    def _make_circle_preview(self, p1, p2):
        radius = p1.Distance(p2)
        print(f"🌀 [Preview] دائرة مؤقتة — نصف قطر {radius:.2f}")
        axis = gp_Ax2(p1, gp_Dir(0, 0, 1))
        circ = GC_MakeCircle(axis, radius).Value()
        edge = BRepBuilderAPI_MakeEdge(circ).Edge()
        return self.display.DisplayShape(edge, color=Quantity_Color(0.6, 0.8, 1.0, Quantity_TOC_RGB), update=False)[0]

    def _make_line_preview(self, p1, p2):
        edge = BRepBuilderAPI_MakeEdge(p1, p2).Edge()
        return self.display.DisplayShape(edge, color=Quantity_Color(1.0, 0.6, 0.2, Quantity_TOC_RGB), update=False)[0]

    # === إنهاء الشكل النهائي ===
    def _finalize_circle(self, p1, p2):
        try:
            radius = p1.Distance(p2)
            axis = gp_Ax2(p1, gp_Dir(0, 0, 1))
            circ = GC_MakeCircle(axis, radius).Value()
            edge = BRepBuilderAPI_MakeEdge(circ).Edge()
            self.display.DisplayShape(edge, color=Quantity_Color(0.3, 0.5, 0.9, Quantity_TOC_RGB), update=True)
            print(f"🟢 [Sketch] تم رسم دائرة نهائية بنصف قطر {radius:.2f}")
        except Exception as e:
            print(f"🔥 [Sketch._finalize_circle] {e}")
            traceback.print_exc()

    def _finalize_line(self, p1, p2):
        try:
            edge = BRepBuilderAPI_MakeEdge(p1, p2).Edge()
            self.display.DisplayShape(edge, color=Quantity_Color(1.0, 0.5, 0.1, Quantity_TOC_RGB), update=True)
            print("🟢 [Sketch] تم رسم خط نهائي")
        except Exception as e:
            print(f"🔥 [Sketch._finalize_line] {e}")
            traceback.print_exc()
