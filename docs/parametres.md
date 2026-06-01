
# Contrôle moteurs — Pico WH + MDD3A

## Configuration ROS 2 de l'interface Pico

Le nœud `interface_pico_node` utilise uniquement la liaison UART réelle vers le Pico WH. Les
paramètres actifs sont regroupés dans
`src/robot_devastator_bringup/config/interface_pico_reel.yaml` :

- `port` : port UART, actuellement `/dev/ttyS0`
- `debit` : débit UART, actuellement `115200`
- `timeout_lecture` : attente maximale d'une lecture UART
- `periode_maintien_s` : intervalle entre les rappels de la dernière consigne moteur
- `periode_distance_s` : intervalle entre les demandes de mesure ultrason

Le comportement d'autonomie simple est configuré dans
`src/robot_devastator_bringup/config/autonomie_simple.yaml`. Les vitesses d'avance, de rotation et
de recul sont actuellement fixées à `300`, soit le seuil minimal observé pour obtenir un mouvement
fiable des moteurs.

## Affectation GPIO (validée)

- Moteur gauche :
  - Entrée A : GPIO2
  - Entrée B : GPIO3

- Moteur droit :
  - Entrée A : GPIO4
  - Entrée B : GPIO5

## Liaison UART Raspberry Pi 4 ↔ Pico WH (validée)

- Raspberry Pi 4 :
  - TX : GPIO14
  - RX : GPIO15

- Pico WH :
  - TX : GPIO0
  - RX : GPIO1

- Câblage croisé :
  - Raspberry Pi TX GPIO14 → résistance série 1 kΩ → Pico RX GPIO1
  - Raspberry Pi RX GPIO15 ← résistance série 1 kΩ ← Pico TX GPIO0
  - GND Raspberry Pi ↔ GND Pico

- Convention couleur retenue :
  - TX : jaune
  - RX : vert
  - GND : noir

## Diagnostic validé sur la liaison UART

- Le problème de démarrage observé n'est pas causé par l'USB seul ni par le Pico seul
- La ligne réellement critique est :
  - Raspberry Pi TX GPIO14 → Pico RX GPIO1
- Comportement observé :
  - Pico seul : démarrage OK
  - Pico avec fil GP1 seul : démarrage OK
  - Pico avec Pi4 éteint relié à GP1 : démarrage OK
  - Pico avec Pi4 allumé relié à GP1 : démarrage KO
- Conclusion :
  - la TX du Raspberry Pi 4 perturbe le démarrage du Pico lorsqu'elle est reliée au RX GPIO1 pendant le boot du Pico

## Règle de travail provisoire (obligatoire)

### Mode développement Pico par USB

- USB branché au Pico
- Déconnecter au minimum la ligne :
  - Raspberry Pi TX GPIO14 → Pico RX GPIO1
- La ligne Pico TX GPIO0 → Raspberry Pi RX GPIO15 peut rester en place seulement si elle ne perturbe pas le travail
- Objectif :
  - éviter qu'un état actif de la TX du Raspberry Pi bloque le démarrage du Pico

### Mode test réel avec Raspberry Pi 4

- USB PC débranché du Pico
- Pico alimenté en autonome via VSYS
- UART Raspberry Pi ↔ Pico rebranché complètement
- Tests effectués via le Raspberry Pi 4 sur `/dev/ttyS0`

### Séquence pratique recommandée

- Pour développer sur le Pico :
  - débrancher la ligne Pi4 TX → Pico RX
- Pour tester la communication réelle :
  - rebrancher la ligne Pi4 TX → Pico RX
  - alimenter le Pico en mode réel
  - tester depuis le Raspberry Pi 4

## Convention logique (figée)

- avancer :
  - PWM sur entrée A
  - entrée B = 0

- reculer :
  - entrée A = 0
  - PWM sur entrée B

- arrêter :
  - A = 0
  - B = 0

## Convention de câblage moteurs (figée)

- Fil jaune → entrée A (pour les deux moteurs)
- Fil blanc → entrée B du moteur droit
- Fil vert → entrée B du moteur gauche

## Correction physique appliquée

- Le moteur gauche est inversé physiquement au niveau du MDD3A
- Objectif : garantir que la même convention logique s’applique aux deux moteurs
  - `avancer()` = avance réelle
  - `reculer()` = recul réel

## Fréquence PWM

- Valeur actuelle : 1000 Hz
- Ajustable ultérieurement selon bruit / rendement

## Paramètres UART

- Interface : UART matériel
- Instance retenue : UART0
- Débit prévu : 115200 bauds
- Format de commande : texte ASCII terminé par fin de ligne

### Commandes prévues

- `PING`
- `STOP`
- `SET <gauche> <droite>`
- `STATUS`

### Convention de consigne

- plage : `-1000` à `1000`
- signe :
  - positif = avancer
  - négatif = reculer
- valeur absolue = intensité PWM
- `0` = arrêt

### Sécurité

- arrêt automatique si aucune commande valide reçue depuis plus de `500 ms`

## Règles de conception

- Ne jamais compenser un mauvais sens moteur en logiciel
- Toujours corriger au niveau du câblage
- Conserver une symétrie stricte gauche / droite
- Toute modification doit être répercutée ici
- La masse UART doit toujours être commune entre Raspberry Pi et Pico
- Les résistances série UART 1 kΩ font partie du montage courant
- La ligne Raspberry Pi TX → Pico RX doit être considérée comme ligne sensible au démarrage du Pico

# Interface manette Lynxmotion PS2 ↔ Raspberry Pi 4 (retenue)

## Alimentation

- Manette PS2 alimentée en 3,3 V
- Masse commune avec le Raspberry Pi 4
- Fil rouge = VCC
- Fil noir = GND

## Affectation GPIO Raspberry Pi 4

- GPIO24 = ATT
- GPIO9 = DATA
- GPIO10 = COMMAND
- GPIO11 = CLOCK
- GPIO25 = ACK

## Convention couleur faisceau PS2 retenue

- Brun = DATA
- Orange = COMMAND
- Noir = GND
- Rouge = VCC
- Jaune = ATT
- Bleu = CLOCK
- Vert = ACK
- Gris = alimentation moteur vibration, non connecté
- Blanc = broche 8 inconnue, non connectée

## Composants passifs retenus

- Résistance série 1 kΩ sur :
  - COMMAND
  - ATT
  - CLOCK
  - DATA
  - ACK
- Résistance de tirage 4,7 kΩ vers 3,3 V sur :
  - DATA
  - ACK

## Règles de conception manette

- Ne pas alimenter la manette en 5 V tant qu'aucun besoin réel n'est démontré
- Ne pas connecter la ligne vibration à cette étape
- Ne pas connecter la broche 8 blanche à cette étape
- Garder la logique manette côté Raspberry Pi 4
- La ligne ACK doit être câblée et considérée comme utile
- La ligne ATT doit être pilotée explicitement pour chaque transaction
