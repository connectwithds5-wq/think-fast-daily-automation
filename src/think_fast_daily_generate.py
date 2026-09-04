import json
import os
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types


ROOT = Path(__file__).resolve().parents[1]

OUTPUT = ROOT / "output"
FRAMES = OUTPUT / "think_fast_daily_frames"

SILENT_VIDEO = OUTPUT / "factverse_silent.mp4"
METADATA = OUTPUT / "metadata.json"

OUTPUT.mkdir(parents=True, exist_ok=True)
FRAMES.mkdir(parents=True, exist_ok=True)


# ============================================================
# VIDEO SETTINGS
# ============================================================

WIDTH = 1080
HEIGHT = 1920
FPS = 30

DURATION = 35
TOTAL_FRAMES = FPS * DURATION


# ============================================================
# GEMINI
# ============================================================

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing.")

client = genai.Client(api_key=api_key)

MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)


# ============================================================
# QUIZ CATEGORIES
# ============================================================

categories = [
    "visual brain puzzle",
    "tricky logic puzzle",
    "guess the animal",
    "guess the object",
    "guess the country",
    "geography challenge",
    "emoji guessing challenge",
    "number pattern puzzle",
    "shape pattern puzzle",
    "quick IQ challenge",
    "science brain teaser",
    "space guessing challenge",
    "history guessing challenge",
    "common knowledge trick question"
]

category = random.choice(categories)


# ============================================================
# AI QUIZ GENERATION
# ============================================================

prompt = f"""
You create viral but accurate YouTube Shorts for
THINK FAST DAILY.

Create ONE highly engaging brain quiz / guessing challenge.

Category:
{category}

The video is 35 seconds.

TIMELINE:

0-3 seconds:
POWERFUL HOOK.

3-16 seconds:
QUESTION + FOUR OPTIONS + VISUAL CLUE.

16-21 seconds:
5 SECOND THINKING COUNTDOWN.

21-25 seconds:
ANSWER REVEAL.

25-31 seconds:
SHORT EXPLANATION.

31-35 seconds:
NATURAL CTA.

IMPORTANT:

The question must be easy enough to understand quickly.

The answer must be exactly one of A/B/C/D.

Do not reveal the answer in the hook.

Do not reveal the answer in the visual before the reveal.

Use simple natural English.

No politics.
No medical advice.
No dangerous content.
No adult content.
No graphic content.

Create a visual concept that matches the question.

For example:

animal -> animal silhouette / clues
country -> globe / map clue
object -> mystery object silhouette
number -> animated number sequence
pattern -> geometric pattern
space -> planet / stars
logic -> puzzle blocks
emoji -> emoji clue
science -> simple science visual

Return ONLY valid JSON.

Use EXACTLY this structure:

{{
  "hook": "Short curiosity hook, maximum 10 words",

  "question": "Quiz question, maximum 20 words",

  "options": {{
    "A": "Option A",
    "B": "Option B",
    "C": "Option C",
    "D": "Option D"
  }},

  "answer": "A",

  "explanation": "Short factual explanation, maximum 30 words",

  "visual_type": "animal",

  "visual_prompt": "Describe a simple visual clue for this question without revealing the answer",

  "title": "SEO optimized YouTube Shorts title",

  "description": "SEO optimized YouTube Shorts description",

  "keywords": [
    "brain quiz",
    "iq quiz",
    "guess the answer",
    "brain challenge",
    "puzzle",
    "trivia",
    "think fast daily",
    "shorts"
  ],

  "hashtags": [
    "#brainquiz",
    "#iqquiz",
    "#guess",
    "#brainchallenge",
    "#puzzle",
    "#trivia",
    "#shorts",
    "#thinkfastdaily"
  ]
}}
"""


print("========================================")
print("THINK FAST DAILY V2")
print("Generating quiz...")
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

if text.startswith("```json"):
    text = text[7:]

if text.startswith("```"):
    text = text[3:]

if text.endswith("```"):
    text = text[:-3]

data = json.loads(text.strip())


# ============================================================
# VALIDATION
# ============================================================

required = [
    "hook",
    "question",
    "options",
    "answer",
    "explanation",
    "visual_type",
    "visual_prompt",
    "title",
    "description",
    "keywords",
    "hashtags"
]

for field in required:
    if field not in data:
        raise RuntimeError(
            f"Missing field: {field}"
        )


for option in ["A", "B", "C", "D"]:
    if option not in data["options"]:
        raise RuntimeError(
            f"Missing option: {option}"
        )


data["answer"] = str(
    data["answer"]
).upper().strip()


if data["answer"] not in ["A", "B", "C", "D"]:
    raise RuntimeError(
        "Answer must be A, B, C or D."
    )


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
) as f:

    json.dump(
        data,
        f,
        ensure_ascii=False,
        indent=2
    )


print("Metadata saved.")


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

font_brand = ImageFont.truetype(
    FONT_BOLD, 38
)

font_hook = ImageFont.truetype(
    FONT_BOLD, 70
)

font_question = ImageFont.truetype(
    FONT_BOLD, 52
)

font_option = ImageFont.truetype(
    FONT_BOLD, 43
)

font_answer = ImageFont.truetype(
    FONT_BOLD, 70
)

font_explanation = ImageFont.truetype(
    FONT_BOLD, 44
)

font_countdown = ImageFont.truetype(
    FONT_BOLD, 150
)

font_small = ImageFont.truetype(
    FONT_REGULAR, 31
)


# ============================================================
# HELPERS
# ============================================================

def wrap_text(text, font, max_width):

    dummy = Image.new(
        "RGB",
        (WIDTH, HEIGHT)
    )

    draw = ImageDraw.Draw(dummy)

    words = str(text).split()

    lines = []
    current = ""

    for word in words:

        test = (
            current + " " + word
            if current
            else word
        )

        box = draw.textbbox(
            (0, 0),
            test,
            font=font
        )

        if box[2] - box[0] <= max_width:
            current = test

        else:

            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    return lines


def centered_text(
    draw,
    text,
    font,
    y,
    max_width=850
):

    lines = wrap_text(
        text,
        font,
        max_width
    )

    spacing = int(
        font.size * 1.35
    )

    total = len(lines) * spacing

    start = y - total // 2

    for line in lines:

        box = draw.textbbox(
            (0, 0),
            line,
            font=font
        )

        width = box[2] - box[0]

        x = (WIDTH - width) // 2

        draw.text(
            (x + 4, start + 5),
            line,
            font=font,
            fill=(0, 0, 0)
        )

        draw.text(
            (x, start),
            line,
            font=font,
            fill=(245, 245, 250)
        )

        start += spacing


def brand(draw):

    text = "THINK FAST DAILY"

    box = draw.textbbox(
        (0, 0),
        text,
        font=font_brand
    )

    width = box[2] - box[0]

    draw.text(
        (
            (WIDTH - width) // 2,
            75
        ),
        text,
        font=font_brand,
        fill=(245, 200, 80)
    )


def label(draw, text):

    box = draw.textbbox(
        (0, 0),
        text,
        font=font_small
    )

    width = box[2] - box[0]

    draw.text(
        (
            (WIDTH - width) // 2,
            235
        ),
        text,
        font=font_small,
        fill=(175, 185, 210)
    )


# ============================================================
# VISUAL CLUE
# ============================================================

def draw_visual_clue(
    draw,
    visual_type,
    frame_number
):

    center_x = WIDTH // 2
    center_y = 690

    pulse = int(
        10 *
        abs(
            ((frame_number % 60) - 30)
            / 30
        )
    )

    # Generic glowing brain/puzzle style visual
    # designed not to reveal the answer.

    if visual_type == "animal":

        # mystery animal silhouette

        draw.ellipse(
            (
                center_x - 135,
                center_y - 110 - pulse,
                center_x + 135,
                center_y + 110 + pulse
            ),
            outline=(80, 130, 230),
            width=10
        )

        draw.polygon(
            [
                (center_x - 100, center_y - 70),
                (center_x - 165, center_y - 160),
                (center_x - 45, center_y - 110)
            ],
            outline=(245, 200, 80)
        )

        draw.polygon(
            [
                (center_x + 100, center_y - 70),
                (center_x + 165, center_y - 160),
                (center_x + 45, center_y - 110)
            ],
            outline=(245, 200, 80)
        )

        draw.ellipse(
            (
                center_x - 15,
                center_y - 20,
                center_x + 15,
                center_y + 10
            ),
            fill=(245, 200, 80)
        )

    elif visual_type == "country":

        # Globe

        r = 145 + pulse

        draw.ellipse(
            (
                center_x - r,
                center_y - r,
                center_x + r,
                center_y + r
            ),
            outline=(80, 150, 245),
            width=10
        )

        draw.arc(
            (
                center_x - r,
                center_y - r,
                center_x + r,
                center_y + r
            ),
            70,
            290,
            fill=(245, 200, 80),
            width=6
        )

        draw.line(
            (
                center_x - r,
                center_y,
                center_x + r,
                center_y
            ),
            fill=(80, 150, 245),
            width=5
        )

    elif visual_type in [
        "number",
        "number pattern"
    ]:

        centered_text(
            draw,
            "?  ?  ?  ?",
            font_answer,
            center_y
        )

    elif visual_type in [
        "pattern",
        "shape pattern",
        "logic"
    ]:

        size = 90

        shapes = [
            "circle",
            "square",
            "triangle",
            "circle"
        ]

        for i, shape in enumerate(shapes):

            x = (
                center_x -
                225 +
                i * 150
            )

            y = center_y

            if shape == "circle":

                draw.ellipse(
                    (
                        x - size // 2,
                        y - size // 2,
                        x + size // 2,
                        y + size // 2
                    ),
                    outline=(80, 150, 245),
                    width=8
                )

            elif shape == "square":

                draw.rectangle(
                    (
                        x - size // 2,
                        y - size // 2,
                        x + size // 2,
                        y + size // 2
                    ),
                    outline=(245, 200, 80),
                    width=8
                )

            else:

                draw.polygon(
                    [
                        (x, y - size // 2),
                        (x - size // 2, y + size // 2),
                        (x + size // 2, y + size // 2)
                    ],
                    outline=(80, 150, 245),
                    width=8
                )

    elif visual_type == "space":

        r = 115 + pulse

        draw.ellipse(
            (
                center_x - r,
                center_y - r,
                center_x + r,
                center_y + r
            ),
            outline=(80, 150, 245),
            width=10
        )

        draw.arc(
            (
                center_x - 190,
                center_y - 60,
                center_x + 190,
                center_y + 60
            ),
            0,
            360,
            fill=(245, 200, 80),
            width=6
        )

    elif visual_type == "emoji":

        centered_text(
            draw,
            "❓  ❓  ❓",
            font_answer,
            center_y
        )

    else:

        # Default mystery puzzle visual

        r = 125 + pulse

        draw.ellipse(
            (
                center_x - r,
                center_y - r,
                center_x + r,
                center_y + r
            ),
            outline=(80, 150, 245),
            width=10
        )

        centered_text(
            draw,
            "?",
            font_countdown,
            center_y
        )


# ============================================================
# OPTIONS
# ============================================================

def draw_option(
    draw,
    letter,
    text,
    y
):

    draw.rounded_rectangle(
        (
            80,
            y,
            WIDTH - 80,
            y + 105
        ),
        radius=25,
        fill=(18, 24, 52),
        outline=(65, 80, 125),
        width=3
    )

    cx = 145
    cy = y + 52

    draw.ellipse(
        (
            cx - 28,
            cy - 28,
            cx + 28,
            cy + 28
        ),
        fill=(245, 200, 80)
    )

    centered_letter = draw.textbbox(
        (0, 0),
        letter,
        font=font_option
    )

    lw = centered_letter[2] - centered_letter[0]
    lh = centered_letter[3] - centered_letter[1]

    draw.text(
        (
            cx - lw // 2,
            cy - lh // 2 - 4
        ),
        letter,
        font=font_option,
        fill=(8, 10, 25)
    )

    lines = wrap_text(
        text,
        font_option,
        700
    )

    for i, line in enumerate(lines[:2]):

        draw.text(
            (
                205,
                y + 18 + i * 45
            ),
            line,
            font=font_option,
            fill=(245, 245, 250)
        )


# ============================================================
# FRAME
# ============================================================

def create_frame(frame_number):

    img = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (7, 10, 26)
    )

    draw = ImageDraw.Draw(img)

    # background particles

    random.seed(2026)

    for _ in range(100):

        x = random.randint(
            20,
            WIDTH - 20
        )

        y = random.randint(
            20,
            HEIGHT - 20
        )

        radius = random.randint(
            1,
            3
        )

        draw.ellipse(
            (
                x - radius,
                y - radius,
                x + radius,
                y + radius
            ),
            fill=(70, 80, 115)
        )

    brand(draw)

    # ========================================================
    # 0-3 HOOK
    # ========================================================

    if frame_number < FPS * 3:

        label(
            draw,
            "🧠 DAILY BRAIN CHALLENGE"
        )

        centered_text(
            draw,
            data["hook"],
            font_hook,
            820
        )

        centered_text(
            draw,
            "CAN YOU GET IT RIGHT?",
            font_small,
            1080
        )


    # ========================================================
    # 3-16 QUESTION + VISUAL + OPTIONS
    # ========================================================

    elif frame_number < FPS * 16:

        label(
            draw,
            "THINK FAST!"
        )

        centered_text(
            draw,
            data["question"],
            font_question,
            450,
            900
        )

        draw_visual_clue(
            draw,
            str(
                data["visual_type"]
            ).lower(),
            frame_number
        )

        draw_option(
            draw,
            "A",
            data["options"]["A"],
            1080
        )

        draw_option(
            draw,
            "B",
            data["options"]["B"],
            1200
        )

        draw_option(
            draw,
            "C",
            data["options"]["C"],
            1320
        )

        draw_option(
            draw,
            "D",
            data["options"]["D"],
            1440
        )


    # ========================================================
    # 16-21 COUNTDOWN
    # ========================================================

    elif frame_number < FPS * 21:

        label(
            draw,
            "LOCK IN YOUR ANSWER"
        )

        elapsed = (
            frame_number / FPS
        ) - 16

        number = max(
            1,
            5 - int(elapsed)
        )

        centered_text(
            draw,
            str(number),
            font_countdown,
            760
        )

        centered_text(
            draw,
            "THINK FAST!",
            font_answer,
            1080
        )


    # ========================================================
    # 21-25 ANSWER
    # ========================================================

    elif frame_number < FPS * 25:

        label(
            draw,
            "CORRECT ANSWER"
        )

        centered_text(
            draw,
            f"OPTION {data['answer']}",
            font_answer,
            650
        )

        centered_text(
            draw,
            data["options"][data["answer"]],
            font_answer,
            920,
            850
        )

        centered_text(
            draw,
            "✓ YOU GOT IT?",
            font_small,
            1160
        )


    # ========================================================
    # 25-31 EXPLANATION
    # ========================================================

    elif frame_number < FPS * 31:

        label(
            draw,
            "HERE'S WHY"
        )

        centered_text(
            draw,
            data["explanation"],
            font_explanation,
            800,
            850
        )


    # ========================================================
    # 31-35 CTA
    # ========================================================

    else:

        label(
            draw,
            "DID YOU GET IT RIGHT?"
        )

        centered_text(
            draw,
            "COMMENT A / B / C / D",
            font_answer,
            700
        )

        centered_text(
            draw,
            "SUBSCRIBE FOR TOMORROW'S CHALLENGE",
            font_small,
            1050,
            900
        )


    # ========================================================
    # PROGRESS BAR
    # ========================================================

    progress = int(
        WIDTH *
        (frame_number + 1)
        /
        TOTAL_FRAMES
    )

    draw.rectangle(
        (
            0,
            HEIGHT - 12,
            progress,
            HEIGHT
        ),
        fill=(245, 200, 80)
    )

    return img


# ============================================================
# CLEAN OLD FRAMES
# ============================================================

print("Cleaning old frames...")

for old in FRAMES.glob("frame_*.png"):

    try:
        old.unlink()
    except Exception:
        pass


# ============================================================
# RENDER
# ============================================================

print("========================================")
print("Rendering 35 second video...")
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
            f"Rendered "
            f"{frame_number / FPS:.0f}s"
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
        "20",

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
# VERIFY
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
print("VIDEO GENERATED")
print("Duration:", round(video_duration, 2))
print("Visual type:", data["visual_type"])
print("========================================")


if abs(
    video_duration - DURATION
) > 0.15:

    raise RuntimeError(
        "Generated video duration is incorrect."
    )
