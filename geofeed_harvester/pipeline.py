from __future__ import annotations

from pathlib import Path
from datetime import UTC, datetime

from geofeed_harvester.bgp import BgpValidator, CymruBulkBgpValidator
from geofeed_harvester.discovery import dedupe_refs, parse_rir_dump
from geofeed_harvester.export import write_outputs
from geofeed_harvester.fetch import HttpCache, fetch_all
from geofeed_harvester.sources import load_direct_geofeed
from geofeed_harvester.validate import validate_rows


async def run_harvest(
    rir_dump_paths: list[Path],
    out_dir: Path,
    cache_dir: Path,
    concurrency: int = 32,
    bgp_validator: str = "none",
    direct_geofeed_paths: list[tuple[str, str, Path]] | None = None,
) -> dict[str, int]:
    refs = []
    for path in rir_dump_paths:
        refs.extend(parse_rir_dump(path.read_text(encoding="utf-8", errors="replace"), source=str(path)))
    refs = dedupe_refs(refs)

    results = await fetch_all(refs, HttpCache(cache_dir), concurrency=concurrency)
    raw_rows = [row for result in results for row in result.rows]
    fetched_at_by_url = {result.ref.url: result.fetched_at for result in results}

    direct_rows = []
    for rir, url, path in direct_geofeed_paths or []:
        fetched_at = datetime.now(UTC).isoformat(timespec="seconds")
        direct_rows.extend(load_direct_geofeed(path, rir=rir, url=url, fetched_at=fetched_at))
        fetched_at_by_url[url] = fetched_at
    raw_rows.extend(direct_rows)

    validator: BgpValidator | None
    if bgp_validator == "cymru":
        validator = CymruBulkBgpValidator()
    else:
        validator = None
    bgp_verdicts = {}
    if validator is not None:
        bgp_verdicts = await validator.validate_prefixes(row.prefix for row in raw_rows)

    validated = validate_rows(raw_rows, fetched_at_by_url, bgp_verdicts=bgp_verdicts)
    write_outputs(validated, out_dir)

    return {
        "refs": len(refs),
        "fetches": len(results),
        "failed_fetches": sum(1 for result in results if result.status == "failed"),
        "raw_rows": len(raw_rows),
        "direct_rows": len(direct_rows),
        "valid_rows": len(validated),
        "bgp_checked": len(bgp_verdicts),
    }
