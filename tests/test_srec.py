"""S-record parser/writer tests, using a real essensys-gcc header layout."""

import pytest

from bdm_programmer.srec import SRecFile, SRecordError

# Real line lifted from essensys-gcc/bp/build/bp/BP_MQX_ETH-local-dev.s19:
# address 0x3000, 16 bytes: CRC placeholder 0102, version 0000, jmp 4EF9
# 00009E64, rts 4E75, padding 00000000.
_HEADER_LINE = "S31500003000010200004EF900009E644E7500000000AB"
_S19_TEXT = (
    "S02400006275696C642F62702F42505F4D51585F4554482D6C6F63616C2D6465762E733139C5\n"
    f"{_HEADER_LINE}\n"
    "S9030000FC\n"
)


def _write(tmp_path, text: str):
    path = tmp_path / "sample.s19"
    path.write_text(text)
    return path


def test_load_rejects_bad_checksum(tmp_path) -> None:
    bad = _S19_TEXT.replace(_HEADER_LINE, _HEADER_LINE[:-2] + "00")
    path = _write(tmp_path, bad)
    with pytest.raises(SRecordError):
        SRecFile.load(path)


def test_read_range_extracts_header_bytes(tmp_path) -> None:
    path = _write(tmp_path, _S19_TEXT)
    image = SRecFile.load(path)
    header = image.read_range(0x3000, 0x300F)
    expected = bytes([0x01, 0x02, 0x00, 0x00, 0x4E, 0xF9, 0x00, 0x00,
                       0x9E, 0x64, 0x4E, 0x75, 0x00, 0x00, 0x00, 0x00])
    assert header == expected


def test_read_range_fills_gaps_with_0xff(tmp_path) -> None:
    path = _write(tmp_path, _S19_TEXT)
    image = SRecFile.load(path)
    gap = image.read_range(0x4000, 0x4003)
    assert gap == b"\xff\xff\xff\xff"


def test_patch_word_be_updates_data_and_checksum(tmp_path) -> None:
    path = _write(tmp_path, _S19_TEXT)
    image = SRecFile.load(path)
    image.patch_word_be(0x3000, 0xBEEF)
    out_path = tmp_path / "patched.s19"
    image.save(out_path)

    reloaded = SRecFile.load(out_path)  # re-parses; raises on bad checksum
    assert reloaded.read_range(0x3000, 0x3001) == b"\xbe\xef"
    # Rest of the record must be untouched.
    assert reloaded.read_range(0x3002, 0x300F) == bytes(
        [0x00, 0x00, 0x4E, 0xF9, 0x00, 0x00, 0x9E, 0x64, 0x4E, 0x75, 0x00, 0x00, 0x00, 0x00]
    )


def test_patch_word_be_raises_if_no_record_covers_address(tmp_path) -> None:
    path = _write(tmp_path, _S19_TEXT)
    image = SRecFile.load(path)
    with pytest.raises(SRecordError):
        image.patch_word_be(0x9000, 0x0000)


def test_covers_range_detects_overlap(tmp_path) -> None:
    path = _write(tmp_path, _S19_TEXT)
    image = SRecFile.load(path)
    assert image.covers_range(0x3000, 0x3005) is True
    assert image.covers_range(0x9000, 0x9010) is False
