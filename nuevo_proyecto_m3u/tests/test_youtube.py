from pathlib import Path

from m3u_app.config import load_app_config
from m3u_app.youtube import YoutubeResolver


class FakeYoutubeDL:
    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def extract_info(self, url, download=False):
        if url.endswith("/streams"):
            return {
                "entries": [
                    {
                        "id": "abc123",
                        "title": "Canal en vivo",
                        "live_status": "is_live",
                    },
                    {
                        "id": "upcoming1",
                        "title": "Programado",
                        "live_status": "is_upcoming",
                        "release_timestamp": 200,
                    },
                ]
            }

        if "watch?v=abc123" in url:
            return {"url": "https://manifest.googlevideo.com/api/playlist/yt_live_broadcast/abc123.m3u8"}

        return {}


def test_resolve_live_entries_uses_ytdlp_and_updates_cache(monkeypatch) -> None:
    config = load_app_config(str(Path(__file__).resolve().parents[1] / "config.json"))
    cache = {"version": 1, "youtube": {}, "revive": {}}

    monkeypatch.setattr("m3u_app.youtube.yt_dlp.YoutubeDL", FakeYoutubeDL)

    resolver = YoutubeResolver(config, cache)
    live_entries, next_event = resolver.resolve_live_entries("https://www.youtube.com/@canal/live", "Canal Test")

    assert len(live_entries) == 1
    assert live_entries[0]["name"] == "Canal Test"
    assert "yt_live_broadcast" in live_entries[0]["link"]
    assert next_event == 200
    assert "https://www.youtube.com/@canal/live" in cache["youtube"]


def test_resolve_live_entries_uses_cache_when_fresh() -> None:
    config = load_app_config(str(Path(__file__).resolve().parents[1] / "config.json"))
    cache = {
        "version": 1,
        "youtube": {
            "https://www.youtube.com/@canal/live": {
                "timestamp": 9999999999,
                "next_event": 123,
                "vivos": [{"name": "Canal Cache", "link": "cached-link"}],
            }
        },
        "revive": {},
    }

    resolver = YoutubeResolver(config, cache)
    live_entries, next_event = resolver.resolve_live_entries("https://www.youtube.com/@canal/live", "Canal Test")

    assert live_entries == [{"name": "Canal Cache", "link": "cached-link"}]
    assert next_event == 123
