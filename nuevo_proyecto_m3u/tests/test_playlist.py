from m3u_app.models import PlaylistChannel
from m3u_app.playlist import group_channels, render_playlist


class DummyPlaylistConfig:
    epg_url = "https://example.com/epg.xml"
    group_order = ["Noticias", "Deportes"]


def test_group_channels_groups_by_title() -> None:
    grouped = group_channels(
        [
            PlaylistChannel("A", "Noticias", "A", "logo-a", "url-a"),
            PlaylistChannel("B", "Deportes", "B", "logo-b", "url-b"),
            PlaylistChannel("C", "Noticias", "C", "logo-c", "url-c"),
        ]
    )

    assert list(grouped.keys()) == ["Noticias", "Deportes"]
    assert [channel.name for channel in grouped["Noticias"]] == ["A", "C"]


def test_render_playlist_renders_groups_and_options() -> None:
    grouped = {
        "Noticias": [
            PlaylistChannel(
                name="Canal Uno",
                group_title="Noticias",
                tvg_id="CANAL_UNO",
                tvg_logo="http://logo/uno.png",
                url="http://stream.example.com/uno.m3u8",
                options=["#EXTVLCOPT:http-reconnect=true"],
            )
        ]
    }

    rendered = render_playlist(grouped, DummyPlaylistConfig())

    assert '#EXTM3U x-tvg-url="https://example.com/epg.xml"' in rendered
    assert 'group-title="Noticias" tvg-id="CANAL_UNO"' in rendered
    assert "#EXTVLCOPT:http-reconnect=true" in rendered
    assert "http://stream.example.com/uno.m3u8" in rendered
