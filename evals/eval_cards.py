"""Score the tool's cards against Spencer's hand-written ones.

Usage:
    python make_deck.py <url>                          # makes cards.json
    python evals/eval_cards.py <video_id>
    python evals/eval_cards.py <video_id> --until 3600  # only cards from the first hour

Compares the main-idea cards in outputs/<video_id>/cards.json with
golden/<video_id>/cards.md (your main-idea cards only; vocab lives in jargon.txt) and
gives three numbers:
  - Recall:    of your cards, how many does the tool have a matching card for?
  - Precision: of the tool's cards, how many match one of yours?
  - Rule pass: of the tool's cards, how many break none of the 10 card rules?
Claude does the judging (which cards match, which rules a card breaks); the
scores are plain counting. The report is printed and saved to
outputs/<video_id>/eval_cards.json.

cards.md format: one card per block, with blocks separated by a blank line.
Write a card however reads best, e.g. "Q: ... A: ..." or a {{c1::cloze}}.
Lines starting with # are notes and headings, and are ignored.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from ankibot import llm  # noqa: E402  (must come after the path and .env setup)


def read_golden(video_id: str) -> list[str]:
    """Split cards.md into cards: each blank-line-separated block is one card."""
    text = (ROOT / "golden" / video_id / "cards.md").read_text()
    cards = []
    for block in text.split("\n\n"):
        lines = [line.strip().lstrip("-• ").strip() for line in block.splitlines()]
        lines = [line for line in lines if line and not line.startswith("#")]
        if lines:
            cards.append(" ".join(lines))
    return cards


def main(video_id: str, until: int | None) -> None:
    golden = read_golden(video_id)
    if not golden:
        sys.exit(f"golden/{video_id}/cards.md has no cards yet.")

    tool = json.loads((ROOT / "outputs" / video_id / "cards.json").read_text())
    # Vocab cards are scored by eval_terms.py, so only compare main-idea cards.
    tool = [c for c in tool if c.get("kind", "idea") == "idea"]
    if until is not None:
        # Only compare the part of the video Spencer wrote cards for.
        tool = [c for c in tool if c["start_seconds"] <= until]

    client = llm.make_client()
    coverage = llm.cover_cards(client, golden, tool)
    grades = llm.grade_cards(client, tool)

    # Card numbers in the prompt start at 1 (G1, T1); list positions start at 0.
    matched = {}  # golden card -> list of matching tool cards
    for c in coverage:
        if 1 <= c.golden_number <= len(golden):
            hits = [tool[n - 1]["front"] for n in c.tool_numbers if 1 <= n <= len(tool)]
            if hits:
                matched[golden[c.golden_number - 1]] = hits
    missed = [g for g in golden if g not in matched]
    used_tool_fronts = {front for hits in matched.values() for front in hits}
    extra = [c["front"] for c in tool if c["front"] not in used_tool_fronts]

    problems = {}  # tool card front -> list of "rule N: reason"
    rule_counts = Counter()  # rule number -> how many cards break it
    for g in grades:
        if g.breaks and 1 <= g.tool_number <= len(tool):
            problems[tool[g.tool_number - 1]["front"]] = [f"rule {b.rule}: {b.reason}" for b in g.breaks]
            rule_counts.update(b.rule for b in g.breaks)

    recall = len(matched) / len(golden)
    precision = len(used_tool_fronts) / len(tool) if tool else 0.0
    rule_pass = (len(tool) - len(problems)) / len(tool) if tool else 0.0

    report = {
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "rule_pass": round(rule_pass, 3),
        "golden_count": len(golden),
        "tool_count": len(tool),
        "until_seconds": until,
        "broken_rule_counts": {f"rule {r}": n for r, n in sorted(rule_counts.items())},
        "matched": matched,
        "missed": missed,
        "extra": extra,
        "problems": problems,
    }
    out_path = ROOT / "outputs" / video_id / "eval_cards.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print(f"Recall:    {recall:.0%}  ({len(matched)} of your {len(golden)} cards covered)")
    print(f"Precision: {precision:.0%}  ({len(used_tool_fronts)} of its {len(tool)} cards match one of yours)")
    print(f"Rule pass: {rule_pass:.0%}  ({len(tool) - len(problems)} of its {len(tool)} cards break no rules)")
    print("\nMost broken rules:")
    for rule, n in rule_counts.most_common():
        print(f"  rule {rule}: {n} cards")
    print("\nMissed (your cards with no match):")
    for card in missed:
        print(f"  - {card}")
    print("\nCards that break rules:")
    for front, reasons in problems.items():
        print(f"  - {front}")
        for reason in reasons:
            print(f"      {reason}")
    print(f"\nsaved {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score the tool's cards against golden/<video_id>/cards.md.")
    parser.add_argument("video_id")
    parser.add_argument("--until", type=int, help="only use tool cards up to this many seconds into the video")
    args = parser.parse_args()
    main(args.video_id, args.until)
