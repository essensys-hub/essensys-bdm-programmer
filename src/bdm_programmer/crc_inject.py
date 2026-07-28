"""`crc-inject` — post-link CRC-16 injection for essensys-gcc .s19 images.

Fills the gap essensys-gcc/bp/bootloader.c leaves open on purpose (commit
36de4cc, essensys-gcc#14): it emits a placeholder CRC (0x0102) at 0x3000 and
documents "the real value is injected post-link by the CRC tool". This is
that tool, implementing the algorithm confirmed in crc16.py.

essensys-gcc#14 is the upstream issue tracking this gap. This tool exists
in essensys-bdm-programmer per OpenSpec change
essensys-rpi4-bdm-programmer-2026-07-037 D4: reconcile with #14 once/if
essensys-gcc ships its own — do not maintain two divergent CRC
implementations long-term.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import memory_map as mm
from .programmer import inject_crc
from .srec import SRecFile, SRecordError


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        image = SRecFile.load(args.input)
    except (SRecordError, OSError) as exc:
        print(f"crc-inject: error reading {args.input}: {exc}", file=sys.stderr)
        return 1

    try:
        crc = inject_crc(image)
    except Exception as exc:  # interlocks.InterlockError or SRecordError
        print(f"crc-inject: refused: {exc}", file=sys.stderr)
        return 1

    output = args.output or args.input
    if args.dry_run:
        print(f"crc-inject: computed CRC-16 = 0x{crc:04X} (dry-run, not written)")
        return 0

    image.save(output)
    print(f"crc-inject: wrote CRC-16 = 0x{crc:04X} to {output} at 0x{mm.APP_HEADER_CRC_ADDR:X}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crc-inject",
        description=(
            "Compute the CRC-16 (algorithm confirmed from "
            "client-essensys-legacy/Ethernet/Download.c) over the app zone "
            "0x3002-0x7DFFF of an .s19 image and patch it at 0x3000."
        ),
    )
    parser.add_argument("input", type=Path, help="input .s19 (essensys-gcc output)")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="output .s19 (default: patch input in place)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="compute and print the CRC without writing any file",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
