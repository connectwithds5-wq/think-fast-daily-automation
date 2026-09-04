import asyncio
import json
import math
import os
import struct
import subprocess
import wave
from pathlib import Path

import edge_tts


ROOT = Path(__file__).resolve().parents[1]

OUTPUT = ROOT / "output"

VIDEO = OUTPUT / "factverse_silent.mp4"
FINAL_VIDEO = OUTPUT / "think_fast_daily.mp4"
METADATA = OUTPUT / "metadata.json"

VOICE_DIR = OUTPUT / "voice_segments"

VOICE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

VOICE_WAV = OUTPUT / "voice_timed.wav"
MUSIC_WAV = OUTPUT / "music.wav"


# ============================================================
# SETTINGS
# ============================================================

VOICE = os.environ.get(
    "TTS_VOICE",
    "en-US-GuyNeural"
)

VIDEO_DURATION = 35.0


# ============================================================
# EXACT TIMELINE
# ============================================================

SEGMENTS = [

    ("01_hook", 3.0),

    ("02_question_options", 13.0),

    ("03_countdown", 5.0),

    ("04_answer", 4.0),

    ("05_explanation", 6.0),

    ("06_cta", 4.0),

]


# ============================================================
# TTS
# ============================================================

async def create_voice(
    text,
    output_file
):

    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate="+0%",
        volume="+0%"
    )

    await communicate.save(
        str(output_file)
    )


# ============================================================
# DURATION
# ============================================================

def get_duration(
    file_path
):

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

    return float(
        result.stdout.strip()
    )


# ============================================================
# ATEMPO
# ============================================================

def build_tempo_filter(
    speed
):

    filters = []

    remaining = speed

    while remaining > 2.0:

        filters.append(
            "atempo=2.0"
        )

        remaining /= 2.0


    while remaining < 0.5:

        filters.append(
            "atempo=0.5"
        )

        remaining /= 0.5


    filters.append(
        f"atempo={remaining:.6f}"
    )

    return ",".join(filters)


# ============================================================
# FIT AUDIO
# ============================================================

def fit_audio(
    input_file,
    output_file,
    target_duration
):

    source_duration = get_duration(
        input_file
    )

    if source_duration <= 0:

        raise RuntimeError(
            "Invalid source audio duration."
        )


    speed = (
        source_duration /
        target_duration
    )


    filters = []


    # Only modify speed when necessary.

    if abs(
        speed - 1.0
    ) > 0.002:

        filters.append(
            build_tempo_filter(
                speed
            )
        )


    filters.append(
        "apad"
    )


    filters.append(
        f"atrim="
        f"duration={target_duration:.3f}"
    )


    filters.append(
        "asetpts=N/SR/TB"
    )


    subprocess.run(
        [
            "ffmpeg",
            "-y",

            "-i",
            str(input_file),

            "-af",
            ",".join(filters),

            "-ar",
            "48000",

            "-ac",
            "2",

            "-c:a",
            "pcm_s16le",

            str(output_file)
        ],
        check=True,

        stdout=subprocess.DEVNULL,

        stderr=subprocess.PIPE,

        text=True
    )


    actual = get_duration(
        output_file
    )


    if abs(
        actual -
        target_duration
    ) > 0.08:

        raise RuntimeError(
            f"Timing mismatch: "
            f"{output_file.name}"
        )


    return (
        source_duration,
        actual
    )


# ============================================================
# INPUT CHECK
# ============================================================

if not VIDEO.exists():

    raise RuntimeError(
        "factverse_silent.mp4 missing."
    )


if not METADATA.exists():

    raise RuntimeError(
        "metadata.json missing."
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


answer = str(
    data["answer"]
).upper()


answer_text = data[
    "options"
][answer]


# ============================================================
# SEGMENT SCRIPTS
# ============================================================

scripts = {

    "01_hook":

        f"""
        {data['hook']}.
        """,


    "02_question_options":

        f"""
        Here is your challenge.

        {data['question']}.

        Option A:
        {data['options']['A']}.

        Option B:
        {data['options']['B']}.

        Option C:
        {data['options']['C']}.

        Option D:
        {data['options']['D']}.
        """,


    "03_countdown":

        """
        Think carefully.

        You have five seconds.

        Five.

        Four.

        Three.

        Two.

        One.
        """,


    "04_answer":

        f"""
        The correct answer is
        option {answer}.

        {answer_text}.
        """,


    "05_explanation":

        f"""
        Here's why.

        {data['explanation']}.
        """,


    "06_cta":

        """
        Did you get it right?

        Comment A, B, C, or D.

        Subscribe for tomorrow's challenge.
        """
}


# ============================================================
# START
# ============================================================

print("========================================")
print("THINK FAST DAILY V2 AUDIO")
print("========================================")

print(
    "Voice:",
    VOICE
)

print(
    "Target:",
    VIDEO_DURATION,
    "seconds"
)

print("========================================")


# ============================================================
# CLEAN OLD AUDIO
# ============================================================

for old in VOICE_DIR.glob("*"):

    try:
        old.unlink()
    except Exception:
        pass


# ============================================================
# GENERATE SEGMENTS
# ============================================================

fitted_files = []


for name, duration in SEGMENTS:

    raw = (
        VOICE_DIR /
        f"{name}_raw.mp3"
    )

    fitted = (
        VOICE_DIR /
        f"{name}.wav"
    )


    print(
        f"Generating: {name}"
    )


    asyncio.run(
        create_voice(
            scripts[name],
            raw
        )
    )


    source, actual = fit_audio(
        raw,
        fitted,
        duration
    )


    print(
        f"Source: {source:.2f}s "
        f"-> Target: {duration:.2f}s "
        f"-> Final: {actual:.2f}s"
    )


    fitted_files.append(
        fitted
    )


# ============================================================
# CONCATENATE SEGMENTS
# ============================================================

inputs = []

labels = []


for index, file_path in enumerate(
    fitted_files
):

    inputs.extend(
        [
            "-i",
            str(file_path)
        ]
    )

    labels.append(
        f"[{index}:a]"
    )


concat_filter = (
    "".join(labels)
    +
    f"concat="
    f"n={len(fitted_files)}:"
    f"v=0:"
    f"a=1,"
    f"aresample=48000,"
    f"asetpts=N/SR/TB[aout]"
)


subprocess.run(
    [
        "ffmpeg",
        "-y",

        *inputs,

        "-filter_complex",
        concat_filter,

        "-map",
        "[aout]",

        "-ar",
        "48000",

        "-ac",
        "2",

        "-c:a",
        "pcm_s16le",

        str(VOICE_WAV)
    ],
    check=True,

    stdout=subprocess.DEVNULL,

    stderr=subprocess.PIPE,

    text=True
)


voice_duration = get_duration(
    VOICE_WAV
)


print(
    "Combined narration:",
    round(
        voice_duration,
        2
    ),
    "seconds"
)


if abs(
    voice_duration -
    VIDEO_DURATION
) > 0.08:

    raise RuntimeError(
        "VOICE/VIDEO TIMELINE MISMATCH."
    )


# ============================================================
# BACKGROUND MUSIC
# ============================================================

print(
    "Generating subtle background music..."
)


sample_rate = 44100


with wave.open(
    str(MUSIC_WAV),
    "w"
) as wav:

    wav.setnchannels(2)

    wav.setsampwidth(2)

    wav.setframerate(
        sample_rate
    )


    total = int(
        VIDEO_DURATION *
        sample_rate
    )


    for i in range(total):

        t = (
            i /
            sample_rate
        )


        value = (

            math.sin(
                2 *
                math.pi *
                110 *
                t
            )
            *
            0.018

            +

            math.sin(
                2 *
                math.pi *
                164.81 *
                t
            )
            *
            0.009

            +

            math.sin(
                2 *
                math.pi *
                220 *
                t
            )
            *
            0.006
        )


        fade_in = min(
            1.0,
            t / 2
        )


        fade_out = min(
            1.0,
            (
                VIDEO_DURATION -
                t
            ) / 2
        )


        value *= (
            fade_in *
            fade_out
        )


        sample = int(
            max(
                -1,
                min(
                    1,
                    value
                )
            )
            *
            32767
        )


        wav.writeframes(
            struct.pack(
                "<hh",
                sample,
                sample
            )
        )


# ============================================================
# FINAL MIX
# ============================================================

print(
    "Merging video + narration + music..."
)


filter_complex = (

    "[1:a]"
    "loudnorm="
    "I=-16:"
    "TP=-1.5:"
    "LRA=11"
    "[voice];"

    "[2:a]"
    "volume=0.055"
    "[music];"

    "[voice][music]"
    "amix="
    "inputs=2:"
    "duration=first:"
    "dropout_transition=1,"
    f"atrim=duration={VIDEO_DURATION:.3f},"
    "aresample=48000"
    "[audio]"
)


subprocess.run(
    [
        "ffmpeg",
        "-y",

        "-i",
        str(VIDEO),

        "-i",
        str(VOICE_WAV),

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
# FINAL CHECK
# ============================================================

final_duration = get_duration(
    FINAL_VIDEO
)


print("========================================")
print("THINK FAST DAILY V2 READY")
print("========================================")

print(
    "Narration:",
    round(
        voice_duration,
        2
    ),
    "seconds"
)

print(
    "Final video:",
    round(
        final_duration,
        2
    ),
    "seconds"
)

print(
    "Output:",
    FINAL_VIDEO
)

print("========================================")


if abs(
    final_duration -
    VIDEO_DURATION
) > 0.08:

    raise RuntimeError(
        "FINAL VIDEO DURATION MISMATCH."
    )


print(
    "SYNC CHECK: PASSED"
)

print("========================================")
