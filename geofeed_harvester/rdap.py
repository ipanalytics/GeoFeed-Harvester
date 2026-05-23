from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx


class RateLimitedRdapClient:
    """RDAP fallback client with per-host pacing and persistent response cache."""

    def __init__(
        self,
        cache_dir: Path,
        min_interval_seconds: float = 2.0,
        timeout: float = 20.0,
    ):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval_seconds = min_interval_seconds
        self.timeout = timeout
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_request_at: dict[str, float] = {}

    async def get_json(self, url: str) -> dict:
        cache_path = self._cache_path(url)
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        host = urlparse(url).netloc
        lock = self._locks.setdefault(host, asyncio.Lock())
        async with lock:
            await self._pace(host)
            async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
                response = await client.get(url, headers={"Accept": "application/rdap+json"})
                response.raise_for_status()
                payload = response.json()
            cache_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            self._last_request_at[host] = time.monotonic()
            return payload

    async def _pace(self, host: str) -> None:
        last = self._last_request_at.get(host)
        if last is None:
            return
        elapsed = time.monotonic() - last
        if elapsed < self.min_interval_seconds:
            await asyncio.sleep(self.min_interval_seconds - elapsed)

    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"
