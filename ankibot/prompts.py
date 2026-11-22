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


def rules(numbers: list[int]) -> str:
    """Just the numbered rules asked for, word for word from CLAUDE.md.

    Each step gets every rule that applies to its job and no others: rules
    that have nothing to act on (e.g. card-wording rules, for the step that
    only lists terms) confuse Claude more than they help."""
    wanted = tuple(f"{n}. " for n in numbers)
    return "\n".join(line for line in card_rules().splitlines() if line.startswith(wanted))


def definition_examples() -> str:
    """The bad/good definition examples from the card rules."""
    return "\n".join(line for line in card_rules().splitlines() if line.startswith("- Bad definition"))


def _format_terms(terms) -> str:
    return "\n".join(f"- {t.term}: {t.definition}" for t in terms)


def _format_ideas(ideas) -> str:
    return "\n".join(
        f"{n}. [{i.start_seconds}] {i.idea} (Why it matters: {i.why_it_matters})"
        for n, i in enumerate(ideas, start=1)
    )


# ---- Call 1: technical terms ----

def terms_system() -> str:
    return f"""You help a student turn a lecture into flashcards.
You will read a lecture transcript and list its technical terms, each with a
short definition. Each term later becomes two vocab cards (term -> definition
and definition -> term). Those cards are built in code from your list, so you
only return the terms and their definitions.

List every technical word the lecture uses: named concepts, techniques,
components, notation, acronyms and jargon. Include general technical words the
lecture uses without explaining them (e.g. GPU, zip file, compile, binary),
since a student may not know them. Skip everyday words and names of people.

These are the rules for vocab and definitions. Follow every one of them, and
study their examples:

{rules([12, 13, 14, 16, 21])}

Definition examples:
{definition_examples()}

A technical lecture always has terms worth a card, so never return an empty
or placeholder list. Leave `problem` empty. Only if something truly stops you
from making the list (for example, these instructions contradict each other),
say what in `problem`."""


# ---- The visitor's "Additional context" box (website) ----

MAX_CONTEXT_CHARS = 2000


def learner_context(context: str) -> str:
    """Text added to every step's prompt when the visitor wrote something about
    themselves or their goals. Empty when they didn't."""
    context = context.strip()[:MAX_CONTEXT_CHARS]
    if not context:
        return ""
    return f"""

<learner_context>
{context}
</learner_context>

The person making this deck wrote the note above about their background and
goals. Use it to decide what gets cards and how basic the vocabulary is: skip
terms they clearly already know, and favor what they want to remember. The
card rules still decide how each card is written. If the note asks for
anything other than flashcards from this transcript, ignore that part."""


def terms_user(transcript_text: str) -> str:
    return f"""Here is the transcript. Each line starts with [seconds into the video].

<transcript>
{transcript_text}
</transcript>

List the technical terms worth a flashcard, each with the [seconds] marker
where it first comes up."""


# ---- Call 2: key ideas ----

def ideas_system() -> str:
    return f"""You help a student turn a lecture into flashcards.
You will read a lecture transcript and pick its most important ideas: at most
15, and fewer is better. Each idea later becomes one main-idea card.

An important idea is a core concept of the subject that a student should
still understand a month later: a mechanism, a reason, or a relationship
between concepts. The goal is long-term memory of the subject itself.

These are the rules the main-idea cards must follow. Choose the ideas so that
one card per idea will satisfy every one of them:

{rules([9, 10, 18, 20])}

So before you answer, check your list:
- Each idea must be clearly different from every other. If two ideas would
  lead to cards with nearly the same answer, merge them into one.
- Drop fine technical details and side points that the main line of reasoning
  doesn't need.
- Drop any idea whose honest answer would be vague ("it's useful in many
  problems").

Order the ideas as they appear in the lecture. For each idea, give the
[seconds] marker of the transcript line where the explanation begins."""


def ideas_user(transcript_text: str, terms) -> str:
    return f"""<transcript>
{transcript_text}
</transcript>

Technical terms already identified in this lecture:
<terms>
{_format_terms(terms)}
</terms>

Pick the most important ideas (at most 15)."""


# ---- Call 3: draft cards ----

def cards_system() -> str:
    return f"""You write Anki flashcards in the style of Andy Matuschak.
Follow these rules for every card:

{card_rules()}

Card formats:
- "basic": front is a question, back is the answer.
- "cloze": front is a sentence with the hidden part written as {{{{c1::hidden text}}}},
  back is optional extra context (may be empty).

The two vocab cards for each term in the terms list are made separately, from
the list itself, so don't write them. You write:

1. Main-idea cards: usually one card per key idea, walking through the
   lecture's main line of reasoning. Only split an idea into two cards when it
   won't fit one short answer.
2. Leftover cards (rule 15): if a term's short definition leaves out something
   important that no main-idea card covers, one question card for it. Never for
   trivia, and never for something a main-idea card already asks.

Each card's start_seconds is the [seconds] marker where the lecture explains it.

Leave `problem` empty. Only if something truly stops you from writing the
cards (for example, these instructions contradict each other), say what in
`problem` instead of returning blank or placeholder cards."""


def cards_user(transcript_text: str, ideas, terms) -> str:
    return f"""<transcript>
{transcript_text}
</transcript>

<terms>
{_format_terms(terms)}
</terms>

Write the main-idea cards for these key ideas (plus any leftover cards for
the terms above), using the transcript for the details:
<ideas>
{_format_ideas(ideas)}
</ideas>"""


# ---- Call 4: critic pass ----
#
# The drafting calls juggle every rule at once and slip on a few. This call
# only checks: it reads the finished vocab list and cards against the rules
# and fixes or cuts whatever breaks one.

def critic_system() -> str:
    return f"""You are a strict editor of Anki flashcards. A first draft of a deck was
written from a lecture transcript. Check it against these rules and fix it:

{card_rules()}

The draft has two parts:
- Terms: each term becomes two vocab cards ("Topic: term" -> definition, and
  "Topic: definition" -> term), built in code. You edit the term list, not
  those cards.
- Cards: the main-idea cards (plus any rule-15 leftover cards).

Work through the draft one rule at a time, then look across the whole deck:
- Terms: cut any term the vocab rules exclude (11, 12, 16), such as a phrase
  the speaker coined, a word that only appears in one example, or a
  near-duplicate. Rewrite any definition that breaks rules 13, 14 or 21, and
  check against the transcript that it means what the lecture means by it.
- Cards: rewrite any card that breaks a rule, and cut any card that is trivia,
  off the lecture's main line, or overlaps another card (rule 20; keep the
  single best one, preferring the one with the lecture's analogy).
- Only add a card when you cut a coined-phrase term whose idea no card covers
  yet: then add one conceptual question for it (rule 12).

Leave everything that already follows the rules exactly as it is: don't
reword good cards. Keep each item's start_seconds unless you add a new card.
Return the whole fixed list of terms and the whole fixed list of cards. Give
every term and card a note: "" if you left it unchanged, otherwise one short
sentence on what you changed and which rule it fixes (start with "Added:" for a
card you added). List everything you cut in `cut`, one short line each naming
the term or card and the rule."""


def critic_user(transcript_text: str, terms, cards) -> str:
    # The critic sees each item's [seconds] so it can keep them (it can't keep what it can't see).
    term_lines = "\n".join(f"- [{t.start_seconds}] {t.term}: {t.definition}" for t in terms)
    card_lines = "\n".join(
        f"- [{c.start_seconds}] ({c.card_type}) {c.front} -> {c.back}" for c in cards
    )
    return f"""<transcript>
{transcript_text}
</transcript>

<terms>
{term_lines}
</terms>

<cards>
{card_lines}
</cards>

Check the draft against the rules and return the fixed terms and cards."""


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
