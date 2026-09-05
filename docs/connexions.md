# Connexions — Devastator

## Raspberry Pi 4

| GPIO      | Composante (ID) | Broche  | Couleur | Commentaire                                                                                                                    |
| --------- | ----------- | ------- | ------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 14 (TXD)  | PICO_WH        | RX      | Jaune   | UART TX du Raspberry Pi vers RX du Pico via résistance série 1 kΩ ; ligne critique à déconnecter en développement Pico par USB |
| 15 (RXD)  | PICO_WH        | TX      | Vert    | UART RX du Raspberry Pi depuis TX du Pico via résistance série 1 kΩ                                                            |
| GND       | PICO_WH        | GND     | Noir    | Masse commune UART                                                                                                             |
| 18        | AUDIO_I2S    | BCLK    | Blanc   |                                                                                                                                |
| 19        | AUDIO_I2S    | LRC     | Bleu    |                                                                                                                                |
| 21        | AUDIO_I2S    | DIN     | Jaune   |                                                                                                                                |
| 2 (SDA1)  | INA260 x2 | SDA | —       | Ligne de données I2C1, partagée par les deux INA260 (0x40 rail logique, 0x41 rail moteur) ; résistances de tirage sur les modules Adafruit |
| 3 (SCL1)  | INA260 x2 | SCL | —       | Ligne d'horloge I2C1, partagée par les deux INA260                                                                            |

## I2C — capteurs d'alimentation INA260

Bus I2C1 du Raspberry Pi 4 (`/dev/i2c-1`, broches GPIO2/GPIO3), activé par
`dtparam=i2c_arm=on`. Deux capteurs Adafruit INA260 y sont câblés en parallèle, chacun inséré
en série sur le fil positif d'une batterie :

| Adresse | Rail surveillé | Batterie |
|---|---|---|
| `0x40` | Logique | Pack Tenergy 7,2 V, 6 cellules NiMH |
| `0x41` | Moteur | Pack Melasta 6 V, 5 cellules NiMH |

Les deux modules sont alimentés en 3,3 V par le rail logique (Pololu 4090) : aucune lecture n'est
possible robot éteint. Détection : `i2cdetect -y 1` doit montrer `40` et `41`. Lecture ROS 2 :
nœud `surveillance_alimentation` (voir `src/surveillance_alimentation/README.md`).

## Audio I2S

La sortie audio I2S est fonctionnelle avec `dtparam=i2s=on` et
`dtoverlay=hifiberry-dac`. Le HiFiBerry DAC est détecté comme carte ALSA, et le test fonctionnel
Devastator est :

```bash
aplay -D default ~/.cache/robot_devastator/audio/demarrage_01.wav
```

Le clac observé à chaque lecture séparée vient probablement de l'ouverture et fermeture du flux
audio par `aplay` avec l'ampli I2S. Ce diagnostic ne pointe pas vers le routage GPIO ni vers
`dtparam=audremap`. Les pistes futures sont un pré-silence ou un fade-in dans les WAV, un lecteur
audio persistant, ou une solution matérielle anti-pop si le besoin reste présent.

## Pico

| GPIO | Composante (ID) | Broche | Couleur | Commentaire |
| --- | --- | --- | --- | --- |
| 0 | RASPI4 | RX | Vert | UART TX du Pico vers RX du Raspberry Pi via résistance série 1 kΩ |
| 1 | RASPI4 | TX | Jaune | UART RX du Pico depuis TX du Raspberry Pi via résistance série 1 kΩ ; ligne critique au démarrage du Pico si le Pi4 est déjà allumé |
| GND | RASPI4 | GND | Noir | Masse commune UART |
| 2 | MDD3A | M1A | Jaune | Moteur droit |
| 3 | MDD3A | M1B | Blanc | Moteur droit |
| 4 | MDD3A | M2A | Jaune | Moteur gauche |
| 5 | MDD3A | M2B | Vert | Moteur gauche |
| GND | MDD3A | GND | Noir |  |
| 10 | FIT0521_G | A | Vert | Encodeur |
| 11 | FIT0521_G | B | Jaune | Encodeur |
| --- | FIT0521_G | 3,3V | Bleu | Encodeur |
| --- | FIT0521_G | GND | Noir | Encodeur |
| 12 | FIT0521_D | A | Vert | Encodeur |
| 13 | FIT0521_D | B | Jaune | Encodeur |
| --- | FIT0521_D | 3,3V | Bleu | Encodeur |
| --- | FIT0521_D | GND | Noir | Encodeur |
| 15 | SERVO_TOUR | SIG | Jaune |  |
| --- | SERVO_TOUR | 5 V | Rouge |  |
| --- | SERVO_TOUR | GND | Noir |  |
| 14 | ULTRASON | SIG | Jaune |  |
| --- | ULTRASON | 3,3V | Rouge |  |
| --- | ULTRASON | GND | Noir |  |

## Connexions USB sur le Raspberry Pi 4

| Composante (ID) | Usage                 | Commentaire   |
| ----- | --------------------- | ------------- |
| CLAV_X8 | Permet de pouvoir saisir du texte directement sur le raspi4 | connecté  |

## Affichage LCD Waveshare 2" ST7789V — PLAN NON CÂBLÉ

Brochage prévu, non encore câblé. 

| GPIO | Broche module | Commentaire |
| --- | --- | --- |
| 11 | SCLK | |
| 10 | MOSI (DIN côté module) | |
| 8 (CE0) | CS | |
| 25 | DC | |
| 24 | RST | |
| 12 | BL (rétroéclairage) | PWM0 matériel ; déplacé de sa position usuelle car GPIO18-21 sont réservés à l'interface I2S du BCM2711 |
| 9 (MISO) | — | Inutilisé, le ST7789V étant en écriture seule |

Le brochage et la tension d'alimentation du module restent à confirmer contre la documentation
Waveshare avant câblage. Mode de raccordement prévu : nappe Dupont femelle fournie avec le
module, branchée directement sur les broches mâles du HAT du Raspberry Pi 4, sans breadboard.

