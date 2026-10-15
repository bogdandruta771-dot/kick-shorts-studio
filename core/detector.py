"""Kick Stream Big Win Detector & Dual-Sentinel Event Engine (Non-VLM).

Components:
- WinExtractor: Regex parser for dollar amounts and multipliers.
- KickClipPulseSentinel: Sentinel A - Polls clips endpoint, detects clip creation bursts and big win titles.
- KickPusherChatSentinel: Sentinel B - Pusher WebSocket listener, tracks chat velocity and keyword spikes.
- KickWatchdogManager: Orchestrates live monitoring threads, state aggregation, and studio ingestion.
"""
import json
import re
import time
import threading
import urllib.request
import urllib.error
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable

from core.config import (
    DEFAULT_PUSHER_KEYS,
    DEFAULT_PUSHER_CLUSTER,
    DEFAULT_MIN_WIN_AMOUNT,
    DEFAULT_MIN_MULTIPLIER,
    CLIP_BURST_WINDOW_SEC,
    CLIP_BURST_MIN_COUNT,
    CHAT_VELOCITY_WINDOW_SEC,
    CHAT_VELOCITY_SPIKE_RATIO,
    DEFAULT_POLL_INTERVAL_SEC,
    WIN_KEYWORDS,
    GAMING_KEYWORDS,
    IRL_KEYWORDS,
    CASINO_KEYWORDS,
    ALL_HYPE_KEYWORDS,
    TWITCH_IRC_WS_URL,
    DEFAULT_TIMEOUT,
)


def sanitize_channel_slug(raw: str) -> str:
    """Sanitizes user input (Kick URL, Twitch URL, path, or raw username) into a clean channel slug."""
    if not raw:
        return ""
    clean = raw.strip()
    clean = re.sub(r"^https?://(?:www\.|clips\.)?twitch\.tv/", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^https?://(?:www\.)?kick\.com/", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^(?:www\.|clips\.)?twitch\.tv/", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^(?:www\.)?kick\.com/", "", clean, flags=re.IGNORECASE)
    clean = clean.lstrip("/@#")
    if "/" in clean:
        clean = clean.split("/")[0]
    if "?" in clean:
        clean = clean.split("?")[0]
    if "#" in clean:
        clean = clean.split("#")[0]
    return clean.strip().lower()


class WinExtractor:
    """Enhanced Regex-based parser for win amounts, multipliers, suffixes, and threshold filtering."""

    # Multiplier specific regex patterns: supports "120x", "500X", "1,030x", "10,000X", "x250", "x 1500"
    MULTIPLIER_REGEX = re.compile(
        r"(?:^|[^\w])(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*[xX]\b|\b[xX]\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\b|"
        r"\b(\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?\s*(?:times|multi|multiplier)\b",
        re.IGNORECASE,
    )

    # Number with magnitude suffix (k, m, mil, mill, b) e.g. "50k", "19k", "1.2m", "9 mill", "$250K"
    SUFFIX_AMOUNT_REGEX = re.compile(
        r"(?:[\$€£]|(?:\b(?:usd|eur|gbp|cad|aud)\s*))?(\d+(?:\.\d+)?)\s*(k|m|mil|mill|million|b|billion)\b",
        re.IGNORECASE,
    )

    # Explicit currency amount patterns including symbols and words (e.g. "$450", "€1,250.50", "500 dollars", "2,000 USD", "CA$5,000")
    CURRENCY_AMOUNT_REGEX = re.compile(
        r"(?:[\$€£]|ca\$|a\$|nz\$|r\$)\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)|"
        r"([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)\s*(?:usd|eur|gbp|cad|aud|dollars?|bucks?|euros?|pounds?|kr|zł|₺|\$|€|£)",
        re.IGNORECASE,
    )

    # Primary general win amount regex
    PRIMARY_AMOUNT_REGEX = re.compile(
        r"(?:\$|€|£)?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)\s*(?:\$|€|£|x|X|usd)?",
        re.IGNORECASE,
    )

    # Max win / Handpay keywords (pinnacle slot events)
    MAX_WIN_REGEX = re.compile(
        r"\b(max\s*win|maxwin|handpay|jackpot|record\s*win)\b",
        re.IGNORECASE,
    )

    @staticmethod
    def clean_number(num_str: str) -> float:
        """Converts string with commas/decimals into float."""
        try:
            return float(num_str.replace(",", "").strip())
        except (ValueError, AttributeError):
            return 0.0

    @classmethod
    def extract_win_info(
        cls,
        title: str,
        min_amount: float = DEFAULT_MIN_WIN_AMOUNT,
        min_multiplier: float = DEFAULT_MIN_MULTIPLIER,
    ) -> Optional[Dict[str, Any]]:
        """
        Parses title for dollar amounts, multipliers, and special casino win events.
        Extracts all candidates and selects the maximum win payout.
        """
        if not title:
            return None

        clean_title = title.strip()
        found_amounts = []
        found_multipliers = []
        is_max_win_keyword = bool(cls.MAX_WIN_REGEX.search(clean_title))

        # 1. Check for multipliers (e.g. 120x, 1,030x, 2,170x, x1500, 500 times)
        for m in cls.MULTIPLIER_REGEX.finditer(clean_title):
            val_str = m.group(1) or m.group(2) or m.group(3)
            if val_str:
                val = cls.clean_number(val_str)
                if 2.0 <= val <= 200000.0:
                    found_multipliers.append((val, m.group(0).strip()))

        # 2. Check for suffix numbers (e.g. 50k, 19k, 1.2m, 9 mill, 250k)
        for m in cls.SUFFIX_AMOUNT_REGEX.finditer(clean_title):
            val_str = m.group(1)
            suffix = m.group(2).lower()
            if val_str:
                val = cls.clean_number(val_str)
                mult = 1000.0 if suffix == "k" else (1000000.0 if suffix in ("m", "mil", "mill", "million") else 1000000000.0)
                total = val * mult
                if total > 0:
                    found_amounts.append((total, m.group(0).strip()))

        # 3. Check for standard currency ($450, 500 dollars, 2,000 USD, €1,250.50)
        for m in cls.CURRENCY_AMOUNT_REGEX.finditer(clean_title):
            val_str = m.group(1) or m.group(2)
            if val_str:
                val = cls.clean_number(val_str)
                if val > 0:
                    found_amounts.append((val, m.group(0).strip()))

        # 4. Contextual Fallback: If title has win context, check for bare numbers
        if not found_amounts and not found_multipliers:
            has_win_context = any(kw.lower() in clean_title.lower() for kw in WIN_KEYWORDS)
            if has_win_context:
                # Check for bare number in title e.g. "WON 500 ON GATES"
                m_bare = re.search(r"\b(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?\b", clean_title)
                if m_bare:
                    val = cls.clean_number(m_bare.group(1))
                    if val >= 50.0:
                        found_amounts.append((val, m_bare.group(0)))
                else:
                    for m in cls.PRIMARY_AMOUNT_REGEX.finditer(clean_title):
                        val_str = m.group(1)
                        if val_str:
                            val = cls.clean_number(val_str)
                            if val > 0:
                                found_amounts.append((val, m.group(0).strip()))

        # Handle explicit Max Win / Handpay keyword if no specific multiplier was written
        if is_max_win_keyword and not found_multipliers:
            found_multipliers.append((5000.0, "MAX WIN"))

        if not found_amounts and not found_multipliers and not is_max_win_keyword:
            return None

        # Select maximum payout amount and multiplier
        parsed_amount = None
        amt_text = ""
        if found_amounts:
            found_amounts.sort(key=lambda x: x[0], reverse=True)
            parsed_amount, amt_text = found_amounts[0]

        parsed_multiplier = None
        mult_text = ""
        if found_multipliers:
            found_multipliers.sort(key=lambda x: x[0], reverse=True)
            parsed_multiplier, mult_text = found_multipliers[0]

        # Qualification rules
        amount_qualifies = parsed_amount is not None and parsed_amount >= min_amount
        multiplier_qualifies = parsed_multiplier is not None and parsed_multiplier >= min_multiplier
        is_big_win = bool(amount_qualifies or multiplier_qualifies or is_max_win_keyword)

        if is_max_win_keyword:
            match_type = "max_win"
            matched_text = "MAX WIN"
        elif multiplier_qualifies:
            match_type = "multiplier"
            matched_text = mult_text
        elif amount_qualifies:
            match_type = "amount"
            matched_text = amt_text
        else:
            match_type = "amount" if parsed_amount is not None else "multiplier"
            matched_text = amt_text if parsed_amount is not None else mult_text

        return {
            "title": clean_title,
            "amount": parsed_amount,
            "multiplier": parsed_multiplier,
            "is_big_win": is_big_win,
            "is_max_win": is_max_win_keyword,
            "match_type": match_type,
            "matched_text": matched_text,
            "min_amount_threshold": min_amount,
            "min_multiplier_threshold": min_multiplier,
        }



def parse_kick_iso_timestamp(ts_str: Optional[str]) -> float:
    """Parses Kick API ISO timestamp into Unix seconds."""
    if not ts_str:
        return time.time()
    try:
        # Handles 2026-10-10T20:15:28.170332Z
        clean_ts = ts_str.rstrip("Z")
        if "." in clean_ts:
            dt = datetime.fromisoformat(clean_ts).replace(tzinfo=timezone.utc)
        else:
            dt = datetime.fromisoformat(clean_ts).replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return time.time()


class KickClipPulseSentinel:
    """Sentinel A: Polls Kick clips API and detects clip creation bursts and big win titles."""

    def __init__(
        self,
        channel_slug: str,
        poll_interval: float = DEFAULT_POLL_INTERVAL_SEC,
        min_amount: float = DEFAULT_MIN_WIN_AMOUNT,
        min_multiplier: float = DEFAULT_MIN_MULTIPLIER,
        on_big_win: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_burst: Optional[Callable[[int, List[Dict[str, Any]]], None]] = None,
    ):
        self.channel_slug = channel_slug.strip().lower()
        self.poll_interval = poll_interval
        self.min_amount = min_amount
        self.min_multiplier = min_multiplier
        self.on_big_win = on_big_win
        self.on_burst = on_burst

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._seen_clip_ids = set()
        self._recent_clips: deque = deque(maxlen=20)
        self.last_poll_time = 0.0
        self.last_error: Optional[str] = None

    def fetch_channel_clips(self) -> List[Dict[str, Any]]:
        """Queries Kick API v2 for channel clips across recent and sorted endpoints."""
        all_clips: List[Dict[str, Any]] = []
        seen_ids = set()

        endpoints = [
            f"https://kick.com/api/v2/channels/{self.channel_slug}/clips",
            f"https://kick.com/api/v2/channels/{self.channel_slug}/clips?sort=date",
        ]

        for ep_url in endpoints:
            req = urllib.request.Request(
                ep_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    for c in data.get("clips", []):
                        cid = str(c.get("id"))
                        if cid and cid not in seen_ids:
                            seen_ids.add(cid)
                            all_clips.append(c)
            except Exception as exc:
                self.last_error = str(exc)

        return all_clips

    def check_clip_burst(self, clips: List[Dict[str, Any]]) -> bool:
        """
        Detects if 2+ clips were created within a 60-second window.
        Returns True if a burst is detected.
        """
        now = time.time()
        window_start = now - CLIP_BURST_WINDOW_SEC

        burst_candidates = []
        for c in clips:
            c_time = parse_kick_iso_timestamp(c.get("created_at"))
            if c_time >= window_start:
                burst_candidates.append(c)

        if len(burst_candidates) >= CLIP_BURST_MIN_COUNT:
            if self.on_burst:
                self.on_burst(len(burst_candidates), burst_candidates)
            return True
        return False

    def fetch_channel_livestream(self) -> Dict[str, Any]:
        """Queries Kick API v2 for channel livestream status, category, and viewer count."""
        url = f"https://kick.com/api/v2/channels/{self.channel_slug}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                livestream = data.get("livestream")
                if livestream:
                    categories = livestream.get("categories", [])
                    category_name = categories[0].get("name", "Casino") if categories else "Casino"
                    return {
                        "is_live": True,
                        "session_title": livestream.get("session_title", ""),
                        "viewers": livestream.get("viewer_count", 0),
                        "category": category_name,
                        "thumbnail_url": livestream.get("thumbnail", {}).get("url"),
                    }
        except Exception:
            pass
        return {"is_live": False, "session_title": "", "viewers": 0, "category": "Offline"}

    def scan_recent_clips(self, hours: int = 168) -> List[Dict[str, Any]]:
        """Scans channel clips for all big win moments. Falls back to all available clips if none in window."""
        now = time.time()
        cutoff = now - (hours * 3600) if (hours and hours > 0) else 0
        clips = self.fetch_channel_clips()

        def _evaluate(c_list, enforce_cutoff=True):
            res = []
            for c in c_list:
                c_time = parse_kick_iso_timestamp(c.get("created_at"))
                if enforce_cutoff and cutoff > 0 and c_time < cutoff:
                    continue

                clip_id = str(c.get("id"))
                title = c.get("title", "")
                win_info = WinExtractor.extract_win_info(
                    title=title,
                    min_amount=self.min_amount,
                    min_multiplier=self.min_multiplier,
                )

                if win_info and win_info["is_big_win"]:
                    event_data = {
                        "clip_id": clip_id,
                        "title": title,
                        "clip_url": c.get("clip_url") or f"https://kick.com/{self.channel_slug}?clip={clip_id}",
                        "video_url": c.get("video_url"),
                        "thumbnail_url": c.get("thumbnail_url"),
                        "duration": c.get("duration", 0),
                        "created_at": c.get("created_at"),
                        "creator": c.get("creator", {}).get("username", "Viewer"),
                        "amount": win_info.get("amount"),
                        "multiplier": win_info.get("multiplier"),
                        "match_type": win_info.get("match_type"),
                        "matched_text": win_info.get("matched_text"),
                        "is_max_win": win_info.get("is_max_win", False),
                        "is_burst": False,
                        "source": "clip_pulse",
                        "detected_at": c_time,
                    }
                    res.append(event_data)
                    self._seen_clip_ids.add(clip_id)
            return res

        matching = _evaluate(clips, enforce_cutoff=True)
        if not matching and cutoff > 0:
            matching = _evaluate(clips, enforce_cutoff=False)

        return matching

    def poll_once(self) -> List[Dict[str, Any]]:
        """Executes a single polling iteration, extracts wins, and detects bursts."""
        self.last_poll_time = time.time()
        try:
            clips = self.fetch_channel_clips()
            self.last_error = None
        except Exception as exc:
            self.last_error = str(exc)
            return []

        # Check for clip burst
        is_burst = self.check_clip_burst(clips)

        detected_events = []
        for c in clips:
            clip_id = str(c.get("id"))
            if clip_id in self._seen_clip_ids:
                continue

            self._seen_clip_ids.add(clip_id)
            title = c.get("title", "")
            win_info = WinExtractor.extract_win_info(
                title=title,
                min_amount=self.min_amount,
                min_multiplier=self.min_multiplier,
            )

            # Trigger condition: Qualified big win OR (burst active AND win keyword present)
            has_keyword = any(kw.lower() in title.lower() for kw in WIN_KEYWORDS)
            should_trigger = False

            if win_info and win_info["is_big_win"]:
                should_trigger = True
            elif is_burst and has_keyword:
                should_trigger = True
                if not win_info:
                    win_info = {
                        "title": title,
                        "amount": None,
                        "multiplier": None,
                        "is_big_win": True,
                        "match_type": "clip_burst",
                        "matched_text": "Clip Burst",
                    }

            if should_trigger:
                event_data = {
                    "clip_id": clip_id,
                    "title": title,
                    "clip_url": c.get("clip_url") or f"https://kick.com/{self.channel_slug}?clip={clip_id}",
                    "video_url": c.get("video_url"),
                    "thumbnail_url": c.get("thumbnail_url"),
                    "duration": c.get("duration", 0),
                    "created_at": c.get("created_at"),
                    "creator": c.get("creator", {}).get("username", "Viewer"),
                    "amount": win_info.get("amount") if win_info else None,
                    "multiplier": win_info.get("multiplier") if win_info else None,
                    "match_type": win_info.get("match_type") if win_info else "burst",
                    "matched_text": win_info.get("matched_text") if win_info else "",
                    "is_burst": is_burst,
                    "source": "clip_pulse",
                    "detected_at": time.time(),
                }
                detected_events.append(event_data)
                self._recent_clips.append(event_data)
                if self.on_big_win:
                    self.on_big_win(event_data)

        return detected_events

    def _worker(self):
        """Worker thread loop with deterministic timeouts and anti-hang guarantees."""
        while self._running:
            try:
                self.poll_once()
            except Exception as exc:
                self.last_error = str(exc)
            # Sleep in 0.5s increments to respond promptly to stop()
            for _ in range(int(self.poll_interval * 2)):
                if not self._running:
                    break
                time.sleep(0.5)

    def start(self):
        """Starts background polling thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True, name="KickClipPulseSentinel")
        self._thread.start()

    def stop(self):
        """Stops background polling thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)


class KickPusherChatSentinel:
    """Sentinel B: Real-Time Kick Pusher WebSocket listener, chat velocity, and spike trigger."""

    def __init__(
        self,
        channel_slug: str,
        on_velocity_spike: Optional[Callable[[float, float], None]] = None,
        on_chat_message: Optional[Callable[[str, str], None]] = None,
    ):
        self.channel_slug = channel_slug.strip().lower()
        self.on_velocity_spike = on_velocity_spike
        self.on_chat_message = on_chat_message

        self.chatroom_id: Optional[int] = None
        self._running = False
        self._ws_app = None
        self._thread: Optional[threading.Thread] = None
        self.is_connected = False
        self.total_messages = 0

        # Rolling message timestamps for velocity calculation
        self._message_times: deque = deque()
        self._keyword_times: deque = deque()
        self._baseline_velocity: float = 0.5  # Initial estimated baseline msgs/sec
        self.current_velocity: float = 0.0
        self.last_spike_time: float = 0.0
        self.last_error: Optional[str] = None

    def fetch_chatroom_id(self) -> int:
        """Retrieves numeric chatroom ID from Kick API."""
        url = f"https://kick.com/api/v1/channels/{self.channel_slug}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                cid = data.get("chatroom", {}).get("id")
                if not cid:
                    raise ValueError(f"No chatroom found for channel: {self.channel_slug}")
                self.chatroom_id = int(cid)
                return self.chatroom_id
        except Exception as exc:
            # Fallback to v2
            v2_url = f"https://kick.com/api/v2/channels/{self.channel_slug}"
            req_v2 = urllib.request.Request(v2_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_v2, timeout=DEFAULT_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                cid = data.get("chatroom", {}).get("id")
                if not cid:
                    raise ValueError(f"No chatroom found for channel: {self.channel_slug}") from exc
                self.chatroom_id = int(cid)
                return self.chatroom_id

    def _update_velocity(self) -> float:
        """Computes current messages per second within rolling window."""
        now = time.time()
        cutoff = now - CHAT_VELOCITY_WINDOW_SEC

        while self._message_times and self._message_times[0] < cutoff:
            self._message_times.popleft()

        count = len(self._message_times)
        span = min(CHAT_VELOCITY_WINDOW_SEC, max(1.0, now - (self._message_times[0] if count > 0 else now)))
        velocity = count / span
        self.current_velocity = round(velocity, 2)

        # Slowly adapt baseline when not in a spike
        if now - self.last_spike_time > 30:
            self._baseline_velocity = (self._baseline_velocity * 0.95) + (max(0.1, velocity) * 0.05)

        return self.current_velocity

    def _check_spike(self, content: str):
        """Checks if current velocity or keyword burst exceeds trigger threshold."""
        now = time.time()
        self._message_times.append(now)
        self.total_messages += 1
        current_vel = self._update_velocity()

        # Track win keywords and viewer reaction emotes
        content_lower = content.lower()
        has_win_kw = any(kw.lower() in content_lower for kw in WIN_KEYWORDS) or bool(
            re.search(r"\b(w{1,6}|clip(\s*it|\s*that)?|omg|holy|sheesh|pog|poggies|sheeeesh|\$\$\$)\b", content_lower)
        )

        if has_win_kw:
            self._keyword_times.append(now)

        cutoff_kw = now - 10.0
        while self._keyword_times and self._keyword_times[0] < cutoff_kw:
            self._keyword_times.popleft()

        kw_burst_count = len(self._keyword_times)

        # Trigger conditions:
        # 1. Traditional velocity spike (> 300% over rolling baseline)
        threshold = max(1.5, self._baseline_velocity * CHAT_VELOCITY_SPIKE_RATIO)
        is_spike = current_vel >= threshold

        # 2. Keyword density surge: 3+ win reaction messages in 10s (works for smaller/niche streams!)
        is_kw_surge = kw_burst_count >= 3

        # 3. Fast velocity with win keyword
        is_boosted = has_win_kw and current_vel >= 1.0

        if (is_spike or is_kw_surge or is_boosted) and (now - self.last_spike_time > 15):
            self.last_spike_time = now
            if self.on_velocity_spike:
                self.on_velocity_spike(current_vel, self._baseline_velocity)

    def _run_socket(self, app_key: str):
        """Connects to Pusher with a specific app key."""
        import websocket

        ws_url = (
            f"wss://ws-{DEFAULT_PUSHER_CLUSTER}.pusher.com/app/{app_key}"
            f"?protocol=7&client=js&version=7.6.0&flash=false"
        )

        def on_open(ws):
            self.is_connected = True
            self.last_error = None

        def on_message(ws, raw_msg):
            try:
                payload = json.loads(raw_msg)
                event = payload.get("event")

                if event == "pusher:connection_established":
                    # Subscribe to chatroom channel
                    sub_payload = json.dumps({
                        "event": "pusher:subscribe",
                        "data": {"auth": "", "channel": f"chatrooms.{self.chatroom_id}.v2"},
                    })
                    ws.send(sub_payload)

                elif event == "pusher:ping":
                    # Heartbeat pong response
                    ws.send(json.dumps({"event": "pusher:pong", "data": {}}))

                elif event == "App\\Events\\ChatMessageEvent":
                    data_str = payload.get("data", "{}")
                    data = json.loads(data_str) if isinstance(data_str, str) else data_str
                    content = data.get("content", "")
                    sender = data.get("sender", {}).get("username", "user")

                    self._check_spike(content)
                    if self.on_chat_message:
                        self.on_chat_message(sender, content)

            except Exception:
                pass

        def on_error(ws, error):
            self.last_error = str(error)
            self.is_connected = False

        def on_close(ws, close_status_code, close_msg):
            self.is_connected = False

        self._ws_app = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )

        # Run loop with ping intervals
        self._ws_app.run_forever(ping_interval=30, ping_timeout=10)

    def _worker(self):
        """Connection loop with key fallback and retry backoff."""
        try:
            self.fetch_chatroom_id()
        except Exception as exc:
            self.last_error = f"Failed to resolve chatroom ID: {exc}"
            return

        keys = list(DEFAULT_PUSHER_KEYS)
        key_idx = 0

        while self._running:
            active_key = keys[key_idx % len(keys)]
            try:
                self._run_socket(active_key)
            except Exception as exc:
                self.last_error = str(exc)

            if not self._running:
                break

            key_idx += 1
            time.sleep(2.0)

    def start(self):
        """Starts WebSocket listener in background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True, name="KickPusherChatSentinel")
        self._thread.start()

    def stop(self):
        """Stops WebSocket listener."""
        self._running = False
        self.is_connected = False
        if self._ws_app:
            try:
                self._ws_app.close()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)


class TwitchIrcChatSentinel:
    """Sentinel for Twitch live chat via anonymous IRC WebSocket (wss://irc-ws.chat.twitch.tv:443).
    Zero API key required. Tracks chat velocity, emote surges, and hype keyword spikes.
    """

    def __init__(
        self,
        channel_slug: str,
        stream_category: str = "all",
        on_velocity_spike: Optional[Callable[[float, float], None]] = None,
        on_chat_message: Optional[Callable[[str, str], None]] = None,
    ):
        self.channel_slug = channel_slug.strip().lower().lstrip("#@")
        self.stream_category = stream_category
        self.on_velocity_spike = on_velocity_spike
        self.on_chat_message = on_chat_message

        self.is_connected = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._ws_app = None

        self.total_messages = 0
        self._message_times: deque = deque()
        self._keyword_times: deque = deque()
        self._baseline_velocity: float = 0.5
        self.current_velocity: float = 0.0
        self.last_spike_time: float = 0.0
        self.last_error: Optional[str] = None

        # Select keyword filter based on stream category
        if self.stream_category == "gaming":
            raw_kws = GAMING_KEYWORDS
        elif self.stream_category == "just_chatting":
            raw_kws = IRL_KEYWORDS
        elif self.stream_category == "casino":
            raw_kws = CASINO_KEYWORDS
        else:
            raw_kws = ALL_HYPE_KEYWORDS
        self._active_keywords = [k.lower() for k in raw_kws]

    def _update_velocity(self) -> float:
        now = time.time()
        cutoff = now - CHAT_VELOCITY_WINDOW_SEC

        while self._message_times and self._message_times[0] < cutoff:
            self._message_times.popleft()

        count = len(self._message_times)
        span = min(CHAT_VELOCITY_WINDOW_SEC, max(1.0, now - (self._message_times[0] if count > 0 else now)))
        velocity = count / span
        self.current_velocity = round(velocity, 2)

        if now - self.last_spike_time > 30:
            self._baseline_velocity = (self._baseline_velocity * 0.95) + (max(0.1, velocity) * 0.05)

        return self.current_velocity

    def _check_spike(self, content: str):
        now = time.time()
        self._message_times.append(now)
        self.total_messages += 1
        current_vel = self._update_velocity()

        content_upper = content.upper()
        has_hype_kw = any(kw in content_upper for kw in self._active_keywords)

        if has_hype_kw:
            self._keyword_times.append(now)

        cutoff_kw = now - 10.0
        while self._keyword_times and self._keyword_times[0] < cutoff_kw:
            self._keyword_times.popleft()

        kw_burst_count = len(self._keyword_times)

        # Trigger conditions
        threshold = max(1.5, self._baseline_velocity * CHAT_VELOCITY_SPIKE_RATIO)
        is_spike = current_vel >= threshold
        is_kw_surge = kw_burst_count >= 3
        is_boosted = has_hype_kw and current_vel >= 1.0

        if (is_spike or is_kw_surge or is_boosted) and (now - self.last_spike_time > 15):
            self.last_spike_time = now
            if self.on_velocity_spike:
                self.on_velocity_spike(current_vel, self._baseline_velocity)

    def _parse_and_handle_message(self, raw_line: str):
        if raw_line.startswith("PING"):
            if self._ws_app:
                try:
                    self._ws_app.send("PONG :tmi.twitch.tv\r\n")
                except Exception:
                    pass
            return

        if "PRIVMSG" in raw_line:
            sender = "viewer"
            match = re.search(r"display-name=([^;]*)", raw_line)
            if match and match.group(1):
                sender = match.group(1).strip()
            else:
                user_match = re.search(r":([^!]+)!", raw_line)
                if user_match:
                    sender = user_match.group(1).strip()

            if " :" in raw_line:
                msg_body = raw_line.split(" :", 1)[1].strip()
            else:
                msg_body = raw_line.split("PRIVMSG", 1)[1].strip()

            self._check_spike(msg_body)
            if self.on_chat_message:
                self.on_chat_message(sender, msg_body)

    def _worker(self):
        import websocket
        import random

        anon_num = random.randint(10000, 99999)
        nick = f"justinfan{anon_num}"

        def on_open(ws):
            self.is_connected = True
            self.last_error = None
            ws.send("CAP REQ :twitch.tv/tags twitch.tv/commands\r\n")
            ws.send(f"PASS oauth:{nick}\r\n")
            ws.send(f"NICK {nick}\r\n")
            ws.send(f"USER {nick} 8 * :{nick}\r\n")
            ws.send(f"JOIN #{self.channel_slug}\r\n")

        def on_message(ws, raw_msg):
            for line in raw_msg.splitlines():
                line = line.strip()
                if line:
                    self._parse_and_handle_message(line)

        def on_error(ws, error):
            self.last_error = str(error)
            self.is_connected = False

        def on_close(ws, close_status_code, close_msg):
            self.is_connected = False

        while self._running:
            try:
                self._ws_app = websocket.WebSocketApp(
                    TWITCH_IRC_WS_URL,
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                )
                self._ws_app.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                self.last_error = str(e)
                self.is_connected = False

            if not self._running:
                break
            time.sleep(2.0)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True, name="TwitchIrcChatSentinel")
        self._thread.start()

    def stop(self):
        self._running = False
        self.is_connected = False
        if self._ws_app:
            try:
                self._ws_app.close()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)


class UniversalWatchdogManager:
    """Universal stream monitoring watchdog supporting both Kick (Pusher) and Twitch (IRC + GQL)."""

    def __init__(self):
        self.platform: str = "kick"
        self.stream_category: str = "all"
        self.channel_slug: Optional[str] = None
        self.clip_sentinel: Optional[KickClipPulseSentinel] = None
        self.chat_sentinel: Optional[Any] = None
        self.is_active = False

        self.min_amount: float = DEFAULT_MIN_WIN_AMOUNT
        self.min_multiplier: float = DEFAULT_MIN_MULTIPLIER
        self.poll_interval: float = DEFAULT_POLL_INTERVAL_SEC

        # Detected highlights / wins buffer (max 50)
        self.detected_wins: deque = deque(maxlen=50)
        self.recent_chat_events: deque = deque(maxlen=30)
        self.burst_alerts: deque = deque(maxlen=10)
        self._lock = threading.Lock()

    def _on_big_win_detected(self, event: Dict[str, Any]):
        """Handler for qualified big win events from Kick Sentinel A."""
        with self._lock:
            if not any(w["clip_id"] == event["clip_id"] for w in self.detected_wins):
                self.detected_wins.appendleft(event)

    def _on_clip_burst(self, count: int, clips: List[Dict[str, Any]]):
        """Handler for clip burst detected."""
        with self._lock:
            self.burst_alerts.appendleft({
                "count": count,
                "time": time.time(),
                "sample_title": clips[0].get("title", "") if clips else "",
            })

    def _on_velocity_spike(self, current_vel: float, baseline: float):
        """Handler for chat velocity spikes from Sentinel B."""
        with self._lock:
            self.burst_alerts.appendleft({
                "count": int(current_vel * 2),
                "time": time.time(),
                "sample_title": f"Chat velocity spike: {current_vel:.1f} msg/s (Baseline: {baseline:.1f})",
            })

        if self.platform == "kick" and self.clip_sentinel:
            threading.Thread(target=self.clip_sentinel.poll_once, daemon=True).start()
        elif self.platform == "twitch":
            threading.Thread(target=self._poll_twitch_clips_once, daemon=True).start()

    def _poll_twitch_clips_once(self):
        """Quick background scan for newly created Twitch clips."""
        if not self.channel_slug:
            return
        from core.video_ingest import fetch_twitch_channel_clips
        clips = fetch_twitch_channel_clips(self.channel_slug, limit=6, period="LAST_DAY")
        with self._lock:
            for c in clips:
                cid = str(c.get("id") or c.get("slug"))
                if not any(x["clip_id"] == cid for x in self.detected_wins):
                    self.detected_wins.appendleft({
                        "clip_id": cid,
                        "title": c.get("title", "Twitch Highlight"),
                        "win_amount": c.get("views", 0),
                        "multiplier": 0.0,
                        "view_count": c.get("views", 0),
                        "duration": c.get("duration", 30.0),
                        "created_at": c.get("created_at", ""),
                        "clip_url": c.get("url", ""),
                        "thumbnail_url": c.get("thumbnail_url", ""),
                        "clipped_by": c.get("clipped_by", "Twitch Viewer"),
                        "platform": "twitch",
                    })

    def _on_chat_message(self, sender: str, content: str):
        """Handler for incoming chat message."""
        with self._lock:
            self.recent_chat_events.appendleft({
                "sender": sender,
                "content": content[:80],
                "time": time.time(),
            })

    def start_watchdog(
        self,
        channel_slug: str,
        platform: str = "kick",
        stream_category: str = "all",
        min_amount: float = DEFAULT_MIN_WIN_AMOUNT,
        min_multiplier: float = DEFAULT_MIN_MULTIPLIER,
        poll_interval: float = DEFAULT_POLL_INTERVAL_SEC,
    ) -> Dict[str, Any]:
        """Starts monitoring either a Kick channel (Pusher) or Twitch channel (IRC)."""
        self.stop_watchdog()

        clean_slug = sanitize_channel_slug(channel_slug)
        if not clean_slug:
            raise ValueError(f"Could not parse valid channel slug from '{channel_slug}'")

        self.platform = "twitch" if ("twitch" in str(platform).lower() or "twitch.tv" in str(channel_slug).lower()) else "kick"
        self.stream_category = stream_category
        self.channel_slug = clean_slug
        self.min_amount = min_amount
        self.min_multiplier = min_multiplier
        self.poll_interval = poll_interval

        with self._lock:
            self.detected_wins.clear()
            self.burst_alerts.clear()

        if self.platform == "twitch":
            self.chat_sentinel = TwitchIrcChatSentinel(
                channel_slug=clean_slug,
                stream_category=stream_category,
                on_velocity_spike=self._on_velocity_spike,
                on_chat_message=self._on_chat_message,
            )
            self.chat_sentinel.start()
            threading.Thread(target=self._poll_twitch_clips_once, daemon=True).start()
        else:
            self.clip_sentinel = KickClipPulseSentinel(
                channel_slug=clean_slug,
                poll_interval=poll_interval,
                min_amount=min_amount,
                min_multiplier=min_multiplier,
                on_big_win=self._on_big_win_detected,
                on_burst=self._on_clip_burst,
            )
            self.clip_sentinel.start()
            threading.Thread(target=self.clip_sentinel.poll_once, daemon=True).start()

            self.chat_sentinel = KickPusherChatSentinel(
                channel_slug=clean_slug,
                on_velocity_spike=self._on_velocity_spike,
                on_chat_message=self._on_chat_message,
            )
            self.chat_sentinel.start()

        self.is_active = True
        return {
            "status": "started",
            "channel": clean_slug,
            "platform": self.platform,
            "category": self.stream_category,
        }

    def stop_watchdog(self) -> Dict[str, Any]:
        """Stops active monitoring threads."""
        self.is_active = False
        if self.clip_sentinel:
            self.clip_sentinel.stop()
            self.clip_sentinel = None
        if self.chat_sentinel:
            self.chat_sentinel.stop()
            self.chat_sentinel = None
        return {"status": "stopped"}

    def set_sensitivity_preset(self, preset: str) -> Dict[str, Any]:
        """Configures detection sensitivity (aggressive, balanced, high_roller)."""
        preset_clean = (preset or "balanced").lower().strip()
        if preset_clean == "aggressive":
            self.min_amount = 50.0
            self.min_multiplier = 25.0
        elif preset_clean == "high_roller":
            self.min_amount = 1000.0
            self.min_multiplier = 500.0
        else:
            preset_clean = "balanced"
            self.min_amount = 100.0
            self.min_multiplier = 50.0

        if self.clip_sentinel:
            self.clip_sentinel.min_amount = self.min_amount
            self.clip_sentinel.min_multiplier = self.min_multiplier

        return {
            "preset": preset_clean,
            "min_amount": self.min_amount,
            "min_multiplier": self.min_multiplier,
        }

    def scan_channel_recent_wins(self, hours: int = 168, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """Scans channel clips from Twitch or Kick and adds them to detected clips/wins."""
        slug = self.channel_slug
        if not slug:
            return []

        target_platform = platform or self.platform

        if target_platform == "twitch":
            from core.video_ingest import fetch_twitch_channel_clips
            raw_clips = fetch_twitch_channel_clips(slug, limit=20, period="ALL_TIME")
            results = []
            for c in raw_clips:
                formatted = {
                    "clip_id": str(c.get("id") or c.get("slug")),
                    "title": c.get("title", "Twitch Clip"),
                    "win_amount": c.get("views", 0),
                    "multiplier": 0.0,
                    "view_count": c.get("views", 0),
                    "duration": c.get("duration", 30.0),
                    "created_at": c.get("created_at", ""),
                    "clip_url": c.get("url", ""),
                    "thumbnail_url": c.get("thumbnail_url", ""),
                    "clipped_by": c.get("clipped_by", "Twitch Viewer"),
                    "platform": "twitch",
                }
                results.append(formatted)

            with self._lock:
                for w in results:
                    if not any(x["clip_id"] == w["clip_id"] for x in self.detected_wins):
                        self.detected_wins.append(w)
            return results
        else:
            sentinel = KickClipPulseSentinel(
                channel_slug=slug,
                min_amount=self.min_amount,
                min_multiplier=self.min_multiplier,
            )
            recent_wins = sentinel.scan_recent_clips(hours=hours)
            with self._lock:
                for w in recent_wins:
                    if not any(x["clip_id"] == w["clip_id"] for x in self.detected_wins):
                        self.detected_wins.append(w)
            return recent_wins

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive watchdog status and telemetry."""
        with self._lock:
            wins_copy = list(self.detected_wins)
            bursts_copy = list(self.burst_alerts)
            chat_events = list(self.recent_chat_events)

        ws_connected = self.chat_sentinel.is_connected if self.chat_sentinel else False
        chat_vel = self.chat_sentinel.current_velocity if self.chat_sentinel else 0.0
        total_msgs = self.chat_sentinel.total_messages if self.chat_sentinel else 0
        chatroom_id = getattr(self.chat_sentinel, "chatroom_id", None) if self.chat_sentinel else None

        last_error = None
        if self.clip_sentinel and self.clip_sentinel.last_error:
            last_error = self.clip_sentinel.last_error
        elif self.chat_sentinel and self.chat_sentinel.last_error:
            last_error = self.chat_sentinel.last_error

        livestream_info = {}
        if self.clip_sentinel and self.channel_slug and self.platform == "kick":
            try:
                livestream_info = self.clip_sentinel.fetch_channel_livestream()
            except Exception:
                pass

        return {
            "is_active": self.is_active,
            "platform": self.platform,
            "category": self.stream_category,
            "channel_slug": self.channel_slug,
            "ws_connected": ws_connected,
            "chatroom_id": chatroom_id,
            "chat_velocity": chat_vel,
            "total_messages": total_msgs,
            "min_amount": self.min_amount,
            "min_multiplier": self.min_multiplier,
            "detected_wins_count": len(wins_copy),
            "detected_wins": wins_copy[:30],
            "recent_bursts": bursts_copy[:5],
            "recent_chat_events": chat_events[:10],
            "last_error": last_error,
            "livestream": livestream_info,
        }


# Backward-compatible alias
KickWatchdogManager = UniversalWatchdogManager

