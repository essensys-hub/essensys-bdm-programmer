# Carte de diagnostic BP

Carte de banc : accès BDM au BP (J33, nappe 10 broches), écoute passive du bus I2C BP↔BA et analyseur 8 voies, derrière un seul port USB-C.

Spécification : `openspec/changes/carte-diagnostic-bp-2026-11-009/`.

| Fichier | Rôle |
|---|---|
| `gen_sch.py` | Décrit le circuit (table broche → net) et génère `carte-diagnostic-bp.kicad_sch` |
| `carte-diagnostic-bp.kicad_sch` | Schéma KiCad 10, à ouvrir avec le projet `.kicad_pro` |
| `gen_pcb.py`, `route_pcb.py`, `close_gaps.py` | Placement, routage et finition de `carte-diagnostic-bp.kicad_pcb` |
| `check_netlist.py` | Invariants de sécurité contrôlés sur la netlist exportée |
| `nomenclature.md` | Références LCSC, stock et prix relevés |
| `protection-port-i2c.md` | Calcul de la protection 15 V du port I2C |

## Régénérer et contrôler

    python3 hardware/carte-diagnostic-bp/gen_sch.py
    kicad-cli sch erc --severity-all --exit-code-violations hardware/carte-diagnostic-bp/carte-diagnostic-bp.kicad_sch
    pytest tests/test_carte_diagnostic_netlist.py

## Router la carte

    KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
    kicad-cli sch export netlist --format kicadsexpr -o /tmp/carte.net hardware/carte-diagnostic-bp/carte-diagnostic-bp.kicad_sch
    $KPY hardware/carte-diagnostic-bp/gen_pcb.py /tmp/carte.net            # empreintes, nets, placement, plans internes
    $KPY hardware/carte-diagnostic-bp/route_pcb.py freerouting-2.5.0.jar   # routage Freerouting, plans de masse externes
    $KPY hardware/carte-diagnostic-bp/close_gaps.py                        # ferme les dernières liaisons sous contrôle du DRC

Le routage automatique n'est pas reproductible à l'identique : `carte-diagnostic-bp.kicad_pcb` est versionné tel que routé, et la CI contrôle son DRC sans le régénérer.

## État

Carte de 100 × 60 mm, 4 couches, routée le 2026-11-15 : DRC à 0 violation et 0 liaison manquante, 301 pastilles conformes à la netlist du schéma. Les repères des petits composants (R, C, D, F) ne sont pas sérigraphiés.

Le routage sort d'un routeur automatique et **doit être relu avant toute commande** : paire USB non routée en différentiel, position du quartz, découplage. Les fichiers de fabrication JLCPCB ne sont pas générés.

Les pastilles TP2 et TP3 du module Pico sont sous le module : elles demandent de la pâte à braser et de l'air chaud, ou un perçage de la carte à ajouter.

À confirmer avant la commande :

- fiche technique du hub CH334R : quartz 12 MHz et broche `RESET/CDP` ;
- empreinte des embases I2C, à confronter au plan Würth 66200421122 (empreinte Micro-Fit 3.0 provisoire) ;
- empreinte du connecteur USB-C KH-TYPE-C-16P ;
- chaîne de capture RP2040 (tâche 1.2).

Le micro-USB du module Pico ne doit jamais être branché : son USB passe par les pastilles TP2 et TP3 vers le hub.
