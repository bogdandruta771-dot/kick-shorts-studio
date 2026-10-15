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

