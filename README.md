# 🎬 Captionizer Studio (All-in-One)

The full-stack video caption generator matching the exact **Captionizer** user interface and workflow, featuring the signature **Editorial Hybrid** aesthetic (Apple SF Pro / Inter ExtraBold + glowing Instrument Serif Italic).

---

## ⚡ What was built to match your screenshots:

1. **Exact 4-Tab Step Workflow (`each div to move to the next one`)**:
   - **Tab 1: 📑 Words & Transcript**:
     - Upload dropzone (MP4, MOV, WEBM for vertical reels & shorts).
     - `🗑️ Delete / Wrong Video` button.
     - `No video on hand?` card with **`🪄 Try Demo Reel`** button that instantly loads a sample 12s 9:16 reel with real timestamps!
     - `EDITABLE WORD LIST`:
       - `Words per phrase: [ 2 ] [ 3 ] [ 4 ]` selector.
       - `✨ Last word italic` button to auto-emphasize key punchlines.
       - Word chip editor: click word to fix typos, click `✦` to toggle Instrument Serif Italic glowing emphasis.
       - `▶` play button on each phrase to preview that segment in the video.
     - `Next: Caption Style →` button.
   - **Tab 2: 🎨 Caption Style**:
     - `CAPTION TYPOGRAPHY STYLE` (`✨ 8 Styles Ready`).
     - 8 Interactive Cards:
       1. **Editorial Hybrid** (`★ FEATURED HERO`): `RELENTLESS focus.`
       2. **Editorial Serif**: `Subtle mastery.`
       3. **Bold Yellow**: `LEVEL UP!`
       4. **Cyan Pop**: `Instant speed`
       5. **Yellow Tag**: `Pure GOLD`
       6. **Red Impact**: `RAW POWER`
       7. **Minimalist Mono**: `quiet clarity`
       8. **Blue Glow**: `DEEP FLOW`
     - Step buttons: `← Back: Transcript` & `Next: Position & Size →`.
   - **Tab 3: 🎛️ Position & Size**:
     - **Vertical Position**: `80% from top`, presets `[ Top (25%) ] [ Middle (50%) ] [ Bottom (80%) ]`, slider, and interactive drag on screen.
     - **Caption Font Size**: `76px`, presets `[ Compact ] [ Standard ] [ Impact ]`, and slider.
     - **Active Word Highlight Color**: 8 circular color swatches (`#FFFFFF`, `#C47D4C`, `#FACC15`, `#06B6D4`, `#84CC16`, `#F43F5E`, `#A855F7`, `#FB7185`) + custom `+` color picker.
     - Step buttons: `← Back: Caption Style` & `Next: Render & Export →`.
   - **Tab 4: 📥 Render & Export**:
     - Card: `🎞️ Render & Export Captioned Video`.
     - Giant CTA button: **`✨ Render Full Captioned Video (FFmpeg)`**.
     - Download buttons for **MP4 Video**, **SRT Subtitles**, and **ASS Subtitles**.
     - Automatically switches video player to the burned video with zero duplicate overlay!

2. **Interactive Live Preview Phone (Left Column)**:
   - Header: `LIVE PREVIEW` and `720×1280 • 12.0s`.
   - `9:16 Vertical` and `Live Canvas` badges.
   - Centered circular Play button overlay with orange gradient.
   - Real-time word highlight sync during playback.
   - Dedicated player dock with scrubber, play/pause, replay (`↺`), time display, `1x` speed, and volume/mute.
   - Bottom card: `✦ Editorial Hybrid Mode Active`.

3. **Top Bar Header**:
   - `Captionizer` title with `EDITORIAL HYBRID` badge.
   - `🗝️ API Keys •` modal for Groq Whisper.
   - `⚡ Transcribe with Groq` (and offline local AI faster-whisper fallback).
   - `🎦 Render MP4` quick action button.
   - `📁 Library` to view, load, or delete past videos and clean disk space.
   - `☀️` / `🌙` Theme toggle.

---

## 🚀 How to Run

Double-click:
```
start.bat
```
Or run in terminal:
```bash
cd E:\CODE\Projects\CAPTION
python app.py
```
Your browser will launch automatically to `http://127.0.0.1:8080`.
