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
| `docs` | Documentation du projet |
| `.vscode/tasks.json` | Tâches de build et de nettoyage |
| `.vscode/launch.json` | Lancements et debug VSCode |

## Interfaces ROS 2

### Topics

| Topic | Type | Producteur | Consommateur | Rôle |
|---|---|---|---|---|
| `/pico/commande_moteurs` | `commun/msg/ConsigneMoteurs` | `principal` | `interface_pico_node` | Envoyer les consignes des moteurs gauche et droit vers le Pico |
| `/pico/commande_tourelle_deg` | `std_msgs/msg/Int32` | Outil de test ou futur nœud de décision | `interface_pico_node` | Commander l'angle du servo de tourelle en degrés |
| `/pico/distance_ultrason_mm` | `std_msgs/msg/Int32` | `interface_pico_node` | Futur nœud de décision | Publier la distance ultrason mesurée en millimètres |
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

Les configurations de lancement et de debug sont définies dans `.vscode/launch.json`.

## Commandes CLI de secours

Ces commandes restent utiles pour un diagnostic rapide hors VSCode.

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select commun interface_pico robot_devastator
source install/setup.bash
```

```bash
ros2 launch interface_pico interface_pico.launch.py mode_materiel:=simulation
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
