# 🎰 KickStream Shorts Studio

<p align="center">
  <strong>Automated Local 9:16 Shorts Creation & Real-Time Big Win Sentinel for Kick Livestreams</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Faster--Whisper-Speech--to--Text-orange?style=flat-square" alt="Faster-Whisper">
  <img src="https://img.shields.io/badge/FFmpeg-Hardware--Accelerated-green?style=flat-square&logo=ffmpeg" alt="FFmpeg">
  <img src="https://img.shields.io/badge/Cost-100%25%20Free%20%2F%20Local-success?style=flat-square" alt="100% Free">
  <img src="https://img.shields.io/badge/License-MIT-purple?style=flat-square" alt="MIT License">
</p>

---

## ⚡ Overview

**KickStream Shorts Studio** is a local, high-performance video production automation studio designed specifically for Kick creators, casino streamers, and clip editors. It ingests 16:9 streams, detects big wins in real time with zero expensive Vision-Language-Model (VLM) API costs, transforms footage into 9:16 vertical shorts, transcribes audio into animated karaoke subtitles, adds custom affiliate promo overlays, generates high-CTR titles and descriptions, and publishes directly to YouTube Shorts with a single click.

```
+-----------------------------------------------------------------------------------------+
|                                    KICKSTREAM STUDIO                                    |
|                                                                                         |
|  [ Step 1: Ingest & Trim ]  ->  [ Step 2: 9:16 Framing ]  ->  [ Step 3: Subtitles ]  ->  [ Step 4: Export & Upload ]
|   • Live Pusher Sentinel         • Gameplay Top Reel           • Local Faster-Whisper    • Multi-thread FFmpeg
|   • Direct Kick URL Ingest       • Facecam Bottom Cam          • Word-by-Word Karaoke    • Free AI Copywriter
|   • Local Video File Upload      • 60 FPS Ambient Blur Fill    • 200px-1800px Placement  • 1-Click YouTube Upload
|   • Interactive Cut Scrubber     • Promo / Affiliate Overlays  • Live Phone Preview      • Channel Management
+-----------------------------------------------------------------------------------------+
```

---

## ✨ Key Features

### 🎰 1. Real-Time Big Win Sentinel Watchdog
- **Triple-Sensor Non-VLM Detection**: Operates 24/7 with zero costly external vision models:
  1. **Kick Pusher WebSocket Interceptor**: Listens directly to real-time events (`pusher:subscribe` to Kick chatrooms and casino channels), detecting win multipliers, jackpot alerts, and bonus rounds with sub-second latency.
  2. **Chat Velocity Spike Engine**: Tracks rolling chat message frequency per second. Massive sudden spikes (>300% above baseline) trigger highlight flags.
  3. **Clip Burst Cluster Analysis**: Monitors cluster clip creation frequency via Kick API.
- **Smart Clip Buffer**: Automatically records and buffers preceding context so streamer reactions and buildup are never cut off.

### 🎬 2. Interactive 9:16 Split Framing Studio
- **Dual Visual Stacking**: Stacks the gameplay reel on top and the streamer facecam on the bottom over a 60 FPS darkened and blurred ambient background fill.
- **Visual Cropper & Drag-and-Drop Handles**: Live WYSIWYG crop box positioning with interactive drag handles, size constraints, and instant aspect-ratio locks.
- **1-Click Layout Presets**: Center Slot + Bottom-Right Cam, Center Slot + Top-Left Cam, Roulette Table, Full 16:9 screen, or custom manual pixel coordinates.
- **Visual Promo Overlays**: Upload custom transparent PNG banners (e.g., `"USE CODE: VIP"`, `"18+ Gamble Aware"`, streamer logos) with opacity sliders and real-time canvas placement.

### 🎙️ 3. Animated Word-by-Word Karaoke AI Subtitles
- **100% Local Faster-Whisper Engine**: Transcribes speech with word-level timestamps on local CPU or GPU without sending audio to third-party paid APIs.
- **Pop-Highlight Animations**: Words dynamically enlarge and pop with custom highlight colors as they are spoken (Hormozi, Royale, Cyberpunk, and Minimal presets).
- **Pixel-Perfect ASS Positioning**: Anchored with `\an5\pos(540, Y)\q2` to guarantee subtitles never jump to default margins or line-break awkwardly.
- **Full-Range Vertical Placement**: Continuous vertical adjustment ($200\text{px}$ to $1800\text{px}$) with 4 instant placement presets (Top Reels, Center Gap, Over Cam, Bottom Safe) and live phone canvas drag support.

### 🤖 4. 100% Free AI Copywriting Engine
- **Free Gemini API Integration**: Connect a free Google AI Studio API key (`GEMINI_API_KEY`) to generate 5 high-CTR viral titles, 3 SEO descriptions, and relevant hashtags.
- **Built-in Offline Copywriter**: No API key? No problem! The built-in offline casino copywriter generates tailored titles, descriptions, and hashtags without internet access or external APIs.

### 🚀 5. 1-Click Direct YouTube Shorts Publishing
- **Integrated OAuth 2.0 Client**: Authorize your YouTube channel directly through the studio.
- **Built-in Diagnostic Probe**: Automatically tests OAuth redirect URIs before launching authentication windows, preventing confusing `redirect_uri_mismatch` errors.
- **Background Publishing**: Uploads directly to YouTube Data API v3 with title, description, tags, and category automatically filled.

---

## 🛠️ Tech Stack & Architecture

- **Backend**: Python 3.10+, [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/)
- **Frontend**: Clean Vanilla JavaScript (ES6+), [Tailwind CSS](https://tailwindcss.com/) (CDN), [Lucide Icons](https://lucide.dev/)
- **Media Engine**: [FFmpeg 7](https://ffmpeg.org/), `imageio-ffmpeg`
- **Speech Recognition**: [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2)
- **Networking**: `websockets`, `websocket-client`, `requests`, `yt-dlp`
- **Cloud APIs**: Google YouTube Data API v3, Google Gemini API (optional)

---

## 🚀 Quick Start

### 1. Prerequisites
- **Operating System**: Windows 10/11, macOS, or Linux
- **Python**: Version 3.10, 3.11, or 3.12 installed ([python.org](https://www.python.org/downloads/))
- **FFmpeg**: Required for media processing. On Windows, the studio can automatically download and localize FFmpeg binaries for you!

### 2. Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/kick-shorts-studio.git
   cd kick-shorts-studio
   ```

2. **Run Dependency Bootstrap**:
   - **On Windows**:
     Simply double-click:
     ```cmd
     run.bat
     ```
     *This script verifies Python, downloads and localizes standalone FFmpeg binaries if needed, installs dependencies from `requirements.txt`, and launches the studio.*

   - **On macOS / Linux**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
     python app.py
     ```

3. **Open the Studio**:
   Open your browser and navigate to:
   ```text
   http://127.0.0.1:7860
   ```

---

## 🔑 YouTube Upload Setup (Optional)

To publish directly from the studio to YouTube Shorts:

1. Open the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Create a project (or select an existing one) and enable the **YouTube Data API v3**.
3. Go to **Credentials** &rarr; **Create Credentials** &rarr; **OAuth client ID**.
   - **Recommended (Zero Config)**: Select **Desktop App**. Download the JSON file and upload it into Step 4 of the studio. Desktop credentials require no redirect URIs!
   - **Alternative (Web Application)**: If selecting **Web Application**, add this under **Authorized redirect URIs**:
     ```text
     http://127.0.0.1:7860/api/youtube/oauth2callback
     ```
4. In Step 4 of KickStream Studio, click **Upload client_secret.json**, then click **Connect YouTube Channel**.

---

## 🧪 Running Automated Tests

KickStream Studio includes a comprehensive automated test suite verifying every component from video ingestion to ASS subtitle generation and YouTube authorization:

```bash
# Run studio UI flow tests (ingest, trim, crop, export, session reset)
python test_studio_ui_flow.py

# Run AI copywriter & YouTube authorization diagnostics test
python test_ai_and_youtube_flow.py

# Run overlay composition tests
python test_overlay_pipeline.py

# Run pipeline unit tests
python test_pipeline.py
```

---

## 📁 Repository Structure

```
kick-shorts-studio/
├── app.py                      # FastAPI server & REST API endpoints
├── run.bat                     # 1-click Windows launcher & environment bootstrap
├── install_dependencies.py     # Self-installing dependency & FFmpeg manager
├── requirements.txt            # Python dependencies
├── core/
│   ├── ai_copywriter.py        # Gemini API & offline casino title/description engine
│   ├── audio_detector.py       # Audio volume & cheering peak analysis
│   ├── banner_generator.py     # Pillow promo banner generation
│   ├── config.py               # Geometric defaults, crop presets & Pusher keys
│   ├── detector.py             # Pusher WebSocket listener & Sentinel watchdog
│   ├── subtitles.py            # Faster-Whisper transcription & ASS karaoke pop engine
│   ├── utils.py                # FFmpeg wrappers, geometry scaling & probe utilities
│   ├── video_ingest.py         # yt-dlp Kick clip downloader & validator
│   ├── video_processor.py      # Multi-stage FFmpeg 9:16 layout compositor
│   └── youtube_uploader.py     # OAuth 2.0 authentication & YouTube upload dispatcher
├── templates/
│   └── index.html              # Single-page studio interface (4-step stepper wizard)
├── credentials/
│   ├── .gitkeep
│   └── client_secret.json.example
├── output/                     # Rendered 9:16 vertical shorts (ignored by git)
│   └── .gitkeep
├── temp/                       # Temporary media working files (ignored by git)
│   └── .gitkeep
├── tests_fixtures/             # Small test fixtures (<1MB) for test suite
└── LICENSE                     # MIT License
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with ❤️ for livestream creators and video editors.
</p>
