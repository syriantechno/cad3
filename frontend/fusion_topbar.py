# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class FusionTopBar(QWidget):
    """شريط علوي ثلاثي الأجزاء بأسلوب Fusion."""
    def __init__(self, parent=None):
        super(FusionTopBar, self).__init__(parent)
        self.setFixedHeight(48)
        self._build_ui()

    def _build_ui(self):
        # ألوان Fusion
        dark_gray = "#C8C9C8"
        light_gray = "#F1F2F1"

        # 🔹 الخلفية العامة للشريط (غامقة)
        self.setStyleSheet(f"background-color: {dark_gray};")
        self.setAttribute(Qt.WA_StyledBackground, True)

        # ===== تخطيط عمودي أساسي =====
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 🔸 القسم العلوي (فارغ بسيط لإعطاء ارتفاع)
        top_spacer = QWidget()
        top_spacer.setFixedHeight(6)  # ← هذا اللي يرفع الجانبين الغامقين للأعلى
        outer_layout.addWidget(top_spacer)

        # ===== التخطيط الأفقي للأقسام الثلاثة =====
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # القسم الأيسر (رمادي غامق)
        left_section = QWidget()
        left_section.setFixedWidth(300)
        left_section.setStyleSheet(f"background-color: {dark_gray}; border-right: 1px solid #B0B0B0;")

        # القسم الأوسط (رمادي فاتح نازل فعلياً)
        center_section = QWidget()
        center_section.setStyleSheet(f"""
            background-color: {light_gray};
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            border: 1px solid #BFBFBF;
            border-bottom: none;
        """)

        # القسم الأيمن (رمادي غامق)
        right_section = QWidget()
        right_section.setFixedWidth(300)
        right_section.setStyleSheet(f"background-color: {dark_gray}; border-left: 1px solid #B0B0B0;")

        # محتوى داخلي بسيط
        center_layout = QHBoxLayout(center_section)
        center_layout.setAlignment(Qt.AlignCenter)
        label = QLabel("ALUM CAM — Fusion Mode")
        label.setFont(QFont("Roboto", 11))
        label.setStyleSheet("color: #333; font-weight: bold;")
        center_layout.addWidget(label)

        # تجميع الأقسام الثلاثة
        main_layout.addWidget(left_section)
        main_layout.addWidget(center_section)
        main_layout.addWidget(right_section)

        outer_layout.addLayout(main_layout)

