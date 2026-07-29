# Revue anti-brick adversariale — essensys-bdm-programmer

> Produite par l'agent V1 (`ruflo-core:reviewer`) du swarm `essensys-rpi4-bdm-programmer-2026-07-037`.
> Revue de code pure (aucune modification). Chaque verdict cite le fichier/ligne réel.
> À traiter comme prérequis avant d'implémenter les transports réels (USBDM / GPIO bit-bang).

## Verdict global

**Le POC n'est PAS sûr comme base pour un contact matériel en l'état** — mais tant que
les transports `usbdm`/`gpio` restent des stubs `NotImplementedError`, **aucun gap ne
peut bricker quoi que ce soit aujourd'hui**. Ces trous deviennent exploitables dès qu'un
transport réel est implémenté → prérequis des tâches « validation USBDM » (§2) et §1.6 de
`tasks.md`, pas du polish optionnel.

## Findings bloquants (avant tout branchement réel)

### B1 — Aucune vérification d'identité de cible (CSR/IDCODE)
`read_identity()` existe dans l'interface (`transport/base.py:17-24,67-69`) et est implémenté
par le mock, mais **n'est appelé nulle part** dans `src/`. `dump_info()` (`programmer.py:45-52`)
ne fait qu'un `read_memory` à adresse fixe — ne prouve pas que la puce est un MCF52259.
Exigé par `design.md:132,203` et `specs/flash-pipeline/spec.md:29-34,41-44`.
**Scénario** : pod mal câblé / mauvaise carte → `info→backup→erase→program` s'exécute sans
jamais détecter que la cible n'est pas la bonne. Omission d'implémentation (API déjà prête).

### B2 — Le backup-avant-write n'est pas lié à la cible physique
`require_verified_backup` (`interlocks.py:26-38`) vérifie seulement qu'un `BackupRecord` au
sha256 cohérent existe **sur disque** pour la chaîne `--serial` — jamais que ce backup
correspond à la carte réellement câblée. Démontré par `test_cli_process_boundary.py:50-76`
qui fait passer l'interlock avec **deux `MockTransport` indépendants**.
**Scénario** : `--backup-record backup-ANCIEN.json erase-app` sur une cible jamais sauvegardée
dans la session → erase/program s'exécutent. Mitigé en CI (chaque job refait un backup frais)
mais **c'est une convention d'usage, pas un invariant vérifié par le code**.

## Findings à traiter avant transports réels (non bloquants aujourd'hui)

- **V3 — `verify` non atomique avec `program`** : `program()` retourne sans relire ; `cli.py:65-67`
  affiche « program: OK » dès que `write_memory()` ne lève pas. Le verify n'existe que si
  l'appelant l'invoque séparément (le CI le fait ; la librairie ne l'impose pas).
- **V4 — « confirmation de reset » ne prouve rien** : `reset()` relit du flash statique déjà
  vérifié, ne prouve pas que le bootloader a validé le CRC et démarré l'app. Le PASS/FAIL du
  pipeline (`flash.yml` grep `"reset: OK"`) est donc trompeur (firmware qui plante au boot = PASS).
- **V5 — CRC : « injecté » ≠ « correct »** : `require_crc_injected` (`interlocks.py:71-81`) rejette
  seulement le placeholder littéral `0x0102` ; ne recompare jamais `crc16_modbus(zone)` au CRC
  stocké. (L'algo lui-même est correct, vérifié contre `0x4B37`.)
- **V7 — footgun `--transport mock`** : rien n'empêche `--transport mock` dans un
  `workflow_dispatch` sur `environment: hardware-flash` → faux « PASS » sans rien écrire.
  `flash.yml`/`rollback.yml` devraient refuser `inputs.transport == 'mock'`.

## Ce qui est solide

- Interlock CFM `0x400-0x417` (Security Word inclus, correction R1) — le point fort, bien testé,
  double protection par borne + par contenu (`srec.require_image_excludes_cfm`).
- Algo CRC-16/MODBUS correct, vérifié contre vecteur de référence + implémentation indépendante.
- Bornes zone app `0x3000-0x7DFFF` arithmétiquement correctes (pas d'off-by-one), tests bilatéraux.
- Workflows : fork-safety respectée (pas de `pull_request`), pas de secrets/contenu flash loggés.
- Transports non implémentés échouent proprement (`NotImplementedError`), aucun faux succès.
