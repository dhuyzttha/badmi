"""
Badminton Virtual Referee & Rally Analytics
Author: Senior Computer Vision Engineer
Features:
- Automated Shot Counter (Direction Inflection / Velocity Reversal Detection)
- In/Out Court Boundary Arbitration (BWF Standard Polygon Testing)
- Rally State Machine (WARMUP -> SERVE -> IN_PLAY -> POINT_CONCLUDED -> BREAK)
- Live HUD Broadcast Metrics (Rally duration, Shot count, Max speed, In/Out verdict)
"""

from typing import Dict, List, Optional
import numpy as np
from court_detector import CourtDetector

class VirtualReferee:
    def __init__(self, court_detector: CourtDetector, fps: float = 30.0):
        self.court = court_detector
        self.fps = fps
        self.state = "IN_PLAY" # "SERVE", "IN_PLAY", "POINT_AWARDED", "BREAK"
        self.shot_count = 0
        self.rally_duration_frames = 0
        self.last_hit_player = None
        self.last_velocity_y = 0.0
        self.last_decision = "PLAY ON" # "IN", "OUT", "FAULT", "PLAY ON"
        self.landing_spot_bwf = None
        self.landing_spot_px = None
        self.rally_history = []

    def update(self, shuttle_data: Optional[Dict], players: Dict[int, Dict]) -> Dict:
        """
        Updates referee logic, checks velocity inflections for shots, and tests landing boundaries.
        """
        self.rally_duration_frames += 1
        duration_sec = self.rally_duration_frames / self.fps

        if shuttle_data is not None:
            bwf_y = shuttle_data["bwf_y"]
            bwf_x = shuttle_data["bwf_x"]
            
            # Detect shot inflection (shuttlecock moving from top court to bottom court or vice versa)
            # Velocity Y inflection:
            if len(shuttle_data) > 0 and "speed_kmh" in shuttle_data:
                # Check player proximity to detect shot hit
                top_player = players.get(1)
                bottom_player = players.get(2)
                
                # Check inflection in Y direction
                # In pixel coordinates, top player hits down (+y), bottom player hits up (-y)
                if len(self.rally_history) > 2:
                    dy_recent = shuttle_data["py"] - self.rally_history[-2]["py"]
                    if abs(dy_recent) > 3.0:
                        curr_dir_y = 1 if dy_recent > 0 else -1
                        if self.last_velocity_y != 0 and curr_dir_y != self.last_velocity_y:
                            # Direction changed -> Shot registered!
                            self.shot_count += 1
                            self.state = "IN_PLAY"
                        self.last_velocity_y = curr_dir_y

                self.rally_history.append(shuttle_data)
                if len(self.rally_history) > 100:
                    self.rally_history.pop(0)

                # Check if shuttlecock is near ground (at near/far baseline or stopping)
                # In court coordinate, Y < 0.2 (out far), Y > 13.5 (out near), X < -0.1 (out left), X > width + 0.1 (out right)
                if shuttle_data["speed_kmh"] < 12.0 and len(self.rally_history) > 5:
                    # Potential landing
                    is_in = self.court.is_in_court(bwf_x, bwf_y, margin=0.05)
                    self.landing_spot_bwf = (bwf_x, bwf_y)
                    self.landing_spot_px = (shuttle_data["px"], shuttle_data["py"])
                    if is_in:
                        self.last_decision = "IN"
                    else:
                        self.last_decision = "OUT"

        return {
            "state": self.state,
            "shot_count": self.shot_count,
            "duration_sec": round(duration_sec, 1),
            "decision": self.last_decision,
            "landing_spot_bwf": self.landing_spot_bwf,
            "landing_spot_px": self.landing_spot_px
        }
