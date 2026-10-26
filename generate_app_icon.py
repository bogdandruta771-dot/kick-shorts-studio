import math
import os
from PIL import Image, ImageDraw, ImageFilter

def create_omnistudio_icon():
    # Render at high resolution (1024x1024) for supersampled anti-aliased perfection
    size = 1024
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    
    # Base squircle
    radius = 220
    pad = 48
    
    # Create smooth rounded rectangle mask
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=radius, fill=255)
    
    # Background gradient: deep space cyber navy to midnight violet
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg)
    for y in range(pad, size - pad):
        t = (y - pad) / (size - 2 * pad)
        # Gradient from #090D16 -> #161233 -> #0F172A
        r = int(9 * (1 - t) + 20 * t)
        g = int(13 * (1 - t) + 22 * t)
        b = int(24 * (1 - t) + 52 * t)
        bg_draw.line([(pad, y), (size - pad, y)], fill=(r, g, b, 255))
        
    # Apply squircle mask to background
    bg.putalpha(mask)
    
    # Outer glow / border layer
    border_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(border_img)
    b_draw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=radius, outline=(120, 80, 255, 180), width=12)
    b_draw.rounded_rectangle([pad + 6, pad + 6, size - pad - 6, size - pad - 6], radius=radius - 6, outline=(6, 182, 212, 140), width=6)
    
    # Top-down ambient highlight on squircle rim
    rim_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rim_draw = ImageDraw.Draw(rim_img)
    rim_draw.arc([pad + 4, pad + 4, size - pad - 4, size - pad - 4], start=190, end=350, fill=(255, 255, 255, 120), width=8)
    
    # Combine background and borders
    comp = Image.alpha_composite(img, bg)
    comp = Image.alpha_composite(comp, border_img)
    comp = Image.alpha_composite(comp, rim_img)
    
    # Draw Central Icon: Layered 3D Motion Play Ribbon + Lightning Bolt
    # Center is (512, 512)
    cx, cy = 512, 512
    
    # Layer 1: Background ambient neon glow
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    g_draw.ellipse([cx - 280, cy - 280, cx + 280, cy + 280], fill=(139, 92, 246, 75))
    g_draw.ellipse([cx - 200, cy - 200, cx + 200, cy + 200], fill=(6, 182, 212, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(65))
    comp = Image.alpha_composite(comp, glow)
    
    # Layer 2: 3D Isometric Play Shape (Back Prism - Magenta/Purple)
    prism_back = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pb_draw = ImageDraw.Draw(prism_back)
    # Triangular play polygon shifted slightly down-right
    p_back_coords = [
        (cx - 150 + 25, cy - 210 + 25),
        (cx + 210 + 25, cy + 25),
        (cx - 150 + 25, cy + 210 + 25)
    ]
    pb_draw.polygon(p_back_coords, fill=(168, 85, 247, 230))
    prism_back = prism_back.filter(ImageFilter.GaussianBlur(12))
    comp = Image.alpha_composite(comp, prism_back)
    
    # Layer 3: Main Glass/Metallic Play Badge (Cyan -> Indigo gradient polygon)
    play_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pl_draw = ImageDraw.Draw(play_layer)
    
    p1 = (cx - 150, cy - 210)
    p2 = (cx + 210, cy)
    p3 = (cx - 150, cy + 210)
    
    # Draw smooth triangle
    pl_draw.polygon([p1, p2, p3], fill=(30, 27, 75, 245))
    
    # Draw internal gradient facets on the play button
    facet1 = [p1, (cx + 30, cy - 70), (cx - 150, cy)]
    facet2 = [(cx - 150, cy), (cx + 30, cy - 70), p2]
    facet3 = [(cx - 150, cy), p2, (cx + 30, cy + 70)]
    facet4 = [(cx - 150, cy), (cx + 30, cy + 70), p3]
    
    pl_draw.polygon(facet1, fill=(59, 130, 246, 235))   # Electric Blue
    pl_draw.polygon(facet2, fill=(6, 182, 212, 245))    # Cyan
    pl_draw.polygon(facet3, fill=(139, 92, 246, 240))   # Violet
    pl_draw.polygon(facet4, fill=(236, 72, 153, 230))   # Magenta
    
    # Stroke outline
    pl_draw.line([p1, p2, p3, p1], fill=(255, 255, 255, 200), width=8)
    comp = Image.alpha_composite(comp, play_layer)
    
    # Layer 4: Electric Lightning Bolt across center (Golden/White with glowing shadow)
    bolt_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bl_draw = ImageDraw.Draw(bolt_layer)
    
    # Stylized dynamic lightning bolt
    # Sharp, energetic silhouette
    bolt_pts = [
        (cx - 30, cy - 230),   # Top point
        (cx + 60, cy - 230),
        (cx - 20, cy - 30),
        (cx + 80, cy - 30),
        (cx - 70, cy + 230),   # Bottom point
        (cx - 20, cy + 40),
        (cx - 95, cy + 40),
    ]
    
    # Bolt glow
    bolt_glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg_d = ImageDraw.Draw(bolt_glow)
    bg_d.polygon(bolt_pts, fill=(250, 204, 21, 220))
    bolt_glow = bolt_glow.filter(ImageFilter.GaussianBlur(18))
    comp = Image.alpha_composite(comp, bolt_glow)
    
    # Solid bolt with bright core
    bl_draw.polygon(bolt_pts, fill=(254, 240, 138, 255))
    
    # Highlight inside bolt
    bolt_hi_pts = [
        (cx - 15, cy - 210),
        (cx + 40, cy - 210),
        (cx - 25, cy - 20),
        (cx + 50, cy - 20),
        (cx - 50, cy + 200),
        (cx - 20, cy + 30),
        (cx - 80, cy + 30),
    ]
    bl_draw.polygon(bolt_hi_pts, fill=(255, 255, 255, 240))
    comp = Image.alpha_composite(comp, bolt_layer)
    
    # Decorative elements: Film sprocket / AI sparkles
    sparkle = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sp_draw = ImageDraw.Draw(sparkle)
    
    # Top right 4-point star
    sx, sy = cx + 250, cy - 250
    sp_pts = [
        (sx, sy - 35), (sx + 8, sy - 8), (sx + 35, sy), (sx + 8, sy + 8),
        (sx, sy + 35), (sx - 8, sy + 8), (sx - 35, sy), (sx - 8, sy - 8)
    ]
    sp_draw.polygon(sp_pts, fill=(255, 255, 255, 220))
    
    # Bottom left small star
    sx2, sy2 = cx - 260, cy + 220
    sp_pts2 = [
        (sx2, sy2 - 20), (sx2 + 5, sy2 - 5), (sx2 + 20, sy2), (sx2 + 5, sy2 + 5),
        (sx2, sy2 + 20), (sx2 - 5, sy2 + 5), (sx2 - 20, sy2), (sx2 - 5, sy2 - 5)
    ]
    sp_draw.polygon(sp_pts2, fill=(6, 182, 212, 220))
    
    comp = Image.alpha_composite(comp, sparkle)
    
    # Downsample with Lanczos to final 512x512
    final_512 = comp.resize((512, 512), Image.Resampling.LANCZOS)
    
    # Ensure assets directory exists
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    png_path = os.path.join(assets_dir, "icon.png")
    ico_path = os.path.join(assets_dir, "icon.ico")
    
    # Save high-res PNG
    final_512.save(png_path, format="PNG")
    print(f"Saved PNG icon: {png_path} (512x512)")
    
    # Save multi-size ICO: 256, 128, 64, 48, 32, 16
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    final_512.save(ico_path, format="ICO", sizes=sizes)
    print(f"Saved multi-resolution ICO: {ico_path} {sizes}")
    
    # Also save in root directory for convenience
    root_ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    root_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
    final_512.save(root_ico, format="ICO", sizes=sizes)
    final_512.save(root_png, format="PNG")
    print("Export complete!")

if __name__ == "__main__":
    create_omnistudio_icon()
