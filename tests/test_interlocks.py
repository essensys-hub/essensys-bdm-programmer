"""Interlock unit tests: refuse without backup, refuse CFM range, refuse
out-of-app-zone range. These are the tests the anti-brick posture of this
whole repo rests on — see specs/bdm-programmer/spec.md."""

import pytest

from bdm_programmer import memory_map as mm
from bdm_programmer.backup import BackupRecord
from bdm_programmer.interlocks import (
    InterlockError,
    require_crc_injected,
    require_image_excludes_cfm,
    require_no_cfm_overlap,
    require_verified_backup,
    require_within_app_zone,
)
from bdm_programmer.srec import SRecFile

_HEADER_LINE = "S31500003000010200004EF900009E644E7500000000AB"
_S19_TEXT = f"S02400006275696C642F62702F42505F4D51585F4554482D6C6F63616C2D6465762E733139C5\n{_HEADER_LINE}\nS9030000FC\n"


def _verified_record() -> BackupRecord:
    return BackupRecord(
        serial="t1", timestamp="now", bin_path="b.bin", s19_path="b.s19",
        meta_path="b.json", sha256_read="x", sha256_disk="x", verified=True,
        version=0, crc_stored=0x0102,
    )


def _unverified_record() -> BackupRecord:
    return BackupRecord(
        serial="t1", timestamp="now", bin_path="b.bin", s19_path="b.s19",
        meta_path="b.json", sha256_read="x", sha256_disk="y", verified=False,
        version=0, crc_stored=0x0102,
    )


def test_refuses_write_when_no_backup_exists() -> None:
    with pytest.raises(InterlockError, match="run `backup` first"):
        require_verified_backup(None)


def test_refuses_write_when_backup_not_verified() -> None:
    with pytest.raises(InterlockError, match="NOT verified"):
        require_verified_backup(_unverified_record())


def test_allows_write_when_backup_verified() -> None:
    require_verified_backup(_verified_record())  # must not raise


@pytest.mark.parametrize(
    "start,end",
    [
        (0x0000, 0x2FFF),  # bootloader, wholly outside app zone
        (0x2FF0, 0x3010),  # straddles into app zone but starts before it
        (0x7E000, 0x7EFFF),  # persistence
        (0x7DFF0, 0x7E010),  # straddles into persistence
    ],
)
def test_refuses_range_outside_app_zone(start: int, end: int) -> None:
    with pytest.raises(InterlockError, match="outside the application zone"):
        require_within_app_zone(start, end)


def test_allows_range_fully_inside_app_zone() -> None:
    require_within_app_zone(mm.APP_START, mm.APP_END)  # must not raise


@pytest.mark.parametrize(
    "start,end",
    [
        (0x400, 0x417),  # exact CFM range
        (0x3F0, 0x405),  # overlaps start of CFM
        (0x414, 0x420),  # overlaps the Security Word specifically
        (0x000, 0x500),  # fully contains CFM
    ],
)
def test_refuses_cfm_overlap(start: int, end: int) -> None:
    with pytest.raises(InterlockError, match="CFM"):
        require_no_cfm_overlap(start, end)


@pytest.mark.parametrize(
    "start,end",
    [
        (0x300, 0x3FF),  # adjacent, just before CFM — must NOT trip
        (0x418, 0x420),  # adjacent, just after CFM — must NOT trip
    ],
)
def test_allows_adjacent_but_non_overlapping_ranges(start: int, end: int) -> None:
    require_no_cfm_overlap(start, end)  # must not raise


def test_refuses_image_covering_cfm(tmp_path) -> None:
    path = tmp_path / "cfm.s19"
    # S-record at 0x400, 4 bytes: 11 22 33 44
    line = "S309000004001122334448"
    path.write_text(f"S0030000FC\n{line}\nS9030000FC\n")
    image = SRecFile.load(path)
    with pytest.raises(InterlockError, match="CFM"):
        require_image_excludes_cfm(image)


def test_allows_image_not_covering_cfm(tmp_path) -> None:
    path = tmp_path / "sample.s19"
    path.write_text(_S19_TEXT)
    image = SRecFile.load(path)
    require_image_excludes_cfm(image)  # must not raise


def test_refuses_crc_placeholder(tmp_path) -> None:
    path = tmp_path / "placeholder.s19"
    path.write_text(_S19_TEXT)  # header line carries placeholder 0x0102
    image = SRecFile.load(path)
    with pytest.raises(InterlockError, match="placeholder"):
        require_crc_injected(image)


def test_allows_when_crc_injected(tmp_path) -> None:
    path = tmp_path / "injected.s19"
    path.write_text(_S19_TEXT)
    image = SRecFile.load(path)
    image.patch_word_be(0x3000, 0xBEEF)  # any non-placeholder CRC
    require_crc_injected(image)  # must not raise
