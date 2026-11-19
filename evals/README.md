# Evals

Ground truth lives in `golden/<video_id>/`, written by hand by Spencer:
- `jargon.txt`: one technical term per line
- `cards.md`: ideal cards for the video

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

## Later
Card quality against `cards.md`, once the critic pass exists.
