"""AI Title, Description & Hashtags generator supporting free Gemini API, Groq API, and offline heuristics."""
import re
import json
from typing import Dict, Any, Optional, List
import requests


# Extended stream games & categories registry
KNOWN_GAMES = [
    # Casino & Slots
    "Gates of Olympus", "Sweet Bonanza", "Wanted Dead or a Wild", "Sugar Rush",
    "Plinko", "Crazy Time", "Monopoly Live", "Big Bass Bonanza", "Tombstone RIP",
    "San Quentin", "Fruit Party", "Book of Shadows", "Mental", "Dork Unit",
    "Chaos Crew", "Roulette", "Blackjack", "Baccarat", "Slots",
    # Esports & Gaming
    "Valorant", "Counter-Strike 2", "CS2", "Fortnite", "Warzone", "Call of Duty",
    "Minecraft", "GTA V", "GTA RP", "Apex Legends", "League of Legends", "Dota 2",
    "Overwatch 2", "Elden Ring", "Rocket League", "Rainbow Six Siege", "Roblox"
]


def extract_game_from_text(text: str) -> Optional[str]:
    """Infers game or stream category from clip title or speech."""
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
    category: str = "general",
) -> Dict[str, Any]:
    """
    100% Free Offline Heuristic Copywriting Engine.
    Generates 5 viral YouTube Shorts titles, 3 description variants, and trending hashtags.
    Supports Gaming, Just Chatting / IRL, Casino, and General streaming categories.
    """
    # Clean inputs
    streamer_clean = streamer.strip() if streamer else "Streamer"
    promo = promo_code.strip() if promo_code else "PROMO100"
    inferred_game = extract_game_from_text(clip_title) or (extract_game_from_text(transcript or "") or "")

    cat = (category or "general").lower().strip()
    if cat == "general":
        if any(g.lower() in (clip_title + " " + (transcript or "")).lower() for g in ["valorant", "cs2", "fortnite", "clutch", "ace", "headshot", "kill", "warzone", "minecraft", "apex"]):
            cat = "gaming"
        elif any(c.lower() in (clip_title + " " + (transcript or "")).lower() for c in ["slot", "casino", "bonus", "win", "spin", "multiplier", "$"]):
            cat = "casino"
        elif any(i.lower() in (clip_title + " " + (transcript or "")).lower() for i in ["drama", "talking", "story", "irl", "reaction", "react"]):
            cat = "just_chatting"

    # --- CATEGORY: GAMING & ESPORTS ---
    if cat == "gaming":
        game_tag = inferred_game or "Gaming"
        titles = [
            f"BRO DID NOT JUST HIT THAT! 😱🎯 ({game_tag}) #shorts",
            f"The Cleanest Clutch You Will See All Week! 🔥 #shorts",
            f"{streamer_clean.upper()} Raged So Hard After This Play... 💀 #shorts",
            f"HOW DID HE SURVIVE THIS?! 🤯 #shorts #gaming",
            f"Look At His Face When He Realized What Happened 🤣 #shorts",
        ]
        desc_highlight = (
            f"🎮 Insane {game_tag} highlight from {streamer_clean}'s live stream!\n\n"
            f"👉 Drop a comment with your best clutch moment! 👇\n"
            f"🔔 Smash Like & Subscribe for daily stream clips & insane plays!\n\n"
            f"#shorts #gaming #streamer #twitch #twitchclips #clutch #gameplay #{game_tag.lower().replace(' ', '')}"
        )
        desc_engagement = (
            f"Could you pull off this play under pressure?! Let me know below! 👇\n\n"
            f"🔥 Streamer: {streamer_clean}\n"
            f"🎮 Game: {game_tag}\n\n"
            f"✨ Subscribe for daily funny & clutch moments!\n\n"
            f"#shorts #gamingcommunity #twitch #clips #viral"
        )
        desc_seo = (
            f"Best stream moments and highlight reel featuring {streamer_clean} playing {game_tag}.\n\n"
            f"📌 Daily gaming shorts, funny fails, and epic clutches.\n"
            f"👉 Don't forget to like and subscribe!\n\n"
            f"#shorts #gaming #streamclips #esports #{game_tag.lower().replace(' ', '')}"
        )
        hashtags = ["#shorts", "#gaming", "#twitch", "#twitchclips", "#streamer", "#clutch", "#viral", f"#{game_tag.lower().replace(' ', '')}"]

    # --- CATEGORY: JUST CHATTING & IRL ---
    elif cat in ("just_chatting", "irl", "reaction"):
        titles = [
            f"I Cannot Believe He Actually Said This On Stream... 😭 #shorts",
            f"{streamer_clean.upper()}'s Honest Reaction Is Priceless 😂 #shorts",
            f"The Craziest Story Told On Stream Today 💀 #shorts #irl",
            f"Things Got Completely Out Of Hand Here... 😳 #shorts",
            f"Watch His Face When She Said That 🤣 #shorts #clips",
        ]
        desc_highlight = (
            f"Unfiltered stream moment from {streamer_clean} live on stream!\n\n"
            f"💬 What would you have done in this situation? Comment below! 👇\n"
            f"🔔 Subscribe for daily stream drama, funny moments & reactions!\n\n"
            f"#shorts #justchatting #streamer #twitch #kick #irl #reaction #funny"
        )
        desc_engagement = (
            f"Did not expect this conversation to go this way 😭💀\n\n"
            f"🔥 Streamer: {streamer_clean}\n\n"
            f"👉 Make sure to subscribe for more crazy live moments!\n\n"
            f"#shorts #streamclips #irl #storytime #reaction"
        )
        desc_seo = (
            f"Top Just Chatting and IRL moments from {streamer_clean}'s livestream.\n\n"
            f"✨ Daily stream highlights, comedy, and creator moments.\n\n"
            f"#shorts #justchatting #twitch #kick #streamers #funnyclips"
        )
        hashtags = ["#shorts", "#justchatting", "#streamer", "#twitch", "#kick", "#irl", "#reaction", "#funny"]

    # --- CATEGORY: CASINO & SLOTS ---
    else:
        game_tag = inferred_game or "Slots"
        amount_str = win_amount or ""
        if not amount_str:
            m = re.search(r"(\$[\d,]+(?:\.\d+)?|\d+x|\d+X)", clip_title)
            if m:
                amount_str = m.group(1).upper()
            else:
                amount_str = "HUGE WIN"

        titles = [
            f"HE HIT {amount_str} ON {game_tag.upper()}?! 😱💸 #shorts",
            f"Watch What Happens On The Very Last Spin... 🎰🤯 #shorts",
            f"INSANE {amount_str} MOMENT LIVE ON STREAM! ({game_tag}) 🚀 #shorts",
            f"{streamer_clean.upper()} ACTUALLY DID IT... Look At His Face! 😭🔥 #shorts",
            f"BIGGEST WIN OF THE NIGHT! ({amount_str}) 💰 #shorts #casino",
        ]
        desc_highlight = (
            f"🎰 Insane {amount_str} hit on {game_tag} live on stream!\n\n"
            f"🎁 Use Code: {promo} for exclusive VIP rewards & bonus!\n"
            f"👉 Subscribe for daily big win shorts!\n\n"
            f"🔞 18+ Only. Gamble responsibly.\n\n"
            f"#shorts #casino #bigwin #{game_tag.lower().replace(' ', '')} #slots"
        )
        desc_engagement = (
            f"Did you expect this {amount_str} at the end?! Drop a comment with your biggest multiplier below! 👇\n\n"
            f"🔥 Streamer: {streamer_clean}\n"
            f"🎰 Game: {game_tag}\n"
            f"🎁 Claim Code: {promo}\n\n"
            f"🔔 Smash Like & Subscribe for daily winning moments!\n\n"
            f"#shorts #streamer #casino #jackpot"
        )
        desc_seo = (
            f"Huge winning reaction livestream playing {game_tag}. "
            f"Watch the full bonus round and payout of {amount_str}.\n\n"
            f"📌 Claim your bonus with code: {promo}\n"
            f"🔞 18+ Be Gamble Aware.\n\n"
            f"#shorts #casino #slots #gambling #{game_tag.lower().replace(' ', '')}"
        )
        hashtags = ["#shorts", "#casino", "#bigwin", f"#{game_tag.lower().replace(' ', '')}", "#slots", "#gambling", "#jackpot"]

    return {
        "provider": "offline",
        "engine": "offline_templates",
        "category": cat,
        "titles": titles,
        "descriptions": [desc_highlight, desc_engagement, desc_seo],
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
    category: str = "general",
) -> Dict[str, Any]:
    """Calls free Google Gemini API with automated multi-model fallbacks for high-converting Shorts copy."""
    clean_key = api_key.strip()
    promo = promo_code.strip() if promo_code else "PROMO100"
    fallback_data = generate_offline_shorts_copy(clip_title, win_amount, streamer, transcript, promo, category=category)

    cat_label = {
        "gaming": "gaming, esports, clutches, and funny stream fails",
        "just_chatting": "Just Chatting, IRL, podcast drama, and funny streamer reactions",
        "casino": "casino slot big wins, multipliers, and jackpot moments",
    }.get(category.lower(), "stream highlights, funny moments, and viral clips")

    prompt = f"""
You are an elite YouTube Shorts growth specialist for {cat_label}.
Analyze this stream clip moment and generate viral metadata.

DETAILS:
- Content Category: {category.upper()}
- Clip Title: {clip_title}
- Context/Highlight: {win_amount or 'Stream Highlight'}
- Streamer: {streamer or 'Streamer'}
- Spoken Words / Transcript: {transcript or 'No dialogue recorded'}
- Active Promo Code (if relevant): {promo}

OUTPUT REQUIREMENTS:
Return strict, raw JSON with no markdown backticks and no preamble:
{{
  "titles": [
    "5 catchy, high-CTR YouTube Shorts titles with emojis and #shorts (under 75 characters each)"
  ],
  "descriptions": [
    "Variant 1: Action-packed highlight description with creator credits",
    "Variant 2: High engagement question-based description asking viewers to comment",
    "Variant 3: SEO-optimized description with game/topic keywords and subscribe CTA"
  ],
  "hashtags": [
    "7-10 trending relevant hashtags including #shorts"
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
    category: str = "general",
) -> Dict[str, Any]:
    """Calls free Groq API (llama-3.3-70b-versatile) for high-converting Shorts copy."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    promo = promo_code.strip() if promo_code else "PROMO100"
    fallback_data = generate_offline_shorts_copy(clip_title, win_amount, streamer, transcript, promo, category=category)

    prompt = f"""
You are an elite YouTube Shorts growth specialist for {category} stream highlights.
Analyze this stream clip moment and generate viral metadata.

DETAILS:
- Category: {category.upper()}
- Clip Title: {clip_title}
- Context/Highlight: {win_amount or 'Stream Highlight'}
- Streamer: {streamer or 'Streamer'}
- Spoken Words: {transcript or 'None'}
- Active Promo Code: {promo}

Return valid JSON with:
"titles": 5 viral YouTube Shorts titles with emojis and #shorts,
"descriptions": 3 full description variants (Highlight-focused, Engagement, SEO),
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
    category: str = "general",
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
                    clean_key, clip_title, win_amount, streamer, transcript, promo_code, category=category
                )
            except Exception as e:
                print(f"Groq call notice: {e}; falling back to offline copywriter.")
        else:
            try:
                return generate_with_gemini_api(
                    clean_key, clip_title, win_amount, streamer, transcript, promo_code, category=category
                )
            except Exception as e:
                print(f"Gemini call notice: {e}; falling back to offline copywriter.")

    # Guaranteed 100% free fallback
    return generate_offline_shorts_copy(
        clip_title, win_amount, streamer, transcript, promo_code, category=category
    )
