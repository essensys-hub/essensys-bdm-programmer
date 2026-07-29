# R1 — Note de recherche : inconnues matérielles du programmeur BDM RPi4/SC944D

> Phase de recherche pure, read-only. Aucun matériel branché, aucune écriture. Chaque affirmation est sourcée ; ce qui n'a pas pu être vérifié est marqué **[À LEVER]**.

---

## 1. Brochage du connecteur J33 (barrette 2x5, "JTAG/BDM debug")

### Statut : **LEVÉ** — brochage complet obtenu par lecture directe du schéma Altium exporté en PDF.

**Source primaire** : `essensys-board-SC944D/Schematic PDF_[No Variations].pdf`, page **5/14** (feuille Altium `SDEC944-xD_Coeur`, cartouche "Coeur", case grille **A1-A2**). Le fichier `essensys-board-SC944D/docs/assets/SC944D_Schematic.pdf` est un **doublon binaire identique** (même 14 pages, même taille 2 406 571 octets) — même contenu, même page 5.

Méthode : extraction texte (`pdftotext -layout`) pour localiser la feuille contenant "J33", puis rendu visuel haute résolution de la page 5 (`pdftoppm`/`pdftocairo`) pour lecture directe du schéma (le `.SchDoc` Altium binaire, lui, reste illisible sans Altium — non utilisé).

**Brochage confirmé visuellement** (J33, connecteur `e2.54-D-L6`, 2 colonnes x 5 rangées) :

| Broche | Net Altium | Signal | Remarque |
|--------|-----------|--------|----------|
| 1 | `UC_TCLK` | TCLK | Horloge JTAG (TAP), voir §2 — rôle en mode BDM pur à confirmer (probablement câblé pour compat. mode JTAG/legacy pod, non essentiel au protocole BDM série 3 fils) |
| 2 | `UC_TMS/BKPT` | **BKPT** (en mode BDM) | Broche physique partagée TMS(JTAG)/BKPT(BDM), sélection par JTAG_EN |
| 3 | `UC_TDO/DSO` | **DSO** (en mode BDM) | Broche partagée TDO(JTAG)/DSO(BDM) |
| 4 | `UC_TDI/DSI` | **DSI** (en mode BDM) | Broche partagée TDI(JTAG)/DSI(BDM) |
| 5 | `UC_ALLPST` | ALLPST | Sortie "All Processor Status" = ET logique de PST[3:0], asserted quand le cœur est halted (signal de statut, cf. §2 RM 33.2) |
| 6 | `UC_TRST/DSCLK` | **DSCLK** (en mode BDM) | Broche partagée TRST(JTAG)/DSCLK(BDM) |
| 7 | `+3V3S` | VDD target (3.3V) | Alimentation cible / référence niveau logique — pas une alim fournie par le pod, sert au sense/référence |
| 8 | `UC_RESET` | RESET | Reset MCU |
| 9 | GND | GND | |
| 10 | GND | GND | |

Confirmation croisée par extraction texte brute (`pdftotext`) des mêmes libellés de net (`POUC0TCLK`, `POUC0TMS0B\K\P\T\`, `POUC0TDO0DSO`, `POUC0TDI0DSI`, `POUC0ALLPST`, `POUC0T\R\S\T\0DSCLK`, `POUC0R\E\S\E\T\`) — cohérent à 100% avec la lecture visuelle.

### Découverte critique associée : jumper **JC1** (sélecteur BDM/JTAG)

Sur la **même feuille** (page 5, en bas à gauche, zone jumper "JTAG_EN"), une note explicite indique :

> « Si 0 (JC1 monté) → BDM mode » / « Si 1 (JC1 non monté) → JTAG mode »

C'est le pin `JTAG_EN` du MCF52259 (cf. §2, RM chapitre 34) qui sélectionne, au niveau matériel, si les broches partagées de J33 se comportent en JTAG (TMS/TDI/TDO/TRST) ou en BDM (BKPT/DSI/DSO/DSCLK). **Condition préalable au câblage du pod** : vérifier/monter JC1 sur la carte cible pour être en mode BDM — sinon le pod BDM ne verra pas les bons signaux. **[À LEVER avant tout câblage]** : localisation physique de JC1 sur le PCB assemblé (repère visible sur `Assembly Drawings_[No Variations].pdf` ou en inspection visuelle de la carte — non fait ici, aucune carte manipulée).

### Reste à lever (mineur)

- Rôle exact de **TCLK (broche 1)** en mode BDM pur (le protocole BDM 3 fils DSCLK/DSI/DSO ne le requiert pas d'après le RM — cf. §2) : est-ce juste un câblage legacy compatible JTAG/pod P&E, ou le pod P&E historique l'utilise-t-il (ex. détection de présence de clock cible) ? À confirmer via la doc P&E Micro du connecteur 10 broches, ou par mesure passive (lecture seule, sans risque).
- Position physique de JC1 sur la carte assemblée — à vérifier visuellement sur une carte réelle ou sur `Assembly Drawings_[No Variations].pdf` avant le premier câblage.

---

## 2. Protocole / registres / timing BDM ColdFire V2 (MCF52259)

### Statut : **LEVÉ** — extrait directement du Reference Manual officiel NXP/Freescale, chapitre 33 "Debug Module".

**Source primaire** : `MCF52259 ColdFire® Integrated Microcontroller Reference Manual, Rev. 4` (NXP/Freescale, doc `MCF52259RM.pdf`). Le téléchargement direct sur `nxp.com` a échoué (404, anti-bot) ; le document complet (689 pages, 11 629 086 octets, PDF v1.6, non chiffré) a été récupéré via l'archive Wayback Machine (`web.archive.org/web/20251109060223/https://www.nxp.com/docs/en/reference-manual/MCF52259RM.pdf`), en deux requêtes `Range` HTTP concaténées (la CDN plafonnait chaque requête à 5 Mo). Fichier vérifié valide par `pdfinfo`/`pdftotext`. **Chapitre 33 "Debug Module"**, sections 33.1 à 33.4.6 ; **Chapitre 34 "IEEE 1149.1 Test Access Port (JTAG)"** ; **Chapitre 18 "ColdFire Flash Module (CFM)"** pour la sécurité flash.

#### 2.1 Signaux (RM §33.2, Table 33-2 ; §2.18, Table 2-17)

| Signal | Rôle | Détail |
|--------|------|--------|
| **DSCLK** | Horloge série de dev. (entrée) | Synchronisée en interne (validée si stable 2 cycles consécutifs de l'horloge bus). **Fréquence max = 1/5 de PSTCLK**. Sur le front montant synchronisé de DSCLK : DSI est échantillonné, DSO change d'état. |
| **DSI** | Entrée série de dev. | Échantillonné après que DSCLK a été vu haut. |
| **DSO** | Sortie série de dev. | Enregistrée en interne, retardée par rapport à la validation de DSCLK haut. |
| **BKPT** | Requête de breakpoint manuel (entrée) | Halt après l'instruction en cours ; statut reflété sur PST[3:0] = 0xF. Cas spécial : si BKPT est asserté dans les 8 cycles après négation de RESET → entrée en mode emulation (seule fenêtre pour CSR[EMU]). |
| **PSTCLK** | Horloge de sortie (dérivée de l'horloge processeur) | Toutes les transitions du protocole BDM série sont cadencées sur le front montant de **PSTCLK**, pas TCLK. |
| **ALLPST** | ET logique de PST[3:0] | Assertée quand le cœur est halted — confirme le libellé J33 pin5. |
| **PST[3:0] / DDATA[3:0]** | Trace temps réel | Non implémentés sur les boîtiers <100 broches (non présents sur J33 10 broches). |

#### 2.2 Protocole série BDM (RM §33.4.1.2 "BDM Serial Interface")

- Mode **full-duplex synchrone**, maître = système de développement (**doit générer DSCLK**), esclave = MCU.
- Paquet = **17 bits** (1 bit statut/contrôle + 16 bits data), **MSB first**.
- Fréquence : **DC à PSTCLK/5**.
- Séquence par bit (5 cycles PSTCLK, cf. Fig. 33-12) : C0 = état DSI posé, C1/C2 = double synchronisation DSI (DSCLK haut), C3 = la machine à états change, C4 = DSO change. **DSCLK doit être échantillonné bas entre chaque échange de bit.**
- Réponse "not-ready" (S=1, data=0x0000) : le module peut accepter un nouveau transfert après **32 cycles processeur**.

#### 2.3 Format des trames (RM §33.4.1.3)

- **Réception (MCU→hôte)** : 16 bits data + 1 bit statut S. `S=0/data=xxxx` → transfert valide ; `S=0/data=FFFF` → Status OK ; `S=1/data=0000` → not ready ; `S=1/data=0001` → bus error ; `S=1/data=FFFF` → commande illégale.
- **Commande (hôte→MCU)** : mot d'opération 16 bits + mots d'extension optionnels. Champs : `Operation[15:10]`, `R/W[8]` (0=write, 1=read), `Op Size[7:6]` (00=byte,01=word,10=longword), `A/D[3]`, `Register[2:0]`.
- Adresses en **absolu 32 bits** (2 mots d'extension), MSW first.

#### 2.4 Jeu de commandes BDM (RM §33.4.1.5, Table 33-20) — **essentiel pour backup/flash/verify**

| Commande | Mnémonique | Opcode (hex) | État CPU requis | Usage pipeline |
|----------|-----------|---------------|------------------|-----------------|
| Read memory | **READ** | `0x1900` (byte) / `0x1940` (word) / `0x1980` (long) | Steal (pas besoin halt) | **Backup 512 KB** (lecture flash) |
| Write memory | **WRITE** | `0x1800` (byte) / `0x1840` (word) / `0x1880` (long) | Steal | **Programmation flash** |
| Dump block | **DUMP** | `0x1D00/1D40/1D80` | Steal | Lecture blocs grande taille après READ initial |
| Fill block | **FILL** | `0x1C00/1C40/1C80` | Steal | Écriture blocs grande taille après WRITE initial |
| Resume | **GO** | `0x0C00` | Halted | Reprise après programmation |
| Read A/D register | RAREG/RDREG | `0x218{A/D,Reg}` | Halted | Lecture PC/SP/registres (identité, vérif CPU halted) |
| Write A/D register | WAREG/WDREG | `0x208{A/D,Reg}` | Halted | Ex. positionner PC |
| No-op | NOP | `0x0000` | Parallel | Test de canal |
| Read/Write debug module reg | RDMREG/WDMREG | `0x2D{...}` / `0x2C{...}` | Parallel | Accès CSR (Configuration/Status Register), IDCODE-like |

Note : **READ/WRITE/DUMP/FILL fonctionnent en "Steal" (bus cycles volés, pas besoin d'un CPU halted)** — le CPU peut donc théoriquement tourner pendant une lecture, mais pour un **backup recovery-grade et un flash write sûrs, le halt (BKPT) reste la pratique recommandée** pour éviter toute race avec le firmware en cours d'exécution (cohérent avec E6/E11 du prompt).

#### 2.5 Entrée en BDM / halt (RM §33.4.1.1)

Le CPU peut être halté par : (1) fault-on-fault catastrophique, (2) trigger de breakpoint matériel, (3) instruction HALT, (4) **assertion du pin BKPT** (méthode utilisée par un pod externe). Cas spécial pertinent pour un **premier accès / recovery** : si BKPT est asserté dans les 8 cycles après négation de RESET, le CPU entre en halt et **tous les registres/mémoire sont accessibles** dès ce point — c'est le point d'entrée standard pour un backup avant tout démarrage du firmware.

#### 2.6 Sécurité flash CFM — **correction importante par rapport au prompt §0**

Le prompt (fait vérifié §0) indique : *"CFM (sécurité flash) : Flash Configuration Field @ 0x400–0x40F (verrou possible si mal écrit) — à confirmer sur RM NXP"*. **Le RM confirme le risque mais précise/élargit la plage exacte** (RM Chapitre 18.3.1, Table 18-1, "CFM Configuration Field") :

| Offset (depuis PROGRAM_ARRAY_BASE) | Taille | Contenu | Défaut usine |
|---|---|---|---|
| `0x400–0x407` | 8 o | Backdoor Comparison Key | `0xFFFFFFFF_FFFFFFFF` |
| `0x408–0x40B` | 4 o | Flash Protection Bytes (CFMPROT) | `0xFFFFFFFF` |
| `0x40C–0x40F` | 4 o | Flash SUPV Access Bytes (CFMSACC) | `0xFFFFFFFF` |
| `0x410–0x413` | 4 o | Flash DATA Access Bytes (CFMDACC) | `0xFFFFFFFF` |
| `0x414–0x417` | 4 o | **Flash Security Word (CFMSEC)** | `0xFFFFFFFF` |

**Le champ complet fait 24 octets, `0x400` à `0x417`, PAS `0x400–0x40F` comme indiqué dans le prompt** — le mot le plus critique, le **Security Word (CFMSEC) qui contrôle le verrouillage BDM, est à `0x414–0x417`, donc en dehors de la plage `0x400–0x40F`** citée dans le fait vérifié initial. RM §18.4.3 (citation directe) : *« **Enabling flash security disables BDM communications.** »* Un déverrouillage est possible a posteriori (backdoor key sequence §18.4.3.1, blank check §18.4.3.2, JTAG lockout recovery §18.4.3.3) mais complexe et risqué. **Recommandation à intégrer dans `specs/bdm-programmer/spec.md`** : interlock logiciel bloquant toute écriture dans la plage **`0x400–0x417`** (pas seulement `0x40F`), sauf procédure explicite et documentée.

### Reste à lever

- Table 18-7 (codes exacts SEC[1:0] "secure" vs "unsecure") — non extraite dans cette passe (non nécessaire pour l'interlock : bloquer toute écriture dans `0x400-0x417` suffit en MVP, cf. E5/E12).
- Détail des adresses/registres CSR (Configuration/Status Register, RM §33.3.2) pour lire un "identifiant MCU" fiable via BDM (le prompt mentionne "IDCODE/CSR" en §3.1) — la section existe dans le RM (33.3.2, `33-5`) mais n'a pas été extraite dans cette passe ; à faire en phase design (C1) si un identifiant de sécurité anti-mauvaise-cible est requis avant flash.

---

## 3. Faisabilité USBDM CLI sur Raspberry Pi OS 64-bit (ARM64)

### Statut : **PARTIELLEMENT LEVÉ** — support ColdFire V2 et existence d'outils CLI confirmés, **support ARM64/RPi NON confirmé nulle part** (absence de preuve = à traiter comme un risque, pas une conclusion positive).

**Sources** :
- `usbdm.sourceforge.io/USBDM_V4.12/...` (documentation officielle USBDM, projet de P. O'Donoghue)
- `github.com/podonoghue/usbdm` (dépôt de submodules : `usbdm-eclipse-makefiles-build`, `usbdm-eclipse-plugins`, `usbdm-firmware`, `usbdm-flash-routines`, `usbdm-hcs08`, `usbdm-kinetis`, `usbdm-legacy-flash-routines`)
- Recherche web PEmicro (pemicro.com) pour comparaison avec l'alternative propriétaire.

**Ce qui est confirmé** :
1. **USBDM supporte ColdFire V1, V2, V3, V4** (documentation USBDM, page `index.html` : "Supports HCS12, HCS08, RS08 & Coldfire V1" et variantes JS16 "Supports Coldfire V2,3,4, Kinetis (via JTAG) and DSC"). Compatible avec la cible MCF52259 (V2).
2. **Un programmeur en ligne de commande existe**, distinct du plugin Eclipse : "A set of stand-alone programmers are also provided" — mais le contenu exact (dépendances GUI ou non) n'a pas pu être vérifié en détail (page `what_is_provided.html` peu explicite sur ce point précis).
3. **Build depuis les sources possible en ligne de commande** (`make -f MakeAll.mk all`, doc `building_software_page.html`), **mais dépendances lourdes coté GUI** : wxWidgets, TCL, Xerces-C (XML), Java SDK (plugin Eclipse), CodeWarrior 10.x (firmware du pod). wxWidgets suggère que l'exécutable principal de programmation est **une appli GUI**, pas un CLI headless pur.
4. **Distribution binaire officielle Linux = paquets Debian pour i386/amd64 uniquement** (version 4.10.6 : "Ubuntu 32-bit (i386) et 64-bit (amd64)"). **Aucune mention d'ARM, ARM64, aarch64 ou Raspberry Pi dans toute la documentation consultée** (recherches multiples, dépôt GitHub, pages de build) — absence totale, pas juste omission mineure.
5. **PEmicro (alternative propriétaire)** propose `CPROGCFZ`/`CPROGCFV1` (programmeurs BDM ColdFire en ligne de commande), confirmés existants, mais **aucune indication Linux ARM** dans la documentation publique ; PEmicro cible historiquement Windows/parallel port/USB x86. Probable **non portable sans effort significatif** (binaires fermés).
6. **Alternative académique** : projet **"bdm"** (CVUT/W. Eric Norum/Chris Johns/Pavel Pisa, `cmp.felk.cvut.cz/~pisa/m683xx/bdm_driver.html`) — pilote Linux + patch GDB pour BDM CPU32/ColdFire (5206/5206e/5207, générations V2 antérieures au MCF5225x) **mais cible exclusivement le port parallèle** (absent sur RPi4) et le protocole documenté (commandes READ/WRITE/GO en 17 bits MSB-first, un peu différentes en encodage mais structurellement proches — cohérent avec le RM officiel §2.2-2.4 ci-dessus). Ce pilote n'est **pas directement réutilisable tel quel** sur GPIO RPi4 (nécessiterait un portage bit-bang du protocole parallel-port vers GPIO, ce qui est exactement la Piste 2 "DIY").

### Facteur décisif pour Piste 1 vs Piste 2

Le protocole officiel (RM §33.4.1.2, ci-dessus §2.2) impose : **DSCLK max = PSTCLK/5** (à 80 MHz cœur, PSTCLK est proche de l'horloge cœur → plusieurs MHz de marge théorique, mais la contrainte réelle est la **synchronisation stricte 2-cycles + échantillonnage MSB-first sans jitter**, sur un bus temps réel). Un bit-bang GPIO Linux non-RT (E7 du prompt) devra soit :
- tourner largement en dessous de la fréquence max (facile, le protocole tolère DC → très bas débit acceptable, donc le risque n'est pas "trop lent" mais **jitter/latence imprévisible du noyau Linux standard qui casse le respect du timing inter-bit et le délai de réponse "not ready" (32 cycles processeur, très court en absolu — de l'ordre de la centaine de ns à 80 MHz)** ;
- ou déporter le bit-bang sur un co-processeur déterministe (RP2040/Pico en pont SPI↔BDM, PIO du RP2040 étant idéal pour ce genre de protocole synchrone bit-level) — mitigation déjà identifiée dans le prompt (E7).

### Recommandation

**Piste 1 (pod USBDM/P&E) reste recommandée pour le MVP**, mais avec un bémol factuel à faire remonter en `design.md` : **aucun support ARM64/RPi officiel n'a été trouvé pour USBDM ni pour les outils PEmicro** — la faisabilité du "Pi4 exécute les utilitaires USBDM CLI" n'est **pas validée**, seulement plausible (code C/C++ + libusb, portable en théorie). Ceci implique une **tâche de validation technique dédiée en phase C2/POC** avant de committer sur cette piste : soit (a) compiler USBDM depuis les sources sur Raspberry Pi OS 64-bit et vérifier qu'un exécutable non-GUI de programmation fonctionne réellement, soit (b) accepter qu'un exécutable GUI (wxWidgets) tourne en mode "headless" via un script d'automatisation (moins propre pour un pipeline CI non-interactif), soit (c) basculer vers un firmware de pod alternatif dont le protocole USB est documenté et ré-implémentable en un client CLI natif ARM64 (ex. reverse d'un pod TBLCF/OSBDM déjà bien documenté par la communauté, mais alors on se rapproche du "NIH" que le prompt veut éviter).

La **Piste 2 (bit-bang GPIO, éventuellement via RP2040 en pont)** reste documentée comme alternative "full-DIY" Phase 2, cohérente avec le prompt — le protocole exact nécessaire (§2 ci-dessus) est maintenant totalement sourcé pour l'implémenter si besoin, contrairement à Piste 1 dont la faisabilité logicielle sur ARM64 est encore un **[À LEVER — test POC requis]**.

### Reste à lever

- **[BLOQUANT POC]** Test réel : `git clone` + build `usbdm-eclipse-makefiles-build` (ou équivalent) sur un Raspberry Pi OS 64-bit à blanc (sans cible branchée, juste vérifier que ça compile et qu'un exécutable CLI de flash existe et s'exécute) — pas fait ici (recherche uniquement, aucune machine/carte manipulée, hors mandat R1 qui est read-only).
- Vérifier si une communauté (forums NXP, USBDM SourceForge tickets) rapporte un usage RPi/ARM — recherches web n'ont rien remonté de positif ni négatif explicite ; silence de la documentation, pas une confirmation d'impossibilité.
- Comparer l'effort de portage USBDM-CLI-ARM64 vs implémentation native d'un client BDM minimal en Python/C sur GPIO RPi4 en s'appuyant directement sur le protocole RM §2 ci-dessus (les deux options restent ouvertes pour `design.md`).

---

## Sources consultées (récapitulatif)

| # | Document | Emplacement / URL | Utilisé pour |
|---|----------|-------------------|---------------|
| 1 | `Schematic PDF_[No Variations].pdf` (page 5, feuille Coeur) | `essensys-board-SC944D/Schematic PDF_[No Variations].pdf` | Brochage J33 + jumper JC1 |
| 2 | `SC944D_Schematic.pdf` (identique) | `essensys-board-SC944D/docs/assets/SC944D_Schematic.pdf` | Doublon de confirmation |
| 3 | `hardware-sc944d.md` | `essensys-doc/archi/hardware-sc944d.md` | Table connecteurs (fait initial J33) |
| 4 | `legacy-client-deployment.md` | `essensys-doc/archi/legacy-client-deployment.md` | Contexte bootloader/CRC/JTAG-BDM historique |
| 5 | MCF52259 ColdFire Reference Manual, Rev. 4 | NXP (via archive Wayback : `web.archive.org/web/20251109060223/https://www.nxp.com/docs/en/reference-manual/MCF52259RM.pdf`) | Protocole BDM (Ch. 33), JTAG (Ch. 34), CFM/sécurité flash (Ch. 18) |
| 6 | ColdFire Family Programmer's Reference Manual (CFPRM) | `nxp.com/docs/en/reference-manual/CFPRM.pdf` (mirroir SLAC utilisé) | ISA générale ColdFire (pas de détail BDM chip-level — confirmé hors périmètre de ce doc) |
| 7 | USBDM documentation | `usbdm.sourceforge.io/USBDM_V4.12/...` (`index.html`, `what_is_provided.html`, `building_software_page.html`) | Support ColdFire V2, absence ARM64, dépendances build |
| 8 | Dépôt USBDM | `github.com/podonoghue/usbdm` | Structure des submodules |
| 9 | Driver BDM CPU32/ColdFire (CVUT) | `cmp.felk.cvut.cz/~pisa/m683xx/bdm_driver.html` | Protocole BDM générique parallel-port (comparatif) |
| 10 | PEmicro CPROGCFZ | Recherche web (pemicro.com, kanda.com) | Alternative propriétaire, absence Linux ARM |

---

## Résumé (5 lignes)

Le brochage J33 est **entièrement levé** par lecture directe du PDF schématique (page 5, feuille Coeur) : 1=TCLK, 2=BKPT, 3=DSO, 4=DSI, 5=ALLPST, 6=DSCLK, 7=+3V3S(sense), 8=RESET, 9-10=GND — avec la découverte critique d'un jumper **JC1** à vérifier/monter pour activer le mode BDM (sinon le connecteur est en mode JTAG). Le protocole BDM (signaux, timing DSCLK≤PSTCLK/5, format des trames 17 bits, commandes READ/WRITE/GO avec leurs opcodes exacts) est **entièrement sourcé** depuis le Reference Manual officiel NXP (chapitre 33), avec une **correction importante** : le champ de sécurité flash CFM s'étend en réalité de `0x400` à `0x417` (pas `0x40F`), le Security Word critique étant à `0x414-0x417`. La faisabilité USBDM CLI sur Raspberry Pi OS 64-bit **reste non validée** : ColdFire V2 est supporté par USBDM mais aucune distribution ni documentation ne mentionne ARM64/RPi (paquets officiels i386/amd64 seulement) — un POC de build doit trancher avant d'investir dans la Piste 1. Recommandation : conserver **Piste 1 (pod USBDM/P&E) comme option MVP par défaut** mais l'assortir d'une tâche de validation ARM64 explicite dans `tasks.md`, la Piste 2 (bit-bang GPIO, possiblement via co-processeur RP2040) restant une alternative crédible et maintenant bien documentée protocolairement si Piste 1 échoue.

Crop du schéma J33 ayant servi à la lecture : `./assets/j33-schematic-crop.png`

> Note : ce document a été produit par l'agent R1 (`ruflo-core:researcher`) du swarm
> `essensys-rpi4-bdm-programmer-2026-07-037`, puis déplacé du scratchpad de session
> vers ce repo pour pérennisation.
