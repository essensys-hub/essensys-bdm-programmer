## Purpose

Permettre de lire et de sauvegarder le firmware du BP SC944D par BDM avec un Pico, sans aucune possibilité d'écrire dans la cible.

## ADDED Requirements

### Requirement: Chemin strictement en lecture seule
Le firmware Pico et la commande `bdm-backup` SHALL n'offrir aucune opération d'effacement ou d'écriture de la mémoire cible. Le firmware Pico SHALL n'émettre que les commandes BDM d'une liste blanche nécessaire à la lecture, à l'arrêt et à la relance du processeur.

#### Scenario: Commande non autorisée reçue par le Pico
- **WHEN** le Pico reçoit sur l'USB une commande hors de sa liste blanche
- **THEN** il répond par une erreur et n'émet rien sur le BDM

#### Scenario: Contrôle automatique du code
- **WHEN** la suite de tests s'exécute
- **THEN** elle échoue si le transport `pico` ou `bdm-backup` expose une opération d'écriture, ou si le firmware Pico contient un opcode BDM d'écriture mémoire

### Requirement: Contrôles avant lecture
L'outil SHALL vérifier la présence du +3V3S et l'identité du processeur MCF52259 avant toute lecture de flash, et SHALL s'arrêter sans lire en cas d'échec.

#### Scenario: Carte non alimentée
- **WHEN** le +3V3S est absent
- **THEN** l'outil s'arrête avec un message explicite, sans piloter RESET ni BKPT

#### Scenario: Identité inattendue
- **WHEN** l'identité lue n'est pas celle d'un MCF52259, par exemple si JC1 n'est pas monté
- **THEN** l'outil s'arrête et indique de vérifier JC1 et le câblage

### Requirement: Sauvegarde complète vérifiée
L'outil SHALL lire les 512 Ko de `0x0` à `0x7FFFF` deux fois, et SHALL ne déclarer la sauvegarde valide que si les deux SHA-256 sont identiques. Il SHALL produire un `.bin`, un `.s19`, un SHA-256 et des métadonnées contenant la version en `0x3002`, le CRC en `0x3000` et la date.

#### Scenario: Deux lectures identiques
- **WHEN** les deux lectures donnent le même SHA-256
- **THEN** les quatre fichiers sont écrits et la sauvegarde est déclarée valide

#### Scenario: Lectures différentes
- **WHEN** les deux SHA-256 diffèrent
- **THEN** l'outil signale l'échec et ne déclare aucune sauvegarde valide

### Requirement: Rapport sur la sécurité flash
L'outil SHALL lire la zone CFM `0x400`-`0x417` et SHALL indiquer dans le rapport l'état du Security Word `0x414`-`0x417`.

#### Scenario: Rapport produit
- **WHEN** une sauvegarde se termine
- **THEN** les métadonnées contiennent la valeur de la zone CFM et son interprétation

### Requirement: Remise en marche du processeur
L'outil SHALL arrêter le processeur pendant la lecture et SHALL le relancer ensuite, y compris après une erreur de lecture.

#### Scenario: Erreur pendant la lecture
- **WHEN** la lecture échoue après l'arrêt du processeur
- **THEN** l'outil tente la relance et indique son résultat

### Requirement: Sauvegardes hors du dépôt
Les fichiers de sauvegarde SHALL rester hors de Git et SHALL être écrits par défaut hors du dépôt.

#### Scenario: Dossier de sortie dans le dépôt
- **WHEN** le dossier de sortie est suivi par Git ou non ignoré
- **THEN** l'outil refuse d'écrire et demande un autre dossier
