# 🤖 AI Agent Prompt — Caption App Builder

> **Copy and paste this entire prompt into a new Antigravity conversation to have the AI build your app.**

---

## PROMPT TO GIVE THE AI

```
Build me a full-stack video captioning web app in e:\CODE\Projects\Test\caption-app

The app is inspired by https://producers-south-violin-punch.trycloudflare.com/ (Captionizer).

## WHAT IT DOES
1. User uploads a video (drag & drop, localhost only for now)
2. App extracts audio and transcribes it via Groq Whisper API (free tier) to get WORD-LEVEL timestamps
3. User sees an EDITABLE word list — clickable word chips to fix typos
4. User picks a caption STYLE, POSITION (top/middle/bottom), TEXT SIZE, HIGHLIGHT COLOR
5. Live PREVIEW shows word-by-word animation overlaid on the video in the browser
6. User clicks "Render" — FFmpeg burns the captions into an MP4
7. User downloads the captioned MP4 + SRT + ASS files

## CAPTION STYLE TO IMPLEMENT (PRIORITY: Editorial Hybrid)
The main style is called "Editorial Hybrid" — exactly like the image shows:
- Regular words: SF Pro Display Bold (or Inter ExtraBold as substitute), white, scaleY(1.08), drop shadow
- Emphasis/highlighted words: Instrument Serif Italic (Google Fonts), bigger size, glowing white text-shadow
- Word-by-word: show 2-3 words at a time, highlight current word at full brightness, others slightly dimmer
- The last word of each phrase gets the Instrument Serif italic treatment

CSS for the style:
```css
.caption-editorial-hybrid .word-normal {
  font-family: "Inter", sans-serif;
  font-weight: 800;
  font-size: 72px;
  color: white;
  text-shadow: 0 1px 6px rgba(0,0,0,0.55), 0 1px 2px rgba(0,0,0,0.35);
  transform: scaleY(1.08);
  display: inline-block;
}
.caption-editorial-hybrid .word-emphasis {
  font-family: "Instrument Serif", serif;
  font-style: italic;
  font-weight: 400;
  font-size: 100px;
  color: white;
  text-shadow: 0 0 8px rgba(255,255,255,0.9), 0 0 16px rgba(255,255,255,0.55);
  display: inline-block;
}
.word-dimmed { opacity: 0.45; }
.word-active { opacity: 1; }
```

## TRANSCRIPTION API
Use Groq Whisper API for transcription:
```python
from groq import Groq
client = Groq(api_key=os.environ["GROQ_API_KEY"])

with open("audio.mp3", "rb") as f:
    result = client.audio.transcriptions.create(
        file=("audio.mp3", f.read()),
        model="whisper-large-v3-turbo",
        response_format="verbose_json",
        timestamp_granularities=["word", "segment"]
    )
words = [{"word": w.word, "start": w.start, "end": w.end} for w in result.words]
```

## TECH STACK
- Backend: Python FastAPI + uvicorn
- Frontend: React + Vite (no TypeScript needed)
- Transcription: Groq Whisper API (pip install groq)
- Video: FFmpeg for audio extraction + caption burning
- Fonts: Google Fonts (Inter + Instrument Serif via CSS @import)
- State: React useState/useEffect (no Redux needed)
- Styling: Plain CSS (no Tailwind needed, write custom CSS matching the site's style)

## BACKEND ENDPOINTS
POST /api/upload — save video, return {file_id, duration, thumbnail_url}
POST /api/transcribe/{file_id} — transcribe, return {words: [{word, start, end, emphasis}]}
GET  /api/preview/{style_id} — return HTML snippet for live caption preview iframe
POST /api/render — burn captions, return {output_url, srt_url, ass_url}
GET  /api/files/{file_id} — serve the rendered file

## WORD GROUPING LOGIC
Group words into phrases of 2-3 words max. Mark the LAST word of each phrase as emphasis=true.
Show the whole phrase, highlight the current word (full opacity), dim others (0.45 opacity).

## FFmpeg COMMANDS
Extract audio: ffmpeg -i input.mp4 -q:a 0 -map a /tmp/audio.mp3
Burn captions: ffmpeg -i input.mp4 -vf "ass=captions.ass" -c:a copy output.mp4

## UI DESIGN
Match the Captionizer website style:
- Left column: video preview (9:16 aspect ratio, dark background, rounded corners)  
- Right panel: controls (upload, style picker, position slider, word size slider, color swatches)
- Word editor: scrollable list of phrase boxes, each with word chips (dark background chips, clickable)
- Dark/light theme toggle
- Color scheme: --accent: #B5532F (rust/orange), clean sans-serif UI

## PROJECT STRUCTURE
caption-app/
├── backend/
│   ├── main.py
│   ├── transcribe.py
│   ├── renderer.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/VideoUpload.jsx
│   │   ├── components/StylePicker.jsx
│   │   ├── components/CaptionPreview.jsx
│   │   ├── components/TranscriptEditor.jsx
│   │   ├── components/ControlPanel.jsx
│   │   └── styles/app.css
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── README.md

## SETUP REQUIREMENTS
- Python 3.10+
- Node 18+
- FFmpeg installed
- GROQ_API_KEY environment variable set

Build the COMPLETE, WORKING app with all files. Make it actually run with:
  cd backend && pip install -r requirements.txt && uvicorn main:app --reload
  cd frontend && npm install && npm run dev
```

---

## HOW TO USE THIS PROMPT

1. Open a **new chat** in Antigravity IDE
2. Use the `/goal` command for best results (it keeps the AI working until done)
3. Paste the entire code block above
4. The AI will build all files in `e:\CODE\Projects\Test\caption-app\`

## BEFORE RUNNING

Get your free Groq API key:
1. Go to https://console.groq.com/
2. Sign up (free, no credit card)
3. Create API key
4. Set it: `set GROQ_API_KEY=your_key_here`

Install FFmpeg on Windows:
```powershell
winget install FFmpeg
# or download from https://ffmpeg.org/download.html
```
