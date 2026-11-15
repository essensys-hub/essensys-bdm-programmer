## 1. Carte de diagnostic BP (#3)

- [x] 1.1 Vérifier le stock et les références LCSC (FX2, hub, écrêteurs, embases) et figer la nomenclature
- [ ] 1.2 Dessiner le schéma KiCad dans `hardware/carte-diagnostic-bp/` : USB-C et hub, module Pico, FX2, port J33, port I2C protégé
- [ ] 1.3 Écrire `check_netlist.py` et son test `NR-bdm-programmer-67` (brochage J33, broche 1 non connectée, +3V3S sans chemin d'alimentation)
- [ ] 1.4 Dimensionner et simuler la protection 15 V du port I2C, dans les deux polarités
- [ ] 1.5 Router la carte (2 couches), ERC et DRC à 0 avec les règles JLCPCB
- [ ] 1.6 Générer Gerber, BOM et CPL en CI et les contrôler dans l'outil de commande JLCPCB
- [ ] 1.7 Valider sur banc : énumération USB, sauvegarde BDM par la nappe, capture I2C comparée à l'analyseur externe, essai 15 V sur alimentation de laboratoire, puis `/checkup`

## 2. Documentation (essensys-doc#43)

- [ ] 2.1 Rédiger le guide de branchement, de commande JLCPCB et les précautions dans `essensys-doc` (`docs/debug`)

## 3. Mémoire du projet (essensys-memory#41)

- [ ] 3.1 Consigner le change dans `essensys-memory` et ses liens avec les changes 2026-07-037 et 2026-07-038
