"""
Badminton Hawk-Eye CLI Video Processor
Processes an input badminton video, runs computer vision analysis, and exports an annotated Hawk-Eye video.
"""

import os
import sys
import argparse
import cv2
import json
import numpy as np
from court_detector import CourtDetector
from player_tracker import PlayerTracker
from shuttlecock_tracker import ShuttlecockTracker
from virtual_referee import VirtualReferee
from video_renderer import VideoRenderer

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

def process_video(input_path: str, output_path: str, mode: str = "singles", 
                  player1: str = "Momota", player2: str = "Axelsen", 
                  max_frames: int = None, sensitivity: float = 0.8):
    if not os.path.exists(input_path):
        print(f"Error: Input video not found at {input_path}")
        sys.exit(1)

    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"Loaded video: {width}x{height} @ {fps:.1f} FPS, Total Frames: {total_frames}")

    # Read first 30 frames to calibrate court detector
    court = CourtDetector(mode=mode)
    sample_frame = None
    for _ in range(30):
        ret, frame = cap.read()
        if ret:
            sample_frame = frame
            
    if sample_frame is None:
        print("Error: Could not read video frames.")
        sys.exit(1)

    court_info = court.detect_court(sample_frame)
    print("Court Detection Complete. Detected Corners:", court_info["corners"])

    # Reset video pointer
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    # Initialize Tracker Modules
    player_tracker = PlayerTracker(court, player_top_name=player1, player_bottom_name=player2)
    shuttle_tracker = ShuttlecockTracker(court, fps=fps, sensitivity=sensitivity)
    referee = VirtualReferee(court, fps=fps)
    renderer = VideoRenderer(court)

    # Video Writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_count = 0
    all_telemetry = []

    print("Beginning frame-by-frame Computer Vision pipeline...")
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if max_frames and frame_count > max_frames:
            break

        # 1. Player Tracking
        players = player_tracker.update(frame)

        # 2. Shuttlecock Tracking
        shuttle_data = shuttle_tracker.update(frame)

        # 3. Virtual Referee
        referee_data = referee.update(shuttle_data, players)

        # 4. Render Video Overlay
        rendered_frame = renderer.render_frame(
            frame=frame,
            court_data=court_info,
            players=players,
            shuttle_data=shuttle_data,
            shuttle_trajectory=shuttle_tracker.trajectory,
            referee_data=referee_data
        )

        out.write(rendered_frame)

        # Record telemetry
        all_telemetry.append({
            "frame": frame_count,
            "timestamp": round(frame_count / fps, 3),
            "shuttlecock": shuttle_data,
            "players": {
                "1": {"name": players[1]["name"], "dist": round(players[1]["rally_dist"], 2), "pos_bwf": [float(x) for x in players[1]["foot_bwf"]] if players[1]["foot_bwf"] else None},
                "2": {"name": players[2]["name"], "dist": round(players[2]["rally_dist"], 2), "pos_bwf": [float(x) for x in players[2]["foot_bwf"]] if players[2]["foot_bwf"] else None},
            },
            "referee": {
                "state": referee_data["state"],
                "shot_count": referee_data["shot_count"],
                "duration_sec": referee_data["duration_sec"],
                "decision": referee_data["decision"]
            }
        })

        if frame_count % 60 == 0:
            print(f"Processed {frame_count}/{total_frames} frames ({frame_count/total_frames*100:.1f}%) - Shots: {referee.shot_count}, Max Speed: {shuttle_tracker.max_speed_kmh:.1f} km/h")

    cap.release()
    out.release()

    # Save JSON telemetry file alongside video
    json_path = os.path.splitext(output_path)[0] + "_telemetry.json"
    with open(json_path, "w") as f:
        json.dump({
            "video_metadata": {"width": width, "height": height, "fps": fps, "total_frames": frame_count},
            "court_metadata": court_info,
            "summary": {
                "total_shots": referee.shot_count,
                "max_speed_kmh": round(shuttle_tracker.max_speed_kmh, 1),
                "rally_duration_sec": round(frame_count / fps, 2),
                "player_distances": {
                    player1: round(players[1]["total_dist"], 2),
                    player2: round(players[2]["total_dist"], 2)
                }
            },
            "frames": all_telemetry
        }, f, indent=2, cls=NumpyEncoder)

    print(f"Analysis complete! Saved rendered video to {output_path} and telemetry to {json_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Badminton Hawk-Eye Video Analyzer")
    parser.add_argument("--input", type=str, required=True, help="Path to input MP4 video")
    parser.add_argument("--output", type=str, required=True, help="Path to output rendered MP4 video")
    parser.add_argument("--mode", type=str, default="singles", choices=["singles", "doubles"], help="Court mode")
    parser.add_argument("--player1", type=str, default="Momota", help="Top court player name")
    parser.add_argument("--player2", type=str, default="Axelsen", help="Bottom court player name")
    parser.add_argument("--max-frames", type=int, default=None, help="Max frames to process")
    parser.add_argument("--sensitivity", type=float, default=0.8, help="Sensitivity threshold (0.1 - 1.0)")

    args = parser.parse_args()
    process_video(args.input, args.output, args.mode, args.player1, args.player2, args.max_frames, args.sensitivity)
