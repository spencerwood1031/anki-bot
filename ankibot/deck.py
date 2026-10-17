"""Step 3: turn cards into an Anki .apkg file with genanki."""

import zlib

import genanki

# Anki identifies note types by a number. These must stay the same forever,
# otherwise re-importing a deck would create duplicate note types in Anki.
# (They're just random numbers picked once.)
BASIC_MODEL_ID = 1607392319
CLOZE_MODEL_ID = 1607392320

CARD_CSS = """
.card { font-family: arial; font-size: 20px; text-align: center; }
.source { font-size: 14px; margin-top: 20px; }
"""

BASIC_MODEL = genanki.Model(
    BASIC_MODEL_ID,
    "Anki Bot Basic",
    fields=[{"name": "Front"}, {"name": "Back"}, {"name": "Source"}],
    templates=[{
        "name": "Card 1",
        "qfmt": "{{Front}}",
        "afmt": '{{FrontSide}}<hr id="answer">{{Back}}'
                '<div class="source">{{Source}}</div>',
    }],
    css=CARD_CSS,
)

CLOZE_MODEL = genanki.Model(
    CLOZE_MODEL_ID,
    "Anki Bot Cloze",
    fields=[{"name": "Text"}, {"name": "Extra"}, {"name": "Source"}],
    templates=[{
        "name": "Cloze",
        "qfmt": "{{cloze:Text}}",
        "afmt": "{{cloze:Text}}<br>{{Extra}}"
                '<div class="source">{{Source}}</div>',
    }],
    css=CARD_CSS,
    model_type=genanki.Model.CLOZE,
)


def build_deck(video_id: str, title: str, cards: list[dict], path: str) -> None:
    """Write cards (dicts with card_type, front, back, source_url) to an .apkg."""
    # A stable deck id per video, so re-importing updates the same deck.
    deck_id = zlib.crc32(video_id.encode())
    deck = genanki.Deck(deck_id, title)

    for card in cards:
        source = f'<a href="{card["source_url"]}">Watch this part</a>'
        if card["card_type"] == "cloze":
            note = genanki.Note(model=CLOZE_MODEL, fields=[card["front"], card["back"], source])
        else:
            note = genanki.Note(model=BASIC_MODEL, fields=[card["front"], card["back"], source])
        deck.add_note(note)

    genanki.Package(deck).write_to_file(path)
