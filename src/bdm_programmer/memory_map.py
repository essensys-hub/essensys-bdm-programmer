"""Flash memory layout constants for the SC944D / MCF52259CAG80 target.

Source of truth (do not edit without re-checking these files, read-only):

- ``essensys-gcc/bp/intflash.ld`` and ``essensys-gcc/bp/bootloader.c``
  (commit ``36de4cc``, essensys-gcc#14) — application header layout.
- ``client-essensys-legacy/Ethernet/Download.h`` lines 6-16 — historical
  ``ul_FLASH_*`` constants, byte-identical to the modern layout.
- OpenSpec change ``essensys-rpi4-bdm-programmer-2026-07-037``,
  ``specs/bdm-programmer/spec.md`` — the SHALL requirements these constants
  enforce (erase/program confined to the app zone, CFM writes forbidden).

Total internal flash is 512 KiB (``0x00000``-``0x7FFFF``).
"""

from __future__ import annotations

FLASH_START: int = 0x00000
FLASH_SIZE: int = 0x80000  # 512 KiB
FLASH_END: int = FLASH_START + FLASH_SIZE - 1  # 0x7FFFF, inclusive

# Bootloader — never touched by this MVP (Non-Goal, proposal.md).
BOOTLOADER_START: int = 0x00000
BOOTLOADER_END: int = 0x02FFF  # inclusive

# Application header, at the fixed address the bootloader reads.
APP_HEADER_CRC_ADDR: int = 0x03000  # 2 bytes, big-endian, .APP_CRC
APP_HEADER_VERSION_ADDR: int = 0x03002  # 2 bytes, big-endian, .APP_VERSION
APP_HEADER_JUMP_ADDR: int = 0x03004  # 6 bytes, .APP_JUMP (jmp __boot)

# Application zone — the only range erase-app/program/verify may touch.
APP_START: int = 0x03000
APP_END: int = 0x7DFFF  # inclusive; persistence starts immediately after

# CRC-16 is computed over the app zone *excluding* the CRC field itself
# (us_CalculerCRCZoneApp/New start at ul_FLASH_APP_SOFT_START + CRC_SIZE),
# but *including* the version halfword. Confirmed by both:
#   - client-essensys-legacy/Ethernet/Download.c lines 436-448, 469-487
#   - essensys-gcc/bp/bootloader.c comment: "CRC-16 over 0x3002-0x7DFFF"
CRC_COMPUTE_START: int = 0x03002
CRC_COMPUTE_END: int = APP_END  # 0x7DFFF, inclusive

# Persistence — Tb_Echange[] domotic state, 4 KiB, NOLOAD. Never erased by
# erase-app/program (piege E4 du prompt de cadrage).
PERSISTENCE_START: int = 0x7E000
PERSISTENCE_END: int = 0x7EFFF  # inclusive

# FlashX spare sector.
FLASHX_SPARE_START: int = 0x7F000
FLASHX_SPARE_END: int = FLASH_END  # 0x7FFFF

# CFM Configuration Field — RM MCF52259 chapter 18.3.1, Table 18-1.
# R1 correction: the field is 24 bytes (0x400-0x417), NOT 0x400-0x40F as the
# initial framing prompt assumed. CFMSEC (Security Word) at 0x414-0x417
# disables BDM communications if misprogrammed (RM section 18.4.3) — this is
# the single most important interlock in this codebase.
CFM_START: int = 0x400
CFM_END: int = 0x417  # inclusive

# CRC placeholder emitted by essensys-gcc/bp/bootloader.c until crc-inject
# runs. Also the historical CodeWarrior placeholder value.
CRC_PLACEHOLDER: int = 0x0102

# Backup covers the entire internal flash only. It does NOT cover the
# external SPI OTA flash (SST25VF016B) or the SPI EEPROM (25AA02E48T: MAC,
# server key, alarm code) — see README "Hors périmètre".
BACKUP_START: int = FLASH_START
BACKUP_END: int = FLASH_END


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Inclusive-range overlap test used by every interlock check."""
    return a_start <= b_end and b_start <= a_end


def within(start: int, end: int, bound_start: int, bound_end: int) -> bool:
    """True if [start, end] is fully contained in [bound_start, bound_end]."""
    return bound_start <= start <= end <= bound_end
