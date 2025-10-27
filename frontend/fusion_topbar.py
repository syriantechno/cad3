# -*- coding: utf-8 -*-
from PyQt5 import QtCore
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
        from PyQt5.QtCore import Qt
        # 🔹 الخلفية العامة للشريط (غامقة)
        self.setStyleSheet(f"background-color: {dark_gray};")
        self.setAttribute(Qt.WA_StyledBackground, True)
        from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
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

        # =====================
        # القسم الأيسر (أيقونات)
        # =====================
        left_section = QWidget()
        left_section.setFixedWidth(300)
        left_section.setStyleSheet(f"background-color: {dark_gray}; border-right: 1px solid #B0B0B0;")

        from PyQt5.QtWidgets import QToolButton
        from PyQt5.QtGui import QIcon

        from PyQt5.QtWidgets import QToolButton
        from PyQt5.QtGui import QIcon, QColor
        from PyQt5 import QtCore

        # =====================
        # القسم الأيسر (أيقونات Fusion)
        # =====================
        left_section = QWidget()
        left_section.setFixedWidth(260)
        left_section.setStyleSheet(f"background-color: {dark_gray}; border-right: 1px solid #B0B0B0;")



        from PyQt5.QtSvg import QSvgWidget
        from PyQt5.QtWidgets import QWidget, QHBoxLayout
        from PyQt5.QtCore import Qt

        # =====================
        # القسم الأيسر (أيقونات SVG احترافية)
        # =====================
        left_section = QWidget()
        left_section.setFixedWidth(280)
        left_section.setStyleSheet(f"background-color: {dark_gray}; border: none;")  # 🔹 أزلنا الخط الجانبي

        icons = [
            ("frontend/icons/open.svg", "Open File"),
            ("frontend/icons/new.svg", "New Project"),
            ("frontend/icons/save.svg", "Save Project"),
            ("frontend/icons/undo.svg", "Undo Action"),
            ("frontend/icons/redo.svg", "Redo Action"),
        ]

        left_layout = QHBoxLayout(left_section)
        left_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        left_layout.setContentsMargins(10, 0, 0, 0)
        left_layout.setSpacing(25)

        from PyQt5.QtSvg import QSvgRenderer
        from PyQt5.QtGui import QPixmap, QPainter, QColor
        from PyQt5.QtWidgets import QLabel, QGraphicsOpacityEffect
        from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, Qt

        class HoverSvg(QLabel):
            """أيقونة SVG احترافية بلون قابل للتغيير وتأثير Fade عند المرور"""

            def __init__(self, path, tooltip):
                super().__init__()
                self.path = path
                self.setFixedSize(28, 28)
                self.setToolTip(tooltip)

                self.default_color = QColor("#566273")  # رمادي أساسي
                self.hover_color = QColor("#E67E22")  # برتقالي ناعم
                self.renderer = QSvgRenderer(path)

                # تأثير شفافية (fade)
                self.opacity_effect = QGraphicsOpacityEffect(self)
                self.setGraphicsEffect(self.opacity_effect)
                self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
                self.fade_anim.setDuration(180)
                self.fade_anim.setEasingCurve(QEasingCurve.InOutQuad)

                # عرض أولي
                self._update_icon(self.default_color)
                self.opacity_effect.setOpacity(1.0)

            def _update_icon(self, color):
                """يرسم الأيقونة على Pixmap باللون المطلوب"""
                pixmap = QPixmap(self.width(), self.height())
                pixmap.fill(Qt.transparent)
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                self.renderer.render(painter)
                painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
                painter.fillRect(pixmap.rect(), color)
                painter.end()
                self.setPixmap(pixmap)

            def enterEvent(self, event):
                """تغيير اللون إلى البرتقالي بتدرج ناعم"""
                self._update_icon(self.hover_color)
                self.fade_anim.stop()
                self.fade_anim.setStartValue(0.0)
                self.fade_anim.setEndValue(1.0)
                self.fade_anim.start()
                super().enterEvent(event)

            def leaveEvent(self, event):
                """العودة إلى الرمادي بتدرج ناعم"""
                self._update_icon(self.default_color)
                self.fade_anim.stop()
                self.fade_anim.setStartValue(0.0)
                self.fade_anim.setEndValue(1.0)
                self.fade_anim.start()
                super().leaveEvent(event)

        # إنشاء الأيقونات وإضافتها
        for path, tooltip in icons:
            svg_icon = HoverSvg(path, tooltip)
            left_layout.addWidget(svg_icon)

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
        # =====================
        # القسم الأيمن (أيقونة الإعدادات)
        # =====================
        right_section = QWidget()
        right_section.setFixedWidth(300)
        right_section.setStyleSheet(f"background-color: {dark_gray}; border: none;")

        right_layout = QHBoxLayout(right_section)
        right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        right_layout.setContentsMargins(0, 0, 10, 0)

        settings_icon = HoverSvg("frontend/icons/setting.svg", "Settings")
        right_layout.addWidget(settings_icon)
        # ---------------------------------------------
        # 🔄 زر تحديث الستايل (Refresh Style Button)
        # ---------------------------------------------
        from PyQt5.QtWidgets import QApplication
        import importlib
        from frontend import style

        from PyQt5.QtWidgets import QApplication, QWidget
        import importlib
        from frontend import style

        # def reload_style_safe():
        #     """تحديث شامل للستايل بدون كراش"""
        #     try:
        #         importlib.reload(style)
        #         app = QApplication.instance()
        #         if app:
        #             app.setStyleSheet(style.TOPBAR_STYLE)
        #         print("♻️ [Style] تم تحديث الستايل العام.")
        #
        #         # 🔁 تحديث جميع النوافذ النشطة
        #         for widget in app.allWidgets():
        #             if isinstance(widget, QWidget):
        #                 widget.setStyleSheet(style.TOPBAR_STYLE)
        #         print("✅ [Style] تم تطبيق التغييرات على جميع العناصر.")
        #
        #     except Exception as e:
        #         print(f"⚠️ [Style] خطأ أثناء التحديث: {e}")

        # إنشاء الزر وإضافته بجانب settings
        refresh_btn = QPushButton("⟳")
        refresh_btn.setFixedSize(28, 28)
        refresh_btn.setToolTip("Reload style.py")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #566273;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #E67E22;
            }
        """)
        # refresh_btn.clicked.connect(reload_style_safe)

        # عند الضغط يتم التحديث الفوري


        # أضف الزر إلى القسم الأيمن بجانب أيقونة الإعدادات
        right_layout.addWidget(refresh_btn)

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

