
# -*- coding: utf-8 -*-
"""
OCCViewer — Fusion-style Professional Viewer (pythonocc-core 7.9.x friendly)
- Light gray background (#F1F2F1)
- Fusion-like fading grid (AIS_Line)
- Safe axes (no AIS_TextLabel)
- Debounced auto-restore of grid/axes after DisplayShape/EraseAll (no recursion)
"""

from OCC.Display.backend import load_backend
load_backend('pyqt5')

from OCC.Display.qtDisplay import qtViewer3d
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QTimer, Qt

from OCC.Core.gp import gp_Pnt
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.Geom import Geom_CartesianPoint
from OCC.Core.AIS import AIS_Line


class OCCViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.display = qtViewer3d(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.display)

        # Keep references so AIS objects are not GC'd
        self._grid = []
        self._axes = []

        # Refresh control
        self._is_refreshing = False
        self._suspend_hooks = False
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(30)  # debounce 30ms
        self._refresh_timer.timeout.connect(self._do_refresh)

        # Colors
        self._bg = Quantity_Color(0.945, 0.949, 0.945, Quantity_TOC_RGB)  # #F1F2F1

        QTimer.singleShot(200, self.init_viewer)

    # ------------------------------------------------------------------
    def init_viewer(self):
        try:
            disp = self.display._display
            view = disp.View

            # Background only first (safe)
            view.SetBackgroundColor(self._bg)
            view.MustBeResized()
            view.Redraw()
            print("[DEBUG] Viewer background set to light gray (#F1F2F1)")

            # Draw everything a bit later to avoid OCC GL race conditions
            QTimer.singleShot(350, self._safe_draw)

        except Exception as e:
            print(f"⚠️ [OCCViewer.init_viewer] {e}")

    # ------------------------------------------------------------------
    def _safe_draw(self):
        try:
            disp = self.display._display
            ctx = disp.Context

            # Draw base scene
            self._draw_grid(ctx)
            self._draw_axes(ctx)

            ctx.UpdateCurrentViewer()
            self._apply_fusion_colors()

            # Camera after everything is in
            QTimer.singleShot(200, self.reset_camera)

            # Install minimal hooks (DisplayShape/EraseAll only) with debounce
            self._install_hooks()

            print("✅ [OCCViewer] Fusion viewer initialized (grid+axes ready)")
        except Exception as e:
            print(f"⚠️ [OCCViewer._safe_draw] {e}")

    def _apply_fusion_colors(self):
        """تطبيق ألوان فيوجن (Hover برتقالي - Select أزرق) كما في العارض التجريبي."""
        try:
            ctx = self.display._display.Context
            hl_style = ctx.HighlightStyle()
            hl_style.SetColor(Quantity_Color(1.0, 0.6, 0.1, Quantity_TOC_RGB))  # Fusion orange
            ctx.SetHighlightStyle(hl_style)

            sel_style = ctx.SelectionStyle()
            sel_style.SetColor(Quantity_Color(0.2, 0.6, 1.0, Quantity_TOC_RGB))  # Fusion blue
            ctx.SetSelectionStyle(sel_style)

            print("🎨 [OCCViewer] Fusion-style hover/select colors applied successfully")

        except Exception as e:
            print(f"⚠️ [OCCViewer._apply_fusion_colors] {e}")


    # ------------------------------------------------------------------
    def _draw_grid(self, ctx):
        try:
            # Clear previous
            for g in self._grid:
                try:
                    ctx.Erase(g, False)
                except Exception:
                    pass
            self._grid.clear()

            step = 20
            limit = 200

            for i in range(-limit, limit + step, step):
                # Soft fade towards edges
                fade = 1.0 - abs(i) / float(limit)
                alpha = max(0.15, fade * 0.80)   # 0.15..0.80
                col = Quantity_Color(0.75, 0.75, 0.75, Quantity_TOC_RGB)

                # X-lines (parallel to Y)
                p1 = Geom_CartesianPoint(gp_Pnt(-limit, i, 0))
                p2 = Geom_CartesianPoint(gp_Pnt(limit, i, 0))
                lx = AIS_Line(p1, p2)
                lx.SetColor(col)
                try:
                    lx.SetTransparency(1.0 - alpha)
                except Exception:
                    pass
                ctx.Display(lx, False)
                self._grid.append(lx)

                # Y-lines (parallel to X)
                p3 = Geom_CartesianPoint(gp_Pnt(i, -limit, 0))
                p4 = Geom_CartesianPoint(gp_Pnt(i, limit, 0))
                ly = AIS_Line(p3, p4)
                ly.SetColor(col)
                try:
                    ly.SetTransparency(1.0 - alpha)
                except Exception:
                    pass
                ctx.Display(ly, False)
                self._grid.append(ly)

            ctx.UpdateCurrentViewer()
            print("[DEBUG] Grid drawn (fading AIS lines)")
        except Exception as e:
            print(f"⚠️ [OCCViewer._draw_grid] {e}")

    # ------------------------------------------------------------------
    def _draw_axes(self, ctx):
        try:
            # Clear previous
            for a in self._axes:
                try:
                    ctx.Erase(a, False)
                except Exception:
                    pass
            self._axes.clear()

            axes = (
                (gp_Pnt(0, 0, 0), gp_Pnt(100, 0, 0), Quantity_Color(1.0, 0.2, 0.2, Quantity_TOC_RGB)),  # X (red)
                (gp_Pnt(0, 0, 0), gp_Pnt(0, 100, 0), Quantity_Color(0.2, 0.8, 0.2, Quantity_TOC_RGB)),  # Y (green)
                (gp_Pnt(0, 0, 0), gp_Pnt(0, 0, 100), Quantity_Color(0.2, 0.4, 1.0, Quantity_TOC_RGB)),  # Z (blue)
            )
            for s, e, col in axes:
                l = AIS_Line(Geom_CartesianPoint(s), Geom_CartesianPoint(e))
                l.SetColor(col)
                try:
                    l.SetWidth(2.5)
                except Exception:
                    pass
                ctx.Display(l, False)
                self._axes.append(l)

            ctx.UpdateCurrentViewer()
            print("[DEBUG] Axes drawn (safe version without text)")
        except Exception as e:
            print(f"⚠️ [OCCViewer._draw_axes] {e}")

    # ------------------------------------------------------------------
    def _install_hooks(self):
        """Install debounced hooks to auto-refresh after DisplayShape/EraseAll without recursion."""
        try:
            disp = self.display._display

            if getattr(self, "_hooks_installed", False):
                return

            def _patch(obj, name):
                """Patch a method with a debounced wrapper."""
                if not hasattr(obj, name):
                    return
                orig = getattr(obj, name)
                sentinel = f"__orig__{name}__"
                if hasattr(obj, sentinel):
                    return
                setattr(obj, sentinel, orig)

                def wrapper(*args, **kwargs):
                    # استدعاء الدالة الأصلية
                    res = orig(*args, **kwargs)

                    # ✅ إذا تم عرض شكل جديد (DisplayShape) نحاول تطبيق ألوانه
                    if name == "DisplayShape" and args:
                        try:
                            shape_arg = args[0]
                            if hasattr(shape_arg, "GetObject"):
                                self.apply_default_colors(shape_arg)
                        except Exception as e:
                            print(f"⚠️ [OCCViewer.wrapper.DisplayShape] {e}")

                    # تأجيل تحديث المشهد لتجنب التكرار
                    if not self._suspend_hooks:
                        self._refresh_timer.start()  # سيستدعي _do_refresh مرة واحدة فقط
                    return res

                setattr(obj, name, wrapper)

            # 🔹 نربط الـ hooks على الدالتين الرئيسيتين فقط
            for m in ("DisplayShape", "EraseAll"):
                _patch(disp, m)

            self._hooks_installed = True
            print("🧷 [OCCViewer] Hooks installed (debounced DisplayShape/EraseAll + color fix)")

        except Exception as e:
            print(f"⚠️ [OCCViewer._install_hooks] {e}")

    # ------------------------------------------------------------------
    def apply_default_colors(self, ais_obj):
        """ضبط ألوان الهوفر والتحديد يدويًا بشكل متوافق مع النسخ القديمة (pythonocc ≤ 7.9)."""
        try:
            from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

            # ألوان فيوجن
            base_color = Quantity_Color(0.75, 0.75, 0.75, Quantity_TOC_RGB)  # رمادي فاتح (شكل عادي)
            hover_color = Quantity_Color(1.0, 0.9, 0.0, Quantity_TOC_RGB)  # أصفر
            select_color = Quantity_Color(0.2, 0.6, 1.0, Quantity_TOC_RGB)  # أزرق

            # 🔸 نغير اللون الأساسي مباشرة
            ais_obj.SetColor(base_color)

            # 🔸 نحاول دعم التحديد: نضبط لون عند تحديد العنصر
            ctx = self.display._display.Context
            try:
                ctx.SetColor(ais_obj, base_color, False)
            except Exception:
                pass

            # نحاكي “تأثير الهوفر” بأن نغير لون الشكل لحظيًا عند مرور الماوس عليه
            # (الطريقة تعمل لأن MoveTo يعيد استدعاء Display مؤقتًا)
            def on_hover():
                try:
                    ctx.SetColor(ais_obj, hover_color, False)
                    ctx.UpdateCurrentViewer()
                except Exception:
                    pass

            def on_unhover():
                try:
                    ctx.SetColor(ais_obj, base_color, False)
                    ctx.UpdateCurrentViewer()
                except Exception:
                    pass

            # نحفظها بالذاكرة لنقدر نستخدمها لاحقًا لو احتجنا
            ais_obj._on_hover = on_hover
            ais_obj._on_unhover = on_unhover

            print("[DEBUG] Manual Fusion-style colors applied (base/hover/select)")

        except Exception as e:
            print(f"⚠️ [OCCViewer.apply_default_colors] {e}")

    # ------------------------------------------------------------------
    def _do_refresh(self):
        """Debounced refresh callback."""
        if self._is_refreshing:
            return
        self.refresh_scene()

    # ------------------------------------------------------------------
    def refresh_scene(self):
        """Re-display grid & axes safely, preventing recursive refresh loops."""
        if self._is_refreshing:
            return
        self._is_refreshing = True
        self._suspend_hooks = True
        try:
            disp = self.display._display
            ctx = disp.Context

            # Re-display or rebuild
            if not self._grid:
                self._draw_grid(ctx)
            else:
                for g in self._grid:
                    try:
                        ctx.Display(g, False)
                    except Exception:
                        pass

            if not self._axes:
                self._draw_axes(ctx)
            else:
                for a in self._axes:
                    try:
                        ctx.Display(a, False)
                    except Exception:
                        pass

            ctx.UpdateCurrentViewer()
            print("♻️ [OCCViewer] Grid & axes refreshed safely")

        except Exception as e:
            print(f"⚠️ [OCCViewer.refresh_scene] {e}")
        finally:
            self._suspend_hooks = False
            self._is_refreshing = False

    # ------------------------------------------------------------------
    def reset_camera(self):
        try:
            view = self.display._display.View
            view.SetProj(1, -1, 0.7)
            view.SetTwist(0)
            view.Redraw()
            print("📸 [Camera] Reset to Fusion-style angle")
        except Exception as e:
            print(f"⚠️ [OCCViewer.reset_camera] {e}")

    # ------------------------------------------------------------------
    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        try:
            self.display.Context.MoveTo(e.x(), e.y(), self.display._display.Viewer, True)
            self.display._display.View.Redraw()
        except Exception:
            pass

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        if e.button() == Qt.LeftButton:
            try:
                self.display.Context.Select(True)
                self.display._display.View.Redraw()
            except Exception:
                pass
