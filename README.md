# Devastator

## Objectif du projet

Devastator est un robot mobile utilisé comme plateforme d'apprentissage pour ROS 2,
l'électronique, Python et les systèmes embarqués. Le workspace contient la logique ROS 2
exécutée sur Raspberry Pi 4, l'interface avec un Raspberry Pi Pico WH et les interfaces
communes du projet.

## Environnement

- ROS 2 Jazzy
- Ubuntu 24.04
- Raspberry Pi 4
- Raspberry Pi Pico WH
- VSCode
- Validation matérielle sur Raspberry Pi 4

## Structure du workspace

| Chemin | Rôle |
|---|---|
| `src/commun` | Interfaces ROS 2 communes |
| `src/interface_pico` | Pont ROS 2 ↔ UART ↔ Pico WH |
| `src/odometrie` | Calcul de l'odométrie à partir des ticks encodeurs |
| `src/surveillance_alimentation` | Surveillance tension et courant des batteries (INA260 sur I2C) |
| `src/robot_devastator` | Logique principale du robot |
| `src/robot_devastator_bringup` | Fichiers de lancement (`*.launch.yaml`) et paramètres |
| `src/robot_devastator_description` | Description URDF/Xacro du robot et visualisation RViz |
| `docs` | Documentation détaillée du projet |

## Faire fonctionner le robot

Le robot réel s'exécute entièrement sur le Raspberry Pi 4, en terminal, via SSH. VSCode sert au
développement et au débogage, jamais à lancer le robot.

### 1. Mettre à jour et compiler

```bash
cd ~/projets/robot_devastator_ws
git pull
colcon build --symlink-install
source install/setup.bash
```

`colcon build --symlink-install` compile tout le workspace en quelques secondes. Refaire
`source install/setup.bash` dans chaque nouveau terminal. L'underlay ROS 2
(`source /opt/ros/jazzy/setup.bash`) est supposé déjà chargé depuis `~/.bashrc`.

### 2. Lancer le robot et le conduire

Deux terminaux SSH, tous deux sourcés :

```bash
# Terminal 1 — robot complet
ros2 launch robot_devastator_bringup devastator.launch.yaml

# Terminal 2 — conduite au clavier
ros2 launch robot_devastator_bringup teleop.launch.yaml
```

`devastator.launch.yaml` démarre l'interface Pico, l'odométrie, l'arbitre moteur, l'autonomie (en
attente) et les annonces audio, en mode manuel. `teleop.launch.yaml` se lance à part parce que
`teleop_clavier` lit les touches du terminal courant : c'est la seule exception au lancement
unique.

Touches (clavier QWERTY, terminal 2 au premier plan) :

| Touche | Effet |
|---|---|
| `w` / `s` | avancer / reculer |
| `a` / `d` | tourner à gauche / à droite |
| `espace` | arrêter |
| `=` / `-` | augmenter / diminuer la vitesse |
| `m` | basculer manuel ↔ autonomie |
| `x` | quitter (publie un arrêt moteur) |

Garder les roues dans le vide au premier essai. La vitesse par défaut est `300`, bornée de `300` à
`1000` (`config/teleop_clavier.yaml`). En mode autonomie, les touches de mouvement sont ignorées ;
`m`, `=` et `-` restent actives. `Ctrl+C` dans un terminal publie aussi un arrêt moteur.

### 3. Fin de séance (quotidien)

- **Débrancher le connecteur XT30 de la batterie moteur (6 V Melasta).** Le MDD3A consomme
  ~32,5 mA en continu tant que ce connecteur est branché, même moteurs à l'arrêt : le pack de
  2000 mAh est à plat en ~2,5 jours, avec risque d'inversion de cellule sur un pack NiMH 5S
  (dommage permanent).
- La batterie logique (7,2 V Tenergy) n'a **pas** besoin d'être débranchée chaque jour (veille des
  régulateurs Pololu ~0,2 mA). La débrancher seulement en cas d'inactivité de plusieurs jours.

## Comportement du robot

- **Modes de conduite.** `teleop_clavier` publie le mode (`manuel` ou `autonomie`) ; l'arbitre
  `arbitre_commande_moteurs` sélectionne la source moteur correspondante. L'arbitre est le seul
  nœud à publier vers `/pico/commande_moteurs`, ce qui évite tout conflit entre le clavier et
  l'autonomie.
- **Autonomie simple (expérimentale).** En mode autonomie, le robot avance tant que le sonar est
  dégagé. Devant un obstacle, il arrête les moteurs, balaie avec la tourelle (gauche, centre,
  droite), tourne vers le côté le plus dégagé, puis reprend l'avance après confirmation du passage
  par plusieurs mesures. Sans issue dans le délai prévu, il recule brièvement et recommence.
- **Arrêt de sécurité.** `interface_pico` ne maintient une consigne moteur que `0,5 s`. Sans
  nouvelle consigne, après une erreur UART ou à la reconnexion, il force et mémorise un arrêt.
- **Audio.** `annonces_audio` joue des annonces vocales (Piper) sur les événements du robot.
  Purement décoratif : si Piper ou `aplay` sont absents, l'erreur est journalisée et les autres
  nœuds continuent normalement.

## Développement dans VSCode

Ouvrir la palette de commandes avec F1.

### Build et nettoyage

Tâches définies dans `.vscode/tasks.json` :

| Tâche | Usage |
|---|---|
| `ROS 2 - Build Devastator` | build par défaut (`Tasks: Run Build Task`) |
| `ROS 2 - Build complet` | build de tout le workspace |
| `ROS 2 - Nettoyer packages Devastator` | après modification ou renommage d'un `.msg` / `.srv`, ou si `build/` ou `install/` contiennent des artefacts obsolètes |

### Débogage d'un nœud Python

`.vscode/launch.json` → configuration `Nœud Python ROS 2` (F5) : demande le module à exécuter, par
exemple `robot_devastator.evitement_obstacle` ou `interface_pico.interface_pico`. Réservé au debug
d'un nœud isolé, jamais à l'exploitation du robot.

### Simulation et visualisation (Legion-Linux, sans matériel)

- **Gazebo** : tâche `ROS 2 - Lancer simulation Gazebo` (seule tâche VSCode d'exécution).
- **RViz / URDF** :

  ```bash
  colcon build --symlink-install --packages-select robot_devastator_description
  source install/setup.bash
  ros2 launch robot_devastator_description affichage.launch.py
  ```

  Dans RViz : ajouter un affichage **RobotModel**, fixer le **Fixed Frame** à `base_footprint`.
  `joint_state_publisher_gui` ouvre une fenêtre pour tourner les roues manuellement.

## Référence

### Interfaces ROS 2 — topics

| Topic | Type | Producteur | Consommateur | Rôle |
|---|---|---|---|---|
| `/pico/commande_moteurs` | `commun/msg/ConsigneMoteurs` | `arbitre_commande_moteurs` | `interface_pico` | Envoyer la commande moteur active vers le Pico |
| `/robot/commande_moteurs/manuelle` | `commun/msg/ConsigneMoteurs` | `teleop_clavier` | `arbitre_commande_moteurs` | Porter les consignes issues du clavier |
| `/robot/commande_moteurs/autonomie` | `commun/msg/ConsigneMoteurs` | `evitement_obstacle` | `arbitre_commande_moteurs` | Porter les consignes issues de l'autonomie simple |
| `/robot/mode_conduite` | `std_msgs/msg/String` | `teleop_clavier` | `arbitre_commande_moteurs` | Choisir `manuel` ou `autonomie` comme source moteur active |
| `/pico/commande_tourelle_deg` | `std_msgs/msg/Int32` | Outil de test ou `evitement_obstacle` | `interface_pico` | Commander l'angle du servo de tourelle en degrés |
| `/pico/distance_ultrason_mm` | `std_msgs/msg/Int32` | `interface_pico` | `evitement_obstacle` | Publier la distance ultrason mesurée en millimètres |
| `/pico/encodeurs` | `commun/msg/EtatEncodeurs` | `interface_pico` | `odometrie`, outil de diagnostic | Publier les ticks des encodeurs gauche et droit lus sur le Pico |
| `/pico/etat` | `std_msgs/msg/String` | `interface_pico` | Outil de diagnostic | Publier les lignes d'état reçues côté Pico |
| `/robot/evenement` | `std_msgs/msg/String` | `evitement_obstacle`, `surveillance_alimentation` | `annonces_audio` | Signaler les transitions du comportement autonome et les franchissements de seuil batterie |
| `/odom` | `nav_msgs/msg/Odometry` | `odometrie` | RViz, outil de diagnostic | Publier la pose et la vitesse estimées à partir des encodeurs |
| `/alimentation/logique` | `sensor_msgs/msg/BatteryState` | `surveillance_alimentation` | Outil de diagnostic | Publier tension et courant du rail logique (pack 7,2 V NiMH) |
| `/alimentation/moteur` | `sensor_msgs/msg/BatteryState` | `surveillance_alimentation` | Outil de diagnostic | Publier tension et courant du rail moteur (pack 6 V NiMH) |

### Interfaces ROS 2 — services

| Service | Type | Serveur | Client connu | Rôle |
|---|---|---|---|---|
| `/pico/ping` | `std_srvs/srv/Trigger` | `interface_pico` | Outil de diagnostic | Envoyer `PING` et réussir seulement si le Pico répond `OK PING` dans le délai |
| `/pico/stop_moteurs` | `std_srvs/srv/Trigger` | `interface_pico` | Outil de diagnostic | Demander un arrêt explicite des moteurs au Pico avec `STOP_MOT` |
| `/pico/reset_encodeurs` | `std_srvs/srv/Trigger` | `interface_pico` | Outil de diagnostic | Remettre à zéro les compteurs d'encodeurs avec `RESET_ENC` |
| `/odometrie/reset` | `std_srvs/srv/Trigger` | `odometrie` | Outil de diagnostic | Remettre x, y, theta à zéro sans toucher aux ticks du Pico |

Aucune action ROS 2 n'est implémentée actuellement.

### Nœuds ROS 2

Convention : noms de nœuds et d'exécutables en `snake_case`, sans suffixe `_node` systématique. Les
clés racines des fichiers YAML de paramètres reprennent le nom exact du nœud lancé.

| Nœud | Package | Exécutable / module | État | Rôle |
|---|---|---|---|---|
| `interface_pico` | `interface_pico` | `interface_pico` / `interface_pico.interface_pico` | Actif | Exposer les topics et services Pico, puis traduire les commandes ROS 2 vers UART |
| `arbitre_commande_moteurs` | `robot_devastator` | `arbitre_commande_moteurs` / `robot_devastator.arbitre_commande_moteurs` | Actif | Sélectionner une seule source moteur active avant `/pico/commande_moteurs` |
| `evitement_obstacle` | `robot_devastator` | `evitement_obstacle` / `robot_devastator.evitement_obstacle` | Expérimental | Avancer lentement, balayer avec la tourelle, puis tourner jusqu'à trouver un dégagement |
| `teleop_clavier` | `robot_devastator` | `teleop_clavier` / `robot_devastator.teleop_clavier` | Actif | Conduire localement au clavier et basculer entre mode manuel et autonomie |
| `annonces_audio` | `robot_devastator` | `annonces_audio` / `robot_devastator.annonces_audio` | Actif | Préparer les WAV manquants avec Piper, puis jouer les annonces selon les événements du robot |
| `odometrie` | `odometrie` | `odometrie` / `odometrie.odometrie` | Actif | Calculer x, y, theta depuis `/pico/encodeurs` et publier `/odom` et la TF `odom → base_footprint` |
| `surveillance_alimentation` | `surveillance_alimentation` | `surveillance_alimentation` / `surveillance_alimentation.surveillance_alimentation` | Diagnostic | Lire deux INA260 sur I2C, publier `sensor_msgs/BatteryState` par rail et alerter sur tension basse maintenue (hors `devastator.launch.yaml` pour l'instant) |

### Interfaces personnalisées

| Interface | Type | Rôle |
|---|---|---|
| `commun/msg/ConsigneMoteurs` | Message | Transporter les consignes moteur gauche et droite, sur une plage prévue de `-1000` à `1000` |
| `commun/msg/EtatEncodeurs` | Message | Transporter les ticks des encodeurs gauche et droit publiés par `interface_pico` |

### Commandes de diagnostic

Lancements `diag_*` : jamais utilisés en exploitation normale, réservés à l'isolement d'un
sous-système. Dans un terminal sourcé, roues dans le vide :

```bash
# Banc de test de l'interface Pico seule
ros2 launch robot_devastator_bringup diag_interface_pico.launch.yaml

# Essai moteurs borné à faible vitesse, suivi d'un arrêt explicite attendu
ros2 run interface_pico essai_moteurs_borne

# Lien Pico et arrêt manuel
ros2 service call /pico/ping std_srvs/srv/Trigger
ros2 service call /pico/stop_moteurs std_srvs/srv/Trigger

# Capteurs
ros2 topic echo /pico/distance_ultrason_mm
ros2 topic echo /pico/encodeurs
ros2 service call /pico/reset_encodeurs std_srvs/srv/Trigger

# Surveillance de l'alimentation seule (INA260 sur I2C)
ros2 launch robot_devastator_bringup diag_surveillance_alimentation.launch.yaml
ros2 topic echo /alimentation/logique
ros2 topic echo /alimentation/moteur
```

Les ticks doivent augmenter en marche avant et diminuer en marche arrière. Si un moteur tourne dans
le mauvais sens, corriger le câblage au MDD3A plutôt que le logiciel.

### Matériel — repères électriques

Mesures INA260, robot au repos sans charge :

| Rail | Tension typique | Courant typique |
|---|---|---|
| Logique (7,2 V) | ~7,1–7,2 V | ~380 mA (Pi 4 sans écran HDMI) |
| Moteur (6 V) | ~5,8–6,4 V | ~20–34 mA (MDD3A en veille) |

Le courant logique varie selon la charge active (SSH, nœuds ROS 2, écran HDMI +~145 mA) : utiliser
la tension, pas le courant, comme indicateur de batterie faible. Les deux INA260 sont alimentés par
le rail logique 3,3 V (Pololu 4090), coupé quand l'interrupteur logique est à off : aucune lecture
de tension ou de courant batterie n'est possible robot éteint. Pour vérifier l'état de charge avant
un rangement prolongé, allumer brièvement le robot ou utiliser un multimètre externe.

Ces deux INA260 (0x40 rail logique, 0x41 rail moteur) sont lus par le nœud
`surveillance_alimentation`, encore isolé dans `diag_surveillance_alimentation.launch.yaml` le
temps de la mise au point. Voir `src/surveillance_alimentation/README.md`.

### Audio I2S — état du diagnostic

Sortie fonctionnelle avec `dtparam=i2s=on` et `dtoverlay=hifiberry-dac` ; le HiFiBerry DAC est
détecté comme carte ALSA. Test fonctionnel :

```bash
aplay -D default ~/.cache/robot_devastator/audio/demarrage_01.wav
```

`annonces_audio` charge les annonces de `config/annonces_audio.yaml`, vérifie le cache persistant
`~/.cache/robot_devastator/audio`, génère synchroniquement avec Piper les WAV manquants au
démarrage, puis les réutilise aux lancements suivants. Une annonce peut proposer plusieurs
variantes ; une chaîne vide représente une variante silencieuse.

Limitation connue : l'ampli I2S produit un clac au début de chaque lecture. Pistes essayées sans
succès : audremap, lecture en stream, tentative via SD/shutdown. Décision : ne pas poursuivre ce
chantier maintenant, conserver l'audio comme capacité décorative.

## Documentation détaillée

- [Carte ROS 2 pour l'apprentissage](docs/carte_ros_apprentissage.md)
- [Journal des essais](docs/journal_essais.md)
- [Architecture cible](docs/architecture_cible.md)
- [Paramètres techniques](docs/parametres.md)
- [Connexions des composantes matérielles](docs/connexions.md)
- [Inventaire des composantes matérielles principales](docs/inventaire_composantes.md)
