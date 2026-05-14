from __future__ import annotations

from collections import defaultdict

from m3u_app.config import PlaylistConfig
from m3u_app.models import PlaylistChannel


def group_channels(channels: list[PlaylistChannel]) -> dict[str, list[PlaylistChannel]]:
    grouped: dict[str, list[PlaylistChannel]] = defaultdict(list)
    for channel in channels:
        grouped[channel.group_title].append(channel)
    return dict(grouped)


def render_playlist(grouped_channels: dict[str, list[PlaylistChannel]], config: PlaylistConfig) -> str:
    lines = [f'#EXTM3U x-tvg-url="{config.epg_url}"']
    ordered_groups = config.group_order + [group for group in grouped_channels if group not in config.group_order]

    for group in ordered_groups:
        for channel in grouped_channels.get(group, []):
            lines.append(
                f'#EXTINF:-1 group-title="{channel.group_title}" tvg-id="{channel.tvg_id}" '
                f'tvg-logo="{channel.tvg_logo}",{channel.name}'
            )
            lines.extend(channel.options)
            lines.append(channel.url)

    return "\n".join(lines) + "\n"
