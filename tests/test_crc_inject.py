"""crc-inject tests: placeholder detection, patch correctness, and an
end-to-end run against a real essensys-gcc build artifact fixture."""

from pathlib import Path

import pytest

from bdm_programmer import memory_map as mm
from bdm_programmer.crc16 import crc16_modbus
from bdm_programmer.crc_inject import main
from bdm_programmer.interlocks import InterlockError
from bdm_programmer.programmer import inject_crc
from bdm_programmer.srec import SRecFile

FIXTURE = Path(__file__).parent / "fixtures" / "BP_MQX_ETH-sample.s19"


def test_fixture_carries_the_known_placeholder() -> None:
    image = SRecFile.load(FIXTURE)
    crc_bytes = image.read_range(mm.APP_HEADER_CRC_ADDR, mm.APP_HEADER_CRC_ADDR + 1)
    assert crc_bytes == b"\x01\x02"


def test_inject_crc_patches_the_header_and_matches_manual_computation() -> None:
    image = SRecFile.load(FIXTURE)
    computed = inject_crc(image)

    # Recompute independently over the same declared range with the same
    # 0xFF gap-fill policy, to catch a bug in inject_crc()'s own plumbing.
    zone = SRecFile.load(FIXTURE).read_range(
        mm.CRC_COMPUTE_START, mm.CRC_COMPUTE_END, fill=0xFF
    )
    expected = crc16_modbus(zone)
    assert computed == expected

    patched = image.read_range(mm.APP_HEADER_CRC_ADDR, mm.APP_HEADER_CRC_ADDR + 1)
    assert patched == bytes([(computed >> 8) & 0xFF, computed & 0xFF])
    assert computed != mm.CRC_PLACEHOLDER  # a real image should not collide


def test_cli_dry_run_does_not_modify_input(tmp_path) -> None:
    working = tmp_path / "input.s19"
    working.write_text(FIXTURE.read_text())
    before = working.read_text()

    rc = main([str(working), "--dry-run"])

    assert rc == 0
    assert working.read_text() == before


def test_cli_writes_patched_output(tmp_path) -> None:
    working = tmp_path / "input.s19"
    output = tmp_path / "output.s19"
    working.write_text(FIXTURE.read_text())

    rc = main([str(working), "-o", str(output)])

    assert rc == 0
    patched = SRecFile.load(output)
    crc_bytes = patched.read_range(mm.APP_HEADER_CRC_ADDR, mm.APP_HEADER_CRC_ADDR + 1)
    assert crc_bytes != b"\x01\x02"
    # Input is untouched when -o is given.
    assert working.read_text() == FIXTURE.read_text()


def test_inject_crc_refuses_image_overlapping_cfm(tmp_path) -> None:
    path = tmp_path / "cfm.s19"
    header = "S31500003000010200004EF900009E644E7500000000AB"
    cfm_record = "S309000004001122334448"
    path.write_text(f"S0030000FC\n{header}\n{cfm_record}\nS9030000FC\n")
    image = SRecFile.load(path)
    with pytest.raises(InterlockError, match="CFM"):
        inject_crc(image)
