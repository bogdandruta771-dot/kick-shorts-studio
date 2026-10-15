"""Self-test verification suite for Dynamic Hardware Encoding and Anti-Shadowban Protections."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

# Set stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from core.video_processor import VideoProcessor, detect_optimal_video_encoder
from core.subtitles import sanitize_subtitle_text
from core.ai_copywriter import generate_safe_metadata
from core.utils import resolve_binary_paths, run_command_safe


def test_encoder_detection():
    print("=== TEST 1: Dynamic Hardware Encoder Auto-Detection ===")
    ffmpeg_bin, _ = resolve_binary_paths()
    encoder = detect_optimal_video_encoder(ffmpeg_bin)
    print(f"Detected Encoder: {encoder['name']} ({encoder['type']})")
    print(f"GPU Accelerated: {encoder['is_gpu']}")
    print(f"Encoding Flags: {' '.join(encoder['args'])}")

    assert encoder["name"] in ("h264_amf", "h264_nvenc", "h264_qsv", "libx264"), f"Unexpected encoder: {encoder['name']}"
    assert "-pix_fmt" in encoder["args"] and "yuv420p" in encoder["args"], "pix_fmt yuv420p must be forced"
    print("PASS: Encoder detection verified successfully.\n")
    return encoder


def test_subtitle_sanitizer():
    print("=== TEST 2: NLP Subtitle Sanitizer ===")
    samples = [
        ("I BET 500 ON STAKE CASINO", "I ENTRY 500 ON THE PLATFORM SESSION"),
        ("Huge gambling deposit on 1win", "Huge gaming reload on the platform"),
        ("Wager on Roobet", "Round on The Platform"),
        ("best crypto casino games and bets", "best crypto session games and entries"),
    ]
    for raw, expected in samples:
        result = sanitize_subtitle_text(raw)
        print(f"  Raw:      '{raw}'")
        print(f"  Sanitized:'{result}'")
        assert "casino" not in result.lower(), f"Failed to sanitize 'casino' in: {result}"
        assert "stake" not in result.lower(), f"Failed to sanitize 'stake' in: {result}"
        assert "1win" not in result.lower(), f"Failed to sanitize '1win' in: {result}"
        assert "roobet" not in result.lower(), f"Failed to sanitize 'roobet' in: {result}"
        assert "deposit" not in result.lower(), f"Failed to sanitize 'deposit' in: {result}"
    print("PASS: NLP subtitle sanitizer passed all test cases.\n")


def test_safe_metadata_generator():
    print("=== TEST 3: Metadata & Title Spinner ===")
    m1 = generate_safe_metadata("Roshtein", "$25,000")
    m2 = generate_safe_metadata("Trainwreckstv", "500X")
    m3 = generate_safe_metadata("XQC", "1000")

    print(f"  Title 1: {m1['title']}")
    print(f"  Title 2: {m2['title']}")
    print(f"  Title 3: {m3['title']}")
    print(f"  Hashtags: {m1['hashtags']}")

    assert len(m1["titles"]) == 3, "Must provide 3 dynamic formulas"
    assert m1["hashtags"] == ["#gaming", "#streamerhighlights", "#epicmoments"], f"Invalid hashtags: {m1['hashtags']}"
    blacklisted = ["#casino", "#deposit", "#gambling", "#bet", "#wager", "#slots"]
    for tag in m1["hashtags"]:
        assert tag.lower() not in blacklisted, f"Blacklisted tag found: {tag}"
    print("PASS: Safe metadata generator passed all assertions.\n")


def test_video_render_and_hash_disruption():
    print("=== TEST 4: Video Processing & Hash Disruptor Integrity ===")
    ffmpeg_bin, ffprobe_bin = resolve_binary_paths()
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)

    raw_input_path = temp_dir / "_test_synth_input.mp4"
    out_1 = temp_dir / "_test_export_1.mp4"
    out_2 = temp_dir / "_test_export_2.mp4"

    try:
        # 1. Create a 1.2 second synthetic source video with 1080x1920 resolution & audio
        create_cmd = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=30:duration=1.2",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1.2",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            str(raw_input_path),
        ]
        run_res = run_command_safe(create_cmd, timeout=30)
        assert run_res.returncode == 0 and raw_input_path.is_file(), "Failed to create synthetic test input"

        processor = VideoProcessor()
        crop_gp = {"x": 200, "y": 50, "w": 1400, "h": 900}
        crop_fc = {"x": 1300, "y": 650, "w": 500, "h": 380}

        print("  Rendering Short 1 (with Anti-Shadowban & GPU auto-detect)...")
        processor.process_short(
            input_video_path=raw_input_path,
            output_video_path=out_1,
            gameplay_crop=crop_gp,
            facecam_crop=crop_fc,
            enable_subtitles=False,
            enable_anti_shadowban=True,
        )

        print("  Rendering Short 2 (with Anti-Shadowban & GPU auto-detect)...")
        processor.process_short(
            input_video_path=raw_input_path,
            output_video_path=out_2,
            gameplay_crop=crop_gp,
            facecam_crop=crop_fc,
            enable_subtitles=False,
            enable_anti_shadowban=True,
        )

        assert out_1.is_file() and out_1.stat().st_size > 0, "Export 1 file not created"
        assert out_2.is_file() and out_2.stat().st_size > 0, "Export 2 file not created"

        # Verify geometry via ffprobe
        probe_cmd = [
            ffprobe_bin,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,pix_fmt",
            "-of", "json",
            str(out_1),
        ]
        probe_res = run_command_safe(probe_cmd, timeout=10)
        assert probe_res.returncode == 0, "ffprobe probe failed"
        probe_data = json.loads(probe_res.stdout)
        stream_info = probe_data["streams"][0]
        width = int(stream_info["width"])
        height = int(stream_info["height"])
        pix_fmt = stream_info["pix_fmt"]

        print(f"  Export Resolution: {width}x{height}")
        print(f"  Pixel Format: {pix_fmt}")
        assert width == 1080 and height == 1920, f"Incorrect dimensions: {width}x{height} (expected 1080x1920)"
        assert pix_fmt == "yuv420p", f"Incorrect pixel format: {pix_fmt} (expected yuv420p)"

        # Verify Unique Hash Generation
        hash1 = hashlib.sha256(out_1.read_bytes()).hexdigest()
        hash2 = hashlib.sha256(out_2.read_bytes()).hexdigest()

        print(f"  Short 1 SHA256: {hash1}")
        print(f"  Short 2 SHA256: {hash2}")

        assert hash1 != hash2, "Anti-shadowban disruption failure: consecutive exports must have unique hashes!"
        print("PASS: Consecutive renders produced distinct digital hashes with exact 1080x1920 yuv420p geometry.\n")

    finally:
        # Cleanup test artifacts
        for p in (raw_input_path, out_1, out_2):
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass


def main():
    print("================================================================================")
    print("KICK SHORTS STUDIO - HARDWARE ENCODING & ANTI-SHADOWBAN VERIFICATION TEST")
    print("================================================================================\n")
    test_encoder_detection()
    test_subtitle_sanitizer()
    test_safe_metadata_generator()
    test_video_render_and_hash_disruption()
    print("================================================================================")
    print("ALL VERIFICATION SUITES PASSED (100% SUCCESS)")
    print("================================================================================")


if __name__ == "__main__":
    main()
