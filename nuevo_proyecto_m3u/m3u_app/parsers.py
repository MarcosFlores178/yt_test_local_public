from __future__ import annotations

import logging
import re
from pathlib import Path

from m3u_app.models import DynamicChannelSource, PlaylistChannel


LOGGER = logging.getLogger(__name__)

EXTINF_NAME_SPLIT = re.compile(r"^[^,]*,(.*)$")


def parse_channel_file(path: Path) -> list[DynamicChannelSource]:
    if not path.exists():
        LOGGER.warning("No existe el archivo de canales dinámicos: %s", path)
        return []

    channels: list[DynamicChannelSource] = []
    current_header: dict[str, str] | None = None

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, 1):
            line = raw_line.strip()
            if not line or line.startswith("~~"):
                continue

            if line.startswith("http"):
                if current_header is None:
                    LOGGER.warning("URL sin cabecera en %s:%s: %s", path.name, line_number, line)
                    continue
                channels.append(
                    DynamicChannelSource(
                        name=current_header["name"],
                        group=current_header["group"],
                        logo=current_header["logo"],
                        tvg_id=current_header["tvg_id"],
                        source_url=line,
                    )
                )
                current_header = None
                continue

            parts = [part.strip() for part in line.split("|")]
            if len(parts) < 4:
                LOGGER.warning("Cabecera inválida en %s:%s: %s", path.name, line_number, line)
                current_header = None
                continue

            current_header = {
                "name": parts[0],
                "group": parts[1] or "Otros",
                "logo": parts[2],
                "tvg_id": parts[3],
            }

    if current_header is not None:
        LOGGER.warning("Cabecera sin URL al final de %s: %s", path.name, current_header["name"])

    return channels


def _extract_extinf_value(pattern: str, line: str) -> str:
    match = re.search(pattern, line)
    return match.group(1) if match else ""


def _extract_extinf_name(line: str) -> str:
    match = EXTINF_NAME_SPLIT.match(line)
    return match.group(1).strip() if match else line


def parse_static_m3u(path: Path) -> list[PlaylistChannel]:
    if not path.exists():
        LOGGER.warning("No existe la lista estática: %s", path)
        return []

    channels: list[PlaylistChannel] = []
    current_header: dict[str, str] | None = None
    options: list[str] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, 1):
            line = raw_line.strip()
            if not line or line.startswith("#EXTM3U"):
                continue

            if line.startswith("#EXTINF"):
                current_header = {
                    "tvg_id": _extract_extinf_value(r'tvg-id="([^"]+)"', line),
                    "tvg_logo": _extract_extinf_value(r'tvg-logo="([^"]+)"', line),
                    "group_title": _extract_extinf_value(r'group-title="([^"]+)"', line) or "Otros",
                    "name": _extract_extinf_name(line),
                }
                options = []
                continue

            if line.startswith("#EXTVLCOPT"):
                options.append(line)
                continue

            if line.startswith("http"):
                if current_header is None:
                    LOGGER.warning("URL estática sin #EXTINF en %s:%s: %s", path.name, line_number, line)
                    continue
                channels.append(
                    PlaylistChannel(
                        name=current_header["name"],
                        group_title=current_header["group_title"],
                        tvg_id=current_header["tvg_id"],
                        tvg_logo=current_header["tvg_logo"],
                        url=line,
                        options=options.copy(),
                    )
                )
                current_header = None
                options = []

    return channels


def parse_playlist(path: Path) -> list[PlaylistChannel]:
    return parse_static_m3u(path)
