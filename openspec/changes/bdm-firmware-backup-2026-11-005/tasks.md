## 1. Firmware et outil de sauvegarde Pico (#1)

- [x] 1.1 Écrire le pilote BDM PIO et la liste blanche de commandes dans `firmware/pico/`
- [x] 1.2 Écrire le protocole USB série et son traitement des commandes refusées
- [x] 1.3 Écrire `PicoReadOnlyTransport` sans opération d'écriture
- [x] 1.4 Écrire `bdm-backup` : contrôles +3V3S et identité, double lecture, fichiers de sortie, rapport CFM
- [x] 1.5 Refuser un dossier de sortie non ignoré par Git et compléter `.gitignore`
- [x] 1.6 Écrire les tests unitaires avec transport simulé, dont le test d'absence d'écriture
- [ ] 1.7 Valider sur la carte de banc : deux sauvegardes identiques, BP relancé, puis `/checkup`

## 2. Documentation de la sauvegarde (essensys-doc#35)

- [ ] 2.1 Rédiger la procédure de sauvegarde et les précautions dans `essensys-doc`
- [ ] 2.2 Mettre à jour le guide Pico (GP26, JC1, emplacement de la broche 1)

## 3. Mémoire du projet (essensys-memory#36)

- [ ] 3.1 Consigner le change dans `essensys-memory` et sa relation avec `essensys-rpi4-bdm-programmer-2026-07-037`
