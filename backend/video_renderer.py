"""
Badminton Hawk-Eye Video Overlay & HUD Renderer
Author: Senior Computer Vision Engineer
Features:
- Broadcast-grade AR Overlay (Glow lines, court boundaries, player trackers)
- Dynamic Trajectory Ribbon with Speed Gradient (Green -> Amber -> Red)
- Real-time Birds-Eye-View 2D Mini-Court Map Radar in top-right / bottom-right corner
- Telemetry HUD Banner (Speedometer, Shot Count, Rally Clock, In/Out verdict)
"""

import cv2
import numpy as np
from typing import Dict, List, Optional
from court_detector import CourtDetector

class VideoRenderer:
    def __init__(self, court_detector: CourtDetector):
        self.court = court_detector

    def render_frame(self, frame: np.ndarray, 
                     court_data: Dict, 
                     players: Dict[int, Dict], 
                     shuttle_data: Optional[Dict], 
                     shuttle_trajectory: List[Dict], 
                     referee_data: Dict) -> np.ndarray:
        """
        Draws all HUD overlays, trajectory trails, player tracking, and mini court onto frame.
        """
        canvas = frame.copy()
        h, w = canvas.shape[:2]

        # 1. Draw Court Overlay Polygon
        if court_data.get("corners"):
            corners = np.array(court_data["corners"], dtype=np.int32)
            # Semi-transparent court wireframe
            overlay = canvas.copy()
            cv2.polylines(overlay, [corners], isClosed=True, color=(0, 255, 128), thickness=2, lineType=cv2.LINE_AA)
            cv2.addWeighted(overlay, 0.7, canvas, 0.3, 0, canvas)
            
            # Corner markers
            for i, pt in enumerate(corners):
                cv2.circle(canvas, tuple(pt), 5, (0, 255, 255), -1, lineType=cv2.LINE_AA)

        # 2. Draw Player Tracking Boxes & Foot Markers
        for pid, p in players.items():
            if p.get("bbox"):
                bx, by, bw, bh = p["bbox"]
                # Color: Player 1 (Momota - Red/White theme), Player 2 (Axelsen - Cyan/Blue theme)
                box_color = (0, 165, 255) if pid == 1 else (255, 200, 0)
                
                # Bounding box
                cv2.rectangle(canvas, (bx, by), (bx + bw, by + bh), box_color, 2, lineType=cv2.LINE_AA)
                
                # Name & Distance Badge
                label = f"{p['name']} | {p['rally_dist']:.1f}m"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                
                badge_y = max(by - 6, th + 6)
                cv2.rectangle(canvas, (bx, badge_y - th - 4), (bx + tw + 10, badge_y + 4), (20, 20, 20), -1)
                cv2.rectangle(canvas, (bx, badge_y - th - 4), (bx + tw + 10, badge_y + 4), box_color, 1)
                cv2.putText(canvas, label, (bx + 5, badge_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
                
                # Foot position anchor
                if p.get("foot_px"):
                    fx, fy = int(p["foot_px"][0]), int(p["foot_px"][1])
                    cv2.ellipse(canvas, (fx, fy), (12, 6), 0, 0, 360, box_color, 2, lineType=cv2.LINE_AA)

        # 3. Draw Shuttlecock Trajectory Trail Ribbon (Color Gradient based on Speed)
        if len(shuttle_trajectory) > 1:
            for i in range(1, len(shuttle_trajectory)):
                pt1 = (int(shuttle_trajectory[i-1]["px"]), int(shuttle_trajectory[i-1]["py"]))
                pt2 = (int(shuttle_trajectory[i]["px"]), int(shuttle_trajectory[i]["py"]))
                speed = shuttle_trajectory[i].get("speed_kmh", 0.0)
                
                # Color gradient: Green (<80) -> Yellow (80-160) -> Red (>160)
                if speed < 80.0:
                    trail_color = (0, 255, 0)
                elif speed < 160.0:
                    trail_color = (0, 220, 255)
                else:
                    trail_color = (0, 60, 255)
                    
                thickness = max(2, int(4 * (i / len(shuttle_trajectory))))
                cv2.line(canvas, pt1, pt2, trail_color, thickness, lineType=cv2.LINE_AA)

        # 4. Draw Current Shuttlecock Marker & Speedometer Callout
        if shuttle_data is not None:
            sx, sy = int(shuttle_data["px"]), int(shuttle_data["py"])
            cv2.circle(canvas, (sx, sy), 7, (0, 255, 255), -1, lineType=cv2.LINE_AA)
            cv2.circle(canvas, (sx, sy), 11, (0, 140, 255), 2, lineType=cv2.LINE_AA)
            
            # Speed Callout Pin
            speed_txt = f"{shuttle_data['speed_kmh']:.0f} km/h"
            (sw, sh), _ = cv2.getTextSize(speed_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
            callout_x = min(w - sw - 12, max(10, sx + 12))
            callout_y = max(sh + 10, sy - 10)
            
            cv2.rectangle(canvas, (callout_x - 3, callout_y - sh - 3), (callout_x + sw + 5, callout_y + 4), (15, 15, 15), -1)
            cv2.rectangle(canvas, (callout_x - 3, callout_y - sh - 3), (callout_x + sw + 5, callout_y + 4), (0, 255, 255), 1)
            cv2.putText(canvas, speed_txt, (callout_x, callout_y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)

        # 5. Draw Top Broadcast Telemetry HUD Banner
        self._draw_telemetry_hud(canvas, referee_data, shuttle_data, w)

        # 6. Draw 2D Birds-Eye-View Mini-Court Radar Map in Top-Right
        self._draw_mini_court_radar(canvas, players, shuttle_data, referee_data, w)

        return canvas

    def _draw_telemetry_hud(self, canvas: np.ndarray, referee_data: Dict, shuttle_data: Optional[Dict], w: int):
        hud_h = 75
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, 0), (w, hud_h), (18, 22, 28), -1)
        cv2.addWeighted(overlay, 0.85, canvas, 0.15, 0, canvas)
        cv2.line(canvas, (0, hud_h), (w, hud_h), (0, 255, 160), 2)

        # Header Titles
        cv2.putText(canvas, "HAWK-EYE PRO AI", (14, 24), cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 160), 1, cv2.LINE_AA)
        
        # Rally Status & Time
        dur = referee_data.get("duration_sec", 0.0)
        state = referee_data.get("state", "IN_PLAY")
        shots = referee_data.get("shot_count", 0)
        
        status_color = (0, 255, 0) if state == "IN_PLAY" else (0, 215, 255)
        cv2.putText(canvas, f"STATUS: {state}", (14, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.42, status_color, 1, cv2.LINE_AA)
        cv2.putText(canvas, f"SHOTS: {shots:02d} | TIME: {dur:.1f}s", (14, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1, cv2.LINE_AA)

        # Speed readout
        spd = shuttle_data["speed_kmh"] if shuttle_data else 0.0
        spd_text = f"{spd:.0f}"
        cv2.putText(canvas, spd_text, (int(w * 0.48), 50), cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(canvas, "KM/H", (int(w * 0.48), 65), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (160, 160, 160), 1, cv2.LINE_AA)

    def _draw_mini_court_radar(self, canvas: np.ndarray, players: Dict[int, Dict], 
                               shuttle_data: Optional[Dict], referee_data: Dict, w: int):
        """
        Draws a 2D BWF Mini-Court Map projection with players and shuttle position.
        """
        map_w = 120
        map_h = 240
        map_x = w - map_w - 12
        map_y = 85

        # Background card
        overlay = canvas.copy()
        cv2.rectangle(overlay, (map_x - 4, map_y - 4), (map_x + map_w + 4, map_y + map_h + 4), (15, 18, 22), -1)
        cv2.addWeighted(overlay, 0.85, canvas, 0.15, 0, canvas)
        cv2.rectangle(canvas, (map_x - 4, map_y - 4), (map_x + map_w + 4, map_y + map_h + 4), (60, 70, 80), 1)

        # Court green surface
        cv2.rectangle(canvas, (map_x, map_y), (map_x + map_w, map_y + map_h), (34, 110, 60), -1)
        cv2.rectangle(canvas, (map_x, map_y), (map_x + map_w, map_y + map_h), (255, 255, 255), 1)

        # Net line (middle: y = length / 2 = 6.7m)
        net_y = int(map_y + map_h / 2)
        cv2.line(canvas, (map_x, net_y), (map_x + map_w, net_y), (255, 255, 255), 2)

        # Short service lines (1.98m from net)
        scale_y = map_h / self.court.length
        scale_x = map_w / self.court.width
        
        ssl1_y = int(map_y + (6.70 - 1.98) * scale_y)
        ssl2_y = int(map_y + (6.70 + 1.98) * scale_y)
        cv2.line(canvas, (map_x, ssl1_y), (map_x + map_w, ssl1_y), (200, 200, 200), 1)
        cv2.line(canvas, (map_x, ssl2_y), (map_x + map_w, ssl2_y), (200, 200, 200), 1)

        # Center line
        mid_x = int(map_x + map_w / 2)
        cv2.line(canvas, (mid_x, map_y), (mid_x, ssl1_y), (200, 200, 200), 1)
        cv2.line(canvas, (mid_x, ssl2_y), (mid_x, map_y + map_h), (200, 200, 200), 1)

        # Plot Players on Mini Court
        for pid, p in players.items():
            if p.get("foot_bwf"):
                bx, by = p["foot_bwf"]
                mx = int(map_x + (bx / self.court.width) * map_w)
                my = int(map_y + (by / self.court.length) * map_h)
                mx = max(map_x, min(map_x + map_w, mx))
                my = max(map_y, min(map_y + map_h, my))
                
                color = (0, 165, 255) if pid == 1 else (255, 200, 0)
                cv2.circle(canvas, (mx, my), 5, color, -1, lineType=cv2.LINE_AA)
                cv2.circle(canvas, (mx, my), 7, (255, 255, 255), 1, lineType=cv2.LINE_AA)

        # Plot Shuttlecock on Mini Court
        if shuttle_data is not None and "bwf_x" in shuttle_data:
            sx = shuttle_data["bwf_x"]
            sy = shuttle_data["bwf_y"]
            smx = int(map_x + (sx / self.court.width) * map_w)
            smy = int(map_y + (sy / self.court.length) * map_h)
            smx = max(map_x, min(map_x + map_w, smx))
            smy = max(map_y, min(map_y + map_h, smy))
            cv2.circle(canvas, (smx, smy), 4, (0, 255, 255), -1, lineType=cv2.LINE_AA)

        # Mini court label
        cv2.putText(canvas, "2D MINI-COURT", (map_x + 6, map_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 160), 1, cv2.LINE_AA)
