# frontend/operation_browser.py
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import pyqtSignal

class OperationBrowser(QTreeWidget):
    """
    شجرة العمليات (Profiles → Extrudes → Drills ...)
    مسؤولة عن عرض كل ما يحدث في العارض بشكل هرمي، مشابه للـ Browser في Fusion.
    """
    item_selected = pyqtSignal(str, str)  # category, name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
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
                background: rgb(235, 235, 235);
            }
            QTreeWidget::item:selected {
                background: rgb(0, 120, 215);
                color: white;
            }
        """)

        # جذر Profiles
        self.profiles_root = QTreeWidgetItem(["Profiles"])
        self.addTopLevelItem(self.profiles_root)
        self.profiles_root.setExpanded(True)

        # profile_name → profile_item
        self.profile_nodes = {}

        self.itemClicked.connect(self._on_item_clicked)

    # ---------- عمليات أساسية ----------
    def add_profile(self, profile_name: str):
        """إضافة بروفايل جديد"""
        if profile_name in self.profile_nodes:
            return self.profile_nodes[profile_name]
        p_item = QTreeWidgetItem([profile_name])
        self.profiles_root.addChild(p_item)
        self.profiles_root.setExpanded(True)
        self.profile_nodes[profile_name] = p_item
        return p_item

    def add_extrude(self, profile_name: str, distance: float):
        """إضافة عملية Extrude تحت بروفايل"""
        if profile_name not in self.profile_nodes:
            p_item = self.add_profile(profile_name)
        else:
            p_item = self.profile_nodes[profile_name]

        extrude_item = QTreeWidgetItem([f"Extrude {distance} mm"])
        p_item.addChild(extrude_item)
        p_item.setExpanded(True)
        return extrude_item

    def add_sub_operation(self, extrude_item: QTreeWidgetItem, op_name: str):
        """إضافة عملية فرعية (Drill / Cut ...) تحت extrude"""
        sub_item = QTreeWidgetItem([op_name])
        extrude_item.addChild(sub_item)
        extrude_item.setExpanded(True)
        return sub_item

    # ---------- التحديد ----------
    def _on_item_clicked(self, item, column):
        parent = item.parent()
        if parent is None:
            category = "root"
        elif parent == self.profiles_root:
            category = "profile"
        elif parent.text(0).startswith("Extrude"):
            category = "sub_op"
        elif item.text(0).startswith("Extrude"):
            category = "extrude"
        else:
            category = "unknown"
        self.item_selected.emit(category, item.text(0))
