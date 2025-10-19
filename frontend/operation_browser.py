# ==============================================================
#  File: operation_browser.py
#  Purpose: Fusion-style Operation Browser (Profiles → Extrudes → Holes)
# ==============================================================

from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QAction
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont, QIcon, QColor, QBrush
from pathlib import Path

# ==============================================================
#  Icons
# ==============================================================
ICON_PATH = Path("frontend/icons")
PROFILE_ICON = QIcon(str(ICON_PATH / "profile.svg"))
EXTRUDE_ICON = QIcon(str(ICON_PATH / "extrude.svg"))
HOLE_ICON = QIcon(str(ICON_PATH / "hole.svg"))
FOLDER_ICON = QIcon(str(ICON_PATH / "folder.svg"))


class OperationBrowser(QTreeWidget):
    """شجرة عمليات CAD منظمة مثل Fusion"""
    item_selected = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.setHeaderLabels(["Operation", "Details"])
        self.setColumnCount(2)

        # 🎨 تنسيق عام
        self.setIndentation(18)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #f7f7f7;
                border: none;
                font-size: 10.5pt;
            }
            QTreeWidget::item {
                padding: 3px 4px;
            }
            QTreeWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
        """)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemClicked.connect(self._on_item_clicked)

        # الجذر العام
        self.root_profiles = QTreeWidgetItem(["Profiles"])
        self.root_profiles.setIcon(0, FOLDER_ICON)
        self.addTopLevelItem(self.root_profiles)
        self.root_profiles.setExpanded(True)

        # بيانات داخلية
        self._operations = []
        self._profile_items = {}
        self._extrude_items = {}

        # عنوان غامق
        bold = QFont()
        bold.setBold(True)
        self.root_profiles.setFont(0, bold)

    # ==========================================================
    # 📄 إضافة Profile
    # ==========================================================
    def add_profile(self, name: str):
        if not name:
            name = "Unnamed"

        if name in self._profile_items:
            print(f"⚠️ [OPS] Profile '{name}' already exists.")
            return self._profile_items[name]

        prof_item = QTreeWidgetItem([name, "Profile"])
        prof_item.setIcon(0, PROFILE_ICON)
        prof_item.setExpanded(True)
        self.root_profiles.addChild(prof_item)

        self._profile_items[name] = prof_item
        self._extrude_items[name] = []
        self._operations.append({"type": "Profile", "name": name})

        print(f"📄 [OPS] Added Profile: {name}")
        self.expandAll()
        return prof_item

    # ==========================================================
    # 🧱 إضافة Extrude
    # ==========================================================
    def add_extrude(self, profile_name: str, distance: float, axis: str = "Y"):
        if not profile_name:
            profile_name = "Unnamed"
        if profile_name not in self._profile_items:
            self.add_profile(profile_name)

        prof_item = self._profile_items[profile_name]
        count = len(self._extrude_items[profile_name]) + 1
        label = f"Extrude #{count}"
        details = f"Axis={axis}, Height={distance:.1f}mm"

        extrude_item = QTreeWidgetItem([label, details])
        extrude_item.setIcon(0, EXTRUDE_ICON)
        extrude_item.setExpanded(True)
        prof_item.addChild(extrude_item)

        # مجلد عمليات فرعية
        ops_group = QTreeWidgetItem(["Operations", ""])
        ops_group.setIcon(0, FOLDER_ICON)
        ops_group.setExpanded(True)
        extrude_item.addChild(ops_group)

        self._extrude_items[profile_name].append(extrude_item)
        op_data = {
            "type": "Extrude",
            "profile": profile_name,
            "axis": axis,
            "distance": distance
        }
        extrude_item.setData(0, Qt.UserRole, op_data)
        self._operations.append(op_data)
        self.expandAll()

        print(f"🧱 [OPS] Added Extrude for {profile_name}: {distance}mm ({axis})")
        return extrude_item

    # ==========================================================
    # 🕳️ إضافة Hole داخل آخر Extrude
    # ==========================================================
    def add_hole(self, profile_name: str, position, diameter, depth, axis):
        if not profile_name:
            profile_name = "Unnamed"

        if profile_name not in self._profile_items:
            self.add_profile(profile_name)
        if not self._extrude_items[profile_name]:
            self.add_extrude(profile_name, 0.0, axis)

        last_extrude = self._extrude_items[profile_name][-1]
        ops_group = last_extrude.child(0)

        count = ops_group.childCount() + 1
        label = f"Hole #{count}"
        details = f"Ø{diameter:.1f}, Depth={depth:.1f}mm, Axis={axis}"

        hole_item = QTreeWidgetItem([label, details])
        hole_item.setIcon(0, HOLE_ICON)
        hole_item.setForeground(0, QBrush(QColor("#0078d4")))
        ops_group.addChild(hole_item)

        x, y, z = position
        op_data = {
            "type": "Hole",
            "profile": profile_name,
            "x": float(x),
            "y": float(y),
            "z": float(z),
            "dia": float(diameter),
            "depth": float(depth),
            "axis": str(axis)
        }
        hole_item.setData(0, Qt.UserRole, op_data)
        self._operations.append(op_data)
        self.expandAll()
        print(f"🕳 [OPS] Added Hole to {profile_name}: {op_data}")

        return hole_item

    # ==========================================================
    # 🎛️ أدوات عامة
    # ==========================================================
    def _on_item_clicked(self, item, column):
        parent = item.parent()
        category = parent.text(0) if parent else "Root"
        name = item.text(0)
        self.item_selected.emit(category, name)

    def _show_context_menu(self, position):
        item = self.itemAt(position)
        if not item:
            return
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
            op_data = item.data(0, Qt.UserRole)
            if op_data in self._operations:
                self._operations.remove(op_data)
            parent.removeChild(item)
            print(f"🗑 [OPS] Deleted: {op_data}")

    def _rename_item(self, item):
        self.editItem(item, 0)

    # ==========================================================
    # 🔧 API خارجي
    # ==========================================================
    def list_operations(self):
        return list(self._operations)

    def clear_all(self):
        self.root_profiles.takeChildren()
        self._operations.clear()
        self._profile_items.clear()
        self._extrude_items.clear()
        print("🧹 [OPS] Cleared all operations.")
