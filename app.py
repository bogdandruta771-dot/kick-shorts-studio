import asyncio
import os
import sys
import time
import json
import base64
import io
import uuid
import threading
import subprocess
import webbrowser
import re
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

from core.banner_generator import generate_promo_banner, process_uploaded_overlay, generate_hook_banner
from core.ai_copywriter import generate_shorts_metadata, get_available_ai_providers, generate_viral_hooks, test_ai_provider_connection
from core.audio_detector import analyze_audio_climax
from core.youtube_uploader import (
    get_youtube_auth_status,
    save_client_secrets_json,
    save_client_id_and_secret,
    reset_youtube_credentials,
    start_youtube_oauth_flow,
    disconnect_youtube,
    disconnect_youtube_account,
    list_youtube_accounts,
    upload_shorts_video,
    get_youtube_authorization_url,
    exchange_youtube_code,
    get_youtube_client_type,
    CLIENT_SECRETS_FILE,
)

from core.clip_history import (
    record_clipped_short,
    check_if_clipped,
    tag_clip_search_results,
    list_clip_history,
    delete_history_item,
    clear_all_history,
)

from core.facecam_detector import (
    detect_facecam_from_image,
    detect_facecam_from_video,
    calculate_optimal_layout,
)

from core.motion_explainer.ai_scriptwriter import VIRAL_PRESETS, get_available_presets, generate_motion_script_ai
from core.motion_explainer.voice_engine import get_available_voices, synthesize_speech, probe_audio_duration
from core.motion_explainer.asset_generator import ASSETS_CACHE_DIR
from core.motion_explainer.motion_renderer import (
    render_motion_frame,
    render_motion_explainer_short,
    detect_best_ffmpeg_encoder,
)
from core.motion_explainer.sfx_library import ensure_sfx_library
from core.motion_explainer.tradeit_assets import get_tradeit_default_items
from core.faceless_engine import (
    generate_faceless_script,
    render_faceless_short,
)
from core.ai_virality_scorer import score_stream_transcript
from core.broll_fetcher import search_pexels_videos, search_pixabay_videos
from core.subtitles import SUBTITLE_PRESETS
from core.autopilot import autopilot

from core.config import (
    OUTPUT_DIR,
    TEMP_DIR,
    CROP_PRESETS,
    DEFAULT_FONT_NAME,
    DEFAULT_FONT_SIZE,
    DEFAULT_PRIMARY_COLOR,
    DEFAULT_HIGHLIGHT_COLOR,
    DEFAULT_SUBTITLE_Y_OFFSET,
    TARGET_WIDTH,
    TARGET_HEIGHT,
    DEFAULT_MIN_WIN_AMOUNT,
    DEFAULT_MIN_MULTIPLIER,
    DEFAULT_POLL_INTERVAL_SEC,
)
from core.utils import TempFileManager, cleanup_stale_temp_dirs
from core.video_ingest import (
    validate_media_file,
    download_kick_clip,
    download_stream_clip,
    detect_stream_platform,
    fetch_twitch_channel_clips,
    fetch_kick_clips,
    fetch_twitch_clips,
    fetch_youtube_clips,
    parse_youtube_timestamp,
    search_unified_clips,
    extract_preview_frame,
)
from core.video_processor import VideoProcessor
from core.detector import UniversalWatchdogManager, KickWatchdogManager, WinExtractor, sanitize_channel_slug

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """Configures asyncio exception handler to silence client disconnects during video scrubbing."""
    try:
        loop = asyncio.get_running_loop()
        def _exc_handler(loop, context):
            exc = context.get("exception")
            if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
                return
            loop.default_exception_handler(context)
        loop.set_exception_handler(_exc_handler)
    except Exception:
        pass
    yield


app = FastAPI(title="OmniStream Shorts Studio - Kick & Twitch", version="2.5.0", lifespan=lifespan)
processor = VideoProcessor()
watchdog = UniversalWatchdogManager()

# In-Memory Background Job Store
export_jobs: Dict[str, Dict[str, Any]] = {}
youtube_upload_jobs: Dict[str, Dict[str, Any]] = {}
_RENDER_SEMAPHORE = threading.Semaphore(1)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def pil_to_base64(img: Image.Image) -> str:
    """Encodes PIL Image to base64 JPEG string."""
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


# Request Models
class IngestUrlRequest(BaseModel):
    url: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None


class WatchdogStartRequest(BaseModel):
    channel_slug: str
    platform: Optional[str] = "kick"
    category: Optional[str] = "all"
    min_amount: Optional[float] = DEFAULT_MIN_WIN_AMOUNT
    min_multiplier: Optional[float] = DEFAULT_MIN_MULTIPLIER
    poll_interval: Optional[float] = DEFAULT_POLL_INTERVAL_SEC


class SensitivityPresetRequest(BaseModel):
    preset: str  # aggressive, balanced, high_roller


class ScanRecentClipsRequest(BaseModel):
    channel_slug: Optional[str] = None
    platform: Optional[str] = "kick"
    category: Optional[str] = "all"
    hours: Optional[int] = 24


class AnalyzeAudioClimaxRequest(BaseModel):
    video_path: Optional[str] = None
    target_clip_duration: Optional[float] = 20.0
    pre_roll_sec: Optional[float] = 6.0


class SelectWinRequest(BaseModel):
    clip_url: str
    clip_id: Optional[str] = None
    title: Optional[str] = None


class SearchClipsRequest(BaseModel):
    query: Optional[str] = ""
    platform: Optional[str] = "all"  # "all", "kick", "twitch"
    category: Optional[str] = "all"
    time_filter: Optional[str] = "all"  # "day", "week", "month", "all"
    sort: Optional[str] = "view"  # "view", "date"
    limit: Optional[int] = 60
    page: Optional[int] = 1
    page_size: Optional[int] = 12


class ImportClipRequest(BaseModel):
    clip_url: str
    clip_id: Optional[str] = None
    title: Optional[str] = None
    platform: Optional[str] = None
    category: Optional[str] = None
    streamer: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None


class OneClickShortRequest(BaseModel):
    clip_url: str
    title: Optional[str] = None
    streamer: Optional[str] = None
    category: Optional[str] = None
    preset: Optional[str] = "auto"
    enable_anti_shadowban: Optional[bool] = True
    enable_hook: Optional[bool] = True
    hook_text: Optional[str] = None
    hook_options: Optional[Dict[str, Any]] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None


class FrameExtractRequest(BaseModel):
    video_path: Optional[str] = None
    timestamp: float = 0.0


class AutoDetectFacecamRequest(BaseModel):
    video_path: Optional[str] = None
    timestamp: Optional[float] = None


class ExportPayload(BaseModel):
    video_path: Optional[str] = None
    crops: Optional[Dict[str, Any]] = None
    subtitles: Optional[Dict[str, Any]] = None
    outro_path: Optional[str] = None
    trim_start: Optional[float] = None
    trim_end: Optional[float] = None
    overlays: Optional[List[Dict[str, Any]]] = None
    enable_anti_shadowban: Optional[bool] = True
    hook_text: Optional[str] = None
    hook_options: Optional[Dict[str, Any]] = None


class GenerateHooksRequest(BaseModel):
    clip_title: Optional[str] = None
    streamer: Optional[str] = None
    category: Optional[str] = "general"


class PreviewHookBannerRequest(BaseModel):
    text: str
    style: Optional[str] = "yellow_badge"


class SafeMetadataRequest(BaseModel):
    streamer: Optional[str] = None
    detected_win: Optional[str] = None


class SetYouTubeCredentialsRequest(BaseModel):
    raw_json: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    client_type: Optional[str] = "desktop"


class GenerateBannerRequest(BaseModel):
    text: str
    sub_text: Optional[str] = None
    badge_text: Optional[str] = "PROMO CODE"
    bg_color: Optional[str] = "#0b0f19"
    text_color: Optional[str] = "#ffd700"
    accent_color: Optional[str] = "#00dcff"
    width: Optional[int] = 1080
    height: Optional[int] = 140


class GenerateMetadataRequest(BaseModel):
    clip_title: Optional[str] = "Stream Highlight Moment"
    category: Optional[str] = "general"
    win_amount: Optional[Any] = None
    multiplier: Optional[Any] = None
    streamer: Optional[str] = None
    transcript: Optional[str] = None
    promo_code: Optional[str] = None
    api_key: Optional[str] = None
    provider: Optional[str] = "auto"
    model: Optional[str] = None
    base_url: Optional[str] = None


class TestAiConnectionRequest(BaseModel):
    provider: Optional[str] = "auto"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class YouTubeUploadRequest(BaseModel):
    video_path: Optional[str] = None
    title: str
    description: str
    tags: Optional[List[str]] = None
    privacy_status: Optional[str] = "public"
    made_for_kids: Optional[bool] = False
    channel_id: Optional[str] = None
    channel_ids: Optional[List[str]] = None


class DisconnectAccountRequest(BaseModel):
    channel_id: str


class ExchangeCodeRequest(BaseModel):
    code: str
    redirect_uri: Optional[str] = None


# Mount media & assets for studio playback and motion rendering
app.mount("/temp_media", StaticFiles(directory=str(TEMP_DIR)), name="temp_media")

ASSETS_DIR = Path(__file__).parent.resolve() / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR = ASSETS_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR = Path(__file__).parent.resolve() / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")
app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")


@app.get("/", response_class=HTMLResponse)
async def serve_home():
    """Serves the minimalist multi-step studio UI."""
    template_path = Path(__file__).parent / "templates" / "index.html"
    if not template_path.is_file():
        raise HTTPException(status_code=500, detail="Template index.html not found.")
    return HTMLResponse(content=template_path.read_text(encoding="utf-8"))


@app.get("/favicon.ico")
async def favicon():
    icon_path = Path(__file__).parent / "assets" / "icon.ico"
    if icon_path.exists():
        return FileResponse(str(icon_path), media_type="image/x-icon")
    return Response(status_code=404)


# --- DETECTOR API ENDPOINTS ---

@app.post("/api/detector/start")
async def start_detector_watchdog(req: WatchdogStartRequest):
    """Starts dual-sentinel Kick or Twitch live monitoring watchdog."""
    slug = req.channel_slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="Missing channel slug.")
    try:
        res = watchdog.start_watchdog(
            channel_slug=slug,
            platform=req.platform or "kick",
            stream_category=req.category or "all",
            min_amount=req.min_amount or DEFAULT_MIN_WIN_AMOUNT,
            min_multiplier=req.min_multiplier or DEFAULT_MIN_MULTIPLIER,
            poll_interval=req.poll_interval or DEFAULT_POLL_INTERVAL_SEC,
        )
        return res
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/detector/stop")
async def stop_detector_watchdog():
    """Stops active watchdog monitoring."""
    return watchdog.stop_watchdog()


@app.get("/api/detector/status")
async def get_detector_status():
    """Returns real-time status, chat velocity gauge, and detected wins feed."""
    return watchdog.get_status()


@app.post("/api/detector/set-sensitivity")
async def set_detector_sensitivity(req: SensitivityPresetRequest):
    """Updates detector sensitivity threshold preset (aggressive, balanced, high_roller)."""
    return watchdog.set_sensitivity_preset(req.preset)


@app.post("/api/detector/scan-recent-clips")
async def scan_recent_clips_endpoint(req: ScanRecentClipsRequest):
    """Scans Kick or Twitch channel clips for qualified big wins and viral moments."""
    slug = req.channel_slug or watchdog.channel_slug
    if not slug:
        raise HTTPException(status_code=400, detail="Missing channel slug.")
    try:
        clean_slug = sanitize_channel_slug(slug)
        watchdog.channel_slug = clean_slug
        plat = req.platform or ("twitch" if ("twitch" in str(slug).lower() or "twitch.tv" in str(slug).lower()) else watchdog.platform)
        wins = watchdog.scan_channel_recent_wins(hours=req.hours or 168, platform=plat)
        return {"channel": clean_slug, "platform": plat, "wins": wins, "count": len(wins)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/detector/analyze-audio-climax")
async def analyze_audio_climax_endpoint(req: AnalyzeAudioClimaxRequest):
    """Pinpoints the peak excitement moment / winning spin reaction in video using lightweight audio RMS energy analysis."""
    target_file = None
    if req.video_path:
        target_file = _resolve_safe_video_path(req.video_path)

    if not target_file or not target_file.is_file():
        clip_candidates = sorted(
            [f for f in TEMP_DIR.glob("*.*") if f.suffix.lower() in (".mp4", ".mov", ".mkv") and not f.name.startswith("outro_")],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        if clip_candidates:
            target_file = clip_candidates[0]
        else:
            raise HTTPException(status_code=400, detail="No video file available to analyze.")

    try:
        res = analyze_audio_climax(
            video_path=target_file,
            target_clip_duration=req.target_clip_duration or 20.0,
            pre_roll_sec=req.pre_roll_sec or 6.0,
        )
        return res
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/detector/select-win")
async def select_detector_win(req: SelectWinRequest):
    """Downloads a detected clip via yt-dlp and returns preview snapshot for Step 2 Framing."""
    url = req.clip_url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing clip URL.")

    platform = detect_stream_platform(url)
    ts = int(time.time())
    dest_path = TEMP_DIR / f"{platform}_clip_{ts}.mp4"

    try:
        active_path = download_stream_clip(url, dest_path)
        meta = validate_media_file(active_path)

        preview_img_path = TEMP_DIR / f"snap_{ts}.jpg"
        extract_preview_frame(active_path, preview_img_path, timestamp=2.0)
        img = Image.open(preview_img_path)
        b64 = pil_to_base64(img)

        suggested_preset = "gaming_fps" if platform == "twitch" else "standard_dual"
        dup_info = check_if_clipped(url)

        return {
            "path": str(active_path),
            "filename": active_path.name,
            "video_url": f"/temp_media/{active_path.name}",
            "platform": platform,
            "suggested_preset": suggested_preset,
            "title": req.title or f"{platform.capitalize()} Clip",
            "width": meta["width"],
            "height": meta["height"],
            "duration": meta["duration"],
            "fps": meta["fps"],
            "has_audio": meta["has_audio"],
            "preview_base64": b64,
            "is_already_clipped": dup_info.get("is_clipped", False),
            "clip_count": dup_info.get("clip_count", 0),
            "latest_output": dup_info.get("latest_output", ""),
            "last_clipped_at": dup_info.get("last_clipped_at", ""),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# --- 🔍 VIRAL CLIP EXPLORER & INSTANT CLIPPER ENDPOINTS ---

@app.post("/api/clips/search")
async def search_clips_endpoint(req: SearchClipsRequest):
    """Searches and discovers top clips across Kick and Twitch with category and time filters and multi-page support."""
    try:
        fetch_limit = req.limit or 60
        results = search_unified_clips(
            query=req.query or "",
            platform=req.platform or "all",
            category=req.category or "all",
            time_filter=req.time_filter or "all",
            sort=req.sort or "view",
            limit=fetch_limit,
        )
        # Tag each clip with persistent history and anti-repeat badges
        try:
            results = tag_clip_search_results(results)
        except Exception as _tag_err:
            print(f"NOTICE: History tagging notice: {_tag_err}")
        total_count = len(results)
        page = max(1, req.page or 1)
        page_size = max(1, req.page_size or 12)
        total_pages = max(1, (total_count + page_size - 1) // page_size) if total_count > 0 else 1

        return {
            "count": total_count,
            "clips": results,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "query": req.query,
            "platform": req.platform,
            "category": req.category,
            "time_filter": req.time_filter,
            "sort": req.sort,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/clips/search")
async def search_clips_get(
    query: Optional[str] = "",
    platform: Optional[str] = "all",
    category: Optional[str] = "all",
    time_filter: Optional[str] = "all",
    sort: Optional[str] = "view",
    limit: Optional[int] = 60,
    page: Optional[int] = 1,
    page_size: Optional[int] = 12,
):
    """GET variant for instant URL query searching."""
    req = SearchClipsRequest(
        query=query,
        platform=platform,
        category=category,
        time_filter=time_filter,
        sort=sort,
        limit=limit,
        page=page,
        page_size=page_size,
    )
    return await search_clips_endpoint(req)


@app.get("/api/clips/trending")
async def get_trending_clips(
    platform: Optional[str] = "all",
    time_filter: Optional[str] = "day",
    limit: Optional[int] = 60,
):
    """Returns hottest trending clips right now from Kick and Twitch."""
    req = SearchClipsRequest(
        query="",
        platform=platform,
        category="all",
        time_filter=time_filter or "day",
        sort="view",
        limit=limit or 60,
    )
    return await search_clips_endpoint(req)


@app.post("/api/clips/import")
async def import_clip_endpoint(req: ImportClipRequest):
    """Imports any discovered clip from Kick or Twitch directly into Step 2 Framing."""
    url = req.clip_url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing clip URL.")

    platform = req.platform or detect_stream_platform(url)
    ts = int(time.time())
    dest_path = TEMP_DIR / f"{platform}_clip_{ts}_{uuid.uuid4().hex[:4]}.mp4"

    try:
        active_path = await asyncio.to_thread(
            download_stream_clip,
            url,
            dest_path,
            start_time=req.start_time,
            end_time=req.end_time,
            duration=req.duration,
        )
        meta = await asyncio.to_thread(validate_media_file, active_path)

        preview_img_path = TEMP_DIR / f"snap_{active_path.stem}.jpg"
        await asyncio.to_thread(extract_preview_frame, active_path, preview_img_path, 2.0)
        img = Image.open(preview_img_path)
        b64 = pil_to_base64(img)

        # Smart preset determination
        cat = (req.category or "").lower()
        if "slot" in cat or "casino" in cat:
            suggested_preset = "center_slot"
        elif "chatting" in cat or "irl" in cat or "react" in cat:
            suggested_preset = "reaction_standard"
        elif "fps" in cat or "valorant" in cat or "shooter" in cat or platform in ("twitch", "youtube"):
            suggested_preset = "gaming_fps"
        else:
            suggested_preset = "ambient_blur_16_9"

        return {
            "path": str(active_path),
            "filename": active_path.name,
            "video_url": f"/temp_media/{active_path.name}",
            "platform": platform,
            "suggested_preset": suggested_preset,
            "title": req.title or f"{platform.capitalize()} Clip",
            "streamer": req.streamer or "",
            "category": req.category or "",
            "width": meta["width"],
            "height": meta["height"],
            "duration": meta["duration"],
            "fps": meta["fps"],
            "has_audio": meta["has_audio"],
            "preview_base64": b64,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/clips/one-click-short")
async def one_click_short_endpoint(req: OneClickShortRequest):
    """
    1-Click End-to-End Automation:
    Downloads clip -> Auto-frames layout -> Whisper Speech-to-Text with anti-shadowban NLP sanitizer ->
    GPU-accelerated hardware encoding with anti-shadowban layer -> High-CTR titles/hashtags generation.
    """
    url = req.clip_url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing clip URL.")

    job_id = f"auto_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    export_jobs[job_id] = {
        "job_id": job_id,
        "percent": 0.05,
        "message": "Initializing 1-click clip pipeline...",
        "done": False,
        "error": None,
        "output_path": None,
        "output_filename": None,
        "output_url": None,
        "metadata": None,
    }

    def _worker():
        try:
            platform = detect_stream_platform(url)
            ts = int(time.time())
            dest_path = TEMP_DIR / f"{platform}_auto_{ts}_{uuid.uuid4().hex[:4]}.mp4"

            export_jobs[job_id]["message"] = f"Downloading {platform.capitalize()} clip..."
            export_jobs[job_id]["percent"] = 0.15

            downloaded = download_stream_clip(
                url,
                dest_path,
                start_time=req.start_time,
                end_time=req.end_time,
                duration=req.duration,
            )
            meta = validate_media_file(downloaded)

            # Choose optimal preset via AI Facecam / Layout Intelligence
            cat = (req.category or "").lower()
            preset_key = req.preset or "auto"
            ai_layout = None
            if preset_key == "auto":
                if "slot" in cat or "casino" in cat:
                    preset_key = "center_slot"
                else:
                    try:
                        ai_layout = detect_facecam_from_video(
                            downloaded,
                            target_timestamp=req.start_time,
                            duration=meta.get("duration", 0.0),
                        )
                        if ai_layout and ai_layout.get("detected"):
                            preset_key = ai_layout.get("preset_name", "reaction_top_left")
                        else:
                            # If no face is detected (e.g. gameplay montage, knife unbox, anime),
                            # ambient blur is 1000x superior to slicing a random corner
                            preset_key = "ambient_blur_16_9"
                    except Exception as _ai_det_err:
                        print(f"WARN: Auto facecam detection notice: {_ai_det_err}")
                        preset_key = "ambient_blur_16_9"

            if ai_layout and ai_layout.get("detected"):
                gp = ai_layout["gameplay"]
                fc = ai_layout["facecam"]
                stack_mode = ai_layout["stack_mode"]
            else:
                preset_cfg = CROP_PRESETS.get(preset_key, CROP_PRESETS["ambient_blur_16_9"])
                gp = preset_cfg["gameplay"]
                fc = preset_cfg["facecam"]
                stack_mode = preset_cfg.get("stack_mode", "standard")
                if req.preset in ("reaction_cam_top", "reaction_top_left", "reddit_reaction"):
                    stack_mode = "cam_top"

            export_jobs[job_id]["message"] = "Processing video, generating subtitles & anti-shadowban FX..."
            export_jobs[job_id]["percent"] = 0.35

            out_filename = f"short_auto_{ts}_{uuid.uuid4().hex[:6]}.mp4"
            out_path = OUTPUT_DIR / out_filename

            def _prog(frac, msg):
                export_jobs[job_id]["percent"] = 0.35 + (frac * 0.55)
                export_jobs[job_id]["message"] = msg

            hook_txt = req.hook_text
            if not hook_txt and (req.enable_hook if req.enable_hook is not None else True):
                auto_hooks = generate_viral_hooks(
                    clip_title=req.title or "Viral Highlight",
                    streamer=req.streamer,
                    category=req.category or "general",
                )
                if auto_hooks:
                    hook_txt = auto_hooks[0]

            with _RENDER_SEMAPHORE:
                final_file = processor.process_short(
                    input_video_path=downloaded,
                    output_video_path=out_path,
                    gameplay_crop=gp,
                    facecam_crop=fc,
                    stack_mode=stack_mode,
                    enable_subtitles=True,
                    subtitle_options={
                        "font_name": DEFAULT_FONT_NAME,
                        "font_size": DEFAULT_FONT_SIZE,
                        "primary_color": DEFAULT_PRIMARY_COLOR,
                        "highlight_color": DEFAULT_HIGHLIGHT_COLOR,
                        "y_position": DEFAULT_SUBTITLE_Y_OFFSET,
                    },
                    enable_anti_shadowban=bool(req.enable_anti_shadowban if req.enable_anti_shadowban is not None else True),
                    hook_text=hook_txt,
                    hook_options=req.hook_options or {"duration": 3.5, "style": "yellow_badge", "position": "top"},
                    progress_cb=_prog,
                )

            export_jobs[job_id]["message"] = "Generating safe high-CTR metadata..."
            export_jobs[job_id]["percent"] = 0.95

            meta_res = generate_shorts_metadata(
                clip_title=req.title or f"{platform.capitalize()} Highlight Moment",
                category=req.category or "general",
                streamer=req.streamer,
                provider="offline",
            )

            export_jobs[job_id].update({
                "percent": 1.0,
                "message": "Viral Short created successfully!",
                "done": True,
                "error": None,
                "output_path": str(final_file),
                "output_filename": final_file.name,
                "output_url": f"/outputs/{final_file.name}",
                "metadata": meta_res,
            })
            # Record into Clip History & Anti-Repeat DB
            try:
                record_clipped_short(
                    source_url=url,
                    output_filename=final_file.name,
                    title=req.title or f"{platform.capitalize()} Clip",
                    channel=req.streamer or "",
                    duration=meta.get("duration", 0.0),
                    preset=preset_key,
                    ai_title=meta_res.get("title", ""),
                )
            except Exception as _hist_err:
                print(f"NOTICE: History logging notice: {_hist_err}")
            cleanup_stale_temp_dirs(max_age_hours=2.0)
        except Exception as exc:
            export_jobs[job_id].update({
                "done": True,
                "error": str(exc),
                "message": f"Pipeline failed: {exc}",
            })

    threading.Thread(target=_worker, daemon=True).start()
    return {"job_id": job_id, "status": "started"}



@app.get("/api/active-session")
async def get_active_session():
    """Returns the latest ingested clip, outro, and latest exported short."""
    latest_export = None
    output_candidates = sorted(
        OUTPUT_DIR.glob("*.mp4"),
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )
    if output_candidates and output_candidates[0].is_file():
        newest_out = output_candidates[0]
        latest_export = {
            "output_path": str(newest_out),
            "output_filename": newest_out.name,
            "output_url": f"/outputs/{newest_out.name}",
        }

    clip_candidates = sorted(
        [f for f in TEMP_DIR.glob("*.*") if f.suffix.lower() in (".mp4", ".mov", ".mkv") and not f.name.startswith("outro_")],
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )
    if not clip_candidates:
        return {"has_clip": False, "latest_export": latest_export}

    active_clip = clip_candidates[0]
    try:
        meta = validate_media_file(active_clip)
        preview_img_path = TEMP_DIR / f"snap_{active_clip.stem}.jpg"
        if not preview_img_path.is_file():
            extract_preview_frame(active_clip, preview_img_path, timestamp=2.0)
        img = Image.open(preview_img_path)
        b64 = pil_to_base64(img)

        outro_candidates = sorted(
            [f for f in TEMP_DIR.glob("outro_*.*") if f.suffix.lower() in (".mp4", ".mov")],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        outro_info = None
        if outro_candidates and outro_candidates[0].is_file():
            outro_info = {
                "path": str(outro_candidates[0]),
                "filename": outro_candidates[0].name,
            }

        return {
            "has_clip": True,
            "path": str(active_clip),
            "filename": active_clip.name,
            "video_url": f"/temp_media/{active_clip.name}",
            "width": meta["width"],
            "height": meta["height"],
            "duration": meta["duration"],
            "fps": meta["fps"],
            "has_audio": meta["has_audio"],
            "preview_base64": b64,
            "outro": outro_info,
            "latest_export": latest_export,
        }
    except Exception as exc:
        print(f"Warning: Failed to load active session for {active_clip}: {exc}")
        return {"has_clip": False, "latest_export": latest_export}
@app.post("/api/reset-session")
async def reset_session():
    """Clears temporary downloaded/uploaded clips and snapshots from TEMP_DIR (preserving attached outro)."""
    try:
        deleted = 0
        for f in TEMP_DIR.glob("*.*"):
            if f.suffix.lower() in (".mp4", ".mov", ".mkv") and not f.name.startswith("outro_"):
                try:
                    f.unlink(missing_ok=True)
                    deleted += 1
                except Exception:
                    pass
            elif f.suffix.lower() in (".jpg", ".png", ".jpeg", ".wav", ".ass"):
                try:
                    f.unlink(missing_ok=True)
                    deleted += 1
                except Exception:
                    pass
        return {"status": "ok", "deleted_files": deleted}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))



@app.get("/api/crop-presets")
async def get_crop_presets():
    """Returns available crop presets categorized for gaming, IRL, podcasts, and casino streams."""
    return CROP_PRESETS


@app.post("/api/ingest-url")
async def ingest_stream_url(req: IngestUrlRequest):
    """Downloads a Kick, Twitch, or web stream clip via yt-dlp, detects platform & suggests preset."""
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing clip or stream URL.")

    platform = detect_stream_platform(url)
    ts = int(time.time())
    dest_path = TEMP_DIR / f"{platform}_dl_{ts}.mp4"

    try:
        active_path = download_stream_clip(
            url,
            dest_path,
            start_time=req.start_time,
            end_time=req.end_time,
            duration=req.duration,
        )
        meta = validate_media_file(active_path)

        preview_ts = 2.0
        if req.start_time is not None:
            preview_ts = max(0.5, float(req.start_time) + 0.5)

        preview_img_path = TEMP_DIR / f"snap_{ts}.jpg"
        extract_preview_frame(active_path, preview_img_path, timestamp=preview_ts)
        img = Image.open(preview_img_path)
        b64 = pil_to_base64(img)

        # AI-powered facecam and optimal layout detection
        face_layout = detect_facecam_from_image(preview_img_path)
        if face_layout.get("detected"):
            suggested_preset = face_layout.get("preset_name", "reaction_top_left")
        else:
            # Fall back to 16:9 ambient blur if no face is detected (e.g. unboxing/montage)
            suggested_preset = "ambient_blur_16_9"

        # Anti-repeat duplicate check
        dup_info = check_if_clipped(url)

        return {
            "path": str(active_path),
            "filename": active_path.name,
            "video_url": f"/temp_media/{active_path.name}",
            "platform": platform,
            "suggested_preset": suggested_preset,
            "face_layout": face_layout,
            "width": meta["width"],
            "height": meta["height"],
            "duration": meta["duration"],
            "fps": meta["fps"],
            "has_audio": meta["has_audio"],
            "preview_base64": b64,
            "is_already_clipped": dup_info.get("is_clipped", False),
            "clip_count": dup_info.get("clip_count", 0),
            "latest_output": dup_info.get("latest_output", ""),
            "last_clipped_at": dup_info.get("last_clipped_at", ""),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/ingest-file")
async def ingest_local_file(file: UploadFile = File(...)):
    """Receives uploaded local video file, validates stream integrity, and extracts preview snapshot."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected.")

    ext = Path(file.filename).suffix or ".mp4"
    ts = int(time.time())
    dest_path = TEMP_DIR / f"upload_{ts}_{file.filename}"

    try:
        with open(dest_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        meta = validate_media_file(dest_path)
        preview_img_path = TEMP_DIR / f"snap_{ts}.jpg"
        extract_preview_frame(dest_path, preview_img_path, timestamp=2.0)
        img = Image.open(preview_img_path)
        b64 = pil_to_base64(img)

        # AI-powered facecam and optimal layout detection
        face_layout = detect_facecam_from_image(preview_img_path)
        suggested_preset = face_layout.get("preset_name", "ambient_blur_16_9") if face_layout.get("detected") else "ambient_blur_16_9"

        return {
            "path": str(dest_path),
            "filename": file.filename,
            "video_url": f"/temp_media/{dest_path.name}",
            "suggested_preset": suggested_preset,
            "face_layout": face_layout,
            "width": meta["width"],
            "height": meta["height"],
            "duration": meta["duration"],
            "fps": meta["fps"],
            "has_audio": meta["has_audio"],
            "preview_base64": b64,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/upload-outro")
async def upload_outro_file(file: UploadFile = File(...)):
    """Handles optional outro branding video upload."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected.")

    ts = int(time.time())
    dest_path = TEMP_DIR / f"outro_{ts}_{file.filename}"

    try:
        with open(dest_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        meta = validate_media_file(dest_path)
        return {
            "path": str(dest_path),
            "filename": file.filename,
            "duration": meta["duration"],
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/remove-outro")
async def remove_outro():
    """Removes any stored outro videos from TEMP_DIR."""
    try:
        deleted = 0
        for f in TEMP_DIR.glob("outro_*.*"):
            try:
                f.unlink(missing_ok=True)
                deleted += 1
            except Exception:
                pass
        return {"status": "ok", "deleted_files": deleted}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/extract-frame-at")
async def extract_frame_at(req: FrameExtractRequest):
    """Extracts a frame snapshot at the user's scrubbing timestamp for precision crop framing."""
    target_path = _resolve_safe_video_path(req.video_path)
    if not target_path or not target_path.is_file():
        raise HTTPException(status_code=400, detail="Video file not found.")

    ts = int(time.time() * 1000)
    snap_path = TEMP_DIR / f"scrub_{ts}.jpg"
    try:
        extract_preview_frame(target_path, snap_path, timestamp=max(0.0, float(req.timestamp)))
        img = Image.open(snap_path)
        b64 = pil_to_base64(img)
        face_layout = detect_facecam_from_image(snap_path)
        return {
            "timestamp": req.timestamp,
            "preview_base64": b64,
            "face_layout": face_layout,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Frame extraction failed: {str(exc)}")


@app.post("/api/auto-detect-facecam")
async def auto_detect_facecam_endpoint(req: AutoDetectFacecamRequest):
    """
    AI-powered streamer webcam detection using YuNet deep neural network.
    Analyzes the video frame at the current timestamp, detects webcam corner/boundaries,
    and returns perfectly calculated non-overlapping crop coordinates and layout mode.
    """
    target_path = _resolve_safe_video_path(req.video_path) if req.video_path else None
    if not target_path or not target_path.is_file():
        candidates = sorted(
            [f for f in TEMP_DIR.glob("*.*") if f.suffix.lower() in (".mp4", ".mov", ".mkv") and not f.name.startswith("outro_")],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            target_path = candidates[0].resolve()

    if not target_path or not target_path.is_file():
        raise HTTPException(status_code=400, detail="Video file not found for auto-detection.")

    try:
        layout = detect_facecam_from_video(target_path, target_timestamp=req.timestamp)
        return layout
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Auto facecam detection failed: {str(exc)}")


@app.post("/api/upload-overlay")
async def upload_overlay_file(file: UploadFile = File(...)):
    """Handles custom cover/photo overlay upload (PNG/JPG/WEBP with transparency)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected.")

    ts = int(time.time() * 1000)
    raw_dest = TEMP_DIR / f"raw_ovl_{ts}_{file.filename}"
    clean_dest = TEMP_DIR / f"overlay_{ts}.png"

    try:
        with open(raw_dest, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        w, h = process_uploaded_overlay(raw_dest, clean_dest)
        try:
            raw_dest.unlink(missing_ok=True)
        except Exception:
            pass

        return {
            "path": str(clean_dest),
            "filename": clean_dest.name,
            "video_url": f"/temp_media/{clean_dest.name}",
            "width": w,
            "height": h,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Overlay processing failed: {str(exc)}")


@app.post("/api/generate-banner")
async def generate_banner_endpoint(req: GenerateBannerRequest):
    """Generates a high-quality promo code banner overlay using Pillow."""
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Missing banner text.")

    ts = int(time.time() * 1000)
    dest_path = TEMP_DIR / f"banner_{ts}.png"
    w = req.width or 1080
    h = req.height or 140

    try:
        generate_promo_banner(
            text=text,
            sub_text=req.sub_text,
            badge_text=req.badge_text,
            bg_color_hex=req.bg_color or "#0b0f19",
            text_color_hex=req.text_color or "#ffd700",
            accent_color_hex=req.accent_color or "#00dcff",
            width=w,
            height=h,
            output_path=dest_path,
        )
        return {
            "path": str(dest_path),
            "filename": dest_path.name,
            "video_url": f"/temp_media/{dest_path.name}",
            "width": w,
            "height": h,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Banner generation failed: {str(exc)}")


@app.post("/api/generate-hooks")
async def generate_hooks_endpoint(req: GenerateHooksRequest):
    """Generates viral high-CTR engagement hooks for Shorts / TikTok overlays."""
    hooks = generate_viral_hooks(
        clip_title=req.clip_title or "",
        streamer=req.streamer,
        category=req.category or "general",
    )
    return {"success": True, "hooks": hooks}


@app.post("/api/preview-hook-banner")
async def preview_hook_banner_endpoint(req: PreviewHookBannerRequest):
    """Renders a viral engagement hook banner for real-time live preview."""
    txt = req.text.strip() if req.text else "WAIT TILL THE END!"
    ts = int(time.time() * 1000)
    dest_path = TEMP_DIR / f"hook_preview_{ts}_{uuid.uuid4().hex[:4]}.png"
    try:
        generate_hook_banner(
            text=txt,
            style=req.style or "yellow_badge",
            width=960,
            height=160,
            output_path=dest_path,
        )
        return {
            "path": str(dest_path),
            "filename": dest_path.name,
            "url": f"/temp_media/{dest_path.name}",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Hook banner preview failed: {str(exc)}")


def _resolve_safe_video_path(path_str: Optional[str]) -> Optional[Path]:
    """Resolves video paths robustly across absolute, relative, and temp directory locations."""
    if not path_str:
        return None
    clean = str(path_str).strip().strip('"').strip("'")
    if not clean:
        return None
    p = Path(clean)
    if p.is_file():
        return p.resolve()
    # Try relative to BASE_DIR or TEMP_DIR
    p_base = (TEMP_DIR.parent / clean)
    if p_base.is_file():
        return p_base.resolve()
    p_temp = (TEMP_DIR / clean)
    if p_temp.is_file():
        return p_temp.resolve()
    p_name = (TEMP_DIR / p.name)
    if p_name.is_file():
        return p_name.resolve()
    return None


def _run_export_thread(job_id: str, payload: ExportPayload):
    """Worker thread executing FFmpeg layout stacking, faster-whisper, and outro concatenation."""
    out_filename = f"short_{int(time.time())}_{uuid.uuid4().hex[:6]}.mp4"
    out_path = OUTPUT_DIR / out_filename

    def _prog(fraction: float, msg: str):
        if job_id in export_jobs:
            export_jobs[job_id]["percent"] = fraction
            export_jobs[job_id]["message"] = msg

    crops = payload.crops or {}
    stack_mode = crops.get("stack_mode", "standard")
    gameplay_crop = {
        "x": int(float(crops.get("gx", 260))),
        "y": int(float(crops.get("gy", 80))),
        "w": int(float(crops.get("gw", 1400))),
        "h": int(float(crops.get("gh", 920))),
        "stack_mode": stack_mode,
    }
    facecam_crop = {
        "x": int(float(crops.get("cx", 1380))),
        "y": int(float(crops.get("cy", 680))),
        "w": int(float(crops.get("cw", 520))),
        "h": int(float(crops.get("ch", 380))),
        "stack_mode": stack_mode,
    }

    sub_opts = payload.subtitles or {}
    subtitle_options = {
        "font_name": str(sub_opts.get("font_name", DEFAULT_FONT_NAME)),
        "font_size": int(float(sub_opts.get("font_size", DEFAULT_FONT_SIZE))),
        "primary_color": str(sub_opts.get("primary_color", DEFAULT_PRIMARY_COLOR)),
        "highlight_color": str(sub_opts.get("highlight_color", DEFAULT_HIGHLIGHT_COLOR)),
        "y_position": int(float(sub_opts.get("y_position", DEFAULT_SUBTITLE_Y_OFFSET))),
    }

    outro_file = Path(payload.outro_path) if (payload.outro_path and Path(payload.outro_path).is_file()) else None

    # Resolve image overlays (promo code banners, cover photos, stickers)
    resolved_overlays = []
    if payload.overlays:
        for ovl in payload.overlays:
            if isinstance(ovl, dict) and ovl.get("image_path"):
                safe_img = _resolve_safe_video_path(ovl["image_path"])
                if safe_img and safe_img.is_file():
                    resolved_overlays.append({
                        "image_path": str(safe_img),
                        "x": ovl.get("x", 0),
                        "y": ovl.get("y", 0),
                        "w": ovl.get("w", 1080),
                        "h": ovl.get("h", 140),
                        "opacity": ovl.get("opacity", 1.0),
                    })

    try:
        with _RENDER_SEMAPHORE:
            final_file = processor.process_short(
                input_video_path=Path(payload.video_path),
                output_video_path=out_path,
                gameplay_crop=gameplay_crop,
                facecam_crop=facecam_crop,
                crops=crops,
                stack_mode=stack_mode,
                enable_subtitles=bool(sub_opts.get("enabled", True)),
                subtitle_options=subtitle_options,
                outro_video_path=outro_file,
                trim_start=payload.trim_start,
                trim_end=payload.trim_end,
                overlays=resolved_overlays,
                enable_anti_shadowban=bool(payload.enable_anti_shadowban if payload.enable_anti_shadowban is not None else True),
                hook_text=payload.hook_text,
                hook_options=payload.hook_options,
                progress_cb=_prog,
            )

        export_jobs[job_id].update({
            "percent": 1.0,
            "message": "Render completed successfully!",
            "done": True,
            "error": None,
            "output_path": str(final_file),
            "output_filename": final_file.name,
            "output_url": f"/outputs/{final_file.name}",
        })
        # Record into Clip History & Anti-Repeat DB
        try:
            record_clipped_short(
                source_url=payload.video_path,
                output_filename=final_file.name,
                title=getattr(payload, "title", "") or final_file.stem,
                preset=getattr(payload, "preset_name", "") or "",
                subtitle_style=str(sub_opts.get("font_name", "")),
                ai_title=getattr(payload, "ai_title", "") or "",
            )
        except Exception as _hist_err:
            print(f"NOTICE: History logging notice: {_hist_err}")
        cleanup_stale_temp_dirs(max_age_hours=2.0)
    except Exception as exc:
        export_jobs[job_id].update({
            "done": True,
            "error": str(exc),
            "message": f"Render failed: {str(exc)}",
        })


@app.post("/api/start-export")
async def start_export(payload: ExportPayload):
    """Initiates an asynchronous short generation job with smart recovery."""
    resolved_video = _resolve_safe_video_path(payload.video_path)
    if not resolved_video or not resolved_video.is_file():
        # Fall back to the most recent ingested video in TEMP_DIR if available
        candidates = sorted(
            [f for f in TEMP_DIR.glob("*.*") if f.suffix.lower() in (".mp4", ".mov", ".mkv") and not f.name.startswith("outro_")],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            resolved_video = candidates[0].resolve()
            print(f"INFO: Auto-recovered most recent clip from temp: {resolved_video}")

    if not resolved_video or not resolved_video.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"Video file not found ({payload.video_path}). Please re-ingest your clip in Step 1.",
        )

    # Use canonical absolute path
    payload.video_path = str(resolved_video)

    # Resolve outro if provided
    if payload.outro_path:
        resolved_outro = _resolve_safe_video_path(payload.outro_path)
        if resolved_outro and resolved_outro.is_file():
            payload.outro_path = str(resolved_outro)
        else:
            print(f"NOTICE: Outro video not found at {payload.outro_path}, proceeding without outro.")
            payload.outro_path = None

    job_id = str(uuid.uuid4())
    export_jobs[job_id] = {
        "percent": 0.05,
        "message": "Validating media & initializing render pipeline...",
        "done": False,
        "error": None,
        "output_path": None,
        "output_filename": None,
        "output_url": None,
    }

    t = threading.Thread(target=_run_export_thread, args=(job_id, payload), daemon=True)
    t.start()

    return {"job_id": job_id}


@app.get("/api/export-status/{job_id}")
async def get_export_status(job_id: str):
    """Retrieves current job progress and result."""
    if job_id not in export_jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    return export_jobs[job_id]


@app.get("/api/export-stream/{job_id}")
async def stream_export_progress(job_id: str):
    """Server-Sent Events (SSE) stream for real-time progress updates."""
    if job_id not in export_jobs:
        raise HTTPException(status_code=404, detail="Job not found.")

    def event_generator():
        while True:
            job = export_jobs.get(job_id)
            if not job:
                break
            payload = json.dumps(job)
            yield f"data: {payload}\n\n"
            if job.get("done"):
                break
            time.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/open-folder")
async def open_output_folder():
    """Opens the output directory in Windows File Explorer."""
    try:
        if os.name == "nt":
            os.startfile(str(OUTPUT_DIR))
        else:
            subprocess.run(["xdg-open", str(OUTPUT_DIR)])
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/outputs/{filename}")
async def serve_output_video(filename: str):
    """Streams the rendered output MP4 short video."""
    target = OUTPUT_DIR / filename
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Video not found.")
    return FileResponse(path=str(target), media_type="video/mp4", filename=filename)


# --- AI COPYWRITING ENDPOINTS (MULTI-PROVIDER & OFFLINE) ---

@app.get("/api/ai/providers")
async def get_ai_providers_endpoint():
    """Returns registry of supported AI providers for studio UI."""
    return {"providers": get_available_ai_providers()}


@app.post("/api/ai/test-connection")
async def test_ai_connection_endpoint(req: TestAiConnectionRequest):
    """Tests the AI provider connection and returns clear success or diagnostic error."""
    return test_ai_provider_connection(
        provider=req.provider or "auto",
        api_key=req.api_key,
        base_url=req.base_url,
        model=req.model,
    )


@app.post("/api/ai/generate-metadata")
async def generate_ai_metadata(req: GenerateMetadataRequest):
    """Generates 5 viral titles, 3 description variants, and hashtags using free Gemini/Groq, OpenAI, Claude, DeepSeek, Ollama, or offline engine."""
    try:
        win_str = req.win_amount
        if isinstance(win_str, (int, float)):
            win_str = f"${win_str:,.2f}".rstrip("0").rstrip(".")
        elif win_str is not None:
            win_str = str(win_str)

        if not win_str and req.multiplier:
            win_str = f"{req.multiplier}x"

        result = generate_shorts_metadata(
            clip_title=req.clip_title or "Stream Highlight Moment",
            category=req.category or "general",
            win_amount=win_str,
            streamer=req.streamer,
            transcript=req.transcript,
            promo_code=req.promo_code,
            api_key=req.api_key,
            provider=req.provider or "auto",
            model=req.model,
            base_url=req.base_url,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI generation notice: {str(exc)}")


@app.post("/api/ai/safe-metadata")
async def generate_safe_metadata_endpoint(req: SafeMetadataRequest):
    """Generates dynamic algorithm-safe metadata with rotating formulas and strictly compliant hashtags."""
    from core.ai_copywriter import generate_safe_metadata
    return generate_safe_metadata(streamer_name=req.streamer, detected_win=req.detected_win)


@app.get("/api/system/encoder-info")
async def get_system_encoder_info():
    """Returns detected hardware encoder status (NVIDIA NVENC, AMD AMF, Intel QSV, or CPU)."""
    from core.video_processor import detect_optimal_video_encoder
    info = detect_optimal_video_encoder()
    return {
        "name": info["name"],
        "type": info["type"],
        "is_gpu": info["is_gpu"],
    }


# --- YOUTUBE DIRECT SHORTS UPLOAD ENDPOINTS ---

@app.get("/api/youtube/status")
async def get_youtube_status_endpoint():
    """Returns current YouTube channel authentication status."""
    return get_youtube_auth_status()


@app.post("/api/youtube/upload-client-secrets")
async def upload_client_secrets_endpoint(file: UploadFile = File(...)):
    """Uploads OAuth client_secret.json downloaded from Google Cloud Console."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")
    try:
        content = await file.read()
        text = content.decode("utf-8")
        save_client_secrets_json(text)
        status = get_youtube_auth_status()
        return {"status": "ok", "auth_status": status}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid client_secret.json: {str(exc)}")


@app.post("/api/youtube/set-credentials")
async def set_youtube_credentials_endpoint(req: SetYouTubeCredentialsRequest):
    """Sets, changes, or replaces YouTube API Key / OAuth credentials via raw JSON or Client ID & Secret."""
    try:
        if req.raw_json and req.raw_json.strip():
            save_client_secrets_json(req.raw_json.strip())
        elif req.client_id and req.client_secret:
            save_client_id_and_secret(
                client_id=req.client_id,
                client_secret=req.client_secret,
                client_type=req.client_type or "desktop",
            )
        else:
            raise HTTPException(status_code=400, detail="Please provide either raw JSON or both Client ID and Client Secret.")
        status = get_youtube_auth_status()
        return {
            "status": "ok",
            "message": "YouTube API credentials updated successfully.",
            "auth_status": status,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/youtube/reset-credentials")
async def reset_youtube_credentials_endpoint():
    """Completely clears stored client_secret.json, all connected channels, and tokens."""
    ok = reset_youtube_credentials()
    status = get_youtube_auth_status()
    return {
        "status": "ok",
        "reset": ok,
        "auth_status": status,
        "message": "YouTube API credentials and connected accounts have been cleared.",
    }


@app.get("/api/youtube/diagnose-oauth")
async def diagnose_youtube_oauth_endpoint(request: Request):
    """Probes Google OAuth consent endpoint to detect redirect_uri_mismatch or configuration issues."""
    import urllib.request
    st = get_youtube_auth_status()
    if not st.get("has_secrets"):
        return {"status": "no_secrets", "message": "client_secret.json is not uploaded yet."}

    if st.get("authenticated"):
        return {"status": "authenticated", "channel_title": st.get("channel_title")}

    client_type = st.get("client_type", "unknown")
    client_info = {}
    try:
        with open(CLIENT_SECRETS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
            k = "web" if "web" in raw else ("installed" if "installed" in raw else list(raw.keys())[0])
            client_info = raw.get(k, {})
    except Exception:
        pass

    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/youtube/oauth2callback"
    if "0.0.0.0" in redirect_uri or "testserver" in redirect_uri:
        redirect_uri = "http://127.0.0.1:7860/api/youtube/oauth2callback"

    proj_id = client_info.get("project_id", "")
    registered_uris = client_info.get("redirect_uris", [])
    console_url = f"https://console.cloud.google.com/apis/credentials{f'?project={proj_id}' if proj_id else ''}"
    consent_url = f"https://console.cloud.google.com/apis/credentials/consent{f'?project={proj_id}' if proj_id else ''}"

    try:
        auth_info = get_youtube_authorization_url(redirect_uri=redirect_uri)
        auth_url = auth_info["auth_url"]

        probe_req = urllib.request.Request(
            auth_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"},
        )
        is_mismatch = False
        try:
            with urllib.request.urlopen(probe_req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                if "redirect_uri_mismatch" in html:
                    is_mismatch = True
        except Exception:
            # If Google blocks or errors on probe, fallback to checking local client_secret
            if client_type == "web" and redirect_uri not in registered_uris:
                is_mismatch = True

        if is_mismatch or (client_type == "web" and redirect_uri not in registered_uris):
            return {
                "status": "redirect_uri_mismatch",
                "client_type": client_type,
                "project_id": proj_id,
                "client_id": client_info.get("client_id", ""),
                "required_redirect_uri": redirect_uri,
                "console_url": console_url,
                "consent_url": consent_url,
                "message": "Google requires adding http://127.0.0.1:7860/api/youtube/oauth2callback under Authorized Redirect URIs in Google Cloud Console."
            }

        return {
            "status": "ready",
            "client_type": client_type,
            "auth_url": auth_url,
            "redirect_uri": redirect_uri,
        }
    except Exception as exc:
        return {
            "status": "probe_error",
            "client_type": client_type,
            "error": str(exc),
        }


@app.get("/api/youtube/authorize-redirect")
async def youtube_authorize_redirect(request: Request):
    """Direct redirect to Google OAuth consent screen for 100% popup-free authorization."""
    st = get_youtube_auth_status()
    if not st.get("has_secrets"):
        return HTMLResponse(
            """<!DOCTYPE html><html><body style="font-family:sans-serif;background:#0b0f19;color:#fff;text-align:center;padding:50px;">
            <h2 style="color:#ef4444;">client_secret.json missing</h2><p style="color:#94a3b8;">Please upload client_secret.json in the Shorts Studio first.</p>
            <p><a href="/" style="color:#38bdf8;">Return to Studio</a></p></body></html>""",
            status_code=400,
        )
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/youtube/oauth2callback"
    if "0.0.0.0" in redirect_uri:
        redirect_uri = redirect_uri.replace("0.0.0.0", "127.0.0.1")

    auth_info = get_youtube_authorization_url(redirect_uri=redirect_uri)
    return RedirectResponse(url=auth_info["auth_url"], status_code=307)


@app.post("/api/youtube/connect")
async def connect_youtube_endpoint(request: Request):
    """Generates real Google OAuth consent URL and initiates channel authentication."""
    try:
        st = get_youtube_auth_status()
        if not st.get("has_secrets"):
            raise HTTPException(
                status_code=400,
                detail="OAuth client_secret.json is missing. Please upload it first."
            )

        base_url = str(request.base_url).rstrip("/")
        redirect_uri = f"{base_url}/api/youtube/oauth2callback"
        if "0.0.0.0" in redirect_uri:
            redirect_uri = redirect_uri.replace("0.0.0.0", "127.0.0.1")

        auth_info = get_youtube_authorization_url(redirect_uri=redirect_uri)
        return {
            "status": "ready",
            "auth_url": auth_info["auth_url"],
            "redirect_uri": auth_info["redirect_uri"],
            "client_type": auth_info.get("client_type", "unknown"),
            "message": "Opening Google authentication window...",
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/youtube/oauth2callback", response_class=HTMLResponse)
async def youtube_oauth2_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """Handles OAuth2 redirect directly from Google consent screen."""
    if error:
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>YouTube Auth Failed</title></head>
            <body style="font-family: -apple-system, sans-serif; background: #0b0f19; color: #f8fafc; padding: 40px; text-align: center;">
                <h2 style="color: #ef4444;">YouTube Authorization Cancelled or Failed</h2>
                <p style="color: #94a3b8;">Google message: {error}</p>
                <p><a href="/" style="color: #38bdf8; text-decoration: none; font-weight: bold;">Return to Kick Shorts Studio</a></p>
            </body>
            </html>
            """,
            status_code=400,
        )

    if not code:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head><title>No Code</title></head>
            <body style="font-family: -apple-system, sans-serif; background: #0b0f19; color: #f8fafc; padding: 40px; text-align: center;">
                <h2 style="color: #ef4444;">No authorization code received</h2>
                <p><a href="/" style="color: #38bdf8;">Return to Studio</a></p>
            </body>
            </html>
            """,
            status_code=400,
        )

    try:
        base_url = str(request.base_url).rstrip("/")
        redirect_uri = f"{base_url}/api/youtube/oauth2callback"
        if "0.0.0.0" in redirect_uri:
            redirect_uri = redirect_uri.replace("0.0.0.0", "127.0.0.1")

        res = exchange_youtube_code(code, redirect_uri=redirect_uri, state=state)
        channel_name = res.get("channel_title") or "YouTube Channel"
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>YouTube Connected!</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
                    .card {{ background: #131b2e; border: 1px solid #1e293b; border-radius: 20px; padding: 36px 48px; text-align: center; max-width: 440px; box-shadow: 0 25px 50px rgba(0,0,0,0.6); }}
                    h2 {{ color: #10b981; margin: 12px 0 8px; font-size: 22px; }}
                    p {{ color: #94a3b8; font-size: 14px; line-height: 1.5; }}
                    .btn {{ display: inline-block; margin-top: 20px; padding: 10px 24px; background: #10b981; color: #fff; font-weight: bold; border-radius: 10px; text-decoration: none; font-size: 13px; cursor: pointer; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div style="font-size: 52px;">🎉</div>
                    <h2>YouTube Channel Connected!</h2>
                    <p>Successfully authenticated as <strong>{channel_name}</strong>.<br>You can safely close this tab and return to the Shorts Studio.</p>
                    <button onclick="window.close()" class="btn">Close Window</button>
                </div>
                <script>
                    setTimeout(() => {{ window.close(); }}, 3500);
                </script>
            </body>
            </html>
            """
        )
    except Exception as exc:
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Connection Failed</title></head>
            <body style="font-family: -apple-system, sans-serif; background: #0b0f19; color: #f8fafc; padding: 40px; text-align: center;">
                <h2 style="color: #ef4444;">Exchange Failed</h2>
                <p style="color: #94a3b8;">{str(exc)}</p>
                <p><a href="/" style="color: #38bdf8;">Back to Studio</a></p>
            </body>
            </html>
            """,
            status_code=500,
        )


@app.post("/api/youtube/exchange-code")
async def manual_exchange_code_endpoint(req: ExchangeCodeRequest, request: Request):
    """Manually exchanges code or redirect URL pasted by the user."""
    try:
        base_url = str(request.base_url).rstrip("/")
        redirect_uri = req.redirect_uri or f"{base_url}/api/youtube/oauth2callback"
        if "0.0.0.0" in redirect_uri:
            redirect_uri = redirect_uri.replace("0.0.0.0", "127.0.0.1")
        return exchange_youtube_code(req.code, redirect_uri=redirect_uri)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/youtube/accounts")
async def get_youtube_accounts_endpoint():
    """Returns list of all connected YouTube channels."""
    return {"accounts": list_youtube_accounts()}


@app.post("/api/youtube/disconnect-account")
async def disconnect_youtube_account_endpoint(req: DisconnectAccountRequest):
    """Disconnects a specific YouTube channel while keeping other channels intact."""
    removed = disconnect_youtube_account(req.channel_id)
    return {"status": "ok", "removed": removed, "auth_status": get_youtube_auth_status()}


@app.post("/api/youtube/disconnect")
async def disconnect_youtube_endpoint():
    """Disconnects all YouTube channels by clearing stored OAuth tokens."""
    ok = disconnect_youtube()
    return {"status": "ok", "disconnected": ok}


def _run_youtube_upload_thread(job_id: str, req: YouTubeUploadRequest):
    def _prog(frac: float, msg: str):
        if job_id in youtube_upload_jobs:
            youtube_upload_jobs[job_id]["percent"] = frac
            youtube_upload_jobs[job_id]["message"] = msg

    try:
        resolved_video = _resolve_safe_video_path(req.video_path)
        if not resolved_video or not resolved_video.is_file():
            candidates = sorted(OUTPUT_DIR.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True)
            if candidates:
                resolved_video = candidates[0]
            else:
                raise FileNotFoundError("Video to upload not found.")

        result = upload_shorts_video(
            video_path=resolved_video,
            title=req.title,
            description=req.description,
            tags=req.tags,
            privacy_status=req.privacy_status or "public",
            made_for_kids=bool(req.made_for_kids),
            channel_id=req.channel_id,
            channel_ids=req.channel_ids,
            progress_cb=_prog,
        )

        youtube_upload_jobs[job_id].update({
            "percent": 1.0,
            "message": "Uploaded to YouTube Shorts successfully!",
            "done": True,
            "error": None,
            "video_id": result["video_id"],
            "shorts_url": result["shorts_url"],
            "watch_url": result["watch_url"],
            "title": result["title"],
            "results": result.get("results", []),
            "total_uploaded": result.get("total_uploaded", 1),
        })
    except Exception as exc:
        youtube_upload_jobs[job_id].update({
            "done": True,
            "error": str(exc),
            "message": f"YouTube upload failed: {str(exc)}",
        })


@app.post("/api/youtube/upload-video")
async def start_youtube_upload_endpoint(req: YouTubeUploadRequest):
    """Initiates background upload of the short video to YouTube Shorts."""
    if not req.title or not req.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty.")

    if req.video_path:
        resolved_video = _resolve_safe_video_path(req.video_path)
        if not resolved_video or not resolved_video.is_file():
            raise HTTPException(status_code=400, detail=f"Video file not found: {req.video_path}")
    else:
        candidates = sorted(OUTPUT_DIR.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True)
        if not candidates:
            raise HTTPException(status_code=400, detail="No exported video available to upload.")

    job_id = str(uuid.uuid4())
    youtube_upload_jobs[job_id] = {
        "percent": 0.05,
        "message": "Initializing YouTube upload...",
        "done": False,
        "error": None,
        "video_id": None,
        "shorts_url": None,
        "watch_url": None,
    }
    t = threading.Thread(target=_run_youtube_upload_thread, args=(job_id, req), daemon=True)
    t.start()
    return {"job_id": job_id}


@app.get("/api/youtube/upload-status/{job_id}")
async def get_youtube_upload_status(job_id: str):
    """Retrieves progress and results of a YouTube Shorts upload job."""
    if job_id not in youtube_upload_jobs:
        raise HTTPException(status_code=404, detail="Upload job not found.")
    return youtube_upload_jobs[job_id]


@app.get("/api/status")
@app.get("/api/motion/status")
async def get_system_status():
    """Returns server and hardware encoder status."""
    encoder, enc_args = detect_best_ffmpeg_encoder()
    voices = get_available_voices()
    outputs_count = len(list(OUTPUT_DIR.glob("*.mp4")))
    return {
        "status": "online",
        "port": 7860,
        "encoder": encoder,
        "encoder_args": enc_args,
        "available_voices": len(voices),
        "total_renders": outputs_count,
    }


# ==============================================================================
# 📚 CLIP HISTORY & ANTI-REPEAT DATABASE ENDPOINTS
# ==============================================================================
class CheckHistoryRequest(BaseModel):
    url: str


@app.post("/api/history/check")
async def check_history_endpoint(req: CheckHistoryRequest):
    """Checks if a URL or clip ID has already been processed to prevent accidental duplicate clips."""
    return check_if_clipped(req.url)


@app.get("/api/history")
@app.get("/api/history/list")
async def get_history_endpoint(
    search: Optional[str] = "",
    platform: Optional[str] = "all",
    page: Optional[int] = 1,
    page_size: Optional[int] = 30,
):
    """Returns paginated history of all previously processed clips with metadata and outputs."""
    return list_clip_history(search=search or "", platform=platform or "all", page=page or 1, page_size=page_size or 30)


@app.delete("/api/history/{item_id}")
async def delete_history_endpoint(item_id: str):
    """Deletes an item from clip history."""
    ok = delete_history_item(item_id)
    return {"success": ok}


@app.post("/api/history/clear")
async def clear_history_endpoint():
    """Clears all records in clip history."""
    count = clear_all_history()
    return {"success": True, "deleted_count": count}


# ==============================================================================
# ⚡ MOTION EXPLAINER STUDIO - 2.5D VIRAL SHORTS ENGINE
# ==============================================================================
class ScriptGenRequest(BaseModel):
    topic: str
    product_name: Optional[str] = "SmartApp"
    category: Optional[str] = "Security / SaaS"
    preset_id: Optional[str] = None


class VoicePreviewRequest(BaseModel):
    text: str
    voice: Optional[str] = "en-US-ChristopherNeural"
    rate: Optional[str] = "+0%"


class ScenePreviewRequest(BaseModel):
    scene: Dict[str, Any]
    progress: Optional[float] = 0.5
    global_time: Optional[float] = 1.0
    width: Optional[int] = 540
    height: Optional[int] = 960


class RenderShortRequest(BaseModel):
    script_data: Dict[str, Any]
    voice_id: Optional[str] = "en-US-ChristopherNeural"
    custom_audio_path: Optional[str] = None
    fps: Optional[int] = 30
    include_sfx: Optional[bool] = True
    include_music: Optional[bool] = True
    voice_volume: Optional[float] = 1.0
    music_volume: Optional[float] = 0.18
    sfx_volume: Optional[float] = 0.8


MOTION_RENDER_JOBS: Dict[str, Dict[str, Any]] = {}
CURRENT_DIR = Path(__file__).parent.resolve()


def _resolve_motion_scene_paths(scene: Dict[str, Any]) -> Dict[str, Any]:
    """Resolves web URLs to absolute filesystem paths for local assets."""
    s = dict(scene)
    for key in ["custom_image_path", "custom_screenshot_path", "custom_logo_path", "custom_skin_image_path"]:
        val = s.get(key)
        if val and isinstance(val, str) and val.startswith("/assets/"):
            local = CURRENT_DIR / val.lstrip("/")
            if local.exists():
                s[key] = str(local)

    if "items" in s and isinstance(s["items"], list):
        resolved_items = []
        for it in s["items"]:
            it_c = dict(it)
            for ikey in ["image_path", "custom_image_path"]:
                ival = it_c.get(ikey)
                if ival and isinstance(ival, str) and ival.startswith("/assets/"):
                    ilocal = CURRENT_DIR / ival.lstrip("/")
                    if ilocal.exists():
                        it_c[ikey] = str(ilocal)
            resolved_items.append(it_c)
        s["items"] = resolved_items
    return s


@app.post("/api/motion/upload")
@app.post("/api/upload")
async def upload_motion_asset(file: UploadFile = File(...)):
    """Uploads custom scene image, screenshot, logo, or audio/voiceover track."""
    ext = Path(file.filename).suffix.lower()
    allowed_exts = [".png", ".jpg", ".jpeg", ".webp", ".mp3", ".wav", ".m4a", ".aac"]
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported file type {ext}. Supported: {allowed_exts}")

    clean_stem = re.sub(r"[^\w\-]", "_", Path(file.filename).stem)[:30]
    unique_name = f"upload_{int(time.time())}_{clean_stem}{ext}"
    dest_path = UPLOADS_DIR / unique_name

    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)

    duration = None
    if ext in [".mp3", ".wav", ".m4a", ".aac"]:
        duration = probe_audio_duration(str(dest_path))

    return {
        "success": True,
        "filename": unique_name,
        "url": f"/assets/uploads/{unique_name}",
        "local_path": str(dest_path),
        "duration": duration,
        "is_audio": ext in [".mp3", ".wav", ".m4a", ".aac"],
    }


@app.get("/api/motion/presets")
@app.get("/api/presets")
async def get_motion_presets():
    """Returns list of pre-configured viral motion short templates."""
    return {"presets": get_available_presets()}


@app.get("/api/motion/default-items/{scene_num}")
@app.get("/api/default-items/{scene_num}")
async def get_motion_default_items(scene_num: int, code: str = "MESTO300"):
    """Returns default on-screen items/layers for a specific scene."""
    items = get_tradeit_default_items(scene_num, code=code)
    return {"scene_num": scene_num, "items": items}


@app.get("/api/motion/asset-presets")
@app.get("/api/asset-presets")
async def get_motion_asset_presets():
    """Returns available asset presets for easy 1-click addition into scenes."""
    presets = [
        {"id": "tradeit_homepage_card.jpg", "name": "TradeIt Homepage Card", "type": "card", "category": "tradeit"},
        {"id": "tradeit_dropdown_menu.jpg", "name": "TradeIt Dropdown Menu", "type": "card", "category": "tradeit"},
        {"id": "tradeit_modal_raw.jpg", "name": "TradeIt Redeem Modal (Live Typing)", "type": "card", "category": "tradeit"},
        {"id": "tradeit_header_toast.jpg", "name": "Balance Header Toast Bar", "type": "card", "category": "tradeit"},
        {"id": "tradeit_item_grid.jpg", "name": "CS2 Skins Selection Grid", "type": "card", "category": "tradeit"},
        {"id": "tradeit_floating_skins.jpg", "name": "3 Floating Dream Weapons", "type": "card", "category": "tradeit"},
        {"id": "steam_proceed_stop.jpg", "name": "Steam Proceed & STOP Button", "type": "card", "category": "steam"},
        {"id": "missing_item_bar.jpg", "name": "Trade Missing Item Strip", "type": "card", "category": "steam"},
        {"id": "steam_inventory_5x5.jpg", "name": "Steam 5x5 Inventory Grid", "type": "card", "category": "steam"},
        {"id": "cs2_trade_badge.jpg", "name": "CS2 Handshake Badge", "type": "badge", "category": "badge"},
        {"id": "prohibition_badge.jpg", "name": "Prohibition Sign Badge", "type": "badge", "category": "badge"},
    ]
    return {"asset_presets": presets}


@app.get("/api/motion/voices")
@app.get("/api/voices")
async def get_motion_voices():
    """Returns list of studio-grade neural voices."""
    return {"voices": get_available_voices()}


@app.post("/api/motion/generate-script")
@app.post("/api/generate-script")
async def generate_motion_script_endpoint(req: ScriptGenRequest):
    """Generates 5-scene viral motion explainer script."""
    if req.preset_id:
        for p in VIRAL_PRESETS:
            if p["id"] == req.preset_id:
                return {"script": p}

    script = generate_motion_script_ai(
        topic_or_url=req.topic,
        product_name=req.product_name or "SmartApp",
        category=req.category or "SaaS / Security",
    )
    return {"script": script}


@app.post("/api/motion/preview-voice")
@app.post("/api/preview-voice")
async def preview_motion_voice(req: VoicePreviewRequest):
    """Synthesizes preview audio clip for narrator voice testing."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Voice text cannot be empty.")
    try:
        res = synthesize_speech(req.text, voice=req.voice or "en-US-ChristopherNeural")
        rel_path = Path(res["audio_path"]).relative_to(CURRENT_DIR)
        web_url = "/" + str(rel_path).replace("\\", "/")
        return {
            "success": True,
            "audio_url": web_url,
            "duration": res["duration"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice synthesis failed: {str(e)}")


@app.post("/api/motion/preview-scene")
@app.post("/api/preview-scene")
def preview_motion_scene(req: ScenePreviewRequest):
    """
    Renders an instantaneous preview frame for the selected scene
    and returns a preview WebP image URL.
    Master render is always evaluated at 1080x1920 to guarantee 100% exact
    framing, typography, card scale, and margins identical to the final video export.
    """
    try:
        resolved_scene = _resolve_motion_scene_paths(req.scene)
        # Always render on canonical 1080x1920 canvas to maintain exact framing & proportions
        img = render_motion_frame(
            scene=resolved_scene,
            scene_progress=req.progress if req.progress is not None else 0.5,
            global_time=req.global_time or 1.2,
            width=1080,
            height=1920,
        )

        # Downscale composited frame for rapid UI transfer if requested
        req_w = req.width or 540
        req_h = req.height or 960
        if req_w and req_h and (req_w != 1080 or req_h != 1920):
            img = img.resize((req_w, req_h), resample=Image.BILINEAR)

        preview_id = f"preview_{int(time.time() * 1000)}.webp"
        preview_path = ASSETS_CACHE_DIR / preview_id
        rgb_img = img.convert("RGB")
        rgb_img.save(str(preview_path), format="WEBP", quality=86)

        web_url = f"/assets/cache/{preview_id}"
        return {"success": True, "preview_url": web_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scene preview failed: {str(e)}")


@app.post("/api/motion/render-short")
@app.post("/api/render-short")
async def start_motion_render_job(req: RenderShortRequest):
    """Initiates an asynchronous 1080x1920 video render job and returns job ID for SSE progress tracking."""
    job_id = str(uuid.uuid4())[:8]
    MOTION_RENDER_JOBS[job_id] = {
        "status": "queued",
        "progress": 0.02,
        "message": "Initializing render pipeline...",
        "result": None,
        "error": None,
    }

    def _execute():
        def _prog_cb(pct: float, msg: str):
            if job_id in MOTION_RENDER_JOBS:
                MOTION_RENDER_JOBS[job_id]["progress"] = round(pct, 3)
                MOTION_RENDER_JOBS[job_id]["message"] = msg
                MOTION_RENDER_JOBS[job_id]["status"] = "processing"

        try:
            # Resolve all file paths for uploaded assets
            script_copy = dict(req.script_data)
            script_copy["scenes"] = [_resolve_motion_scene_paths(s) for s in req.script_data.get("scenes", [])]

            # Resolve custom voiceover / audio track
            c_audio = req.custom_audio_path or script_copy.get("custom_audio_path")
            if c_audio and isinstance(c_audio, str) and c_audio.startswith("/assets/"):
                local_audio = CURRENT_DIR / c_audio.lstrip("/")
                if local_audio.exists():
                    c_audio = str(local_audio)
            if c_audio:
                script_copy["custom_audio_path"] = c_audio

            res = render_motion_explainer_short(
                script_data=script_copy,
                voice_id=req.voice_id or "en-US-ChristopherNeural",
                fps=req.fps or 30,
                include_sfx=req.include_sfx,
                include_music=req.include_music,
                voice_volume=req.voice_volume if req.voice_volume is not None else 1.0,
                music_volume=req.music_volume if req.music_volume is not None else 0.18,
                sfx_volume=req.sfx_volume if req.sfx_volume is not None else 0.8,
                progress_callback=_prog_cb,
            )
            out_filename = res["video_filename"]
            
            # Record into clip history as motion short
            try:
                record_clipped_short(
                    source_url=f"motion://{req.script_data.get('theme', 'explainer')}/{req.script_data.get('promocode', 'PROMO')}",
                    output_filename=out_filename,
                    title=req.script_data.get("name") or req.script_data.get("topic") or "Motion Explainer Short",
                    channel="Motion Studio",
                    duration=res.get("duration", 0.0),
                    preset="motion_2.5d",
                    ai_title=req.script_data.get("name", ""),
                )
            except Exception as _h_err:
                print(f"NOTICE: Motion short history logging: {_h_err}")

            MOTION_RENDER_JOBS[job_id]["status"] = "completed"
            MOTION_RENDER_JOBS[job_id]["progress"] = 1.0
            MOTION_RENDER_JOBS[job_id]["message"] = "Short video exported successfully!"
            MOTION_RENDER_JOBS[job_id]["result"] = {
                "video_url": f"/outputs/{out_filename}",
                "filename": out_filename,
                "duration": res["duration"],
                "fps": res["fps"],
                "resolution": res["resolution"],
            }
        except Exception as e:
            MOTION_RENDER_JOBS[job_id]["status"] = "failed"
            MOTION_RENDER_JOBS[job_id]["error"] = str(e)
            MOTION_RENDER_JOBS[job_id]["message"] = f"Render failed: {str(e)}"

    thread = threading.Thread(target=_execute, daemon=True)
    thread.start()

    return {"job_id": job_id, "status": "queued"}


@app.get("/api/motion/render-stream/{job_id}")
@app.get("/api/render-stream/{job_id}")
async def stream_motion_render_progress(job_id: str):
    """Server-Sent Events (SSE) endpoint providing live 60fps/real-time progress feedback."""
    async def event_generator():
        while True:
            job = MOTION_RENDER_JOBS.get(job_id)
            if not job:
                yield f"data: {json.dumps({'status': 'not_found', 'progress': 0})}\n\n"
                break

            data = {
                "status": job["status"],
                "progress": job["progress"],
                "message": job["message"],
                "result": job.get("result"),
                "error": job.get("error"),
            }
            yield f"data: {json.dumps(data)}\n\n"

            if job["status"] in ("completed", "failed"):
                break
            await asyncio.sleep(0.4)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/motion/outputs")
@app.get("/api/outputs")
async def list_motion_outputs():
    """Lists all previously rendered shorts with metadata."""
    videos = []
    # Search both OUTPUT_DIR and ASSETS_CACHE_DIR / OUTPUTS
    search_dirs = [OUTPUT_DIR, CURRENT_DIR / "outputs"]
    seen_names = set()
    for sdir in search_dirs:
        if not sdir.exists():
            continue
        for f in sdir.glob("*.mp4"):
            if f.name in seen_names:
                continue
            seen_names.add(f.name)
            try:
                stat = f.stat()
                videos.append({
                    "filename": f.name,
                    "url": f"/outputs/{f.name}",
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                })
            except Exception:
                pass
    videos.sort(key=lambda x: x["created_at"], reverse=True)
    return {"videos": videos}


@app.delete("/api/motion/outputs/{filename}")
@app.delete("/api/outputs/{filename}")
async def delete_motion_output(filename: str):
    """Deletes an output video."""
    target1 = OUTPUT_DIR / filename
    target2 = CURRENT_DIR / "outputs" / filename
    deleted = False
    for t in [target1, target2]:
        if t.exists() and t.suffix.lower() == ".mp4":
            t.unlink()
            deleted = True
    if deleted:
        return {"success": True, "deleted": filename}
    raise HTTPException(status_code=404, detail="File not found")


# ============================================================================
# FUSED ENGINE: FACELESS SHORTS (MoneyPrinterTurbo) & VIRALITY SCORING (SupoClip)
# ============================================================================

class FacelessScriptRequest(BaseModel):
    topic: str
    provider: str = "auto"
    model: Optional[str] = None
    api_key: Optional[str] = None
    include_affiliate: bool = True
    promo_code: str = "mesto300"


class FacelessRenderRequest(BaseModel):
    script_data: Dict[str, Any]
    voice_id: str = "en-US-ChristopherNeural"
    subtitle_preset: str = "submagic_yellow"
    output_filename: Optional[str] = None
    pexels_api_key: Optional[str] = None
    pixabay_api_key: Optional[str] = None
    bgm_volume: float = 0.14


class ViralityScoreRequest(BaseModel):
    transcript: Any
    provider: str = "auto"
    model: Optional[str] = None
    api_key: Optional[str] = None
    target_clip_duration: float = 35.0


FACELESS_RENDER_JOBS: Dict[str, Dict[str, Any]] = {}


@app.get("/api/faceless/voices")
def get_faceless_voices():
    """Returns available Edge-TTS and ElevenLabs voices."""
    return {"voices": get_available_voices()}


@app.get("/api/faceless/presets")
def get_subtitle_presets():
    """Returns available SupoClip/Submagic/MrBeast animated subtitle presets."""
    return {"presets": SUBTITLE_PRESETS}


@app.post("/api/faceless/generate-script")
def api_generate_faceless_script(req: FacelessScriptRequest):
    """Generates a viral 4-beat short-form script using AI or offline fallback."""
    try:
        script = generate_faceless_script(
            topic=req.topic,
            provider=req.provider,
            model=req.model,
            api_key=req.api_key,
            include_affiliate=req.include_affiliate,
            promo_code=req.promo_code
        )
        return {"success": True, "script": script}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/faceless/render")
def api_render_faceless_short(req: FacelessRenderRequest):
    """Asynchronously renders a full faceless short with stock B-roll, voiceover, and bouncing ASS subtitles."""
    job_id = f"job_faceless_{uuid.uuid4().hex[:8]}"
    FACELESS_RENDER_JOBS[job_id] = {
        "status": "queued",
        "progress": 0.05,
        "message": "Initializing Faceless Short pipeline...",
        "result": None,
        "error": None,
    }

    def _execute():
        try:
            FACELESS_RENDER_JOBS[job_id]["status"] = "processing"
            FACELESS_RENDER_JOBS[job_id]["progress"] = 0.15
            FACELESS_RENDER_JOBS[job_id]["message"] = "Synthesizing neural voiceover & aligning words..."

            out_filename = req.output_filename
            if not out_filename:
                t_slug = re.sub(r"[^a-zA-Z0-9]", "_", req.script_data.get("title", "short"))[:18]
                out_filename = f"faceless_{t_slug}_{int(time.time())}.mp4"

            FACELESS_RENDER_JOBS[job_id]["progress"] = 0.40
            FACELESS_RENDER_JOBS[job_id]["message"] = "Fetching B-Roll stock video & generating dynamic canvas..."

            res = render_faceless_short(
                script_data=req.script_data,
                voice_id=req.voice_id,
                subtitle_preset=req.subtitle_preset,
                output_filename=out_filename,
                pexels_api_key=req.pexels_api_key,
                pixabay_api_key=req.pixabay_api_key,
                bgm_volume=req.bgm_volume
            )

            # Record in clip history
            try:
                record_clipped_short(
                    source_url="faceless://moneyprinter",
                    output_filename=out_filename,
                    title=res.get("title", "Faceless AI Short"),
                    channel="Faceless Studio",
                    duration=res.get("duration", 0.0),
                    preset="moneyprinter_faceless",
                    ai_title=res.get("title", ""),
                )
            except Exception:
                pass

            FACELESS_RENDER_JOBS[job_id]["status"] = "completed"
            FACELESS_RENDER_JOBS[job_id]["progress"] = 1.0
            FACELESS_RENDER_JOBS[job_id]["message"] = "Faceless Short exported successfully!"
            FACELESS_RENDER_JOBS[job_id]["result"] = {
                "video_url": f"/outputs/{out_filename}",
                "filename": out_filename,
                "duration": res["duration"],
                "render_time_seconds": res.get("render_time_seconds", 0),
            }
        except Exception as exc:
            FACELESS_RENDER_JOBS[job_id]["status"] = "failed"
            FACELESS_RENDER_JOBS[job_id]["error"] = str(exc)
            FACELESS_RENDER_JOBS[job_id]["message"] = f"Render failed: {str(exc)}"

    thread = threading.Thread(target=_execute, daemon=True)
    thread.start()

    return {"job_id": job_id, "status": "queued"}


@app.get("/api/faceless/render-stream/{job_id}")
async def stream_faceless_render_progress(job_id: str):
    """Server-Sent Events (SSE) endpoint providing live progress feedback for faceless video generation."""
    async def event_generator():
        while True:
            job = FACELESS_RENDER_JOBS.get(job_id)
            if not job:
                yield f"data: {json.dumps({'status': 'not_found', 'progress': 0})}\n\n"
                break

            data = {
                "status": job["status"],
                "progress": job["progress"],
                "message": job["message"],
                "result": job.get("result"),
                "error": job.get("error"),
            }
            yield f"data: {json.dumps(data)}\n\n"

            if job["status"] in ("completed", "failed"):
                break
            await asyncio.sleep(0.4)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/virality/score")
def api_score_virality(req: ViralityScoreRequest):
    """SupoClip-style AI transcript virality scoring and highlight finder."""
    try:
        res = score_stream_transcript(
            transcript_text_or_segments=req.transcript,
            provider=req.provider,
            model=req.model,
            api_key=req.api_key,
            target_clip_duration=req.target_clip_duration
        )
        return res
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/broll/search")
def api_search_broll(query: str, pexels_key: Optional[str] = None, pixabay_key: Optional[str] = None):
    """Search stock footage from Pexels and Pixabay."""
    results = []
    if pexels_key or os.getenv("PEXELS_API_KEY"):
        results.extend(search_pexels_videos(query, per_page=4, api_key=pexels_key))
    if pixabay_key or os.getenv("PIXABAY_API_KEY"):
        results.extend(search_pixabay_videos(query, per_page=4, api_key=pixabay_key))
    return {"query": query, "results": results}


# ============================================================================
# 🚀 24/7 AUTOPILOT FACTORY (A TO Z AUTOMATION)
# ============================================================================

class AutopilotStartRequest(BaseModel):
    interval_minutes: int = 180
    daily_quota: int = 4
    auto_upload: bool = False
    voice_id: str = "en-US-ChristopherNeural"
    subtitle_preset: str = "submagic_yellow"


class AutopilotRunOnceRequest(BaseModel):
    topic: Optional[str] = None
    auto_upload: bool = False


@app.get("/api/autopilot/status")
def api_get_autopilot_status():
    """Returns live 24/7 Autopilot status, queue, and logs."""
    return autopilot.get_status()


@app.post("/api/autopilot/start")
def api_start_autopilot(req: AutopilotStartRequest):
    """Activates the 24/7 background autopilot daemon."""
    return autopilot.start(
        interval_minutes=req.interval_minutes,
        daily_quota=req.daily_quota,
        auto_upload=req.auto_upload,
        voice_id=req.voice_id,
        subtitle_preset=req.subtitle_preset
    )


@app.post("/api/autopilot/stop")
def api_stop_autopilot():
    """Stops the 24/7 background autopilot daemon."""
    return autopilot.stop()


@app.post("/api/autopilot/run-once")
def api_run_autopilot_once(req: AutopilotRunOnceRequest):
    """Triggers an immediate A-to-Z production cycle in a background worker."""
    job_id = f"job_auto_{uuid.uuid4().hex[:8]}"
    FACELESS_RENDER_JOBS[job_id] = {
        "status": "queued",
        "progress": 0.05,
        "message": "Starting A-to-Z Autopilot cycle...",
        "result": None,
        "error": None,
    }

    def _execute():
        def _prog(pct, msg):
            FACELESS_RENDER_JOBS[job_id]["progress"] = pct
            FACELESS_RENDER_JOBS[job_id]["message"] = msg

        try:
            FACELESS_RENDER_JOBS[job_id]["status"] = "processing"
            res = autopilot.run_single_faceless_cycle(
                topic=req.topic,
                auto_upload=req.auto_upload,
                progress_cb=_prog
            )
            FACELESS_RENDER_JOBS[job_id]["status"] = "completed"
            FACELESS_RENDER_JOBS[job_id]["progress"] = 1.0
            FACELESS_RENDER_JOBS[job_id]["message"] = "Autopilot cycle complete!"
            FACELESS_RENDER_JOBS[job_id]["result"] = res
        except Exception as exc:
            FACELESS_RENDER_JOBS[job_id]["status"] = "failed"
            FACELESS_RENDER_JOBS[job_id]["error"] = str(exc)
            FACELESS_RENDER_JOBS[job_id]["message"] = f"Autopilot failed: {str(exc)}"

    thread = threading.Thread(target=_execute, daemon=True)
    thread.start()

    return {"job_id": job_id, "status": "queued"}


def open_browser_delayed(url: str, delay_sec: float = 1.0):
    """Opens browser after server starts."""
    def _open():
        time.sleep(delay_sec)
        webbrowser.open(url)
    threading.Thread(target=_open, daemon=True).start()


if __name__ == "__main__":
    import uvicorn
    server_url = "http://127.0.0.1:7860"
    print("=" * 65)
    print("  KICK CASINO STREAM-TO-SHORTS AUTOMATION STUDIO (v2.0)")
    print(f"  Server URL: {server_url}")
    print("=" * 65)

    try:
        open_browser_delayed(server_url, delay_sec=1.2)
    except Exception as exc:
        print(f"Notice: Failed to launch browser automatically: {exc}")

    print("INFO: Starting Uvicorn studio server on http://127.0.0.1:7860...")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=7860,
        log_level="info",
        access_log=True,
    )

