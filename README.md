# ⚡ OmniStream Shorts Studio (Kick & Twitch)

<p align="center">
  <strong>Universal Stream-to-Shorts Production Automation & Real-Time Hype Sentinel for Kick & Twitch</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platforms-Kick%20%7C%20Twitch-purple?style=flat-square" alt="Kick and Twitch">
  <img src="https://img.shields.io/badge/Categories-Gaming%20%7C%20IRL%20%7C%20Podcasts%20%7C%20Casino-blue?style=flat-square" alt="All Stream Types">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Speech-Faster--Whisper-orange?style=flat-square" alt="Faster-Whisper">
  <img src="https://img.shields.io/badge/Cost-100%25%20Free%20%2F%20Zero%20API%20Keys-success?style=flat-square" alt="100% Free">
  <img src="https://img.shields.io/badge/License-MIT-purple?style=flat-square" alt="MIT License">
</p>

---

## ⚡ Overview

**OmniStream Shorts Studio** is a 100% free, local-first video production studio that turns full-length 16:9 livestreams and clips from **Kick** and **Twitch** into viral 9:16 vertical shorts (YouTube Shorts, TikTok, Instagram Reels) with sub-second responsiveness.

Supports all major stream categories:
- 🎮 **Gaming & Esports** (Valorant, CS2, Fortnite, League of Legends, Apex Legends, GTA V)
- 💬 **Just Chatting, IRL & Reactions** (Webcam bottom + React video top, drama, storytime)
- 🎙️ **Podcasts & Dual Cam** (Split top guest + bottom host interview mode)
- 🎰 **Casino & Slots** (Slot reels, multipliers, jackpot alerts)
- 📱 **Ambient Blur 16:9** (Centered gameplay with dynamic blurred background fill)

```
+-----------------------------------------------------------------------------------------+
|                                  OMNISTREAM STUDIO                                      |
|                                                                                         |
|  [ Step 1: Ingest & Trim ]  ->  [ Step 2: 9:16 Framing ]  ->  [ Step 3: Subtitles ]  ->  [ Step 4: Export & Upload ]
|   • Kick (Pusher WebSocket)      • Categorized Presets         • Local Faster-Whisper    • Multi-thread FFmpeg
|   • Twitch (Anonymous IRC & GQL) • 60 FPS Ambient Blur Fill    • Word-by-Word Karaoke    • Multi-Niche AI Copywriter
|   • Clips URL Auto-Detect        • Drag & Drop Resize Handles  • Vertical Pos (200-1800) • 1-Click YouTube Upload
|   • Audio Energy Climax Scan     • Promo Code Banner Maker     • Neon Gamer / Rage Red   • Zero Paid API Keys
+-----------------------------------------------------------------------------------------+
```

---

## ✨ Key Features

### 📡 1. Universal Real-Time Hype Sentinel Watchdog (Kick & Twitch)
- **Zero API Key Architecture**: Connects without requiring any paid API keys, logins, or developer accounts:
  1. **Twitch Anonymous IRC WebSocket (`wss://irc-ws.chat.twitch.tv:443`)**: Listens directly to Twitch chatrooms with zero tokens (`NICK justinfan<random>`), tracking chat velocity and hype emote bursts (`POG`, `KEKW`, `LUL`, `CLUTCH`, `ACE`, `W`, etc.).
  2. **Twitch Public GQL (`https://gql.twitch.tv/gql`)**: Queries and discovers recent top channel clips and view milestones instantly.
  3. **Kick Pusher WebSocket**: Intercepts real-time events (`chatrooms.<id>.v2`), detecting big wins, multipliers, and chat bursts.
- **Category-Aware Filters**: Switch between Gaming, Just Chatting, Casino, or All Streams to filter relevant hype moments.
- **Audio Climax Pinpointing**: Lightweight RMS energy waveform scanning pinpoints shouts, celebrations, and volume peaks to auto-trim 20s clips.

### 🎬 2. Universal 9:16 Visual Framing Studio
- **Categorized Presets**:
  - `🎮 Gaming FPS`: Crosshair/Gameplay top + Streamer webcam bottom right.
  - `⚔️ Gaming MOBA`: Minimap-safe top view + Streamer camera.
  - `🎯 Gaming Centered`: Focused screen center + camera.
  - `💬 Reaction Standard`: 60% reaction media top + 40% streamer facecam.
  - `👥 Dual Cam / Interview`: 50/50 vertical split for podcasts and guest interviews.
  - `🎰 Casino Royale`: Big slot reel center + camera.
  - `✨ Ambient Blur 16:9`: Full 16:9 screen centered with 60 FPS mirrored blurred background.
- **Interactive Drag & Resize Handles**: Move and adjust crop boxes directly on the canvas with real-time iPhone 9:16 preview.
- **Cover Photo & Promo Banner Maker**: Generate transparent promo banners (e.g. `"USE CODE: VIP"`) or upload your own logos to cover unwanted stream HUD elements or balances.

### 🎙️ 3. Animated Word-by-Word Karaoke AI Subtitles
- **100% Local Faster-Whisper Engine**: Transcribes speech with word-level precision on CPU/GPU without sending audio to paid APIs.
- **Preset Styles**:
  - `🔥 Hormozi`: Bold font with vibrant golden highlight.
  - `🎮 Neon Gamer`: Electric cyan with neon lime highlight.
  - `🔴 Rage Red`: Clean white with crimson red highlight.
  - `⚡ Cyberpunk`: Neon cyan with hot pink highlight.
  - `✨ Minimal`: Clean modern subtitles.
- **Pixel-Perfect ASS Subtitle Positioning**: Drag and adjust height ($200\text{px}$ to $1800\text{px}$) with instant placement pills (Top Reels, Center Gap, Over Cam, Bottom Safe).

### 🤖 4. Multi-Category AI Shorts Copywriter
- **Niche-Specific Copy Generation**: Generates 5 viral title hooks and 3 complete description variants with hashtags tailored to:
  - 🎮 **Gaming & Esports** (Clutch, Ace, Pog, Ranked Highlights)
  - 💬 **Just Chatting & IRL** (Drama, Reactions, Unfiltered moments)
  - 🎰 **Casino & Slots** (Multipliers, Jackpot, High Roller)
  - 🌐 **General Streams**
- **100% Free Offline Engine**: Operates locally out-of-the-box. Optional free Google Gemini or Groq API keys can be added for extra variety.

### 🚀 5. 1-Click Direct YouTube Shorts Publishing
- **Built-in Google OAuth 2.0 Client**: Connect your YouTube channel and publish vertical shorts directly from the studio.
- **Zero-Config Desktop Mode**: Drop in a Desktop Application `client_secret.json` from Google Cloud Console with zero redirect URI configuration needed.
- **Built-in Diagnostic Probe**: Pre-validates redirect URIs to prevent `redirect_uri_mismatch` errors.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Operating System**: Windows 10/11, macOS, or Linux
- **Python**: Version 3.10, 3.11, or 3.12+ installed ([python.org](https://www.python.org/downloads/))
- **FFmpeg**: Handled automatically on Windows via bootstrap scripts.

### 2. Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/bogdandruta771-dot/kick-shorts-studio.git
   cd kick-shorts-studio
   ```

2. **Run Dependency Bootstrap**:
   - **On Windows**:
     Double-click `run.bat` or run:
     ```powershell
     python -m pip install -r requirements.txt
     python app.py
     ```
   - **On macOS / Linux**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
     python app.py
     ```

3. **Open Studio**:
   Open your browser to:
   ```text
   http://127.0.0.1:7860
   ```

---

## 🧪 Running Automated Tests

Run the test suites verifying Twitch ingestion, Kick sentinels, AI copywriter, and subtitle pipelines:

```bash
# Run Universal Stream & Twitch test suite
python -m pytest test_universal_and_twitch.py

# Run AI Copywriter & YouTube OAuth diagnostics
python test_ai_and_youtube_flow.py

# Run overlay pipeline tests
python test_overlay_pipeline.py
```

---

## 📄 License

This project is licensed under the MIT License.
