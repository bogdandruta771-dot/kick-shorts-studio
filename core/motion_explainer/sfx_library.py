"""
Procedural Sound Effects (SFX) & Ambient Audio Generator
Generates clean, royalty-free audio cues (whooshes, pops, chimes, clicks) programmatically using standard wave/math.
"""
import os
import math
import wave
import struct
import random
from pathlib import Path

SFX_DIR = Path(__file__).parent.parent / "assets" / "sfx"
SFX_DIR.mkdir(parents=True, exist_ok=True)


def _write_wav(filename: str, samples: list, sample_rate: int = 44100):
    path = SFX_DIR / filename
    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        packed = struct.pack(f"<{len(samples)}h", *samples)
        wav_file.writeframes(packed)
    return str(path)


def generate_whoosh_sfx(filename: str = "whoosh.wav", duration: float = 0.35) -> str:
    """Generates an aerodynamic motion whoosh transition sound."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    samples = []
    for i in range(n_samples):
        t = i / n_samples
        # Bell curve envelope
        env = math.sin(t * math.pi) ** 2
        # Frequency sweep from low to high to low
        freq = 150 + 600 * math.sin(t * math.pi)
        # Noise component + sine
        noise = (random.random() * 2 - 1) * 0.4
        tone = math.sin(2 * math.pi * freq * (i / sample_rate)) * 0.6
        val = int((tone + noise) * env * 24000)
        samples.append(max(-32767, min(32767, val)))
    return _write_wav(filename, samples, sample_rate)


def generate_pop_sfx(filename: str = "pop.wav", duration: float = 0.12) -> str:
    """Generates a snappy tactile bubble/card pop sound."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    samples = []
    for i in range(n_samples):
        t = i / n_samples
        env = math.exp(-t * 18)  # Sharp decay
        freq = 700 - 400 * t  # Pitch drop
        tone = math.sin(2 * math.pi * freq * (i / sample_rate))
        val = int(tone * env * 28000)
        samples.append(max(-32767, min(32767, val)))
    return _write_wav(filename, samples, sample_rate)


def generate_chime_sfx(filename: str = "chime.wav", duration: float = 0.6) -> str:
    """Generates a modern digital success/metric chime."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    samples = []
    for i in range(n_samples):
        t = i / n_samples
        env = math.exp(-t * 7)
        # Harmonious dual tone (1046Hz C6 + 1318Hz E6)
        tone1 = math.sin(2 * math.pi * 1046.5 * (i / sample_rate))
        tone2 = math.sin(2 * math.pi * 1318.5 * (i / sample_rate)) * 0.7
        tone3 = math.sin(2 * math.pi * 1567.9 * (i / sample_rate)) * 0.4
        val = int((tone1 + tone2 + tone3) * 0.5 * env * 22000)
        samples.append(max(-32767, min(32767, val)))
    return _write_wav(filename, samples, sample_rate)


def generate_paper_rustle_sfx(filename: str = "paper_slide.wav", duration: float = 0.4) -> str:
    """Generates a newspaper slide/rustle sound."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    samples = []
    for i in range(n_samples):
        t = i / n_samples
        env = math.sin(t * math.pi) * math.exp(-t * 3)
        # Filtered high-frequency noise
        noise = (random.random() * 2 - 1)
        friction = math.sin(2 * math.pi * 1200 * (i / sample_rate)) * 0.2
        val = int((noise * 0.8 + friction) * env * 18000)
        samples.append(max(-32767, min(32767, val)))
    return _write_wav(filename, samples, sample_rate)


def generate_ambient_tech_loop(filename: str = "ambient_loop.wav", duration: float = 20.0) -> str:
    """Generates a subtle, low-frequency suspenseful tech background bed."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    samples = []
    for i in range(n_samples):
        sec = i / sample_rate
        # Sub-bass pulse at 65Hz (C2) with slow 0.5Hz LFO
        lfo = 0.5 + 0.5 * math.sin(2 * math.pi * 0.5 * sec)
        bass = math.sin(2 * math.pi * 65.4 * sec) * (0.3 + 0.15 * lfo)
        # Warm pad harmonic at 130Hz
        pad = math.sin(2 * math.pi * 130.8 * sec) * 0.12
        # Very quiet rhythmic hi-hat pulse every 0.5s
        beat_t = (sec % 0.5) / 0.5
        beat_env = math.exp(-beat_t * 30)
        shaker = (random.random() * 2 - 1) * beat_env * 0.08
        val = int((bass + pad + shaker) * 16000)
        samples.append(max(-32767, min(32767, val)))
    return _write_wav(filename, samples, sample_rate)


def generate_high_energy_gaming_beat(filename: str = "gaming_beat.wav", duration: float = 35.0) -> str:
    """Generates an upbeat 128 BPM electronic trap/gaming beat with punchy kick, snare, hi-hat rolls, and rolling 808 bass."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    samples = []
    
    bpm = 128.0
    beat_sec = 60.0 / bpm  # ~0.46875s per beat
    bar_sec = beat_sec * 4.0
    
    for i in range(n_samples):
        sec = i / sample_rate
        bar_t = sec % bar_sec
        beat_idx = int(bar_t / beat_sec)
        beat_t = (bar_t % beat_sec) / beat_sec
        
        # 1. Punchy Kick Drum on beats 0 and 2 (and syncopated on 2.75)
        kick_val = 0.0
        is_kick = (beat_idx in (0, 2)) or (bar_t > beat_sec * 2.75 and bar_t < beat_sec * 2.75 + 0.15)
        if is_kick:
            k_t = beat_t if beat_idx in (0, 2) else ((bar_t - beat_sec * 2.75) / beat_sec)
            if 0 <= k_t <= 0.35:
                k_env = math.exp(-k_t * 16)
                k_freq = 130 * math.exp(-k_t * 22) + 48
                kick_val = math.sin(2 * math.pi * k_freq * sec) * k_env * 0.75
                # Click transient
                if k_t < 0.02:
                    kick_val += (random.random() * 2 - 1) * 0.35
        
        # 2. Snappy Snare / Clap on beats 1 and 3
        snare_val = 0.0
        if beat_idx in (1, 3):
            s_t = beat_t
            if 0 <= s_t <= 0.28:
                s_env = math.exp(-s_t * 15)
                s_noise = (random.random() * 2 - 1) * s_env * 0.55
                s_body = math.sin(2 * math.pi * 210 * sec) * math.exp(-s_t * 25) * 0.4
                snare_val = s_noise + s_body
        
        # 3. Trap Hi-Hat rolls every 1/8th note (and 1/16th in second half)
        hat_interval = beat_sec / 2.0
        hat_t = (sec % hat_interval) / hat_interval
        h_env = math.exp(-hat_t * 40)
        hat_val = (random.random() * 2 - 1) * h_env * 0.18
        
        # 4. Driving 808 Bass Line
        bass_note = 55.0  # A1
        if beat_idx == 2:
            bass_note = 65.4  # C2
        elif beat_idx == 3:
            bass_note = 49.0  # G1
        bass_env = 0.45 + 0.35 * math.sin(2 * math.pi * (1.0 / beat_sec) * sec)
        bass_val = math.sin(2 * math.pi * bass_note * sec) * bass_env * 0.45
        # Soft saturation / overdrive warmth
        bass_val = math.tanh(bass_val * 1.6)
        
        # Synth arp lead melody (Gaming vibe)
        arp_notes = [440, 523.25, 659.25, 783.99, 880]  # A minor pentatonic
        arp_idx = int((sec * (bpm / 15.0))) % len(arp_notes)
        arp_freq = arp_notes[arp_idx]
        arp_t = (sec % (60.0 / (bpm * 2))) / (60.0 / (bpm * 2))
        arp_env = math.exp(-arp_t * 14)
        synth_val = math.sin(2 * math.pi * arp_freq * sec) * arp_env * 0.12
        
        mixed = kick_val + snare_val + hat_val + bass_val + synth_val
        val = int(max(-1.0, min(1.0, mixed)) * 26000)
        samples.append(val)
        
    return _write_wav(filename, samples, sample_rate)


def generate_cash_register_sfx(filename: str = "cash_register.wav", duration: float = 0.5) -> str:
    """Generates a crisp 'cha-ching' cash register / trading profit sound."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    samples = []
    for i in range(n_samples):
        sec = i / sample_rate
        # Part 1: Initial metallic coin clink
        env1 = math.exp(-sec * 12)
        ping1 = math.sin(2 * math.pi * 2637 * sec) * env1 * 0.5
        ping2 = math.sin(2 * math.pi * 3136 * sec) * env1 * 0.4
        
        # Part 2: Register mechanical latch at 0.15s
        env2 = math.exp(-max(0.0, sec - 0.15) * 16) if sec >= 0.15 else 0.0
        ratchet = (random.random() * 2 - 1) * env2 * 0.35
        bell = math.sin(2 * math.pi * 3951 * (sec - 0.15)) * env2 * 0.6 if sec >= 0.15 else 0.0
        
        mixed = ping1 + ping2 + ratchet + bell
        val = int(max(-1.0, min(1.0, mixed)) * 28000)
        samples.append(val)
    return _write_wav(filename, samples, sample_rate)


def generate_case_unlock_sfx(filename: str = "case_unlock.wav", duration: float = 0.75) -> str:
    """Generates a CS2 case unlocking click and golden rare item arpeggio chime."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    samples = []
    chords = [1046.5, 1318.5, 1567.9, 2093.0]  # C6 -> E6 -> G6 -> C7
    for i in range(n_samples):
        sec = i / sample_rate
        # Click at start
        click = 0.0
        if sec < 0.08:
            click = (random.random() * 2 - 1) * math.exp(-sec * 60) * 0.7
            
        # Arpeggio chime
        chime_val = 0.0
        step_len = 0.12
        for idx, freq in enumerate(chords):
            t_offset = 0.08 + idx * step_len
            if sec >= t_offset:
                note_t = sec - t_offset
                env = math.exp(-note_t * 8)
                chime_val += math.sin(2 * math.pi * freq * note_t) * env * 0.28
                
        mixed = click + chime_val
        val = int(max(-1.0, min(1.0, mixed)) * 26000)
        samples.append(val)
    return _write_wav(filename, samples, sample_rate)


def generate_heavy_impact_sfx(filename: str = "heavy_impact.wav", duration: float = 0.6) -> str:
    """Generates a heavy bass drop / impact boom for high-stakes gaming transitions."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    samples = []
    for i in range(n_samples):
        sec = i / sample_rate
        env = math.exp(-sec * 5.5)
        freq = 110 * math.exp(-sec * 10) + 38
        sub = math.sin(2 * math.pi * freq * sec) * env * 0.8
        noise = (random.random() * 2 - 1) * math.exp(-sec * 18) * 0.35
        val = int(max(-1.0, min(1.0, sub + noise)) * 30000)
        samples.append(val)
    return _write_wav(filename, samples, sample_rate)


def ensure_sfx_library() -> dict:
    """Ensures all required SFX files exist and returns a mapping of sfx_name -> filepath."""
    return {
        "whoosh": generate_whoosh_sfx(),
        "pop": generate_pop_sfx(),
        "chime": generate_chime_sfx(),
        "paper_slide": generate_paper_rustle_sfx(),
        "ambient_music": generate_ambient_tech_loop(),
        "gaming_beat": generate_high_energy_gaming_beat(),
        "cash_register": generate_cash_register_sfx(),
        "case_unlock": generate_case_unlock_sfx(),
        "heavy_impact": generate_heavy_impact_sfx(),
    }


if __name__ == "__main__":
    lib = ensure_sfx_library()
    print("Generated procedural SFX library successfully:", lib)
