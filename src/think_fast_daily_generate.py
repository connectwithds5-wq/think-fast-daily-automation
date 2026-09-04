import json
import os
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

OUTPUT = ROOT / "output"
FRAMES = OUTPUT / "think_fast_daily_frames"

SILENT_VIDEO = OUTPUT / "factverse_silent.mp4"
METADATA = OUTPUT / "metadata.json"

OUTPUT.mkdir(
    parents=True,
    exist_ok=True
)

FRAMES.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# VIDEO SETTINGS
# ============================================================

WIDTH = 1080
HEIGHT = 1920

FPS = 30

DURATION = 30

TOTAL_FRAMES = FPS * DURATION


# ============================================================
# GEMINI
# ============================================================

api_key = os.environ.get(
    "GEMINI_API_KEY"
)

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY GitHub Secret is missing."
    )


client = genai.Client(
    api_key=api_key
)


MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)


# ============================================================
# QUIZ CATEGORIES
# ============================================================

categories = [
    "visual brain puzzles",
    "tricky logic questions",
    "guess the object",
    "guess the animal",
    "guess the country",
    "guess the famous place",
    "emoji guessing challenge",
    "spot the pattern",
    "number puzzle",
    "quick IQ challenge",
    "optical illusion style puzzle",
    "common knowledge trick question",
    "science brain teaser",
    "history guessing challenge",
    "geography challenge"
]


category = random.choice(
    categories
)


# ============================================================
# AI PROMPT
# ============================================================

prompt = f"""
You are the expert content creator for a viral YouTube Shorts channel
called THINK FAST DAILY.

Create ONE highly engaging 30-second brain quiz / guessing challenge.

Category:
{category}

The goal is maximum viewer retention.

The viewer should:
1. Immediately become curious.
2. Read the question.
3. Choose between four options.
4. Think during a countdown.
5. Wait for the answer reveal.
6. Learn something interesting.
7. Want to comment and subscribe.

IMPORTANT FACTUAL RULES:

- Never invent facts.
- Never invent statistics.
- Never use fake scientific claims.
- Never use misleading information.
- If the question has a factual answer, make sure the answer is correct.
- The answer MUST exactly match one of A, B, C or D.
- Avoid politics.
- Avoid medical advice.
- Avoid dangerous instructions.
- Avoid graphic content.
- Avoid adult content.
- Avoid copyrighted characters as the main subject.
- Make the challenge suitable for a general audience.
- Keep the language simple and natural.
- Use English.

TIMING:

0–3 seconds:
POWERFUL HOOK.

3–15 seconds:
QUESTION + FOUR OPTIONS.

15–20 seconds:
THINKING / COUNTDOWN.

20–24 seconds:
ANSWER REVEAL.

24–28 seconds:
SHORT EXPLANATION.

28–30 seconds:
CTA.

VERY IMPORTANT:

The answer must NOT be revealed inside the question,
options, hook or explanation before the answer section.

Return ONLY valid JSON.

Use exactly this structure:

{{
  "hook": "Short curiosity hook, maximum 10 words",

  "question": "The actual quiz question, maximum 20 words",

  "options": {{
    "A": "Option A",
    "B": "Option B",
    "C": "Option C",
    "D": "Option D"
  }},

  "answer": "A",

  "explanation": "Short factual explanation, maximum 25 words",

  "title": "SEO optimized YouTube Shorts title",

  "description": "SEO optimized YouTube Shorts description",

  "keywords": [
    "brain quiz",
    "iq quiz",
    "guess the answer",
    "brain challenge",
    "trivia",
    "puzzle",
    "think fast daily",
    "shorts"
  ],

  "hashtags": [
    "#brainquiz",
    "#iqquiz",
    "#guess",
    "#brainchallenge",
    "#trivia",
    "#puzzle",
    "#shorts",
    "#thinkfastdaily"
  ]
}}
"""


# ============================================================
# GENERATE QUIZ
# ============================================================

print("========================================")
print("Generating THINK FAST DAILY quiz...")
print("Category:", category)
print("Model:", MODEL)
print("========================================")


response = client.models.generate_content(
    model=MODEL,
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json"
    )
)


text = response.text.strip()


# ============================================================
# CLEAN JSON
# ============================================================

if text.startswith("```json"):
    text = text[7:]

if text.startswith("```"):
    text = text[3:]

if text.endswith("```"):
    text = text[:-3]


data = json.loads(
    text.strip()
)


# ============================================================
# VALIDATE DATA
# ============================================================

required_fields = [
    "hook",
    "question",
    "options",
    "answer",
    "explanation",
    "title",
    "description",
    "keywords",
    "hashtags"
]


for field in required_fields:

    if field not in data:

        raise RuntimeError(
            f"Missing quiz field: {field}"
        )


# Validate options

required_options = [
    "A",
    "B",
    "C",
    "D"
]


for option in required_options:

    if option not in data["options"]:

        raise RuntimeError(
            f"Missing option: {option}"
        )


# Validate answer

if data["answer"] not in required_options:

    raise RuntimeError(
        "Invalid answer. Must be A, B, C or D."
    )


# ============================================================
# CHANNEL DATA
# ============================================================

data["channel"] = "THINK FAST DAILY"

data["category"] = category

data["duration"] = DURATION


# ============================================================
# SAVE METADATA
# ============================================================

with open(
    METADATA,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        data,
        file,
        ensure_ascii=False,
        indent=2
    )


print("Quiz metadata saved.")


# ============================================================
# FONTS
# ============================================================

FONT_BOLD = (
    "/usr/share/fonts/truetype/dejavu/"
    "DejaVuSans-Bold.ttf"
)

FONT_REGULAR = (
    "/usr/share/fonts/truetype/dejavu/"
    "DejaVuSans.ttf"
)


font_hook = ImageFont.truetype(
    FONT_BOLD,
    72
)

font_question = ImageFont.truetype(
    FONT_BOLD,
    55
)

font_option = ImageFont.truetype(
    FONT_BOLD,
    46
)

font_answer = ImageFont.truetype(
    FONT_BOLD,
    68
)

font_explanation = ImageFont.truetype(
    FONT_BOLD,
    46
)

font_countdown = ImageFont.truetype(
    FONT_BOLD,
    130
)

font_brand = ImageFont.truetype(
    FONT_BOLD,
    38
)

font_small = ImageFont.truetype(
    FONT_REGULAR,
    32
)


# ============================================================
# TEXT WRAPPING
# ============================================================

def wrap_text(
    text,
    font,
    max_width
):

    dummy = Image.new(
        "RGB",
        (WIDTH, HEIGHT)
    )

    draw = ImageDraw.Draw(
        dummy
    )

    words = text.split()

    lines = []

    current = ""

    for word in words:

        test = (
            f"{current} {word}"
            if current
            else word
        )

        box = draw.textbbox(
            (0, 0),
            test,
            font=font
        )

        width = (
            box[2] -
            box[0]
        )

        if width <= max_width:

            current = test

        else:

            if current:

                lines.append(
                    current
                )

            current = word


    if current:

        lines.append(
            current
        )


    return lines


# ============================================================
# PREPARE TEXT
# ============================================================

hook_lines = wrap_text(
    data["hook"],
    font_hook,
    850
)


question_lines = wrap_text(
    data["question"],
    font_question,
    850
)


explanation_lines = wrap_text(
    data["explanation"],
    font_explanation,
    850
)


# ============================================================
# STAR FIELD
# ============================================================

random.seed(
    2026
)

stars = []

for _ in range(130):

    stars.append(
        (
            random.randint(
                20,
                WIDTH - 20
            ),

            random.randint(
                20,
                HEIGHT - 20
            ),

            random.randint(
                1,
                4
            )
        )
    )


# ============================================================
# DRAW CENTERED TEXT
# ============================================================

def draw_centered(
    draw,
    lines,
    font,
    center_y,
    spacing
):

    if not lines:

        return


    total_height = (
        len(lines) *
        spacing
    )


    y = (
        center_y -
        total_height // 2
    )


    for line in lines:

        box = draw.textbbox(
            (0, 0),
            line,
            font=font
        )

        width = (
            box[2] -
            box[0]
        )


        x = (
            WIDTH -
            width
        ) // 2


        # Shadow

        draw.text(
            (
                x + 5,
                y + 6
            ),

            line,

            font=font,

            fill=(
                0,
                0,
                0
            )
        )


        draw.text(
            (
                x,
                y
            ),

            line,

            font=font,

            fill=(
                245,
                245,
                250
            )
        )


        y += spacing


# ============================================================
# DRAW OPTION
# ============================================================

def draw_option(
    draw,
    letter,
    text,
    y
):

    box_x1 = 110
    box_x2 = WIDTH - 110

    box_y1 = y
    box_y2 = y + 115


    # Option box

    draw.rounded_rectangle(
        (
            box_x1,
            box_y1,
            box_x2,
            box_y2
        ),

        radius=28,

        fill=(
            18,
            23,
            48
        ),

        outline=(
            70,
            80,
            125
        ),

        width=3
    )


    # Letter circle

    circle_x = 175
    circle_y = (
        y + 57
    )


    draw.ellipse(
        (
            circle_x - 32,
            circle_y - 32,
            circle_x + 32,
            circle_y + 32
        ),

        fill=(
            245,
            200,
            80
        )
    )


    letter_box = draw.textbbox(
        (0, 0),
        letter,
        font=font_option
    )


    letter_width = (
        letter_box[2] -
        letter_box[0]
    )


    letter_height = (
        letter_box[3] -
        letter_box[1]
    )


    draw.text(
        (
            circle_x -
            letter_width // 2,

            circle_y -
            letter_height // 2 -
            5
        ),

        letter,

        font=font_option,

        fill=(
            8,
            10,
            25
        )
    )


    # Option text

    option_lines = wrap_text(
        text,
        font_option,
        650
    )


    if len(option_lines) > 2:

        option_lines = option_lines[:2]


    start_y = (
        y + 25
    )


    for index, line in enumerate(
        option_lines
    ):

        draw.text(
            (
                245,
                start_y +
                index * 50
            ),

            line,

            font=font_option,

            fill=(
                245,
                245,
                250
            )
        )


# ============================================================
# DRAW BRAND
# ============================================================

def draw_brand(
    draw
):

    brand = "THINK FAST DAILY"


    box = draw.textbbox(
        (0, 0),
        brand,
        font=font_brand
    )


    width = (
        box[2] -
        box[0]
    )


    draw.text(
        (
            (WIDTH - width) // 2,
            90
        ),

        brand,

        font=font_brand,

        fill=(
            245,
            200,
            80
        )
    )


# ============================================================
# DRAW LABEL
# ============================================================

def draw_label(
    draw,
    text
):

    box = draw.textbbox(
        (0, 0),
        text,
        font=font_small
    )


    width = (
        box[2] -
        box[0]
    )


    draw.text(
        (
            (WIDTH - width) // 2,
            260
        ),

        text,

        font=font_small,

        fill=(
            180,
            185,
            205
        )
    )


# ============================================================
# CREATE FRAME
# ============================================================

def create_frame(
    frame_number
):

    img = Image.new(
        "RGB",
        (
            WIDTH,
            HEIGHT
        ),

        (
            8,
            10,
            25
        )
    )


    draw = ImageDraw.Draw(
        img
    )


    # --------------------------------------------------------
    # Animated stars
    # --------------------------------------------------------

    for x, y, radius in stars:

        yy = int(
            (
                y +
                frame_number * 0.35
            )
            % HEIGHT
        )


        draw.ellipse(
            (
                x - radius,
                yy - radius,
                x + radius,
                yy + radius
            ),

            fill=(
                90,
                95,
                125
            )
        )


    # --------------------------------------------------------
    # Brand
    # --------------------------------------------------------

    draw_brand(
        draw
    )


    # ========================================================
    # 0–3 SEC
    # HOOK
    # ========================================================

    if frame_number < FPS * 3:

        draw_label(
            draw,
            "🧠 QUICK BRAIN CHALLENGE"
        )


        draw_centered(
            draw,
            hook_lines,
            font_hook,
            850,
            100
        )


        # Small instruction

        instruction = (
            "GET READY..."
        )


        box = draw.textbbox(
            (0, 0),
            instruction,
            font=font_small
        )


        width = (
            box[2] -
            box[0]
        )


        draw.text(
            (
                (WIDTH - width) // 2,
                1160
            ),

            instruction,

            font=font_small,

            fill=(
                180,
                185,
                205
            )
        )


    # ========================================================
    # 3–15 SEC
    # QUESTION + OPTIONS
    # ========================================================

    elif frame_number < FPS * 15:

        draw_label(
            draw,
            "CAN YOU GET IT RIGHT?"
        )


        draw_centered(
            draw,
            question_lines,
            font_question,
            500,
            72
        )


        option_y = 850

        draw_option(
            draw,
            "A",
            data["options"]["A"],
            option_y
        )


        draw_option(
            draw,
            "B",
            data["options"]["B"],
            option_y + 135
        )


        draw_option(
            draw,
            "C",
            data["options"]["C"],
            option_y + 270
        )


        draw_option(
            draw,
            "D",
            data["options"]["D"],
            option_y + 405
        )


    # ========================================================
    # 15–20 SEC
    # COUNTDOWN
    # ========================================================

    elif frame_number < FPS * 20:

        draw_label(
            draw,
            "THINK FAST!"
        )


        # Countdown:
        #
        # 15.0–16.0 = 5
        # 16.0–17.0 = 4
        # 17.0–18.0 = 3
        # 18.0–19.0 = 2
        # 19.0–20.0 = 1

        elapsed = (
            frame_number / FPS
        ) - 15


        countdown_number = (
            5 -
            int(elapsed)
        )


        countdown_number = max(
            1,
            min(
                5,
                countdown_number
            )
        )


        number = str(
            countdown_number
        )


        box = draw.textbbox(
            (0, 0),
            number,
            font=font_countdown
        )


        width = (
            box[2] -
            box[0]
        )


        height = (
            box[3] -
            box[1]
        )


        draw.text(
            (
                (WIDTH - width) // 2,
                730
            ),

            number,

            font=font_countdown,

            fill=(
                245,
                200,
                80
            )
        )


        think_text = (
            "LOCK IN YOUR ANSWER"
        )


        box = draw.textbbox(
            (0, 0),
            think_text,
            font=font_small
        )


        width = (
            box[2] -
            box[0]
        )


        draw.text(
            (
                (WIDTH - width) // 2,
                1050
            ),

            think_text,

            font=font_small,

            fill=(
                180,
                185,
                205
            )
        )


    # ========================================================
    # 20–24 SEC
    # ANSWER REVEAL
    # ========================================================

    elif frame_number < FPS * 24:

        draw_label(
            draw,
            "THE CORRECT ANSWER IS"
        )


        answer_letter = (
            data["answer"]
        )


        draw_centered(
            draw,
            [
                f"OPTION {answer_letter}"
            ],

            font_answer,

            700,

            100
        )


        answer_text = (
            data["options"]
            [answer_letter]
        )


        answer_lines = wrap_text(
            answer_text,
            font_answer,
            800
        )


        draw_centered(
            draw,
            answer_lines,
            font_answer,
            950,
            90
        )


        correct = "✓ CORRECT ANSWER"


        box = draw.textbbox(
            (0, 0),
            correct,
            font=font_small
        )


        width = (
            box[2] -
            box[0]
        )


        draw.text(
            (
                (WIDTH - width) // 2,
                1180
            ),

            correct,

            font=font_small,

            fill=(
                245,
                200,
                80
            )
        )


    # ========================================================
    # 24–28 SEC
    # EXPLANATION
    # ========================================================

    elif frame_number < FPS * 28:

        draw_label(
            draw,
            "WHY?"
        )


        draw_centered(
            draw,
            explanation_lines,
            font_explanation,
            850,
            75
        )


    # ========================================================
    # 28–30 SEC
    # CTA
    # ========================================================

    else:

        draw_label(
            draw,
            "DID YOU GET IT RIGHT?"
        )


        cta = [
            "COMMENT",
            "YOUR ANSWER"
        ]


        draw_centered(
            draw,
            cta,
            font_answer,
            700,
            100
        )


        follow = (
            "SUBSCRIBE FOR TOMORROW'S CHALLENGE"
        )


        box = draw.textbbox(
            (0, 0),
            follow,
            font=font_small
        )


        width = (
            box[2] -
            box[0]
        )


        draw.text(
            (
                (WIDTH - width) // 2,
                1050
            ),

            follow,

            font=font_small,

            fill=(
                245,
                200,
                80
            )
        )


    # ========================================================
    # PROGRESS BAR
    # ========================================================

    progress = int(
        WIDTH *
        (
            frame_number + 1
        ) /
        TOTAL_FRAMES
    )


    draw.rectangle(
        (
            0,
            HEIGHT - 15,
            progress,
            HEIGHT
        ),

        fill=(
            245,
            200,
            80
        )
    )


    return img


# ============================================================
# CLEAN OLD FRAMES
# ============================================================

print("Cleaning old frames...")


for old_frame in FRAMES.glob(
    "frame_*.png"
):

    try:

        old_frame.unlink()

    except Exception:

        pass


# ============================================================
# RENDER FRAMES
# ============================================================

print("========================================")
print("Rendering THINK FAST DAILY video")
print("Duration:", DURATION, "seconds")
print("Resolution:", WIDTH, "x", HEIGHT)
print("FPS:", FPS)
print("========================================")


for frame_number in range(
    TOTAL_FRAMES
):

    frame = create_frame(
        frame_number
    )


    frame.save(
        FRAMES /
        f"frame_{frame_number:05d}.png"
    )


    if frame_number % (
        FPS * 5
    ) == 0:

        print(
            f"Rendered {frame_number / FPS:.0f}s"
        )


# ============================================================
# CREATE SILENT VIDEO
# ============================================================

print("Creating silent video...")


subprocess.run(
    [
        "ffmpeg",
        "-y",

        "-framerate",
        str(FPS),

        "-i",
        str(
            FRAMES /
            "frame_%05d.png"
        ),

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "18",

        "-pix_fmt",
        "yuv420p",

        "-r",
        str(FPS),

        "-t",
        str(DURATION),

        "-movflags",
        "+faststart",

        str(SILENT_VIDEO)
    ],

    check=True
)


# ============================================================
# VERIFY VIDEO
# ============================================================

result = subprocess.run(
    [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(SILENT_VIDEO)
    ],

    capture_output=True,

    text=True,

    check=True
)


video_duration = float(
    result.stdout.strip()
)


print("========================================")
print("THINK FAST DAILY VIDEO GENERATED")
print("========================================")
print("Category:", category)
print("Title:", data["title"])
print("Duration:", round(video_duration, 2))
print("Video:", SILENT_VIDEO)
print("Metadata:", METADATA)
print("========================================")
