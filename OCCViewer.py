# -*- coding: utf-8 -*-
"""
OCCViewer — النسخة الأصلية المستقرة (Fusion-style)
متوافقة تمامًا مع pythonocc-core 7.9.x
"""

from OCC.Display.backend import load_backend
load_backend("pyqt5")

from OCC.Display.qtDisplay import qtViewer3d
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QTimer, Qt
from OCC.Core.gp import gp_Pnt
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.Geom import Geom_CartesianPoint
from OCC.Core.AIS import AIS_Line, AIS_TextLabel
from OCC.Core.TCollection import TCollection_ExtendedString


class OCCViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.display = qtViewer3d(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.display)
        self._grid = []
        self._axes = []
        self._labels = []
        QTimer.singleShot(300, self.init_viewer)

    # ------------------------------------------------------------
    def init_viewer(self):
        """تهيئة Fusion-style آمنة بالكامل"""
        try:
            disp = self.display._display
            ctx = disp.Context
            view = disp.View

            # خلفية فقط أولاً
            bg = Quantity_Color(0.945, 0.949, 0.945, Quantity_TOC_RGB)
            view.SetBackgroundColor(bg)
            view.MustBeResized()
            view.Redraw()
            print("[DEBUG] Viewer background set to light gray with black edges.")

            # نرسم كل شيء بعد أن يجهز الـ context
            QTimer.singleShot(500, lambda: self._safe_draw(ctx))

        except Exception as e:
            print(f"⚠️ [OCCViewer.init_viewer] {e}")

            # ===== رسم الشبكة =====
            self._draw_grid(ctx)

            # ===== رسم المحاور =====
            self._draw_axes(ctx)



            # ===== ضبط ألوان التفاعل =====
            ctx.SetHighlightColor(Quantity_Color(1.0, 0.9, 0.0, Quantity_TOC_RGB))  # Hover أصفر
            ctx.SetSelectionColor(Quantity_Color(0.2, 0.6, 1.0, Quantity_TOC_RGB))  # تحديد أزرق
            ctx.SetAutomaticHilight(True)
            ctx.SetAutoActivateSelection(True)

            # بعد أن تنتهي التهيئة، نثبتهم كمحميين
            self._protected_objects = list(self._grid + self._axes)

            # --- after self._draw_grid(ctx) and self._draw_axes(ctx) in init_viewer() ---
            disp = self.display._display

            # 1) Patch DisplayShape
            if not hasattr(self, "_orig_DisplayShape"):
                self._orig_DisplayShape = disp.DisplayShape

                def _patched_DisplayShape(*args, **kwargs):
                    # نفّذ العرض الأصلي
                    res = self._orig_DisplayShape(*args, **kwargs)
                    # رجّع الشبكة والمحاور فورًا بعد العرض
                    try:
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(0, self.refresh_scene)
                    except Exception:
                        self.refresh_scene()
                    return res

                disp.DisplayShape = _patched_DisplayShape

            # 2) Patch EraseAll
            if not hasattr(self, "_orig_EraseAll"):
                self._orig_EraseAll = disp.EraseAll

                def _patched_EraseAll(*args, **kwargs):
                    res = self._orig_EraseAll(*args, **kwargs)
                    try:
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(0, self.refresh_scene)
                    except Exception:
                        self.refresh_scene()
                    return res

                disp.EraseAll = _patched_EraseAll

            print("🧷 [OCCViewer] Hooks installed: DisplayShape/EraseAll -> refresh_scene()")

            ctx.UpdateCurrentViewer()
            QTimer.singleShot(400, self.reset_camera)
            print("✅ [OCCViewer] Stable Fusion viewer initialized")

        except Exception as e:
            print(f"⚠️ [OCCViewer.init_viewer] {e}")

    # ------------------------------------------------------------
    def _draw_grid(self, ctx):
        """شبكة رمادية مستقرة"""
        try:
            step = 20
            limit = 200
            color = Quantity_Color(0.8, 0.8, 0.8, Quantity_TOC_RGB)

            for i in range(-limit, limit + step, step):
                # خطوط X (موازية لمحور Y)
                p1 = Geom_CartesianPoint(gp_Pnt(-limit, i, 0))
                p2 = Geom_CartesianPoint(gp_Pnt(limit, i, 0))
                l1 = AIS_Line(p1, p2)
                l1.SetColor(color)
                ctx.Display(l1, False)
                self._grid.append(l1)

                # خطوط Y (موازية لمحور X)
                p3 = Geom_CartesianPoint(gp_Pnt(i, -limit, 0))
                p4 = Geom_CartesianPoint(gp_Pnt(i, limit, 0))
                l2 = AIS_Line(p3, p4)
                l2.SetColor(color)
                ctx.Display(l2, False)
                self._grid.append(l2)

            ctx.UpdateCurrentViewer()
            print("[DEBUG] Grid drawn successfully")

        except Exception as e:
            print(f"⚠️ [OCCViewer._draw_grid] {e}")

    # ------------------------------------------------------------
    def _draw_axes(self, ctx):
        """محاور X/Y/Z آمنة (بدون AIS_TextLabel)"""
        try:
            axes = [
                ("X", gp_Pnt(0, 0, 0), gp_Pnt(100, 0, 0), Quantity_Color(1.0, 0.2, 0.2, Quantity_TOC_RGB)),
                ("Y", gp_Pnt(0, 0, 0), gp_Pnt(0, 100, 0), Quantity_Color(0.2, 0.8, 0.2, Quantity_TOC_RGB)),
                ("Z", gp_Pnt(0, 0, 0), gp_Pnt(0, 0, 100), Quantity_Color(0.2, 0.4, 1.0, Quantity_TOC_RGB)),
            ]
            for name, s, e, color in axes:
                p1 = Geom_CartesianPoint(s)
                p2 = Geom_CartesianPoint(e)
                line = AIS_Line(p1, p2)
                line.SetColor(color)
                line.SetWidth(2.5)
                ctx.Display(line, False)
                self._axes.append(line)

                # طرف المحور (نقطة صغيرة بلون غامق)
                tip_p1 = Geom_CartesianPoint(e)
                tip_p2 = Geom_CartesianPoint(gp_Pnt(e.X() * 1.05, e.Y() * 1.05, e.Z() * 1.05))
                tip = AIS_Line(tip_p1, tip_p2)
                tip.SetColor(color)
                tip.SetWidth(3.0)
                ctx.Display(tip, False)
                self._axes.append(tip)

            ctx.UpdateCurrentViewer()
            print("[DEBUG] Axes (safe version without text) drawn successfully")

        except Exception as e:
            print(f"⚠️ [OCCViewer._draw_axes] {e}")

    # ------------------------------------------------------------
    def reset_camera(self):
        """تعيين زاوية Fusion"""
        try:
            view = self.display._display.View
            view.SetProj(1, -1, 0.7)
            view.SetTwist(0)
            view.Redraw()
            print("📸 [Camera] Reset to Fusion angle")
        except Exception as e:
            print(f"⚠️ [OCCViewer.reset_camera] {e}")

    # ------------------------------------------------------------
    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        try:
            self.display.Context.MoveTo(e.x(), e.y(), self.display._display.Viewer, True)
        except Exception:
            pass

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        if e.button() == Qt.LeftButton:
            try:
                self.display.Context.Select(True)
            except Exception:
                pass

    def _safe_draw(self, ctx):
        """ترسم الشبكة والمحاور بعد تأكد من جاهزية الـ Viewer"""
        try:
            self._draw_grid(ctx)
            self._draw_axes(ctx)

            # ===== إصلاح ألوان الهوفر والتحديد لإصدارات 7.9.x =====
            from OCC.Core.Prs3d import Prs3d_Drawer
            from OCC.Core.Quantity import Quantity_TOC_RGB

            drawer = ctx.DefaultDrawer()
            # لون التحديد (Select)
            sel_color = Quantity_Color(0.2, 0.6, 1.0, Quantity_TOC_RGB)  # أزرق
            drawer.SetSelectionColor(sel_color)

            # لون الهوفر (Highlight)
            from OCC.Core.Graphic3d import Graphic3d_HighlightStyle, Graphic3d_TypeOfHighlight
            style = Graphic3d_HighlightStyle(Graphic3d_TypeOfHighlight.Graphic3d_TOH_FACE)
            style.SetColor(Quantity_Color(1.0, 0.9, 0.0, Quantity_TOC_RGB))  # أصفر
            style.SetTransparency(0.0)
            ctx.SetHighlightStyle(style)

            ctx.UpdateCurrentViewer()
            QTimer.singleShot(300, self.reset_camera)
            print("✅ [OCCViewer] Safe viewer fully initialized")

        except Exception as e:
            print(f"⚠️ [OCCViewer._safe_draw] {e}")

    def refresh_scene(self):
        """إعادة إظهار الشبكة والمحاور + إصلاح ألوان الهوفر"""
        try:
            disp = self.display._display
            ctx = disp.Context

            # إعادة عرض الشبكة والمحاور دائماً
            for g in getattr(self, "_grid", []):
                ctx.Display(g, False)
            for a in getattr(self, "_axes", []):
                ctx.Display(a, False)

            # إعداد ألوان التفاعل (7.9+)
            from OCC.Core.Prs3d import Prs3d_Drawer
            from OCC.Core.Graphic3d import Graphic3d_HighlightStyle, Graphic3d_TypeOfHighlight
            from OCC.Core.Quantity import Quantity_TOC_RGB, Quantity_Color

            drawer = ctx.DefaultDrawer()
            sel_color = Quantity_Color(0.2, 0.6, 1.0, Quantity_TOC_RGB)
            drawer.SetSelectionColor(sel_color)

            style = Graphic3d_HighlightStyle(Graphic3d_TypeOfHighlight.Graphic3d_TOH_FACE)
            style.SetColor(Quantity_Color(1.0, 0.9, 0.0, Quantity_TOC_RGB))  # أصفر
            style.SetTransparency(0.0)
            ctx.SetHighlightStyle(style)

            ctx.UpdateCurrentViewer()
            print("♻️ [OCCViewer] Grid & axes refreshed (hover fixed)")
        except Exception as e:
            print(f"⚠️ [OCCViewer.refresh_scene] {e}")

    def ensure_scene(self):
        """ضمان بقاء الشبكة والمحاور بعد أي EraseAll"""
        try:
            disp = self.display._display
            ctx = disp.Context
            # إذا ما في ولا عنصر، نعيد إنشاء الشبكة والمحاور
            if ctx.NbSelected() == 0 and not getattr(self, "_grid", []) and not getattr(self, "_axes", []):
                print("♻️ [OCCViewer] Scene empty — rebuilding grid and axes")
                self._draw_grid(ctx)
                self._draw_axes(ctx)
                ctx.UpdateCurrentViewer()
        except Exception as e:
            print(f"⚠️ [OCCViewer.ensure_scene] {e}")
