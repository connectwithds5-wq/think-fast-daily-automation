import json
import re
from pathlib import Path
from difflib import SequenceMatcher
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
FRAMES = OUTPUT / "think_fast_daily_frames"
HISTORY = ROOT / "think_fast_history.json"
METADATA = OUTPUT / "metadata.json"

WIDTH, HEIGHT, FPS, DURATION = 1080, 1920, 30, 35
TOTAL_FRAMES = FPS * DURATION

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

QUESTIONS = [
    {"category":"science", "hook":"Only sharp minds get this one!", "question":"Which planet has the most prominent ring system?", "options":{"A":"Mars","B":"Saturn","C":"Venus","D":"Mercury"}, "answer":"B", "explanation":"Saturn has the most extensive and visually prominent ring system in our solar system."},
    {"category":"animal", "hook":"Can you guess this animal fact?", "question":"Which animal is known for changing its skin color to communicate and camouflage?", "options":{"A":"Chameleon","B":"Penguin","C":"Elephant","D":"Giraffe"}, "answer":"A", "explanation":"Chameleons can change color for communication, temperature regulation, and camouflage."},
    {"category":"geography", "hook":"Quick geography challenge!", "question":"Which is the largest ocean on Earth?", "options":{"A":"Atlantic","B":"Indian","C":"Pacific","D":"Arctic"}, "answer":"C", "explanation":"The Pacific Ocean is the largest and deepest ocean on Earth."},
    {"category":"space", "hook":"Space fans, get this right!", "question":"What is the closest star to Earth after the Sun?", "options":{"A":"Sirius","B":"Polaris","C":"Proxima Centauri","D":"Betelgeuse"}, "answer":"C", "explanation":"Proxima Centauri is the closest known star to the Sun, about 4.24 light-years away."},
    {"category":"science", "hook":"One tiny clue gives it away!", "question":"Which gas do plants mainly absorb from the air for photosynthesis?", "options":{"A":"Oxygen","B":"Nitrogen","C":"Helium","D":"Carbon dioxide"}, "answer":"D", "explanation":"Plants absorb carbon dioxide and use it with water and light to make sugars during photosynthesis."},
    {"category":"animal", "hook":"This animal question looks easy...", "question":"Which animal is the fastest land animal?", "options":{"A":"Cheetah","B":"Horse","C":"Lion","D":"Ostrich"}, "answer":"A", "explanation":"The cheetah is the fastest land animal, capable of very high speeds over short distances."},
    {"category":"geography", "hook":"Can you beat the clock?", "question":"Which country is shaped like a boot?", "options":{"A":"Spain","B":"Italy","C":"Greece","D":"Portugal"}, "answer":"B", "explanation":"Italy's distinctive peninsula is commonly described as having the shape of a boot."},
    {"category":"trivia", "hook":"Most people rush this answer!", "question":"How many sides does a hexagon have?", "options":{"A":"Five","B":"Six","C":"Seven","D":"Eight"}, "answer":"B", "explanation":"A hexagon is a polygon with six sides."},
    {"category":"science", "hook":"Think before you choose!", "question":"What force keeps planets in orbit around the Sun?", "options":{"A":"Magnetism","B":"Friction","C":"Gravity","D":"Electricity"}, "answer":"C", "explanation":"The Sun's gravity provides the force that keeps planets in their orbital paths."},
    {"category":"space", "hook":"A cosmic question in five seconds!", "question":"Which planet is known as the Red Planet?", "options":{"A":"Jupiter","B":"Mars","C":"Neptune","D":"Uranus"}, "answer":"B", "explanation":"Mars appears reddish because iron minerals in its surface rocks have oxidized, or rusted."},
    {"category":"trivia", "hook":"Can you solve this instantly?", "question":"Which number comes next: 2, 4, 8, 16, ?", "options":{"A":"18","B":"24","C":"32","D":"34"}, "answer":"C", "explanation":"Each number is doubled, so 16 multiplied by 2 gives 32."},
    {"category":"geography", "hook":"Here's a sneaky geography test!", "question":"Which continent is the Sahara Desert located in?", "options":{"A":"Asia","B":"Africa","C":"Australia","D":"South America"}, "answer":"B", "explanation":"The Sahara stretches across much of North Africa and is the world's largest hot desert."},
    {"category":"animal", "hook":"Animal experts, your turn!", "question":"Which bird is famous for being unable to fly?", "options":{"A":"Eagle","B":"Sparrow","C":"Penguin","D":"Swallow"}, "answer":"C", "explanation":"Penguins are flightless birds whose wings are adapted into flippers for swimming."},
    {"category":"science", "hook":"This one tests basic science!", "question":"At sea level, water normally boils at what temperature?", "options":{"A":"50°C","B":"75°C","C":"100°C","D":"125°C"}, "answer":"C", "explanation":"At standard atmospheric pressure, water boils at 100 degrees Celsius."},
    {"category":"trivia", "hook":"Five seconds. Pick wisely!", "question":"Which shape has exactly three sides?", "options":{"A":"Square","B":"Triangle","C":"Pentagon","D":"Circle"}, "answer":"B", "explanation":"A triangle is a polygon with exactly three sides and three angles."},
    {"category":"space", "hook":"Only one answer fits!", "question":"Which object is at the center of our solar system?", "options":{"A":"Earth","B":"Moon","C":"Sun","D":"Jupiter"}, "answer":"C", "explanation":"The Sun is the central star of our solar system and contains most of its mass."},
    {"category":"geography", "hook":"World map challenge!", "question":"Which is the smallest continent by land area?", "options":{"A":"Europe","B":"Australia","C":"Antarctica","D":"South America"}, "answer":"B", "explanation":"Australia is the smallest continent by land area."},
    {"category":"animal", "hook":"Do you know your animals?", "question":"Which animal is commonly called the ship of the desert?", "options":{"A":"Camel","B":"Zebra","C":"Yak","D":"Llama"}, "answer":"A", "explanation":"Camels are adapted to desert travel and are traditionally called ships of the desert."},
    {"category":"science", "hook":"Quick science brain test!", "question":"Which organ pumps blood around the human body?", "options":{"A":"Lung","B":"Brain","C":"Heart","D":"Liver"}, "answer":"C", "explanation":"The heart is a muscular organ that pumps blood through the body's circulatory system."},
    {"category":"trivia", "hook":"Don't overthink this one!", "question":"How many days are there in a leap year?", "options":{"A":"364","B":"365","C":"366","D":"367"}, "answer":"C", "explanation":"A leap year has 366 days because February gets an extra day."},
]


def load_history():
    try:
        data = json.loads(HISTORY.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def norm(s):
    return re.sub(r"\\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(s).lower())).strip()


def duplicate(q, history):
    n = norm(q)
    for item in history:
        old = item.get("question", "") if isinstance(item, dict) else str(item)
        if n == norm(old) or SequenceMatcher(None, n, norm(old)).ratio() >= 0.88:
            return True
    return False


def wrap(draw, text, font, max_width):
    words = str(text).split()
    lines, cur = [], ""
    for word in words:
        test = f"{cur} {word}".strip()
        if draw.textbbox((0,0), test, font=font)[2] <= max_width:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = word
    if cur: lines.append(cur)
    return lines


def centered(draw, text, font, y, max_width=900, fill=(245,245,250)):
    lines = wrap(draw, text, font, max_width)
    spacing = int(font.size * 1.28)
    start = y - (len(lines) * spacing) // 2
    for line in lines:
        box = draw.textbbox((0,0), line, font=font)
        x = (WIDTH - (box[2]-box[0])) // 2
        draw.text((x+4,start+5), line, font=font, fill=(0,0,0))
        draw.text((x,start), line, font=font, fill=fill)
        start += spacing


def make_frame(index, data, phase):
    img = Image.new("RGB", (WIDTH, HEIGHT), (10, 14, 30))
    d = ImageDraw.Draw(img)
    bold70 = ImageFont.truetype(FONT_BOLD, 70)
    bold52 = ImageFont.truetype(FONT_BOLD, 52)
    bold44 = ImageFont.truetype(FONT_BOLD, 44)
    bold38 = ImageFont.truetype(FONT_BOLD, 38)
    reg34 = ImageFont.truetype(FONT_REG, 34)

    d.text((WIDTH//2, 70), "THINK FAST DAILY", anchor="ma", font=bold38, fill=(245,200,80))
    d.text((WIDTH//2, 150), "⚡ QUICK BRAIN CHALLENGE", anchor="ma", font=reg34, fill=(175,185,210))

    if phase == "hook":
        centered(d, data["hook"], bold70, 720)
        centered(d, "READY?", bold52, 1020, fill=(245,200,80))
    elif phase == "question":
        centered(d, data["question"], bold52, 500)
        y = 780
        for key in "ABCD":
            box = (90, y-65, 990, y+65)
            d.rounded_rectangle(box, radius=28, outline=(80,130,230), width=5)
            centered(d, f"{key}  {data['options'][key]}", bold44, y, max_width=820)
            y += 190
    elif phase == "countdown":
        centered(d, "LOCK IN YOUR ANSWER", bold52, 500)
        remaining = 5 - min(4, int(index / FPS) - 16)
        centered(d, str(max(1, remaining)), ImageFont.truetype(FONT_BOLD, 170), 950, fill=(245,200,80))
    elif phase == "answer":
        centered(d, "CORRECT ANSWER", bold52, 500, fill=(245,200,80))
        centered(d, f"OPTION {data['answer']}", bold70, 800)
        centered(d, data["options"][data["answer"]], bold52, 1030)
    elif phase == "explanation":
        centered(d, "HERE'S WHY", bold52, 500, fill=(245,200,80))
        centered(d, data["explanation"], bold44, 850, max_width=850)
    else:
        centered(d, "DID YOU GET IT RIGHT?", bold52, 620)
        centered(d, "Comment A, B, C or D", bold44, 900, fill=(245,200,80))
        centered(d, "Follow for tomorrow's challenge!", reg34, 1110)

    d.text((WIDTH//2, 1810), f"#{data['category'].replace(' ', '')}  •  THINK FAST DAILY", anchor="mm", font=reg34, fill=(140,150,180))
    return img


history = load_history()
selected = None
for item in QUESTIONS:
    if not duplicate(item["question"], history):
        selected = item
        break
if selected is None:
    selected = QUESTIONS[len(history) % len(QUESTIONS)]

data = dict(selected)
data.update({
    "visual_type": "brain",
    "visual_prompt": "Clean mystery brain challenge graphic.",
    "title": f"{selected['hook']} {selected['question']} #shorts",
    "description": f"Test your brain with this quick {selected['category']} challenge. Can you get the correct answer in five seconds? Comment your answer!",
    "keywords": ["brain quiz", "iq quiz", "guess the answer", "brain challenge", "puzzle", "trivia", "think fast daily", "shorts"],
    "hashtags": ["#brainquiz", "#iqquiz", "#guess", "#brainchallenge", "#puzzle", "#trivia", "#shorts", "#thinkfastdaily"],
    "channel": "THINK FAST DAILY",
    "duration": DURATION,
    "generation_source": "offline_fallback"
})

OUTPUT.mkdir(parents=True, exist_ok=True)
FRAMES.mkdir(parents=True, exist_ok=True)
for old in FRAMES.glob("frame_*.png"):
    old.unlink()

for i in range(TOTAL_FRAMES):
    sec = i / FPS
    if sec < 3: phase = "hook"
    elif sec < 16: phase = "question"
    elif sec < 21: phase = "countdown"
    elif sec < 25: phase = "answer"
    elif sec < 31: phase = "explanation"
    else: phase = "cta"
    make_frame(i, data, phase).save(FRAMES / f"frame_{i:05d}.png", optimize=True)

history.append({"question": data["question"], "answer": data["answer"], "category": data["category"], "title": data["title"], "source": "offline_fallback"})
HISTORY.write_text(json.dumps(history[-500:], ensure_ascii=False, indent=2), encoding="utf-8")
METADATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("OFFLINE FALLBACK SUCCESS")
print("Question:", data["question"])
print("Answer:", data["answer"], data["options"][data["answer"]])
print("Frames:", TOTAL_FRAMES)
