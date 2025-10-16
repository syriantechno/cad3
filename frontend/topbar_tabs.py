from PyQt5.QtWidgets import QWidget, QTabWidget, QHBoxLayout, QToolButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize
from frontend.style import TOPBAR_STYLE
from file_ops import (export_step, import_step, load_project, save_file)
from PyQt5.QtWidgets import QFileDialog


def create_topbar_tabs(parent):
    tabs = QTabWidget()
    tabs.setStyleSheet(TOPBAR_STYLE)

    def create_tab(tab_name, tools):
        tab = QWidget()
        tab.setMinimumHeight(60)  # ارتفاع Panel فقط
        layout = QHBoxLayout(tab)
        layout.setAlignment(Qt.AlignLeft)
        layout.setSpacing(4)
        layout.setContentsMargins(4, 0, 4, 0)

        for icon_path, text, callback, checkable in tools:
            btn = QToolButton(parent)
            btn.setIcon(QIcon(icon_path))
            btn.setText(text)
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setIconSize(QSize(28, 28))
            btn.setFixedSize(64, 64)
            btn.setCheckable(checkable)

            if checkable:
                # لأزرار Toggle مثل Grid & Axes
                btn.toggled.connect(callback)
            else:
                # لأزرار عادية
                btn.clicked.connect(callback)

            layout.addWidget(btn)

        tabs.addTab(tab, tab_name)

    def open_file():
        path, _ = QFileDialog.getOpenFileName(parent, "Open Project", "", "Alucam Project (*.alucam)")
        if path:
            shape, meta = parent.load_project(path)
            if shape:
                parent.current_shape = shape
                parent.display.DisplayShape(shape, update=True)

    def save_file():
        path, _ = QFileDialog.getSaveFileName(parent, "Save Project", "", "Alucam Project (*.alucam)")
        if path:
            metadata = {"name": "My Project"}
            parent.save_project(parent.current_shape, path, metadata)

    def import_file():
        path, _ = QFileDialog.getOpenFileName(parent, "Import STEP", "", "STEP files (*.step *.stp)")
        if path:
            shape = parent.import_step(path)
            if shape:
                parent.current_shape = shape
                parent.display.DisplayShape(shape, update=True)

    def export_file():
        path, _ = QFileDialog.getSaveFileName(parent, "Export STEP", "", "STEP files (*.step *.stp)")
        if path:
            parent.export_step(parent.current_shape, path)

    # ===== Home Tab =====
    home_tools = [
        ("frontend/icons/open.png", "Open File", open_file, False),
        ("frontend/icons/new.png", "New File", lambda: print("New File"), False),
        ("frontend/icons/save.png", "Save File", save_file, False),
        ("frontend/icons/import.png", "Import File", import_file, False),
        ("frontend/icons/export.png", "Export File", export_file, False)
    ]
    create_tab("Home", home_tools)

    # ===== Extrude Tab =====
    extrude_tools = [
        ("frontend/icons/extrude.png", "Extrude", lambda: parent.show_extrude_window(0), False)
    ]
    create_tab("Extrude", extrude_tools)

    # ===== Operation Tab =====
    operation_tools = [
        ("frontend/icons/cut.png", "Cut", lambda: print("Cut"), False),
        ("frontend/icons/hole.png", "Hole", lambda: print("Hole"), False),
        ("frontend/icons/lock.png", "Lock", lambda: print("Lock"), False),
        ("frontend/icons/etc.png", "Etc", lambda: print("Etc"), False)
    ]
    create_tab("Operation", operation_tools)

    # ===== Tools Tab =====
    tools_tools = [

        ("frontend/icons/tools.png", "Tools", lambda: print("Tools clicked"), False),
        ("frontend/icons/tools_manager.png", "Tool Manager", lambda: parent.show_extrude_window(3), False)
    ]

    create_tab("Tools", tools_tools)

    # ===== Profile Tab =====

    profile_tools = [
        ("frontend/icons/profile.png", "Profile", lambda: parent.open_add_profile_page(), False)

    ]
    create_tab("Profile", profile_tools)

    # ===== Help Tab =====
    help_tools = [
        ("frontend/icons/help.png", "Help", lambda: print("Help"), False),
        ("frontend/icons/about.png", "About", lambda: print("About"), False)
    ]
    create_tab("Help", help_tools)

    return tabs
