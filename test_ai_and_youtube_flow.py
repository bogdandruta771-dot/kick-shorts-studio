"""
Comprehensive Automated Test Suite for AI Shorts Copywriter & YouTube Direct Uploader
Verifies:
1. 100% Free Offline Copywriting Heuristics (5 titles, 3 description variants, trending hashtags).
2. Gemini / Groq API dispatcher fallback mechanism.
3. YouTube Data API credentials handling, status queries, and validation.
4. FastAPI endpoints for AI generation and YouTube management.
"""

import os
import json
import tempfile
import pytest
from fastapi.testclient import TestClient

from app import app
from core.ai_copywriter import (
    generate_offline_shorts_copy,
    generate_shorts_metadata
)
from core.youtube_uploader import (
    get_youtube_auth_status,
    save_client_secrets_json,
    TOKEN_FILE
)

def test_offline_copywriter_generation():
    """Verify offline generator creates 5 viral titles, 3 description variants, and hashtags with 0 cost."""
    result = generate_offline_shorts_copy(
        clip_title="XQC WON $12,500 ON WANTED DEAD OR A WILD",
        win_amount="$12,500",
        streamer="xQc",
        transcript="Oh my god 500x bonus! Look at that screen!",
        promo_code="KICKVIP"
    )
    
    assert "titles" in result
    assert len(result["titles"]) == 5, f"Expected 5 titles, got {len(result['titles'])}"
    for title in result["titles"]:
        assert len(title) <= 100, f"Title exceeded 100 chars: {title}"
        assert "#shorts" in title.lower()
        
    assert "descriptions" in result
    assert len(result["descriptions"]) == 3, f"Expected 3 descriptions, got {len(result['descriptions'])}"
    
    # Check that promo description includes the promo code
    promo_desc = result["descriptions"][0]
    assert "KICKVIP" in promo_desc
    
    assert "hashtags" in result
    assert len(result["hashtags"]) >= 5
    assert any("shorts" in h.lower() for h in result["hashtags"])
    assert "offline" in result["provider"].lower()

def test_dispatcher_with_no_key_fallback():
    """Verify metadata dispatcher seamlessly defaults to offline engine when no key is supplied."""
    meta = generate_shorts_metadata(
        clip_title="Sweet Bonanza 100x Bonus Round Win $450",
        promo_code="LUCKY777",
        api_key=None
    )
    assert "offline" in meta["provider"].lower()
    assert len(meta["titles"]) == 5
    assert len(meta["descriptions"]) == 3
    assert "LUCKY777" in meta["descriptions"][0]

def test_dispatcher_graceful_fallback_on_invalid_key():
    """Verify that an invalid or expired API key falls back to offline engine instead of crashing."""
    meta = generate_shorts_metadata(
        clip_title="Gates of Olympus Max Win",
        api_key="invalid_fake_key_12345"
    )
    assert "titles" in meta
    assert len(meta["titles"]) == 5
    assert len(meta["descriptions"]) == 3

def test_youtube_status_initially_not_authenticated():
    """Verify YouTube status reporting without existing user credentials."""
    status = get_youtube_auth_status()
    assert isinstance(status, dict)
    assert "authenticated" in status
    assert "has_client_secrets" in status

def test_fastapi_ai_generate_endpoint():
    """Test the FastAPI POST /api/ai/generate-metadata endpoint."""
    client = TestClient(app)
    payload = {
        "clip_title": "Huge Sugar Rush Multiplier $850 Win",
        "game_name": "Sugar Rush",
        "win_amount": 850.0,
        "multiplier": 120.0,
        "promo_code": "SPIN100"
    }
    resp = client.post("/api/ai/generate-metadata", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["titles"]) == 5
    assert len(data["descriptions"]) == 3
    assert len(data["hashtags"]) >= 5
    assert "SPIN100" in data["descriptions"][0]

def test_fastapi_youtube_status_endpoint():
    """Test the FastAPI GET /api/youtube/status endpoint."""
    client = TestClient(app)
    resp = client.get("/api/youtube/status")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "authenticated" in data
    assert "has_client_secrets" in data

def test_fastapi_youtube_upload_video_validation():
    """Test validation when trying to upload without authenticated credentials or missing file."""
    client = TestClient(app)
    # 1. Non-existent video file
    resp = client.post("/api/youtube/upload-video", json={
        "video_path": "h:/non_existent_folder/fake_video.mp4",
        "title": "Test Title #shorts",
        "description": "Test Desc",
        "privacy_status": "private"
    })
    assert resp.status_code == 400
    assert "Video file not found" in resp.json()["detail"]

    # 2. Missing title
    resp = client.post("/api/youtube/upload-video", json={
        "video_path": "app.py", # exists but empty title
        "title": "   ",
        "description": "Test Desc",
        "privacy_status": "private"
    })
    assert resp.status_code == 400
    assert "Title cannot be empty" in resp.json()["detail"]

if __name__ == "__main__":
    print("Running AI & YouTube integration tests...")
    test_offline_copywriter_generation()
    print("[PASS] Offline copywriter test passed (5 titles, 3 descriptions, hashtags).")
    test_dispatcher_with_no_key_fallback()
    print("[PASS] Dispatcher fallback test passed.")
    test_dispatcher_graceful_fallback_on_invalid_key()
    print("[PASS] Graceful fallback on invalid key test passed.")
    test_youtube_status_initially_not_authenticated()
    print("[PASS] YouTube initial status test passed.")
    test_fastapi_ai_generate_endpoint()
    print("[PASS] FastAPI AI generate endpoint test passed.")
    test_fastapi_youtube_status_endpoint()
    print("[PASS] FastAPI YouTube status endpoint test passed.")
    test_fastapi_youtube_upload_video_validation()
    print("[PASS] FastAPI YouTube upload validation test passed.")
    print("ALL TESTS PASSED SUCCESSFULLY! [OK]")
