"""In-memory fake flash — the only transport allowed to "work" in this repo.

No GPIO, no USB, no hardware access anywhere. This is what the CLI's
`--transport mock` (also the default) and every test in `tests/` use. It
lets the interlocks, CRC injection, and CLI plumbing be exercised
end-to-end without a Raspberry Pi, a pod, or a target board — exactly the
"dry-run/mock" testability required by the POC brief.
"""

from __future__ import annotations

from . import base
from .. import memory_map as mm


class MockTransport(base.BdmTransport):
    """Simulates a 512 KiB flash device, in RAM, for one BDM session."""

    def __init__(self, initial_image: bytes | None = None) -> None:
        if initial_image is None:
            self._flash = bytearray([0xFF]) * mm.FLASH_SIZE
        else:
            if len(initial_image) != mm.FLASH_SIZE:
                raise ValueError(
                    f"initial_image must be {mm.FLASH_SIZE} bytes, "
                    f"got {len(initial_image)}"
                )
            self._flash = bytearray(initial_image)
        self._connected = False
        self._halted = False
        self.call_log: list[tuple[str, int, int]] = []

    def connect(self) -> None:
        self._connected = True

    def halt(self) -> None:
        self._require_connected()
        self._halted = True

    def read_memory(self, address: int, length: int) -> bytes:
        self._require_connected()
        self.call_log.append(("read", address, length))
        return bytes(self._flash[address : address + length])

    def erase_range(self, address: int, length: int) -> None:
        self._require_connected()
        self._require_halted()
        self.call_log.append(("erase", address, length))
        self._flash[address : address + length] = bytes([0xFF]) * length

    def write_memory(self, address: int, data: bytes) -> None:
        self._require_connected()
        self._require_halted()
        self.call_log.append(("write", address, len(data)))
        self._flash[address : address + len(data)] = data

    def resume(self) -> None:
        self._require_connected()
        self._halted = False

    def reset(self) -> None:
        self._require_connected()
        self._halted = False

    def read_identity(self) -> base.TargetIdentity:
        self._require_connected()
        return base.TargetIdentity(csr=0x0000_0000, is_halted=self._halted)

    def disconnect(self) -> None:
        self._connected = False
        self._halted = False

    def _require_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("MockTransport: not connected — call connect() first")

    def _require_halted(self) -> None:
        if not self._halted:
            raise RuntimeError("MockTransport: target not halted — call halt() first")
