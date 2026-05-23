from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from geofeed_harvester.pipeline import run_harvest


def main() -> None:
    parser = argparse.ArgumentParser(description="Harvest RFC 8805 geofeed datasets.")
    parser.add_argument(
        "--rir-dump",
        action="append",
        required=True,
        type=Path,
        help="Path to a bulk/RDAP-style RIR text dump. Can be passed multiple times.",
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

    stats = asyncio.run(
        run_harvest(
            rir_dump_paths=args.rir_dump,
            out_dir=args.out_dir,
            cache_dir=args.cache_dir,
            concurrency=args.concurrency,
            bgp_validator=args.bgp_validator,
        )
    )
    print(json.dumps(stats, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
