# -*- coding: utf-8 -*-
# test_graphics_kit.py
# جرّب الباكيج بشكل مستقل (بدون ما تلمس مشروعك)
from OCC.Display.SimpleGui import init_display
from graphics_kit import GraphicsKit, Style, make_rectangle, make_circle

display, start_display, add_menu, add_function_to_menu = init_display()
gk = GraphicsKit(display)

def demo():
    print("== Demo: Grid + Axes + Shapes ==")
    gk.toggle_grid(True)
    gk.show_axes(True)

    # رسمات
    gk.add_line((0, 0, 0), (100, 0, 0))
    gk.add_rectangle((10, 10, 0), 80, 40, layer="Construction", style=Style((0.2, 0.2, 0.9), 0.3))
    gk.add_circle((0, 0, 0), 30, style=Style((0.0, 0.6, 0.0), 0.0))
    gk.add_arc_3pts((0, 0, 0), (30, 40, 0), (60, 0, 0), style=Style((0.6, 0.0, 0.0), 0.0))
    gk.add_polyline([(0,0,0),(0,50,0),(50,50,0)], close=True, style=Style((0.7,0.3,0.0), 0.2))

    # معاينة Ghost (مثال)
    ghost_rect = make_rectangle((120, 0, 0), 60, 30)
    gk.preview_shape(ghost_rect)

    gk.fit_all()

demo()
start_display()
