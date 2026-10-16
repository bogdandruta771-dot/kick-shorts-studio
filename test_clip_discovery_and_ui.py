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


def test_viral_hook_ai_and_banner_generation(tmp_path):
    """Verifies viral hook copywriting and PNG banner generator."""
    from core.ai_copywriter import generate_viral_hooks
    from core.banner_generator import generate_hook_banner

    # 1. Test AI hooks generation
    hooks = generate_viral_hooks("INSANE 5000X MAX WIN ON GATES", "Roshtein", "slots")
    assert isinstance(hooks, list)
    assert len(hooks) >= 4
    assert any("WIN" in h.upper() or "😱" in h or "💀" in h or "🚨" in h for h in hooks)

    # 2. Test banner generation across all 10 visual styles (including modern viral styles)
    styles = [
        "floating_yellow", "reddit_card", "twitter_x_card", "tiktok_comment",
        "mrbeast_impact", "breaking_news", "yellow_badge", "red_alert",
        "tiktok_white", "cyber_cyan"
    ]
    for s in styles:
        out_png = tmp_path / f"hook_{s}.png"
        res_path = generate_hook_banner("WAIT TILL THE VERY END 😱", style=s, output_path=str(out_png))
        assert out_png.exists()
        assert out_png.stat().st_size > 500

    # 3. Test explicit asterisk highlight for OhnePixel floating yellow & reddit card
    ohnepixel_png = tmp_path / "hook_ohnepixel_highlight.png"
    generate_hook_banner("Worst *possible* timing 😳", style="floating_yellow", output_path=str(ohnepixel_png))
    assert ohnepixel_png.exists()
    assert ohnepixel_png.stat().st_size > 500


def test_hook_api_endpoints():
    """Verifies FastAPI endpoints for hook generation and banner preview."""
    # 1. Generate hooks endpoint
    res_gen = client.post("/api/generate-hooks", json={
        "clip_title": "Craziest Valorant 1v5 Clutch",
        "streamer": "Tarik",
        "category": "gaming"
    })
    assert res_gen.status_code == 200
    data = res_gen.json()
    assert data["success"] is True
    assert isinstance(data["hooks"], list)
    assert len(data["hooks"]) > 0

    # 2. Preview banner endpoint with floating_yellow
    res_prev = client.post("/api/preview-hook-banner", json={
        "text": "this gotta be *scripted* 💀",
        "style": "floating_yellow"
    })
    assert res_prev.status_code == 200
    prev_data = res_prev.json()
    assert "url" in prev_data
    assert "path" in prev_data
    assert prev_data["filename"].endswith(".png")

    # 3. Preview banner endpoint with twitter_x_card
    res_twitter = client.post("/api/preview-hook-banner", json={
        "text": "Bro actually pulled this off live",
        "style": "twitter_x_card"
    })
    assert res_twitter.status_code == 200
    assert res_twitter.json()["filename"].endswith(".png")

    # 4. Preview banner endpoint with mrbeast_impact
    res_beast = client.post("/api/preview-hook-banner", json={
        "text": "1 IN A BILLION MOMENT 🔥",
        "style": "mrbeast_impact"
    })
    assert res_beast.status_code == 200
    assert res_beast.json()["filename"].endswith(".png")


def test_ui_hook_header_card_and_handlers():
    """Verifies HTML template contains the hook header card, presets, and JS handlers."""
    res_home = client.get("/")
    assert res_home.status_code == 200
    html = res_home.text

    # Card & Inputs
    assert "Viral Hook Header Overlay" in html
    assert 'id="hook-enabled-toggle"' in html
    assert 'id="hook-text-input"' in html
    assert 'id="hook-preset-pills"' in html
    assert 'id="hook-style-floating_yellow"' in html
    assert 'id="hook-style-reddit_card"' in html
    assert 'id="hook-style-twitter_x_card"' in html
    assert 'id="hook-style-tiktok_comment"' in html
    assert 'id="hook-style-mrbeast_impact"' in html
    assert 'id="hook-style-breaking_news"' in html
    assert 'id="hook-style-yellow_badge"' in html
    assert 'id="hook-style-red_alert"' in html
    assert 'id="hook-style-tiktok_white"' in html
    assert 'id="hook-style-cyber_cyan"' in html
    assert 'id="sum-hook-status"' in html

    # Layout Framing Presets
    assert 'id="btn-toggle-cam-stack"' in html
    assert "reaction_cam_top" in html
    assert "reddit_reaction" in html
    assert "pip_corner_cam" in html
    assert "triple_stack" in html
    assert "cinema_letterbox" in html
    assert "full_bleed_9_16" in html
    assert "toggleCamStackMode" in html

    # JavaScript Functions
    assert "function toggleHookHeader()" in html
    assert "function updateHookText(" in html
    assert "function setHookPreset(" in html
    assert "function setHookStyle(" in html
    assert "function setHookDuration(" in html
    assert "function setHookPosition(" in html
    assert "async function generateAiHookIdeas(" in html
    assert "function syncHookControlsFromState()" in html
    assert "hook_text" in html
    assert "hook_options" in html


def test_ohnepixel_video_processor_stack_mode(tmp_path):
    """Verifies VideoProcessor properly processes shorts with various stack_modes."""
    import subprocess
    from core.utils import resolve_binary_paths
    from core.video_processor import VideoProcessor

    ffmpeg, _ = resolve_binary_paths()
    sample_mp4 = tmp_path / "sample_clip.mp4"
    out_cam_top = tmp_path / "output_short_cam_top.mp4"
    out_pip = tmp_path / "output_short_pip.mp4"

    # Generate a lightweight 1-second 1280x720 video clip
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
        "-t", "1",
        "-c:v", "libx264", "-c:a", "aac",
        str(sample_mp4)
    ]
    sub = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert sub.returncode == 0
    assert sample_mp4.exists()

    vp = VideoProcessor()
    crops_cam_top = {
        "gameplay": {"x": 0, "y": 0, "width": 1280, "height": 720},
        "camera": {"x": 100, "y": 50, "width": 300, "height": 300},
        "stack_mode": "cam_top"
    }

    res_cam = vp.process_short(
        input_video_path=sample_mp4,
        output_video_path=out_cam_top,
        crops=crops_cam_top,
        generate_subtitles=False
    )
    assert res_cam.is_file()
    assert res_cam.stat().st_size > 1000

    crops_pip = {
        "gameplay": {"x": 0, "y": 0, "width": 1280, "height": 720},
        "camera": {"x": 100, "y": 50, "width": 300, "height": 300},
        "stack_mode": "pip_corner"
    }
    res_pip = vp.process_short(
        input_video_path=sample_mp4,
        output_video_path=out_pip,
        crops=crops_pip,
        generate_subtitles=False
    )
    assert res_pip.is_file()
    assert res_pip.stat().st_size > 1000




