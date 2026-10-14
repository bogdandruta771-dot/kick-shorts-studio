"""Media ingestion via yt-dlp and container integrity validation via ffprobe."""
import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from core.config import DOWNLOAD_TIMEOUT, DEFAULT_TIMEOUT
from core.utils import (
    resolve_binary_paths,
    run_command_safe,
    retry_with_backoff,
)


def validate_media_file(file_path: Path) -> Dict[str, Any]:
    """
    Validates container integrity, streams, resolution, fps, and audio channels using ffprobe.
    Raises ValueError or FileNotFoundError if invalid.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"Media file does not exist: {file_path}")

    _, ffprobe_bin = resolve_binary_paths()

    probe_cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "format=duration,size,bit_rate",
        "-show_entries", "stream=index,codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels",
        "-of", "json",
        str(file_path),
    ]

    result = run_command_safe(probe_cmd, timeout=DEFAULT_TIMEOUT)
    if result.returncode != 0:
        raise ValueError(
            f"Corrupted or invalid media container: {result.stderr.strip() or 'Unknown ffprobe error'}"
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse ffprobe output for {file_path}") from exc

    streams = data.get("streams", [])
    format_info = data.get("format", {})

    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    if not video_streams:
        raise ValueError(f"No video stream found in media file: {file_path}")

    v_stream = video_streams[0]
    width = int(v_stream.get("width", 0))
    height = int(v_stream.get("height", 0))

    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid video dimensions ({width}x{height}) in {file_path}")

    # Parse frame rate
    fps_raw = v_stream.get("r_frame_rate", "30/1")
    try:
        if "/" in fps_raw:
            num, den = fps_raw.split("/")
            fps = float(num) / float(den) if float(den) > 0 else 30.0
        else:
            fps = float(fps_raw)
    except Exception:
        fps = 30.0

    duration = float(format_info.get("duration", 0.0))
    if duration <= 0:
        # Check stream duration if format duration missing
        duration = float(v_stream.get("duration", 0.0))

    has_audio = len(audio_streams) > 0
    audio_channels = int(audio_streams[0].get("channels", 0)) if has_audio else 0
    audio_sample_rate = int(audio_streams[0].get("sample_rate", 0)) if has_audio else 0

    return {
        "file_path": str(file_path),
        "width": width,
        "height": height,
        "duration": duration,
        "fps": round(fps, 2),
        "has_audio": has_audio,
        "audio_channels": audio_channels,
        "audio_sample_rate": audio_sample_rate,
        "video_codec": v_stream.get("codec_name", "unknown"),
        "audio_codec": audio_streams[0].get("codec_name", "none") if has_audio else "none",
        "size_bytes": int(format_info.get("size", file_path.stat().st_size)),
    }


def download_kick_clip(
    url: str,
    output_target: Path,
    timeout: int = DOWNLOAD_TIMEOUT,
) -> Path:
    """
    Downloads a Kick clip or stream cut using yt-dlp with automated format fallbacks.
    Returns the validated output Path.
    """
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        raise ValueError(f"Invalid clip URL format: {clean_url}")

    ffmpeg_bin, _ = resolve_binary_paths()
    ffmpeg_dir = str(Path(ffmpeg_bin).parent)

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--ffmpeg-location", ffmpeg_dir,
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--no-check-certificates",
        "--retries", "3",
        "-o", str(output_target),
        clean_url,
    ]

    def _execute_download() -> Path:
        res = run_command_safe(cmd, timeout=timeout)
        if res.returncode != 0:
            # Check if output file was created anyway despite warnings
            if output_target.is_file() and output_target.stat().st_size > 1024:
                return output_target
            err_msg = res.stderr.strip() or res.stdout.strip()
            raise RuntimeError(f"yt-dlp download failed: {err_msg[:400]}")
        return output_target

    downloaded_file = retry_with_backoff(
        _execute_download,
        max_retries=2,
        initial_delay=2.0,
        task_name=f"Download Kick clip ({clean_url})",
    )

    # Validate container
    validate_media_file(downloaded_file)
    return downloaded_file


def extract_preview_frame(
    video_path: Path,
    output_image_path: Path,
    timestamp: float = 2.0,
) -> Path:
    """
    Extracts a high-quality preview frame for crop calibration.
    """
    ffmpeg_bin, _ = resolve_binary_paths()
    metadata = validate_media_file(video_path)

    # Ensure timestamp is within valid video duration bounds
    dur = float(metadata.get("duration", 0.0))
    if dur > 0.2:
        target_ts = max(0.0, min(float(timestamp), max(0.0, dur - 0.1)))
    else:
        target_ts = 0.0

    cmd = [
        ffmpeg_bin,
        "-y",
        "-ss", f"{target_ts:.2f}",
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_image_path),
    ]

    res = run_command_safe(cmd, timeout=DEFAULT_TIMEOUT)
    if res.returncode != 0 or not output_image_path.is_file():
        raise RuntimeError(f"Failed to extract frame at {target_ts}s: {res.stderr.strip()[:300]}")

    return output_image_path
