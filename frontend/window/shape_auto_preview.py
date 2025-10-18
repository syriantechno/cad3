# ==========================================
# shape_auto_preview.py
# ==========================================
# Auto-Preview System for Shape Manager
# - يربط كل مدخلات الصفحة مع المعاينة التلقائية
# - يستدعي preview_extrude(page, display) تلقائيًا
# - يحتوي على حماية من الكراش + Debounce للتقليل من التحديثات السريعة
# ==========================================

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QLineEdit, QComboBox
import traceback

# الحالة العامة لتفعيل/إيقاف الميزة
AUTO_PREVIEW_ENABLED = True

# التأخير الزمني بين آخر تعديل وتشغيل المعاينة (ms)
DELAY_MS = 250


def safe_auto_preview(page, display):
    """
    استدعاء آمن لـ preview_extrude بدون كراش.
    """
    global AUTO_PREVIEW_ENABLED

    if not AUTO_PREVIEW_ENABLED:
        print("🟡 [AutoPreview] المعاينة التلقائية متوقفة.")
        return

    try:
        # تأكد أن الشكل جاهز
        if not hasattr(page, "shape_2d") or page.shape_2d is None or page.shape_2d.IsNull():
            print("⚠️ [AutoPreview] لا يوجد شكل جاهز للمعاينة بعد.")
            return

        # ✅ الاستيراد المباشر داخل الدالة
        from frontend.window.shape_manager_window import preview_extrude

        print("🔁 [AutoPreview] تحديث المعاينة التلقائية...")
        preview_extrude(page, display)
        print("✅ [AutoPreview] تم تحديث المعاينة بنجاح")

    except Exception as e:
        print(f"❌ [AutoPreview] خطأ أثناء تنفيذ المعاينة: {e}")
        traceback.print_exc()



def connect_auto_preview(page, display):
    """
    توصيل جميع مدخلات الصفحة بإشارة معاينة تلقائية.
    - يستمع لأي تغيير في النص أو القيم ويستدعي safe_auto_preview بعد تأخير بسيط.
    """

    print("🧩 [AutoPreview] تم تفعيل نظام المعاينة التلقائية.")

    timer = QTimer()
    timer.setSingleShot(True)

    def schedule_preview():
        if not AUTO_PREVIEW_ENABLED:
            return
        timer.start(DELAY_MS)

    def run_preview():
        safe_auto_preview(page, display)

    timer.timeout.connect(run_preview)

    # تحديد الودجتات القابلة للتوصيل تلقائيًا
    widgets = []
    for name in dir(page):
        obj = getattr(page, name)
        if isinstance(obj, (QLineEdit, QComboBox)):
            widgets.append(obj)

    # توصيل الإشارات لكل مدخل
    for w in widgets:
        if isinstance(w, QLineEdit):
            w.textChanged.connect(schedule_preview)
        elif isinstance(w, QComboBox):
            w.currentIndexChanged.connect(schedule_preview)

    # حفظ المؤقت داخل الصفحة لتجنب جمع القمامة
    page._auto_preview_timer = timer

    print(f"🔗 [AutoPreview] تم توصيل {len(widgets)} مدخل بالمعاينة التلقائية.")


def toggle_auto_preview(enable: bool):
    """
    تفعيل أو تعطيل النظام يدويًا من أي مكان.
    """
    global AUTO_PREVIEW_ENABLED
    AUTO_PREVIEW_ENABLED = enable
    state = "مفعل ✅" if enable else "متوقف ⛔"
    print(f"[AutoPreview] الحالة الآن: {state}")
