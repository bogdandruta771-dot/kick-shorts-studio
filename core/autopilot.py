"""
OmniStudio 24/7 Autopilot Automation Factory.
Fully automates the video pipeline from A to Z:
1. Autonomous Topic Selection / Trend Discovery
2. Scriptwriting & Hook Optimization
3. Neural Voiceover (Edge-TTS / ElevenLabs) & Whisper Word Timing
4. Automated HD B-Roll Sourcing (Pexels / Pixabay / Procedural Canvas)
5. Audio Ducking & Bouncing ASS Subtitles
6. Sponsor & Affiliate Card Splicing (TradeIt mesto300)
7. SEO Copywriting (High-CTR Titles, Descriptions, Tags)
8. Direct YouTube Shorts Publishing & Duplicate Shield Database Logging
"""

import os
import re
import json
import time
import uuid
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from core.faceless_engine import (
    generate_faceless_script,
    render_faceless_short,
)
from core.ai_copywriter import generate_shorts_metadata
from core.ai_virality_scorer import score_stream_transcript
from core.youtube_uploader import upload_shorts_video, list_youtube_accounts, get_youtube_auth_status
from core.clip_history import record_clipped_short
from core.config import OUTPUT_DIR


AUTOPILOT_TOPIC_BANK = [
    "The $1.5M CS2 Knife That Vanished 🗡️",
    "Why CS2 Cases Are So Addictive 📦",
    "The Most Expensive Mistakes in Esports History 🎮",
    "Top 3 CS2 Skins That Made Players Millionaires 💰",
    "How One Player Traded a $5 Skin into a Dragon Lore 📈",
    "The Dark Psychology of Mystery Case Openings 🧠",
    "Why Valve Banned the Rarest Skin in History 🚫",
    "The $500,000 Blue Gem Karambit Mystery 💎",
    "Crazy CS2 Skin Trades That Shook the Community ⚡",
    "How Pro Players Make Millions from In-Game Stickers 🏆"
]


class AutopilotEngine:
    """Manages the fully autonomous background shorts production factory."""

    def __init__(self):
        self.is_running: bool = False
        self.mode: str = "faceless"  # 'faceless', 'stream', 'hybrid'
        self.interval_minutes: int = 180  # Default every 3 hours
        self.daily_quota: int = 4
        self.published_today: int = 0
        self.auto_upload_to_youtube: bool = False
        self.custom_topics_queue: List[str] = []
        self.voice_id: str = "en-US-ChristopherNeural"
        self.subtitle_preset: str = "submagic_yellow"
        self.include_affiliate: bool = True
        self.promo_code: str = "mesto300"
        self.logs: List[Dict[str, Any]] = []
        self.last_run_time: Optional[float] = None
        self.next_run_time: Optional[float] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def log(self, message: str, level: str = "info"):
        entry = {
            "timestamp": time.strftime("%H:%M:%S"),
            "level": level,
            "message": message
        }
        self.logs.append(entry)
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]
        try:
            print(f"[Autopilot {level.upper()}] {message}")
        except Exception:
            clean_msg = message.encode("ascii", "replace").decode("ascii")
            print(f"[Autopilot {level.upper()}] {clean_msg}")

    def get_next_topic(self) -> str:
        """Retrieves next topic from user queue or rotates through high-CTR topic bank."""
        if self.custom_topics_queue:
            return self.custom_topics_queue.pop(0)
        idx = self.published_today % len(AUTOPILOT_TOPIC_BANK)
        return AUTOPILOT_TOPIC_BANK[idx]

    def run_single_faceless_cycle(
        self,
        topic: Optional[str] = None,
        auto_upload: Optional[bool] = None,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes a complete A-to-Z production run for a single short:
        Topic -> Script -> Audio -> B-Roll -> Ducking -> Subtitles -> SEO -> YouTube Upload.
        """
        selected_topic = topic or self.get_next_topic()
        should_upload = self.auto_upload_to_youtube if auto_upload is None else auto_upload

        self.log(f"Starting A-to-Z Autonomous Cycle for topic: '{selected_topic}'")
        if progress_cb:
            progress_cb(0.10, f"Generating viral script for '{selected_topic}'...")

        # Step 1: Scriptwriting
        script = generate_faceless_script(
            topic=selected_topic,
            provider="auto",
            include_affiliate=self.include_affiliate,
            promo_code=self.promo_code
        )
        self.log(f"Script generated: '{script.get('title')}' ({len(script.get('segments', []))} beats)")

        if progress_cb:
            progress_cb(0.35, "Synthesizing voiceover, downloading B-Roll & burning subtitles...")

        # Step 2: Render 1080x1920 60fps Short
        out_filename = f"autopilot_{re.sub(r'[^a-zA-Z0-9]', '_', selected_topic)[:15]}_{int(time.time())}.mp4"
        render_res = render_faceless_short(
            script_data=script,
            voice_id=self.voice_id,
            subtitle_preset=self.subtitle_preset,
            output_filename=out_filename,
            bgm_volume=0.14
        )
        video_path = Path(render_res["video_path"])
        self.log(f"Video rendered successfully: {out_filename} ({render_res['duration']}s)")

        if progress_cb:
            progress_cb(0.75, "Generating SEO metadata, high-CTR titles and hashtags...")

        # Step 3: SEO Copywriting
        full_text = " ".join(seg.get("text", "") for seg in script.get("segments", []))
        meta = generate_shorts_metadata(
            clip_title=script.get("title", selected_topic),
            streamer="OmniStudio",
            transcript=full_text,
            promo_code=self.promo_code,
            provider="auto"
        )
        chosen_title = meta["titles"][0] if meta.get("titles") else script.get("title")
        description = meta["descriptions"][0] if meta.get("descriptions") else ""
        hashtags = meta.get("hashtags", ["#Shorts", "#CS2", "#Gaming"])
        full_description = f"{description}\n\n{' '.join(hashtags)}\n\nUse code {self.promo_code} on TradeIt for an instant 5% bonus!"

        # Step 4: Record in Clip History Anti-Repeat Database
        record_clipped_short(
            source_url="autopilot://faceless",
            output_filename=out_filename,
            title=chosen_title,
            channel="Autopilot Studio",
            duration=render_res.get("duration", 0.0),
            preset="autopilot_a_to_z",
            ai_title=chosen_title
        )

        upload_result = None
        # Step 5: Direct YouTube Shorts Upload if enabled
        if should_upload:
            auth_status = get_youtube_auth_status()
            if auth_status.get("authenticated"):
                if progress_cb:
                    progress_cb(0.90, "Publishing short directly to YouTube...")
                self.log(f"Uploading to YouTube Shorts: '{chosen_title}'...")
                try:
                    upload_result = upload_shorts_video(
                        video_path=video_path,
                        title=chosen_title[:100],
                        description=full_description,
                        tags=hashtags,
                        privacy_status="public"
                    )
                    self.log(f"Short published live to YouTube! (Video ID: {upload_result.get('video_id', 'uploaded')})")
                except Exception as exc:
                    self.log(f"Notice: YouTube upload encountered an error ({exc}). Video is safely saved locally.", level="warn")
            else:
                self.log("Notice: YouTube account not authenticated yet. Video saved locally in outputs folder.", level="warn")

        self.published_today += 1
        self.last_run_time = time.time()
        if progress_cb:
            progress_cb(1.0, f"Cycle complete! Video ready: {out_filename}")

        return {
            "success": True,
            "filename": out_filename,
            "video_url": f"/outputs/{out_filename}",
            "duration": render_res["duration"],
            "title": chosen_title,
            "description": full_description,
            "hashtags": hashtags,
            "uploaded": bool(upload_result),
            "upload_info": upload_result
        }

    def _worker_loop(self):
        """Continuous background execution loop."""
        self.log(f"Autopilot daemon activated. Running every {self.interval_minutes} minutes.")
        while not self._stop_event.is_set():
            try:
                self.run_single_faceless_cycle()
            except Exception as exc:
                self.log(f"Autopilot cycle error: {exc}", level="error")

            # Sleep in small increments for graceful interruption
            wait_seconds = max(60, self.interval_minutes * 60)
            self.next_run_time = time.time() + wait_seconds
            for _ in range(wait_seconds):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

        self.log("Autopilot daemon safely stopped.")

    def start(
        self,
        interval_minutes: int = 180,
        daily_quota: int = 4,
        auto_upload: bool = False,
        voice_id: str = "en-US-ChristopherNeural",
        subtitle_preset: str = "submagic_yellow"
    ) -> Dict[str, Any]:
        """Starts the 24/7 autonomous factory background daemon."""
        if self.is_running:
            return {"success": False, "message": "Autopilot is already running."}

        self.interval_minutes = max(10, interval_minutes)
        self.daily_quota = daily_quota
        self.auto_upload_to_youtube = auto_upload
        self.voice_id = voice_id
        self.subtitle_preset = subtitle_preset

        self._stop_event.clear()
        self.is_running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

        return {
            "success": True,
            "status": "running",
            "interval_minutes": self.interval_minutes,
            "auto_upload": self.auto_upload_to_youtube,
            "message": f"Autopilot running in background every {self.interval_minutes} minutes."
        }

    def stop(self) -> Dict[str, Any]:
        """Stops the autonomous factory."""
        if not self.is_running:
            return {"success": False, "message": "Autopilot is not running."}

        self._stop_event.set()
        self.is_running = False
        return {"success": True, "status": "stopped", "message": "Autopilot stopped."}

    def get_status(self) -> Dict[str, Any]:
        """Returns live autopilot telemetry and status."""
        return {
            "is_running": self.is_running,
            "mode": self.mode,
            "interval_minutes": self.interval_minutes,
            "published_today": self.published_today,
            "daily_quota": self.daily_quota,
            "auto_upload_to_youtube": self.auto_upload_to_youtube,
            "last_run_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.last_run_time)) if self.last_run_time else None,
            "next_run_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.next_run_time)) if (self.is_running and self.next_run_time) else None,
            "queued_topics_count": len(self.custom_topics_queue),
            "logs": self.logs[-20:]
        }


# Global singleton instance
autopilot = AutopilotEngine()
