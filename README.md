# GeoFeed Harvester

Python batch harvester for RFC 8805 geofeed CSV files discovered from RIR data
according to RFC 9632.

The pipeline:

1. Parse bulk/RDAP-style RIR records into `inetnum -> geofeed URL` references.
2. Keep HTTPS-only geofeed URLs.
3. Fetch CSV files asynchronously with ETag and Last-Modified cache metadata.
4. Validate rows against the referring inetnum, RFC 8805 field shape, and ISO-like codes.
5. Resolve overlaps by preferring the most specific referring inetnum.
6. Attach provenance and confidence flags.
7. Publish `CSV` and `JSONL` outputs plus a daily changelog.

## Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

## Run

Create newline-delimited RIR records in text form:

```text
inetnum: 203.0.113.0/24
geofeed: https://example.net/geofeed.csv
source: RIPE

NetRange: 198.51.100.0 - 198.51.100.255
Comment: Geofeed https://example.org/geofeed.csv
```

Then harvest:

```bash
geofeed-harvester \
  --rir-dump data/rir.txt \
  --out-dir dist \
  --cache-dir .cache/geofeeds
```

Enable bulk BGP announcement checks through Team Cymru:

```bash
geofeed-harvester \
  --rir-dump data/rir.txt \
  --out-dir dist \
  --cache-dir .cache/geofeeds \
  --bgp-validator cymru
```

Outputs:

- `dist/geofeed.csv`
- `dist/geofeed.jsonl`
- `dist/changelog.md`

## Standards Notes

- Geofeed file format: RFC 8805.
- Discovery mechanism: RFC 9632, replacing RFC 9092.
- HTTPS geofeed URLs are required.
- RIPE/APNIC-style data may expose a `geofeed:` attribute.
- ARIN-style data is handled by treating `NetRange` as `inetnum` and
  `Comment` as `remarks`.
- Large-scale collection should use RIR bulk access where available. ARIN bulk
  access requires authorization, so RDAP enrichment belongs in a dedicated
  adapter.

## Verification Hooks

The current implementation ships conservative hooks for production hardening:

- RPKI CMS signature verification can be delegated to `rpki-client`.
- BGP announcement validation can use Team Cymru bulk WHOIS via
  `--bgp-validator cymru`, or later ASN-Signal-Graph/RouteSentinel.
- LACNIC Geofeeds Service can be added as a separate discovery adapter.
- RDAP fallback should use `RateLimitedRdapClient`, which caches responses and
  serializes requests per RDAP host.

## Bulk First

RDAP must stay a fallback path. The intended production order is:

1. RIR bulk dumps for geofeed discovery.
2. Team Cymru bulk WHOIS for BGP origin/prefix validation.
3. RDAP only for missing ARIN or malformed bulk records, with per-host pacing.

Team Cymru's IP-to-ASN service supports WHOIS bulk mode over TCP/43 with
`begin`, `verbose`, query lines, and `end`. Keep batches to a few thousand
addresses and avoid large volumes of individual WHOIS requests.
