from __future__ import annotations

import logging
import time

from m3u_app.cache import load_cache, save_cache
from m3u_app.config import AppConfig
from m3u_app.deploy import deploy_file
from m3u_app.healthcheck import LinkChecker
from m3u_app.io_utils import atomic_write_text
from m3u_app.models import DynamicChannelSource
from m3u_app.parsers import parse_channel_file, parse_playlist, parse_static_m3u
from m3u_app.playlist import group_channels, render_playlist
from m3u_app.youtube import YoutubeResolver


LOGGER = logging.getLogger(__name__)


class PlaylistReviver:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.cache = load_cache(config.paths.cache_file)
        self.link_checker = LinkChecker(config)
        self.youtube = YoutubeResolver(config, self.cache)
        self.dynamic_sources = {source.name.lower(): source for source in parse_channel_file(config.paths.channels_file)}
        self.static_sources = {source.name.lower(): source for source in parse_static_m3u(config.paths.static_list_file)}

    def run(self, write_output: bool = True) -> int:
        playlist = parse_playlist(self.config.paths.output_file)
        revived_count = 0

        for channel in playlist:
            if self.config.error_urls.base_error_url not in channel.url:
                continue

            recovered = self._recover_channel(channel.name)
            if not recovered:
                LOGGER.info("Sigue offline: %s", channel.name)
                continue

            channel.url = recovered
            revived_count += 1
            LOGGER.info("Revivido: %s", channel.name)

        if write_output and revived_count:
            grouped = group_channels(playlist)
            atomic_write_text(self.config.paths.output_file, render_playlist(grouped, self.config.playlist))
            save_cache(self.config.paths.cache_file, self.cache)
            if self.config.deploy.enabled:
                deploy_file(self.config.paths.output_file, self.config.deploy.destination_file)

        LOGGER.info("Revisión completada a las %s", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        return revived_count

    def _recover_channel(self, channel_name: str) -> str | None:
        source = self.dynamic_sources.get(channel_name.lower())
        if source:
            return self._recover_dynamic(source, requested_name=channel_name)

        static_channel = self.static_sources.get(channel_name.lower())
        if static_channel:
            validated = self.link_checker.validate(static_channel.url, static_channel.name, is_youtube=False)
            return static_channel.url if validated is True else None

        base_name = channel_name.split(" - Señal ")[0].strip().lower()
        source = self.dynamic_sources.get(base_name)
        if source:
            return self._recover_dynamic(source, requested_name=channel_name)

        return None

    def _recover_dynamic(self, source: DynamicChannelSource, requested_name: str) -> str | None:
        if "youtube" not in source.source_url.lower():
            validated = self.link_checker.validate(source.source_url, source.name, is_youtube=False)
            return source.source_url if validated is True else None

        revive_cache = self.cache.setdefault("revive", {})
        cached = revive_cache.get(source.source_url)
        if cached and (time.time() - float(cached.get("timestamp", 0)) < 600):
            cached_url = cached.get("url")
            validated = self.link_checker.validate(cached_url, requested_name, is_youtube=True)
            if validated is True:
                return cached_url

        live_entries, _next_event = self.youtube.resolve_live_entries(source.source_url, source.name)
        for entry in live_entries:
            if entry["name"].lower() == requested_name.lower():
                validated = self.link_checker.validate(entry["link"], requested_name, is_youtube=True)
                if validated is True:
                    revive_cache[source.source_url] = {"timestamp": time.time(), "url": entry["link"]}
                    return entry["link"]

        if live_entries:
            fallback = live_entries[0]["link"]
            validated = self.link_checker.validate(fallback, requested_name, is_youtube=True)
            if validated is True:
                revive_cache[source.source_url] = {"timestamp": time.time(), "url": fallback}
                return fallback

        return None
