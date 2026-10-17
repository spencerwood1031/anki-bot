"""Step 1: get a timestamped transcript for a YouTube video."""

from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi


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
    fetched = YouTubeTranscriptApi().fetch(video_id)
    return fetched.to_raw_data()


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
