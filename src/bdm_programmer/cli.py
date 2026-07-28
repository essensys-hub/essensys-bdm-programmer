"""`bdm-programmer` CLI — non-interactive, scriptable, CI-friendly.

Subcommands: info, backup, erase-app, program, verify, reset. Defaults to
`--transport mock` everywhere: this repository ships no code path that
touches real hardware (see transport/usbdm_transport.py and
transport/gpio_bitbang_transport.py — both raise NotImplementedError).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import interlocks
from .backup import BackupStore, load_backup_record
from .programmer import BdmProgrammer, ProgrammingError
from .transport import TRANSPORTS

# One process-lifetime backup store. A real CI job persists/reloads the
# backup .json sidecar across job boundaries instead (see .github/workflows).
_STORE = BackupStore()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1

    transport = TRANSPORTS[args.transport]()
    programmer = BdmProgrammer(transport, _STORE, serial=args.serial)

    if args.backup_record is not None:
        # Carries a verified backup across process/job boundaries — see
        # backup.py `load_backup_record` docstring. Re-verifies on load;
        # does not just trust the sidecar's stored `verified` flag.
        _STORE.register(load_backup_record(args.backup_record))

    try:
        return _dispatch(args, programmer)
    except (interlocks.InterlockError, ProgrammingError) as exc:
        print(f"bdm-programmer: refused: {exc}", file=sys.stderr)
        return 2
    except NotImplementedError as exc:
        print(f"bdm-programmer: transport not implemented: {exc}", file=sys.stderr)
        return 3


def _dispatch(args: argparse.Namespace, programmer: BdmProgrammer) -> int:
    if args.command == "info":
        info = programmer.dump_info()
        print(f"version=0x{info.version:04X} crc_stored=0x{info.crc_stored:04X}")
    elif args.command == "backup":
        record = programmer.backup(args.out_dir)
        print(f"backup: verified={record.verified} sha256={record.sha256_read}")
        print(f"backup: bin={record.bin_path}")
        print(f"backup: record={record.meta_path}")
        if not record.verified:
            return 2
    elif args.command == "erase-app":
        programmer.erase_app()
        print("erase-app: OK (0x3000-0x7DFFF)")
    elif args.command == "program":
        programmer.program(args.s19)
        print(f"program: OK ({args.s19})")
    elif args.command == "verify":
        result = programmer.verify(args.s19)
        if result.ok:
            print("verify: PASS")
        else:
            print(f"verify: FAIL at 0x{result.mismatch_address:X}")
            return 2
    elif args.command == "reset":
        info = programmer.reset()
        print(f"reset: OK version=0x{info.version:04X} crc_stored=0x{info.crc_stored:04X}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bdm-programmer")
    parser.add_argument(
        "--transport", choices=sorted(TRANSPORTS), default="mock",
        help="BDM transport (default: mock — no hardware access exists yet)",
    )
    parser.add_argument(
        "--serial", default="test-board",
        help="target serial/identifier, scopes the backup-before-write interlock",
    )
    parser.add_argument(
        "--backup-record", type=Path, default=None,
        help=(
            "path to a backup-<serial>-<ts>.json produced by a prior "
            "`backup` invocation (possibly in another process/CI job) — "
            "required by erase-app/program when the backup did not happen "
            "in the same process"
        ),
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("info", help="read-only: version + CRC, never writes")

    backup_p = sub.add_parser("backup", help="full 512 KiB read + verified save")
    backup_p.add_argument("--out-dir", type=Path, default=Path("./backups"))

    sub.add_parser("erase-app", help="erase 0x3000-0x7DFFF only")

    program_p = sub.add_parser("program", help="write a CRC-injected .s19")
    program_p.add_argument("s19", type=Path)

    verify_p = sub.add_parser("verify", help="readback compare vs an .s19")
    verify_p.add_argument("s19", type=Path)

    sub.add_parser("reset", help="resume/reset and confirm bootloader CRC check")

    return parser


if __name__ == "__main__":
    raise SystemExit(main())
