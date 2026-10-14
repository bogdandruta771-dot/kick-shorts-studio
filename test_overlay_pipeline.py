"""Comprehensive automated verification test suite for Cover & Promo Photo Overlays pipeline."""
import os
import sys
import time
from pathlib import Path
from PIL import Image

import pytest
from fastapi.testclient import TestClient

from app import app
from core.config import TEMP_DIR, OUTPUT_DIR
from core.banner_generator import generate_promo_banner, process_uploaded_overlay
from core.video_processor import VideoProcessor
from core.utils import run_command_safe, resolve_binary_paths
from core.video_ingest import validate_media_file

client = TestClient(app)


def create_synthetic_test_video(out_path: Path, duration_sec: int = 3) -> Path:
    """Generates a synthetic 1920x1080 test video with audio using FFmpeg."""
    ffmpeg_bin, _ = resolve_binary_paths()
    cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration_sec}:size=1920x1080:rate=30",
        "-f", "lavfi",
        "-i", f"sine=frequency=1000:duration={duration_sec}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "48000",
        "-ac", "2",
        str(out_path),
    ]
    res = run_command_safe(cmd, timeout=30)
    assert res.returncode == 0, f"FFmpeg synthetic generator failed: {res.stderr}"
    assert out_path.is_file(), "Test video was not created"
    return out_path


def test_banner_generator_standalone():
    """Verifies standalone banner generation using Pillow."""
    banner_out = TEMP_DIR / "test_promo_standalone.png"
    banner_path = generate_promo_banner(
        text="USE CODE: BOGDAN",
        sub_text="200% CASINO BONUS • VIP ACCESS",
        badge_text="SPECIAL OFFER",
        bg_color_hex="#0b0f19",
        text_color_hex="#ffd700",
        accent_color_hex="#00dcff",
        width=1080,
        height=140,
        output_path=banner_out,
    )
    assert banner_path.is_file()
    with Image.open(banner_path) as img:
        assert img.size == (1080, 140)
        assert img.mode == "RGBA"
    print("Standalone banner generator verified OK.")


def test_upload_overlay_endpoint():
    """Verifies uploading an image overlay via /api/upload-overlay."""
    # Create dummy PNG image
    test_img_path = TEMP_DIR / "dummy_logo.png"
    dummy = Image.new("RGBA", (400, 100), (255, 0, 128, 220))
    dummy.save(test_img_path, format="PNG")

    with open(test_img_path, "rb") as f:
        res = client.post(
            "/api/upload-overlay",
            files={"file": ("dummy_logo.png", f, "image/png")}
        )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "path" in data
    assert Path(data["path"]).is_file()
    assert data["width"] == 400
    assert data["height"] == 100
    print("Upload overlay endpoint verified OK.")


def test_generate_banner_endpoint():
    """Verifies generating a banner via /api/generate-banner API."""
    res = client.post(
        "/api/generate-banner",
        json={
            "text": "USE CODE: KICKWIN",
            "sub_text": "INSTANT $500 REWARD",
            "badge_text": "PROMO",
            "text_color": "#ffd700",
            "accent_color": "#00dcff",
            "bg_color": "#0f172a",
            "width": 1080,
            "height": 140
        }
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "path" in data
    assert Path(data["path"]).is_file()
    assert data["width"] == 1080
    assert data["height"] == 140
    print("Generate banner endpoint verified OK.")


def test_video_processor_with_overlays():
    """Verifies VideoProcessor renders 9:16 video with image overlay burned in."""
    fixtures_dir = Path("tests_fixtures")
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    src_video = fixtures_dir / "test_src_overlay.mp4"
    if not src_video.is_file():
        create_synthetic_test_video(src_video, duration_sec=3)

    # Generate an overlay image
    banner_img = fixtures_dir / "test_cover_banner.png"
    generate_promo_banner("USE CODE: LUCKY", "TOP CASINO BAR COVER", output_path=banner_img)

    out_video = fixtures_dir / "test_short_with_overlay.mp4"
    if out_video.is_file():
        out_video.unlink()

    processor = VideoProcessor()
    rendered = processor.process_short(
        input_video_path=src_video,
        output_video_path=out_video,
        gameplay_crop={"x": 260, "y": 80, "w": 1400, "h": 920},
        facecam_crop={"x": 1380, "y": 680, "w": 520, "h": 380},
        enable_subtitles=False,
        overlays=[{
            "image_path": str(banner_img),
            "x": 0,
            "y": 0,
            "w": 1080,
            "h": 140,
            "opacity": 1.0
        }],
        trim_start=0.0,
        trim_end=3.0,
    )

    assert rendered.is_file()
    meta = validate_media_file(rendered)
    assert meta["width"] == 1080
    assert meta["height"] == 1920
    assert meta["duration"] > 0
    print(f"Video processor with overlay verified OK: {meta['width']}x{meta['height']} ({meta['duration']:.1f}s)")


def test_export_api_flow_with_overlays():
    """Verifies end-to-end /api/start-export with custom overlays."""
    fixtures_dir = Path("tests_fixtures")
    src_video = fixtures_dir / "test_src_overlay.mp4"
    if not src_video.is_file():
        create_synthetic_test_video(src_video, duration_sec=3)

    banner_img = fixtures_dir / "test_cover_banner.png"
    if not banner_img.is_file():
        generate_promo_banner("USE CODE: WINNER", output_path=banner_img)

    export_payload = {
        "video_path": str(src_video),
        "crops": {
            "gx": 260, "gy": 80, "gw": 1400, "gh": 920,
            "cx": 1380, "cy": 680, "cw": 520, "ch": 380,
            "origW": 1920, "origH": 1080
        },
        "trim_start": 0.0,
        "trim_end": 3.0,
        "subtitles": {"enabled": False},
        "overlays": [{
            "image_path": str(banner_img),
            "x": 0,
            "y": 0,
            "w": 1080,
            "h": 140,
            "opacity": 1.0
        }]
    }

    res = client.post("/api/start-export", json=export_payload)
    assert res.status_code == 200, res.text
    job_id = res.json()["job_id"]

    # Poll status until done
    done = False
    for _ in range(30):
        time.sleep(0.5)
        st_res = client.get(f"/api/export-status/{job_id}")
        assert st_res.status_code == 200
        st = st_res.json()
        if st.get("done"):
            done = True
            assert st.get("error") is None, f"Export failed with error: {st.get('error')}"
            assert "output_path" in st
            assert Path(st["output_path"]).is_file()
            break

    assert done, "Export job did not complete within timeout"
    print("End-to-end export flow with overlays verified OK!")


if __name__ == "__main__":
    test_banner_generator_standalone()
    test_upload_overlay_endpoint()
    test_generate_banner_endpoint()
    test_video_processor_with_overlays()
    test_export_api_flow_with_overlays()
    print("\nALL 5 OVERLAY VERIFICATION TESTS PASSED SUCCESSFULLY!")
