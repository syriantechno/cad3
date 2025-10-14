# frontend/tree.py

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class Tree(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 30, 120);
                border-radius: 8px;
                color: white;
            }
            QLabel {
                padding: 6px;
                font-size: 14px;
            }
        """)
        self.setLayout(QVBoxLayout())
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.raise_()

    def add_item(self, name, shape=None, callback=None):
        label = QLabel(name)
        label.setStyleSheet("background-color: transparent;")
        if callback:
            label.mousePressEvent = lambda event: callback(shape)
        self.layout().addWidget(label)