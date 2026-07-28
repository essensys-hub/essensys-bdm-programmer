"""Recovery-grade backup: read, hash, write, reread, re-hash, compare.

A backup is only "verified" once the sha256 computed *during the BDM read*
matches the sha256 recomputed *from the file written to disk* — this is the
"relu et vérifié" requirement in specs/bdm-programmer/spec.md, distinct from
merely writing a file and trusting it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import memory_map as mm
from .transport.base import BdmTransport


@dataclass(frozen=True)
class BackupRecord:
    serial: str
    timestamp: str
    bin_path: Path
    s19_path: Path
    meta_path: Path
    sha256_read: str
    sha256_disk: str | None
    verified: bool
    version: int
    crc_stored: int


def _to_srec(data: bytes, base_addr: int) -> str:
    """Serialize `data` as S3 records (32-bit addr), 32 bytes/line, like
    essensys-gcc's `--srec-forceS3 --srec-len=32`."""
    lines = ["S0030000FC"]
    chunk = 32
    for offset in range(0, len(data), chunk):
        block = data[offset : offset + chunk]
        addr = base_addr + offset
        count = 4 + len(block) + 1
        addr_hex = f"{addr:08X}"
        data_hex = block.hex().upper()
        total = count + sum(addr.to_bytes(4, "big")) + sum(block)
        checksum = (~total) & 0xFF
        lines.append(f"S3{count:02X}{addr_hex}{data_hex}{checksum:02X}")
    lines.append("S70500000000FA")
    return "\n".join(lines) + "\n"


def perform_backup(
    transport: BdmTransport, out_dir: Path, serial: str
) -> BackupRecord:
    """Read the full 512 KiB flash, hash it, persist it, and reread-verify.

    Order matters and is deliberate: hash is computed on bytes as they come
    off BDM, *before* any disk I/O, so a truncated/corrupted write is caught
    by the reread-compare step rather than silently accepted.
    """
    transport.connect()
    transport.halt()
    data = transport.read_memory(mm.BACKUP_START, mm.BACKUP_END - mm.BACKUP_START + 1)
    sha_read = hashlib.sha256(data).hexdigest()

    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bin_path = out_dir / f"backup-{serial}-{date_tag}.bin"
    s19_path = out_dir / f"backup-{serial}-{date_tag}.s19"
    meta_path = out_dir / f"backup-{serial}-{date_tag}.json"

    bin_path.write_bytes(data)
    s19_path.write_text(_to_srec(data, mm.BACKUP_START))

    sha_disk = hashlib.sha256(bin_path.read_bytes()).hexdigest()
    verified = sha_disk == sha_read

    crc_stored = int.from_bytes(
        data[mm.APP_HEADER_CRC_ADDR : mm.APP_HEADER_CRC_ADDR + 2], "big"
    )
    version = int.from_bytes(
        data[mm.APP_HEADER_VERSION_ADDR : mm.APP_HEADER_VERSION_ADDR + 2], "big"
    )

    record = BackupRecord(
        serial=serial,
        timestamp=date_tag,
        bin_path=bin_path,
        s19_path=s19_path,
        meta_path=meta_path,
        sha256_read=sha_read,
        sha256_disk=sha_disk,
        verified=verified,
        version=version,
        crc_stored=crc_stored,
    )
    meta_path.write_text(json.dumps(_record_to_dict(record), indent=2))
    return record


def load_backup_record(meta_path: Path) -> BackupRecord:
    """Reload a backup produced by a *different process* (e.g. a prior CI
    step/job) and re-verify it now, not just trust the stored `verified`
    flag.

    This is what lets `backup-before-write` hold across process/job
    boundaries: the CLI is invoked once per subcommand, so the in-memory
    BackupStore alone cannot carry state from `backup` to `erase-app`/
    `program` in a later invocation — this sidecar file is the durable
    handoff (see cli.py `--backup-record`).
    """
    meta_path = Path(meta_path)
    data = json.loads(meta_path.read_text())
    bin_path = Path(data["bin_path"])
    sha256_now = hashlib.sha256(bin_path.read_bytes()).hexdigest()
    verified = bool(data["verified"]) and sha256_now == data["sha256_read"]
    return BackupRecord(
        serial=data["serial"],
        timestamp=data["timestamp"],
        bin_path=bin_path,
        s19_path=Path(data["s19_path"]),
        meta_path=meta_path,
        sha256_read=data["sha256_read"],
        sha256_disk=sha256_now,
        verified=verified,
        version=int(data["version"], 16),
        crc_stored=int(data["crc_stored"], 16),
    )


def _record_to_dict(record: BackupRecord) -> dict:
    return {
        "serial": record.serial,
        "timestamp": record.timestamp,
        "bin_path": str(record.bin_path),
        "s19_path": str(record.s19_path),
        "sha256_read": record.sha256_read,
        "sha256_disk": record.sha256_disk,
        "verified": record.verified,
        "version": f"0x{record.version:04X}",
        "crc_stored": f"0x{record.crc_stored:04X}",
    }


class BackupStore:
    """In-process registry of the current verified backup per target serial.

    A real deployment persists this via the exported .json sidecar (read
    back by the `flash` CI job); this in-memory store is what the CLI/tests
    use within a single process run.
    """

    def __init__(self) -> None:
        self._records: dict[str, BackupRecord] = {}

    def register(self, record: BackupRecord) -> None:
        self._records[record.serial] = record

    def get(self, serial: str) -> BackupRecord | None:
        return self._records.get(serial)

    def invalidate(self, serial: str) -> None:
        self._records.pop(serial, None)
