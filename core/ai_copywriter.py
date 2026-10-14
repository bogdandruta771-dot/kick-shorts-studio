"""AI Title, Description & Hashtags generator supporting free Gemini API, Groq API, and offline heuristics."""
import re
import json
from typing import Dict, Any, Optional, List
import requests


# Detected slot games registry for smart tag enrichment
KNOWN_GAMES = [
    "Gates of Olympus", "Sweet Bonanza", "Wanted Dead or a Wild", "Sugar Rush",
    "Plinko", "Crazy Time", "Monopoly Live", "Big Bass Bonanza", "Tombstone RIP",
    "San Quentin", "Fruit Party", "Book of Shadows", "Mental", "Dork Unit",
    "Chaos Crew", "Roulette", "Blackjack", "Baccarat"
]


def extract_game_from_text(text: str) -> Optional[str]:
    """Infers casino game name from clip title or speech."""
    if not text:
        return None
    lower = text.lower()
    for game in KNOWN_GAMES:
        if game.lower() in lower:
            return game
    return None


def generate_offline_shorts_copy(
    clip_title: str,
    win_amount: Optional[str] = None,
    streamer: Optional[str] = None,
    transcript: Optional[str] = None,
    promo_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    100% Free Offline Heuristic Copywriting Engine.
    Generates 5 viral YouTube Shorts titles, 3 description variants, and trending hashtags.
    Works with ZERO API keys or internet connection required.
    """
    # Clean inputs
    streamer_clean = streamer.strip() if streamer else "Streamer"
    promo = promo_code.strip() if promo_code else "PROMO100"
    game = extract_game_from_text(clip_title) or (extract_game_from_text(transcript or "") or "Slots")
    
    # Try to find dollar amount or multiplier if win_amount not given
    amount_str = win_amount or ""
    if not amount_str:
        m = re.search(r"(\$[\d,]+(?:\.\d+)?|\d+x|\d+X)", clip_title)
        if m:
            amount_str = m.group(1).upper()
        else:
            amount_str = "HUGE WIN"

    # 5 Viral Title Options with High Click-Through Rate Hooks
    titles = [
        f"HE HIT {amount_str} ON {game.upper()}?! 😱💸 #shorts",
        f"Watch What Happens On The Very Last Spin... 🎰🤯 #shorts",
        f"INSANE {amount_str} MOMENT ON KICK! ({game}) 🚀 #shorts",
        f"{streamer_clean.upper()} ACTUALLY DID IT... Look At His Face! 😭🔥 #shorts",
        f"BIGGEST WIN OF THE NIGHT! ({amount_str}) 💰 #shorts #casino",
    ]

    # 3 High-Converting Description Variants
    desc_promo = (
        f"🎰 Insane {amount_str} hit on {game} live on stream!\n\n"
        f"🎁 Use Code: {promo} for exclusive VIP rewards & bonus!\n"
        f"👉 Subscribe for daily Kick casino big win shorts!\n\n"
        f"🔞 18+ Only. Gamble responsibly. Gambling is for entertainment purposes only.\n\n"
        f"#shorts #kick #casino #bigwin #{game.lower().replace(' ', '')} #slots"
    )

    desc_engagement = (
        f"Did you expect this {amount_str} at the end?! Drop a comment with your biggest multiplier below! 👇\n\n"
        f"🔥 Streamer: {streamer_clean}\n"
        f"🎰 Game: {game}\n"
        f"🎁 Claim Code: {promo}\n\n"
        f"🔔 Smash Like & Subscribe for daily winning moments!\n\n"
        f"🔞 18+ Play responsibly.\n\n"
        f"#shorts #kickclips #casino #jackpot #gambling"
    )

    desc_seo = (
        f"Huge winning reaction on Kick livestream playing {game}. "
        f"Watch the full bonus round and massive payout of {amount_str}.\n\n"
        f"📌 Claim your bonus with code: {promo}\n"
        f"✨ Daily Kick slot highlights & high-stakes moments.\n\n"
        f"🔞 18+ Be Gamble Aware.\n\n"
        f"#shorts #kick #casino #slots #gambling #{game.lower().replace(' ', '')} #slotmachine"
    )

    hashtags = [
        "#shorts",
        "#kick",
        "#casino",
        "#bigwin",
        f"#{game.lower().replace(' ', '')}",
        "#slots",
        "#gambling",
        "#stake",
        "#jackpot",
    ]

    return {
        "provider": "offline",
        "titles": titles,
        "descriptions": [desc_promo, desc_engagement, desc_seo],
        "hashtags": hashtags,
    }


def _normalize_metadata(result: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures exactly 5 titles, 3 description variants, and valid hashtags are present."""
    titles = result.get("titles") or []
    if not isinstance(titles, list):
        titles = [str(titles)]
    if len(titles) < 5:
        titles.extend(fallback["titles"][len(titles):])

    descriptions = result.get("descriptions") or []
    if not isinstance(descriptions, list):
        descriptions = [str(descriptions)]
    if len(descriptions) < 3:
        descriptions.extend(fallback["descriptions"][len(descriptions):])

    hashtags = result.get("hashtags") or fallback.get("hashtags", [])
    if not isinstance(hashtags, list):
        hashtags = fallback.get("hashtags", [])

    return {
        "provider": result.get("provider", fallback.get("provider", "offline")),
        "titles": [str(t) for t in titles[:5]],
        "descriptions": [str(d) for d in descriptions[:3]],
        "hashtags": [str(h) for h in hashtags],
    }


def generate_with_gemini_api(
    api_key: str,
    clip_title: str,
    win_amount: Optional[str] = None,
    streamer: Optional[str] = None,
    transcript: Optional[str] = None,
    promo_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Calls free Google Gemini API with automated multi-model fallbacks for high-converting Shorts copy."""
    clean_key = api_key.strip()
    promo = promo_code.strip() if promo_code else "PROMO100"
    fallback_data = generate_offline_shorts_copy(clip_title, win_amount, streamer, transcript, promo)

    prompt = f"""
You are an elite YouTube Shorts growth specialist for gaming and casino highlight channels.
Analyze this livestream big win moment and generate viral metadata.

DETAILS:
- Clip Title: {clip_title}
- Win/Multiplier: {win_amount or 'Big Win'}
- Streamer: {streamer or 'Streamer'}
- Spoken Words / Transcript: {transcript or 'No dialogue recorded'}
- Active Promo Code: {promo}

OUTPUT REQUIREMENTS:
Return strict, raw JSON with no markdown backticks and no preamble:
{{
  "titles": [
    "5 catchy, high-CTR YouTube Shorts titles with emojis and #shorts (under 75 characters each)"
  ],
  "descriptions": [
    "Variant 1: Promo-focused description with the promo code and 18+ disclaimer",
    "Variant 2: High engagement question-based description asking viewers to comment",
    "Variant 3: SEO-optimized description with game keywords and subscribe CTA"
  ],
  "hashtags": [
    "7-10 trending relevant hashtags including #shorts #kick #casino"
  ]
}}
"""
    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 800},
    }

    candidate_models = [
        ("v1beta", "gemini-1.5-flash-latest"),
        ("v1beta", "gemini-2.0-flash"),
        ("v1beta", "gemini-1.5-flash"),
        ("v1", "gemini-1.5-flash"),
        ("v1beta", "gemini-2.5-flash"),
        ("v1beta", "gemini-1.5-pro"),
    ]

    last_err = None
    for api_ver, model_name in candidate_models:
        url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{model_name}:generateContent?key={clean_key}"
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    continue
                raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                match = re.search(r"\{[\s\S]*\}", raw_text)
                if match:
                    parsed = json.loads(match.group(0))
                else:
                    clean = re.sub(r"^```(?:json)?", "", raw_text.strip(), flags=re.MULTILINE)
                    clean = re.sub(r"```$", "", clean.strip(), flags=re.MULTILINE).strip()
                    parsed = json.loads(clean)
                parsed["provider"] = f"{model_name} (free)"
                return _normalize_metadata(parsed, fallback_data)
            elif resp.status_code == 404:
                last_err = f"Model {model_name} on {api_ver} not found (404)"
                continue
            else:
                last_err = f"Gemini API error ({resp.status_code}): {resp.text}"
                break
        except Exception as e:
            last_err = str(e)
            continue

    raise ValueError(f"Gemini API error: {last_err}")


def generate_with_groq_api(
    api_key: str,
    clip_title: str,
    win_amount: Optional[str] = None,
    streamer: Optional[str] = None,
    transcript: Optional[str] = None,
    promo_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Calls free Groq API (llama-3.3-70b-versatile) for high-converting Shorts copy."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    promo = promo_code.strip() if promo_code else "PROMO100"
    fallback_data = generate_offline_shorts_copy(clip_title, win_amount, streamer, transcript, promo)

    prompt = f"""
You are an elite YouTube Shorts growth specialist for gaming and casino highlight channels.
Analyze this livestream big win moment and generate viral metadata.

DETAILS:
- Clip Title: {clip_title}
- Win/Multiplier: {win_amount or 'Big Win'}
- Streamer: {streamer or 'Streamer'}
- Spoken Words: {transcript or 'None'}
- Active Promo Code: {promo}

Return valid JSON with:
"titles": 5 viral YouTube Shorts titles with emojis and #shorts,
"descriptions": 3 full description variants (Promo-focused, Engagement, SEO),
"hashtags": 8-10 trending hashtags.
"""
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a YouTube Shorts viral growth copywriter. Output only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
    }

    resp = requests.post(url, headers=headers, json=body, timeout=20)
    if resp.status_code != 200:
        raise ValueError(f"Groq API error ({resp.status_code}): {resp.text}")

    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    match = re.search(r"\{[\s\S]*\}", content)
    if match:
        parsed = json.loads(match.group(0))
    else:
        parsed = json.loads(content)
    parsed["provider"] = "groq-llama-3.3 (free)"
    return _normalize_metadata(parsed, fallback_data)


def generate_shorts_metadata(
    clip_title: str,
    win_amount: Optional[str] = None,
    streamer: Optional[str] = None,
    transcript: Optional[str] = None,
    promo_code: Optional[str] = None,
    api_key: Optional[str] = None,
    provider: str = "auto",
) -> Dict[str, Any]:
    """
    Main dispatcher:
    1. If user provided a Gemini key, uses free Google Gemini API.
    2. If user provided a Groq key (starts with 'gsk_'), uses free Groq API.
    3. If no key or API call fails, falls back instantly to the Smart Offline Copywriter.
    Zero crashes, 100% reliable and free.
    """
    clean_key = (api_key or "").strip()
    
    if clean_key:
        if clean_key.startswith("gsk_") or provider == "groq":
            try:
                return generate_with_groq_api(
                    clean_key, clip_title, win_amount, streamer, transcript, promo_code
                )
            except Exception as e:
                print(f"Groq call notice: {e}; falling back to offline copywriter.")
        else:
            try:
                return generate_with_gemini_api(
                    clean_key, clip_title, win_amount, streamer, transcript, promo_code
                )
            except Exception as e:
                print(f"Gemini call notice: {e}; falling back to offline copywriter.")

    # Guaranteed 100% free fallback
    return generate_offline_shorts_copy(
        clip_title, win_amount, streamer, transcript, promo_code
    )
