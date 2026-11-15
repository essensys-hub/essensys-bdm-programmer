# Nomenclature de la carte de diagnostic BP

Références relevées le 2026-11-15 dans l'index public du catalogue JLCPCB (`jlcsearch.tscircuit.com`). Stock et prix unitaires indicatifs, en dollars, à reconfirmer dans l'outil de commande JLCPCB au moment de commander (tâche 1.6).

## Posés par JLCPCB (CMS, une face)

| Repère | Fonction | Référence | Boîtier | LCSC | Stock | Prix |
|---|---|---|---|---|---|---|
| U1 | Analyseur 8 voies (FX2) | CY7C68013A-56LTXC | QFN-56 8×8 | C14912 | 1 725 | 10,68 |
| U2 | Hub USB 2.0, 4 ports | CH334P | QFN-16 3×3 | C5373042 | 28 614 | 0,46 |
| U3 | Régulateur 3,3 V du FX2 | AMS1117-3.3 | SOT-223 | C6186 (basic) | 1 439 007 | 0,20 |
| U4 | Tampon à trigger de Schmitt SDA/SCL | SN74LVC2G17DBVR | SOT-23-6 | C10429 | 128 769 | 0,33 |
| U5 | Protection ESD de l'USB | USBLC6-2SC6 | SOT-23-6 | C5261088 | 70 038 | 0,04 |
| U6 | EEPROM d'identification du FX2 (option, cavalier) | AT24C02 | SOP-8 | C688857 | 56 946 | 0,07 |
| Y1 | Quartz 24 MHz du FX2 | TXM24M0004322FBCDO00T | 3225 | C362340 | 110 262 | 0,07 |
| D1, D2 | Écrêteurs 5,1 V de SDA et SCL | BZT52C5V1 | SOD-123 | C19077401 | 2 172 587 | 0,02 |
| F1 | Fusible réarmable de la masse du port I2C, 50 mA / 60 V | JK-nSMD005/60V | 1206 | C2830235 | 696 810 | 0,03 |
| J1 | USB-C 16 broches | KH-TYPE-C-16P | CMS | C709357 | 147 898 | 0,08 |
| R, C | Résistances et condensateurs 0603 | pièces « basic » | 0603 | à figer au schéma | | |

## Soudés à la main (absents de l'index ou traversants)

| Repère | Fonction | Référence | Source |
|---|---|---|---|
| A1 | Module Pico | Raspberry Pi Pico (pastilles crénelées) | stock du banc |
| J2 | Port BP vers J33 | Embase mâle 2×5, pas de 2,54 mm, à détrompeur (type DC3-10P droit) | à approvisionner |
| J3, J4 | Port de diagnostic I2C en passage | Würth 66200421122 | Farnell, comme la sonde |

## Coût

La puce FX2 représente l'essentiel du coût des composants, soit environ 11 $ par carte sur un total voisin de 13 $ hors PCB, assemblage et port. Le repli prévu au `design.md`, un RP2040 nu (C2040, 0,99 $, 79 876 en stock), diviserait ce poste par dix mais demanderait de revalider le décodeur avec un autre pilote sigrok.
