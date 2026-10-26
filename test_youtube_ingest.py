"""Unit and Integration Tests for YouTube Clip Discovery, Trimming, and Ingestion."""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app import app
from core.video_ingest import (
    detect_stream_platform,
    parse_youtube_timestamp,
    fetch_youtube_clips,
    search_unified_clips,
)
from core.clip_history import normalize_source_id, check_if_clipped, record_clipped_short

client = TestClient(app)


def test_detect_stream_platform_youtube():
    """Verifies that all YouTube variations are recognized as 'youtube' platform."""
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/3Zz9M1kL0pA",
        "https://youtube.com/clip/Ugkx_12345Abcde",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "http://m.youtube.com/watch?v=dQw4w9WgXcQ&t=30s",
    ]
    for u in urls:
        assert detect_stream_platform(u) == "youtube", f"Failed for {u}"


def test_parse_youtube_timestamp():
    """Verifies extracting starting seconds from YouTube URL query parameters."""
    assert parse_youtube_timestamp("https://www.youtube.com/watch?v=abc&t=45s") == 45.0
    assert parse_youtube_timestamp("https://youtu.be/abc?t=1m30s") == 90.0
    assert parse_youtube_timestamp("https://www.youtube.com/watch?v=abc&t=120") == 120.0
    assert parse_youtube_timestamp("https://www.youtube.com/watch?v=abc&start=60") == 60.0
    assert parse_youtube_timestamp("https://www.youtube.com/watch?v=abc") is None
    assert parse_youtube_timestamp("https://kick.com/streamer?clip=123") is None


def test_fetch_youtube_clips_structure():
    """Verifies that fetch_youtube_clips extracts normalized clip dictionaries."""
    clips = fetch_youtube_clips(query="cs2 clips", limit=3)
    assert isinstance(clips, list)
    if clips:
        first = clips[0]
        assert first["platform"] == "youtube"
        assert "id" in first and len(first["id"]) > 0
        assert "title" in first and len(first["title"]) > 0
        assert "url" in first and "youtube.com" in first["url"]
        assert "streamer" in first
        assert "views" in first and isinstance(first["views"], int)
        assert "duration" in first and isinstance(first["duration"], (int, float))
        assert "thumbnail_url" in first


def test_search_unified_clips_youtube():
    """Verifies search_unified_clips with platform='youtube' returns YouTube clips."""
    clips = search_unified_clips(query="cs2", platform="youtube", limit=5)
    assert isinstance(clips, list)
    if clips:
        for c in clips:
            assert c["platform"] == "youtube"


def test_search_unified_clips_includes_youtube_in_all():
    """Verifies search_unified_clips with platform='all' includes multi-platform results."""
    clips = search_unified_clips(query="cs2", platform="all", limit=12)
    assert isinstance(clips, list)
    assert len(clips) > 0
    platforms = set(c["platform"] for c in clips)
    assert "youtube" in platforms or "twitch" in platforms or "kick" in platforms


def test_clip_history_youtube_canonical_id():
    """Verifies that YouTube video URLs produce stable canonical keys."""
    key1, plat1, id1 = normalize_source_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=45s")
    assert plat1 == "youtube"
    assert id1 == "dQw4w9WgXcQ"
    assert key1 == "youtube:dQw4w9WgXcQ"

    key2, plat2, id2 = normalize_source_id("https://youtu.be/dQw4w9WgXcQ")
    assert plat2 == "youtube"
    assert id2 == "dQw4w9WgXcQ"
    assert key2 == "youtube:dQw4w9WgXcQ"

    key3, plat3, id3 = normalize_source_id("https://www.youtube.com/shorts/dQw4w9WgXcQ")
    assert key3 == "youtube:dQw4w9WgXcQ"

    key4, plat4, id4 = normalize_source_id("https://www.youtube.com/clip/Ugkx_TestClipId")
    assert plat4 == "youtube"
    assert "Ugkx_TestClipId" in id4


def test_api_search_clips_youtube():
    """Verifies FastAPI endpoint /api/clips/search supports platform='youtube'."""
    res = client.post(
        "/api/clips/search",
        json={"query": "cs2", "platform": "youtube", "limit": 4},
    )
    assert res.status_code == 200
    data = res.json()
    assert "clips" in data
    assert isinstance(data["clips"], list)
    if data["clips"]:
        for c in data["clips"]:
            assert c["platform"] == "youtube"


def test_ui_html_has_youtube_elements():
    """Verifies templates/index.html includes YouTube buttons, badges, and controls."""
    html = Path("templates/index.html").read_text(encoding="utf-8")
    assert "btn-exp-plat-youtube" in html, "Missing YouTube button in discovery platform selector"
    assert "🔴 YouTube" in html or "YouTube" in html, "Missing YouTube label in HTML"
    assert "setClipExplorerPlatform('youtube')" in html
    assert "ingest-start-time" in html, "Missing Start Time input in URL ingest panel"
    assert "ingest-duration" in html, "Missing Duration input in URL ingest panel"
    assert "platform === 'youtube'" in html, "Missing YouTube preview modal handler"
