"""Piste 2 (DIY, Phase 2) — direct GPIO bit-bang of the BDM serial protocol.

STUB ONLY. No hardware access, no GPIO library imported. Documented as the
fallback if Piste 1 (USBDM) fails its POC validation (tasks.md sect. 2.3).

The protocol itself IS fully sourced (R1 research notes section 2, from the
MCF52259 Reference Manual Rev. 4 chapter 33 "Debug Module") so a future
implementation has everything it needs without further silicon research:

- Full-duplex synchronous, host (this Pi) is master and drives DSCLK.
- Packet = 17 bits (1 status/control bit + 16 data bits), MSB first.
- Max frequency PSTCLK/5; DC is a valid lower bound, so raw speed is not the
  constraint — jitter-free, exact-timing sampling is (RM Fig. 33-12: 5
  PSTCLK cycles per bit, C0=DSI asserted, C1/C2=double-sync DSI while DSCLK
  high, C3=state machine advances, C4=DSO changes; DSCLK must be sampled low
  between bit exchanges).
- "Not ready" response (S=1, data=0x0000): next transfer only after 32
  processor cycles — on the order of 100ns at 80MHz, i.e. a hard real-time
  budget a non-RT Linux kernel is not guaranteed to meet (E7 in the framing
  prompt; R1 flags this as the deciding risk factor for Piste 1 vs Piste 2).
- READ/WRITE/GO opcodes: identical table to usbdm_transport.py's docstring
  (RM Table 33-20).

[A LEVER] before any real implementation:
- Physical location of jumper JC1 on the assembled PCB (tasks.md 1.2) —
  without it in BDM position, J33's shared pins carry JTAG signals, not
  BDM, and this transport would bit-bang the wrong protocol entirely.
- Role of TCLK (J33 pin 1) in pure BDM mode (tasks.md 1.4).
- Whether a deterministic co-processor (RP2040/PIO) is required to meet the
  32-cycle not-ready window, or whether pigpio/DMA on the Pi4 itself
  suffices — not evaluated, no GPIO timing measurement has been taken.
"""

from __future__ import annotations

from . import base

_NOT_IMPLEMENTED = (
    "GPIO bit-bang BDM is Phase 2 / DIY fallback, documented only. "
    "Implementing it requires resolving jumper JC1's physical position "
    "(tasks.md 1.2, [A LEVER]) and a timing strategy for the 32-processor "
    "-cycle not-ready window on non-RT Linux (E7) — neither has been done. "
    "No GPIO library is imported by this module; do not fabricate a "
    "working bit-bang path without real timing validation on hardware."
)


class GpioBitbangTransport(base.BdmTransport):
    """Direct Raspberry Pi GPIO drive of DSCLK/DSI/DSO/BKPT/RESET.

    Deliberately has no dependency on RPi.GPIO/pigpio/lgpio: importing one
    here would suggest this path has been exercised on real GPIO, which it
    has not. Wire the dependency in only once the timing strategy above is
    resolved and tested against a scope/logic analyzer on real silicon.
    """

    def __init__(self, chip: str | None = None) -> None:
        self._chip = chip

    def connect(self) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def halt(self) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def read_memory(self, address: int, length: int) -> bytes:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def erase_range(self, address: int, length: int) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def write_memory(self, address: int, data: bytes) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def resume(self) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def reset(self) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def read_identity(self) -> base.TargetIdentity:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def disconnect(self) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED)
