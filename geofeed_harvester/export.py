from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from pathlib import Path

from geofeed_harvester.models import ValidatedGeofeedRow

CSV_HEADER = [
    "prefix",
    "country",
    "region",
    "city",
    "postal_code",
    "rir",
    "inetnum",
    "url",
    "fetched_at",
    "signed",
    "signature_valid",
    "bgp_valid",
    "confidence",
    "flags",
]


def write_outputs(rows: Iterable[ValidatedGeofeedRow], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    materialized = list(rows)
    _write_csv(materialized, out_dir / "geofeed.csv")
    _write_jsonl(materialized, out_dir / "geofeed.jsonl")
    _write_changelog(materialized, out_dir / "changelog.md")


def _write_csv(rows: list[ValidatedGeofeedRow], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_HEADER)
        writer.writerows(row.csv_fields() for row in rows)


def _write_jsonl(rows: list[ValidatedGeofeedRow], path: Path) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row.json_dict(), ensure_ascii=False, sort_keys=True))
            fh.write("\n")


def _write_changelog(rows: list[ValidatedGeofeedRow], path: Path) -> None:
    by_rir: dict[str, int] = {}
    flagged = 0
    for row in rows:
        by_rir[row.rir] = by_rir.get(row.rir, 0) + 1
        if row.flags:
            flagged += 1

    lines = [
        "# GeoFeed Harvester Changelog",
        "",
        f"- Valid rows: {len(rows)}",
        f"- Rows with flags: {flagged}",
        "",
        "## By RIR",
        "",
    ]
    for rir, count in sorted(by_rir.items()):
        lines.append(f"- {rir}: {count}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
