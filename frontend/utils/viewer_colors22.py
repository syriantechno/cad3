# frontend/utils/viewer_colors.py
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

def setup_viewer_colors(display):
    """
    إعداد ألوان الخلفية، الهوفر، التحديد وغيرها للعارض (Fusion Style)
    """
    view = display._display.View

    # 🟡 الخلفية بتدرج رأسي (أعلى رمادي، أسفل أبيض)
    top_color = Quantity_Color(0.9, 0.9, 0.9, Quantity_TOC_RGB)
    bottom_color = Quantity_Color(1.0, 1.0, 1.0, Quantity_TOC_RGB)
    view.SetBgGradientColors(top_color, bottom_color, 1, True)  # 1 = عمودي
    view.Update()

    # ✨ لون Hover = رمادي فاتح
    hover_color = Quantity_Color(0.85, 0.85, 0.85, Quantity_TOC_RGB)
    display.Context.SetHighlightColor(hover_color)
    display.Context.SetAutomaticHighlight(True)


    # 🟠 لون التحديد = برتقالي باهت
    select_color = Quantity_Color(1.0, 0.6, 0.0, Quantity_TOC_RGB)
    display.Context.SetSelectionColor(select_color)


def _apply_view_theme_once(self):
    if getattr(self, "_theme_applied", False):
        return
    view = self.display.View
    ctx = self.display.Context
    viewer = self.display.Viewer

    try:
        # خلفية (تدرج رأسي)، لو ما توفر أو سبب مشكلة نتجاهله
        from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
        top = Quantity_Color(0.92, 0.92, 0.92, Quantity_TOC_RGB)
        bottom = Quantity_Color(1.00, 1.00, 1.00, Quantity_TOC_RGB)
        try:
            view.SetBgGradientColors(top, bottom, 1, True)  # 1 = Vertical
            view.Redraw()
        except Exception:
            pass

        # الشبكة عبر Viewer (أكثر ثباتًا من EnableGrid)
        try:
            from OCC.Core.Aspect import Aspect_GT_Rectangular, Aspect_GDM_Lines
            from OCC.Core.Quantity import Quantity_NOC_BLACK
            viewer.ActivateGrid(Aspect_GT_Rectangular, Aspect_GDM_Lines)
            viewer.SetPrivilegedPlane(0.0, 0.0, 1.0, 0.0)
            viewer.SetGridColor(Quantity_NOC_BLACK)
            viewer.DisplayGrid()
        except Exception:
            pass

        # ألوان hover/selection
        try:
            hover = Quantity_Color(0.85, 0.85, 0.85, Quantity_TOC_RGB)   # رمادي فاتح (بدل التركواز)
            select = Quantity_Color(1.0, 0.6, 0.0, Quantity_TOC_RGB)     # برتقالي باهت
            ctx.SetHighlightColor(hover)
            ctx.SetSelectionColor(select)
            ctx.SetAutomaticHighlight(True)
        except Exception:
            pass

        self._theme_applied = True
        print("✅ View theme applied once (background, grid, hover/selection).")
    except Exception as e:
        print(f"[WARN] theme apply skipped: {e}")
