# -*- coding: utf-8 -*-
"""
tools.preview_utils
توليد صورة معاينة DXF (2D Flat) بدون OCC
يعتمد على ezdxf + PyQt5
"""

import ezdxf
from PyQt5.QtGui import QImage, QPainter, QPen, QColor
from PyQt5.QtCore import Qt


def generate_dxf_preview_png(dxf_path: str, png_path: str, width: int = 480, height: int = 320) -> bool:
    """رسم إسقاط ثنائي الأبعاد من DXF على صورة PNG"""
    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()

        # حدود الشكل
        min_x, min_y, max_x, max_y = 1e9, 1e9, -1e9, -1e9
        for e in msp:
            if e.dxftype() == "LINE":
                x1, y1 = e.dxf.start.x, e.dxf.start.y
                x2, y2 = e.dxf.end.x, e.dxf.end.y
                min_x, min_y = min(min_x, x1, x2), min(min_y, y1, y2)
                max_x, max_y = max(max_x, x1, x2), max(max_y, y1, y2)
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                for p in e.get_points():
                    x, y = p[0], p[1]
                    min_x, min_y = min(min_x, x), min(min_y, y)
                    max_x, max_y = max(max_x, x), max(max_y, y)

        if min_x > max_x or min_y > max_y:
            min_x, min_y, max_x, max_y = -10, -10, 10, 10

        sx = width / (max_x - min_x + 1e-9)
        sy = height / (max_y - min_y + 1e-9)
        scale = min(sx, sy) * 0.9
        ox = (width - (max_x - min_x) * scale) / 2
        oy = (height + (max_y - min_y) * scale) / 2

        img = QImage(width, height, QImage.Format_ARGB32)
        img.fill(QColor(250, 250, 250))

        painter = QPainter(img)
        pen = QPen(QColor(40, 40, 40), 1)
        painter.setPen(pen)

        for e in msp:
            if e.dxftype() == "LINE":
                x1, y1, x2, y2 = e.dxf.start.x, e.dxf.start.y, e.dxf.end.x, e.dxf.end.y
                painter.drawLine(
                    int(ox + (x1 - min_x) * scale),
                    int(oy - (y1 - min_y) * scale),
                    int(ox + (x2 - min_x) * scale),
                    int(oy - (y2 - min_y) * scale)
                )
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = [(p[0], p[1]) for p in e.get_points()]
                for i in range(len(pts) - 1):
                    x1, y1 = pts[i]
                    x2, y2 = pts[i + 1]
                    painter.drawLine(
                        int(ox + (x1 - min_x) * scale),
                        int(oy - (y1 - min_y) * scale),
                        int(ox + (x2 - min_x) * scale),
                        int(oy - (y2 - min_y) * scale)
                    )

        painter.end()
        img.save(png_path)
        print(f"🖼 تم توليد معاينة DXF (2D): {png_path}")
        return True

    except Exception as e:
        print(f"🔥 خطأ أثناء توليد المعاينة 2D: {e}")
        return False
