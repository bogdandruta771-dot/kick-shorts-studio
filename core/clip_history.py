"""
Clip History & Anti-Repeat Database Engine
Tracks all processed clips, VODs, and streams to prevent accidental duplicate clipping.
Provides lightning-fast fuzzy & canonical URL matching, clip explorer badges,
and historical export logs.
"""
import sqlite3
import json
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "clip_history.sqlite"


def get_db_connection() -> sqlite3.Connection:
    """Creates a thread-safe connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH), timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_history_db():
    """Initializes SQLite schema for clip history and duplicate prevention."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clip_history (
                id TEXT PRIMARY KEY,
                clean_id TEXT NOT NULL,
                source_url TEXT NOT NULL,
                platform TEXT NOT NULL,
                title TEXT,
                channel TEXT,
                thumbnail_url TEXT,
                duration REAL DEFAULT 0.0,
                first_clipped_at TEXT NOT NULL,
                last_clipped_at TEXT NOT NULL,
                clip_count INTEGER DEFAULT 1,
                outputs_json TEXT DEFAULT '[]',
                notes TEXT DEFAULT ''
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_clean_id ON clip_history(clean_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_platform ON clip_history(platform);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_channel ON clip_history(channel);")
        conn.commit()


# Initialize schema on module import
init_history_db()


def normalize_source_id(url_or_id: str) -> Tuple[str, str, str]:
    """
    Extracts platform and a canonical, query-agnostic ID from any video URL or identifier.
    Returns: (canonical_key, platform, clean_id)
    """
    raw = str(url_or_id).strip()
    if not raw:
        return ("", "unknown", "")

    # 1. Kick Clip / Stream
    # e.g. https://kick.com/streamer?clip=clip_01HR... or https://kick.com/clip/clip_01HR...
    kick_clip_m = re.search(r"clip[=/](clip_[a-zA-Z0-9_-]+)", raw, re.IGNORECASE)
    if kick_clip_m:
        clean_id = kick_clip_m.group(1)
        return (f"kick:{clean_id.lower()}", "kick", clean_id)

    if "kick.com" in raw:
        # Kick channel / stream / video
        kick_vod_m = re.search(r"kick\.com/[^/]+/videos/([a-zA-Z0-9-]+)", raw, re.IGNORECASE)
        if kick_vod_m:
            clean_id = kick_vod_m.group(1)
            return (f"kick:vod_{clean_id.lower()}", "kick", clean_id)
        # Fallback to normalized channel or URL path
        slug = raw.split("kick.com/")[-1].split("?")[0].strip("/").lower()
        return (f"kick:slug_{slug}", "kick", slug)

    # 2. Twitch Clip / VOD
    # e.g. https://clips.twitch.tv/SpeedyBraveHawk or https://www.twitch.tv/streamer/clip/SpeedyBraveHawk
    twitch_clip_m = re.search(r"(?:clips\.twitch\.tv/|twitch\.tv/[^/]+/clip/)([a-zA-Z0-9_-]+)", raw, re.IGNORECASE)
    if twitch_clip_m:
        clean_id = twitch_clip_m.group(1)
        return (f"twitch:{clean_id.lower()}", "twitch", clean_id)

    if "twitch.tv" in raw:
        twitch_vod_m = re.search(r"twitch\.tv/videos/(\d+)", raw, re.IGNORECASE)
        if twitch_vod_m:
            clean_id = twitch_vod_m.group(1)
            return (f"twitch:vod_{clean_id}", "twitch", clean_id)
        slug = raw.split("twitch.tv/")[-1].split("?")[0].strip("/").lower()
        return (f"twitch:slug_{slug}", "twitch", slug)

    # 3. YouTube Shorts / Video / Clip
    yt_clip_m = re.search(r"youtube\.com/clip/([a-zA-Z0-9_-]+)", raw, re.IGNORECASE)
    if yt_clip_m:
        clean_id = yt_clip_m.group(1)
        return (f"youtube:clip_{clean_id}", "youtube", clean_id)

    yt_m = re.search(r"(?:youtube\.com/(?:watch\?v=|shorts/|embed/)|youtu\.be/)([a-zA-Z0-9_-]{11})", raw, re.IGNORECASE)
    if yt_m:
        clean_id = yt_m.group(1)
        return (f"youtube:{clean_id}", "youtube", clean_id)

    # 4. Local media file
    p = Path(raw)
    if p.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm", ".avi"]:
        clean_id = p.stem.lower()
        return (f"local:{clean_id}", "local", clean_id)

    # Generic string / slug identifier
    clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", raw).lower()[:64]
    return (f"generic:{clean_id}", "generic", clean_id)


def check_if_clipped(url_or_id: str) -> Dict[str, Any]:
    """
    Checks if a given video URL or clip ID has already been processed into a short.
    Returns:
        {
            "is_clipped": True/False,
            "record": dict or None,
            "clip_count": int,
            "latest_output": str,
            "first_clipped_at": str,
            "last_clipped_at": str
        }
    """
    canonical_key, platform, clean_id = normalize_source_id(url_or_id)
    if not canonical_key:
        return {"is_clipped": False, "record": None, "clip_count": 0}

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM clip_history WHERE id = ? OR clean_id = ?",
            (canonical_key, clean_id)
        ).fetchone()

        if not row:
            return {"is_clipped": False, "record": None, "clip_count": 0}

        rec = dict(row)
        try:
            outputs = json.loads(rec.get("outputs_json") or "[]")
        except Exception:
            outputs = []

        latest_output = outputs[-1].get("filename", "") if outputs else ""

        return {
            "is_clipped": True,
            "record": rec,
            "clip_count": rec.get("clip_count", 1),
            "latest_output": latest_output,
            "first_clipped_at": rec.get("first_clipped_at", ""),
            "last_clipped_at": rec.get("last_clipped_at", ""),
            "outputs": outputs,
        }


def record_clipped_short(
    source_url: str,
    output_filename: str,
    title: str = "",
    channel: str = "",
    thumbnail_url: str = "",
    duration: float = 0.0,
    preset: str = "",
    subtitle_style: str = "",
    ai_title: str = "",
) -> Dict[str, Any]:
    """
    Records or updates a processed clip entry in the history database.
    Increments clip_count and appends generated short details to outputs_json.
    """
    canonical_key, platform, clean_id = normalize_source_id(source_url)
    if not canonical_key:
        canonical_key = f"manual_{int(time.time())}"
        platform = "manual"
        clean_id = canonical_key

    now_iso = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    new_output_entry = {
        "filename": output_filename,
        "video_url": f"/output/{output_filename}",
        "created_at": now_iso,
        "preset": preset,
        "subtitle_style": subtitle_style,
        "ai_title": ai_title,
    }

    with get_db_connection() as conn:
        existing = conn.execute(
            "SELECT * FROM clip_history WHERE id = ? OR clean_id = ?",
            (canonical_key, clean_id)
        ).fetchone()

        if existing:
            rec = dict(existing)
            try:
                outputs = json.loads(rec.get("outputs_json") or "[]")
            except Exception:
                outputs = []

            # Avoid exact duplicate output filename entries
            if not any(o.get("filename") == output_filename for o in outputs):
                outputs.append(new_output_entry)

            new_count = rec.get("clip_count", 0) + 1
            updated_title = title or rec.get("title") or ""
            updated_channel = channel or rec.get("channel") or ""
            updated_thumb = thumbnail_url or rec.get("thumbnail_url") or ""

            conn.execute("""
                UPDATE clip_history
                SET last_clipped_at = ?,
                    clip_count = ?,
                    outputs_json = ?,
                    title = ?,
                    channel = ?,
                    thumbnail_url = ?
                WHERE id = ?
            """, (now_iso, new_count, json.dumps(outputs), updated_title, updated_channel, updated_thumb, rec["id"]))
            conn.commit()

            return {
                "id": rec["id"],
                "is_new": False,
                "clip_count": new_count,
                "first_clipped_at": rec["first_clipped_at"],
                "last_clipped_at": now_iso,
            }
        else:
            outputs = [new_output_entry]
            conn.execute("""
                INSERT INTO clip_history (
                    id, clean_id, source_url, platform, title, channel,
                    thumbnail_url, duration, first_clipped_at, last_clipped_at,
                    clip_count, outputs_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """, (
                canonical_key, clean_id, source_url, platform, title, channel,
                thumbnail_url, duration, now_iso, now_iso, json.dumps(outputs)
            ))
            conn.commit()

            return {
                "id": canonical_key,
                "is_new": True,
                "clip_count": 1,
                "first_clipped_at": now_iso,
                "last_clipped_at": now_iso,
            }


def tag_clip_search_results(clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Batches lookup against clip_history database and tags every clip dictionary with:
    - is_already_clipped: bool
    - clip_count: int
    - clipped_date: str
    - latest_short_filename: str
    Runs in a single fast query for up to hundreds of clips.
    """
    if not clips:
        return []

    # Map each clip's possible identifier to index
    id_map: Dict[str, List[int]] = {}
    clean_ids: List[str] = []

    for idx, c in enumerate(clips):
        url = c.get("clip_url") or c.get("url") or ""
        clip_id = c.get("id") or ""
        ck1, _, cid1 = normalize_source_id(url)
        ck2, _, cid2 = normalize_source_id(clip_id)

        for candidate in set(filter(None, [ck1, cid1, ck2, cid2])):
            id_map.setdefault(candidate, []).append(idx)
            clean_ids.append(candidate)

    if not clean_ids:
        for c in clips:
            c["is_already_clipped"] = False
        return clips

    placeholders = ",".join(["?"] * len(clean_ids))
    with get_db_connection() as conn:
        cursor = conn.execute(
            f"SELECT id, clean_id, last_clipped_at, clip_count, outputs_json FROM clip_history WHERE id IN ({placeholders}) OR clean_id IN ({placeholders})",
            clean_ids + clean_ids
        )
        rows = cursor.fetchall()

    # Pre-default all clips to not clipped
    for c in clips:
        c["is_already_clipped"] = False
        c["clip_count"] = 0
        c["clipped_date"] = ""
        c["latest_short_filename"] = ""

    for r in rows:
        cid = r["clean_id"]
        canonical_id = r["id"]
        matched_indices = set(id_map.get(cid, []) + id_map.get(canonical_id, []))
        
        try:
            outputs = json.loads(r["outputs_json"] or "[]")
        except Exception:
            outputs = []
        latest_fn = outputs[-1].get("filename", "") if outputs else ""

        for idx in matched_indices:
            clips[idx]["is_already_clipped"] = True
            clips[idx]["clip_count"] = r["clip_count"]
            clips[idx]["clipped_date"] = r["last_clipped_at"]
            clips[idx]["latest_short_filename"] = latest_fn

    return clips


def list_clip_history(
    search: str = "",
    platform: str = "all",
    page: int = 1,
    page_size: int = 30
) -> Dict[str, Any]:
    """
    Returns paginated list of historically clipped videos with search & filter.
    """
    offset = max(0, (page - 1) * page_size)
    conditions = []
    params = []

    if search.strip():
        s = f"%{search.strip().lower()}%"
        conditions.append("(LOWER(title) LIKE ? OR LOWER(channel) LIKE ? OR LOWER(source_url) LIKE ?)")
        params.extend([s, s, s])

    if platform and platform != "all":
        conditions.append("platform = ?")
        params.append(platform.lower())

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_db_connection() as conn:
        count_cursor = conn.execute(f"SELECT COUNT(*) as total FROM clip_history {where_clause}", params)
        total_count = count_cursor.fetchone()["total"]

        query = f"""
            SELECT * FROM clip_history
            {where_clause}
            ORDER BY datetime(last_clipped_at) DESC
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(query, params + [page_size, offset]).fetchall()

    records = []
    for r in rows:
        d = dict(r)
        try:
            d["outputs"] = json.loads(d.get("outputs_json") or "[]")
        except Exception:
            d["outputs"] = []
        records.append(d)

    total_pages = max(1, (total_count + page_size - 1) // page_size) if total_count > 0 else 1

    return {
        "records": records,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "search": search,
        "platform": platform,
    }


def delete_history_item(item_id: str) -> bool:
    """Deletes an item from clip history by primary key or clean_id."""
    canonical_key, _, clean_id = normalize_source_id(item_id)
    with get_db_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM clip_history WHERE id = ? OR clean_id = ? OR id = ?",
            (canonical_key, clean_id, item_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def clear_all_history() -> int:
    """Clears all records in clip history."""
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM clip_history;")
        conn.commit()
        return cursor.rowcount
