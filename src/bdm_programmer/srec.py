"""Minimal Motorola S-record (.s19) reader/writer.

Supports the subset essensys-gcc emits (``--srec-forceS3 --srec-len=32``):
S0 (header), S3 (32-bit address data), S7 (32-bit start address). S1/S2 are
parsed too for robustness against other producers, but essensys-gcc only
emits S3 data records.

Deliberately stdlib-only (no external S-record library), per the
library-first / minimal-dependency posture of this POC — the format is
small enough that a bespoke parser is lower risk than a new dependency in a
tool that patches firmware images.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_ADDR_LEN_BYTES = {"S1": 2, "S2": 3, "S3": 4}
_DATA_RECORD_TYPES = frozenset(_ADDR_LEN_BYTES)


class SRecordError(ValueError):
    """Raised on malformed S-record input (bad checksum, bad hex, ...)."""


@dataclass
class _Line:
    rec_type: str
    address: int
    data: bytearray
    addr_len: int = 4

    def checksum(self) -> int:
        count = self.addr_len + len(self.data) + 1
        total = count
        addr = self.address
        for shift in range(8 * (self.addr_len - 1), -1, -8):
            total += (addr >> shift) & 0xFF
        total += sum(self.data)
        return (~total) & 0xFF

    def render(self) -> str:
        count = self.addr_len + len(self.data) + 1
        addr_hex = f"{self.address:0{self.addr_len * 2}X}"
        data_hex = self.data.hex().upper()
        return f"{self.rec_type}{count:02X}{addr_hex}{data_hex}{self.checksum():02X}"


@dataclass
class SRecFile:
    """A parsed .s19 file: passthrough non-data lines + patchable data lines."""

    lines: list[_Line] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "SRecFile":
        lines: list[_Line] = []
        text = Path(path).read_text()
        for raw in text.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            lines.append(_parse_line(raw))
        return cls(lines=lines)

    def save(self, path: Path) -> None:
        Path(path).write_text("\n".join(line.render() for line in self.lines) + "\n")

    def read_range(self, start: int, end: int, fill: int = 0xFF) -> bytes:
        """Assemble bytes for [start, end] inclusive; gaps filled with `fill`."""
        size = end - start + 1
        buf = bytearray([fill]) * size
        for line in self.lines:
            if line.rec_type not in _DATA_RECORD_TYPES:
                continue
            _copy_overlap(line, start, end, buf)
        return bytes(buf)

    def patch_word_be(self, address: int, value: int) -> None:
        """Overwrite the big-endian 16-bit value at `address` in place.

        Raises SRecordError if no single data record fully covers both bytes
        (essensys-gcc's app header record always does, per bp/bootloader.c).
        """
        hi, lo = (value >> 8) & 0xFF, value & 0xFF
        for line in self.lines:
            if line.rec_type not in _DATA_RECORD_TYPES:
                continue
            offset = address - line.address
            if 0 <= offset and offset + 1 < len(line.data):
                line.data[offset] = hi
                line.data[offset + 1] = lo
                return
        raise SRecordError(
            f"no single S-record covers address 0x{address:X}-0x{address + 1:X}"
        )

    def covers_range(self, start: int, end: int) -> bool:
        """True if any data record overlaps [start, end] inclusive."""
        for line in self.lines:
            if line.rec_type not in _DATA_RECORD_TYPES:
                continue
            rec_end = line.address + len(line.data) - 1
            if line.address <= end and start <= rec_end:
                return True
        return False


def _copy_overlap(line: _Line, start: int, end: int, buf: bytearray) -> None:
    rec_start = line.address
    rec_end = line.address + len(line.data) - 1
    lo = max(rec_start, start)
    hi = min(rec_end, end)
    if lo > hi:
        return
    buf[lo - start : hi - start + 1] = line.data[lo - rec_start : hi - rec_start + 1]


def _parse_line(raw: str) -> _Line:
    if len(raw) < 4 or raw[0] != "S":
        raise SRecordError(f"not an S-record line: {raw!r}")
    rec_type = raw[0:2]
    try:
        payload = bytes.fromhex(raw[2:])
    except ValueError as exc:
        raise SRecordError(f"invalid hex in line: {raw!r}") from exc
    count = payload[0]
    body = payload[1 : 1 + count]
    if len(body) != count:
        raise SRecordError(f"length mismatch in line: {raw!r}")
    checksum = body[-1]
    rest = body[:-1]
    # S0/S7/S8/S9 (header/start-address/count) are never patched: fold the
    # whole payload into `address` so render() reproduces the line byte-for
    # -byte without needing a type-specific address width table.
    addr_len = _ADDR_LEN_BYTES.get(rec_type, len(rest))
    address = int.from_bytes(rest[:addr_len], "big") if addr_len else 0
    data = bytearray(rest[addr_len:])
    line = _Line(rec_type=rec_type, address=address, data=data, addr_len=addr_len or 0)
    if rec_type in _DATA_RECORD_TYPES and line.checksum() != checksum:
        raise SRecordError(f"checksum mismatch in line: {raw!r}")
    return line
