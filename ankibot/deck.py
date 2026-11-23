"""Step 3: turn cards into an Anki .apkg file with genanki.

Math on cards is LaTeX between \\( and \\) (card rule 22). Anki draws it
itself with its built-in MathJax, so no add-on is needed.
"""

import html
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


def build_deck(deck_key: str, title: str, cards: list[dict], path: str) -> None:
    """Write cards (dicts with card_type, front, back, source_url) to an .apkg.
    deck_key is the video id (or page link): the same key gives the same deck,
    so re-importing updates it instead of making a copy."""
    deck_id = zlib.crc32(deck_key.encode())
    deck = genanki.Deck(deck_id, title)

    for card in cards:
        # Anki fields are HTML, so card text is escaped: a "<" in "\(x < y\)"
        # must reach Anki as text, not as the start of an HTML tag.
        front, back = html.escape(card["front"], quote=False), html.escape(card.get("back", ""), quote=False)
        source = f'<a href="{card["source_url"]}">Watch this part</a>' if card.get("source_url") else ""
        # A hidden Anki tag says which kind of card it is, so it can be filtered in Anki.
        tags = ["vocab"] if card.get("kind") == "vocab" else ["main-idea"]
        if card["card_type"] == "cloze":
            # No extra context on fill-in-the-blank cards.
            note = genanki.Note(model=CLOZE_MODEL, fields=[front, "", source], tags=tags)
        else:
            note = genanki.Note(model=BASIC_MODEL, fields=[front, back, source], tags=tags)
        deck.add_note(note)

    genanki.Package(deck).write_to_file(path)
