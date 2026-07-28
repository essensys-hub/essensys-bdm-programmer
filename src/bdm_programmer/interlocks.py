"""Anti-brick interlocks — the non-negotiable SHALL requirements.

Every function here is a pure precondition check: it raises
``InterlockError`` and sends **zero** bytes over BDM if violated. Callers
(``programmer.py``) MUST call these before touching a ``BdmTransport``.
Traceable to ``specs/bdm-programmer/spec.md``:

- "Backup complet et vérifié avant toute écriture"
- "Erase et program limités à la zone application"
- "Interdiction d'écriture dans le champ de sécurité flash CFM"
- "Refus de programmer une image sans CRC-16 injecté"
"""

from __future__ import annotations

from . import memory_map as mm
from .backup import BackupRecord
from .crc16 import unpack_be
from .srec import SRecFile


class InterlockError(RuntimeError):
    """Raised when an operation would violate an anti-brick interlock."""


def require_verified_backup(record: BackupRecord | None) -> None:
    """SHALL refuse erase-app/program if no verified backup exists."""
    if record is None:
        raise InterlockError(
            "no backup on record for this target — run `backup` first "
            "(interlock: backup-before-write)"
        )
    if not record.verified:
        raise InterlockError(
            f"backup {record.bin_path} exists but is NOT verified "
            "(sha256 mismatch between BDM read and on-disk reread) — "
            "refusing to authorize any write"
        )


def require_within_app_zone(start: int, end: int) -> None:
    """SHALL refuse any erase/program range outside 0x3000-0x7DFFF."""
    if not mm.within(start, end, mm.APP_START, mm.APP_END):
        raise InterlockError(
            f"range 0x{start:X}-0x{end:X} is outside the application zone "
            f"0x{mm.APP_START:X}-0x{mm.APP_END:X} "
            "(bootloader and persistence must never be touched by this MVP)"
        )


def require_no_cfm_overlap(start: int, end: int) -> None:
    """SHALL unconditionally block any write touching 0x400-0x417 (CFM)."""
    if mm.overlaps(start, end, mm.CFM_START, mm.CFM_END):
        raise InterlockError(
            f"range 0x{start:X}-0x{end:X} overlaps the CFM Configuration "
            f"Field 0x{mm.CFM_START:X}-0x{mm.CFM_END:X} (Security Word "
            "CFMSEC at 0x414-0x417 disables BDM if misprogrammed, RM "
            "MCF52259 sect. 18.4.3) — refusing unconditionally"
        )


def require_image_excludes_cfm(image: SRecFile) -> None:
    """SHALL reject at load time an .s19 whose S-records cover the CFM."""
    if image.covers_range(mm.CFM_START, mm.CFM_END):
        raise InterlockError(
            f"input image contains S-records overlapping CFM range "
            f"0x{mm.CFM_START:X}-0x{mm.CFM_END:X} — refusing to load"
        )


def require_crc_injected(image: SRecFile) -> None:
    """SHALL refuse `program` if the CRC placeholder is still present."""
    crc_bytes = image.read_range(
        mm.APP_HEADER_CRC_ADDR, mm.APP_HEADER_CRC_ADDR + 1
    )
    stored = unpack_be(crc_bytes)
    if stored == mm.CRC_PLACEHOLDER:
        raise InterlockError(
            f"image carries the CRC placeholder 0x{mm.CRC_PLACEHOLDER:04X} "
            "at 0x3000 — run `crc-inject` before `program`"
        )
