"""Abstract BDM transport — the boundary between orchestration and silicon.

`programmer.py` and the interlocks never talk to hardware directly; they go
through this interface. That is what lets the whole CLI be exercised in
tests/CI with `MockTransport` while the two hardware-backed implementations
(`UsbdmTransport`, `GpioBitbangTransport`) remain stubs pending the POC
validation tasks in tasks.md sections 2 and 1.6 — no real hardware is
touched anywhere in this repository.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class TargetIdentity:
    """What `dump-info`/pre-write checks use to confirm "this is a
    MCF52259", read via RDMREG/CSR (RM MCF52259 sect. 33.3.2)."""

    csr: int
    is_halted: bool


class BdmTransport(ABC):
    """One BDM session to one target. Byte-addressed, absolute addresses.

    Implementations MUST NOT perform any address-range policy (that is the
    job of `interlocks.py`) — a transport blindly does what it is told, so
    that interlocks can be tested independently of hardware and so a single
    set of interlocks guards every transport uniformly.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish the BDM session (pod handshake or GPIO init)."""

    @abstractmethod
    def halt(self) -> None:
        """Assert BKPT within 8 cycles of RESET negation (RM sect. 33.4.1.1).

        This is the standard entry point: the CPU halts before the firmware
        starts, and all registers/memory become accessible from here.
        """

    @abstractmethod
    def read_memory(self, address: int, length: int) -> bytes:
        """READ command (opcode 0x1900/0x1940/0x1980, RM Table 33-20)."""

    @abstractmethod
    def erase_range(self, address: int, length: int) -> None:
        """Erase flash sectors covering [address, address+length)."""

    @abstractmethod
    def write_memory(self, address: int, data: bytes) -> None:
        """WRITE command (opcode 0x1800/0x1840/0x1880, RM Table 33-20)."""

    @abstractmethod
    def resume(self) -> None:
        """GO command (opcode 0x0C00) — resume execution after halt."""

    @abstractmethod
    def reset(self) -> None:
        """Negate RESET and let the target reboot through the bootloader."""

    @abstractmethod
    def read_identity(self) -> TargetIdentity:
        """Read CSR/status to confirm the target responds as a MCF52259."""

    @abstractmethod
    def disconnect(self) -> None:
        """Tear down the BDM session cleanly."""
