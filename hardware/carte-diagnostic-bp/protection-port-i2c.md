# Protection du port de diagnostic I2C

Brochage des embases J3 et J4, identique à J1/J2 des BA : 1 SDA, 2 SCL, 3 0 V, 4 +15 V. Les quatre broches passent de J3 à J4 par des pistes directes. La carte ne prélève que SDA, SCL et la référence 0 V.

## Entrées SDA et SCL

Chaque ligne suit la chaîne : broche → 100 kΩ en série → Zener 5,1 V vers la masse (BZT52C5V1) → entrée du SN74LVC2G17 alimenté en 3,3 V.

| Cas | Courant dans la résistance | Tension à l'entrée du tampon | Puissance dans la résistance |
|---|---|---|---|
| Bus normal à 5 V | 0 (Zener bloquée) | 5 V, entrée tolérante 5,5 V | 0 |
| +15 V sur la broche | (15 − 5,1) / 100 k = 0,1 mA | 5,1 V nominal, 5,36 V au pire (±5 %) | 1 mW |
| −15 V sur la broche | (15 − 0,7) / 100 k = 0,14 mA | −0,7 V, sous les 50 mA admis par la diode d'entrée | 2 mW |
| Carte sans USB, bus actif | 0 | l'entrée LVC reste à haute impédance hors tension (Ioff) | 0 |

- Charge ajoutée au bus : 100 kΩ en série avec environ 15 pF, négligeable devant les tirages du bus.
- Retard : 100 kΩ × 15 pF ≈ 1,5 µs, identique sur SDA et SCL, contre une période d'horloge de 22 µs (44 kHz mesurés le 2026-10-14).
- L'écrêtage se fait vers la masse et non vers le 3,3 V : aucun courant n'est injecté dans l'alimentation, et la carte hors tension ne charge pas le bus.

## Référence 0 V (broche 3)

La masse de la carte, commune à l'USB du Mac et au BP par J33, rejoint la broche 3 par le fusible réarmable F1 (50 mA de maintien, 60 V). Si le +15 V se présente sur la broche 3, F1 limite puis coupe le courant de défaut, qui ne traverse ni l'USB ni la nappe J33 de façon durable. Une LED « erreur de branchement » entre la broche 3 et la masse, côté bus, signale le défaut.

## Broche 4 (+15 V)

Elle n'est reliée qu'à la piste de passage J3 ↔ J4. Aucun composant de la carte n'y est connecté.

## À vérifier sur banc (tâche 1.7)

- Fronts de SDA et SCL à l'oscilloscope, avec et sans la carte.
- Essai 15 V sur chaque broche, dans les deux polarités, sur alimentation de laboratoire limitée en courant. Jamais sur une armoire réelle.
- Temps de coupure de F1 et tenue de la piste de masse pendant le défaut.

Ces valeurs sont calculées, pas encore simulées ni mesurées.
