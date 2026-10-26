"""
OmniStudio Master Synchronizer:
Generates the authentic TradeIt affiliate video with 100% frame-by-frame synchronization
between ElevenLabs Liam voiceover and the visual kinetic animations.
- Scene 1: "Stop! Don't confirm your next CS2 trade until you do this." -> Steam PROCEED button with STOP! slam & handshake badge
- Scene 2: "Your trade is missing one item, and it isn't in your Steam inventory." -> MISSING ITEM? bar & 5x5 Steam inventory grid with prohibition badge
- Scene 3: "Go to tradeit.gg and enter code MESTO300." -> TradeIt homepage card, dropdown menu, and modal typing MESTO300
- Scene 4: "The code adds a bonus to your balance before you choose your upgrade." -> Balance bar toast & glowing upgrade arrows
- Scene 5: "Now add the skins you no longer use and see what the complete trade can get you." -> Real priced CS2 skins grid with cursor click
- Scene 6: "The most useful item in your next trade might be the one you can't equip." -> Trio of dream skins & outro CTA
- Outro: Seamless CapCut 1017.mp4 real screen recording typing mesto300
"""
import os
import sys

# Reconfigure stdout/stderr for Windows UTF-8
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import time
import shutil
import tempfile
import subprocess
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.resolve()
load_dotenv(PROJECT_ROOT / ".env")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.motion_explainer.tradeit_assets import render_tradeit_scene_frame
from core.motion_explainer.voice_engine import synthesize_speech, probe_audio_duration
from core.motion_explainer.sfx_library import ensure_sfx_library
from core.config import OUTPUT_DIR

SCRATCH_DIR = PROJECT_ROOT / "scratch"
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
CAPCUT_OUTRO = PROJECT_ROOT / "assets" / "tradeit" / "capcut_outro_clean.mp4"

SCENES_DEF = [
    {
        "scene_num": 1,
        "voice_text": "Stop! Don't confirm your next CS2 trade until you do this.",
        "sfx": "heavy_impact",
        "audio_file": SCRATCH_DIR / "scene_1.mp3",
    },
    {
        "scene_num": 2,
        "voice_text": "Your trade is missing one item, and it isn't in your Steam inventory.",
        "sfx": "whoosh",
        "audio_file": SCRATCH_DIR / "scene_2.mp3",
    },
    {
        "scene_num": 3,
        "voice_text": "Go to tradeit.gg and enter code MESTO300.",
        "sfx": "cash_register",
        "audio_file": SCRATCH_DIR / "scene_3.mp3",
    },
    {
        "scene_num": 4,
        "voice_text": "The code adds a bonus to your balance before you choose your upgrade.",
        "sfx": "case_unlock",
        "audio_file": SCRATCH_DIR / "scene_4.mp3",
    },
    {
        "scene_num": 5,
        "voice_text": "Now add the skins you no longer use and see what the complete trade can get you.",
        "sfx": "chime",
        "audio_file": SCRATCH_DIR / "scene_5.mp3",
    },
    {
        "scene_num": 6,
        "voice_text": "The most useful item in your next trade might be the one you can't equip.",
        "sfx": "pop",
        "audio_file": SCRATCH_DIR / "scene_6.mp3",
    },
]


def build_synchronized_master_video(fps: int = 30) -> str:
    print("=" * 60)
    print("🎬 RENDERING 100% SYNCHRONIZED AUTHENTIC TRADEIT VIDEO")
    print("=" * 60)

    # 1. Verify / generate per-scene speech clips for precise timing
    scene_durations = []
    audio_paths = []
    for sc in SCENES_DEF:
        p = sc["audio_file"]
        if not p.exists():
            print(f"🎙️ Synthesizing Scene {sc['scene_num']}: \"{sc['voice_text']}\"")
            res = synthesize_speech(sc["voice_text"], voice="eleven_liam", output_path=str(p))
            dur = res["duration"]
        else:
            dur = probe_audio_duration(str(p))
        print(f"✓ Scene {sc['scene_num']} audio: {dur:.2f}s -> {sc['voice_text'][:35]}...")
        scene_durations.append(dur)
        audio_paths.append(str(p))

    total_motion_duration = sum(scene_durations)
    print(f"\n📊 Total Explainer Duration: {total_motion_duration:.2f}s across 6 perfectly synced scenes.")

    # 2. Concatenate voiceover clips with exact timing
    concat_list_file = SCRATCH_DIR / "voice_concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for ap in audio_paths:
            # Escape path for ffmpeg concat
            clean_p = ap.replace("\\", "/")
            f.write(f"file '{clean_p}'\n")

    full_voice_path = SCRATCH_DIR / "full_synchronized_voice.wav"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c:a", "pcm_s16le",
        "-ar", "44100",
        "-ac", "2",
        str(full_voice_path)
    ], capture_output=True, check=True)
    print(f"✓ Master voice track assembled ({probe_audio_duration(str(full_voice_path)):.2f}s)")

    # 3. Render frames with per-scene progress u in [0.0, 1.0] matching voice timing
    temp_dir = Path(tempfile.mkdtemp(prefix="synced_render_"))
    frames_dir = temp_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🎨 Rendering visual frames (1080x1920 @ {fps}fps)...")
    current_frame = 0
    t0 = time.time()

    for s_idx, (sc, s_dur) in enumerate(zip(SCENES_DEF, scene_durations)):
        s_num = sc["scene_num"]
        s_frames = int(round(s_dur * fps))
        print(f"  Rendering Scene {s_num}: {s_dur:.2f}s ({s_frames} frames)...")

        for f in range(s_frames):
            s_prog = f / max(1, s_frames)
            global_sec = current_frame / fps

            frame_img = render_tradeit_scene_frame(
                scene_num=s_num,
                scene_progress=s_prog,
                global_time=global_sec,
                code="MESTO300",
                width=1080,
                height=1920,
            )

            if frame_img.mode != "RGB":
                frame_img = frame_img.convert("RGB")

            frame_path = frames_dir / f"frame_{current_frame:05d}.jpg"
            frame_img.save(frame_path, quality=92)
            current_frame += 1

    print(f"✓ Successfully rendered {current_frame} frames in {time.time() - t0:.1f}s")

    # 4. Mix voiceover with synchronized SFX
    sfx_lib = ensure_sfx_library()
    audio_inputs = ["-i", str(full_voice_path)]
    filter_complex = ["[0:a]volume=1.0[voice];"]
    sfx_tags = []

    accum_t = 0.0
    for idx, (sc, dur) in enumerate(zip(SCENES_DEF, scene_durations), start=1):
        sfx_key = sc.get("sfx")
        if sfx_key and sfx_key in sfx_lib:
            sfx_file = sfx_lib[sfx_key]
            if os.path.exists(sfx_file):
                audio_inputs.extend(["-i", sfx_file])
                delay_ms = int(accum_t * 1000)
                filter_complex.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms},volume=0.35[sfx_{idx}];")
                sfx_tags.append(f"[sfx_{idx}]")
        accum_t += dur

    total_audio_streams = 1 + len(sfx_tags)
    filter_complex.append(f"[voice]{''.join(sfx_tags)}amix=inputs={total_audio_streams}:duration=first:dropout_transition=0:normalize=0[aout]")

    mixed_audio_file = temp_dir / "mixed_audio.wav"
    subprocess.run([
        "ffmpeg", "-y",
        *audio_inputs,
        "-filter_complex", "".join(filter_complex),
        "-map", "[aout]",
        "-t", str(total_motion_duration),
        str(mixed_audio_file)
    ], capture_output=True, check=True)

    # 5. Encode Motion Explainer Segment
    segment1_path = temp_dir / "segment1.mp4"
    print("\n📦 Encoding Motion Explainer segment (1080x1920 libx264)...")
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
        str(segment1_path)
    ], capture_output=True, check=True)

    # 6. Seamlessly Concat CapCut Outro (1017.mp4)
    final_output_file = OUTPUT_DIR / f"tradeit_synced_perfect_{int(time.time())}.mp4"
    print(f"\n🔗 Appending CapCut screen recording outro...")

    concat_cmd = [
        "ffmpeg", "-y",
        "-i", str(segment1_path),
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

    shutil.rmtree(temp_dir, ignore_errors=True)
    final_dur = probe_audio_duration(str(final_output_file))
    print(f"\n🎉 DONE! Perfect Synchronized Video Created:")
    print(f"👉 File: {final_output_file} ({final_dur:.2f}s)")
    return str(final_output_file)


if __name__ == "__main__":
    build_synchronized_master_video(fps=30)
