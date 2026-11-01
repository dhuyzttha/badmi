"""
Badminton Player Tracker & Distance Estimation
Author: Senior Computer Vision Engineer
Features:
- Dual-Player Tracking (Top vs Bottom court halves)
- Fixed Player ID and Label Assignment (e.g. Momota & Axelsen)
- Foot-point localization & Homography projection to 2D BWF Court (meters)
- Real-time and per-rally cumulative distance measurement (Euclidean metric displacement)
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from court_detector import CourtDetector

class PlayerTracker:
    def __init__(self, court_detector: CourtDetector, 
                 player_top_name: str = "Momota", 
                 player_bottom_name: str = "Axelsen"):
        self.court = court_detector
        self.player_top_name = player_top_name
        self.player_bottom_name = player_bottom_name
        
        # MOG2 Background Subtractor with shadow rejection
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=60, varThreshold=25, detectShadows=False)
        
        # State tracking
        self.players = {
            1: {
                "id": 1, 
                "name": player_top_name, 
                "side": "top", 
                "bbox": None, 
                "foot_px": None, 
                "foot_bwf": None, 
                "last_bwf": None, 
                "total_dist": 0.0, 
                "rally_dist": 0.0,
                "history_bwf": []
            },
            2: {
                "id": 2, 
                "name": player_bottom_name, 
                "side": "bottom", 
                "bbox": None, 
                "foot_px": None, 
                "foot_bwf": None, 
                "last_bwf": None, 
                "total_dist": 0.0, 
                "rally_dist": 0.0,
                "history_bwf": []
            }
        }
        self.frame_idx = 0

    def reset_rally_distances(self):
        """Reset distance traveled for a new rally."""
        for p in self.players.values():
            p["rally_dist"] = 0.0
            p["history_bwf"].clear()

    def update(self, frame: np.ndarray) -> Dict[int, Dict]:
        """
        Processes frame, segments foreground blobs, classifies players, 
        and updates world positions & distances.
        """
        self.frame_idx += 1
        h, w = frame.shape[:2]
        fgmask = self.bg_subtractor.apply(frame)

        # Morphological filtering to eliminate small noise and close player shapes
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_clean = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)
        fg_clean = cv2.morphologyEx(fg_clean, cv2.MORPH_DILATE, kernel, iterations=2)

        contours, _ = cv2.findContours(fg_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Court midline (net line in pixel space)
        net_px_y = 0.52 * h
        if self.court.detected_corners is not None:
            # Net is approximately halfway between far baseline and near baseline
            corners = self.court.detected_corners
            net_px_y = (corners[0][1] + corners[1][1] + corners[2][1] + corners[3][1]) / 4.0

        top_candidates = []
        bottom_candidates = []

        for c in contours:
            area = cv2.contourArea(c)
            if area < 350:  # Noise threshold
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            # Filter court vertical band
            if y < 0.25 * h or y > 0.88 * h:
                continue

            center_y = y + bh / 2.0
            foot_x = x + bw / 2.0
            foot_y = float(y + bh)  # Foot touches ground at bottom of bounding box

            if center_y < net_px_y:
                top_candidates.append({"bbox": (x, y, bw, bh), "foot_px": (foot_x, foot_y), "area": area})
            else:
                bottom_candidates.append({"bbox": (x, y, bw, bh), "foot_px": (foot_x, foot_y), "area": area})

        # Select most prominent candidate on each half
        best_top = max(top_candidates, key=lambda c: c["area"]) if top_candidates else None
        best_bottom = max(bottom_candidates, key=lambda c: c["area"]) if bottom_candidates else None

        # Update Player 1 (Top Court / Far Side)
        self._update_player_data(1, best_top)
        # Update Player 2 (Bottom Court / Near Side)
        self._update_player_data(2, best_bottom)

        return self.players

    def _update_player_data(self, player_id: int, candidate: Optional[Dict]):
        p = self.players[player_id]
        if candidate is not None:
            p["bbox"] = candidate["bbox"]
            p["foot_px"] = candidate["foot_px"]
            
            # Project foot to BWF metric space (meters)
            world_x, world_y = self.court.pixel_to_world(candidate["foot_px"][0], candidate["foot_px"][1])
            
            # Constrain to plausible court boundaries
            world_x = max(-1.0, min(self.court.width + 1.0, world_x))
            world_y = max(-1.0, min(self.court.length + 1.0, world_y))
            p["foot_bwf"] = (world_x, world_y)

            # Calculate metric distance displacement
            if p["last_bwf"] is not None:
                dx = world_x - p["last_bwf"][0]
                dy = world_y - p["last_bwf"][1]
                step_dist = np.sqrt(dx * dx + dy * dy)
                
                # Filter out outlier jumps (> 1.5 meters per frame at 30fps is unrealistic)
                if 0.01 < step_dist < 1.5:
                    p["total_dist"] += step_dist
                    p["rally_dist"] += step_dist

            p["last_bwf"] = (world_x, world_y)
            p["history_bwf"].append((world_x, world_y))
            if len(p["history_bwf"]) > 40:
                p["history_bwf"].pop(0)
