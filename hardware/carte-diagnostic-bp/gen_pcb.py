#!/usr/bin/env python3
"""Génère la carte ``carte-diagnostic-bp.kicad_pcb`` : empreintes, nets, placement et contour.

Feature carte-diagnostic-bp-2026-11-009 (essensys-hub/essensys-feature-lifecycle#67), tâche 1.6.
À lancer avec le Python fourni par KiCad 10 (module ``pcbnew``) :

    KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
    kicad-cli sch export netlist --format kicadsexpr -o /tmp/carte.net carte-diagnostic-bp.kicad_sch
    $KPY gen_pcb.py /tmp/carte.net

Le routage des pistes est fait ensuite (voir README) ; ce script ne trace aucune piste.
"""
import os
import re
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
FPDIR = os.environ.get("KICAD9_FOOTPRINT_DIR", "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")
W, H = 100.0, 60.0          # dimensions de la carte, mm
OX, OY = 100.0, 100.0       # origine de la carte sur la feuille
MM = pcbnew.FromMM

# ref -> (x, y, angle) en mm, repère carte (0,0 en haut à gauche)
PLACE = {
    "A1": (13, 30, 0),       # module Pico, USB du module vers le haut
    "J2": (38, 9, 90),       # nappe vers J33
    "J1": (40, 55.5, 0),     # USB-C, bord bas
    "U5": (40, 47, 0), "U2": (40, 38, 0), "Y2": (48, 38, 0), "U3": (54, 49, 0),
    "U1": (64, 24, 0), "U6": (78, 12, 0), "Y1": (64, 37, 0), "SW1": (67, 53, 0), "J5": (64, 5, 90), "D5": (72, 44, 0),
    "J3": (92, 16, 0), "J4": (92, 42, 0), "U4": (80.5, 30.5, 0),
}
# grappes de composants passifs : (x0, y0, pas x, pas y, colonnes, angle, références)
CLUSTERS = [
    (31, 30, 2.6, 0, 9, 90, ["R1", "R2", "C1", "C20", "C18", "C19"]),                       # USB et hub
    (50, 55, 2.6, 0, 9, 90, ["C2", "C10"]),                                                   # régulateur
    (27, 18, 2.6, 0, 9, 90, ["R10", "R11", "R12", "R13", "R14", "R15", "R16", "R17"]),        # série BDM et mesure
    (51, 16, 0, 2.6, 9, 0, ["R30", "R31", "R32", "R33", "R34", "R35"]),                        # prises analyseur
    (55, 12, 2.6, 0, 8, 90, ["C3", "C4", "C5", "C6", "C7", "C8", "C9"]),                       # découplage RP2040, haut
    (74, 20, 0, 2.6, 9, 0, ["C11", "C12", "C13", "C14", "R6", "R7"]),                          # découplage RP2040, droite
    (55, 42, 2.6, 0, 9, 90, ["C16", "C17", "R5", "R3", "R4", "R8"]),                           # quartz, USB, LED
    (80, 20.5, 0, 2.6, 4, 0, ["R20", "R21", "C15"]),                                             # port I2C
    (80, 36, 0, 3.2, 9, 0, ["D1", "D2", "F1", "R22", "D3", "D4"]),
]


def parse_netlist(path):
    text = open(path, encoding="utf-8").read()
    comps = {}
    for block in re.split(r"\n\t\t\(comp\n", text[text.index("(components"):text.index("(libparts")])[1:]:
        ref = re.search(r'\(ref "([^"]+)"\)', block)[1]
        comps[ref] = (re.search(r'\(value "([^"]*)"\)', block)[1], re.search(r'\(footprint "([^"]*)"\)', block)[1])
    pads = {}
    for block in re.split(r"\n\s*\(net\n", text[text.index("(nets"):])[1:]:
        name = re.search(r'\(name "([^"]*)"\)', block)[1].lstrip("/")
        if name.startswith("unconnected"):
            continue
        for r, p in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', block):
            pads[(r, p)] = name
    return comps, pads


def main(netlist):
    comps, padnets = parse_netlist(netlist)
    board = pcbnew.BOARD()
    place = dict(PLACE)
    for x0, y0, dx, dy, cols, ang, refs in CLUSTERS:
        for i, ref in enumerate(refs):
            place[ref] = (x0 + dx * (i % cols), y0 + dy * (i % cols), ang)
    missing = sorted(set(comps) - set(place))
    if missing:
        sys.exit("composants sans position : %s" % missing)

    nets = {}
    for name in sorted(set(padnets.values())):
        nets[name] = pcbnew.NETINFO_ITEM(board, name)
        board.Add(nets[name])
    used = set()
    for ref in sorted(comps):
        value, fpid = comps[ref]
        lib, name = fpid.split(":")
        fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + ".pretty"), name)
        if fp is None:
            sys.exit("empreinte introuvable : %s" % fpid)
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        x, y, ang = place[ref]
        board.Add(fp)
        fp.SetPosition(pcbnew.VECTOR2I(MM(OX + x), MM(OY + y)))
        fp.SetOrientationDegrees(ang)
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            if key in padnets:
                pad.SetNet(nets[padnets[key]])
                used.add(key)
    orphan = sorted(set(padnets) - used)
    if orphan:
        sys.exit("broches du schéma sans pastille : %s" % orphan)

    # contour
    pts = [(0, 0), (W, 0), (W, H), (0, H), (0, 0)]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(MM(OX + x1), MM(OY + y1)))
        seg.SetEnd(pcbnew.VECTOR2I(MM(OX + x2), MM(OY + y2)))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(MM(0.1))
        board.Add(seg)

    # règles : capacités standard JLCPCB 2 couches (piste et isolement 0,127 mm mini, via 0,3/0,6 mm)
    bds = board.GetDesignSettings()
    bds.m_TrackMinWidth = MM(0.15)
    bds.m_MinClearance = MM(0.15)
    bds.m_ViasMinSize = MM(0.6)
    bds.m_MinThroughDrill = MM(0.3)
    bds.m_CopperEdgeClearance = MM(0.3)
    nc = bds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(MM(0.15))
    nc.SetTrackWidth(MM(0.2))
    nc.SetViaDiameter(MM(0.6))
    nc.SetViaDrill(MM(0.3))

    out = os.path.join(HERE, "carte-diagnostic-bp.kicad_pcb")
    pcbnew.SaveBoard(out, board)
    print("ok", len(comps), "empreintes,", len(nets), "nets ->", os.path.basename(out))


if __name__ == "__main__":
    main(sys.argv[1])
