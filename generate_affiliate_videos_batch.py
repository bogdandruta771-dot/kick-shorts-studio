"""
OmniStudio 2.5D Motion Explainer - Affiliate Batch Generator
Generates 12 High-Retention 1080x1920 Viral Shorts for Tradeit.gg Promo Code 'mesto300'
Each video features:
- Unique psychological hook (Glitch, Valve Tax, Case Scam, $0 to Knife, Anti-Scam, etc.)
- Multi-directional animations (Zoom/Pop hook, Left glide, Top slam, Right glide, Bottom rise)
- High-res cropped visual cards from the actual Tradeit affiliate dashboard
- Neural Edge-TTS voiceovers (GuyNeural & ChristopherNeural) with fast pacing
- Synchronized sound effects (heavy_impact, case_unlock, cash_register, whoosh, pop)
- Music track disabled / muted so user can add custom music tracks as requested
- Automatic registration in SQLite history for OmniStudio UI
"""
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

# Reconfigure stdout/stderr for clean utf-8 on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import OUTPUT_DIR
from core.motion_explainer.motion_renderer import render_motion_explainer_short
from core.clip_history import record_clipped_short

ASSETS_DIR = PROJECT_ROOT / "assets" / "tradeit"
CROP_COUPON = str(ASSETS_DIR / "crop_coupon_mesto300.png")
CROP_BONUS = str(ASSETS_DIR / "crop_bonus_5dollar.png")
CROP_TRUSTPILOT = str(ASSETS_DIR / "crop_trustpilot_tradeit.png")
CROP_HOW_IT_WORKS = str(ASSETS_DIR / "crop_how_it_works.png")
CROP_WEAPONS = str(ASSETS_DIR / "weapons_crop.png")
CROP_DASHBOARD = str(ASSETS_DIR / "affiliate_dashboard.png")

# ==============================================================================
# 12 DISTINCT AFFILIATE VIDEO SCRIPTS FOR CODE 'mesto300'
# ==============================================================================
AFFILIATE_VIDEOS: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # 1. The $5 Free Balance Glitch (Curiosity & Glitch Hook)
    # -------------------------------------------------------------------------
    {
        "id": "affiliate_01_glitch",
        "name": "The $5 Free Balance Glitch",
        "theme": "tradeit",
        "promocode": "MESTO300",
        "category": "Gaming / CS2",
        "voice_id": "en-US-GuyNeural",
        "speech_rate": "+18%",
        "include_music": False,
        "include_sfx": True,
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "skin",
                "skin_name": "★ Karambit | Doppler",
                "price_usd": "$1,850.00 USD",
                "rarity": "covert",
                "direction": "zoom",
                "caption": "The $5 Free Balance Glitch",
                "caption_highlight": "$5 Free",
                "highlight_color": [0, 255, 65],
                "voice_text": "Did Valve really just allow a free five dollar balance trick?",
                "sfx": "heavy_impact",
                "duration": 3.0,
            },
            {
                "scene_num": 2,
                "visual_type": "comparison",
                "left_title": "CASE OPENING",
                "right_title": "TRADEIT.GG",
                "left_fee": "99.7% LOSS RATE",
                "right_perk": "FREE $5.00 BALANCE",
                "bonus_code": "CODE: MESTO300",
                "direction": "left",
                "caption": "Stop wasting cash on cases",
                "caption_highlight": "wasting cash",
                "highlight_color": [255, 42, 85],
                "voice_text": "Most players spend real cash on cases and lose ninety-nine percent of their money.",
                "sfx": "whoosh",
                "duration": 3.8,
            },
            {
                "scene_num": 3,
                "visual_type": "crop",
                "custom_image_path": CROP_BONUS,
                "direction": "top",
                "caption": "Get $5 Free On Your First Trade",
                "caption_highlight": "$5 Free",
                "highlight_color": [0, 255, 65],
                "voice_text": "Tradeit literally gives you a five dollar bonus on your very first trade.",
                "sfx": "case_unlock",
                "duration": 3.6,
            },
            {
                "scene_num": 4,
                "visual_type": "crop",
                "custom_image_path": CROP_COUPON,
                "direction": "right",
                "caption": "Enter Coupon Code mesto300",
                "caption_highlight": "mesto300",
                "highlight_color": [255, 215, 0],
                "voice_text": "All you have to do is type coupon code mesto 300.",
                "sfx": "cash_register",
                "duration": 3.2,
            },
            {
                "scene_num": 5,
                "visual_type": "voucher",
                "promocode": "MESTO300",
                "bonus_text": "+35% TOPUP BONUS",
                "free_balance": "$5.00 FREE BALANCE",
                "direction": "bottom",
                "caption": "Claim it at tradeit.gg right now",
                "caption_highlight": "tradeit.gg",
                "highlight_color": [56, 182, 255],
                "voice_text": "Go to tradeit.gg with code mesto 300 before this gets patched.",
                "sfx": "chime",
                "duration": 3.5,
            },
        ],
    },

    # -------------------------------------------------------------------------
    # 2. Steam 15% Tax Ripoff (Financial Pain Point Hook)
    # -------------------------------------------------------------------------
    {
        "id": "affiliate_02_steam_tax",
        "name": "The Steam 15% Tax Ripoff",
        "theme": "tradeit",
        "promocode": "MESTO300",
        "category": "Gaming / CS2",
        "voice_id": "en-US-ChristopherNeural",
        "speech_rate": "+16%",
        "include_music": False,
        "include_sfx": True,
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "skin",
                "skin_name": "AWP | Dragon Lore",
                "price_usd": "$9,400.00 USD",
                "rarity": "covert",
                "direction": "zoom",
                "caption": "Stop Selling Skins On Steam!",
                "caption_highlight": "Stop Selling",
                "highlight_color": [255, 42, 85],
                "voice_text": "Stop selling your CS2 skins directly on Steam!",
                "sfx": "heavy_impact",
                "duration": 2.8,
            },
            {
                "scene_num": 2,
                "visual_type": "comparison",
                "left_title": "STEAM MARKET",
                "right_title": "TRADEIT.GG",
                "left_fee": "-15% VALVE TAX",
                "right_perk": "0% SELLER FEE",
                "bonus_code": "CODE: MESTO300",
                "direction": "top",
                "caption": "Valve takes 15% of your money",
                "caption_highlight": "15% of your money",
                "highlight_color": [255, 42, 85],
                "voice_text": "Valve takes a massive fifteen percent cut from every single sale you make.",
                "sfx": "heavy_impact",
                "duration": 3.8,
            },
            {
                "scene_num": 3,
                "visual_type": "crop",
                "custom_image_path": CROP_WEAPONS,
                "direction": "left",
                "caption": "Tradeit swaps skins instantly",
                "caption_highlight": "swaps skins instantly",
                "highlight_color": [56, 182, 255],
                "voice_text": "On Tradeit, automated bots swap your skins in zero seconds with zero seller tax.",
                "sfx": "whoosh",
                "duration": 4.0,
            },
            {
                "scene_num": 4,
                "visual_type": "crop",
                "custom_image_path": CROP_BONUS,
                "direction": "right",
                "caption": "+35% Deposit Match Bonus",
                "caption_highlight": "+35% Deposit",
                "highlight_color": [0, 255, 65],
                "voice_text": "Plus you get an extra thirty-five percent deposit bonus and five dollars free balance.",
                "sfx": "cash_register",
                "duration": 3.8,
            },
            {
                "scene_num": 5,
                "visual_type": "crop",
                "custom_image_path": CROP_COUPON,
                "direction": "bottom",
                "caption": "Use Code mesto300 on Tradeit.gg",
                "caption_highlight": "mesto300",
                "highlight_color": [255, 215, 0],
                "voice_text": "Enter promo code mesto 300 on tradeit.gg and stop losing your money to Steam.",
                "sfx": "chime",
                "duration": 3.8,
            },
        ],
    },

    # -------------------------------------------------------------------------
    # 3. Case Openings Are a Scam (Statistical Reality Hook)
    # -------------------------------------------------------------------------
    {
        "id": "affiliate_03_case_scam",
        "name": "Case Openings Are a Mathematical Scam",
        "theme": "tradeit",
        "promocode": "MESTO300",
        "category": "Gaming / CS2",
        "voice_id": "en-US-GuyNeural",
        "speech_rate": "+18%",
        "include_music": False,
        "include_sfx": True,
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "newspaper",
                "headline": "CS2 Case Odds Revealed: 99.74% Of Openings Result In Loss",
                "source": "Esports Economy Report",
                "author": "By Skin Analytics",
                "caption": "Case Openings Are A Scam",
                "caption_highlight": "Scam",
                "highlight_color": [255, 42, 85],
                "direction": "zoom",
                "voice_text": "Opening CS2 cases is mathematically guaranteed to lose you money.",
                "sfx": "heavy_impact",
                "duration": 3.2,
            },
            {
                "scene_num": 2,
                "visual_type": "skin",
                "skin_name": "★ Butterfly Knife | Fade",
                "price_usd": "$2,600.00 USD",
                "rarity": "covert",
                "direction": "left",
                "caption": "Trade direct for your dream knife",
                "caption_highlight": "dream knife",
                "highlight_color": [56, 182, 255],
                "voice_text": "Instead of burning hundreds on keys and getting blue trash, trade directly for a knife.",
                "sfx": "whoosh",
                "duration": 3.9,
            },
            {
                "scene_num": 3,
                "visual_type": "crop",
                "custom_image_path": CROP_BONUS,
                "direction": "top",
                "caption": "$5.00 Free Balance On Tradeit",
                "caption_highlight": "$5.00 Free",
                "highlight_color": [0, 255, 65],
                "voice_text": "Tradeit gives you five dollars free balance on your first trade.",
                "sfx": "case_unlock",
                "duration": 3.4,
            },
            {
                "scene_num": 4,
                "visual_type": "crop",
                "custom_image_path": CROP_COUPON,
                "direction": "right",
                "caption": "Use Coupon Code mesto300",
                "caption_highlight": "mesto300",
                "highlight_color": [255, 215, 0],
                "voice_text": "Just enter coupon code mesto 300 to activate the boost.",
                "sfx": "cash_register",
                "duration": 3.2,
            },
            {
                "scene_num": 5,
                "visual_type": "voucher",
                "promocode": "MESTO300",
                "bonus_text": "+35% TOPUP BONUS",
                "free_balance": "$5.00 FREE BALANCE",
                "direction": "bottom",
                "caption": "Upgrade today at tradeit.gg",
                "caption_highlight": "tradeit.gg",
                "highlight_color": [0, 255, 65],
                "voice_text": "Head to tradeit.gg right now with code mesto 300 and guarantee your knife.",
                "sfx": "chime",
                "duration": 3.6,
            },
        ],
    },

    # -------------------------------------------------------------------------
    # 4. The $0 to Knife Challenge (Underdog Progression Hook)
    # -------------------------------------------------------------------------
    {
        "id": "affiliate_04_zero_to_knife",
        "name": "The $0 to Knife Blueprint",
        "theme": "tradeit",
        "promocode": "MESTO300",
        "category": "Gaming / CS2",
        "voice_id": "en-US-GuyNeural",
        "speech_rate": "+18%",
        "include_music": False,
        "include_sfx": True,
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "skin",
                "skin_name": "★ M9 Bayonet | Slaughter",
                "price_usd": "$1,450.00 USD",
                "rarity": "covert",
                "direction": "zoom",
                "caption": "How To Get A Knife From $0",
                "caption_highlight": "$0",
                "highlight_color": [0, 255, 65],
                "voice_text": "Here is how to get your very first CS2 knife starting from zero dollars.",
                "sfx": "heavy_impact",
                "duration": 3.2,
            },
            {
                "scene_num": 2,
                "visual_type": "crop",
                "custom_image_path": CROP_HOW_IT_WORKS,
                "direction": "left",
                "caption": "Step 1: Collect Weekly Drop Cases",
                "caption_highlight": "Weekly Drop",
                "highlight_color": [56, 182, 255],
                "voice_text": "Step one. Collect your weekly case drops just from playing competitive games.",
                "sfx": "whoosh",
                "duration": 3.6,
            },
            {
                "scene_num": 3,
                "visual_type": "crop",
                "custom_image_path": CROP_BONUS,
                "direction": "top",
                "caption": "Step 2: Claim Free $5.00 Balance",
                "caption_highlight": "$5.00 Balance",
                "highlight_color": [0, 255, 65],
                "voice_text": "Step two. Deposit them on Tradeit to unlock your free five dollar trade bonus.",
                "sfx": "case_unlock",
                "duration": 3.8,
            },
            {
                "scene_num": 4,
                "visual_type": "crop",
                "custom_image_path": CROP_COUPON,
                "direction": "right",
                "caption": "Step 3: Enter Code mesto300",
                "caption_highlight": "mesto300",
                "highlight_color": [255, 215, 0],
                "voice_text": "Step three. Apply code mesto 300 to get a thirty-five percent bonus on your balance.",
                "sfx": "cash_register",
                "duration": 3.6,
            },
            {
                "scene_num": 5,
                "visual_type": "voucher",
                "promocode": "MESTO300",
                "bonus_text": "+35% TOPUP BONUS",
                "free_balance": "$5.00 FREE BALANCE",
                "direction": "bottom",
                "caption": "Start Trading Up At Tradeit.gg",
                "caption_highlight": "Tradeit.gg",
                "highlight_color": [0, 255, 65],
                "voice_text": "Start your knife journey today at tradeit.gg with code mesto 300.",
                "sfx": "chime",
                "duration": 3.5,
            },
        ],
    },

    # -------------------------------------------------------------------------
    # 5. Don't Fall for API Scams (Security / Trust Hook)
    # -------------------------------------------------------------------------
    {
        "id": "affiliate_05_anti_scam",
        "name": "Don't Fall For Steam API Scams",
        "theme": "tradeit",
        "promocode": "MESTO300",
        "category": "Gaming / CS2",
        "voice_id": "en-US-ChristopherNeural",
        "speech_rate": "+16%",
        "include_music": False,
        "include_sfx": True,
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "newspaper",
                "headline": "Steam API Scammers Drain Over $10M In CS2 Inventories This Year",
                "source": "Cybersecurity Watch",
                "author": "By Threat Intelligence",
                "caption": "Never Trust Trade DMs!",
                "caption_highlight": "Never Trust",
                "highlight_color": [255, 42, 85],
                "direction": "zoom",
                "voice_text": "If someone messages you on Discord or Steam offering to trade skins, block them immediately.",
                "sfx": "heavy_impact",
                "duration": 4.2,
            },
            {
                "scene_num": 2,
                "visual_type": "crop",
                "custom_image_path": CROP_TRUSTPILOT,
                "direction": "top",
                "caption": "Tradeit: 9.5 Rating On Trustpilot",
                "caption_highlight": "9.5 Rating",
                "highlight_color": [0, 255, 65],
                "voice_text": "Tradeit is officially rated 9.5 Excellent on Trustpilot across more than five thousand verified reviews.",
                "sfx": "case_unlock",
                "duration": 4.2,
            },
            {
                "scene_num": 3,
                "visual_type": "crop",
                "custom_image_path": CROP_BONUS,
                "direction": "left",
                "caption": "Guaranteed Bot Security + $5 Free",
                "caption_highlight": "Guaranteed Security",
                "highlight_color": [56, 182, 255],
                "voice_text": "Every trade is executed by verified automated bots, plus you get five dollars free on your first swap.",
                "sfx": "whoosh",
                "duration": 4.2,
            },
            {
                "scene_num": 4,
                "visual_type": "crop",
                "custom_image_path": CROP_COUPON,
                "direction": "right",
                "caption": "Verified Promo Code mesto300",
                "caption_highlight": "mesto300",
                "highlight_color": [255, 215, 0],
                "voice_text": "Enter coupon code mesto 300 to activate maximum protection and your bonus.",
                "sfx": "cash_register",
                "duration": 3.6,
            },
            {
                "scene_num": 5,
                "visual_type": "voucher",
                "promocode": "MESTO300",
                "bonus_text": "+35% TOPUP BONUS",
                "free_balance": "$5.00 FREE BALANCE",
                "direction": "bottom",
                "caption": "Trade Safe Today at Tradeit.gg",
                "caption_highlight": "Tradeit.gg",
                "highlight_color": [0, 255, 65],
                "voice_text": "Protect your inventory and trade safely at tradeit.gg using code mesto 300.",
                "sfx": "chime",
                "duration": 3.8,
            },
        ],
    },

    # -------------------------------------------------------------------------
    # 6. The 35% Deposit Multiplier Hack (Math / Value Hook)
    # -------------------------------------------------------------------------
    {
        "id": "affiliate_06_multiplier_hack",
        "name": "The +35% Balance Multiplier Hack",
        "theme": "tradeit",
        "promocode": "MESTO300",
        "category": "Gaming / CS2",
        "voice_id": "en-US-GuyNeural",
        "speech_rate": "+18%",
        "include_music": False,
        "include_sfx": True,
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "crop",
                "custom_image_path": CROP_BONUS,
                "direction": "zoom",
                "caption": "+35% Free Balance Hack",
                "caption_highlight": "+35% Free",
                "highlight_color": [0, 255, 65],
                "voice_text": "This is how smart CS2 traders get thirty-five percent more balance for free.",
                "sfx": "heavy_impact",
                "duration": 3.4,
            },
            {
                "scene_num": 2,
                "visual_type": "comparison",
                "left_title": "NORMAL TOPUP",
                "right_title": "WITH MESTO300",
                "left_fee": "$100 -> $100",
                "right_perk": "$100 -> $135 + $5 FREE",
                "bonus_code": "CODE: MESTO300",
                "direction": "left",
                "caption": "$100 Becomes $140 Instantly",
                "caption_highlight": "$140 Instantly",
                "highlight_color": [255, 215, 0],
                "voice_text": "Normally one hundred dollars gets you one hundred. With code mesto 300, it turns into one hundred forty dollars.",
                "sfx": "case_unlock",
                "duration": 4.2,
            },
            {
                "scene_num": 3,
                "visual_type": "skin",
                "skin_name": "★ Skeleton Knife | Case Hardened",
                "price_usd": "$1,120.00 USD",
                "rarity": "covert",
                "direction": "top",
                "caption": "Buy knives at massive discounts",
                "caption_highlight": "massive discounts",
                "highlight_color": [56, 182, 255],
                "voice_text": "That extra forty dollars is pure free profit you can use directly toward a knife.",
                "sfx": "whoosh",
                "duration": 3.8,
            },
            {
                "scene_num": 4,
                "visual_type": "crop",
                "custom_image_path": CROP_COUPON,
                "direction": "right",
                "caption": "Enter Code mesto300 At Checkout",
                "caption_highlight": "mesto300",
                "highlight_color": [255, 215, 0],
                "voice_text": "Just type coupon code mesto 300 before topping up your balance.",
                "sfx": "cash_register",
                "duration": 3.2,
            },
            {
                "scene_num": 5,
                "visual_type": "voucher",
                "promocode": "MESTO300",
                "bonus_text": "+35% TOPUP BONUS",
                "free_balance": "$5.00 FREE BALANCE",
                "direction": "bottom",
                "caption": "Multiply your wallet at tradeit.gg",
                "caption_highlight": "tradeit.gg",
                "highlight_color": [0, 255, 65],
                "voice_text": "Multiply your wallet right now at tradeit.gg using code mesto 300.",
                "sfx": "chime",
                "duration": 3.5,
            },
        ],
    },

    # -------------------------------------------------------------------------
    # 7. The 0-Second Instant Bot Swap (Speed / Impatience Hook)
    # -------------------------------------------------------------------------
    {
        "id": "affiliate_07_instant_swap",
        "name": "The 0-Second Instant Bot Swap",
        "theme": "tradeit",
        "promocode": "MESTO300",
        "category": "Gaming / CS2",
        "voice_id": "en-US-GuyNeural",
        "speech_rate": "+18%",
        "include_music": False,
        "include_sfx": True,
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "comparison",
                "left_title": "MANUAL TRADES",
                "right_title": "TRADEIT.GG",
                "left_fee": "7 DAYS WAITING",
                "right_perk": "0 SECONDS INSTANT",
                "bonus_code": "CODE: MESTO300",
                "direction": "zoom",
                "caption": "Why Wait 7 Days To Trade?",
                "caption_highlight": "Why Wait",
                "highlight_color": [255, 42, 85],
                "voice_text": "Why are you still waiting seven whole days just to trade your CS skins?",
                "sfx": "heavy_impact",
                "duration": 3.2,
            },
            {
                "scene_num": 2,
                "visual_type": "skin",
                "skin_name": "AK-47 | Fire Serpent",
                "price_usd": "$980.00 USD",
                "rarity": "covert",
                "direction": "left",
                "caption": "Manual traders constantly cancel",
                "caption_highlight": "constantly cancel",
                "highlight_color": [255, 42, 85],
                "voice_text": "Peer to peer traders take forever, lowball your items, and cancel at the last second.",
                "sfx": "whoosh",
                "duration": 3.8,
            },
            {
                "scene_num": 3,
                "visual_type": "crop",
                "custom_image_path": CROP_WEAPONS,
                "direction": "top",
                "caption": "Tradeit bots swap in 0 seconds",
                "caption_highlight": "0 seconds",
                "highlight_color": [0, 255, 65],
                "voice_text": "Tradeit automated bots send you the exact skin you want in zero seconds flat.",
                "sfx": "case_unlock",
                "duration": 3.8,
            },
            {
                "scene_num": 4,
                "visual_type": "crop",
                "custom_image_path": CROP_BONUS,
                "direction": "right",
                "caption": "Get $5 Free On Your First Trade",
                "caption_highlight": "$5 Free",
                "highlight_color": [0, 255, 65],
                "voice_text": "Plus you get five dollars in free balance when you complete your first trade.",
                "sfx": "cash_register",
                "duration": 3.4,
            },
            {
                "scene_num": 5,
                "visual_type": "crop",
                "custom_image_path": CROP_COUPON,
                "direction": "bottom",
                "caption": "Swap now with code mesto300",
                "caption_highlight": "mesto300",
                "highlight_color": [255, 215, 0],
                "voice_text": "Head over to tradeit.gg and enter code mesto 300 to swap instantly.",
                "sfx": "chime",
                "duration": 3.6,
            },
        ],
    },

    # -------------------------------------------------------------------------
    # 8. Rust & TF2 to CS2 Cross-Game Trade (Arbitrage Hook)
    # -------------------------------------------------------------------------
    {
        "id": "affiliate_08_cross_game",
        "name": "Rust & TF2 to CS2 Cross-Game Trade",
        "theme": "tradeit",
        "promocode": "MESTO300",
        "category": "Gaming / Multi-Game",
        "voice_id": "en-US-ChristopherNeural",
        "speech_rate": "+16%",
        "include_music": False,
        "include_sfx": True,
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "skin",
                "skin_name": "★ Talon Knife | Marble Fade",
                "price_usd": "$1,380.00 USD",
                "rarity": "covert",
                "direction": "zoom",
                "caption": "Turn Rust Skins Into CS2 Knives",
                "caption_highlight": "CS2 Knives",
                "highlight_color": [0, 255, 65],
                "voice_text": "Did you know you can trade your dusty Rust and TF2 items directly for a CS2 knife?",
                "sfx": "heavy_impact",
                "duration": 4.0,
            },
            {
                "scene_num": 2,
                "visual_type": "crop",
                "custom_image_path": CROP_DASHBOARD,
                "direction": "left",
                "caption": "Cash out dead game items",
                "caption_highlight": "dead game items",
                "highlight_color": [255, 42, 85],
                "voice_text": "Millions of gamers have hundreds of dollars in dead Rust skins and TF2 hats sitting untouched.",
                "sfx": "whoosh",
                "duration": 4.2,
            },
            {
                "scene_num": 3,
                "visual_type": "crop",
                "custom_image_path": CROP_WEAPONS,
                "direction": "top",
                "caption": "Tradeit connects CS2, Rust & TF2",
                "caption_highlight": "connects CS2, Rust",
                "highlight_color": [56, 182, 255],
                "voice_text": "Tradeit lets you combine items across all games and cash them out into high-tier CS skins.",
                "sfx": "case_unlock",
                "duration": 4.0,
            },
            {
                "scene_num": 4,
                "visual_type": "crop",
                "custom_image_path": CROP_BONUS,
                "direction": "right",
                "caption": "+35% Bonus + $5 Free Balance",
                "caption_highlight": "+35% Bonus",
                "highlight_color": [0, 255, 65],
                "voice_text": "And you get a thirty-five percent deposit bonus plus five dollars free on your trade.",
                "sfx": "cash_register",
                "duration": 3.8,
            },
            {
                "scene_num": 5,
                "visual_type": "crop",
                "custom_image_path": CROP_COUPON,
                "direction": "bottom",
                "caption": "Use Code mesto300 on Tradeit.gg",
                "caption_highlight": "mesto300",
                "highlight_color": [255, 215, 0],
                "voice_text": "Revive your dead inventory today at tradeit.gg with code mesto 300.",
                "sfx": "chime",
                "duration": 3.8,
            },
        ],
    },

    # -------------------------------------------------------------------------
    # 9. Streamer Knife Rotation Secret (Insider Secret Hook)
    # -------------------------------------------------------------------------
    {
        "id": "affiliate_09_streamer_rotation",
        "name": "The Streamer Knife Rotation Secret",
        "theme": "tradeit",
        "promocode": "MESTO300",
        "category": "Gaming / CS2",
        "voice_id": "en-US-GuyNeural",
        "speech_rate": "+18%",
        "include_music": False,
        "include_sfx": True,
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "skin",
                "skin_name": "★ Karambit | Doppler Phase 2",
                "price_usd": "$2,100.00 USD",
                "rarity": "covert",
                "direction": "zoom",
                "caption": "How Streamers Switch Knives Weekly",
                "caption_highlight": "Switch Knives",
                "highlight_color": [56, 182, 255],
                "voice_text": "Ever wonder how CS streamers play with a brand new knife every single week?",
                "sfx": "heavy_impact",
                "duration": 3.4,
            },
            {
                "scene_num": 2,
                "visual_type": "skin",
                "skin_name": "★ Butterfly Knife | Marble Fade",
                "price_usd": "$2,850.00 USD",
                "rarity": "covert",
                "direction": "left",
                "caption": "They never buy them with cash",
                "caption_highlight": "never buy",
                "highlight_color": [255, 42, 85],
                "voice_text": "They don't buy them with cash. They rotate them using Tradeit automated bots.",
                "sfx": "whoosh",
                "duration": 3.6,
            },
            {
                "scene_num": 3,
                "visual_type": "crop",
                "custom_image_path": CROP_WEAPONS,
                "direction": "top",
                "caption": "Swap equal value in 0 seconds",
                "caption_highlight": "equal value",
                "highlight_color": [0, 255, 65],
                "voice_text": "You can swap your current knife for another knife at exact fair market value in seconds.",
                "sfx": "case_unlock",
                "duration": 3.8,
            },
            {
                "scene_num": 4,
                "visual_type": "crop",
                "custom_image_path": CROP_BONUS,
                "direction": "right",
                "caption": "$5.00 Free + 35% Upgrade Boost",
                "caption_highlight": "$5.00 Free",
                "highlight_color": [0, 255, 65],
                "voice_text": "Plus code mesto 300 adds a five dollar bonus and thirty-five percent deposit match.",
                "sfx": "cash_register",
                "duration": 3.6,
            },
            {
                "scene_num": 5,
                "visual_type": "crop",
                "custom_image_path": CROP_COUPON,
                "direction": "bottom",
                "caption": "Rotate your skins at tradeit.gg",
                "caption_highlight": "tradeit.gg",
                "highlight_color": [255, 215, 0],
                "voice_text": "Rotate your dream skins right now at tradeit.gg with code mesto 300.",
                "sfx": "chime",
                "duration": 3.5,
            },
        ],
    },

    # -------------------------------------------------------------------------
    # 10. The Secret Code Mesto300 (Tutorial / FOMO Hook)
    # -------------------------------------------------------------------------
    {
        "id": "affiliate_10_secret_code",
        "name": "The Secret Coupon Code Mesto300",
        "theme": "tradeit",
        "promocode": "MESTO300",
        "category": "Gaming / CS2",
        "voice_id": "en-US-ChristopherNeural",
        "speech_rate": "+16%",
        "include_music": False,
        "include_sfx": True,
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "crop",
                "custom_image_path": CROP_COUPON,
                "direction": "zoom",
                "caption": "Secret Code: mesto300",
                "caption_highlight": "mesto300",
                "highlight_color": [255, 215, 0],
                "voice_text": "Do not confirm your next CS2 trade without entering this secret promo code.",
                "sfx": "heavy_impact",
                "duration": 3.6,
            },
            {
                "scene_num": 2,
                "visual_type": "crop",
                "custom_image_path": CROP_HOW_IT_WORKS,
                "direction": "left",
                "caption": "How To Redeem Your Perks",
                "caption_highlight": "Redeem",
                "highlight_color": [56, 182, 255],
                "voice_text": "Go to tradeit.gg and click on the coupon code redemption button in the top menu.",
                "sfx": "whoosh",
                "duration": 3.8,
            },
            {
                "scene_num": 3,
                "visual_type": "crop",
                "custom_image_path": CROP_BONUS,
                "direction": "top",
                "caption": "Unlock $5 Free + 35% Top-Up",
                "caption_highlight": "$5 Free",
                "highlight_color": [0, 255, 65],
                "voice_text": "Type mesto 300 to instantly unlock five dollars in free balance and a thirty-five percent deposit bonus.",
                "sfx": "case_unlock",
                "duration": 4.2,
            },
            {
                "scene_num": 4,
                "visual_type": "skin",
                "skin_name": "★ Stiletto Knife | Doppler",
                "price_usd": "$820.00 USD",
                "rarity": "covert",
                "direction": "right",
                "caption": "Grab your dream skins now",
                "caption_highlight": "dream skins",
                "highlight_color": [0, 255, 65],
                "voice_text": "You can immediately spend the bonus balance on clean knives, gloves, and weapons.",
                "sfx": "cash_register",
                "duration": 3.6,
            },
            {
                "scene_num": 5,
                "visual_type": "voucher",
                "promocode": "MESTO300",
                "bonus_text": "+35% TOPUP BONUS",
                "free_balance": "$5.00 FREE BALANCE",
                "direction": "bottom",
                "caption": "Go to tradeit.gg - Code mesto300",
                "caption_highlight": "mesto300",
                "highlight_color": [255, 215, 0],
                "voice_text": "Do not miss out. Visit tradeit.gg right now and enter code mesto 300.",
                "sfx": "chime",
                "duration": 3.8,
            },
        ],
    },

    # -------------------------------------------------------------------------
    # 11. Clean Up Your Grey Trash Inventory (Inventory Cleanup Hook)
    # -------------------------------------------------------------------------
    {
        "id": "affiliate_11_inventory_cleanup",
        "name": "Trash Inventory To Covert Weapon",
        "theme": "tradeit",
        "promocode": "MESTO300",
        "category": "Gaming / CS2",
        "voice_id": "en-US-GuyNeural",
        "speech_rate": "+18%",
        "include_music": False,
        "include_sfx": True,
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "skin",
                "skin_name": "AWP | Asiimov",
                "price_usd": "$165.00 USD",
                "rarity": "covert",
                "direction": "zoom",
                "caption": "Turn 3-Cent Skins Into This!",
                "caption_highlight": "Turn 3-Cent Skins",
                "highlight_color": [0, 255, 65],
                "voice_text": "Your Steam inventory is full of worthless three-cent skins. Turn them into this!",
                "sfx": "heavy_impact",
                "duration": 3.4,
            },
            {
                "scene_num": 2,
                "visual_type": "comparison",
                "left_title": "STEAM INVENTORY",
                "right_title": "TRADEIT.GG",
                "left_fee": "50 WORTHLESS SKINS",
                "right_perk": "1 COVERT WEAPON",
                "bonus_code": "CODE: MESTO300",
                "direction": "top",
                "caption": "Bulk select all trash in 1 click",
                "caption_highlight": "1 click",
                "highlight_color": [56, 182, 255],
                "voice_text": "Tradeit lets you select all your duplicate consumer skins at once and combine their full value.",
                "sfx": "whoosh",
                "duration": 4.0,
            },
            {
                "scene_num": 3,
                "visual_type": "crop",
                "custom_image_path": CROP_BONUS,
                "direction": "left",
                "caption": "Adds $5.00 Free Balance On Top",
                "caption_highlight": "$5.00 Free",
                "highlight_color": [0, 255, 65],
                "voice_text": "Then code mesto 300 adds an extra five dollars free on top to jump you into a covert skin.",
                "sfx": "case_unlock",
                "duration": 3.8,
            },
            {
                "scene_num": 4,
                "visual_type": "crop",
                "custom_image_path": CROP_COUPON,
                "direction": "right",
                "caption": "Code: mesto300",
                "caption_highlight": "mesto300",
                "highlight_color": [255, 215, 0],
                "voice_text": "Enter code mesto 300 and watch your trash inventory transform.",
                "sfx": "cash_register",
                "duration": 3.2,
            },
            {
                "scene_num": 5,
                "visual_type": "voucher",
                "promocode": "MESTO300",
                "bonus_text": "+35% TOPUP BONUS",
                "free_balance": "$5.00 FREE BALANCE",
                "direction": "bottom",
                "caption": "Upgrade today at tradeit.gg",
                "caption_highlight": "tradeit.gg",
                "highlight_color": [0, 255, 65],
                "voice_text": "Clean your inventory today at tradeit.gg with code mesto 300.",
                "sfx": "chime",
                "duration": 3.4,
            },
        ],
    },

    # -------------------------------------------------------------------------
    # 12. The 9.5 Trustpilot Social Proof (Reputation Hook)
    # -------------------------------------------------------------------------
    {
        "id": "affiliate_12_trustpilot_proof",
        "name": "9.5 Trustpilot Rating Proof",
        "theme": "tradeit",
        "promocode": "MESTO300",
        "category": "Gaming / CS2",
        "voice_id": "en-US-ChristopherNeural",
        "speech_rate": "+16%",
        "include_music": False,
        "include_sfx": True,
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "crop",
                "custom_image_path": CROP_TRUSTPILOT,
                "direction": "zoom",
                "caption": "9.5 Excellent On Trustpilot",
                "caption_highlight": "9.5 Excellent",
                "highlight_color": [0, 255, 65],
                "voice_text": "Why do over five thousand CS2 players rate this website 9.5 on Trustpilot?",
                "sfx": "heavy_impact",
                "duration": 3.8,
            },
            {
                "scene_num": 2,
                "visual_type": "newspaper",
                "headline": "Tradeit Crosses 45 Million Completed Trades In CS2 And Rust",
                "source": "Global Gaming Ledger",
                "author": "By Trading Desk",
                "caption": "Over 45 Million Trades Done",
                "caption_highlight": "45 Million",
                "highlight_color": [56, 182, 255],
                "direction": "left",
                "voice_text": "With over forty-five million trades completed, Tradeit is the single most trusted skin platform in the world.",
                "sfx": "whoosh",
                "duration": 4.2,
            },
            {
                "scene_num": 3,
                "visual_type": "crop",
                "custom_image_path": CROP_BONUS,
                "direction": "top",
                "caption": "$5.00 Free + 35% Deposit Match",
                "caption_highlight": "$5.00 Free",
                "highlight_color": [0, 255, 65],
                "voice_text": "Every single new user gets five dollars in free balance and a thirty-five percent deposit match.",
                "sfx": "case_unlock",
                "duration": 3.8,
            },
            {
                "scene_num": 4,
                "visual_type": "crop",
                "custom_image_path": CROP_COUPON,
                "direction": "right",
                "caption": "Code: mesto300",
                "caption_highlight": "mesto300",
                "highlight_color": [255, 215, 0],
                "voice_text": "Unlock all official perks by using coupon code mesto 300.",
                "sfx": "cash_register",
                "duration": 3.2,
            },
            {
                "scene_num": 5,
                "visual_type": "voucher",
                "promocode": "MESTO300",
                "bonus_text": "+35% TOPUP BONUS",
                "free_balance": "$5.00 FREE BALANCE",
                "direction": "bottom",
                "caption": "Trade with confidence at tradeit.gg",
                "caption_highlight": "tradeit.gg",
                "highlight_color": [0, 255, 65],
                "voice_text": "Trade with total peace of mind at tradeit.gg using code mesto 300.",
                "sfx": "chime",
                "duration": 3.6,
            },
        ],
    },
]


def render_all_affiliate_videos(start_idx: int = 0, count: int = 12):
    """Renders the batch of affiliate videos and logs each into SQLite history."""
    target_videos = AFFILIATE_VIDEOS[start_idx : start_idx + count]
    print(f"\n=======================================================")
    print(f"🚀 STARTING BATCH RENDER: {len(target_videos)} AFFILIATE SHORTS")
    print(f"Offer: Tradeit.gg Promo Code 'mesto300' ($5 Free + 35% Bonus)")
    print(f"Destination Directory: {OUTPUT_DIR.resolve()}")
    print(f"=======================================================\n")

    rendered_results = []

    for idx, video_spec in enumerate(target_videos, start=1):
        vid_id = video_spec["id"]
        vid_name = video_spec["name"]
        print(f"\n🎬 [{idx}/{len(target_videos)}] Rendering: '{vid_name}' ({vid_id})")
        t0 = time.time()

        try:
            res = render_motion_explainer_short(
                script_data=video_spec,
                voice_id=video_spec.get("voice_id", "en-US-GuyNeural"),
                fps=30,
                include_sfx=video_spec.get("include_sfx", True),
                include_music=video_spec.get("include_music", False),
                progress_callback=lambda pct, msg: print(f"   [{int(pct*100):3d}%] {msg}"),
            )

            out_filename = res["video_filename"]
            duration = res["duration"]

            # Record into clip history database
            try:
                record_clipped_short(
                    source_url=f"motion://tradeit/mesto300/{vid_id}",
                    output_filename=out_filename,
                    title=f"Tradeit.gg - {vid_name} (Code: mesto300)",
                    channel="Tradeit Affiliate Studio",
                    duration=duration,
                    preset="motion_2.5d_affiliate",
                    ai_title=vid_name,
                )
                print(f"   ✅ Logged to clip_history.sqlite: {out_filename}")
            except Exception as h_err:
                print(f"   ⚠️ History logging notice: {h_err}")

            elapsed = time.time() - t0
            print(f"   ✨ Video Finished in {elapsed:.1f}s -> {res['video_path']}")
            rendered_results.append({
                "id": vid_id,
                "name": vid_name,
                "filename": out_filename,
                "path": res["video_path"],
                "duration": duration,
                "elapsed": elapsed,
            })

        except Exception as e:
            print(f"   ❌ Error rendering {vid_id}: {e}")
            import traceback
            traceback.print_exc()

    print("\n=======================================================")
    print(f"🎉 BATCH COMPLETE: {len(rendered_results)}/{len(target_videos)} videos successfully rendered!")
    for r in rendered_results:
        print(f" - {r['name']}: {r['filename']} ({r['duration']:.1f}s)")
    print("=======================================================\n")
    return rendered_results


if __name__ == "__main__":
    count_to_run = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    start_from = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    render_all_affiliate_videos(start_idx=start_from, count=count_to_run)
