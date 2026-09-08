"""Inject the latest strategy into the quiz prompt without permanently rewriting it."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRATEGY = ROOT / "think_fast_strategy.json"
GENERATOR = ROOT / "src" / "think_fast_daily_generate.py"


def main():
    if not STRATEGY.exists():
        print("No think_fast_strategy.json; using normal generator.")
        return
    data = json.loads(STRATEGY.read_text(encoding="utf-8"))
    directions = data.get("next_best_quiz_directions") or []
    if not directions:
        print("No recommended quiz directions; using normal generator.")
        return
    d = directions[0]
    directive = f'''
STRATEGY ENGINE DIRECTIVE — USE THIS FOR THIS VIDEO

Latest THINK FAST DAILY performance analysis selected this direction.
Create a FRESH quiz; do not copy existing wording or questions.
Recommended topic: {d.get("topic", "")}
Recommended hook: {d.get("hook", "")}
Recommended visual type: {d.get("visual_type", "")}
Why selected: {d.get("reason", "")}
Confidence: {d.get("confidence", data.get("confidence", "low"))}

Strategy rules:
- Follow the recommended direction unless it conflicts with accuracy or safety.
- Keep the question instantly understandable and answerable as A/B/C/D.
- Maximize curiosity and participation without making the answer ambiguous.
- Use a visually obvious clue that does NOT reveal the answer early.
- Never repeat a recent question or merely reword it.
'''.strip()
    source = GENERATOR.read_text(encoding="utf-8")
    marker = 'prompt = f"""'
    pos = source.find(marker)
    if pos < 0:
        raise RuntimeError("Could not find quiz prompt block")
    start = pos + len(marker)
    if "STRATEGY ENGINE DIRECTIVE — USE THIS FOR THIS VIDEO" in source:
        print("Strategy directive already present in generator workspace.")
        return
    source = source[:start] + "\n" + directive + "\n\n" + source[start:]
    GENERATOR.write_text(source, encoding="utf-8")
    print("AI strategy injected:", d.get("topic", ""))

if __name__ == "__main__":
    main()
