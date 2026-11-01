"""
Badminton Hawk-Eye FastAPI Server
Provides WebSocket live telemetry streaming and REST API for mobile app integration.
"""

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
import shutil
import os
import cv2
import json
import asyncio
from court_detector import CourtDetector
from player_tracker import PlayerTracker
from shuttlecock_tracker import ShuttlecockTracker
from virtual_referee import VirtualReferee
from video_renderer import VideoRenderer
from cli_analyze import NumpyEncoder

app = FastAPI(title="Badminton Hawk-Eye Engine API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "processed"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.get("/")
def read_root():
    return {"system": "Badminton Hawk-Eye Edge Engine", "status": "ONLINE", "version": "1.0.0"}

@app.post("/api/calibrate_court")
async def calibrate_court(file: UploadFile = File(...), mode: str = Form("singles")):
    """Uploads a single court frame or sample image and returns detected court corners & Homography."""
    temp_path = os.path.join(UPLOAD_DIR, f"calib_{file.filename}")
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    img = cv2.imread(temp_path)
    if img is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file"})

    detector = CourtDetector(mode=mode)
    court_info = detector.detect_court(img)
    os.remove(temp_path)

    return JSONResponse(content=json.loads(json.dumps(court_info, cls=NumpyEncoder)))

@app.post("/api/analyze_video")
async def analyze_video(
    file: UploadFile = File(...),
    mode: str = Form("singles"),
    player1: str = Form("Momota"),
    player2: str = Form("Axelsen"),
    sensitivity: float = Form(0.8)
):
    """Processes video, produces rendered Hawk-Eye MP4 and returns full telemetry JSON."""
    input_path = os.path.join(UPLOAD_DIR, file.filename)
    output_filename = f"hawkeye_{file.filename}"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Run analysis
    from cli_analyze import process_video
    process_video(input_path, output_path, mode=mode, player1=player1, player2=player2, sensitivity=sensitivity)

    json_path = os.path.splitext(output_path)[0] + "_telemetry.json"
    with open(json_path, "r") as f:
        telemetry_data = json.load(f)

    return JSONResponse(content={
        "status": "success",
        "video_url": f"/api/download/{output_filename}",
        "telemetry": telemetry_data["summary"],
        "total_frames": telemetry_data["video_metadata"]["total_frames"]
    })

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="video/mp4", filename=filename)
    return JSONResponse(status_code=404, content={"error": "File not found"})

@app.websocket("/ws/live_telemetry")
async def websocket_telemetry_stream(websocket: WebSocket):
    """Live WebSocket channel for real-time telemetry streaming to Flutter client."""
    await websocket.accept()
    try:
        while True:
            # Client can request frame data or trigger live camera feed frames
            data = await websocket.receive_text()
            req = json.loads(data)
            await websocket.send_text(json.dumps({"status": "ack", "received": req}))
    except WebSocketDisconnect:
        print("WebSocket client disconnected")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
