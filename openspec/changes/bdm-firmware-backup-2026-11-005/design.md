## Context

Le dépôt fournit déjà `backup.py`, une lecture vérifiée et un transport abstrait, mais son CLI `bdm-programmer` expose aussi `erase-app` et `program`, et aucun code Pico n'existe. Le Pico est sous MicroPython. Brochage J33 : DSCLK GP2, DSI GP3, DSO GP4, BKPT GP5, RESET GP6 (collecteur ouvert), ALLPST GP7, +3V3S sur GP26 ; TCLK non connecté.

## Goals / Non-Goals

**Goals:** une sauvegarde complète et vérifiée, sans chemin d'écriture, depuis un Mac.

**Non-Goals:** écriture ou effacement flash, intégration CI, prise en charge du Raspberry Pi 4 ou d'USBDM, sauvegarde de la flash SPI externe.

## Decisions

- **Commande séparée `bdm-backup`** plutôt qu'une option de `bdm-programmer` : les commandes d'écriture restent inaccessibles depuis ce chemin. Le code existant d'écriture n'est pas retiré, car il sert le change 2026-07-037. Le critère « aucune commande d'écriture » s'applique au chemin Pico.
- **Transport `PicoReadOnlyTransport` séparé de l'interface d'écriture** : il n'implémente ni `erase_range` ni `write_memory`. Si l'interface de base les impose, on en extrait une interface de lecture.
- **Liste blanche dans le firmware Pico** : la barrière d'écriture est du côté qui parle à la cible. Un bug côté Mac ne peut donc rien écrire.
- **MicroPython avec PIO** pour le premier jalon, chargé sans outillage C. Le passage en C reste possible si le débit est insuffisant.
- **Arrêt par BKPT** à la fin de RESET quand c'est possible, pour lire avant le démarrage du firmware.

## Risks / Trade-offs

- Le mode BDM dépend de JC1, dont la position n'est pas documentée → détection par l'identité, relevé sur la carte.
- La lecture d'identité ou l'arrêt écrivent éventuellement un registre de debug → seuls les registres de debug listés sont autorisés, jamais la mémoire ni le module CFM.
- Si le Security Word a verrouillé le BDM, la lecture échoue → rapporté, aucun contournement.
- Un RESET ou un arrêt interrompt le BP → sur carte de banc uniquement, jamais sur une armoire en service.
- Le débit MicroPython peut être faible → une lecture de 512 Ko reste acceptable pour un usage ponctuel, à mesurer.
