# Connexions — Devastator
| Header 1 | Header 2 |
| --- | --- |
| Cell 1 | Cell 2 |


## Raspberry Pi 4

| GPIO      | Composante  | Broche  | Couleur | Commentaire                                                                                                                    |
| --------- | ----------- | ------- | ------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 14 (TXD)  | Pico        | RX      | Jaune   | UART TX du Raspberry Pi vers RX du Pico via résistance série 1 kΩ ; ligne critique à déconnecter en développement Pico par USB |
| 15 (RXD)  | Pico        | TX      | Vert    | UART RX du Raspberry Pi depuis TX du Pico via résistance série 1 kΩ                                                            |
| GND       | Pico        | GND     | Noir    | Masse commune UART                                                                                                             |
| 18        | MAX98357    | BCLK    | Blanc   |                                                                                                                                |
| 19        | MAX98357    | LRC     | Bleu    |                                                                                                                                |
| 21        | MAX98357    | DIN     | Jaune   |                                                                                                                                |
| 24        | Manette PS2 | ATT     | Jaune   | Attention via résistance série 1 kΩ ; fil jaune du faisceau PS2                                                                |
| 9 (MISO)  | Manette PS2 | DATA    | Brun    | Données manette -> Pi4 via résistance série 1 kΩ + résistance de tirage 4,7 kΩ vers 3,3 V ; fil brun du faisceau PS2           |
| 10 (MOSI) | Manette PS2 | COMMAND | Orange  | Commande Pi4 -> manette via résistance série 1 kΩ ; fil orange du faisceau PS2                                                 |
| 11 (SCLK) | Manette PS2 | CLOCK   | Bleu    | Horloge Pi4 -> manette via résistance série 1 kΩ ; fil bleu du faisceau PS2                                                    |
| 25        | Manette PS2 | ACK     | Vert    | Acknowledge manette -> Pi4 via résistance série 1 kΩ + résistance de tirage 4,7 kΩ vers 3,3 V ; fil vert du faisceau PS2       |
| 3,3V      | Manette PS2 | VCC     | Rouge   | Alimentation logique PS2 en 3,3 V ; fil rouge du faisceau PS2                                                                  |
| GND       | Manette PS2 | GND     | Noir    | Masse commune ; fil noir du faisceau PS2                                                                                       |


## Pico

| GPIO | Composante                | Broche | Couleur | Commentaire                                                                                                                         |
| ---- | ------------------------- | ------ | ------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| 0    | Raspberry Pi              | RX     | Vert    | UART TX du Pico vers RX du Raspberry Pi via résistance série 1 kΩ                                                                   |
| 1    | Raspberry Pi              | TX     | Jaune   | UART RX du Pico depuis TX du Raspberry Pi via résistance série 1 kΩ ; ligne critique au démarrage du Pico si le Pi4 est déjà allumé |
| GND  | Raspberry Pi              | GND    | Noir    | Masse commune UART                                                                                                                  |
| 2    | MDD3A                     | M1A    | Jaune   |                                                                                                                                     |
| 3    | MDD3A                     | M1B    | Blanc   |                                                                                                                                     |
| 4    | MDD3A                     | M2A    | Jaune   |                                                                                                                                     |
| 5    | MDD3A                     | M2B    | Vert    |                                                                                                                                     |
| GND  | MDD3A                     | GND    | Noir    |                                                                                                                                     |
| 10   | FIT0521 - Encodeur droit  | A      | Vert    |                                                                                                                                     |
| 11   | FIT0521 - Encodeur droit  | B      | Jaune   |                                                                                                                                     |
| ---  | FIT0521 - Encodeur droit  | 3,3V   | Bleu    |                                                                                                                                     |
| ---  | FIT0521 - Encodeur droit  | GND    | Noir    |                                                                                                                                     |
| 12   | FIT0521 - Encodeur gauche | A      | Vert    |                                                                                                                                     |
| 13   | FIT0521 - Encodeur gauche | B      | Jaune   |                                                                                                                                     |
| ---  | FIT0521 - Encodeur gauche | 3,3V   | Bleu    |                                                                                                                                     |
| ---  | FIT0521 - Encodeur gauche | GND    | Noir    |                                                                                                                                     |
| 15   | HS-422 / Tourelle         | SIG    | Jaune   |                                                                                                                                     |
| ---  | HS-422 / Tourelle         | 5 V    | Rouge   |                                                                                                                                     |
| ---  | HS-422 / Tourelle         | GND    | Noir    |                                                                                                                                     |
| 14   | Grove Ultrasonic Ranger   | SIG    | Jaune   |                                                                                                                                     |
| ---  | Grove Ultrasonic Ranger   | 3,3V   | Rouge   |                                                                                                                                     |
| ---  | Grove Ultrasonic Ranger   | GND    | Noir    |                                                                                                                                     |

## Faisceau PS2 non connectés à cette étape

| Fil   | Usage                 | Commentaire   |
| ----- | --------------------- | ------------- |
| Gris  | Vibration motor power | Non connecté  |
| Blanc | Broche 8 inconnue     | Non connectée |
