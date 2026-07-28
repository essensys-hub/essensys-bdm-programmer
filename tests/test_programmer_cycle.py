"""End-to-end programmer tests against MockTransport: the full
backup -> erase-app -> program -> verify -> reset cycle, plus the negative
paths specs/bdm-programmer/spec.md requires (refuse without backup,
persistence preserved bit-for-bit)."""

from pathlib import Path

import pytest

from bdm_programmer import memory_map as mm
from bdm_programmer.backup import BackupStore
from bdm_programmer.crc_inject import main as crc_inject_main
from bdm_programmer.interlocks import InterlockError
from bdm_programmer.programmer import BdmProgrammer
from bdm_programmer.transport.mock_transport import MockTransport

FIXTURE = Path(__file__).parent / "fixtures" / "BP_MQX_ETH-sample.s19"


def _crc_injected_s19(tmp_path: Path) -> Path:
    working = tmp_path / "app.s19"
    working.write_text(FIXTURE.read_text())
    output = tmp_path / "app-crc.s19"
    rc = crc_inject_main([str(working), "-o", str(output)])
    assert rc == 0
    return output


def _seeded_flash() -> bytes:
    """A plausible 'currently deployed' flash image: 0xFF everywhere except
    a distinct, recognizable persistence payload at 0x7E000."""
    flash = bytearray([0xFF]) * mm.FLASH_SIZE
    marker = bytes(range(256)) * 16  # 4 KiB, matches persistence size
    flash[mm.PERSISTENCE_START : mm.PERSISTENCE_START + len(marker)] = marker
    return bytes(flash)


def _programmer() -> tuple[BdmProgrammer, MockTransport]:
    transport = MockTransport(initial_image=_seeded_flash())
    store = BackupStore()
    return BdmProgrammer(transport, store, serial="board-001"), transport


def test_program_without_backup_is_refused_and_sends_nothing(tmp_path) -> None:
    programmer, transport = _programmer()
    s19 = _crc_injected_s19(tmp_path)

    with pytest.raises(InterlockError, match="run `backup` first"):
        programmer.program(s19)

    assert transport.call_log == []  # zero BDM traffic before the refusal


def test_erase_app_without_backup_is_refused(tmp_path) -> None:
    programmer, transport = _programmer()
    with pytest.raises(InterlockError, match="run `backup` first"):
        programmer.erase_app()
    assert transport.call_log == []


def test_full_cycle_backup_erase_program_verify_preserves_persistence(
    tmp_path,
) -> None:
    programmer, transport = _programmer()
    s19 = _crc_injected_s19(tmp_path)
    transport.connect()

    persistence_before = transport.read_memory(
        mm.PERSISTENCE_START, mm.PERSISTENCE_END - mm.PERSISTENCE_START + 1
    )

    record = programmer.backup(tmp_path / "backups")
    assert record.verified is True

    programmer.erase_app()
    programmer.program(s19)
    result = programmer.verify(s19)
    assert result.ok is True

    persistence_after = transport.read_memory(
        mm.PERSISTENCE_START, mm.PERSISTENCE_END - mm.PERSISTENCE_START + 1
    )
    assert persistence_after == persistence_before

    info = programmer.reset()
    assert info.crc_stored != mm.CRC_PLACEHOLDER


def test_verify_fails_on_readback_mismatch(tmp_path) -> None:
    programmer, transport = _programmer()
    s19 = _crc_injected_s19(tmp_path)

    programmer.backup(tmp_path / "backups")
    programmer.erase_app()
    programmer.program(s19)

    # Corrupt one byte directly in the mock flash to simulate a bad write.
    transport.connect()
    transport.halt()
    transport.write_memory(mm.APP_START + 0x10, b"\x00")

    result = programmer.verify(s19)
    assert result.ok is False
    assert result.mismatch_address == mm.APP_START + 0x10


def test_program_refuses_placeholder_crc(tmp_path) -> None:
    programmer, transport = _programmer()
    working = tmp_path / "no-crc.s19"
    working.write_text(FIXTURE.read_text())  # still carries 0x0102 placeholder

    programmer.backup(tmp_path / "backups")
    with pytest.raises(InterlockError, match="placeholder"):
        programmer.program(working)
