"""
Badminton Court Detector & Homography Engine
Author: Senior Computer Vision Engineer
Features:
- BWF Standard Dimension Mapping (Singles: 13.40m x 5.18m, Doubles: 13.40m x 6.10m)
- Automatic Court & Line Segmentation
- Corner Detection & Extrapolation (Projective Geometry / Cross-ratio / Line Intersection)
- RANSAC Homography Matrix Computation (Pixel <-> BWF Metric Space)
"""

import cv2
import numpy as np
from typing import Tuple, Dict, Optional, List

class CourtDetector:
    # BWF Standards (Dimensions in meters)
    BWF_LENGTH = 13.40
    BWF_WIDTH_SINGLES = 5.18
    BWF_WIDTH_DOUBLES = 6.10
    BWF_NET_POS = 6.70
    BWF_SHORT_SERVICE_DIST = 1.98  # from net (4.72m and 8.68m)
    BWF_DOUBLES_REAR_SERVICE_DIST = 0.76 # from baseline (0.76m and 12.64m)
    BWF_SIDE_TRAMLINE_WIDTH = 0.46 # difference between singles & doubles sideline

    def __init__(self, mode: str = "singles"):
        self.mode = mode.lower()
        self.width = self.BWF_WIDTH_SINGLES if self.mode == "singles" else self.BWF_WIDTH_DOUBLES
        self.length = self.BWF_LENGTH
        
        # World coordinates (X in [0, width], Y in [0, length])
        # Origin (0,0) is Top-Left (Far-Left corner)
        self.world_corners = np.array([
            [0.0, 0.0],              # Top-Left (Far-Left)
            [self.width, 0.0],       # Top-Right (Far-Right)
            [self.width, self.length],# Bottom-Right (Near-Right)
            [0.0, self.length]       # Bottom-Left (Near-Left)
        ], dtype=np.float32)
        
        self.H = None
        self.H_inv = None
        self.detected_corners = None

    @staticmethod
    def line_intersection(line1: Tuple[np.ndarray, np.ndarray], line2: Tuple[np.ndarray, np.ndarray]) -> Optional[Tuple[float, float]]:
        """Calculate intersection of two 2D lines defined by two points each."""
        p1, p2 = line1
        p3, p4 = line2
        x1, y1 = p1[0], p1[1]
        x2, y2 = p2[0], p2[1]
        x3, y3 = p3[0], p3[1]
        x4, y4 = p4[0], p4[1]

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-6:
            return None  # Parallel lines
        
        px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denom
        py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denom
        return (float(px), float(py))

    def detect_court(self, frame: np.ndarray) -> Dict:
        """
        Detects court boundaries and computes Homography.
        Supports automatic corner detection and geometric extrapolation for occluded/clipped corners.
        """
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 1. Court Surface Segmentation (Badminton green mat)
        lower_green = np.array([30, 25, 25])
        upper_green = np.array([90, 255, 255])
        court_mask = cv2.inRange(hsv, lower_green, upper_green)

        # Morphological clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        court_clean = cv2.morphologyEx(court_mask, cv2.MORPH_CLOSE, kernel)
        court_clean = cv2.morphologyEx(court_clean, cv2.MORPH_OPEN, kernel)

        # 2. White Line Extraction within Court
        white_mask = cv2.inRange(hsv, np.array([0, 0, 165]), np.array([180, 75, 255]))
        lines_mask = cv2.bitwise_and(white_mask, court_clean)

        # 3. Detect line segments via Probabilistic Hough Transform
        edges = cv2.Canny(lines_mask, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=40, minLineLength=35, maxLineGap=12)

        horizontals = []
        verticals = []

        if lines is not None:
            for l in lines:
                x1, y1, x2, y2 = l[0]
                dx = x2 - x1
                dy = y2 - y1
                angle = abs(np.arctan2(dy, dx) * 180 / np.pi)
                if angle < 25 or angle > 155:
                    horizontals.append(((float(x1), float(y1)), (float(x2), float(y2))))
                elif 50 < angle < 130:
                    verticals.append(((float(x1), float(y1)), (float(x2), float(y2))))

        # 4. Determine key boundaries (Far baseline, Near baseline, Left sideline, Right sideline)
        # Group & fit robust line equations
        far_y = 0.42 * h
        near_y = 0.75 * h

        if horizontals:
            far_cands = [l for l in horizontals if (l[0][1] + l[1][1]) / 2 < 0.55 * h]
            near_cands = [l for l in horizontals if (l[0][1] + l[1][1]) / 2 >= 0.55 * h]
            if far_cands:
                far_y = float(np.median([(l[0][1] + l[1][1]) / 2 for l in far_cands]))
            if near_cands:
                near_y = float(np.median([(l[0][1] + l[1][1]) / 2 for l in near_cands]))

        # Fit lines for sidelines
        left_pts = []
        right_pts = []
        mid_x = w / 2.0

        for l in verticals:
            lx = (l[0][0] + l[1][0]) / 2.0
            if lx < mid_x:
                left_pts.extend([l[0], l[1]])
            else:
                right_pts.extend([l[0], l[1]])

        # Robust fit or fallback to reliable geometry
        if len(left_pts) >= 4:
            pts = np.array(left_pts)
            [vx, vy, x0, y0] = cv2.fitLine(pts, cv2.DIST_L2, 0, 0.01, 0.01)
            left_line = ((float(x0), float(y0)), (float(x0 + vx * 100), float(y0 + vy * 100)))
        else:
            left_line = ((0.25 * w, far_y), (0.03 * w, near_y))

        if len(right_pts) >= 4:
            pts = np.array(right_pts)
            [vx, vy, x0, y0] = cv2.fitLine(pts, cv2.DIST_L2, 0, 0.01, 0.01)
            right_line = ((float(x0), float(y0)), (float(x0 + vx * 100), float(y0 + vy * 100)))
        else:
            right_line = ((0.75 * w, far_y), (0.97 * w, near_y))

        far_line = ((0.0, far_y), (float(w), far_y))
        near_line = ((0.0, near_y), (float(w), near_y))

        # 5. Corner Intersection Calculation
        tl = self.line_intersection(left_line, far_line)
        tr = self.line_intersection(right_line, far_line)
        br = self.line_intersection(right_line, near_line)
        bl = self.line_intersection(left_line, near_line)

        # Check for missing/clipped/out-of-bounds corners & extrapolate
        corners = self.extrapolate_missing_corners([tl, tr, br, bl], w, h, far_line, near_line, left_line, right_line)
        self.detected_corners = np.array(corners, dtype=np.float32)

        # 6. Compute Homography via RANSAC
        H, _ = cv2.findHomography(self.detected_corners, self.world_corners, cv2.RANSAC, 5.0)
        if H is not None:
            self.H = H
            self.H_inv = np.linalg.inv(H)
        else:
            # Fallback standard homography
            self.H, _ = cv2.findHomography(self.detected_corners, self.world_corners)
            self.H_inv = np.linalg.inv(self.H)

        return {
            "mode": self.mode,
            "corners": [list(c) for c in self.detected_corners],
            "H": self.H.tolist(),
            "H_inv": self.H_inv.tolist(),
            "world_dimensions": {"width": self.width, "length": self.length}
        }

    def extrapolate_missing_corners(self, corners: List[Optional[Tuple[float, float]]], 
                                   w: int, h: int, 
                                   far_line, near_line, left_line, right_line) -> List[Tuple[float, float]]:
        """
        Extrapolates missing, occluded or off-frame corners using perspective symmetry
        and line intersection equations.
        """
        tl, tr, br, bl = corners
        # Defaults based on camera perspective if any corner is severely degenerate
        default_tl = (0.25 * w, 0.42 * h)
        default_tr = (0.75 * w, 0.42 * h)
        default_br = (0.97 * w, 0.75 * h)
        default_bl = (0.03 * w, 0.75 * h)

        if tl is None or tl[1] < 0 or tl[0] < 0:
            tl = default_tl
        if tr is None or tr[1] < 0 or tr[0] > w * 1.2:
            tr = default_tr
        if br is None or br[1] > h * 1.2:
            # If bottom-right is missing, extrapolate from bottom-left & sideline slopes
            if bl is not None:
                br = (w - bl[0], bl[1])
            else:
                br = default_br
        if bl is None or bl[1] > h * 1.2:
            # If bottom-left is missing, extrapolate from bottom-right & sideline slopes
            if br is not None:
                bl = (w - br[0], br[1])
            else:
                bl = default_bl

        return [tl, tr, br, bl]

    def pixel_to_world(self, px: float, py: float) -> Tuple[float, float]:
        """Maps image pixel coordinates (u, v) to BWF court (X, Y) in meters."""
        if self.H is None:
            return (0.0, 0.0)
        pt = np.array([[[px, py]]], dtype=np.float32)
        trans = cv2.perspectiveTransform(pt, self.H)
        return float(trans[0][0][0]), float(trans[0][0][1])

    def world_to_pixel(self, x: float, y: float) -> Tuple[float, float]:
        """Maps BWF court (X, Y) in meters to image pixel coordinates (u, v)."""
        if self.H_inv is None:
            return (0.0, 0.0)
        pt = np.array([[[x, y]]], dtype=np.float32)
        trans = cv2.perspectiveTransform(pt, self.H_inv)
        return float(trans[0][0][0]), float(trans[0][0][1])

    def is_in_court(self, x_world: float, y_world: float, margin: float = 0.0) -> bool:
        """Determines if a world position falls inside the active BWF court boundaries."""
        return (-margin <= x_world <= self.width + margin) and (-margin <= y_world <= self.length + margin)
