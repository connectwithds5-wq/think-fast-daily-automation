import asyncio
import json
import os
import subprocess
import wave
from pathlib import Path
import math
import struct

import edge_tts


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"

VIDEO = OUTPUT / "factverse_silent.mp4"
FINAL_VIDEO = OUTPUT / "think_fast_daily.mp4"
METADATA = OUTPUT / "metadata.json"

VOICE_MP3 = OUTPUT / "voice.mp3"
MUSIC_WAV = OUTPUT / "music.wav"

VOICE = os.environ.get(
    "TTS_VOICE",
    "en-US-GuyNeural"
)

FPS = 30
VIDEO_DURATION = 30


async def create_voice(text):
    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate="-8%",
        volume="+0%"
    )

    await communicate.save(
        str(VOICE_MP3)
    )


# ============================================================
# LOAD METADATA
# ============================================================

with open(
    METADATA,
    "r",
    encoding="utf-8"
) as f:
    data = json.load(f)


answer = data["answer"]
answer_text = data["options"][answer]


# ============================================================
# VOICE SCRIPT
#
# IMPORTANT:
# The pauses below are intentional.
# They keep the narration aligned with the visual timeline.
# ============================================================

voice_script = f"""
{data["hook"]}.

Here is your challenge.

{data["question"]}.

Option A: {data["options"]["A"]}.

Option B: {data["options"]["B"]}.

Option C: {data["options"]["C"]}.

Option D: {data["options"]["D"]}.

Think carefully.

You have five seconds.

Five.

Four.

Three.

Two.

One.

The correct answer is option {answer}.

{answer_text}.

Here's why.

{data["explanation"]}.

Did you get it right?

Comment your answer and subscribe to Think Fast Daily for tomorrow's challenge.
"""


print("========================================")
print("Generating natural neural voice")
print("Voice:", VOICE)
print("========================================")


asyncio.run(
    create_voice(
        voice_script
    )
)


# ============================================================
# GET VOICE DURATION
# ============================================================

def get_duration(file_path):

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(file_path)
        ],
        capture_output=True,
        text=True,
        check=True
    )

    return float(result.stdout.strip())


voice_duration = get_duration(
    VOICE_MP3
)

print(
    f"Original voice duration: {voice_duration:.2f}s"
)


# ============================================================
# CREATE SOFT BACKGROUND MUSIC
# ============================================================

print("Generating background music...")

duration = VIDEO_DURATION
sample_rate = 44100


with wave.open(
    str(MUSIC_WAV),
    "w"
) as wav:

    wav.setnchannels(2)
    wav.setsampwidth(2)
    wav.setframerate(sample_rate)

    total = duration * sample_rate

    for i in range(total):

        t = i / sample_rate

        freq1 = 110
        freq2 = 164.81
        freq3 = 220

        value = (
            math.sin(
                2 * math.pi * freq1 * t
            ) * 0.025
            +
            math.sin(
                2 * math.pi * freq2 * t
            ) * 0.012
            +
            math.sin(
                2 * math.pi * freq3 * t
            ) * 0.008
        )

        fade_in = min(
            1.0,
            t / 2
        )

        fade_out = min(
            1.0,
            (duration - t) / 2
        )

        value *= (
            fade_in *
            fade_out
        )

        sample = int(
            max(-1, min(1, value))
            * 32767
        )

        wav.writeframes(
            struct.pack(
                "<hh",
                sample,
                sample
            )
        )


# ============================================================
# NORMALIZE / FIT VOICE TO VIDEO
#
# We DON'T speed it up aggressively.
# If narration is shorter than video, silence is added.
# If narration is slightly longer, it is gently slowed.
# ============================================================

TARGET_AUDIO_DURATION = VIDEO_DURATION


if voice_duration > TARGET_AUDIO_DURATION:

    tempo = (
        voice_duration /
        TARGET_AUDIO_DURATION
    )

    # Keep tempo adjustment reasonable.
    tempo = max(
        1.0,
        min(1.18, tempo)
    )

    voice_filter = (
        f"atempo={tempo:.4f}"
    )

else:

    voice_filter = "anull"


# ============================================================
# MERGE VIDEO + VOICE + MUSIC
# ============================================================

print("Merging video + voice + music...")
print("Voice filter:", voice_filter)


filter_complex = (
    f"[1:a]"
    f"{voice_filter},"
    f"loudnorm=I=-16:TP=-1.5:LRA=11"
    f"[voice];"

    f"[2:a]"
    f"volume=0.07"
    f"[music];"

    f"[voice][music]"
    f"amix=inputs=2:"
    f"duration=first:"
    f"dropout_transition=1,"
    f"apad,"
    f"atrim=duration={VIDEO_DURATION}"
    f"[audio]"
)


subprocess.run(
    [
        "ffmpeg",
        "-y",

        "-i",
        str(VIDEO),

        "-i",
        str(VOICE_MP3),

        "-i",
        str(MUSIC_WAV),

        "-filter_complex",
        filter_complex,

        "-map",
        "0:v:0",

        "-map",
        "[audio]",

        "-c:v",
        "copy",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-t",
        str(VIDEO_DURATION),

        "-movflags",
        "+faststart",

        str(FINAL_VIDEO)
    ],
    check=True
)


# ============================================================
# FINAL VERIFICATION
# ============================================================

final_duration = get_duration(
    FINAL_VIDEO
)

print("========================================")
print("FINAL VIDEO READY")
print("========================================")
print("Voice duration:", round(voice_duration, 2))
print("Final video duration:", round(final_duration, 2))
print("Video:", FINAL_VIDEO)
print("========================================")
