from pathlib import Path

from m3u_app.parsers import parse_channel_file, parse_static_m3u


def test_parse_channel_file_skips_invalid_entries(tmp_path: Path) -> None:
    content = """~~ comentario
Canal Uno | Noticias | http://logo/uno.png | CANAL_UNO
https://www.youtube.com/@canaluno/live

Linea invalida
https://example.com/huorfana
Canal Dos | Deportes | http://logo/dos.png | CANAL_DOS
https://stream.example.com/live.m3u8
"""
    path = tmp_path / "channel.txt"
    path.write_text(content, encoding="utf-8")

    channels = parse_channel_file(path)

    assert len(channels) == 2
    assert channels[0].name == "Canal Uno"
    assert channels[0].source_url == "https://www.youtube.com/@canaluno/live"
    assert channels[1].name == "Canal Dos"
    assert channels[1].group == "Deportes"


def test_parse_static_m3u_preserves_options(tmp_path: Path) -> None:
    content = """#EXTM3U
#EXTINF:-1 tvg-id="ESPN" tvg-logo="http://logo/espn.png" group-title="Deportes",ESPN
#EXTVLCOPT:network-caching=1000
#EXTVLCOPT:http-reconnect=true
http://stream.example.com/espn.m3u8
"""
    path = tmp_path / "static_list.m3u"
    path.write_text(content, encoding="utf-8")

    channels = parse_static_m3u(path)

    assert len(channels) == 1
    assert channels[0].name == "ESPN"
    assert channels[0].group_title == "Deportes"
    assert channels[0].options == [
        "#EXTVLCOPT:network-caching=1000",
        "#EXTVLCOPT:http-reconnect=true",
    ]
