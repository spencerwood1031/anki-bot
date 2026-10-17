"""Score the tool's vocab list against Spencer's hand-written one.

Usage:
    python make_deck.py https://youtu.be/aircAruvnKk --terms   # makes terms.json
    python evals/eval_terms.py aircAruvnKk

Compares outputs/<video_id>/terms.json with golden/<video_id>/jargon.txt.
Claude judges which terms mean the same thing; the scores are plain counting.
The report is printed and saved to outputs/<video_id>/eval_terms.json.
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Running this file directly only puts evals/ on Python's import path,
# so add the project folder too, to find the ankibot package.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from ankibot import llm  # noqa: E402  (must come after the path and .env setup)


def read_golden(video_id: str) -> list[str]:
    path = ROOT / "golden" / video_id / "jargon.txt"
    lines = [line.strip().lstrip("-• ").strip() for line in path.read_text().splitlines()]
    return [line for line in lines if line]


def main(video_id: str) -> None:
    golden = read_golden(video_id)
    if not golden:
        sys.exit(f"golden/{video_id}/jargon.txt is empty. Add one term per line first.")

    terms_path = ROOT / "outputs" / video_id / "terms.json"
    tool = [t["term"] for t in json.loads(terms_path.read_text())]

    matches = llm.match_terms(golden, tool)
    # Look golden terms up case-insensitively, in case Claude changed capitals when
    # echoing them back, and only trust tool terms that really are in the tool's list.
    answers = {m.golden_term.lower(): m.tool_term for m in matches}
    found = {}
    for g in golden:
        tool_term = answers.get(g.lower())
        if tool_term in tool:
            found[g] = tool_term

    missed = [g for g in golden if g not in found]
    matched_tool_terms = set(found.values())
    extra = [t for t in tool if t not in matched_tool_terms]

    # Recall: of your terms, how many did the tool find? ("did it miss anything?")
    # Precision: of the tool's terms, how many are on your list? ("did it add junk?")
    recall = len(found) / len(golden)
    precision = len(matched_tool_terms) / len(tool) if tool else 0.0

    report = {
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "golden_count": len(golden),
        "tool_count": len(tool),
        "matched": found,
        "missed": missed,
        "extra": extra,
    }
    out_path = ROOT / "outputs" / video_id / "eval_terms.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print(f"Recall:    {recall:.0%}  ({len(found)} of your {len(golden)} terms found)")
    print(f"Precision: {precision:.0%}  ({len(matched_tool_terms)} of its {len(tool)} terms are on your list)")
    print("\nMissed (on your list, not found):")
    for term in missed:
        print(f"  - {term}")
    print("\nExtra (found, not on your list):")
    for term in extra:
        print(f"  - {term}")
    print(f"\nsaved {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
