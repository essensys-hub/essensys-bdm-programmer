#!/usr/bin/env python3
"""Route la carte avec Freerouting, puis remplit les plans de masse.

À lancer avec le Python de KiCad 10, après ``gen_pcb.py`` :

    $KPY route_pcb.py /chemin/freerouting-2.5.0.jar [passes]

Freerouting (https://github.com/freerouting/freerouting, v2.5.0) n'est pas versionné ici.
Le routage automatique doit être relu avant toute commande de cartes.
"""
import os
import subprocess
import sys
import tempfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "carte-diagnostic-bp" + ("-" + os.environ["CARTE_VARIANTE"] if os.environ.get("CARTE_VARIANTE") else "") + ".kicad_pcb")


def stitch(board):
    """Relie aux plans internes les bouts de piste GND et +3V3 laissés en l'air par le routeur."""
    planes = {z.GetNetname() for z in board.Zones()}
    tracks = [t for t in board.GetTracks() if t.GetNetname() in planes]
    ends = {}
    for t in tracks:
        pts = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
        for p in pts:
            ends.setdefault((t.GetNetname(), p.x, p.y), []).append(t)
    pads = [p for p in board.GetPads() if p.GetNetname() in planes]
    added = 0
    for (net, x, y), items in sorted(ends.items()):
        pos = pcbnew.VECTOR2I(x, y)
        if len(items) > 1 or any(i.Type() == pcbnew.PCB_VIA_T for i in items):
            continue
        if any(p.GetNetname() == net and p.HitTest(pos) for p in pads):
            continue
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(pos)
        via.SetWidth(pcbnew.F_Cu, pcbnew.FromMM(0.6))
        via.SetDrill(pcbnew.FromMM(0.3))
        via.SetNet(items[0].GetNet())
        board.Add(via)
        added += 1
    print("vias vers les plans :", added)


def main(jar, passes="40"):
    tmp = tempfile.mkdtemp()
    dsn, ses = os.path.join(tmp, "carte.dsn"), os.path.join(tmp, "carte.ses")
    board = pcbnew.LoadBoard(PCB)
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        sys.exit("export DSN impossible")
    log = open(os.path.join(tmp, "route.log"), "w")
    subprocess.run(["java", "-jar", jar, "-de", dsn, "-do", ses, "-mp", passes, "--gui.enabled=false"], stdout=log, stderr=log, check=True)
    if not pcbnew.ImportSpecctraSES(board, ses):
        sys.exit("import SES impossible")
    stitch(board)
    # plans de masse des faces externes, ajoutés après le routage : ils relient les bouts de piste GND restants
    gnd = board.FindNet("/GND") or board.FindNet("GND")
    box = board.GetBoardEdgesBoundingBox()
    m = pcbnew.FromMM(0.5)
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNet(gnd)
        zone.SetZoneName("GND")
        outline = zone.Outline()
        outline.NewOutline()
        for x, y in ((box.GetLeft() + m, box.GetTop() + m), (box.GetRight() - m, box.GetTop() + m),
                     (box.GetRight() - m, box.GetBottom() - m), (box.GetLeft() + m, box.GetBottom() - m)):
            outline.Append(x, y)
        zone.SetLocalClearance(pcbnew.FromMM(0.25))
        zone.SetMinThickness(pcbnew.FromMM(0.2))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        board.Add(zone)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)
    print("ok", len(board.GetTracks()), "segments et vias ; journal :", log.name)


if __name__ == "__main__":
    main(*sys.argv[1:])
