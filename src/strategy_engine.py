"""Build THINK FAST DAILY strategy from public YouTube data and owner Analytics."""
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from google import genai
from google.genai import types
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "think_fast_history.json"
STRATEGY = ROOT / "think_fast_strategy.json"
MAX_VIDEOS = 50
ANALYTICS_VIDEO_LIMIT = 20
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def youtube_public_data():
    key = os.getenv("YOUTUBE_API_KEY", "").strip()
    channel_id = os.getenv("YOUTUBE_CHANNEL_ID", "").strip()
    if not key or not channel_id:
        return []
    base = "https://www.googleapis.com/youtube/v3"
    r = requests.get(base + "/channels", params={"part": "contentDetails", "id": channel_id, "key": key}, timeout=30)
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        raise RuntimeError("YouTube channel not found. Check YOUTUBE_CHANNEL_ID.")
    uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    r = requests.get(base + "/playlistItems", params={"part": "contentDetails", "playlistId": uploads, "maxResults": MAX_VIDEOS, "key": key}, timeout=30)
    r.raise_for_status()
    ids = [x["contentDetails"]["videoId"] for x in r.json().get("items", []) if x.get("contentDetails", {}).get("videoId")]
    if not ids:
        return []
    r = requests.get(base + "/videos", params={"part": "snippet,statistics,contentDetails", "id": ",".join(ids[:50]), "key": key}, timeout=30)
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


def load_oauth_credentials():
    raw = os.environ.get("YOUTUBE_OAUTH_JSON", "").strip()
    if not raw:
        raise RuntimeError("YOUTUBE_OAUTH_JSON GitHub Secret is missing.")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("YOUTUBE_OAUTH_JSON is not valid JSON.") from exc
    missing = [k for k in ("client_id", "client_secret", "refresh_token") if not data.get(k)]
    if missing:
        raise RuntimeError("YOUTUBE_OAUTH_JSON is missing: " + ", ".join(missing))
    credentials = Credentials.from_authorized_user_info(data, YOUTUBE_SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials.valid:
        raise RuntimeError("YouTube OAuth credentials are invalid.")
    return credentials


def youtube_owner_analytics(videos):
    credentials = load_oauth_credentials()
    api = build("youtubeAnalytics", "v2", credentials=credentials, cache_discovery=False)
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=365)
    report = api.reports().query(
        ids="channel==MINE",
        startDate=start.isoformat(),
        endDate=today.isoformat(),
        dimensions="video",
        metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,shares,subscribersGained,subscribersLost",
        sort="-views",
        maxResults=200,
    ).execute()
    headers = [h["name"] for h in report.get("columnHeaders", [])]
    analytics = {}
    for row in report.get("rows", []):
        item = dict(zip(headers, row))
        video_id = item.pop("video", None)
        if video_id:
            analytics[video_id] = item

    retention = {}
    for video in videos[:ANALYTICS_VIDEO_LIMIT]:
        video_id = video.get("video_id")
        published = (video.get("published_at") or "")[:10]
        if not video_id or not published:
            continue
        try:
            rr = api.reports().query(
                ids="channel==MINE",
                startDate=published,
                endDate=today.isoformat(),
                dimensions="elapsedVideoTimeRatio",
                metrics="audienceWatchRatio,relativeRetentionPerformance",
                filters=f"video=={video_id}",
                sort="elapsedVideoTimeRatio",
                maxResults=200,
            ).execute()
            rh = [h["name"] for h in rr.get("columnHeaders", [])]
            points = [dict(zip(rh, row)) for row in rr.get("rows", [])]
            if points:
                retention[video_id] = points
        except Exception as exc:
            print(f"Retention unavailable for {video_id}: {exc}")
    return analytics, retention


def summarize_retention(points):
    if not points:
        return None
    sampled = []
    for point in points:
        try:
            ratio = float(point.get("elapsedVideoTimeRatio", 0))
            watch = float(point.get("audienceWatchRatio", 0))
            relative = float(point.get("relativeRetentionPerformance", 0))
        except (TypeError, ValueError):
            continue
        if ratio <= 0.10 or abs(ratio - 0.25) < 0.02 or abs(ratio - 0.50) < 0.02 or abs(ratio - 0.75) < 0.02 or ratio >= 0.90:
            sampled.append({"video_progress": round(ratio, 3), "audience_watch_ratio": round(watch, 4), "relative_retention": round(relative, 4)})
    return sampled[:15]


def build_prompt(videos, analytics, retention, history):
    compact = []
    for video in videos:
        row = {
            "title": video["title"], "published_at": video["published_at"],
            "views": video["views"], "likes": video["likes"], "comments": video["comments"],
        }
        if video["video_id"] in analytics:
            row["youtube_studio"] = analytics[video["video_id"]]
        rp = summarize_retention(retention.get(video["video_id"], []))
        if rp:
            row["retention_curve"] = rp
        compact.append(row)
    return f"""
You are the performance strategist for THINK FAST DAILY, a YouTube Shorts quiz/brain-challenge channel.
Analyze ONLY the supplied YouTube performance data and question history. Never invent metrics.
When owner Analytics are present, use average view duration, average percentage watched, estimated watch time,
likes/comments/shares, subscriber conversion and retention curves. Use retention curves to identify early drop-offs,
strong hold zones and payoff timing.
Identify repeatable winning quiz formats, topics, hooks, visual styles, difficulty and posting times.
Penalize repeated questions and weak engagement. Recommend fresh variations, not copies.
Prefer instantly understandable A/B/C/D challenges with a strong curiosity gap and visual clue.
Choose TWO distinct best posting times from observed publish timestamps and performance. Return exact UTC hour/minute integers,
at least 30 minutes apart. If evidence is weak, choose conservative observed clusters and set confidence low.

Return ONLY valid JSON in exactly this shape:
{{
  "generated_at":"",
  "confidence":"low|medium|high",
  "analytics_source":"youtube_analytics_api",
  "overall_summary":"",
  "winning_patterns":[{{"pattern":"","evidence":"","action":""}}],
  "improvements":[{{"pattern":"","evidence":"","action":""}}],
  "retention_insights":[{{"video_pattern":"","drop_or_strength":"","evidence":"","action":""}}],
  "best_posting_windows":[{{"window":"","hour_utc":0,"minute_utc":0,"reason":"","confidence":"low|medium|high"}}],
  "next_best_quiz_directions":[{{"priority":1,"topic":"","hook":"","visual_type":"","reason":"","confidence":"low|medium|high"}}],
  "avoid_or_limit":[{{"item":"","reason":""}}]
}}

YOUTUBE PERFORMANCE + OWNER ANALYTICS:
{json.dumps(compact, ensure_ascii=False, indent=2)}

QUESTION HISTORY:
{json.dumps(history[-80:], ensure_ascii=False, indent=2)}
"""


def generate_strategy(client, model, prompt):
    response = client.models.generate_content(model=model, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
    text = (response.text or "").strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(text)


def is_transient(message):
    text = str(message).lower()
    return any(token in text for token in ("408", "429", "500", "502", "503", "504", "unavailable", "high demand", "resource_exhausted", "rate limit", "quota", "timed out", "timeout", "deadline exceeded", "temporarily unavailable"))


def main():
    history = load(HISTORY, [])
    videos = youtube_public_data()
    if not videos:
        raise RuntimeError("No YouTube performance data found. Check YOUTUBE_API_KEY and YOUTUBE_CHANNEL_ID.")
    analytics, retention = youtube_owner_analytics(videos)
    for video in videos:
        if video["video_id"] in analytics:
            video["owner_analytics"] = analytics[video["video_id"]]
        rp = summarize_retention(retention.get(video["video_id"], []))
        if rp:
            video["retention_curve"] = rp
    source = "youtube_analytics_api"
    save(HISTORY, {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "analytics_source": source,
        "videos": videos[:MAX_VIDEOS],
    })

    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing")
    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=12000, retry_options=types.HttpRetryOptions(attempts=1)))
    requested = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
    models = []
    for model in [requested, "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]:
        if model and model not in models:
            models.append(model)
    prompt = build_prompt(videos[:MAX_VIDEOS], analytics, retention, history)
    strategy = None
    last_error = None
    for model in models:
        try:
            print(f"Trying Gemini strategy model: {model}")
            strategy = generate_strategy(client, model, prompt)
            if not isinstance(strategy, dict):
                raise RuntimeError("Gemini strategy response was not a JSON object")
            strategy["model_used"] = model
            print(f"Strategy SUCCESS with {model}")
            break
        except Exception as exc:
            last_error = exc
            print(f"Gemini strategy model failed: {model}: {exc}")
            if not is_transient(exc):
                message = str(exc).lower()
                if any(token in message for token in ("401", "403", "api key", "authentication", "permission denied")):
                    raise
                print("Non-transient model response error; trying next model for resilience.")
    if strategy is None:
        raise RuntimeError(f"All Gemini strategy models failed. Last error: {last_error}")
    strategy["generated_at"] = datetime.now(timezone.utc).isoformat()
    strategy["data_source"] = source
    strategy["analytics_source"] = source
    strategy["data_points"] = len(videos)
    strategy["owner_analytics_videos"] = len(analytics)
    strategy["retention_videos"] = len(retention)
    save(STRATEGY, strategy)
    print("THINK FAST strategy updated")
    print("Videos analyzed:", len(videos))
    print("Analytics source:", source)
    print("Owner analytics videos:", len(analytics))
    print("Retention reports:", len(retention))
    print("Gemini model:", strategy["model_used"])


if __name__ == "__main__":
    main()
