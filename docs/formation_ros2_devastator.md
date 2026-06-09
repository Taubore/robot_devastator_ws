# Formation ROS 2 Devastator

## Source de référence (pour séance de reprise ou avant audit)

Dépôt officiel :
https://github.com/Taubore/robot_devastator_ws

Branche de référence :
`main`

Commit de référence consulté (`git rev-parse HEAD`):
bdffbc7ec6fa96528d8f50feda5ca1903a034342

Date de vérification :
2026-06-08

Note :
Ce commit identifie l’état du dépôt utilisé pour rédiger ou valider ce document. Il ne prétend pas être le commit contenant nécessairement cette version du document.

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
- l'arbitrage moteur évite que la téléopération clavier et l'autonomie publient directement en
  même temps vers le Pico ;
- les encodeurs FIT0521 sont lus par le Pico et publiés dans ROS 2 ;
- la voix française avec Piper, la chaîne audio I2S et le haut-parleur sont actifs et testés ;
- le mini clavier USB sans-fil Rii X8 sert à la capacité permanente `teleop_clavier` ;
- les lancements principaux sont centralisés dans `robot_devastator_bringup`.

Les fichiers de lancement documentés sont :

| Lancement | Rôle |
|---|---|
| `devastator.launch.yaml` | Lance le robot avec interface Pico, arbitre, autonomie simple en attente et audio |
| `interface_pico.launch.yaml` | Lance seulement le pont ROS 2 vers le Pico |

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
| `arbitre_commande_moteurs` | `robot_devastator` | `arbitre_commande_moteurs` | Actif | Sélectionne une seule source moteur active avant le topic Pico |
| `teleop_clavier` | `robot_devastator` | `teleop_clavier` | Actif | Conduit le robot au clavier et bascule entre mode manuel et autonomie |
| `evitement_obstacle` | `robot_devastator` | `evitement_obstacle` | Expérimental | Avance lentement, détecte un obstacle, balaie la tourelle et cherche un dégagement |
| `annonces_audio` | `robot_devastator` | `annonces_audio` | Actif | Écoute les événements du robot et demande la lecture d'annonces configurées |
| `voix_piper` | `robot_devastator` | `voix_piper` | Actif | Génère et joue des fichiers WAV avec Piper |
| `essai_moteurs_borne` | `interface_pico` | `essai_moteurs_borne` | Outil de test | Publie une consigne moteur courte et bornée pour un essai roues dans le vide |

## Topics, services et messages connus

### Topics ROS 2

| Topic | Type | Producteur connu | Consommateur connu | Rôle |
|---|---|---|---|---|
| `/pico/commande_moteurs` | `commun/msg/ConsigneMoteurs` | `arbitre_commande_moteurs`, outils de test | `interface_pico` | Envoyer la commande moteur active au Pico |
| `/robot/commande_moteurs/manuelle` | `commun/msg/ConsigneMoteurs` | `teleop_clavier` | `arbitre_commande_moteurs` | Porter les consignes clavier |
| `/robot/commande_moteurs/autonomie` | `commun/msg/ConsigneMoteurs` | `evitement_obstacle` | `arbitre_commande_moteurs` | Porter les consignes autonomes |
| `/robot/mode_conduite` | `std_msgs/msg/String` | `teleop_clavier` | `arbitre_commande_moteurs` | Demander le mode `manuel` ou `autonomie` |
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
| `/pico/stop_moteurs` | `std_srvs/srv/Trigger` | `interface_pico` | Diagnostic | Envoyer `STOP_MOT` et attendre `OK STOP_MOT` |
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
| `CLAV_X8` | Mini clavier USB sans-fil Rii X8 | Téléopération clavier locale et SSH |

Note : `CLAV_X8` reste un périphérique Linux standard géré par Ubuntu. La capacité ROS 2
`teleop_clavier` lit le terminal local ou SSH, sans pilote clavier dédié.

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
6. Valider la téléopération clavier permanente sur Raspberry Pi 4, puis décider si la manette PS2
   apporte encore un gain réel.
7. Réactiver ensuite un seul sous-système gelé selon le besoin pédagogique le plus immédiat,
   probablement la manette PS2 ou le RPLIDAR.

## Jalons pédagogiques globaux

1. Cartographier le système ROS 2 actuel.
2. Stabiliser le contrat Pico ↔ ROS 2.
3. Valider téléopération et arrêt fiable.
4. Formaliser les diagnostics rapides.
5. Documenter l’autonomie simple comme machine à états.
6. Ajouter une description robot minimale en URDF/Xacro.
7. Mettre en place TF et visualisation RViz.
8. Exploiter les encodeurs pour une odométrie simple.
9. Créer un banc logiciel ou simulateur minimal.
10. Décider objectivement si RPLIDAR/Nav2 sont intégrés sur Devastator ou reportés à RobotPi.

## Points ouverts

- Seul `src/interface_pico` contient un README de package. Les responsabilités de `commun`,
  `robot_devastator` et `robot_devastator_bringup` sont déduites du README principal, des
  manifestes et des fichiers présents.
- Le clavier Rii X8 est actif comme périphérique USB/HID standard géré par Ubuntu sur Raspberry Pi 4.
  La capacité ROS 2 `teleop_clavier` l'utilise via le terminal, localement ou par SSH.
- La manette PS2 a un câblage retenu dans la documentation, mais elle est gelée tant que le clavier
  Rii X8 répond mieux au besoin courant.
- Les encodeurs sont publiés par `interface_pico`, mais aucun nœud d'odométrie n'est documenté
  actuellement.
- `arret_robot` est configuré dans les annonces audio, mais sa publication effective n'est pas
  clairement établie par les documents de haut niveau.

## Règle de reprise

Au début de chaque séance, relire :
1. `AGENTS.md` ;
2. `README.md` ;
3. ce fichier : `docs/formation_ros2_devastator.md` ;
4. les fichiers `docs/`, `src/`, `launch/` ou `config/` touchés par la séance.

Chaque reprise commence par :
- dernier jalon validé ;
- prochaine action concrète ;
- prochain test observable ;
- risque matériel principal ;
- fichier(s) à modifier ou à ne pas modifier.

GitHub `main` reste la source principale. Les fichiers joints, souvenirs de conversation et notes locales sont secondaires si une divergence existe.

## Décisions validées
- rqt_graph sera exécuté sur Lenovo-Linux, pas sur le Raspberry Pi 4.
- Le Raspberry Pi 4 reste l’environnement d’exécution matérielle via SSH.
- ROS_DOMAIN_ID reste non défini pour l’instant, car la découverte ROS 2 fonctionne correctement avec le domaine par défaut.

## Tests validés
- rqt_graph sur Lenovo-Linux détecte les nœuds ROS 2 lancés sur le Raspberry Pi 4.
- ros2 node list, ros2 topic list, ros2 service list fonctionnels dans sur le Raspberry Pi 4 qu'à partir de Lenovo-Linux.
- ros2 service call et ros2 topic echo ont également été testé avec deux services et deux topic.

## Journal court

- 2026-06-07 — Création de la fiche de formation ROS 2 Devastator à partir de `AGENTS.md`,
  `README.md`, des documents techniques et du README de `interface_pico`.
- 2026-06-08 - la phase 1 a été validée : test CLI sur Raspberry Pi 4 via SSH fonctionnel, et observation du graphe ROS 2 depuis Legion-Linux avec rqt_graph sur le même réseau et le même ROS_DOMAIN_ID. Fichier `contrat_pico_ros2.md` a été créé, il documente clairement le rôle du node interface_pico.
- 2026-06-09 - Phase 3A validée sur Raspberry Pi 4 via SSH, roues dans le vide : la sécurité moteur CLI arrête bien les moteurs par expiration de consigne, mais un arrêt fiable de téléopération doit aussi arrêter ou neutraliser la source de commande active.
- 2026-06-09 - La téléopération clavier devient une capacité permanente `teleop_clavier`.
  Un arbitre moteur centralise les consignes manuelles et autonomes avant `/pico/commande_moteurs`.
- 2026-06-09 - `teleop_clavier` reste lancé en avant-plan dans un terminal interactif séparé.
  `ros2 launch` ne fournit pas d'entrée clavier fiable aux nœuds lancés.
