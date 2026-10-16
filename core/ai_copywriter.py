"""AI Title, Description & Hashtags generator supporting Gemini, Groq, OpenAI, Claude, DeepSeek, Ollama, OpenRouter, and offline heuristics."""
import re
import json
import time
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


SUPPORTED_AI_PROVIDERS = [
    {
        "id": "auto",
        "name": "Auto-Detect (Smart Routing)",
        "badge": "Smart Auto",
        "free": True,
        "requires_key": False,
        "description": "Automatically selects the best available engine based on your key or local Ollama setup.",
    },
    {
        "id": "gemini",
        "name": "Google Gemini (Free Tier)",
        "badge": "100% Free",
        "free": True,
        "requires_key": True,
        "default_model": "gemini-1.5-flash-latest",
        "models": ["gemini-1.5-flash-latest", "gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-pro"],
        "docs_url": "https://aistudio.google.com/app/apikey",
        "description": "Fast multimodal Google AI model with generous free daily tier.",
    },
    {
        "id": "groq",
        "name": "Groq (Ultra-Fast Free)",
        "badge": "Ultra-Fast Free",
        "free": True,
        "requires_key": True,
        "default_model": "llama-3.3-70b-versatile",
        "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"],
        "docs_url": "https://console.groq.com/keys",
        "description": "Near-instantaneous inference (500+ tokens/sec) on Llama 3.3 70B.",
    },
    {
        "id": "ollama",
        "name": "Ollama (Local LLM / Private / No Key)",
        "badge": "100% Free & Offline",
        "free": True,
        "requires_key": False,
        "default_base_url": "http://localhost:11434/v1",
        "default_model": "llama3",
        "models": ["llama3", "mistral", "qwen2.5", "llama3.2", "phi3"],
        "docs_url": "https://ollama.com",
        "description": "Runs completely locally on your GPU/CPU with 100% privacy and zero API fees.",
    },
    {
        "id": "openai",
        "name": "OpenAI (GPT-4o Mini / GPT-4o)",
        "badge": "High CTR",
        "free": False,
        "requires_key": True,
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        "docs_url": "https://platform.openai.com/api-keys",
        "description": "Industry benchmark for high-CTR YouTube title hooks and copywriting.",
    },
    {
        "id": "claude",
        "name": "Anthropic Claude (3.5 Sonnet / Haiku)",
        "badge": "Elite Nuance",
        "free": False,
        "requires_key": True,
        "default_model": "claude-3-5-haiku-20241022",
        "models": ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
        "docs_url": "https://console.anthropic.com/settings/keys",
        "description": "Known for highly natural, non-generic conversational hooks and descriptions.",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek (V3 / Chat)",
        "badge": "Cost Effective",
        "free": False,
        "requires_key": True,
        "default_base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "docs_url": "https://platform.deepseek.com/api_keys",
        "description": "High performance at ultra-low cost per token.",
    },
    {
        "id": "openrouter",
        "name": "OpenRouter (100+ Models)",
        "badge": "Multi-Model Hub",
        "free": True,
        "requires_key": True,
        "default_base_url": "https://openrouter.ai/api/v1",
        "default_model": "meta-llama/llama-3.1-8b-instruct:free",
        "models": ["meta-llama/llama-3.1-8b-instruct:free", "google/gemini-2.0-flash-exp:free", "openrouter/auto"],
        "docs_url": "https://openrouter.ai/keys",
        "description": "Unified gateway to dozens of free and paid open-source models.",
    },
    {
        "id": "custom",
        "name": "Custom OpenAI-Compatible Endpoint",
        "badge": "LM Studio / vLLM",
        "free": True,
        "requires_key": False,
        "default_base_url": "http://localhost:1234/v1",
        "default_model": "local-model",
        "description": "Connect to LM Studio, vLLM, LocalAI, or any custom API server.",
    },
    {
        "id": "offline",
        "name": "Smart Offline Template Engine",
        "badge": "Zero Setup / Built-in",
        "free": True,
        "requires_key": False,
        "description": "Instant heuristic copywriter tuned for Gaming, Casino, and Just Chatting streams.",
    },
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
    streamer_clean = streamer.strip() if streamer else "Streamer"
    promo = promo_code.strip() if promo_code else "PROMO100"
    inferred_game = extract_game_from_text(clip_title) or (extract_game_from_text(transcript or "") or "")

    cat = (category or "general").lower().strip()
    if cat == "general":
        text_lower = (clip_title + " " + (transcript or "")).lower()
        if any(g.lower() in text_lower for g in ["valorant", "cs2", "fortnite", "clutch", "ace", "headshot", "kill", "warzone", "minecraft", "apex"]):
            cat = "gaming"
        elif any(c.lower() in text_lower for c in ["slot", "casino", "bonus", "win", "spin", "multiplier", "$"]):
            cat = "casino"
        elif any(i.lower() in text_lower for i in ["drama", "talking", "story", "irl", "reaction", "react"]):
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
        "provider": "Offline Heuristics (Instant)",
        "engine": "offline_templates",
        "category": cat,
        "titles": titles,
        "descriptions": [desc_highlight, desc_engagement, desc_seo],
        "hashtags": hashtags,
    }


def _normalize_metadata(result: Dict[str, Any], fallback: Dict[str, Any], provider_name: str = "AI Engine") -> Dict[str, Any]:
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
        "provider": provider_name,
        "titles": [str(t) for t in titles[:5]],
        "descriptions": [str(d) for d in descriptions[:3]],
        "hashtags": [str(h) for h in hashtags],
    }


def _parse_ai_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """Safely extracts JSON object from raw LLM output."""
    if not raw_text or not raw_text.strip():
        return None
    # 1. Regex find outer braces
    match = re.search(r"\{[\s\S]*\}", raw_text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    # 2. Try markdown strip
    clean = re.sub(r"^```(?:json)?", "", raw_text.strip(), flags=re.MULTILINE)
    clean = re.sub(r"```$", "", clean.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(clean)
    except Exception:
        return None


def build_shorts_prompt(
    clip_title: str,
    win_amount: Optional[str] = None,
    streamer: Optional[str] = None,
    transcript: Optional[str] = None,
    promo_code: Optional[str] = None,
    category: str = "general",
) -> str:
    """Constructs prompt for viral YouTube Shorts metadata generation."""
    cat_label = {
        "gaming": "gaming, esports, clutches, and funny stream fails",
        "just_chatting": "Just Chatting, IRL, podcast drama, and funny streamer reactions",
        "casino": "casino slot big wins, multipliers, and jackpot moments",
    }.get(category.lower(), "stream highlights, funny moments, and viral clips")

    promo = promo_code.strip() if promo_code else "PROMO100"

    return f"""You are an elite YouTube Shorts growth specialist and algorithm hacker for {cat_label}.
Analyze this stream clip moment and generate viral metadata.

DETAILS:
- Content Category: {category.upper()}
- Clip Title: {clip_title}
- Context/Highlight: {win_amount or 'Stream Highlight'}
- Streamer: {streamer or 'Streamer'}
- Spoken Words / Transcript: {transcript or 'No dialogue recorded'}
- Promo/Affiliate Code: {promo}

OUTPUT REQUIREMENTS:
Return strict, raw JSON with NO markdown formatting, NO backticks, and NO conversational text:
{{
  "titles": [
    "5 catchy, high-CTR YouTube Shorts titles with emojis and #shorts (under 75 characters each)"
  ],
  "descriptions": [
    "Variant 1: Action-packed highlight description with creator credits and hashtags",
    "Variant 2: High engagement question-based description asking viewers to comment below",
    "Variant 3: SEO-optimized description with game/topic keywords and subscribe CTA"
  ],
  "hashtags": [
    "7-10 trending relevant hashtags including #shorts"
  ]
}}"""


def generate_with_gemini_api(
    api_key: str,
    clip_title: str,
    win_amount: Optional[str] = None,
    streamer: Optional[str] = None,
    transcript: Optional[str] = None,
    promo_code: Optional[str] = None,
    category: str = "general",
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Calls Google Gemini API with multi-model failover."""
    clean_key = api_key.strip()
    fallback_data = generate_offline_shorts_copy(clip_title, win_amount, streamer, transcript, promo_code, category=category)
    prompt = build_shorts_prompt(clip_title, win_amount, streamer, transcript, promo_code, category)

    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 800},
    }

    candidate_models = [
        ("v1beta", model or "gemini-1.5-flash-latest"),
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
            resp = requests.post(url, headers=headers, json=body, timeout=18)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    continue
                raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                parsed = _parse_ai_json(raw_text)
                if parsed:
                    return _normalize_metadata(parsed, fallback_data, f"Gemini ({model_name})")
            elif resp.status_code == 404:
                last_err = f"Model {model_name} (404)"
                continue
            else:
                last_err = f"Gemini error ({resp.status_code}): {resp.text}"
                break
        except Exception as e:
            last_err = str(e)
            continue

    raise ValueError(f"Gemini API notice: {last_err}")


def generate_with_claude_api(
    api_key: str,
    clip_title: str,
    win_amount: Optional[str] = None,
    streamer: Optional[str] = None,
    transcript: Optional[str] = None,
    promo_code: Optional[str] = None,
    category: str = "general",
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Calls Anthropic Claude API (e.g. claude-3-5-haiku-20241022 or claude-3-5-sonnet)."""
    clean_key = api_key.strip()
    fallback_data = generate_offline_shorts_copy(clip_title, win_amount, streamer, transcript, promo_code, category=category)
    prompt = build_shorts_prompt(clip_title, win_amount, streamer, transcript, promo_code, category)

    target_model = model or "claude-3-5-haiku-20241022"
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": clean_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": target_model,
        "max_tokens": 1000,
        "system": "You are a professional YouTube Shorts growth copywriter. Output only valid raw JSON.",
        "messages": [
            {"role": "user", "content": prompt}
        ],
    }

    resp = requests.post(url, headers=headers, json=body, timeout=20)
    if resp.status_code != 200:
        raise ValueError(f"Claude API error ({resp.status_code}): {resp.text}")

    data = resp.json()
    content_parts = data.get("content", [])
    raw_text = content_parts[0].get("text", "") if content_parts else ""
    parsed = _parse_ai_json(raw_text)
    if not parsed:
        raise ValueError("Failed to parse valid JSON from Claude response.")

    return _normalize_metadata(parsed, fallback_data, f"Claude ({target_model})")


def generate_with_openai_compatible(
    api_key: Optional[str],
    base_url: str,
    model: str,
    clip_title: str,
    win_amount: Optional[str] = None,
    streamer: Optional[str] = None,
    transcript: Optional[str] = None,
    promo_code: Optional[str] = None,
    category: str = "general",
    provider_label: str = "OpenAI",
) -> Dict[str, Any]:
    """Universal caller for OpenAI, Groq, DeepSeek, Ollama, OpenRouter, LM Studio, etc."""
    fallback_data = generate_offline_shorts_copy(clip_title, win_amount, streamer, transcript, promo_code, category=category)
    prompt = build_shorts_prompt(clip_title, win_amount, streamer, transcript, promo_code, category)

    clean_url = base_url.strip().rstrip("/")
    if not clean_url.endswith("/chat/completions"):
        if clean_url.endswith("/v1"):
            clean_url = f"{clean_url}/chat/completions"
        else:
            clean_url = f"{clean_url}/v1/chat/completions"

    headers = {"Content-Type": "application/json"}
    if api_key and api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a viral YouTube Shorts growth copywriter. Output only raw valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
    }

    # If provider supports json_object response_format
    if any(k in provider_label.lower() for k in ["groq", "openai", "deepseek"]):
        body["response_format"] = {"type": "json_object"}

    resp = requests.post(clean_url, headers=headers, json=body, timeout=25)
    if resp.status_code != 200:
        raise ValueError(f"{provider_label} error ({resp.status_code}): {resp.text}")

    data = resp.json()
    choices = data.get("choices", [])
    if not choices:
        raise ValueError(f"{provider_label} returned no response choices.")

    content = choices[0].get("message", {}).get("content", "")
    parsed = _parse_ai_json(content)
    if not parsed:
        raise ValueError(f"Could not parse valid JSON from {provider_label} output.")

    return _normalize_metadata(parsed, fallback_data, f"{provider_label} ({model})")


def is_ollama_running(base_url: str = "http://localhost:11434") -> bool:
    """Checks if local Ollama server is running and accessible."""
    try:
        clean = base_url.strip().rstrip("/")
        if clean.endswith("/v1"):
            clean = clean[:-3]
        resp = requests.get(f"{clean}/api/tags", timeout=1.0)
        return resp.status_code == 200
    except Exception:
        return False


def get_available_ai_providers() -> List[Dict[str, Any]]:
    """Returns registry of supported AI providers for studio UI."""
    return SUPPORTED_AI_PROVIDERS


def generate_shorts_metadata(
    clip_title: str,
    win_amount: Optional[str] = None,
    streamer: Optional[str] = None,
    transcript: Optional[str] = None,
    promo_code: Optional[str] = None,
    api_key: Optional[str] = None,
    provider: str = "auto",
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    category: str = "general",
) -> Dict[str, Any]:
    """
    Unified AI Metadata Dispatcher:
    Supports Gemini, Groq, OpenAI, Claude, DeepSeek, Ollama (Local), OpenRouter, Custom Endpoints.
    Guaranteed zero-crash fallback to Smart Offline Heuristics engine.
    """
    clean_key = (api_key or "").strip()
    clean_provider = (provider or "auto").lower().strip()
    target_category = category or "general"

    # 1. Resolve Provider when set to 'auto'
    if clean_provider == "auto":
        if clean_key.startswith("gsk_"):
            clean_provider = "groq"
        elif clean_key.startswith("sk-ant-"):
            clean_provider = "claude"
        elif clean_key.startswith("sk-or-"):
            clean_provider = "openrouter"
        elif clean_key.startswith("sk-"):
            clean_provider = "openai"
        elif clean_key.startswith("AIza"):
            clean_provider = "gemini"
        elif base_url and ("11434" in base_url or "ollama" in base_url.lower()):
            clean_provider = "ollama"
        elif is_ollama_running():
            clean_provider = "ollama"
        elif clean_key:
            clean_provider = "gemini"
        else:
            clean_provider = "offline"

    # 2. Dispatch to designated provider with seamless error-handling
    try:
        if clean_provider == "gemini":
            if not clean_key:
                raise ValueError("Gemini API key is required.")
            return generate_with_gemini_api(
                api_key=clean_key,
                clip_title=clip_title,
                win_amount=win_amount,
                streamer=streamer,
                transcript=transcript,
                promo_code=promo_code,
                category=target_category,
                model=model,
            )

        elif clean_provider == "groq":
            if not clean_key:
                raise ValueError("Groq API key is required.")
            return generate_with_openai_compatible(
                api_key=clean_key,
                base_url="https://api.groq.com/openai/v1",
                model=model or "llama-3.3-70b-versatile",
                clip_title=clip_title,
                win_amount=win_amount,
                streamer=streamer,
                transcript=transcript,
                promo_code=promo_code,
                category=target_category,
                provider_label="Groq",
            )

        elif clean_provider == "claude":
            if not clean_key:
                raise ValueError("Anthropic Claude API key is required.")
            return generate_with_claude_api(
                api_key=clean_key,
                clip_title=clip_title,
                win_amount=win_amount,
                streamer=streamer,
                transcript=transcript,
                promo_code=promo_code,
                category=target_category,
                model=model or "claude-3-5-haiku-20241022",
            )

        elif clean_provider == "openai":
            if not clean_key:
                raise ValueError("OpenAI API key is required.")
            return generate_with_openai_compatible(
                api_key=clean_key,
                base_url="https://api.openai.com/v1",
                model=model or "gpt-4o-mini",
                clip_title=clip_title,
                win_amount=win_amount,
                streamer=streamer,
                transcript=transcript,
                promo_code=promo_code,
                category=target_category,
                provider_label="OpenAI",
            )

        elif clean_provider == "deepseek":
            if not clean_key:
                raise ValueError("DeepSeek API key is required.")
            return generate_with_openai_compatible(
                api_key=clean_key,
                base_url=base_url or "https://api.deepseek.com/v1",
                model=model or "deepseek-chat",
                clip_title=clip_title,
                win_amount=win_amount,
                streamer=streamer,
                transcript=transcript,
                promo_code=promo_code,
                category=target_category,
                provider_label="DeepSeek",
            )

        elif clean_provider == "openrouter":
            if not clean_key:
                raise ValueError("OpenRouter API key is required.")
            return generate_with_openai_compatible(
                api_key=clean_key,
                base_url=base_url or "https://openrouter.ai/api/v1",
                model=model or "meta-llama/llama-3.1-8b-instruct:free",
                clip_title=clip_title,
                win_amount=win_amount,
                streamer=streamer,
                transcript=transcript,
                promo_code=promo_code,
                category=target_category,
                provider_label="OpenRouter",
            )

        elif clean_provider == "ollama":
            ollama_url = base_url or "http://localhost:11434/v1"
            return generate_with_openai_compatible(
                api_key=clean_key or "ollama",
                base_url=ollama_url,
                model=model or "llama3",
                clip_title=clip_title,
                win_amount=win_amount,
                streamer=streamer,
                transcript=transcript,
                promo_code=promo_code,
                category=target_category,
                provider_label="Ollama Local",
            )

        elif clean_provider == "custom":
            if not base_url:
                raise ValueError("Base URL is required for custom endpoint.")
            return generate_with_openai_compatible(
                api_key=clean_key or "custom",
                base_url=base_url,
                model=model or "local-model",
                clip_title=clip_title,
                win_amount=win_amount,
                streamer=streamer,
                transcript=transcript,
                promo_code=promo_code,
                category=target_category,
                provider_label="Custom Endpoint",
            )

    except Exception as exc:
        print(f"Notice: {clean_provider} generation error ({exc}). Falling back to Offline Smart Copywriter.")

    # Guaranteed fallback
    return generate_offline_shorts_copy(
        clip_title=clip_title,
        win_amount=win_amount,
        streamer=streamer,
        transcript=transcript,
        promo_code=promo_code,
        category=target_category,
    )


_SAFE_TITLE_COUNTER = 0


def generate_safe_metadata(
    streamer_name: Optional[str] = None,
    detected_win: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Metadata & Title Spinner for Anti-Shadowban Compliance:
    - Rotates between 3 dynamic, high-CTR title formulas.
    - Appends 3 non-spammy, algorithm-compliant hashtags (#gaming, #streamerhighlights, #epicmoments).
    - Strictly avoids blacklisted tags like #casino, #deposit, #gambling, or #bet.
    """
    global _SAFE_TITLE_COUNTER
    name = (streamer_name or "").strip() or "Streamer"

    raw_highlight = (detected_win or "").strip()
    if raw_highlight:
        if re.match(r"^\d+(?:\.\d+)?$", raw_highlight):
            try:
                highlight = f"${float(raw_highlight):,.0f}"
            except Exception:
                highlight = raw_highlight.upper()
        else:
            highlight = raw_highlight.upper()
    else:
        highlight = "INSANE HIGHLIGHT"

    # 3 Dynamic High-CTR Title Formulas
    formulas = [
        f"NO WAY HE HIT THIS! 😱🔥 ({highlight}) #shorts",
        f"{name.upper()} Reaction Is Completely Unhinged! 💀 ({highlight}) #shorts",
        f"The Luckiest Moment In Live Streaming History?! 🤯 ({highlight}) #shorts",
    ]

    selected_title = formulas[_SAFE_TITLE_COUNTER % len(formulas)]
    _SAFE_TITLE_COUNTER += 1

    safe_hashtags = ["#gaming", "#streamerhighlights", "#epicmoments"]

    # Blacklist assertion
    blacklisted = {"#casino", "#deposit", "#gambling", "#bet", "#wager", "#slots", "#crypto"}
    cleaned_hashtags = [h for h in safe_hashtags if h.lower() not in blacklisted]

    desc_1 = (
        f"🎮 Unbelievable live moment from {name}! Watch until the very end!\n\n"
        f"👉 Drop a comment with your craziest clutch or lucky moment! 👇\n"
        f"🔔 Subscribe for daily stream highlights!\n\n"
        f"{' '.join(cleaned_hashtags)}"
    )
    desc_2 = (
        f"Did you expect this to happen?! Let me know below! 👇\n\n"
        f"✨ Creator: {name}\n\n"
        f"📌 Subscribe for more epic plays and funny reactions!\n\n"
        f"{' '.join(cleaned_hashtags)}"
    )
    desc_3 = (
        f"Top streamer highlight featuring {name}.\n\n"
        f"🚀 Daily shorts, unforgettable live moments, and crazy reactions.\n"
        f"🔔 Like and subscribe for more!\n\n"
        f"{' '.join(cleaned_hashtags)}"
    )

    return {
        "title": selected_title,
        "titles": formulas,
        "descriptions": [desc_1, desc_2, desc_3],
        "description": desc_1,
        "hashtags": cleaned_hashtags,
        "streamer": name,
        "detected_win": highlight,
        "safe_compliance": True,
    }


def generate_viral_hooks(
    clip_title: str = "",
    streamer: Optional[str] = None,
    category: str = "general",
) -> List[str]:
    """
    Generates high-CTR engagement hooks tailored for YouTube Shorts and TikTok overlays.
    Applies proven viral psychology: Curiosity Gaps, Cliffhangers, Extreme Stakes, and Relatable Shock.
    """
    name = (streamer or "He").strip()
    cat = (category or "general").lower()
    title = (clip_title or "").lower()

    if "slot" in cat or "casino" in cat or any(w in title for w in ["win", "spin", "multiplier", "$", "bonus"]):
        return [
            "WAIT TILL THE END... 😱",
            "HE WAS DOWN TO HIS LAST $10 🚨",
            "BIGGEST WIN OF THE YEAR?! 🤯",
            "WATCH HIS REAL REACTION 💀",
            "BRO COULD NOT BELIEVE THIS 😭",
            "1 IN A MILLION MULTIPLIER 🔥",
        ]
    elif any(w in cat or w in title for w in ["valorant", "cs2", "fortnite", "clutch", "gaming", "warzone", "ace", "ranked"]):
        return [
            "Worst *possible* timing 😳",
            "this gotta be *scripted* 💀",
            "BRO DID NOT JUST HIT THAT! 😱",
            "HOW DID HE SURVIVE THIS?! 🤯",
            "WAIT TILL THE LAST SECOND... 💀",
            f"WHY DID {name.upper()} DO THIS?! 😭",
            "THE CLEANEST CLUTCH EVER 🔥",
            "WATCH HIS HANDS SHAKE AT THE END 🎯",
        ]
    elif any(w in cat or w in title for w in ["chatting", "irl", "react", "drama", "podcast", "reddit"]):
        return [
            "Worst *possible* timing 😳",
            "this gotta be *scripted* 💀",
            "HE DID NOT MEAN TO SAY THIS 💀",
            "WAIT FOR HIS REAL REACTION 😳",
            "THINGS GOT OUT OF HAND FAST... 🚨",
            "BRO THOUGHT THE MIC WAS MUTED 😭",
            "I STILL CANNOT BELIEVE THIS HAPPENED 🤯",
            "DO NOT BLINK AT THE END 👀",
        ]
    else:
        return [
            "Worst *possible* timing 😳",
            "this gotta be *scripted* 💀",
            "WAIT TILL THE END... 😱",
            "BRO DID NOT EXPECT THIS 💀",
            "THIS ACTUALLY HAPPENED ON STREAM 🚨",
            "HE CANNOT BE SERIOUS 😭",
            "DO NOT SCROLL PAST THIS! 👀",
            "1 IN A MILLION MOMENT 🔥",
        ]


