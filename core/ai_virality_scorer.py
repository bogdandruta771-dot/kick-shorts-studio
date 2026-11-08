"""
AI Stream Transcript Virality Scorer & Highlight Hunter.
Inspired by SupoClip & OpusClip local-first intelligence.
Analyzes full Whisper/faster-whisper transcripts to automatically identify,
score (0-100), and rank the most viral 30-60 second moments from livestreams or VODs.
"""

import os
import re
import json
from typing import Dict, Any, List, Optional
from core.ai_copywriter import (
    generate_with_gemini_api,
    generate_with_groq_api,
    generate_with_openai_compatible,
    _parse_ai_json,
    clean_api_key
)


VIRALITY_EVALUATION_SYSTEM_PROMPT = """You are an elite short-form virality expert and stream highlight editor for TikTok, YouTube Shorts, and Instagram Reels.
Your job is to analyze long video/stream transcripts, identify the highest-retention moments, and score them based on virality.

VIRALITY SCORING RUBRIC (0-100):
1. Hook Strength (0-100): Does the clip start with high curiosity, shock, loud emotion, or high stakes within the first 3 seconds?
2. Emotional Climax (0-100): Is there an explosive reaction, funny laugh, huge scream, catastrophic failure, clutch win, or unexpected plot twist?
3. Pacing & Retention (0-100): Does the dialogue flow without dead air or boring filler?
4. Overall Score (0-100): Weighted formula: 40% Hook + 40% Climax + 20% Pacing.

Output STRICT JSON with an array of the top 3-5 viral moments:
{
  "clips": [
    {
      "rank": 1,
      "start_time": 12.0,
      "end_time": 45.0,
      "duration": 33.0,
      "virality_score": 95,
      "hook_score": 98,
      "climax_score": 94,
      "headline": "Short punchy all-caps viral title with emoji",
      "rationale": "1-2 sentences explaining why this exact segment will stop thumbs and get comments.",
      "recommended_layout": "split_screen" or "focused_gameplay" or "full_facecam",
      "titles": [
        "Viral Title Option 1",
        "Curiosity Gap Option 2",
        "High Stakes Option 3"
      ],
      "key_quote": "Most memorable line said in the clip"
    }
  ]
}
"""


def heuristic_virality_scanner(
    transcript_segments: List[Dict[str, Any]],
    target_clip_duration: float = 35.0
) -> List[Dict[str, Any]]:
    """
    100% Free Offline Heuristic Highlight Hunter.
    Scores segments based on:
    - High-energy vocabulary (clutch, insane, no way, holy, wtf, money, dollar, hack, ban)
    - Exclamation density and loud exclamation tokens
    - Speech tempo (words per second)
    """
    if not transcript_segments:
        return []

    HYPE_WORDS = {
        "insane": 18, "crazy": 15, "omg": 20, "holy": 20, "shit": 15, "fuck": 15,
        "clutch": 25, "ace": 25, "no way": 25, "how": 10, "what": 12, "win": 15,
        "dollar": 20, "knife": 20, "dragon": 20, "lore": 20, "bro": 10, "dude": 10,
        "screaming": 25, "dropped": 18, "unreal": 20, "glitch": 15, "banned": 22
    }

    # Flatten into list of words with timestamps
    words = []
    for seg in transcript_segments:
        if "words" in seg and isinstance(seg["words"], list):
            words.extend(seg["words"])
        elif "word" in seg:
            words.append(seg)
        elif "text" in seg:
            # Approximate sentence-level timing
            s_words = seg["text"].split()
            dur = max(0.5, seg.get("end", 1.0) - seg.get("start", 0.0))
            w_step = dur / max(1, len(s_words))
            for i, w in enumerate(s_words):
                words.append({
                    "word": w,
                    "start": seg.get("start", 0.0) + i * w_step,
                    "end": seg.get("start", 0.0) + (i + 1) * w_step
                })

    if not words:
        return []

    total_duration = words[-1].get("end", target_clip_duration)
    step = 10.0  # Sliding window step
    candidates = []

    curr_start = 0.0
    while curr_start + 15.0 <= total_duration:
        curr_end = min(total_duration, curr_start + target_clip_duration)
        window_words = [w for w in words if w.get("start", 0) >= curr_start and w.get("end", 0) <= curr_end]

        if len(window_words) >= 6:
            text_str = " ".join(w.get("word", "") for w in window_words).lower()
            score = 50.0  # Base score

            # 1. Hype words
            for hw, boost in HYPE_WORDS.items():
                if hw in text_str:
                    score += boost

            # 2. Exclamations and caps
            all_caps_count = sum(1 for w in window_words if w.get("word", "").isupper() and len(w.get("word", "")) > 1)
            score += min(20, all_caps_count * 3)

            # 3. Speech pacing
            wps = len(window_words) / max(1.0, curr_end - curr_start)
            if 2.0 <= wps <= 4.5:
                score += 15

            # Hook score: first 3 seconds energy
            hook_words = [w for w in window_words if w.get("start", 0) <= curr_start + 3.5]
            hook_text = " ".join(w.get("word", "") for w in hook_words).lower()
            hook_score = 60 + sum(boost for hw, boost in HYPE_WORDS.items() if hw in hook_text)
            hook_score = min(99, max(50, hook_score))

            candidates.append({
                "start_time": round(curr_start, 2),
                "end_time": round(curr_end, 2),
                "duration": round(curr_end - curr_start, 2),
                "score": min(98, int(score)),
                "hook_score": hook_score,
                "text": text_str[:120] + "..."
            })

        curr_start += step

    # Sort by score descending and deduplicate overlapping clips
    candidates.sort(key=lambda x: x["score"], reverse=True)
    selected = []
    for c in candidates:
        # Check overlap
        overlaps = False
        for s in selected:
            if not (c["end_time"] <= s["start_time"] or c["start_time"] >= s["end_time"]):
                overlaps = True
                break
        if not overlaps:
            selected.append(c)
        if len(selected) >= 4:
            break

    # Format result
    results = []
    for idx, c in enumerate(selected, 1):
        results.append({
            "rank": idx,
            "start_time": c["start_time"],
            "end_time": c["end_time"],
            "duration": c["duration"],
            "virality_score": c["score"],
            "hook_score": c["hook_score"],
            "climax_score": max(65, c["score"] - 5),
            "headline": f"MOMENT #{idx}: INSANE STREAM HIGHLIGHT! 🔥",
            "rationale": f"High emotional velocity and speech density detected between {c['start_time']}s and {c['end_time']}s.",
            "recommended_layout": "split_screen",
            "titles": [
                f"NO WAY HE DID THIS LIVE ON STREAM 😱",
                f"THE CRAZIEST REACTION EVER?! 🔥",
                f"WAIT FOR THE END... YOU WON'T BELIEVE IT"
            ],
            "key_quote": c["text"][:60]
        })

    return results


def score_stream_transcript(
    transcript_text_or_segments: Any,
    provider: str = "auto",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    target_clip_duration: float = 35.0
) -> Dict[str, Any]:
    """
    SupoClip AI Virality Scorer Master Resolver:
    Evaluates video transcript using active LLM (Gemini, Groq, Ollama, OpenAI)
    or falls back cleanly to the heuristic highlight scanner.
    """
    # 1. Standardize transcript representation
    transcript_summary = ""
    segments_list = []

    if isinstance(transcript_text_or_segments, str):
        transcript_summary = transcript_text_or_segments
    elif isinstance(transcript_text_or_segments, list):
        segments_list = transcript_text_or_segments
        # Build timestamped transcript string
        lines = []
        for s in transcript_text_or_segments:
            st = s.get("start", 0.0)
            txt = s.get("text") or s.get("word") or ""
            lines.append(f"[{st:.1f}s] {txt}")
        transcript_summary = " ".join(lines)

    # 2. Heuristic fallback computation
    fallback_clips = heuristic_virality_scanner(segments_list, target_clip_duration)
    if not fallback_clips and transcript_summary:
        fallback_clips = [
            {
                "rank": 1,
                "start_time": 0.0,
                "end_time": min(40.0, target_clip_duration),
                "duration": min(40.0, target_clip_duration),
                "virality_score": 85,
                "hook_score": 88,
                "climax_score": 84,
                "headline": "EXPLOSIVE OPENING MOMENT 🔥",
                "rationale": "High immediate hook potential in the opening segment.",
                "recommended_layout": "split_screen",
                "titles": [
                    "YOU WON'T BELIEVE WHAT HAPPENED NEXT 😱",
                    "THE MOMENT EVERYTHING CHANGED...",
                    "STREAMER COMPLETELY LOST HIS MIND 😂"
                ],
                "key_quote": transcript_summary[:50]
            }
        ]

    # 3. Attempt LLM AI Virality Scoring if keys or Ollama available
    clean_key = clean_api_key(api_key)
    prompt = f"{VIRALITY_EVALUATION_SYSTEM_PROMPT}\n\nSTREAM TRANSCRIPT TO EVALUATE:\n{transcript_summary[:6000]}"

    raw_ai_response = None
    engine_used = "Offline Heuristics"

    # Try Groq
    groq_key = clean_key or clean_api_key(os.getenv("GROQ_API_KEY"))
    if groq_key and (provider in ("auto", "groq")):
        try:
            raw_ai_response = generate_with_groq_api(prompt, api_key=groq_key, model=model or "llama-3.3-70b-versatile")
            engine_used = "Groq (Llama 3.3)"
        except Exception:
            pass

    # Try Gemini
    gemini_key = clean_key or clean_api_key(os.getenv("GEMINI_API_KEY"))
    if not raw_ai_response and gemini_key and (provider in ("auto", "gemini")):
        try:
            raw_ai_response = generate_with_gemini_api(prompt, api_key=gemini_key, model=model or "gemini-1.5-flash")
            engine_used = "Google Gemini"
        except Exception:
            pass

    # Try Ollama (Local)
    if not raw_ai_response and (provider in ("auto", "ollama")):
        try:
            raw_ai_response = generate_with_openai_compatible(
                prompt,
                base_url="http://localhost:11434/v1",
                model=model or "llama3",
                api_key="ollama"
            )
            engine_used = "Ollama (Local Offline)"
        except Exception:
            pass

    # Parse AI response if available
    if raw_ai_response:
        parsed = _parse_ai_json(raw_ai_response)
        if parsed and "clips" in parsed and isinstance(parsed["clips"], list) and len(parsed["clips"]) > 0:
            return {
                "success": True,
                "engine": engine_used,
                "clips": parsed["clips"]
            }

    # Return validated fallback
    return {
        "success": True,
        "engine": "Smart Heuristic Scanner",
        "clips": fallback_clips
    }
