"""Step 1: get a timestamped transcript for a YouTube video."""

import os
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
