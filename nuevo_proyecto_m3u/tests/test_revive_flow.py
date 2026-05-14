from pathlib import Path

from m3u_app.config import load_app_config
from m3u_app.models import DynamicChannelSource, PlaylistChannel
from m3u_app.revive import PlaylistReviver


def test_recover_dynamic_uses_matching_signal_name(monkeypatch) -> None:
    config = load_app_config(str(Path(__file__).resolve().parents[1] / "config.json"))

    monkeypatch.setattr(
        "m3u_app.revive.parse_channel_file",
        lambda path: [
            DynamicChannelSource(
                name="Telefe Streams",
                group="Nacionales",
                logo="http://logo/telefe.png",
                tvg_id="TELEFE",
                source_url="https://www.youtube.com/@telefe/live",
            )
        ],
    )
    monkeypatch.setattr("m3u_app.revive.parse_static_m3u", lambda path: [])

    reviver = PlaylistReviver(config)

    monkeypatch.setattr(
        reviver.youtube,
        "resolve_live_entries",
        lambda source_url, original_name: (
            [
                {"name": "Telefe Streams - Señal 1", "link": "http://signal-1.m3u8"},
                {"name": "Telefe Streams - Señal 2", "link": "http://signal-2.m3u8"},
            ],
            None,
        ),
    )
    monkeypatch.setattr(reviver.link_checker, "validate", lambda url, channel_name, is_youtube=False: True)

    recovered = reviver._recover_channel("Telefe Streams - Señal 2")

    assert recovered == "http://signal-2.m3u8"


def test_recover_static_channel_returns_none_when_validation_fails(monkeypatch) -> None:
    config = load_app_config(str(Path(__file__).resolve().parents[1] / "config.json"))

    monkeypatch.setattr("m3u_app.revive.parse_channel_file", lambda path: [])
    monkeypatch.setattr(
        "m3u_app.revive.parse_static_m3u",
        lambda path: [
            PlaylistChannel(
                name="Canal Local",
                group_title="Locales",
                tvg_id="LOCAL",
                tvg_logo="http://logo/local.png",
                url="http://stream.local/live.m3u8",
            )
        ],
    )

    reviver = PlaylistReviver(config)
    monkeypatch.setattr(reviver.link_checker, "validate", lambda url, channel_name, is_youtube=False: "offline-url")

    recovered = reviver._recover_channel("Canal Local")

    assert recovered is None
