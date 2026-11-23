"""Run the whole pipeline several times on saved transcripts and score each deck.

Usage:
    python evals/bench.py wjZofJX0v4M WUvTyaaNkzM --runs 3 --label baseline

Needs outputs/<video_id>/transcript.json for each video (no YouTube fetch).
Each run is a real run (make_deck.build_cards) saved in
outputs/<video_id>/bench/<label>/run<n>/, then scored three ways:

  - Notes covered: of the points in answer-keys/<video_id>.md (distilled from
    Spencer's notes), how many does some card in the deck test? Skipped if
    there's no answer key.
  - Vocab kept:    of the deck's terms, how many break none of the vocab rules?
  - Ideas clean:   of the main-idea cards, how many break none of the card rules?

Claude judges each point and card; the scores are plain counting. Runs vary,
so read the average over the runs, not any single run. The summary is printed
and saved to outputs/bench_<label>.md.
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from ankibot import llm, transcript  # noqa: E402
from make_deck import build_cards  # noqa: E402


def read_key_vocab(path: Path) -> list[str]:
    """The answer key's '## Vocab' section: terms Spencer wrote in his notes."""
    if not path.exists() or "## Vocab" not in path.read_text():
        return []
    section = path.read_text().split("## Vocab", 1)[1].split("\n## ", 1)[0]
    return [line.strip() for line in section.splitlines() if line.strip() and not line.startswith("#")]


def read_key(path: Path) -> list[str]:
    """Answer-key points: every non-empty line that isn't a # comment or heading."""
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text().splitlines()
            if line.strip() and not line.startswith("#")]


def score_run(client, transcript_text: str, key: list[str], key_vocab: list[str],
              cards: list[dict], terms: list[dict]) -> dict:
    idea_cards = [c for c in cards if c["kind"] == "idea"]
    score = {"terms": len(terms), "idea_cards": len(idea_cards)}

    if key:
        coverage = llm.cover_notes(client, key, cards)
        covered = {c.golden_number for c in coverage if c.tool_numbers}
        score["notes_covered"] = len(covered) / len(key)
        score["missed_points"] = [p for n, p in enumerate(key, start=1) if n not in covered]

    vocab = llm.grade_vocab(client, transcript_text, terms, key_vocab)
    bad_terms = {g.tool_number: g.breaks for g in vocab if g.breaks}
    score["vocab_kept"] = 1 - len(bad_terms) / max(len(terms), 1)
    score["bad_terms"] = [
        f"{terms[n - 1]['term']}: " + "; ".join(f"rule {b.rule}: {b.reason}" for b in breaks)
        for n, breaks in bad_terms.items() if 0 < n <= len(terms)
    ]

    grades = llm.grade_cards(client, idea_cards)
    bad_cards = {g.tool_number: g.breaks for g in grades if g.breaks}
    score["ideas_clean"] = 1 - len(bad_cards) / max(len(idea_cards), 1)
    score["bad_cards"] = [
        f"{idea_cards[n - 1]['front']} -> {idea_cards[n - 1]['back']}: "
        + "; ".join(f"rule {b.rule}: {b.reason}" for b in breaks)
        for n, breaks in bad_cards.items() if 0 < n <= len(idea_cards)
    ]
    return score


def one_run(client, outputs: Path, keys: Path, video_id: str, label: str, n: int, rescore: bool) -> dict:
    out_dir = outputs / video_id / "bench" / label / f"run{n}"
    out_dir.mkdir(parents=True, exist_ok=True)
    segments = json.loads((outputs / video_id / "transcript.json").read_text())
    transcript_text = transcript.format_for_prompt(segments)
    try:
        if rescore:  # score the decks already saved, without new runs
            cards = json.loads((out_dir / "cards.json").read_text())
            terms = json.loads((out_dir / "terms.json").read_text())
        else:
            cards, terms, _ = build_cards(client, video_id, transcript_text, out_dir)
            terms = [t.model_dump() for t in terms]
        key_path = keys / f"{video_id}.md"
        score = score_run(client, transcript_text, read_key(key_path), read_key_vocab(key_path), cards, terms)
    except Exception as error:  # one failed run shouldn't sink the others
        score = {"error": str(error)}
    (out_dir / "score.json").write_text(json.dumps(score, indent=2, ensure_ascii=False))
    return {"video": video_id, "run": n, **score}


def pct(values: list[float]) -> str:
    return f"{100 * sum(values) / len(values):.0f}%" if values else "–"


def summary(results: list[dict], label: str) -> str:
    lines = [f"# Bench: {label}", "",
             "| Video | Runs | Notes covered | Vocab kept | Ideas clean | Terms | Idea cards |",
             "|---|---|---|---|---|---|---|"]
    for video in dict.fromkeys(r["video"] for r in results):
        ok = [r for r in results if r["video"] == video and "error" not in r]
        lines.append(
            f"| {video} | {len(ok)} | {pct([r['notes_covered'] for r in ok if 'notes_covered' in r])} "
            f"| {pct([r['vocab_kept'] for r in ok])} | {pct([r['ideas_clean'] for r in ok])} "
            f"| {sum(r['terms'] for r in ok) / max(len(ok), 1):.0f} "
            f"| {sum(r['idea_cards'] for r in ok) / max(len(ok), 1):.0f} |"
        )
    for r in results:
        lines += ["", f"## {r['video']} run {r['run']}"]
        if "error" in r:
            lines.append(f"Error: {r['error']}")
            continue
        for heading, key in [("Missed points", "missed_points"), ("Weak terms", "bad_terms"),
                             ("Rule-breaking idea cards", "bad_cards")]:
            if r.get(key):
                lines.append(f"**{heading}**")
                lines += [f"- {item}" for item in r[key]]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("videos", nargs="+")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--label", default="latest")
    parser.add_argument("--outputs", type=Path, default=ROOT / "outputs")
    parser.add_argument("--keys", type=Path, default=ROOT / "answer-keys")
    parser.add_argument("--rescore", action="store_true", help="re-score saved decks without new runs")
    args = parser.parse_args()

    client = llm.make_client()
    jobs = [(v, n) for v in args.videos for n in range(1, args.runs + 1)]
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        results = list(pool.map(lambda job: one_run(client, args.outputs, args.keys, job[0], args.label, job[1], args.rescore), jobs))

    report = summary(results, args.label)
    (args.outputs / f"bench_{args.label}.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
