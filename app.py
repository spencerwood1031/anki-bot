"""The Anki Bot website: paste a YouTube URL, review the cards, download a deck.

Run it on your computer:
    flask --app app run --debug
then open http://127.0.0.1:5000

Visitors' API keys never reach this server. The page (templates/index.html)
keeps the key in the browser and calls Claude directly. This server only does
the parts that don't need the key:
- GET  /                     the web page.
- POST /api/transcript       {url, transcript?} -> {video_id, title, transcript_text}
- POST /api/claude-request   {step, ...} -> the request body for one Claude call
                             (terms, ideas, cards or suggest), built from the same
                             prompts as make_deck.py. The browser sends it to Claude.
- POST /api/download         {video_id, title, cards} -> the finished .apkg file.

The server keeps nothing between requests: the cards live on the page until
the visitor downloads them.
"""

import json
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

import requests  # comes with youtube-transcript-api; used for its network errors
from flask import Flask, jsonify, request, send_file
from youtube_transcript_api import CouldNotRetrieveTranscript

from ankibot import deck, llm, transcript
from ankibot.links import timestamp_url

app = Flask(__name__)
PAGE = Path(__file__).parent / "templates" / "index.html"

# Long lectures cost the visitor more and can exceed what Claude reads in one go.
# About 3 hours of speech is roughly this many characters.
MAX_TRANSCRIPT_CHARS = 200_000

# Rules the browser enforces on our page. The important one is connect-src:
# the page may only send data to this server and to Claude's API, so even a
# bug or an injected script couldn't send a visitor's key anywhere else.
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "connect-src 'self' https://api.anthropic.com; "
        "img-src 'self' data:; "
        "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}


class UserError(Exception):
    """A problem the visitor can fix. Its message is shown on the page."""


@app.after_request
def add_security_headers(response):
    response.headers.update(SECURITY_HEADERS)
    return response


@app.get("/")
def home():
    # Sent as a plain file, not a Flask template, because the page shows
    # cloze examples like {{c1::...}} that the template engine would misread.
    return send_file(PAGE)


@app.post("/api/transcript")
def get_transcript():
    data = request.get_json()
    try:
        video_id = video_id_from(data.get("url", "").strip())
        segments = get_segments(video_id, data.get("transcript", "").strip())
    except UserError as error:
        return jsonify(error=str(error)), 400

    transcript_text = transcript.format_for_prompt(segments)
    if len(transcript_text) > MAX_TRANSCRIPT_CHARS:
        return jsonify(error="That video is too long. Try one under about 3 hours."), 400
    return jsonify(video_id=video_id, title=video_title(video_id), transcript_text=transcript_text)


@app.post("/api/claude-request")
def claude_request():
    data = request.get_json()
    return jsonify(llm.browser_request(data["step"], data))


@app.post("/api/download")
def download():
    data = request.get_json()
    video_id = data["video_id"]
    title = data.get("title") or f"Lecture {video_id}"
    cards = []
    for card in data["cards"]:
        if card["card_type"] == "cloze" and "{{c" not in card["front"]:
            return jsonify(error=f'This cloze card has no {{{{c1::...}}}} blank: "{card["front"]}"'), 400
        card["source_url"] = timestamp_url(video_id, card.get("start_seconds", 0))
        cards.append(card)
    if not cards:
        return jsonify(error="The deck is empty. Add a card first."), 400

    # A fresh temporary folder per request, so two visitors never share files.
    apkg_path = Path(tempfile.mkdtemp()) / "deck.apkg"
    deck.build_deck(video_id, title, cards, str(apkg_path))
    return send_file(apkg_path, as_attachment=True, download_name=safe_filename(title) + ".apkg")


def video_id_from(url: str) -> str:
    try:
        return transcript.get_video_id(url)
    except (ValueError, KeyError, IndexError):
        raise UserError("That doesn't look like a YouTube video link.")


def get_segments(video_id: str, pasted_transcript: str) -> list[dict]:
    """Use the pasted transcript if there is one, otherwise fetch it from YouTube."""
    if pasted_transcript:
        return transcript.parse_pasted_transcript(pasted_transcript)
    try:
        return transcript.fetch_transcript(video_id)
    except (CouldNotRetrieveTranscript, requests.RequestException):
        raise UserError(
            "Couldn't get this video's transcript from YouTube. It may have no captions, "
            "or YouTube blocked the request. You can paste the transcript instead."
        )


def video_title(video_id: str) -> str:
    """Ask YouTube's public oEmbed endpoint for the title. Falls back to the id."""
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    oembed_url = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(watch_url)
    try:
        with urllib.request.urlopen(oembed_url, timeout=10) as response:
            return json.load(response)["title"]
    except Exception:
        return f"Lecture {video_id}"


def safe_filename(title: str) -> str:
    """Keep letters, digits, spaces and dashes so the name works on every computer."""
    kept = "".join(c for c in title if c.isalnum() or c in " -_").strip()
    return kept[:80] or "deck"
