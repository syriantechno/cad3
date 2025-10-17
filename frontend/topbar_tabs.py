from PyQt5.QtWidgets import QWidget, QTabWidget, QHBoxLayout, QToolButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize
from frontend.style import TOPBAR_STYLE

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



    # ===== Home Tab =====
    home_tools = [
        ("frontend/icons/open.png", "Open File", lambda: parent.open_file(), False),
        ("frontend/icons/new.png", "New File", lambda: parent.new_file(), False),
        ("frontend/icons/save.png", "Save File", lambda: parent.save_file(), False),
        ("frontend/icons/import.png", "Import File", lambda: parent.load_dxf(), False),
        ("frontend/icons/export.png", "Export File", lambda: parent.export_stl_dialog(), False)

    ]
    create_tab("Home", home_tools)

    # ===== Profile Tab =====

    profile_tools = [
        ("frontend/icons/profile.png", "Profile", lambda: parent.open_add_profile_page(), False),
        ("frontend/icons/profile.png", "Profile Manger", lambda: parent.show_tool_page(4), False)

    ]
    create_tab("Profile", profile_tools)

    # ===== Extrude Tab =====
    extrude_tools = [
        ("frontend/icons/extrude.png", "Extrude", lambda: parent.show_extrude_window(0), False)
    ]
    create_tab("Extrude", extrude_tools)

    # ===== Operation Tab =====
    operation_tools = [
        ("frontend/icons/cut.png", "Cut", lambda: parent.show_tool_page(6), False),
        ("frontend/icons/hole.png", "Hole", lambda: parent.show_tool_page(5), False),
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



    # ===== Help Tab =====
    help_tools = [
        ("frontend/icons/help.png", "Help", lambda: print("Help"), False),
        ("frontend/icons/about.png", "About", lambda: print("About"), False)
    ]
    create_tab("Help", help_tools)

    return tabs
