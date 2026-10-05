import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any
from .config import get_ffmpeg_path, OUTPUTS_DIR
from .styles import get_style_by_id

def format_ass_time(seconds: float) -> str:
    """Formats float seconds into ASS timestamp format: H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def format_srt_time(seconds: float) -> str:
    """Formats float seconds into SRT timestamp format: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def generate_srt(phrases: List[Dict[str, Any]], output_path: Path) -> Path:
    """Generates a standard .srt subtitle file."""
    lines = []
    for idx, phrase in enumerate(phrases, 1):
        start = format_srt_time(phrase["start"])
        end = format_srt_time(phrase["end"])
        text = phrase["text"]
        lines.append(f"{idx}\n{start} --> {end}\n{text}\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return output_path

def hex_to_ass_color(hex_color: str, alpha: int = 0) -> str:
    """Converts hex '#RRGGBB' to ASS color format '&HAABBGGRR'."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r = hex_color[0:2]
        g = hex_color[2:4]
        b = hex_color[4:6]
    else:
        r, g, b = "FF", "FF", "FF"
    a = f"{alpha:02X}"
    return f"&H{a}{b}{g}{r}"

def generate_ass(
    phrases: List[Dict[str, Any]],
    output_path: Path,
    style_id: str = "style_11",
    position_pct: int = 50,
    size_pct: int = 100,
    custom_accent: str = "auto",
    video_width: int = 1080,
    video_height: int = 1920
) -> Path:
    """
    Generates an Advanced SubStation Alpha (.ass) subtitle file.
    Renders word-by-word highlighted captions matching the style.
    """
    style_info = get_style_by_id(style_id)
    accent_color = style_info["accent"] if custom_accent == "auto" else custom_accent

    # Vertical margin calculation
    # ASS Alignment: 2 = Bottom Center, 5 = Top Center, 8 = Center Middle
    # MarginV controls offset from edge
    margin_v = int((position_pct / 100.0) * video_height)
    # Using Alignment 2 (bottom center) where MarginV is distance from bottom
    # position_pct: 10% (top) -> 88% (bottom)
    # MarginV from bottom = (100 - position_pct)%
    ass_margin_v = int(((100 - position_pct) / 100.0) * video_height)
    if ass_margin_v < 40:
        ass_margin_v = 40

    base_font_size = int(68 * (size_pct / 100.0))
    emphasis_font_size = int(88 * (size_pct / 100.0))

    primary_color = "&H00FFFFFF"  # White
    highlight_ass = hex_to_ass_color(accent_color, 0)
    dim_ass = "&H70FFFFFF"  # Partially transparent white

    font_base = "Arial"
    if "Inter" in style_info["font_family_base"]:
        font_base = "Inter"
    elif "Montserrat" in style_info["font_family_base"]:
        font_base = "Montserrat"
    elif "Poppins" in style_info["font_family_base"]:
        font_base = "Poppins"

    header = f"""[Script Info]
Title: Word-by-Word Caption
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Normal,{font_base},{base_font_size},{primary_color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,108,1,0,1,3,2,2,40,40,{ass_margin_v},1
Style: Active,{font_base},{base_font_size},{highlight_ass},&H000000FF,&H00000000,&H80000000,-1,0,0,0,105,112,1,0,1,3,3,2,40,40,{ass_margin_v},1
Style: Emphasis,Georgia,{emphasis_font_size},{highlight_ass},&H000000FF,&H00000000,&H80000000,0,-1,0,0,100,100,2,0,1,2,3,2,40,40,{ass_margin_v},1

[Events]
Format: Layer, Start, End, Style, Text
"""

    events = []
    for phrase in phrases:
        words = phrase.get("words", [])
        if not words:
            continue

        # If phrase has multiple words, generate sub-events for each word highlight
        for active_idx, active_word in enumerate(words):
            start_t = format_ass_time(active_word["start"])
            end_t = format_ass_time(active_word["end"])

            text_chunks = []
            for j, w in enumerate(words):
                is_curr = (j == active_idx)
                is_emph = w.get("emphasis", False)

                if is_curr:
                    if is_emph:
                        # Instrument serif / Georgia italic glow
                        text_chunks.append(f"{{\\rEmphasis\\c{highlight_ass}\\i1}}{w['text']}{{\\rNormal}}")
                    else:
                        text_chunks.append(f"{{\\rActive\\c{highlight_ass}}}{w['text']}{{\\rNormal}}")
                else:
                    # Inactive word in phrase (dimmed)
                    if is_emph:
                        text_chunks.append(f"{{\\i1\\alpha&HA0&}}{w['text']}{{\\i0\\alpha&H00&}}")
                    else:
                        text_chunks.append(f"{{\\alpha&HA0&}}{w['text']}{{\\alpha&H00&}}")

            full_line = " ".join(text_chunks)
            events.append(f"Dialogue: 0,{start_t},{end_t},Normal,,{full_line}")

    content = header + "\n".join(events) + "\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path

def burn_captions_to_video(
    video_path: Path,
    ass_path: Path,
    output_path: Path
) -> Path:
    """Uses FFmpeg to burn ASS captions into the video."""
    ffmpeg = get_ffmpeg_path()

    # Escape path for FFmpeg filter on Windows
    # Best practice: use forward slashes and escape colon
    clean_ass = str(ass_path.resolve()).replace("\\", "/")
    if ":" in clean_ass:
        drive, rest = clean_ass.split(":", 1)
        clean_ass = f"{drive}\\:{rest}"

    cmd = [
        ffmpeg, "-y",
        "-i", str(video_path),
        "-vf", f"ass='{clean_ass}'",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-c:a", "copy",
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback if libass had path parsing difficulty
        # Run inside directory with relative filename
        parent_dir = ass_path.parent
        rel_ass = ass_path.name
        cmd_fallback = [
            ffmpeg, "-y",
            "-i", str(video_path.resolve()),
            "-vf", f"ass={rel_ass}",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "copy",
            str(output_path.resolve())
        ]
        fallback_res = subprocess.run(cmd_fallback, cwd=str(parent_dir), capture_output=True, text=True)
        if fallback_res.returncode != 0:
            raise RuntimeError(f"FFmpeg caption burning failed:\n{result.stderr}\nFallback:\n{fallback_res.stderr}")

    return output_path
