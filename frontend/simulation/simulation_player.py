# -*- coding: utf-8 -*-
"""
🎬 Simulation Player
--------------------
يشغّل محاكاة حركة رأس الحفر (Tool Head) بناءً على ملف G-Code.
يدعم أوامر G0 / G1 مع X,Y,Z.
التحريك يتم في عارض OCC (pythonocc) عبر AIS_Shape بسيط (كرة حمراء).
"""

from OCC.Core.gp import gp_Pnt
from OCC.Core.Geom import Geom_Point
from OCC.Core.AIS import AIS_Point
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from PyQt5.QtCore import QTimer
import re, time

class SimulationPlayer:
    def __init__(self, display):
        self.display = display
        self.points = []
        self.current_index = 0
        self.timer = None
        self.point_ais = None
        self.is_running = False

    # ==========================================================
    # 🧩 تحميل ملف G-Code
    # ==========================================================
    def load_gcode(self, path):
        """قراءة ملف .nc واستخراج نقاط الحركة."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            coords = []
            x = y = z = 0.0
            for line in lines:
                line = line.strip()
                if not line or line.startswith("("):
                    continue
                if line.startswith("G0") or line.startswith("G1"):
                    match_x = re.search(r"X(-?\d+\.?\d*)", line)
                    match_y = re.search(r"Y(-?\d+\.?\d*)", line)
                    match_z = re.search(r"Z(-?\d+\.?\d*)", line)
                    if match_x: x = float(match_x.group(1))
                    if match_y: y = float(match_y.group(1))
                    if match_z: z = float(match_z.group(1))
                    coords.append((x, y, z))
            self.points = coords
            print(f"[SIM] Loaded {len(lines)} G-Code lines.")
            print(f"[SIM] Parsed {len(coords)} points from G-Code.")
            return len(coords)
        except Exception as e:
            print(f"[❌ SIM] Load error: {e}")
            return 0

    # ==========================================================
    # ▶️ بدء المحاكاة
    # ==========================================================
    def start(self, speed_ms=120):
        """بدء التحريك التدريجي للنقاط."""
        if not self.points:
            print("[SIM] No points to simulate.")
            return
        if self.is_running:
            print("[SIM] Already running.")
            return

        self.current_index = 0
        self.is_running = True

        # أنشئ الكرة الأولى
        start_p = gp_Pnt(*self.points[0])
        geom_p = Geom_Point(start_p)
        self.point_ais = AIS_Point(geom_p)
        self.point_ais.SetColor(Quantity_Color(1.0, 0.0, 0.0, Quantity_TOC_RGB))
        self.display.Context.Display(self.point_ais, False)
        self.display.Context.UpdateCurrentViewer()
        print(f"[SIM] Starting animation with {len(self.points)} points...")

        self.timer = QTimer()
        self.timer.timeout.connect(self._step)
        self.timer.start(speed_ms)

    # ==========================================================
    # ⏹ إيقاف المحاكاة
    # ==========================================================
    def stop(self):
        if self.timer:
            self.timer.stop()
            self.timer = None
        self.is_running = False
        print("[SIM] Simulation stopped.")

    # ==========================================================
    # 🔁 خطوة واحدة
    # ==========================================================
    def _step(self):
        try:
            if self.current_index >= len(self.points):
                self.stop()
                print("[SIM] Simulation finished safely.")
                return

            x, y, z = self.points[self.current_index]
            p = gp_Pnt(x, y, z)
            geom = Geom_Point(p)
            if self.point_ais:
                self.display.Context.Erase(self.point_ais, False)
            self.point_ais = AIS_Point(geom)
            self.point_ais.SetColor(Quantity_Color(1.0, 0.0, 0.0, Quantity_TOC_RGB))
            self.display.Context.Display(self.point_ais, False)
            self.display.Context.UpdateCurrentViewer()
            self.current_index += 1
        except Exception as e:
            print(f"[SIM] step error: {e}")
