"""CRC-16 matching the SC944D bootloader's ``us_CalculerCRCZoneNew``.

CONFIRMED (not guessed) — read directly from the legacy firmware source,
read-only:

- ``client-essensys-legacy/Ethernet/Download.c`` lines 18-36 (helper
  ``us_CalculerCRCSurUnOctet``), lines 436-448 (``us_CalculerCRCZoneApp``),
  lines 469-487 (``us_CalculerCRCZoneNew``).
- ``client-essensys-legacy/Ethernet/Download.h`` lines 6-16 (the
  ``ul_FLASH_*`` offsets that bound the CRC computation).
- Cross-checked against ``essensys-gcc/bp/bootloader.c`` (essensys-gcc#14,
  commit ``36de4cc``), whose comment independently states: "CRC-16 over
  0x3002-0x7DFFF" — identical range, same algorithm family.

Algorithm, transcribed bit-for-bit from the C source:

    crc = 0xFFFF
    for each byte b in the zone (address order, low to high):
        crc ^= b
        repeat 8 times:
            if crc & 1: crc = (crc >> 1) ^ 0xA001
            else:       crc = crc >> 1

This is the standard **CRC-16/MODBUS** parametrisation (poly 0x8005 normal /
0xA001 reflected, init 0xFFFF, refin=refout=True, xorout=0x0000) — verified
against the public reference check value for "123456789" -> 0x4B37 in
``tests/test_crc16.py``. The 16-bit result is stored **big-endian** (MSB at
the lower address) at ``0x3000-0x3001`` — see ``vd_CalculInfosZoneNew``
(Download.c lines 489-508): ``Data1`` (high byte) is read from offset 0,
``Data2`` (low byte) from offset 1.

No further parametrisation is required: this is not an [A LEVER] item.
"""

from __future__ import annotations

_POLY_REFLECTED = 0xA001
_INIT = 0xFFFF


def crc16_update_byte(crc: int, byte: int) -> int:
    """Advance the running CRC by one byte. Mirrors us_CalculerCRCSurUnOctet."""
    crc ^= byte & 0xFF
    for _ in range(8):
        if crc & 1:
            crc = (crc >> 1) ^ _POLY_REFLECTED
        else:
            crc = crc >> 1
    return crc & 0xFFFF


def crc16_modbus(data: bytes, init: int = _INIT) -> int:
    """CRC-16/MODBUS over ``data``, matching us_CalculerCRCZoneApp/New."""
    crc = init
    for byte in data:
        crc = crc16_update_byte(crc, byte)
    return crc


def pack_be(value: int) -> bytes:
    """Pack a 16-bit CRC as big-endian bytes, as stored at 0x3000-0x3001."""
    return bytes([(value >> 8) & 0xFF, value & 0xFF])


def unpack_be(data: bytes) -> int:
    """Unpack a big-endian 16-bit value (inverse of pack_be)."""
    if len(data) != 2:
        raise ValueError(f"expected 2 bytes, got {len(data)}")
    return (data[0] << 8) | data[1]
