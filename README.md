# Anki Bot

Turns a YouTube lecture into an Anki deck.

## Setup (once)
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then paste your API key into .env
```
For cloud sessions, set `ANKI_BOT_API_KEY` in the environment settings instead (Claude Code reserves `ANTHROPIC_API_KEY` there).

Get an API key at https://console.anthropic.com → API Keys. `.env` is git-ignored, so the key never gets committed.

## Run
```bash
python make_deck.py https://youtu.be/aircAruvnKk
```
Results land in `outputs/<video_id>/`: `transcript.json`, `terms.json`, `ideas.json`, `cards.json` and `deck.apkg`. Double-click the `.apkg` to import it into Anki.

## Layout
- `make_deck.py`: runs the pipeline top to bottom
- `ankibot/transcript.py`: URL → video id → timestamped transcript
- `ankibot/llm.py`: the three Claude calls and the shapes they return
- `ankibot/prompts.py`: prompt text (card rules are read from `CLAUDE.md`)
- `ankibot/deck.py`: cards → `.apkg`
- `ankibot/links.py`: timestamp links
- `golden/`: your hand-written ground truth (the tool never touches it)
- `evals/`: eval plan
