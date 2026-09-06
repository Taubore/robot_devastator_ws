# Connexions — Devastator

## A. Repères de numérotation

Deux systèmes de numérotation distincts coexistent sur le Raspberry Pi 4 et ne doivent pas être
confondus :

- **GPIO (BCM)** — numéro logique du signal dans le SoC BCM2711. C'est l'identifiant utilisé dans
  le code (bibliothèques GPIO, overlays de l'arbre de périphériques, paramètres ROS 2).
  Exemple : `GPIO14`.
- **Broche J8** — position physique de la broche sur l'embase 40 broches du Raspberry Pi 4,
  désignée J8. C'est ce que l'on regarde en câblant. Exemple : broche 8.

La correspondance entre les deux est figée sur le Raspberry Pi 4. La commande `pinout` sur le
Raspberry Pi affiche la correspondance de référence complète.

Le **Pico WH** utilise une convention différente : ses broches sont numérotées **GP0 à GP28**,
sans numérotation BCM. Les fiches des composantes raccordées au Pico WH utilisent donc une seule
colonne « GP » à la place des colonnes « GPIO (BCM) » et « Broche J8 ».

`GPIO18` à `GPIO21` du Raspberry Pi 4 sont réservés à l'interface I2S matérielle du BCM2711 :
aucun autre usage ne doit leur être affecté.

### Lecture des fiches

Chaque fiche décrit une composante : un en-tête (contrôleur hôte, interface ou bus, alimentation,
mode de raccordement physique, statut) puis un tableau de connexions. Dans ce tableau :

- **Broche composante** — repère de la broche tel qu'imprimé sur la composante externe ;
- **Signal** — fonction de la ligne ;
- **GPIO (BCM)** — identifiant utilisé dans le code, côté Raspberry Pi 4 ;
- **Broche J8** — position physique sur l'embase du Raspberry Pi 4 ;
- **GP** — broche du Pico WH (fiches Pico uniquement) ;
- **Couleur** — couleur du fil ;
- **Commentaire**.

Une correspondance incertaine est marquée **« à vérifier »** plutôt que devinée.

## B. Fiches par composante

### Liaison UART Raspberry Pi 4 ↔ Pico WH

- **Contrôleurs** : Raspberry Pi 4 et Pico WH (liaison entre les deux contrôleurs)
- **Interface** : UART0, série asynchrone, 115200 bd, commandes texte ASCII terminées par une fin
  de ligne
- **Alimentation** : sans objet (lignes de signal). Le Pico WH est alimenté séparément via VSYS
  en fonctionnement autonome.
- **Mode de raccordement** : câblage croisé, une résistance série de 1 kΩ sur chaque ligne de
  données ; masse commune obligatoire.
- **Statut** : câblé, liaison validée sur `/dev/ttyS0`

Cette fiche relie deux contrôleurs : le tableau conserve donc à la fois les colonnes du
Raspberry Pi 4 (GPIO BCM, broche J8) et la colonne GP du Pico WH.

| Signal | GPIO (BCM) RPi4 | Broche J8 RPi4 | GP Pico | Couleur | Commentaire |
| --- | --- | --- | --- | --- | --- |
| RPi4 TX → Pico RX | GPIO14 (TXD) | 8 | GP1 | Jaune | Via résistance série 1 kΩ. Ligne critique : à déconnecter en développement du Pico par USB ; une TX active du Raspberry Pi perturbe le démarrage du Pico si le Pi 4 est déjà allumé. |
| Pico TX → RPi4 RX | GPIO15 (RXD) | 10 | GP0 | Vert | Via résistance série 1 kΩ. |
| Masse commune | GND | GND | GND | Noir | Masse commune UART, obligatoire. |

> Voir aussi `docs/parametres.md`, sections « Diagnostic validé sur la liaison UART » et « Règle
> de travail provisoire », pour les lignes sensibles au démarrage et les modes de travail
> USB / autonome.

### INA260 ×2 (capteurs d'alimentation)

- **Contrôleur hôte** : Raspberry Pi 4
- **Interface / bus** : I2C1 (`/dev/i2c-1`), lignes GPIO2/GPIO3, activé par `dtparam=i2c_arm=on`.
  Deux capteurs Adafruit INA260 câblés en parallèle sur le bus, aux adresses `0x40` et `0x41`.
- **Alimentation** : 3,3 V fournis par le rail logique (Pololu 4090), via le circuit
  d'alimentation maison — pas depuis l'embase J8. Aucune lecture n'est possible robot éteint.
- **Mode de raccordement** : chaque module est inséré en série (VIN+ / VIN-) sur le fil positif de
  la batterie qu'il surveille. Résistances de tirage I2C présentes sur les modules Adafruit.
- **Statut** : câblé, intégré et validé ; lu en permanence par le nœud `surveillance_alimentation`.

| Broche composante | Signal | GPIO (BCM) | Broche J8 | Couleur | Commentaire |
| --- | --- | --- | --- | --- | --- |
| SDA | I2C1 — données | GPIO2 (SDA1) | 3 | — | Ligne partagée par les deux INA260 ; tirage sur les modules Adafruit |
| SCL | I2C1 — horloge | GPIO3 (SCL1) | 5 | — | Ligne partagée par les deux INA260 |

Adresses et rails surveillés :

| Adresse | Rail surveillé | Batterie |
| --- | --- | --- |
| `0x40` | Logique | Pack Tenergy 7,2 V, 6 cellules NiMH |
| `0x41` | Moteur | Pack Melasta 6 V, 5 cellules NiMH |

- Vérification : `i2cdetect -y 1` doit montrer `40` et `41`.
- Lecture ROS 2 : nœud `surveillance_alimentation` (voir `src/surveillance_alimentation/README.md`).

### AUDIO_I2S (MAX98357 + PCM5102A)

- **Contrôleur hôte** : Raspberry Pi 4
- **Interface / bus** : I2S (PCM) matériel, activé par `dtparam=i2s=on` et
  `dtoverlay=hifiberry-dac`. Détecté comme carte ALSA.
- **Alimentation** : 5 V fournis par le rail logique (Pololu 4091), via le circuit d'alimentation maison 
- **Mode de raccordement** : sur breadboard avec condensateurs recommandés.
- **Statut** : câblé, sortie audio fonctionnelle.

| Broche composante | Signal | GPIO (BCM) | Broche J8 | Couleur | Commentaire |
| --- | --- | --- | --- | --- | --- |
| BCLK | I2S — horloge bit | GPIO18 | 12 | Blanc | GPIO réservé I2S (BCM2711) |
| LRC | I2S — sélection de voie (LRCLK) | GPIO19 | 35 | Bleu | GPIO réservé I2S (BCM2711) |
| DIN | I2S — données vers l'ampli | GPIO21 | 40 | Jaune | GPIO réservé I2S (BCM2711) |

Les connexions d'alimentation et de masse des modules audio ne sont pas documentées ici — à
compléter.

**Notes**

Activation logicielle : `dtparam=i2s=on`, `dtoverlay=hifiberry-dac`. Le HiFiBerry DAC est alors
détecté comme carte ALSA. Test fonctionnel Devastator :

```bash
aplay -D default ~/.cache/robot_devastator/audio/demarrage_01.wav
```

Diagnostic du « clac » à la lecture : le bruit observé à chaque lecture séparée vient probablement
de l'ouverture et de la fermeture du flux audio par `aplay` avec l'ampli I2S. Ce diagnostic ne
pointe pas vers le routage GPIO ni vers `dtparam=audremap`. Pistes futures : un pré-silence ou un
fade-in dans les WAV, un lecteur audio persistant, ou une solution matérielle anti-pop si le
besoin reste présent.

### CLAV_X8 (mini clavier USB sans-fil Rii X8)

- **Contrôleur hôte** : Raspberry Pi 4 ou Legion-Linux
- **Interface / bus** : USB (récepteur sans-fil sur un port USB)
- **Alimentation** : 5 V par le port USB
- **Mode de raccordement** : dongle USB
- **Statut** : câblé (connecté)

Aucun tableau de broches : la composante se connecte par un port USB standard du Raspberry Pi 4 ou 
sur PC (Legion-Linux)

Usage : permet de saisir du texte directement pour une téléopération simple pour des tests manuels.

### LCD2 (Waveshare 2" ST7789V)

- **Contrôleur hôte** : Raspberry Pi 4
- **Interface / bus** : SPI0, sélection de puce CE0 (GPIO8). Affichage en écriture seule.
- **Alimentation** : 3,3 V, branché directement au Raspberry Pi 4 (fil violet). Broche J8 1 
- **Mode de raccordement** : nappe Dupont femelle fournie avec le module, branchée directement sur
  les broches mâles du HAT du Raspberry Pi 4.
- **Statut** : câblé.

| Broche composante | Signal | GPIO (BCM) | Broche J8 | Couleur | Commentaire |
| --- | --- | --- | --- | --- | --- |
| 3V3 | Alimentation 3,3 V | — | 1 | Violet | Branché directement au Raspberry Pi 4 |
| GND | Masse | — | 6 | — | Broche J8 et couleur non renseignées dans la source |
| SCLK | SPI0 — horloge | GPIO11 (SCLK) | 23 | Orange | |
| DIN | SPI0 — données (MOSI ; « DIN » côté module) | GPIO10 (MOSI) | 19 | Vert | |
| CS | SPI0 — sélection de puce (CE0) | GPIO8 (CE0) | 24 | Jaune | |
| DC | Donnée / commande | GPIO25 | 22 | Bleu | |
| RST | Réinitialisation | GPIO24 | 18 | Brun | |
| BL | Rétroéclairage | GPIO12 (PWM0) | 32 | Gris | PWM0 matériel ; déplacé de sa position usuelle car GPIO18-21 sont réservés à l'interface I2S du BCM2711 |
| — | SPI0 — MISO | GPIO9 (MISO) | 21 | — | Inutilisé, le ST7789V étant en écriture seule |

### MDD3A (Cytron MDD3A)

- **Contrôleur hôte** : Pico WH
- **Interface / bus** : GPIO — 4 lignes PWM, deux par moteur (entrées A et B)
- **Alimentation** : entrées logiques pilotées par le Pico WH (3,3 V). Alimentation de puissance
  des moteurs par le rail moteur (batterie Melasta 6 V) via un fusible 10 A fast.
- **Mode de raccordement** : par l'entremise des borniers. La carte est fixée sur le chassis bas 
du robot.
- **Statut** : câblé, validé.

Le Pico WH utilise la numérotation GP0–GP28 (pas de BCM) : la colonne « GP » remplace
« GPIO (BCM) » et « Broche J8 ».

| Broche composante | Signal | GP | Couleur | Commentaire |
| --- | --- | --- | --- | --- |
| M1A | PWM entrée A, moteur 1 | GP2 | Jaune | Moteur droit |
| M1B | PWM entrée B, moteur 1 | GP3 | Blanc | Moteur droit |
| M2A | PWM entrée A, moteur 2 | GP4 | Jaune | Moteur gauche |
| M2B | PWM entrée B, moteur 2 | GP5 | Vert | Moteur gauche |
| GND | Masse de commande | GND | Noir | Masse commune |

Sorties M1/M2 vers les moteurs FIT0521 (voir fiches FIT0521_G / FIT0521_D).

> **À vérifier — correspondance moteur** : `docs/parametres.md` (« Affectation GPIO (validée) »)
> associe GPIO2/GPIO3 au **moteur gauche** et GPIO4/GPIO5 au **moteur droit**, soit l'inverse de la
> colonne « Commentaire » ci-dessus (reprise de l'état antérieur de ce fichier). La correspondance
> M1 ↔ droite / M2 ↔ gauche est à confirmer contre le firmware du Pico WH.

### FIT0521_G (DFRobot FIT0521 gauche) — encodeur

- **Contrôleur hôte** : Pico WH (signaux d'encodeur)
- **Interface / bus** : GPIO — encodeur en quadrature, 2 voies (A et B)
- **Alimentation** : encodeur en 3,3 V (fil bleu) et masse (fil noir), depuis le Pico WH. Le
  bobinage moteur est piloté par le MDD3A (voir fiche MDD3A) ; cette fiche ne couvre que
  l'encodeur.
- **Mode de raccordement** : directement avec les fils fournis sur le moteur.
- **Statut** : câblé, validé.

| Broche composante | Signal | GP | Couleur | Commentaire |
| --- | --- | --- | --- | --- |
| A | Voie A quadrature | GP10 | Vert | Encodeur |
| B | Voie B quadrature | GP11 | Jaune | Encodeur |
| 3,3 V | Alimentation encodeur | — | Bleu | Encodeur |
| GND | Masse encodeur | — | Noir | Encodeur |

### FIT0521_D (DFRobot FIT0521 droit) — encodeur

- **Contrôleur hôte** : Pico WH (signaux d'encodeur)
- **Interface / bus** : GPIO — encodeur en quadrature, 2 voies (A et B)
- **Alimentation** : encodeur en 3,3 V (fil bleu) et masse (fil noir), depuis le Pico WH. Le
  bobinage moteur est piloté par le MDD3A (voir fiche MDD3A) ; cette fiche ne couvre que
  l'encodeur.
- **Mode de raccordement** : directement avec les fils fournis sur le moteur.
- **Statut** : câblé, validé.

| Broche composante | Signal | GP | Couleur | Commentaire |
| --- | --- | --- | --- | --- |
| A | Voie A quadrature | GP12 | Vert | Encodeur |
| B | Voie B quadrature | GP13 | Jaune | Encodeur |
| 3,3 V | Alimentation encodeur | — | Bleu | Encodeur |
| GND | Masse encodeur | — | Noir | Encodeur |

### SERVO_TOUR (Hitec HS-422)

- **Contrôleur hôte** : Pico WH
- **Interface / bus** : GPIO — 1 ligne de signal PWM servo
- **Alimentation** : 5 V (fil rouge) et masse (fil noir). 
- **Mode de raccordement** : sur le breadboard 5V, puis le signal va au Pico.
- **Statut** : câblé.

| Broche composante | Signal | GP | Couleur | Commentaire |
| --- | --- | --- | --- | --- |
| SIG | Signal PWM servo | GP15 | Jaune | |
| 5 V | Alimentation | — | Rouge | |
| GND | Masse | — | Noir | |

### ULTRASON (Grove Ultrasonic Ranger)

- **Contrôleur hôte** : Pico WH
- **Interface / bus** : GPIO — signal sur un seul fil
- **Alimentation** : 3,3 V (fil rouge) et masse (fil noir). 
- **Mode de raccordement** : alimentation sur breadboard et signal directement au Pico.
- **Statut** : câblé.

| Broche composante | Signal | GP | Couleur | Commentaire |
| --- | --- | --- | --- | --- |
| SIG | Signal (un seul fil) | GP14 | Jaune | |
| 3,3 V | Alimentation | — | Rouge | |
| GND | Masse | — | Noir | |

## C. Table d'occupation des GPIO du Raspberry Pi 4

Index inversé. Les fiches ci-dessus restent la source de vérité pour les couleurs, les
commentaires et les broches des composantes.

| GPIO (BCM) | Composante |
| --- | --- |
| GPIO2 (SDA1) | INA260 ×2 — I2C1 SDA |
| GPIO3 (SCL1) | INA260 ×2 — I2C1 SCL |
| GPIO8 (CE0) | LCD2 — SPI0 CS |
| GPIO9 (MISO) | LCD2 — SPI0 MISO (inutilisé) |
| GPIO10 (MOSI) | LCD2 — SPI0 MOSI |
| GPIO11 (SCLK) | LCD2 — SPI0 SCLK |
| GPIO12 (PWM0) | LCD2 — rétroéclairage |
| GPIO14 (TXD) | Liaison UART Pico WH — Raspberry Pi TX |
| GPIO15 (RXD) | Liaison UART Pico WH — Raspberry Pi RX |
| GPIO18 | AUDIO_I2S — BCLK · réservé à l'interface I2S (BCM2711) |
| GPIO19 | AUDIO_I2S — LRC · réservé à l'interface I2S (BCM2711) |
| GPIO20 | Libre · réservé à l'interface I2S (BCM2711) |
| GPIO21 | AUDIO_I2S — DIN · réservé à l'interface I2S (BCM2711) |
| GPIO24 | LCD2 — RST |
| GPIO25 | LCD2 — DC |
