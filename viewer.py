from OCC.Display.backend import load_backend
load_backend('pyqt5')

from OCC.Display.qtDisplay import qtViewer3d
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QTimer
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB, Quantity_NOC_GRAY, Quantity_NOC_LIGHTSTEELBLUE
from OCC.Core.Aspect import Aspect_GT_Rectangular, Aspect_GDM_Lines

class OCCViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # إنشاء العارض فقط
        self.display = qtViewer3d(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.display)
        self.setLayout(layout)

        # مؤقت لتهيئة العرض بعد ظهور الواجهة
        QTimer.singleShot(800, self.init_viewer)

    def init_viewer(self):
        """تهيئة العرض بعد أن يصبح View جاهز داخلياً"""
        view = self.display._display.View
        viewer = self.display._display.Viewer
        ctx = self.display.Context

        try:
            if not view.IsDefined():
                print("❌ View غير معرف بعد، تأجيل التهيئة...")
                QTimer.singleShot(500, self.init_viewer)
                return
        except Exception:
            print("❌ View غير جاهز داخلياً، إعادة المحاولة...")
            QTimer.singleShot(500, self.init_viewer)
            return

        print("✅ Viewer جاهز داخلياً، نطبق التهيئة...")

        # ===== الخلفية =====
        top = Quantity_Color(0.92, 0.92, 0.92, Quantity_TOC_RGB)
        bottom = Quantity_Color(1.0, 1.0, 1.0, Quantity_TOC_RGB)
        view.SetBgGradientColors(top, bottom, 2, True)  # من الأعلى للأسفل

        # ===== الشبكة =====
        viewer.ActivateGrid(Aspect_GT_Rectangular, Aspect_GDM_Lines)
        viewer.SetGridColor(Quantity_NOC_GRAY)
        viewer.DisplayGrid()

        # ===== المحاور =====
        viewer.SetTrihedronSize(0.05)
        viewer.SetTrihedronColor(Quantity_NOC_LIGHTSTEELBLUE)

        # ===== لون الهوفر والاختيار =====
        hover_color = Quantity_Color(0.85, 0.85, 0.85, Quantity_TOC_RGB)
        select_color = Quantity_Color(1.0, 0.6, 0.0, Quantity_TOC_RGB)
        ctx.SetHighlightColor(hover_color)
        ctx.SetSelectionColor(select_color)
        ctx.SetAutomaticHighlight(True)

        view.Redraw()
        print("✅ الشبكة + الخلفية + الهوفر تم تهيئتها بنجاح")
