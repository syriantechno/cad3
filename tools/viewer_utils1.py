from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.Prs3d import Prs3d_LineAspect
from OCC.Core.Aspect import Aspect_TOL_SOLID

def setup_viewer_colors(display):
    """
    يضبط مظهر العارض: خلفية بيضاء + حدود/خطوط سوداء.
    متوافق مع pythonocc 7.7+.
    """
    white = Quantity_Color(1.0, 1.0, 1.0, Quantity_TOC_RGB)
    black = Quantity_Color(0.0, 0.0, 0.0, Quantity_TOC_RGB)

    view = display.View

    # خلفية بيضاء (لونان متطابقان + إطفاء التدرج)
    view.SetBgGradientColors(white, white, True)
    view.SetBgGradientStyle(0)  # 0 = no gradient
    view.MustBeResized()

    # حدود الوجوه بالأسود
    drawer = display.Context.DefaultDrawer()
    drawer.SetFaceBoundaryDraw(True)
    line_aspect = Prs3d_LineAspect(black, Aspect_TOL_SOLID, 1.0)
    drawer.SetFaceBoundaryAspect(line_aspect)

    # تحديث
    display.Context.UpdateCurrentViewer()
    view.Redraw()
