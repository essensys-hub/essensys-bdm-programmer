## Context

Le Pico parle BDM sur J33 (2×5, pas de 2,54 mm) : DSCLK GP2, DSI GP3, DSO GP4, BKPT GP5, RESET GP6 en collecteur ouvert, ALLPST GP7, +3V3S mesuré sur GP26, broche 1 (TCLK) non connectée, masse en 9 et 10. Le bus BP↔BA passe par des embases Würth 4 broches : 1 SDA, 2 SCL, 3 0 V, 4 +15 V. L'analyseur FX2 externe (`fx2lafw`, 24 MHz) est déjà validé avec le décodeur de `essensys-i2c-ba-sniffer` ; il sert de référence pour valider l'analyseur de la carte.

## Goals / Non-Goals

**Goals:**
- Une carte, un câble USB, deux fonctions : BDM et écoute I2C.
- Aucun dommage si le connecteur I2C est mal câblé ou si le +15 V arrive sur une broche de signal.
- Dossier de fabrication accepté tel quel par JLCPCB (PCB et assemblage CMS).

**Non-Goals:**
- Écrire dans la flash du BP ou reflasher un BA (pas d'ICSP).
- Émettre sur le bus I2C.
- Alimenter le BP ou les BA depuis la carte.

## Decisions

- **Hub USB 2.0 embarqué (type CH334) et USB-C unique.** Le Pico BDM et l'analyseur restent deux périphériques USB indépendants. Alternative écartée : un seul microcontrôleur pour les deux fonctions, qui lierait le firmware BDM en lecture seule à celui de l'analyseur.
- **Analyseur : RP2040 nu, flash W25Q16 et quartz 12 MHz**, choisi le 2026-11-15 par le mainteneur à la place de la puce FX2 (0,99 $ contre 10,68 $). Firmware `sigrok-pico`, pilote libsigrok `raspberrypi-pico`. Voies D0 = SCL, D1 = SDA, D2 à D7 = DSCLK, DSI, DSO, BKPT, RESET, ALLPST, sur GP2 à GP9 de l'analyseur. Bouton BOOTSEL et points de test SWD pour le premier chargement du firmware.
- **Module Pico soudé (pastilles crénelées)**, pas de puce nue : firmware de la feature 005 inchangé, remplacement possible.
- **Port J33 : embase 2×5 à détrompeur.** Résistances série sur chaque signal, broche 1 non connectée, +3V3S relié à GP26 par un pont diviseur à haute impédance, sans aucun chemin d'alimentation vers la cible.
- **Port I2C tolérant 15 V.** SDA et SCL passent par une résistance série puis un écrêteur vers 3,3 V et un tampon à trigger de Schmitt (SN74LVC2G17). La résistance est dimensionnée pour que 15 V permanents, ou une inversion (−15 V), restent dans les limites de l'écrêteur. Le +15 V et le 0 V traversent de J1 vers J2 par des pistes dédiées ; le +15 V n'est relié à rien d'autre. La masse de mesure rejoint la broche 3 par un élément de protection, pour qu'une inversion 0 V / +15 V ne court-circuite pas le bus à travers l'USB.
- **Fabrication : 2 couches, 1,6 mm, pièces du catalogue LCSC**, CMS sur une seule face. Les embases et le module Pico peuvent rester en soudure manuelle si l'assemblage traversant renchérit trop.
- **Outillage : projet KiCad 10 versionné, ERC, DRC et export par `kicad-cli` en CI**, plus un contrôle des nets sur le modèle de `check_netlist.py` du dépôt sniffer.

## Risks / Trade-offs

- Le pilote `raspberrypi-pico` est absent de libsigrok 0.5.2, la version installée par Homebrew (vérifié le 2026-11-15 : seul `fx2lafw` est listé) → compiler libsigrok depuis les sources, ou écrire un firmware de capture propre lu directement par `essensys-i2c-sniff`. À trancher avant le routage, avec un Pico du commerce chargé de `sigrok-pico`.
- Le décodeur doit être revalidé avec le nouvel analyseur → comparer une même séquence avec l'analyseur FX2 externe.
- Capacité ajoutée sur SDA et SCL par la protection → mesurer les fronts sur banc et comparer à la sonde actuelle.
- Position de JC1 inconnue (BDM ou JTAG) → détection par l'identité, déjà prévue par `bdm-backup`.
- Boucle de masse entre le Mac et l'armoire → usage sur banc seulement, à documenter ; jamais sur une armoire réelle pendant les tests.
- Première série : prévoir des points de test et des cavaliers de coupure sur chaque signal.

## Open Questions

- Références LCSC définitives et coût de la série de 5 cartes.
- Assemblage des composants traversants par JLCPCB ou à la main.
