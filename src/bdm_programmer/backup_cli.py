"""`bdm-backup` : sauvegarde en lecture seule de la flash du BP via Pico."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import memory_map as mm
from .backup import _to_srec
from .transport.pico_transport import PicoError, PicoReadOnlyTransport

DEFAULT_OUT = Path.home() / "essensys-backups"
FLASH_LEN = mm.BACKUP_END - mm.BACKUP_START + 1
CFM_LEN = mm.CFM_END - mm.CFM_START + 1
CFMSEC_OFFSET = 0x14


class BackupError(RuntimeError):
    pass


def check_out_dir(out_dir: Path) -> None:
    """Refuse un dossier situé dans un dépôt Git sans y être ignoré."""
    probe = out_dir.resolve()
    while not probe.exists():
        probe = probe.parent
    if not probe.is_dir():
        raise BackupError(f"{probe} n'est pas un dossier")
    inside = subprocess.run(
        ["git", "-C", str(probe), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
    )
    if inside.returncode != 0:
        return
    ignored = subprocess.run(
        ["git", "-C", str(probe), "check-ignore", "-q", str(out_dir.resolve()) + "/"],
        capture_output=True,
    )
    if ignored.returncode != 0:
        raise BackupError(f"{out_dir} est dans un dépôt Git et n'est pas ignoré : choisir un autre dossier")


def check_identity(csr: int) -> None:
    if csr in (0, 0xFFFFFFFF):
        raise BackupError(f"CSR invalide (0x{csr:08X}) : vérifier le jumper JC1 et le câblage J33")


def cfm_report(cfm: bytes) -> dict:
    word = cfm[CFMSEC_OFFSET : CFMSEC_OFFSET + 4]
    factory = word == b"\xff\xff\xff\xff"
    return {
        "cfm_field": cfm.hex(),
        "security_word": word.hex(),
        "security_interpretation": (
            "valeur usine (0xFFFFFFFF)" if factory else "valeur non usine : à comparer au RM MCF52259, table 18-7"
        ),
    }


def read_flash(transport) -> tuple[bytes, bytes, int]:
    """Arrête le processeur, lit deux fois, et le relance dans tous les cas."""
    transport.halt()
    try:
        csr = transport.read_csr()
        check_identity(csr)
        first = transport.read_memory(mm.BACKUP_START, FLASH_LEN)
        second = transport.read_memory(mm.BACKUP_START, FLASH_LEN)
        cfm = first[mm.CFM_START : mm.CFM_END + 1]
    except Exception:
        try:
            transport.resume()
        except PicoError as exc:
            print(f"RELANCE ÉCHOUÉE : {exc}. Couper et remettre l'alimentation du BP.", file=sys.stderr)
            transport.release()
        else:
            print("Processeur relancé après l'erreur.", file=sys.stderr)
        raise
    transport.resume()
    if hashlib.sha256(first).digest() != hashlib.sha256(second).digest():
        raise BackupError("les deux lectures diffèrent : aucune sauvegarde valide")
    return first, cfm, csr


def write_backup(data: bytes, cfm: bytes, csr: int, out_dir: Path, serial: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = out_dir / f"backup-{serial}-{tag}"
    sha = hashlib.sha256(data).hexdigest()
    bin_path = stem.with_suffix(".bin")
    bin_path.write_bytes(data)
    if hashlib.sha256(bin_path.read_bytes()).hexdigest() != sha:
        raise BackupError("le fichier écrit diffère de la lecture")
    stem.with_suffix(".s19").write_text(_to_srec(data, mm.BACKUP_START))
    stem.with_suffix(".sha256").write_text(f"{sha}  {bin_path.name}\n")
    meta = {
        "serial": serial,
        "date": tag,
        "sha256": sha,
        "verified": True,
        "reads_compared": 2,
        "csr": f"0x{csr:08X}",
        "crc_stored": f"0x{int.from_bytes(data[mm.APP_HEADER_CRC_ADDR:mm.APP_HEADER_CRC_ADDR+2], 'big'):04X}",
        "version": f"0x{int.from_bytes(data[mm.APP_HEADER_VERSION_ADDR:mm.APP_HEADER_VERSION_ADDR+2], 'big'):04X}",
        **cfm_report(cfm),
    }
    meta_path = stem.with_suffix(".json")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return meta_path


def run_backup(transport, out_dir: Path, serial: str) -> Path:
    check_out_dir(out_dir)
    transport.connect()
    try:
        data, cfm, csr = read_flash(transport)
    finally:
        transport.disconnect()
    return write_backup(data, cfm, csr, out_dir, serial)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bdm-backup", description=__doc__)
    parser.add_argument("--port", required=True, help="port USB du Pico, ex. /dev/cu.usbmodem2101")
    parser.add_argument("--serial", required=True, help="nom de la carte, repris dans les fichiers")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    import serial as pyserial

    try:
        with pyserial.Serial(args.port, 115200, timeout=5) as port:
            meta = run_backup(PicoReadOnlyTransport(port), args.out_dir, args.serial)
    except (BackupError, PicoError) as exc:
        print(f"ÉCHEC : {exc}", file=sys.stderr)
        return 1
    print(f"Sauvegarde valide : {meta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
