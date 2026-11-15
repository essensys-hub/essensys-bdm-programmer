## Why

La sauvegarde BDM du BP (feature `bdm-firmware-backup-2026-11-005`) et l'espion I2C du bus BP↔BA (feature `i2c-ba-sniffer-2026-10-009`) se montent aujourd'hui sur fils volants, avec deux câbles USB et un analyseur externe. Une erreur de branchement peut amener le +15 V du bus sur une entrée 3,3 V. Une carte unique, fabriquée en série courte, rend le banc reproductible et sûr.

Ticket : essensys-hub/essensys-feature-lifecycle#67.

## What Changes

- Nouvelle carte « diagnostic BP », conçue sous KiCad dans `hardware/carte-diagnostic-bp/`, fabriquée et assemblée (CMS) par JLCPCB.
- Un seul port USB-C : un hub embarqué relie le module Pico et un analyseur logique 8 voies (puce FX2, `fx2lafw`).
- Port BP : embase 2×5 à détrompeur pour une nappe IDC 10 broches vers J33, au brochage de la feature 005.
- Port de diagnostic I2C : deux embases Würth 4 broches en passage, écoute passive, chaque broche tolérant 15 V dans tous les sens de branchement.
- Génération des fichiers de fabrication (Gerber, BOM, CPL) et contrôles ERC, DRC et nets en CI.
- Aucun changement du firmware Pico ni de `bdm-backup` : le chemin reste en lecture seule.

## Capabilities

### New Capabilities
- `carte-diagnostic-bp` : carte matérielle réunissant l'accès BDM au BP, l'écoute passive du bus I2C et un analyseur 8 voies derrière un seul USB, avec ses protections et ses fichiers de fabrication.

### Modified Capabilities

Aucune.

## Impact

- Dépôt `essensys-bdm-programmer` : nouveau dossier `hardware/carte-diagnostic-bp/`, scripts de contrôle et job CI KiCad.
- `essensys-doc` : guide de branchement et de commande dans `docs/debug`.
- `essensys-memory` : consignation et lien avec les changes 2026-07-037 et 2026-07-038.
- Dépôt public : aucune adresse IP, aucun secret, aucune sauvegarde de firmware.
- Dépend du firmware Pico de la feature 005 pour la validation BDM.
