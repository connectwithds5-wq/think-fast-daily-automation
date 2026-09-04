import json
import os
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]

VIDEO = ROOT / "output" / "think_fast_daily.mp4"
METADATA = ROOT / "output" / "metadata.json"

INSTAGRAM_ACCESS_TOKEN = os.environ.get(
    "INSTAGRAM_ACCESS_TOKEN"
)

INSTAGRAM_USER_ID = os.environ.get(
    "INSTAGRAM_USER_ID"
)

GRAPH_VERSION = "v25.0"


def require(value, name):
    if not value:
        raise RuntimeError(
            f"{name} secret is missing."
        )


require(
    INSTAGRAM_ACCESS_TOKEN,
    "INSTAGRAM_ACCESS_TOKEN"
)

require(
    INSTAGRAM_USER_ID,
    "INSTAGRAM_USER_ID"
)

if not VIDEO.exists():
    raise RuntimeError(
        f"Final video not found: {VIDEO}"
    )

if not METADATA.exists():
    raise RuntimeError(
        f"Metadata file not found: {METADATA}"
    )


# ============================================
# LOAD METADATA
# ============================================

with open(
    METADATA,
    "r",
    encoding="utf-8"
) as f:

    metadata = json.load(f)


title = metadata.get(
    "title",
    "Think Fast Daily Brain Quiz"
)

description = metadata.get(
    "description",
    ""
)

hashtags = metadata.get(
    "hashtags",
    []
)


# ============================================
# CREATE INSTAGRAM CAPTION
# ============================================

caption_parts = []

if description:
    caption_parts.append(
        description.strip()
    )

caption_parts.append(
    "🧠 THINK FAST DAILY"
)

caption_parts.append(
    "Can you get this one right? 👀"
)

caption_parts.append(
    "Comment your answer before the reveal! 👇"
)

caption_parts.append(
    "Follow @thinkfastdaily.v1 for daily brain challenges."
)

if hashtags:
    caption_parts.append(
        " ".join(hashtags)
    )

caption = "\n\n".join(
    caption_parts
)

caption = caption[:2200]


print("========================================")
print("THINK FAST DAILY - INSTAGRAM REEL")
print("========================================")
print("Title:", title)
print("Video:", VIDEO)
print("========================================")


# ============================================
# GITHUB PAGES PUBLIC VIDEO URL
# ============================================

pages_url = os.environ.get(
    "PAGES_VIDEO_URL"
)

require(
    pages_url,
    "PAGES_VIDEO_URL"
)

video_url = pages_url.rstrip("/") + \
    "/think_fast_daily.mp4"


print("")
print("Public video URL:")
print(video_url)


# ============================================
# STEP 1
# CREATE INSTAGRAM REEL CONTAINER
# ============================================

print("")
print("Creating Instagram Reel container...")


create_url = (
    f"https://graph.instagram.com/"
    f"{GRAPH_VERSION}/"
    f"{INSTAGRAM_USER_ID}/media"
)


response = requests.post(
    create_url,
    data={
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": INSTAGRAM_ACCESS_TOKEN
    },
    timeout=120
)


if response.status_code != 200:

    print("Instagram API response:")
    print(response.text)

    raise RuntimeError(
        "Instagram Reel container creation failed."
    )


container_data = response.json()

container_id = container_data.get("id")


if not container_id:

    print("Instagram response:")
    print(container_data)

    raise RuntimeError(
        "Instagram container ID was not returned."
    )


print("")
print("Instagram container created:")
print(container_id)


# ============================================
# STEP 2
# WAIT FOR VIDEO PROCESSING
# ============================================

print("")
print("Waiting for Instagram processing...")


status_url = (
    f"https://graph.instagram.com/"
    f"{GRAPH_VERSION}/"
    f"{container_id}"
)


finished = False

max_attempts = 36


for attempt in range(
    1,
    max_attempts + 1
):

    status_response = requests.get(
        status_url,
        params={
            "fields": "status_code,status",
            "access_token": INSTAGRAM_ACCESS_TOKEN
        },
        timeout=60
    )


    if status_response.status_code != 200:

        print(
            "Status API response:"
        )

        print(
            status_response.text
        )

        raise RuntimeError(
            "Unable to check Instagram processing status."
        )


    status_data = (
        status_response.json()
    )


    status_code = status_data.get(
        "status_code"
    )

    status_text = status_data.get(
        "status",
        ""
    )


    print(
        f"Attempt {attempt}/{max_attempts} "
        f"→ {status_code} {status_text}"
    )


    if status_code == "FINISHED":

        finished = True

        break


    if status_code in (
        "ERROR",
        "EXPIRED"
    ):

        raise RuntimeError(
            "Instagram video processing failed: "
            + json.dumps(
                status_data
            )
        )


    time.sleep(5)


if not finished:

    raise RuntimeError(
        "Instagram processing did not finish "
        "within the allowed time."
    )


# ============================================
# STEP 3
# PUBLISH REEL
# ============================================

print("")
print("Publishing Instagram Reel...")


publish_url = (
    f"https://graph.instagram.com/"
    f"{GRAPH_VERSION}/"
    f"{INSTAGRAM_USER_ID}/media_publish"
)


publish_response = requests.post(
    publish_url,
    data={
        "creation_id": container_id,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    },
    timeout=120
)


if publish_response.status_code != 200:

    print(
        "Instagram publish response:"
    )

    print(
        publish_response.text
    )

    raise RuntimeError(
        "Instagram Reel publishing failed."
    )


publish_data = (
    publish_response.json()
)

media_id = publish_data.get(
    "id"
)


if not media_id:

    print(
        "Instagram publish response:"
    )

    print(
        publish_data
    )

    raise RuntimeError(
        "Instagram media ID was not returned."
    )


print("")
print("========================================")
print("INSTAGRAM REEL SUCCESS")
print("========================================")
print("Instagram Media ID:", media_id)
print("Reel published successfully.")
print("========================================")
