"""
Captionizer Studio - High Fidelity Word-by-Word Animated Caption Generator
Matches exact UI/UX from reference design:
- 4-Tab workflow: Words & Transcript -> Caption Style -> Position & Size -> Render & Export
- Live 9:16 Preview Canvas with real-time word highlight sync
- Custom Video Player with scrubber, replay, 1x speed, volume, and centered play button
- 8 Curated Typography Styles including Editorial Hybrid (Inter/SF Pro + Instrument Serif Italic Glow)
- Editable Word List with word chip typo editing, ✦ emphasis toggle, words per phrase (2, 3, 4), and 'Last word italic'
- Free Offline Local AI (faster-whisper) + optional Groq Whisper integration
- Video Library & Backend Disk Storage manager
- Cloud-ready: Supports Render, Railway, Hugging Face Spaces (Docker), Fly.io, or VPS
"""

import os
import sys
import uuid
import json
import time
import socket
import shutil
import webbrowser
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Base directories
BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
ASSETS_DIR = BASE_DIR / "assets"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Helper: Find ffmpeg executable
def get_ffmpeg_path() -> str:
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    sys_exe = shutil.which("ffmpeg")
    return sys_exe if sys_exe else "ffmpeg"

def get_groq_api_key() -> str:
    return os.environ.get("GROQ_API_KEY", "").strip()

# Font mapping for FFmpeg libass:
# Maps user-facing family name -> (Exact internal font name in libass, Bold flag, Italic flag)
FONT_ASS_MAP = {
    "SF Pro Display": ("SF Pro Display", -1, 0),
    "Instrument Serif": ("Instrument Serif", 0, -1),
    "PP Editorial New": ("PP Editorial New", 0, 0),
    "Montserrat": ("Montserrat ExtraBold", 0, 0),
    "Poppins": ("Poppins ExtraBold", 0, 0),
    "Inter Caption": ("Inter ExtraBold", 0, 0),
    "Inter": ("Inter ExtraBold", 0, 0),
    "Plus Jakarta Sans": ("Plus Jakarta Sans", 0, 0),
    "Alex Brush": ("Alex Brush", 0, 0),
}

# 8 Caption Styles exactly matching reference design
STYLES = [
    {
        "id": "style_11",
        "name": "Editorial Hybrid",
        "featured": True,
        "tagline": "SF Pro / Inter ExtraBold + Instrument Serif Italic glowing aura",
        "description": "Regular words in Inter/SF Pro (800) with vertical scale (1.08). Emphasis words glow in Instrument Serif Italic with soft ambient aura.",
        "font_base": "Inter Caption",
        "font_emphasis": "Instrument Serif",
        "accent": "#FFFFFF",
        "sample_html": '<span class="s11">RELENTLESS <em>focus.</em></span>'
    },
    {
        "id": "style_10",
        "name": "Editorial Serif",
        "featured": False,
        "tagline": "Pure Instrument Serif with timeless magazine elegance",
        "description": "Timeless editorial magazine look with high-contrast serif italic typography.",
        "font_base": "PP Editorial New",
        "font_emphasis": "Instrument Serif",
        "accent": "#FFFFFF",
        "sample_html": '<span class="s10"><em>Subtle mastery.</em></span>'
    },
    {
        "id": "style_1",
        "name": "Bold Yellow",
        "featured": False,
        "tagline": "Montserrat 900 ALL-CAPS with black stroke & energetic yellow...",
        "description": "Punchy all-caps bold typography with electric yellow pop highlights.",
        "font_base": "Montserrat",
        "font_emphasis": "Montserrat",
        "accent": "#FFE600",
        "sample_html": '<span class="s1">LEVEL <span class="y">UP!</span></span>'
    },
    {
        "id": "style_2",
        "name": "Cyan Pop",
        "featured": False,
        "tagline": "Poppins 800 with electric neon cyan word highlights",
        "description": "Thick geometric typography with vibrant neon cyan key phrase highlighting.",
        "font_base": "Poppins",
        "font_emphasis": "Poppins",
        "accent": "#00E5FF",
        "sample_html": '<span class="s2">Instant <span class="c">speed</span></span>'
    },
    {
        "id": "style_3",
        "name": "Yellow Tag",
        "featured": False,
        "tagline": "Plus Jakarta Sans with a high-contrast yellow pill background",
        "description": "Clean modern sans-serif with a high-contrast yellow highlighter marker badge.",
        "font_base": "Plus Jakarta Sans",
        "font_emphasis": "Plus Jakarta Sans",
        "accent": "#FFE600",
        "sample_html": '<span class="s3">Pure <mark>GOLD</mark></span>'
    },
    {
        "id": "style_4",
        "name": "Red Impact",
        "featured": False,
        "tagline": "Crimson cinema glow with heavy uppercase typography",
        "description": "High-adrenaline styling with sharp contrast and neon crimson red glow.",
        "font_base": "Montserrat",
        "font_emphasis": "Montserrat",
        "accent": "#FF4154",
        "sample_html": '<span class="s4">RAW <span class="r">POWER</span></span>'
    },
    {
        "id": "style_5",
        "name": "Minimalist Mono",
        "featured": False,
        "tagline": "Clean modern monochrome Inter with soft opacity transitions",
        "description": "Minimalist clean aesthetic for storytellers, tech creators and documentarians.",
        "font_base": "Inter Caption",
        "font_emphasis": "Instrument Serif",
        "accent": "#FFFFFF",
        "sample_html": '<span class="s5">quiet <em>clarity</em></span>'
    },
    {
        "id": "style_6",
        "name": "Blue Glow",
        "featured": False,
        "tagline": "Electric cobalt drop-shadow on deep charcoal background",
        "description": "Dynamic electric cobalt drop glow highlighting impactful keywords.",
        "font_base": "Montserrat",
        "font_emphasis": "Montserrat",
        "accent": "#00AAFF",
        "sample_html": '<span class="s6">DEEP <span class="b">FLOW</span></span>'
    }
]

def get_style_by_id(style_id: str):
    for s in STYLES:
        if s["id"] == style_id:
            return s
    return STYLES[0]

# Fine-tuned rendering specifications for each style
STYLE_PROFILES = {
    "style_11": { # Editorial Hybrid
        "outline_normal": 1.0,
        "outline_color_normal": "&H50000000",
        "shadow_normal": 0,
        "blur_normal": 1,
        "blur_active": 2,
        "scale_y": 108,
        "emph_font_scale": 1.38,
        "emph_glow": True,
        "emph_blur": 6,
        "all_caps": False,
    },
    "style_10": { # Editorial Serif
        "outline_normal": 1.0,
        "outline_color_normal": "&H40000000",
        "shadow_normal": 0,
        "blur_normal": 1,
        "blur_active": 3,
        "scale_y": 100,
        "emph_font_scale": 1.25,
        "emph_glow": True,
        "emph_blur": 5,
        "all_caps": False,
    },
    "style_1": { # Bold Yellow
        "outline_normal": 3.0,
        "outline_color_normal": "&H00000000", # solid black outline
        "shadow_normal": 2.2,
        "blur_normal": 0,
        "blur_active": 0,
        "scale_y": 100,
        "emph_font_scale": 1.05,
        "emph_glow": False,
        "emph_blur": 0,
        "all_caps": True,
    },
    "style_2": { # Cyan Pop
        "outline_normal": 2.6,
        "outline_color_normal": "&H00000000",
        "shadow_normal": 1.8,
        "blur_normal": 0,
        "blur_active": 2,
        "scale_y": 100,
        "emph_font_scale": 1.05,
        "emph_glow": False,
        "emph_blur": 0,
        "all_caps": False,
    },
    "style_3": { # Yellow Tag
        "outline_normal": 2.2,
        "outline_color_normal": "&H00000000",
        "shadow_normal": 1.0,
        "blur_normal": 0,
        "blur_active": 1,
        "scale_y": 100,
        "emph_font_scale": 1.05,
        "emph_glow": False,
        "emph_blur": 0,
        "all_caps": False,
    },
    "style_4": { # Red Impact
        "outline_normal": 2.5,
        "outline_color_normal": "&H00000000",
        "shadow_normal": 2.0,
        "blur_normal": 0,
        "blur_active": 3,
        "scale_y": 100,
        "emph_font_scale": 1.08,
        "emph_glow": True,
        "emph_blur": 4,
        "all_caps": True,
    },
    "style_5": { # Minimalist Mono
        "outline_normal": 0.8,
        "outline_color_normal": "&H60000000",
        "shadow_normal": 0,
        "blur_normal": 1,
        "blur_active": 2,
        "scale_y": 100,
        "emph_font_scale": 1.25,
        "emph_glow": False,
        "emph_blur": 1,
        "all_caps": False,
    },
    "style_6": { # Blue Glow
        "outline_normal": 2.4,
        "outline_color_normal": "&H00000000",
        "shadow_normal": 2.0,
        "blur_normal": 0,
        "blur_active": 3,
        "scale_y": 100,
        "emph_font_scale": 1.08,
        "emph_glow": True,
        "emph_blur": 5,
        "all_caps": True,
    }
}

# Audio extraction & video info
def extract_audio(video_path: Path, output_audio_path: Path) -> Path:
    ffmpeg = get_ffmpeg_path()
    cmd = [
        ffmpeg, "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "libmp3lame",
        "-ar", "16000",
        "-ac", "1",
        "-b:a", "64k",
        str(output_audio_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed: {res.stderr}")
    return output_audio_path

def get_video_info(video_path: Path) -> Dict[str, Any]:
    ffmpeg = get_ffmpeg_path()
    cmd = [ffmpeg, "-i", str(video_path)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    duration = 12.0
    width = 720
    height = 1280
    has_audio = False

    for line in res.stderr.splitlines():
        if "Duration:" in line:
            try:
                part = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = part.split(":")
                duration = float(h) * 3600 + float(m) * 60 + float(s)
            except Exception:
                pass
        if "Video:" in line and "x" in line:
            import re
            m = re.search(r"(\d{3,5})x(\d{3,5})", line)
            if m:
                width = int(m.group(1))
                height = int(m.group(2))
        if "Audio:" in line:
            has_audio = True

    return {"duration": round(duration, 1), "width": width, "height": height, "has_audio": has_audio}

def ensure_demo_reel_exists():
    """Generates the 12-second 9:16 demo reel if it does not already exist."""
    dest = ASSETS_DIR / "demo_reel.mp4"
    if not dest.exists():
        ffmpeg = get_ffmpeg_path()
        cmd = [
            ffmpeg, "-y",
            "-f", "lavfi", "-i", "color=c=0x0a0c12:s=720x1280:d=12:r=30",
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-vf", r"drawtext=text=CAPTIONIZER DEMO:fontcolor=white@0.2:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2-30,drawtext=text=00\\:00\\:01.000:fontcolor=orange@0.25:fontsize=30:x=(w-text_w)/2:y=(h-text_h)/2+20",
            "-t", "12",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            str(dest)
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except Exception as e:
            print("Notice: demo reel auto-generation fallback:", e)

# Speech Transcription
_WHISPER_MODEL = None

def get_local_whisper_model():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        try:
            from faster_whisper import WhisperModel
            print("Loading local faster-whisper (tiny, CPU int8)...")
            _WHISPER_MODEL = WhisperModel("tiny", device="cpu", compute_type="int8")
            print("Local whisper model ready.")
        except Exception as e:
            print("faster-whisper init notice:", e)
            _WHISPER_MODEL = None
    return _WHISPER_MODEL

def transcribe_audio_local(audio_path: Path) -> List[Dict[str, Any]]:
    model = get_local_whisper_model()
    if model is None:
        raise RuntimeError("Local faster-whisper is not available.")

    segments, info = model.transcribe(
        str(audio_path),
        beam_size=5,
        word_timestamps=True,
        vad_filter=True
    )

    words = []
    for segment in segments:
        if segment.words:
            for w in segment.words:
                raw_text = w.word.strip()
                clean_text = raw_text.lstrip(",.;:!?")
                if not clean_text:
                    continue
                words.append({
                    "id": f"w_{len(words)}",
                    "text": clean_text,
                    "start": round(float(w.start), 2),
                    "end": round(float(w.end), 2),
                    "emphasis": False
                })
    return words

def transcribe_audio_groq(audio_path: Path, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    key = api_key or get_groq_api_key()
    if not key:
        raise ValueError("GROQ_API_KEY is not configured.")

    from groq import Groq
    client = Groq(api_key=key)
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(audio_path.name, f.read()),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"]
        )

    words = []
    if hasattr(transcription, "words") and transcription.words:
        for idx, w in enumerate(transcription.words):
            raw = w.word.strip()
            clean = raw.lstrip(",.;:!?")
            if clean:
                words.append({
                    "id": f"w_{idx}",
                    "text": clean,
                    "start": round(float(w.start), 2),
                    "end": round(float(w.end), 2),
                    "emphasis": False
                })
    return words

def get_demo_words_and_phrases(words_per_phrase: int = 3):
    raw_tokens = [
        ("if", 0.40, 0.75, False),
        ("you", 0.75, 1.15, False),
        ("want", 1.15, 1.60, True),
        ("to", 1.70, 2.10, False),
        ("float", 2.10, 2.90, True),
        ("above", 2.90, 3.60, False),
        ("the", 3.60, 4.00, False),
        ("ordinary,", 4.00, 4.90, True),
        ("master", 5.30, 5.80, False),
        ("your", 5.80, 6.25, False),
        ("craft", 6.25, 6.90, True),
        ("step", 7.30, 7.90, False),
        ("by", 7.90, 8.50, False),
        ("step", 8.50, 9.60, True)
    ]
    all_words = []
    for idx, (t, s, e, emph) in enumerate(raw_tokens):
        all_words.append({
            "id": f"w_{idx}",
            "text": t,
            "start": s,
            "end": e,
            "emphasis": emph
        })

    phrases = group_words_into_phrases(all_words, target_words_per_phrase=words_per_phrase)
    return all_words, phrases

def apply_casing(text: str, casing: str) -> str:
    if casing == "upper": return text.upper()
    if casing == "title": return text.title()
    if casing == "lower": return text.lower()
    return text

def group_words_into_phrases(
    words: List[Dict[str, Any]],
    target_words_per_phrase: int = 3,
    casing: str = "default"
) -> List[Dict[str, Any]]:
    if not words:
        return []

    phrases = []
    curr_words = []

    for i, word in enumerate(words):
        w_copy = dict(word)
        w_copy["text"] = apply_casing(w_copy["text"], casing)
        curr_words.append(w_copy)

        has_punct = any(w_copy["text"].endswith(p) for p in [".", ",", "!", "?", ";"])
        time_gap = (i < len(words) - 1) and ((words[i+1]["start"] - word["end"]) > 0.45)
        should_break = len(curr_words) >= target_words_per_phrase or has_punct or time_gap or (i == len(words) - 1)

        if should_break and curr_words:
            # Emphasize the last word of phrase if none is emphasized
            if not any(w.get("emphasis") for w in curr_words):
                curr_words[-1]["emphasis"] = True
            
            phrases.append({
                "id": f"phrase_{len(phrases)}",
                "start": curr_words[0]["start"],
                "end": curr_words[-1]["end"],
                "text": " ".join(w["text"] for w in curr_words),
                "words": curr_words
            })
            curr_words = []
    return phrases

# Subtitle generation & FFmpeg burn
def format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100: cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000: ms = 999
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def hex_to_ass_color(hex_color: str, alpha: int = 0) -> str:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    else:
        r, g, b = "FF", "FF", "FF"
    return f"&H{alpha:02X}{b}{g}{r}"

def generate_ass(
    phrases: List[Dict[str, Any]],
    output_path: Path,
    style_id: str = "style_11",
    custom_font: Optional[str] = None,
    casing: Optional[str] = "default",
    emphasis_font: Optional[str] = None,
    position_pct: int = 80,
    size_pct: int = 100,
    custom_accent: str = "auto",
    video_width: int = 720,
    video_height: int = 1280
) -> Path:
    prof = STYLE_PROFILES.get(style_id, STYLE_PROFILES["style_11"])
    style_info = get_style_by_id(style_id)
    accent_color = style_info["accent"] if custom_accent == "auto" else custom_accent
    highlight_ass = hex_to_ass_color(accent_color, 0)

    # Sizing dynamically scaled to resolution height (reference: 1280)
    scale_factor = (video_height / 1280.0) * (size_pct / 100.0)
    base_font_size = max(24, int(48 * scale_factor))
    emph_scale = prof["emph_font_scale"]
    emphasis_font_size = max(28, int(48 * emph_scale * scale_factor))

    # Font determination
    font_base_key = custom_font if (custom_font and custom_font != "auto") else style_info["font_base"]
    if emphasis_font == "same":
        font_emph_key = font_base_key
    elif emphasis_font and emphasis_font != "auto":
        font_emph_key = emphasis_font
    else:
        font_emph_key = style_info["font_emphasis"]

    base_font_name, base_bold, base_italic = FONT_ASS_MAP.get(font_base_key, (font_base_key, -1, 0))
    emph_font_name, emph_bold, emph_italic = FONT_ASS_MAP.get(font_emph_key, (font_emph_key, 0, -1))

    scale_y = prof["scale_y"]
    outline_val = prof["outline_normal"]
    outline_col = prof["outline_color_normal"]
    shadow_val = prof["shadow_normal"]
    shadow_col = "&H80000000"

    # Margin from bottom for Alignment 2 (bottom center)
    ass_margin_v = int((1.0 - (position_pct / 100.0)) * video_height) - int(base_font_size / 2)
    if ass_margin_v < 40: ass_margin_v = 40
    if ass_margin_v > video_height - 80: ass_margin_v = video_height - 80

    emph_outline_col = highlight_ass if prof["emph_glow"] else outline_col

    header = f"""[Script Info]
Title: Caption AI Word-by-Word Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Normal,{base_font_name},{base_font_size},&H00FFFFFF,&H000000FF,{outline_col},{shadow_col},{base_bold},{base_italic},0,0,100,{scale_y},1,0,1,{outline_val},{shadow_val},2,40,40,{ass_margin_v},1
Style: Active,{base_font_name},{base_font_size},{highlight_ass},&H000000FF,{outline_col},{shadow_col},{base_bold},{base_italic},0,0,103,{scale_y+3},1,0,1,{outline_val+0.3},{shadow_val},2,40,40,{ass_margin_v},1
Style: Emphasis,{emph_font_name},{emphasis_font_size},{highlight_ass},&H000000FF,{emph_outline_col},{shadow_col},{emph_bold},{emph_italic},0,0,100,100,2,0,1,{outline_val+0.5},{shadow_val},2,40,40,{ass_margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Casing selection
    eff_casing = casing if (casing and casing != "default") else ("upper" if prof["all_caps"] else "default")

    events = []
    for phrase in phrases:
        words = phrase.get("words", [])
        if not words: continue

        for active_idx, active_word in enumerate(words):
            start_t = format_ass_time(active_word["start"])
            end_t = format_ass_time(active_word["end"])

            text_chunks = []
            for j, w in enumerate(words):
                is_curr = (j == active_idx)
                is_emph = w.get("emphasis", False)
                clean_w = w["text"].strip().lstrip(",.;:!?")
                if not clean_w: continue

                if eff_casing == "upper":
                    clean_w = clean_w.upper()
                elif eff_casing == "lower":
                    clean_w = clean_w.lower()
                elif eff_casing == "title":
                    clean_w = clean_w.title()

                if is_curr:
                    if is_emph:
                        if prof["emph_glow"]:
                            b_r = prof["emph_blur"]
                            text_chunks.append(f"{{\\rEmphasis\\c{highlight_ass}\\3c{highlight_ass}\\blur{b_r}}}{clean_w}{{\\rNormal}}")
                        else:
                            text_chunks.append(f"{{\\rEmphasis\\c{highlight_ass}\\3c{outline_col}\\blur0}}{clean_w}{{\\rNormal}}")
                    else:
                        b_a = prof["blur_active"]
                        blur_tag = f"\\blur{b_a}" if b_a > 0 else "\\blur0"
                        text_chunks.append(f"{{\\rActive\\c{highlight_ass}{blur_tag}}}{clean_w}{{\\rNormal}}")
                else:
                    if is_emph:
                        if prof["emph_glow"]:
                            text_chunks.append(f"{{\\rEmphasis\\alpha&H60&\\blur2}}{clean_w}{{\\rNormal}}")
                        else:
                            text_chunks.append(f"{{\\rEmphasis\\alpha&H60&\\3c{outline_col}}}{clean_w}{{\\rNormal}}")
                    else:
                        text_chunks.append(f"{{\\alpha&H60&}}{clean_w}{{\\alpha&H00&}}")

            full_line = " ".join(text_chunks)
            events.append(f"Dialogue: 0,{start_t},{end_t},Normal,,0,0,0,,{full_line}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")
    return output_path

def burn_captions_to_video(video_path: Path, ass_path: Path, output_path: Path) -> Path:
    ffmpeg = get_ffmpeg_path()
    rel_ass = f"outputs/{ass_path.name}"
    
    info = get_video_info(video_path)
    has_audio = info.get("has_audio", False)

    cmd = [
        ffmpeg, "-y",
        "-i", str(video_path.resolve()),
        "-vf", f"ass=filename={rel_ass}:fontsdir=assets",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
    ]
    if has_audio:
        cmd.extend(["-c:a", "aac", "-b:a", "192k"])
    else:
        cmd.append("-an")

    cmd.append(str(output_path.resolve()))

    res = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg caption burning failed:\n{res.stderr}")
    return output_path

# FASTAPI APP
app = FastAPI(title="Caption AI", version="4.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

TASKS: Dict[str, Dict[str, Any]] = {}

# Session API Keys storage
CONFIG: Dict[str, Any] = {
    "groq_api_key": get_groq_api_key()
}

class TranscribeRequest(BaseModel):
    task_id: str
    groq_api_key: Optional[str] = None
    words_per_phrase: int = 3
    casing: str = "default"

class RenderRequest(BaseModel):
    task_id: str
    phrases: List[Dict[str, Any]]
    words: Optional[List[Dict[str, Any]]] = None
    style_id: str = "style_11"
    custom_font: Optional[str] = None
    casing: Optional[str] = "default"
    emphasis_font: Optional[str] = None
    position_pct: int = 80
    size_pct: int = 100
    accent_color: str = "auto"

class KeyUpdateRequest(BaseModel):
    groq_api_key: str

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "has_groq_env": bool(CONFIG.get("groq_api_key")),
        "ffmpeg": get_ffmpeg_path()
    }

@app.get("/api/keys")
async def get_keys():
    k = CONFIG.get("groq_api_key", "")
    masked = f"{k[:4]}...{k[-4:]}" if len(k) > 8 else ("Configured" if k else "")
    return {"has_key": bool(k), "masked": masked}

@app.post("/api/keys")
async def set_keys(req: KeyUpdateRequest):
    CONFIG["groq_api_key"] = req.groq_api_key.strip()
    return {"status": "updated", "has_key": bool(CONFIG["groq_api_key"])}

@app.get("/api/styles")
async def get_styles():
    return {"styles": STYLES}

@app.get("/api/demo")
async def get_demo():
    ensure_demo_reel_exists()
    demo_video = ASSETS_DIR / "demo_reel.mp4"
    if not demo_video.exists():
        demo_video = ASSETS_DIR / "preview_bg.jpg"
    
    words, phrases = get_demo_words_and_phrases(words_per_phrase=3)
    task_id = "demo_reel"
    TASKS[task_id] = {
        "task_id": task_id,
        "filename": "demo-sample-916.mp4",
        "video_path": str(demo_video),
        "duration": 12.0,
        "width": 720,
        "height": 1280,
        "words": words,
        "phrases": phrases
    }
    return {
        "task_id": task_id,
        "filename": "demo-sample-916.mp4",
        "duration": 12.0,
        "width": 720,
        "height": 1280,
        "video_url": "/assets/demo_reel.mp4",
        "words": words,
        "phrases": phrases
    }

@app.get("/api/videos")
async def list_videos():
    videos = []
    total_bytes = 0
    source_files = list(UPLOADS_DIR.glob("*_source.*"))
    for f in source_files:
        f_size = f.stat().st_size
        total_bytes += f_size
        task_id = f.stem.replace("_source", "")
        rendered_mp4 = OUTPUTS_DIR / f"{task_id}_rendered.mp4"
        r_size = rendered_mp4.stat().st_size if rendered_mp4.exists() else 0
        total_bytes += r_size
        videos.append({
            "task_id": task_id,
            "filename": f.name,
            "size_mb": round((f_size + r_size) / (1024 * 1024), 2),
            "video_url": f"/api/files/video/{task_id}",
            "is_rendered": rendered_mp4.exists(),
            "rendered_url": f"/api/files/output/{rendered_mp4.name}" if rendered_mp4.exists() else None,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_ctime))
        })
    videos.sort(key=lambda x: x["created_at"], reverse=True)
    return {
        "videos": videos,
        "total_storage_mb": round(total_bytes / (1024 * 1024), 2),
        "total_count": len(videos)
    }

@app.get("/api/videos/{task_id}")
async def get_video_task(task_id: str):
    if task_id == "demo_reel":
        return await get_demo()

    source_files = list(UPLOADS_DIR.glob(f"{task_id}_source.*"))
    if not source_files:
        raise HTTPException(status_code=404, detail="Video file not found")
    
    video_path = source_files[0]
    audio_path = UPLOADS_DIR / f"{task_id}_audio.mp3"
    info = get_video_info(video_path)

    rendered_mp4 = OUTPUTS_DIR / f"{task_id}_rendered.mp4"
    task_data = {
        "task_id": task_id,
        "filename": video_path.name,
        "video_path": str(video_path),
        "audio_path": str(audio_path),
        "has_audio": audio_path.exists(),
        "duration": info["duration"],
        "width": info["width"],
        "height": info["height"],
        "video_url": f"/api/files/video/{task_id}",
        "is_rendered": rendered_mp4.exists(),
        "rendered_url": f"/api/files/output/{rendered_mp4.name}" if rendered_mp4.exists() else None,
        "words": TASKS.get(task_id, {}).get("words", []),
        "phrases": TASKS.get(task_id, {}).get("phrases", [])
    }
    TASKS[task_id] = task_data
    return task_data

@app.delete("/api/videos/{task_id}")
async def delete_video(task_id: str):
    deleted_files = []
    for p in UPLOADS_DIR.glob(f"{task_id}*"):
        try:
            p.unlink()
            deleted_files.append(p.name)
        except Exception:
            pass
    for p in OUTPUTS_DIR.glob(f"{task_id}*"):
        try:
            p.unlink()
            deleted_files.append(p.name)
        except Exception:
            pass
    if task_id in TASKS:
        del TASKS[task_id]
    return {"status": "deleted", "task_id": task_id, "deleted_files": deleted_files}

@app.delete("/api/videos")
async def clear_all_videos():
    count = 0
    for p in UPLOADS_DIR.glob("*"):
        try:
            p.unlink()
            count += 1
        except Exception:
            pass
    for p in OUTPUTS_DIR.glob("*"):
        if not p.name.startswith("debug") and not p.name.startswith("preview"):
            try:
                p.unlink()
                count += 1
            except Exception:
                pass
    TASKS.clear()
    return {"status": "cleared", "deleted_count": count}

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    task_id = str(uuid.uuid4())[:8]
    ext = Path(file.filename).suffix or ".mp4"
    safe_name = f"{task_id}_source{ext}"
    video_path = UPLOADS_DIR / safe_name
    audio_path = UPLOADS_DIR / f"{task_id}_audio.mp3"

    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    info = get_video_info(video_path)
    try:
        extract_audio(video_path, audio_path)
        has_audio = True
    except Exception:
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
async def transcribe_video(req: TranscribeRequest):
    if req.task_id == "demo_reel":
        words, phrases = get_demo_words_and_phrases(words_per_phrase=req.words_per_phrase)
        return {"task_id": "demo_reel", "words": words, "phrases": phrases}

    task = TASKS.get(req.task_id)
    if not task:
        source_files = list(UPLOADS_DIR.glob(f"{req.task_id}_source.*"))
        if not source_files:
            raise HTTPException(status_code=404, detail="Task not found. Please upload again.")
        video_path = source_files[0]
        audio_path = UPLOADS_DIR / f"{req.task_id}_audio.mp3"
        if not audio_path.exists():
            try:
                extract_audio(video_path, audio_path)
            except Exception:
                pass
        info = get_video_info(video_path)
        task = {
            "task_id": req.task_id,
            "filename": video_path.name,
            "video_path": str(video_path),
            "audio_path": str(audio_path),
            "has_audio": audio_path.exists(),
            "duration": info["duration"],
            "width": info["width"],
            "height": info["height"],
            "words": [],
            "phrases": []
        }
        TASKS[req.task_id] = task

    audio_path = Path(task["audio_path"])
    words = []
    
    # 1. Groq if configured
    groq_key = req.groq_api_key or CONFIG.get("groq_api_key")
    if groq_key and audio_path.exists():
        try:
            print("Transcribing via Groq Whisper...")
            words = transcribe_audio_groq(audio_path, api_key=groq_key)
        except Exception as e:
            print("Groq transcription notice:", e)

    # 2. Local AI faster-whisper
    if not words and audio_path.exists():
        try:
            print("Transcribing via local faster-whisper...")
            words = transcribe_audio_local(audio_path)
        except Exception as e:
            print("Local whisper notice:", e)

    # 3. Fallback demo words
    if not words:
        all_words, phrases = get_demo_words_and_phrases(words_per_phrase=req.words_per_phrase)
        words = all_words

    phrases = group_words_into_phrases(words, target_words_per_phrase=req.words_per_phrase, casing=req.casing)
    task["words"] = words
    task["phrases"] = phrases

    return {
        "task_id": req.task_id,
        "words": words,
        "phrases": phrases
    }

@app.post("/api/render")
async def render_video(req: RenderRequest):
    if req.task_id == "demo_reel":
        ensure_demo_reel_exists()
        video_path = ASSETS_DIR / "demo_reel.mp4"
        w, h = 720, 1280
    else:
        task = TASKS.get(req.task_id)
        if not task:
            source_files = list(UPLOADS_DIR.glob(f"{req.task_id}_source.*"))
            if not source_files:
                raise HTTPException(status_code=404, detail="Task not found")
            video_path = source_files[0]
            info = get_video_info(video_path)
            w, h = info["width"], info["height"]
        else:
            video_path = Path(task["video_path"])
            w = task.get("width", 720)
            h = task.get("height", 1280)

    ass_path = OUTPUTS_DIR / f"{req.task_id}_rendered.ass"
    srt_path = OUTPUTS_DIR / f"{req.task_id}_rendered.srt"
    output_mp4 = OUTPUTS_DIR / f"{req.task_id}_rendered.mp4"

    # 1. Generate ASS
    generate_ass(
        phrases=req.phrases,
        output_path=ass_path,
        style_id=req.style_id,
        custom_font=req.custom_font,
        casing=req.casing,
        emphasis_font=req.emphasis_font,
        position_pct=req.position_pct,
        size_pct=req.size_pct,
        custom_accent=req.accent_color,
        video_width=w,
        video_height=h
    )

    # 2. Generate SRT
    srt_lines = []
    for idx, p in enumerate(req.phrases, 1):
        s_t = format_srt_time(p["start"])
        e_t = format_srt_time(p["end"])
        srt_lines.append(f"{idx}\n{s_t} --> {e_t}\n{p['text']}\n")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    # 3. Burn captions via FFmpeg
    burn_captions_to_video(video_path, ass_path, output_mp4)

    return {
        "status": "success",
        "video_url": f"/api/files/output/{output_mp4.name}",
        "srt_url": f"/api/files/output/{srt_path.name}",
        "ass_url": f"/api/files/output/{ass_path.name}"
    }

@app.get("/api/files/video/{task_id}")
async def serve_video(task_id: str):
    matches = list(UPLOADS_DIR.glob(f"{task_id}_source.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(matches[0])

@app.get("/api/files/output/{filename}")
async def serve_output(filename: str):
    file_path = OUTPUTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

# MAIN WEB UI
STUDIO_HTML = """<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Caption AI — Word-by-word animated captions with Groq Whisper & FFmpeg</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0C0F17;
      --surface: #141923;
      --surface-2: #1A202E;
      --surface-hover: #222A3A;
      --border: #222A3A;
      --border-strong: #2E384D;
      --text: #F3F4F6;
      --text-2: #9CA3AF;
      --text-3: #6B7280;
      --accent: #E25822;
      --accent-hover: #F05A28;
      --accent-gradient: linear-gradient(135deg, #F05A28 0%, #D94611 100%);
      --accent-soft: rgba(226, 88, 34, 0.15);
      --accent-glow: 0 0 16px rgba(226, 88, 34, 0.45);
      --danger: #EF4444;
      --danger-soft: rgba(239, 68, 68, 0.15);
      --success: #10B981;
      --r: 8px;
      --r-lg: 14px;
    }

    [data-theme="light"] {
      --bg: #F4F6F9;
      --surface: #FFFFFF;
      --surface-2: #EDF2F7;
      --surface-hover: #E2E8F0;
      --border: #E2E8F0;
      --border-strong: #CBD5E1;
      --text: #0F172A;
      --text-2: #475569;
      --text-3: #94A3B8;
    }

    /* Embedded Typography */
    @font-face { font-family: 'SF Pro Display'; src: url('/assets/SF-Pro-Display-Bold.otf') format('opentype'); font-weight: 700; }
    @font-face { font-family: 'Instrument Serif'; src: url('/assets/InstrumentSerif-Italic.ttf') format('truetype'); font-weight: 400; font-style: italic; }
    @font-face { font-family: 'PP Editorial New'; src: url('/assets/PPEditorialNew-Regular.otf') format('opentype'); }
    @font-face { font-family: 'Montserrat'; src: url('/assets/Montserrat-ExtraBold.ttf') format('truetype'); font-weight: 800; }
    @font-face { font-family: 'Poppins'; src: url('/assets/Poppins-ExtraBold.ttf') format('truetype'); font-weight: 800; }
    @font-face { font-family: 'Plus Jakarta Sans'; src: url('/assets/PlusJakartaSans-VariableFont_wght.ttf') format('truetype'); }
    @font-face { font-family: 'Inter Caption'; src: url('/assets/Inter-ExtraBold.otf') format('opentype'); font-weight: 800; }
    @font-face { font-family: 'Alex Brush'; src: url('/assets/AlexBrush-Regular.ttf') format('truetype'); }

    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      overflow-x: hidden;
      display: flex;
      flex-direction: column;
    }

    /* Topbar Header */
    .topbar {
      height: 60px;
      border-bottom: 1px solid var(--border);
      background: var(--bg);
      display: flex;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 50;
      padding: 0 24px;
    }
    .topbar-inner {
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .brand-group {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-mark {
      width: 32px;
      height: 32px;
      border-radius: 9px;
      background: var(--accent-gradient);
      box-shadow: 0 0 16px rgba(226, 88, 34, 0.4);
      display: grid;
      place-items: center;
      font-size: 17px;
      font-weight: 900;
      color: #fff;
    }
    .brand-title {
      font-size: 17px;
      font-weight: 800;
      color: var(--text);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .badge-pill {
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      padding: 3px 8px;
      border-radius: 999px;
      background: rgba(226, 88, 34, 0.2);
      border: 1px solid rgba(226, 88, 34, 0.4);
      color: #F97316;
    }
    .brand-sub {
      font-size: 11px;
      color: var(--text-3);
      margin-top: 1px;
    }

    .top-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .btn-top {
      height: 34px;
      padding: 0 12px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--text);
      cursor: pointer;
      transition: all 0.15s;
    }
    .btn-top:hover {
      border-color: var(--border-strong);
      background: var(--surface-2);
    }
    .btn-top-orange {
      background: var(--accent-gradient);
      border: none;
      color: #fff;
      box-shadow: 0 2px 10px rgba(226, 88, 34, 0.35);
    }
    .btn-top-orange:hover {
      filter: brightness(1.1);
    }
    .status-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #10B981;
    }

    /* Studio Main Layout */
    .studio-container {
      display: grid;
      grid-template-columns: 420px 1fr;
      flex: 1;
      height: calc(100vh - 60px);
      overflow: hidden;
    }

    /* Left Column: Live Preview */
    .preview-col {
      background: #0B0E15;
      border-right: 1px solid var(--border);
      padding: 20px 24px;
      display: flex;
      flex-direction: column;
      align-items: center;
      overflow-y: auto;
      gap: 14px;
    }
    .preview-header {
      width: 100%;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11.5px;
      font-weight: 700;
      color: var(--text-3);
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }

    /* Vertical Phone Screen */
    .phone-canvas {
      width: 295px;
      height: 525px;
      border-radius: 28px;
      background: #000;
      position: relative;
      overflow: hidden;
      box-shadow: 0 20px 50px -10px rgba(0,0,0,0.85), 0 0 0 1.5px var(--border-strong);
      user-select: none;
    }
    .phone-canvas iframe, .phone-canvas video {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    .canvas-badge-left {
      position: absolute;
      top: 12px;
      left: 12px;
      z-index: 25;
      font-size: 10px;
      font-weight: 700;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(6px);
      color: #fff;
      padding: 4px 8px;
      border-radius: 6px;
      border: 1px solid rgba(255, 255, 255, 0.15);
      pointer-events: none;
    }
    .canvas-badge-right {
      position: absolute;
      top: 12px;
      right: 12px;
      z-index: 25;
      font-size: 10px;
      font-weight: 700;
      background: var(--accent-gradient);
      color: #fff;
      padding: 4px 8px;
      border-radius: 6px;
      box-shadow: 0 2px 8px rgba(226, 88, 34, 0.4);
      pointer-events: none;
    }

    /* Big Center Play Overlay */
    .play-overlay-circle {
      position: absolute;
      inset: 0;
      z-index: 24;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      background: rgba(0,0,0,0.25);
      transition: background 0.15s;
    }
    .play-overlay-circle:hover {
      background: rgba(0,0,0,0.35);
    }
    .circle-play-btn {
      width: 58px;
      height: 58px;
      border-radius: 50%;
      background: var(--accent-gradient);
      box-shadow: 0 8px 24px rgba(226, 88, 34, 0.5);
      display: grid;
      place-items: center;
      color: #fff;
      font-size: 22px;
      padding-left: 4px;
      transition: transform 0.15s;
    }
    .play-overlay-circle:hover .circle-play-btn {
      transform: scale(1.1);
    }

    /* Live Caption Text Overlay */
    .live-caption-overlay {
      position: absolute;
      left: 0;
      right: 0;
      top: 80%;
      transform: translateY(-50%);
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      justify-content: center;
      gap: 8px;
      padding: 0 16px;
      pointer-events: none;
      z-index: 22;
      text-align: center;
      transition: top 0.08s ease-out;
    }

    /* Drag Handle for Position */
    .drag-handle-overlay {
      position: absolute;
      inset: 0;
      z-index: 23;
      cursor: ns-resize;
    }
    .drag-line {
      position: absolute;
      left: 0;
      right: 0;
      top: 80%;
      height: 2px;
      background: var(--accent);
      opacity: 0;
      transition: opacity .15s;
      pointer-events: none;
    }
    .drag-handle-overlay:hover .drag-line {
      opacity: 0.9;
    }
    .drag-pill {
      position: absolute;
      left: 50%;
      top: -14px;
      transform: translateX(-50%);
      background: #1A202E;
      color: #fff;
      font-size: 10px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 999px;
      border: 1px solid var(--accent);
    }

    /* Player Controls Bar */
    .player-dock {
      width: 295px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .player-progress-bar {
      width: 100%;
      height: 5px;
      background: rgba(255, 255, 255, 0.15);
      border-radius: 3px;
      cursor: pointer;
      position: relative;
    }
    .player-progress-fill {
      height: 100%;
      background: var(--accent);
      border-radius: 3px;
      width: 0%;
      pointer-events: none;
      position: relative;
    }
    .player-progress-thumb {
      width: 11px;
      height: 11px;
      border-radius: 50%;
      background: #fff;
      border: 2px solid var(--accent);
      position: absolute;
      right: -5px;
      top: -3px;
      box-shadow: 0 0 6px rgba(0,0,0,0.5);
    }
    .player-dock-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11.5px;
    }
    .player-mini-btn {
      background: transparent;
      border: none;
      color: var(--text-2);
      font-size: 13px;
      cursor: pointer;
      padding: 3px 5px;
      border-radius: 4px;
      transition: all 0.15s;
    }
    .player-mini-btn:hover {
      color: #fff;
      background: var(--surface-2);
    }
    .speed-tag {
      font-size: 10.5px;
      font-weight: 700;
      color: var(--text-3);
      padding: 2px 5px;
      border-radius: 4px;
      background: var(--surface-2);
    }

    /* Editorial Mode Info Card */
    .mode-info-card {
      width: 295px;
      background: rgba(226, 88, 34, 0.06);
      border: 1px solid rgba(226, 88, 34, 0.3);
      border-radius: 12px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .mode-info-title {
      font-size: 12px;
      font-weight: 700;
      color: #F97316;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .mode-info-desc {
      font-size: 11px;
      line-height: 1.45;
      color: var(--text-2);
    }

    /* Right Column: Tab Navigation & Workspaces */
    .work-col {
      padding: 20px 28px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 18px;
      background: var(--bg);
    }

    /* 4 Tabs Bar */
    .tabs-bar {
      display: flex;
      gap: 8px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 4px;
    }
    .tab-btn {
      flex: 1;
      height: 40px;
      border-radius: 9px;
      font-size: 13px;
      font-weight: 600;
      color: var(--text-2);
      background: transparent;
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: all 0.15s;
    }
    .tab-btn:hover {
      color: #fff;
      background: rgba(255, 255, 255, 0.04);
    }
    .tab-btn.is-active {
      background: var(--accent-gradient);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(226, 88, 34, 0.35);
    }

    /* Tab Panels */
    .tab-pane {
      display: none;
      flex-direction: column;
      gap: 16px;
    }
    .tab-pane.is-active {
      display: flex;
    }

    /* Card Panels */
    .panel-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r-lg);
      padding: 18px 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .panel-card-title {
      font-size: 13px;
      font-weight: 700;
      color: var(--text);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    /* Drop Video Card */
    .drop-box {
      border: 1.5px dashed var(--border-strong);
      border-radius: var(--r-lg);
      background: var(--surface);
      padding: 32px 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 10px;
      text-align: center;
      cursor: pointer;
      transition: all 0.15s;
    }
    .drop-box:hover {
      border-color: var(--accent);
      background: rgba(226, 88, 34, 0.04);
    }
    .drop-icon-box {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      background: rgba(226, 88, 34, 0.12);
      border: 1px solid rgba(226, 88, 34, 0.3);
      display: grid;
      place-items: center;
      color: #F97316;
      font-size: 20px;
    }
    .drop-title {
      font-size: 15px;
      font-weight: 700;
      color: var(--text);
    }
    .drop-sub {
      font-size: 12px;
      color: var(--text-3);
    }

    /* Demo Reel Banner */
    .demo-banner {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r-lg);
      padding: 14px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .demo-banner-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .demo-icon {
      width: 36px;
      height: 36px;
      border-radius: 9px;
      background: rgba(245, 158, 11, 0.15);
      color: #F59E0B;
      display: grid;
      place-items: center;
      font-size: 17px;
    }

    /* Word List Controls Row */
    .word-list-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12px;
      margin-top: 4px;
    }
    .word-list-title {
      font-weight: 700;
      color: var(--text);
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .word-list-hint {
      color: var(--text-3);
    }

    .word-config-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 8px 12px;
    }
    .btn-num-group {
      display: inline-flex;
      gap: 4px;
      background: var(--surface-2);
      padding: 2px;
      border-radius: 6px;
    }
    .btn-num {
      width: 28px;
      height: 26px;
      border-radius: 4px;
      background: transparent;
      border: none;
      color: var(--text-2);
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
    }
    .btn-num.is-active {
      background: var(--accent);
      color: #fff;
    }
    .btn-italic-star {
      background: rgba(226, 88, 34, 0.12);
      border: 1px solid rgba(226, 88, 34, 0.35);
      color: #F97316;
      border-radius: 6px;
      padding: 5px 10px;
      font-size: 11.5px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }
    .btn-italic-star:hover {
      background: rgba(226, 88, 34, 0.22);
    }

    /* Phrase Cards List */
    .phrase-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-height: 400px;
      overflow-y: auto;
    }
    .phrase-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .phrase-card-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
      color: var(--text-3);
    }
    .phrase-time-btn {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      background: transparent;
      border: none;
      color: var(--text-2);
      cursor: pointer;
      font-size: 11.5px;
      font-family: monospace;
    }
    .phrase-time-btn:hover {
      color: var(--text);
    }
    .word-chips-wrap {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
    }
    .word-chip {
      background: var(--surface-2);
      border: 1px solid var(--border-strong);
      border-radius: 7px;
      padding: 4px 9px;
      font-size: 13.5px;
      font-weight: 600;
      color: var(--text);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.12s;
    }
    .word-chip:hover {
      border-color: var(--accent);
    }
    .word-chip.is-emph {
      background: rgba(226, 88, 34, 0.15);
      border-color: #E25822;
      color: #F59E0B;
      font-family: 'Instrument Serif', Georgia, serif;
      font-style: italic;
      font-size: 16.5px;
      text-shadow: 0 0 10px rgba(245, 158, 11, 0.5);
    }
    .chip-star {
      font-size: 10px;
      opacity: 0.5;
    }
    .word-chip:hover .chip-star {
      opacity: 1;
      color: var(--accent);
    }

    /* Style Grid (Tab 2) */
    .style-grid-container {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
    }
    .style-card {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--surface);
      padding: 10px 10px 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      cursor: pointer;
      transition: all .15s;
      position: relative;
    }
    .style-card:hover {
      border-color: var(--border-strong);
      transform: translateY(-1px);
    }
    .style-card.is-active {
      border-color: var(--accent);
      box-shadow: 0 0 0 1.5px var(--accent), 0 8px 24px rgba(226, 88, 34, 0.2);
    }
    .style-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12.5px;
      font-weight: 700;
      color: var(--text);
      padding: 0 4px;
    }
    .hero-badge {
      font-size: 9.5px;
      font-weight: 800;
      color: #F97316;
      letter-spacing: 0.05em;
    }
    .style-preview-box {
      height: 72px;
      border-radius: 8px;
      background: radial-gradient(120% 140% at 50% 0%, #1E2536 0%, #0D1017 80%);
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      color: #fff;
    }
    .style-card-desc {
      font-size: 11px;
      color: var(--text-3);
      padding: 0 4px;
      line-height: 1.35;
    }

    /* Style Typography Previews */
    .s11 { font-family: 'Inter Caption', sans-serif; font-weight: 800; font-size: 15px; letter-spacing: -0.01em; transform: scaleY(1.08); display: inline-block; }
    .s11 em { font-family: 'Instrument Serif', Georgia, serif; font-style: italic; font-weight: 400; font-size: 21px; margin-left: 5px; color: #fff; text-shadow: 0 0 10px rgba(255,255,255,0.9), 0 0 20px rgba(255,255,255,0.6); }
    .s10 { font-family: 'Instrument Serif', Georgia, serif; font-size: 20px; font-style: italic; color: #fff; }
    .s1 { font-family: 'Montserrat', sans-serif; font-weight: 900; font-size: 16px; letter-spacing: 0.02em; }
    .s1 .y { color: #FFE600; text-shadow: 0 0 12px rgba(255,230,0,0.5); }
    .s2 { font-family: 'Poppins', sans-serif; font-weight: 800; font-size: 15px; }
    .s2 .c { color: #00E5FF; }
    .s3 { font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 800; font-size: 14px; }
    .s3 mark { background: #FFE600; color: #000; padding: 2px 6px; border-radius: 4px; font-weight: 900; }
    .s4 { font-family: 'Montserrat', sans-serif; font-weight: 900; font-size: 16px; }
    .s4 .r { color: #FF4154; text-shadow: 0 0 12px rgba(255,65,84,0.6); }
    .s5 { font-family: 'Inter Caption', sans-serif; font-weight: 700; font-size: 15px; }
    .s5 em { font-family: 'Instrument Serif', Georgia, serif; font-style: italic; font-weight: 400; font-size: 19px; }
    .s6 { font-family: 'Montserrat', sans-serif; font-weight: 900; font-size: 15px; }
    .s6 .b { color: #00AAFF; text-shadow: 0 0 14px rgba(0,170,255,0.6); }

    /* Segmented Options (Tab 3) */
    .seg-pill-row {
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: 1fr;
      padding: 3px;
      background: var(--surface-2);
      border-radius: 8px;
      gap: 3px;
    }
    .seg-pill-btn {
      padding: 7px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      color: var(--text-2);
      background: transparent;
      border: none;
      cursor: pointer;
      transition: all 0.15s;
    }
    .seg-pill-btn.is-active {
      background: var(--accent-gradient);
      color: #fff;
      box-shadow: 0 2px 8px rgba(226, 88, 34, 0.3);
    }

    .slider-track {
      width: 100%;
      accent-color: var(--accent);
      cursor: pointer;
    }

    /* Color Swatches (Tab 3) */
    .color-swatches-grid {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .color-circle {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      border: 1px solid var(--border-strong);
      cursor: pointer;
      display: grid;
      place-items: center;
      transition: transform 0.12s;
    }
    .color-circle:hover {
      transform: scale(1.08);
    }
    .color-circle.is-active::after {
      content: '';
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #000;
    }
    .color-circle.dark-circle.is-active::after {
      background: #fff;
    }

    .studio-select {
      width: 100%;
      height: 38px;
      background: var(--surface-2);
      border: 1px solid var(--border-strong);
      border-radius: 8px;
      color: var(--text);
      font-size: 13px;
      padding: 0 10px;
      outline: none;
      cursor: pointer;
      font-family: inherit;
      transition: border-color 0.15s;
    }
    .studio-select:focus {
      border-color: var(--accent);
    }

    /* Giant CTA Buttons */
    .btn-giant {
      height: 48px;
      border-radius: 10px;
      background: var(--accent-gradient);
      border: none;
      color: #fff;
      font-size: 14.5px;
      font-weight: 700;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      cursor: pointer;
      box-shadow: 0 4px 16px rgba(226, 88, 34, 0.4);
      transition: all 0.15s;
      width: 100%;
    }
    .btn-giant:hover {
      filter: brightness(1.08);
      transform: translateY(-1px);
    }
    .btn-giant:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none;
    }

    /* Next / Back Step Controls */
    .step-nav-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 10px;
      padding-top: 12px;
      border-top: 1px solid var(--border);
    }
    .btn-step {
      height: 38px;
      padding: 0 16px;
      border-radius: 8px;
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--text);
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s;
    }
    .btn-step:hover {
      border-color: var(--border-strong);
      background: var(--surface-2);
    }
    .btn-step-primary {
      background: var(--accent-gradient);
      border: none;
      color: #fff;
      box-shadow: 0 2px 10px rgba(226, 88, 34, 0.3);
    }
    .btn-step-primary:hover {
      filter: brightness(1.08);
    }

    /* Modals */
    .modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.75);
      backdrop-filter: blur(8px);
      z-index: 100;
      display: grid;
      place-items: center;
      padding: 20px;
    }
    .modal-window {
      width: 100%;
      max-width: 580px;
      background: var(--surface);
      border: 1px solid var(--border-strong);
      border-radius: var(--r-lg);
      padding: 22px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      max-height: 82vh;
      overflow-y: auto;
      box-shadow: 0 25px 60px -15px rgba(0,0,0,0.85);
    }
    .library-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--surface-2);
      gap: 12px;
    }

    @media (max-width: 1024px) {
      .studio-container { grid-template-columns: 1fr; height: auto; }
      .preview-col { border-right: none; border-bottom: 1px solid var(--border); }
    }
  </style>
</head>
<body>
  <!-- Topbar Header -->
  <header class="topbar">
    <div class="topbar-inner">
      <div class="brand-group">
        <div class="brand-mark">C</div>
        <div>
          <div class="brand-title">
            <span>Caption AI</span>
            <span class="badge-pill">EDITORIAL HYBRID</span>
          </div>
          <div class="brand-sub">Word-by-word animated captions with Groq Whisper & FFmpeg</div>
        </div>
      </div>

      <div class="top-actions">
        <button id="openKeysBtn" class="btn-top">
          🗝️ API Keys <span class="status-dot"></span>
        </button>
        <button id="topTranscribeBtn" class="btn-top" title="Transcribe current video with Groq / Local AI">
          ⚡ Transcribe with Groq
        </button>
        <button id="topRenderBtn" class="btn-top btn-top-orange">
          🎦 Render MP4
        </button>
        <button id="openLibraryBtn" class="btn-top" title="Open Backend Video Library & Disk Storage">
          📁 Library
        </button>
        <button id="themeToggle" class="btn-top" style="padding:0 8px;">
          ☀️
        </button>
      </div>
    </div>
  </header>

  <!-- Studio Main -->
  <main class="studio-container">
    <!-- Left Column: Live Preview & Player -->
    <section class="preview-col">
      <div class="preview-header">
        <span>LIVE PREVIEW</span>
        <span id="canvasDims">720×1280 • 12.0s</span>
      </div>

      <!-- Phone Canvas -->
      <div class="phone-canvas" id="stage">
        <span class="canvas-badge-left">9:16 Vertical</span>
        <span class="canvas-badge-right">Live Canvas</span>

        <!-- Video element -->
        <video id="userVideo" playsinline loop hidden></video>

        <!-- Big Centered Play Button Overlay -->
        <div id="playOverlayCircle" class="play-overlay-circle">
          <div class="circle-play-btn">▶</div>
        </div>

        <!-- Live Caption Overlay -->
        <div id="liveCaptionOverlay" class="live-caption-overlay"></div>

        <!-- Position Drag Handle -->
        <div id="dragHandleOverlay" class="drag-handle-overlay">
          <div id="dragLine" class="drag-line">
            <div id="dragPill" class="drag-pill">80%</div>
          </div>
        </div>
      </div>

      <!-- Player Controls Dock -->
      <div class="player-dock">
        <div class="player-progress-bar" id="playerProgressBar">
          <div class="player-progress-fill" id="playerProgressFill">
            <div class="player-progress-thumb"></div>
          </div>
        </div>
        <div class="player-dock-row">
          <div style="display:flex; align-items:center; gap:8px;">
            <button id="playBtn" class="player-mini-btn" title="Play / Pause">▶</button>
            <button id="replayBtn" class="player-mini-btn" title="Replay from 0:00">↺</button>
            <span id="timeText" style="font-family:monospace; color:var(--text-2); font-size:11px;">0.0s / 12.0s</span>
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="speed-tag">1x</span>
            <button id="muteBtn" class="player-mini-btn" title="Mute / Unmute">🔊</button>
          </div>
        </div>
      </div>

      <!-- Editorial Hybrid Mode Active Banner -->
      <div class="mode-info-card">
        <div class="mode-info-title">
          <span>✦</span> Editorial Hybrid Mode Active
        </div>
        <div class="mode-info-desc">
          Regular words are formatted in <strong>Inter ExtraBold (800)</strong> with vertical scale (1.08). Emphasis words glow in <strong>Instrument Serif Italic</strong> with soft aura. Click word chips in the editor to switch emphasis anytime!
        </div>
      </div>
    </section>

    <!-- Right Column: Tabs & Step Workspaces -->
    <section class="work-col">
      <!-- 4 Tab Buttons -->
      <nav class="tabs-bar">
        <button class="tab-btn is-active" data-tab="tab-transcript">
          <span>📑</span> Words & Transcript
        </button>
        <button class="tab-btn" data-tab="tab-styles">
          <span>🎨</span> Caption Style
        </button>
        <button class="tab-btn" data-tab="tab-position">
          <span>🎛️</span> Position & Size
        </button>
        <button class="tab-btn" data-tab="tab-render">
          <span>📥</span> Render & Export
        </button>
      </nav>

      <!-- TAB 1: Words & Transcript -->
      <div id="tab-transcript" class="tab-pane is-active">
        <!-- Dropzone -->
        <div class="drop-box" id="dropZone">
          <div class="drop-icon-box">📤</div>
          <div class="drop-title" id="dropTitle">Drop video here or click to browse</div>
          <div class="drop-sub">Supports MP4, MOV, WEBM (Vertical 9:16 reels, shorts, or horizontal)</div>
          <input type="file" id="fileInput" accept="video/*,.mp4,.mov,.webm,.mkv" style="display:none;" />
        </div>

        <!-- Wrong Video Delete Action Bar -->
        <div id="activeVideoBar" style="display:none; justify-content:space-between; align-items:center; padding:10px 14px; background:var(--surface); border:1px solid var(--border); border-radius:10px;">
          <div>
            <div style="font-size:11px; color:var(--text-3);">Active Video:</div>
            <div id="activeVideoName" style="font-size:12.5px; font-weight:600;"></div>
          </div>
          <button id="deleteActiveBtn" class="btn-top" style="color:var(--danger); border-color:var(--danger);">
            🗑️ Delete / Wrong Video
          </button>
        </div>

        <!-- No Video on Hand? Demo Reel Banner -->
        <div class="demo-banner">
          <div class="demo-banner-left">
            <div class="demo-icon">🎬</div>
            <div>
              <div style="font-weight:700; font-size:13px;">No video on hand?</div>
              <div style="font-size:11.5px; color:var(--text-3); margin-top:1px;">Load our sample 9:16 reel with Groq Whisper audio</div>
            </div>
          </div>
          <button id="tryDemoBtn" class="btn-top btn-top-orange">
            🪄 Try Demo Reel
          </button>
        </div>

        <!-- Editable Word List Header & Controls -->
        <div class="word-list-header">
          <span class="word-list-title" id="wordListTitle">EDITABLE WORD LIST (14 WORDS)</span>
          <span class="word-list-hint">Click chip to edit typo • Click ✦ to toggle Instrument Serif Italic</span>
        </div>

        <div class="word-config-row">
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:12px; color:var(--text-2);">Words per phrase:</span>
            <div class="btn-num-group" id="wordsPerPhraseGroup">
              <button class="btn-num" data-n="2">2</button>
              <button class="btn-num is-active" data-n="3">3</button>
              <button class="btn-num" data-n="4">4</button>
            </div>
          </div>
          <button id="lastWordItalicBtn" class="btn-italic-star">
            ✨ Last word italic
          </button>
        </div>

        <!-- Editable Phrase Cards Container -->
        <div class="phrase-list" id="phraseListContainer"></div>

        <!-- Step Navigation -->
        <div class="step-nav-row">
          <span></span>
          <button class="btn-step btn-step-primary" onclick="switchTab('tab-styles')">
            Next: Caption Style →
          </button>
        </div>
      </div>

      <!-- TAB 2: Caption Style -->
      <div id="tab-styles" class="tab-pane">
        <div class="word-list-header">
          <span class="word-list-title">CAPTION TYPOGRAPHY STYLE</span>
          <span class="word-list-hint" style="color:#F97316;">✨ 8 Styles Ready</span>
        </div>

        <div class="style-grid-container" id="styleGrid"></div>

        <!-- Step Navigation -->
        <div class="step-nav-row">
          <button class="btn-step" onclick="switchTab('tab-transcript')">
            ← Back: Transcript
          </button>
          <button class="btn-step btn-step-primary" onclick="switchTab('tab-position')">
            Next: Position & Size →
          </button>
        </div>
      </div>

      <!-- TAB 3: Position & Size -->
      <div id="tab-position" class="tab-pane">
        <!-- Vertical Position Card -->
        <div class="panel-card">
          <div class="panel-card-title">
            <span style="display:flex; align-items:center; gap:6px;">↕ Vertical Position</span>
            <span id="posValueText" style="font-size:12px; color:var(--text-3); font-weight:500;">80% from top</span>
          </div>
          <div class="seg-pill-row">
            <button class="seg-pill-btn" data-pos="25">Top (25%)</button>
            <button class="seg-pill-btn" data-pos="50">Middle (50%)</button>
            <button class="seg-pill-btn is-active" data-pos="80">Bottom (80%)</button>
          </div>
          <input type="range" class="slider-track" id="posSlider" min="15" max="88" value="80" />
        </div>

        <!-- Caption Font Size Card -->
        <div class="panel-card">
          <div class="panel-card-title">
            <span style="display:flex; align-items:center; gap:6px;">T Caption Font Size</span>
            <span id="sizeValueText" style="font-size:12px; color:var(--text-3); font-weight:500;">76px</span>
          </div>
          <div class="seg-pill-row">
            <button class="seg-pill-btn" data-sz="56">Compact</button>
            <button class="seg-pill-btn is-active" data-sz="76">Standard</button>
            <button class="seg-pill-btn" data-sz="98">Impact</button>
          </div>
          <input type="range" class="slider-track" id="sizeSlider" min="40" max="120" value="76" />
        </div>

        <!-- Typography & Font Format Card -->
        <div class="panel-card">
          <div class="panel-card-title">
            <span style="display:flex; align-items:center; gap:6px;">🔤 Font Format & Typography</span>
            <span id="fontFormatBadge" class="badge-pill">Style Default</span>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:8px;">
            <div>
              <label style="font-size:11px; color:var(--text-3); display:block; margin-bottom:4px; font-weight:600;">BASE FONT</label>
              <select id="baseFontSelect" class="studio-select">
                <option value="auto">Auto (From Style)</option>
                <option value="Inter Caption">Inter ExtraBold</option>
                <option value="SF Pro Display">SF Pro Display</option>
                <option value="Montserrat">Montserrat ExtraBold</option>
                <option value="Poppins">Poppins ExtraBold</option>
                <option value="PP Editorial New">PP Editorial New</option>
                <option value="Plus Jakarta Sans">Plus Jakarta Sans</option>
              </select>
            </div>
            <div>
              <label style="font-size:11px; color:var(--text-3); display:block; margin-bottom:4px; font-weight:600;">TEXT CASING</label>
              <select id="casingSelect" class="studio-select">
                <option value="default">Original (Speech)</option>
                <option value="upper">UPPERCASE (ALL CAPS)</option>
                <option value="title">Title Case</option>
                <option value="lower">lowercase</option>
              </select>
            </div>
          </div>

          <div style="margin-top:10px;">
            <label style="font-size:11px; color:var(--text-3); display:block; margin-bottom:4px; font-weight:600;">EMPHASIS FONT (✦ WORDS)</label>
            <select id="emphFontSelect" class="studio-select">
              <option value="auto">Auto (Instrument Serif Italic)</option>
              <option value="Instrument Serif">Instrument Serif (Italic Glow)</option>
              <option value="Alex Brush">Alex Brush (Calligraphy Script)</option>
              <option value="same">Same as Base Font (Color Glow Only)</option>
            </select>
          </div>
        </div>

        <!-- Highlight Color Card -->
        <div class="panel-card">
          <div class="panel-card-title">
            <span style="display:flex; align-items:center; gap:6px;">🎨 Active Word Highlight Color</span>
            <span id="colorHexText" style="font-size:12px; color:var(--text-3); font-family:monospace;">#FFFFFF</span>
          </div>
          <div class="color-swatches-grid" id="colorSwatches">
            <button class="color-circle is-active" style="background:#FFFFFF;" data-c="#FFFFFF"></button>
            <button class="color-circle" style="background:#C47D4C;" data-c="#C47D4C"></button>
            <button class="color-circle" style="background:#FACC15;" data-c="#FACC15"></button>
            <button class="color-circle" style="background:#06B6D4;" data-c="#06B6D4"></button>
            <button class="color-circle" style="background:#84CC16;" data-c="#84CC16"></button>
            <button class="color-circle" style="background:#F43F5E;" data-c="#F43F5E"></button>
            <button class="color-circle" style="background:#A855F7;" data-c="#A855F7"></button>
            <button class="color-circle" style="background:#FB7185;" data-c="#FB7185"></button>
            <label class="color-circle dark-circle" style="background:var(--surface-2);color:var(--text);font-size:14px;cursor:pointer;">
              +
              <input type="color" id="customColorInput" style="display:none;" value="#FFFFFF" />
            </label>
          </div>
        </div>

        <!-- Step Navigation -->
        <div class="step-nav-row">
          <button class="btn-step" onclick="switchTab('tab-styles')">
            ← Back: Caption Style
          </button>
          <button class="btn-step btn-step-primary" onclick="switchTab('tab-render')">
            Next: Render & Export →
          </button>
        </div>
      </div>

      <!-- TAB 4: Render & Export -->
      <div id="tab-render" class="tab-pane">
        <!-- Render Card -->
        <div class="panel-card">
          <div class="panel-card-title">
            <span style="display:flex; align-items:center; gap:8px;">🎞️ Render & Export Captioned Video</span>
            <span class="badge-pill" id="renderSourceBadge">Source: sample-video.mp4 • 12.0s</span>
          </div>
          <p style="font-size:12.5px; color:var(--text-3); line-height:1.45;">
            Burns typography directly into full MP4 video frames with FFmpeg & libass. Preserves the exact SF Pro / Inter Bold and glowing Instrument Serif Italic styling.
          </p>

          <button id="renderCtaBtn" class="btn-giant">
            ✨ Render Full Captioned Video (FFmpeg)
          </button>

          <!-- Render Result Downloads Box -->
          <div id="renderResultBox" style="display:none; flex-direction:column; gap:10px; margin-top:8px; padding-top:14px; border-top:1px solid var(--border);">
            <div style="font-weight:700; font-size:14px; color:#10B981; display:flex; align-items:center; gap:6px;">
              <span>🎉</span> Video Render Complete!
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
              <a class="btn-top btn-top-orange" style="grid-column:1 / -1; height:42px; font-size:13px; justify-content:center;" id="dlMp4Btn" download>
                ⬇️ Download MP4 Video
              </a>
              <a class="btn-top" style="justify-content:center;" id="dlSrtBtn" download>📄 SRT Subtitles</a>
              <a class="btn-top" style="justify-content:center;" id="dlAssBtn" download>🎨 ASS Subtitles</a>
            </div>
          </div>
        </div>

        <!-- Step Navigation -->
        <div class="step-nav-row">
          <button class="btn-step" onclick="switchTab('tab-position')">
            ← Back: Position & Size
          </button>
          <span></span>
        </div>
      </div>
    </section>
  </main>

  <!-- API Keys Modal -->
  <div id="keysModal" class="modal-backdrop" style="display:none;">
    <div class="modal-window">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h3 style="font-size:16px; font-weight:700;">🗝️ Groq Whisper API Settings</h3>
        <button id="closeKeysBtn" class="player-mini-btn" style="font-size:16px;">✕</button>
      </div>
      <p style="font-size:12px; color:var(--text-3);">
        Enter your free Groq API Key to enable instant cloud speech transcription (&lt;1s for 60s video). If omitted, Captionizer uses offline local faster-whisper.
      </p>
      <div>
        <label style="font-size:11px; color:var(--text-3); margin-bottom:4px; display:block;">Groq API Key (gsk_...)</label>
        <input type="password" id="groqKeyInput" placeholder="gsk_..." style="width:100%;height:38px;padding:0 12px;background:var(--surface-2);border:1px solid var(--border-strong);border-radius:8px;color:var(--text);outline:none;" />
      </div>
      <div style="display:flex; justify-content:flex-end; gap:8px;">
        <button id="clearKeyBtn" class="btn-top">Clear</button>
        <button id="saveKeyBtn" class="btn-top btn-top-orange">Save API Key</button>
      </div>
    </div>
  </div>

  <!-- Video Library Modal -->
  <div id="libraryModal" class="modal-backdrop" style="display:none;">
    <div class="modal-window">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <h3 style="font-size:16px; font-weight:700;">📁 Video Library & Storage</h3>
          <p id="libStorageText" style="font-size:11.5px; color:var(--text-3); margin-top:2px;">Loading storage usage...</p>
        </div>
        <button id="closeLibraryBtn" class="player-mini-btn" style="font-size:16px;">✕</button>
      </div>

      <div style="display:flex; justify-content:flex-end;">
        <button id="clearAllDiskBtn" class="btn-top" style="color:var(--danger); border-color:var(--danger);">
          🧹 Clear All Files from Disk
        </button>
      </div>

      <div id="libraryListContainer" style="display:flex; flex-direction:column; gap:8px;"></div>
    </div>
  </div>

  <script>
    const state = {
      activeTab: "tab-transcript",
      style: "style_11",
      customFont: "auto",
      casing: "default",
      emphasisFont: "auto",
      position: 80,
      size: 76,
      accent: "#FFFFFF",
      wordsPerPhrase: 3,
      task: null,
      phrases: [],
      styles: [],
      isRendered: false
    };

    const userVideo = document.getElementById("userVideo");
    const playOverlayCircle = document.getElementById("playOverlayCircle");
    const liveCaptionOverlay = document.getElementById("liveCaptionOverlay");
    const playerProgressFill = document.getElementById("playerProgressFill");
    const playerProgressBar = document.getElementById("playerProgressBar");
    const timeText = document.getElementById("timeText");
    const playBtn = document.getElementById("playBtn");
    const replayBtn = document.getElementById("replayBtn");
    const muteBtn = document.getElementById("muteBtn");

    // Tab Navigation
    function switchTab(tabId) {
      state.activeTab = tabId;
      document.querySelectorAll(".tab-btn").forEach(b => {
        b.classList.toggle("is-active", b.dataset.tab === tabId);
      });
      document.querySelectorAll(".tab-pane").forEach(p => {
        p.classList.toggle("is-active", p.id === tabId);
      });
    }

    document.querySelectorAll(".tab-btn").forEach(btn => {
      btn.onclick = () => switchTab(btn.dataset.tab);
    });

    // Load available styles
    fetch("/api/styles")
      .then(r => r.json())
      .then(data => {
        state.styles = data.styles;
        renderStylesGrid();
      })
      .catch(e => console.error("Styles error:", e));

    function renderStylesGrid() {
      const grid = document.getElementById("styleGrid");
      grid.innerHTML = "";
      state.styles.forEach(s => {
        const div = document.createElement("div");
        div.className = `style-card ${s.id === state.style ? 'is-active' : ''}`;
        div.innerHTML = `
          <div class="style-card-header">
            <span>${s.name}</span>
            ${s.featured ? '<span class="hero-badge">★ FEATURED HERO</span>' : ''}
          </div>
          <div class="style-preview-box">${s.sample_html}</div>
          <div class="style-card-desc">${s.tagline}</div>
        `;
        div.onclick = () => {
          state.style = s.id;
          document.querySelectorAll(".style-card").forEach(c => c.classList.remove("is-active"));
          div.classList.add("is-active");
          if (s.accent) {
            setColor(s.accent);
          }
          const badge = document.getElementById("fontFormatBadge");
          if (badge) badge.textContent = s.name;
          updateLiveOverlay();
        };
        grid.appendChild(div);
      });
    }

    // Video Player Functions
    function togglePlay() {
      if (userVideo.paused) {
        userVideo.play().catch(() => {});
        playBtn.textContent = "⏸";
        playOverlayCircle.style.display = "none";
      } else {
        userVideo.pause();
        playBtn.textContent = "▶";
        playOverlayCircle.style.display = "flex";
      }
    }

    playBtn.onclick = togglePlay;
    playOverlayCircle.onclick = togglePlay;

    replayBtn.onclick = () => {
      userVideo.currentTime = 0;
      userVideo.play().catch(() => {});
      playBtn.textContent = "⏸";
      playOverlayCircle.style.display = "none";
    };

    muteBtn.onclick = () => {
      userVideo.muted = !userVideo.muted;
      muteBtn.textContent = userVideo.muted ? "🔇" : "🔊";
    };

    playerProgressBar.onclick = (e) => {
      const rect = playerProgressBar.getBoundingClientRect();
      const pct = (e.clientX - rect.left) / rect.width;
      if (userVideo.duration) {
        userVideo.currentTime = pct * userVideo.duration;
      }
    };

    userVideo.ontimeupdate = () => {
      if (userVideo.duration) {
        const pct = (userVideo.currentTime / userVideo.duration) * 100;
        playerProgressFill.style.width = pct + "%";
        timeText.textContent = `${userVideo.currentTime.toFixed(1)}s / ${userVideo.duration.toFixed(1)}s`;
      }
      updateLiveOverlay();
    };

    userVideo.onplay = () => {
      playBtn.textContent = "⏸";
      playOverlayCircle.style.display = "none";
    };
    userVideo.onpause = () => {
      playBtn.textContent = "▶";
      playOverlayCircle.style.display = "flex";
    };

    // Live Caption Highlight
    function updateLiveOverlay() {
      if (state.isRendered) {
        liveCaptionOverlay.style.display = "none";
        liveCaptionOverlay.innerHTML = "";
        return;
      }
      if (!state.phrases || !state.phrases.length) {
        liveCaptionOverlay.innerHTML = "";
        return;
      }

      const t = userVideo.currentTime;
      let activePhrase = null;
      let activeWordId = null;

      for (const p of state.phrases) {
        if (t >= p.start && t <= p.end) {
          activePhrase = p;
          break;
        }
      }

      if (!activePhrase) {
        for (let i = 0; i < state.phrases.length; i++) {
          if (t < state.phrases[i].start) {
            activePhrase = (i > 0) ? state.phrases[i - 1] : state.phrases[0];
            break;
          }
        }
      }

      if (!activePhrase) {
        liveCaptionOverlay.innerHTML = "";
        return;
      }

      for (const w of activePhrase.words) {
        if (t >= w.start && t <= w.end) {
          activeWordId = w.id;
          break;
        }
      }

      const curStyle = state.styles.find(s => s.id === state.style) || state.styles[0] || {};
      const effAccent = (state.accent === "#FFFFFF" && curStyle.accent && curStyle.accent !== "#FFFFFF") ? curStyle.accent : state.accent;
      const baseFs = Math.round(state.size * 0.42);
      const emphFs = Math.round(state.size * 0.58);
      
      const effBaseFont = (state.customFont && state.customFont !== "auto") ? state.customFont : (curStyle.font_base || 'Inter Caption');
      const effEmphFont = (state.emphasisFont === 'same') ? effBaseFont : ((state.emphasisFont && state.emphasisFont !== "auto") ? state.emphasisFont : (curStyle.font_emphasis || 'Instrument Serif'));
      
      // Determine casing
      const isStyleAllCaps = ['style_1', 'style_4', 'style_6'].includes(state.style);
      const effCasing = (state.casing && state.casing !== "default") ? state.casing : (isStyleAllCaps ? 'upper' : 'default');

      liveCaptionOverlay.style.top = state.position + "%";
      liveCaptionOverlay.style.display = "flex";

      liveCaptionOverlay.innerHTML = activePhrase.words.map(w => {
        const isCurr = (w.id === activeWordId);
        const isEmph = Boolean(w.emphasis);
        
        let wordText = w.text;
        if (effCasing === "upper") {
          wordText = wordText.toUpperCase();
        } else if (effCasing === "lower") {
          wordText = wordText.toLowerCase();
        } else if (effCasing === "title") {
          wordText = wordText.replace(/\\w\\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase());
        }

        // 1. Editorial Hybrid
        if (state.style === "style_11") {
          if (isEmph) {
            return `<span style="font-family:'${effEmphFont}', Georgia, serif; font-style:italic; font-weight:400; font-size:${emphFs}px; color:${isCurr ? effAccent : '#fff'}; opacity:${isCurr ? 1 : 0.65}; text-shadow:${isCurr ? `0 0 16px ${effAccent}, 0 0 32px ${effAccent}, 0 2px 8px rgba(0,0,0,0.6)` : `0 0 8px ${effAccent}`}; transform:scaleY(1.0);">${wordText}</span>`;
          }
          return `<span style="font-family:'${effBaseFont}', -apple-system, sans-serif; font-weight:800; font-size:${baseFs}px; color:${isCurr ? effAccent : '#fff'}; opacity:${isCurr ? 1 : 0.45}; transform:scaleY(1.08); text-shadow:0 3px 14px rgba(0,0,0,0.6);">${wordText}</span>`;
        }

        // 2. Editorial Serif
        if (state.style === "style_10") {
          return `<span style="font-family:'${effEmphFont}', Georgia, serif; font-style:italic; font-weight:400; font-size:${emphFs}px; color:${isCurr ? effAccent : '#fff'}; opacity:${isCurr ? 1 : 0.55}; text-shadow:0 0 14px ${isCurr ? effAccent : 'rgba(255,255,255,0.7)'};">${wordText}</span>`;
        }

        // 3. Bold Yellow
        if (state.style === "style_1") {
          const color = (isCurr || isEmph) ? effAccent : '#FFFFFF';
          return `<span style="font-family:'${effBaseFont}', sans-serif; font-weight:900; font-size:${baseFs + 2}px; color:${color}; -webkit-text-stroke:2px #000; text-shadow:0 3px 6px #000; opacity:${isCurr ? 1 : 0.6};">${wordText}</span>`;
        }

        // 4. Cyan Pop
        if (state.style === "style_2") {
          const color = (isCurr || isEmph) ? effAccent : '#FFFFFF';
          return `<span style="font-family:'${effBaseFont}', sans-serif; font-weight:800; font-size:${baseFs}px; color:${color}; -webkit-text-stroke:1.6px #000; text-shadow:${isCurr ? `0 0 16px ${effAccent}, 0 2px 6px #000` : '0 2px 6px #000'}; opacity:${isCurr ? 1 : 0.55};">${wordText}</span>`;
        }

        // 5. Yellow Tag
        if (state.style === "style_3") {
          if (isCurr || isEmph) {
            return `<mark style="background:${effAccent}; color:#000; font-family:'${effBaseFont}', sans-serif; font-weight:900; font-size:${baseFs}px; padding:2px 8px; border-radius:6px; box-shadow:0 3px 10px rgba(0,0,0,0.5);">${wordText}</mark>`;
          }
          return `<span style="font-family:'${effBaseFont}', sans-serif; font-weight:800; font-size:${baseFs}px; color:#fff; text-shadow:0 2px 6px rgba(0,0,0,0.7); opacity:0.6;">${wordText}</span>`;
        }

        // 6. Red Impact
        if (state.style === "style_4") {
          const color = (isCurr || isEmph) ? effAccent : '#FFFFFF';
          return `<span style="font-family:'${effBaseFont}', sans-serif; font-weight:900; font-size:${baseFs + 2}px; color:${color}; -webkit-text-stroke:1.8px #000; text-shadow:${isCurr ? `0 0 18px ${effAccent}, 0 2px 8px #000` : '0 2px 8px #000'}; opacity:${isCurr ? 1 : 0.6};">${wordText}</span>`;
        }

        // 7. Minimalist Mono
        if (state.style === "style_5") {
          if (isEmph && effEmphFont !== effBaseFont) {
            return `<span style="font-family:'${effEmphFont}', serif; font-style:italic; font-size:${emphFs - 4}px; color:${isCurr ? effAccent : '#fff'}; opacity:${isCurr ? 1 : 0.55};">${wordText}</span>`;
          }
          return `<span style="font-family:'${effBaseFont}', sans-serif; font-weight:700; font-size:${baseFs}px; color:${isCurr ? effAccent : '#fff'}; opacity:${isCurr ? 1 : 0.45};">${wordText}</span>`;
        }

        // 8. Blue Glow
        if (state.style === "style_6") {
          const color = (isCurr || isEmph) ? effAccent : '#FFFFFF';
          return `<span style="font-family:'${effBaseFont}', sans-serif; font-weight:900; font-size:${baseFs + 1}px; color:${color}; -webkit-text-stroke:1.8px #000; text-shadow:${isCurr ? `0 0 20px ${effAccent}, 0 2px 8px #000` : '0 2px 8px #000'}; opacity:${isCurr ? 1 : 0.6};">${wordText}</span>`;
        }

        // Default fallback
        return `<span style="font-family:'${effBaseFont}', sans-serif; font-weight:800; font-size:${baseFs}px; color:${isCurr ? effAccent : '#fff'}; opacity:${isCurr ? 1 : 0.45}; text-shadow:0 2px 8px rgba(0,0,0,0.7);">${wordText}</span>`;
      }).join(" ");
    }

    // Typography & Font Format Controls
    const baseFontSelect = document.getElementById("baseFontSelect");
    const casingSelect = document.getElementById("casingSelect");
    const emphFontSelect = document.getElementById("emphFontSelect");

    if (baseFontSelect) {
      baseFontSelect.onchange = (e) => {
        state.customFont = e.target.value;
        updateLiveOverlay();
      };
    }

    if (casingSelect) {
      casingSelect.onchange = (e) => {
        state.casing = e.target.value;
        updateLiveOverlay();
      };
    }

    if (emphFontSelect) {
      emphFontSelect.onchange = (e) => {
        state.emphasisFont = e.target.value;
        updateLiveOverlay();
      };
    }

    // Drag to reposition
    const dragHandle = document.getElementById("dragHandleOverlay");
    let isDragging = false;
    dragHandle.onmousedown = (e) => { isDragging = true; updatePosFromDrag(e); };
    window.onmousemove = (e) => { if (isDragging) updatePosFromDrag(e); };
    window.onmouseup = () => { isDragging = false; };

    function updatePosFromDrag(e) {
      const stage = document.getElementById("stage");
      const rect = stage.getBoundingClientRect();
      const pct = Math.round(((e.clientY - rect.top) / rect.height) * 100);
      setPos(Math.max(15, Math.min(88, pct)));
    }

    function setPos(v) {
      state.position = v;
      document.getElementById("posSlider").value = v;
      document.getElementById("posValueText").textContent = v + "% from top";
      document.getElementById("dragLine").style.top = v + "%";
      document.getElementById("dragPill").textContent = v + "%";
      document.querySelectorAll(".seg-pill-btn[data-pos]").forEach(b => {
        b.classList.toggle("is-active", Number(b.dataset.pos) === v);
      });
      updateLiveOverlay();
    }

    document.getElementById("posSlider").oninput = (e) => setPos(Number(e.target.value));
    document.querySelectorAll(".seg-pill-btn[data-pos]").forEach(btn => {
      btn.onclick = () => setPos(Number(btn.dataset.pos));
    });

    // Font Size Controls
    function setSize(v) {
      state.size = v;
      document.getElementById("sizeSlider").value = v;
      document.getElementById("sizeValueText").textContent = v + "px";
      document.querySelectorAll(".seg-pill-btn[data-sz]").forEach(b => {
        b.classList.toggle("is-active", Number(b.dataset.sz) === v);
      });
      updateLiveOverlay();
    }

    document.getElementById("sizeSlider").oninput = (e) => setSize(Number(e.target.value));
    document.querySelectorAll(".seg-pill-btn[data-sz]").forEach(btn => {
      btn.onclick = () => setSize(Number(btn.dataset.sz));
    });

    // Highlight Color Controls
    function setColor(hex) {
      state.accent = hex;
      document.getElementById("colorHexText").textContent = hex;
      document.querySelectorAll(".color-circle[data-c]").forEach(c => {
        c.classList.toggle("is-active", c.dataset.c.toLowerCase() === hex.toLowerCase());
      });
      updateLiveOverlay();
    }

    document.querySelectorAll(".color-circle[data-c]").forEach(btn => {
      btn.onclick = () => setColor(btn.dataset.c);
    });

    document.getElementById("customColorInput").onchange = (e) => {
      setColor(e.target.value.toUpperCase());
    };

    // Words per phrase selector (2, 3, 4)
    document.querySelectorAll("#wordsPerPhraseGroup button").forEach(btn => {
      btn.onclick = () => {
        document.querySelectorAll("#wordsPerPhraseGroup button").forEach(b => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        state.wordsPerPhrase = Number(btn.dataset.n);
        if (state.task) {
          triggerTranscribe();
        }
      };
    });

    // Last word italic toggle
    document.getElementById("lastWordItalicBtn").onclick = () => {
      state.phrases.forEach(p => {
        p.words.forEach((w, idx) => {
          w.emphasis = (idx === p.words.length - 1);
        });
      });
      renderWordList();
      updateLiveOverlay();
    };

    // Render Editable Phrase Cards
    function renderWordList() {
      const container = document.getElementById("phraseListContainer");
      container.innerHTML = "";
      let totalWords = 0;

      state.phrases.forEach((phrase, pIdx) => {
        const card = document.createElement("div");
        card.className = "phrase-card";

        const top = document.createElement("div");
        top.className = "phrase-card-top";
        top.innerHTML = `
          <button class="phrase-time-btn" onclick="playPhrase(${phrase.start})">
            ▶ ${phrase.start.toFixed(2)}s – ${phrase.end.toFixed(2)}s
          </button>
          <span>Phrase ${pIdx + 1}</span>
        `;
        card.appendChild(top);

        const chipsWrap = document.createElement("div");
        chipsWrap.className = "word-chips-wrap";

        phrase.words.forEach((w) => {
          totalWords++;
          const chip = document.createElement("div");
          chip.className = `word-chip ${w.emphasis ? 'is-emph' : ''}`;
          chip.innerHTML = `<span>${w.text}</span> <span class="chip-star">✦</span>`;

          // Click text to edit typo
          chip.querySelector("span").onclick = (e) => {
            e.stopPropagation();
            const next = prompt("Edit word text:", w.text);
            if (next !== null && next.trim()) {
              w.text = next.trim();
              chip.querySelector("span").textContent = w.text;
              phrase.text = phrase.words.map(x => x.text).join(" ");
              updateLiveOverlay();
            }
          };

          // Click ✦ to toggle Instrument Serif Italic emphasis
          chip.querySelector(".chip-star").onclick = (e) => {
            e.stopPropagation();
            w.emphasis = !w.emphasis;
            chip.classList.toggle("is-emph", w.emphasis);
            updateLiveOverlay();
          };

          chipsWrap.appendChild(chip);
        });

        card.appendChild(chipsWrap);
        container.appendChild(card);
      });

      document.getElementById("wordListTitle").textContent = `EDITABLE WORD LIST (${totalWords} WORDS)`;
    }

    window.playPhrase = (startTime) => {
      userVideo.currentTime = startTime;
      userVideo.play().catch(() => {});
    };

    // Video Upload Handlers
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");
    dropZone.onclick = () => fileInput.click();
    dropZone.ondragover = (e) => e.preventDefault();
    dropZone.ondrop = (e) => {
      e.preventDefault();
      if (e.dataTransfer.files.length) handleUpload(e.dataTransfer.files[0]);
    };
    fileInput.onchange = (e) => {
      if (e.target.files.length) handleUpload(e.target.files[0]);
    };

    async function handleUpload(file) {
      document.getElementById("dropTitle").textContent = "Uploading " + file.name + "...";
      const fd = new FormData();
      fd.append("file", file);
      try {
        const res = await fetch("/api/upload", { method: "POST", body: fd });
        if (!res.ok) throw new Error("Upload failed");
        const data = await res.json();
        setupVideoData(data);
        // Automatically start transcribing
        triggerTranscribe();
      } catch (err) {
        alert("Upload error: " + err.message);
        document.getElementById("dropTitle").textContent = "Drop video here or click to browse";
      }
    }

    function setupVideoData(data) {
      state.task = data;
      state.isRendered = false;
      document.getElementById("dropTitle").textContent = "Change Video";
      document.getElementById("activeVideoBar").style.display = "flex";
      document.getElementById("activeVideoName").textContent = data.filename;
      document.getElementById("canvasDims").textContent = `${data.width}×${data.height} • ${data.duration.toFixed(1)}s`;
      document.getElementById("renderSourceBadge").textContent = `Source: ${data.filename} • ${data.duration.toFixed(1)}s`;

      userVideo.src = data.video_url;
      userVideo.hidden = false;
      userVideo.currentTime = 0;
      playOverlayCircle.style.display = "flex";
      timeText.textContent = `0.0s / ${data.duration.toFixed(1)}s`;
    }

    // Try Demo Reel
    document.getElementById("tryDemoBtn").onclick = async () => {
      try {
        const res = await fetch("/api/demo");
        const data = await res.json();
        setupVideoData(data);
        state.phrases = data.phrases;
        renderWordList();
        updateLiveOverlay();
      } catch (err) {
        alert("Failed to load demo reel: " + err.message);
      }
    };

    // Delete Active Video
    document.getElementById("deleteActiveBtn").onclick = async () => {
      if (!state.task) return;
      if (!confirm("Permanently delete this video from disk and start over?")) return;
      try {
        await fetch(`/api/videos/${state.task.task_id}`, { method: "DELETE" });
        state.task = null;
        state.phrases = [];
        state.isRendered = false;
        fileInput.value = "";
        userVideo.src = "";
        userVideo.hidden = true;
        document.getElementById("activeVideoBar").style.display = "none";
        document.getElementById("dropTitle").textContent = "Drop video here or click to browse";
        document.getElementById("phraseListContainer").innerHTML = "";
        document.getElementById("wordListTitle").textContent = "EDITABLE WORD LIST (0 WORDS)";
        document.getElementById("renderResultBox").style.display = "none";
        liveCaptionOverlay.innerHTML = "";
      } catch (err) {
        alert("Delete failed: " + err.message);
      }
    };

    // Transcribe
    async function triggerTranscribe() {
      if (!state.task) return;
      const topBtn = document.getElementById("topTranscribeBtn");
      topBtn.textContent = "⏳ Transcribing...";
      topBtn.disabled = true;

      try {
        const res = await fetch("/api/transcribe", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            task_id: state.task.task_id,
            words_per_phrase: state.wordsPerPhrase
          })
        });
        const data = await res.json();
        state.phrases = data.phrases;
        renderWordList();
        updateLiveOverlay();
        topBtn.textContent = "⚡ Transcribe with Groq";
        topBtn.disabled = false;
      } catch (err) {
        alert("Transcription error: " + err.message);
        topBtn.textContent = "⚡ Transcribe with Groq";
        topBtn.disabled = false;
      }
    }

    document.getElementById("topTranscribeBtn").onclick = triggerTranscribe;

    // Render Full Video
    async function triggerRender() {
      if (!state.task) {
        alert("Please upload a video or click 'Try Demo Reel' first!");
        switchTab("tab-transcript");
        return;
      }
      switchTab("tab-render");
      const cta = document.getElementById("renderCtaBtn");
      cta.disabled = true;
      cta.textContent = "🎬 Burning Exact Captions with FFmpeg & libass...";

      try {
        const res = await fetch("/api/render", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            task_id: state.task.task_id,
            phrases: state.phrases,
            style_id: state.style,
            custom_font: (state.customFont && state.customFont !== "auto") ? state.customFont : null,
            casing: state.casing || "default",
            emphasis_font: (state.emphasisFont && state.emphasisFont !== "auto") ? state.emphasisFont : null,
            position_pct: state.position,
            size_pct: Math.round((state.size / 76) * 100),
            accent_color: state.accent
          })
        });
        const data = await res.json();
        const baseName = state.task.filename ? state.task.filename.replace(/\\.[^/.]+$/, "") : "captioned";
        const dlMp4 = document.getElementById("dlMp4Btn");
        dlMp4.href = data.video_url;
        dlMp4.download = `${baseName}_captioned.mp4`;

        const dlSrt = document.getElementById("dlSrtBtn");
        dlSrt.href = data.srt_url;
        dlSrt.download = `${baseName}.srt`;

        const dlAss = document.getElementById("dlAssBtn");
        dlAss.href = data.ass_url;
        dlAss.download = `${baseName}.ass`;

        document.getElementById("renderResultBox").style.display = "flex";
        cta.disabled = false;
        cta.textContent = "✨ Render Full Captioned Video (FFmpeg)";

        // Play burned video directly with zero duplicate overlay
        state.isRendered = true;
        liveCaptionOverlay.style.display = "none";
        liveCaptionOverlay.innerHTML = "";
        userVideo.src = data.video_url;
        userVideo.play().catch(() => {});
      } catch (err) {
        alert("Render error: " + err.message);
        cta.disabled = false;
        cta.textContent = "✨ Render Full Captioned Video (FFmpeg)";
      }
    }

    document.getElementById("renderCtaBtn").onclick = triggerRender;
    document.getElementById("topRenderBtn").onclick = triggerRender;

    // API Keys Modal
    const keysModal = document.getElementById("keysModal");
    document.getElementById("openKeysBtn").onclick = () => {
      fetch("/api/keys").then(r => r.json()).then(d => {
        document.getElementById("groqKeyInput").placeholder = d.masked || "gsk_...";
      });
      keysModal.style.display = "grid";
    };
    document.getElementById("closeKeysBtn").onclick = () => keysModal.style.display = "none";

    document.getElementById("saveKeyBtn").onclick = async () => {
      const val = document.getElementById("groqKeyInput").value.trim();
      await fetch("/api/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ groq_api_key: val })
      });
      keysModal.style.display = "none";
      alert("Groq API key saved!");
    };
    document.getElementById("clearKeyBtn").onclick = async () => {
      document.getElementById("groqKeyInput").value = "";
      await fetch("/api/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ groq_api_key: "" })
      });
      keysModal.style.display = "none";
    };

    // Library Modal
    const libModal = document.getElementById("libraryModal");
    document.getElementById("openLibraryBtn").onclick = () => {
      loadLibrary();
      libModal.style.display = "grid";
    };
    document.getElementById("closeLibraryBtn").onclick = () => libModal.style.display = "none";

    async function loadLibrary() {
      const list = document.getElementById("libraryListContainer");
      const stat = document.getElementById("libStorageText");
      list.innerHTML = "<div style='color:var(--text-3);text-align:center;'>Loading disk storage...</div>";

      try {
        const res = await fetch("/api/videos");
        const data = await res.json();
        stat.textContent = `Total disk usage: ${data.total_storage_mb || 0} MB across ${data.total_count || 0} video files.`;

        if (!data.videos || !data.videos.length) {
          list.innerHTML = "<div style='color:var(--text-3);text-align:center;'>No video projects found on disk.</div>";
          return;
        }

        list.innerHTML = "";
        data.videos.forEach(v => {
          const item = document.createElement("div");
          item.className = "library-item";
          item.innerHTML = `
            <div>
              <div style="font-weight:600; font-size:13px; max-width:260px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${v.filename}</div>
              <div style="font-size:11px; color:var(--text-3); margin-top:2px;">
                ${v.created_at} • ${v.size_mb} MB ${v.is_rendered ? '• <span style=\"color:#10B981;\">Burned MP4</span>' : ''}
              </div>
            </div>
            <div style="display:flex; gap:6px;">
              <button class="btn-top" onclick="openLibVideo('${v.task_id}')">👁️ Open</button>
              ${v.rendered_url ? `<a href="${v.rendered_url}" download class="btn-top btn-top-orange">⬇️ MP4</a>` : ''}
              <button class="btn-top" style="color:var(--danger);" onclick="deleteLibVideo('${v.task_id}')">🗑️</button>
            </div>
          `;
          list.appendChild(item);
        });
      } catch (err) {
        list.innerHTML = "Error: " + err.message;
      }
    }

    window.openLibVideo = async (taskId) => {
      try {
        const res = await fetch(`/api/videos/${taskId}`);
        const data = await res.json();
        setupVideoData(data);
        if (data.phrases && data.phrases.length) {
          state.phrases = data.phrases;
          renderWordList();
        } else {
          triggerTranscribe();
        }
        libModal.style.display = "none";
        switchTab("tab-transcript");
      } catch (err) {
        alert("Failed to load: " + err.message);
      }
    };

    window.deleteLibVideo = async (taskId) => {
      if (!confirm("Permanently delete this video from disk?")) return;
      await fetch(`/api/videos/${taskId}`, { method: "DELETE" });
      if (state.task && state.task.task_id === taskId) {
        document.getElementById("deleteActiveBtn").click();
      }
      loadLibrary();
    };

    document.getElementById("clearAllDiskBtn").onclick = async () => {
      if (!confirm("Permanently delete ALL videos and renders from disk?")) return;
      await fetch("/api/videos", { method: "DELETE" });
      loadLibrary();
      if (state.task) {
        document.getElementById("deleteActiveBtn").click();
      }
    };

    // Theme toggle
    document.getElementById("themeToggle").onclick = () => {
      const dark = document.documentElement.getAttribute("data-theme") !== "light";
      document.documentElement.setAttribute("data-theme", dark ? "light" : "dark");
      document.getElementById("themeToggle").textContent = dark ? "☀️" : "🌙";
    };

    // Keyboard Space shortcut
    window.addEventListener("keydown", (e) => {
      if (e.target && (e.target.tagName === "INPUT" || e.target.tagName === "SELECT" || e.target.isContentEditable)) return;
      if (e.code === "Space" && userVideo.src) {
        e.preventDefault();
        togglePlay();
      }
    });

    // Automatically load demo reel on first start so canvas is immediately active!
    document.getElementById("tryDemoBtn").click();
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def serve_home():
    return HTMLResponse(content=STUDIO_HTML)

def find_available_port(preferred_port: int = 8080) -> int:
    for port in [preferred_port, 8000, 8081, 8082, 5000, 8501]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", port))
            s.close()
            return port
        except Exception:
            pass
    return preferred_port

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", str(find_available_port(8080))))
    url = f"http://127.0.0.1:{port}"
    print("=" * 60)
    print(f"Captionizer Studio is launching on: {url} (Host: {host}:{port})")
    print("=" * 60)
    
    # Auto-open browser if running locally on desktop
    is_cloud = bool(os.environ.get("PORT") or os.environ.get("RENDER") or os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("SPACE_ID"))
    if not is_cloud:
        import threading
        try:
            threading.Timer(1.2, lambda: webbrowser.open(url)).start()
        except Exception:
            pass
    
    uvicorn.run(app, host=host, port=port, log_level="info")
