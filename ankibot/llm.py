"""Step 2: the three Claude calls (terms, ideas, cards).

Each function sends one prompt and gets back structured data. We describe
the shape we want with small Pydantic classes, and `client.messages.parse`
makes Claude return exactly that shape, so we never have to scrape JSON
out of free text.
"""

from typing import Literal

import anthropic
from pydantic import BaseModel

from ankibot import prompts

# One place to change the model for every call.
MODEL = "claude-opus-5-5"

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment


# ---- The shapes we ask Claude to return ----

class Term(BaseModel):
    term: str
    definition: str  # one sentence, as used in this lecture


class TermList(BaseModel):
    terms: list[Term]


class Idea(BaseModel):
    idea: str            # the idea stated in one sentence
    why_it_matters: str  # one sentence on why it's worth remembering
    start_seconds: int   # where in the video it's explained


class IdeaList(BaseModel):
    ideas: list[Idea]


class Card(BaseModel):
    card_type: Literal["basic", "cloze"]
    front: str           # basic: the question. cloze: text with {{c1::...}}
    back: str            # basic: the answer. cloze: optional extra context
    start_seconds: int   # timestamp the source link will point to


class CardList(BaseModel):
    cards: list[Card]


# ---- The three calls ----

def _ask(system: str, user: str, output_shape: type[BaseModel]) -> BaseModel:
    """Send one prompt and return Claude's answer as an instance of output_shape."""
    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=output_shape,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined this request.")
    return response.parsed_output


def extract_terms(transcript_text: str) -> list[Term]:
    result = _ask(
        prompts.TERMS_SYSTEM,
        prompts.terms_user(transcript_text),
        TermList,
    )
    return result.terms


def pick_ideas(transcript_text: str, terms: list[Term]) -> list[Idea]:
    result = _ask(
        prompts.IDEAS_SYSTEM,
        prompts.ideas_user(transcript_text, terms),
        IdeaList,
    )
    return result.ideas


def draft_cards(transcript_text: str, ideas: list[Idea], terms: list[Term]) -> list[Card]:
    result = _ask(
        prompts.cards_system(),
        prompts.cards_user(transcript_text, ideas, terms),
        CardList,
    )
    return result.cards
