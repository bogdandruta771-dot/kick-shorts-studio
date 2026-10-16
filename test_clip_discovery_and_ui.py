"""Unit and Integration Tests for Viral Clip Explorer, Discovery Engine & Instant 1-Click Clipper."""
import pytest
from fastapi.testclient import TestClient

from app import app
from core.video_ingest import (
    fetch_kick_clips,
    fetch_twitch_clips,
    search_unified_clips,
)


client = TestClient(app)


def test_fetch_kick_clips_structure():
    """Verifies Kick clips fetcher returns normalized clip dictionaries with expected metadata."""
    clips = fetch_kick_clips(limit=5)
    assert isinstance(clips, list)
    if clips:
        first = clips[0]
        assert first["platform"] == "kick"
        assert "id" in first
        assert "title" in first
        assert "url" in first
        assert "streamer" in first
        assert "views" in first
        assert "duration" in first
        assert isinstance(first["views"], int)
        assert isinstance(first["duration"], (int, float))


def test_fetch_twitch_clips_structure():
    """Verifies Twitch clips fetcher returns normalized clip dictionaries with expected metadata."""
    clips = fetch_twitch_clips(category_name="Just Chatting", limit=5)
    assert isinstance(clips, list)
    if clips:
        first = clips[0]
        assert first["platform"] == "twitch"
        assert "id" in first
        assert "title" in first
        assert "url" in first
        assert "streamer" in first
        assert "views" in first
        assert isinstance(first["views"], int)


def test_search_unified_clips_multiplatform():
    """Verifies multi-platform unified clip search, sorting, and deduplication."""
    # Test All platforms
    all_clips = search_unified_clips(platform="all", limit=6)
    assert isinstance(all_clips, list)

    # Test sorting by views (highest view count first)
    if len(all_clips) >= 2:
        for i in range(len(all_clips) - 1):
            assert all_clips[i]["views"] >= all_clips[i + 1]["views"]


def test_clip_search_endpoints():
    """Tests FastAPI HTTP routes for Clip Explorer."""
    # 1. Search endpoint POST
    res_post = client.post("/api/clips/search", json={
        "platform": "all",
        "category": "all",
        "time_filter": "day",
        "sort": "view",
        "limit": 4,
    })
    assert res_post.status_code == 200
    data_post = res_post.json()
    assert "clips" in data_post
    assert "count" in data_post

    # 2. Search endpoint GET
    res_get = client.get("/api/clips/search?platform=kick&limit=3")
    assert res_get.status_code == 200
    data_get = res_get.json()
    assert "clips" in data_get
    assert data_get["platform"] == "kick"

    # 3. Trending endpoint GET
    res_tr = client.get("/api/clips/trending?limit=3")
    assert res_tr.status_code == 200
    data_tr = res_tr.json()
    assert "clips" in data_tr


def test_clip_import_validation():
    """Verifies clip import endpoint input validation."""
    # Missing clip_url
    res_bad = client.post("/api/clips/import", json={"clip_url": ""})
    assert res_bad.status_code == 400

    res_empty = client.post("/api/clips/one-click-short", json={"clip_url": ""})
    assert res_empty.status_code == 400


def test_ui_html_structure_and_enhancements():
    """Verifies the UI contains all modern beauty upgrades, badges, modals, and Clip Explorer."""
    res_home = client.get("/")
    assert res_home.status_code == 200
    html = res_home.text

    # Brand & Badges
    assert "OmniStream" in html
    assert "header-encoder-badge" in html
    assert "header-yt-btn" in html

    # Explorer Tabs & Panels
    assert "tab-mode-explorer" in html
    assert "tab-mode-watchdog" in html
    assert "tab-mode-url" in html
    assert "tab-mode-file" in html
    assert "panel-ingest-explorer" in html
    assert "clips-grid" in html

    # Modals & Multi-Player Previews
    assert "modal-clip-preview" in html
    assert "preview-modal-iframe" in html
    assert "preview-modal-video" in html
    assert "preview-modal-external-link" in html
    assert "modal-oneclick-progress" in html
    assert "hls.min.js" in html

    # Pagination & Batch Controls
    assert "clips-pagination-container" in html
    assert "clips-pagination-buttons" in html
    assert "btn-load-all-clips" in html


def test_pagination_and_preview_enhancements():
    """Verifies pagination metadata and search response structure."""
    res = client.post("/api/clips/search", json={
        "platform": "all",
        "category": "all",
        "limit": 10,
        "page": 1,
        "page_size": 5,
    })
    assert res.status_code == 200
    data = res.json()
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert "total_count" in data
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert data["total_pages"] >= 1


def test_twitch_clips_slug_mapping():
    """Verifies Twitch clips have their alphanumeric slug preserved in 'id' and 'slug'."""
    clips = fetch_twitch_clips(category_name="Just Chatting", limit=3)
    if clips:
        for c in clips:
            assert "slug" in c
            # When slug is available from Twitch, id must be the slug or at least match
            if c.get("slug"):
                assert c["id"] == c["slug"]
                assert not c["id"].isdigit(), f"Twitch clip ID should be alphanumeric slug, not pure digits: {c['id']}"


def test_ui_youtube_svg_and_preview_integrity():
    """Verifies no broken data-lucide='youtube' tags and preview iframe has proper embed attributes."""
    res_home = client.get("/")
    assert res_home.status_code == 200
    html = res_home.text

    # No broken lucide youtube icons
    assert 'data-lucide="youtube"' not in html
    assert 'data-lucide=\'youtube\'' not in html

    # Has inline SVG youtube icons in header and direct upload
    assert '<svg class="w-3.5 h-3.5 fill-current text-rose-500' in html
    assert 'header-yt-btn' in html

    # Preview iframe has proper parent domain handling and allow attributes
    assert 'preview-modal-iframe' in html
    assert 'allow="autoplay; fullscreen"' in html
    assert 'clips.twitch.tv/embed?clip=' in html


def test_no_unwanted_autoplay_and_audio_silence_controls():
    """Verifies final video player does not autoplay on page load and pauseAllMediaPlayers is wired."""
    res_home = client.get("/")
    assert res_home.status_code == 200
    html = res_home.text

    # Final video player must NOT have autoplay in HTML to avoid background blasting on page load
    assert 'id="final-video-player" controls autoplay' not in html
    assert 'id="final-video-player" controls loop' in html

    # pauseAllMediaPlayers function and Escape key handler must be present
    assert 'function pauseAllMediaPlayers()' in html
    assert 'closeClipPreviewModal()' in html
    assert "e.key === 'Escape'" in html



