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
    out_dir = Path("outputs") / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    print("1/4 Fetching transcript...")
    transcript_path = out_dir / "transcript.json"
    if transcript_path.exists():
        # Reuse the saved copy: it doesn't change, and YouTube may block repeat fetches.
        segments = json.loads(transcript_path.read_text())
        print(f"  reused {transcript_path}")
    else:
        segments = transcript.fetch_transcript(video_id)
        save_json(transcript_path, segments)
    transcript_text = transcript.format_for_prompt(segments)

    print("2/4 Extracting technical terms...")
    terms = llm.extract_terms(transcript_text)
    save_json(out_dir / "terms.json", [t.model_dump() for t in terms])
    if terms_only:
        print(f"Done: {len(terms)} terms. Score them with: python evals/eval_terms.py {video_id}")
        return

    print("3/4 Picking the key ideas...")
    ideas = llm.pick_ideas(transcript_text, terms)
    save_json(out_dir / "ideas.json", [i.model_dump() for i in ideas])

    print("4/4 Drafting cards...")
    cards = llm.draft_cards(transcript_text, ideas, terms)
    card_dicts = []
    for card in cards:
        card_dict = card.model_dump()
        card_dict["source_url"] = timestamp_url(video_id, card.start_seconds)
        card_dicts.append(card_dict)
    save_json(out_dir / "cards.json", card_dicts)

    apkg_path = out_dir / "deck.apkg"
    deck.build_deck(video_id, f"Lecture {video_id}", card_dicts, str(apkg_path))
    print(f"  saved {apkg_path}")
    print(f"Done: {len(terms)} terms, {len(ideas)} ideas, {len(cards)} cards.")


if __name__ == "__main__":
    args = sys.argv[1:]
    terms_only = "--terms" in args
    urls = [a for a in args if a != "--terms"]
    if len(urls) != 1:
        print(__doc__)
        sys.exit(1)
    main(urls[0], terms_only)
