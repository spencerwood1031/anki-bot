"""The prompt text for each Claude call.

Kept separate from the code because you'll tweak prompts far more often.
The card rules are read from CLAUDE.md so there's only one copy of them.
"""

from pathlib import Path

CLAUDE_MD = Path(__file__).parent.parent / "CLAUDE.md"


def card_rules() -> str:
    """Return the text of the '## Card rules' section of CLAUDE.md."""
    text = CLAUDE_MD.read_text()
    section = text.split("\n## Card rules\n", 1)[1]
    return section.split("\n## ", 1)[0].strip()


def _format_terms(terms) -> str:
    return "\n".join(f"- {t.term}: {t.definition}" for t in terms)


def _format_ideas(ideas) -> str:
    return "\n".join(
        f"{n}. [{i.start_seconds}] {i.idea} (Why it matters: {i.why_it_matters})"
        for n, i in enumerate(ideas, start=1)
    )


# ---- Call 1: technical terms ----

TERMS_SYSTEM = """You help a student turn a lecture into flashcards.
You will read a lecture transcript and list the technical terms worth a flashcard.

A term is worth a card if it is domain vocabulary a student would need to know to
follow this subject: named concepts, techniques, components, notation, or jargon.
Skip everyday words, names of people, and terms that are only mentioned in passing
without being explained or used.

Give each term a one-sentence definition as it is used in this lecture."""


def terms_user(transcript_text: str) -> str:
    return f"""Here is the transcript. Each line starts with [seconds into the video].

<transcript>
{transcript_text}
</transcript>

List the technical terms worth a flashcard."""


# ---- Call 2: key ideas ----

IDEAS_SYSTEM = """You help a student turn a lecture into flashcards.
You will read a lecture transcript and pick the 5 to 15 most important ideas.

An important idea is something the lecture spends time explaining and that a
student should still understand a month later: a mechanism, a reason, a
relationship between concepts, or a key fact. Prefer ideas that explain why or
how over ideas that only name things. Order them as they appear in the lecture.

For each idea, give the [seconds] marker of the transcript line where the
explanation begins."""


def ideas_user(transcript_text: str, terms) -> str:
    return f"""<transcript>
{transcript_text}
</transcript>

Technical terms already identified in this lecture:
<terms>
{_format_terms(terms)}
</terms>

Pick the 5 to 15 most important ideas."""


# ---- Call 3: draft cards ----

def cards_system() -> str:
    return f"""You write Anki flashcards in the style of Andy Matuschak.
Follow these rules for every card:

{card_rules()}

Card formats:
- "basic": front is a question, back is the answer.
- "cloze": front is a sentence with the hidden part written as {{{{c1::hidden text}}}},
  back is optional extra context (may be empty).

Each card's start_seconds is the [seconds] marker where the lecture explains it.
An idea may need more than one card to keep each card atomic.

Vocabulary is handled in a separate pass, so these cards are conceptual: how
things work, why they matter, and how they relate. Use the terms list for
context and correct wording, but don't write cards whose only job is to define
a term, expand an abbreviation, or recall a bare name."""


def cards_user(transcript_text: str, ideas, terms) -> str:
    return f"""<transcript>
{transcript_text}
</transcript>

<terms>
{_format_terms(terms)}
</terms>

Write flashcards for these key ideas, using the transcript for the details:
<ideas>
{_format_ideas(ideas)}
</ideas>"""


# ---- Eval: match the tool's terms against Spencer's golden list ----

MATCH_SYSTEM = """You grade a vocabulary extractor against a hand-written answer key.
For each golden term, find the tool term that means the same thing, if any.
Count it as a match when they name the same concept, even if the wording differs
("ReLU" and "rectified linear unit", "sigmoid" and "sigmoid function").
Don't count a broader or narrower term as a match ("layer" is not "hidden layer").
Each tool term can match at most one golden term."""


def match_user(golden_terms, tool_terms) -> str:
    golden = "\n".join(f"- {t}" for t in golden_terms)
    tool = "\n".join(f"- {t}" for t in tool_terms)
    return f"""<golden_terms>
{golden}
</golden_terms>

<tool_terms>
{tool}
</tool_terms>

For every golden term, give the matching tool term exactly as written, or null if none matches."""
