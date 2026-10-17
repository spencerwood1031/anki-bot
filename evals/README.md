# Evals (planned, not built yet)

Ground truth lives in `golden/<video_id>/`, written by hand by Spencer:
- `jargon.txt`: one technical term per line
- `cards.md`: ideal cards for the video

The tool never writes to `golden/`.

## eval_terms.py (next, once Phase 1 works)
Compares `outputs/<video_id>/terms.json` with `golden/<video_id>/jargon.txt`.

- Matching: an LLM judges whether a tool term and a golden term mean the same thing
  ("ReLU" vs "rectified linear unit" counts as a match).
- Recall = golden terms the tool found / all golden terms ("did it miss anything?")
- Precision = tool terms that match a golden term / all tool terms ("did it add junk?")
- Output: the two scores plus the lists of missed and extra terms, so you can see why.

## Later
Card quality against `cards.md`, once the critic pass exists.
