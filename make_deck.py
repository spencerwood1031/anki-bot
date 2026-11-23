"""Turn a YouTube lecture into an Anki deck.

Usage:
    python make_deck.py https://youtu.be/aircAruvnKk          # full run: vocab + concept cards
    python make_deck.py https://youtu.be/aircAruvnKk --terms  # vocab list only

Run 1 (--terms) just lists the technical vocab, so you can check it against
golden/<video_id>/jargon.txt with evals/eval_terms.py.
Run 2 (no flag) goes on to the key ideas and writes conceptual cards.

Everything is saved to outputs/<video_id>/.
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # puts ANTHROPIC_API_KEY from .env into the environment

from ankibot import deck, llm, transcript  # noqa: E402  (must come after load_dotenv)
from ankibot.links import timestamp_url  # noqa: E402


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"  saved {path}")


def main(url: str, terms_only: bool = False) -> None:
    video_id = transcript.get_video_id(url)
    client = llm.make_client()
    out_dir = Path("outputs") / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    print("1/5 Fetching transcript...")
    transcript_path = out_dir / "transcript.json"
    if transcript_path.exists():
        # Reuse the saved copy: it doesn't change, and YouTube may block repeat fetches.
        segments = json.loads(transcript_path.read_text())
        print(f"  reused {transcript_path}")
    else:
        segments = transcript.fetch_transcript(video_id)
        save_json(transcript_path, segments)
    transcript_text = transcript.format_for_prompt(segments)

    print("2/5 Extracting technical terms...")
    term_list = llm.extract_terms(client, transcript_text)
    terms = term_list.terms
    save_json(out_dir / "terms.json", [t.model_dump() for t in terms])
    if terms_only:
        print(f"Done: {len(terms)} terms. Score them with: python evals/eval_terms.py {video_id}")
        return

    card_dicts, terms, ideas = build_cards(client, video_id, transcript_text, out_dir, terms)

    apkg_path = out_dir / "deck.apkg"
    deck.build_deck(video_id, f"Lecture {video_id}", card_dicts, str(apkg_path))
    print(f"  saved {apkg_path}")
    print(f"Done: {len(terms)} terms, {len(ideas)} ideas, {len(card_dicts)} cards.")


def build_cards(client, video_id: str, transcript_text: str, out_dir: Path, terms=None):
    """Steps 3-5: key ideas, card drafts and the rules check. Saves each step's
    output in out_dir and returns (card dicts, checked terms, ideas).
    evals/bench.py calls this too, so a benchmark run is exactly a real run."""
    if terms is None:
        terms = llm.extract_terms(client, transcript_text).terms
        save_json(out_dir / "draft_terms.json", [t.model_dump() for t in terms])

    print("3/5 Picking the key ideas...")
    ideas = llm.pick_ideas(client, transcript_text, terms)
    save_json(out_dir / "ideas.json", [i.model_dump() for i in ideas])

    print("4/5 Drafting cards...")
    cards = llm.draft_cards(client, transcript_text, ideas, terms)
    save_json(out_dir / "draft_cards.json", [c.model_dump() for c in cards])

    print("5/5 Checking the draft against the card rules...")
    review = llm.review_deck(client, transcript_text, terms, cards)
    save_json(out_dir / "review.json", review.model_dump())
    for item in [*review.terms, *review.cards]:
        if item.note:
            print(f"  - {item.note}")
    for line in review.cut:
        print(f"  - Cut: {line}")
    terms, cards = review.terms, review.cards
    save_json(out_dir / "terms.json", [t.model_dump() for t in terms])  # the checked list

    # Vocab cards come straight from the terms list; Claude writes the idea cards.
    card_dicts = llm.vocab_cards(terms)
    card_dicts += [{"kind": "idea", **card.model_dump()} for card in cards]
    for card_dict in card_dicts:
        card_dict["source_url"] = timestamp_url(video_id, card_dict["start_seconds"])
    save_json(out_dir / "cards.json", card_dicts)
    return card_dicts, terms, ideas


if __name__ == "__main__":
    args = sys.argv[1:]
    terms_only = "--terms" in args
    urls = [a for a in args if a != "--terms"]
    if len(urls) != 1:
        print(__doc__)
        sys.exit(1)
    main(urls[0], terms_only)
