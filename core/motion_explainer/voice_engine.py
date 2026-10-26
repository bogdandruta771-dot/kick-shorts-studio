"""
High-Fidelity Neural Voice Synthesis Engine & Custom Audio Processor
Supports:
1. Edge-TTS (100% free, zero-key, studio neural voices) with word/sentence boundary timing.
2. ElevenLabs TTS integration (Adam, Rachel, Antoni, Josh, Charlie) with ELEVENLABS_API_KEY.
3. User-uploaded custom voiceover / audio files with ffprobe duration analysis.
"""
import os
import sys
import json
import asyncio
import re
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import edge_tts

OUTPUTS_AUDIO_DIR = Path(__file__).parent.parent / "outputs" / "audio"
OUTPUTS_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# ElevenLabs voice catalog mapping
ELEVENLABS_VOICES = {
    "eleven_liam": {"id": "TX3LPaxmHKxFdv7VOQHJ", "name": "ElevenLabs: Liam (Energetic Social Media Creator)", "gender": "Male"},
    "eleven_adam": {"id": "pNInz6obpgDQGcFmaJgB", "name": "ElevenLabs: Adam (Deep / Authoritative)", "gender": "Male"},
    "eleven_charlie": {"id": "IKne3meq5aSn9XLyUdCD", "name": "ElevenLabs: Charlie (Confident / Fast)", "gender": "Male"},
    "eleven_antoni": {"id": "ErXwobaYiN019PkySvjV", "name": "ElevenLabs: Antoni (Energetic / Storyteller)", "gender": "Male"},
    "eleven_josh": {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "ElevenLabs: Josh (Casual / Young)", "gender": "Male"},
    "eleven_rachel": {"id": "21m00Tcm4TlvDq8ikWAM", "name": "ElevenLabs: Rachel (Calm / Polished)", "gender": "Female"},
}

AVAILABLE_VOICES = [
    {
        "id": "eleven_liam",
        "name": "Liam (ElevenLabs Energetic Creator)",
        "gender": "Male",
        "recommended": True,
        "style": "Crystal-clear, energetic, natural social media creator",
    },
    {
        "id": "en-US-ChristopherNeural",
        "name": "Christopher (Authoritative / Documentary / Tech) [Edge-TTS]",
        "gender": "Male",
        "recommended": True,
        "style": "Fast, clear, serious hook delivery",
    },
    {
        "id": "en-US-GuyNeural",
        "name": "Guy (Energetic / Modern Tech) [Edge-TTS]",
        "gender": "Male",
        "recommended": True,
        "style": "High-energy conversational pacing",
    },
    {
        "id": "en-US-EricNeural",
        "name": "Eric (Deep / Serious Warning) [Edge-TTS]",
        "gender": "Male",
        "recommended": False,
        "style": "Deep, high-gravity narration",
    },
    {
        "id": "en-US-AriaNeural",
        "name": "Aria (Polished / Corporate / Fintech) [Edge-TTS]",
        "gender": "Female",
        "recommended": True,
        "style": "Sharp, executive, high clarity",
    },
    {
        "id": "en-US-JennyNeural",
        "name": "Jenny (Casual / Friendly SaaS) [Edge-TTS]",
        "gender": "Female",
        "recommended": False,
        "style": "Upbeat, approachable tone",
    },
    {
        "id": "en-GB-RyanNeural",
        "name": "Ryan (British / Tech Insider) [Edge-TTS]",
        "gender": "Male",
        "recommended": False,
        "style": "Sophisticated tech journalist",
    },
    {
        "id": "ru-RU-DmitryNeural",
        "name": "Dmitry (Russian / Modern & Energetic) [Edge-TTS]",
        "gender": "Male",
        "recommended": False,
        "style": "Clear Russian delivery for promos",
    },
    {
        "id": "eleven_adam",
        "name": "Adam (ElevenLabs Studio Deep Voice)",
        "gender": "Male",
        "recommended": True,
        "style": "Premium ElevenLabs narration",
    },
    {
        "id": "eleven_antoni",
        "name": "Antoni (ElevenLabs Energetic Commercial)",
        "gender": "Male",
        "recommended": True,
        "style": "Fast-paced YouTube/TikTok ads",
    },
    {
        "id": "eleven_rachel",
        "name": "Rachel (ElevenLabs Clear Narrative)",
        "gender": "Female",
        "recommended": False,
        "style": "Smooth studio audio",
    },
]


def get_available_voices() -> List[Dict[str, Any]]:
    """Returns the list of neural and ElevenLabs voices."""
    return AVAILABLE_VOICES


def probe_audio_duration(audio_path: str) -> float:
    """Uses ffprobe to precisely determine the duration of any audio file (WAV, MP3, AAC, etc.)."""
    if not os.path.exists(audio_path):
        return 0.0
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        dur = float(res.stdout.strip())
        return round(dur, 3)
    except Exception:
        # Fallback approximate size estimation or 15s default
        return 15.0


def synthesize_elevenlabs(
    text: str,
    voice_key: str = "eleven_adam",
    api_key: Optional[str] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Synthesizes speech using the ElevenLabs REST API.
    Falls back to Edge-TTS if ELEVENLABS_API_KEY is not provided or fails.
    """
    api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("Notice: ELEVENLABS_API_KEY not configured. Falling back to Edge-TTS ChristopherNeural.")
        return synthesize_speech(text, voice="en-US-ChristopherNeural", output_path=output_path)

    v_meta = ELEVENLABS_VOICES.get(voice_key, ELEVENLABS_VOICES["eleven_adam"])
    voice_id = v_meta["id"]

    if not output_path:
        out_file = OUTPUTS_AUDIO_DIR / f"speech_eleven_{os.urandom(4).hex()}.mp3"
    else:
        out_file = Path(output_path)

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.85,
            "style": 0.20,
            "use_speaker_boost": True,
        }
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            audio_data = resp.read()
            with open(out_file, "wb") as f:
                f.write(audio_data)

        duration = probe_audio_duration(str(out_file))

        # Build approximate word timing for kinetic typography
        words = text.split()
        words_timed = []
        if words and duration > 0:
            dur_per_word = duration / len(words)
            cur_t = 0.0
            for w in words:
                words_timed.append({
                    "word": w,
                    "start": round(cur_t, 3),
                    "end": round(cur_t + dur_per_word, 3),
                })
                cur_t += dur_per_word

        return {
            "success": True,
            "audio_path": str(out_file),
            "duration": duration,
            "sentences": [{"text": text, "start": 0.0, "end": duration, "duration": duration}],
            "words": words_timed,
            "voice": voice_key,
            "text": text,
        }
    except Exception as e:
        print(f"Warning: ElevenLabs synthesis failed ({e}). Falling back to Edge-TTS.")
        return synthesize_speech(text, voice="en-US-ChristopherNeural", output_path=output_path)


async def _synthesize_edge_tts(
    text: str,
    voice: str = "en-US-ChristopherNeural",
    output_path: Optional[str] = None,
    rate: str = "+5%",
    pitch: str = "+0Hz",
) -> Dict[str, Any]:
    """Internal async synthesizer collecting audio and boundary timing."""
    if not output_path:
        out_file = OUTPUTS_AUDIO_DIR / f"speech_{os.urandom(4).hex()}.mp3"
    else:
        out_file = Path(output_path)

    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)

    audio_chunks = []
    sentences = []
    current_time = 0.0

    async for chunk in communicate.stream():
        chunk_type = chunk["type"]
        if chunk_type == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk_type == "SentenceBoundary":
            offset_sec = chunk["offset"] / 10_000_000.0
            duration_sec = chunk["duration"] / 10_000_000.0
            sentences.append({
                "text": chunk["text"],
                "start": round(offset_sec, 3),
                "end": round(offset_sec + duration_sec, 3),
                "duration": round(duration_sec, 3),
            })
            current_time = max(current_time, offset_sec + duration_sec)

    with open(out_file, "wb") as f:
        for data in audio_chunks:
            f.write(data)

    words_timed = []
    for s in sentences:
        words = s["text"].split()
        if not words:
            continue
        total_chars = sum(len(w) for w in words)
        w_start = s["start"]
        for w in words:
            weight = len(w) / max(1, total_chars)
            w_dur = max(0.12, s["duration"] * weight)
            words_timed.append({
                "word": w,
                "start": round(w_start, 3),
                "end": round(w_start + w_dur, 3),
            })
            w_start += w_dur

    return {
        "success": True,
        "audio_path": str(out_file),
        "duration": round(current_time, 2) if current_time > 0 else 15.0,
        "sentences": sentences,
        "words": words_timed,
        "voice": voice,
        "text": text,
    }


def synthesize_speech(
    text: str,
    voice: str = "en-US-ChristopherNeural",
    output_path: Optional[str] = None,
    rate: str = "+5%",
) -> Dict[str, Any]:
    """Synchronous wrapper for FastAPI and background rendering pipelines."""
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("Text cannot be empty for voice synthesis.")

    # Check if ElevenLabs voice was selected
    if str(voice).startswith("eleven_"):
        return synthesize_elevenlabs(clean_text, voice_key=voice, output_path=output_path)

    try:
        return asyncio.run(_synthesize_edge_tts(clean_text, voice=voice, output_path=output_path, rate=rate))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_synthesize_edge_tts(clean_text, voice=voice, output_path=output_path, rate=rate))
