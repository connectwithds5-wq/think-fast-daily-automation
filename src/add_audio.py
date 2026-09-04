import asyncio
import json
import os
import subprocess
import wave
from pathlib import Path

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


async def create_voice(text):

    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate="-5%",
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
# ============================================================

voice_script = f"""
{data["hook"]}

{data["question"]}

Option A: {data["options"]["A"]}.

Option B: {data["options"]["B"]}.

Option C: {data["options"]["C"]}.

Option D: {data["options"]["D"]}.

You have five seconds.

Five.

Four.

Three.

Two.

One.

The correct answer is {answer}.
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
# CREATE SOFT BACKGROUND MUSIC
# ============================================================

print("Generating background music...")


duration = 30
sample_rate = 44100

# Simple stereo WAV with subtle synthesized tones.
# No external copyrighted music.

import math
import struct


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


        # soft ambient tones

        freq1 = 110
        freq2 = 164.81
        freq3 = 220


        value = (
            math.sin(
                2 * math.pi * freq1 * t
            )
            * 0.035
            +
            math.sin(
                2 * math.pi * freq2 * t
            )
            * 0.018
            +
            math.sin(
                2 * math.pi * freq3 * t
            )
            * 0.012
        )


        # fade in/out

        fade_in = min(
            1.0,
            t / 2
        )

        fade_out = min(
            1.0,
            (duration - t) / 2
        )


        value *= fade_in * fade_out


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
# MERGE VIDEO + AUDIO
# ============================================================

print("Merging voice + music...")


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
        "[1:a]volume=1.0[voice];"
        "[2:a]volume=0.12[music];"
        "[voice][music]"
        "amix=inputs=2:"
        "duration=first:"
        "dropout_transition=2[a]",

        "-map",
        "0:v:0",

        "-map",
        "[a]",

        "-c:v",
        "copy",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-shortest",

        "-movflags",
        "+faststart",

        str(FINAL_VIDEO)
    ],
    check=True
)


print("========================================")
print("FINAL VIDEO READY")
print(FINAL_VIDEO)
print("========================================")
