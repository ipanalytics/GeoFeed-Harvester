from __future__ import annotations

import re
from collections.abc import Iterable

from geofeed_harvester.models import RawGeofeedRow, ValidatedGeofeedRow

COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
REGION_RE = re.compile(r"^$|^[A-Z]{2}-[A-Z0-9]{1,3}$")


def validate_rows(
    rows: Iterable[RawGeofeedRow],
    fetched_at_by_url: dict[str, str],
    bgp_verdicts: dict[object, bool | None] | None = None,
) -> list[ValidatedGeofeedRow]:
    bgp_verdicts = bgp_verdicts or {}
    candidates: list[ValidatedGeofeedRow] = []
    for row in rows:
        flags: list[str] = []
        if row.prefix.version != row.inetnum.version:
            flags.append("ip_version_mismatch")
        elif not row.prefix.subnet_of(row.inetnum):
            flags.append("outside_inetnum")
        if not COUNTRY_RE.fullmatch(row.country):
            flags.append("invalid_country")
        if row.region and not REGION_RE.fullmatch(row.region.upper()):
            flags.append("invalid_region")

        if "outside_inetnum" in flags or "ip_version_mismatch" in flags:
            continue

        confidence = 0.55
        if not flags:
            confidence += 0.25
        bgp_valid = bgp_verdicts.get(row.prefix)
        if bgp_valid is True:
            confidence += 0.1
        elif bgp_valid is False:
            flags.append("bgp_not_announced")
            confidence -= 0.2

        candidates.append(
            ValidatedGeofeedRow(
                prefix=row.prefix,
                country=row.country,
                region=row.region.upper(),
                city=row.city,
                postal_code=row.postal_code,
                url=row.url,
                rir=row.rir,
                inetnum=row.inetnum,
                fetched_at=fetched_at_by_url.get(row.url, ""),
                bgp_valid=bgp_valid,
                confidence=confidence,
                flags=tuple(flags),
            )
        )

    return _prefer_most_specific_inetnum(candidates)


def _prefer_most_specific_inetnum(rows: list[ValidatedGeofeedRow]) -> list[ValidatedGeofeedRow]:
    winners: list[ValidatedGeofeedRow] = []
    for row in sorted(rows, key=lambda r: (r.prefix.version, int(r.prefix.network_address), -r.prefix.prefixlen)):
        existing_idx = _find_covering_conflict(winners, row)
        if existing_idx is None:
            winners.append(row)
            continue
        existing = winners[existing_idx]
        if row.inetnum.prefixlen > existing.inetnum.prefixlen:
            winners[existing_idx] = _with_flag(row, "overlap_more_specific_inetnum")
        elif row.inetnum.prefixlen == existing.inetnum.prefixlen and row.prefix.prefixlen > existing.prefix.prefixlen:
            winners[existing_idx] = _with_flag(row, "overlap_more_specific_prefix")
        else:
            winners[existing_idx] = _with_flag(existing, "overlap_conflict")
    return sorted(winners, key=lambda r: (r.prefix.version, int(r.prefix.network_address), r.prefix.prefixlen))


def _find_covering_conflict(rows: list[ValidatedGeofeedRow], row: ValidatedGeofeedRow) -> int | None:
    for idx, existing in enumerate(rows):
        if existing.prefix.version != row.prefix.version:
            continue
        if row.prefix.overlaps(existing.prefix):
            return idx
    return None


def _with_flag(row: ValidatedGeofeedRow, flag: str) -> ValidatedGeofeedRow:
    flags = tuple(dict.fromkeys((*row.flags, flag)))
    return ValidatedGeofeedRow(
        prefix=row.prefix,
        country=row.country,
        region=row.region,
        city=row.city,
        postal_code=row.postal_code,
        url=row.url,
        rir=row.rir,
        inetnum=row.inetnum,
        fetched_at=row.fetched_at,
        signed=row.signed,
        signature_valid=row.signature_valid,
        bgp_valid=row.bgp_valid,
        confidence=max(row.confidence - 0.15, 0.0),
        flags=flags,
    )
