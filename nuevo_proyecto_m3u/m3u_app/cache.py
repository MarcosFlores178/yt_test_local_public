from __future__ import annotations

import logging
from pathlib import Path

from m3u_app.io_utils import atomic_write_json
from m3u_app.models import CacheData


LOGGER = logging.getLogger(__name__)


def load_cache(cache_file: Path) -> CacheData:
    if not cache_file.exists():
        return {"version": 1, "youtube": {}, "revive": {}}

    try:
        import json

        with cache_file.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("El caché no contiene un objeto JSON.")
        data.setdefault("version", 1)
        data.setdefault("youtube", {})
        data.setdefault("revive", {})
        return data
    except Exception as exc:
        LOGGER.warning("No se pudo leer el caché %s: %s. Se usará uno vacío.", cache_file, exc)
        return {"version": 1, "youtube": {}, "revive": {}}


def save_cache(cache_file: Path, cache: CacheData) -> None:
    atomic_write_json(cache_file, cache)
