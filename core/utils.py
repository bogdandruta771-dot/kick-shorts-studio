"""Robust utility functions, subprocess management, retries, and temporary file lifecycle."""
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import List, Optional, Callable, Any, Tuple

from core.config import (
    BASE_DIR,
    BIN_DIR,
    TEMP_DIR,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    RETRY_BACKOFF_FACTOR,
)


def resolve_binary_paths() -> Tuple[str, str]:
    """
    Locates ffmpeg and ffprobe binaries across PATH, local bin/, winget, and fallback directories.
    Returns (ffmpeg_path, ffprobe_path).
    Raises FileNotFoundError if neither binary can be found.
    """
    # 1. Check local bin directory first
    local_ffmpeg = BIN_DIR / "ffmpeg.exe"
    local_ffprobe = BIN_DIR / "ffprobe.exe"
    if local_ffmpeg.is_file() and local_ffprobe.is_file():
        os.environ["PATH"] = str(BIN_DIR) + os.pathsep + os.environ.get("PATH", "")
        return str(local_ffmpeg), str(local_ffprobe)

    # 2. Check system PATH
    sys_ffmpeg = shutil.which("ffmpeg")
    sys_ffprobe = shutil.which("ffprobe")
    if sys_ffmpeg and sys_ffprobe:
        return sys_ffmpeg, sys_ffprobe

    # 3. Check common Windows install directories (winget, local appdata, scoop, chocolatey)
    search_roots = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
        Path(os.environ.get("PROGRAMFILES", "")) / "ffmpeg",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "ffmpeg",
        Path("C:/Program Files/ffmpeg"),
        Path("C:/ffmpeg"),
    ]

    found_ffmpeg: Optional[Path] = None
    found_ffprobe: Optional[Path] = None

    for root in search_roots:
        if root.is_dir():
            for exe in root.glob("**/ffmpeg.exe"):
                if exe.is_file():
                    found_ffmpeg = exe
                    break
            for exe in root.glob("**/ffprobe.exe"):
                if exe.is_file():
                    found_ffprobe = exe
                    break
            if found_ffmpeg and found_ffprobe:
                break

    # 4. Fallback: imageio_ffmpeg for ffmpeg if available
    if not found_ffmpeg:
        try:
            import imageio_ffmpeg
            img_ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())
            if img_ffmpeg.is_file():
                found_ffmpeg = img_ffmpeg
                # Check if ffprobe sits next to it
                probe_sibling = img_ffmpeg.parent / "ffprobe.exe"
                if probe_sibling.is_file():
                    found_ffprobe = probe_sibling
        except Exception:
            pass

    if found_ffmpeg and found_ffprobe:
        # Prepend to PATH so subprocesses can resolve them without full paths if needed
        ffmpeg_dir = str(found_ffmpeg.parent)
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        return str(found_ffmpeg), str(found_ffprobe)

    if found_ffmpeg and not found_ffprobe:
        # Return ffmpeg and dummy or raise actionable error
        return str(found_ffmpeg), str(found_ffmpeg)

    raise FileNotFoundError(
        "Could not locate FFmpeg and FFprobe. Please run install_dependencies.py to download or install them."
    )


def escape_ffmpeg_filter_path(file_path: str) -> str:
    """
    Escapes a Windows file path for FFmpeg filter complexes (e.g. subtitles=filename).
    Escapes colons after drive letters, single quotes, and uses forward slashes.
    """
    # Normalize path with forward slashes
    p = str(Path(file_path).resolve()).replace("\\", "/")
    # Escape colon (e.g. C:/ -> C\:/)
    p = p.replace(":", r"\:")
    # Escape single quote
    p = p.replace("'", r"\'")
    return p


def run_command_safe(
    cmd: List[str],
    timeout: int = DEFAULT_TIMEOUT,
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
) -> subprocess.CompletedProcess:
    """
    Executes a subprocess with a mandatory strict timeout to prevent deadlocks and infinite hangs.
    Captures stdout and stderr for inspection.
    """
    # Ensure environment includes our resolved PATH
    exec_env = os.environ.copy()
    if env:
        exec_env.update(env)

    # Run background subprocesses with below-normal CPU priority on Windows to keep system responsive
    extra_run_kwargs = {}
    if sys.platform == "win32":
        extra_run_kwargs["creationflags"] = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0x00004000)

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
            env=exec_env,
            check=False,
            **extra_run_kwargs,
        )
        return result
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(
            f"Process timed out after {timeout} seconds: {' '.join(cmd[:5])}..."
        ) from exc


def retry_with_backoff(
    action: Callable[[], Any],
    max_retries: int = MAX_RETRIES,
    initial_delay: float = 1.0,
    backoff_factor: float = RETRY_BACKOFF_FACTOR,
    task_name: str = "Operation",
) -> Any:
    """
    Executes a callable with deterministic retries and exponential backoff.
    Fails cleanly after max_retries attempts.
    """
    current_delay = initial_delay
    last_exception: Optional[Exception] = None

    for attempt in range(1, max_retries + 2):
        try:
            return action()
        except Exception as exc:
            last_exception = exc
            if attempt <= max_retries:
                time.sleep(current_delay)
                current_delay *= backoff_factor
            else:
                break

    raise RuntimeError(
        f"{task_name} failed after {max_retries + 1} attempts. Last error: {last_exception}"
    ) from last_exception


class TempFileManager:
    """Manages unique timestamped UUID temporary directories with guaranteed cleanup."""

    def __init__(self, session_prefix: str = "job"):
        self.session_id = f"{session_prefix}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        self.dir = TEMP_DIR / self.session_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self._tracked_files: List[Path] = []

    def get_path(self, filename_or_suffix: str) -> Path:
        """Returns a path inside this session's temp directory."""
        if filename_or_suffix.startswith("."):
            path = self.dir / f"temp_{uuid.uuid4().hex[:8]}{filename_or_suffix}"
        else:
            path = self.dir / filename_or_suffix
        self._tracked_files.append(path)
        return path

    def cleanup(self) -> None:
        """Removes all files in this session directory."""
        if self.dir.exists():
            try:
                shutil.rmtree(self.dir, ignore_errors=True)
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def cleanup_stale_temp_dirs(max_age_hours: float = 3.0) -> int:
    """Cleans up stale temp directories older than max_age_hours."""
    count = 0
    now = time.time()
    cutoff = now - (max_age_hours * 3600)
    for entry in TEMP_DIR.iterdir():
        if entry.is_dir():
            try:
                if entry.stat().st_mtime < cutoff:
                    shutil.rmtree(entry, ignore_errors=True)
                    count += 1
            except Exception:
                pass
    return count
