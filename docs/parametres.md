
# Paramètres techniques — Devastator

## Configuration ROS 2 des annonces audio

Le nœud `annonces_audio` utilise `src/robot_devastator_bringup/config/annonces_audio.yaml`.
L'audio reste une capacité décorative : une erreur de génération, de lecture ou de GPIO est
journalisée sans arrêter les autres fonctions du robot.

Paramètres principaux :

- `delai_min_repetition_s` : délai minimal avant de rejouer une annonce du même événement,
  actuellement `3.0 s`.
- `preparer_audio_au_demarrage` : génère les WAV Piper manquants avant d'écouter
  `/robot/evenement`, actuellement `true`.
- `jouer_annonce_demarrage` : joue l'annonce `demarrage` après la préparation initiale,
  actuellement `true`.
- `piper_executable`, `piper_model`, `piper_config` : chemins utilisés pour générer les WAV
  manquants avec Piper.
- `command_timeout_s` : délai maximal accordé à Piper et au repli `aplay` ponctuel,
  actuellement `15.0 s`.
- `lecteur_audio_persistant_active` : garde un processus `aplay` raw ouvert entre les annonces
  pour éviter un clac avant chaque lecture, actuellement `true`.
- `controle_ampli_active` : active le contrôle logiciel de la broche SD du MAX98357,
  actuellement `true`.
- `gpio_sd_ampli` : GPIO Raspberry Pi utilisé pour SD, actuellement `23`.
- `frequence_audio_hz` : fréquence attendue des WAV Piper et du flux raw, actuellement
  `16000 Hz`.
- `canaux_audio` : nombre de canaux attendu, actuellement `1`.
- `largeur_echantillon_octets` : largeur d'un échantillon PCM, actuellement `2` octets
  (`16 bits`).
- `silence_initial_s` : silence brut écrit au démarrage du lecteur persistant, actuellement
  `1.0 s`.
- `silence_fin_annonce_s` : silence brut écrit après chaque annonce et à la fermeture,
  actuellement `0.3 s`.

Le lecteur persistant attend des WAV RIFF/WAVE PCM, mono, `16 bits`, `16000 Hz`. Un fichier au
mauvais format est ignoré avec une erreur claire. Si le lecteur persistant ne peut pas démarrer ou
si son flux se ferme, le nœud tente le repli historique `aplay fichier.wav`.

## Configuration ROS 2 de l'interface Pico

Le nœud `interface_pico` utilise la liaison UART vers le Pico WH. Les paramètres actifs sont
regroupés dans `src/robot_devastator_bringup/config/interface_pico.yaml` :

- `port` : port UART, actuellement `/dev/ttyS0`
- `debit` : débit UART, actuellement `115200`
- `timeout_lecture` : attente maximale d'une lecture UART, actuellement `0.02 s`
- `periode_maintien_s` : intervalle entre les rappels de la dernière consigne moteur,
  actuellement `0.25 s`
- `delai_expiration_consigne_moteurs_s` : délai maximal sans nouvelle consigne ROS avant un arrêt
  explicite, actuellement `0.5 s`
- `periode_distance_s` : intervalle entre les demandes de mesure ultrason, actuellement `0.10 s`
- `periode_encodeurs_s` : intervalle entre les demandes de compteurs encodeurs, actuellement
  `0.10 s`
- `delai_attente_reponse_service_s` : délai maximal d'attente des confirmations UART pour les
  services, actuellement `1.0 s`

Le comportement d'autonomie simple est configuré dans
`src/robot_devastator_bringup/config/autonomie_simple.yaml`. Les consignes moteur actives sont :

- avance lente : `500`
- rotation de recherche : `500`
- recul de récupération : `300`

Dans le lancement principal, `actif_au_demarrage` vaut `false` : l'autonomie reste au repos tant
que `teleop_clavier` ne demande pas le mode `autonomie`.

La téléopération clavier est configurée dans
`src/robot_devastator_bringup/config/teleop_clavier.yaml` :

- vitesse initiale : `300`
- vitesse minimale : `300`
- vitesse maximale : `1000`
- pas d'incrément : `50`
- période de lecture et publication : `0.1 s`

L'arbitre de commandes moteur est configuré dans
`src/robot_devastator_bringup/config/arbitre_commande_moteurs.yaml` :

- mode initial du lancement principal : `manuel`
- période de publication vers le Pico : `0.1 s`
- délai sans commande de la source active avant arrêt : `0.35 s`

Les angles configurés pour la tourelle sont :

- centre : `95°`
- gauche : `45°`
- droite : `140°`

Association validée sur le robot :

- `45°` oriente la tourelle vers la gauche ;
- `140°` oriente la tourelle vers la droite.

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

### Mode test avec Raspberry Pi 4

- USB PC débranché du Pico
- Pico alimenté en autonome via VSYS
- UART Raspberry Pi ↔ Pico rebranché complètement
- Tests effectués via le Raspberry Pi 4 sur `/dev/ttyS0`

### Séquence pratique recommandée

- Pour développer sur le Pico :
  - débrancher la ligne Pi4 TX → Pico RX
- Pour tester la communication avec le Raspberry Pi 4 :
  - rebrancher la ligne Pi4 TX → Pico RX
  - alimenter le Pico via VSYS
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
  - `avancer()` = avance
  - `reculer()` = recul

## Fréquence PWM

- Valeur actuelle : 1000 Hz
- Ajustable ultérieurement selon bruit / rendement

## Paramètres UART

- Interface : UART matériel
- Instance retenue : UART0
- Débit prévu : 115200 bauds
- Format de commande : texte ASCII terminé par fin de ligne

### Commandes utilisées

Le protocole UART texte courant du Pico est utilisé sans alias vers les anciennes commandes :

- `PING` → `OK PING`
- `STOP_MOT` → `OK STOP_MOT`
- `SET_MOT <gauche> <droite>` → `OK SET_MOT <gauche> <droite>`
- `STATUS` → `OK STATUS <gauche> <droite> <actif>`
- `SONAR` → `OK SONAR <distance_mm>`
- `SET_SERVO <angle>` → `OK SET_SERVO <angle>`
- `ENC` → `OK ENC <gauche_ticks> <droite_ticks>`
- `RESET_ENC` → `OK RESET_ENC`

Les lignes spontanées `READY` et `AVERT TIMEOUT` peuvent aussi être reçues. Elles sont publiées
sur `/pico/etat`, mais ne remplacent pas les confirmations attendues par les services.

Le service ROS 2 `/pico/ping` réussit seulement si la réponse `OK PING` est reçue dans le délai
configuré par `delai_attente_reponse_service_s`.

### Convention de consigne

- plage : `-1000` à `1000`
- signe :
  - positif = avancer
  - négatif = reculer
- valeur absolue = intensité PWM
- `0` = arrêt

### Sécurité

- arrêt automatique par le Pico si aucune commande UART valide n'est reçue depuis plus de `500 ms`
- arrêt explicite par `interface_pico` si aucune nouvelle consigne moteur ROS n'est reçue
  depuis plus de `500 ms`
- neutralisation de l'ancienne consigne moteur après une erreur ou une reconnexion UART
- tentative d'envoi de `STOP_MOT` par `interface_pico` avant la fermeture de la liaison UART

## Règles de conception

- Ne jamais compenser un mauvais sens moteur en logiciel
- Toujours corriger au niveau du câblage
- Conserver une symétrie stricte gauche / droite
- Toute modification doit être répercutée ici
- La masse UART doit toujours être commune entre Raspberry Pi et Pico
- Les résistances série UART 1 kΩ font partie du montage courant
- La ligne Raspberry Pi TX → Pico RX doit être considérée comme ligne sensible au démarrage du Pico

# Interface manette Lynxmotion PS2 ↔ Raspberry Pi 4 

Cette interface est gelé puisque l'usage du clavier USB sans-fil Rii X8 est beaucoup plus simple d'usage et permet beaucoup plus de latitude pour téléopérer le robot et interagir avec lui. La manette pourra être implémentée si un besoin de contrôle plus ergonomique et précis est requis. En effet, il est plus commode de contrôler finement les mouvement du robot manuellement à l'aide de la manette PS2 que via des petits boutons sur un clavier USB sans-fil.

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
