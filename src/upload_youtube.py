import json
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


ROOT = Path(__file__).resolve().parents[1]

VIDEO = ROOT / "output" / "think_fast_daily.mp4"
METADATA = ROOT / "output" / "metadata.json"


OAUTH_JSON = os.environ.get(
    "YOUTUBE_OAUTH_JSON"
)


if not OAUTH_JSON:

    raise RuntimeError(
        "YOUTUBE_OAUTH_JSON secret is missing."
    )


oauth = json.loads(
    OAUTH_JSON
)


required = [
    "client_id",
    "client_secret",
    "refresh_token"
]


for field in required:

    if not oauth.get(field):

        raise RuntimeError(
            f"YOUTUBE_OAUTH_JSON missing: {field}"
        )


credentials = Credentials(
    token=None,

    refresh_token=oauth["refresh_token"],

    token_uri="https://oauth2.googleapis.com/token",

    client_id=oauth["client_id"],

    client_secret=oauth["client_secret"],

    scopes=[
        "https://www.googleapis.com/auth/youtube.upload"
    ]
)


youtube = build(
    "youtube",
    "v3",
    credentials=credentials
)


with open(
    METADATA,
    "r",
    encoding="utf-8"
) as f:

    data = json.load(f)


title = data["title"]

description = data["description"]

hashtags = data.get(
    "hashtags",
    []
)


# Add hashtags naturally to description.

description = (
    description
    + "\n\n"
    + " ".join(hashtags)
)


tags = data.get(
    "keywords",
    []
)


request_body = {
    "snippet": {
        "title": title[:100],
        "description": description[:5000],
        "tags": tags[:30],
        "categoryId": "24"
    },

    "status": {
        "privacyStatus": os.environ.get(
            "YOUTUBE_PRIVACY_STATUS",
            "public"
        ),

        "selfDeclaredMadeForKids": False
    }
}


print("========================================")
print("Uploading THINK FAST DAILY Short")
print("Title:", title)
print("========================================")


media = MediaFileUpload(
    str(VIDEO),
    mimetype="video/mp4",
    resumable=True
)


request = youtube.videos().insert(
    part="snippet,status",
    body=request_body,
    media_body=media
)


response = None


while response is None:

    status, response = request.next_chunk()

    if status:

        print(
            "Upload progress:",
            int(status.progress() * 100),
            "%"
        )


print("========================================")
print("YOUTUBE UPLOAD SUCCESS")
print("Video ID:", response["id"])
print(
    "https://www.youtube.com/watch?v="
    + response["id"]
)
print("========================================")
