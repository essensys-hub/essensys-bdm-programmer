#!/usr/bin/env python3
"""Produit le dossier de fabrication JLCPCB de la carte de diagnostic BP dans ``fab/``.

    python3 hardware/carte-diagnostic-bp/export_fab.py [chemin de kicad-cli]

Sorties : ``fab/gerbers.zip`` (cuivre, masques, pâte, sérigraphie, contour, perçages),
``fab/bom-jlcpcb.csv`` et ``fab/cpl-jlcpcb.csv``. Seuls les composants dont le champ LCSC
est une référence « C<nombre> » sont assemblés ; les autres sont listés dans
``fab/a-souder-a-la-main.csv``. Les rotations du fichier de placement sont celles de KiCad, corrigées par ``JLC_ROTATION`` ;
elles restent à contrôler dans l'aperçu de l'outil de commande JLCPCB avant de valider.
"""
import csv
import os
import re
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
VARIANT = os.environ.get("CARTE_VARIANTE", "")
NAME = "carte-diagnostic-bp" + ("-" + VARIANT if VARIANT else "")
# Corrections de rotation (degrés, sens antihoraire) entre l'orientation KiCad et celle de la bibliothèque JLCPCB,
# relevées le 2026-11-15 dans l'aperçu « Component Placements » de l'outil de commande, par référence LCSC.
JLC_ROTATION = {"C6186": 180, "C5261088": 180, "C10429": 270, "C131025": 270}  # AMS1117, USBLC6-2SC6, SN74LVC2G17, W25Q16
LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"


def run(cli, *args):
    r = subprocess.run([cli, *args], capture_output=True, text=True)
    if r.returncode:
        sys.exit("échec : %s\n%s" % (" ".join(args), r.stdout + r.stderr))


def main(cli=shutil.which("kicad-cli") or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"):
    fab, sch, pcb = os.path.join(HERE, "fab" + ("-" + VARIANT if VARIANT else "")), os.path.join(HERE, NAME + ".kicad_sch"), os.path.join(HERE, NAME + ".kicad_pcb")
    shutil.rmtree(fab, ignore_errors=True)
    ger = os.path.join(fab, "gerbers")
    os.makedirs(ger)
    run(cli, "pcb", "export", "gerbers", "--layers", LAYERS, "--subtract-soldermask", "-o", ger + "/", pcb)
    run(cli, "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "--excellon-units", "mm", "-o", ger + "/", pcb)
    with zipfile.ZipFile(os.path.join(fab, "gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(ger)):
            z.write(os.path.join(ger, f), f)

    raw = os.path.join(fab, "bom-kicad.csv")
    run(cli, "sch", "export", "bom", "--fields", "Reference,Value,Footprint,LCSC", "--labels", "Reference,Value,Footprint,LCSC",
        "--group-by", "", "-o", raw, sch)
    parts = {r["Reference"]: r for r in csv.DictReader(open(raw, encoding="utf-8"))}
    os.remove(raw)
    smt = {ref: p for ref, p in parts.items() if re.fullmatch(r"C\d+", p["LCSC"])}
    groups = {}
    for ref, p in smt.items():
        groups.setdefault((p["Value"], p["Footprint"].split(":")[-1], p["LCSC"]), []).append(ref)
    key = lambda r: (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r)))  # noqa: E731
    with open(os.path.join(fab, "bom-jlcpcb.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (val, fp, lcsc), refs in sorted(groups.items(), key=lambda g: key(sorted(g[1], key=key)[0])):
            w.writerow([val, ",".join(sorted(refs, key=key)), fp, lcsc])
    with open(os.path.join(fab, "a-souder-a-la-main.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Comment", "Footprint", "Note"])
        for ref in sorted(set(parts) - set(smt), key=key):
            w.writerow([ref, parts[ref]["Value"], parts[ref]["Footprint"].split(":")[-1], parts[ref]["LCSC"]])

    raw = os.path.join(fab, "pos-kicad.csv")
    run(cli, "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "front", "-o", raw, pcb)
    rows = [r for r in csv.DictReader(open(raw, encoding="utf-8")) if r["Ref"] in smt]
    os.remove(raw)
    missing = sorted(set(smt) - {r["Ref"] for r in rows}, key=key)
    if missing:
        sys.exit("composants à assembler absents du fichier de placement : %s" % missing)
    with open(os.path.join(fab, "cpl-jlcpcb.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in sorted(rows, key=lambda r: key(r["Ref"])):
            rot = (float(r["Rot"]) + JLC_ROTATION.get(smt[r["Ref"]]["LCSC"], 0)) % 360
            w.writerow([r["Ref"], r["PosX"] + "mm", r["PosY"] + "mm", "Top", "%g" % rot])
    print("ok : %d fichiers Gerber et perçage, %d lignes de BOM (%d composants assemblés), %d à souder à la main"
          % (len(os.listdir(ger)), len(groups), len(smt), len(parts) - len(smt)))


if __name__ == "__main__":
    main(*sys.argv[1:])
