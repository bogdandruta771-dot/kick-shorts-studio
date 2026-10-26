"""
Kinetic Transitions Engine for Motion Explainer Shorts
Provides smooth 3-phase lifecycle transforms (Entry -> Settle/Float -> Exit/Return):
- Rapid ease-out spring entry from bottom, left, right, or zoom
- Organic subtle breathing / bobbing during hold
- Accelerated ease-in exit / return before the next element and text arrive
- Text synchronization helpers for kinetic typography
"""
import math
from typing import Tuple, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFilter


def ease_out_back(t: float, s: float = 1.35) -> float:
    """Overshoot spring ease-out for punchy kinetic entry."""
    t = max(0.0, min(1.0, t)) - 1.0
    return t * t * ((s + 1.0) * t + s) + 1.0


def ease_out_cubic(t: float) -> float:
    """Smooth cubic deceleration."""
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def ease_in_cubic(t: float) -> float:
    """Accelerated cubic exit."""
    t = max(0.0, min(1.0, t))
    return t ** 2.6


def compute_kinetic_transform(
    progress: float,            # 0.0 to 1.0 within element lifecycle
    entry_dur: float = 0.20,    # portion of time for entry (e.g. 20%)
    exit_dur: float = 0.16,     # portion of time for exit (e.g. 16%)
    direction: str = "bottom",  # default direction if entry/exit not specified
    slide_distance: int = 750,  # pixels to slide
    entry_direction: Optional[str] = None, # "left", "right", "bottom", "top", "zoom"
    exit_direction: Optional[str] = None,  # "left", "right", "bottom", "top", "zoom"
    max_tilt_deg: float = 3.5,  # angular inertia tilt during horizontal travel
) -> Tuple[float, float, float, float, float]:
    """
    Computes (offset_x, offset_y, scale, alpha, rotation_deg) for any visual card or text block.
    
    Phases:
    1. Entry (0.0 -> entry_dur):
       Slides in from entry_direction with ease-out bounce, kinetic tilt, scaling and alpha fade.
    2. Hold / Settle (entry_dur -> 1.0 - exit_dur):
       Resting in center (0, 0), scale = 1.0, alpha = 1.0, rotation = 0.0.
    3. Exit / Return (1.0 - exit_dur -> 1.0):
       Slides off in exit_direction with accelerated cubic speed and exit tilt.
    """
    progress = max(0.0, min(1.0, progress))
    in_dir = entry_direction or direction
    out_dir = exit_direction or direction
    
    # -------------------------------------------------------------
    # PHASE 1: ENTRY (Comes in from side, bottom, etc.)
    # -------------------------------------------------------------
    if progress < entry_dur:
        u = progress / max(0.01, entry_dur)
        e = ease_out_back(u, s=1.28)
        scale = 0.88 + 0.12 * e
        alpha = min(1.0, 0.30 + u * 1.1)
        
        inv_e = 1.0 - e
        rotation_deg = 0.0
        
        if in_dir == "left":
            offset_x = -slide_distance * inv_e
            offset_y = 0.0
            rotation_deg = -max_tilt_deg * inv_e
        elif in_dir == "right":
            offset_x = slide_distance * inv_e
            offset_y = 0.0
            rotation_deg = max_tilt_deg * inv_e
        elif in_dir == "bottom":
            offset_x = 0.0
            offset_y = slide_distance * inv_e
        elif in_dir == "top":
            offset_x = 0.0
            offset_y = -slide_distance * inv_e
        elif in_dir in ("zoom", "pop"):
            offset_x = 0.0
            offset_y = 0.0
            scale = 0.25 + 0.75 * e
        elif in_dir == "diagonal_tl":
            offset_x = -slide_distance * 0.72 * inv_e
            offset_y = -slide_distance * 0.72 * inv_e
            rotation_deg = -max_tilt_deg * 0.85 * inv_e
        elif in_dir == "diagonal_tr":
            offset_x = slide_distance * 0.72 * inv_e
            offset_y = -slide_distance * 0.72 * inv_e
            rotation_deg = max_tilt_deg * 0.85 * inv_e
        else:
            offset_x = 0.0
            offset_y = slide_distance * inv_e
            
        return offset_x, offset_y, scale, alpha, rotation_deg

    # -------------------------------------------------------------
    # PHASE 3: EXIT / RETURN (Slides off in exit direction)
    # -------------------------------------------------------------
    elif progress > (1.0 - exit_dur):
        exit_start = 1.0 - exit_dur
        u = (progress - exit_start) / max(0.01, exit_dur)
        e = ease_in_cubic(u)
        
        scale = 1.0 - 0.06 * e
        alpha = max(0.0, 1.0 - u * 0.40)
        rotation_deg = 0.0
        
        if out_dir == "left":
            offset_x = -slide_distance * e
            offset_y = 0.0
            rotation_deg = -max_tilt_deg * 1.15 * e
        elif out_dir == "right":
            offset_x = slide_distance * e
            offset_y = 0.0
            rotation_deg = max_tilt_deg * 1.15 * e
        elif out_dir == "bottom":
            offset_x = 0.0
            offset_y = slide_distance * e
        elif out_dir == "top":
            offset_x = 0.0
            offset_y = -slide_distance * e
        elif out_dir in ("zoom", "pop"):
            offset_x = 0.0
            offset_y = 0.0
            scale = max(0.1, 1.0 - 0.65 * e)
        elif out_dir == "diagonal_tl":
            offset_x = -slide_distance * 0.72 * e
            offset_y = -slide_distance * 0.72 * e
            rotation_deg = -max_tilt_deg * 0.85 * e
        elif out_dir == "diagonal_tr":
            offset_x = slide_distance * 0.72 * e
            offset_y = -slide_distance * 0.72 * e
            rotation_deg = max_tilt_deg * 0.85 * e
        else:
            offset_x = 0.0
            offset_y = slide_distance * e
            
        return offset_x, offset_y, scale, alpha, rotation_deg

    # -------------------------------------------------------------
    # PHASE 2: HOLD / SETTLE
    # -------------------------------------------------------------
    else:
        return 0.0, 0.0, 1.0, 1.0, 0.0


def apply_alpha_to_image(img: Image.Image, alpha: float) -> Image.Image:
    """Multiplies an RGBA image's alpha channel by alpha (0.0 to 1.0)."""
    if alpha >= 0.999:
        return img
    if alpha <= 0.001:
        return Image.new("RGBA", img.size, (0, 0, 0, 0))
    
    r, g, b, a = img.split()
    a = a.point(lambda p: int(p * alpha))
    out = Image.new("RGBA", img.size)
    out.paste(img, (0, 0))
    out.putalpha(a)
    return out


def composite_kinetic_element(
    canvas: Image.Image,
    element: Image.Image,
    target_center: Tuple[int, int],
    progress: float,
    global_time: float,
    entry_dur: float = 0.20,
    exit_dur: float = 0.16,
    direction: str = "bottom",
    slide_distance: int = 750,
    bob_amplitude: float = 8.0,
    bob_speed: float = 2.5,
    entry_direction: Optional[str] = None,
    exit_direction: Optional[str] = None,
    max_tilt_deg: float = 3.5,
) -> None:
    """
    Renders element onto canvas with full 3-phase kinetic transform:
    Entry (slide in & spring & tilt) -> Hold (subtle float/bob) -> Exit/Return (slide out).
    """
    offset_x, offset_y, scale, alpha, rotation_deg = compute_kinetic_transform(
        progress=progress,
        entry_dur=entry_dur,
        exit_dur=exit_dur,
        direction=direction,
        slide_distance=slide_distance,
        entry_direction=entry_direction,
        exit_direction=exit_direction,
        max_tilt_deg=max_tilt_deg,
    )
    
    if alpha <= 0.005:
        return

    # Add gentle organic bobbing during hold
    bob_y = math.sin(global_time * bob_speed) * bob_amplitude
    
    # Resize according to scale
    target_w = max(4, int(element.width * scale))
    target_h = max(4, int(element.height * scale))
    
    if target_w != element.width or target_h != element.height:
        scaled_img = element.resize((target_w, target_h), resample=Image.BICUBIC)
    else:
        scaled_img = element

    # Apply kinetic rotational tilt if element is in motion
    if abs(rotation_deg) > 0.05:
        scaled_img = scaled_img.rotate(rotation_deg, resample=Image.BICUBIC, expand=True)

    if alpha < 0.999:
        scaled_img = apply_alpha_to_image(scaled_img, alpha)

    tx, ty = target_center
    paste_x = int(tx - scaled_img.width // 2 + offset_x)
    paste_y = int(ty - scaled_img.height // 2 + offset_y + bob_y)

    canvas.paste(scaled_img, (paste_x, paste_y), scaled_img)
