from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DynamicChannelSource:
    name: str
    group: str
    logo: str
    tvg_id: str
    source_url: str


@dataclass(slots=True)
class PlaylistChannel:
    name: str
    group_title: str
    tvg_id: str
    tvg_logo: str
    url: str
    options: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GenerationResult:
    grouped_channels: dict[str, list[PlaylistChannel]]

    @property
    def channel_count(self) -> int:
        return sum(len(channels) for channels in self.grouped_channels.values())

    @property
    def group_count(self) -> int:
        return len(self.grouped_channels)


CacheData = dict[str, Any]
