# tools/grid.py
from OCC.Core.gp import gp_Ax3, gp_Pnt, gp_Dir
from OCC.Core.V3d import V3d_RectangularGrid
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

def _set_xy_plane(viewer):
    # مستوى XY (Z لأعلى)
    ax3 = gp_Ax3(gp_Pnt(0.0, 0.0, 0.0), gp_Dir(0.0, 0.0, 1.0))
    viewer.SetPrivilegedPlane(ax3)

def _set_grid_style(view, *, gray=0.85):
    # لون شبكة رمادي فاتح + بدون echo
    grid_color = Quantity_Color(gray, gray, gray, Quantity_TOC_RGB)
    view.SetGridColor(grid_color)
    view.SetGridEcho(False)
    view.MustBeResized()

def setup_grid_and_axes(display):
    """
    تفعيل شبكة XY لا نهائية + أسماء المحاور (Triedron) في الزاوية السفلية اليسرى.
    """
    viewer = display.Viewer
    view = display.View

    _set_xy_plane(viewer)
    viewer.ActivateGrid(V3d_RectangularGrid)   # شبكة مستطيلة لا نهائية على XY
    _set_grid_style(view)
    view.TriedronDisplay()                     # يعرض X/Y/Z في الركن (Left-Lower) افتراضيًا
    view.Redraw()

def toggle_grid_and_axes(display, state: bool):
    """
    إظهار/إخفاء الشبكة + أسماء المحاور.
    """
    viewer = display.Viewer
    view = display.View

    if state:
        _set_xy_plane(viewer)
        viewer.ActivateGrid(V3d_RectangularGrid)
        _set_grid_style(view)
        view.TriedronDisplay()
    else:
        viewer.DeactivateGrid()
        view.TriedronErase()

    view.Redraw()
