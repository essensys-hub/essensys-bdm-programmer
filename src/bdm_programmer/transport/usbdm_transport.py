"""Piste 1 — USBDM pod transport. STUB ONLY. No hardware access.

Status per OpenSpec design.md (b) and R1 research notes section 3:
"PARTIELLEMENT LEVÉ" — USBDM confirms ColdFire V1-V4 support (covers the
MCF52259/V2 target) and a CLI programmer distinct from the Eclipse plugin
exists in the distribution, BUT no USBDM distribution or documentation
mentions ARM64/aarch64/Raspberry Pi anywhere (official binaries are
i386/amd64 Debian packages only), and the build dependencies (wxWidgets,
TCL, Xerces-C) suggest the primary executable is GUI, not headless CLI.

This is a **risk, not a conclusion** — tasks.md section 2 requires a
dedicated POC (`git clone` + build `usbdm-eclipse-makefiles-build` on
Raspberry Pi OS 64-bit, no target attached) before this class can be
implemented for real. Until that POC lands, every method here raises
NotImplementedError. Do not stub in a fake "success" path — a silently
successful transport that isn't real would defeat the anti-brick posture
of this whole project.
"""

from __future__ import annotations

from . import base

_NOT_VALIDATED = (
    "USBDM ARM64/RPi feasibility is UNVALIDATED (R1 research notes sect. 3; "
    "OpenSpec tasks.md sect. 2, item 2.1 [A LEVER, bloquant POC]). "
    "Implement this method only after: (1) building "
    "usbdm-eclipse-makefiles-build on Raspberry Pi OS 64-bit and confirming "
    "a non-GUI programming executable exists and runs, or (2) an equivalent "
    "documented CLI path. Do not fabricate a working transport."
)


class UsbdmTransport(base.BdmTransport):
    """Wraps the USBDM CLI utilities over a USB pod cabled to J33.

    TODO (sourced, not guessed — see design.md (a) and R1 sect. 1):
    - Pod cables to J33 pins 2 (BKPT), 3 (DSO), 4 (DSI), 6 (DSCLK), 8
      (RESET), 9-10 (GND), sense pin 7 (+3V3S). Pin 1 (TCLK) role in pure
      BDM mode is [A LEVER] (design.md (a), tasks.md 1.4).
    - Precondition: jumper JC1 must be fitted (BDM mode) before cabling —
      its physical PCB location is [A LEVER] (tasks.md 1.2), do not cable
      until confirmed.
    - READ/WRITE opcodes (0x1900/0x1940/0x1980 and 0x1800/0x1840/0x1880,
      RM MCF52259 Table 33-20) are the pod's problem once the CLI exists;
      this class should shell out to the USBDM CLI, not reimplement BDM
      framing (that would only be needed for GpioBitbangTransport).
    """

    def __init__(self, device: str | None = None) -> None:
        self._device = device

    def connect(self) -> None:
        raise NotImplementedError(_NOT_VALIDATED)

    def halt(self) -> None:
        raise NotImplementedError(_NOT_VALIDATED)

    def read_memory(self, address: int, length: int) -> bytes:
        raise NotImplementedError(_NOT_VALIDATED)

    def erase_range(self, address: int, length: int) -> None:
        raise NotImplementedError(_NOT_VALIDATED)

    def write_memory(self, address: int, data: bytes) -> None:
        raise NotImplementedError(_NOT_VALIDATED)

    def resume(self) -> None:
        raise NotImplementedError(_NOT_VALIDATED)

    def reset(self) -> None:
        raise NotImplementedError(_NOT_VALIDATED)

    def read_identity(self) -> base.TargetIdentity:
        raise NotImplementedError(_NOT_VALIDATED)

    def disconnect(self) -> None:
        raise NotImplementedError(_NOT_VALIDATED)
