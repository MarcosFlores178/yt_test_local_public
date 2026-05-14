from __future__ import annotations

import argparse
import logging

from m3u_app.config import load_app_config
from m3u_app.revive import PlaylistReviver


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Intenta revivir entradas offline de una playlist existente.")
    parser.add_argument("--config", default="config.json", help="Ruta al archivo de configuración JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Analiza cambios sin escribir archivos.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_app_config(args.config)
    logging.basicConfig(level=getattr(logging, config.logging.level.upper(), logging.INFO), format="%(levelname)s: %(message)s")

    reviver = PlaylistReviver(config)
    revived = reviver.run(write_output=not args.dry_run)
    logging.info("Proceso completado: %s canales revividos.", revived)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
