#!/usr/bin/env python3
"""Vérifie les invariants de sécurité de la carte de diagnostic BP sur la netlist exportée par KiCad.

Les nets attendus sont écrits ici à la main, indépendamment de ``gen_sch.py`` :
brochage J33 de la feature bdm-firmware-backup-2026-11-005, broche 1 non connectée,
+3V3S sans chemin d'alimentation, port I2C atteint seulement à travers ses protections.

Usage : kicad-cli sch export netlist --format kicadsexpr -o carte.net carte-diagnostic-bp.kicad_sch
        python3 check_netlist.py carte.net
"""
import re
import sys

# signal BDM -> (broche J33, broche du module Pico, résistance série, résistance de prise analyseur)
BDM = {
    "DSCLK": ("6", "4", "R10", "R30"),   # GP2
    "DSI": ("4", "5", "R11", "R31"),     # GP3
    "DSO": ("3", "6", "R12", "R32"),     # GP4
    "BKPT": ("2", "7", "R13", "R33"),    # GP5
    "RESET": ("8", "9", "R14", "R34"),   # GP6
    "ALLPST": ("5", "10", "R15", "R35"),  # GP7
}
EXPECTED = {
    # port I2C : passage direct, prises uniquement par 100 kΩ, fusible et LED de défaut
    "BUS_15V": {"J3.4", "J4.4"},
    "BUS_SDA": {"J3.1", "J4.1", "R21.1"},
    "BUS_SCL": {"J3.2", "J4.2", "R20.1"},
    "BUS_0V": {"J3.3", "J4.3", "F1.1", "R22.1"},
    "SCL_IN": {"R20.2", "D1.1", "U4.1"},
    "SDA_IN": {"R21.2", "D2.1", "U4.3"},
    # +3V3S du BP : mesure seule, par 10 kΩ vers GP26
    "J33_3V3S": {"J2.7", "R16.1"},
    "SENSE_3V3S": {"R16.2", "R17.1", "A1.31"},
}
for sig, (j33, pico, rs, ra) in BDM.items():
    EXPECTED["J33_" + sig] = {"J2." + j33, rs + ".2", ra + ".1"}
    EXPECTED["P_" + sig] = {"A1." + pico, rs + ".1"}
MUST_BE_UNCONNECTED = {"J2.1"}  # TCLK : jamais reliée
VALUES = {"R20": "100k", "R21": "100k", "R16": "10k", "D1": "5V1", "D2": "5V1"}


def parse(text):
    nets, loose = {}, set()
    for block in re.split(r"\n\s*\(net\n", text[text.index("(nets"):])[1:]:
        name = re.search(r'\(name "([^"]*)"\)', block)[1].lstrip("/")
        nodes = {f"{r}.{p}" for r, p in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', block) if not r.startswith("#")}
        if name.startswith("unconnected"):
            loose |= nodes
        elif nodes:
            nets[name] = nodes
    values = dict(re.findall(r'\(comp\s*\(ref "([^"]+)"\)\s*\(value "([^"]*)"\)', text))
    return nets, loose, values


def check(text):
    nets, loose, values = parse(text)
    errors = [f"{n} : attendu {sorted(v)}, obtenu {sorted(nets.get(n, set()))}" for n, v in EXPECTED.items() if nets.get(n) != v]
    errors += [f"{p} doit rester non connectée" for p in sorted(MUST_BE_UNCONNECTED - loose)]
    errors += [f"{r} : valeur attendue {v}, obtenue {values.get(r)}" for r, v in VALUES.items() if values.get(r) != v]
    for rail in ("VBUS", "+3V3", "+1V1", "HUB_3V3"):
        bad = {n for n in nets.get(rail, set()) if n.split(".")[0] in ("J2", "J3", "J4")}
        if bad:
            errors.append(f"{rail} atteint un connecteur vers la cible : {sorted(bad)}")
    return errors


def main(path):
    errors = check(open(path, encoding="utf-8").read())
    for e in errors:
        print("ÉCART", e)
    print("netlist conforme" if not errors else "netlist NON conforme")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
