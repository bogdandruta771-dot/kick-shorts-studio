"""Media ingestion via yt-dlp and container integrity validation via ffprobe."""
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, Optional, List

from core.config import (
    DOWNLOAD_TIMEOUT,
    DEFAULT_TIMEOUT,
    TWITCH_GQL_URL,
    TWITCH_GQL_CLIENT_ID,
)
from core.utils import (
    resolve_binary_paths,
    run_command_safe,
    retry_with_backoff,
)


def validate_media_file(file_path: Path) -> Dict[str, Any]:
    """
    Validates container integrity, streams, resolution, fps, and audio channels using ffprobe.
    Raises ValueError or FileNotFoundError if invalid.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"Media file does not exist: {file_path}")

    _, ffprobe_bin = resolve_binary_paths()

    probe_cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "format=duration,size,bit_rate",
        "-show_entries", "stream=index,codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels",
        "-of", "json",
        str(file_path),
    ]

    result = run_command_safe(probe_cmd, timeout=DEFAULT_TIMEOUT)
    if result.returncode != 0:
        raise ValueError(
            f"Corrupted or invalid media container: {result.stderr.strip() or 'Unknown ffprobe error'}"
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse ffprobe output for {file_path}") from exc

    streams = data.get("streams", [])
    format_info = data.get("format", {})

    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    if not video_streams:
        raise ValueError(f"No video stream found in media file: {file_path}")

    v_stream = video_streams[0]
    width = int(v_stream.get("width", 0))
    height = int(v_stream.get("height", 0))

    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid video dimensions ({width}x{height}) in {file_path}")

    # Parse frame rate
    fps_raw = v_stream.get("r_frame_rate", "30/1")
    try:
        if "/" in fps_raw:
            num, den = fps_raw.split("/")
            fps = float(num) / float(den) if float(den) > 0 else 30.0
        else:
            fps = float(fps_raw)
    except Exception:
        fps = 30.0

    duration = float(format_info.get("duration", 0.0))
    if duration <= 0:
        # Check stream duration if format duration missing
        duration = float(v_stream.get("duration", 0.0))

    has_audio = len(audio_streams) > 0
    audio_channels = int(audio_streams[0].get("channels", 0)) if has_audio else 0
    audio_sample_rate = int(audio_streams[0].get("sample_rate", 0)) if has_audio else 0

    return {
        "file_path": str(file_path),
        "width": width,
        "height": height,
        "duration": duration,
        "fps": round(fps, 2),
        "has_audio": has_audio,
        "audio_channels": audio_channels,
        "audio_sample_rate": audio_sample_rate,
        "video_codec": v_stream.get("codec_name", "unknown"),
        "audio_codec": audio_streams[0].get("codec_name", "none") if has_audio else "none",
        "size_bytes": int(format_info.get("size", file_path.stat().st_size)),
    }


def detect_stream_platform(url: str) -> str:
    """Detects whether a URL belongs to Twitch, Kick, YouTube, or is a generic stream link."""
    clean = url.strip().lower()
    if "twitch.tv" in clean or "clips.twitch.tv" in clean:
        return "twitch"
    if "kick.com" in clean:
        return "kick"
    if "youtube.com" in clean or "youtu.be" in clean:
        return "youtube"
    return "generic"


# Shared category & game normalization maps
KICK_CAT_ALIASES: Dict[str, str] = {
    "casino": "slots",
    "gambling": "slots",
    "slots": "slots",
    "just_chatting": "just-chatting",
    "just chatting": "just-chatting",
    "irl": "irl",
    "gta": "grand-theft-auto-v",
    "gta v": "grand-theft-auto-v",
    "gta 5": "grand-theft-auto-v",
    "grand theft auto v": "grand-theft-auto-v",
    "valorant": "valorant",
    "fortnite": "fortnite",
    "cs": "counter-strike-2",
    "cs2": "counter-strike-2",
    "cs 2": "counter-strike-2",
    "csgo": "counter-strike-2",
    "counter-strike": "counter-strike-2",
    "counter strike": "counter-strike-2",
    "counter-strike-2": "counter-strike-2",
    "counter-strike 2": "counter-strike-2",
    "case_opening": "counter-strike-2",
    "case-opening": "counter-strike-2",
    "case opening": "counter-strike-2",
    "cases": "counter-strike-2",
    "unboxing": "counter-strike-2",
    "minecraft": "minecraft",
    "apex": "apex-legends",
    "apex legends": "apex-legends",
    "league": "league-of-legends",
    "league of legends": "league-of-legends",
    "dota": "dota-2",
    "dota 2": "dota-2",
    "fifa": "ea-sports-fc-24",
    "fc 24": "ea-sports-fc-24",
    "fc 25": "ea-sports-fc-25",
    "roblox": "roblox",
    "rust": "rust",
    "warzone": "call-of-duty-warzone",
    "call of duty": "call-of-duty-warzone",
}

TWITCH_GAME_ALIASES: Dict[str, str] = {
    "casino": "Slots",
    "gambling": "Slots",
    "slots": "Slots",
    "just_chatting": "Just Chatting",
    "just chatting": "Just Chatting",
    "irl": "Just Chatting",
    "gta": "Grand Theft Auto V",
    "gta v": "Grand Theft Auto V",
    "gta 5": "Grand Theft Auto V",
    "grand theft auto v": "Grand Theft Auto V",
    "valorant": "Valorant",
    "fortnite": "Fortnite",
    "cs": "Counter-Strike",
    "cs2": "Counter-Strike",
    "cs 2": "Counter-Strike",
    "csgo": "Counter-Strike",
    "counter-strike": "Counter-Strike",
    "counter strike": "Counter-Strike",
    "counter-strike-2": "Counter-Strike",
    "counter-strike 2": "Counter-Strike",
    "case_opening": "Counter-Strike",
    "case-opening": "Counter-Strike",
    "case opening": "Counter-Strike",
    "cases": "Counter-Strike",
    "unboxing": "Counter-Strike",
    "minecraft": "Minecraft",
    "apex": "Apex Legends",
    "apex legends": "Apex Legends",
    "league": "League of Legends",
    "league of legends": "League of Legends",
    "dota": "Dota 2",
    "dota 2": "Dota 2",
    "fifa": "EA Sports FC 24",
    "fc 24": "EA Sports FC 24",
    "fc 25": "EA Sports FC 25",
    "roblox": "Roblox",
    "rust": "Rust",
    "warzone": "Call of Duty: Warzone",
    "call of duty": "Call of Duty: Warzone",
}


def fetch_kick_clips(
    channel_slug: Optional[str] = None,
    category_slug: Optional[str] = None,
    sort: str = "view",
    time_filter: str = "day",
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Fetches clips from Kick's public API without authentication.
    Supports channel filtering, category filtering (e.g. slots, gaming, irl), and time filters.
    """
    time_map = {"24h": "day", "day": "day", "week": "week", "month": "month", "all": "all"}
    clean_time = time_map.get(str(time_filter).lower(), "day")
    clean_sort = "date" if str(sort).lower() == "date" else "view"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    if channel_slug and channel_slug.strip():
        slug = channel_slug.strip().lower()
        slug = re.sub(r"^https?://(?:www\.)?kick\.com/", "", slug)
        slug = slug.split("/")[0].split("?")[0].lstrip("@#")
        url = f"https://kick.com/api/v2/channels/{slug}/clips?sort={clean_sort}&time={clean_time}"
    elif category_slug and category_slug.strip() and category_slug.lower() not in ("all", "general"):
        raw_cat = category_slug.strip().lower()
        cat = KICK_CAT_ALIASES.get(raw_cat, raw_cat.replace(" ", "-"))
        url = f"https://kick.com/api/v2/categories/{cat}/clips?sort={clean_sort}&time={clean_time}"
    else:
        url = f"https://kick.com/api/v2/clips?sort={clean_sort}&time={clean_time}"

    clips: List[Dict[str, Any]] = []
    cursor: Optional[str] = None
    target_limit = max(1, limit)
    max_pages = min(6, (target_limit + 19) // 20)

    try:
        for _ in range(max_pages):
            page_url = url + (f"&cursor={cursor}" if cursor else "")
            req = urllib.request.Request(page_url, headers=headers)
            with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_clips = data.get("clips", [])
                if not raw_clips:
                    break
                for item in raw_clips:
                    channel = item.get("channel") or {}
                    category = item.get("category") or {}
                    creator = item.get("creator") or {}
                    clip_id = str(item.get("id") or "")
                    ch_slug = channel.get("slug") or channel.get("username") or "streamer"
                    clip_page = f"https://kick.com/{ch_slug}?clip={clip_id}" if clip_id else f"https://kick.com/{ch_slug}"

                    clips.append({
                        "id": clip_id,
                        "title": item.get("title") or f"{ch_slug} Moment",
                        "url": clip_page,
                        "stream_url": item.get("clip_url") or item.get("video_url") or "",
                        "thumbnail_url": item.get("thumbnail_url") or "",
                        "platform": "kick",
                        "streamer": channel.get("username") or ch_slug,
                        "streamer_slug": ch_slug,
                        "streamer_avatar": channel.get("profile_picture") or "",
                        "creator": creator.get("username") or "Viewer",
                        "views": int(item.get("views") or item.get("view_count") or 0),
                        "duration": float(item.get("duration") or 30.0),
                        "category": category.get("name") or "Kick Stream",
                        "created_at": item.get("created_at") or "",
                    })
                    if len(clips) >= target_limit:
                        break

                cursor = data.get("nextCursor")
                if not cursor or len(clips) >= target_limit:
                    break

        return clips
    except Exception:
        return clips


def fetch_twitch_clips(
    channel_slug: Optional[str] = None,
    category_name: Optional[str] = None,
    time_filter: str = "LAST_WEEK",
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Fetches top clips from Twitch using Twitch's public GQL endpoint without user tokens.
    Handles channel filtering, game/category filtering, and time ranges.
    """
    time_map = {
        "24h": "LAST_DAY",
        "day": "LAST_DAY",
        "week": "LAST_WEEK",
        "month": "LAST_MONTH",
        "all": "ALL_TIME",
        "LAST_DAY": "LAST_DAY",
        "LAST_WEEK": "LAST_WEEK",
        "LAST_MONTH": "LAST_MONTH",
        "ALL_TIME": "ALL_TIME",
    }
    gql_filter = time_map.get(str(time_filter), "ALL_TIME")

    headers = {
        "Client-ID": TWITCH_GQL_CLIENT_ID,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    clips: List[Dict[str, Any]] = []

    if channel_slug and channel_slug.strip():
        slug = channel_slug.strip().lower()
        slug = re.sub(r"^https?://(?:www\.)?twitch\.tv/", "", slug)
        slug = slug.split("/")[0].split("?")[0].lstrip("@#")

        # Query user clips using UserClipsInput
        def _query_user(filt: str) -> List[Dict[str, Any]]:
            query = """
            query GetChannelClips($login: String!, $first: Int!, $criteria: UserClipsInput) {
              user(login: $login) {
                displayName
                profileImageURL(width: 70)
                clips(first: $first, criteria: $criteria) {
                  edges {
                    node {
                      id
                      slug
                      title
                      viewCount
                      durationSeconds
                      createdAt
                      url
                      thumbnailURL
                      curator { displayName }
                      game { name }
                    }
                  }
                }
              }
            }
            """
            payload = json.dumps({
                "query": query,
                "variables": {
                    "login": slug,
                    "first": max(1, min(limit, 100)),
                    "criteria": {"filter": filt},
                },
            }).encode("utf-8")
            req = urllib.request.Request(TWITCH_GQL_URL, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                user_data = data.get("data", {}).get("user") or {}
                streamer_name = user_data.get("displayName") or slug
                streamer_avatar = user_data.get("profileImageURL") or ""
                edges = user_data.get("clips", {}).get("edges", [])
                out = []
                for edge in edges:
                    node = edge.get("node") or {}
                    out.append({
                        "id": node.get("slug") or node.get("id") or "",
                        "slug": node.get("slug") or "",
                        "title": node.get("title") or "Twitch Clip",
                        "url": node.get("url") or f"https://clips.twitch.tv/{node.get('slug')}",
                        "stream_url": node.get("url") or "",
                        "thumbnail_url": node.get("thumbnailURL") or "",
                        "platform": "twitch",
                        "streamer": streamer_name,
                        "streamer_slug": slug,
                        "streamer_avatar": streamer_avatar,
                        "creator": (node.get("curator") or {}).get("displayName") or "Viewer",
                        "views": int(node.get("viewCount") or 0),
                        "duration": float(node.get("durationSeconds") or 30.0),
                        "category": (node.get("game") or {}).get("name") or "Twitch Stream",
                        "created_at": node.get("createdAt") or "",
                    })
                return out

        try:
            clips = _query_user(gql_filter)
            # If 0 clips found in requested narrow filter, fall back to ALL_TIME
            if not clips and gql_filter != "ALL_TIME":
                clips = _query_user("ALL_TIME")
        except Exception:
            pass

    else:
        # Query category/game clips
        raw_cat = (category_name or "Just Chatting").strip().lower()
        game_target = TWITCH_GAME_ALIASES.get(raw_cat, category_name or "Just Chatting")

        query = """
        query GetGameClips($name: String!, $first: Int!) {
          game(name: $name) {
            id
            name
            clips(first: $first) {
              edges {
                node {
                  id
                  slug
                  title
                  viewCount
                  durationSeconds
                  createdAt
                  url
                  thumbnailURL
                  broadcaster {
                    displayName
                    login
                    profileImageURL(width: 70)
                  }
                  curator { displayName }
                }
              }
            }
          }
        }
        """
        payload = json.dumps({
            "query": query,
            "variables": {
                "name": game_target,
                "first": max(1, min(limit, 100)),
            },
        }).encode("utf-8")
        try:
            req = urllib.request.Request(TWITCH_GQL_URL, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                game_data = data.get("data", {}).get("game") or {}
                edges = game_data.get("clips", {}).get("edges", [])
                for edge in edges:
                    node = edge.get("node") or {}
                    bcast = node.get("broadcaster") or {}
                    clips.append({
                        "id": node.get("slug") or node.get("id") or "",
                        "slug": node.get("slug") or "",
                        "title": node.get("title") or "Twitch Clip",
                        "url": node.get("url") or f"https://clips.twitch.tv/{node.get('slug')}",
                        "stream_url": node.get("url") or "",
                        "thumbnail_url": node.get("thumbnailURL") or "",
                        "platform": "twitch",
                        "streamer": bcast.get("displayName") or "Streamer",
                        "streamer_slug": bcast.get("login") or "streamer",
                        "streamer_avatar": bcast.get("profileImageURL") or "",
                        "creator": (node.get("curator") or {}).get("displayName") or "Viewer",
                        "views": int(node.get("viewCount") or 0),
                        "duration": float(node.get("durationSeconds") or 30.0),
                        "category": game_data.get("name") or game_target,
                        "created_at": node.get("createdAt") or "",
                    })
        except Exception:
            pass

    return clips


def fetch_twitch_channel_clips(
    channel_slug: str,
    limit: int = 12,
    period: str = "ALL_TIME",
) -> List[Dict[str, Any]]:
    """Backward-compatible alias for existing callers."""
    return fetch_twitch_clips(channel_slug=channel_slug, time_filter=period, limit=limit)


def parse_youtube_timestamp(url: str) -> Optional[float]:
    """Extracts starting timestamp in seconds from YouTube URL (?t=120 or ?t=1m30s or ?start=45)."""
    m = re.search(r"[?&](?:t|start)=([0-9hms]+)", url, re.IGNORECASE)
    if not m:
        return None
    val = m.group(1).lower()
    if val.isdigit():
        return float(val)
    seconds = 0.0
    h_m = re.search(r"(\d+)h", val)
    if h_m:
        seconds += float(h_m.group(1)) * 3600
    m_m = re.search(r"(\d+)m", val)
    if m_m:
        seconds += float(m_m.group(1)) * 60
    s_m = re.search(r"(\d+)s", val)
    if s_m:
        seconds += float(s_m.group(1))
    return seconds if seconds > 0 else None


def fetch_youtube_clips(
    query: str = "",
    channel_slug: Optional[str] = None,
    category: Optional[str] = None,
    sort: str = "view",
    time_filter: str = "all",
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Fetches trending or topic-specific clips, shorts, and highlights from YouTube using yt-dlp flat extraction.
    No Google API key required.
    """
    import yt_dlp

    clean_q = (query or "").strip()
    search_terms = []

    if channel_slug and channel_slug.strip():
        ch = channel_slug.strip().lstrip("@")
        search_terms.append(f"{ch} clips")
    elif clean_q:
        q_l = clean_q.lower()
        if "clip" not in q_l and "short" not in q_l:
            search_terms.append(f"{clean_q} clips")
        else:
            search_terms.append(clean_q)
    elif category and category.lower() != "all":
        search_terms.append(f"{category} clips moments")
    else:
        search_terms.append("viral gaming clips trending moments")

    clips: List[Dict[str, Any]] = []
    target_limit = max(1, limit)

    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
        "ignoreerrors": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for term in search_terms:
                yt_query = f"ytsearch{target_limit}:{term}"
                data = ydl.extract_info(yt_query, download=False)
                entries = data.get("entries") or []
                for entry in entries:
                    if not entry:
                        continue
                    v_id = entry.get("id") or ""
                    if not v_id:
                        continue
                    title = entry.get("title") or "YouTube Clip"
                    uploader = entry.get("uploader") or entry.get("channel") or "YouTube Creator"
                    views = int(entry.get("view_count") or 0)
                    duration = float(entry.get("duration") or 30.0)

                    # High quality thumbnail
                    thumbs = entry.get("thumbnails") or []
                    thumb_url = f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg"
                    if thumbs and isinstance(thumbs, list):
                        last_t = thumbs[-1]
                        if isinstance(last_t, dict) and last_t.get("url"):
                            thumb_url = last_t["url"]

                    yt_url = entry.get("url") or f"https://www.youtube.com/watch?v={v_id}"
                    if not yt_url.startswith("http"):
                        yt_url = f"https://www.youtube.com/watch?v={v_id}"

                    clips.append({
                        "id": v_id,
                        "slug": v_id,
                        "title": title,
                        "url": yt_url,
                        "stream_url": yt_url,
                        "thumbnail_url": thumb_url,
                        "platform": "youtube",
                        "streamer": uploader,
                        "streamer_slug": re.sub(r"[^a-zA-Z0-9_-]", "", uploader.lower()) or "creator",
                        "streamer_avatar": "",
                        "creator": uploader,
                        "views": views,
                        "duration": duration,
                        "category": category if category and category != "all" else "YouTube Gaming",
                        "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(entry.get("timestamp") or time.time())),
                    })
                    if len(clips) >= target_limit:
                        break
                if len(clips) >= target_limit:
                    break
        return clips
    except Exception:
        return clips


TOPIC_INTENTS: Dict[str, Dict[str, Any]] = {
    "cs2": {
        "patterns": [
            r"\bcs2\b",
            r"\bcs\s*2\b",
            r"\bcsgo\b",
            r"\bcs:go\b",
            r"\bcounter[- ]?strike\b",
            r"\bcounter[- ]?strike[- ]?2\b",
            r"\bcase[s]?\b",
            r"\bunbox(ing)?\b",
            r"\bknife\b",
            r"\bdragon\s*lore\b",
            r"\bhowl\b",
            r"\bglove[s]?\b",
            r"\bgold\b",
            r"\bcase\s*opening[s]?\b",
            r"\bcrate[s]?\b",
            r"\bcs2\s*case\b",
            r"\bcsgo\s*case\b",
            r"\bdoppler\b",
            r"\bkarambit\b",
            r"\bbutterfly\b",
            r"\bclutch\b",
            r"\bace\b",
            r"\bawp\b",
            r"\bdeagle\b",
            r"\bmirage\b",
            r"\bdust2\b",
            r"\binferno\b",
            r"\bnuke\b",
        ],
        "kick_category": "counter-strike-2",
        "twitch_category": "Counter-Strike",
        "youtube_query": "cs2 clips moments highlights",
        "boost_streamers": ["ohnepixel", "anomaly", "s1mple", "m0nesy", "tarik", "flom", "gaules"],
        "bonus_keywords": [
            "cs2", "csgo", "counter-strike", "counter strike", "knife", "gold", "glove", "gloves",
            "dragon lore", "howl", "doppler", "sapphire", "ruby", "fade", "skin", "skins",
            "pull", "opened", "karambit", "butterfly", "crate", "case opening", "case", "unbox", "unboxing",
            "clutch", "ace", "awp", "deagle", "mirage", "dust2", "inferno", "nuke", "major"
        ],
    },
    "case_opening": {
        "patterns": [
            r"\bcase\s*opening[s]?\b",
            r"\bcases\b",
            r"\bunbox(ing)?\b",
            r"\bknife\b",
            r"\bglove[s]?\b",
            r"\bgold\b",
            r"\bkarambit\b",
            r"\bbutterfly\b",
            r"\bdoppler\b",
        ],
        "kick_category": "counter-strike-2",
        "twitch_category": "Counter-Strike",
        "youtube_query": "cs2 case opening knife gold clips",
        "boost_streamers": ["ohnepixel", "anomaly", "sparkles"],
        "bonus_keywords": [
            "case", "opening", "unbox", "unboxing", "knife", "gold", "glove", "gloves",
            "karambit", "butterfly", "doppler", "skin", "skins", "pull", "opened"
        ],
    },
    "slots": {
        "patterns": [
            r"\bslot[s]?\b",
            r"\bcasino\b",
            r"\bgambl(ing|e)\b",
            r"\bmax\s*win\b",
            r"\bbonus\s*hunt\b",
            r"\bstake\b",
            r"\bsweet\s*bonanza\b",
            r"\bgates\s*of\s*olympus\b",
            r"\bjackpot\b",
            r"\bplinko\b",
            r"\broulette\b",
            r"\bblackjack\b",
        ],
        "kick_category": "slots",
        "twitch_category": "Slots",
        "youtube_query": "slots max win big win bonus clips",
        "boost_streamers": ["roshtein", "trainwreckstv", "xposed", "classybeef", "deuceace"],
        "bonus_keywords": [
            "max win", "big win", "slot", "slots", "bonus", "hunt", "jackpot", "multi",
            "x1000", "x5000", "gates", "sweet bonanza", "pragmatic", "stake", "plinko"
        ],
    },
    "valorant": {
        "patterns": [
            r"\bval(orant)?\b",
            r"\bvct\b",
            r"\bradiant\b",
            r"\bvandal\b",
            r"\bphantom\b",
            r"\bjett\b",
            r"\breyna\b",
        ],
        "kick_category": "valorant",
        "twitch_category": "Valorant",
        "youtube_query": "valorant ace clutch clips",
        "boost_streamers": ["tarik", "kyedae", "tenz", "shroud", "subroza"],
        "bonus_keywords": ["valorant", "vct", "clutch", "ace", "radiant", "vandal", "phantom"],
    },
    "gta": {
        "patterns": [
            r"\bgta\b",
            r"\bgta\s*(v|5|rp)\b",
            r"\bfivem\b",
            r"\bnopixel\b",
            r"\bgrand\s*theft\s*auto\b",
        ],
        "kick_category": "grand-theft-auto-v",
        "twitch_category": "Grand Theft Auto V",
        "youtube_query": "gta rp funny clips moments",
        "boost_streamers": ["buddha", "xqc", "fuslie", "sykkuno"],
        "bonus_keywords": ["gta", "nopixel", "rp", "chase", "heist", "police"],
    },
    "fortnite": {
        "patterns": [
            r"\bfortnite\b",
            r"\bfn\b",
            r"\bvictory\s*royale\b",
        ],
        "kick_category": "fortnite",
        "twitch_category": "Fortnite",
        "youtube_query": "fortnite victory royale clutch clips",
        "boost_streamers": ["clix", "mongraal", "bugha", "tfue"],
        "bonus_keywords": ["fortnite", "victory royale", "clutch", "box", "build"],
    },
    "pack_opening": {
        "patterns": [
            r"\bpack\s*opening[s]?\b",
            r"\bpack[s]?\b",
            r"\bfifa\b",
            r"\bfc\s*24\b",
            r"\bfc\s*25\b",
            r"\bfut\b",
            r"\bicon\s*pull\b",
            r"\btcg\b",
            r"\bpokemon\b",
        ],
        "kick_category": "ea-sports-fc-24",
        "twitch_category": "EA Sports FC 24",
        "youtube_query": "fifa fc 25 pack opening walkout clips",
        "boost_streamers": ["castro_1021", "dannyaarons", "bateson87"],
        "bonus_keywords": [
            "pack", "packs", "icon", "toty", "tots", "walkout", "pele", "r9", "mbappe", "messi", "charizard",
        ],
    },
    "just_chatting": {
        "patterns": [
            r"\bjust\s*chatting\b",
            r"\birl\b",
            r"\bdrama\b",
            r"\bpodcast\b",
            r"\breaction[s]?\b",
        ],
        "kick_category": "just-chatting",
        "twitch_category": "Just Chatting",
        "youtube_query": "streamer funny moments reaction clips",
        "boost_streamers": ["kaicenat", "adinross", "hasanabi", "speed", "ishowspeed"],
        "bonus_keywords": ["irl", "drama", "react", "reaction", "funny", "podcast"],
    },
}


def search_unified_clips(
    query: str = "",
    platform: str = "all",
    category: str = "all",
    time_filter: str = "all",
    sort: str = "view",
    limit: int = 60,
) -> List[Dict[str, Any]]:
    """
    High-level clip discovery engine across Kick and Twitch.
    Supports topic intent detection (e.g. 'cs2', 'case opening', 'slots', 'pack opening'),
    streamer channel searching, game category mapping, and free-form title keyword matching.
    Uses concurrent multi-threaded fetching for maximum speed and zero-lag performance.
    """
    clean_query = (query or "").strip()
    clean_plat = (platform or "all").lower()
    clean_cat = (category or "all").lower()

    # Detect platform from query URL if given
    if "twitch.tv" in clean_query:
        clean_plat = "twitch"
        clean_query = re.sub(r"^https?://(?:www\.)?twitch\.tv/", "", clean_query).split("/")[0]
    elif "kick.com" in clean_query:
        clean_plat = "kick"
        clean_query = re.sub(r"^https?://(?:www\.)?kick\.com/", "", clean_query).split("/")[0]
    elif "youtube.com" in clean_query or "youtu.be" in clean_query:
        clean_plat = "youtube"

    q_lower = clean_query.lower()

    # 1. Detect Topic Intent (e.g. "cs2", "case opening", "slots", "valorant")
    matched_intent = None
    bonus_keywords: List[str] = []

    # Check query first
    if q_lower:
        for topic_name, intent_data in TOPIC_INTENTS.items():
            for pat in intent_data["patterns"]:
                if re.search(pat, q_lower):
                    matched_intent = intent_data
                    bonus_keywords = intent_data["bonus_keywords"]
                    break
            if matched_intent:
                break

    # Also check if query or category matches direct category aliases
    if not matched_intent and (q_lower in KICK_CAT_ALIASES or q_lower in TWITCH_GAME_ALIASES):
        k_cat = KICK_CAT_ALIASES.get(q_lower, q_lower.replace(" ", "-"))
        t_cat = TWITCH_GAME_ALIASES.get(q_lower, q_lower.title())
        matched_intent = {
            "kick_category": k_cat,
            "twitch_category": t_cat,
            "boost_streamers": [],
            "bonus_keywords": [q_lower],
        }
        bonus_keywords = [q_lower]

    # If no intent from query, check if category itself matches an intent or alias
    if not matched_intent and clean_cat != "all":
        for topic_name, intent_data in TOPIC_INTENTS.items():
            if clean_cat in (topic_name, topic_name.replace("_", "-"), topic_name.replace("_", " ")):
                matched_intent = intent_data
                bonus_keywords = intent_data["bonus_keywords"]
                break
        if not matched_intent and (clean_cat in KICK_CAT_ALIASES or clean_cat in TWITCH_GAME_ALIASES):
            matched_intent = {
                "kick_category": KICK_CAT_ALIASES.get(clean_cat, clean_cat.replace("_", "-")),
                "twitch_category": TWITCH_GAME_ALIASES.get(clean_cat, clean_cat.replace("_", " ").title()),
                "boost_streamers": [],
                "bonus_keywords": [clean_cat],
            }
            bonus_keywords = [clean_cat]

    all_results: List[Dict[str, Any]] = []

    # Helper for running safely in thread pool
    def _fetch_kick_safe(**kwargs):
        try:
            return fetch_kick_clips(**kwargs)
        except Exception:
            return []

    def _fetch_twitch_safe(**kwargs):
        try:
            return fetch_twitch_clips(**kwargs)
        except Exception:
            return []

    def _fetch_youtube_safe(**kwargs):
        try:
            return fetch_youtube_clips(**kwargs)
        except Exception:
            return []

    # Case A: Intent or Game Category Detected (e.g. CS2, Case Opening, Slots, Valorant)
    if matched_intent:
        kick_cat = matched_intent["kick_category"]
        tw_cat = matched_intent["twitch_category"]
        boost_streamers = matched_intent.get("boost_streamers", [])

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = []
            if clean_plat in ("all", "kick"):
                futures.append(pool.submit(_fetch_kick_safe, category_slug=kick_cat, sort=sort, time_filter=time_filter, limit=max(30, limit // 2)))
                for s in boost_streamers[:3]:
                    futures.append(pool.submit(_fetch_kick_safe, channel_slug=s, sort=sort, time_filter=time_filter, limit=15))
            if clean_plat in ("all", "twitch"):
                futures.append(pool.submit(_fetch_twitch_safe, category_name=tw_cat, time_filter=time_filter, limit=max(40, limit)))
                for s in boost_streamers[:3]:
                    futures.append(pool.submit(_fetch_twitch_safe, channel_slug=s, time_filter=time_filter, limit=20))
            if clean_plat in ("all", "youtube"):
                yt_q = matched_intent.get("youtube_query") or f"{clean_query} clips"
                futures.append(pool.submit(_fetch_youtube_safe, query=yt_q, limit=max(25, limit // 2)))

            for f in as_completed(futures):
                all_results.extend(f.result())

    # Case B: Streamer Channel Query (single word or @handle, no spaces, not a known intent)
    elif q_lower and (clean_query.startswith("@") or " " not in q_lower) and clean_cat == "all" and not clean_query.startswith("http"):
        handle = clean_query.lstrip("@#")
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = []
            if clean_plat in ("all", "kick"):
                futures.append(pool.submit(_fetch_kick_safe, channel_slug=handle, sort=sort, time_filter=time_filter, limit=limit))
            if clean_plat in ("all", "twitch"):
                futures.append(pool.submit(_fetch_twitch_safe, channel_slug=handle, time_filter=time_filter, limit=limit))
            if clean_plat in ("all", "youtube"):
                futures.append(pool.submit(_fetch_youtube_safe, channel_slug=handle, limit=limit))

            for f in as_completed(futures):
                all_results.extend(f.result())

        # If streamer channel returned 0 results, fall back to searching clips with this query as title keyword
        if not all_results:
            with ThreadPoolExecutor(max_workers=6) as pool:
                futures = []
                for cat_slug, game_name in [("counter-strike-2", "Counter-Strike"), ("valorant", "Valorant"), ("slots", "Slots")]:
                    if clean_plat in ("all", "kick"):
                        futures.append(pool.submit(_fetch_kick_safe, category_slug=cat_slug, sort=sort, time_filter=time_filter, limit=25))
                    if clean_plat in ("all", "twitch"):
                        futures.append(pool.submit(_fetch_twitch_safe, category_name=game_name, time_filter=time_filter, limit=25))
                if clean_plat in ("all", "youtube"):
                    futures.append(pool.submit(_fetch_youtube_safe, query=f"{clean_query} clips", limit=30))
                for f in as_completed(futures):
                    all_results.extend(f.result())

    # Case C: Freeform Keyword Search or Category Browse
    else:
        k_slug = None
        tw_name = None
        if clean_cat != "all":
            k_slug = KICK_CAT_ALIASES.get(clean_cat, clean_cat.replace("_", "-"))
            tw_name = TWITCH_GAME_ALIASES.get(clean_cat, clean_cat.replace("_", " ").title())

        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = []
            if clean_plat in ("all", "kick"):
                futures.append(pool.submit(_fetch_kick_safe, category_slug=k_slug, sort=sort, time_filter=time_filter, limit=limit))
            if clean_plat in ("all", "twitch"):
                futures.append(pool.submit(_fetch_twitch_safe, category_name=tw_name, time_filter=time_filter, limit=limit))
            if clean_plat in ("all", "youtube"):
                yt_query = clean_query or (clean_cat if clean_cat != "all" else "viral clips")
                futures.append(pool.submit(_fetch_youtube_safe, query=yt_query, category=clean_cat if clean_cat != "all" else None, limit=limit))
            for f in as_completed(futures):
                all_results.extend(f.result())

    # Deduplicate by URL or ID
    seen = set()
    deduped = []
    for c in all_results:
        key = c.get("url") or c.get("id")
        if key and key not in seen:
            seen.add(key)
            deduped.append(c)

    # Relevance Scoring & Ranking
    query_words = [w for w in q_lower.split() if len(w) >= 2] if q_lower else []

    def _score(clip: Dict[str, Any]) -> int:
        title = (clip.get("title") or "").lower()
        streamer = (clip.get("streamer") or "").lower()
        cat = (clip.get("category") or "").lower()
        views = int(clip.get("views") or 0)
        s = 0

        if q_lower:
            # Exact query matches
            if q_lower in title:
                s += 600
            if q_lower in streamer:
                s += 450
            if q_lower in cat:
                s += 500

            # Word-level matches
            for w in query_words:
                if w in title:
                    s += 150
                if w in streamer:
                    s += 120
                if w in cat:
                    s += 100

            # Bonus keywords from matched intent
            for kw in bonus_keywords:
                if kw in title:
                    s += 80
                if kw in cat:
                    s += 50

        # Intent category alignment
        if matched_intent:
            m_kick = (matched_intent.get("kick_category") or "").lower()
            m_tw = (matched_intent.get("twitch_category") or "").lower()
            if m_kick in cat or m_tw in cat or cat in (m_kick, m_tw):
                s += 300
            elif clip.get("platform") == "youtube":
                s += 200

        # Viral views tie-breaker (capped at +50 so relevance dominates)
        s += min(views // 3000, 50)
        return s

    if q_lower:
        # When a query is active, only retain relevant clips!
        if matched_intent:
            m_kick = (matched_intent.get("kick_category") or "").lower()
            m_tw = (matched_intent.get("twitch_category") or "").lower()
            filtered = [
                c for c in deduped
                if _score(c) >= 100 or m_kick in (c.get("category") or "").lower() or m_tw in (c.get("category") or "").lower()
                or (c.get("platform") == "youtube" and _score(c) >= 50)
            ]
            if filtered:
                deduped = filtered
        else:
            filtered = [c for c in deduped if _score(c) >= 60]
            if filtered:
                deduped = filtered

    if sort == "date":
        deduped.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    else:
        deduped.sort(key=_score, reverse=True)

    return deduped[:limit]


def download_stream_clip(
    url: str,
    output_target: Path,
    timeout: int = DOWNLOAD_TIMEOUT,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    duration: Optional[float] = None,
) -> Path:
    """
    Downloads a clip or VOD from Twitch, Kick, YouTube, or direct stream link using yt-dlp.
    Supports smart YouTube timestamp detection (?t=45s), custom section cutting, and format fallbacks.
    Returns the validated output Path.
    """
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        raise ValueError(f"Invalid clip URL format: {clean_url}")

    platform = detect_stream_platform(clean_url)
    ffmpeg_bin, _ = resolve_binary_paths()
    ffmpeg_dir = str(Path(ffmpeg_bin).parent)

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--ffmpeg-location", ffmpeg_dir,
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--no-check-certificates",
        "--retries", "3",
    ]

    # Handle YouTube timestamps and section clipping
    if platform == "youtube":
        if start_time is None:
            start_time = parse_youtube_timestamp(clean_url)

        is_short_or_clip = ("/shorts/" in clean_url.lower()) or ("/clip/" in clean_url.lower())

        if start_time is not None:
            if end_time is None:
                end_time = start_time + (float(duration) if duration else 60.0)
            cmd.extend(["--download-sections", f"*{start_time:.1f}-{end_time:.1f}"])
        elif not is_short_or_clip:
            if duration or end_time:
                s_t = float(start_time or 0.0)
                e_t = float(end_time) if end_time else (s_t + float(duration or 60.0))
                cmd.extend(["--download-sections", f"*{s_t:.1f}-{e_t:.1f}"])
    elif start_time is not None or end_time is not None:
        s_t = float(start_time or 0.0)
        e_t = float(end_time) if end_time else (s_t + float(duration or 60.0))
        cmd.extend(["--download-sections", f"*{s_t:.1f}-{e_t:.1f}"])

    cmd.extend(["-o", str(output_target), clean_url])

    def _execute_download() -> Path:
        res = run_command_safe(cmd, timeout=timeout)
        if res.returncode != 0:
            if output_target.is_file() and output_target.stat().st_size > 1024:
                return output_target
            err_msg = res.stderr.strip() or res.stdout.strip()
            raise RuntimeError(f"yt-dlp download failed ({platform}): {err_msg[:400]}")
        return output_target

    downloaded_file = retry_with_backoff(
        _execute_download,
        max_retries=2,
        initial_delay=2.0,
        task_name=f"Download {platform.capitalize()} clip ({clean_url})",
    )

    # Validate container
    validate_media_file(downloaded_file)
    return downloaded_file


# Backward-compatible alias for existing imports
download_kick_clip = download_stream_clip


def extract_preview_frame(
    video_path: Path,
    output_image_path: Path,
    timestamp: float = 2.0,
) -> Path:
    """
    Extracts a high-quality preview frame for crop calibration.
    """
    ffmpeg_bin, _ = resolve_binary_paths()
    metadata = validate_media_file(video_path)

    # Ensure timestamp is within valid video duration bounds
    dur = float(metadata.get("duration", 0.0))
    if dur > 0.2:
        target_ts = max(0.0, min(float(timestamp), max(0.0, dur - 0.1)))
    else:
        target_ts = 0.0

    cmd = [
        ffmpeg_bin,
        "-y",
        "-ss", f"{target_ts:.2f}",
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_image_path),
    ]

    res = run_command_safe(cmd, timeout=DEFAULT_TIMEOUT)
    if res.returncode != 0 or not output_image_path.is_file():
        raise RuntimeError(f"Failed to extract frame at {target_ts}s: {res.stderr.strip()[:300]}")

    return output_image_path
