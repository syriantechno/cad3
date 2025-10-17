# tools/dimension_manager.py
from typing import List, Dict

class DimensionManager:
    """
    يدير عناصر القياس (AIS) على مجموعات:
      - general: قياسات عامة (Bounding Box)
      - holes: قياسات الحفر بعد التطبيق
      - preview: قياسات المعاينة المؤقتة
    """
    def __init__(self, display):
        self.display = display
        self.groups: Dict[str, List[object]] = {
            "general": [],
            "holes": [],
            "preview": [],
        }

    def add(self, ais_obj, group: str):
        if ais_obj is None:
            return
        self.groups.setdefault(group, []).append(ais_obj)

    def clear_group(self, group: str, update=False):
        ctx = self.display.Context
        for obj in self.groups.get(group, []):
            try:
                ctx.Erase(obj, False)
            except Exception:
                pass
        self.groups[group] = []
        if update:
            ctx.UpdateCurrentViewer()

    def clear_all(self):
        for g in list(self.groups.keys()):
            self.clear_group(g)
