"""BDM programmer POC for the essensys-board-SC944D (MCF52259, ColdFire V2).

See README.md for hardware setup, and docs/openspec change
essensys-rpi4-bdm-programmer-2026-07-037 for the full spec this implements.
No code path in this package touches real hardware — see
transport/usbdm_transport.py and transport/gpio_bitbang_transport.py.
"""

__version__ = "0.1.0"
