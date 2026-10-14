"""Configuration and constants for Kick Shorts Studio."""
from pathlib import Path
from typing import Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / "temp"
OUTPUT_DIR = BASE_DIR / "output"
BIN_DIR = BASE_DIR / "bin"

# Ensure runtime directories exist
TEMP_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
BIN_DIR.mkdir(parents=True, exist_ok=True)

# Process & Network Timeouts (Seconds)
DEFAULT_TIMEOUT = 120
DOWNLOAD_TIMEOUT = 300
TRANSCRIBE_TIMEOUT = 300
RENDER_TIMEOUT = 450
MAX_RETRIES = 2
RETRY_BACKOFF_FACTOR = 1.5

# Video Geometry Defaults (9:16 Canvas)
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
DEFAULT_FPS = 30
AUDIO_SAMPLE_RATE = 48000
AUDIO_CHANNELS = 2

# HUD Crop Presets (Assuming standard 1920x1080 source clip)
CROP_PRESETS: Dict[str, Dict[str, Any]] = {
    "🎯 Center Slot (Main Reel) + Bottom-Right Camera": {
        "gameplay": {"x": 260, "y": 80, "w": 1400, "h": 920},
        "facecam": {"x": 1380, "y": 680, "w": 520, "h": 380},
    },
    "🎯 Center Slot (Main Reel) + Top-Left Camera": {
        "gameplay": {"x": 260, "y": 80, "w": 1400, "h": 920},
        "facecam": {"x": 20, "y": 20, "w": 520, "h": 380},
    },
    "🎯 Center Slot (Main Reel) + Bottom-Left Camera": {
        "gameplay": {"x": 260, "y": 80, "w": 1400, "h": 920},
        "facecam": {"x": 20, "y": 680, "w": 520, "h": 380},
    },
    "🎯 Center Slot (Main Reel) + Top-Right Camera": {
        "gameplay": {"x": 260, "y": 80, "w": 1400, "h": 920},
        "facecam": {"x": 1380, "y": 20, "w": 520, "h": 380},
    },
    "🎰 Full 16:9 Screen (Whole Game) + Bottom-Right Camera": {
        "gameplay": {"x": 0, "y": 0, "w": 1920, "h": 1080},
        "facecam": {"x": 1400, "y": 700, "w": 500, "h": 360},
    },
    "🎰 Full 16:9 Screen (Whole Game) + Bottom-Left Camera": {
        "gameplay": {"x": 0, "y": 0, "w": 1920, "h": 1080},
        "facecam": {"x": 20, "y": 700, "w": 500, "h": 360},
    },
    "🎲 Live Dealer Table / Roulette + Bottom-Left Camera": {
        "gameplay": {"x": 160, "y": 40, "w": 1600, "h": 1000},
        "facecam": {"x": 40, "y": 660, "w": 520, "h": 390},
    },
    "🎲 Live Dealer Table / Roulette + Bottom-Right Camera": {
        "gameplay": {"x": 160, "y": 40, "w": 1600, "h": 1000},
        "facecam": {"x": 1360, "y": 660, "w": 520, "h": 390},
    },
    "👑 Huge Facecam (Big Reaction) + Centered Slot": {
        "gameplay": {"x": 300, "y": 100, "w": 1320, "h": 850},
        "facecam": {"x": 1240, "y": 550, "w": 660, "h": 510},
    },
    "✏️ Custom / Manual Coordinates": {
        "gameplay": {"x": 260, "y": 80, "w": 1400, "h": 920},
        "facecam": {"x": 1380, "y": 680, "w": 520, "h": 380},
    },
}

# Subtitle Styling Defaults
DEFAULT_FONT_NAME = "Arial"
DEFAULT_FONT_SIZE = 48
DEFAULT_PRIMARY_COLOR = "#FFFFFF"     # Clean White
DEFAULT_HIGHLIGHT_COLOR = "#FFD700"   # Casino Golden Yellow
DEFAULT_OUTLINE_COLOR = "#000000"     # Heavy Black
DEFAULT_OUTLINE_WIDTH = 4
DEFAULT_SHADOW_DEPTH = 2
DEFAULT_SUBTITLE_Y_OFFSET = 1000      # Placed in the vertical sweet-spot

# Kick Big Win Detector Constants (Non-VLM Event Engine)
DEFAULT_PUSHER_KEYS = [
    "32cbd69e4b950bf97679",
    "eb1d5f283081a78b932c",
]
DEFAULT_PUSHER_CLUSTER = "us2"
DEFAULT_MIN_WIN_AMOUNT = 100.0        # Minimum dollar amount ($100.00)
DEFAULT_MIN_MULTIPLIER = 50.0        # Minimum multiplier (50x)
CLIP_BURST_WINDOW_SEC = 60            # Window in seconds for clip burst detection
CLIP_BURST_MIN_COUNT = 2              # Abnormally high clip creation frequency threshold
CHAT_VELOCITY_WINDOW_SEC = 60         # Window in seconds for rolling baseline chat velocity
CHAT_VELOCITY_SPIKE_RATIO = 3.0       # > 300% spike over baseline
DEFAULT_POLL_INTERVAL_SEC = 10        # Clip API polling interval
WIN_KEYWORDS = [
    "W", "WIN", "MASSIVE", "BIG WIN", "MAX WIN", "JACKPOT",
    "$$$", "OMG", "LETS GO", "BOOM", "HUGE", "CLIP", "BONUS"
]
