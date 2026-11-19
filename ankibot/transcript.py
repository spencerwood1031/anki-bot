"""Step 1: get a timestamped transcript for a YouTube video."""

import os
import re
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig


def get_video_id(url: str) -> str:
    """Pull the 11-character video id out of a YouTube URL.

    Handles the common shapes:
      https://www.youtube.com/watch?v=aircAruvnKk
      https://youtu.be/aircAruvnKk
      https://www.youtube.com/embed/aircAruvnKk
    """
    parsed = urlparse(url)

    if parsed.hostname == "youtu.be":
        return parsed.path.lstrip("/")

    if parsed.path == "/watch":
        return parse_qs(parsed.query)["v"][0]

    if parsed.path.startswith(("/embed/", "/shorts/", "/live/")):
        return parsed.path.split("/")[2]

    raise ValueError(f"Couldn't find a video id in: {url}")


def fetch_transcript(video_id: str) -> list[dict]:
    """Return the transcript as a list of segments.

    Each segment looks like: {"text": "...", "start": 12.3, "duration": 4.1}
    where start and duration are in seconds.
    """
    return _transcript_api().fetch(video_id).to_raw_data()


def _transcript_api() -> YouTubeTranscriptApi:
    """Fetch directly, or through a Webshare proxy if its login is set.

    YouTube blocks transcript requests from cloud servers, so the hosted
    website routes them through Webshare's home-internet IPs. On your own
    computer, leave WEBSHARE_PROXY_USERNAME unset and it fetches directly.
    """
    username = os.environ.get("WEBSHARE_PROXY_USERNAME")
    if not username:
        return YouTubeTranscriptApi()
    proxy = WebshareProxyConfig(
        proxy_username=username,
        proxy_password=os.environ["WEBSHARE_PROXY_PASSWORD"],
    )
    return YouTubeTranscriptApi(proxy_config=proxy)


def format_for_prompt(segments: list[dict]) -> str:
    """Turn segments into plain text with a [seconds] marker on each line.

    The markers let Claude tell us *where* in the video an idea appears,
    which we turn into a timestamp link on each card.
    """
    lines = []
    for segment in segments:
        seconds = int(segment["start"])
        text = segment["text"].replace("\n", " ")
        lines.append(f"[{seconds}] {text}")
    return "\n".join(lines)


def parse_pasted_transcript(text: str) -> list[dict]:
    """Turn a transcript copied from YouTube's "Show transcript" panel into segments.

    Handles the shapes YouTube copies as:
        0:00                          a timestamp on its own line,
        In this video we'll look at   then the text;
        1:02:15 and that's why...     or timestamp and text on one line.
    YouTube sometimes adds a spoken-out label under each timestamp
    ("2 minutes, 5 seconds"); those lines are skipped.

    Lines with no timestamp before them start at 0 seconds, so a plain paste
    with no timestamps still works. has_timestamps() tells the page whether
    the card times mean anything.
    """
    segments = []
    start = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or SPOKEN_TIME.fullmatch(line):
            continue
        match = TIMESTAMP_AT_START.match(line)
        if match:
            start = _timestamp_to_seconds(match.group(1))
            line = (match.group(2) or "").strip()
            if not line:
                continue
        segments.append({"text": line, "start": start, "duration": 0})
    return segments


def has_timestamps(segments: list[dict]) -> bool:
    """True if any segment starts after 0:00, i.e. we know where things are."""
    return any(segment["start"] > 0 for segment in segments)


# "1:02:15" or "0:05", optionally followed by the line's text.
TIMESTAMP_AT_START = re.compile(r"(\d{1,2}(?::\d{2}){1,2})(?:\s+(.*)|$)")
# YouTube's spoken-out labels: "5 seconds", "2 minutes, 5 seconds", "1 hour, 2 minutes".
SPOKEN_TIME = re.compile(r"(\d+ (hours?|minutes?|seconds?),? ?)+")


def _timestamp_to_seconds(stamp: str) -> int:
    """'1:02:15' -> 3735."""
    seconds = 0
    for part in stamp.split(":"):
        seconds = seconds * 60 + int(part)
    return seconds
