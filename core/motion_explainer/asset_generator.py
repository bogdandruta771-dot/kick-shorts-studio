"""
Motion Graphics 2.5D Visual Asset Generator
Programmatically renders photorealistic visual layers inspired by high-converting SaaS explainer Shorts:
1. Minimalist Dark Grid Background with Ambient Radial Glow
2. Floating 3D Credit / Crypto Card with Specular Shine & EMV Chip
3. Tilted Newspaper Article Card (NYT / WSJ / TechCrunch) with Authentic Typography
4. Sleek Smartphone App Mockup with Interactive Metrics & Animated Progress Bars
5. Warning / Sanction Security Badges
"""
import os
import math
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ASSETS_CACHE_DIR = Path(__file__).parent.parent / "assets" / "cache"
ASSETS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# System Font Resolvers with graceful fallbacks
def _get_font(font_type: str = "bold", size: int = 40):
    """Retrieves standard Windows fonts for typography."""
    candidates = {
        "serif_bold_italic": ["C:/Windows/Fonts/timesbi.ttf", "C:/Windows/Fonts/georgiaz.ttf"],
        "serif_bold": ["C:/Windows/Fonts/timesbd.ttf", "C:/Windows/Fonts/georgiab.ttf"],
        "sans_bold": ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf"],
        "gaming_impact": ["C:/Windows/Fonts/impact.ttf", "C:/Windows/Fonts/ariblk.ttf"],
        "sans_black": ["C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/arialbd.ttf"],
        "sans_regular": ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf"],
        "mono": ["C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/cour.ttf"],
    }
    for p in candidates.get(font_type, candidates["sans_bold"]):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


# ==============================================================================
# 1. MINIMALIST DARK GRID TILE BACKGROUND
# ==============================================================================
def create_dark_grid_background(
    width: int = 1080,
    height: int = 1920,
    grid_size: int = 135,
    glow_color: Tuple[int, int, int] = (32, 44, 76),
    bg_color: Tuple[int, int, int] = (12, 14, 20),
    line_color: Tuple[int, int, int, int] = (45, 52, 72, 80),
    offset_x: float = 0.0,
    offset_y: float = 0.0,
) -> Image.Image:
    """Generates the signature dark aesthetic grid tile background with ambient center glow."""
    img = Image.new("RGBA", (width, height), (*bg_color, 255))
    glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    # Ambient radial glow in center
    cx, cy = width // 2, height // 2
    max_radius = int(width * 0.75)
    for r in range(max_radius, 0, -15):
        alpha = int(45 * (1.0 - (r / max_radius)))
        glow_draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(*glow_color, alpha)
        )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=60))
    img = Image.alpha_composite(img, glow_layer)

    # Grid overlay
    grid_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid_layer)

    start_x = int(offset_x) % grid_size
    for x in range(start_x, width + grid_size, grid_size):
        grid_draw.line([(x, 0), (x, height)], fill=line_color, width=2)

    start_y = int(offset_y) % grid_size
    for y in range(start_y, height + grid_size, grid_size):
        grid_draw.line([(0, y), (width, y)], fill=line_color, width=2)

    return Image.alpha_composite(img, grid_layer)


# ==============================================================================
# 2. FLOATING 3D BANK / CREDIT / CRYPTO CARD
# ==============================================================================
def create_floating_card(
    width: int = 680,
    height: int = 425,
    card_type: str = "emerald",  # emerald, obsidian, violet, gold
    holder_name: str = "VERIFIED HOLDER",
    card_number: str = "•••• •••• •••• 0000",
    tilt_angle: float = -6.0,
    sheen_offset: float = 0.5,  # 0.0 to 1.0 animated specular reflection sweep
    custom_logo_path: Optional[str] = None,
) -> Image.Image:
    """Renders a sleek floating card with dynamic metallic sheen, EMV chip, and brand logo."""
    # Palette definition
    palettes = {
        "emerald": {"start": (24, 210, 110), "end": (10, 120, 65), "glow": (24, 210, 110, 70)},
        "obsidian": {"start": (36, 40, 52), "end": (15, 17, 24), "glow": (100, 120, 180, 50)},
        "violet": {"start": (138, 43, 226), "end": (45, 12, 105), "glow": (138, 43, 226, 70)},
        "gold": {"start": (255, 195, 18), "end": (160, 110, 10), "glow": (255, 195, 18, 60)},
    }
    p = palettes.get(card_type, palettes["emerald"])

    # Oversized canvas for shadow & tilt
    pad = 90
    canvas_w = width + pad * 2
    canvas_h = height + pad * 2
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # Base card graphic
    card_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card_img)

    # Gradient background
    for y in range(height):
        factor = y / height
        r = int(p["start"][0] * (1 - factor) + p["end"][0] * factor)
        g = int(p["start"][1] * (1 - factor) + p["end"][1] * factor)
        b = int(p["start"][2] * (1 - factor) + p["end"][2] * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Round card corners using mask
    corner_radius = 32
    mask = Image.new("L", (width, height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, width, height], radius=corner_radius, fill=255)
    card_img.putalpha(mask)

    # Dynamic metallic specular sheen sweep
    shine = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shine)
    sheen_center = int((width + height) * sheen_offset)
    for x in range(sheen_center - 160, sheen_center + 160, 4):
        dist = abs(x - sheen_center)
        if dist < 160:
            alpha = int(75 * math.cos((dist / 160.0) * (math.pi / 2)))
            s_draw.line([(x - height, height), (x, 0)], fill=(255, 255, 255, alpha), width=4)
    card_img = Image.alpha_composite(card_img, shine)
    draw = ImageDraw.Draw(card_img)

    # Gold EMV Chip
    chip_x, chip_y = 55, 95
    chip_w, chip_h = 75, 55
    draw.rounded_rectangle([chip_x, chip_y, chip_x + chip_w, chip_y + chip_h], radius=8, fill=(235, 190, 85))
    draw.rounded_rectangle([chip_x + 2, chip_y + 2, chip_x + chip_w - 2, chip_y + chip_h - 2], radius=6, outline=(175, 130, 40), width=2)
    # Chip contact lines
    draw.line([(chip_x, chip_y + chip_h // 2), (chip_x + chip_w, chip_y + chip_h // 2)], fill=(175, 130, 40), width=2)
    draw.line([(chip_x + chip_w // 2, chip_y), (chip_x + chip_w // 2, chip_y + chip_h)], fill=(175, 130, 40), width=2)

    # Contactless Wireless Wave Icon
    wave_x, wave_y = chip_x + chip_w + 30, chip_y + 12
    for r in [12, 22, 32]:
        draw.arc([wave_x - r, wave_y - r, wave_x + r, wave_y + r], start=-45, end=45, fill=(255, 255, 255, 200), width=3)

    # Logo: Custom uploaded logo or Dual-tone Mastercard Logo Circles
    if custom_logo_path and os.path.exists(custom_logo_path):
        try:
            custom_logo = Image.open(custom_logo_path).convert("RGBA")
            aspect = custom_logo.width / max(1, custom_logo.height)
            target_h = 55
            target_w = int(target_h * aspect)
            custom_logo = custom_logo.resize((target_w, target_h), resample=Image.BICUBIC)
            card_img.paste(custom_logo, (width - target_w - 40, chip_y), custom_logo)
        except Exception:
            mc_r = 38
            mc_x, mc_y = width - 110, chip_y + 10
            draw.ellipse([mc_x - mc_r, mc_y - mc_r, mc_x + mc_r, mc_y + mc_r], fill=(235, 0, 27, 240))
            draw.ellipse([mc_x + 35 - mc_r, mc_y - mc_r, mc_x + 35 + mc_r, mc_y + mc_r], fill=(247, 158, 27, 220))
    else:
        mc_r = 38
        mc_x, mc_y = width - 110, chip_y + 10
        draw.ellipse([mc_x - mc_r, mc_y - mc_r, mc_x + mc_r, mc_y + mc_r], fill=(235, 0, 27, 240))  # Red
        draw.ellipse([mc_x + 35 - mc_r, mc_y - mc_r, mc_x + 35 + mc_r, mc_y + mc_r], fill=(247, 158, 27, 220))  # Yellow/Orange

    # Embossed Card Number
    font_num = _get_font("sans_bold", 38)
    draw.text((55, 225), card_number, font=font_num, fill=(255, 255, 255, 245))

    # Cardholder & Expiry
    font_small = _get_font("sans_bold", 22)
    font_tiny = _get_font("sans_regular", 16)
    draw.text((55, 305), "CARDHOLDER", font=font_tiny, fill=(255, 255, 255, 160))
    draw.text((55, 330), holder_name.upper(), font=font_small, fill=(255, 255, 255, 235))

    draw.text((width - 170, 305), "EXPIRES", font=font_tiny, fill=(255, 255, 255, 160))
    draw.text((width - 170, 330), "08/29", font=font_small, fill=(255, 255, 255, 235))

    # Border stroke
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=corner_radius, outline=(255, 255, 255, 60), width=2)

    # Render soft drop shadow
    shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rounded_rectangle(
        [pad + 10, pad + 25, pad + width + 10, pad + height + 25],
        radius=corner_radius + 4,
        fill=(0, 0, 0, 140)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=28))
    canvas.paste(shadow, (0, 0), shadow)

    # Paste card onto canvas
    canvas.paste(card_img, (pad, pad), card_img)

    # Apply 3D perspective / tilt rotation
    if tilt_angle != 0.0:
        canvas = canvas.rotate(tilt_angle, resample=Image.BICUBIC, expand=True)

    return canvas


# ==============================================================================
# 3. TILTED NEWSPAPER CLIPPING / HEADLINE CARD
# ==============================================================================
def create_newspaper_clipping(
    headline: str = "FBI Tracks Suspect Through a Contaminated Crypto Wallet",
    source: str = "The New York Times",
    author: str = "By Somini Sengupta",
    date_str: str = "March 27, 2026",
    body_text: Optional[str] = None,
    width: int = 860,
    height: int = 1200,
    tilt_angle: float = -3.5,
    highlight_phrase: Optional[str] = None,
    marker_progress: float = 1.0,  # 0.0 to 1.0 animated marker swipe
    marker_color: Tuple[int, int, int] = (255, 235, 59),  # Translucent neon yellow highlighter
    custom_image_path: Optional[str] = None,
) -> Image.Image:
    """Renders a realistic newspaper front page with drop shadow, serif editorial typography, and animated highlighter marker swipe."""
    pad = 80
    canvas_w = width + pad * 2
    canvas_h = height + pad * 2
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # If user provided a custom newspaper image/screenshot, frame and render that directly
    if custom_image_path and os.path.exists(custom_image_path):
        try:
            custom_img = Image.open(custom_image_path).convert("RGBA")
            custom_img = custom_img.resize((width, height), resample=Image.BICUBIC)
            mask = Image.new("L", (width, height), 0)
            m_draw = ImageDraw.Draw(mask)
            m_draw.rounded_rectangle([0, 0, width, height], radius=28, fill=255)
            custom_img.putalpha(mask)

            shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            s_draw = ImageDraw.Draw(shadow)
            s_draw.rounded_rectangle(
                [pad + 15, pad + 30, pad + width + 15, pad + height + 30],
                radius=36,
                fill=(0, 0, 0, 160)
            )
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=34))
            canvas.paste(shadow, (0, 0), shadow)
            canvas.paste(custom_img, (pad, pad), custom_img)
            if tilt_angle != 0.0:
                canvas = canvas.rotate(tilt_angle, resample=Image.BICUBIC, expand=True)
            return canvas
        except Exception:
            pass

    # Paper sheet with warm off-white newsprint tint
    paper = Image.new("RGBA", (width, height), (252, 251, 248, 255))
    draw = ImageDraw.Draw(paper)

    # Masthead header (The New York Times style)
    font_masthead = _get_font("serif_bold", 54)
    draw.text((width // 2, 85), source, font=font_masthead, fill=(18, 18, 18), anchor="mm")

    # Double rule below masthead
    draw.line([(50, 125), (width - 50, 125)], fill=(30, 30, 30), width=2)
    draw.line([(50, 131), (width - 50, 131)], fill=(30, 30, 30), width=1)

    # Action bar (Share / Bookmark pill simulation)
    font_bar = _get_font("sans_regular", 20)
    draw.rounded_rectangle([50, 155, 230, 195], radius=20, outline=(200, 200, 200), width=1)
    draw.text((140, 175), "Share full article", font=font_bar, fill=(70, 70, 70), anchor="mm")

    # Author & Date
    font_author = _get_font("sans_bold", 24)
    font_date = _get_font("sans_regular", 20)
    draw.text((50, 235), author, font=font_author, fill=(35, 35, 35))
    draw.text((50, 270), date_str, font=font_date, fill=(110, 110, 110))

    # Main Headline (Heavy serif) with word tokenization for highlighter
    font_headline = _get_font("serif_bold", 58)
    words = headline.split()
    headline_lines = []
    cur_line = []
    for w in words:
        test = " ".join(cur_line + [w])
        bbox = draw.textbbox((0, 0), test, font=font_headline)
        if bbox[2] - bbox[0] > (width - 100) and cur_line:
            headline_lines.append(cur_line)
            cur_line = [w]
        else:
            cur_line.append(w)
    if cur_line:
        headline_lines.append(cur_line)

    # Highlighter Marker Swipe Effect
    clean_high = (highlight_phrase or "").lower().strip()
    high_words = [hw.strip(",.!?").lower() for hw in clean_high.split() if hw.strip()]

    marker_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    m_draw = ImageDraw.Draw(marker_layer)
    y_pos = 325

    for line in headline_lines[:3]:
        x_cur = 50
        for w in line:
            w_clean = w.strip(",.!?").lower()
            bbox = draw.textbbox((0, 0), w + " ", font=font_headline)
            w_w = bbox[2] - bbox[0]

            if clean_high and (w_clean in high_words or w_clean in clean_high):
                swipe_w = int(w_w * max(0.0, min(1.0, marker_progress)))
                if swipe_w > 0:
                    m_draw.rounded_rectangle(
                        [x_cur - 4, y_pos + 6, x_cur + swipe_w + 4, y_pos + 66],
                        radius=6,
                        fill=(*marker_color, 165)
                    )
            x_cur += w_w
        y_pos += 70

    paper = Image.alpha_composite(paper, marker_layer)
    draw = ImageDraw.Draw(paper)

    # Draw crisp black headline text over paper & marker
    y_pos = 325
    for line in headline_lines[:3]:
        line_str = " ".join(line)
        draw.text((50, y_pos), line_str, font=font_headline, fill=(15, 15, 15))
        y_pos += 70

    # Separator line
    y_pos += 20
    draw.line([(50, y_pos), (width - 50, y_pos)], fill=(215, 215, 215), width=1)
    y_pos += 30

    # Article Body Text
    if not body_text:
        body_text = (
            "A crypto user was taken into custody after federal investigators "
            "connected one of the transactions in his wallet to funds associated with illicit activity.\n\n"
            "According to the investigation, the user had received tokens from an external address "
            "without checking its risk score or history. The transfer appeared completely ordinary at first. "
            "The amount was not unusually large, and there were no obvious warning signs inside the wallet interface.\n\n"
            "However, on-chain blockchain analysis revealed that the sender address was directly linked "
            "to stolen assets and flagged mixers under surveillance by law enforcement.\n\n"
            "Investigators were able to trace the movement across permanent ledger records, "
            "freezing linked exchange accounts."
        )

    font_body = _get_font("serif_regular", 28)
    paragraphs = body_text.split("\n\n")

    for para in paragraphs:
        p_words = para.split()
        p_lines = []
        p_cur = []
        for w in p_words:
            test = " ".join(p_cur + [w])
            bbox = draw.textbbox((0, 0), test, font=font_body)
            if bbox[2] - bbox[0] > (width - 100) and p_cur:
                p_lines.append(" ".join(p_cur))
                p_cur = [w]
            else:
                p_cur.append(w)
        if p_cur:
            p_lines.append(" ".join(p_cur))

        for line in p_lines:
            if y_pos > height - 60:
                break
            draw.text((50, y_pos), line, font=font_body, fill=(45, 45, 45))
            y_pos += 38
        y_pos += 25

    # Rounded corners mask
    mask = Image.new("L", (width, height), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle([0, 0, width, height], radius=28, fill=255)
    paper.putalpha(mask)

    # Realistic layered drop shadow
    shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rounded_rectangle(
        [pad + 15, pad + 30, pad + width + 15, pad + height + 30],
        radius=36,
        fill=(0, 0, 0, 160)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=34))
    canvas.paste(shadow, (0, 0), shadow)

    canvas.paste(paper, (pad, pad), paper)

    if tilt_angle != 0.0:
        canvas = canvas.rotate(tilt_angle, resample=Image.BICUBIC, expand=True)

    return canvas


# ==============================================================================
# 4. SLEEK 3D SMARTPHONE APP MOCKUP
# ==============================================================================
def create_smartphone_app_mockup(
    width: int = 740,
    height: int = 1480,
    app_name: str = "AML Check",
    risk_score: str = "12.55%",
    status_label: str = "Rating scored from A to F, clean wallet",
    button_text: str = "Check your wallet",
    progress_pct: float = 1.0,      # 0.0 to 1.0 for animating metric bars
    counter_progress: float = 1.0,  # 0.0 to 1.0 for dynamic number count-up & ring arc
    custom_screenshot_path: Optional[str] = None,
) -> Image.Image:
    """Renders a sleek smartphone mockup displaying interactive risk metrics, animated progress bars, or custom app screenshots."""
    pad = 70
    canvas_w = width + pad * 2
    canvas_h = height + pad * 2
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # If user provided an uploaded app screenshot, frame it perfectly inside phone chassis
    if custom_screenshot_path and os.path.exists(custom_screenshot_path):
        try:
            custom_screen = Image.open(custom_screenshot_path).convert("RGBA")
            phone = Image.new("RGBA", (width, height), (15, 17, 26, 255))
            screen_w = width - 24
            screen_h = height - 50
            custom_screen = custom_screen.resize((screen_w, screen_h), resample=Image.BICUBIC)
            phone.paste(custom_screen, (12, 38), custom_screen)

            # Draw sleek iPhone Dynamic Island notch at top
            island_w, island_h = 180, 36
            island_x = (width - island_w) // 2
            p_draw = ImageDraw.Draw(phone)
            p_draw.rounded_rectangle([island_x, 14, island_x + island_w, 14 + island_h], radius=18, fill=(0, 0, 0))
            p_draw.ellipse([island_x + island_w - 36, 22, island_x + island_w - 18, 40], fill=(20, 20, 45))  # Camera lens

            corner_r = 54
            mask = Image.new("L", (width, height), 0)
            m_draw = ImageDraw.Draw(mask)
            m_draw.rounded_rectangle([0, 0, width, height], radius=corner_r, fill=255)
            phone.putalpha(mask)

            p_draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=corner_r, outline=(210, 215, 225), width=5)

            shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            s_draw = ImageDraw.Draw(shadow)
            s_draw.rounded_rectangle(
                [pad + 10, pad + 35, pad + width + 10, pad + height + 35],
                radius=corner_r + 8,
                fill=(0, 0, 0, 175)
            )
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=36))
            canvas.paste(shadow, (0, 0), shadow)
            canvas.paste(phone, (pad, pad), phone)
            return canvas
        except Exception:
            pass

    # Phone chassis
    phone = Image.new("RGBA", (width, height), (248, 249, 252, 255))
    draw = ImageDraw.Draw(phone)

    # Dynamic Island notch
    island_w, island_h = 180, 36
    island_x = (width - island_w) // 2
    draw.rounded_rectangle([island_x, 14, island_x + island_w, 14 + island_h], radius=18, fill=(0, 0, 0))

    # Header section
    font_title = _get_font("sans_bold", 36)
    font_sub = _get_font("sans_bold", 24)

    # Blue app icon circle
    draw.ellipse([45, 65, 95, 115], fill=(26, 115, 232))
    draw.ellipse([58, 78, 82, 102], fill=(248, 249, 252))  # Ring
    draw.text((115, 90), app_name, font=font_title, fill=(20, 20, 20), anchor="lm")

    # Hamburger menu icon
    for y in [80, 90, 100]:
        draw.line([(width - 85, y), (width - 45, y)], fill=(80, 80, 80), width=3)

    # Subtitle / Protection banner
    banner_y = 155
    draw.text(
        (width // 2, banner_y),
        "By checking your wallet, you protect yourself",
        font=font_sub,
        fill=(50, 50, 50),
        anchor="mm"
    )
    draw.text(
        (width // 2, banner_y + 35),
        "from scammers and stolen coins.",
        font=font_sub,
        fill=(50, 50, 50),
        anchor="mm"
    )

    # Central Card Box for score & metrics
    card_x1, card_y1 = 45, 240
    card_x2, card_y2 = width - 45, height - 160
    draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=24, fill=(255, 255, 255), outline=(230, 232, 240), width=2)

    # Large Circular Risk Ring with Animated Progress Arc
    ring_cx, ring_cy = width // 2, 340
    r_outer = 64
    r_inner = 46
    # Gray background ring
    draw.ellipse([ring_cx - r_outer, ring_cy - r_outer, ring_cx + r_outer, ring_cy + r_outer], fill=(235, 238, 245))
    # Colored dynamic progress arc
    fill_angle = int(360 * max(0.04, min(1.0, counter_progress)))
    draw.pieslice([ring_cx - r_outer, ring_cy - r_outer, ring_cx + r_outer, ring_cy + r_outer], start=-90, end=-90 + fill_angle, fill=(26, 115, 232))
    # Inner white circle cutout
    draw.ellipse([ring_cx - r_inner, ring_cy - r_inner, ring_cx + r_inner, ring_cy + r_inner], fill=(255, 255, 255))

    # Dynamic numeric count-up
    import re
    score_display = risk_score
    nums = re.findall(r"\d+\.?\d*", risk_score)
    if nums and counter_progress < 1.0:
        target_val = float(nums[0])
        cur_val = target_val * max(0.0, min(1.0, counter_progress))
        if "." in nums[0]:
            score_display = risk_score.replace(nums[0], f"{cur_val:.2f}")
        else:
            score_display = risk_score.replace(nums[0], f"{int(cur_val)}")

    font_score = _get_font("sans_bold", 46)
    draw.text((width // 2, ring_cy + 90), score_display, font=font_score, fill=(20, 25, 40), anchor="mm")

    font_caption = _get_font("sans_regular", 18)
    draw.text(
        (width // 2, ring_cy + 135),
        status_label,
        font=font_caption,
        fill=(140, 145, 160),
        anchor="mm"
    )

    # Metric breakdown bars
    metrics = [
        ("Transaction diversity", 0.20, (26, 115, 232)),       # Blue
        ("Wallet activity", 0.70, (46, 204, 113)),            # Green
        ("Transaction to/from CEX", 0.20, (26, 115, 232)),    # Blue
        ("Avg. Transaction Value", 0.60, (46, 204, 113)),     # Green
        ("Wallet Age", 0.60, (46, 204, 113)),                 # Green
        ("Suspicious transactions", 0.55, (243, 156, 18)),     # Orange
        ("Transaction to High-Risk addresses", 0.55, (235, 87, 87)), # Red
    ]

    bar_y = ring_cy + 185
    font_label = _get_font("sans_bold", 20)
    font_val = _get_font("sans_bold", 20)
    bar_w = card_x2 - card_x1 - 80

    for name, target_ratio, color in metrics:
        draw.text((card_x1 + 40, bar_y), name, font=font_label, fill=(40, 45, 55))
        pct_display = f"{int(target_ratio * 100)}%"
        draw.text((card_x2 - 40, bar_y), pct_display, font=font_val, fill=(30, 30, 30), anchor="ra")

        # Bar track
        track_y = bar_y + 30
        draw.rounded_rectangle([card_x1 + 40, track_y, card_x1 + 40 + bar_w, track_y + 10], radius=5, fill=(240, 242, 248))

        # Animated fill
        current_w = max(6, int(bar_w * target_ratio * progress_pct))
        draw.rounded_rectangle([card_x1 + 40, track_y, card_x1 + 40 + current_w, track_y + 10], radius=5, fill=color)

        bar_y += 65

    # Secondary "Share report" button inside card
    btn2_y = bar_y + 20
    draw.rounded_rectangle([card_x1 + 40, btn2_y, card_x2 - 40, btn2_y + 60], radius=16, fill=(26, 115, 232))
    font_btn = _get_font("sans_bold", 22)
    draw.text((width // 2, btn2_y + 30), "Share report", font=font_btn, fill=(255, 255, 255), anchor="mm")

    # Primary Big CTA Button outside
    cta_y = height - 120
    draw.rounded_rectangle([45, cta_y, width - 45, cta_y + 75], radius=38, fill=(0, 112, 243))
    font_cta = _get_font("sans_bold", 28)
    draw.text((width // 2, cta_y + 37), button_text, font=font_cta, fill=(255, 255, 255), anchor="mm")

    # Phone chassis rounded corners & border
    corner_r = 54
    mask = Image.new("L", (width, height), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle([0, 0, width, height], radius=corner_r, fill=255)
    phone.putalpha(mask)

    p_draw = ImageDraw.Draw(phone)
    p_draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=corner_r, outline=(210, 215, 225), width=4)

    # Soft 3D drop shadow
    shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rounded_rectangle(
        [pad + 10, pad + 35, pad + width + 10, pad + height + 35],
        radius=corner_r + 8,
        fill=(0, 0, 0, 175)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=36))
    canvas.paste(shadow, (0, 0), shadow)

    canvas.paste(phone, (pad, pad), phone)
    return canvas


# ==============================================================================
# 5. KINETIC TYPOGRAPHY CAPTION OVERLAY
def render_kinetic_caption(
    text: str,
    width: int = 1080,
    height: int = 1920,
    position: str = "top",  # "top" or "bottom"
    y_offset_pct: Optional[float] = None,  # Custom percentage Y slider from UI (0.0 to 1.0)
    font_size: int = 92,
    font_family: str = "gaming_impact",  # "gaming_impact", "sans_black", "serif_bold_italic"
    primary_color: Tuple[int, int, int] = (255, 255, 255),
    highlight_color: Tuple[int, int, int] = (235, 50, 75),  # Crimson / Blue / Neon Green
    active_word: Optional[str] = None,
    active_word_index: Optional[int] = None,
    bounce_active: bool = True,
    uppercase: bool = True,
) -> Image.Image:
    """Renders high-impact kinetic typography with word popping, neon pill glow, and customizable vertical positioning."""
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font = _get_font(font_family, font_size)
    font_bounce = _get_font(font_family, int(font_size * 1.14)) if bounce_active else font
    raw_words = text.split()
    if not raw_words:
        return overlay

    words = [w.upper() if uppercase else w for w in raw_words]

    # Break into 1 or 2 lines
    lines = []
    if len(words) <= 3:
        lines = [words]
    else:
        mid = (len(words) + 1) // 2
        lines = [words[:mid], words[mid:]]

    if y_offset_pct is not None:
        y_start = int(height * y_offset_pct)
    else:
        y_start = 220 if position == "top" else 1580

    global_w_idx = 0
    for line_idx, line in enumerate(lines):
        line_w = 0
        word_widths = []
        for w in line:
            is_active = (active_word and active_word.lower().strip(",.!?") == w.lower().strip(",.!?")) or (active_word_index is not None and active_word_index == global_w_idx)
            w_font = font_bounce if (is_active and bounce_active) else font
            bbox = draw.textbbox((0, 0), w + " ", font=w_font)
            w_len = bbox[2] - bbox[0]
            word_widths.append((w_len, (is_active and bounce_active)))
            line_w += w_len

        x_cur = (width - line_w) // 2
        y_cur = y_start + line_idx * int(font_size * 1.25)

        for w_idx, w in enumerate(line):
            w_len, is_bounced = word_widths[w_idx]
            is_active = (active_word and active_word.lower().strip(",.!?") == w.lower().strip(",.!?")) or (active_word_index is not None and active_word_index == global_w_idx)
            color = highlight_color if is_active else primary_color
            cur_font = font_bounce if is_bounced else font

            if is_active:
                # Translucent rounded neon pill glow badge behind active bouncing word
                glow_pad_x = 12
                glow_pad_y = 6
                draw.rounded_rectangle(
                    [x_cur - glow_pad_x, y_cur - glow_pad_y, x_cur + w_len - 10 + glow_pad_x, y_cur + font_size + glow_pad_y],
                    radius=14,
                    fill=(*highlight_color, 45),
                    outline=(*highlight_color, 110),
                    width=2,
                )

            # Multi-angle heavy stroke drop shadow for ultra-clear visibility
            for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 5), (4, 4), (-2, 4)]:
                draw.text((x_cur + dx, y_cur + dy), w, font=cur_font, fill=(0, 0, 0, 220))
            draw.text((x_cur, y_cur), w, font=cur_font, fill=(*color, 255))
            x_cur += w_len
            global_w_idx += 1

    return overlay



# ==============================================================================
# VECTOR ICON HELPER (Crisp Icons Without System Font Tofu)
# ==============================================================================
def draw_vector_icon(draw: ImageDraw.ImageDraw, icon_type: str, cx: int, cy: int, size: int = 18):
    """Draws crisp geometric vector icons (star, check, cross, bolt, gift) reliably across all platforms."""
    if icon_type == "star":
        pts = []
        r_out = size
        r_in = size * 0.42
        for i in range(10):
            r = r_out if i % 2 == 0 else r_in
            angle = i * (math.pi / 5) - (math.pi / 2)
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        draw.polygon(pts, fill=(255, 215, 0), outline=(210, 160, 20))

    elif icon_type == "check":
        draw.ellipse([cx - size, cy - size, cx + size, cy + size], fill=(16, 185, 90))
        pts = [
            (cx - size * 0.45, cy),
            (cx - size * 0.1, cy + size * 0.4),
            (cx + size * 0.5, cy - size * 0.35),
        ]
        draw.line(pts, fill=(255, 255, 255), width=max(2, size // 4))

    elif icon_type == "cross":
        draw.ellipse([cx - size, cy - size, cx + size, cy + size], fill=(225, 35, 50))
        d = size * 0.42
        draw.line([(cx - d, cy - d), (cx + d, cy + d)], fill=(255, 255, 255), width=max(2, size // 4))
        draw.line([(cx - d, cy + d), (cx + d, cy - d)], fill=(255, 255, 255), width=max(2, size // 4))

    elif icon_type == "bolt":
        draw.ellipse([cx - size, cy - size, cx + size, cy + size], fill=(255, 180, 0))
        bolt = [
            (cx + size * 0.1, cy - size * 0.6),
            (cx - size * 0.4, cy + size * 0.05),
            (cx, cy + size * 0.05),
            (cx - size * 0.1, cy + size * 0.6),
            (cx + size * 0.4, cy - size * 0.05),
            (cx, cy - size * 0.05),
        ]
        draw.polygon(bolt, fill=(255, 255, 255))

    elif icon_type == "gift":
        draw.ellipse([cx - size, cy - size, cx + size, cy + size], fill=(138, 43, 226))
        bx, by, bw, bh = cx - size * 0.45, cy - size * 0.3, size * 0.9, size * 0.75
        draw.rectangle([bx, by, bx + bw, by + bh], fill=(255, 215, 0))
        draw.line([(cx, by), (cx, by + bh)], fill=(235, 50, 75), width=2)
        draw.line([(bx, by + bh * 0.4), (bx + bw, by + bh * 0.4)], fill=(235, 50, 75), width=2)


# ==============================================================================
# 5. CS2 WEAPON / KNIFE SKIN 3D ITEM CARD
# ==============================================================================
def create_skin_item_card(
    width: int = 760,
    height: int = 500,
    skin_name: str = "★ Karambit | Doppler",
    skin_category: str = "Covert Knife",
    wear_rating: str = "Factory New • Float 0.00142",
    price_usd: str = "$1,850.00 USD",
    stattrak_count: Optional[str] = "001337",
    rarity: str = "covert",  # covert, rare_special, classified, restricted
    tilt_angle: float = -4.0,
    sheen_offset: float = 0.5,
    custom_skin_image_path: Optional[str] = None,
) -> Image.Image:
    """Renders a 3D CS2 Weapon/Knife skin card with StatTrak, wear meter, Doppler blade sheen, and price tag."""
    rarity_palettes = {
        "covert": {"color": (235, 50, 75), "bg": (22, 16, 20), "glow": (235, 50, 75, 70)},
        "rare_special": {"color": (255, 215, 0), "bg": (28, 24, 12), "glow": (255, 215, 0, 80)},
        "classified": {"color": (211, 44, 230), "bg": (24, 14, 28), "glow": (211, 44, 230, 70)},
        "restricted": {"color": (136, 71, 255), "bg": (18, 14, 30), "glow": (136, 71, 255, 70)},
    }
    p = rarity_palettes.get(rarity, rarity_palettes["covert"])
    rarity_col = p["color"]

    pad = 90
    canvas_w = width + pad * 2
    canvas_h = height + pad * 2
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    card_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card_img)

    # Dark tactical carbon gradient background
    for y in range(height):
        factor = y / height
        r = int(24 * (1 - factor) + 12 * factor)
        g = int(26 * (1 - factor) + 14 * factor)
        b = int(36 * (1 - factor) + 20 * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Ambient radial rarity spotlight in center
    spotlight = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    sp_draw = ImageDraw.Draw(spotlight)
    cx, cy = width // 2, int(height * 0.48)
    for rad in range(220, 0, -10):
        alpha = int(40 * (1.0 - (rad / 220.0)))
        sp_draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(*rarity_col, alpha))
    spotlight = spotlight.filter(ImageFilter.GaussianBlur(radius=25))
    card_img = Image.alpha_composite(card_img, spotlight)
    draw = ImageDraw.Draw(card_img)

    # Top Header: Category & StatTrak
    font_bold_small = _get_font("sans_bold", 22)
    font_impact = _get_font("gaming_impact", 42)
    font_regular_small = _get_font("sans_regular", 20)
    font_mono_bold = _get_font("mono", 22)

    # Clean category string and draw vector star
    clean_cat = skin_category.upper().replace("★", "").replace("*", "").strip()
    is_knife_or_glove = "knife" in clean_cat.lower() or "glove" in clean_cat.lower()
    cat_x = 45
    if is_knife_or_glove:
        draw_vector_icon(draw, "star", 55, 44, size=11)
        cat_x = 74
    draw.text((cat_x, 32), clean_cat, font=font_bold_small, fill=(*rarity_col, 255))

    # StatTrak Counter Pill (if applicable)
    if stattrak_count:
        st_box_x = width - 260
        st_box_y = 26
        draw.rounded_rectangle([st_box_x, st_box_y, width - 45, st_box_y + 36], radius=8, fill=(35, 18, 10, 240), outline=(255, 120, 20), width=2)
        draw.text((st_box_x + 12, st_box_y + 6), "StatTrak", font=font_bold_small, fill=(255, 130, 30))
        draw.text((st_box_x + 115, st_box_y + 6), stattrak_count, font=font_mono_bold, fill=(255, 185, 70))

    # Big Skin Title (e.g. Karambit | Doppler)
    clean_skin_name = skin_name.replace("★", "").replace("*", "").strip()
    draw.text((45, 66), clean_skin_name, font=font_impact, fill=(255, 255, 255, 250))

    # Wear & Float Info
    draw.text((45, 120), wear_rating, font=font_regular_small, fill=(185, 195, 215))

    # 5-Segmented Wear Meter Bar [FN | MW | FT | WW | BS]
    bar_x, bar_y, bar_w, bar_h = 45, 150, 280, 8
    segment_colors = [(76, 175, 80), (139, 195, 74), (255, 235, 59), (255, 152, 0), (244, 67, 54)]
    seg_w = bar_w // 5
    for idx, sc in enumerate(segment_colors):
        sx = bar_x + idx * seg_w
        draw.rectangle([sx, bar_y, sx + seg_w - 2, bar_y + bar_h], fill=sc)
    # Needle marker at Factory New position (~15px in)
    needle_x = bar_x + 16
    draw.polygon([(needle_x, bar_y - 4), (needle_x - 4, bar_y - 9), (needle_x + 4, bar_y - 9)], fill=(255, 255, 255))

    # Center Illustration: Weapon / Knife Graphic
    if custom_skin_image_path and os.path.exists(custom_skin_image_path):
        try:
            skin_img = Image.open(custom_skin_image_path).convert("RGBA")
            aspect = skin_img.width / max(1, skin_img.height)
            target_h = 240
            target_w = int(target_h * aspect)
            skin_img = skin_img.resize((target_w, target_h), resample=Image.BICUBIC)
            card_img.paste(skin_img, ((width - target_w) // 2, 170), skin_img)
        except Exception:
            pass
    else:
        # High-Fidelity Procedural CS2 Karambit Knife Rendering
        knife_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        k_draw = ImageDraw.Draw(knife_layer)

        # Karambit Ring & Handle
        ring_cx, ring_cy = width // 2 + 190, 240
        k_draw.ellipse([ring_cx - 38, ring_cy - 38, ring_cx + 38, ring_cy + 38], fill=(32, 35, 45), outline=(70, 75, 92), width=7)
        k_draw.ellipse([ring_cx - 21, ring_cy - 21, ring_cx + 21, ring_cy + 21], fill=(0, 0, 0, 0))  # Ring hole

        # Curved Handle Body
        handle_poly = [
            (ring_cx - 24, ring_cy + 10),
            (width // 2 + 80, 265),
            (width // 2 + 10, 280),
            (width // 2 + 15, 240),
            (width // 2 + 85, 225),
            (ring_cx - 20, ring_cy - 12),
        ]
        k_draw.polygon(handle_poly, fill=(26, 28, 36))
        # Handle texture grips & brass rivets
        for rivet_x, rivet_y in [(width // 2 + 50, 255), (width // 2 + 105, 245), (width // 2 + 155, 235)]:
            k_draw.ellipse([rivet_x - 5, rivet_y - 5, rivet_x + 5, rivet_y + 5], fill=(215, 175, 75), outline=(150, 115, 40))

        # Talon Curved Blade - Doppler Phase 2 Gradient (Navy Spine -> Magenta -> Bright Cyan Edge)
        blade_spine = [
            (width // 2 + 15, 240),
            (width // 2 - 70, 245),
            (width // 2 - 170, 260),
            (width // 2 - 250, 305),  # Talon tip
            (width // 2 - 190, 330),
            (width // 2 - 90, 315),
            (width // 2 + 10, 280),
        ]
        k_draw.polygon(blade_spine, fill=(195, 25, 145))

        # Deep Indigo Spine Shadow
        spine_bevel = [
            (width // 2 + 15, 240),
            (width // 2 - 70, 245),
            (width // 2 - 170, 260),
            (width // 2 - 250, 305),
            (width // 2 - 180, 285),
            (width // 2 - 90, 270),
            (width // 2, 260),
        ]
        k_draw.polygon(spine_bevel, fill=(40, 25, 85, 220))

        # Electric Doppler Sheen Swirls
        sheen_color = (0, 225, 255, 190) if (int(sheen_offset * 10) % 2 == 0) else (255, 60, 200, 210)
        inner_blade = [
            (width // 2 - 10, 275),
            (width // 2 - 95, 305),
            (width // 2 - 180, 318),
            (width // 2 - 245, 304),
            (width // 2 - 165, 266),
            (width // 2 - 70, 252),
        ]
        k_draw.polygon(inner_blade, fill=sheen_color)

        # Razor Blade Edge Highlight Stroke
        edge_pts = [(width // 2 + 10, 280), (width // 2 - 90, 315), (width // 2 - 190, 330), (width // 2 - 250, 305)]
        for ep_idx in range(len(edge_pts) - 1):
            k_draw.line([edge_pts[ep_idx], edge_pts[ep_idx + 1]], fill=(255, 255, 255, 240), width=3)

        # Star sparkle glint near blade tip
        tip_x, tip_y = width // 2 - 250, 305
        draw_vector_icon(k_draw, "star", tip_x, tip_y, size=9)

        card_img = Image.alpha_composite(card_img, knife_layer)
        draw = ImageDraw.Draw(card_img)

    # Specular sweep light sweep
    shine = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shine)
    sheen_center = int((width + height) * sheen_offset)
    for x in range(sheen_center - 140, sheen_center + 140, 4):
        dist = abs(x - sheen_center)
        if dist < 140:
            alpha = int(55 * math.cos((dist / 140.0) * (math.pi / 2)))
            s_draw.line([(x - height, height), (x, 0)], fill=(255, 255, 255, alpha), width=4)
    card_img = Image.alpha_composite(card_img, shine)
    draw = ImageDraw.Draw(card_img)

    # Bottom Information Bar
    # Left: TradeIt Verification Badge with clean vector check
    draw.rounded_rectangle([45, height - 70, 300, height - 28], radius=8, fill=(18, 38, 30, 220), outline=(0, 255, 120), width=1)
    draw_vector_icon(draw, "check", 66, height - 49, size=9)
    font_tiny_bold = _get_font("sans_bold", 18)
    draw.text((85, height - 59), "TradeIt Bot Verified", font=font_tiny_bold, fill=(0, 255, 120))

    # Right: Instant Price Tag Pill
    price_box_w = 260
    price_box_x = width - price_box_w - 45
    draw.rounded_rectangle([price_box_x, height - 74, width - 45, height - 24], radius=12, fill=(28, 22, 10, 240), outline=(255, 215, 0), width=2)
    font_price = _get_font("gaming_impact", 32)
    draw.text((price_box_x + 18, height - 66), price_usd, font=font_price, fill=(255, 215, 0))

    # Rarity Glow Border
    corner_radius = 28
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=corner_radius, outline=(*rarity_col, 160), width=3)
    draw.line([(0, height - 6), (width, height - 6)], fill=(*rarity_col, 240), width=6)

    # Soft Drop Shadow
    shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rounded_rectangle([pad + 12, pad + 24, pad + width + 12, pad + height + 24], radius=corner_radius + 4, fill=(0, 0, 0, 160))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=28))
    canvas.paste(shadow, (0, 0), shadow)

    canvas.paste(card_img, (pad, pad), card_img)
    if tilt_angle != 0.0:
        canvas = canvas.rotate(tilt_angle, resample=Image.BICUBIC, expand=True)

    return canvas


# ==============================================================================
# 6. STEAM VS TRADEIT BATTLE COMPARISON CARD
# ==============================================================================
def create_steam_vs_tradeit_comparison(
    width: int = 860,
    height: int = 560,
    left_title: str = "STEAM MARKET",
    right_title: str = "TRADEIT.GG",
    left_fee: str = "-15% VALVE TAX",
    right_perk: str = "INSTANT 0s BOT SWAP",
    bonus_code: str = "CODE: MESTO300",
    tilt_angle: float = 0.0,
    sheen_offset: float = 0.5,
) -> Image.Image:
    """Renders a high-energy split comparison card: Steam Market (-15% tax) vs TradeIt (+300% bonus & instant swap)."""
    pad = 80
    canvas_w = width + pad * 2
    canvas_h = height + pad * 2
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    card_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card_img)

    half_w = width // 2
    corner_radius = 28

    # 1. Left Half: Steam Market (Crimson/Red Trap Theme)
    for x in range(half_w):
        factor = x / half_w
        r = int(38 * (1 - factor * 0.4))
        g = int(14 * (1 - factor * 0.4))
        b = int(18 * (1 - factor * 0.4))
        draw.line([(x, 0), (x, height)], fill=(r, g, b, 255))

    # 2. Right Half: TradeIt.gg (Cyber Emerald/Gold Profit Theme)
    for x in range(half_w, width):
        factor = (x - half_w) / half_w
        r = int(14 + factor * 8)
        g = int(36 + factor * 14)
        b = int(26 + factor * 8)
        draw.line([(x, 0), (x, height)], fill=(r, g, b, 255))

    font_impact_title = _get_font("gaming_impact", 36)
    font_bold = _get_font("sans_bold", 22)
    font_impact_banner = _get_font("gaming_impact", 30)

    # Left Column Content (Steam)
    draw.text((45, 36), left_title, font=font_impact_title, fill=(245, 75, 90))
    # Big Red Tax Pill with vector cross
    draw.rounded_rectangle([45, 90, half_w - 35, 148], radius=12, fill=(180, 25, 45), outline=(245, 75, 90), width=2)
    draw_vector_icon(draw, "cross", 72, 119, size=14)
    clean_fee = left_fee.replace("❌", "").replace("[X]", "").strip()
    draw.text((98, 102), clean_fee, font=font_impact_banner, fill=(255, 255, 255))

    left_points = [
        "7-Day Trade Lock Hold",
        "Wallet Locked (No Cashout)",
        "15% Lost on Every Sale",
        "Exposed to API Phishing Scams",
    ]
    cur_y = 180
    for pt in left_points:
        draw_vector_icon(draw, "cross", 60, cur_y + 12, size=10)
        draw.text((80, cur_y), pt, font=font_bold, fill=(235, 150, 155))
        cur_y += 58

    # Right Column Content (TradeIt.gg)
    draw.text((half_w + 35, 36), right_title, font=font_impact_title, fill=(0, 255, 140))
    # Big Emerald Instant Pill with vector bolt
    draw.rounded_rectangle([half_w + 35, 90, width - 45, 148], radius=12, fill=(12, 140, 75), outline=(0, 255, 140), width=2)
    draw_vector_icon(draw, "bolt", half_w + 64, 119, size=14)
    clean_perk = right_perk.replace("⚡", "").strip()
    draw.text((half_w + 88, 102), clean_perk, font=font_impact_banner, fill=(255, 255, 255))

    right_points = [
        ("Instant 0s Automated Swap", "check", (120, 255, 180)),
        ("Instant Cash & Crypto Payouts", "check", (120, 255, 180)),
        (f"{bonus_code}: +300% Bonus", "gift", (255, 225, 60)),
        ("100% Anti-Scam Bot Security", "check", (120, 255, 180)),
    ]
    cur_y = 180
    for pt_text, icon, col in right_points:
        draw_vector_icon(draw, icon, half_w + 50, cur_y + 12, size=10)
        draw.text((half_w + 72, cur_y), pt_text, font=font_bold, fill=col)
        cur_y += 58

    # Center Divider Line
    draw.line([(half_w, 20), (half_w, height - 20)], fill=(60, 65, 80), width=3)

    # Floating Center "VS" Badge
    vs_cx, vs_cy = half_w, height // 2
    vs_r = 44
    draw.ellipse([vs_cx - vs_r, vs_cy - vs_r, vs_cx + vs_r, vs_cy + vs_r], fill=(24, 20, 12), outline=(255, 200, 30), width=3)
    font_vs = _get_font("gaming_impact", 38)
    draw.text((vs_cx - 22, vs_cy - 24), "VS", font=font_vs, fill=(255, 215, 0))

    # Specular sheen sweep
    shine = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shine)
    sheen_center = int((width + height) * sheen_offset)
    for x in range(sheen_center - 130, sheen_center + 130, 4):
        dist = abs(x - sheen_center)
        if dist < 130:
            alpha = int(45 * math.cos((dist / 130.0) * (math.pi / 2)))
            s_draw.line([(x - height, height), (x, 0)], fill=(255, 255, 255, alpha), width=4)
    card_img = Image.alpha_composite(card_img, shine)
    draw = ImageDraw.Draw(card_img)

    # Outer border: Half red, half green
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=corner_radius, outline=(85, 95, 120), width=2)
    draw.rounded_rectangle([half_w - 4, 0, width - 1, height - 1], radius=corner_radius, outline=(0, 255, 140, 120), width=3)

    # Soft Drop Shadow
    shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rounded_rectangle([pad + 12, pad + 24, pad + width + 12, pad + height + 24], radius=corner_radius + 4, fill=(0, 0, 0, 160))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=28))
    canvas.paste(shadow, (0, 0), shadow)

    canvas.paste(card_img, (pad, pad), card_img)
    if tilt_angle != 0.0:
        canvas = canvas.rotate(tilt_angle, resample=Image.BICUBIC, expand=True)

    return canvas


# ==============================================================================
# 7. VIP PROMOCODE VOUCHER CARD (MESTO300)
# ==============================================================================
def create_promocode_voucher_card(
    width: int = 820,
    height: int = 520,
    promocode: str = "MESTO300",
    bonus_text: str = "+300% BONUS",
    free_balance: str = "$5.00 FREE BALANCE",
    platform: str = "TradeIt.gg",
    tilt_angle: float = -3.0,
    sheen_offset: float = 0.5,
) -> Image.Image:
    """Renders a glowing VIP ticket voucher for Promocode MESTO300 with +300% Bonus."""
    pad = 80
    canvas_w = width + pad * 2
    canvas_h = height + pad * 2
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    card_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card_img)

    # Golden Obsidian Gradient
    for y in range(height):
        factor = y / height
        r = int(32 * (1 - factor) + 14 * factor)
        g = int(26 * (1 - factor) + 14 * factor)
        b = int(12 * (1 - factor) + 20 * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    corner_radius = 26

    # Top VIP Header Banner with clean vector stars
    draw.rounded_rectangle([width // 2 - 250, 24, width // 2 + 250, 68], radius=10, fill=(45, 34, 12, 220), outline=(255, 200, 30), width=2)
    draw_vector_icon(draw, "star", width // 2 - 225, 46, size=11)
    font_gold_badge = _get_font("gaming_impact", 26)
    draw.text((width // 2 - 200, 30), "OFFICIAL VIP SPONSOR VOUCHER", font=font_gold_badge, fill=(255, 215, 40))
    draw_vector_icon(draw, "star", width // 2 + 225, 46, size=11)

    font_bold_small = _get_font("sans_bold", 20)
    draw.text((width // 2 - 165, 80), f"{platform.upper()} EXCLUSIVE COMMUNITY REWARD", font=font_bold_small, fill=(195, 185, 160))

    # Big Glowing Promocode Container Box
    box_x = 75
    box_y = 118
    box_w = width - 150
    box_h = 175
    draw.rounded_rectangle([box_x, box_y, box_x + box_w, box_y + box_h], radius=16, fill=(18, 16, 12, 250), outline=(255, 195, 20), width=3)

    font_code_label = _get_font("sans_bold", 22)
    draw.text((box_x + 30, box_y + 18), "USE PROMO CODE AT CHECKOUT:", font=font_code_label, fill=(215, 185, 110))

    # Huge Promocode Typography (MESTO300) in glowing gold
    font_code = _get_font("gaming_impact", 86)
    code_text = promocode.upper()

    # Drop glow behind code
    draw.text((box_x + 34, box_y + 58), code_text, font=font_code, fill=(255, 150, 0, 160))
    draw.text((box_x + 30, box_y + 54), code_text, font=font_code, fill=(255, 225, 50))

    # Active Verified Pill on right side of code box with vector check
    st_pill_x = box_x + box_w - 235
    st_pill_y = box_y + 68
    draw.rounded_rectangle([st_pill_x, st_pill_y, box_x + box_w - 25, st_pill_y + 44], radius=10, fill=(12, 45, 24), outline=(0, 255, 120), width=2)
    draw_vector_icon(draw, "check", st_pill_x + 22, st_pill_y + 22, size=9)
    font_active = _get_font("sans_bold", 18)
    draw.text((st_pill_x + 38, st_pill_y + 11), "ACTIVE & TESTED", font=font_active, fill=(0, 255, 120))

    # Two Reward Benefit Badges
    badge_y = 315
    badge_w = (width - 170) // 2
    # Perk 1: +300% Bonus with vector gift icon
    draw.rounded_rectangle([75, badge_y, 75 + badge_w, badge_y + 85], radius=12, fill=(20, 36, 24), outline=(0, 255, 140), width=2)
    draw_vector_icon(draw, "gift", 102, badge_y + 28, size=14)
    font_badge_title = _get_font("gaming_impact", 32)
    clean_bonus = bonus_text.replace("🎁", "").strip()
    draw.text((126, badge_y + 12), clean_bonus, font=font_badge_title, fill=(0, 255, 140))
    draw.text((95, badge_y + 52), "Applied on Instant Skin Trades", font=font_bold_small, fill=(160, 220, 180))

    # Perk 2: Free Balance with vector bolt
    draw.rounded_rectangle([width - 75 - badge_w, badge_y, width - 75, badge_y + 85], radius=12, fill=(35, 28, 12), outline=(255, 215, 0), width=2)
    draw_vector_icon(draw, "bolt", width - 50 - badge_w + 14, badge_y + 28, size=14)
    clean_bal = free_balance.replace("💵", "").strip()
    draw.text((width - 50 - badge_w + 36, badge_y + 12), clean_bal, font=font_badge_title, fill=(255, 215, 0))
    draw.text((width - 55 - badge_w, badge_y + 52), "Claim Free Skins Instantly", font=font_bold_small, fill=(225, 205, 140))

    # Bottom CTA Banner
    draw.rounded_rectangle([75, height - 85, width - 75, height - 28], radius=12, fill=(14, 28, 38), outline=(0, 210, 255), width=2)
    font_cta = _get_font("gaming_impact", 28)
    cta_str = f"ENTER CODE ON {platform.upper()} TO CLAIM FREE SKINS >"
    draw.text((105, height - 76), cta_str, font=font_cta, fill=(0, 230, 255))

    # Outer Gold Border & Dashed Inset
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=corner_radius, outline=(255, 205, 40), width=3)
    draw.rounded_rectangle([8, 8, width - 9, height - 9], radius=corner_radius - 4, outline=(255, 180, 20, 80), width=1)

    # Specular sweep light sweep
    shine = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shine)
    sheen_center = int((width + height) * sheen_offset)
    for x in range(sheen_center - 140, sheen_center + 140, 4):
        dist = abs(x - sheen_center)
        if dist < 140:
            alpha = int(45 * math.cos((dist / 140.0) * (math.pi / 2)))
            s_draw.line([(x - height, height), (x, 0)], fill=(255, 255, 255, alpha), width=4)
    card_img = Image.alpha_composite(card_img, shine)
    draw = ImageDraw.Draw(card_img)

    # Soft Drop Shadow
    shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rounded_rectangle([pad + 12, pad + 24, pad + width + 12, pad + height + 24], radius=corner_radius + 4, fill=(0, 0, 0, 160))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=28))
    canvas.paste(shadow, (0, 0), shadow)

    canvas.paste(card_img, (pad, pad), card_img)
    if tilt_angle != 0.0:
        canvas = canvas.rotate(tilt_angle, resample=Image.BICUBIC, expand=True)

    return canvas


if __name__ == "__main__":
    print("Generating sample 2.5D visual components...")
    bg = create_dark_grid_background()
    bg.save(ASSETS_CACHE_DIR / "sample_bg.png")

    card = create_floating_card(card_type="emerald")
    card.save(ASSETS_CACHE_DIR / "sample_card.png")

    newspaper = create_newspaper_clipping()
    newspaper.save(ASSETS_CACHE_DIR / "sample_newspaper.png")

    phone = create_smartphone_app_mockup()
    phone.save(ASSETS_CACHE_DIR / "sample_phone.png")

    caption = render_kinetic_caption("The FBI will come for you", position="top", highlight_color=(75, 110, 245), active_word="FBI")
    caption.save(ASSETS_CACHE_DIR / "sample_caption.png")

    print("All sample visual assets generated successfully in assets/cache!")
