from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QAction
from PyQt5.QtCore import pyqtSignal, Qt

class OperationBrowser(QTreeWidget):
    item_selected = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.setHeaderLabels(["Operation", "Details"])
        self.setColumnCount(2)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemClicked.connect(self._on_item_clicked)

        self.profile_root = QTreeWidgetItem(["Profiles"])
        self.extrude_root = QTreeWidgetItem(["Extrudes"])
        self.hole_root = QTreeWidgetItem(["Holes"])

        self.addTopLevelItem(self.profile_root)
        self.addTopLevelItem(self.extrude_root)
        self.addTopLevelItem(self.hole_root)

    def add_profile(self, name):
        item = QTreeWidgetItem([name, "DXF"])
        self.profile_root.addChild(item)
        return item

    def add_extrude(self, profile_name, distance):
        label = f"{profile_name} → {distance}mm"
        item = QTreeWidgetItem([label, "Extrude"])
        self.extrude_root.addChild(item)
        return item

    def add_hole(self, position, diameter, axis):
        x, y, z = position
        label = f"Hole @ ({x},{y},{z}) Ø{diameter} Axis:{axis}"
        item = QTreeWidgetItem([label, "Hole"])
        self.hole_root.addChild(item)
        return item

    def _on_item_clicked(self, item, column):
        category = item.parent().text(0) if item.parent() else "Root"
        name = item.text(0)
        self.item_selected.emit(category, name)

    def currentItem(self):
        return self.selectedItems()[0] if self.selectedItems() else None

    def _show_context_menu(self, position):
        item = self.itemAt(position)
        if item and item.parent():
            menu = QMenu()
            delete_action = QAction("Delete", self)
            rename_action = QAction("Rename", self)

            delete_action.triggered.connect(lambda: self._delete_item(item))
            rename_action.triggered.connect(lambda: self._rename_item(item))

            menu.addAction(delete_action)
            menu.addAction(rename_action)
            menu.exec_(self.viewport().mapToGlobal(position))

    def _delete_item(self, item):
        parent = item.parent()
        if parent:
            parent.removeChild(item)

    def _rename_item(self, item):
        self.editItem(item, 0)