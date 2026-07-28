"""Proves the backup-before-write interlock survives across *separate
process* invocations of the CLI (e.g. distinct steps in a CI job) — not
just within one Python process. This is exactly the gap a purely
in-memory BackupStore would miss: each `bdm-programmer` invocation is its
own process, so `backup` in one step and `erase-app` in the next only see
each other via the on-disk `--backup-record` JSON sidecar.

Uses real `subprocess` calls to `python -m bdm_programmer.cli` (mock
transport — no hardware) rather than importing `cli.main` twice in one
interpreter, which would trivially "pass" via the module-level singleton
even if the disk handoff were broken.
"""

import subprocess
import sys
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "BP_MQX_ETH-sample.s19"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "bdm_programmer.cli", *args],
        capture_output=True,
        text=True,
    )


def _crc_inject(tmp_path: Path) -> Path:
    working = tmp_path / "app.s19"
    working.write_text(FIXTURE.read_text())
    output = tmp_path / "app-crc.s19"
    result = subprocess.run(
        [sys.executable, "-m", "bdm_programmer.crc_inject", str(working), "-o", str(output)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return output


def test_erase_app_in_a_fresh_process_is_refused_without_backup_record(
    tmp_path,
) -> None:
    result = _run("--serial", "proc-test", "erase-app")
    assert result.returncode == 2
    assert "run `backup` first" in result.stderr


def test_backup_record_carries_verified_backup_across_processes(tmp_path) -> None:
    out_dir = tmp_path / "backups"
    s19 = _crc_inject(tmp_path)

    backup_proc = _run(
        "--serial", "proc-test", "backup", "--out-dir", str(out_dir)
    )
    assert backup_proc.returncode == 0, backup_proc.stderr
    assert "verified=True" in backup_proc.stdout

    record_line = next(
        line for line in backup_proc.stdout.splitlines() if line.startswith("backup: record=")
    )
    record_path = record_line.split("=", 1)[1]

    # A brand-new process, with NO knowledge of the previous one's memory,
    # must still be able to erase-app/program once pointed at the sidecar.
    erase_proc = _run(
        "--serial", "proc-test", "--backup-record", record_path, "erase-app"
    )
    assert erase_proc.returncode == 0, erase_proc.stderr

    program_proc = _run(
        "--serial", "proc-test", "--backup-record", record_path, "program", str(s19)
    )
    assert program_proc.returncode == 0, program_proc.stderr
