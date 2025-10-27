# -*- coding: utf-8 -*-
"""
AlumCam GUI - Fusion-style interface using OCCViewer stable viewer
"""

import logging
from PyQt5.QtWidgets import QMainWindow, QPushButton, QFileDialog, QWidget, QVBoxLayout, QSplitter, QMessageBox
from PyQt5.QtCore import QTimer, Qt
from pathlib import Path

# === Imports ===
from frontend.topbar_tabs import create_topbar_tabs
from frontend.window.floating_window import create_tool_window
from frontend.operation_browser import OperationBrowser
from tools.tool_db import init_db
from tools.gcode_generator import generate_program, save_program, GCodeSettings
from dxf_tools import load_dxf_file
from frontend.fusion_topbar import FusionTopBar

# ✅ استبدلنا العارض الافتراضي بالعارض المستقر الرسمي
from OCCViewer import OCCViewer

logging.basicConfig(level=logging.DEBUG)


class AlumCamGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        init_db()
        self.setWindowTitle("AlumCam GUI - Fusion-style Viewer")
        self.setGeometry(100, 100, 1400, 800)

        # ===== Viewer & Browser =====
        self.viewer_widget = OCCViewer(self)
        print("🟢 Fusion Viewer ready (using OCCViewer)")
        self.display = self.viewer_widget.display._display

        self.active_profile_name = None
        self.active_profile_id = None

        # ===== Operation Browser =====
        self.op_browser = OperationBrowser()
        self.op_browser.setStyleSheet("background-color: rgba(220, 220, 220, 180);")
        self.op_browser.setFixedWidth(250)

        # 🎨 تطبيق ستايل إضافي إن وجد
        try:
            from frontend.style import OP_BROWSER_STYLE
            self.op_browser.setStyleSheet(self.op_browser.styleSheet() + OP_BROWSER_STYLE)
        except Exception:
            pass

        # ===== الشريط العلوي Fusion =====
        self.top_bar = FusionTopBar(self)
        self.setMenuWidget(self.top_bar)  # ← يظهر مباشرة تحت الـ title bar

        # ===== التبويبات =====
        self.top_tabs = create_topbar_tabs(self)

        # ===== الواجهة الرئيسية =====
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.op_browser)
        splitter.addWidget(self.viewer_widget)

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ترتيب العرض من الأعلى للأسفل
        self.top_tabs.setFixedHeight(72)  # 🔹 يحدد ارتفاع التبويبات
        main_layout.addWidget(self.top_tabs)
        main_layout.addWidget(splitter)

        self.setCentralWidget(main_widget)

        # ===== Floating tool window =====
        self.tool_dialog, self.show_tool_page = create_tool_window(self)
        self.tool_dialog.hide()

        # ===== Toolbar / Buttons =====
        self.delete_btn = QPushButton("🗑 Delete Operation")
        self.delete_btn.clicked.connect(self.delete_selected_operation)

        # ===== Geometry State =====
        self.loaded_shape = None
        self.hole_preview = None
        self.extrude_axis = "Y"


    # ------------------------------------------------------------------
    def on_generate_from_ops(self, ops_list):
        """تُستدعى عند توليد G-Code من OperationBrowser"""
        try:
            if hasattr(self, "gcode_page") and self.gcode_page:
                self.gcode_page.generate_from_ops(ops_list)
            else:
                print("[GCODE] Received ops:", ops_list)
        except Exception as e:
            print("[GCODE] handler error:", e)

    # ------------------------------------------------------------------
    def _export_gcode(self):
        """توليد G-Code كامل"""
        try:
            ops = self.op_browser.list_operations()
            if not ops:
                QMessageBox.information(self, "G-Code", "لا توجد عمليات في الشجرة.")
                return
            settings = GCodeSettings()
            program = generate_program(ops, settings)
            out_path = save_program(program, Path("output/gcode"), "full_program")
            QMessageBox.information(self, "G-Code", f"تم توليد G-Code:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "G-Code Error", str(e))

    # ------------------------------------------------------------------
    def on_operation_selected(self, category, name):
        """عرض الشكل عند اختيار عملية من الشجرة"""
        item = self.op_browser.currentItem()
        shape = getattr(item, "shape", None)
        if shape and not shape.IsNull():
            self.display_shape_with_axes(shape)

    # ------------------------------------------------------------------
    def display_shape(self, shape):
        """عرض شكل بدون أي شبكة أو محاور إضافية"""
        self.display.EraseAll()
        self.display.Context.Display(shape, True)
        self.display.Repaint()

    # ------------------------------------------------------------------
    def show_extrude_window(self, page_index=0):
        """عرض نافذة الأدوات العائمة (Extrude / Profile / Manager)"""
        geo = self.geometry()
        if self.tool_dialog.width() == 0:
            self.tool_dialog.resize(360, 420)
        x = geo.x() + geo.width() - self.tool_dialog.width() - 20
        y = geo.y() + 100
        self.tool_dialog.move(x, y)
        self.show_tool_page(page_index)
        print(f"[✅] Floating tool window (page {page_index}) shown.")

    # ------------------------------------------------------------------
    def load_dxf(self):
        """تحميل ملف DXF وعرضه في العارض"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Open DXF", "", "DXF Files (*.dxf)")
        if not file_name:
            return
        shape = load_dxf_file(file_name)
        if shape is None:
            return
        self.loaded_shape = shape
        QTimer.singleShot(100, self._safe_display_shape)
        item = self.op_browser.add_profile("DXF Profile")
        item.shape = self.loaded_shape

    # ------------------------------------------------------------------
    def _safe_display_shape(self):
        """عرض آمن للشكل بعد التحميل"""
        try:
            if self.loaded_shape:
                self.display_shape(self.loaded_shape)
        except Exception as e:
            print(f"Display failed: {e}")

    # ------------------------------------------------------------------
    def open_add_profile_page(self):
        """فتح صفحة إضافة بروفايل جديد"""
        print("[DEBUG] تم الضغط على زر Profile")

        if not hasattr(self, "tool_dialog") or self.tool_dialog is None:
            print("[ERROR] tool_dialog غير جاهز")
            return

        dialog = self.tool_dialog

        if not hasattr(dialog, "profile_page") or dialog.profile_page is None:
            print("[ERROR] profile_page غير جاهزة")
            return

        profile_page = dialog.profile_page
        print("[DEBUG] tool_dialog و profile_page جاهزين")

        # تصفير سياق التعديل
        dialog._edit_ctx.update({
            "active": False,
            "pid": None,
            "orig_name": None,
            "orig_dxf": None,
            "orig_img": None
        })

        # تصفير الحقول
        profile_page._p_name.clear()
        profile_page._p_code.clear()
        profile_page._p_dims.clear()
        profile_page._p_notes.clear()
        profile_page._dxf_path_edit.clear()

        self.show_tool_page(1)
        print("[DEBUG] show_tool_page(1) تم استدعاؤه بنجاح")

    # ------------------------------------------------------------------
    def save_project(self):
        from file_ops import save_project_dialog
        save_project_dialog(self)

    # ------------------------------------------------------------------
    def open_project(self):
        from file_ops import open_project_dialog
        open_project_dialog(self)

    # ------------------------------------------------------------------
    def new_file(self):
        """إنشاء مشروع جديد فارغ"""
        self.loaded_shape = None
        self.display.EraseAll()
        self.display.Repaint()
        print("🆕 تم إنشاء مشروع جديد فارغ")

    # ------------------------------------------------------------------
    def delete_selected_operation(self):
        """حذف العملية المحددة من الشجرة"""
        item = self.op_browser.currentItem()
        if item and item.parent():
            parent = item.parent()
            parent.removeChild(item)

            # عرض آخر عنصر متبقي
            remaining = parent.childCount()
            if remaining > 0:
                last_item = parent.child(remaining - 1)
                shape = getattr(last_item, "shape", None)
                if shape and not shape.IsNull():
                    self.display_shape(shape)
                else:
                    self.display.EraseAll()
            else:
                self.display.EraseAll()
