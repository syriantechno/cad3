from OCC.Display.backend import load_backend
load_backend('pyqt5')

from OCC.Display.qtDisplay import qtViewer3d
from PyQt5.QtWidgets import QWidget, QVBoxLayout

class OCCViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.display = qtViewer3d(self)
        layout = QVBoxLayout()
        layout.addWidget(self.display)
        self.setLayout(layout)

    def enable_trihedron(self):
        from OCC.Core.V3d import V3d_TypeOfOrientation

        try:
            view = self.display._display.View
            view.TriedronDisplay(True)
            view.SetTrihedronPosition(V3d_TypeOfOrientation.V3d_TOB_BOTTOM_LEFT)
            view.SetTrihedronSize(0.08)
            view.SetTrihedronVisibility(True)
            self.display._display.Context.UpdateCurrentViewer()
        except Exception as e:
            print(f"[trihedron] error: {e}")