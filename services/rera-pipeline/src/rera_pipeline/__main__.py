"""Pipeline entry point: python -m rera_pipeline <stage>. See docs/MAP-01."""

import argparse
import sys

STAGES = {
    "fetch": "S01: list and download K-RERA project pages",
    "parse": "S01: parse raw pages into rera_project_raw",
    "locate": "S02: place projects (cascade in docs/MAP-02)",
    "enrich": "S03: fill missing facts with sources",
    "export": "S04: write PMTiles for the map",
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rera_pipeline", description=__doc__)
    sub = ap.add_subparsers(dest="stage", required=True)
    for name, help_ in STAGES.items():
        sub.add_parser(name, help=help_)
    sub.add_parser("sharpen", help="re-place approximate seed pins (locate.sharpen --help)")
    args, rest = ap.parse_known_args(argv)
    if args.stage == "sharpen":
        from .locate import sharpen

        sys.argv = ["sharpen", *rest]
        sharpen.main()
        return 0
    print(
        f"{args.stage}: not implemented yet ({STAGES[args.stage].split(':')[0]})", file=sys.stderr
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
