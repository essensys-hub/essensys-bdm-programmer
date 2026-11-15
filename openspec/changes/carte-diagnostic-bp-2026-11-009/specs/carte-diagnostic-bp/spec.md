## Purpose

Fournir une carte de banc unique qui donne accès au BDM du BP et à l'écoute passive du bus I2C BP↔BA par un seul port USB, sans risque pour les cartes en cas d'erreur de branchement.

## ADDED Requirements

### Requirement: Un seul port USB
La carte SHALL exposer le module Pico et l'analyseur logique 8 voies à l'ordinateur par un unique connecteur USB-C.

#### Scenario: Branchement au Mac
- **WHEN** la carte est reliée au Mac par un seul câble USB
- **THEN** le port série du Pico et l'analyseur reconnu par `sigrok-cli --scan` apparaissent tous les deux

### Requirement: Port BDM vers J33
La carte SHALL porter une embase 2×5 à détrompeur au brochage de J33 : DSCLK, DSI, DSO, BKPT, RESET, ALLPST et +3V3S reliés au Pico selon la feature `bdm-firmware-backup-2026-11-005`, broche 1 non connectée. La carte SHALL NOT fournir de courant à la broche +3V3S.

#### Scenario: Sauvegarde par la nappe
- **WHEN** la carte est reliée à J33 par une nappe IDC 10 broches et que `bdm-backup` est lancé
- **THEN** la sauvegarde aboutit comme avec le câblage sur fils volants

#### Scenario: Cible non alimentée
- **WHEN** la carte est alimentée par l'USB et que le BP est éteint
- **THEN** aucune tension n'apparaît sur la broche +3V3S du côté du BP

### Requirement: Écoute I2C passive en passage
La carte SHALL porter deux embases 4 broches identiques à J1/J2 des BA, reliées broche à broche, et SHALL observer SDA et SCL sans jamais les piloter.

#### Scenario: Capture du bus
- **WHEN** la carte est insérée entre le BP et un BA et qu'une capture est lancée
- **THEN** le décodeur produit les mêmes trames qu'avec l'analyseur externe actuel

#### Scenario: Carte non alimentée sur le bus
- **WHEN** la carte est insérée sur le bus sans câble USB
- **THEN** le bus fonctionne normalement

### Requirement: Tolérance aux erreurs de branchement
Chaque broche du port I2C SHALL supporter 15 V en continu, dans les deux polarités par rapport à toute autre broche, sans dommage pour la carte ni pour l'ordinateur.

#### Scenario: +15 V sur une broche de signal
- **WHEN** 15 V est appliqué sur SDA ou SCL depuis une alimentation de laboratoire
- **THEN** la carte fonctionne normalement une fois le branchement corrigé

#### Scenario: Connecteur inversé
- **WHEN** le 0 V et le +15 V sont inversés sur le port I2C
- **THEN** aucun composant n'est détruit et aucun courant de défaut ne passe par l'USB

### Requirement: Dossier de fabrication vérifié
Le dépôt SHALL contenir le projet KiCad et SHALL produire en CI les fichiers Gerber, BOM et CPL au format JLCPCB, après ERC, DRC et contrôle des nets sans erreur.

#### Scenario: Erreur de schéma
- **WHEN** un net attendu manque ou l'ERC ou le DRC signale une erreur
- **THEN** la CI échoue et aucun dossier de fabrication n'est publié
