"""BDM transport implementations, selected by name in the CLI (`--transport`).

Only `mock` is functional in this repository. `usbdm` and `gpio` are
documented stubs — see their module docstrings for the sourced [A LEVER]
items blocking a real implementation.
"""

from __future__ import annotations

from .base import BdmTransport, TargetIdentity
from .gpio_bitbang_transport import GpioBitbangTransport
from .mock_transport import MockTransport
from .usbdm_transport import UsbdmTransport

TRANSPORTS: dict[str, type[BdmTransport]] = {
    "mock": MockTransport,
    "usbdm": UsbdmTransport,
    "gpio": GpioBitbangTransport,
}

__all__ = [
    "BdmTransport",
    "TargetIdentity",
    "MockTransport",
    "UsbdmTransport",
    "GpioBitbangTransport",
    "TRANSPORTS",
]
