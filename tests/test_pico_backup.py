import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from bdm_programmer import backup_cli as bc
from bdm_programmer import memory_map as mm
from bdm_programmer.transport.pico_transport import (
    PicoError,
    PicoReadOnlyTransport,
    TargetNotPowered,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "firmware" / "pico"))
import bdm_protocol as bp


class FakeHw:
    """Cible BDM simulée au niveau des paquets de 17 bits."""

    def __init__(self, mv=3300, not_ready=0):
        self.mv, self.not_ready = mv, not_ready
        self.sent, self.queue, self.pending = [], [], []
        self.halts = self.stops = 0

    def sense_mv(self):
        return self.mv

    def start_and_halt(self):
        self.halts += 1
        return 1

    def stop(self):
        self.stops += 1

    def exchange(self, word):
        self.sent.append(word)
        if self.pending:
            self.pending.append(word)
            if len(self.pending) == 3:
                a = (self.pending[1] << 16) | self.pending[2]
                self.pending = []
                self.queue = [bp.NOT_READY] * self.not_ready + [(a >> 16) & 0xFFFF, a & 0xFFFF]
            return 0xFFFF
        if word == bp.READ_LONG:
            self.pending = [word]
        elif word == bp.RDMREG_CSR:
            self.queue = [0x0010, 0x0000]
        elif word == bp.GO:
            self.queue = [0xFFFF]
        elif word == bp.NOP and self.queue:
            return self.queue.pop(0)
        return 0xFFFF


class FakeTarget:
    def __init__(self, image=None, csr=0x00100000, unstable=False, fail_read=False, powered=True):
        self.image = image or bytes(range(256)) * (mm.FLASH_SIZE // 256)
        self.csr, self.unstable, self.fail_read, self.powered = csr, unstable, fail_read, powered
        self.calls, self.reads = [], 0

    def connect(self):
        self.calls.append("connect")
        if not self.powered:
            raise TargetNotPowered("off")

    def halt(self):
        self.calls.append("halt")

    def read_csr(self):
        return self.csr

    def read_memory(self, address, length):
        self.reads += 1
        if self.fail_read:
            raise PicoError("READ : ERR BUS")
        data = bytearray(self.image[address : address + length])
        if self.unstable and self.reads == 2:
            data[0] ^= 1
        return bytes(data)

    def resume(self):
        self.calls.append("resume")

    def release(self):
        self.calls.append("release")

    def disconnect(self):
        self.calls.append("disconnect")


def started_agent(**kw):
    hw = FakeHw(**kw)
    agent = bp.Agent(hw)
    assert agent.handle("HALT").startswith("OK")
    return agent, hw


def test_aucune_operation_d_ecriture_sur_le_chemin_pico():
    for name in ("erase_range", "write_memory", "program", "erase"):
        assert not hasattr(PicoReadOnlyTransport, name)
    assert set(bp.ALLOWED_OPCODES) == {0x0000, 0x0C00, 0x1980, 0x2D80}
    tree = ast.parse((ROOT / "src/bdm_programmer/backup_cli.py").read_text())
    imported = " ".join(
        ast.dump(n) for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
    )
    for forbidden in ("programmer'", "interlocks", "usbdm", "gpio_bitbang", "mock_transport"):
        assert forbidden not in imported
    source = (ROOT / "firmware/pico/bdm_protocol.py").read_text().split('"""', 2)[2]
    numbers = {n.value for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Constant) and isinstance(n.value, int)}
    for base in (0x1800, 0x1840, 0x1880, 0x1C00, 0x1C40, 0x1C80, 0x0800):
        assert base not in numbers
    assert not any(0x2C00 <= n <= 0x2CFF or 0x2080 <= n <= 0x209F for n in numbers)


@pytest.mark.parametrize("line", ["WRITE 0 4", "ERASE", "FILL 0 4", "POKE 400 0"])
def test_commande_hors_liste_blanche_refusee(line):
    agent, hw = started_agent()
    before = list(hw.sent)
    assert agent.handle(line) == "ERR UNKNOWN"
    assert hw.sent == before


def test_opcode_interdit_refuse_avant_le_bdm():
    agent, hw = started_agent()
    with pytest.raises(bp.BdmError):
        agent._command(0x1880)
    assert hw.sent == []


@pytest.mark.parametrize("args", ["80000 4", "7FFFC 8", "2 4", "0 3", "0 800"])
def test_lecture_hors_plage_ou_non_alignee_refusee(args):
    agent, hw = started_agent()
    assert agent.handle(f"READ {args}").startswith("ERR")
    assert hw.sent == []


def test_lecture_attend_la_cible():
    agent, _ = started_agent(not_ready=3)
    assert agent.handle("READ 10 8") == "OK 0000001000000014"


def test_carte_non_alimentee_sans_arret():
    hw = FakeHw(mv=120)
    assert bp.Agent(hw).handle("HALT").startswith("ERR NO_POWER")
    assert hw.halts == 0


def test_carte_non_alimentee_sans_lecture(tmp_path):
    t = FakeTarget(powered=False)
    with pytest.raises(TargetNotPowered):
        bc.run_backup(t, tmp_path, "a")
    assert "halt" not in t.calls and t.reads == 0


@pytest.mark.parametrize("csr", [0, 0xFFFFFFFF])
def test_identite_inattendue_sans_lecture(tmp_path, csr):
    t = FakeTarget(csr=csr)
    with pytest.raises(bc.BackupError, match="JC1"):
        bc.run_backup(t, tmp_path, "a")
    assert t.reads == 0 and "resume" in t.calls


def test_deux_lectures_identiques_requises(tmp_path):
    t = FakeTarget(unstable=True)
    with pytest.raises(bc.BackupError, match="diffèrent"):
        bc.run_backup(t, tmp_path, "a")
    assert list(tmp_path.iterdir()) == []


def test_sauvegarde_complete_et_rapport_zone_cfm(tmp_path):
    image = bytearray(b"\xff" * mm.FLASH_SIZE)
    image[0x3000:0x3004] = bytes.fromhex("12340063")
    t = FakeTarget(image=bytes(image))
    meta_path = bc.run_backup(t, tmp_path, "banc")
    meta = json.loads(meta_path.read_text())
    assert t.reads == 2 and t.calls == ["connect", "halt", "resume", "disconnect"]
    assert meta["sha256"] == hashlib.sha256(bytes(image)).hexdigest()
    assert (meta["crc_stored"], meta["version"]) == ("0x1234", "0x0063")
    assert meta["security_word"] == "ffffffff" and "usine" in meta["security_interpretation"]
    assert len(meta["cfm_field"]) == 48
    assert {p.suffix for p in tmp_path.iterdir()} == {".bin", ".s19", ".sha256", ".json"}


def test_relance_apres_erreur(tmp_path):
    t = FakeTarget(fail_read=True)
    with pytest.raises(PicoError):
        bc.run_backup(t, tmp_path, "a")
    assert "resume" in t.calls and "disconnect" in t.calls


def _git(path, *args):
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def test_sortie_refusee_dans_le_depot(tmp_path):
    _git(tmp_path, "init")
    (tmp_path / ".gitignore").write_text("ignored/\n")
    with pytest.raises(bc.BackupError, match="dépôt"):
        bc.check_out_dir(tmp_path / "sauvegardes")
    bc.check_out_dir(tmp_path / "ignored")


def test_transport_decoupe_et_decode():
    class Port:
        def __init__(self):
            self.out, self.sizes = [], []

        def write(self, b):
            self.out.append(b)

        def readline(self):
            cmd = self.out[-1].decode().split()
            if "bdm_agent.run()" in self.out[-1].decode():
                return b"READY\r\n"
            if cmd[0] == "SENSE":
                return b"OK 3300 1\r\n"
            size = int(cmd[2], 16)
            self.sizes.append(size)
            return b"OK " + b"ab" * size + b"\r\n"

    port = Port()
    t = PicoReadOnlyTransport(port)
    t.connect()
    assert t.read_memory(0, 2048 + 4) == b"\xab" * 2052
    assert port.sizes == [1024, 1024, 4]


def test_liaison_muette_detectee():
    class Mute(FakeHw):
        def exchange(self, word):
            self.sent.append(word)
            return 0

    agent = bp.Agent(Mute())
    agent.handle("HALT")
    assert agent.handle("CSR").startswith("ERR NO_LINK")
    assert agent.handle("GO") == "ERR GO_NOT_ACKED"
