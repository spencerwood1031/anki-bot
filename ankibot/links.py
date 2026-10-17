"""Build links that open a YouTube video at a specific moment."""


def timestamp_url(video_id: str, seconds: int) -> str:
    """e.g. timestamp_url("aircAruvnKk", 95) -> "https://youtu.be/aircAruvnKk?t=95" """
    return f"https://youtu.be/{video_id}?t={int(seconds)}"
