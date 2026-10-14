"""Promo banner generator and image overlay processor using Pillow."""
import os
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont


def _get_font(font_size: int, bold: bool = True) -> ImageFont.ImageFont:
    """Loads a high-quality system font or falls back cleanly."""
    candidate_names = (
        ["arialbd.ttf", "segoeuib.ttf", "calibrib.ttf"]
        if bold
        else ["arial.ttf", "segoeui.ttf", "calibri.ttf"]
    )
    for name in candidate_names:
        win_font = Path("C:/Windows/Fonts") / name
        if win_font.is_file():
            try:
                return ImageFont.truetype(str(win_font), font_size)
            except Exception:
                continue

    # Fallback to default
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def hex_to_rgba(hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    """Converts hex color string to RGBA tuple."""
    clean = hex_color.strip().lstrip("#")
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    if len(clean) >= 6:
        r = int(clean[0:2], 16)
        g = int(clean[2:4], 16)
        b = int(clean[4:6], 16)
        return (r, g, b, alpha)
    return (20, 24, 38, alpha)


def generate_promo_banner(
    text: str,
    sub_text: Optional[str] = None,
    badge_text: Optional[str] = "PROMO CODE",
    bg_color_hex: str = "#0b0f19",
    text_color_hex: str = "#ffd700",
    accent_color_hex: str = "#00dcff",
    width: int = 1080,
    height: int = 140,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Renders a crisp, modern promo banner overlay (e.g., 'USE CODE: BOGDAN').
    Designed to cover casino watermarks, headers, or sit between reel & cam.
    """
    if output_path is None:
        raise ValueError("output_path must be provided.")

    # Create RGBA canvas
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bg_rgba = hex_to_rgba(bg_color_hex, 245)
    border_rgba = hex_to_rgba(accent_color_hex, 220)
    text_rgba = hex_to_rgba(text_color_hex, 255)
    subtext_rgba = hex_to_rgba("#e2e8f0", 220)
    badge_bg = hex_to_rgba(accent_color_hex, 45)

    # 1. Outer rounded container card with subtle border
    corner_radius = 16
    draw.rounded_rectangle(
        [(4, 4), (width - 4, height - 4)],
        radius=corner_radius,
        fill=bg_rgba,
        outline=border_rgba,
        width=3,
    )

    # 2. Left side accent glow line
    draw.rounded_rectangle(
        [(8, 8), (20, height - 8)],
        radius=6,
        fill=border_rgba,
    )

    # Fonts
    font_main = _get_font(42, bold=True)
    font_sub = _get_font(24, bold=False)
    font_badge = _get_font(20, bold=True)

    # Center placement calculations
    has_sub = bool(sub_text and sub_text.strip())
    has_badge = bool(badge_text and badge_text.strip())

    content_x_start = 50
    curr_y = 24 if has_sub else (height // 2)

    # Optional Pill Badge
    if has_badge:
        b_text = f"★ {badge_text.strip().upper()} ★"
        bbox = draw.textbbox((0, 0), b_text, font=font_badge)
        b_w = (bbox[2] - bbox[0]) + 24
        b_h = (bbox[3] - bbox[1]) + 12

        # Draw pill
        draw.rounded_rectangle(
            [(content_x_start, 18), (content_x_start + b_w, 18 + b_h)],
            radius=8,
            fill=badge_bg,
            outline=border_rgba,
            width=1,
        )
        draw.text(
            (content_x_start + 12, 22),
            b_text,
            font=font_badge,
            fill=border_rgba,
        )
        content_x_start += b_w + 24

    # Main Promo Text (e.g. USE CODE: BOGDAN)
    clean_text = text.strip() if text else "USE CODE: BIGWIN"
    # Text shadow for pop
    shadow_offset = 2
    if has_sub:
        main_y = 44
        draw.text((content_x_start + shadow_offset, main_y + shadow_offset), clean_text, font=font_main, fill=(0, 0, 0, 180))
        draw.text((content_x_start, main_y), clean_text, font=font_main, fill=text_rgba)

        # Subtext line
        clean_sub = sub_text.strip()
        draw.text((content_x_start, 96), clean_sub, font=font_sub, fill=subtext_rgba)
    else:
        # Centered vertically
        main_y = height // 2
        draw.text((content_x_start + shadow_offset, main_y + shadow_offset), clean_text, font=font_main, fill=(0, 0, 0, 180), anchor="lm")
        draw.text((content_x_start, main_y), clean_text, font=font_main, fill=text_rgba, anchor="lm")

    # Save PNG preserving transparency
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), format="PNG")
    return output_path


def process_uploaded_overlay(
    input_file_path: Path,
    output_path: Path,
) -> Tuple[int, int]:
    """
    Validates uploaded overlay image, converts to RGBA to preserve transparency,
    and saves to destination path. Returns (width, height).
    """
    if not input_file_path.is_file():
        raise FileNotFoundError(f"Uploaded file not found: {input_file_path}")

    with Image.open(input_file_path) as img:
        rgba = img.convert("RGBA")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        rgba.save(str(output_path), format="PNG")
        return rgba.size
