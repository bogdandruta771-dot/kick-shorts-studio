"""
AI Motion Scriptwriter & Presets Engine
Generates high-converting 5-scene motion explainer scripts designed for 1080x1920 60fps Shorts:
Scene 1: Curiosity Hook (3D Floating Card)
Scene 2: The News / Proof (Tilted Newspaper Article Card)
Scene 3: The Risk / Twist (Warning Breakdown / Danger)
Scene 4: The App Solution (Interactive Smartphone Mockup with Metrics)
Scene 5: Call to Action (Big Action CTA Button & Link)
"""
import os
import re
import json
from typing import Dict, Any, List, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

VIRAL_PRESETS = [
    {
        "id": "aml_crypto_check",
        "name": "AML & Crypto Wallet Risk (Ref Short Style)",
        "category": "Crypto / Security",
        "badge": "1M+ Views Formula",
        "description": "Explains how innocent users get flagged by receiving tainted coins and introduces an instant wallet risk checker.",
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "card",
                "card_type": "emerald",
                "caption": "The FBI will track you",
                "caption_highlight": "FBI",
                "highlight_color": [75, 110, 245],
                "voice_text": "The FBI will track you because of a single transaction.",
                "duration": 3.0,
            },
            {
                "scene_num": 2,
                "visual_type": "newspaper",
                "source": "The New York Times",
                "headline": "FBI Tracks Suspect Through a Contaminated Crypto Wallet",
                "author": "By Somini Sengupta • March 27, 2026",
                "caption": "because of a single transaction",
                "caption_highlight": "single transaction",
                "highlight_color": [235, 50, 75],
                "voice_text": "A crypto user was recently taken into custody after receiving ordinary coins from an external wallet.",
                "duration": 4.5,
            },
            {
                "scene_num": 3,
                "visual_type": "card",
                "card_type": "obsidian",
                "caption": "the sender's address was tainted",
                "caption_highlight": "tainted",
                "highlight_color": [245, 166, 35],
                "voice_text": "Turns out, the sender's address was linked to high-risk mixers and stolen funds.",
                "duration": 3.5,
            },
            {
                "scene_num": 4,
                "visual_type": "phone",
                "app_name": "AML Check",
                "risk_score": "12.55%",
                "status_label": "Rating scored from A to F, clean wallet",
                "caption": "and get a full risk breakdown",
                "caption_highlight": "risk breakdown",
                "highlight_color": [46, 204, 113],
                "voice_text": "By checking your wallet first, you protect your assets from high-risk contamination.",
                "duration": 4.0,
            },
            {
                "scene_num": 5,
                "visual_type": "phone",
                "app_name": "AML Check",
                "risk_score": "100% Clean",
                "status_label": "Zero Registration Required",
                "caption": "Try it now at AMLCheck.fun",
                "caption_highlight": "AMLCheck.fun",
                "highlight_color": [26, 115, 232],
                "voice_text": "No registration required. Scan your wallet in seconds at AMLCheck.fun.",
                "duration": 3.0,
            },
        ],
    },
    {
        "id": "vpn_privacy_leak",
        "name": "VPN & Browser DNS Leak Alert",
        "category": "Cybersecurity / Tech",
        "badge": "High CTR",
        "description": "Reveals how ordinary browsing histories leak to ISPs and shows an instant DNS leak test tool.",
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "card",
                "card_type": "obsidian",
                "caption": "Your Internet Provider sees everything",
                "caption_highlight": "everything",
                "highlight_color": [235, 50, 75],
                "voice_text": "Your internet provider is watching everything you do, even in incognito mode.",
                "duration": 3.2,
            },
            {
                "scene_num": 2,
                "visual_type": "newspaper",
                "source": "The Wall Street Journal",
                "headline": "Federal Court Rules ISPs Can Sell Unencrypted User Browsing Logs",
                "author": "Tech & Privacy Bureau",
                "caption": "even with private browsing enabled",
                "caption_highlight": "private browsing",
                "highlight_color": [75, 110, 245],
                "voice_text": "Court documents reveal millions of unencrypted DNS requests are logged every single day.",
                "duration": 4.2,
            },
            {
                "scene_num": 3,
                "visual_type": "card",
                "card_type": "violet",
                "caption": "your real IP is completely exposed",
                "caption_highlight": "completely exposed",
                "highlight_color": [245, 166, 35],
                "voice_text": "If your connection leaks, your home address and private data are exposed to data brokers.",
                "duration": 3.8,
            },
            {
                "scene_num": 4,
                "visual_type": "phone",
                "app_name": "LeakGuard Shield",
                "risk_score": "99.8%",
                "status_label": "Encryption grade: Military AES-256",
                "caption": "run an instant leak test now",
                "caption_highlight": "leak test",
                "highlight_color": [46, 204, 113],
                "voice_text": "Run an instant security scan to verify your encryption and kill all hidden tracking pixels.",
                "duration": 4.0,
            },
            {
                "scene_num": 5,
                "visual_type": "phone",
                "app_name": "LeakGuard Shield",
                "risk_score": "Secure",
                "status_label": "100% Anonymous",
                "caption": "Shield your device today",
                "caption_highlight": "Shield your device",
                "highlight_color": [46, 204, 113],
                "voice_text": "One click. Zero logs. Protect your privacy before it is too late.",
                "duration": 3.0,
            },
        ],
    },
    {
        "id": "gaming_ban_alert",
        "name": "Why Innocent Gamers Get Hardware Banned",
        "category": "Gaming & Esports",
        "badge": "Viral Gaming Hook",
        "description": "Tells the story of used PC parts carrying hardware ID bans and how players can audit their PC.",
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "card",
                "card_type": "violet",
                "caption": "Never buy a used GPU without this",
                "caption_highlight": "Never buy",
                "highlight_color": [235, 50, 75],
                "voice_text": "Never buy a second-hand PC part without checking its hardware ID first.",
                "duration": 3.2,
            },
            {
                "scene_num": 2,
                "visual_type": "newspaper",
                "source": "TechCrunch",
                "headline": "Game Anti-Cheat Systems Now Permaban Hardware Across Multiple Titles",
                "author": "Gaming Investigation Desk",
                "caption": "anti-cheat engines permanently blacklist serials",
                "caption_highlight": "permanently blacklist",
                "highlight_color": [235, 50, 75],
                "voice_text": "Anti-cheat systems permanently blacklist motherboard serial numbers across major titles.",
                "duration": 4.5,
            },
            {
                "scene_num": 3,
                "visual_type": "card",
                "card_type": "obsidian",
                "caption": "your new account gets banned instantly",
                "caption_highlight": "banned instantly",
                "highlight_color": [245, 166, 35],
                "voice_text": "The moment you log into Valorant or Warzone, your main account gets wiped instantly.",
                "duration": 3.8,
            },
            {
                "scene_num": 4,
                "visual_type": "phone",
                "app_name": "HWID Audit Pro",
                "risk_score": "0 Flagged",
                "status_label": "Hardware serial clean across 14 titles",
                "caption": "verify your PC hardware health in 5 seconds",
                "caption_highlight": "hardware health",
                "highlight_color": [46, 204, 113],
                "voice_text": "Run an instant hardware audit before you buy or trade any gaming rig.",
                "duration": 4.0,
            },
            {
                "scene_num": 5,
                "visual_type": "phone",
                "app_name": "HWID Audit Pro",
                "risk_score": "Clean",
                "status_label": "Download Free Diagnostic",
                "caption": "Save your account now",
                "caption_highlight": "Save your account",
                "highlight_color": [75, 110, 245],
                "voice_text": "Download the free diagnostic tool and keep your competitive rank safe.",
                "duration": 3.0,
            },
        ],
    },
    {
        "id": "tradeit_mesto300_authentic",
        "name": "TradeIt Promocode MESTO300 (Authentic Motion Ad)",
        "theme": "tradeit",
        "promocode": "MESTO300",
        "category": "Gaming / CS2",
        "badge": "Official Motion Ad",
        "music_track": "none",
        "include_music": False,
        "custom_audio_path": "/assets/cache/ref_ad_audio.wav",
        "speech_rate": "+10%",
        "voice_id": "en-US-ChristopherNeural",
        "description": "Authentic TradeIt motion ad matching ready (2).mp4 with CS2 stop slam, missing item bar, coupon redeem modal, balance toast, and code MESTO300.",
        "scenes": [
            {
                "scene_num": 1,
                "theme": "tradeit",
                "promocode": "MESTO300",
                "duration": 4.0,
                "caption": "Don't confirm your next CS2 trade",
                "caption_highlight": "confirm",
                "highlight_color": [0, 255, 65],
                "voice_text": "Stop! Don't confirm your next CS2 trade until you do this.",
                "sfx": "heavy_impact",
            },
            {
                "scene_num": 2,
                "theme": "tradeit",
                "promocode": "MESTO300",
                "duration": 4.5,
                "caption": "Your trade is missing one item",
                "caption_highlight": "missing",
                "highlight_color": [255, 42, 85],
                "voice_text": "Your trade is missing one item, and it isn't in your Steam inventory.",
                "sfx": "heavy_impact",
            },
            {
                "scene_num": 3,
                "theme": "tradeit",
                "promocode": "MESTO300",
                "duration": 5.0,
                "caption": "Go to tradeit.gg and enter MESTO300",
                "caption_highlight": "MESTO300",
                "highlight_color": [0, 255, 65],
                "voice_text": "Go to tradeit.gg and enter MESTO 300.",
                "sfx": "case_unlock",
            },
            {
                "scene_num": 4,
                "theme": "tradeit",
                "promocode": "MESTO300",
                "duration": 4.0,
                "caption": "The code adds a bonus to your balance",
                "caption_highlight": "bonus",
                "highlight_color": [0, 255, 65],
                "voice_text": "The code adds a bonus to your balance before you choose your upgrade.",
                "sfx": "cash_register",
            },
            {
                "scene_num": 5,
                "theme": "tradeit",
                "promocode": "MESTO300",
                "duration": 3.5,
                "caption": "Now add the skins you no longer use",
                "caption_highlight": "add",
                "highlight_color": [0, 255, 65],
                "voice_text": "Now add the skins you no longer use and see what the complete trade can get you.",
                "sfx": "whoosh",
            },
            {
                "scene_num": 6,
                "theme": "tradeit",
                "promocode": "MESTO300",
                "duration": 7.0,
                "caption": "The most useful item in your next trade",
                "caption_highlight": "useful",
                "highlight_color": [0, 255, 65],
                "voice_text": "The most useful item in your next trade might be the one you can't equip. Go to tradeit.gg and enter MESTO 300.",
                "sfx": "cash_register",
            },
        ],
    },
    {
        "id": "tradeit_mesto300",
        "name": "TradeIt Promocode MESTO300 (CS2 High-Energy)",
        "category": "Gaming / Skin Trading",
        "badge": "Viral Gaming Short",
        "music_track": "gaming_beat",
        "speech_rate": "+18%",
        "description": "High-energy CS2 trading short explaining why Steam fees hurt players and giving +300% bonus with code MESTO300.",
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "skin",
                "skin_name": "★ Karambit | Doppler",
                "skin_category": "Covert Knife",
                "wear_rating": "Factory New • Float 0.00142",
                "price_usd": "$1,850.00 USD",
                "stattrak_count": "001337",
                "rarity": "covert",
                "caption": "Never sell your skins on Steam!",
                "caption_highlight": "Never sell",
                "highlight_color": [235, 50, 75],
                "caption_y_offset": 0.12,
                "caption_font_size": 90,
                "voice_text": "Never sell your CS skins directly on Steam, because Valve takes a massive fifteen percent cut.",
                "sfx": "heavy_impact",
                "duration": 3.6,
            },
            {
                "scene_num": 2,
                "visual_type": "comparison",
                "left_title": "STEAM MARKET",
                "right_title": "TRADEIT.GG",
                "left_fee": "-15% VALVE TAX",
                "right_perk": "INSTANT 0s BOT SWAP",
                "bonus_code": "CODE: MESTO300",
                "caption": "Steam takes 15% - TradeIt is instant",
                "caption_highlight": "TradeIt is instant",
                "highlight_color": [0, 255, 140],
                "caption_y_offset": 0.82,
                "caption_font_size": 90,
                "voice_text": "On Steam you lose fifteen percent and wait seven days. On TradeIt, bots swap your skins in zero seconds.",
                "sfx": "case_unlock",
                "duration": 4.2,
            },
            {
                "scene_num": 3,
                "visual_type": "skin",
                "skin_name": "AWP | Dragon Lore",
                "skin_category": "Covert Sniper Rifle",
                "wear_rating": "Factory New • Float 0.0081",
                "price_usd": "$9,400.00 USD",
                "stattrak_count": None,
                "rarity": "rare_special",
                "caption": "Manual trades expose you to API scams",
                "caption_highlight": "API scams",
                "highlight_color": [255, 60, 60],
                "caption_y_offset": 0.12,
                "caption_font_size": 88,
                "voice_text": "Manual peer-to-peer trades expose your entire inventory to phishing links and fake API bots.",
                "sfx": "heavy_impact",
                "duration": 3.8,
            },
            {
                "scene_num": 4,
                "visual_type": "voucher",
                "promocode": "MESTO300",
                "bonus_text": "+300% BONUS",
                "free_balance": "$5.00 FREE BALANCE",
                "platform": "TradeIt.gg",
                "caption": "Get +300% Bonus with code MESTO300",
                "caption_highlight": "MESTO300",
                "highlight_color": [255, 215, 0],
                "caption_y_offset": 0.82,
                "caption_font_size": 90,
                "voice_text": "Use code MESTO300 to get a massive three hundred percent deposit bonus and five dollars free balance.",
                "sfx": "cash_register",
                "duration": 4.0,
            },
            {
                "scene_num": 5,
                "visual_type": "voucher",
                "promocode": "MESTO300",
                "bonus_text": "+300% BONUS",
                "free_balance": "$5.00 FREE BALANCE",
                "platform": "TradeIt.gg",
                "caption": "Claim free skins now at TradeIt.gg",
                "caption_highlight": "TradeIt.gg",
                "highlight_color": [0, 255, 140],
                "caption_y_offset": 0.82,
                "caption_font_size": 92,
                "voice_text": "Head over to TradeIt.gg right now, enter promo code MESTO300, and claim your free skins today.",
                "sfx": "cash_register",
                "duration": 3.6,
            },
        ],
    },
]


def get_available_presets() -> List[Dict[str, Any]]:
    """Returns available motion explainer templates with populated scene items."""
    from core.motion_explainer.tradeit_assets import get_tradeit_default_items
    try:
        from generate_affiliate_videos_batch import AFFILIATE_VIDEOS
    except Exception:
        AFFILIATE_VIDEOS = []

    presets = []
    # Add all high-converting Tradeit affiliate presets first
    for aff in AFFILIATE_VIDEOS:
        aff_copy = json.loads(json.dumps(aff))
        aff_copy["badge"] = "Affiliate Formula"
        presets.append(aff_copy)

    for p in VIRAL_PRESETS:
        p_copy = json.loads(json.dumps(p))
        if p_copy.get("theme") == "tradeit" or p_copy.get("id") == "tradeit_mesto300_authentic":
            code = p_copy.get("promocode", "MESTO300")
            for s in p_copy.get("scenes", []):
                if not s.get("items"):
                    s["items"] = get_tradeit_default_items(int(s.get("scene_num", 1)), code=code)
        presets.append(p_copy)
    return presets


def generate_motion_script_ai(
    topic_or_url: str,
    product_name: str = "MyProduct",
    category: str = "crypto",
    api_key: Optional[str] = None,
    provider: str = "auto",
) -> Dict[str, Any]:
    """
    Generates a viral 5-scene motion script based on a product URL or topic.
    Returns structured scenes with visual types, headlines, captions, and voiceover text.
    """
    # If no key, find the best matching preset or generate dynamic heuristic script
    clean_topic = topic_or_url.strip()
    clean_prod = product_name.strip() or "SmartShield"

    # Match against built-in viral templates
    topic_lower = clean_topic.lower()
    if any(k in topic_lower for k in ["tradeit", "mesto", "skin", "cs2", "csgo", "steam", "rust"]):
        preset = [p for p in VIRAL_PRESETS if p["id"] == "tradeit_mesto300"][0]
        return preset
    elif any(k in topic_lower for k in ["aml", "crypto", "wallet", "bitcoin", "solana", "stolen", "coins"]):
        preset = [p for p in VIRAL_PRESETS if p["id"] == "aml_crypto_check"][0]
        return preset
    elif any(k in topic_lower for k in ["vpn", "dns", "privacy", "browse", "isp", "track", "ip"]):
        preset = [p for p in VIRAL_PRESETS if p["id"] == "vpn_privacy_leak"][0]
        return preset
    elif any(k in topic_lower for k in ["game", "gamer", "ban", "anticheat", "valorant", "gpu", "hwid"]):
        preset = [p for p in VIRAL_PRESETS if p["id"] == "gaming_ban_alert"][0]
        return preset

    # Generic custom dynamic SaaS script
    return {
        "id": f"custom_{os.urandom(3).hex()}",
        "name": f"{clean_prod} Viral Explainer",
        "category": category.title(),
        "badge": "AI Generated",
        "description": f"Motion storytelling explainer for {clean_prod}",
        "scenes": [
            {
                "scene_num": 1,
                "visual_type": "card",
                "card_type": "emerald",
                "caption": f"Nobody told you about {clean_prod}",
                "caption_highlight": clean_prod,
                "highlight_color": [75, 110, 245],
                "voice_text": f"Here is the secret about {clean_topic} that most people find out way too late.",
                "duration": 3.2,
            },
            {
                "scene_num": 2,
                "visual_type": "newspaper",
                "source": "The Wall Street Journal",
                "headline": f"Why Millions Are Switching to {clean_prod} This Year",
                "author": "By Tech & Business Insights",
                "caption": "industry insiders are quietly switching",
                "caption_highlight": "quietly switching",
                "highlight_color": [235, 50, 75],
                "voice_text": f"Major reports reveal how traditional solutions are costing users thousands every single month.",
                "duration": 4.5,
            },
            {
                "scene_num": 3,
                "visual_type": "card",
                "card_type": "obsidian",
                "caption": "the hidden flaw in ordinary tools",
                "caption_highlight": "hidden flaw",
                "highlight_color": [245, 166, 35],
                "voice_text": "Without automated protection, you are wasting hours on manual headaches.",
                "duration": 3.5,
            },
            {
                "scene_num": 4,
                "visual_type": "phone",
                "app_name": clean_prod,
                "risk_score": "99.9% Faster",
                "status_label": "Verified automated performance",
                "caption": f"automate everything with {clean_prod}",
                "caption_highlight": clean_prod,
                "highlight_color": [46, 204, 113],
                "voice_text": f"With {clean_prod}, you get instant results directly from your smartphone or desktop in seconds.",
                "duration": 4.0,
            },
            {
                "scene_num": 5,
                "visual_type": "phone",
                "app_name": clean_prod,
                "risk_score": "Free Tier",
                "status_label": "Zero Setup Required",
                "caption": f"Try {clean_prod} free today",
                "caption_highlight": "free today",
                "highlight_color": [26, 115, 232],
                "voice_text": f"No credit card required. Try {clean_prod} today and take full control.",
                "duration": 3.0,
            },
        ],
    }


if __name__ == "__main__":
    script = generate_motion_script_ai("Crypto wallet AML check tool", "AMLCheck")
    print("Generated motion script successfully:")
    print("Name:", script["name"])
    print("Scenes count:", len(script["scenes"]))
