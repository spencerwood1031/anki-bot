"""Turn a YouTube lecture into an Anki deck.

Usage:
    python make_deck.py https://youtu.be/aircAruvnKk

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


def main(url: str) -> None:
    video_id = transcript.get_video_id(url)
    out_dir = Path("outputs") / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    print("1/4 Fetching transcript...")
    segments = transcript.fetch_transcript(video_id)
    save_json(out_dir / "transcript.json", segments)
    transcript_text = transcript.format_for_prompt(segments)

    print("2/4 Extracting technical terms...")
    terms = llm.extract_terms(transcript_text)
    save_json(out_dir / "terms.json", [t.model_dump() for t in terms])

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
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
