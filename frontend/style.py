TOPBAR_STYLE = """
QTabWidget::pane {
    border: 0;
    background: #EAEAEA;
}

QTabBar::tab {
    background: #EAEAEA;
    color: #000000;
    padding: 0px 5px;
    margin: 0px;
    border-radius: 0px;
    font-size: 13px;
    min-width: 60px;
    min-height: 32px;
}

QTabBar::tab:selected {
    border-bottom: 2px solid #3A84FF;
    background-color: transparent;
    color: #000000;
}

QTabBar::tab:hover {
    background-color: transparent;
}

QToolButton {
    background-color: transparent;
    color: #000000;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 0px;
    margin: 0px;
    font-size: 12px;
    min-height: 48px;
    min-width: 64px;
    qproperty-iconSize: 36px;
}

QToolButton:hover, QToolButton:pressed {
    background-color: transparent;
}

QToolButton:checked {
    border-bottom: 2px solid #3A84FF;
}

QWidget {
    background-color: #EAEAEA;
}
"""
DOCK_STYLE = """
QDockWidget {
    background-color: #EAEAEA;
    titlebar-close-icon: url(frontend/icons/close.png);
    titlebar-normal-icon: url(frontend/icons/float.png);
    font-size: 14px;
    font-weight: bold;
}

QWidget {
    background-color: #EAEAEA;
}

QLabel {
    font-size: 12px;
}

QComboBox, QDoubleSpinBox, QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #C0C0C0;
    border-radius: 4px;
    padding: 4px;
    font-size: 12px;
}

QPushButton {
    background-color: #3A84FF;
    color: #FFFFFF;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #346BCC;
}
"""
EXTRUDE_WINDOW_STYLE = """
QWidget#container {
    background-color: #F3F3F3;
    border-radius: 10px;
}

QComboBox, QDoubleSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #C0C0C0;
    border-radius: 5px;
    padding: 6px;
    font-size: 14px;
    min-height: 22px;
    min-width: 140px;
}

QComboBox::drop-down {
    width: 25px;
}

QPushButton#applyBtn {
    background-color: #0078D4;
    color: white;
    font-size: 14px;
    font-weight: bold;
    padding: 6px;
    border-radius: 5px;
    min-height: 22px;
}
QPushButton#applyBtn:hover {
    background-color: #005a9e;
}

QPushButton#cancelBtn {
    background-color: #E0E0E0;
    color: #333;
    font-size: 13px;
    border-radius: 5px;
    padding: 5px;
    min-height: 25px;
}
QPushButton#cancelBtn:hover {
    background-color: #C8C8C8;
}
"""

TOOL_FLOATING_WINDOW_STYLE = """
    QDialog#ToolFloatingWindow {
        background-color: #EAEAEA;
        border: 1px solid #b4b4b4;
        border-radius: 8px;
    }
    QLabel { font-size: 13px; color: #333; }
    QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit {
        min-height: 28px; font-size: 13px; border: 1px solid #ccc;
        border-radius: 4px; background: white;
    }
    QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QLineEdit:focus {
        border: 1px solid #0078d4;
    }
    QPushButton {
        min-height: 30px; min-width: 100px; font-size: 13px; border-radius: 4px;
    }
    QPushButton#ApplyBtn {
        background-color: #0078d4; color: white;
    }
    
    QPushButton#PreviewBtn {
        background-color: #d9024d; color: white;
    }
    QPushButton#ApplyBtn:hover { background-color: #005ea2; }
    QPushButton#CancelBtn {
        background-color: #e0e0e0; color: black;
    }
    QPushButton#CancelBtn:hover { background-color: #cacaca; }
    QFrame#line { background:#dcdcdc; height:1px; }
"""

HOLE_WINDOW_STYLE = """
QWidget#HoleWindow {
    background-color: #F3F3F3;
    border-radius: 8px;
}

QComboBox, QDoubleSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #C0C0C0;
    border-radius: 5px;
    padding: 6px;
    font-size: 13px;
    min-height: 24px;
    min-width: 120px;
}

QLabel {
    color: #333;
    font-size: 13px;
}

QPushButton#btnPreview {
    background-color: #2196F3;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    padding: 8px 14px;
}
QPushButton#btnPreview:hover {
    background-color: #1976D2;
}

QPushButton#btnApply {
    background-color: #4CAF50;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    padding: 8px 14px;
}
QPushButton#btnApply:hover {
    background-color: #388E3C;
}

QPushButton#btnRefresh {
    background-color: #e0e0e0;
    border: 1px solid #bbb;
    border-radius: 5px;
    padding: 4px 12px;
}
QPushButton#btnRefresh:hover {
    background-color: #d5d5d5;
}
"""
# أمثلة: تأكد أن btnApply/btnPreview مضافين أصلاً
# 🌳 تخصيص شجرة العمليات Operation Browser Style
OP_BROWSER_STYLE = """
QTreeWidget {
    background-color: rgba(240, 240, 240, 200);
    border: none;
    font-size: 12px;
    alternate-background-color: rgba(255,255,255,0.5);
}

QTreeWidget::item {
    height: 22px;
    padding-left: 4px;
    padding-right: 4px;
}

QTreeWidget::item:selected {
    background-color: rgba(100, 170, 255, 80);
    color: black;
}

/* ✅ ضمان بقاء الأيقونات مرئية */
QTreeWidget::item:selected:active {
    icon: inherit;
}
QTreeWidget::item:selected:!active {
    icon: inherit;
}
"""


