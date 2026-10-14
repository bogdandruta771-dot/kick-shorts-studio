"""Video processing engine: 9:16 vertical composition, crop layout stacking, blurred background, subtitle burning, and outro concatenation."""
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List

from core.config import (
    TARGET_WIDTH,
    TARGET_HEIGHT,
    DEFAULT_FPS,
    AUDIO_SAMPLE_RATE,
    RENDER_TIMEOUT,
    DEFAULT_SUBTITLE_Y_OFFSET,
)
from core.utils import (
    resolve_binary_paths,
    run_command_safe,
    escape_ffmpeg_filter_path,
    TempFileManager,
)
from core.video_ingest import validate_media_file
from core.subtitles import SubtitleEngine, extract_audio_track


class VideoProcessor:
    """Orchestrates layout transformation, subtitle rendering, and outro concatenation."""

    def __init__(self):
        self.ffmpeg_bin, self.ffprobe_bin = resolve_binary_paths()
        self.subtitle_engine = SubtitleEngine()

    def process_short(
        self,
        input_video_path: Path,
        output_video_path: Path,
        gameplay_crop: Dict[str, int],
        facecam_crop: Dict[str, int],
        enable_subtitles: bool = True,
        subtitle_options: Optional[Dict[str, Any]] = None,
        outro_video_path: Optional[Path] = None,
        trim_start: Optional[float] = None,
        trim_end: Optional[float] = None,
        overlays: Optional[List[Dict[str, Any]]] = None,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Path:
        """
        Executes the full pipeline:
        1. Validates input
        2. Applies trim cut if trim_start/trim_end specified
        3. Transcribes & generates karaoke ASS subtitles
        4. Stacks gameplay (top) + cam (bottom) over blurred background mirror
        5. Burns subtitles (if speech exists and enabled)
        6. Normalizes and appends outro (if provided)
        """
        if progress_cb:
            progress_cb(0.05, "Validating media container...")

        meta = validate_media_file(input_video_path)
        src_w = meta["width"]
        src_h = meta["height"]

        # Clamp crop coordinates to source dimensions
        gx = max(0, min(gameplay_crop.get("x", 0), src_w - 2))
        gy = max(0, min(gameplay_crop.get("y", 0), src_h - 2))
        gw = max(2, min(gameplay_crop.get("w", src_w), src_w - gx))
        gh = max(2, min(gameplay_crop.get("h", src_h), src_h - gy))

        cx = max(0, min(facecam_crop.get("x", 0), src_w - 2))
        cy = max(0, min(facecam_crop.get("y", 0), src_h - 2))
        cw = max(2, min(facecam_crop.get("w", src_w), src_w - cx))
        ch = max(2, min(facecam_crop.get("h", src_h), src_h - cy))

        # Ensure even numbers for H.264
        gw -= gw % 2
        gh -= gh % 2
        cw -= cw % 2
        ch -= ch % 2

        with TempFileManager("render_job") as temp_mgr:
            ass_path: Optional[Path] = None
            active_source_path = input_video_path

            # Optional Pre-Trim Slicing
            if trim_start is not None and trim_end is not None and (trim_end - trim_start > 0.5):
                t_start = max(0.0, float(trim_start))
                t_end = min(meta["duration"], float(trim_end))
                is_full_clip = (t_start <= 0.05 and t_end >= meta["duration"] - 0.15)
                if not is_full_clip and t_end > t_start:
                    if progress_cb:
                        progress_cb(0.12, f"Slicing cut: {t_start:.1f}s to {t_end:.1f}s...")
                    trimmed_slice_path = temp_mgr.get_path("_trimmed_cut.mp4")
                    trim_cmd = [
                        self.ffmpeg_bin,
                        "-y",
                        "-ss", f"{t_start:.3f}",
                        "-to", f"{t_end:.3f}",
                        "-i", str(input_video_path),
                        "-c:v", "libx264",
                        "-preset", "ultrafast",
                        "-crf", "18",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-avoid_negative_ts", "make_zero",
                        str(trimmed_slice_path),
                    ]
                    run_res = run_command_safe(trim_cmd, timeout=RENDER_TIMEOUT)
                    if run_res.returncode == 0 and trimmed_slice_path.is_file():
                        active_source_path = trimmed_slice_path
                        meta = validate_media_file(active_source_path)

            # Stage A: Subtitle Generation
            if enable_subtitles and meta["has_audio"]:
                if progress_cb:
                    progress_cb(0.20, "Extracting audio track for transcription...")
                audio_wav = temp_mgr.get_path(".wav")
                try:
                    extract_audio_track(active_source_path, audio_wav)
                    if progress_cb:
                        progress_cb(0.35, "Transcribing speech with Whisper...")
                    words = self.subtitle_engine.transcribe(audio_wav)

                    if words:
                        if progress_cb:
                            progress_cb(0.50, f"Generating karaoke subtitles ({len(words)} words)...")
                        opts = subtitle_options or {}
                        raw_ass = temp_mgr.get_path(".ass")
                        ass_path = self.subtitle_engine.generate_ass_script(
                            words=words,
                            output_ass_path=raw_ass,
                            font_name=opts.get("font_name", "Arial"),
                            font_size=opts.get("font_size", 48),
                            primary_color_hex=opts.get("primary_color", "#FFFFFF"),
                            highlight_color_hex=opts.get("highlight_color", "#FFD700"),
                            y_position=opts.get("y_position", DEFAULT_SUBTITLE_Y_OFFSET),
                        )
                    else:
                        if progress_cb:
                            progress_cb(0.50, "No speech detected; continuing with clean audio...")
                except Exception as exc:
                    # Non-fatal subtitle failure fallback: continue without subtitles
                    if progress_cb:
                        progress_cb(0.50, f"Subtitle notice: {exc}; continuing without subtitles...")

            # Stage B: Construct Layout Stacking Filter Complex
            if progress_cb:
                progress_cb(0.65, "Composing 9:16 layout (Top Gameplay + Bottom Cam)...")

            # Output intermediate short (before outro, or directly to output if no outro)
            primary_short_path = (
                temp_mgr.get_path("_main_short.mp4") if outro_video_path else output_video_path
            )

            # Gameplay scales to 1080 width, maintaining its aspect ratio
            # Cam scales to 1080 width, maintaining its aspect ratio
            # Blurred background mirror fills 1080x1920
            filter_chains = []

            # Background stream
            filter_chains.append(
                f"[0:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={TARGET_WIDTH}:{TARGET_HEIGHT},boxblur=25:10,setsar=1,fps={DEFAULT_FPS}[bg]"
            )

            # Cropped Gameplay (Top) - max height 1100, centered horizontally
            filter_chains.append(
                f"[0:v]crop={gw}:{gh}:{gx}:{gy},scale={TARGET_WIDTH}:1100:force_original_aspect_ratio=decrease,setsar=1,fps={DEFAULT_FPS}[gp]"
            )

            # Cropped Facecam (Bottom) - max height 780, centered horizontally
            filter_chains.append(
                f"[0:v]crop={cw}:{ch}:{cx}:{cy},scale={TARGET_WIDTH}:780:force_original_aspect_ratio=decrease,setsar=1,fps={DEFAULT_FPS}[fc]"
            )

            # Overlay gameplay on top (x=(W-w)/2, y=0)
            filter_chains.append("[bg][gp]overlay=(W-w)/2:0[layer1]")

            # Overlay facecam on bottom (x=(W-w)/2, y=H-h)
            filter_chains.append("[layer1][fc]overlay=(W-w)/2:H-h[v_composed]")

            # Collect valid image overlays (to cover casino header, chat goal, promo code banner, etc.)
            valid_overlays = []
            if overlays:
                for ovl in overlays:
                    if isinstance(ovl, dict) and ovl.get("image_path"):
                        ovl_p = Path(str(ovl["image_path"]))
                        if ovl_p.is_file():
                            valid_overlays.append({
                                "path": ovl_p,
                                "x": max(0, min(TARGET_WIDTH - 2, int(float(ovl.get("x", 0))))),
                                "y": max(0, min(TARGET_HEIGHT - 2, int(float(ovl.get("y", 0))))),
                                "w": max(4, min(TARGET_WIDTH, int(float(ovl.get("w", TARGET_WIDTH))))),
                                "h": max(4, min(TARGET_HEIGHT, int(float(ovl.get("h", 140))))),
                                "opacity": max(0.05, min(1.0, float(ovl.get("opacity", 1.0)))),
                            })

            current_v_layer = "v_composed"
            for idx, ovl in enumerate(valid_overlays):
                in_idx = idx + 1
                w = ovl["w"]
                h = ovl["h"]
                x = ovl["x"]
                y = ovl["y"]
                opacity = ovl["opacity"]

                sc_label = f"ovl_sc_{idx}"
                if opacity < 0.99:
                    filter_chains.append(
                        f"[{in_idx}:v]scale={w}:{h}:force_original_aspect_ratio=disable,format=rgba,colorchannelmixer=aa={opacity:.2f}[{sc_label}]"
                    )
                else:
                    filter_chains.append(
                        f"[{in_idx}:v]scale={w}:{h}:force_original_aspect_ratio=disable[{sc_label}]"
                    )

                next_layer = f"v_ovl_{idx}"
                filter_chains.append(
                    f"[{current_v_layer}][{sc_label}]overlay={x}:{y}[{next_layer}]"
                )
                current_v_layer = next_layer

            # Subtitles burn-in
            if ass_path and ass_path.is_file():
                escaped_ass = escape_ffmpeg_filter_path(str(ass_path))
                filter_chains.append(f"[{current_v_layer}]subtitles='{escaped_ass}'[v_out]")
            else:
                filter_chains.append(f"[{current_v_layer}]null[v_out]")

            full_filter_complex = ";".join(filter_chains)

            # Audio mapping
            audio_args = []
            if meta["has_audio"]:
                audio_args = [
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-ar", str(AUDIO_SAMPLE_RATE),
                    "-ac", "2",
                ]
            else:
                # Add silent audio stream
                audio_args = [
                    "-f", "lavfi",
                    "-i", f"anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest",
                ]

            render_cmd = [
                self.ffmpeg_bin,
                "-y",
                "-i", str(active_source_path),
            ]

            # Append overlay images as inputs 1..N
            for ovl in valid_overlays:
                render_cmd.extend(["-i", str(ovl["path"])])

            # Append silent audio input if no audio exists
            silent_audio_idx = None
            if not meta["has_audio"]:
                silent_audio_idx = 1 + len(valid_overlays)
                render_cmd.extend(["-f", "lavfi", "-i", f"anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo"])

            render_cmd.extend([
                "-filter_complex", full_filter_complex,
                "-map", "[v_out]",
            ])

            if meta["has_audio"]:
                render_cmd.extend(["-map", "0:a:0"])
            else:
                render_cmd.extend(["-map", f"{silent_audio_idx}:a:0"])

            render_cmd.extend([
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "19",
                "-threads", "0",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", str(AUDIO_SAMPLE_RATE),
                "-ac", "2",
            ])

            if not meta["has_audio"]:
                render_cmd.append("-shortest")

            render_cmd.append(str(primary_short_path))

            dynamic_timeout = max(RENDER_TIMEOUT, int(meta.get("duration", 60.0) * 8))
            res = run_command_safe(render_cmd, timeout=dynamic_timeout)
            if res.returncode != 0 or not primary_short_path.is_file():
                raise RuntimeError(f"FFmpeg render failed: {res.stderr.strip()[:400]}")

            # Stage C: Outro Concatenation (if specified)
            if outro_video_path and outro_video_path.is_file():
                if progress_cb:
                    progress_cb(0.85, "Normalizing & appending outro video...")
                self._concatenate_outro(
                    main_short_path=primary_short_path,
                    outro_path=outro_video_path,
                    output_path=output_video_path,
                )

        if progress_cb:
            progress_cb(1.0, "Short generated successfully!")

        validate_media_file(output_video_path)
        return output_video_path

    def _concatenate_outro(
        self,
        main_short_path: Path,
        outro_path: Path,
        output_path: Path,
    ) -> Path:
        """
        Normalizes resolution, SAR, audio rate, and timebase, then concatenates seamlessly.
        """
        outro_meta = validate_media_file(outro_path)
        has_outro_audio = outro_meta["has_audio"]
        outro_dur = outro_meta["duration"]

        filter_parts = [
            f"[0:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={DEFAULT_FPS},"
            f"format=yuv420p[v0]",
            f"[0:a]aformat=sample_rates={AUDIO_SAMPLE_RATE}:channel_layouts=stereo[a0]",
            f"[1:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={DEFAULT_FPS},"
            f"format=yuv420p[v1]",
        ]

        if has_outro_audio:
            filter_parts.append(
                f"[1:a]aformat=sample_rates={AUDIO_SAMPLE_RATE}:channel_layouts=stereo[a1]"
            )
        else:
            filter_parts.append(
                f"aevalsrc=0:d={outro_dur}:s={AUDIO_SAMPLE_RATE}:c=stereo[a1]"
            )

        filter_parts.append("[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")
        concat_filter = ";".join(filter_parts)

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i", str(main_short_path),
            "-i", str(outro_path),
            "-filter_complex", concat_filter,
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path),
        ]

        res = run_command_safe(cmd, timeout=RENDER_TIMEOUT)
        if res.returncode != 0 or not output_path.is_file():
            raise RuntimeError(f"Outro concatenation failed: {res.stderr.strip()[:400]}")

        return output_path
