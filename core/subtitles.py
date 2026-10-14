import math
import re
import wave
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import numpy as np

# PyAV 19+ compatibility safeguard for faster-whisper
try:
    import av
    _orig_av_open = av.open
    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)
    av.open = _safe_av_open
except Exception:
    pass

from core.config import (
    DEFAULT_FONT_NAME,
    DEFAULT_FONT_SIZE,
    DEFAULT_PRIMARY_COLOR,
    DEFAULT_HIGHLIGHT_COLOR,
    DEFAULT_OUTLINE_COLOR,
    DEFAULT_OUTLINE_WIDTH,
    DEFAULT_SHADOW_DEPTH,
    DEFAULT_SUBTITLE_Y_OFFSET,
    TRANSCRIBE_TIMEOUT,
)
from core.utils import (
    resolve_binary_paths,
    run_command_safe,
    retry_with_backoff,
    TempFileManager,
)


def hex_to_ass_color(hex_color: str, alpha: str = "00") -> str:
    """
    Converts #RRGGBB to ASS &H<alpha><BB><GG><RR>& format.
    Example: #FFD700 -> &H0000D7FF&
    """
    cleaned = hex_color.strip().lstrip("#")
    if len(cleaned) == 3:
        cleaned = "".join([c * 2 for c in cleaned])
    if len(cleaned) != 6:
        cleaned = "FFFFFF"

    r = cleaned[0:2].upper()
    g = cleaned[2:4].upper()
    b = cleaned[4:6].upper()
    return f"&H{alpha}{b}{g}{r}&"


def format_ass_timestamp(seconds: float) -> str:
    """Converts seconds into ASS timestamp H:MM:SS.cs"""
    if seconds < 0:
        seconds = 0.0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"


def extract_audio_track(video_path: Path, output_wav: Path) -> Path:
    """Extracts a 16kHz mono WAV audio track optimized for Whisper transcription."""
    ffmpeg_bin, _ = resolve_binary_paths()
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_wav),
    ]
    res = run_command_safe(cmd, timeout=TRANSCRIBE_TIMEOUT)
    if res.returncode != 0 or not output_wav.is_file():
        raise RuntimeError(f"Audio extraction failed: {res.stderr.strip()[:300]}")
    return output_wav


def get_optimal_whisper_config() -> Tuple[str, str]:
    """Detects available hardware and chooses optimal device and quantization."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


class SubtitleEngine:
    """Manages local Whisper transcription and generates dynamic ASS subtitle files."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            device, compute_type = get_optimal_whisper_config()
            try:
                self._model = WhisperModel(
                    self.model_size,
                    device=device,
                    compute_type=compute_type,
                    cpu_threads=4,
                )
            except Exception:
                # Fallback to pure CPU int8 if CUDA initialization fails
                self._model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=4,
                )
        return self._model

    def transcribe(self, audio_wav_path: Path) -> List[Dict[str, Any]]:
        """
        Transcribes audio with word-level timestamps.
        Returns a list of word dictionaries: [{'word': str, 'start': float, 'end': float}].
        Returns empty list if no speech detected.
        """
        model = self._get_model()

        # Direct PCM read to bypass container decode issues
        try:
            with wave.open(str(audio_wav_path), "rb") as wf:
                raw_bytes = wf.readframes(wf.getnframes())
                audio_input = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        except Exception:
            audio_input = str(audio_wav_path)

        def _do_transcribe():
            segments, info = model.transcribe(
                audio_input,
                word_timestamps=True,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )
            all_words = []
            for seg in segments:
                if seg.words:
                    for w in seg.words:
                        cleaned = w.word.strip().upper()
                        # Filter out punctuation-only artifacts
                        cleaned = re.sub(r"[^\w\s\$\€\£\!\?\%]", "", cleaned)
                        if cleaned:
                            all_words.append({
                                "word": cleaned,
                                "start": w.start,
                                "end": max(w.end, w.start + 0.1),
                            })
            return all_words

        return retry_with_backoff(
            _do_transcribe,
            max_retries=2,
            initial_delay=1.0,
            task_name="Audio transcription with faster-whisper",
        )

    def generate_ass_script(
        self,
        words: List[Dict[str, Any]],
        output_ass_path: Path,
        font_name: str = DEFAULT_FONT_NAME,
        font_size: int = DEFAULT_FONT_SIZE,
        primary_color_hex: str = DEFAULT_PRIMARY_COLOR,
        highlight_color_hex: str = DEFAULT_HIGHLIGHT_COLOR,
        outline_color_hex: str = DEFAULT_OUTLINE_COLOR,
        outline_width: int = DEFAULT_OUTLINE_WIDTH,
        shadow_depth: int = DEFAULT_SHADOW_DEPTH,
        y_position: int = DEFAULT_SUBTITLE_Y_OFFSET,
        words_per_burst: int = 3,
    ) -> Optional[Path]:
        """
        Generates an ASS subtitle script featuring word-by-word pop highlight karaoke styling.
        If words is empty, returns None cleanly (No-speech fallback).
        """
        if not words:
            return None

        primary_ass = hex_to_ass_color(primary_color_hex)
        highlight_ass = hex_to_ass_color(highlight_color_hex)
        outline_ass = hex_to_ass_color(outline_color_hex)
        back_ass = "&H80000000&"  # 50% translucent black shadow

        # Group words into bursts of 2-4 words for short-form retention
        bursts: List[List[Dict[str, Any]]] = []
        current_burst: List[Dict[str, Any]] = []

        for w in words:
            current_burst.append(w)
            word_str = w.get("word", "") if isinstance(w, dict) else getattr(w, "word", "")
            if len(current_burst) >= words_per_burst or (word_str.endswith((".", "!", "?"))):
                bursts.append(current_burst)
                current_burst = []

        if current_burst:
            bursts.append(current_burst)

        # Header template for 1080x1920 layout
        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_ass},{highlight_ass},{outline_ass},{back_ass},-1,0,0,0,100,100,1,0,1,{outline_width},{shadow_depth},5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        dialogue_lines: List[str] = []

        # X center is 540 for 1080 canvas width
        x_center = 540

        for burst in bursts:
            if not burst:
                continue
            total_words = len(burst)
            for active_idx in range(total_words):
                active_word = burst[active_idx]
                t_start = active_word["start"]
                # Active word ends either when next word starts or at burst end
                if active_idx + 1 < total_words:
                    t_end = burst[active_idx + 1]["start"]
                else:
                    t_end = active_word["end"]

                # Ensure minimum visible duration of 120ms
                if t_end <= t_start:
                    t_end = t_start + 0.12

                start_str = format_ass_timestamp(t_start)
                end_str = format_ass_timestamp(t_end)

                # Assemble line text with active word pop without using destructive \r tag
                tokens = []
                for idx, w in enumerate(burst):
                    word_text = w["word"]
                    if idx == active_idx:
                        # Pop styling: highlight color + scale pulse, then return to primary color and 100% scale
                        tokens.append(f"{{\\c{highlight_ass}\\fscx114\\fscy114}}{word_text}{{\\c{primary_ass}\\fscx100\\fscy100}}")
                    else:
                        tokens.append(f"{{\\c{primary_ass}\\fscx100\\fscy100}}{word_text}")

                line_body = " ".join(tokens)
                # Clamp Y to valid screen coordinates (middle-center alignment)
                safe_y = max(100, min(1820, int(y_position)))
                dialogue_text = f"{{\\an5\\pos({x_center},{safe_y})\\q2}}{line_body}"
                dialogue_lines.append(
                    f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{dialogue_text}"
                )

        content = header + "\n".join(dialogue_lines) + "\n"
        output_ass_path.write_text(content, encoding="utf-8")
        return output_ass_path
