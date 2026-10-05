import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
FONTS_DIR = BASE_DIR / "fonts"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
FONTS_DIR.mkdir(parents=True, exist_ok=True)

def get_ffmpeg_path() -> str:
    """Finds the best ffmpeg executable available (bundled imageio_ffmpeg or system PATH)."""
    # 1. Try imageio_ffmpeg
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass

    # 2. Try system PATH
    sys_exe = shutil.which("ffmpeg")
    if sys_exe:
        return sys_exe

    # Default fallback
    return "ffmpeg"

def get_groq_api_key() -> str:
    """Returns the Groq API key from environment variable if set."""
    return os.environ.get("GROQ_API_KEY", "").strip()
