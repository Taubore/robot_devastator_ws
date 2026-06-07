# Formation ROS 2 Devastator

## Objectif de la formation Devastator

Devastator sert de plateforme d'apprentissage progressive pour relier la robotique réelle,
l'électronique, Python, ROS 2 Jazzy et les systèmes embarqués. La formation doit permettre de
comprendre comment un robot mobile est construit par sous-systèmes simples, testés séparément puis
assemblés dans ROS 2.

L'objectif n'est pas de produire un robot industriel ou une architecture générique complète. Le but
est de construire un banc pédagogique maintenable, capable de montrer concrètement :

- la séparation entre contrôle haut niveau sur Raspberry Pi 4 et contrôle bas niveau sur Pico WH ;
- la publication et la consommation de topics ROS 2 ;
- l'utilisation de services ROS 2 pour des demandes ponctuelles ;
- la création d'interfaces communes avec des messages et services personnalisés ;
- l'assemblage de nœuds par fichiers `launch` et fichiers YAML de paramètres ;
- la validation matérielle courte, observable et sécuritaire.

## État courant du système

Le workspace ROS 2 officiel du projet est organisé autour d'une base mobile réelle. Le Raspberry
Pi 4 exécute ROS 2 Jazzy et communique avec le Raspberry Pi Pico WH par UART. Le Pico pilote les
moteurs, lit le sonar, oriente la tourelle et publie les mesures utiles vers ROS 2 par
`interface_pico`.

État fonctionnel documenté :

- la chaîne Raspberry Pi 4 -> `interface_pico` -> UART -> Pico WH -> MDD3A -> moteurs est active ;
- les consignes moteur utilisent la plage `-1000` à `1000`, avec `0` comme arrêt ;
- l'arrêt est protégé côté Pico et côté `interface_pico` par un délai de `500 ms` ;
- le sonar Grove est monté sur une tourelle servo Hitec HS-422 ;
- l'autonomie simple avec évitement d'obstacle est expérimentale ;
- les encodeurs FIT0521 sont lus par le Pico et publiés dans ROS 2 ;
- la voix française avec Piper, la chaîne audio I2S et le haut-parleur sont actifs et testés ;
- le mini clavier USB sans-fil Rii X8 est actif pour les interactions et essais manuels simples ;
- les lancements principaux sont centralisés dans `robot_devastator_bringup`.

Les fichiers de lancement documentés sont :

| Lancement | Rôle |
|---|---|
| `interface_pico.launch.yaml` | Lance seulement le pont ROS 2 vers le Pico |
| `autonomie_simple.launch.yaml` | Lance `interface_pico`, `voix_piper`, `annonces_audio` et `evitement_obstacle` |

## Packages ROS 2 existants

| Package | Type | Responsabilité |
|---|---|---|
| `commun` | `ament_cmake` | Définit les messages et services ROS 2 communs du projet |
| `interface_pico` | `ament_python` | Adapte ROS 2 vers le protocole UART texte du Pico WH |
| `robot_devastator` | `ament_python` | Contient la logique applicative du robot : autonomie simple et annonces audio |
| `robot_devastator_bringup` | `ament_cmake` | Regroupe les fichiers `launch` et les paramètres YAML d'assemblage |

Nœuds et exécutables connus :

| Nœud | Package | Exécutable | État | Rôle |
|---|---|---|---|---|
| `interface_pico` | `interface_pico` | `interface_pico` | Actif | Expose les topics et services Pico, puis traduit les commandes ROS 2 vers UART |
| `evitement_obstacle` | `robot_devastator` | `evitement_obstacle` | Expérimental | Avance lentement, détecte un obstacle, balaie la tourelle et cherche un dégagement |
| `annonces_audio` | `robot_devastator` | `annonces_audio` | Actif | Écoute les événements du robot et demande la lecture d'annonces configurées |
| `voix_piper` | `robot_devastator` | `voix_piper` | Actif | Génère et joue des fichiers WAV avec Piper |
| `essai_moteurs_borne` | `interface_pico` | `essai_moteurs_borne` | Outil de test | Publie une consigne moteur courte et bornée pour un essai roues dans le vide |

## Topics, services et messages connus

### Topics ROS 2

| Topic | Type | Producteur connu | Consommateur connu | Rôle |
|---|---|---|---|---|
| `/pico/commande_moteurs` | `commun/msg/ConsigneMoteurs` | `evitement_obstacle`, outils de test | `interface_pico` | Envoyer les consignes gauche et droite au Pico |
| `/pico/commande_tourelle_deg` | `std_msgs/msg/Int32` | `evitement_obstacle`, outils de test | `interface_pico` | Commander l'angle du servo de tourelle en degrés |
| `/pico/distance_ultrason_mm` | `std_msgs/msg/Int32` | `interface_pico` | `evitement_obstacle`, diagnostic | Publier la distance sonar en millimètres |
| `/pico/encodeurs` | `commun/msg/EtatEncodeurs` | `interface_pico` | Diagnostic, futur calcul d'odométrie | Publier les ticks encodeurs gauche et droit |
| `/pico/etat` | `std_msgs/msg/String` | `interface_pico` | Diagnostic | Publier les lignes d'état reçues du Pico |
| `/robot/evenement` | `std_msgs/msg/String` | `evitement_obstacle` | `annonces_audio` | Signaler les transitions significatives du comportement autonome |

Événements robot documentés ou configurés :

- `autonomie_demarre`
- `obstacle_detecte`
- `analyse_obstacle`
- `rotation_gauche`
- `rotation_droite`
- `recul_recuperation`
- `reprise_avance`
- `arret_robot`

### Services ROS 2

| Service | Type | Serveur | Client connu | Rôle |
|---|---|---|---|---|
| `/pico/ping` | `std_srvs/srv/Trigger` | `interface_pico` | Diagnostic | Envoyer `PING` et attendre `OK PING` |
| `/pico/stop` | `std_srvs/srv/Trigger` | `interface_pico` | Diagnostic | Envoyer `STOP_MOT` et attendre `OK STOP_MOT` |
| `/pico/reset_encodeurs` | `std_srvs/srv/Trigger` | `interface_pico` | Diagnostic | Envoyer `RESET_ENC` et attendre `OK RESET_ENC` |
| `/generer_audio` | `commun/srv/GenererAudio` | `voix_piper` | `annonces_audio` | Générer un fichier WAV absent du cache |
| `/jouer_audio` | `commun/srv/JouerAudio` | `voix_piper` | `annonces_audio` | Jouer un fichier WAV existant |

Aucune action ROS 2 n'est documentée ou implémentée actuellement.

### Interfaces personnalisées

| Interface | Définition | Rôle |
|---|---|---|
| `commun/msg/ConsigneMoteurs` | `int16 gauche`, `int16 droite` | Porter les consignes des moteurs gauche et droit |
| `commun/msg/EtatEncodeurs` | `int32 gauche_ticks`, `int32 droite_ticks` | Porter les compteurs encodeurs gauche et droit |
| `commun/srv/GenererAudio` | Requête : `texte`, `nom_fichier` ; réponse : `succes`, `message`, `chemin_fichier` | Demander la génération d'un fichier audio |
| `commun/srv/JouerAudio` | Requête : `nom_fichier` ; réponse : `succes`, `message`, `chemin_fichier` | Demander la lecture d'un fichier audio |

### Protocole UART Pico connu

Le protocole texte courant est utilisé sans alias vers d'anciennes commandes :

| Commande UART | Réponse attendue |
|---|---|
| `PING` | `OK PING` |
| `STOP_MOT` | `OK STOP_MOT` |
| `SET_MOT <gauche> <droite>` | `OK SET_MOT <gauche> <droite>` |
| `STATUS` | `OK STATUS <gauche> <droite> <actif>` |
| `SONAR` | `OK SONAR <distance_mm>` |
| `SET_SERVO <angle>` | `OK SET_SERVO <angle>` |
| `ENC` | `OK ENC <gauche_ticks> <droite_ticks>` |
| `RESET_ENC` | `OK RESET_ENC` |

Les lignes spontanées `READY` et `AVERT TIMEOUT` peuvent aussi être reçues et publiées sur
`/pico/etat`.

## Composants actifs, gelés et futurs

### Actifs

| ID | Composant | Rôle |
|---|---|---|
| `RASPI4` | Raspberry Pi 4 4 GB | Ordinateur principal ROS 2 |
| `PICO_WH` | Raspberry Pi Pico WH | Contrôle bas niveau et UART |
| `MDD3A` | Cytron MDD3A | Contrôleur des deux moteurs DC |
| `FIT0521_G` | DFRobot FIT0521 gauche | Traction gauche et encodeur |
| `FIT0521_D` | DFRobot FIT0521 droit | Traction droite et encodeur |
| `ULTRASON` | Grove Ultrasonic Ranger | Détection d'obstacle simple |
| `SERVO_TOUR` | Hitec HS-422 | Orientation du sonar |
| `BATT_LOGIQUE` | NiMH Tenergy PRO, pack maison | Alimentation logique |
| `BATT_MOTEUR` | NiMH Melasta | Alimentation moteurs |
| `VOLTM_LOGIQUE` | Voltmètre logique | Surveillance tension logique |
| `VOLTM_MOTEUR` | Voltmètre moteurs | Surveillance tension moteurs |
| `BUCK_3V3` | Pololu 4090 D36V50F3 | Rail 3,3 V |
| `BUCK_5V` | Pololu 4091 D36V50F5 | Rail 5 V |
| `ALIM_LOGIQUE` | Circuit d'alimentation 3,3 V / 5 V | Distribution logique |
| `SW_LOGIQUE` | Interrupteur alimentation logique | Mise sous tension logique |
| `AUDIO_I2S` | MAX98357 + PCM5102A | Amplification et conversion audio |
| `HP_BF37` | Visaton BF 37 | Sortie sonore du robot |
| `CLAV_X8` | Mini clavier USB sans-fil Rii X8 | Téléopération et interactions manuelles simples |

### Gelés

| ID | Composant | Rôle prévu |
|---|---|---|
| `PS2` | Manette Lynxmotion PS2 | Téléopération plus ergonomique si le besoin apparaît |
| `RPLIDAR` | Slamtec RPLIDAR A1M8 | Découverte lidar, cartographie ou navigation simple |

### Futurs

| ID | Composant | Rôle prévu |
|---|---|---|
| `INA260` | Adafruit INA260 | Mesure tension, courant et puissance |
| `REALSENSE` | Intel RealSense D435IF | Perception 3D |
| `LCD2` | Waveshare LCD 2 pouces ST7789V | Visage ou pages d'état |
| `MIC_ARRAY` | ReSpeaker Mic Array v3.0 | Expérimentation de réception vocale |

## Prochains jalons proposés

Ces jalons respectent la progression documentée : une seule complexité significative à la fois,
sans nouvelle architecture.

1. Stabiliser la fiche de formation et la garder alignée avec le README principal.
2. Valider de nouveau le lancement `interface_pico.launch.yaml` sur Raspberry Pi 4 avec roues dans
   le vide : ping, stop, sonar, tourelle et encodeurs.
3. Consolider les essais de l'autonomie simple au sonar : obstacle, balayage gauche-centre-droite,
   rotation, recul de récupération et reprise d'avance.
4. Documenter les limites observées de l'évitement d'obstacle après tests réels.
5. Exploiter les encodeurs d'abord en diagnostic simple avant de viser une odométrie.
6. Utiliser le clavier Rii X8 pour des essais manuels simples avant de décider si la manette PS2
   vaut une intégration ROS 2 dédiée.
7. Réactiver ensuite un seul sous-système gelé selon le besoin pédagogique le plus immédiat,
   probablement la manette PS2 ou le RPLIDAR.

## Points ouverts

- Seul `src/interface_pico` contient un README de package. Les responsabilités de `commun`,
  `robot_devastator` et `robot_devastator_bringup` sont déduites du README principal, des
  manifestes et des fichiers présents.
- Le clavier Rii X8 est actif comme périphérique USB, mais aucune interface ROS 2 dédiée au clavier
  n'est documentée actuellement.
- La manette PS2 a un câblage retenu dans la documentation, mais elle est gelée tant que le clavier
  Rii X8 répond mieux au besoin courant.
- Les encodeurs sont publiés par `interface_pico`, mais aucun nœud d'odométrie n'est documenté
  actuellement.
- `arret_robot` est configuré dans les annonces audio, mais sa publication effective n'est pas
  clairement établie par les documents de haut niveau.

## Journal court

- 2026-06-07 — Création de la fiche de formation ROS 2 Devastator à partir de `AGENTS.md`,
  `README.md`, des documents techniques et du README de `interface_pico`.
  