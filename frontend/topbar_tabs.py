from PyQt5.QtWidgets import QWidget, QTabWidget, QHBoxLayout, QToolButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize
from frontend.style import TOPBAR_STYLE

from PyQt5.QtWidgets import QFileDialog
from file_ops import open_project_dialog


def create_topbar_tabs(parent):
    tabs = QTabWidget()
    tabs.setStyleSheet(TOPBAR_STYLE)

    def create_tab(tab_name, tools):
        tab = QWidget()
        tab.setFixedHeight(110)
        tab.setMinimumHeight(100)  # ارتفاع Panel فقط
        layout = QHBoxLayout(tab)
        layout.setAlignment(Qt.AlignLeft)
        layout.setSpacing(4)
        layout.setContentsMargins(4, 0, 4, 0)


        for icon_path, tooltip_text, callback, checkable in tools:
            btn = QToolButton(parent)
            btn.setIcon(QIcon(icon_path))
            #btn.setText(text)
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            tab.setMinimumHeight(10)  # ✅ يعطي مساحة مريحة للنص والأيقونة
            btn.setIconSize(QSize(48, 48))
            btn.setFixedSize(48, 48)
            btn.setCheckable(checkable)

            # 🏷️ Tooltip تلقائي
            if tooltip_text:
                btn.setToolTip(tooltip_text)
            else:
                # في حال ما فيه نص بالـ tuple، نستخدم اسم الملف كخطة احتياطية
                btn.setToolTip(icon_path.split("/")[-1].replace(".png", ""))

            if checkable:
                # لأزرار Toggle مثل Grid & Axes
                btn.toggled.connect(callback)
            else:
                # لأزرار عادية
                btn.clicked.connect(callback)

            layout.addWidget(btn)


        tabs.addTab(tab, tab_name)


    # ===== Home Tab =====
    # home_tools = [
    #     ("frontend/icons/open.svg", "Open File", lambda: open_project_dialog(parent), False),
    #     ("frontend/icons/new.svg", "New File", lambda: parent.new_file(), False),
    #     ("frontend/icons/save.png", "Save File", lambda: parent.save_project(), False),
    #     ("frontend/icons/import.png", "Import File", lambda: parent.load_dxf(), False),
    #     ("frontend/icons/export.png", "Export File", lambda: parent.export_stl_dialog(), False)
    #
    # ]
    # create_tab("Home", home_tools)

    # ===== Sketch Tab =====
    def safe_call(parent, action):
        """يستدعي دالة داخل parent بأمان بدون كراش"""
        try:
            if hasattr(parent, "sketch_page"):
                page = parent.sketch_page
                if action == "draw_circle":
                    print("[DEBUG] Circle button clicked — calling draw_circle() safely")
                    parent.sketch_page.set_mode("circle")
                elif action == "draw_line":
                    print("[DEBUG] Line button clicked — calling draw_line() safely")
                    page.draw_line()
                elif action == "draw_rect":
                    print("[DEBUG] Rectangle button clicked — calling draw_rect() safely")
                    page.draw_rect()
                elif action == "draw_arc":
                    print("[DEBUG] Arc button clicked — calling draw_arc() safely")
                    page.draw_arc()
            else:
                print(f"⚠️ [SAFE_CALL] parent.sketch_page غير جاهزة بعد")
        except Exception as e:
            import traceback
            print(f"🔥 [SAFE_CALL ERROR] أثناء تنفيذ {action}: {e}")
            traceback.print_exc()

    sketch_tools = [
        ("frontend/icons/sketch/stop.png", "Stop", lambda: parent.open_add_profile_page(), False),
        ("frontend/icons/sketch/circle.png", "Circle", lambda: safe_call(parent, "draw_circle"), False),
        ("frontend/icons/sketch/rect.png", "Rectangle", lambda: parent.show_tool_page(4), False),
        ("frontend/icons/sketch/arc.png", "Arc", lambda: parent.show_tool_page(4), False),

    ]
    create_tab("sketch", sketch_tools)


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
        ("frontend/icons/lock.png", "Shape", lambda: parent.show_tool_page(7), False)

    ]
    create_tab("Operation", operation_tools)

    # ===== Tools Tab =====
    tools_tools = [

        ("frontend/icons/tools.png", "Tools", lambda: print("Tools clicked"), False),
        ("frontend/icons/tools_manager.png", "Tool Manager", lambda: parent.show_extrude_window(3), False)
    ]

    create_tab("Tools", tools_tools)

    # ===== G-Code Tab =====
    g_code = [


        ("frontend/icons/tools_manager.png", "G-code", lambda: parent.show_extrude_window(8), False),
        ("frontend/icons/tools_manager.png", "sim_page", lambda: parent.show_extrude_window(10), False)
    ]

    create_tab("G-Code", g_code)



    # ===== Help Tab =====
    help_tools = [
        ("frontend/icons/help.png", "Help", lambda: print("Help"), False),
        ("frontend/icons/about.png", "About", lambda: print("About"), False)
    ]
    create_tab("Help", help_tools)

    return tabs
