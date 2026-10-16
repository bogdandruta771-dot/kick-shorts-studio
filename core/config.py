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

# Anti-Shadowban Algorithm Disruption & Compliance Defaults
ENABLE_ANTI_SHADOWBAN = True

# Universal Stream HUD Crop Presets (Gaming, Reaction, Podcast, Casino, Fullscreen)
CROP_PRESETS: Dict[str, Dict[str, Any]] = {
    # --- 🎮 Gaming & Esports ---
    "gaming_fps": {
        "label": "🎮 Gaming: FPS & Shooters (Crosshair Top + Cam)",
        "gameplay": {"x": 160, "y": 0, "w": 1600, "h": 900},
        "facecam": {"x": 1440, "y": 720, "w": 480, "h": 360},
    },
    "gaming_moba": {
        "label": "⚔️ Gaming: MOBA (League, Dota 2 - Minimap Safe)",
        "gameplay": {"x": 0, "y": 40, "w": 1560, "h": 1000},
        "facecam": {"x": 1400, "y": 660, "w": 520, "h": 420},
    },
    "gaming_centered": {
        "label": "🎯 Gaming: Centered Action (HUD Focus)",
        "gameplay": {"x": 240, "y": 80, "w": 1440, "h": 920},
        "facecam": {"x": 700, "y": 720, "w": 520, "h": 360},
    },

    # --- 💬 Reaction & Just Chatting ---
    "reaction_cam_top": {
        "label": "👑 OhnePixel Style: Top Facecam + Bottom Video Reaction",
        "gameplay": {"x": 0, "y": 0, "w": 1360, "h": 1080},
        "facecam": {"x": 1360, "y": 460, "w": 560, "h": 620},
        "stack_mode": "cam_top",
    },
    "reddit_reaction": {
        "label": "🔥 Reddit Post Reaction (Top Facecam + Bottom Reddit/Gameplay)",
        "gameplay": {"x": 0, "y": 0, "w": 1360, "h": 1080},
        "facecam": {"x": 1360, "y": 460, "w": 560, "h": 620},
        "stack_mode": "cam_top",
    },
    "reaction_standard": {
        "label": "💬 Reaction: Top 16:9 Video + Bottom Streamer Webcam",
        "gameplay": {"x": 0, "y": 0, "w": 1360, "h": 1080},
        "facecam": {"x": 1360, "y": 460, "w": 560, "h": 620},
        "stack_mode": "standard",
    },
    "reaction_interview": {
        "label": "👥 Dual Cam / Split Screen (50/50 Interview)",
        "gameplay": {"x": 0, "y": 0, "w": 960, "h": 1080},
        "facecam": {"x": 960, "y": 0, "w": 960, "h": 1080},
    },

    # --- 🎙️ Podcasts & Shows ---
    "podcast_split": {
        "label": "🎙️ Podcast / Dual Host: Split Top Guest + Bottom Host",
        "gameplay": {"x": 40, "y": 80, "w": 900, "h": 920},
        "facecam": {"x": 980, "y": 80, "w": 900, "h": 920},
    },

    # --- 🎰 Casino & Slots ---
    "center_slot": {
        "label": "🎰 Casino: Center Slot (Main Reel) + Bottom-Right Camera",
        "gameplay": {"x": 260, "y": 80, "w": 1400, "h": 920},
        "facecam": {"x": 1380, "y": 680, "w": 520, "h": 380},
    },
    "roulette_table": {
        "label": "🎲 Casino: Live Dealer Table / Roulette + Bottom-Left Camera",
        "gameplay": {"x": 100, "y": 60, "w": 1720, "h": 960},
        "facecam": {"x": 40, "y": 680, "w": 540, "h": 380},
    },
    "full_reel": {
        "label": "🎰 Casino: Full Slot Grid + Bottom Camera",
        "gameplay": {"x": 0, "y": 0, "w": 1920, "h": 1080},
        "facecam": {"x": 1360, "y": 680, "w": 540, "h": 380},
    },

    # --- 📱 Ambient & Custom ---
    "ambient_blur_16_9": {
        "label": "📱 Full 16:9 Ambient: Center Fit with Blurred Dynamic Fill",
        "gameplay": {"x": 0, "y": 0, "w": 1920, "h": 1080},
        "facecam": {"x": 0, "y": 0, "w": 1920, "h": 1080},
    },
    "custom": {
        "label": "✏️ Custom / Manual Coordinates",
        "gameplay": {"x": 260, "y": 80, "w": 1400, "h": 920},
        "facecam": {"x": 1380, "y": 680, "w": 520, "h": 380},
    },
}

# Subtitle Styling Defaults
DEFAULT_FONT_NAME = "Arial"
DEFAULT_FONT_SIZE = 48
DEFAULT_PRIMARY_COLOR = "#FFFFFF"     # Clean White
DEFAULT_HIGHLIGHT_COLOR = "#FFD700"   # Golden Yellow / Pop
DEFAULT_OUTLINE_COLOR = "#000000"     # Heavy Black
DEFAULT_OUTLINE_WIDTH = 4
DEFAULT_SHADOW_DEPTH = 2
DEFAULT_SUBTITLE_Y_OFFSET = 1000      # Placed in the vertical sweet-spot

# Kick Live Pusher Constants
DEFAULT_PUSHER_KEYS = [
    "32cbd69e4b950bf97679",
    "eb1d5f283081a78b932c",
]
DEFAULT_PUSHER_CLUSTER = "us2"

# Twitch Live IRC & GQL Constants (Zero API Key / Zero Cost Anonymous Access)
TWITCH_IRC_WS_URL = "wss://irc-ws.chat.twitch.tv:443"
TWITCH_GQL_URL = "https://gql.twitch.tv/gql"
TWITCH_GQL_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"

# Detection Thresholds
DEFAULT_MIN_WIN_AMOUNT = 100.0        # Minimum dollar amount ($100.00)
DEFAULT_MIN_MULTIPLIER = 50.0        # Minimum multiplier (50x)
CLIP_BURST_WINDOW_SEC = 60            # Window in seconds for clip burst detection
CLIP_BURST_MIN_COUNT = 2              # Abnormally high clip creation frequency threshold
CHAT_VELOCITY_WINDOW_SEC = 60         # Window in seconds for rolling baseline chat velocity
CHAT_VELOCITY_SPIKE_RATIO = 3.0       # > 300% spike over baseline
DEFAULT_POLL_INTERVAL_SEC = 10        # Clip API polling interval

# Stream Category Keyword Dictionaries
GAMING_KEYWORDS = [
    "POG", "POGCHAMP", "POGGERS", "W", "ACE", "CLUTCH", "CLIP IT", "CLIP THAT",
    "WHAT", "NO WAY", "INSANE", "BROOO", "SHEESH", "LMAO", "LMAOOO", "KEKW",
    "OMEGALUL", "LUL", "GG", "WTF", "HEADSHOT", "1V5", "EZ", "HOLY", "OMG",
    "BOOM", "CRACKED", "GOAT", "DIFF", "RAGE", "WIN", "BRO", "NO SHOT"
]

IRL_KEYWORDS = [
    "DRAMA", "EXPOSED", "CAUGHT", "REAL", "W STREAM", "LMAOOO", "💀", "😭",
    "🔥", "OMG", "NO SHOT", "SUS", "DEAD", "WAIT WHAT", "W", "BRO", "WHAAAT",
    "KEKW", "LUL", "OMEGALUL", "RIP"
]

CASINO_KEYWORDS = [
    "BIG WIN", "MAX WIN", "JACKPOT", "HANDPAY", "$$$", "BONUS", "500X",
    "1000X", "WIN", "BOOM", "HUGE", "MASSIVE", "LETS GO"
]

# Legacy and Unified Hype Keywords
WIN_KEYWORDS = CASINO_KEYWORDS
ALL_HYPE_KEYWORDS = list(dict.fromkeys(GAMING_KEYWORDS + IRL_KEYWORDS + CASINO_KEYWORDS))

