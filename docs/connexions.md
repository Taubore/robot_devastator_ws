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
| 24        | PS2 | ATT     | Jaune   | Attention via résistance série 1 kΩ ; fil jaune du faisceau PS2                                                                |
| 9 (MISO)  | PS2 | DATA    | Brun    | Données manette -> Pi4 via résistance série 1 kΩ + résistance de tirage 4,7 kΩ vers 3,3 V ; fil brun du faisceau PS2           |
| 10 (MOSI) | PS2 | COMMAND | Orange  | Commande Pi4 -> manette via résistance série 1 kΩ ; fil orange du faisceau PS2                                                 |
| 11 (SCLK) | PS2 | CLOCK   | Bleu    | Horloge Pi4 -> manette via résistance série 1 kΩ ; fil bleu du faisceau PS2                                                    |
| 25        | PS2 | ACK     | Vert    | Acknowledge manette -> Pi4 via résistance série 1 kΩ + résistance de tirage 4,7 kΩ vers 3,3 V ; fil vert du faisceau PS2       |
| 3,3V      | PS2 | VCC     | Rouge   | Alimentation logique PS2 en 3,3 V ; fil rouge du faisceau PS2                                                                  |
| GND       | PS2 | GND     | Noir    | Masse commune ; fil noir du faisceau PS2                                                                                       |


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

## Fils du PS2 non connectés

| Fil   | Usage                 | Commentaire   |
| ----- | --------------------- | ------------- |
| Rouge | Alimentation | Temporaire - penser à reconnecter si on désire l'utiliser |
| Noir | Alimentation | Temporaire - penser à reconnecter si on désire l'utiliser  |
| Gris  | Vibration motor power | Non utilisé  |
| Blanc | Broche 8 inconnue     | Non utilisé  |


