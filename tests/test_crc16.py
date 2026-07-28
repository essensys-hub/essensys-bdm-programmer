"""CRC-16 tests: known vector + cross-check against a from-scratch table impl."""

from bdm_programmer.crc16 import crc16_modbus, pack_be, unpack_be


def test_known_vector_crc16_modbus_check_string() -> None:
    # Reference check value for CRC-16/MODBUS (poly 0x8005/0xA001 reflected,
    # init 0xFFFF, refin=refout=True, xorout=0x0000) over ASCII "123456789",
    # per the standard CRC catalogue (reveng "CRC-16/MODBUS" entry).
    assert crc16_modbus(b"123456789") == 0x4B37


def test_matches_independent_table_driven_implementation() -> None:
    """Cross-check crc16_modbus against a from-scratch table-based CRC-16
    (poly 0xA001, init 0xFFFF) to catch bugs a single implementation could
    share with itself."""
    table = _build_table()
    for sample in (b"", b"\x00", b"\xff" * 16, bytes(range(256)), b"essensys-bdm"):
        assert crc16_modbus(sample) == _crc_via_table(sample, table)


def test_pack_unpack_be_roundtrip() -> None:
    for value in (0x0000, 0x0102, 0xABCD, 0xFFFF):
        assert unpack_be(pack_be(value)) == value


def test_pack_be_matches_bootloader_storage_order() -> None:
    # vd_CalculInfosZoneNew reads Data1 (high byte) at offset 0, Data2 (low
    # byte) at offset 1 -> big-endian storage.
    assert pack_be(0x0102) == b"\x01\x02"


def _build_table() -> list[int]:
    table = []
    for byte in range(256):
        crc = byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
        table.append(crc)
    return table


def _crc_via_table(data: bytes, table: list[int]) -> int:
    crc = 0xFFFF
    for byte in data:
        crc = (crc >> 8) ^ table[(crc ^ byte) & 0xFF]
    return crc
