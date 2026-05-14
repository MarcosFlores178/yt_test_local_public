from __future__ import annotations

import logging
import shutil
from pathlib import Path


LOGGER = logging.getLogger(__name__)


def deploy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    LOGGER.info("Archivo desplegado en %s", destination)
