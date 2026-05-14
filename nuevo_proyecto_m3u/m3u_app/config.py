from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PathsConfig:
    channels_file: Path
    static_list_file: Path
    cookies_file: Path
    cache_file: Path
    output_file: Path


@dataclass(slots=True)
class NetworkConfig:
    request_timeout_seconds: int
    youtube_request_timeout_seconds: int
    verify_tls: bool
    max_retries: int
    youtube_max_retries: int
    user_agents: list[str]


@dataclass(slots=True)
class YoutubeConfig:
    cache_ttl_seconds: int
    playlist_items: str


@dataclass(slots=True)
class ErrorUrlConfig:
    base_error_url: str


@dataclass(slots=True)
class PlaylistConfig:
    epg_url: str
    group_order: list[str]


@dataclass(slots=True)
class DeployConfig:
    enabled: bool
    destination_file: Path


@dataclass(slots=True)
class LoggingConfig:
    level: str


@dataclass(slots=True)
class AppConfig:
    base_dir: Path
    paths: PathsConfig
    network: NetworkConfig
    youtube: YoutubeConfig
    error_urls: ErrorUrlConfig
    playlist: PlaylistConfig
    deploy: DeployConfig
    logging: LoggingConfig


def _resolve_path(base_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else (base_dir / path).resolve()


def load_app_config(config_path: str) -> AppConfig:
    config_file = Path(config_path).resolve()
    with config_file.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    base_dir = config_file.parent
    paths = raw["paths"]

    return AppConfig(
        base_dir=base_dir,
        paths=PathsConfig(
            channels_file=_resolve_path(base_dir, paths["channels_file"]),
            static_list_file=_resolve_path(base_dir, paths["static_list_file"]),
            cookies_file=_resolve_path(base_dir, paths["cookies_file"]),
            cache_file=_resolve_path(base_dir, paths["cache_file"]),
            output_file=_resolve_path(base_dir, paths["output_file"]),
        ),
        network=NetworkConfig(**raw["network"]),
        youtube=YoutubeConfig(**raw["youtube"]),
        error_urls=ErrorUrlConfig(**raw["error_urls"]),
        playlist=PlaylistConfig(**raw["playlist"]),
        deploy=DeployConfig(
            enabled=raw["deploy"]["enabled"],
            destination_file=_resolve_path(base_dir, raw["deploy"]["destination_file"]),
        ),
        logging=LoggingConfig(**raw["logging"]),
    )
