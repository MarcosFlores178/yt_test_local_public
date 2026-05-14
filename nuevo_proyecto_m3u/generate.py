from __future__ import annotations

import argparse
import logging

from m3u_app.config import load_app_config
from m3u_app.pipeline import PlaylistGenerator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera la playlist M3U combinada.")
    parser.add_argument("--config", default="config.json", help="Ruta al archivo de configuración JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Procesa canales sin escribir archivos.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_app_config(args.config)
    logging.basicConfig(level=getattr(logging, config.logging.level.upper(), logging.INFO), format="%(levelname)s: %(message)s")

    generator = PlaylistGenerator(config)
    result = generator.run(write_output=not args.dry_run)
    logging.info("Proceso completado: %s canales en %s grupos.", result.channel_count, result.group_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
