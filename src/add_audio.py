import asyncio
import json
import math
import os
import struct
import subprocess
import wave
from pathlib import Path

import edge_tts


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"

VIDEO = OUTPUT / "factverse_silent.mp4"
FINAL_VIDEO = OUTPUT / "think_fast_daily.mp4"
METADATA = OUTPUT / "metadata.json"

VOICE_DIR = OUTPUT / "voice_segments"
VOICE_DIR.mkdir(parents=True, exist_ok=True)

MUSIC_WAV = OUTPUT / "music.wav"
VOICE_WAV = OUTPUT / "voice_timed.wav"


# ============================================================
# SETTINGS
# ============================================================

VOICE = os.environ.get(
    "TTS_VOICE",
    "en-US-GuyNeural"
)

VIDEO_DURATION = 30.0


# ============================================================
# EXACT VISUAL TIMELINE
#
# 0-3    Hook
# 3-15   Question + Options
# 15-20  Countdown
# 20-24  Answer
# 24-28  Explanation
# 28-30  CTA
# ============================================================

SEGMENTS = [
    ("01_hook", 3.0),
    ("02_question_options", 12.0),
    ("03_countdown", 5.0),
    ("04_answer", 4.0),
    ("05_explanation", 4.0),
    ("06_cta", 2.0),
]


# ============================================================
# TTS
# ============================================================

async def create_voice(text, output_file):

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
# GET MEDIA DURATION
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

    return float(
        result.stdout.strip()
    )


# ============================================================
# SAFE ATEMPO CHAIN
# ============================================================

def build_tempo_filter(speed):

    if speed <= 0:
        raise ValueError(
            "Invalid audio speed."
        )

    filters = []

    remaining = speed

    # atempo supports 0.5 -> 2.0
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

    return ",".join(
        filters
    )


# ============================================================
# FIT AUDIO EXACTLY TO VISUAL DURATION
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
            f"Invalid voice duration: {input_file}"
        )

    # Example:
    #
    # source = 6 sec
    # target = 3 sec
    #
    # speed = 2.0
    #
    speed = (
        source_duration /
        target_duration
    )

    filters = []

    if abs(speed - 1.0) > 0.002:

        filters.append(
            build_tempo_filter(
                speed
            )
        )

    # If voice is shorter:
    # add silence.
    #
    # If voice is longer:
    # trim after fitting.
    filters.append(
        "apad"
    )

    filters.append(
        f"atrim=duration={target_duration:.3f}"
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

    actual_duration = get_duration(
        output_file
    )

    if abs(
        actual_duration -
        target_duration
    ) > 0.08:

        raise RuntimeError(
            f"Audio timing error: "
            f"{output_file.name} "
            f"expected={target_duration:.2f}s "
            f"actual={actual_duration:.2f}s"
        )

    return (
        source_duration,
        actual_duration
    )


# ============================================================
# CHECK INPUTS
# ============================================================

if not METADATA.exists():

    raise RuntimeError(
        "metadata.json is missing."
    )


if not VIDEO.exists():

    raise RuntimeError(
        "factverse_silent.mp4 is missing."
    )


# ============================================================
# LOAD QUIZ
# ============================================================

with open(
    METADATA,
    "r",
    encoding="utf-8"
) as file:

    data = json.load(
        file
    )


answer = str(
    data["answer"]
).strip().upper()


answer_text = data[
    "options"
][answer]


# ============================================================
# BUILD SYNCHRONIZED SCRIPTS
# ============================================================

scripts = {

    # --------------------------------------------------------
    # 0-3 seconds
    # --------------------------------------------------------

    "01_hook":

        f"{data['hook']}.",


    # --------------------------------------------------------
    # 3-15 seconds
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # 15-20 seconds
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # 20-24 seconds
    # --------------------------------------------------------

    "04_answer":

        f"""
        The correct answer is
        option {answer}.

        {answer_text}.
        """,


    # --------------------------------------------------------
    # 24-28 seconds
    # --------------------------------------------------------

    "05_explanation":

        f"""
        Here's why.

        {data['explanation']}.
        """,


    # --------------------------------------------------------
    # 28-30 seconds
    # --------------------------------------------------------

    "06_cta":

        """
        Comment your answer.

        Subscribe!
        """
}


# ============================================================
# START
# ============================================================

print(
    "========================================"
)

print(
    "THINK FAST DAILY AUDIO ENGINE"
)

print(
    "========================================"
)

print(
    "Voice:",
    VOICE
)

print(
    "Creating synchronized narration..."
)

print(
    "========================================"
)


# ============================================================
# REMOVE OLD SEGMENTS
# ============================================================

for old_file in VOICE_DIR.glob("*"):

    try:

        old_file.unlink()

    except Exception:

        pass


# ============================================================
# GENERATE EACH SEGMENT
# ============================================================

fitted_files = []


for name, target_duration in SEGMENTS:

    raw_file = (
        VOICE_DIR /
        f"{name}_raw.mp3"
    )

    fitted_file = (
        VOICE_DIR /
        f"{name}.wav"
    )


    print(
        f"Generating {name}"
    )

    print(
        f"Target duration: "
        f"{target_duration:.2f}s"
    )


    asyncio.run(
        create_voice(
            scripts[name],
            raw_file
        )
    )


    source_duration, actual_duration = fit_audio(
        raw_file,
        fitted_file,
        target_duration
    )


    print(
        f"Source: "
        f"{source_duration:.2f}s"
    )

    print(
        f"Fitted: "
        f"{actual_duration:.2f}s"
    )


    fitted_files.append(
        fitted_file
    )


# ============================================================
# CONCATENATE ALL VOICE SEGMENTS
# ============================================================

concat_inputs = []

filter_labels = []

for index, file_path in enumerate(
    fitted_files
):

    concat_inputs.append(
        "-i"
    )

    concat_inputs.append(
        str(file_path)
    )

    filter_labels.append(
        f"[{index}:a]"
    )


concat_filter = (
    "".join(filter_labels)
    +
    f"concat=n={len(fitted_files)}:v=0:a=1,"
    "aresample=48000,"
    "asetpts=N/SR/TB[aout]"
)


subprocess.run(
    [
        "ffmpeg",
        "-y",

        *concat_inputs,

        "-filter_complex",
        concat_filter,

        "-map",
        "[aout]",

        "-c:a",
        "pcm_s16le",

        "-ar",
        "48000",

        "-ac",
        "2",

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
    "========================================"
)

print(
    "Timed narration duration:",
    round(
        voice_duration,
        2
    ),
    "seconds"
)

print(
    "========================================"
)


if abs(
    voice_duration -
    VIDEO_DURATION
) > 0.08:

    raise RuntimeError(
        f"Voice/video mismatch: "
        f"{voice_duration:.2f}s vs "
        f"{VIDEO_DURATION:.2f}s"
    )


# ============================================================
# CREATE SOFT BACKGROUND MUSIC
# ============================================================

print(
    "Generating background music..."
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


        freq1 = 110

        freq2 = 164.81

        freq3 = 220


        value = (

            math.sin(
                2 *
                math.pi *
                freq1 *
                t
            )
            *
            0.025

            +

            math.sin(
                2 *
                math.pi *
                freq2 *
                t
            )
            *
            0.012

            +

            math.sin(
                2 *
                math.pi *
                freq3 *
                t
            )
            *
            0.008
        )


        fade_in = min(
            1.0,
            t / 2.0
        )


        fade_out = min(
            1.0,
            (
                VIDEO_DURATION -
                t
            ) / 2.0
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
# FINAL AUDIO MIX
# ============================================================

print(
    "Merging voice + music..."
)


filter_complex = (

    "[1:a]"

    "loudnorm="
    "I=-16:"
    "TP=-1.5:"
    "LRA=11"

    "[voice];"

    "[2:a]"

    "volume=0.07"

    "[music];"

    "[voice][music]"

    "amix="
    "inputs=2:"
    "duration=first:"
    "dropout_transition=1"

    ","

    f"atrim="
    f"duration={VIDEO_DURATION:.3f}"

    ","

    "aresample=48000"

    "[audio]"
)


# ============================================================
# MERGE VIDEO + AUDIO
# ============================================================

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
# FINAL VERIFICATION
# ============================================================

final_duration = get_duration(
    FINAL_VIDEO
)


print(
    "========================================"
)

print(
    "THINK FAST DAILY FINAL VIDEO READY"
)

print(
    "========================================"
)

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

print(
    "========================================"
)


if abs(
    final_duration -
    VIDEO_DURATION
) > 0.08:

    raise RuntimeError(
        "Final video is not exactly 30 seconds."
    )

print(
    "SYNC CHECK: PASSED"
)

print(
    "========================================"
)
