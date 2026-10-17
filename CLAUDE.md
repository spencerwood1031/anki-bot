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
Distilled from Andy Matuschak's "How to write good prompts" and Piotr Wozniak's "20 rules of formulating knowledge".

1. **One idea per card.** Never stitch several clauses into one answer. Extra details go on their own cards.
2. **Why/how over cloze.** Prefer genuine why/how questions. Use cloze only for bare facts like a term or a number.
3. **Sharp why/how.** A why-question needs a specific mechanism as its answer, not a vague one. "Why use bones in stock?" invites "they're cheap"; "How do bones give stock its rich texture?" doesn't.
4. **Precise.** The question must rule out other reasonable answers, so the answer is the same on every review, and short enough to be clearly right or wrong.
5. **No yes/no questions.** Reframe them as open questions.
6. **No sets or lists as answers.** Never ask "What are the parts of X?" Split a list into one-blank cloze cards that keep the list in the same order.
7. **Cues narrow, never give away.** "(a type of function)" is fine; a rhyme or anything containing the answer is not.
8. **Minimum wording.** Cut every word that isn't needed to get the answer. Start the front with a short topic label (e.g. "Neural nets:") instead of long setup wording; this also keeps similar cards from being confused.
9. **Several angles on one concept.** Its attributes, how it differs from nearby concepts, its parts and examples, its causes and effects, and why it matters. Several simple cards beat one complex card.
10. **Only what the lecture explains.** No cards on things it mentions only in passing.

### Examples
- Bad: "What are the characteristics of the Dead Sea?" (too broad). Good: "Where is the Dead Sea located?" → "On the border between Israel and Jordan."
- Bad: "Does chicken stock make vegetable dishes taste like chicken?" (yes/no). Good: an open question about how stock changes the flavor of vegetables.
- Bad: "What does GRE stand for in biochemistry?" Good: "Biochem: GRE" → "glucocorticoid response element."
