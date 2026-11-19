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

List every technical word the lecture uses: named concepts, techniques,
components, notation, acronyms and jargon. Include general technical words the
lecture uses without explaining them (e.g. GPU, zip file, compile, binary), since
a student may not know them.

Skip: everyday words; names of people; product, model and company names (e.g.
Llama 2, ChatGPT, Claude); units of storage (byte, gigabyte); programming
languages (C, Python); and generic words like "state-of-the-art" or "data type".

Give each term a short definition: the fewest words that make the meaning clear,
because it becomes the back of a flashcard. A definition must contain no
numbers, sizes, counts, costs or examples from the lecture, and must not define
a term by a synonym (don't define "parameters" as "weights"); say what it is."""


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
student should still understand a month later: a mechanism, a reason, or a
relationship between concepts. Follow the lecture's main line of reasoning, so
the ideas read as a chain, and order them as they appear in the lecture. Skip
illustrative numbers (costs, counts, sizes, durations), side remarks, and
anything about the speaker rather than the subject.

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

Write two kinds of cards:

1. Vocab cards (kind "vocab"): for EVERY term in the terms list, write two basic
   cards, in the order of the list:
   - front "<topic>: <term>", back: its short definition.
   - front "<topic>: <short definition>", back: the term.
   <topic> is a short label for the lecture's subject (e.g. "LLMs"), the same on
   every card. start_seconds is where the term first comes up.

2. Main-idea cards (kind "idea"): usually one card per key idea, walking
   through the lecture's main line of reasoning. Only split an idea into two
   cards when it won't fit one short answer. Don't repeat the vocab cards.

Each card's start_seconds is the [seconds] marker where the lecture explains it."""


def cards_user(transcript_text: str, ideas, terms) -> str:
    return f"""<transcript>
{transcript_text}
</transcript>

<terms>
{_format_terms(terms)}
</terms>

Write two vocab cards for every term above, then main-idea cards for these
key ideas, using the transcript for the details:
<ideas>
{_format_ideas(ideas)}
</ideas>"""


# ---- Website: suggest a better version of a visitor's card ----

def suggest_system() -> str:
    return f"""You help a student improve an Anki flashcard they wrote themselves.
Rewrite it so it follows these rules:

{card_rules()}

Card formats:
- "basic": front is a question, back is the answer.
- "cloze": front is a sentence with the hidden part written as {{{{c1::hidden text}}}},
  back is optional extra context (may be empty).

Keep the student's meaning and facts; don't add new information. If the card
already follows the rules, return it unchanged and say so. If it holds several
ideas, split it into several cards. In "why", name the rules the rewrite fixes
in one or two short sentences, written to the student."""


def suggest_user(card, deck_title: str) -> str:
    return f"""The card is from a deck on the lecture "{deck_title}".

<card type="{card.card_type}">
<front>{card.front}</front>
<back>{card.back}</back>
</card>

Suggest a better version."""


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


# ---- Eval: compare the tool's cards with Spencer's golden cards ----

COVER_SYSTEM = """You grade a flashcard generator against a hand-written answer key.
For each golden card, list the tool cards that test the same piece of knowledge:
a student who knows the answer to one would know the answer to the other.
Wording and format don't matter (a cloze card can match a question card).
A tool card that only tests part of the golden card, or a broader or narrower
fact, doesn't count. A tool card may match more than one golden card."""


def cover_user(golden_cards, tool_cards) -> str:
    golden = "\n".join(f"G{n}. {c}" for n, c in enumerate(golden_cards, start=1))
    tool = "\n".join(f"T{n}. {c['front']} -> {c['back']}" for n, c in enumerate(tool_cards, start=1))
    return f"""<golden_cards>
{golden}
</golden_cards>

<tool_cards>
{tool}
</tool_cards>

For every golden card, give its number and the numbers of the tool cards that match it (an empty list if none)."""


def grade_system() -> str:
    return f"""You review Anki flashcards against these rules:

{card_rules()}

These are main-idea cards; vocab cards are graded separately, so a card whose
only job is to define a term breaks rule 9 here.

Be strict but fair: only flag a rule the card clearly breaks. For each broken
rule give a short reason a student would understand."""


def grade_user(tool_cards) -> str:
    tool = "\n".join(f"T{n}. [{c['card_type']}] {c['front']} -> {c['back']}" for n, c in enumerate(tool_cards, start=1))
    return f"""<cards>
{tool}
</cards>

For every card, give its number and the rules it breaks (an empty list if it follows them all)."""
