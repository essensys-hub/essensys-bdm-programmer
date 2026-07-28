# essensys-bdm-programmer

POC/skeleton for a Raspberry Pi 4 BDM programmer targeting the
`essensys-board-SC944D` (Freescale **MCF52259CAG80**, ColdFire V2, 80 MHz,
512 KiB internal flash). Implements the CLI, interlocks, and GitHub Actions
pipeline described in OpenSpec change
`essensys-rpi4-bdm-programmer-2026-07-037` (see
`essensys-memory/openspec/changes/essensys-rpi4-bdm-programmer-2026-07-037/`).

**No code path in this repository touches real hardware.** Every BDM
transport that would talk to a pod or GPIO is a documented stub raising
`NotImplementedError`. The only functional transport is an in-memory mock,
used for the CLI, tests, and CI. See "Status" below before wiring anything.

---

## Safety first — read this before connecting anything

1. **Never flash without a verified backup.** The CLI refuses `erase-app`
   and `program` unless a full 512 KiB backup has been read via BDM,
   written to disk, re-read from disk, and its sha256 confirmed identical
   both times. This is enforced in code (`interlocks.py`), not just by
   procedure.
2. **Never write `0x400-0x417` (CFM Configuration Field).** The Security
   Word (`CFMSEC`, `0x414-0x417`) **disables BDM communications** if
   misprogrammed (MCF52259 Reference Manual, section 18.4.3 — direct
   quote: *"Enabling flash security disables BDM communications."*).
   Recovery from that state requires a backdoor key sequence, which is
   complex, risky, and explicitly out of scope for this MVP. The interlock
   blocks this range unconditionally, with no override flag.
3. **Never erase/program outside `0x3000-0x7DFFF`.** The bootloader
   (`0x0-0x2FFF`) and the domotic persistence table `Tb_Echange[]`
   (`0x7E000-0x7EFFF`) must never be touched by this MVP. A mass-erase
   would brick the bootloader with no recovery path unless you already
   have a verified bootloader backup and a separate, hardened recovery
   procedure — neither exists yet (Phase 2, out of scope).
4. **This backup does not cover everything.** It covers only the MCF52259
   internal flash (512 KiB). It does **not** cover the external SPI OTA
   flash (`SST25VF016B`) or the SPI EEPROM (`25AA02E48T`, which holds the
   MAC address, server key, and alarm code). Do not conclude a full board
   backup has been made.
5. **Jumper JC1 must be in BDM position before you cable anything to J33.**
   See "Jumper JC1" below — its physical location on the assembled PCB is
   still **[A LEVER]**. Do not guess; confirm on the assembly drawing or by
   visual inspection of a real board first.
6. **Power stability.** A power cut mid-`program` can corrupt the app zone
   mid-write. Use a dedicated regulated supply for the test board and
   re-run `verify` after any suspected power event before trusting the
   result.

---

## Hardware — connector J33 pinout

Source: OpenSpec design.md (a) and R1 research notes, obtained by direct
reading of the Altium schematic PDF (`essensys-board-SC944D/Schematic
PDF_[No Variations].pdf`, page 5, sheet "Coeur") — not guessed.

J33 is a 2×5, 2.54 mm pin header labeled "JTAG/BDM debug" (connector ref.
`e2.54-D-L6`).

| Pin | Altium net | Signal (BDM mode) | Notes |
|-----|-----------|--------------------|-------|
| 1 | `UC_TCLK` | TCLK | Not required by the 3-wire BDM protocol (DSCLK/DSI/DSO). Exact role in pure BDM mode is **[A LEVER]** — legacy JTAG/pod wiring vs. actual use by the historical P&E pod. Confirm via P&E docs or passive (read-only) measurement. |
| 2 | `UC_TMS/BKPT` | **BKPT** | Shared TMS(JTAG)/BKPT(BDM), selected by `JTAG_EN` |
| 3 | `UC_TDO/DSO` | **DSO** | Shared TDO(JTAG)/DSO(BDM) |
| 4 | `UC_TDI/DSI` | **DSI** | Shared TDI(JTAG)/DSI(BDM) |
| 5 | `UC_ALLPST` | ALLPST | AND of PST[3:0]; asserted when the core is halted (RM sect. 33.2) |
| 6 | `UC_TRST/DSCLK` | **DSCLK** | Shared TRST(JTAG)/DSCLK(BDM) — host-driven clock, host is master |
| 7 | `+3V3S` | VDD target (3.3V, sense) | Level reference / target-present detection — **not** power supplied by the pod |
| 8 | `UC_RESET` | RESET | MCU reset |
| 9-10 | GND | GND | Common ground, mandatory Pi4 <-> target |

### Jumper JC1 (BDM/JTAG selector)

On the same schematic sheet, a note reads: *"Si 0 (JC1 monté) -> BDM mode"
/ "Si 1 (JC1 non monté) -> JTAG mode"*. This jumper drives the MCF52259's
`JTAG_EN` pin, which selects whether J33's shared pins behave as
JTAG (TMS/TDI/TDO/TRST) or BDM (BKPT/DSI/DSO/DSCLK).

**[A LEVER — blocking before any cabling]**: JC1's physical location on the
assembled PCB. Not determinable from the schematic alone — check
`Assembly Drawings_[No Variations].pdf` or inspect a real assembled board.
Do not cable the pod until this is confirmed (tasks.md 1.2/1.3).

### Electrical

- MCF52259 I/O and Pi4 GPIO are both 3.3 V — compatible for a direct
  bit-bang path (Piste 2), but use buffers/protection and check `+3V3S`
  (pin 7) before any activity, to avoid damaging the Pi if the target is
  absent or misconfigured.
- Common ground (pins 9-10) is mandatory.
- Never apply 5 V to the GPIO.

---

## Software architecture

```
src/bdm_programmer/
  memory_map.py          flash layout constants (single source of truth)
  crc16.py                CRC-16 matching the bootloader (see below)
  srec.py                 minimal .s19 (Motorola S-record) reader/writer
  interlocks.py            anti-brick precondition checks (pure functions)
  backup.py                recovery-grade backup: read, hash, write, reread-verify
  programmer.py           orchestration: dump-info/backup/erase-app/program/verify/reset
  report.py                PASS/FAIL report builder
  cli.py                   `bdm-programmer` entry point
  crc_inject.py            `crc-inject` entry point
  transport/
    base.py                 BdmTransport abstract interface
    mock_transport.py       in-memory fake flash — the only functional transport
    usbdm_transport.py      Piste 1 stub (pod BDM/USBDM) — NotImplementedError
    gpio_bitbang_transport.py  Piste 2 stub (direct GPIO) — NotImplementedError
```

`programmer.py` is the only module allowed to call both `interlocks.py` and
a `BdmTransport` — every write path is guarded there, so an anti-brick
review only needs to audit that one file plus `interlocks.py` itself.

### CLI usage (mock transport, safe to run anywhere)

```bash
pip install -e '.[dev]'

crc-inject app.s19 -o app-crc.s19

bdm-programmer --serial board-001 info
bdm-programmer --serial board-001 backup --out-dir ./backups
# -> prints "backup: record=./backups/backup-board-001-<ts>.json"

# erase-app/program are refused without a verified backup for this serial.
# Each CLI invocation is its own process, so the backup-verified state does
# NOT carry over automatically across separate commands — pass the sidecar
# --backup-record explicitly (this is exactly what the flash.yml CI job
# does between its `backup` and `erase-app`/`program` steps):
bdm-programmer --serial board-001 \
  --backup-record ./backups/backup-board-001-<ts>.json erase-app
bdm-programmer --serial board-001 \
  --backup-record ./backups/backup-board-001-<ts>.json program app-crc.s19

bdm-programmer --serial board-001 verify app-crc.s19
bdm-programmer --serial board-001 reset
```

`--transport` defaults to `mock`. Passing `--transport usbdm` or
`--transport gpio` connects to the real stub classes, which immediately
raise `NotImplementedError` with a message pointing at the exact
`tasks.md` item blocking a real implementation — this is intentional, not
a bug.

---

## CRC-16 algorithm — confirmed, not guessed

The task brief for this POC required either confirming the bootloader's
exact CRC-16 algorithm from `client-essensys-legacy/Ethernet/Download.c`
(read-only) or, failing that, marking it `[A LEVER]`. It **was** confirmed:

- `Download.c` lines 18-36 (`us_CalculerCRCSurUnOctet`) and lines 436-487
  (`us_CalculerCRCZoneApp` / `us_CalculerCRCZoneNew`) implement
  **CRC-16/MODBUS**: init `0xFFFF`, polynomial `0x8005` (reflected
  `0xA001`), LSB-first, no final XOR.
- `Download.h` lines 6-16 give the exact byte ranges: the CRC is computed
  over `0x3002-0x7DFFF` (the app zone, **excluding** the 2-byte CRC field
  itself but **including** the 2-byte version field), and stored
  **big-endian** at `0x3000-0x3001`.
- Independently cross-checked against `essensys-gcc/bp/bootloader.c`
  (essensys-gcc#14, commit `36de4cc`), whose comment states verbatim:
  *"The bootloader computes CRC-16 over 0x3002–0x7DFFF and compares it
  against the halfword at 0x3000"* — same range, same conclusion, from an
  independent source.

See `src/bdm_programmer/crc16.py` for the full derivation and
`tests/test_crc16.py` for the CRC-16/MODBUS reference vector
(`"123456789"` -> `0x4B37`) plus a from-scratch table-driven cross-check.

`essensys-gcc#14` tracks the upstream need for this tool; per OpenSpec
decision D4, this repo's `crc-inject` exists to fill that gap now and
should be reconciled with (not duplicated alongside) whatever
`essensys-gcc` ships once #14 lands.

---

## Status — what is real vs. stubbed

| Piece | Status |
|---|---|
| CLI, interlocks, S-record parsing, CRC-16 | Implemented, tested, no hardware dependency |
| `MockTransport` | Fully functional in-memory fake, used by CLI default + all tests |
| `UsbdmTransport` (Piste 1, pod) | **Stub.** USBDM ARM64/RPi feasibility is unvalidated — no official distribution or docs mention ARM64/aarch64 (i386/amd64 packages only), and build deps (wxWidgets, TCL, Xerces-C) suggest a GUI-first executable. **[A LEVER — bloquant POC]**: build `usbdm-eclipse-makefiles-build` on Raspberry Pi OS 64-bit (no target attached) and confirm a headless CLI programming executable exists. |
| `GpioBitbangTransport` (Piste 2, DIY) | **Stub**, documented fallback if Piste 1 fails. Protocol is fully sourced (MCF52259 RM chapter 33) but jitter/timing risk on non-RT Linux is unresolved, and JC1's physical position is unconfirmed. |
| GitHub Actions pipeline | Workflow YAML written (`build`, `crc-inject`, `flash`, `report`, `rollback`); `flash`/`rollback` require a real self-hosted Pi4 runner and a real transport to actually execute — not runnable end-to-end without hardware. |

## Open items ([A LEVER] / TODO), not guessed

- **JC1 physical position** on the assembled PCB — check
  `Assembly Drawings_[No Variations].pdf` or inspect a real board
  (tasks.md 1.2, blocking before any cabling).
- **TCLK (J33 pin 1) role** in pure BDM mode — P&E docs or passive
  measurement (tasks.md 1.4, non-blocking, minor).
- **USBDM CLI on ARM64/Raspberry Pi OS 64-bit** — build-and-run POC not yet
  performed; no hardware exists in this environment to perform it
  (tasks.md 2.1-2.4, blocking Piste 1 commitment).
- **CSR/IDCODE register detail** (RM sect. 33.3.2) for a richer
  anti-wrong-target identity check beyond version/CRC — not extracted by
  R1, non-blocking for MVP.
- **CFM SEC[1:0] exact codes** (RM Table 18-7) — not extracted, non-blocking
  since the MVP interlock blocks the whole `0x400-0x417` range regardless
  of the specific security state encoding.

## Non-goals (MVP)

- Interactive GDB debugging.
- Programming the external SPI OTA flash or EEPROM.
- Reflashing the bootloader (`0x0-0x2FFF`).
- Boundary-scan / production JTAG testing.
- CFM backdoor unlock procedure.
- A working Piste 2 (GPIO bit-bang) implementation.
