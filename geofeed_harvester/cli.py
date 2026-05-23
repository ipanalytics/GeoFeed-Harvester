from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from geofeed_harvester.pipeline import run_harvest
from geofeed_harvester.sources import DIRECT_GEOFEED_SOURCES, prepare_inputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Harvest RFC 8805 geofeed datasets.")
    parser.add_argument(
        "--rir-dump",
        action="append",
        type=Path,
        help="Path to a bulk/RDAP-style RIR text dump. Can be passed multiple times.",
    )
    parser.add_argument(
        "--auto-discover",
        action="store_true",
        help="Download public RIR bulk sources, normalize geofeed references, then harvest.",
    )
    parser.add_argument("--bulk-dir", type=Path, default=Path(".cache/rir-bulk"))
    parser.add_argument("--normalized-rir-dump", type=Path, default=Path("data/rir.txt"))
    parser.add_argument("--direct-geofeed-dir", type=Path, default=Path(".cache/direct-geofeeds"))
    parser.add_argument(
        "--skip-lacnic",
        action="store_true",
        help="Skip LACNIC's direct public geofeed CSV during auto discovery.",
    )
    parser.add_argument("--out-dir", type=Path, default=Path("dist"))
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/geofeeds"))
    parser.add_argument("--concurrency", type=int, default=32)
    parser.add_argument(
        "--bgp-validator",
        choices=["none", "cymru"],
        default="none",
        help="Optional bulk BGP announcement validator. 'cymru' uses Team Cymru TCP/43 bulk WHOIS.",
    )
    args = parser.parse_args()

    input_stats = {}
    rir_dumps = list(args.rir_dump or [])
    direct_geofeeds = []
    if args.auto_discover:
        input_stats = prepare_inputs(
            raw_dir=args.bulk_dir,
            normalized_rir_path=args.normalized_rir_dump,
            direct_geofeed_dir=args.direct_geofeed_dir,
            include_lacnic=not args.skip_lacnic,
        )
        rir_dumps.append(args.normalized_rir_dump)
        if not args.skip_lacnic:
            for source in DIRECT_GEOFEED_SOURCES:
                direct_geofeeds.append(
                    (source.rir, source.url, args.direct_geofeed_dir / f"{source.name}.csv")
                )

    if not rir_dumps and not direct_geofeeds:
        parser.error("pass --rir-dump or use --auto-discover")

    stats = asyncio.run(
        run_harvest(
            rir_dump_paths=rir_dumps,
            out_dir=args.out_dir,
            cache_dir=args.cache_dir,
            concurrency=args.concurrency,
            bgp_validator=args.bgp_validator,
            direct_geofeed_paths=direct_geofeeds,
        )
    )
    stats = {**input_stats, **stats}
    print(json.dumps(stats, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
