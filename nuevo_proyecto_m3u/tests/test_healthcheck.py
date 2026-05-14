from pathlib import Path

from m3u_app.config import load_app_config
from m3u_app.healthcheck import LinkChecker


def test_build_offline_url_slugifies_channel_name() -> None:
    config = load_app_config(str(Path(__file__).resolve().parents[1] / "config.json"))
    checker = LinkChecker(config)

    offline_url = checker.build_offline_url("Crónica TV HD")

    assert offline_url.endswith("/cr_nica_tv_hd/offline.m3u8")
