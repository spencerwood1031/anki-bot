"""The Anki Bot website: paste a YouTube URL and your API key, get a deck.

Run it on your computer:
    flask --app app run --debug
then open http://127.0.0.1:5000

How it fits together:
- GET  /           sends the web page (templates/index.html).
- POST /api/deck   gets {url, api_key, transcript?} from that page, runs the
                   same pipeline as make_deck.py, and sends back the .apkg file.

The visitor's API key is used for this one request and then forgotten.
It is never saved or logged.
"""

import json
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

import anthropic
from flask import Flask, jsonify, render_template, request, send_file
from youtube_transcript_api import CouldNotRetrieveTranscript

from ankibot import deck, llm, transcript
from ankibot.links import timestamp_url

app = Flask(__name__)

# Long lectures cost the visitor more and can exceed what Claude reads in one go.
# About 3 hours of speech is roughly this many characters.
MAX_TRANSCRIPT_CHARS = 200_000


class UserError(Exception):
    """A problem the visitor can fix. Its message is shown on the page."""


@app.get("/")
def home():
    return render_template("index.html")


@app.post("/api/deck")
def make_deck():
    data = request.get_json()
    try:
        apkg_path, filename = build_deck_for(
            url=data.get("url", "").strip(),
            api_key=data.get("api_key", "").strip(),
            pasted_transcript=data.get("transcript", "").strip(),
        )
    except UserError as error:
        return jsonify(error=str(error)), 400
    return send_file(apkg_path, as_attachment=True, download_name=filename)


def build_deck_for(url: str, api_key: str, pasted_transcript: str) -> tuple[str, str]:
    """Run the whole pipeline for one visitor. Returns (apkg path, download name)."""
    try:
        video_id = transcript.get_video_id(url)
    except (ValueError, KeyError, IndexError):
        raise UserError("That doesn't look like a YouTube video link.")

    if not api_key:
        raise UserError("Paste your Anthropic API key.")
    client = llm.make_client(api_key)
    check_key(client)  # before the transcript, so a bad key fails fast

    segments = get_segments(video_id, pasted_transcript)
    transcript_text = transcript.format_for_prompt(segments)
    if len(transcript_text) > MAX_TRANSCRIPT_CHARS:
        raise UserError("That video is too long. Try one under about 3 hours.")

    try:
        terms = llm.extract_terms(client, transcript_text)
        ideas = llm.pick_ideas(client, transcript_text, terms)
        cards = llm.draft_cards(client, transcript_text, ideas, terms)
    except anthropic.RateLimitError:
        raise UserError("Your API key hit its rate limit. Wait a minute and try again.")
    except anthropic.APIStatusError as error:
        raise UserError(f"Claude returned an error: {error.message}")

    card_dicts = []
    for card in cards:
        card_dict = card.model_dump()
        card_dict["source_url"] = timestamp_url(video_id, card.start_seconds)
        card_dicts.append(card_dict)

    title = video_title(video_id)
    # A fresh temporary folder per request, so two visitors never share files.
    apkg_path = Path(tempfile.mkdtemp()) / "deck.apkg"
    deck.build_deck(video_id, title, card_dicts, str(apkg_path))
    return str(apkg_path), safe_filename(title) + ".apkg"


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
    except CouldNotRetrieveTranscript:
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
