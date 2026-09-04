import json
import os
import random
import re
import time
from pathlib import Path

import requests
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
FRAMES = OUTPUT / "frames"
HISTORY_FILE = ROOT / "quiz_history.json"

OUTPUT.mkdir(exist_ok=True)
FRAMES.mkdir(exist_ok=True)


WIDTH = 1080
HEIGHT = 1920
FPS = 30
DURATION = 30


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY secret is missing.")


MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)


client = genai.Client(api_key=GEMINI_API_KEY)


# ============================================================
# CURRENT INTEREST SIGNALS
# ============================================================

def get_interest_topics():

    topics = []

    urls = [
        "https://trends.google.com/trending/rss?geo=US",
        "https://trends.google.com/trending/rss?geo=IN",
        "https://trends.google.com/trending/rss?geo=GB",
    ]

    for url in urls:

        try:

            response = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            if response.ok:

                text = response.text

                matches = re.findall(
                    r"<ht:approx_traffic>(.*?)</ht:approx_traffic>",
                    text
                )

                # RSS titles
                titles = re.findall(
                    r"<title>(.*?)</title>",
                    text,
                    flags=re.S
                )

                for title in titles[1:15]:

                    title = re.sub(
                        r"<.*?>",
                        "",
                        title
                    ).strip()

                    if title:
                        topics.append(title)

        except Exception as exc:

            print(
                "Trend signal unavailable:",
                exc
            )


    # Safe fallback topics
    fallback = [
        "animals",
        "space",
        "science",
        "human psychology",
        "optical illusions",
        "world geography",
        "history",
        "technology",
        "nature",
        "everyday science",
        "logic puzzles",
        "interesting human facts"
    ]

    topics.extend(fallback)

    # Remove duplicates
    cleaned = []

    for topic in topics:

        topic = topic.strip()

        if topic and topic.lower() not in [
            x.lower() for x in cleaned
        ]:

            cleaned.append(topic)


    random.shuffle(cleaned)

    return cleaned[:25]


# ============================================================
# HISTORY
# ============================================================

def load_history():

    if not HISTORY_FILE.exists():
        return []

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, list):
            return data

    except Exception:
        pass

    return []


history = load_history()

recent_questions = history[-100:]


# ============================================================
# GENERATE QUIZ
# ============================================================

interest_topics = get_interest_topics()

topic = random.choice(interest_topics)

history_text = "\n".join(
    recent_questions[-50:]
)


prompt = f"""
You are the senior quiz creator for the YouTube Shorts channel
"THINK FAST DAILY".

Create ONE highly engaging brain quiz for a global English-speaking
audience.

Possible current-interest topic:
{topic}

Previously used questions:
{history_text}

Do NOT repeat any previous question.

The quiz must:
- be solvable by an ordinary viewer
- create curiosity immediately
- be fun and challenging
- work perfectly in a 30-second vertical Short
- have exactly 4 answer options
- have exactly one correct answer
- use clear English
- have a verifiable answer
- avoid ambiguous wording
- avoid fake statistics
- avoid medical advice
- avoid politics
- avoid dangerous instructions
- avoid graphic content
- avoid copyrighted quotes
- avoid celebrity gossip
- never invent facts

Prefer:
- logic
- visual thinking
- science
- geography
- animals
- space
- patterns
- everyday knowledge
- riddles
- observation
- clever trick questions

IMPORTANT:
The question should be genuinely interesting, not merely difficult.

Return ONLY valid JSON.

Schema:

{{
  "question": "Short question",
  "options": {{
    "A": "Option A",
    "B": "Option B",
    "C": "Option C",
    "D": "Option D"
  }},
  "answer": "A",
  "explanation": "Short factual explanation, maximum 25 words",
  "hook": "Powerful hook, maximum 9 words",
  "difficulty": "Easy, Medium, or Hard",
  "category": "Category",
  "title": "Clickable YouTube Shorts title",
  "description": "SEO optimized YouTube description",
  "keywords": [
    "brain quiz",
    "iq test",
    "brain challenge",
    "guess the answer",
    "puzzle",
    "quiz shorts"
  ],
  "hashtags": [
    "#BrainQuiz",
    "#IQTest",
    "#BrainChallenge",
    "#Quiz",
    "#Shorts",
    "#ThinkFastDaily"
  ]
}}

Title rules:
- compelling
- natural
- no misleading claims
- no keyword stuffing
- preferably under 65 characters

Description rules:
- natural English
- explain the challenge
- encourage comments
- mention THINK FAST DAILY naturally

The final answer MUST exactly match one of A, B, C or D.
"""


print("Generating quiz...")
print("Interest signal:", topic)


response = client.models.generate_content(
    model=MODEL,
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.9
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


required = [
    "question",
    "options",
    "answer",
    "explanation",
    "hook",
    "difficulty",
    "category",
    "title",
    "description",
    "keywords",
    "hashtags"
]


for field in required:

    if field not in data:

        raise RuntimeError(
            f"Missing quiz field: {field}"
        )


# ============================================================
# VALIDATION
# ============================================================

if set(data["options"].keys()) != {
    "A",
    "B",
    "C",
    "D"
}:

    raise RuntimeError(
        "Quiz must contain exactly A/B/C/D options."
    )


if data["answer"] not in [
    "A",
    "B",
    "C",
    "D"
]:

    raise RuntimeError(
        "Invalid answer."
    )


question_normalized = (
    data["question"]
    .lower()
    .strip()
)


for old_question in recent_questions:

    if (
        question_normalized
        == old_question.lower().strip()
    ):

        raise RuntimeError(
            "Duplicate question detected."
        )


# ============================================================
# SAVE HISTORY
# ============================================================

history.append(data["question"])

history = history[-300:]


with open(
    HISTORY_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        history,
        f,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# SAVE METADATA
# ============================================================

data["channel"] = "THINK FAST DAILY"
data["topic_signal"] = topic
data["video_duration"] = DURATION
data["format"] = "YouTube Short"


with open(
    OUTPUT / "metadata.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        data,
        f,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# FONTS
# ============================================================

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


font_hook = ImageFont.truetype(
    FONT_BOLD,
    78
)

font_question = ImageFont.truetype(
    FONT_BOLD,
    58
)

font_option = ImageFont.truetype(
    FONT_BOLD,
    46
)

font_answer = ImageFont.truetype(
    FONT_BOLD,
    70
)

font_small = ImageFont.truetype(
    FONT_REGULAR,
    34
)

font_brand = ImageFont.truetype(
    FONT_BOLD,
    42
)

font_timer = ImageFont.truetype(
    FONT_BOLD,
    90
)


# ============================================================
# TEXT WRAPPING
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
    lines,
    font,
    center_y,
    spacing=75
):

    total_height = len(lines) * spacing

    y = center_y - total_height // 2

    for line in lines:

        box = draw.textbbox(
            (0, 0),
            line,
            font=font
        )

        width = box[2] - box[0]

        x = (WIDTH - width) // 2

        # shadow
        draw.text(
            (x + 4, y + 5),
            line,
            font=font,
            fill=(0, 0, 0)
        )

        draw.text(
            (x, y),
            line,
            font=font,
            fill=(245, 245, 250)
        )

        y += spacing


# ============================================================
# BACKGROUND
# ============================================================

random.seed(42)

particles = []

for _ in range(100):

    particles.append(
        (
            random.randint(20, WIDTH - 20),
            random.randint(20, HEIGHT - 20),
            random.randint(1, 4)
        )
    )


def create_background(frame):

    img = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (8, 12, 30)
    )

    draw = ImageDraw.Draw(img)

    # subtle gradient
    for y in range(HEIGHT):

        ratio = y / HEIGHT

        r = int(8 + ratio * 8)
        g = int(12 + ratio * 7)
        b = int(30 + ratio * 18)

        draw.line(
            [(0, y), (WIDTH, y)],
            fill=(r, g, b)
        )


    # animated particles

    for x, y, radius in particles:

        yy = int(
            (y + frame * 0.35)
            % HEIGHT
        )

        draw.ellipse(
            (
                x - radius,
                yy - radius,
                x + radius,
                yy + radius
            ),
            fill=(100, 120, 160)
        )


    return img, draw


# ============================================================
# FRAME
# ============================================================

question_lines = wrap_text(
    data["question"],
    font_question,
    860
)

hook_lines = wrap_text(
    data["hook"],
    font_hook,
    850
)

explanation_lines = wrap_text(
    data["explanation"],
    font_small,
    850
)


def create_frame(frame_number):

    img, draw = create_background(
        frame_number
    )


    # BRAND

    brand = "THINK FAST DAILY"

    box = draw.textbbox(
        (0, 0),
        brand,
        font=font_brand
    )

    brand_width = box[2] - box[0]

    draw.text(
        (
            (WIDTH - brand_width) // 2,
            90
        ),
        brand,
        font=font_brand,
        fill=(245, 205, 70)
    )


    # BRAIN SYMBOL

    draw.text(
        (70, 82),
        "🧠",
        font=font_brand
    )


    # HOOK 0-3 SEC

    if frame_number < FPS * 3:

        centered_text(
            draw,
            hook_lines,
            font_hook,
            650,
            100
        )


        small = "GET READY..."

        box = draw.textbbox(
            (0, 0),
            small,
            font=font_small
        )

        draw.text(
            (
                (WIDTH - (box[2] - box[0])) // 2,
                980
            ),
            small,
            font=font_small,
            fill=(180, 190, 215)
        )


    # QUESTION 3-10 SEC

    elif frame_number < FPS * 10:

        centered_text(
            draw,
            question_lines,
            font_question,
            470,
            75
        )


        labels = ["A", "B", "C", "D"]

        option_y = 820

        for index, label in enumerate(labels):

            y = option_y + index * 175

            draw.rounded_rectangle(
                (
                    110,
                    y,
                    970,
                    y + 125
                ),
                radius=28,
                outline=(80, 100, 150),
                width=3
            )

            text = (
                f"{label}. "
                f"{data['options'][label]}"
            )

            lines = wrap_text(
                text,
                font_option,
                730
            )

            centered_text(
                draw,
                lines,
                font_option,
                y + 62,
                58
            )


    # COUNTDOWN 10-15 SEC

    elif frame_number < FPS * 15:

        centered_text(
            draw,
            question_lines,
            font_question,
            410,
            75
        )


        remaining = 5 - int(
            (frame_number - FPS * 10) / FPS
        )

        remaining = max(
            1,
            min(5, remaining)
        )


        timer = str(remaining)

        box = draw.textbbox(
            (0, 0),
            timer,
            font=font_timer
        )

        draw.text(
            (
                (WIDTH - (box[2] - box[0])) // 2,
                750
            ),
            timer,
            font=font_timer,
            fill=(245, 205, 70)
        )


        draw.text(
            (380, 900),
            "LOCK IN YOUR ANSWER!",
            font=font_small,
            fill=(200, 210, 230)
        )


    # ANSWER 15-21 SEC

    elif frame_number < FPS * 21:

        answer = data["answer"]

        draw.text(
            (390, 450),
            "ANSWER",
            font=font_small,
            fill=(180, 190, 215)
        )


        answer_text = (
            f"{answer}. "
            f"{data['options'][answer]}"
        )

        answer_lines = wrap_text(
            answer_text,
            font_answer,
            850
        )

        centered_text(
            draw,
            answer_lines,
            font_answer,
            700,
            90
        )


        draw.text(
            (335, 1040),
            "DID YOU GET IT RIGHT? 👀",
            font=font_small,
            fill=(245, 205, 70)
        )


    # EXPLANATION 21-27 SEC

    elif frame_number < FPS * 27:

        draw.text(
            (370, 390),
            "WHY?",
            font=font_brand,
            fill=(245, 205, 70)
        )


        centered_text(
            draw,
            explanation_lines,
            font_small,
            700,
            55
        )


    # CTA 27-30 SEC

    else:

        centered_text(
            draw,
            [
                "HOW DID YOU DO?",
                "COMMENT YOUR ANSWER 👇"
            ],
            font_answer,
            650,
            100
        )


        draw.text(
            (345, 1050),
            "SUBSCRIBE FOR TOMORROW'S CHALLENGE ⚡",
            font=font_small,
            fill=(245, 205, 70)
        )


    # PROGRESS BAR

    progress = int(
        WIDTH *
        (frame_number + 1)
        / (FPS * DURATION)
    )

    draw.rectangle(
        (
            0,
            HEIGHT - 16,
            progress,
            HEIGHT
        ),
        fill=(245, 205, 70)
    )


    return img


# ============================================================
# GENERATE FRAMES
# ============================================================

print("========================================")
print("THINK FAST DAILY")
print("Generating video frames...")
print("========================================")


total_frames = FPS * DURATION


for i in range(total_frames):

    frame = create_frame(i)

    frame.save(
        FRAMES / f"frame_{i:05d}.png"
    )


print("Frames generated:", total_frames)
