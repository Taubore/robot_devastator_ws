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
| `src/robot_devastator` | Logique principale du robot |
| `src/robot_devastator_bringup` | Assemblage des nœuds et paramètres de lancement |
| `docs` | Documentation du projet |
| `.vscode/tasks.json` | Tâches de build, de nettoyage et de lancement |
| `.vscode/launch.json` | Debug direct de nœuds Python précis |

## Interfaces ROS 2

### Topics

| Topic | Type | Producteur | Consommateur | Rôle |
|---|---|---|---|---|
| `/pico/commande_moteurs` | `commun/msg/ConsigneMoteurs` | `principal`, `evitement_obstacle_node` | `interface_pico_node` | Envoyer les consignes des moteurs gauche et droit vers le Pico |
| `/pico/commande_tourelle_deg` | `std_msgs/msg/Int32` | Outil de test ou `evitement_obstacle_node` | `interface_pico_node` | Commander l'angle du servo de tourelle en degrés |
| `/pico/distance_ultrason_mm` | `std_msgs/msg/Int32` | `interface_pico_node` | `evitement_obstacle_node` | Publier la distance ultrason mesurée en millimètres |
| `/pico/etat` | `std_msgs/msg/String` | `interface_pico_node` | Outil de diagnostic | Publier les lignes d'état reçues ou simulées côté Pico |

### Services

| Service | Type | Serveur | Client connu | Rôle |
|---|---|---|---|---|
| `/pico/ping` | `std_srvs/srv/Trigger` | `interface_pico_node` | `principal` | Vérifier que la chaîne ROS 2 vers Pico répond |
| `/pico/stop` | `std_srvs/srv/Trigger` | `interface_pico_node` | `principal` | Demander un arrêt explicite au Pico |
| `/generer_audio` | `commun/srv/GenererAudio` | `voix_piper` | Aucun client actif dans le comportement principal | Générer un fichier WAV avec Piper |
| `/jouer_audio` | `commun/srv/JouerAudio` | `voix_piper` | Aucun client actif dans le comportement principal | Jouer un fichier WAV déjà généré |

### Actions

Aucune action ROS 2 n'est implémentée actuellement.

## Nodes ROS 2

| Node | Package | Exécutable / module | État | Rôle |
|---|---|---|---|---|
| `interface_pico_node` | `interface_pico` | `interface_pico_node` / `interface_pico.interface_pico` | Actif | Exposer les topics et services Pico, puis traduire les commandes ROS 2 vers UART |
| `evitement_obstacle_node` | `robot_devastator` | `evitement_obstacle` / `robot_devastator.evitement_obstacle` | Expérimental | Avancer lentement, analyser un obstacle à gauche et à droite, puis tourner brièvement vers le côté le plus dégagé |
| `principal` | `robot_devastator` | `principal` / `robot_devastator.principal` | Actif | Valider la chaîne moteur ROS 2 vers Pico avec une courte séquence de test |
| `voix_piper` | `robot_devastator` | `voix_piper_service` / `robot_devastator.voix_piper_service` | Gelé | Services audio Piper amorcés, mais non intégrés au comportement principal actuel |

## Interfaces personnalisées

| Interface | Type | Rôle |
|---|---|---|
| `commun/msg/ConsigneMoteurs` | Message | Transporter les consignes moteur gauche et droite, sur une plage prévue de `-1000` à `1000` |
| `commun/srv/GenererAudio` | Service | Demander la génération d'un fichier audio à partir d'un texte |
| `commun/srv/JouerAudio` | Service | Demander la lecture d'un fichier audio existant |

## Utilisation avec VSCode (via Quick Access - F1)

### Build

Les tâches disponibles sont définies dans `.vscode/tasks.json`.

- `Tasks: Run Build Task > ROS 2 - Build Devastator`
- `Tasks: Run Task > ROS 2 - Build complet`

### Nettoyage ciblé

- `Tasks: Run Task > ROS 2 - Nettoyer packages Devastator`

Utiliser ce nettoyage après modification, suppression ou renommage d'un `.msg` ou `.srv`, ou si
ROS 2 semble conserver des artefacts obsolètes dans `build/` ou `install/`.

### Lancement / debug

Les assemblages ROS 2 sont centralisés dans `robot_devastator_bringup`. Utiliser les tâches
VSCode suivantes selon le besoin :

- `Tasks: Run Task > ROS 2 - Lancer interface Pico simulation`
- `Tasks: Run Task > ROS 2 - Lancer interface Pico réel`
- `Tasks: Run Task > ROS 2 - Lancer autonomie simple simulation`
- `Tasks: Run Task > ROS 2 - Lancer autonomie simple réel`

Les configurations de `.vscode/launch.json` servent seulement au debug direct d'un nœud Python
précis avec F5 :

`Nœud Python ROS 2` demande le module Python à exécuter, par exemple
`robot_devastator.evitement_obstacle`, `robot_devastator.principal` ou
`interface_pico.interface_pico`. Il demande ensuite si le mode simulation doit être activé.
La réponse `Non`, sélectionnée par défaut, transmet le mode matériel `reel`.

En CLI, la syntaxe équivalente pour passer un paramètre ROS 2 est
`ros2 run <package> <executable> --ros-args -p <parametre>:=<valeur>`.

L'autonomie simple fait avancer lentement le robot lorsque la distance ultrason est suffisante.
Devant un obstacle, elle arrête les moteurs, oriente la tourelle à gauche puis à droite, compare
deux mesures fraîches et tourne brièvement vers le côté le plus dégagé. Après recentrage de la
tourelle, elle reprend l'avance seulement si une nouvelle mesure avant est valide et dégagée.

## Commandes CLI de secours

Ces commandes restent utiles pour un diagnostic rapide hors VSCode.

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select commun interface_pico robot_devastator robot_devastator_bringup
source install/setup.bash
```

```bash
ros2 launch robot_devastator_bringup interface_pico_simulation.launch.yaml
ros2 launch robot_devastator_bringup interface_pico_reel.launch.yaml
ros2 launch robot_devastator_bringup autonomie_simple_simulation.launch.yaml
ros2 launch robot_devastator_bringup autonomie_simple_reel.launch.yaml
```

```bash
ros2 topic pub --once /pico/commande_moteurs commun/msg/ConsigneMoteurs "{gauche: 200, droite: 200}"
ros2 service call /pico/ping std_srvs/srv/Trigger
ros2 service call /pico/stop std_srvs/srv/Trigger
```

## Documentation détaillée

- [État actuel](docs/etat.md)
- [Architecture cible](docs/architecture_cible.md)
- [Paramètres techniques](docs/parametres.md)
- [Connexions des composantes matériel](docs/connexions.md)
- [Inventaire des composantes matériel principales](docs/inventaire_composantes.md)
