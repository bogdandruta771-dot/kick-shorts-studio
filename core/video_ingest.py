"""Media ingestion via yt-dlp and container integrity validation via ffprobe."""
import json
import re
import sys
import urllib.request
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

    # Category normalization for Kick API slugs
    cat_aliases = {
        "casino": "slots",
        "gambling": "slots",
        "slots": "slots",
        "just_chatting": "just-chatting",
        "just chatting": "just-chatting",
        "irl": "irl",
        "gta": "grand-theft-auto-v",
        "grand theft auto v": "grand-theft-auto-v",
        "valorant": "valorant",
        "fortnite": "fortnite",
        "cs2": "counter-strike-2",
        "counter-strike": "counter-strike-2",
    }

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
        cat = cat_aliases.get(raw_cat, raw_cat.replace(" ", "-"))
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
        game_aliases = {
            "casino": "Slots",
            "slots": "Slots",
            "just_chatting": "Just Chatting",
            "just chatting": "Just Chatting",
            "irl": "Just Chatting",
            "gta": "Grand Theft Auto V",
            "valorant": "Valorant",
            "fortnite": "Fortnite",
            "cs2": "Counter-Strike",
            "counter-strike": "Counter-Strike",
        }
        raw_cat = (category_name or "Just Chatting").strip().lower()
        game_target = game_aliases.get(raw_cat, category_name or "Just Chatting")

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
    Searches channels, categories, or trending clips with automatic deduplication and view sorting.
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

    all_results: List[Dict[str, Any]] = []

    # 1. Fetch Kick Clips if requested
    if clean_plat in ("all", "kick"):
        try:
            k_clips = fetch_kick_clips(
                channel_slug=clean_query if clean_query else None,
                category_slug=clean_cat if clean_cat != "all" else None,
                sort=sort,
                time_filter=time_filter,
                limit=limit,
            )
            all_results.extend(k_clips)
        except Exception:
            pass

    # 2. Fetch Twitch Clips if requested
    if clean_plat in ("all", "twitch"):
        try:
            tw_clips = fetch_twitch_clips(
                channel_slug=clean_query if clean_query else None,
                category_name=clean_cat if clean_cat != "all" else None,
                time_filter=time_filter,
                limit=limit,
            )
            all_results.extend(tw_clips)
        except Exception:
            pass

    # Deduplicate by URL or ID
    seen = set()
    deduped = []
    for c in all_results:
        key = c.get("url") or c.get("id")
        if key and key not in seen:
            seen.add(key)
            deduped.append(c)

    # Sort results
    if sort == "date":
        deduped.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    else:
        deduped.sort(key=lambda x: int(x.get("views", 0)), reverse=True)

    return deduped[:limit]


def download_stream_clip(
    url: str,
    output_target: Path,
    timeout: int = DOWNLOAD_TIMEOUT,
) -> Path:
    """
    Downloads a clip or VOD from Twitch, Kick, YouTube, or direct stream link using yt-dlp.
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
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--no-check-certificates",
        "--retries", "3",
        "-o", str(output_target),
        clean_url,
    ]

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
