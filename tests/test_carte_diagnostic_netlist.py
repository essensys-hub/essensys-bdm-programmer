"""NR-bdm-programmer-67 : invariants de sécurité du schéma de la carte de diagnostic BP.

Refs essensys-hub/essensys-feature-lifecycle#67 (feature carte-diagnostic-bp-2026-11-009).
Le schéma versionné est exporté en netlist par kicad-cli, puis contrôlé par
``hardware/carte-diagnostic-bp/check_netlist.py``. Sans KiCad, les tests sont ignorés
en local ; le job CI ``kicad`` les exécute toujours.
"""
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HW = Path(__file__).resolve().parents[1] / "hardware" / "carte-diagnostic-bp"
KICAD = shutil.which("kicad-cli") or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
pytestmark = pytest.mark.skipif(not os.path.exists(KICAD), reason="kicad-cli absent")

spec = importlib.util.spec_from_file_location("check_netlist", HW / "check_netlist.py")
check_netlist = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_netlist)


@pytest.fixture(scope="module")
def netlist(tmp_path_factory):
    out = tmp_path_factory.mktemp("net") / "carte.net"
    subprocess.run([KICAD, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", str(out),
                    str(HW / "carte-diagnostic-bp.kicad_sch")], check=True, capture_output=True)
    return out.read_text(encoding="utf-8")


def test_nr_bdm_programmer_67_brochage_j33_conforme(netlist):
    assert check_netlist.check(netlist) == []


def test_nr_bdm_programmer_67_broche_1_non_connectee(netlist):
    _, loose, _ = check_netlist.parse(netlist)
    assert "J2.1" in loose


def test_nr_bdm_programmer_67_3v3s_sans_chemin_d_alimentation(netlist):
    nets, _, values = check_netlist.parse(netlist)
    assert nets["J33_3V3S"] == {"J2.7", "R16.1"} and values["R16"] == "10k"


def test_nr_bdm_programmer_67_port_i2c_tolerant_15_v_dans_les_deux_polarites(netlist):
    nets, _, values = check_netlist.parse(netlist)
    assert nets["BUS_15V"] == {"J3.4", "J4.4"}
    assert values["R20"] == values["R21"] == "100k" and values["D1"] == values["D2"] == "5V1"
    assert nets["BUS_0V"] == {"J3.3", "J4.3", "F1.1", "R22.1"}


def test_nr_bdm_programmer_67_ecart_detecte(netlist):
    assert check_netlist.check(netlist.replace('(ref "J4") (pin "4")', '(ref "U4") (pin "9")').replace(
        '(ref "J4")\n\t\t\t\t(pin "4")', '(ref "U4")\n\t\t\t\t(pin "9")')) != []


def test_nr_bdm_programmer_67_erc_drc_et_nets_sans_erreur(tmp_path):
    r = subprocess.run([KICAD, "sch", "erc", "--severity-all", "--exit-code-violations", "-o", str(tmp_path / "erc.rpt"),
                        str(HW / "carte-diagnostic-bp.kicad_sch")], capture_output=True)
    assert r.returncode == 0, (tmp_path / "erc.rpt").read_text()


def test_nr_bdm_programmer_67_carte_routee_drc_sans_erreur(tmp_path):
    """La carte routée versionnée passe le DRC sans violation ni liaison manquante."""
    r = subprocess.run([KICAD, "pcb", "drc", "--severity-all", "--exit-code-violations", "-o", str(tmp_path / "drc.rpt"),
                        str(HW / "carte-diagnostic-bp.kicad_pcb")], capture_output=True)
    assert r.returncode == 0, (tmp_path / "drc.rpt").read_text()
