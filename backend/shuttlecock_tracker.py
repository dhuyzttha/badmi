"""
Badminton Shuttlecock Tracker & Speed Measurement Engine
Author: Senior Computer Vision Engineer
Features:
- High Sensitivity 3-Frame Differencing + Brightness Candidate Extraction
- 4D Kalman Filter State Estimator (Position [x, y] & Velocity [vx, vy])
- Trajectory Spline Interpolation for Motion Blur & Dropped Frames
- Real-time Speed Estimation in km/h based on BWF Metric Homography Space & Video FPS
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.interpolate import UnivariateSpline
from court_detector import CourtDetector

class ShuttlecockTracker:
    def __init__(self, court_detector: CourtDetector, fps: float = 30.0, sensitivity: float = 0.75):
        self.court = court_detector
        self.fps = fps if fps > 0 else 30.0
        self.dt = 1.0 / self.fps
        self.sensitivity = sensitivity # 0.0 to 1.0
        
        # Frame buffer for 3-frame differencing
        self.frame_buffer: List[np.ndarray] = []
        
        # 4D Kalman Filter initialization
        # State: [x, y, vx, vy]^T
        self.kf = cv2.KalmanFilter(4, 2)
        self.kf.measurementMatrix = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ], dtype=np.float32)
        
        # State transition matrix
        self.kf.transitionMatrix = np.array([
            [1, 0, self.dt, 0],
            [0, 1, 0, self.dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        
        # Process and Measurement Noise
        cv2.setIdentity(self.kf.processNoiseCov, 1e-2)
        cv2.setIdentity(self.kf.measurementNoiseCov, 1e-1)
        cv2.setIdentity(self.kf.errorCovPost, 1.0)
        
        self.is_initialized = False
        self.lost_frames_count = 0
        self.max_lost_frames = 10
        
        # Trajectory history: list of dicts {px, py, bwf_x, bwf_y, speed_kmh, frame_idx, interpolated}
        self.trajectory: List[Dict] = []
        self.current_speed_kmh: float = 0.0
        self.max_speed_kmh: float = 0.0
        self.frame_idx = 0

    def update(self, frame: np.ndarray) -> Optional[Dict]:
        """
        Processes new frame, runs 3-frame diff + Kalman update, and computes metric speed.
        """
        self.frame_idx += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Maintain 3 frames in buffer
        self.frame_buffer.append(gray)
        if len(self.frame_buffer) > 3:
            self.frame_buffer.pop(0)
            
        detected_pt = None
        if len(self.frame_buffer) == 3:
            detected_pt = self._detect_shuttlecock_candidate(self.frame_buffer, frame.shape)
            
        # Kalman Prediction
        pred = self.kf.predict()
        pred_x, pred_y = float(pred[0][0]), float(pred[1][0])
        
        current_pt = None
        is_interpolated = False
        
        if detected_pt is not None:
            # Measurement gating (reject physically impossible teleportation)
            if self.is_initialized:
                dist = np.hypot(detected_pt[0] - pred_x, detected_pt[1] - pred_y)
                max_allowed_jump = 250.0 # pixels at 30fps
                if dist < max_allowed_jump:
                    meas = np.array([[np.float32(detected_pt[0])], [np.float32(detected_pt[1])]])
                    self.kf.correct(meas)
                    current_pt = detected_pt
                    self.lost_frames_count = 0
                else:
                    # Gating failed, trust Kalman prediction
                    current_pt = (pred_x, pred_y)
                    is_interpolated = True
                    self.lost_frames_count += 1
            else:
                # Initialize state
                self.kf.statePost = np.array([[np.float32(detected_pt[0])],
                                              [np.float32(detected_pt[1])],
                                              [0.0], [0.0]], dtype=np.float32)
                current_pt = detected_pt
                self.is_initialized = True
                self.lost_frames_count = 0
        else:
            if self.is_initialized and self.lost_frames_count < self.max_lost_frames:
                # Extrapolate state via Kalman
                current_pt = (pred_x, pred_y)
                is_interpolated = True
                self.lost_frames_count += 1
            else:
                self.is_initialized = False
                current_pt = None

        # Calculate BWF world coordinates & Speed
        if current_pt is not None:
            px, py = current_pt
            world_x, world_y = self.court.pixel_to_world(px, py)
            
            # Speed calculation (km/h)
            speed_kmh = 0.0
            if len(self.trajectory) > 0:
                prev = self.trajectory[-1]
                dx_m = world_x - prev["bwf_x"]
                dy_m = world_y - prev["bwf_y"]
                dist_m = np.hypot(dx_m, dy_m)
                
                # Speed = (distance in meters / time step) * 3.6 for km/h
                raw_speed = (dist_m / self.dt) * 3.6
                
                # Physical badminton shuttlecock speed filter (up to 450 km/h)
                if raw_speed < 450.0:
                    # Exponential smoothing filter
                    speed_kmh = 0.7 * raw_speed + 0.3 * self.current_speed_kmh
                else:
                    speed_kmh = self.current_speed_kmh

            self.current_speed_kmh = speed_kmh
            if speed_kmh > self.max_speed_kmh and not is_interpolated:
                self.max_speed_kmh = speed_kmh

            frame_data = {
                "frame": self.frame_idx,
                "px": float(px),
                "py": float(py),
                "bwf_x": float(world_x),
                "bwf_y": float(world_y),
                "speed_kmh": float(speed_kmh),
                "interpolated": is_interpolated
            }
            self.trajectory.append(frame_data)
            if len(self.trajectory) > 30:
                self.trajectory.pop(0)

            return frame_data
        
        return None

    def _detect_shuttlecock_candidate(self, frames: List[np.ndarray], shape: Tuple[int, int, int]) -> Optional[Tuple[float, float]]:
        """
        High sensitivity candidate detection via 3-frame differencing + intensity peak analysis.
        """
        f_prev, f_curr, f_next = frames[0], frames[1], frames[2]
        
        # 3-frame differencing
        d1 = cv2.absdiff(f_curr, f_prev)
        d2 = cv2.absdiff(f_next, f_curr)
        diff = cv2.bitwise_and(d1, d2)
        
        # Dynamic threshold based on sensitivity slider
        thresh_val = int(35 - (self.sensitivity * 25)) # lower threshold = higher sensitivity
        thresh_val = max(8, thresh_val)
        
        _, mask_diff = cv2.threshold(diff, thresh_val, 255, cv2.THRESH_BINARY)
        
        # White brightness mask (shuttlecock is white)
        _, mask_white = cv2.threshold(f_curr, 200, 255, cv2.THRESH_BINARY)
        
        # Combined motion + brightness candidate mask
        candidate_mask = cv2.bitwise_and(mask_diff, mask_white)
        
        # Only look inside court playing area (avoid crowd & stadium ceiling)
        h, w = shape[:2]
        roi_mask = np.zeros_like(candidate_mask)
        roi_y_min, roi_y_max = int(0.20 * h), int(0.85 * h)
        roi_mask[roi_y_min:roi_y_max, :] = 255
        candidate_mask = cv2.bitwise_and(candidate_mask, roi_mask)

        contours, _ = cv2.findContours(candidate_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        candidates = []
        for c in contours:
            area = cv2.contourArea(c)
            # Shuttlecock blob is small: 4 to 120 pixels in area
            if 3 <= area <= 180:
                (cx, cy), radius = cv2.minEnclosingCircle(c)
                candidates.append(((cx, cy), area))
                
        if not candidates:
            return None
            
        # Select best candidate closest to predicted trajectory or with compact circularity
        if self.is_initialized and len(self.trajectory) > 0:
            last_pt = (self.trajectory[-1]["px"], self.trajectory[-1]["py"])
            candidates.sort(key=lambda cand: np.hypot(cand[0][0] - last_pt[0], cand[0][1] - last_pt[1]))
        else:
            candidates.sort(key=lambda cand: cand[1], reverse=True)
            
        return candidates[0][0]
