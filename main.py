# main.py
from OCC.Display.backend import load_backend
load_backend('pyqt5')  # أو 'qt-pyqt6' حسب بيئتك
import sys
from PyQt5.QtWidgets import QApplication
from gui_fusion import AlumCamGUI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AlumCamGUI()
    window.show()
    sys.exit(app.exec_())

