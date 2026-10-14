"""Automated End-to-End Test for the Minimalist Multi-Step Studio UI & Detector API."""
import time
import requests
from pathlib import Path

BASE_URL = "http://127.0.0.1:7860"

def run_e2e_api_test():
    print("=" * 65)
    print("  TESTING MULTI-STEP STUDIO UI & DUAL-SENTINEL DETECTOR API")
    print("=" * 65)

    # 1. Test Home page
    print("[1/6] Testing GET / (Studio HTML UI & Stepper Wizard)...")
    res_home = requests.get(f"{BASE_URL}/")
    assert res_home.status_code == 200, f"Expected 200, got {res_home.status_code}"
    assert "KickStudio" in res_home.text, "Page missing KickStudio branding"
    assert "canvas-9-16" in res_home.text, "Page missing 9:16 canvas"
    assert "stage-step-1" in res_home.text, "Page missing Step 1"
    assert "stage-step-2" in res_home.text, "Page missing Step 2"
    assert "stage-step-3" in res_home.text, "Page missing Step 3"
    assert "stage-step-4" in res_home.text, "Page missing Step 4"
    assert "panel-ingest-watchdog" in res_home.text, "Page missing Sentinel Watchdog Panel"
    assert "watchdog-wins-feed" in res_home.text, "Page missing Detected Wins Feed"
    assert "btn-start-watchdog" in res_home.text, "Page missing Start Watchdog button"
    print("      [OK] UI HTML with 4-step wizard & Sentinel Watchdog verified successfully!")

    # 2. Test Sentinel Watchdog API Endpoints
    print("[2/6] Testing Sentinel Watchdog API (start / status / stop)...")
    # Start watchdog
    res_start = requests.post(f"{BASE_URL}/api/detector/start", json={
        "channel_slug": "xqc",
        "min_amount": 100.0,
        "min_multiplier": 50.0,
        "poll_interval": 10.0
    })
    assert res_start.status_code == 200, f"Failed start watchdog: {res_start.text}"
    print(f"      [OK] Watchdog started: {res_start.json()}")

    # Check status
    time.sleep(1.0)
    res_status = requests.get(f"{BASE_URL}/api/detector/status")
    assert res_status.status_code == 200, f"Failed status check: {res_status.text}"
    status_data = res_status.json()
    assert status_data["is_active"] is True, "Watchdog should be active"
    assert status_data["channel_slug"] == "xqc", "Channel slug mismatch"
    print(f"      [OK] Watchdog status active: channel={status_data['channel_slug']}, WS connected={status_data['ws_connected']}, velocity={status_data['chat_velocity']} msg/s")

    # Stop watchdog
    res_stop = requests.post(f"{BASE_URL}/api/detector/stop")
    assert res_stop.status_code == 200, f"Failed stop watchdog: {res_stop.text}"
    print("      [OK] Watchdog stopped gracefully.")

    # 3. Test Ingestion via File Upload
    print("[3/8] Testing POST /api/ingest-file (Step 1 Ingestion)...")
    fixture_dir = Path("tests_fixtures")
    fixture_dir.mkdir(parents=True, exist_ok=True)
    test_video = fixture_dir / "quick_test_clip.mp4"
    if not test_video.is_file():
        from core.utils import resolve_binary_paths, run_command_safe
        ff_bin, _ = resolve_binary_paths()
        cmd = [
            ff_bin, "-y",
            "-f", "lavfi", "-i", "testsrc=duration=5:size=1920x1080:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=5",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac", str(test_video)
        ]
        run_command_safe(cmd, timeout=30)

    with open(test_video, "rb") as f:
        res_ingest = requests.post(f"{BASE_URL}/api/ingest-file", files={"file": ("quick_test.mp4", f, "video/mp4")})

    assert res_ingest.status_code == 200, f"Ingest failed: {res_ingest.text}"
    meta = res_ingest.json()
    assert "path" in meta, "Missing video path in response"
    assert "preview_base64" in meta, "Missing snapshot in response"
    assert meta["width"] > 0 and meta["height"] > 0, "Invalid dimensions"
    print(f"      [OK] Ingested {meta['filename']}: {meta['width']}x{meta['height']}, duration={meta['duration']:.1f}s, fps={meta['fps']}")

    # 4. Test Extract Frame at scrubbing timestamp (Step 1 Snap Frame)
    print("[4/8] Testing POST /api/extract-frame-at (Scrub Frame Snap)...")
    res_snap = requests.post(f"{BASE_URL}/api/extract-frame-at", json={
        "video_path": meta["path"],
        "timestamp": 2.5
    })
    assert res_snap.status_code == 200, f"Frame snap failed: {res_snap.text}"
    snap_data = res_snap.json()
    assert "preview_base64" in snap_data, "Missing preview_base64 in snap response"
    assert snap_data["preview_base64"].startswith("data:image/jpeg;base64,"), "Invalid base64 JPEG format"
    print("      [OK] Extracted scrub frame snapshot at 2.5s successfully!")

    # 5. Test Export Job with Cut Trimming (Step 4 Render with trim 1.0s to 3.5s)
    print("[5/8] Testing POST /api/start-export with Trim Cut (1.0s to 3.5s)...")
    payload = {
        "video_path": meta["path"],
        "trim_start": 1.0,
        "trim_end": 3.5,
        "crops": {
            "gx": 260, "gy": 80, "gw": 1400, "gh": 920,
            "cx": 1380, "cy": 680, "cw": 520, "ch": 380,
            "origW": meta["width"], "origH": meta["height"]
        },
        "subtitles": {
            "enabled": True,
            "font_name": "Arial",
            "font_size": 48,
            "primary_color": "#FFFFFF",
            "highlight_color": "#FFD700",
            "y_position": 1000
        },
        "outro_path": None
    }

    res_export = requests.post(f"{BASE_URL}/api/start-export", json=payload)
    assert res_export.status_code == 200, f"Start export failed: {res_export.text}"
    job_id = res_export.json()["job_id"]
    print(f"      [OK] Export job started with trim: job_id={job_id}")

    # 6. Monitor Job Progress via Polling
    print("[6/8] Monitoring job progress via /api/export-status...")
    max_wait = 180
    start_t = time.time()
    last_pct = 0
    final_status = None

    while time.time() - start_t < max_wait:
        res_job_status = requests.get(f"{BASE_URL}/api/export-status/{job_id}")
        assert res_job_status.status_code == 200, f"Failed status check: {res_job_status.text}"
        status = res_job_status.json()

        pct = int(status.get("percent", 0) * 100)
        if pct != last_pct:
            print(f"      -> [{pct}%] {status.get('message')}")
            last_pct = pct

        if status.get("done"):
            final_status = status
            break
        time.sleep(1.0)

    assert final_status is not None, "Job timed out"
    assert final_status.get("error") is None, f"Job encountered error: {final_status.get('error')}"
    assert final_status.get("output_url"), "Missing output_url"
    out_file = Path(final_status["output_path"])
    assert out_file.is_file(), f"Rendered file not found on disk: {out_file}"

    # Verify trimmed output duration is ~2.5s (3.5 - 1.0)
    from core.video_ingest import validate_media_file
    meta_out = validate_media_file(out_file)
    assert meta_out["width"] == 1080 and meta_out["height"] == 1920, f"Resolution mismatch: {meta_out['width']}x{meta_out['height']}"
    assert 2.0 <= meta_out["duration"] <= 3.0, f"Expected ~2.5s trimmed duration, got {meta_out['duration']:.2f}s"
    print(f"      [OK] Trimmed 9:16 short rendered: {final_status['output_filename']} ({meta_out['duration']:.2f}s, 1080x1920)")

    # 7. Test Video Playback Endpoint
    print("[7/8] Testing GET /outputs/{filename} (Playback Endpoint)...")
    res_video = requests.get(f"{BASE_URL}{final_status['output_url']}", headers={"Range": "bytes=0-1024"})
    assert res_video.status_code in [200, 206], f"Failed video stream: {res_video.status_code}"
    assert "video/mp4" in res_video.headers.get("Content-Type", ""), "Invalid Content-Type"
    print("      [OK] Output video stream validated!")

    # 8. Test 'Process Next Clip' Reset Flow & Clean Ingest of Clip #2
    print("[8/8] Testing 'Process Next Clip' flow (reset session & process clip #2)...")
    res_reset = requests.post(f"{BASE_URL}/api/reset-session")
    assert res_reset.status_code == 200, f"Reset session failed: {res_reset.text}"
    
    # Active session must now report has_clip == False
    res_sess = requests.get(f"{BASE_URL}/api/active-session")
    assert res_sess.status_code == 200
    assert res_sess.json().get("has_clip") is False, "Active session should be empty after reset"
    print("      [OK] Session cleared cleanly! No stale clips resurrected.")

    # Re-ingest fresh clip for Clip #2
    with open(test_video, "rb") as f:
        res_ingest2 = requests.post(f"{BASE_URL}/api/ingest-file", files={"file": ("second_clip.mp4", f, "video/mp4")})
    assert res_ingest2.status_code == 200, f"Second ingest failed: {res_ingest2.text}"
    meta2 = res_ingest2.json()
    assert meta2["filename"] == "second_clip.mp4", "Second clip filename mismatch"
    print(f"      [OK] Second clip ingested cleanly: {meta2['filename']}")

    # Quick test outro removal endpoint
    res_rem_outro = requests.post(f"{BASE_URL}/api/remove-outro")
    assert res_rem_outro.status_code == 200, f"Remove outro failed: {res_rem_outro.text}"
    print("      [OK] Outro lifecycle endpoint verified!")

    print("=" * 65)
    print("  ALL MULTI-STEP STUDIO UI & DETECTOR TESTS PASSED (100% SUCCESS)!")
    print("=" * 65)

if __name__ == "__main__":
    run_e2e_api_test()
