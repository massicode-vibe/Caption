import os
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from groq import Groq
from .config import get_ffmpeg_path, get_groq_api_key

def extract_audio(video_path: Path, output_audio_path: Path) -> Path:
    """Extracts 16kHz mono audio from video using ffmpeg."""
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
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed: {result.stderr}")
    return output_audio_path

def get_video_info(video_path: Path) -> Dict[str, Any]:
    """Gets duration, width, height using ffprobe or ffmpeg."""
    ffmpeg = get_ffmpeg_path()
    cmd = [
        ffmpeg, "-i", str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = 5.0
    width = 1080
    height = 1920

    # Parse stderr for Duration and Video dimensions
    stderr = result.stderr or ""
    for line in stderr.splitlines():
        line = line.strip()
        if "Duration:" in line:
            try:
                part = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = part.split(":")
                duration = float(h) * 3600 + float(m) * 60 + float(s)
            except Exception:
                pass
        if "Video:" in line:
            try:
                # Look for patterns like 1080x1920 or 720x1280
                parts = line.split(",")
                for p in parts:
                    p = p.strip()
                    if "x" in p and any(c.isdigit() for c in p):
                        for token in p.split():
                            if "x" in token:
                                w_str, h_str = token.split("x")
                                w_val = int("".join(c for c in w_str if c.isdigit()))
                                h_val = int("".join(c for c in h_str if c.isdigit()))
                                if w_val > 0 and h_val > 0:
                                    width = w_val
                                    height = h_val
                                    break
            except Exception:
                pass

    return {
        "duration": duration,
        "width": width,
        "height": height,
        "aspect_ratio": f"{width}/{height}"
    }

def transcribe_audio_groq(audio_path: Path, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Transcribes audio using Groq Whisper API with word-level timestamps."""
    key = api_key or get_groq_api_key()
    if not key:
        raise ValueError("GROQ_API_KEY is not configured.")

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
            word_dict = {
                "id": f"w_{idx}",
                "text": w.word.strip(),
                "start": round(float(w.start), 3),
                "end": round(float(w.end), 3),
                "emphasis": False
            }
            if word_dict["text"]:
                words.append(word_dict)
    else:
        # Fallback to segments if words not directly returned
        idx = 0
        for seg in getattr(transcription, "segments", []):
            text = seg.get("text", "").strip()
            start = float(seg.get("start", 0))
            end = float(seg.get("end", start + 1))
            parts = text.split()
            if not parts:
                continue
            word_dur = (end - start) / len(parts)
            for i, p in enumerate(parts):
                words.append({
                    "id": f"w_{idx}",
                    "text": p,
                    "start": round(start + i * word_dur, 3),
                    "end": round(start + (i + 1) * word_dur, 3),
                    "emphasis": False
                })
                idx += 1

    return words

def generate_demo_words(duration: float = 6.0) -> List[Dict[str, Any]]:
    """Generates realistic sample words (matching potato water density clip) if no API key is provided."""
    sample_text = "If they float, they're not good. If they sink to the bottom, that means they're fresh."
    tokens = sample_text.split()
    total_words = len(tokens)
    dur_per_word = min(0.35, max(0.2, (duration - 0.5) / max(total_words, 1)))

    words = []
    curr = 0.4
    for i, token in enumerate(tokens):
        w_start = round(curr, 2)
        w_end = round(curr + dur_per_word * 0.9, 2)
        curr += dur_per_word
        words.append({
            "id": f"w_{i}",
            "text": token,
            "start": w_start,
            "end": w_end,
            "emphasis": False
        })
    return words

def group_words_into_phrases(words: List[Dict[str, Any]], pacing: str = "auto") -> List[Dict[str, Any]]:
    """
    Groups words into short phrases (1 to 4 words) suitable for short-form video captions.
    Marks emphasis words (e.g. last word or punctuation words) for the Editorial Hybrid style.
    """
    if not words:
        return []

    target_len = 3
    if pacing == "1":
        target_len = 1
    elif pacing == "2-3":
        target_len = 2
    elif pacing == "sentence":
        target_len = 5

    phrases = []
    current_phrase_words = []

    for i, word in enumerate(words):
        current_phrase_words.append(word)

        # Decide whether to break phrase:
        has_punctuation = any(word["text"].endswith(p) for p in [".", ",", "!", "?", ";", ":"])
        time_gap = False
        if i < len(words) - 1:
            time_gap = (words[i+1]["start"] - word["end"]) > 0.4

        should_break = (
            len(current_phrase_words) >= target_len or
            has_punctuation or
            time_gap or
            i == len(words) - 1
        )

        if should_break and current_phrase_words:
            # Emphasize the last word or dramatic word of the phrase for Editorial Hybrid
            last_word = current_phrase_words[-1]
            last_word["emphasis"] = True

            phrase_start = current_phrase_words[0]["start"]
            phrase_end = current_phrase_words[-1]["end"]

            phrases.append({
                "id": f"phrase_{len(phrases)}",
                "start": phrase_start,
                "end": phrase_end,
                "text": " ".join(w["text"] for w in current_phrase_words),
                "words": current_phrase_words
            })
            current_phrase_words = []

    return phrases
