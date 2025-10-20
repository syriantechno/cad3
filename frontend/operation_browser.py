# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QHBoxLayout, QPushButton, QMenu, QAction
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QColor

class OperationBrowser(QWidget):
    """
    شجرة عمليات احترافية:
    - كل Profile جذر
    - تحتوِيه عمليات (Hole / Extrude ...)
    - تلوين + أيقونات + Tooltip
    - عدّاد أسفل الشجرة
    - API متوافقة: add_profile, add_hole
    """

    ICONS = {
        "profile": "frontend/icons/profile.png",
        "hole": "frontend/icons/hole.png",
        "extrude": "frontend/icons/extrude.png",
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self._profiles = {}   # name -> QTreeWidgetItem
        self._ops_count = 0
        self._holes_count = 0

        layout = QVBoxLayout(self)

        # عنوان بسيط
        title = QLabel("Operation Browser")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: 600; padding: 6px;")
        layout.addWidget(title)

        # الشجرة
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Operation", "Details"])
        self.tree.setColumnWidth(0, 180)
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.tree)

        # شريط سفلي بسيط: توليد الجي كود + عدادات
        bottom = QHBoxLayout()
        self.btn_generate = QPushButton("Generate G-Code")
        self.btn_generate.setObjectName("btnApply")
        self.btn_generate.clicked.connect(self._emit_generate)
        bottom.addWidget(self.btn_generate)

        self.stats = QLabel("⚙️ Total: 0 ops | 0 holes")
        self.stats.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bottom.addWidget(self.stats)
        layout.addLayout(bottom)

        self.setLayout(layout)

    # ---------- API ----------
    def add_profile(self, profile_name: str):
        if not profile_name:
            return
        if profile_name in self._profiles:
            # موجود مسبقًا
            return
        root = QTreeWidgetItem(self.tree, [profile_name, ""])
        if self.ICONS["profile"]:
            root.setIcon(0, QIcon(self.ICONS["profile"]))
        root.setFirstColumnSpanned(False)
        root.setExpanded(True)
        self._profiles[profile_name] = root
        self._update_stats()

    def add_extrude(self, profile_name: str, height: float, axis: str = "Z"):
        """عملية عرض فقط (غير مُصدّرة كجي كود حالياً)"""
        root = self._ensure_profile(profile_name)
        text = f"Extrude {height:g} along {axis}"
        node = QTreeWidgetItem(root, ["Extrude", text])
        if self.ICONS["extrude"]:
            node.setIcon(0, QIcon(self.ICONS["extrude"]))
        node.setToolTip(0, text)
        node.setForeground(0, QColor(80, 80, 80))
        self._ops_count += 1
        self._update_stats()
        root.setExpanded(True)

    def add_hole(self, profile_name: str, pos_xyz, dia, depth, axis, tool: str = None):
        """
        متوافق مع النداءات القديمة:
        add_hole(profile, (x,y,z), dia, depth, axis, tool=?)
        """
        root = self._ensure_profile(profile_name)
        x, y, z = pos_xyz
        head = f"Hole Ø{float(dia):g} ⬇{float(depth):g} ({axis})"
        detail = f"@ ({float(x):g},{float(y):g},{float(z):g})"
        if tool:
            detail += f" | Tool: {tool}"

        node = QTreeWidgetItem(root, ["Hole", f"{head}  {detail}"])
        node.setToolTip(0, "Drilling operation")
        node.setToolTip(1, f"Dia={dia}, Depth={depth}, Axis={axis}, Pos=({x},{y},{z})")
        if self.ICONS["hole"]:
            node.setIcon(0, QIcon(self.ICONS["hole"]))
        node.setForeground(0, QColor(30, 90, 160))  # أزرق لعمليات الحفر

        node.setData(0, Qt.UserRole, {
            "type": "Hole",
            "x": float(x), "y": float(y), "z": float(z),
            "dia": float(dia), "depth": float(depth),
            "axis": axis, "tool": tool or ""
        })

        self._ops_count += 1
        self._holes_count += 1
        self._update_stats()
        root.setExpanded(True)

    def get_all_ops(self):
        """إرجاع قائمة بكل العمليات بشكل قاموسات مرتبة حسب البروفايل."""
        results = []
        for profile, root in self._profiles.items():
            count = root.childCount()
            for i in range(count):
                child = root.child(i)
                meta = child.data(0, Qt.UserRole)
                if meta:
                    rec = dict(meta)
                    rec["profile"] = profile
                    results.append(rec)
        return results

    # ---------- داخلي ----------
    def _ensure_profile(self, profile_name):
        if not profile_name:
            profile_name = "Unnamed"
        if profile_name not in self._profiles:
            self.add_profile(profile_name)
        return self._profiles[profile_name]

    def _update_stats(self):
        self.stats.setText(f"⚙️ Total: {self._ops_count} ops | {self._holes_count} holes")

    # ---------- Context Menu ----------
    def _on_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        if item.parent() is None:
            # عنصر بروفايل
            act_gen = QAction("Generate G-Code for this profile", self)
            act_gen.triggered.connect(lambda: self._emit_generate(item))
            menu.addAction(act_gen)
        else:
            # عنصر عملية
            op_meta = item.data(0, Qt.UserRole) or {}
            act_show = QAction("Show details", self)
            act_show.triggered.connect(lambda: self._show_msg(op_meta))
            menu.addAction(act_show)

            menu.addSeparator()
            act_del = QAction("Delete", self)
            act_del.triggered.connect(lambda: self._delete_item(item))
            menu.addAction(act_del)

        menu.exec_(self.tree.viewport().mapToGlobal(pos))

    def _delete_item(self, item: QTreeWidgetItem):
        parent = item.parent()
        if parent is None:
            # حذف بروفايل بالكامل
            name = item.text(0)
            self._tree_remove(item)
            self._profiles.pop(name, None)
        else:
            meta = item.data(0, Qt.UserRole) or {}
            if meta.get("type") == "Hole":
                self._holes_count = max(0, self._holes_count - 1)
            self._ops_count = max(0, self._ops_count - 1)
            self._tree_remove(item)
        self._update_stats()

    def _tree_remove(self, item: QTreeWidgetItem):
        if item.parent():
            item.parent().removeChild(item)
        else:
            idx = self.tree.indexOfTopLevelItem(item)
            self.tree.takeTopLevelItem(idx)

    def _show_msg(self, meta: dict):
        from PyQt5.QtWidgets import QMessageBox
        if not meta:
            QMessageBox.information(self, "Operation", "No metadata.")
            return
        txt = "\n".join([f"{k}: {v}" for k, v in meta.items()])
        QMessageBox.information(self, "Operation", txt)

    # ---------- إشارات توليد الجي كود ----------
    def _emit_generate(self, root_item=None):
        """
        ينادي signal غير مباشر عبر خاصية ديناميكية على الـparent:
        - إذا توفّر self.parent().on_generate_from_ops، يتم تمرير قائمة العمليات
        - وإلا، فقط يطبع للكونسول
        """
        ops = []
        if root_item and root_item.parent() is None:
            # توليد بروفايل واحد
            profile = root_item.text(0)
            count = root_item.childCount()
            for i in range(count):
                child = root_item.child(i)
                meta = child.data(0, Qt.UserRole)
                if meta:
                    rec = dict(meta)
                    rec["profile"] = profile
                    ops.append(rec)
        else:
            # كل العمليات
            ops = self.get_all_ops()

        handler = getattr(self.parent(), "on_generate_from_ops", None)
        if callable(handler):
            handler(ops)
        else:
            print("[GCODE] Emit ops:", ops)
