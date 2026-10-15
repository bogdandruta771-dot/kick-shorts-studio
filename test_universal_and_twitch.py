"""Unit and Integration Tests for Universal Stream Support & Twitch Ingestion."""
import pytest
from fastapi.testclient import TestClient

from app import app
from core.config import (
    CROP_PRESETS,
    GAMING_KEYWORDS,
    IRL_KEYWORDS,
    CASINO_KEYWORDS,
    ALL_HYPE_KEYWORDS,
)
from core.video_ingest import detect_stream_platform
from core.detector import (
    UniversalWatchdogManager,
    TwitchIrcChatSentinel,
    sanitize_channel_slug,
)
from core.ai_copywriter import generate_offline_shorts_copy, generate_shorts_metadata


client = TestClient(app)


def test_detect_stream_platform():
    """Verifies stream platform auto-detection across Twitch, Kick, YouTube, and generic URLs."""
    # Twitch clips
    assert detect_stream_platform("https://clips.twitch.tv/HedonisticMule") == "twitch"
    assert detect_stream_platform("https://www.twitch.tv/tarik/clip/AwesomeClutch") == "twitch"
    assert detect_stream_platform("https://twitch.tv/shroud") == "twitch"

    # Kick clips
    assert detect_stream_platform("https://kick.com/xqc?clip=clip_01J8ABC") == "kick"
    assert detect_stream_platform("https://kick.com/trainwreckstv") == "kick"

    # YouTube
    assert detect_stream_platform("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "youtube"
    assert detect_stream_platform("https://youtu.be/dQw4w9WgXcQ") == "youtube"

    # Generic
    assert detect_stream_platform("https://example.com/stream_highlight.mp4") == "generic"


def test_sanitize_channel_slug():
    """Verifies channel slug parsing for both Kick and Twitch formats."""
    assert sanitize_channel_slug("tarik") == "tarik"
    assert sanitize_channel_slug("https://www.twitch.tv/shroud") == "shroud"
    assert sanitize_channel_slug("https://clips.twitch.tv/tarik") == "tarik"
    assert sanitize_channel_slug("@pokimane") == "pokimane"
    assert sanitize_channel_slug("#val_official") == "val_official"
    assert sanitize_channel_slug("https://kick.com/xqc") == "xqc"


def test_crop_presets_coverage():
    """Verifies categorized crop presets exist for gaming, IRL, podcasts, casino, and ambient."""
    assert "gaming_fps" in CROP_PRESETS
    assert "gaming_moba" in CROP_PRESETS
    assert "gaming_centered" in CROP_PRESETS
    assert "reaction_standard" in CROP_PRESETS
    assert "reaction_interview" in CROP_PRESETS
    assert "podcast_split" in CROP_PRESETS
    assert "center_slot" in CROP_PRESETS
    assert "roulette_table" in CROP_PRESETS
    assert "ambient_blur_16_9" in CROP_PRESETS

    # Check structure
    for key, val in CROP_PRESETS.items():
        assert "gameplay" in val
        assert "facecam" in val
        assert all(k in val["gameplay"] for k in ("x", "y", "w", "h"))
        assert all(k in val["facecam"] for k in ("x", "y", "w", "h"))


def test_twitch_irc_sentinel_keywords():
    """Verifies Twitch IRC sentinel keyword matching across gaming, IRL, and casino categories."""
    sentinel_gaming = TwitchIrcChatSentinel("tarik", stream_category="gaming")
    assert any("pog" in kw for kw in sentinel_gaming._active_keywords)
    assert any("clutch" in kw for kw in sentinel_gaming._active_keywords)

    sentinel_irl = TwitchIrcChatSentinel("hasanabi", stream_category="just_chatting")
    assert any("kekw" in kw for kw in sentinel_irl._active_keywords)
    assert any("lul" in kw for kw in sentinel_irl._active_keywords)

    sentinel_casino = TwitchIrcChatSentinel("trainwreckstv", stream_category="casino")
    assert any("max win" in kw for kw in sentinel_casino._active_keywords)
    assert any("jackpot" in kw for kw in sentinel_casino._active_keywords)


def test_universal_watchdog_manager_lifecycle():
    """Tests starting, status checking, and stopping UniversalWatchdogManager."""
    mgr = UniversalWatchdogManager()

    # Start Twitch Watchdog
    res_tw = mgr.start_watchdog(
        channel_slug="tarik",
        platform="twitch",
        stream_category="gaming",
        min_amount=100.0,
        min_multiplier=50.0,
    )
    assert res_tw["status"] == "started"
    assert res_tw["platform"] == "twitch"
    assert res_tw["category"] == "gaming"

    status = mgr.get_status()
    assert status["is_active"] is True
    assert status["channel_slug"] == "tarik"
    assert status["platform"] == "twitch"

    # Stop Watchdog
    stop_res = mgr.stop_watchdog()
    assert stop_res["status"] == "stopped"
    assert mgr.is_active is False

    # Start Kick Watchdog
    res_kick = mgr.start_watchdog(
        channel_slug="xqc",
        platform="kick",
        stream_category="all",
    )
    assert res_kick["status"] == "started"
    assert res_kick["platform"] == "kick"
    mgr.stop_watchdog()


def test_multi_category_ai_copywriter():
    """Tests offline copywriting generation across gaming, just_chatting, casino, and general categories."""
    categories = ["gaming", "just_chatting", "casino", "general"]
    for cat in categories:
        res = generate_offline_shorts_copy(
            clip_title=f"Insane {cat} moment",
            category=cat,
            streamer="TopStreamer",
            promo_code="VIP99"
        )
        assert len(res["titles"]) == 5
        assert len(res["descriptions"]) == 3
        assert len(res["hashtags"]) >= 4
        assert res["engine"] == "offline_templates"


def test_fastapi_endpoints():
    """Tests FastAPI HTTP routes for Universal Studio."""
    # 1. Home page serves index.html with OmniStream & Twitch mentions
    res_home = client.get("/")
    assert res_home.status_code == 200
    html = res_home.text
    assert "OmniStream" in html
    assert "Twitch" in html
    assert "Gaming" in html
    assert "presetSelect" in html

    # 2. Crop presets endpoint
    res_presets = client.get("/api/crop-presets")
    assert res_presets.status_code == 200
    presets_data = res_presets.json()
    assert "gaming_fps" in presets_data
    assert "reaction_standard" in presets_data

    # 3. Watchdog endpoints
    res_start = client.post("/api/detector/start", json={
        "channel_slug": "tarik",
        "platform": "twitch",
        "category": "gaming"
    })
    assert res_start.status_code == 200
    assert res_start.json()["platform"] == "twitch"

    res_status = client.get("/api/detector/status")
    assert res_status.status_code == 200
    assert res_status.json()["platform"] == "twitch"

    res_stop = client.post("/api/detector/stop")
    assert res_stop.status_code == 200

    # 4. AI Metadata generation endpoint
    res_ai = client.post("/api/ai/generate-metadata", json={
        "clip_title": "1v5 Ace Clutch",
        "category": "gaming",
        "streamer": "Tarik",
        "provider": "offline"
    })
    assert res_ai.status_code == 200
    ai_data = res_ai.json()
    assert len(ai_data["titles"]) == 5
    assert len(ai_data["descriptions"]) == 3
    assert any("gaming" in tag.lower() or "clutch" in tag.lower() or "shorts" in tag.lower() for tag in ai_data["hashtags"])
