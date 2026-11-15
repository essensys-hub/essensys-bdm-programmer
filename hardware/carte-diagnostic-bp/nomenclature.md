# Nomenclature de la carte de diagnostic BP

Références relevées le 2026-11-15 dans l'index public du catalogue JLCPCB (`jlcsearch.tscircuit.com`). Stock et prix unitaires indicatifs, en dollars, à reconfirmer dans l'outil de commande JLCPCB au moment de commander (tâche 1.8).

## Posés par JLCPCB (CMS, une face)

| Repère | Fonction | Référence | Boîtier | LCSC | Stock | Prix |
|---|---|---|---|---|---|---|
| U1 | Analyseur 8 voies | RP2040 | LQFN-56 7×7 | C2040 | 79 876 | 0,99 |
| U2 | Hub USB 2.0, 4 ports | CH334R | QSOP-16 | C4154405 | 18 116 | 0,56 |
| U3 | Régulateur 3,3 V de l'analyseur | AMS1117-3.3 | SOT-223 | C6186 (basic) | 1 439 007 | 0,20 |
| U4 | Tampon à trigger de Schmitt SDA/SCL | SN74LVC2G17DBVR | SOT-23-6 | C10429 | 128 769 | 0,33 |
| U5 | Protection ESD de l'USB | USBLC6-2SC6 | SOT-23-6 | C5261088 | 70 038 | 0,04 |
| U6 | Flash 16 Mbit de l'analyseur | W25Q16JVSSIQ | SOIC-8 208 mil | C131025 | 3 373 | 1,16 |
| Y1, Y2 | Quartz 12 MHz de l'analyseur et du hub | ABM8G-12.000MHZ-B4Y-T | 3225 | C276421 | 3 180 | 0,45 |
| D1, D2 | Écrêteurs 5,1 V de SDA et SCL | BZT52C5V1 | SOD-123 | C19077401 | 2 172 587 | 0,02 |
| F1 | Fusible réarmable de la masse du port I2C, 50 mA / 60 V | JK-nSMD005/60V | 1206 | C2830235 | 696 810 | 0,03 |
| D4 | Diode antiparallèle de la LED de défaut | 1N4148W | SOD-123 | C81598 | à relever | |
| J1 | USB-C 16 broches | KH-TYPE-C-16P | CMS | C709357 | 147 898 | 0,08 |
| R, C | Résistances et condensateurs 0603 | pièces « basic » | 0603 | à figer au schéma | | |

## Soudés à la main (absents de l'index ou traversants)

| Repère | Fonction | Référence | Source |
|---|---|---|---|
| A1 | Module Pico | Raspberry Pi Pico (pastilles crénelées) | stock du banc |
| J2 | Port BP vers J33 | Embase mâle 2×5, pas de 2,54 mm, à détrompeur (type DC3-10P droit) | à approvisionner |
| J3, J4 | Port de diagnostic I2C en passage | Würth 66200421122 | Farnell, comme la sonde |

## Coût

Environ 4 $ de composants par carte, hors PCB, assemblage et port. La puce FX2 (CY7C68013A-56LTXC, C14912, 10,68 $) a été écartée le 2026-11-15 au profit du RP2040.
