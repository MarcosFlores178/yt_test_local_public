from __future__ import annotations

import logging
import time

from m3u_app.cache import load_cache, save_cache
from m3u_app.config import AppConfig
from m3u_app.deploy import deploy_file
from m3u_app.healthcheck import LinkChecker
from m3u_app.io_utils import atomic_write_text
from m3u_app.models import GenerationResult, PlaylistChannel
from m3u_app.parsers import parse_channel_file, parse_static_m3u
from m3u_app.playlist import group_channels, render_playlist
from m3u_app.youtube import YoutubeResolver


LOGGER = logging.getLogger(__name__)


class PlaylistGenerator:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.cache = load_cache(config.paths.cache_file)
        self.link_checker = LinkChecker(config)
        self.youtube = YoutubeResolver(config, self.cache)

    def run(self, write_output: bool = True) -> GenerationResult:
        generated_channels: list[PlaylistChannel] = []

        for channel in parse_channel_file(self.config.paths.channels_file):
            generated_channels.extend(self._resolve_dynamic_channel(channel))

        for channel in parse_static_m3u(self.config.paths.static_list_file):
            validated = self.link_checker.validate(channel.url, channel.name, is_youtube=False)
            if validated is not True:
                channel.url = validated
                LOGGER.info("Estático offline: %s", channel.name)
            generated_channels.append(channel)

        grouped = group_channels(generated_channels)
        result = GenerationResult(grouped)

        if write_output:
            playlist_text = render_playlist(grouped, self.config.playlist)
            atomic_write_text(self.config.paths.output_file, playlist_text)
            save_cache(self.config.paths.cache_file, self.cache)
            if self.config.deploy.enabled:
                deploy_file(self.config.paths.output_file, self.config.deploy.destination_file)

        LOGGER.info("Finalizado a las %s", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        return result

    def _resolve_dynamic_channel(self, channel) -> list[PlaylistChannel]:
        LOGGER.info("Procesando %s", channel.name)

        if "youtube" not in channel.source_url.lower():
            validated = self.link_checker.validate(channel.source_url, channel.name, is_youtube=False)
            final_url = channel.source_url if validated is True else validated
            return [
                PlaylistChannel(
                    name=channel.name,
                    group_title=channel.group,
                    tvg_id=channel.tvg_id,
                    tvg_logo=channel.logo,
                    url=final_url,
                )
            ]

        live_entries, _next_event = self.youtube.resolve_live_entries(channel.source_url, channel.name)
        if not live_entries:
            return [
                PlaylistChannel(
                    name=channel.name,
                    group_title=channel.group,
                    tvg_id=channel.tvg_id,
                    tvg_logo=channel.logo,
                    url=self.link_checker.build_offline_url(channel.name),
                )
            ]

        resolved_channels: list[PlaylistChannel] = []
        total = len(live_entries)
        for index, live_entry in enumerate(live_entries, 1):
            validated = self.link_checker.validate(live_entry["link"], live_entry["name"], is_youtube=True)
            final_url = live_entry["link"] if validated is True else validated
            tvg_id = channel.tvg_id if total == 1 else f"{channel.tvg_id} {index}"
            resolved_channels.append(
                PlaylistChannel(
                    name=live_entry["name"],
                    group_title=channel.group,
                    tvg_id=tvg_id,
                    tvg_logo=channel.logo,
                    url=final_url,
                )
            )
        return resolved_channels
