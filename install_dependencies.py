"""Self-installing dependency and environment bootstrap script for Windows."""
import os
import sys
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BIN_DIR = BASE_DIR / "bin"
REQUIREMENTS_FILE = BASE_DIR / "requirements.txt"

BIN_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    print(f"[BOOTSTRAP] {msg}")


def check_python_version():
    log(f"Checking Python version: {sys.version.split()[0]}...")
    if sys.version_info < (3, 10):
        log("WARNING: Recommended Python version is 3.10+.")
    else:
        log("Python version OK.")


def install_python_requirements():
    log("Installing Python dependencies from requirements.txt...")
    cmd = [
        sys.executable,
        "-m", "pip",
        "install",
        "-r", str(REQUIREMENTS_FILE),
    ]
    res = subprocess.run(cmd)
    if res.returncode != 0:
        log("Warning: Pip reported errors during dependency installation.")
    else:
        log("Python packages installed successfully.")


def ensure_ffmpeg_binaries():
    ffmpeg_target = BIN_DIR / "ffmpeg.exe"
    ffprobe_target = BIN_DIR / "ffprobe.exe"

    if ffmpeg_target.is_file() and ffprobe_target.is_file():
        log(f"FFmpeg & FFprobe already localized at {BIN_DIR}.")
        return

    log("Locating FFmpeg & FFprobe on system...")
    # Check PATH first
    sys_ffmpeg = shutil.which("ffmpeg")
    sys_ffprobe = shutil.which("ffprobe")

    if sys_ffmpeg and sys_ffprobe:
        log(f"Found on system PATH: {sys_ffmpeg}")
        shutil.copy2(sys_ffmpeg, ffmpeg_target)
        shutil.copy2(sys_ffprobe, ffprobe_target)
        log(f"Copied binaries to {BIN_DIR}.")
        return

    # Check Winget / User AppData directories
    user_local = Path(os.environ.get("LOCALAPPDATA", ""))
    winget_packages = user_local / "Microsoft" / "WinGet" / "Packages"

    found_ffmpeg = None
    found_ffprobe = None

    if winget_packages.is_dir():
        for f in winget_packages.glob("**/ffmpeg.exe"):
            found_ffmpeg = f
            break
        for f in winget_packages.glob("**/ffprobe.exe"):
            found_ffprobe = f
            break

    if found_ffmpeg and found_ffprobe:
        log(f"Found Winget FFmpeg installation: {found_ffmpeg.parent}")
        shutil.copy2(found_ffmpeg, ffmpeg_target)
        shutil.copy2(found_ffprobe, ffprobe_target)
        log(f"Localized binaries to {BIN_DIR}.")
        return

    # Download standalone essentials zip if not found
    log("Downloading standalone FFmpeg essentials package for Windows...")
    zip_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    zip_path = BIN_DIR / "ffmpeg_temp.zip"

    try:
        urllib.request.urlretrieve(zip_url, zip_path)
        log("Extracting ffmpeg and ffprobe...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.namelist():
                if member.endswith("ffmpeg.exe"):
                    with zip_ref.open(member) as source, open(ffmpeg_target, "wb") as target:
                        shutil.copyfileobj(source, target)
                elif member.endswith("ffprobe.exe"):
                    with zip_ref.open(member) as source, open(ffprobe_target, "wb") as target:
                        shutil.copyfileobj(source, target)
        if zip_path.is_file():
            zip_path.unlink()
        log(f"FFmpeg successfully localized to {BIN_DIR}.")
    except Exception as exc:
        log(f"Download fallback error: {exc}. Trying imageio-ffmpeg fallback...")
        try:
            import imageio_ffmpeg
            img_exe = Path(imageio_ffmpeg.get_ffmpeg_exe())
            if img_exe.is_file():
                shutil.copy2(img_exe, ffmpeg_target)
                log(f"Copied ffmpeg from imageio_ffmpeg: {img_exe}")
        except Exception:
            pass


def main():
    print("=" * 60)
    print("   Kick Shorts Studio - Dependency & Environment Setup")
    print("=" * 60)
    check_python_version()
    ensure_ffmpeg_binaries()
    install_python_requirements()
    print("=" * 60)
    print("   Environment verification complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
