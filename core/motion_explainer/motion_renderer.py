"""
High-Performance Motion Graphics Video Rendering Engine
Assembles 1080x1920 60fps/30fps vertical Shorts with:
- Dark grid ambient background with breathing radial light
- Easing-driven 2.5D element animations (floating cards, newspaper folds, rising smartphone)
- Animated metric progress bars (0% -> target %)
- Kinetic typography with multi-colored word highlights
- Multi-track audio mix: Neural TTS Voiceover + ducked ambient music + synchronized SFX
- FFmpeg hardware-accelerated encoding (NVENC / QSV / libx264)
"""
import os
import sys
import math
import time
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Tuple
from PIL import Image

from core.motion_explainer.asset_generator import (
    create_dark_grid_background,
    create_floating_card,
    create_newspaper_clipping,
    create_smartphone_app_mockup,
    create_skin_item_card,
    create_steam_vs_tradeit_comparison,
    create_promocode_voucher_card,
    render_kinetic_caption,
)
from core.motion_explainer.tradeit_assets import (
    render_tradeit_scene_frame,
    render_custom_image_card,
    make_rounded_card,
    get_tradeit_background,
)
from core.motion_explainer.kinetic_transitions import composite_kinetic_element, compute_kinetic_transform
from core.motion_explainer.voice_engine import synthesize_speech, probe_audio_duration
from core.motion_explainer.sfx_library import ensure_sfx_library
from core.config import OUTPUT_DIR as GLOBAL_OUTPUT_DIR

OUTPUTS_DIR = GLOBAL_OUTPUT_DIR
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# EASING CURVES FOR ORGANIC MOTION GRAPHICS
# ==============================================================================
def ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - max(0.0, min(1.0, t))) ** 3


def ease_out_back(t: float, s: float = 1.70158) -> float:
    t = max(0.0, min(1.0, t)) - 1.0
    return t * t * ((s + 1) * t + s) + 1.0


def ease_in_out_sine(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return -(math.cos(math.pi * t) - 1.0) / 2.0


def detect_best_ffmpeg_encoder() -> Tuple[str, List[str]]:
    """Detects and tests available hardware video encoders (MediaFoundation, NVENC, QSV, libx264)."""
    candidates = [
        ("h264_mf", ["-b:v", "6M"]),
        ("h264_nvenc", ["-preset", "p4", "-cq", "23"]),
        ("h264_qsv", ["-preset", "medium", "-global_quality", "23"]),
        ("libx264", ["-preset", "veryfast", "-crf", "22"]),
    ]
    for enc, args in candidates:
        try:
            cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=10", "-c:v", enc, *args, "-f", "null", "-"]
            res = subprocess.run(cmd, capture_output=True, timeout=3)
            if res.returncode == 0:
                return enc, args
        except Exception:
            continue
    return "libx264", ["-preset", "veryfast", "-crf", "22"]


# ==============================================================================
# RENDER SINGLE COMPOSITE FRAME
# ==============================================================================
def render_motion_frame(
    scene: Dict[str, Any],
    scene_progress: float,  # 0.0 to 1.0 within this scene
    global_time: float,     # seconds from start of video
    width: int = 1080,
    height: int = 1920,
) -> Image.Image:
    """Renders a single 1080x1920 frame for the current scene with smooth easing, multi-directional kinetic entries, and 2.5D element transforms."""
    # Check if scene uses authentic TradeIt legacy template or has explicit customizable multi-items
    theme = scene.get("theme")
    v_type = scene.get("visual_type", "card")
    custom_img = scene.get("custom_image_path") or scene.get("custom_screenshot_path")
    custom_dir = scene.get("custom_image_direction") or scene.get("direction", "left")

    if (theme == "tradeit_legacy") or scene.get("items"):
        return render_tradeit_scene_frame(
            scene_num=int(scene.get("scene_num", 1)),
            scene_progress=scene_progress,
            global_time=global_time,
            code=str(scene.get("promocode", "MESTO300")),
            width=width,
            height=height,
            custom_image_path=custom_img,
            custom_image_direction=custom_dir,
            items=scene.get("items"),
        )

    # 1. Background with ambient glow or authentic living TradeIt background
    if theme == "tradeit" or scene.get("promocode"):
        bg = get_tradeit_background(width=width, height=height, time_sec=global_time)
    else:
        grid_offset = global_time * 8.0
        bg = create_dark_grid_background(width=width, height=height, offset_x=grid_offset, offset_y=grid_offset * 0.5)

    custom_scale = float(scene.get("asset_scale", 1.0))
    y_offset = int(scene.get("asset_y_offset", 0))

    # Continuous subtle 3D camera push-in (Ken Burns effect)
    camera_zoom = 1.0 + 0.035 * scene_progress

    # Multi-directional entry logic
    # Default alternating direction per scene if not explicitly specified:
    # Scene 1: zoom (hook punch directly in the viewer's face)
    # Scene 2: left (smooth kinetic glide from left)
    # Scene 3: top (heavy slam down from top)
    # Scene 4: right (sleek glide from right)
    # Scene 5: bottom (solid rise up from bottom)
    # Scene 6: zoom (grand outro punch)
    DEFAULT_DIRECTIONS = ["zoom", "left", "top", "right", "bottom", "diagonal_tl", "diagonal_tr"]
    scene_num = int(scene.get("scene_num", 1))
    fallback_dir = DEFAULT_DIRECTIONS[(scene_num - 1) % len(DEFAULT_DIRECTIONS)]
    direction = scene.get("direction") or scene.get("entry_direction") or fallback_dir
    exit_direction = scene.get("exit_direction") or direction

    slide_dist = int(scene.get("slide_distance", 850))
    max_tilt = float(scene.get("max_tilt_deg", 4.0 if direction in ("left", "right", "diagonal_tl", "diagonal_tr") else 1.5))

    target_cx = width // 2
    target_cy = int(height * 0.48) + y_offset

    visual_element: Optional[Image.Image] = None
    bob_amp = 10.0
    bob_spd = 2.4

    # 2. Render and composite visual element based on scene type
    custom_img_path = custom_img if (custom_img and os.path.exists(str(custom_img))) else scene.get("image_path")
    if v_type in ("image", "custom_image", "custom_card", "crop") or (custom_img_path and os.path.exists(str(custom_img_path)) and v_type not in ("skin", "comparison", "newspaper", "phone", "voucher")):
        if custom_img_path and os.path.exists(str(custom_img_path)):
            try:
                raw_c = Image.open(str(custom_img_path)).convert("RGBA")
                target_w = int(880 * custom_scale * camera_zoom)
                target_h = int(820 * custom_scale * camera_zoom)
                aspect = raw_c.width / float(raw_c.height)
                if aspect >= (target_w / float(target_h)):
                    nw = target_w
                    nh = int(nw / aspect)
                else:
                    nh = target_h
                    nw = int(nh * aspect)
                raw_c = raw_c.resize((max(10, nw), max(10, nh)), resample=Image.BICUBIC)
                visual_element = make_rounded_card(raw_c, radius=32, shadow_blur=26, shadow_alpha=175)
                bob_amp = 8.0
            except Exception as e:
                print(f"Notice: Failed to load custom image {custom_img_path}: {e}")

    if visual_element is None:
        if v_type == "card":
            card_type = scene.get("card_type", "emerald")
            sheen_offset = (scene_progress * 1.5) % 1.5
            custom_logo = scene.get("custom_logo_path")
            tilt = -3.0 + math.sin(global_time * 1.8) * 1.5

            card_img = create_floating_card(
                card_type=card_type,
                tilt_angle=tilt,
                sheen_offset=sheen_offset,
                custom_logo_path=custom_logo,
            )
            scale = custom_scale * camera_zoom
            if scale != 1.0:
                card_img = card_img.resize((int(card_img.width * scale), int(card_img.height * scale)), resample=Image.BICUBIC)
            visual_element = card_img
            bob_amp = 14.0

        elif v_type == "newspaper":
            headline = scene.get("headline", "FBI Tracks Suspect Through a Contaminated Crypto Wallet")
            source = scene.get("source", "The New York Times")
            author = scene.get("author", "By Somini Sengupta")
            tilt = -2.5 + math.sin(global_time * 1.2) * 0.8
            marker_prog = ease_out_cubic(max(0.0, min(1.0, (scene_progress - 0.12) / 0.48)))
            high_phrase = scene.get("caption_highlight") or scene.get("highlight_phrase", "")

            paper = create_newspaper_clipping(
                headline=headline,
                source=source,
                author=author,
                tilt_angle=tilt,
                highlight_phrase=high_phrase,
                marker_progress=marker_prog,
                custom_image_path=custom_img,
            )
            scale = custom_scale * camera_zoom
            if scale != 1.0:
                paper = paper.resize((int(paper.width * scale), int(paper.height * scale)), resample=Image.BICUBIC)
            visual_element = paper
            target_cy = int(height * 0.42) + y_offset
            bob_amp = 6.0

        elif v_type == "phone":
            app_name = scene.get("app_name", "TradeIt Check")
            risk_score = scene.get("risk_score", "100% Safe")
            status_label = scene.get("status_label", "Trustpilot 9.5 Verified")
            bar_fill_t = max(0.0, min(1.0, (scene_progress - 0.18) / 0.48))
            bar_fill_ease = ease_out_cubic(bar_fill_t)

            phone = create_smartphone_app_mockup(
                app_name=app_name,
                risk_score=risk_score,
                status_label=status_label,
                progress_pct=bar_fill_ease,
                counter_progress=bar_fill_ease,
                custom_screenshot_path=custom_img,
            )
            scale = custom_scale * camera_zoom
            if scale != 1.0:
                phone = phone.resize((int(phone.width * scale), int(phone.height * scale)), resample=Image.BICUBIC)
            visual_element = phone
            target_cy = int(height * 0.43) + y_offset
            bob_amp = 6.0

        elif v_type == "skin":
            sheen_offset = (scene_progress * 1.6) % 1.6
            tilt = -3.5 + math.sin(global_time * 1.5) * 1.6
            skin_img = create_skin_item_card(
                skin_name=scene.get("skin_name", "★ Karambit | Doppler"),
                skin_category=scene.get("skin_category", "Covert Knife"),
                wear_rating=scene.get("wear_rating", "Factory New • Float 0.00142"),
                price_usd=scene.get("price_usd", "$1,850.00 USD"),
                stattrak_count=scene.get("stattrak_count", "001337"),
                rarity=scene.get("rarity", "covert"),
                tilt_angle=tilt,
                sheen_offset=sheen_offset,
                custom_skin_image_path=scene.get("custom_skin_image_path"),
            )
            scale = custom_scale * camera_zoom
            if scale != 1.0:
                skin_img = skin_img.resize((int(skin_img.width * scale), int(skin_img.height * scale)), resample=Image.BICUBIC)
            visual_element = skin_img
            bob_amp = 12.0

        elif v_type == "comparison":
            tilt = math.sin(global_time * 1.2) * 1.2
            sheen_offset = (scene_progress * 1.4) % 1.4
            comp_img = create_steam_vs_tradeit_comparison(
                left_title=scene.get("left_title", "STEAM MARKET"),
                right_title=scene.get("right_title", "TRADEIT.GG"),
                left_fee=scene.get("left_fee", "-15% VALVE TAX"),
                right_perk=scene.get("right_perk", "INSTANT 0s BOT SWAP"),
                bonus_code=scene.get("bonus_code", "CODE: MESTO300"),
                tilt_angle=tilt,
                sheen_offset=sheen_offset,
            )
            scale = custom_scale * camera_zoom
            if scale != 1.0:
                comp_img = comp_img.resize((int(comp_img.width * scale), int(comp_img.height * scale)), resample=Image.BICUBIC)
            visual_element = comp_img
            target_cy = int(height * 0.44) + y_offset
            bob_amp = 6.0

        elif v_type == "voucher":
            sheen_offset = (scene_progress * 1.5) % 1.5
            tilt = -2.5 + math.sin(global_time * 1.8) * 1.4
            voucher_img = create_promocode_voucher_card(
                promocode=scene.get("promocode", "MESTO300"),
                bonus_text=scene.get("bonus_text", "+35% TOPUP BONUS"),
                free_balance=scene.get("free_balance", "$5.00 FREE BALANCE"),
                platform=scene.get("platform", "TradeIt.gg"),
                tilt_angle=tilt,
                sheen_offset=sheen_offset,
            )
            scale = custom_scale * camera_zoom
            if scale != 1.0:
                voucher_img = voucher_img.resize((int(voucher_img.width * scale), int(voucher_img.height * scale)), resample=Image.BICUBIC)
            visual_element = voucher_img
            bob_amp = 10.0

    # Composite visual element with full multi-directional 3-phase kinetic transform
    if visual_element is not None:
        composite_kinetic_element(
            canvas=bg,
            element=visual_element,
            target_center=(target_cx, target_cy),
            progress=scene_progress,
            global_time=global_time,
            entry_dur=0.22,
            exit_dur=0.15,
            direction=direction,
            entry_direction=direction,
            exit_direction=exit_direction,
            slide_distance=slide_dist,
            bob_amplitude=bob_amp,
            bob_speed=bob_spd,
            max_tilt_deg=max_tilt,
        )

    # 3. Kinetic Typography overlay with word popping and neon badge
    caption_text = scene.get("caption", "")
    active_w = scene.get("active_word") or scene.get("caption_highlight", "")
    h_color = tuple(scene.get("highlight_color", [0, 255, 65] if (theme == "tradeit" or scene.get("promocode")) else [75, 110, 245]))
    caption_y_pct = scene.get("caption_y_offset")
    caption_font_size = int(scene.get("caption_font_size", 90))

    font_fam = scene.get("font_family")
    if not font_fam:
        font_fam = "serif_bold_italic" if (theme == "tradeit" or scene.get("promocode")) else ("gaming_impact" if v_type in ("skin", "comparison", "voucher") else "serif_bold_italic")
    use_upper = scene.get("uppercase", font_fam == "gaming_impact")

    # Dynamic positioning: If element is in upper half (target_cy < 900), caption goes to bottom; otherwise top
    if caption_y_pct is None:
        caption_pos = scene.get("caption_position") or ("bottom" if target_cy < int(height * 0.46) else "top")
    else:
        caption_pos = "custom"

    caption_overlay = render_kinetic_caption(
        text=caption_text,
        width=width,
        height=height,
        position=caption_pos,
        y_offset_pct=caption_y_pct,
        font_size=caption_font_size,
        font_family=font_fam,
        highlight_color=h_color,
        active_word=active_w,
        bounce_active=True,
        uppercase=use_upper,
    )
    bg = Image.alpha_composite(bg, caption_overlay)

    return bg


# ==============================================================================
# FULL VIDEO RENDERING PIPELINE
# ==============================================================================
def render_motion_explainer_short(
    script_data: Dict[str, Any],
    voice_id: str = "en-US-ChristopherNeural",
    fps: int = 30,  # 30fps default for fast renders, 60fps optional
    include_sfx: bool = True,
    include_music: bool = True,
    voice_volume: float = 1.0,
    music_volume: float = 0.18,
    sfx_volume: float = 0.8,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> Dict[str, Any]:
    """
    Renders a complete viral vertical Motion Explainer Short (1080x1920 MP4)
    with synchronized neural voiceover, animated visual assets, kinetic captions,
    and background music/SFX.
    """
    def report(pct: float, msg: str):
        if progress_callback:
            progress_callback(pct, msg)
        print(f"[{int(pct * 100)}%] {msg}")

    report(0.02, "Initializing Motion Explainer Rendering Engine...")
    sfx_lib = ensure_sfx_library()
    encoder, enc_args = detect_best_ffmpeg_encoder()
    report(0.05, f"Hardware Encoder detected: {encoder}")

    scenes = script_data.get("scenes", [])
    if not scenes:
        raise ValueError("Script must have at least one scene.")

    category = str(script_data.get("category", "")).lower()
    is_gaming = "gaming" in category or "skin" in category or script_data.get("music_track") == "gaming_beat"

    # Default speech rate: fast energetic +18% for gaming/shorts, +5% for documentary
    default_rate = "+18%" if is_gaming else "+5%"
    speech_rate = script_data.get("speech_rate", default_rate)
    chosen_voice = script_data.get("voice_id", voice_id)

    # 1. Obtain Voiceover Audio (User-uploaded audio track OR Neural TTS)
    custom_audio_path = script_data.get("custom_audio_path")
    if custom_audio_path and os.path.exists(custom_audio_path):
        report(0.08, f"Using user-provided audio track: {Path(custom_audio_path).name}")
        speech_path = str(custom_audio_path)
        total_audio_duration = probe_audio_duration(speech_path)
        voice_words = []
        report(0.18, f"User audio loaded ({total_audio_duration:.2f}s). Aligning scenes...")
    else:
        full_voice_text = " ".join(s.get("voice_text", "") for s in scenes)
        report(0.08, f"Synthesizing Neural Voiceover (rate={speech_rate}, voice={chosen_voice})...")
        voice_meta = synthesize_speech(full_voice_text, voice=chosen_voice, rate=speech_rate)
        speech_path = voice_meta["audio_path"]
        total_audio_duration = voice_meta["duration"]
        voice_words = voice_meta.get("words", [])
        report(0.18, f"Voiceover complete ({total_audio_duration:.2f}s, {len(voice_words)} words timed). Aligning scenes...")

    # Calculate per-scene durations (honoring explicit scene durations if provided)
    num_scenes = len(scenes)
    has_explicit_durs = any("duration" in s for s in scenes)
    if has_explicit_durs:
        raw_durs = [float(s.get("duration", 3.0)) for s in scenes]
        scale_ratio = total_audio_duration / max(0.1, sum(raw_durs))
        scene_durations = [max(1.5, round(d * scale_ratio, 2)) for d in raw_durs]
    else:
        text_lens = [max(1, len(s.get("voice_text", ""))) for s in scenes]
        total_chars = sum(text_lens)
        scene_durations = [max(1.8, round(total_audio_duration * (tl / total_chars), 2)) for tl in text_lens]

    # Re-normalize sum to match audio duration exactly
    diff = total_audio_duration - sum(scene_durations)
    scene_durations[-1] = max(1.5, round(scene_durations[-1] + diff, 2))

    total_duration = sum(scene_durations)
    total_frames = int(total_duration * fps)
    report(0.22, f"Total video duration: {total_duration:.2f}s ({total_frames} frames @ {fps}fps)")

    # 2. Render Frames to Temporary Image Sequence
    temp_dir = Path(tempfile.mkdtemp(prefix="motion_render_"))
    frames_dir = temp_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    report(0.25, "Rendering 2.5D visual frames & kinetic typography with word sync...")
    current_frame = 0
    start_time = time.time()

    for s_idx, (scene, s_dur) in enumerate(zip(scenes, scene_durations)):
        s_frames = int(s_dur * fps)
        for f in range(s_frames):
            s_prog = f / max(1, s_frames)
            global_sec = current_frame / fps

            # Find active spoken word at this exact timestamp for word-by-word bouncing
            active_word_str = None
            for w_item in voice_words:
                if w_item["start"] <= global_sec <= w_item["end"]:
                    active_word_str = w_item["word"]
                    break

            scene_frame_data = dict(scene)
            if "theme" not in scene_frame_data and "theme" in script_data:
                scene_frame_data["theme"] = script_data["theme"]
            if "promocode" not in scene_frame_data and "promocode" in script_data:
                scene_frame_data["promocode"] = script_data["promocode"]
            if active_word_str:
                scene_frame_data["active_word"] = active_word_str

            frame_img = render_motion_frame(
                scene=scene_frame_data,
                scene_progress=s_prog,
                global_time=global_sec,
                width=1080,
                height=1920,
            )

            frame_file = frames_dir / f"frame_{current_frame:05d}.jpg"
            frame_img.convert("RGB").save(str(frame_file), quality=92)
            current_frame += 1

            if current_frame % 30 == 0 or current_frame == total_frames:
                pct = 0.25 + 0.50 * (current_frame / total_frames)
                fps_render = current_frame / max(0.1, time.time() - start_time)
                report(pct, f"Rendered frame {current_frame}/{total_frames} ({fps_render:.1f} fps)")

    report(0.78, "Compositing multi-track audio (voiceover, ambient music & SFX)...")

    # 3. Construct FFmpeg Audio Filter Graph with custom volume controls
    mixed_audio_file = temp_dir / "mixed_audio.wav"
    audio_inputs = ["-i", speech_path]
    filter_complex_parts = [f"[0:a]volume={voice_volume}[voice];"]
    stream_count = 1

    # Check if music is disabled in script
    if script_data.get("music_track") == "none" or script_data.get("include_music") is False:
        include_music = False

    # Select background music track
    custom_music = script_data.get("music_track")
    if custom_music and custom_music in sfx_lib:
        selected_music_path = sfx_lib[custom_music]
    elif is_gaming and "gaming_beat" in sfx_lib:
        selected_music_path = sfx_lib["gaming_beat"]
    else:
        selected_music_path = sfx_lib.get("ambient_music")

    # Clean ducked music volume (subtle bed, 10-12% so voice stays 100% crisp)
    effective_music_vol = music_volume if music_volume != 0.18 else (0.12 if is_gaming else 0.10)

    if include_music and selected_music_path and os.path.exists(selected_music_path):
        audio_inputs.extend(["-i", selected_music_path])
        filter_complex_parts.append(f"[{stream_count}:a]aloop=loop=-1:size=2e+09,volume={effective_music_vol}[music];")
        stream_count += 1

    # Add SFX cues at scene boundary timestamps
    sfx_tracks = []
    if include_sfx:
        if is_gaming:
            first_sfx = sfx_lib.get("heavy_impact", sfx_lib["whoosh"])
            sfx_sequence = [
                sfx_lib.get("case_unlock", sfx_lib["pop"]),
                sfx_lib.get("heavy_impact", sfx_lib["whoosh"]),
                sfx_lib.get("cash_register", sfx_lib["chime"]),
                sfx_lib.get("chime", sfx_lib["pop"]),
            ]
        else:
            first_sfx = sfx_lib["whoosh"]
            sfx_sequence = [sfx_lib["paper_slide"], sfx_lib["pop"], sfx_lib["chime"]]

        sfx_timeline = [(0.0, first_sfx, 0.70)]
        accum_t = 0.0
        for i in range(len(scene_durations) - 1):
            accum_t += scene_durations[i]
            # Check if current scene requested custom SFX
            custom_sfx_key = scenes[i + 1].get("sfx") if i + 1 < len(scenes) else None
            if custom_sfx_key and custom_sfx_key in sfx_lib:
                sfx_file = sfx_lib[custom_sfx_key]
            else:
                sfx_file = sfx_sequence[i % len(sfx_sequence)]
            sfx_timeline.append((accum_t, sfx_file, 0.75))
        for delay_sec, sfx_path, vol in sfx_timeline:
            if os.path.exists(sfx_path):
                audio_inputs.extend(["-i", sfx_path])
                idx = stream_count
                delay_ms = int(delay_sec * 1000)
                # Scale SFX to comfortable mix level
                filter_complex_parts.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms},volume={vol * sfx_volume * 0.4}[sfx_{idx}];")
                sfx_tracks.append(f"[sfx_{idx}]")
                stream_count += 1

    # Merge audio streams: normalize=0 prevents volume scaling upwards as streams end
    if stream_count > 1:
        sources = "[voice]"
        if include_music:
            sources += "[music]"
        sources += "".join(sfx_tracks)
        total_audio_sources = 1 + (1 if include_music else 0) + len(sfx_tracks)
        filter_complex_parts.append(f"{sources}amix=inputs={total_audio_sources}:duration=first:dropout_transition=0:normalize=0[aout]")
        filter_str = "".join(filter_complex_parts)
        ffmpeg_audio_cmd = [
            "ffmpeg", "-y",
            *audio_inputs,
            "-filter_complex", filter_str,
            "-map", "[aout]",
            "-t", str(total_duration),
            str(mixed_audio_file)
        ]
        subprocess.run(ffmpeg_audio_cmd, capture_output=True, check=True)
        final_audio_track = str(mixed_audio_file)
    else:
        final_audio_track = speech_path

    # 4. Final Encoding: Video Frames + Mixed Audio -> 1080x1920 MP4
    report(0.85, f"Encoding 1080x1920 Short via {encoder}...")
    output_filename = f"motion_short_{int(time.time())}_{os.urandom(3).hex()}.mp4"
    final_output_path = OUTPUTS_DIR / output_filename

    ffmpeg_encode_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frames_dir / "frame_%05d.jpg"),
        "-i", final_audio_track,
        "-c:v", encoder,
        *enc_args,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(final_output_path)
    ]

    res = subprocess.run(ffmpeg_encode_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        # Fallback to libx264 if hardware encoder had an issue
        report(0.90, "Hardware encoder fallback to libx264...")
        fallback_cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(frames_dir / "frame_%05d.jpg"),
            "-i", final_audio_track,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(final_output_path)
        ]
        subprocess.run(fallback_cmd, capture_output=True, check=True)

    # Clean up temp frames
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

    report(1.0, f"Video export complete! Saved as {output_filename}")

    return {
        "success": True,
        "video_filename": output_filename,
        "video_path": str(final_output_path),
        "duration": total_duration,
        "fps": fps,
        "resolution": "1080x1920",
        "scenes_count": num_scenes,
        "encoder": encoder,
    }


if __name__ == "__main__":
    from core.motion_explainer.ai_scriptwriter import VIRAL_PRESETS
    sample_script = VIRAL_PRESETS[0]
    print("Testing motion renderer with preset:", sample_script["name"])
    res = render_motion_explainer_short(sample_script, fps=30)
    print("Render finished:", res)
