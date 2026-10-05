import os
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import UPLOADS_DIR, OUTPUTS_DIR, get_ffmpeg_path, get_groq_api_key
from .styles import STYLES, get_style_by_id
from .transcribe import (
    extract_audio,
    get_video_info,
    transcribe_audio_groq,
    generate_demo_words,
    group_words_into_phrases
)
from .renderer import generate_ass, generate_srt, burn_captions_to_video

app = FastAPI(title="Captionizer Studio API", version="1.0.0")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store for uploaded tasks
TASKS: Dict[str, Dict[str, Any]] = {}

class TranscribeRequest(BaseModel):
    task_id: str
    groq_api_key: Optional[str] = None
    pacing: str = "auto"

class RenderRequest(BaseModel):
    task_id: str
    phrases: List[Dict[str, Any]]
    words: Optional[List[Dict[str, Any]]] = None
    style_id: str = "style_11"
    position_pct: int = 50
    size_pct: int = 100
    accent_color: str = "auto"

@app.get("/api/health")
async def health_check():
    has_groq = bool(get_groq_api_key())
    ffmpeg_exe = get_ffmpeg_path()
    return {
        "status": "healthy",
        "has_groq_env": has_groq,
        "ffmpeg": ffmpeg_exe
    }

@app.get("/api/styles")
async def get_styles():
    return {"styles": STYLES}

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    task_id = str(uuid.uuid4())[:8]
    ext = Path(file.filename).suffix or ".mp4"
    safe_name = f"{task_id}_source{ext}"
    video_path = UPLOADS_DIR / safe_name
    audio_path = UPLOADS_DIR / f"{task_id}_audio.mp3"

    # Save uploaded file
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract video info
    info = get_video_info(video_path)

    # Extract audio track
    has_audio = True
    try:
        extract_audio(video_path, audio_path)
    except Exception as e:
        has_audio = False

    TASKS[task_id] = {
        "task_id": task_id,
        "filename": file.filename,
        "video_path": str(video_path),
        "audio_path": str(audio_path),
        "has_audio": has_audio,
        "duration": info["duration"],
        "width": info["width"],
        "height": info["height"],
        "words": [],
        "phrases": []
    }

    return {
        "task_id": task_id,
        "filename": file.filename,
        "duration": info["duration"],
        "width": info["width"],
        "height": info["height"],
        "video_url": f"/api/files/video/{task_id}"
    }

@app.post("/api/transcribe")
async def transcribe(req: TranscribeRequest):
    task = TASKS.get(req.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    audio_path = Path(task["audio_path"])
    words = []
    provider = "groq"
    note = "Transcribed via Groq Whisper API (word-level timestamps)"

    # Attempt Groq Whisper
    try:
        words = transcribe_audio_groq(audio_path, req.groq_api_key)
    except Exception as e:
        # Fallback to realistic demo words
        provider = "demo"
        note = f"Groq Whisper unavailable ({str(e)}). Loaded sample transcription for testing."
        words = generate_demo_words(duration=task.get("duration", 5.0))

    # Group into phrases
    phrases = group_words_into_phrases(words, pacing=req.pacing)

    task["words"] = words
    task["phrases"] = phrases

    return {
        "task_id": req.task_id,
        "provider": provider,
        "note": note,
        "words": words,
        "phrases": phrases
    }

@app.post("/api/render")
async def render_video(req: RenderRequest):
    task = TASKS.get(req.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    video_path = Path(task["video_path"])
    out_prefix = f"{req.task_id}_rendered"
    ass_path = OUTPUTS_DIR / f"{out_prefix}.ass"
    srt_path = OUTPUTS_DIR / f"{out_prefix}.srt"
    mp4_path = OUTPUTS_DIR / f"{out_prefix}.mp4"

    # 1. Generate SRT
    generate_srt(req.phrases, srt_path)

    # 2. Generate ASS with word-by-word styling
    generate_ass(
        phrases=req.phrases,
        output_path=ass_path,
        style_id=req.style_id,
        position_pct=req.position_pct,
        size_pct=req.size_pct,
        custom_accent=req.accent_color,
        video_width=task.get("width", 1080),
        video_height=task.get("height", 1920)
    )

    # 3. Burn captions onto MP4
    try:
        burn_captions_to_video(video_path, ass_path, mp4_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rendering failed: {str(e)}")

    return {
        "task_id": req.task_id,
        "video_url": f"/api/files/output/{mp4_path.name}",
        "srt_url": f"/api/files/output/{srt_path.name}",
        "ass_url": f"/api/files/output/{ass_path.name}",
        "mp4_filename": mp4_path.name,
        "srt_filename": srt_path.name,
        "ass_filename": ass_path.name
    }

@app.get("/api/files/video/{task_id}")
async def serve_video(task_id: str):
    task = TASKS.get(task_id)
    if not task or not os.path.exists(task["video_path"]):
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(task["video_path"], media_type="video/mp4")

@app.get("/api/files/output/{filename}")
async def serve_output(filename: str):
    file_path = OUTPUTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    media_type = "video/mp4"
    if filename.endswith(".srt"):
        media_type = "text/plain"
    elif filename.endswith(".ass"):
        media_type = "text/plain"

    return FileResponse(
        str(file_path),
        media_type=media_type,
        filename=filename
    )

# Serve built frontend if dist exists
dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")
