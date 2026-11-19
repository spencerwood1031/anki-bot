"""The Anki Bot website: paste a YouTube URL and your API key, get a deck.

Run it on your computer:
    flask --app app run --debug
then open http://127.0.0.1:5000

How it fits together (the page in templates/index.html calls these):
- GET  /              sends the web page.
- POST /api/cards     {url, api_key, transcript?} -> runs the same pipeline as
                      make_deck.py and returns the cards as JSON, so the visitor
                      can review, edit, delete and add cards on the page.
- POST /api/suggest   {api_key, card, title} -> Claude's rewrite of one card so
                      it follows the card rules in CLAUDE.md.
- POST /api/download  {video_id, title, cards} -> the finished .apkg file.

The server keeps nothing between requests: the cards live on the page until
the visitor downloads them. The visitor's API key is used for one request and
then forgotten. It is never saved or logged.
"""

import json
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

import anthropic
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


class UserError(Exception):
    """A problem the visitor can fix. Its message is shown on the page."""


@app.get("/")
def home():
    # Sent as a plain file, not a Flask template, because the page shows
    # cloze examples like {{c1::...}} that the template engine would misread.
    return send_file(PAGE)


@app.post("/api/cards")
def make_cards():
    data = request.get_json()
    try:
        result = cards_for(
            url=data.get("url", "").strip(),
            api_key=data.get("api_key", "").strip(),
            pasted_transcript=data.get("transcript", "").strip(),
        )
    except UserError as error:
        return jsonify(error=str(error)), 400
    return jsonify(result)


@app.post("/api/suggest")
def suggest():
    data = request.get_json()
    try:
        client = client_for(data.get("api_key", "").strip(), check=False)
        card = llm.SuggestedCard(**data["card"])
        suggestion = call_claude(llm.suggest_rewrite, client, card, data.get("title", ""))
    except UserError as error:
        return jsonify(error=str(error)), 400
    return jsonify(suggestion.model_dump())


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


def cards_for(url: str, api_key: str, pasted_transcript: str) -> dict:
    """Run the pipeline for one visitor and return {video_id, title, cards}."""
    try:
        video_id = transcript.get_video_id(url)
    except (ValueError, KeyError, IndexError):
        raise UserError("That doesn't look like a YouTube video link.")
    client = client_for(api_key)  # before the transcript, so a bad key fails fast

    segments = get_segments(video_id, pasted_transcript)
    transcript_text = transcript.format_for_prompt(segments)
    if len(transcript_text) > MAX_TRANSCRIPT_CHARS:
        raise UserError("That video is too long. Try one under about 3 hours.")

    terms = call_claude(llm.extract_terms, client, transcript_text)
    ideas = call_claude(llm.pick_ideas, client, transcript_text, terms)
    cards = call_claude(llm.draft_cards, client, transcript_text, ideas, terms)
    return {
        "video_id": video_id,
        "title": video_title(video_id),
        "cards": [card.model_dump() for card in cards],
    }


def client_for(api_key: str, check: bool = True) -> anthropic.Anthropic:
    """Make a Claude client for the visitor's key, checking it first if asked."""
    if not api_key:
        raise UserError("Paste your Anthropic API key.")
    client = llm.make_client(api_key)
    if check:
        check_key(client)
    return client


def call_claude(step, *args):
    """Run one Claude step, turning API errors into messages the visitor can act on."""
    try:
        return step(*args)
    except anthropic.AuthenticationError:
        raise UserError("That API key didn't work. Check it at console.anthropic.com.")
    except anthropic.RateLimitError:
        raise UserError("Your API key hit its rate limit. Wait a minute and try again.")
    except anthropic.APIStatusError as error:
        raise UserError(f"Claude returned an error: {error.message}")


def check_key(client: anthropic.Anthropic) -> None:
    """Make one free call (listing models) to see if the key works."""
    try:
        client.models.list(limit=1)
    except anthropic.AuthenticationError:
        raise UserError("That API key didn't work. Check it at console.anthropic.com.")
    except anthropic.PermissionDeniedError:
        raise UserError("That API key isn't allowed to use Claude. Check it at console.anthropic.com.")


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
