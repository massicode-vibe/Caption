# 🎬 Caption AI — Word-by-Word Animated Caption Studio

**Caption AI** is a full-stack, browser-based video captioning application that generates dynamic word-by-word animated subtitles burned directly into vertical 9:16 videos using **FFmpeg** and **libass**.

It features 8 curated typography styles, headlined by the signature **Editorial Hybrid** aesthetic (*Apple SF Pro / Inter ExtraBold* base + glowing *Instrument Serif Italic* emphasis aura).

---

## ✨ Features & Capabilities

1. **Sequential 4-Tab Workflow**:
   - **Tab 1: 📑 Words & Transcript**:
     - Drag-and-drop vertical video upload (MP4, MOV, WEBM).
     - Active Video Bar with video metadata and `🗑️ Delete / Wrong Video` button.
     - `No video on hand?` banner with **`🪄 Try Demo Reel`** (auto-loads a 12s vertical 9:16 reel with real word timings).
     - `Words per phrase` buttons (`2`, `3`, `4`) to control caption pacing.
     - `✨ Last word italic` button to auto-emphasize the final word of each phrase.
     - Interactive word chip editor: click text to fix typos, click `✦` to toggle Instrument Serif Italic emphasis.
     - `▶` play button on each phrase card to jump and preview that specific segment.
   - **Tab 2: 🎨 Caption Style**:
     - 8 typography styles matching social media aesthetics:
       1. **Editorial Hybrid** (`★ FEATURED HERO`): Inter ExtraBold + Instrument Serif Italic glowing aura.
       2. **Editorial Serif**: Pure Instrument Serif magazine elegance.
       3. **Bold Yellow**: Montserrat 900 ALL-CAPS with thick black outline & electric yellow.
       4. **Cyan Pop**: Poppins ExtraBold with neon cyan keywords.
       5. **Yellow Tag**: Plus Jakarta Sans with high-contrast highlighter marker badge.
       6. **Red Impact**: Montserrat heavy uppercase with crimson cinema glow.
       7. **Minimalist Mono**: Clean monochrome Inter with soft opacity transitions.
       8. **Blue Glow**: Heavy uppercase with electric cobalt aura.
   - **Tab 3: 🎛️ Position & Size**:
     - **Vertical Position**: Presets (*Top 25%*, *Middle 50%*, *Bottom 80%*), fine slider, and on-canvas drag bar.
     - **Caption Font Size**: Presets (*Compact 56px*, *Standard 76px*, *Impact 98px*) and slider.
     - **🔤 Font Format & Typography**:
       - Base font selector: *Auto*, *Inter ExtraBold*, *SF Pro Display*, *Montserrat*, *Poppins*, *PP Editorial New*, *Plus Jakarta Sans*.
       - Text casing selector: *Original Speech Case*, *UPPERCASE (ALL CAPS)*, *Title Case*, *lowercase*.
       - Emphasis font selector: *Auto*, *Instrument Serif Italic*, *Alex Brush (Calligraphy)*, *Same as Base*.
     - **Active Word Highlight Color**: 8 color swatches + custom color picker.
   - **Tab 4: 📥 Render & Export**:
     - One-click CTA: **`✨ Render Full Captioned Video (FFmpeg)`**.
     - Download buttons for **MP4 Video**, **SRT Subtitles**, and **ASS Subtitles**.
     - Live player switches to the burned video with zero duplicate text overlay.

2. **Real-time Live Canvas & Video Player (Left Column)**:
   - 9:16 vertical phone mockup with custom video player dock.
   - Centered play overlay button, progress scrubber bar, timecode, replay (`↺`), and volume mute.
   - 100% matched typography preview with real-time active word highlighting synchronized to video time.

3. **Transcription Engine (Hybrid Cloud + Offline)**:
   - **Groq Whisper Cloud** (`whisper-large-v3-turbo`): Sub-second transcription when `GROQ_API_KEY` is provided.
   - **Offline Local AI** (`faster-whisper-tiny` CPU int8): Completely private offline fallback requiring zero API keys.
   - Built-in Demo Reel fallback when no audio is detected.

4. **📁 Video Library & Disk Storage Manager**:
   - Modal accessible via top bar `📁 Library`.
   - View all uploaded videos and rendered MP4 files with file sizes and creation dates.
   - One-click `👁️ Open` to reload past video projects.
   - `⬇️ MP4` download button directly from storage.
   - Individual file delete (`🗑️`) and `🧹 Clear All Files from Disk` button.

---

## 💻 Local Setup & Running

### Option 1: Quick Start (Windows)
Double click:
```cmd
start.bat
```

### Option 2: Python Command Line
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the server:
   ```bash
   python app.py
   ```
3. Open your browser at:
   ```
   http://127.0.0.1:8080
   ```

---

## ☁️ How to Host & Deploy

### 1. Deploy on Render (Recommended)
1. Fork or push this repository to GitHub.
2. Go to [Render Dashboard](https://dashboard.render.com/) -> **New +** -> **Web Service**.
3. Connect your repository `massicode-vibe/Caption`.
4. Choose **Python 3** or **Docker**:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, optionally add:
   - `GROQ_API_KEY`: *(Your Groq API key from console.groq.com)*
   - `PYTHON_VERSION`: `3.11.9`
6. Click **Deploy Web Service**.

*(Alternatively, connect via `render.yaml` Blueprint for automatic zero-configuration deploy).*

---

### 2. Deploy on Railway
1. Go to [Railway.app](https://railway.app/) -> **New Project** -> **Deploy from GitHub repo**.
2. Select `massicode-vibe/Caption`.
3. Railway automatically detects the `Procfile` and `Dockerfile`.
4. Add environment variable:
   - `GROQ_API_KEY`: *(Optional for cloud Whisper)*
5. Click **Deploy**.

---

### 3. Deploy on Hugging Face Spaces (Free Cloud GPU/CPU)
1. Go to [Hugging Face Spaces](https://huggingface.co/spaces) -> **Create new Space**.
2. Set Space SDK to **Docker** (Blank).
3. Connect your GitHub repository or push directly to the Space git remote.
4. Hugging Face will automatically build using the included `Dockerfile` and expose port `7860`.
5. Under Space **Settings** -> **Variables and secrets**, add `GROQ_API_KEY`.

---

### 4. Deploy with Docker (VPS / Local / Cloud Run)
Build and run the containerized image:
```bash
# Build the Docker image
docker build -t caption-ai .

# Run container on port 7860
docker run -d -p 7860:7860 -e GROQ_API_KEY="your_api_key_here" caption-ai
```
Visit `http://localhost:7860`.

---

## 🔑 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Optional | Free API key from [Groq](https://console.groq.com/) for ultra-fast Whisper transcription. If not set, Caption AI uses local CPU `faster-whisper`. |
| `PORT` | Optional | Web server listening port (Default: `8080` locally, `$PORT` on cloud platforms, `7860` in Docker). |
| `HOST` | Optional | Host interface binding (Default: `0.0.0.0`). |

---

## 🛠️ Tech Stack
- **Backend**: FastAPI, Uvicorn, Pydantic, Subprocess, Python 3.11/3.14.
- **Video & Audio Processing**: FFmpeg 7.1, libass, imageio-ffmpeg.
- **AI Speech Recognition**: Groq Cloud Whisper API (`whisper-large-v3-turbo`) & local `faster-whisper`.
- **Frontend**: Responsive Single-Page Application (HTML5, Vanilla ES6+, CSS3 custom properties, GSAP 3).
