from __future__ import annotations

import logging
import time
from pathlib import Path

import yt_dlp

from m3u_app.config import AppConfig
from m3u_app.models import CacheData


LOGGER = logging.getLogger(__name__)


class YoutubeResolver:
    def __init__(self, config: AppConfig, cache: CacheData) -> None:
        self.config = config
        self.cache = cache

    def resolve_live_entries(self, channel_url: str, original_name: str) -> tuple[list[dict[str, str]], int | None]:
        cached = self._read_cache(channel_url)
        if cached is not None:
            return cached

        clean_url = channel_url.split("/live")[0].split("/streams")[0].rstrip("/")
        search_url = f"{clean_url}/streams"
        next_event: int | None = None
        resolved_links: list[str] = []

        try:
            with yt_dlp.YoutubeDL(self._channel_opts()) as ydl:
                info = ydl.extract_info(search_url, download=False)
        except Exception as exc:
            LOGGER.warning("Error al escanear YouTube para %s: %s", original_name, exc)
            return [], None

        for entry in info.get("entries", []) or []:
            title = (entry.get("title") or "").upper()
            status = entry.get("live_status")

            if status == "is_upcoming" or any(word in title for word in ("PROGRAMADO", "ESPERA", "PRÓXIMAMENTE")):
                release_ts = entry.get("release_timestamp")
                if release_ts is not None and (next_event is None or release_ts < next_event):
                    next_event = release_ts
                continue

            if status != "is_live":
                continue

            video_id = entry.get("id")
            if not video_id:
                continue

            direct_url = self.extract_m3u8(f"https://www.youtube.com/watch?v={video_id}")
            if direct_url and "yt_live_broadcast" in direct_url:
                resolved_links.append(direct_url)

        live_entries = []
        total = len(resolved_links)
        for index, link in enumerate(resolved_links, 1):
            name = original_name if total == 1 else f"{original_name} - Señal {index}"
            live_entries.append({"name": name, "link": link})

        self.cache["youtube"][channel_url] = {
            "timestamp": time.time(),
            "next_event": next_event,
            "vivos": live_entries,
        }
        return live_entries, next_event

    def extract_m3u8(self, video_url: str) -> str | None:
        try:
            with yt_dlp.YoutubeDL(self._video_opts()) as ydl:
                info = ydl.extract_info(video_url, download=False)
            return info.get("url")
        except Exception as exc:
            LOGGER.debug("No se pudo extraer m3u8 para %s: %s", video_url, exc)
            return None

    def _read_cache(self, channel_url: str) -> tuple[list[dict[str, str]], int | None] | None:
        youtube_cache = self.cache.get("youtube", {})
        data = youtube_cache.get(channel_url)
        if not data:
            return None

        age = time.time() - float(data.get("timestamp", 0))
        if age > self.config.youtube.cache_ttl_seconds:
            return None

        return data.get("vivos", []), data.get("next_event")

    def _common_opts(self) -> dict[str, object]:
        opts: dict[str, object] = {
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android"],
                    "player_skip": ["web", "tv"],
                }
            },
        }
        cookie_file: Path = self.config.paths.cookies_file
        if cookie_file.exists():
            opts["cookiefile"] = str(cookie_file)
        return opts

    def _channel_opts(self) -> dict[str, object]:
        opts = self._common_opts()
        opts.update({"extract_flat": True, "playlist_items": self.config.youtube.playlist_items})
        return opts

    def _video_opts(self) -> dict[str, object]:
        opts = self._common_opts()
        opts.update({"format": "96/best"})
        return opts
