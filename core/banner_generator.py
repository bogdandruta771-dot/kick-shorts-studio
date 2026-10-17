"""Promo banner generator and image overlay processor using Pillow."""
import os
import unicodedata
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


def _get_emoji_font(font_size: int) -> Optional[ImageFont.ImageFont]:
    """Loads a high-quality system color emoji font with native support in Pillow."""
    candidate_paths = [
        Path("C:/Windows/Fonts/seguiemj.ttf"),
        Path("/System/Library/Fonts/Apple Color Emoji.ttc"),
        Path("/Library/Fonts/Apple Color Emoji.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"),
        Path("/usr/share/fonts/google-noto-color-emoji/NotoColorEmoji.ttf"),
    ]
    for p in candidate_paths:
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), font_size)
            except Exception:
                continue
    return None


def is_emoji_char(ch: str) -> bool:
    """Returns True if the character is an emoji or emoji-related modifier."""
    cp = ord(ch)
    if 0x1F300 <= cp <= 0x1FAFF:  # Emoticons, Pictographs, Supplemental, Transport
        return True
    if 0x2600 <= cp <= 0x27BF:    # Misc Symbols, Dingbats
        return True
    if 0x2300 <= cp <= 0x23FF:    # Misc technical (watch, hourglass, etc.)
        return True
    if 0x2B00 <= cp <= 0x2BFF:    # Misc symbols & arrows (stars, squares)
        return True
    if 0xFE00 <= cp <= 0xFE0F:    # Variation selectors (emoji presentation)
        return True
    if cp in (0x200D, 0x20E3):    # ZWJ, keycap enclosing
        return True
    cat = unicodedata.category(ch)
    if cat in ("So", "Sk") and cp > 0x00A0:
        return True
    return False


def split_text_and_emojis(text: str):
    """Splits text into contiguous runs of normal text and emojis."""
    runs = []
    current_run = ""
    current_is_emoji = None
    for ch in text:
        is_em = is_emoji_char(ch)
        if current_is_emoji is None:
            current_is_emoji = is_em
            current_run = ch
        elif is_em == current_is_emoji:
            current_run += ch
        else:
            runs.append((current_run, current_is_emoji))
            current_run = ch
            current_is_emoji = is_em
    if current_run:
        runs.append((current_run, current_is_emoji))
    return runs


def measure_rich_text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, font_size: int) -> float:
    """Measures total width of string taking emoji fallback fonts into account."""
    emoji_font = _get_emoji_font(font_size)
    if not emoji_font:
        return draw.textlength(text, font=font)
    runs = split_text_and_emojis(text)
    total = 0.0
    for r_txt, is_em in runs:
        f = emoji_font if (is_em and emoji_font) else font
        total += draw.textlength(r_txt, font=f)
    return total


def draw_rich_text(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    font_size: int,
    fill: Tuple[int, int, int, int],
    anchor: str = "la",
    stroke_width: int = 0,
    stroke_fill: Optional[Tuple[int, int, int, int]] = None,
    is_shadow: bool = False,
) -> float:
    """
    Renders text with full-color emoji support via system emoji fonts.
    Returns total rendered width.
    """
    emoji_font = _get_emoji_font(font_size)
    if not emoji_font:
        draw.text(xy, text, font=font, fill=fill, anchor=anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)
        return draw.textlength(text, font=font)

    runs = split_text_and_emojis(text)
    has_emoji = any(is_em for _, is_em in runs)
    if not has_emoji:
        draw.text(xy, text, font=font, fill=fill, anchor=anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)
        return draw.textlength(text, font=font)

    run_widths = []
    total_w = 0.0
    for r_txt, is_em in runs:
        f = emoji_font if (is_em and emoji_font) else font
        rw = draw.textlength(r_txt, font=f)
        run_widths.append(rw)
        total_w += rw

    if anchor.startswith(("m", "c")):
        start_x = xy[0] - (total_w / 2.0)
    elif anchor.startswith("r"):
        start_x = xy[0] - total_w
    else:
        start_x = xy[0]

    run_anchor = "lm" if "m" in anchor else "la"

    cur_x = start_x
    for (r_txt, is_em), rw in zip(runs, run_widths):
        f = emoji_font if (is_em and emoji_font) else font
        if is_em:
            if not is_shadow:
                draw.text((cur_x, xy[1]), r_txt, font=emoji_font, embedded_color=True, anchor=run_anchor)
        else:
            draw.text(
                (cur_x, xy[1]),
                r_txt,
                font=font,
                fill=fill,
                anchor=run_anchor,
                stroke_width=stroke_width,
                stroke_fill=stroke_fill,
            )
        cur_x += rw
    return total_w


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
        b_w = measure_rich_text_width(draw, b_text, font=font_badge, font_size=20) + 24
        b_h = 28

        # Draw pill
        draw.rounded_rectangle(
            [(content_x_start, 18), (content_x_start + b_w, 18 + b_h)],
            radius=8,
            fill=badge_bg,
            outline=border_rgba,
            width=1,
        )
        draw_rich_text(
            draw,
            (content_x_start + 12, 22),
            b_text,
            font=font_badge,
            font_size=20,
            fill=border_rgba,
            anchor="la",
        )
        content_x_start += b_w + 24

    # Main Promo Text (e.g. USE CODE: BOGDAN)
    clean_text = text.strip() if text else "USE CODE: BIGWIN"
    # Text shadow for pop
    shadow_offset = 2
    if has_sub:
        main_y = 44
        draw_rich_text(draw, (content_x_start + shadow_offset, main_y + shadow_offset), clean_text, font=font_main, font_size=42, fill=(0, 0, 0, 180), anchor="la", is_shadow=True)
        draw_rich_text(draw, (content_x_start, main_y), clean_text, font=font_main, font_size=42, fill=text_rgba, anchor="la", is_shadow=False)

        # Subtext line
        clean_sub = sub_text.strip()
        draw_rich_text(draw, (content_x_start, 96), clean_sub, font=font_sub, font_size=24, fill=subtext_rgba, anchor="la")
    else:
        # Centered vertically
        main_y = height // 2
        draw_rich_text(draw, (content_x_start + shadow_offset, main_y + shadow_offset), clean_text, font=font_main, font_size=42, fill=(0, 0, 0, 180), anchor="lm", is_shadow=True)
        draw_rich_text(draw, (content_x_start, main_y), clean_text, font=font_main, font_size=42, fill=text_rgba, anchor="lm", is_shadow=False)

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
        word_widths = [measure_rich_text_width(draw, w, font, font_size) for w, _ in tokens]
        total_w = sum(word_widths) + (space_w * (len(tokens) - 1))

        start_x = (width - total_w) / 2
        mid_y = height / 2

        cur_x = start_x
        for (w, hl), ww in zip(tokens, word_widths):
            fill_col = (255, 215, 0, 255) if hl else (255, 255, 255, 255)
            word_center_x = cur_x + ww / 2
            # Drop shadow (skip emoji layer in shadow)
            draw_rich_text(
                draw,
                (word_center_x + 4, mid_y + 4),
                w,
                font=font,
                font_size=font_size,
                fill=(0, 0, 0, 220),
                anchor="mm",
                stroke_width=6,
                stroke_fill=(0, 0, 0, 220),
                is_shadow=True,
            )
            # Main word with thick black stroke and vivid color emojis
            draw_rich_text(
                draw,
                (word_center_x, mid_y),
                w,
                font=font,
                font_size=font_size,
                fill=fill_col,
                anchor="mm",
                stroke_width=5,
                stroke_fill=(0, 0, 0, 255),
                is_shadow=False,
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
        draw_rich_text(
            draw,
            (24, 62),
            post_title,
            font=font_title,
            font_size=28,
            fill=(215, 218, 220, 255),
            anchor="la",
        )

        # Flair badge
        t_w = measure_rich_text_width(draw, post_title, font=font_title, font_size=28)
        flair_x = 24 + t_w + 16
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
        draw_rich_text(draw, (82, 165), "▲ 14.2k ▼", font=font_pill, font_size=16, fill=(129, 131, 132, 255), anchor="mm")

        draw.rounded_rectangle([(152, 144), (248, 186)], radius=12, fill=(39, 39, 41, 255))
        draw_rich_text(draw, (200, 165), "🗨 842", font=font_pill, font_size=16, fill=(129, 131, 132, 255), anchor="mm")

        draw.rounded_rectangle([(260, 144), (350, 186)], radius=12, fill=(39, 39, 41, 255))
        draw.text((305, 165), "Share", font=font_pill, fill=(129, 131, 132, 255), anchor="mm")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), format="PNG")
        return output_path

    elif style in ("twitter_x_card", "x_card", "tweet"):
        # Style: Authentic Twitter / X Dark Mode Tweet Post Card
        card_h = min(height, 220)
        img = Image.new("RGBA", (width, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Card container
        draw.rounded_rectangle(
            [(4, 4), (width - 4, card_h - 4)],
            radius=16,
            fill=(15, 20, 25, 245),
            outline=(47, 51, 54, 255),
            width=2,
        )

        # Avatar circle (X Blue)
        draw.ellipse([(24, 18), (56, 50)], fill=(29, 155, 240, 255))
        font_av = _get_font(20, bold=True) or ImageFont.load_default()
        draw.text((40, 34), "S", font=font_av, fill=(255, 255, 255, 255), anchor="mm")

        # Name, verified badge, handle
        font_name = _get_font(20, bold=True) or ImageFont.load_default()
        draw.text((66, 20), "Streamer Highlights", font=font_name, fill=(231, 233, 234, 255))

        # Verified Checkmark badge circle
        draw.ellipse([(268, 22), (284, 38)], fill=(29, 155, 240, 255))
        font_chk = _get_font(12, bold=True) or ImageFont.load_default()
        draw.text((276, 30), "✓", font=font_chk, fill=(255, 255, 255, 255), anchor="mm")

        font_handle = _get_font(16, bold=False) or ImageFont.load_default()
        draw.text((294, 22), "@streamer • 2h", font=font_handle, fill=(113, 118, 123, 255))

        # Top Right 𝕏 logo
        font_x = _get_font(22, bold=True) or ImageFont.load_default()
        draw.text((width - 36, 22), "𝕏", font=font_x, fill=(231, 233, 234, 255), anchor="mm")

        # Tweet main text
        post_title = clean_text.replace("*", "")
        font_size = 28 if len(post_title) < 40 else 24
        font_tweet = _get_font(font_size, bold=True) or ImageFont.load_default()
        draw_rich_text(
            draw,
            (24, 68),
            post_title,
            font=font_tweet,
            font_size=font_size,
            fill=(245, 245, 247, 255),
            anchor="la",
        )

        # Tweet engagement stats bar
        font_stats = _get_font(16, bold=False) or ImageFont.load_default()
        draw_rich_text(draw, (28, card_h - 32), "💬 1.4K", font=font_stats, font_size=16, fill=(113, 118, 123, 255), anchor="la")
        draw_rich_text(draw, (160, card_h - 32), "🔁 18.2K", font=font_stats, font_size=16, fill=(113, 118, 123, 255), anchor="la")
        draw_rich_text(draw, (310, card_h - 32), "❤️ 84.9K", font=font_stats, font_size=16, fill=(249, 24, 128, 255), anchor="la")
        draw_rich_text(draw, (470, card_h - 32), "📊 1.2M", font=font_stats, font_size=16, fill=(113, 118, 123, 255), anchor="la")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), format="PNG")
        return output_path

    elif style in ("tiktok_comment", "comment_bubble"):
        # Style: Authentic TikTok / Reels Reply Comment Bubble
        card_h = min(height, 180)
        img = Image.new("RGBA", (width, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Bubble container
        draw.rounded_rectangle(
            [(6, 6), (width - 6, card_h - 16)],
            radius=18,
            fill=(24, 26, 32, 248),
            outline=(44, 48, 58, 255),
            width=2,
        )

        # Speech bubble pointer (notch at bottom-left)
        draw.polygon([(40, card_h - 16), (65, card_h - 16), (40, card_h - 2)], fill=(24, 26, 32, 248))
        draw.line([(40, card_h - 16), (40, card_h - 2), (65, card_h - 16)], fill=(44, 48, 58, 255), width=2)

        # Avatar circle
        draw.ellipse([(24, 20), (56, 52)], fill=(254, 44, 85, 255))
        font_av = _get_font(18, bold=True) or ImageFont.load_default()
        draw_rich_text(draw, (40, 36), "👤", font=font_av, font_size=18, fill=(255, 255, 255, 255), anchor="mm")

        # Replying to @user
        font_sub = _get_font(16, bold=False) or ImageFont.load_default()
        draw.text((68, 24), "Replying to @viewer_clip", font=font_sub, fill=(160, 162, 170, 255))

        # Comment text
        post_title = clean_text.replace("*", "")
        font_size = 26 if len(post_title) < 42 else 22
        font_cmt = _get_font(font_size, bold=True) or ImageFont.load_default()
        draw_rich_text(
            draw,
            (68, 54),
            post_title,
            font=font_cmt,
            font_size=font_size,
            fill=(255, 255, 255, 255),
            anchor="la",
        )

        # Heart on right
        font_heart = _get_font(18, bold=True) or ImageFont.load_default()
        draw_rich_text(draw, (width - 55, 42), "❤️", font=font_heart, font_size=18, fill=(254, 44, 85, 255), anchor="mm")
        font_hcnt = _get_font(14, bold=True) or ImageFont.load_default()
        draw.text((width - 55, 66), "48.2k", font=font_hcnt, fill=(160, 162, 170, 255), anchor="mm")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), format="PNG")
        return output_path

    elif style in ("mrbeast_impact", "impact_neon"):
        # Style: High-octane MrBeast / Gaming Impact Typography
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Top pill: MUST WATCH / 1 IN A MILLION
        font_pill = _get_font(18, bold=True) or ImageFont.load_default()
        pill_txt = "🔥 NO WAY THIS HAPPENED 🔥"
        pw = measure_rich_text_width(draw, pill_txt, font=font_pill, font_size=18) + 24
        ph = 28
        px = (width - pw) // 2
        py = 8
        draw.rounded_rectangle([(px, py), (px + pw, py + ph)], radius=10, fill=(10, 10, 15, 230), outline=(34, 197, 94, 255), width=2)
        draw_rich_text(draw, (px + pw // 2, py + ph // 2), pill_txt, font=font_pill, font_size=18, fill=(34, 197, 94, 255), anchor="mm")

        # Main Impact Headline
        post_title = clean_text.replace("*", "").upper()
        font_size = 50 if len(post_title) < 22 else (40 if len(post_title) < 32 else 32)
        font_imp = _get_font(font_size, bold=True) or ImageFont.load_default()

        mid_y = py + ph + (height - (py + ph)) // 2

        # Shadow & Stroke
        draw_rich_text(
            draw,
            (width // 2 + 5, mid_y + 5),
            post_title,
            font=font_imp,
            font_size=font_size,
            fill=(0, 0, 0, 240),
            anchor="mm",
            stroke_width=8,
            stroke_fill=(0, 0, 0, 240),
            is_shadow=True,
        )
        draw_rich_text(
            draw,
            (width // 2, mid_y),
            post_title,
            font=font_imp,
            font_size=font_size,
            fill=(34, 197, 94, 255),
            anchor="mm",
            stroke_width=6,
            stroke_fill=(0, 0, 0, 255),
            is_shadow=False,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), format="PNG")
        return output_path

    elif style in ("breaking_news", "news_ticker"):
        # Style: Broadcast TV Breaking News Alert Banner
        card_h = min(height, 160)
        img = Image.new("RGBA", (width, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Bottom container bar
        draw.rectangle([(0, 36), (width, card_h - 4)], fill=(15, 23, 42, 245), outline=(220, 38, 38, 255), width=2)

        # Gold accent line at bottom
        draw.rectangle([(0, card_h - 8), (width, card_h - 4)], fill=(250, 204, 21, 255))

        # Red "🔴 LIVE BREAKING NEWS" tab
        draw.rectangle([(0, 4), (320, 40)], fill=(220, 38, 38, 255))
        font_live = _get_font(18, bold=True) or ImageFont.load_default()
        draw_rich_text(draw, (160, 22), "🔴 LIVE BREAKING NEWS", font=font_live, font_size=18, fill=(255, 255, 255, 255), anchor="mm")

        # Headline
        post_title = clean_text.replace("*", "").upper()
        font_size = 34 if len(post_title) < 28 else 26
        font_head = _get_font(font_size, bold=True) or ImageFont.load_default()
        draw_rich_text(draw, (width // 2, 78), post_title, font=font_head, font_size=font_size, fill=(255, 255, 255, 255), anchor="mm")

        # Ticker sub-text
        font_tick = _get_font(14, bold=False) or ImageFont.load_default()
        draw.text((width // 2, 118), "▶ REPORTED MOMENTS AGO ON LIVE STREAM • VIRAL CLIP OF THE DAY", font=font_tick, fill=(203, 213, 225, 255), anchor="mm")

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
    bw = measure_rich_text_width(draw, b_label, font=font_badge, font_size=18) + 24
    bh = 28
    bx = (width - bw) // 2
    by = 12
    draw.rounded_rectangle(
        [(bx, by), (bx + bw, by + bh)],
        radius=8,
        fill=badge_bg_rgba,
    )
    draw_rich_text(
        draw,
        (bx + bw // 2, by + bh // 2),
        b_label,
        font=font_badge,
        font_size=18,
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
    draw_rich_text(
        draw,
        ((width // 2) + shadow_offset, main_y + shadow_offset),
        clean_text,
        font=font_main,
        font_size=font_size,
        fill=(0, 0, 0, 220),
        anchor="mm",
        is_shadow=True,
    )
    # Main text
    draw_rich_text(
        draw,
        (width // 2, main_y),
        clean_text,
        font=font_main,
        font_size=font_size,
        fill=text_rgba,
        anchor="mm",
        is_shadow=False,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), format="PNG")
    return output_path
