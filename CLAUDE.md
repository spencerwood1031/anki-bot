# Anki Bot

Turns YouTube lecture videos into Anki flashcards.
Pipeline: YouTube URL → timestamped transcript → technical terms → 5–15 key ideas → cards → .apkg (genanki).

## Working on this project
- Spencer is learning to build with AI: explain choices as you go, and check in before major decisions.
- Keep code simple and readable over clever.
- Never write or edit anything in `golden/`. Those files are Spencer's hand-written ground truth.
- Phase 1 only for now. The critic pass, frame captures and review screen come later.
- The `## Card rules` section below is also sent to Claude in the card-drafting prompt (`ankibot/prompts.py` reads it), so edit the rules there and only there.
- Evals (planned, not built): `evals/eval_terms.py` will compare `outputs/<id>/terms.json` against `golden/<id>/jargon.txt` (recall and precision, with an LLM judging whether two terms match).

## Card rules
- One idea per card (atomic). Never stitch multiple clauses into one answer.
- Prefer genuine why/how questions over cloze deletions. Use cloze only for bare facts like a term or a number.
- Answers must be short enough to be unambiguously right or wrong.
- No yes/no questions.
- Cues may narrow the answer but must never give it away.

### More guidance (from Matuschak's "How to write good prompts" and Wozniak's "20 rules")
- **Precise:** the question must rule out other reasonable answers, so the answer is the same on every review. "What's the first step?" is too open; say which step and in what context.
- **Sharp why/how:** a why-question needs a specific mechanism as its answer, not a vague one. "Why use bones in stock?" invites "they're cheap"; "How do bones give stock its rich texture?" doesn't.
- **Minimum wording:** cut every word that isn't needed to get the answer. Put extra details on their own cards.
- **No sets or lists as answers:** never ask "What are the parts of X?" Split a list into one-blank cloze cards that keep the list in the same order.
- **Context prefix:** start the front with a short topic label (e.g. "Neural nets:") instead of long setup wording. This also keeps similar cards from being confused with each other.
- **Look at the concept from several angles:** its attributes, how it differs from nearby concepts, its parts and examples, its causes and effects, and why it matters. Several simple cards on one idea are better than one complex card.
- **Only what the lecture explains:** don't write cards on things the lecture only mentions in passing.
- **Cues:** a cue like "(a type of function)" narrows the answer; a cue like "(rhymes with...)" or one that contains the answer gives it away.

### Examples
- Bad: "What are the characteristics of the Dead Sea?" (too broad). Good: "Where is the Dead Sea located?" → "On the border between Israel and Jordan."
- Bad: "Does chicken stock make vegetable dishes taste like chicken?" (yes/no). Good: an open question about how stock changes the flavor of vegetables.
- Bad: "What does GRE stand for in biochemistry?" Good: "Biochem: GRE" → "glucocorticoid response element."
