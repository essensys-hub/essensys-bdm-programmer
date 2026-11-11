## Why

Le BP SC944D (MCF52259) n'a aucune sauvegarde fiable de son firmware : seul le pod P&E avec CodeWarrior accède à la flash. Ticket : https://github.com/essensys-hub/essensys-feature-lifecycle/issues/65. Un Raspberry Pi Pico câblé sur J33 permet de faire cette sauvegarde sans pod, à condition de ne prendre aucun risque d'écriture.

## What Changes

- Firmware Pico (PIO) qui parle BDM sur GP2 à GP8 et expose au Mac un protocole USB série limité aux opérations de lecture.
- Transport `pico` et commande dédiée `bdm-backup`, en lecture seule, distincte de `bdm-programmer`.
- Sauvegarde complète de 512 Ko : `.bin`, `.s19`, SHA-256, métadonnées, deux lectures comparées.
- Rapport sur la zone de sécurité CFM (`0x400`-`0x417`).
- Pas d'écriture : aucune commande d'effacement ou d'écriture n'existe sur ce chemin, et un test le vérifie.

## Capabilities

### New Capabilities
- `bdm-firmware-backup`: lecture et sauvegarde en lecture seule du firmware du BP via Pico et BDM.

### Modified Capabilities

## Impact

- `essensys-bdm-programmer` : `firmware/pico/`, `src/bdm_programmer/transport/pico_transport.py`, `src/bdm_programmer/backup_cli.py`, tests, `.gitignore`.
- `essensys-doc` : procédure de sauvegarde. `essensys-memory` : relation avec le change `essensys-rpi4-bdm-programmer-2026-07-037`.
- Aucun impact cloud, gateway, mobile ou déploiement. Le firmware du BP n'est pas modifié.
- Dépôt public : les sauvegardes restent hors Git, car la flash contient les données de la carte (`Tb_Echange` en `0x7E000`).
