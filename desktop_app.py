"""
OmniStudio Desktop App
Standalone native Windows desktop runner powered by Chromium App Engine + EdgeChromium + Unified FastAPI Hub.
Runs as a true native desktop application with a borderless app window, zero terminal clutter,
and instant startup.
"""
import os
import sys
import time
import socket
import shutil
import ctypes
import traceback
import threading
import subprocess
import urllib.request
import webbrowser
from pathlib import Path

# Ensure root directory is in sys.path
ROOT_DIR = Path(__file__).parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

LOG_FILE = ROOT_DIR / "desktop_app.log"


def log(msg: str):
    """Writes diagnostic timestamped logs to desktop_app.log."""
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def custom_excepthook(exc_type, exc_value, exc_traceback):
    """Ensures any uncaught exception anywhere in Python is logged and alerted."""
    err = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    log(f"FATAL UNCAUGHT EXCEPTION:\n{err}")
    try:
        ctypes.windll.user32.MessageBoxW(0, f"OmniStudio encountered an error:\n{err}", "OmniStudio Error", 0x10)
    except Exception:
        pass

sys.excepthook = custom_excepthook

# Redirect streams if running detached or under pythonw.exe
class LogStream:
    def write(self, data):
        if data and data.strip():
            log(f"[stdout/stderr] {data.strip()}")
    def flush(self):
        pass
    def isatty(self):
        return False

if sys.stdout is None:
    sys.stdout = LogStream()
if sys.stderr is None:
    sys.stderr = LogStream()
if sys.stdin is None:
    try:
        sys.stdin = open(os.devnull, "r")
    except Exception:
        pass


# Ensure required runtime folders exist
(ROOT_DIR / "output").mkdir(parents=True, exist_ok=True)
(ROOT_DIR / "temp").mkdir(parents=True, exist_ok=True)
(ROOT_DIR / "data").mkdir(parents=True, exist_ok=True)
(ROOT_DIR / "data" / "app_profile").mkdir(parents=True, exist_ok=True)
(ROOT_DIR / "assets").mkdir(parents=True, exist_ok=True)
(ROOT_DIR / "assets" / "cache").mkdir(parents=True, exist_ok=True)
(ROOT_DIR / "assets" / "uploads").mkdir(parents=True, exist_ok=True)

try:
    import uvicorn
    from app import app
except BaseException as exc:
    err_msg = f"Fatal Error importing studio backend:\n{traceback.format_exc()}"
    log(err_msg)
    try:
        ctypes.windll.user32.MessageBoxW(0, err_msg, "OmniStudio Startup Error", 0x10)
    except Exception:
        pass
    sys.exit(1)


def is_port_in_use(port: int = 7860) -> bool:
    """Checks if port 7860 is already responding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0


def wait_for_server(url: str = "http://127.0.0.1:7860", timeout: float = 12.0) -> bool:
    """Polls until server is actively serving responses."""
    start_t = time.time()
    while time.time() - start_t < timeout:
        try:
            with urllib.request.urlopen(f"{url}/api/crop-presets", timeout=0.8) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def run_server():
    """Runs Uvicorn in a dedicated worker thread."""
    try:
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=7860,
            log_level="warning",
            access_log=False,
            log_config=None,
        )
    except Exception as exc:
        log(f"Uvicorn server thread error: {traceback.format_exc()}")


def find_chromium_app_browser() -> str | None:
    """
    Locates an installed Chromium-based browser to run OmniStudio in true native App Mode.
    App Mode provides an isolated, borderless window with zero browser bars or tabs,
    full hardware acceleration, and perfect video rendering.
    """
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

    candidates = [
        # Google Chrome (Optimal)
        os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe"),
        # Microsoft Edge
        os.path.join(program_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(program_files, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(program_files_x86, "Microsoft", "EdgeCore", "Optimized", "msedge.exe"),
        # Brave Browser
        os.path.join(program_files, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
        os.path.join(program_files_x86, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
    ]

    for p in candidates:
        if p and os.path.isfile(p):
            return p

    # Fallback to PATH lookup
    for name in ["chrome.exe", "msedge.exe", "brave.exe"]:
        found = shutil.which(name)
        if found and os.path.isfile(found):
            return found

    return None


def start_desktop():
    server_url = "http://127.0.0.1:7860"
    log("Starting OmniStudio desktop runner...")

    # Start server thread if not already running
    if not is_port_in_use(7860):
        log("Port 7860 is free. Starting background FastAPI/Uvicorn server thread...")
        t = threading.Thread(target=run_server, daemon=True)
        t.start()
        ready = wait_for_server(server_url, timeout=12.0)
        if not ready:
            err_msg = "OmniStudio backend server failed to become responsive on port 7860 within 12 seconds."
            log(err_msg)
            try:
                ctypes.windll.user32.MessageBoxW(0, err_msg, "OmniStudio Startup Error", 0x10)
            except Exception:
                pass
            sys.exit(1)
        log("Backend server verified online and serving responses on 7860.")
    else:
        log("Port 7860 is already responding. Reusing active instance.")

    # CLI flag for browser-only mode
    if "--browser" in sys.argv:
        log("Browser mode explicitly requested via CLI flag.")
        webbrowser.open(server_url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sys.exit(0)

    # 1. PRIMARY RUNNER: Native Chromium App Mode (Border-free standalone window)
    chromium_bin = find_chromium_app_browser()
    if chromium_bin and "--force-webview" not in sys.argv:
        profile_dir = str(ROOT_DIR / "data" / "app_profile")
        log(f"Launching OmniStudio via Chromium App Engine: {chromium_bin}")

        cmd = [
            chromium_bin,
            f"--app={server_url}",
            "--window-size=1500,960",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--enable-gpu-rasterization",
            "--enable-zero-copy",
        ]

        try:
            proc = subprocess.Popen(cmd)
            log(f"OmniStudio App window active with PID {proc.pid}. Waiting for user close...")
            proc.wait()
            log("OmniStudio window closed by user. Clean shutdown complete.")
            sys.exit(0)
        except Exception as exc:
            log(f"Notice: Chromium app launch exception ({exc}), falling back to webview...")

    # 2. SECONDARY RUNNER: pywebview EdgeChromium / WinForms
    try:
        import webview
        from webview.guilib import initialize
        try:
            initialize('edgechromium')
        except Exception:
            pass

        icon_file = str(ROOT_DIR / "assets" / "icon.ico")
        if not os.path.exists(icon_file):
            icon_file = str(ROOT_DIR / "assets" / "icon.png")

        log("Launching via pywebview desktop window...")
        window = webview.create_window(
            title="OmniStudio - Stream Clipper & Motion Explainer Hub",
            url=server_url,
            width=1500,
            height=960,
            min_size=(1080, 700),
            background_color="#090a0f",
            text_select=True,
            confirm_close=False,
        )
        webview.start(icon=icon_file if os.path.exists(icon_file) else None)
        log("OmniStudio webview window closed cleanly.")
        sys.exit(0)
    except Exception as exc:
        log(f"Notice: Pywebview unavailable or closed with ({exc}). Falling back to system default browser.")

    # 3. TERTIARY FALLBACK: System default web browser
    try:
        log(f"Opening system default browser at {server_url}")
        webbrowser.open(server_url)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    try:
        start_desktop()
    except Exception as exc:
        err = f"Unhandled OmniStudio Exception:\n{traceback.format_exc()}"
        log(err)
        try:
            ctypes.windll.user32.MessageBoxW(0, err, "OmniStudio Error", 0x10)
        except Exception:
            pass
        sys.exit(1)
