# frontend/tree.py

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class Tree(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TreeFrame")
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)  # ← ضروري للشفافية
        self.setStyleSheet("""
            #TreeFrame {
                background-color: rgba(30, 30, 30, 120);
                border-radius: 8px;
                color: white;
            }
            #TreeFrame QLabel {
                padding: 6px;
                font-size: 14px;
                background-color: transparent;
            }
        """)
        self.setLayout(QVBoxLayout())


        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.raise_()

    def add_item(self, name, shape=None, callback=None):
        # تحقق من التكرار


        for i in range(self.layout().count()):
            widget = self.layout().itemAt(i).widget()
            if isinstance(widget, QLabel) and widget.text() == name:
                return  # العنصر موجود مسبقًا

        label = QLabel(name)
        label.setStyleSheet("background-color: transparent;")
        if callback:
            label.mousePressEvent = lambda event: callback(shape)
        self.layout().addWidget(label)
        print(f"Adding item: {name}")