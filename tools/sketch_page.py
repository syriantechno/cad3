"""
SketchPage — نظام رسم تفاعلي بالنقر والسحب داخل العارض
=======================================================

⚙️ مبادئ أساسية:
- ملف مستقل لا يكسر أي كود حالي.
- معاينة مؤقتة أثناء السحب (AIS) تُستبدل بدل التكرار.
- تعطيل الكاميرا أثناء وضع الرسم وتفعيلها بعده.
- تنظيف كامل للمعاينة عند الإنهاء/الإلغاء.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
from OCC.Core.gp import gp_Pnt, gp_Ax2, gp_Dir, gp_Circ
from OCC.Core.AIS import AIS_Line, AIS_Circle
from OCC.Core.Geom import Geom_Circle

@dataclass
class Point2D:
    x: float
    y: float

class SketchPage:
    def __init__(self, parent=None, viewer=None):
        if viewer is None:
            raise ValueError("[SketchPage] ❌ لم يتم تمرير viewer")

        # الوصول الصحيح حسب هيكل مشروعك
        if hasattr(viewer, "display") and hasattr(viewer.display, "_display"):
            self.display = viewer.display._display
            self.view = self.display.View
            self.qt_viewport = viewer
            print("[SketchPage] ✅ تم استخدام viewer.display._display كـ display رئيسي")
        else:
            raise AttributeError("[SketchPage] ❌ لم أجد viewer.display._display داخل الكائن الممرر")

        self.mode = None
        self.start_point = None
        self.preview_ais = None
        self.camera_enabled = True
        print("[SketchPage] ✅ النظام جاهز — وضع الرسم بالنقر والسحب")

    # --------------------------------------------------------
    # التحكم بالكاميرا أثناء الرسم
    # --------------------------------------------------------
    def _disable_camera(self):
        if hasattr(self.qt_viewport, "setMouseTracking"):
            self.qt_viewport.setMouseTracking(True)
        self.camera_enabled = False
        print("[SketchPage] 🟡 تم تعطيل الكاميرا (وضع الرسم فعال)")

    def _enable_camera(self):
        if hasattr(self.qt_viewport, "setMouseTracking"):
            self.qt_viewport.setMouseTracking(False)
        self.camera_enabled = True
        print("[SketchPage] 🟢 تم تفعيل الكاميرا من جديد")

    # --------------------------------------------------------
    # أوضاع الرسم
    # --------------------------------------------------------
    def set_mode(self, mode: str):
        self.mode = mode
        print(f"[SketchPage] ✏️ وضع الرسم: {mode}")
        self._disable_camera()

    def cancel_current(self):
        print("[SketchPage] ❌ تم إلغاء وضع الرسم الحالي")
        self.mode = None
        self._enable_camera()
        if self.preview_ais:
            self.display.Context.Remove(self.preview_ais, True)
            self.preview_ais = None

    # --------------------------------------------------------
    # أحداث الماوس
    # --------------------------------------------------------
    def on_mouse_press(self, x: float, y: float):
        if not self.mode:
            return
        self.start_point = gp_Pnt(x, y, 0)
        print(f"[SketchPage] 🟢 نقطة البداية: ({x}, {y})")

    def on_mouse_move(self, x: float, y: float):
        if not self.mode or not self.start_point:
            return
        end_pnt = gp_Pnt(x, y, 0)

        # معاينة أثناء السحب
        if self.preview_ais:
            self.display.Context.Remove(self.preview_ais, True)

        if self.mode == "line":
            self.preview_ais = AIS_Line(self.start_point, end_pnt)
        elif self.mode == "circle":
            radius = ((x - self.start_point.X())**2 + (y - self.start_point.Y())**2) ** 0.5
            circ = gp_Circ(gp_Ax2(self.start_point, gp_Dir(0, 0, 1)), radius)
            self.preview_ais = AIS_Circle(Geom_Circle(circ))

        if self.preview_ais:
            self.display.Context.Display(self.preview_ais, False)
            self.display.Context.UpdateCurrentViewer()

    def on_mouse_release(self, x: float, y: float):
        if not self.mode or not self.start_point:
            return

        end_pnt = gp_Pnt(x, y, 0)
        print(f"[SketchPage] 🔵 نقطة النهاية: ({x}, {y})")

        # إزالة المعاينة ورسم الشكل النهائي
        if self.preview_ais:
            self.display.Context.Remove(self.preview_ais, True)
            self.preview_ais = None

        if self.mode == "line":
            shape = AIS_Line(self.start_point, end_pnt)
        elif self.mode == "circle":
            radius = ((x - self.start_point.X())**2 + (y - self.start_point.Y())**2) ** 0.5
            circ = gp_Circ(gp_Ax2(self.start_point, gp_Dir(0, 0, 1)), radius)
            shape = AIS_Circle(Geom_Circle(circ))
        else:
            shape = None

        if shape:
            self.display.Context.Display(shape, True)
            self.display.Context.UpdateCurrentViewer()
            print("[SketchPage] ✅ تم رسم الشكل النهائي")

        self.start_point = None
        self._enable_camera()
        self.mode = None
