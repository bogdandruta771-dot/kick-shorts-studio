"""Promo banner generator and image overlay processor using Pillow."""
import os
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont


def _get_font(font_size: int, bold: bool = True) -> ImageFont.ImageFont:
    """Loads a high-quality system font or falls back cleanly."""
    candidate_names = (
        ["impact.ttf", "arialbd.ttf", "segoeuib.ttf", "calibrib.ttf"]
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


def generate_hook_banner(
    text: str,
    style: str = "yellow_badge",
    width: int = 960,
    height: int = 160,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Renders a punchy, high-CTR viral engagement hook overlay banner (first 2-4s of Short).
    Designed to hook scrolling users immediately on TikTok/YouTube Shorts.
    """
    if output_path is None:
        raise ValueError("output_path must be provided.")
    output_path = Path(output_path)

    clean_text = text.strip() if text else "WAIT TILL THE END!"

    if style in ("floating_yellow", "ohnepixel_seam"):
        # Style: Floating White + Yellow Accent Headline (OhnePixel Seam Style)
        # Transparent background, no card box, pure punchy viral typography
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        raw_tokens = clean_text.split()
        tokens = []
        for t in raw_tokens:
            if t.startswith("*") and t.endswith("*") and len(t) > 2:
                tokens.append((t[1:-1], True))
            else:
                tokens.append((t, False))

        has_hl = any(h for _, h in tokens)
        if not has_hl and len(tokens) >= 2:
            hl_idx = 1
            for i, (w, _) in enumerate(tokens):
                if len(w) >= 6:
                    hl_idx = i
                    break
            tokens[hl_idx] = (tokens[hl_idx][0], True)

        font_size = 54
        if len(clean_text) > 34:
            font_size = 38
        elif len(clean_text) > 24:
            font_size = 46

        font = _get_font(font_size, bold=True) or ImageFont.load_default()
        space_w = draw.textlength(" ", font=font)
        word_widths = [draw.textlength(w, font=font) for w, _ in tokens]
        total_w = sum(word_widths) + (space_w * (len(tokens) - 1))

        start_x = (width - total_w) / 2
        mid_y = height / 2

        cur_x = start_x
        for (w, hl), ww in zip(tokens, word_widths):
            fill_col = (255, 215, 0, 255) if hl else (255, 255, 255, 255)
            word_center_x = cur_x + ww / 2
            # Drop shadow
            draw.text(
                (word_center_x + 4, mid_y + 4),
                w,
                font=font,
                fill=(0, 0, 0, 220),
                anchor="mm",
                stroke_width=6,
                stroke_fill=(0, 0, 0, 220),
            )
            # Main word with thick black stroke
            draw.text(
                (word_center_x, mid_y),
                w,
                font=font,
                fill=fill_col,
                anchor="mm",
                stroke_width=5,
                stroke_fill=(0, 0, 0, 255),
            )
            cur_x += ww + space_w

        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), format="PNG")
        return output_path

    elif style == "reddit_card":
        # Style: Authentic Reddit Dark Mode Post Card (Viral Reaction Opener)
        card_h = min(height, 220)
        img = Image.new("RGBA", (width, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Card container
        draw.rounded_rectangle(
            [(4, 4), (width - 4, card_h - 4)],
            radius=16,
            fill=(26, 26, 27, 245),
            outline=(52, 53, 54, 255),
            width=2,
        )

        # Reddit logo avatar
        draw.ellipse([(24, 18), (52, 46)], fill=(255, 69, 0, 255))
        draw.ellipse([(32, 26), (44, 38)], fill=(255, 255, 255, 255))

        font_meta = _get_font(18, bold=False) or ImageFont.load_default()
        draw.text(
            (62, 22),
            "r/GlobalOffensive  •  Posted by u/gamer  •  14h ago",
            font=font_meta,
            fill=(129, 131, 132, 255),
        )

        # Title
        post_title = clean_text.replace("*", "")
        font_title = _get_font(28, bold=True) or ImageFont.load_default()
        draw.text(
            (24, 62),
            post_title,
            font=font_title,
            fill=(215, 218, 220, 255),
        )

        # Flair badge
        t_bbox = draw.textbbox((24, 62), post_title, font=font_title)
        flair_x = t_bbox[2] + 16
        if flair_x < width - 130:
            draw.rounded_rectangle(
                [(flair_x, 64), (flair_x + 95, 92)],
                radius=6,
                fill=(0, 121, 211, 255),
            )
            font_flair = _get_font(15, bold=True) or ImageFont.load_default()
            draw.text(
                (flair_x + 47, 78),
                "Gameplay",
                font=font_flair,
                fill=(255, 255, 255, 255),
                anchor="mm",
            )

        # Bottom stat pills
        font_pill = _get_font(16, bold=True) or ImageFont.load_default()
        draw.rounded_rectangle([(24, 144), (140, 186)], radius=12, fill=(39, 39, 41, 255))
        draw.text((82, 165), "▲ 14.2k ▼", font=font_pill, fill=(129, 131, 132, 255), anchor="mm")

        draw.rounded_rectangle([(152, 144), (248, 186)], radius=12, fill=(39, 39, 41, 255))
        draw.text((200, 165), "🗨 842", font=font_pill, fill=(129, 131, 132, 255), anchor="mm")

        draw.rounded_rectangle([(260, 144), (350, 186)], radius=12, fill=(39, 39, 41, 255))
        draw.text((305, 165), "Share", font=font_pill, fill=(129, 131, 132, 255), anchor="mm")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), format="PNG")
        return output_path

    styles = {
        "yellow_badge": {
            "bg": "#0c0f17",
            "border": "#ffd700",
            "badge_bg": "#ffd700",
            "badge_text": "#000000",
            "badge_label": "★ WAIT FOR IT ★",
            "text": "#ffffff",
        },
        "red_alert": {
            "bg": "#15080b",
            "border": "#ff2a4b",
            "badge_bg": "#ff2a4b",
            "badge_text": "#ffffff",
            "badge_label": "🚨 DANGER / HIGH ALERT 🚨",
            "text": "#ffffff",
        },
        "tiktok_white": {
            "bg": "#07090e",
            "border": "#e2e8f0",
            "badge_bg": "#3b82f6",
            "badge_text": "#ffffff",
            "badge_label": "👀 WATCH THIS PLAY 👀",
            "text": "#ffffff",
        },
        "cyber_cyan": {
            "bg": "#040e17",
            "border": "#00f0ff",
            "badge_bg": "#ec4899",
            "badge_text": "#ffffff",
            "badge_label": "⚡ 1 IN A MILLION ⚡",
            "text": "#00f0ff",
        },
        "purple_glow": {
            "bg": "#0f081c",
            "border": "#a855f7",
            "badge_bg": "#a855f7",
            "badge_text": "#ffffff",
            "badge_label": "🔥 VIRAL MOMENT 🔥",
            "text": "#ffffff",
        },
    }

    st = styles.get(style, styles["yellow_badge"])

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bg_rgba = hex_to_rgba(st["bg"], 240)
    border_rgba = hex_to_rgba(st["border"], 240)
    badge_bg_rgba = hex_to_rgba(st["badge_bg"], 240)
    badge_text_rgba = hex_to_rgba(st["badge_text"], 255)
    text_rgba = hex_to_rgba(st["text"], 255)

    # 1. Main Container Card
    corner_radius = 20
    draw.rounded_rectangle(
        [(4, 4), (width - 4, height - 4)],
        radius=corner_radius,
        fill=bg_rgba,
        outline=border_rgba,
        width=3,
    )

    # 2. Top floating badge pill
    font_badge = _get_font(18, bold=True) or ImageFont.load_default()
    b_label = st["badge_label"]
    bbox_b = draw.textbbox((0, 0), b_label, font=font_badge)
    bw = (bbox_b[2] - bbox_b[0]) + 24
    bh = (bbox_b[3] - bbox_b[1]) + 10
    bx = (width - bw) // 2
    by = 12
    draw.rounded_rectangle(
        [(bx, by), (bx + bw, by + bh)],
        radius=8,
        fill=badge_bg_rgba,
    )
    draw.text(
        (bx + bw // 2, by + bh // 2),
        b_label,
        font=font_badge,
        fill=badge_text_rgba,
        anchor="mm",
    )

    # 3. Main Hook Text
    font_size = 46
    if len(clean_text) > 34:
        font_size = 32
    elif len(clean_text) > 26:
        font_size = 38
    elif len(clean_text) > 20:
        font_size = 42

    font_main = _get_font(font_size, bold=True) or ImageFont.load_default()
    main_y = by + bh + ((height - (by + bh)) // 2)

    # Drop shadow
    shadow_offset = 3
    draw.text(
        ((width // 2) + shadow_offset, main_y + shadow_offset),
        clean_text,
        font=font_main,
        fill=(0, 0, 0, 220),
        anchor="mm",
    )
    # Main text
    draw.text(
        (width // 2, main_y),
        clean_text,
        font=font_main,
        fill=text_rgba,
        anchor="mm",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), format="PNG")
    return output_path
