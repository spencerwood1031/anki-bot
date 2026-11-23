# Evals

Ground truth lives in `golden/<video_id>/`, written by hand by Spencer:
- `jargon.txt`: one technical term per line
- `cards.md`: ideal main-idea cards for the video (vocab goes in `jargon.txt`)

The tool never writes to `golden/`.

## eval_terms.py
```bash
python make_deck.py https://youtu.be/aircAruvnKk --terms
python evals/eval_terms.py aircAruvnKk
```
Compares `outputs/<video_id>/terms.json` with `golden/<video_id>/jargon.txt`.

- Matching: Claude judges whether a tool term and a golden term mean the same thing
  ("ReLU" vs "rectified linear unit" counts as a match; "layer" vs "hidden layer" doesn't).
- Recall = golden terms the tool found / all golden terms ("did it miss anything?")
- Precision = tool terms that match a golden term / all tool terms ("did it add junk?")
- Output: the two scores plus the missed and extra terms, printed and saved to
  `outputs/<video_id>/eval_terms.json`.

The feedback loop: read the missed and extra lists, change `TERMS_SYSTEM` in
`ankibot/prompts.py`, re-run both commands, and see if the scores go up.

## eval_cards.py
```bash
python make_deck.py <url>
python evals/eval_cards.py <video_id>
python evals/eval_cards.py <video_id> --until 3600   # only cards from the first hour
```
Compares the main-idea cards in `outputs/<video_id>/cards.json` with `golden/<video_id>/cards.md`
(write only main-idea cards there; vocab is scored against `jargon.txt`)
(one card per blank-line-separated block; lines starting with `#` are ignored).

- Recall = your cards the tool has a matching card for / all your cards
- Precision = tool cards that match one of yours / all tool cards
- Rule pass = tool cards that break none of the 10 card rules / all tool cards
- Claude judges which cards test the same knowledge, and which rules each card breaks.
- `--until` is for long videos where you only wrote cards for the first part.
- Output: the scores, the most-broken rules, your missed cards and each rule-breaking
  card with reasons, printed and saved to `outputs/<video_id>/eval_cards.json`.

Runs vary, so compare averages of a few runs before trusting a change.

## bench.py
```bash
python evals/bench.py wjZofJX0v4M WUvTyaaNkzM --runs 3 --label baseline
python evals/bench.py wjZofJX0v4M --label baseline --rescore   # re-score saved decks, no new runs
```
Runs the full pipeline (same code as `make_deck.py`) several times on saved transcripts
(`outputs/<video_id>/transcript.json`, no YouTube fetch) and scores each deck:

- Notes covered = points in `answer-keys/<video_id>.md` (distilled from Spencer's notes) that some card teaches
- Vocab kept = terms that break none of the vocab rules (11-14, 16, 21)
- Ideas clean = main-idea cards that break none of the card rules

The averages, plus each run's missed points, weak terms and rule-breaking cards, are
printed and saved to `outputs/bench_<label>.md`. Use it to check a prompt change on
every test video before trusting it.
