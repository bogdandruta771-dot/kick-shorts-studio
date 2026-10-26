"""
Master Generator for Authentic Tradeit.gg Affiliate Videos.
- Matches reference ad ready (2).mp4 and user CapCut screen recording.
- Real skins and authentic CS2 inventory visuals.
- ElevenLabs Liam TTS (energetic social media creator, zero robotic tremor).
- Seamless append of CapCut screen recording outro typing 'mesto300'.
"""
import os
import sys
import json
import time
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

# Reconfigure stdout/stderr for Windows UTF-8
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.resolve()
load_dotenv(PROJECT_ROOT / ".env")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.motion_explainer.tradeit_assets import render_tradeit_scene_frame
from core.motion_explainer.voice_engine import synthesize_speech, probe_audio_duration
from core.motion_explainer.sfx_library import ensure_sfx_library
from core.config import OUTPUT_DIR

ASSETS_DIR = PROJECT_ROOT / "assets" / "tradeit"
CAPCUT_OUTRO = ASSETS_DIR / "capcut_outro_clean.mp4"

VIDEOS_CONFIG = [
    {
        "id": "tradeit_authentic_v1",
        "title": "Stop! Don't Confirm Your CS2 Trade (Authentic Liam)",
        "promocode": "MESTO300",
        "scenes": [
            {
                "scene_num": 1,
                "voice_text": "Stop! Don't confirm your next CS2 trade until you do this.",
                "duration": 3.8,
            },
            {
                "scene_num": 2,
                "voice_text": "Your trade is missing one item, and it isn't in your Steam inventory.",
                "duration": 4.5,
            },
            {
                "scene_num": 3,
                "voice_text": "Go to tradeit.gg and enter code MESTO300.",
                "duration": 4.8,
            },
            {
                "scene_num": 4,
                "voice_text": "The code adds a bonus to your balance before you choose your upgrade.",
                "duration": 4.6,
            },
            {
                "scene_num": 5,
                "voice_text": "Now add the skins you no longer use and see what the complete trade can get you.",
                "duration": 4.5,
            },
            {
                "scene_num": 6,
                "voice_text": "The most useful item in your next trade might be the one you can't equip.",
                "duration": 5.0,
            },
        ],
    },
    {
        "id": "tradeit_authentic_v2",
        "title": "The Hidden CS2 Knife Glitch (Authentic Liam)",
        "promocode": "MESTO300",
        "scenes": [
            {
                "scene_num": 1,
                "voice_text": "Stop! You are making a huge mistake on your CS2 trades.",
                "duration": 3.6,
            },
            {
                "scene_num": 2,
                "voice_text": "Steam takes fifteen percent of every item, leaving you with less value every time.",
                "duration": 4.6,
            },
            {
                "scene_num": 3,
                "voice_text": "Head straight over to tradeit.gg and use code MESTO300 right now.",
                "duration": 4.6,
            },
            {
                "scene_num": 4,
                "voice_text": "It instantly drops a free bonus balance directly into your account.",
                "duration": 4.4,
            },
            {
                "scene_num": 5,
                "voice_text": "Swap your old unused skins and instantly upgrade into high tier knives.",
                "duration": 4.5,
            },
            {
                "scene_num": 6,
                "voice_text": "Check your inventory, enter code MESTO300, and claim your upgrade today.",
                "duration": 4.8,
            },
        ],
    },
    {
        "id": "tradeit_authentic_v3",
        "title": "Upgrade Your CS2 Inventory Instantly (Authentic Liam)",
        "promocode": "MESTO300",
        "scenes": [
            {
                "scene_num": 1,
                "voice_text": "Stop! Before you accept that trade, check this out.",
                "duration": 3.6,
            },
            {
                "scene_num": 2,
                "voice_text": "Instead of losing value on the Steam market, there is a much smarter move.",
                "duration": 4.5,
            },
            {
                "scene_num": 3,
                "voice_text": "Open tradeit.gg and activate promo code MESTO300 today.",
                "duration": 4.5,
            },
            {
                "scene_num": 4,
                "voice_text": "You get a free five dollar balance bonus loaded before you even pick your skin.",
                "duration": 4.8,
            },
            {
                "scene_num": 5,
                "voice_text": "Trade in your battle-scarred playskins and grab instant factory new covert upgrades.",
                "duration": 4.8,
            },
            {
                "scene_num": 6,
                "voice_text": "Hit the link, type code MESTO300, and get your dream loadout.",
                "duration": 4.5,
            },
        ],
    },
]


def render_authentic_video(video_cfg: Dict[str, Any], fps: int = 30) -> str:
    print(f"\n=======================================================")
    print(f"🎬 Generating: {video_cfg['title']}")
    print(f"=======================================================")
    
    scenes = video_cfg["scenes"]
    promocode = video_cfg["promocode"]
    
    # 1. Voiceover synthesis with ElevenLabs Liam
    full_text = " ".join(s["voice_text"] for s in scenes)
    print(f"🎙️ Synthesizing voiceover with ElevenLabs Liam ({len(full_text)} chars)...")
    voice_res = synthesize_speech(full_text, voice="eleven_liam")
    if not voice_res.get("success"):
        raise RuntimeError("Voice synthesis failed!")
        
    voice_audio_path = voice_res["audio_path"]
    total_audio_dur = voice_res["duration"]
    print(f"✓ Voiceover ready: {total_audio_dur:.2f}s -> {voice_audio_path}")
    
    # Calculate scene timings proportional to text length
    text_lens = [max(1, len(s["voice_text"])) for s in scenes]
    total_chars = sum(text_lens)
    scene_durations = [round(total_audio_dur * (tl / total_chars), 3) for tl in text_lens]
    diff = total_audio_dur - sum(scene_durations)
    scene_durations[-1] = round(scene_durations[-1] + diff, 3)
    
    # 2. Render frames for the motion explainer section
    temp_dir = Path(tempfile.mkdtemp(prefix="tradeit_auth_"))
    frames_dir = temp_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🎨 Rendering motion graphic frames (1080x1920 @ {fps}fps)...")
    current_frame = 0
    t0 = time.time()
    
    for s_idx, (scene, s_dur) in enumerate(zip(scenes, scene_durations)):
        s_frames = int(s_dur * fps)
        s_num = scene["scene_num"]
        for f in range(s_frames):
            s_prog = f / max(1, s_frames)
            global_sec = current_frame / fps
            
            frame_img = render_tradeit_scene_frame(
                scene_num=s_num,
                scene_progress=s_prog,
                global_time=global_sec,
                code=promocode,
                width=1080,
                height=1920,
            )
            
            frame_path = frames_dir / f"frame_{current_frame:05d}.jpg"
            if frame_img.mode != "RGB":
                frame_img = frame_img.convert("RGB")
            frame_img.save(frame_path, quality=92)
            current_frame += 1
            
    print(f"✓ Rendered {current_frame} frames in {time.time() - t0:.1f}s")
    
    # 3. Assemble motion explainer portion with SFX
    sfx_lib = ensure_sfx_library()
    first_video_segment = temp_dir / "segment1.mp4"
    
    # Prepare SFX cues
    sfx_cues = [
        (0.0, sfx_lib.get("heavy_impact", sfx_lib["whoosh"]), 0.7),
        (scene_durations[0], sfx_lib.get("pop", sfx_lib["whoosh"]), 0.6),
        (scene_durations[0] + scene_durations[1], sfx_lib.get("cash_register", sfx_lib["pop"]), 0.7),
        (sum(scene_durations[:3]), sfx_lib.get("case_unlock", sfx_lib["pop"]), 0.7),
        (sum(scene_durations[:4]), sfx_lib.get("chime", sfx_lib["pop"]), 0.6),
        (sum(scene_durations[:5]), sfx_lib.get("heavy_impact", sfx_lib["whoosh"]), 0.7),
    ]
    
    audio_inputs = ["-i", voice_audio_path]
    filter_complex = ["[0:a]volume=1.0[voice];"]
    sfx_tags = []
    
    idx = 1
    for t_sec, sfx_file, vol in sfx_cues:
        if os.path.exists(sfx_file):
            audio_inputs.extend(["-i", sfx_file])
            delay_ms = int(t_sec * 1000)
            filter_complex.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms},volume={vol * 0.4}[sfx_{idx}];")
            sfx_tags.append(f"[sfx_{idx}]")
            idx += 1
            
    total_audio_streams = 1 + len(sfx_tags)
    filter_complex.append(f"[voice]{''.join(sfx_tags)}amix=inputs={total_audio_streams}:duration=first:dropout_transition=0:normalize=0[aout]")
    
    mixed_audio_file = temp_dir / "mixed_audio.wav"
    subprocess.run([
        "ffmpeg", "-y",
        *audio_inputs,
        "-filter_complex", "".join(filter_complex),
        "-map", "[aout]",
        "-t", str(total_audio_dur),
        str(mixed_audio_file)
    ], capture_output=True, check=True)
    
    # Encode segment 1
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frames_dir / "frame_%05d.jpg"),
        "-i", str(mixed_audio_file),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-shortest",
        str(first_video_segment)
    ], capture_output=True, check=True)
    print(f"✓ Segment 1 encoded ({total_audio_dur:.2f}s)")
    
    # 4. Seamlessly append CapCut Outro (1017.mp4)
    final_output_file = OUTPUT_DIR / f"{video_cfg['id']}_{int(time.time())}.mp4"
    print(f"🔗 Appending authentic CapCut outro screen recording...")
    
    # Concat filter in ffmpeg for seamless timing and audio match
    concat_cmd = [
        "ffmpeg", "-y",
        "-i", str(first_video_segment),
        "-i", str(CAPCUT_OUTRO),
        "-filter_complex",
        "[0:v]fps=30,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[v0];"
        "[1:v]fps=30,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[v1];"
        "[0:a]aformat=sample_rates=44100:channel_layouts=stereo[a0];"
        "[1:a]aformat=sample_rates=44100:channel_layouts=stereo[a1];"
        "[v0][a0][v1][a1]concat=n=2:v=1:a=1[vfinal][afinal]",
        "-map", "[vfinal]",
        "-map", "[afinal]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        str(final_output_file)
    ]
    
    res = subprocess.run(concat_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Concat Error: {res.stderr}")
        raise RuntimeError(f"FFmpeg concat failed: {res.stderr}")
        
    # Clean up temp
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    final_dur = probe_audio_duration(str(final_output_file))
    print(f"🎉 Complete! Final authentic affiliate video: {final_output_file.name} ({final_dur:.2f}s)")
    return str(final_output_file)


if __name__ == "__main__":
    generated_files = []
    for cfg in VIDEOS_CONFIG:
        path = render_authentic_video(cfg, fps=30)
        generated_files.append(path)
        
    print("\n=======================================================")
    print("🚀 All 3 Authentic Affiliate Videos Generated Successfully:")
    for p in generated_files:
        print(" - ", p)
    print("=======================================================")
