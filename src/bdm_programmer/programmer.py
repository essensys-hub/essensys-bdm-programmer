"""High-level orchestration: the six CLI verbs, interlocks wired in front of
every write path. This module is the only place that is allowed to call
both `interlocks.py` and a `BdmTransport` — keep it that way so a code
reviewer only needs to audit one file to confirm every write is guarded.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import interlocks, memory_map as mm
from .backup import BackupRecord, BackupStore, perform_backup
from .crc16 import crc16_modbus, unpack_be
from .srec import SRecFile
from .transport.base import BdmTransport


class ProgrammingError(RuntimeError):
    """Raised when verify fails or the target does not respond as expected."""


@dataclass
class TargetInfo:
    version: int
    crc_stored: int


@dataclass
class VerifyResult:
    ok: bool
    mismatch_address: int | None = None


class BdmProgrammer:
    """One target session: dump-info, backup, erase-app, program, verify, reset."""

    def __init__(
        self, transport: BdmTransport, backup_store: BackupStore, serial: str
    ) -> None:
        self._transport = transport
        self._store = backup_store
        self._serial = serial

    def dump_info(self) -> TargetInfo:
        """Read-only: connect, halt, report version/CRC. Never writes."""
        self._transport.connect()
        self._transport.halt()
        header = self._transport.read_memory(mm.APP_HEADER_CRC_ADDR, 4)
        return TargetInfo(
            version=unpack_be(header[2:4]), crc_stored=unpack_be(header[0:2])
        )

    def backup(self, out_dir: Path) -> BackupRecord:
        """SHALL run before any write is authorized for this serial."""
        record = perform_backup(self._transport, out_dir, self._serial)
        self._store.register(record)
        return record

    def erase_app(self) -> None:
        interlocks.require_verified_backup(self._store.get(self._serial))
        interlocks.require_within_app_zone(mm.APP_START, mm.APP_END)
        interlocks.require_no_cfm_overlap(mm.APP_START, mm.APP_END)
        self._transport.connect()
        self._transport.halt()
        self._transport.erase_range(mm.APP_START, mm.APP_END - mm.APP_START + 1)

    def program(self, s19_path: Path) -> None:
        interlocks.require_verified_backup(self._store.get(self._serial))
        image = SRecFile.load(s19_path)
        interlocks.require_image_excludes_cfm(image)
        interlocks.require_crc_injected(image)
        payload = image.read_range(mm.APP_START, mm.APP_END)
        interlocks.require_within_app_zone(mm.APP_START, mm.APP_END)
        interlocks.require_no_cfm_overlap(mm.APP_START, mm.APP_END)
        self._transport.connect()
        self._transport.halt()
        self._transport.write_memory(mm.APP_START, payload)

    def verify(self, s19_path: Path) -> VerifyResult:
        """SHALL relu-compare octet-a-octet; never claims success on mismatch."""
        image = SRecFile.load(s19_path)
        expected = image.read_range(mm.APP_START, mm.APP_END)
        self._transport.connect()
        actual = self._transport.read_memory(mm.APP_START, len(expected))
        for offset, (exp, act) in enumerate(zip(expected, actual)):
            if exp != act:
                return VerifyResult(ok=False, mismatch_address=mm.APP_START + offset)
        return VerifyResult(ok=True)

    def reset(self) -> TargetInfo:
        """GO / negate RESET, then confirm the bootloader's own CRC check."""
        self._transport.connect()
        self._transport.resume()
        self._transport.reset()
        return self.dump_info()


def inject_crc(image: SRecFile) -> int:
    """Compute and patch the CRC-16 at 0x3000. Returns the computed value.

    Algorithm confirmed from client-essensys-legacy/Ethernet/Download.c —
    see crc16.py docstring. Range is 0x3002-0x7DFFF (excludes the CRC field
    itself, includes the version halfword), gaps filled with 0xFF to match
    the state of freshly erased-then-partially-programmed flash.
    """
    interlocks.require_image_excludes_cfm(image)
    zone = image.read_range(mm.CRC_COMPUTE_START, mm.CRC_COMPUTE_END, fill=0xFF)
    crc = crc16_modbus(zone)
    image.patch_word_be(mm.APP_HEADER_CRC_ADDR, crc)
    return crc
