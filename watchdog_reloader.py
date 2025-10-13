import os
import sys
import time
import threading
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 📝 الملفات والمجلدات المراقبة
WATCH_PATHS = [
    os.path.join(os.path.dirname(__file__), "frontend"),
    os.path.join(os.path.dirname(__file__), "gui_fusion.py"),
]

# ⏱ مؤقت لتجنب إعادة التشغيل المتكررة بسرعة
reload_timer = None
DEBOUNCE_DELAY = 0.8  # بالثواني


def restart_app():
    """إعادة تشغيل البرنامج الرئيسي تلقائياً"""
    main_path = os.path.join(os.path.dirname(__file__), "main.py")
    print(f"[🔁 RELOAD] Restarting application: {main_path}")
    subprocess.Popen([sys.executable, main_path])
    os._exit(0)




class ReloadHandler(FileSystemEventHandler):
    """مراقبة التعديلات على الملفات"""
    def on_modified(self, event):
        global reload_timer
        # نراقب فقط ملفات .py
        if event.is_directory or not event.src_path.endswith(".py"):
            return

        # تحقق أن الملف ضمن المسارات المراقبة
        if not any(event.src_path.startswith(path) for path in WATCH_PATHS):
            return

        print(f"[👀 CHANGE DETECTED] {event.src_path}")

        # إعادة ضبط المؤقت في كل مرة
        if reload_timer:
            reload_timer.cancel()
        timer = threading.Timer(DEBOUNCE_DELAY, restart_app)
        timer.start()

        # تحديث المؤقت العالمي
        globals()['reload_timer'] = timer


if __name__ == "__main__":
    observer = Observer()

    for path in WATCH_PATHS:
        if os.path.isfile(path):
            folder = os.path.dirname(path)
        else:
            folder = path
        if os.path.exists(folder):
            print(f"[✅ WATCHING] {folder}")
            observer.schedule(ReloadHandler(), folder, recursive=True)

    observer.start()
    print("[🚀 HOT RELOAD ACTIVE] Watching for file changes...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
