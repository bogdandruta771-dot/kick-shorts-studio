"""Synthetic End-to-End Pipeline & Non-VLM Detector Verification Suite.
Validates:
1. Regex win extraction ($ amount >= $100 and multiplier >= 50x)
2. Sentinel A clip burst detection logic (2+ in 60s)
3. Sentinel B Pusher chat velocity spike logic (> 300% rolling spike)
4. Synthetic media generation (16:9 source + vertical outro with FFmpeg)
5. 9:16 Shorts layout stacking (Top Gameplay + Bottom Cam over blurred background)
6. SubtitleEngine faster-whisper & karaoke ASS script generation
7. Seamless outro video concatenation
8. FFprobe container integrity, strict 1080x1920 geometry, and audio sync
"""
import sys
import time
from pathlib import Path

from core.config import (
    BASE_DIR,
    TARGET_WIDTH,
    TARGET_HEIGHT,
    DEFAULT_FPS,
)
from core.utils import (
    resolve_binary_paths,
    run_command_safe,
    TempFileManager,
)
from core.video_ingest import validate_media_file
from core.video_processor import VideoProcessor
from core.detector import (
    WinExtractor,
    KickClipPulseSentinel,
    KickPusherChatSentinel,
)
from core.audio_detector import analyze_audio_climax


def run_regex_and_trigger_tests():
    print("=" * 65)
    print("  STAGE 1: REGEX WIN EXTRACTOR & SENTINEL TRIGGER VERIFICATION")
    print("=" * 65)

    test_cases = [
        ("WON $450 ON GATES", 450.0, None, True),
        ("120x huge bonus", None, 120.0, True),
        ("BIGGEST WIN $1,250.50", 1250.50, None, True),
        ("Won $15", 15.0, None, False),
        ("10x small hit", None, 10.0, False),
        ("5000X MAX WIN", None, 5000.0, True),
        ("CASINO $99.99 WIN", 99.99, None, False),
        ("JUST CHATTING WITH VIEWERS", None, None, False),
        ("Toon Sailor - 1,030x", None, 1030.0, True),
        ("Marcel's Lab - 2,170x", None, 2170.0, True),
        ("19k", 19000.0, None, True),
        ("50k win", 50000.0, None, True),
        ("9 mill zombies", 9000000.0, None, True),
        ("MAX WIN ON SUGAR RUSH", None, 5000.0, True),
        ("10,000x jackpot", None, 10000.0, True),
    ]

    print("[1/3] Testing Regex Win Extractor on test strings...")
    for title, expected_amt, expected_mult, expected_big in test_cases:
        res = WinExtractor.extract_win_info(title, min_amount=100.0, min_multiplier=50.0)
        if expected_amt is None and expected_mult is None:
            assert res is None or res["is_big_win"] is False, f"False positive on '{title}'"
            print(f"      [OK] Ignored non-win: '{title}'")
        else:
            assert res is not None, f"Failed to parse win in '{title}'"
            if expected_amt is not None:
                assert abs(res["amount"] - expected_amt) < 0.01, f"Amount error for '{title}' (got {res.get('amount')}, exp {expected_amt})"
            if expected_mult is not None:
                assert abs(res["multiplier"] - expected_mult) < 0.01, f"Multiplier error for '{title}' (got {res.get('multiplier')}, exp {expected_mult})"
            assert res["is_big_win"] == expected_big, f"Big win mismatch for '{title}' (expected {expected_big})"
            status_txt = "BIG WIN" if expected_big else "SUB-THRESHOLD WIN"
            match_txt = f"${res['amount']}" if res['amount'] else f"{res['multiplier']}x"
            print(f"      [OK] Parsed {status_txt} ({match_txt}): '{title}'")

    # Sentinel A: Clip Burst Detection Test
    print("[2/3] Testing Sentinel A Clip Burst detection logic (2+ clips in 60s)...")
    sentinel_a = KickClipPulseSentinel("dummy_channel")
    now_ts = time.time()
    clips_normal = [
        {"id": 1, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ts - 500))},
        {"id": 2, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ts - 200))},
    ]
    assert not sentinel_a.check_clip_burst(clips_normal), "False positive burst detected"

    clips_burst = [
        {"id": 3, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ts - 30))},
        {"id": 4, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ts - 10))},
    ]
    burst_flagged = sentinel_a.check_clip_burst(clips_burst)
    assert burst_flagged, "Failed to detect clip burst with 2 clips in 60s"
    print("      [OK] Clip Burst trigger correctly detected 2 clips within 60s window!")

    # Sentinel B: Chat Velocity Spike Test
    print("[3/3] Testing Sentinel B Pusher Chat Velocity Spike (>300% surge)...")
    spike_detected = []
    def _on_spike(vel, base):
        spike_detected.append((vel, base))

    sentinel_b = KickPusherChatSentinel("dummy_channel", on_velocity_spike=_on_spike)
    sentinel_b._baseline_velocity = 0.5  # 0.5 msg/s baseline

    # Simulate rapid incoming messages
    t = time.time()
    for i in range(10):
        sentinel_b._check_spike("BIG WIN OMG LETS GO")
    
    assert len(spike_detected) > 0, "Chat velocity spike failed to trigger on surge"
    print(f"      [OK] Chat velocity spike triggered! (Velocity: {spike_detected[0][0]} msg/s vs Base: {spike_detected[0][1]} msg/s)")

    # Audio Energy Climax Peak Detector Test
    print("[4/4] Testing Audio Excitement Climax Peak Detector...")
    ffmpeg_bin, _ = resolve_binary_paths()
    import tempfile
    test_audio_vid = Path(tempfile.gettempdir()) / "test_climax_synth.mp4"
    cmd_audio = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10:duration=8",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=8",
        "-af", "volume=enable='between(t,4,6)':volume=10,volume=enable='not(between(t,4,6))':volume=0.05",
        "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
        str(test_audio_vid)
    ]
    run_command_safe(cmd_audio, timeout=15)
    climax_res = analyze_audio_climax(test_audio_vid, target_clip_duration=6.0, pre_roll_sec=2.0)
    test_audio_vid.unlink(missing_ok=True)
    assert 3.5 <= climax_res["climax_timestamp"] <= 6.5, f"Climax time mismatch: {climax_res['climax_timestamp']}"
    assert climax_res["confidence"] > 0.6, f"Confidence too low: {climax_res['confidence']}"
    print(f"      [OK] Audio climax detected at {climax_res['climax_timestamp']}s (Confidence: {climax_res['confidence']})")
    print("=" * 65)
    print("  STAGE 1 COMPLETED: ALL REGEX, CLIMAX & TRIGGER TESTS PASSED (100% SUCCESS)")
    print("=" * 65)
    print()


def generate_synthetic_assets(temp_mgr: TempFileManager) -> tuple[Path, Path]:
    """Generates synthetic 16:9 source video and vertical outro clip using pure FFmpeg."""
    ffmpeg_bin, _ = resolve_binary_paths()

    source_path = temp_mgr.get_path("synthetic_source.mp4")
    outro_path = temp_mgr.get_path("synthetic_outro.mp4")

    # Generate 5-second 16:9 source video with PIP facecam box and 440Hz audio
    source_cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=30:duration=5",
        "-f", "lavfi", "-i", "smptebars=size=400x300:rate=30:duration=5",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
        "-filter_complex", "[0:v][1:v]overlay=1450:720[v]",
        "-map", "[v]",
        "-map", "2:a",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-ar", "48000",
        "-ac", "2",
        str(source_path),
    ]

    res = run_command_safe(source_cmd, timeout=60)
    if res.returncode != 0 or not source_path.is_file():
        raise RuntimeError(f"Failed to generate synthetic source video: {res.stderr.strip()}")

    # Generate 2-second vertical outro video (1080x1920) with 880Hz audio
    outro_cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi", "-i", "color=c=navy:size=1080x1920:rate=30:duration=2",
        "-f", "lavfi", "-i", "sine=frequency=880:duration=2",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-ar", "48000",
        "-ac", "2",
        str(outro_path),
    ]

    res_outro = run_command_safe(outro_cmd, timeout=60)
    if res_outro.returncode != 0 or not outro_path.is_file():
        raise RuntimeError(f"Failed to generate synthetic outro video: {res_outro.stderr.strip()}")

    return source_path, outro_path


def run_synthetic_video_pipeline_test():
    print("=" * 65)
    print("  STAGE 2: SYNTHETIC 9:16 SHORTS VIDEO PIPELINE VERIFICATION")
    print("=" * 65)

    with TempFileManager("test_suite") as temp_mgr:
        print("[1/5] Generating synthetic test media (pure FFmpeg filters)...")
        source_path, outro_path = generate_synthetic_assets(temp_mgr)

        source_meta = validate_media_file(source_path)
        print(f"      Source created: {source_meta['width']}x{source_meta['height']} @ {source_meta['fps']}fps, duration={source_meta['duration']:.2f}s")

        outro_meta = validate_media_file(outro_path)
        print(f"      Outro created:  {outro_meta['width']}x{outro_meta['height']} @ {outro_meta['fps']}fps, duration={outro_meta['duration']:.2f}s")

        print("[2/5] Initializing VideoProcessor engine...")
        processor = VideoProcessor()
        output_short = temp_mgr.get_path("synthetic_output_short.mp4")

        # Crop parameters
        gameplay_crop = {"x": 100, "y": 50, "w": 1300, "h": 800}
        facecam_crop = {"x": 1450, "y": 720, "w": 400, "h": 300}

        def _progress(fraction: float, msg: str):
            print(f"      -> [{int(fraction * 100)}%] {msg}")

        print("[3/5] Processing through complete pipeline...")
        processor.process_short(
            input_video_path=source_path,
            output_video_path=output_short,
            gameplay_crop=gameplay_crop,
            facecam_crop=facecam_crop,
            enable_subtitles=True,
            subtitle_options={
                "font_name": "Arial",
                "font_size": 48,
                "primary_color": "#FFFFFF",
                "highlight_color": "#FFD700",
                "y_position": 980,
            },
            outro_video_path=outro_path,
            progress_cb=_progress,
        )

        print("[4/5] Validating output artifact with ffprobe...")
        out_meta = validate_media_file(output_short)
        print(f"      Output Resolution: {out_meta['width']}x{out_meta['height']}")
        print(f"      Output FPS:        {out_meta['fps']}")
        print(f"      Output Duration:   {out_meta['duration']:.2f}s")
        print(f"      Audio Streams:     {out_meta['audio_codec']} ({out_meta['audio_channels']}ch @ {out_meta['audio_sample_rate']}Hz)")

        # Assertions
        assert out_meta["width"] == TARGET_WIDTH, f"Expected width {TARGET_WIDTH}, got {out_meta['width']}"
        assert out_meta["height"] == TARGET_HEIGHT, f"Expected height {TARGET_HEIGHT}, got {out_meta['height']}"
        assert out_meta["has_audio"], "Output short is missing audio stream!"
        assert abs(out_meta["fps"] - DEFAULT_FPS) <= 1.0, f"Expected FPS ~{DEFAULT_FPS}, got {out_meta['fps']}"

        # Total expected duration: ~5s source + ~2s outro = ~7s
        expected_dur = source_meta["duration"] + outro_meta["duration"]
        dur_diff = abs(out_meta["duration"] - expected_dur)
        assert dur_diff <= 0.5, f"Expected duration ~{expected_dur:.2f}s, got {out_meta['duration']:.2f}s"

        print("[5/5] Validating explicit ASS subtitle generation & burn-in filter...")
        sub_ass = temp_mgr.get_path("test_burned.ass")
        words_sample = [
            {"word": "MASSIVE", "start": 0.5, "end": 1.1},
            {"word": "CASINO", "start": 1.1, "end": 1.7},
            {"word": "WIN", "start": 1.7, "end": 2.3},
        ]
        processor.subtitle_engine.generate_ass_script(
            words=words_sample,
            output_ass_path=sub_ass,
            font_name="Arial",
            font_size=52,
            primary_color_hex="#FFFFFF",
            highlight_color_hex="#FFD700",
            y_position=980,
        )
        assert sub_ass.is_file(), "ASS subtitle file was not generated!"
        ass_content = sub_ass.read_text(encoding="utf-8")
        assert "MASSIVE" in ass_content, "ASS file missing expected word tokens!"
        assert r"\pos(540,980)" in ass_content, "ASS file missing position tags!"

        sub_burned_short = temp_mgr.get_path("synthetic_burned_short.mp4")
        ffmpeg_bin, _ = resolve_binary_paths()
        from core.utils import escape_ffmpeg_filter_path
        esc_ass = escape_ffmpeg_filter_path(str(sub_ass))
        burn_cmd = [
            ffmpeg_bin, "-y",
            "-i", str(output_short),
            "-vf", f"subtitles='{esc_ass}'",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "copy",
            str(sub_burned_short)
        ]
        res_burn = run_command_safe(burn_cmd, timeout=60)
        assert res_burn.returncode == 0, f"Subtitle burning failed: {res_burn.stderr.strip()}"
        burned_meta = validate_media_file(sub_burned_short)
        assert burned_meta["width"] == TARGET_WIDTH and burned_meta["height"] == TARGET_HEIGHT
        print("      ASS Subtitles burned successfully with zero errors!")

        print("=" * 65)
        print("  STAGE 2 COMPLETED: ALL VIDEO PIPELINE CHECKS PASSED (100% SUCCESS)")
        print("=" * 65)


if __name__ == "__main__":
    try:
        run_regex_and_trigger_tests()
        run_synthetic_video_pipeline_test()
        print("\n" + "=" * 65)
        print("  ALL SYSTEM SUITE VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 65)
        sys.exit(0)
    except Exception as exc:
        print(f"\n[FATAL ERROR IN PIPELINE TEST]: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
