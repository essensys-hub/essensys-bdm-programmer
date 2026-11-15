# Carte de diagnostic BP

Carte de banc : accès BDM au BP (J33, nappe 10 broches), écoute passive du bus I2C BP↔BA et analyseur 8 voies, derrière un seul port USB-C.

Spécification : `openspec/changes/carte-diagnostic-bp-2026-11-009/`.

| Fichier | Rôle |
|---|---|
| `gen_sch.py` | Décrit le circuit (table broche → net) et génère `carte-diagnostic-bp.kicad_sch` |
| `carte-diagnostic-bp.kicad_sch` | Schéma KiCad 10, à ouvrir avec le projet `.kicad_pro` |
| `check_netlist.py` | Invariants de sécurité contrôlés sur la netlist exportée |
| `nomenclature.md` | Références LCSC, stock et prix relevés |
| `protection-port-i2c.md` | Calcul de la protection 15 V du port I2C |

## Régénérer et contrôler

    python3 hardware/carte-diagnostic-bp/gen_sch.py
    kicad-cli sch erc --severity-all --exit-code-violations hardware/carte-diagnostic-bp/carte-diagnostic-bp.kicad_sch
    pytest tests/test_carte_diagnostic_netlist.py

## État

Schéma seulement : le routage, le DRC et les fichiers de fabrication JLCPCB ne sont pas faits. À confirmer avant le routage :

- fiche technique du hub CH334R : quartz 12 MHz et broche `RESET/CDP` ;
- empreinte des embases I2C, à confronter au plan Würth 66200421122 (empreinte Micro-Fit 3.0 provisoire) ;
- empreinte du connecteur USB-C KH-TYPE-C-16P ;
- chaîne de capture RP2040 (tâche 1.2).

Le micro-USB du module Pico ne doit jamais être branché : son USB passe par les pastilles TP2 et TP3 vers le hub.
