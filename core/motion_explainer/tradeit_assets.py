"""
TradeIt Authentic Ad Scene Compositor and Kinetic Motion Engine
Faithfully reproduces the authentic TradeIt motion ad style:
- Organic wavy violet grid background plate with ambient glow pulses
- Georgia Bold Italic typography with neon green, electric cyan, and crimson highlights
- 3-Phase Kinetic Transitions: Elements and text slide in from bottom/side with ease-out bounce,
  settle with subtle organic float, and return/dip downwards before the next element arrives
- Custom image support per scene with auto-fit, rounded corners, and drop shadow
- Steam trade 'STOP!' slam and prohibition badge
- CS2 Trade exchange 'MISSING ITEM ?' strip and 5x5 Steam inventory grid
- TradeIt homepage card, profile dropdown, and animated coupon redemption modal typing MESTO300
- TradeIt balance bar with animated '✓ Coupon Code applied successfully' toast
- Glowing green upgrade triangle arrows
- TradeIt priced skin grid with cursor selection
- Trio of floating dream skins & high-contrast Outro CTA
"""
import os
import math
import re
import uuid
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from core.motion_explainer.kinetic_transitions import (
    compute_kinetic_transform,
    composite_kinetic_element,
    apply_alpha_to_image,
)

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"
TRADEIT_DIR = ASSETS_DIR / "tradeit"

# System Fonts
FONT_SERIF_BI = "C:/Windows/Fonts/georgiaz.ttf"      # Georgia Bold Italic
FONT_SANS_BOLD = "C:/Windows/Fonts/segoeuib.ttf"     # Segoe UI Bold
FONT_SANS_REG = "C:/Windows/Fonts/segoeui.ttf"       # Segoe UI Regular

COLOR_WHITE = (255, 255, 255)
COLOR_NEON_GREEN = (0, 255, 65)
COLOR_ELECTRIC_CYAN = (56, 182, 255)
COLOR_CRIMSON = (255, 42, 85)
COLOR_YELLOW = (255, 255, 34)
COLOR_MUTED_GREY = (160, 160, 180)


def _load_asset(filename: str) -> Optional[Image.Image]:
    p = TRADEIT_DIR / filename
    if p.exists():
        try:
            return Image.open(p).convert("RGBA")
        except Exception:
            return None
    return None


def make_rounded_card(img: Image.Image, radius: int = 36, shadow_blur: int = 24, shadow_alpha: int = 160) -> Image.Image:
    """Wraps an image in smooth rounded corners with anti-aliasing and a soft drop shadow."""
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)

    rounded = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rounded.paste(img, (0, 0), mask)

    pad = shadow_blur * 2
    shadow_w = w + pad * 2
    shadow_h = h + pad * 2
    shadow = Image.new("RGBA", (shadow_w, shadow_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rounded_rectangle([pad, pad + 12, pad + w, pad + h + 12], radius=radius, fill=(0, 0, 0, shadow_alpha))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
    shadow.paste(rounded, (pad, pad), rounded)
    return shadow


def make_circular_badge(img: Image.Image, shadow_blur: int = 22, shadow_alpha: int = 180) -> Image.Image:
    """Wraps a badge image in a circular mask with soft drop shadow."""
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.ellipse([8, 8, w - 8, h - 8], fill=255)

    circ = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    circ.paste(img, (0, 0), mask)

    pad = shadow_blur * 2
    shadow = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.ellipse([pad + 6, pad + 14, pad + w - 6, pad + h + 14], fill=(0, 0, 0, shadow_alpha))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
    shadow.paste(circ, (pad, pad), circ)
    return shadow


def get_tradeit_background(width: int = 1080, height: int = 1920, time_sec: float = 0.0) -> Image.Image:
    """
    Returns the dynamic living synth background matching ready (2).mp4:
    - Shifts mood & color palette across scenes (Violet -> Cold Slate Navy -> Peach Flare -> Magenta/Blue -> Obsidian -> Olive Green)
    - Moving atmospheric spotlight beams with Gaussian diffusion
    """
    bg = _load_asset("tradeit_bg.jpg")
    if bg is None:
        bg = Image.new("RGBA", (width, height), (22, 19, 36, 255))
    else:
        if bg.size != (width, height):
            bg = bg.resize((width, height), resample=Image.BICUBIC)

    sw, sh = 270, 480
    small_overlay = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(small_overlay)

    # Calculate dynamic scene atmosphere based on time_sec
    if time_sec < 4.0:
        # Scene 1: Electric Violet
        breath = math.sin(time_sec * 1.8) * 0.5 + 0.5
        tint = (30, 10, 48, int(35 + 15 * breath))
        d.ellipse([sw - 95, int(sh * 0.12), sw + 45, int(sh * 0.88)], fill=(160, 60, 240, int(70 + 20 * breath)))
    elif time_sec < 8.4:
        # Scene 2: Cold Slate Navy & Cyan Ray
        breath = math.sin(time_sec * 1.5) * 0.5 + 0.5
        tint = (5, 22, 38, int(50 + 15 * breath))
        d.ellipse([sw - 110, -30, sw + 35, int(sh * 0.50)], fill=(0, 180, 255, int(75 + 15 * breath)))
    elif time_sec < 8.95:
        # Fiery Peach / Amber Flare Transition (8.4s -> 8.95s, peak at 8.65s)
        p = max(0.0, min(1.0, (time_sec - 8.4) / 0.55))
        flare_int = math.sin(p * math.pi)
        tint = (int(255 * flare_int * 0.50), int(120 * flare_int * 0.38), int(55 * flare_int * 0.28), int(140 * flare_int))
        d.ellipse([-25, int(sh * 0.18), sw + 25, int(sh * 0.82)], fill=(255, 175, 75, int(160 * flare_int)))
        d.ellipse([int(sw * 0.15), int(sh * 0.30), int(sw * 0.85), int(sh * 0.70)], fill=(255, 225, 130, int(130 * flare_int)))
    elif time_sec < 17.5:
        # Scene 3 & 4: Deep Magenta & Neon Blue Dual Beams
        tint = (28, 8, 38, 42)
        wave = math.sin(time_sec * 1.4) * 16
        d.ellipse([-45, int(sh * 0.38 + wave), int(sw * 0.58), int(sh * 0.94 + wave)], fill=(210, 40, 160, 65))
        d.ellipse([int(sw * 0.38), int(sh * 0.10 - wave), sw + 45, int(sh * 0.65 - wave)], fill=(45, 115, 255, 70))
    elif time_sec < 21.0:
        # Scene 5: High-Contrast Midnight Charcoal
        tint = (10, 8, 20, 58)
        d.ellipse([sw - 85, int(sh * 0.20), sw + 35, int(sh * 0.70)], fill=(110, 50, 200, 48))
    else:
        # Scene 6: Olive Green & Golden Aura (CS2 Exotic skin showcase)
        tint = (18, 32, 14, 52)
        d.ellipse([int(sw * 0.18), int(sh * 0.52), sw + 45, sh + 45], fill=(120, 190, 40, 75))
        d.ellipse([-35, int(sh * 0.62), int(sw * 0.68), sh + 35], fill=(240, 170, 30, 55))

    small_overlay = small_overlay.filter(ImageFilter.GaussianBlur(16))
    big_overlay = small_overlay.resize((width, height), resample=Image.BILINEAR)

    tint_layer = Image.new("RGBA", (width, height), tint)
    result = Image.alpha_composite(bg, tint_layer)
    return Image.alpha_composite(result, big_overlay)


# ==============================================================================
# KINETIC TYPOGRAPHY LAYER COMPOSITOR
# ==============================================================================
def draw_kinetic_caption_line(
    canvas: Image.Image,
    segments: List[Tuple[str, str, int, Tuple[int, int, int]]],  # (text, font_path, font_size, color)
    y_pos: int,
    progress: float,
    global_time: float,
    canvas_w: int = 1080,
    max_w: int = 960,
    entry_dur: float = 0.20,
    exit_dur: float = 0.16,
    direction: str = "bottom",
    slide_distance: int = 450,
    entry_direction: Optional[str] = None,
    exit_direction: Optional[str] = None,
    max_tilt_deg: float = 2.2,
    target_cx: Optional[int] = None,
):
    """
    Renders multi-color caption line onto an isolated layer and composites it with
    full 3-phase kinetic motion (slide-in from side/bottom -> hold -> slide-out).
    """
    # 1. Measure initial width and scale if needed
    def get_layout(scale: float = 1.0):
        fonts = [ImageFont.truetype(f_path, int(f_size * scale)) for _, f_path, f_size, _ in segments]
        widths = []
        max_h = 0
        for (text, _, _, _), font in zip(segments, fonts):
            bbox = font.getbbox(text)
            widths.append(bbox[2] - bbox[0])
            max_h = max(max_h, bbox[3] - bbox[1])
        spacing = int(16 * scale)
        total = sum(widths) + spacing * (len(segments) - 1)
        return total, spacing, widths, fonts, max_h

    total_w, spacing, widths, fonts, max_h = get_layout(1.0)
    if total_w > max_w:
        scale_factor = max_w / float(total_w)
        total_w, spacing, widths, fonts, max_h = get_layout(scale_factor)

    # 2. Render text onto transparent scratch layer with drop shadow
    pad_x = 40
    pad_y = 30
    layer_w = total_w + pad_x * 2
    layer_h = max_h + pad_y * 2 + 20
    text_layer = Image.new("RGBA", (layer_w, layer_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(text_layer)

    cur_x = pad_x
    for (text, _, _, color), font, w in zip(segments, fonts, widths):
        # Drop shadow
        d.text((cur_x + 4, pad_y + 6), text, font=font, fill=(0, 0, 0, 200))
        # Main text
        d.text((cur_x, pad_y), text, font=font, fill=color)
        cur_x += w + spacing

    # 3. Composite onto canvas with kinetic entry, hold, and exit/return
    cx_val = target_cx if target_cx is not None else (canvas_w // 2)
    target_center = (cx_val, y_pos + layer_h // 2 - pad_y)
    composite_kinetic_element(
        canvas=canvas,
        element=text_layer,
        target_center=target_center,
        progress=progress,
        global_time=global_time,
        entry_dur=entry_dur,
        exit_dur=exit_dur,
        direction=direction,
        slide_distance=slide_distance,
        bob_amplitude=4.0,  # Subtle text floating
        bob_speed=2.5,
        entry_direction=entry_direction,
        exit_direction=exit_direction,
        max_tilt_deg=max_tilt_deg,
    )


def draw_styled_caption_line(
    draw_obj: ImageDraw.ImageDraw,
    segments: List[Tuple[str, str, int, Tuple[int, int, int]]],
    y_pos: int,
    canvas_w: int = 1080,
    max_w: int = 960,
    shadow_offset: Tuple[int, int] = (4, 6),
    shadow_color: Tuple[int, int, int, int] = (0, 0, 0, 190),
):
    """Fallback static text renderer for non-animated lines."""
    def get_layout(scale: float = 1.0):
        fonts = [ImageFont.truetype(f_path, int(f_size * scale)) for _, f_path, f_size, _ in segments]
        widths = []
        for (text, _, _, _), font in zip(segments, fonts):
            bbox = font.getbbox(text)
            widths.append(bbox[2] - bbox[0])
        spacing = int(16 * scale)
        total = sum(widths) + spacing * (len(segments) - 1)
        return total, spacing, widths, fonts

    total_w, spacing, widths, fonts = get_layout(1.0)
    if total_w > max_w:
        scale_factor = max_w / float(total_w)
        total_w, spacing, widths, fonts = get_layout(scale_factor)

    cur_x = (canvas_w - total_w) // 2
    for (text, _, _, color), font, w in zip(segments, fonts, widths):
        draw_obj.text((cur_x + shadow_offset[0], y_pos + shadow_offset[1]), text, font=font, fill=shadow_color)
        draw_obj.text((cur_x, y_pos), text, font=font, fill=color)
        cur_x += w + spacing


def draw_upgrade_arrows(canvas: Image.Image, progress: float, time_sec: float):
    """Draws 3 glowing green upgrade triangle stacks floating upwards with kinetic ease-in and pulse."""
    arrow_data = [
        (250, 850, 110, 0.0),
        (540, 1180, 100, 0.4),
        (820, 930, 115, 0.8),
    ]
    for bx, by, size, phase in arrow_data:
        float_y = by - math.fmod((time_sec * 140.0 + phase * 220.0), 340.0)
        alpha_factor = min(1.0, max(0.2, math.sin((float_y / 1920.0) * math.pi)))

        arrow = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(arrow)
        acx = size
        acy = size

        for i, offset_y in enumerate([-size * 0.35, 0, size * 0.35]):
            s = size * (0.55 + 0.15 * i)
            pts = [
                (acx, acy + offset_y - s * 0.6),
                (acx - s * 0.7, acy + offset_y + s * 0.4),
                (acx + s * 0.7, acy + offset_y + s * 0.4),
            ]
            d.polygon(pts, fill=(0, 255, 65, int(130 * alpha_factor)))
            d.polygon(pts, fill=(60, 255, 110, int(255 * alpha_factor)), outline=(200, 255, 200, int(240 * alpha_factor)))

        glow = arrow.filter(ImageFilter.GaussianBlur(radius=16))
        canvas.paste(glow, (int(bx - size), int(float_y - size)), glow)
        canvas.paste(arrow, (int(bx - size), int(float_y - size)), arrow)


def render_custom_image_card(
    canvas: Image.Image,
    img_path: str,
    target_center: Tuple[int, int],
    progress: float,
    global_time: float,
    max_w: int = 960,
    max_h: int = 950,
    radius: int = 32,
    direction: str = "left",
    slide_distance: int = 850,
    entry_direction: Optional[str] = None,
    exit_direction: Optional[str] = None,
    max_tilt_deg: float = 3.5,
) -> bool:
    """Renders user-uploaded custom scene image with rounded card, drop shadow, and side-to-side kinetic motion."""
    if not img_path or not os.path.exists(img_path):
        return False
    try:
        custom_raw = Image.open(img_path).convert("RGBA")
        # Aspect-fit
        aspect = custom_raw.width / float(custom_raw.height)
        if aspect >= (max_w / float(max_h)):
            new_w = max_w
            new_h = int(new_w / aspect)
        else:
            new_h = max_h
            new_w = int(new_h * aspect)
            
        custom_raw = custom_raw.resize((new_w, new_h), resample=Image.BICUBIC)
        card = make_rounded_card(custom_raw, radius=radius, shadow_blur=28, shadow_alpha=180)
        composite_kinetic_element(
            canvas=canvas,
            element=card,
            target_center=target_center,
            progress=progress,
            global_time=global_time,
            entry_dur=0.20,
            exit_dur=0.16,
            direction=direction,
            slide_distance=slide_distance,
            bob_amplitude=8.0,
            bob_speed=2.5,
            entry_direction=entry_direction or direction,
            exit_direction=exit_direction or direction,
            max_tilt_deg=max_tilt_deg,
        )
        return True
    except Exception as e:
        print(f"Notice: Failed to render custom image {img_path}: {e}")
        return False


# ==============================================================================
# CANONICAL DEFAULT ITEMS FOR ALL 6 SCENES (COMPOSER EDITABLE)
# ==============================================================================
def get_tradeit_default_items(scene_num: int, code: str = "MESTO300") -> List[Dict[str, Any]]:
    """Returns the default on-screen items/layers for each scene in the TradeIt ad."""
    if scene_num == 1:
        return [
            {
                "id": "s1_card_stop",
                "name": "Steam Proceed & STOP Slam",
                "type": "card",
                "asset": "steam_proceed_stop.jpg",
                "entry_direction": "left",
                "exit_direction": "left",
                "x_pct": 0.50,
                "y_pct": 0.46,
                "scale": 1.0,
                "start_t": 0.0,
                "end_t": 0.46,
                "slide_distance": 850,
                "max_tilt_deg": 3.5,
            },
            {
                "id": "s1_txt_top",
                "name": "Top Caption",
                "type": "text",
                "text": "Don't confirm",
                "highlight_word": "confirm",
                "highlight_color": [0, 255, 65],
                "text_color": [255, 255, 255],
                "font_size": 86,
                "font_style": "serif_italic",
                "entry_direction": "left",
                "exit_direction": "left",
                "x_pct": 0.50,
                "y_pct": 0.12,
                "start_t": 0.0,
                "end_t": 0.46,
                "slide_distance": 500,
                "max_tilt_deg": 2.5,
            },
            {
                "id": "s1_txt_bot",
                "name": "Bottom Caption",
                "type": "text",
                "text": "your next CS2 trade",
                "highlight_word": "CS2",
                "highlight_color": [0, 220, 255],
                "text_color": [255, 255, 255],
                "font_size": 80,
                "font_style": "serif_italic",
                "entry_direction": "right",
                "exit_direction": "right",
                "x_pct": 0.50,
                "y_pct": 0.84,
                "start_t": 0.0,
                "end_t": 0.46,
                "slide_distance": 500,
                "max_tilt_deg": 2.5,
            },
            {
                "id": "s1_card_badge",
                "name": "CS2 Handshake Badge",
                "type": "card",
                "asset": "cs2_trade_badge.jpg",
                "entry_direction": "right",
                "exit_direction": "bottom",
                "x_pct": 0.50,
                "y_pct": 0.40,
                "scale": 1.0,
                "start_t": 0.46,
                "end_t": 1.0,
                "slide_distance": 800,
                "max_tilt_deg": 3.0,
            },
            {
                "id": "s1_txt_punch1",
                "name": "Punch: until you do",
                "type": "text",
                "text": "until you do",
                "highlight_word": "until",
                "highlight_color": [255, 215, 0],
                "text_color": [255, 255, 255],
                "font_size": 88,
                "font_style": "sans_bold",
                "entry_direction": "left",
                "exit_direction": "left",
                "x_pct": 0.50,
                "y_pct": 0.73,
                "start_t": 0.46,
                "end_t": 1.0,
                "slide_distance": 450,
                "max_tilt_deg": 2.0,
            },
            {
                "id": "s1_txt_punch2",
                "name": "Punch: this.",
                "type": "text",
                "text": "this.",
                "highlight_word": "this.",
                "highlight_color": [255, 255, 255],
                "text_color": [255, 255, 255],
                "font_size": 115,
                "font_style": "serif_italic",
                "entry_direction": "right",
                "exit_direction": "right",
                "x_pct": 0.50,
                "y_pct": 0.79,
                "start_t": 0.46,
                "end_t": 1.0,
                "slide_distance": 450,
                "max_tilt_deg": 2.0,
            },
        ]
    elif scene_num == 2:
        return [
            {
                "id": "s2_bar",
                "name": "Missing Item Strip",
                "type": "card",
                "asset": "missing_item_bar.jpg",
                "entry_direction": "left",
                "exit_direction": "right",
                "x_pct": 0.50,
                "y_pct": 0.48,
                "scale": 1.0,
                "start_t": 0.0,
                "end_t": 0.48,
                "slide_distance": 900,
                "max_tilt_deg": 3.8,
            },
            {
                "id": "s2_txt_top1",
                "name": "Top: Your trade is missing",
                "type": "text",
                "text": "Your trade is missing",
                "highlight_word": "is missing",
                "highlight_color": [255, 42, 85],
                "text_color": [255, 255, 255],
                "font_size": 82,
                "font_style": "serif_italic",
                "entry_direction": "left",
                "exit_direction": "left",
                "x_pct": 0.50,
                "y_pct": 0.11,
                "start_t": 0.0,
                "end_t": 0.48,
                "slide_distance": 500,
                "max_tilt_deg": 2.2,
            },
            {
                "id": "s2_txt_bot1",
                "name": "Bottom: one item",
                "type": "text",
                "text": "one item",
                "highlight_word": "one",
                "highlight_color": [0, 220, 255],
                "text_color": [255, 255, 255],
                "font_size": 82,
                "font_style": "serif_italic",
                "entry_direction": "right",
                "exit_direction": "right",
                "x_pct": 0.50,
                "y_pct": 0.84,
                "start_t": 0.0,
                "end_t": 0.48,
                "slide_distance": 500,
                "max_tilt_deg": 2.2,
            },
            {
                "id": "s2_grid",
                "name": "Steam 5x5 Inventory Grid",
                "type": "card",
                "asset": "steam_inventory_5x5.jpg",
                "entry_direction": "right",
                "exit_direction": "right",
                "x_pct": 0.50,
                "y_pct": 0.48,
                "scale": 1.0,
                "start_t": 0.48,
                "end_t": 1.0,
                "slide_distance": 880,
                "max_tilt_deg": 3.5,
            },
            {
                "id": "s2_badge",
                "name": "Prohibition Sign Badge",
                "type": "badge",
                "asset": "prohibition_badge.jpg",
                "entry_direction": "zoom",
                "exit_direction": "zoom",
                "x_pct": 0.50,
                "y_pct": 0.48,
                "scale": 0.85,
                "start_t": 0.48,
                "end_t": 1.0,
            },
            {
                "id": "s2_txt_top2",
                "name": "Top: and it isn't",
                "type": "text",
                "text": "and it isn't",
                "highlight_word": "isn't",
                "highlight_color": [255, 42, 85],
                "text_color": [255, 255, 255],
                "font_size": 84,
                "font_style": "serif_italic",
                "entry_direction": "right",
                "exit_direction": "right",
                "x_pct": 0.50,
                "y_pct": 0.11,
                "start_t": 0.48,
                "end_t": 1.0,
                "slide_distance": 500,
                "max_tilt_deg": 2.2,
            },
            {
                "id": "s2_txt_bot2",
                "name": "Bottom: in your Steam inventory",
                "type": "text",
                "text": "in your Steam inventory",
                "highlight_word": "Steam",
                "highlight_color": [0, 220, 255],
                "text_color": [255, 255, 255],
                "font_size": 78,
                "font_style": "serif_italic",
                "entry_direction": "left",
                "exit_direction": "left",
                "x_pct": 0.50,
                "y_pct": 0.84,
                "start_t": 0.48,
                "end_t": 1.0,
                "slide_distance": 500,
                "max_tilt_deg": 2.2,
            },
        ]
    elif scene_num == 3:
        return [
            {
                "id": "s3_card_hp",
                "name": "TradeIt Homepage Card",
                "type": "card",
                "asset": "tradeit_homepage_card.jpg",
                "entry_direction": "left",
                "exit_direction": "left",
                "x_pct": 0.50,
                "y_pct": 0.50,
                "scale": 1.0,
                "start_t": 0.0,
                "end_t": 0.33,
                "slide_distance": 850,
                "max_tilt_deg": 3.5,
            },
            {
                "id": "s3_txt_hp",
                "name": "Top: go to tradeit.gg",
                "type": "text",
                "text": "go to tradeit.gg",
                "highlight_word": "tradeit.gg",
                "highlight_color": [0, 220, 255],
                "text_color": [255, 255, 255],
                "font_size": 86,
                "font_style": "serif_italic",
                "entry_direction": "left",
                "exit_direction": "left",
                "x_pct": 0.50,
                "y_pct": 0.10,
                "start_t": 0.0,
                "end_t": 0.33,
                "slide_distance": 500,
                "max_tilt_deg": 2.2,
            },
            {
                "id": "s3_card_menu",
                "name": "TradeIt Dropdown Menu",
                "type": "card",
                "asset": "tradeit_dropdown_menu.jpg",
                "entry_direction": "right",
                "exit_direction": "right",
                "x_pct": 0.50,
                "y_pct": 0.50,
                "scale": 1.0,
                "start_t": 0.33,
                "end_t": 0.60,
                "slide_distance": 800,
                "max_tilt_deg": 3.5,
            },
            {
                "id": "s3_txt_menu",
                "name": "Top: enter MESTO300",
                "type": "text",
                "text": "and enter {code}",
                "highlight_word": "{code}",
                "highlight_color": [0, 255, 65],
                "text_color": [255, 255, 255],
                "font_size": 84,
                "font_style": "serif_italic",
                "entry_direction": "right",
                "exit_direction": "right",
                "x_pct": 0.50,
                "y_pct": 0.10,
                "start_t": 0.33,
                "end_t": 0.60,
                "slide_distance": 500,
                "max_tilt_deg": 2.2,
            },
            {
                "id": "s3_card_modal",
                "name": "TradeIt Redeem Modal with Live Typing",
                "type": "card",
                "asset": "tradeit_modal_raw.jpg",
                "entry_direction": "bottom",
                "exit_direction": "left",
                "x_pct": 0.50,
                "y_pct": 0.50,
                "scale": 1.0,
                "start_t": 0.60,
                "end_t": 1.0,
                "slide_distance": 850,
                "max_tilt_deg": 3.0,
            },
            {
                "id": "s3_txt_modal",
                "name": "Top: enter MESTO300",
                "type": "text",
                "text": "and enter {code}",
                "highlight_word": "{code}",
                "highlight_color": [0, 255, 65],
                "text_color": [255, 255, 255],
                "font_size": 84,
                "font_style": "serif_italic",
                "entry_direction": "left",
                "exit_direction": "left",
                "x_pct": 0.50,
                "y_pct": 0.10,
                "start_t": 0.60,
                "end_t": 1.0,
                "slide_distance": 450,
                "max_tilt_deg": 2.2,
            },
        ]
    elif scene_num == 4:
        return [
            {
                "id": "s4_bar",
                "name": "Balance Header Bar",
                "type": "card",
                "asset": "tradeit_header_toast.jpg",
                "entry_direction": "left",
                "exit_direction": "right",
                "x_pct": 0.50,
                "y_pct": 0.46,
                "scale": 1.0,
                "start_t": 0.0,
                "end_t": 0.50,
                "slide_distance": 880,
                "max_tilt_deg": 3.2,
            },
            {
                "id": "s4_txt_bonus",
                "name": "Top: the code adds a bonus",
                "type": "text",
                "text": "the code adds a bonus",
                "highlight_word": "adds",
                "highlight_color": [0, 255, 65],
                "text_color": [255, 255, 255],
                "font_size": 78,
                "font_style": "serif_italic",
                "entry_direction": "left",
                "exit_direction": "left",
                "x_pct": 0.50,
                "y_pct": 0.11,
                "start_t": 0.0,
                "end_t": 0.50,
                "slide_distance": 500,
                "max_tilt_deg": 2.5,
            },
            {
                "id": "s4_arrows",
                "name": "Glowing Upgrade Arrows",
                "type": "arrows",
                "entry_direction": "bottom",
                "exit_direction": "top",
                "x_pct": 0.50,
                "y_pct": 0.50,
                "start_t": 0.50,
                "end_t": 1.0,
            },
            {
                "id": "s4_txt_choose",
                "name": "Top: before you choose",
                "type": "text",
                "text": "before you choose",
                "highlight_word": "you choose",
                "highlight_color": [0, 220, 255],
                "text_color": [255, 255, 255],
                "font_size": 84,
                "font_style": "serif_italic",
                "entry_direction": "left",
                "exit_direction": "left",
                "x_pct": 0.50,
                "y_pct": 0.11,
                "start_t": 0.50,
                "end_t": 1.0,
                "slide_distance": 500,
                "max_tilt_deg": 2.5,
            },
            {
                "id": "s4_txt_upgrade",
                "name": "Bottom: your upgrade",
                "type": "text",
                "text": "your upgrade",
                "highlight_word": "upgrade",
                "highlight_color": [0, 255, 65],
                "text_color": [255, 255, 255],
                "font_size": 86,
                "font_style": "serif_italic",
                "entry_direction": "right",
                "exit_direction": "right",
                "x_pct": 0.50,
                "y_pct": 0.84,
                "start_t": 0.50,
                "end_t": 1.0,
                "slide_distance": 500,
                "max_tilt_deg": 2.5,
            },
        ]
    elif scene_num == 5:
        return [
            {
                "id": "s5_grid",
                "name": "CS2 Weapon Selection Grid",
                "type": "card",
                "asset": "tradeit_item_grid.jpg",
                "entry_direction": "left",
                "exit_direction": "right",
                "x_pct": 0.50,
                "y_pct": 0.48,
                "scale": 1.0,
                "start_t": 0.0,
                "end_t": 1.0,
                "slide_distance": 950,
                "max_tilt_deg": 4.2,
            },
            {
                "id": "s5_txt_add",
                "name": "Top: now add the skins",
                "type": "text",
                "text": "now add the skins",
                "highlight_word": "add",
                "highlight_color": [0, 255, 65],
                "text_color": [255, 255, 255],
                "font_size": 78,
                "font_style": "serif_italic",
                "entry_direction": "left",
                "exit_direction": "left",
                "x_pct": 0.50,
                "y_pct": 0.11,
                "start_t": 0.0,
                "end_t": 0.50,
                "slide_distance": 500,
                "max_tilt_deg": 2.5,
            },
            {
                "id": "s5_txt_use",
                "name": "Bottom: you no longer use",
                "type": "text",
                "text": "you no longer use",
                "highlight_word": "no longer",
                "highlight_color": [255, 42, 85],
                "text_color": [255, 255, 255],
                "font_size": 78,
                "font_style": "serif_italic",
                "entry_direction": "right",
                "exit_direction": "right",
                "x_pct": 0.50,
                "y_pct": 0.84,
                "start_t": 0.0,
                "end_t": 0.50,
                "slide_distance": 500,
                "max_tilt_deg": 2.5,
            },
            {
                "id": "s5_txt_see",
                "name": "Top: and see what the",
                "type": "text",
                "text": "and see what the",
                "highlight_word": "see",
                "highlight_color": [0, 255, 65],
                "text_color": [255, 255, 255],
                "font_size": 78,
                "font_style": "serif_italic",
                "entry_direction": "right",
                "exit_direction": "right",
                "x_pct": 0.50,
                "y_pct": 0.11,
                "start_t": 0.50,
                "end_t": 1.0,
                "slide_distance": 500,
                "max_tilt_deg": 2.5,
            },
            {
                "id": "s5_txt_complete",
                "name": "Bottom: complete trade can get you",
                "type": "text",
                "text": "complete trade can get you",
                "highlight_word": "complete",
                "highlight_color": [0, 220, 255],
                "text_color": [255, 255, 255],
                "font_size": 78,
                "font_style": "serif_italic",
                "entry_direction": "left",
                "exit_direction": "left",
                "x_pct": 0.50,
                "y_pct": 0.84,
                "start_t": 0.50,
                "end_t": 1.0,
                "slide_distance": 500,
                "max_tilt_deg": 2.5,
            },
        ]
    elif scene_num == 6:
        return [
            {
                "id": "s6_skins",
                "name": "3 Floating Dream Weapons",
                "type": "card",
                "asset": "tradeit_floating_skins.jpg",
                "entry_direction": "left",
                "exit_direction": "bottom",
                "x_pct": 0.50,
                "y_pct": 0.48,
                "scale": 1.0,
                "start_t": 0.0,
                "end_t": 0.45,
                "slide_distance": 850,
                "max_tilt_deg": 2.8,
            },
            {
                "id": "s6_txt_useful",
                "name": "Top: the most useful",
                "type": "text",
                "text": "the most useful",
                "highlight_word": "useful",
                "highlight_color": [0, 255, 65],
                "text_color": [255, 255, 255],
                "font_size": 78,
                "font_style": "serif_italic",
                "entry_direction": "left",
                "exit_direction": "left",
                "x_pct": 0.50,
                "y_pct": 0.10,
                "start_t": 0.0,
                "end_t": 0.45,
                "slide_distance": 500,
                "max_tilt_deg": 2.5,
            },
            {
                "id": "s6_txt_trade",
                "name": "Bottom: item in your trade",
                "type": "text",
                "text": "item in your trade",
                "highlight_word": "your",
                "highlight_color": [0, 255, 65],
                "text_color": [255, 255, 255],
                "font_size": 78,
                "font_style": "serif_italic",
                "entry_direction": "right",
                "exit_direction": "right",
                "x_pct": 0.50,
                "y_pct": 0.84,
                "start_t": 0.0,
                "end_t": 0.45,
                "slide_distance": 500,
                "max_tilt_deg": 2.5,
            },
            {
                "id": "s6_txt_punch1",
                "name": "Punch: you cant",
                "type": "text",
                "text": "you cant",
                "highlight_word": "you cant",
                "highlight_color": [255, 215, 0],
                "text_color": [255, 255, 255],
                "font_size": 88,
                "font_style": "sans_bold",
                "entry_direction": "zoom",
                "exit_direction": "zoom",
                "x_pct": 0.50,
                "y_pct": 0.44,
                "start_t": 0.45,
                "end_t": 0.70,
                "slide_distance": 0,
            },
            {
                "id": "s6_txt_punch2",
                "name": "Punch: equip.",
                "type": "text",
                "text": "equip.",
                "highlight_word": "equip.",
                "highlight_color": [255, 255, 255],
                "text_color": [255, 255, 255],
                "font_size": 115,
                "font_style": "serif_italic",
                "entry_direction": "zoom",
                "exit_direction": "zoom",
                "x_pct": 0.50,
                "y_pct": 0.51,
                "start_t": 0.45,
                "end_t": 0.70,
                "slide_distance": 0,
            },
            {
                "id": "s6_txt_outro1",
                "name": "Outro: go to tradeit.gg",
                "type": "text",
                "text": "go to tradeit.gg",
                "highlight_word": "tradeit.gg",
                "highlight_color": [0, 220, 255],
                "text_color": [255, 255, 255],
                "font_size": 84,
                "font_style": "serif_italic",
                "entry_direction": "left",
                "exit_direction": "left",
                "x_pct": 0.50,
                "y_pct": 0.42,
                "start_t": 0.70,
                "end_t": 1.0,
                "slide_distance": 600,
                "max_tilt_deg": 3.2,
            },
            {
                "id": "s6_txt_outro2",
                "name": "Outro: and enter MESTO300",
                "type": "text",
                "text": "and enter {code}",
                "highlight_word": "{code}",
                "highlight_color": [0, 255, 65],
                "text_color": [255, 255, 255],
                "font_size": 84,
                "font_style": "serif_italic",
                "entry_direction": "right",
                "exit_direction": "right",
                "x_pct": 0.50,
                "y_pct": 0.52,
                "start_t": 0.70,
                "end_t": 1.0,
                "slide_distance": 600,
                "max_tilt_deg": 3.2,
            },
        ]
    return []


# ==============================================================================
# GENERAL PER-ITEM / PER-LAYER RENDERER FOR DYNAMIC SCENE COMPOSITION
# ==============================================================================
def render_scene_items_layer(
    canvas: Image.Image,
    items: List[Dict[str, Any]],
    scene_progress: float,
    global_time: float,
    code: str = "MESTO300",
    width: int = 1080,
    height: int = 1920,
) -> Image.Image:
    """
    Renders customizable on-screen items/layers for the current scene:
    - Independent entry & exit directions ('left', 'right', 'top', 'bottom', 'zoom')
    - Position (x_pct, y_pct), scale, aerodynamic rotational inertia tilt
    - Active time ranges (start_t to end_t)
    - Custom images or asset presets
    - Text lines with multi-color styling & highlights
    - Badges & floating particle upgrade arrows
    """
    for item in items:
        start_t = float(item.get("start_t", 0.0))
        end_t = float(item.get("end_t", 1.0))
        if scene_progress < start_t or scene_progress > end_t:
            continue

        dur = max(0.01, end_t - start_t)
        u = max(0.0, min(1.0, (scene_progress - start_t) / dur))

        item_type = item.get("type", "card")
        entry_dir = item.get("entry_direction", "left")
        exit_dir = item.get("exit_direction", entry_dir)
        slide_dist = int(item.get("slide_distance", 850 if item_type == "card" else 500))
        max_tilt = float(item.get("max_tilt_deg", 3.5 if item_type == "card" else 2.2))
        scale = float(item.get("scale", 1.0))
        x_pct = float(item.get("x_pct", 0.50))
        y_pct = float(item.get("y_pct", 0.50))
        target_cx = int(width * x_pct)
        target_cy = int(height * y_pct)

        if item_type in ("card", "image"):
            img_raw = None
            img_path = item.get("image_path") or item.get("custom_image_path")
            if img_path and os.path.exists(img_path):
                try:
                    img_raw = Image.open(img_path).convert("RGBA")
                except Exception:
                    img_raw = None

            if img_raw is None:
                asset_name = item.get("asset") or item.get("asset_preset") or "tradeit_homepage_card.jpg"
                img_raw = _load_asset(asset_name)

            if img_raw:
                # Modal typing animation
                if "modal" in str(item.get("asset", "")).lower() or item.get("is_modal_typing"):
                    img_raw = img_raw.copy()
                    m_draw = ImageDraw.Draw(img_raw)
                    m_draw.rounded_rectangle([35, 114, 920, 176], radius=6, fill=(30, 31, 39, 255))
                    num_chars = min(len(code), int(len(code) * u * 1.5))
                    typed_text = code[:num_chars]
                    f_input = ImageFont.truetype(FONT_SANS_BOLD, 32)
                    m_draw.text((55, 126), typed_text, font=f_input, fill=(255, 255, 255))
                    if int(global_time * 4) % 2 == 0:
                        bbox = f_input.getbbox(typed_text) if typed_text else (0, 0, 0, 0)
                        cur_x = 55 + (bbox[2] - bbox[0]) + 4
                        m_draw.line([(cur_x, 126), (cur_x, 162)], fill=(255, 255, 255), width=2)

                if scale != 1.0:
                    nw = max(10, int(img_raw.width * scale))
                    nh = max(10, int(img_raw.height * scale))
                    img_raw = img_raw.resize((nw, nh), resample=Image.BICUBIC)

                card_obj = make_rounded_card(img_raw, radius=int(32 * scale), shadow_blur=int(28 * scale))
                composite_kinetic_element(
                    canvas=canvas,
                    element=card_obj,
                    target_center=(target_cx, target_cy),
                    progress=u,
                    global_time=global_time,
                    entry_dur=float(item.get("entry_dur", 0.20)),
                    exit_dur=float(item.get("exit_dur", 0.16)),
                    direction=entry_dir,
                    entry_direction=entry_dir,
                    exit_direction=exit_dir,
                    slide_distance=slide_dist,
                    max_tilt_deg=max_tilt,
                    bob_amplitude=float(item.get("bob_amplitude", 8.0)),
                )

        elif item_type == "badge":
            badge_asset = item.get("asset") or "prohibition_badge.jpg"
            b_raw = _load_asset(badge_asset)
            if b_raw:
                badge_card = make_circular_badge(b_raw, shadow_blur=22)
                if scale != 1.0:
                    badge_card = badge_card.resize((max(10, int(badge_card.width * scale)), max(10, int(badge_card.height * scale))), resample=Image.BICUBIC)
                composite_kinetic_element(
                    canvas=canvas,
                    element=badge_card,
                    target_center=(target_cx, target_cy),
                    progress=u,
                    global_time=global_time,
                    entry_dur=float(item.get("entry_dur", 0.20)),
                    exit_dur=float(item.get("exit_dur", 0.16)),
                    direction=entry_dir,
                    entry_direction=entry_dir,
                    exit_direction=exit_dir,
                    slide_distance=slide_dist,
                    max_tilt_deg=max_tilt,
                )

        elif item_type in ("text", "caption"):
            raw_text = str(item.get("text", "")).strip()
            if not raw_text:
                continue

            font_style = item.get("font_style", "serif_italic")
            font_path = FONT_SANS_BOLD if font_style == "sans_bold" else FONT_SERIF_BI
            font_size = int(item.get("font_size", 84))

            hl_word = str(item.get("highlight_word", "")).strip()
            hl_color = tuple(item.get("highlight_color", [0, 255, 65]))
            text_color = tuple(item.get("text_color", [255, 255, 255]))

            raw_text = raw_text.replace("{code}", code)
            if hl_word == "{code}":
                hl_word = code

            segments = []
            if hl_word and hl_word.lower() in raw_text.lower():
                pattern = re.compile(re.escape(hl_word), re.IGNORECASE)
                parts = pattern.split(raw_text)
                matches = pattern.findall(raw_text)
                for i, part in enumerate(parts):
                    if part:
                        segments.append((part, font_path, font_size, text_color))
                    if i < len(matches):
                        segments.append((matches[i], font_path, font_size, hl_color))
            else:
                segments.append((raw_text, font_path, font_size, text_color))

            draw_kinetic_caption_line(
                canvas=canvas,
                segments=segments,
                y_pos=int(target_cy - font_size // 2),
                progress=u,
                global_time=global_time,
                canvas_w=width,
                entry_dur=float(item.get("entry_dur", 0.20)),
                exit_dur=float(item.get("exit_dur", 0.16)),
                direction=entry_dir,
                entry_direction=entry_dir,
                exit_direction=exit_dir,
                slide_distance=slide_dist,
                max_tilt_deg=max_tilt,
                target_cx=target_cx,
            )

        elif item_type == "arrows":
            draw_upgrade_arrows(canvas, u, global_time)

    return canvas


# ==============================================================================
# MASTER TRADEIT SCENE FRAME RENDERER WITH KINETIC ENTRY & RETURN TRANSITIONS
# ==============================================================================
def render_tradeit_scene_frame(
    scene_num: int,
    scene_progress: float,  # 0.0 to 1.0 within scene
    global_time: float,     # seconds from start
    code: str = "MESTO300",
    width: int = 1080,
    height: int = 1920,
    custom_image_path: Optional[str] = None,
    custom_image_direction: str = "left",
    items: Optional[List[Dict[str, Any]]] = None,
) -> Image.Image:
    """
    Renders the authentic TradeIt ad frame matching ready (2).mp4:
    - Customizable on-screen items with independent entry directions (left, right, bottom, top, zoom)
    - Side-to-side alternating kinetic entries with aerodynamic tilt
    - Dynamic atmospheric background that morphs color palettes across scenes with amber flare
    - Synchronized opposing typography (top from left, bottom from right)
    """
    bg = get_tradeit_background(width, height, global_time)

    # 1. If explicit customizable items are defined on this scene, render items!
    if items and len(items) > 0:
        return render_scene_items_layer(
            canvas=bg,
            items=items,
            scene_progress=scene_progress,
            global_time=global_time,
            code=code,
            width=width,
            height=height,
        )

    # 2. If custom image is explicitly passed and valid, render custom image hero mode
    if custom_image_path and os.path.exists(custom_image_path):
        render_custom_image_card(
            canvas=bg,
            img_path=custom_image_path,
            target_center=(width // 2, int(height * 0.46)),
            progress=scene_progress,
            global_time=global_time,
            direction=custom_image_direction,
            slide_distance=850,
        )

    # =========================================================================
    # SCENE 1: Steam Trade & STOP Prohibition Slam
    # "Stop! Don't confirm your next CS2 trade until you do this."
    # =========================================================================
    if scene_num == 1:
        split_t = 0.46
        if scene_progress < split_t:
            # Sub-phase 1: Steam proceed button + STOP slam (0.0 -> split_t)
            u = scene_progress / split_t
            if not custom_image_path:
                stop_asset = _load_asset("steam_proceed_stop.jpg")
                if stop_asset:
                    card = make_rounded_card(stop_asset, radius=32, shadow_blur=28)
                    composite_kinetic_element(
                        canvas=bg,
                        element=card,
                        target_center=(width // 2, int(height * 0.40)),
                        progress=u,
                        global_time=global_time,
                        entry_dur=0.22,
                        exit_dur=0.18,
                        direction="left",
                        entry_direction="left",
                        exit_direction="left",
                        slide_distance=850,
                        bob_amplitude=8.0,
                        max_tilt_deg=3.5,
                    )

            # Top caption: Don't confirm (slides from LEFT)
            draw_kinetic_caption_line(
                bg,
                [("Don't", FONT_SERIF_BI, 86, COLOR_WHITE), ("confirm", FONT_SERIF_BI, 86, COLOR_NEON_GREEN)],
                y_pos=220,
                progress=u,
                global_time=global_time,
                direction="left",
                entry_direction="left",
                exit_direction="left",
                slide_distance=500,
                max_tilt_deg=2.5,
            )
            # Bottom caption: your next CS2 trade (slides from RIGHT)
            draw_kinetic_caption_line(
                bg,
                [("your next", FONT_SERIF_BI, 80, COLOR_WHITE), ("CS2", FONT_SERIF_BI, 80, COLOR_ELECTRIC_CYAN), ("trade", FONT_SERIF_BI, 80, COLOR_WHITE)],
                y_pos=1600,
                progress=u,
                global_time=global_time,
                direction="right",
                entry_direction="right",
                exit_direction="right",
                slide_distance=500,
                max_tilt_deg=2.5,
            )
        else:
            # Sub-phase 2: CS2 trade handshake badge & "until you do this." (split_t -> 1.0)
            u = (scene_progress - split_t) / (1.0 - split_t)
            if not custom_image_path:
                badge_asset = _load_asset("cs2_trade_badge.jpg")
                if badge_asset:
                    badge = make_rounded_card(badge_asset, radius=42, shadow_blur=26)
                    composite_kinetic_element(
                        canvas=bg,
                        element=badge,
                        target_center=(width // 2, int(height * 0.40)),
                        progress=u,
                        global_time=global_time,
                        entry_dur=0.20,
                        exit_dur=0.16,
                        direction="right",
                        entry_direction="right",
                        exit_direction="bottom",
                        slide_distance=800,
                        bob_amplitude=8.0,
                        max_tilt_deg=3.0,
                    )

            # Central kinetic punch text: until you do this.
            draw_kinetic_caption_line(
                bg,
                [("until", FONT_SANS_BOLD, 88, COLOR_YELLOW), ("you do", FONT_SANS_BOLD, 88, COLOR_WHITE)],
                y_pos=1400,
                progress=u,
                global_time=global_time,
                direction="left",
                entry_direction="left",
                exit_direction="left",
                slide_distance=450,
            )
            draw_kinetic_caption_line(
                bg,
                [("this.", FONT_SERIF_BI, 115, COLOR_WHITE)],
                y_pos=1510,
                progress=u,
                global_time=global_time,
                direction="right",
                entry_direction="right",
                exit_direction="right",
                slide_distance=450,
            )

    # =========================================================================
    # SCENE 2: Missing Item Strip & Steam 5x5 Inventory Grid
    # "Your trade is missing one item, and it isn't in your Steam inventory."
    # =========================================================================
    elif scene_num == 2:
        split_t = 0.48
        if scene_progress < split_t:
            # Trade Exchange Bar with MISSING ITEM ?
            u = scene_progress / split_t
            if not custom_image_path:
                bar_asset = _load_asset("missing_item_bar.jpg")
                if bar_asset:
                    bar = make_rounded_card(bar_asset, radius=24, shadow_blur=26)
                    composite_kinetic_element(
                        canvas=bg,
                        element=bar,
                        target_center=(width // 2, int(height * 0.48)),
                        progress=u,
                        global_time=global_time,
                        entry_dur=0.20,
                        exit_dur=0.18,
                        direction="left",
                        entry_direction="left",
                        exit_direction="right",  # Swooshes smoothly across screen
                        slide_distance=900,
                        max_tilt_deg=3.8,
                    )

            # Top: Your trade is missing (slides from LEFT)
            draw_kinetic_caption_line(
                bg,
                [("Your trade", FONT_SERIF_BI, 82, COLOR_WHITE), ("is missing", FONT_SERIF_BI, 82, COLOR_CRIMSON)],
                y_pos=210,
                progress=u,
                global_time=global_time,
                direction="left",
                entry_direction="left",
                exit_direction="left",
                slide_distance=500,
            )
            # Bottom: one item (slides from RIGHT)
            draw_kinetic_caption_line(
                bg,
                [("one", FONT_SERIF_BI, 84, COLOR_ELECTRIC_CYAN), ("item", FONT_SANS_BOLD, 84, COLOR_WHITE)],
                y_pos=1580,
                progress=u,
                global_time=global_time,
                direction="right",
                entry_direction="right",
                exit_direction="right",
                slide_distance=500,
            )
        else:
            # 5x5 Steam CS2 Inventory with Prohibition Slam
            u = (scene_progress - split_t) / (1.0 - split_t)
            if not custom_image_path:
                inv_asset = _load_asset("steam_inventory_5x5.jpg")
                if inv_asset:
                    inv = make_rounded_card(inv_asset, radius=28, shadow_blur=28)
                    composite_kinetic_element(
                        canvas=bg,
                        element=inv,
                        target_center=(width // 2, int(height * 0.48)),
                        progress=u,
                        global_time=global_time,
                        entry_dur=0.20,
                        exit_dur=0.16,
                        direction="right",
                        entry_direction="right",
                        exit_direction="right",  # Exits off to the right into the amber flare!
                        slide_distance=880,
                        max_tilt_deg=3.5,
                    )

                    # Prohibition badge in center with zoom pop
                    prohib_asset = _load_asset("prohibition_badge.jpg")
                    if prohib_asset:
                        prohib = make_circular_badge(prohib_asset, shadow_blur=22)
                        p_scale = 0.85
                        prohib = prohib.resize((int(prohib.width * p_scale), int(prohib.height * p_scale)), resample=Image.BICUBIC)
                        composite_kinetic_element(
                            canvas=bg,
                            element=prohib,
                            target_center=(width // 2, int(height * 0.48)),
                            progress=u,
                            global_time=global_time,
                            entry_dur=0.26,
                            exit_dur=0.16,
                            direction="zoom",
                        )

            # Top: and it isn't (slides from RIGHT)
            draw_kinetic_caption_line(
                bg,
                [("and it", FONT_SERIF_BI, 84, COLOR_WHITE), ("isn't", FONT_SERIF_BI, 84, COLOR_CRIMSON)],
                y_pos=210,
                progress=u,
                global_time=global_time,
                direction="right",
                entry_direction="right",
                exit_direction="right",
                slide_distance=500,
            )
            # Bottom: in your Steam inventory (slides from LEFT)
            draw_kinetic_caption_line(
                bg,
                [("in your", FONT_SERIF_BI, 78, COLOR_WHITE), ("Steam", FONT_SERIF_BI, 78, COLOR_ELECTRIC_CYAN), ("inventory", FONT_SERIF_BI, 78, COLOR_WHITE)],
                y_pos=1600,
                progress=u,
                global_time=global_time,
                direction="left",
                entry_direction="left",
                exit_direction="left",
                slide_distance=500,
            )

    # =========================================================================
    # SCENE 3: TradeIt Homepage & Redeem Coupon typing MESTO300
    # "Go to tradeit.gg and enter MESTO 300."
    # =========================================================================
    elif scene_num == 3:
        if scene_progress < 0.33:
            # Sub-phase 1: TradeIt Homepage Card (0.0 -> 0.33)
            u = scene_progress / 0.33
            if not custom_image_path:
                hp_asset = _load_asset("tradeit_homepage_card.jpg")
                if hp_asset:
                    hp = make_rounded_card(hp_asset, radius=32, shadow_blur=28)
                    composite_kinetic_element(
                        canvas=bg,
                        element=hp,
                        target_center=(width // 2, int(height * 0.50)),
                        progress=u,
                        global_time=global_time,
                        entry_dur=0.20,
                        exit_dur=0.18,
                        direction="left",
                        entry_direction="left",
                        exit_direction="left",
                        slide_distance=850,
                        max_tilt_deg=3.5,
                    )

            # Top: go to tradeit.gg (slides from LEFT)
            draw_kinetic_caption_line(
                bg,
                [("go to", FONT_SERIF_BI, 86, COLOR_WHITE), ("tradeit.gg", FONT_SERIF_BI, 86, COLOR_ELECTRIC_CYAN)],
                y_pos=200,
                progress=u,
                global_time=global_time,
                direction="left",
                entry_direction="left",
                exit_direction="left",
                slide_distance=500,
                max_tilt_deg=2.2,
            )
        elif scene_progress < 0.60:
            # Sub-phase 2: TradeIt Profile Dropdown Menu (0.33 -> 0.60)
            u = (scene_progress - 0.33) / 0.27
            if not custom_image_path:
                menu_asset = _load_asset("tradeit_dropdown_menu.jpg")
                if menu_asset:
                    menu = make_rounded_card(menu_asset, radius=24, shadow_blur=26)
                    composite_kinetic_element(
                        canvas=bg,
                        element=menu,
                        target_center=(width // 2, int(height * 0.50)),
                        progress=u,
                        global_time=global_time,
                        entry_dur=0.20,
                        exit_dur=0.18,
                        direction="right",
                        entry_direction="right",
                        exit_direction="right",
                        slide_distance=800,
                        max_tilt_deg=3.5,
                    )

            # Top: and enter MESTO300 (slides from RIGHT)
            draw_kinetic_caption_line(
                bg,
                [("and enter", FONT_SERIF_BI, 84, COLOR_WHITE), (code, FONT_SERIF_BI, 84, COLOR_NEON_GREEN)],
                y_pos=200,
                progress=u,
                global_time=global_time,
                direction="right",
                entry_direction="right",
                exit_direction="right",
                slide_distance=500,
                max_tilt_deg=2.2,
            )
        else:
            # Sub-phase 3: TradeIt Redeem Modal typing MESTO300 (0.60 -> 1.0)
            u = (scene_progress - 0.60) / 0.40
            if not custom_image_path:
                modal_asset = _load_asset("tradeit_modal_raw.jpg")
                if modal_asset:
                    modal = modal_asset.copy()
                    m_draw = ImageDraw.Draw(modal)
                    # Clean input box
                    m_draw.rounded_rectangle([35, 114, 920, 176], radius=6, fill=(30, 31, 39, 255))

                    # Smooth typing animation
                    num_chars = min(len(code), int(len(code) * u * 1.5))
                    typed_text = code[:num_chars]

                    f_input = ImageFont.truetype(FONT_SANS_BOLD, 32)
                    m_draw.text((55, 126), typed_text, font=f_input, fill=(255, 255, 255))

                    # Blinking cursor
                    if int(global_time * 4) % 2 == 0:
                        bbox = f_input.getbbox(typed_text) if typed_text else (0, 0, 0, 0)
                        cur_x = 55 + (bbox[2] - bbox[0]) + 4
                        m_draw.line([(cur_x, 126), (cur_x, 162)], fill=(255, 255, 255), width=2)

                    modal_card = make_rounded_card(modal, radius=28, shadow_blur=28)
                    composite_kinetic_element(
                        canvas=bg,
                        element=modal_card,
                        target_center=(width // 2, int(height * 0.50)),
                        progress=u,
                        global_time=global_time,
                        entry_dur=0.20,
                        exit_dur=0.16,
                        direction="left",
                        entry_direction="bottom",
                        exit_direction="left",
                        slide_distance=850,
                        max_tilt_deg=3.0,
                    )

            # Top: and enter MESTO300 (slides from LEFT)
            draw_kinetic_caption_line(
                bg,
                [("and enter", FONT_SERIF_BI, 84, COLOR_WHITE), (code, FONT_SERIF_BI, 84, COLOR_NEON_GREEN)],
                y_pos=200,
                progress=u,
                global_time=global_time,
                direction="left",
                entry_direction="left",
                exit_direction="left",
                slide_distance=450,
                max_tilt_deg=2.2,
            )

    # =========================================================================
    # SCENE 4: Balance Bar & Coupon Toast & Green Upgrade Arrows
    # "The code adds a bonus to your balance before you choose your upgrade."
    # =========================================================================
    elif scene_num == 4:
        split_t = 0.50
        if scene_progress < split_t:
            # Top Header Bar + Toast
            u = scene_progress / split_t
            if not custom_image_path:
                toast_asset = _load_asset("tradeit_header_toast.jpg")
                if toast_asset:
                    toast = make_rounded_card(toast_asset, radius=32, shadow_blur=26)
                    composite_kinetic_element(
                        canvas=bg,
                        element=toast,
                        target_center=(width // 2, int(height * 0.46)),
                        progress=u,
                        global_time=global_time,
                        entry_dur=0.20,
                        exit_dur=0.18,
                        direction="left",
                        entry_direction="left",
                        exit_direction="right",
                        slide_distance=880,
                        max_tilt_deg=3.2,
                    )

            # Top: the code adds a bonus (slides from LEFT)
            draw_kinetic_caption_line(
                bg,
                [("the code", FONT_SERIF_BI, 78, COLOR_WHITE), ("adds", FONT_SERIF_BI, 86, COLOR_NEON_GREEN), ("a bonus", FONT_SERIF_BI, 78, COLOR_WHITE)],
                y_pos=210,
                progress=u,
                global_time=global_time,
                direction="left",
                entry_direction="left",
                exit_direction="left",
                slide_distance=500,
                max_tilt_deg=2.5,
            )
        else:
            # Floating glowing upgrade arrows
            u = (scene_progress - split_t) / (1.0 - split_t)
            draw_upgrade_arrows(bg, scene_progress, global_time)

            # Top: before you choose (slides from LEFT)
            draw_kinetic_caption_line(
                bg,
                [("before", FONT_SERIF_BI, 78, COLOR_WHITE), ("you choose", FONT_SERIF_BI, 84, COLOR_ELECTRIC_CYAN)],
                y_pos=210,
                progress=u,
                global_time=global_time,
                direction="left",
                entry_direction="left",
                exit_direction="left",
                slide_distance=500,
                max_tilt_deg=2.5,
            )
            # Bottom: your upgrade (slides from RIGHT)
            draw_kinetic_caption_line(
                bg,
                [("your", FONT_SERIF_BI, 80, COLOR_WHITE), ("upgrade", FONT_SERIF_BI, 86, COLOR_NEON_GREEN)],
                y_pos=1600,
                progress=u,
                global_time=global_time,
                direction="right",
                entry_direction="right",
                exit_direction="right",
                slide_distance=500,
                max_tilt_deg=2.5,
            )

    # =========================================================================
    # SCENE 5: TradeIt Weapon Selection Grid
    # "Now add the skins you no longer use and see what the complete trade can get you."
    # =========================================================================
    elif scene_num == 5:
        u_card = scene_progress
        if not custom_image_path:
            grid_asset = _load_asset("tradeit_item_grid.jpg")
            if grid_asset:
                grid = make_rounded_card(grid_asset, radius=28, shadow_blur=28)
                composite_kinetic_element(
                    canvas=bg,
                    element=grid,
                    target_center=(width // 2, int(height * 0.48)),
                    progress=u_card,
                    global_time=global_time,
                    entry_dur=0.18,
                    exit_dur=0.14,
                    direction="left",
                    entry_direction="left",
                    exit_direction="right",  # Sweeps off violently to the right matching dx=+28 in optical flow
                    slide_distance=950,
                    max_tilt_deg=4.2,
                )

        split_t = 0.50
        if scene_progress < split_t:
            u_text = scene_progress / split_t
            # Top: now add the skins (slides from LEFT)
            draw_kinetic_caption_line(
                bg,
                [("now", FONT_SERIF_BI, 78, COLOR_WHITE), ("add", FONT_SERIF_BI, 86, COLOR_NEON_GREEN), ("the skins", FONT_SERIF_BI, 78, COLOR_WHITE)],
                y_pos=210,
                progress=u_text,
                global_time=global_time,
                direction="left",
                entry_direction="left",
                exit_direction="left",
                slide_distance=500,
                max_tilt_deg=2.5,
            )
            # Bottom: you no longer use (slides from RIGHT)
            draw_kinetic_caption_line(
                bg,
                [("you", FONT_SERIF_BI, 78, COLOR_WHITE), ("no longer", FONT_SERIF_BI, 86, COLOR_CRIMSON), ("use", FONT_SERIF_BI, 78, COLOR_MUTED_GREY)],
                y_pos=1600,
                progress=u_text,
                global_time=global_time,
                direction="right",
                entry_direction="right",
                exit_direction="right",
                slide_distance=500,
                max_tilt_deg=2.5,
            )
        else:
            u_text = (scene_progress - split_t) / (1.0 - split_t)
            # Top: and see what the (slides from RIGHT)
            draw_kinetic_caption_line(
                bg,
                [("and", FONT_SERIF_BI, 78, COLOR_WHITE), ("see", FONT_SERIF_BI, 86, COLOR_NEON_GREEN), ("what the", FONT_SERIF_BI, 78, COLOR_WHITE)],
                y_pos=210,
                progress=u_text,
                global_time=global_time,
                direction="right",
                entry_direction="right",
                exit_direction="right",
                slide_distance=500,
                max_tilt_deg=2.5,
            )
            # Bottom: complete trade can get you (slides from LEFT)
            draw_kinetic_caption_line(
                bg,
                [("complete", FONT_SERIF_BI, 82, COLOR_ELECTRIC_CYAN), ("trade can get you", FONT_SERIF_BI, 78, COLOR_WHITE)],
                y_pos=1600,
                progress=u_text,
                global_time=global_time,
                direction="left",
                entry_direction="left",
                exit_direction="left",
                slide_distance=500,
                max_tilt_deg=2.5,
            )

    # =========================================================================
    # SCENE 6: Floating Dream Skins Trio & Grand Outro CTA
    # "The most useful item in your next trade might be the one you can't equip. Go to tradeit.gg and enter MESTO 300."
    # =========================================================================
    elif scene_num == 6:
        if scene_progress < 0.45:
            # 3 Floating Dream Weapons
            u = scene_progress / 0.45
            if not custom_image_path:
                skins_asset = _load_asset("tradeit_floating_skins.jpg")
                if skins_asset:
                    card = make_rounded_card(skins_asset, radius=32, shadow_blur=28)
                    composite_kinetic_element(
                        canvas=bg,
                        element=card,
                        target_center=(width // 2, int(height * 0.48)),
                        progress=u,
                        global_time=global_time,
                        entry_dur=0.20,
                        exit_dur=0.18,
                        direction="left",
                        entry_direction="left",
                        exit_direction="bottom",
                        slide_distance=850,
                        max_tilt_deg=2.8,
                    )

            # Top: the most useful (slides from LEFT)
            draw_kinetic_caption_line(
                bg,
                [("the most", FONT_SERIF_BI, 78, COLOR_WHITE), ("useful", FONT_SERIF_BI, 86, COLOR_NEON_GREEN)],
                y_pos=200,
                progress=u,
                global_time=global_time,
                direction="left",
                entry_direction="left",
                exit_direction="left",
                slide_distance=500,
                max_tilt_deg=2.5,
            )
            # Bottom: item in your trade (slides from RIGHT)
            draw_kinetic_caption_line(
                bg,
                [("item in", FONT_SERIF_BI, 78, COLOR_WHITE), ("your", FONT_SERIF_BI, 86, COLOR_NEON_GREEN), ("trade", FONT_SERIF_BI, 78, COLOR_WHITE)],
                y_pos=1600,
                progress=u,
                global_time=global_time,
                direction="right",
                entry_direction="right",
                exit_direction="right",
                slide_distance=500,
                max_tilt_deg=2.5,
            )
        elif scene_progress < 0.70:
            # Kinetic Punch: you cant equip. (Dramatic punch zoom)
            u = (scene_progress - 0.45) / 0.25
            draw_kinetic_caption_line(
                bg,
                [("you cant", FONT_SANS_BOLD, 88, COLOR_YELLOW)],
                y_pos=int(height * 0.44),
                progress=u,
                global_time=global_time,
                direction="zoom",
                slide_distance=0,
            )
            draw_kinetic_caption_line(
                bg,
                [("equip.", FONT_SERIF_BI, 115, COLOR_WHITE)],
                y_pos=int(height * 0.51),
                progress=u,
                global_time=global_time,
                direction="zoom",
                slide_distance=0,
            )
        else:
            # Grand Outro Call To Action: "go to tradeit.gg" sweeps from LEFT, "and enter MESTO300" sweeps from RIGHT
            u = (scene_progress - 0.70) / 0.30
            draw_kinetic_caption_line(
                bg,
                [("go to", FONT_SERIF_BI, 84, COLOR_WHITE), ("tradeit.gg", FONT_SERIF_BI, 84, COLOR_ELECTRIC_CYAN)],
                y_pos=int(height * 0.42),
                progress=u,
                global_time=global_time,
                direction="left",
                entry_direction="left",
                exit_direction="left",
                slide_distance=600,
                max_tilt_deg=3.2,
            )
            draw_kinetic_caption_line(
                bg,
                [("and enter", FONT_SERIF_BI, 84, COLOR_WHITE), (code, FONT_SERIF_BI, 84, COLOR_NEON_GREEN)],
                y_pos=int(height * 0.52),
                progress=u,
                global_time=global_time,
                direction="right",
                entry_direction="right",
                exit_direction="right",
                slide_distance=600,
                max_tilt_deg=3.2,
            )

    return bg
