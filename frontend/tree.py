# frontend/tree.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class Tree(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = set()
        self.setObjectName("TreeFrame")

        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("""
            #TreeFrame {
                background-color: rgb(240, 240, 240);
                border-radius: 8px;
                color: black;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

    def add_item(self, name, shape=None, callback=None):
        if name in self._items:
            return
        label = QLabel(name)
        self.layout().addWidget(label)
        self._items.add(name)
