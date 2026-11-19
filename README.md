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
Two passes: vocab first, then concepts.
```bash
python make_deck.py https://youtu.be/aircAruvnKk --terms   # 1. vocab list only
python evals/eval_terms.py aircAruvnKk                     #    score it against golden/aircAruvnKk/jargon.txt
python make_deck.py https://youtu.be/aircAruvnKk           # 2. full run: key ideas + conceptual cards
```
Results land in `outputs/<video_id>/`: `transcript.json`, `terms.json`, `ideas.json`, `cards.json` and `deck.apkg`. Double-click the `.apkg` to import it into Anki. The transcript is fetched once and reused after that.

## Website
`app.py` is a small Flask website: visitors paste a YouTube link and their own Anthropic API key, then review the cards (edit, delete, add their own, and ask Claude to suggest a better version of any card) before downloading the deck. If YouTube won't give up the transcript, they can paste it from YouTube's "Show transcript" panel instead.

Visitors' API keys never touch the server: the page calls Claude straight from the browser, and the server only fetches transcripts, builds the Claude requests from the same prompts as `make_deck.py`, and packages the deck. `python -m unittest discover tests` checks this still holds.

Try it on your computer:
```bash
pip install -r requirements.txt
flask --app app run --debug      # then open http://127.0.0.1:5000
```

### Put it online (Render + anki.spencerjwood.com)
1. **Webshare** (so YouTube doesn't block the server): sign up at webshare.io and buy a **Residential** plan (not "Proxy Server" or "Static Residential"). Copy the Proxy Username and Password from https://dashboard.webshare.io/proxy/settings.
2. **Render**: sign up at render.com with GitHub. Click **New + → Blueprint**, pick this repo, and paste the two Webshare values when asked. Render reads `render.yaml` and deploys. Every push to `main` redeploys.
3. **Your domain**: in Render, open the anki-bot service → **Settings → Custom Domains → Add** `anki.spencerjwood.com`. Render shows an address like `anki-bot.onrender.com`.
4. **Cloudflare**: open spencerjwood.com → **DNS → Records → Add record**. Type `CNAME`, name `anki`, target the Render address, proxy status **DNS only** (grey cloud). Back in Render, click **Verify**. HTTPS is set up for you within a few minutes.

The free plan sleeps after 15 idle minutes, so the first visit after that takes about a minute.

## Layout
- `make_deck.py`: runs the pipeline top to bottom
- `app.py` + `templates/index.html`: the website
- `render.yaml`: how Render runs the website
- `ankibot/transcript.py`: URL → video id → timestamped transcript
- `ankibot/llm.py`: the Claude calls and the shapes they return
- `ankibot/prompts.py`: prompt text (card rules are read from `CLAUDE.md`)
- `ankibot/deck.py`: cards → `.apkg`
- `ankibot/links.py`: timestamp links
- `golden/`: your hand-written ground truth (the tool never touches it)
- `evals/eval_terms.py`: scores the vocab list against your golden list
