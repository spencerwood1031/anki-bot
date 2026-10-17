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
