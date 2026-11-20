"""Step 2: the Claude calls (terms, ideas, cards, plus the eval's term matching).

Each function sends one prompt and gets back structured data. We describe
the shape we want with small Pydantic classes, and `client.messages.parse`
makes Claude return exactly that shape, so we never have to scrape JSON
out of free text.
"""

import os
from typing import Literal

import anthropic
from anthropic.lib._parse._transform import transform_schema
from pydantic import BaseModel, TypeAdapter

from ankibot import prompts

# One place to change the model for every call.
MODEL = "claude-opus-5-5"
# How hard Claude thinks. This model defaults to "medium"; at that level the
# cards step sometimes gave up and returned a blank or placeholder card.
EFFORT = "high"



def make_client(api_key: str | None = None) -> anthropic.Anthropic:
    """Make a Claude client. Every call below takes one as its first argument.

    The website passes in the visitor's own key. Scripts pass nothing, and the
    key comes from ANKI_BOT_API_KEY if set, otherwise ANTHROPIC_API_KEY. (The
    separate name is for cloud sessions, where ANTHROPIC_API_KEY is reserved
    for Claude Code's own login.)

    Why not one shared client? On the website several visitors can make decks
    at once, each with their own key, so each run needs its own client.
    """
    if api_key is None:
        api_key = os.environ.get("ANKI_BOT_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    return anthropic.Anthropic(api_key=api_key)


# ---- The shapes we ask Claude to return ----

class Term(BaseModel):
    term: str
    definition: str      # one short clause, as used in this lecture
    start_seconds: int   # where the term first comes up


class TermList(BaseModel):
    topic: str           # short label for the lecture's subject, e.g. "LLMs"
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


class Review(BaseModel):
    changes: list[str]   # one short note per change: what and which rule
    terms: list[Term]    # the whole fixed term list
    cards: list[Card]    # the whole fixed list of main-idea cards


class SuggestedCard(BaseModel):
    card_type: Literal["basic", "cloze"]
    front: str
    back: str


class Suggestion(BaseModel):
    why: str                     # one or two sentences: which rules the rewrite fixes
    cards: list[SuggestedCard]   # usually one; more if the original held several ideas


class TermMatch(BaseModel):
    golden_term: str
    tool_term: str | None  # None when the tool missed this golden term


class MatchList(BaseModel):
    matches: list[TermMatch]


class Coverage(BaseModel):
    golden_number: int        # G1 -> 1
    tool_numbers: list[int]   # T3, T7 -> [3, 7]; empty when the tool missed it


class CoverageList(BaseModel):
    coverage: list[Coverage]


class RuleBreak(BaseModel):
    rule: int     # 1-10, the rule number in CLAUDE.md
    reason: str   # one short sentence


class Grade(BaseModel):
    tool_number: int
    breaks: list[RuleBreak]   # empty when the card follows every rule


class GradeList(BaseModel):
    grades: list[Grade]


# ---- The three calls ----

def _ask(client: anthropic.Anthropic, system: str, user: str, output_shape: type[BaseModel]) -> BaseModel:
    """Send one prompt and return Claude's answer as an instance of output_shape."""
    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=output_shape,
        output_config={"effort": EFFORT},
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined this request.")
    return response.parsed_output


def extract_terms(client: anthropic.Anthropic, transcript_text: str) -> TermList:
    """The lecture's technical terms, plus a short topic label for the card fronts."""
    return _ask(
        client,
        prompts.terms_system(),
        prompts.terms_user(transcript_text),
        TermList,
    )


def pick_ideas(client: anthropic.Anthropic, transcript_text: str, terms: list[Term]) -> list[Idea]:
    result = _ask(
        client,
        prompts.IDEAS_SYSTEM,
        prompts.ideas_user(transcript_text, terms),
        IdeaList,
    )
    return result.ideas


def draft_cards(client: anthropic.Anthropic, transcript_text: str, ideas: list[Idea], terms: list[Term]) -> list[Card]:
    """The main-idea cards. (Vocab cards are built from the terms in code: see vocab_cards.)

    Now and then Claude answers with one blank card instead of a real list,
    so we check the answer and ask once more before giving up.
    """
    for attempt in range(2):
        result = _ask(
            client,
            prompts.cards_system(),
            prompts.cards_user(transcript_text, ideas, terms),
            CardList,
        )
        if not cards_look_blank(result.cards, len(ideas)):
            return result.cards
    raise RuntimeError("Claude returned blank cards twice. Please try again.")


def review_deck(client: anthropic.Anthropic, transcript_text: str, terms: list[Term], cards: list[Card]) -> Review:
    """The critic pass: Claude checks the draft against the card rules and
    returns fixed terms and cards. If the answer looks broken, keep the draft."""
    review = _ask(client, prompts.critic_system(), prompts.critic_user(transcript_text, terms, cards), Review)
    if review_looks_broken(review, terms, cards):
        return Review(changes=["The check came back broken, so the draft was kept."], terms=terms, cards=cards)
    return review


def review_looks_broken(review: Review, terms: list[Term], cards: list[Card]) -> bool:
    """The critic should trim and fix, not wipe out: losing more than half the
    terms or cards, or a blank card, means something went wrong."""
    return (len(review.terms) < len(terms) // 2
            or cards_look_blank(review.cards, len(cards)))


def cards_look_blank(cards: list[Card], idea_count: int) -> bool:
    """True if Claude seems to have given up instead of writing real cards:
    far fewer cards than ideas, an empty question or answer, or a
    fill-in-the-blank card with no blank."""
    if len(cards) < max(1, idea_count // 2):
        return True
    for card in cards:
        if not card.front.strip():
            return True
        if card.card_type == "basic" and not card.back.strip():
            return True
        if card.card_type == "cloze" and "{{c" not in card.front:
            return True
    return False


def vocab_cards(terms: list[Term], topic: str) -> list[dict]:
    """Two cards per term, built in code so none get skipped:
    "LLMs: Lossy compression" -> definition, and "LLMs: <definition>" -> term."""
    cards = []
    for t in terms:
        for front, back in [(t.term, t.definition), (t.definition, t.term)]:
            cards.append({"kind": "vocab", "card_type": "basic", "front": f"{topic}: {front}",
                          "back": back, "start_seconds": t.start_seconds})
    return cards


# ---- Website: the browser makes the Claude calls ----
#
# On the website, visitors' API keys must never reach our server. So the
# server only *builds* each request (the same prompts as above), and the
# visitor's browser sends it to Claude with their key. These functions
# return the raw request body for Claude's Messages API.

def request_body(system: str, user: str, output_shape: type[BaseModel]) -> dict:
    """The same request _ask sends, as plain JSON the browser can post to Claude."""
    schema = transform_schema(TypeAdapter(output_shape).json_schema())
    return {
        "model": MODEL,
        "max_tokens": 16000,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "output_config": {"effort": EFFORT, "format": {"type": "json_schema", "schema": schema}},
    }


def browser_request(step: str, data: dict) -> dict:
    """Build the request for one website step. `data` is what the page sent."""
    if step == "terms":
        return request_body(prompts.terms_system(), prompts.terms_user(data["transcript_text"]), TermList)

    if step == "ideas":
        terms = [Term(**t) for t in data["terms"]]
        return request_body(prompts.IDEAS_SYSTEM, prompts.ideas_user(data["transcript_text"], terms), IdeaList)

    if step == "cards":
        terms = [Term(**t) for t in data["terms"]]
        ideas = IdeaList(ideas=data["ideas"]).ideas
        user = prompts.cards_user(data["transcript_text"], ideas, terms)
        return request_body(prompts.cards_system(), user, CardList)

    if step == "review":
        terms = [Term(**t) for t in data["terms"]]
        cards = [Card(**c) for c in data["cards"]]
        user = prompts.critic_user(data["transcript_text"], terms, cards)
        return request_body(prompts.critic_system(), user, Review)

    if step == "suggest":
        card = SuggestedCard(**data["card"])
        return request_body(prompts.suggest_system(), prompts.suggest_user(card, data["title"]), Suggestion)

    raise ValueError(f"Unknown step: {step}")


# ---- Eval call ----

def match_terms(client: anthropic.Anthropic, golden_terms: list[str], tool_terms: list[str]) -> list[TermMatch]:
    """For each golden term, ask Claude which tool term (if any) means the same thing."""
    result = _ask(
        client,
        prompts.MATCH_SYSTEM,
        prompts.match_user(golden_terms, tool_terms),
        MatchList,
    )
    return result.matches


def cover_cards(client: anthropic.Anthropic, golden_cards: list[str], tool_cards: list[dict]) -> list[Coverage]:
    """For each golden card, ask Claude which tool cards test the same knowledge."""
    result = _ask(client, prompts.COVER_SYSTEM, prompts.cover_user(golden_cards, tool_cards), CoverageList)
    return result.coverage


def grade_cards(client: anthropic.Anthropic, tool_cards: list[dict]) -> list[Grade]:
    """Ask Claude which card rules each tool card breaks."""
    result = _ask(client, prompts.grade_system(), prompts.grade_user(tool_cards), GradeList)
    return result.grades
