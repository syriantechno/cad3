import sys
from PyQt6.QtWidgets import QApplication
from frontend.floating_window import AddToolTypeDialog  # غيّر المسار حسب موقع الكلاس
if __name__ == "__main__":
    app = QApplication(sys.argv)        # ✅ هذا أول شيء لازم يتنفذ
    dialog = AddToolTypeDialog({})      # ✅ بعد إنشاء QApplication
    dialog.exec()
