"""Build a data-backed content and posting-time strategy for THINK FAST DAILY."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "think_fast_history.json"
STRATEGY = ROOT / "think_fast_strategy.json"
MAX_VIDEOS = 50


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def youtube_data():
    import requests
    key = os.getenv("YOUTUBE_API_KEY", "").strip()
    channel_id = os.getenv("YOUTUBE_CHANNEL_ID", "").strip()
    if not key or not channel_id:
        return []
    base = "https://www.googleapis.com/youtube/v3"
    r = requests.get(base + "/channels", params={"part": "contentDetails", "id": channel_id, "key": key}, timeout=30)
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        return []
    uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    r = requests.get(base + "/playlistItems", params={"part": "contentDetails", "playlistId": uploads, "maxResults": MAX_VIDEOS, "key": key}, timeout=30)
    r.raise_for_status()
    ids = [x["contentDetails"]["videoId"] for x in r.json().get("items", [])]
    if not ids:
        return []
    r = requests.get(base + "/videos", params={"part": "snippet,statistics,contentDetails", "id": ",".join(ids), "key": key}, timeout=30)
    r.raise_for_status()
    out = []
    for x in r.json().get("items", []):
        s = x.get("statistics", {})
        sn = x.get("snippet", {})
        out.append({
            "video_id": x.get("id"),
            "title": sn.get("title", ""),
            "published_at": sn.get("publishedAt"),
            "views": int(s.get("viewCount", 0)),
            "likes": int(s.get("likeCount", 0)),
            "comments": int(s.get("commentCount", 0)),
            "description_excerpt": sn.get("description", "")[:300],
        })
    return sorted(out, key=lambda x: x.get("published_at") or "", reverse=True)


def build_prompt(videos, history):
    return f"""
You are the performance strategist for THINK FAST DAILY, a YouTube Shorts quiz/brain-challenge channel.
Analyze ONLY the supplied performance data. Do not invent watch time, retention, swipe rate, or subscriber data.
Use views, likes, comments, titles, publish timestamps and question/category history when available.
Identify repeatable winning quiz formats, topics, hooks, visual styles, difficulty and posting times.
Penalize repeated questions and weak engagement. The next videos must be fresh variations, not copies.
Prefer simple, instantly understandable A/B/C/D challenges with a strong curiosity gap and a visual clue.

IMPORTANT POSTING-TIME RULE:
Choose the best TWO posting times based on the supplied performance timestamps. Return exact UTC hour/minute integers.
These values are used to automatically rewrite the GitHub Actions cron schedule for the next runs.
If evidence is weak, choose conservative times from the strongest observed posting cluster and set confidence low.

Return ONLY JSON in exactly this shape:
{{
  "generated_at":"",
  "confidence":"low|medium|high",
  "overall_summary":"",
  "winning_patterns":[{{"pattern":"","evidence":"","action":""}}],
  "improvements":[{{"pattern":"","evidence":"","action":""}}],
  "best_posting_windows":[{{"window":"","hour_utc":0,"minute_utc":0,"reason":"","confidence":"low|medium|high"}}],
  "next_best_quiz_directions":[{{"priority":1,"topic":"","hook":"","visual_type":"","reason":"","confidence":"low|medium|high"}}],
  "avoid_or_limit":[{{"item":"","reason":""}}]
}}

YOUTUBE PERFORMANCE:
{json.dumps(videos, ensure_ascii=False, indent=2)}

QUESTION HISTORY:
{json.dumps(history[-80:], ensure_ascii=False, indent=2)}
"""


def main():
    history = load(HISTORY, [])
    videos = youtube_data()
    source = "youtube_public_analytics" if videos else "question_history_fallback"
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing")
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
        contents=build_prompt(videos, history),
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    text = (response.text or "").strip().removeprefix("```json").removesuffix("```").strip()
    strategy = json.loads(text)
    strategy["generated_at"] = datetime.now(timezone.utc).isoformat()
    strategy["data_source"] = source
    strategy["data_points"] = len(videos)
    save(STRATEGY, strategy)
    print("THINK FAST strategy updated", source, len(videos))


if __name__ == "__main__":
    main()
