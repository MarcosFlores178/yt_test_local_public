from __future__ import annotations

import logging
import random
import re
import time

import requests
import urllib3
from requests.exceptions import ConnectionError, Timeout

from m3u_app.config import AppConfig


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LOGGER = logging.getLogger(__name__)


class LinkChecker:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def build_offline_url(self, channel_name: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", channel_name).strip("_").lower()
        return f"{self.config.error_urls.base_error_url}/{slug}/offline.m3u8"

    def _build_headers(self, include_language: bool) -> dict[str, str]:
        headers = {
            "User-Agent": random.choice(self.config.network.user_agents),
            "Range": "bytes=0-1024",
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Connection": "keep-alive",
        }
        if include_language:
            headers["Accept-Language"] = "es-AR,es;q=0.9,en;q=0.8"
        return headers

    def validate(self, url: str | None, channel_name: str, is_youtube: bool = False) -> bool | str:
        if not url or self.config.error_urls.base_error_url in url:
            return self.build_offline_url(channel_name)

        retries = self.config.network.youtube_max_retries if is_youtube else self.config.network.max_retries
        timeout = self.config.network.youtube_request_timeout_seconds if is_youtube else self.config.network.request_timeout_seconds
        delays = [random.uniform(1.5, 3.0) for _ in range(max(retries, 1))]

        with requests.Session() as session:
            for attempt in range(retries):
                try:
                    response = session.get(
                        url,
                        headers=self._build_headers(include_language=is_youtube),
                        timeout=timeout,
                        stream=True,
                        verify=self.config.network.verify_tls,
                        allow_redirects=True,
                    )
                    if response.status_code not in (200, 206):
                        raise requests.HTTPError(f"Estado HTTP {response.status_code}")

                    if self._looks_finished(url, response):
                        raise ValueError("La playlist parece finalizada.")

                    return True
                except (Timeout, ConnectionError, requests.RequestException, ValueError) as exc:
                    LOGGER.debug("Chequeo fallido para %s (%s/%s): %s", channel_name, attempt + 1, retries, exc)
                    if attempt + 1 < retries:
                        time.sleep(delays[attempt])

        return self.build_offline_url(channel_name)

    @staticmethod
    def _looks_finished(url: str, response: requests.Response) -> bool:
        if ".m3u8" not in url.lower() and "manifest" not in url.lower():
            return False

        inspected = 0
        for line in response.iter_lines():
            if not line:
                continue
            if b"#EXT-X-ENDLIST" in line.upper():
                return True
            inspected += 1
            if inspected >= 60:
                break
        return False
