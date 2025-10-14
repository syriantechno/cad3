# frontend/tree.py
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import Qt

class Tree(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TreeFrame")
        self.setHeaderHidden(True)  # إخفاء العنوان العلوي مثل Fusion
        self.setRootIsDecorated(True)  # إظهار أسهم التوسيع

        # إزالة الحدود، خلفية رمادية فاتحة مثل Fusion
        self.setStyleSheet("""
            QTreeWidget {
                background: rgb(245, 245, 245);
                border: none;
            }
            QTreeWidget::item {
                background: transparent;
                padding: 4px 6px;
            }
            QTreeWidget::item:hover {
                background: rgb(230, 230, 230);
            }
            QTreeWidget::item:selected {
                background: rgb(0, 120, 215);
                color: white;
            }
        """)

        self._populate_items()

    def _populate_items(self):
        # 🧭 Document Settings
        doc_item = QTreeWidgetItem(["Document Settings"])
        doc_item.setExpanded(True)

        # ⚙ Named Views
        views_item = QTreeWidgetItem(["Named Views"])
        views_item.addChild(QTreeWidgetItem(["TOP"]))
        views_item.addChild(QTreeWidgetItem(["FRONT"]))
        views_item.addChild(QTreeWidgetItem(["RIGHT"]))
        views_item.addChild(QTreeWidgetItem(["HOME"]))
        views_item.setExpanded(True)

        # 🌐 Origin
        origin_item = QTreeWidgetItem(["Origin"])
        origin_item.addChild(QTreeWidgetItem(["X"]))
        origin_item.addChild(QTreeWidgetItem(["Y"]))
        origin_item.addChild(QTreeWidgetItem(["Z"]))
        origin_item.addChild(QTreeWidgetItem(["XY"]))
        origin_item.addChild(QTreeWidgetItem(["XZ"]))
        origin_item.addChild(QTreeWidgetItem(["YZ"]))
        origin_item.setExpanded(True)

        # 🧱 Bodies
        bodies_item = QTreeWidgetItem(["Bodies"])
        body1_item = QTreeWidgetItem(["Body1"])
        bodies_item.addChild(body1_item)
        bodies_item.setExpanded(True)

        # إضافة كل العناصر للمستوى الأعلى
        self.addTopLevelItems([doc_item, views_item, origin_item, bodies_item])
