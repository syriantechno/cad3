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
