#!/usr/bin/env python3
"""Ferme les dernières liaisons courtes laissées par le routeur, sous le contrôle du DRC de KiCad.

    $KPY close_gaps.py [chemin de kicad-cli]

Pour chaque liaison manquante, le script essaie une piste droite de 0,15 mm sur la face avant,
depuis le bout en l'air vers la pastille ou le via du même net le plus proche (3 mm au plus),
puis, si le net a un plan interne, vers un via neuf posé à moins de 2 mm.
Une piste n'est gardée que si le DRC compte une liaison manquante de moins et aucune autre
violation de plus. Sinon elle est retirée et la liaison reste signalée.
"""
import json
import math
import os
import subprocess
import sys
import tempfile

import pcbnew

PCB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "carte-diagnostic-bp.kicad_pcb")
IGNORED = {"silk_overlap", "silk_over_copper", "silk_edge_clearance"}


def drc(cli):
    out = os.path.join(tempfile.mkdtemp(), "drc.json")
    subprocess.run([cli, "pcb", "drc", "--severity-all", "--format", "json", "-o", out, PCB], capture_output=True)
    rep = json.load(open(out))
    return rep.get("unconnected_items", []), [v for v in rep.get("violations", []) if v["type"] not in IGNORED]


def main(cli="/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"):
    loose, bad = drc(cli)
    kept = 0
    for item in loose:
        net = item["items"][0]["description"].split("[")[1].split("]")[0]
        ends = [(i["pos"]["x"], i["pos"]["y"]) for i in item["items"][:2]]
        board = pcbnew.LoadBoard(PCB)
        netinfo = board.FindNet(net) or board.FindNet("/" + net)
        targets = [p.GetPosition() for p in board.GetPads() if p.GetNetCode() == netinfo.GetNetCode()]
        targets += [t.GetPosition() for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetCode() == netinfo.GetNetCode()]
        cands = []
        for sx, sy in ends:
            for t in targets:
                d = math.hypot(pcbnew.ToMM(t.x) - sx, pcbnew.ToMM(t.y) - sy)
                if 0.05 < d <= 3:
                    cands.append((d, sx, sy, pcbnew.ToMM(t.x), pcbnew.ToMM(t.y)))
        # net porté par un plan interne : essayer aussi un via neuf autour du bout en l'air
        vias = []
        if any(z.GetNetCode() == netinfo.GetNetCode() and z.GetLayer() in (pcbnew.In1_Cu, pcbnew.In2_Cu) for z in board.Zones()):
            for sx, sy in ends:
                for r in (0.8, 1.0, 1.3, 1.6, 2.0):
                    for k in range(16):
                        ang = k * math.pi / 8
                        vias.append((r, sx, sy, round(sx + r * math.cos(ang), 4), round(sy + r * math.sin(ang), 4)))
        done = False
        for d, sx, sy, tx, ty in sorted(cands)[:12] + sorted(vias):
            board = pcbnew.LoadBoard(PCB)
            backup = open(PCB, "rb").read()
            if (d, sx, sy, tx, ty) in vias:
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(tx), pcbnew.FromMM(ty)))
                via.SetWidth(pcbnew.F_Cu, pcbnew.FromMM(0.6))
                via.SetDrill(pcbnew.FromMM(0.3))
                via.SetNet(board.FindNet(netinfo.GetNetname()))
                board.Add(via)
            track = pcbnew.PCB_TRACK(board)
            track.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(sx), pcbnew.FromMM(sy)))
            track.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(tx), pcbnew.FromMM(ty)))
            track.SetWidth(pcbnew.FromMM(0.15))
            track.SetLayer(pcbnew.F_Cu)
            track.SetNet(board.FindNet(netinfo.GetNetname()))
            board.Add(track)
            pcbnew.ZONE_FILLER(board).Fill(board.Zones())
            pcbnew.SaveBoard(PCB, board)
            loose2, bad2 = drc(cli)
            if len(loose2) < len(loose) and len(bad2) <= len(bad):
                loose, bad, done, kept = loose2, bad2, True, kept + 1
                print("liaison fermée : %s, %.2f mm" % (net, d))
                break
            open(PCB, "wb").write(backup)
        if not done:
            print("liaison laissée ouverte :", net, ends)
    print("pistes ajoutées : %d ; liaisons manquantes : %d ; autres violations : %d" % (kept, len(loose), len(bad)))
    return 1 if loose or bad else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
