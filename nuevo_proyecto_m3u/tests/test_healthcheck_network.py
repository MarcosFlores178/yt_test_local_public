from pathlib import Path

from m3u_app.config import load_app_config
from m3u_app.healthcheck import LinkChecker


class FakeResponse:
    def __init__(self, status_code=200, lines=None):
        self.status_code = status_code
        self._lines = lines or []

    def iter_lines(self):
        for line in self._lines:
            yield line


class FakeSession:
    def __init__(self, response):
        self.response = response

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, *args, **kwargs):
        return self.response


def test_validate_returns_true_for_online_stream(monkeypatch) -> None:
    config = load_app_config(str(Path(__file__).resolve().parents[1] / "config.json"))
    checker = LinkChecker(config)

    monkeypatch.setattr("m3u_app.healthcheck.requests.Session", lambda: FakeSession(FakeResponse(200, [b"#EXTM3U", b"#EXTINF"])))

    assert checker.validate("http://stream.example.com/live.m3u8", "Canal Test") is True


def test_validate_returns_offline_url_for_finished_playlist(monkeypatch) -> None:
    config = load_app_config(str(Path(__file__).resolve().parents[1] / "config.json"))
    checker = LinkChecker(config)

    monkeypatch.setattr(
        "m3u_app.healthcheck.requests.Session",
        lambda: FakeSession(FakeResponse(200, [b"#EXTM3U", b"#EXT-X-ENDLIST"])),
    )

    result = checker.validate("http://stream.example.com/live.m3u8", "Canal Test")

    assert result.endswith("/canal_test/offline.m3u8")
