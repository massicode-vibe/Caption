# 🎬 Word-by-Word Caption App — Full Build Plan

> **Goal**: Build a local web app that uploads a video, transcribes it with a free open-source API (word-level timestamps), renders animated word-by-word captions in the **Editorial Hybrid** style (SF Pro Display Bold + Instrument Serif Italic), lets the user edit words, and exports a captioned MP4.

---

## 🔍 Reference: What the Website Does (Captionizer)

The website at [producers-south-violin-punch.trycloudflare.com](https://producers-south-violin-punch.trycloudflare.com/) is called **"Captionizer"** — a full-stack video captioning tool.

### Caption Style Analyzed (from image)

The style shown is **"Editorial Hybrid" (style_11)**:
```css
/* Regular words */
font-family: "SF Pro Display";
font-weight: 700;
font-size: ~90px (on 1080px canvas);
color: white;
transform: scaleY(1.08);
text-shadow: 0 1px 6px rgba(0,0,0,0.55), 0 1px 2px rgba(0,0,0,0.35);

/* Highlighted/emphasis words (in <em>) */
font-family: "Instrument Serif";
font-style: italic;
font-weight: 400;
font-size: ~126px (bigger than regular);
text-shadow: 0 0 8px rgba(255,255,255,.9), 0 0 16px rgba(255,255,255,.55);
/* → Creates a "glowing" white effect on italic words */
```

### Key Features to Replicate
- ✅ Word-by-word animation (one phrase at a time, each word pops in)
- ✅ Mixed font: SF Pro Display Bold (normal words) + Instrument Serif Italic (highlighted words)
- ✅ Editable transcript (click word chips to fix spelling)
- ✅ Position control (top/middle/bottom %)
- ✅ Text size slider
- ✅ Highlight color swatches
- ✅ Export as MP4 + SRT + ASS

---

## 🧩 Tech Stack Decision

| Layer | Choice | Reason |
|-------|--------|--------|
| **Frontend** | React + Vite | Fast HMR, component-based |
| **Backend** | Python FastAPI | Async, great for file handling |
| **Transcription** | Groq Whisper API (free) | Word-level timestamps, no GPU needed |
| **Local fallback** | faster-whisper | Runs on CPU, word timestamps |
| **Video rendering** | FFmpeg (server-side) | Burn captions onto video |
| **Caption preview** | HTML Canvas / CSS animation | Real-time preview in browser |
| **Fonts** | Google Fonts + SF Pro (self-hosted) | Match Captionizer style |

---

## 🛠️ Open-Source Tools & APIs (Researched)

### 1. 🥇 Groq Whisper API (RECOMMENDED — Free Tier)
- **GitHub**: N/A (hosted service, uses OpenAI-compatible API)
- **URL**: https://console.groq.com/
- **Model**: `whisper-large-v3` or `whisper-large-v3-turbo`
- **Word timestamps**: ✅ YES (`timestamp_granularities=["word"]`)
- **Free tier**: ✅ YES — free API key, ~7200 audio seconds/hour
- **Python usage**:
```python
from groq import Groq
client = Groq(api_key="YOUR_GROQ_API_KEY")

with open("audio.mp3", "rb") as f:
    result = client.audio.transcriptions.create(
        file=("audio.mp3", f.read()),
        model="whisper-large-v3-turbo",
        response_format="verbose_json",
        timestamp_granularities=["word", "segment"]
    )

words = result.words  # [{"word": "If", "start": 0.0, "end": 0.3}, ...]
```

### 2. 🥈 WhisperX (Local, Best Accuracy)
- **GitHub**: https://github.com/m-bain/whisperX
- **Word timestamps**: ✅ YES (forced alignment via wav2vec2, sub-100ms accuracy)
- **Free**: ✅ Fully local/open source
- **Requires**: NVIDIA GPU recommended (works on CPU slowly)
- **Install**: `pip install whisperx`
- **Usage**:
```python
import whisperx
model = whisperx.load_model("large-v2", device="cuda")
result = model.transcribe("audio.wav")
model_a, metadata = whisperx.load_align_model(language_code="en", device="cuda")
result = whisperx.align(result["segments"], model_a, metadata, "audio.wav", device="cuda")
# result["word_segments"] = [{"word": "float", "start": 1.2, "end": 1.6, "score": 0.99}]
```

### 3. 🥉 faster-whisper (Local CPU/GPU)
- **GitHub**: https://github.com/SYSTRAN/faster-whisper
- **Word timestamps**: ✅ YES
- **Free**: ✅ Fully local
- **Install**: `pip install faster-whisper`
- **Usage**:
```python
from faster_whisper import WhisperModel
model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe("audio.wav", word_timestamps=True)
for segment in segments:
    for word in segment.words:
        print(word.start, word.end, word.word)
```

### 4. AssemblyAI (Free Tier)
- **URL**: https://www.assemblyai.com/
- **Word timestamps**: ✅ YES
- **Free**: ✅ 5 hours/month free
- **Install**: `pip install assemblyai`

### 5. HuggingFace Inference API
- **Model**: `openai/whisper-large-v3` on HuggingFace Hub
- **Word timestamps**: ⚠️ Partial (segment level only via inference API)
- **Free**: ✅ Limited free calls
- **URL**: https://huggingface.co/openai/whisper-large-v3

---

## 📁 Project Structure

```
caption-app/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── transcribe.py        # Groq/WhisperX transcription
│   ├── renderer.py          # FFmpeg caption burning
│   ├── caption_styles.py    # Style definitions
│   ├── requirements.txt
│   └── fonts/
│       ├── SF-Pro-Display-Bold.otf
│       └── InstrumentSerif-Italic.ttf
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── VideoUpload.jsx      # Drag & drop upload
│   │   │   ├── StylePicker.jsx      # Style tiles like Captionizer
│   │   │   ├── CaptionPreview.jsx   # Live canvas preview
│   │   │   ├── TranscriptEditor.jsx # Word chip editor
│   │   │   ├── WordChip.jsx         # Clickable editable word
│   │   │   └── ControlPanel.jsx     # Position/size/color controls
│   │   ├── styles/
│   │   │   └── caption-styles.css   # All 11 caption styles
│   │   └── utils/
│   │       ├── api.js               # API calls
│   │       └── captionRenderer.js   # Canvas animation logic
│   ├── public/
│   │   └── fonts/                   # Self-hosted fonts
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── docker-compose.yml       # Optional: containerize everything
└── README.md
```

---

## 🎨 Caption Style Implementation (HTML/CSS/Canvas)

### Style 11 — "Editorial Hybrid" (The one in your image)

```css
/* In caption-styles.css */
@font-face {
  font-family: "SF Pro Display";
  src: url("/fonts/SF-Pro-Display-Bold.otf") format("opentype");
  font-weight: 700;
}
@font-face {
  font-family: "Instrument Serif";
  src: url("/fonts/InstrumentSerif-Italic.ttf") format("truetype");
  font-style: italic;
}

.caption-editorial-hybrid {
  font-family: "SF Pro Display", "Helvetica Neue", sans-serif;
  font-weight: 700;
  font-size: 72px; /* Scale based on canvas size */
  color: #ffffff;
  text-align: center;
  transform: scaleY(1.08);
  text-shadow:
    0 1px 6px rgba(0,0,0,0.55),
    0 1px 2px rgba(0,0,0,0.35);
}

.caption-editorial-hybrid em {
  font-family: "Instrument Serif", Georgia, serif;
  font-style: italic;
  font-weight: 400;
  font-size: 1.4em; /* Bigger than regular */
  text-shadow:
    0 0 8px rgba(255,255,255,0.9),
    0 0 16px rgba(255,255,255,0.55);
  /* Creates the glowing white "float" effect */
}
```

### Word-by-Word Animation Logic

```javascript
// captionRenderer.js
class CaptionRenderer {
  constructor(canvas, words, style) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.words = words; // [{word, start, end, emphasis}]
    this.style = style;
    this.currentWordIndex = -1;
  }

  // Called on video timeupdate event
  update(currentTime) {
    const wordIndex = this.words.findIndex(
      w => currentTime >= w.start && currentTime <= w.end
    );
    if (wordIndex === this.currentWordIndex) return;
    this.currentWordIndex = wordIndex;
    this.renderPhrase(currentTime);
  }

  renderPhrase(currentTime) {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Find the phrase window (2-3 words around current)
    const phraseWords = this.getPhraseWindow(currentTime);
    phraseWords.forEach((word, i) => {
      const isActive = word.start <= currentTime && currentTime <= word.end;
      this.drawWord(word.text, word.emphasis, isActive, i, phraseWords.length);
    });
  }

  drawWord(text, isEmphasis, isActive, index, total) {
    const ctx = this.ctx;
    ctx.save();

    if (isEmphasis) {
      ctx.font = `italic ${this.style.emphasisSize}px "Instrument Serif"`;
      ctx.shadowColor = 'rgba(255,255,255,0.9)';
      ctx.shadowBlur = 20;
    } else {
      ctx.font = `700 ${this.style.fontSize}px "SF Pro Display"`;
      ctx.shadowColor = 'rgba(0,0,0,0.55)';
      ctx.shadowBlur = 6;
    }

    ctx.fillStyle = isActive ? this.style.activeColor : '#ffffff';
    ctx.textAlign = 'center';

    // Scale Y for the editorial stretch effect
    ctx.transform(1, 0, 0, 1.08, 0, 0);
    ctx.fillText(text, this.canvas.width / 2, this.getYPosition(index, total));
    ctx.restore();
  }
}
```

---

## 🔧 Backend API Endpoints (FastAPI)

```python
# main.py
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"])

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload video, return file_id"""

@app.post("/api/transcribe/{file_id}")
async def transcribe(file_id: str, provider: str = "groq"):
    """
    Transcribe video using chosen provider.
    Returns word-level timestamps.
    """

@app.get("/api/style-preview/{style_id}")
async def style_preview(style_id: str, accent: str, position: str, size: float):
    """Return HTML iframe with live caption preview"""

@app.post("/api/render/{file_id}")
async def render_video(file_id: str, words: list, style: str, position: float):
    """
    Burn captions onto video using FFmpeg.
    Returns rendered MP4 URL.
    """

@app.get("/api/download/{file_id}")
async def download(file_id: str):
    """Download rendered MP4"""
```

---

## 🎥 FFmpeg Caption Burning

The server renders captions by generating an ASS subtitle file and burning it with FFmpeg:

```python
# renderer.py
import subprocess
import json

def generate_ass_file(words, style, position_pct):
    """Generate ASS subtitle file from word timestamps"""
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, Outline, Shadow, Alignment, MarginV
Style: Normal,SF Pro Display,90,&H00FFFFFF,&H00000000,2,1,2,{margin_v}
Style: Emphasis,Instrument Serif,120,&H00FFFFFF,&H00000000,0,0,2,{margin_v}

[Events]
Format: Layer, Start, End, Style, Text
""".format(margin_v=int(1920 * position_pct / 100))

    events = []
    # Group words into phrases of 2-3 words
    for phrase in group_words_to_phrases(words):
        # Each word highlighted one at a time
        for i, word in enumerate(phrase):
            start = format_ass_time(word['start'])
            end = format_ass_time(word['end'])
            # Build phrase text with current word highlighted
            text_parts = []
            for j, w in enumerate(phrase):
                if w['emphasis']:
                    if j == i:
                        text_parts.append(f"{{\\i1}}{w['word']}{{\\i0}}")
                    else:
                        text_parts.append(f"{{\\i1\\alpha&H80&}}{w['word']}{{\\i0}}")
                else:
                    if j == i:
                        text_parts.append(w['word'])
                    else:
                        text_parts.append(f"{{\\alpha&H80&}}{w['word']}")
            events.append(f"Dialogue: 0,{start},{end},Normal,," + " ".join(text_parts))

    return ass_header + "\n".join(events)


def burn_captions(input_video, ass_file, output_path):
    """Use FFmpeg to burn ASS captions into video"""
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf", f"ass={ass_file}",
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
```

---

## 🖥️ Frontend Components

### 1. VideoUpload Component
```jsx
// VideoUpload.jsx
import { useState, useCallback } from 'react';

export function VideoUpload({ onFileSelected }) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('video/')) {
      onFileSelected(file);
    }
  }, [onFileSelected]);

  return (
    <div
      className={`drop-zone ${isDragging ? 'dragging' : ''}`}
      onDrop={handleDrop}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onClick={() => document.getElementById('fileInput').click()}
    >
      <span className="icon">🎬</span>
      <strong>Drop a video here or <u>browse</u></strong>
      <small>MP4, MOV, WEBM — up to 2GB</small>
      <input
        id="fileInput"
        type="file"
        accept="video/*"
        hidden
        onChange={(e) => onFileSelected(e.target.files[0])}
      />
    </div>
  );
}
```

### 2. TranscriptEditor Component (Word Chips)
```jsx
// TranscriptEditor.jsx
import { useState } from 'react';

export function WordChip({ word, onEdit }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(word.text);

  if (editing) {
    return (
      <input
        className="word-chip-input"
        value={value}
        autoFocus
        onChange={(e) => setValue(e.target.value)}
        onBlur={() => { setEditing(false); onEdit(value); }}
        onKeyDown={(e) => e.key === 'Enter' && e.target.blur()}
      />
    );
  }

  return (
    <button
      className={`word-chip ${value !== word.originalText ? 'modified' : ''}`}
      onClick={() => setEditing(true)}
    >
      {value}
      {word.emphasis && <span className="italic-badge">✦</span>}
    </button>
  );
}
```

### 3. CaptionPreview (Live Canvas)
```jsx
// CaptionPreview.jsx
import { useEffect, useRef } from 'react';

export function CaptionPreview({ videoRef, words, style, position }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    const renderer = new CaptionRenderer(canvas, words, style);

    const onTimeUpdate = () => renderer.update(video.currentTime);
    video.addEventListener('timeupdate', onTimeUpdate);
    return () => video.removeEventListener('timeupdate', onTimeUpdate);
  }, [words, style]);

  return (
    <div className="preview-container">
      <video ref={videoRef} controls className="preview-video" />
      <canvas ref={canvasRef} className="caption-overlay" />
    </div>
  );
}
```

---

## 🔄 Full App Flow

```
1. User drops video
       ↓
2. Frontend POSTs to /api/upload
       ↓
3. Backend saves file, returns file_id + thumbnail
       ↓
4. User picks caption style + settings
       ↓ (live preview updates in iframe/canvas)
5. User clicks "Transcribe"
       ↓
6. Backend calls Groq Whisper API with audio extracted from video
   → Returns word-level timestamps: [{word, start, end}]
       ↓
7. Frontend renders EDITABLE word chips
   → User can click any word to fix typos
       ↓
8. User clicks "Render Video"
       ↓
9. Backend:
   a. Generates ASS subtitle file
   b. FFmpeg burns captions: ffmpeg -i video.mp4 -vf ass=captions.ass output.mp4
   c. Returns download URL
       ↓
10. User downloads MP4 + SRT + ASS files
```

---

## 📦 Requirements

### Backend (`requirements.txt`)
```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
python-multipart>=0.0.9
groq>=0.9.0
faster-whisper>=1.0.0
aiofiles>=23.2.1
ffmpeg-python>=0.2.0
httpx>=0.27.0
```

### Frontend (`package.json` dependencies)
```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "axios": "^1.7.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.3.0"
  }
}
```

### System Requirements
```
- Python 3.10+
- Node.js 18+
- FFmpeg installed (in PATH)
- Groq API key (free at console.groq.com)
```

---

## ⚡ Quick Start Commands

```bash
# 1. Clone / init project
mkdir caption-app && cd caption-app

# 2. Backend setup
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
# Set env variable:
set GROQ_API_KEY=your_key_here
uvicorn main:app --reload --port 8000

# 3. Frontend setup (new terminal)
cd frontend
npm install
npm run dev
# → Opens at http://localhost:5173
```

---

## 🎨 All Caption Styles to Implement

| ID | Name | Font | Effect |
|----|------|------|--------|
| `style_11` | **Editorial Hybrid** ⭐ | SF Pro Display + Instrument Serif Italic | White glow on italic emphasis words |
| `style_10` | Editorial Serif | PP Editorial New | Clean serif, large/small mix |
| `style_1` | Bold Yellow | Montserrat 900 | ALL CAPS, yellow, stroke |
| `style_2` | Cyan Pop | Poppins 800 | White + cyan highlights, stroke |
| `style_3` | Yellow Tag | Plus Jakarta Sans 800 | Yellow highlight words |
| `style_4` | Red Impact | Montserrat 900 | ALL CAPS, red glow |
| `style_5` | Cyan Minimal | Montserrat 800 | White + cyan, no uppercase |
| `style_6` | Blue Glow | Montserrat 800 | Blue drop-shadow glow |
| `style_7` | Stack Script | Montserrat + Alex Brush | Stacked headline + handwriting |
| `style_8` | Inter Blue | Inter ExtraBold | Blue accent words |
| `style_9` | Yellow Box | Plus Jakarta Sans | Yellow highlight box/pill |

---

## 🔑 API Keys Needed

| Service | Where to get | Cost |
|---------|-------------|------|
| **Groq** | https://console.groq.com/ | ✅ Free |
| AssemblyAI (optional) | https://www.assemblyai.com/ | ✅ 5h/month free |
| HuggingFace (optional) | https://huggingface.co/settings/tokens | ✅ Free tier |

---

## 📝 Notes for the AI Agent Building This

1. **Fonts**: SF Pro Display is Apple's font — for web use, substitute with `Inter` (ExtraBold) or use the actual file if available. Instrument Serif is available on Google Fonts.

2. **Word-level emphasis**: The "Editorial Hybrid" style randomly or rule-based marks certain words as `emphasis=true` (the italic ones). You can make the LAST word of each phrase italic, or every 3rd word, or detect adjectives/nouns via NLP.

3. **Caption grouping**: Group words into phrases of 2-4 words max. Show full phrase with dim opacity, highlight current word at full opacity.

4. **Preview vs. Render**: 
   - Preview: CSS/Canvas animation in browser (real-time, no encode)
   - Render: FFmpeg burns captions permanently into MP4

5. **FFmpeg must be installed** on the system. On Windows: `winget install FFmpeg` or download from https://ffmpeg.org/

6. **CORS**: Backend must allow `http://localhost:5173` (Vite default port)

7. **File cleanup**: Auto-delete temp files after download (or use TTL)

8. **Audio extraction**: FFmpeg extracts audio before transcription:
   ```bash
   ffmpeg -i input.mp4 -q:a 0 -map a audio.mp3
   ```

---

## 🎯 Emphasis Word Detection Logic

For "Editorial Hybrid" style — which words get the Instrument Serif italic treatment:

```python
# Option 1: Mark every Nth word
def mark_emphasis_words(words, every_n=3):
    for i, word in enumerate(words):
        word['emphasis'] = (i % every_n == every_n - 1)
    return words

# Option 2: Mark content words (nouns, verbs, adjectives)
import spacy
nlp = spacy.load("en_core_web_sm")

def mark_emphasis_by_pos(words, text):
    doc = nlp(text)
    content_pos = {"NOUN", "VERB", "ADJ", "ADV"}
    for word, token in zip(words, doc):
        word['emphasis'] = token.pos_ in content_pos
    return words

# Option 3: Always emphasize the LAST word of each phrase
def mark_last_word_emphasis(phrases):
    for phrase in phrases:
        for i, word in enumerate(phrase):
            word['emphasis'] = (i == len(phrase) - 1)
    return phrases
```

