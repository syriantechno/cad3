from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QLabel, QMessageBox, QVBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from pathlib import Path
from frontend.window.tools_db import ToolsDB


class ToolsManagerWindow(QWidget):
    def __init__(self, tool_types: dict):
        super().__init__()
        self._tool_types = tool_types
        self._db = ToolsDB()
        self._current_edit_id = None  # None=إضافة، رقم=تعديل
        self._build_ui()
        self.refresh_tool_table()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ===== نموذج الإدخال =====
        form = QFormLayout()
        self.name_input = QLineEdit()
        self.dia_input = QDoubleSpinBox(); self.dia_input.setSuffix(" mm"); self.dia_input.setRange(0, 1000)
        self.length_input = QDoubleSpinBox(); self.length_input.setSuffix(" mm"); self.length_input.setRange(0, 1000)
        self.type_combo = QComboBox(); self.type_combo.addItems(self._tool_types.keys())
        self.rpm_input = QSpinBox(); self.rpm_input.setRange(0, 100000); self.rpm_input.setValue(1500)
        self.feed_input = QSpinBox(); self.feed_input.setRange(0, 100000); self.feed_input.setValue(300)

        form.addRow("Tool Name:", self.name_input)
        form.addRow("Diameter:", self.dia_input)
        form.addRow("Length:", self.length_input)
        form.addRow("Type:", self.type_combo)
        form.addRow("Default RPM:", self.rpm_input)
        form.addRow("Feedrate:", self.feed_input)

        # معاينة الصورة
        self.image_label = QLabel("No image")
        self.image_label.setFixedSize(120, 120)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid gray; background-color: #fafafa;")
        form.addRow("Preview:", self.image_label)

        self.type_combo.currentTextChanged.connect(self.update_tool_image)
        self.update_tool_image(self.type_combo.currentText())

        main_layout.addLayout(form)

        # ===== جدول الأدوات =====
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Type", "Dia (mm)", "RPM", "Image", ""])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setFixedHeight(300)
        self.table.cellClicked.connect(self.on_table_click)  # تحميل القيم عند اختيار صف
        main_layout.addWidget(self.table)

        self.setLayout(main_layout)

    # صورة النوع
    def update_tool_image(self, tool_type_name):
        img_path = self._tool_types.get(tool_type_name)
        if img_path and Path(img_path).exists():
            pix = QPixmap(str(img_path)).scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(pix)
        else:
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("No image")

    # حفظ عبر Apply العام: إضافة أو تعديل بحسب _current_edit_id
    def apply_tool(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Data", "Please enter the tool name.")
            return False

        tool_type = self.type_combo.currentText()
        dia = self.dia_input.value()
        length = self.length_input.value()
        rpm = self.rpm_input.value()
        feed = self.feed_input.value()
        img_path = self._tool_types.get(tool_type, "")

        try:
            if self._current_edit_id:  # تعديل
                self._db.update_tool(
                    self._current_edit_id,
                    name=name, type=tool_type, diameter=dia,
                    length=length, rpm=rpm, feedrate=feed, image_path=img_path
                )
                print(f"[TOOLS] ✏️ Updated: id={self._current_edit_id}, {name}")
            else:  # إضافة
                new_id = self._db.add_tool(name, tool_type, dia, length, rpm, feed, img_path)
                print(f"[TOOLS] ✅ Added: id={new_id}, {name}")

            self.refresh_tool_table()
            self.clear_form()  # رجّع النموذج للوضع الافتراضي
            return True
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save tool:\n{e}")
            return False

    def clear_form(self):
        self._current_edit_id = None
        self.name_input.clear()
        self.dia_input.setValue(0.0)
        self.length_input.setValue(0.0)
        self.rpm_input.setValue(1500)
        self.feed_input.setValue(300)
        # اترك النوع كما هو، والصورة تتبع النوع الحالي
        self.update_tool_image(self.type_combo.currentText())

    def refresh_tool_table(self):
        tools = self._db.list_tools()
        self.table.setRowCount(len(tools))
        for i, tool in enumerate(tools):
            self.table.setItem(i, 0, QTableWidgetItem(str(tool["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(tool["name"]))
            self.table.setItem(i, 2, QTableWidgetItem(tool["type"]))
            self.table.setItem(i, 3, QTableWidgetItem(str(tool["diameter"])))
            self.table.setItem(i, 4, QTableWidgetItem(str(tool["rpm"])))

            # صورة مصغرة
            img_cell = QLabel()
            img_path = tool.get("image_path", "")
            if img_path and Path(img_path).exists():
                pix = QPixmap(img_path).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_cell.setPixmap(pix)
            else:
                img_cell.setText("—")
            img_cell.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(i, 5, img_cell)

            # أيقونة الحذف (نص أحمر)
            del_btn = QPushButton("🗑")
            del_btn.setStyleSheet("""
                QPushButton {
                    color: #d32f2f;
                    background: none;
                    border: none;
                    font-size: 16px;
                }
                QPushButton:hover {
                    color: #b71c1c;
                }
            """)
            del_btn.setToolTip(f"Delete {tool['name']}")
            del_btn.clicked.connect(lambda _, tid=tool["id"], name=tool["name"]: self.delete_tool(tid, name))
            self.table.setCellWidget(i, 6, del_btn)

    # اختيار صف ⇒ تحميله للأعلى للتعديل
    def on_table_click(self, row, col):
        try:
            tool_id_item = self.table.item(row, 0)
            if not tool_id_item:
                return
            tool_id = int(tool_id_item.text())
            tool = self._db.get_tool(tool_id)
            if not tool:
                return

            self._current_edit_id = tool["id"]
            self.name_input.setText(tool["name"])
            self.type_combo.setCurrentText(tool["type"] or list(self._tool_types.keys())[0])
            self.dia_input.setValue(float(tool.get("diameter", 0) or 0.0))
            self.length_input.setValue(float(tool.get("length", 0) or 0.0))
            self.rpm_input.setValue(int(tool.get("rpm", 0) or 0))
            self.feed_input.setValue(int(tool.get("feedrate", 0) or 0))
            self.update_tool_image(self.type_combo.currentText())
            print(f"[TOOLS] 📝 Editing tool id={tool_id}")
        except Exception as e:
            print(f"[TOOLS] on_table_click error: {e}")

    # حذف
    def delete_tool(self, tool_id, tool_name):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete '{tool_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            try:
                self._db.delete_tool(tool_id)
                self.refresh_tool_table()
                if self._current_edit_id == tool_id:
                    self.clear_form()
                print(f"[TOOLS] 🗑 Deleted: {tool_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete tool:\n{e}")
